"""Validate and summarize the controlled timing records without requiring a GPU."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, read, sha, write  # noqa: E402

NAMES = dict(english='Laya English', multilingual='Laya Multilingual',
             llama31_8b_instruct='Llama-3.1-8B-Instruct', qwen3_8b='Qwen3-8B')


def load_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def estimate(values):
    a = np.asarray(values, dtype=float)
    if len(a) != 8 or not np.isfinite(a).all():
        raise ValueError('Exactly eight finite round statistics are required')
    rng = np.random.default_rng(20260928)
    boot = np.median(a[rng.integers(0, len(a), size=(10000, len(a)))], axis=1)
    return dict(median=float(np.median(a)), ci95=list(map(float, np.quantile(boot, [0.025, 0.975]))),
                min=float(a.min()), max=float(a.max()), rounds=a.tolist())


def validate_cell(run, spec, batch_size, round_id, model, legacy, manifest=None):
    if (run['model'], run['round'], run['workload'], run['batch_size']) != (model, round_id, spec['name'], batch_size):
        raise ValueError('Cell identity mismatch')
    rows = [r for b in run['batches'] for r in b['rows']]
    ids = [r['id'] for r in rows]
    if len(ids) != 64 or len(set(ids)) != 64 or set(ids) != set(spec['case_ids']):
        raise ValueError('Missing/duplicate/unexpected measured requests')
    correct, decisions = 0, 0
    for batch in run['batches']:
        if batch['requests'] != batch_size or len(batch['rows']) != batch_size:
            raise ValueError('Unexpected batch shape')
        if not np.isfinite(batch['seconds']) or batch['seconds'] <= 0:
            raise ValueError('Invalid measured time')
        if batch['decisions'] != batch_size * spec['questions_per_state']:
            raise ValueError('Wrong decision denominator')
    minimum = manifest or dict(warmup_min_calls=3, warmup_min_seconds=1.0)
    if run['warmup_calls'] < minimum['warmup_min_calls'] or run['warmup_predict_seconds'] < minimum['warmup_min_seconds']:
        raise ValueError('Warmup requirement not met')
    if manifest is not None:
        warm = run['warmup_timings']
        if (len(warm) != run['warmup_calls'] or not all(np.isfinite(t) and t > 0 for t in warm) or
                abs(sum(warm) - run['warmup_predict_seconds']) > 1e-9):
            raise ValueError('Warmup timing record mismatch')
        previous_end = -float('inf')
        for batch in run['batches']:
            start, end = batch['start_monotonic'], batch['end_monotonic']
            if not np.isfinite([start, end]).all() or start < previous_end or abs(end - start - batch['seconds']) > 1e-8:
                raise ValueError('Invalid or overlapping timing interval')
            previous_end = end
    for row in rows:
        if row['request_sha256'] != spec['request_hashes'][row['id']]:
            raise ValueError('Input fingerprint mismatch')
        expected = legacy[row['id']]
        if set(row['answers']) != set(expected):
            raise ValueError('Missing question')
        for qid, record in row['answers'].items():
            ref = expected[qid]
            if row['request_sha256'] != ref['request_sha256'] or record['gold'] != ref['gold']:
                raise ValueError('Mismatch with historical frozen reference')
            q = dict(type=ref['type'])
            if ref['type'] == 'choice':
                q['criteria'] = {label: '' for label in ref['labels']}
            elif ref['type'] == 'score':
                q['criteria'] = [''] * len(ref['labels'])
            pred, probs = decode(q, record['answer'])
            if pred != record['prediction'] or probs != record['probabilities']:
                raise ValueError('Stored prediction is inconsistent with raw answer')
            correct += pred == ref['gold']
            decisions += 1
    if decisions != spec['decisions']:
        raise ValueError('Missing decisions')
    seconds = sum(b['seconds'] for b in run['batches'])
    latencies = np.array([b['seconds'] for b in run['batches']]) * 1000
    return dict(seconds=seconds, requests_per_second=64 / seconds, decisions_per_second=decisions / seconds,
                batch_p50_ms=float(np.quantile(latencies, 0.5)), batch_p95_ms=float(np.quantile(latencies, 0.95)),
                reference_agreement=correct / decisions, correct=correct, decisions=decisions,
                peak_allocated_gib=run['max_memory_allocated_bytes'] / 2**30,
                peak_reserved_gib=run['max_memory_reserved_bytes'] / 2**30)


def summarize(root):
    manifest_path = root / 'manifest.json'
    manifest = read(manifest_path)
    contract_path = root / 'run_contract.json'
    contract = read(contract_path)
    if contract['manifest_sha256'] != sha(manifest_path):
        raise ValueError('Contract manifest mismatch')
    for source, fingerprint in contract['source_sha256'].items():
        if sha(ROOT / source) != fingerprint:
            raise ValueError('Published measurement code differs from contract')
    if sha(ROOT / 'docs/PERFORMANCE_PROTOCOL.md') != contract['protocol_document_sha256']:
        raise ValueError('Published protocol differs from contract')
    legacy = {}
    for spec in manifest['workloads']:
        name = spec['source_suite']
        if name not in legacy:
            meta = read(ROOT / 'results/english/metadata.json')
            path = ROOT / 'results/english' / (name + '.json.gz')
            if sha(path) != meta['suites'][name]['sha256']:
                raise ValueError('Historical reference result hash mismatch')
            legacy[name] = {}
            for row in load_gzip(path)['rows']:
                legacy[name].setdefault(row['id'], {})[row['qid']] = row
    output = dict(protocol=manifest['protocol'], manifest_sha256=sha(manifest_path),
                  bootstrap='95% percentile CI of median over 8 round statistics; 10000 draws, seed 20260928',
                  contract_sha256=sha(contract_path), environment=contract['environment'], cells=[], token_audits={}, telemetry={}, block_metadata_sha256={})
    identity, code_identity, model_identities = None, None, {}
    all_raw = []
    for model in manifest['models']:
        grouped = {(s['name'], b): [] for s in manifest['workloads'] for b in manifest['batch_sizes']}
        telemetry = []
        audit_reference = None
        for r in range(manifest['rounds']):
            directory = root / 'raw' / f'round{r:02d}' / model
            meta = read(directory / 'metadata.json')
            if meta['status'] != 'DONE' or meta['telemetry_errors']:
                raise ValueError('Incomplete or contaminated block')
            if meta['manifest_sha256'] != output['manifest_sha256']:
                raise ValueError('Block used another manifest')
            if (meta.get('contract_sha256') != sha(contract_path) or
                    meta.get('environment') != contract['environment'] or
                    meta.get('thread_env') != contract['thread_env'] or
                    meta.get('cpu_affinity') != contract['cpu_affinity'] or
                    meta.get('monitor_cpu_affinity') != contract['monitor_cpu_affinity'] or
                    meta.get('torch_num_threads') != 4 or
                    meta['source_sha256'] != contract['source_sha256'] or
                    any(meta['gpu_before'][k] != v for k, v in contract['device'].items())):
                raise ValueError('Block violates frozen hardware/software/affinity contract')
            if identity is None:
                identity = meta['gpu_before']['uuid']
                code_identity = meta['source_sha256']
            if meta['gpu_before']['uuid'] != identity or meta['source_sha256'] != code_identity:
                raise ValueError('Hardware/code changed between blocks')
            if model in model_identities and meta['adapter'] != model_identities[model]:
                raise ValueError('Model/config changed between rounds')
            model_identities[model] = meta['adapter']
            expected_files = {f'{s["name"]}.batch{b}.json.gz' for s in manifest['workloads'] for b in manifest['batch_sizes']}
            if set(meta['cells']) != expected_files:
                raise ValueError('Missing or extra measured cells')
            for file, key in [('telemetry.json.gz', 'telemetry_sha256'), ('input_audits.json.gz', 'input_audits_sha256')]:
                if sha(directory / file) != meta[key]:
                    raise ValueError('Audit/telemetry hash mismatch')
            samples = load_gzip(directory / 'telemetry.json.gz')
            if not samples or any(x['foreign_compute_process_count'] for x in samples):
                raise ValueError('Missing telemetry or foreign compute process')
            streak, last_phase = 0, None
            for sample in samples:
                if any(sample['gpu'][k] != v for k, v in contract['device'].items()):
                    raise ValueError('Telemetry device identity changed')
                phase = sample['phase']
                delta = sample.get('cpu_interval')
                bad = (delta is not None and (
                    delta['other_busy_fraction_on_worker_cores'] > contract['max_other_cpu_busy_fraction'] or
                    delta['smt_sibling_busy_fraction'] > contract['max_sibling_busy_fraction']))
                streak = streak + 1 if phase == last_phase and phase['phase'] == 'measured' and bad else 0
                if streak >= contract['cpu_contention_consecutive_intervals']:
                    raise ValueError('CPU/SMT contention exceeds declared threshold')
                last_phase = phase
            telemetry.extend(samples)
            audits = load_gzip(directory / 'input_audits.json.gz')
            if audit_reference is None:
                audit_reference = audits
            elif audits != audit_reference:
                raise ValueError('Input encoding differs across rounds')
            for spec in manifest['workloads']:
                expected_questions = set(legacy[spec['source_suite']][spec['case_ids'][0]])
                if set(audits[spec['name']]) != set(spec['warmup_ids'] + spec['case_ids']):
                    raise ValueError('Missing or extra audited inputs')
                for cid in spec['warmup_ids'] + spec['case_ids']:
                    if (set(audits[spec['name']][cid]) != expected_questions or
                            not all(a['complete'] for a in audits[spec['name']][cid].values())):
                        raise ValueError('Incomplete input')
                for b in manifest['batch_sizes']:
                    file = f'{spec["name"]}.batch{b}.json.gz'
                    path = directory / file
                    if sha(path) != meta['cells'][file]['sha256']:
                        raise ValueError('Raw timing hash mismatch')
                    raw = load_gzip(path)
                    if raw.get('contract_sha256') != sha(contract_path):
                        raise ValueError('Raw contract mismatch')
                    if raw['manifest_sha256'] != output['manifest_sha256'] or raw['source_sha256'] != code_identity:
                        raise ValueError('Raw signature mismatch')
                    stats = validate_cell(raw, spec, b, r, model, legacy[spec['source_suite']], manifest)
                    if (meta['cells'][file]['requests'] != 64 or meta['cells'][file]['decisions'] != spec['decisions']):
                        raise ValueError('Metadata count mismatch')
                    if abs(stats['seconds'] - meta['cells'][file]['seconds']) > 1e-9:
                        raise ValueError('Metadata timing sum mismatch')
                    grouped[spec['name'], b].append(stats)
                    all_raw.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path)))
            output['block_metadata_sha256'][str((directory / 'metadata.json').relative_to(ROOT))] = sha(directory / 'metadata.json')
        output['telemetry'][model] = dict(samples=len(telemetry), foreign_process_observations=0,
                                        temperature_c=range_stat([x['gpu']['temperature.gpu'] for x in telemetry]),
                                        sm_clock_mhz=range_stat([x['gpu']['clocks.sm'] for x in telemetry]),
                                        power_w=range_stat([x['gpu']['power.draw'] for x in telemetry]),
                                        host_load_1min=range_stat([x['host_load_average'][0] for x in telemetry]),
                                        observed_cpu_intervals=sum('cpu_interval' in x for x in telemetry),
                                        other_cpu_busy_fraction=range_stat([x['cpu_interval']['other_busy_fraction_on_worker_cores'] for x in telemetry if 'cpu_interval' in x]),
                                        smt_sibling_busy_fraction=range_stat([x['cpu_interval']['smt_sibling_busy_fraction'] for x in telemetry if 'cpu_interval' in x]))
        output['token_audits'][model] = {}
        for spec in manifest['workloads']:
            encoded, state = [], []
            for cid in spec['case_ids']:
                for a in audit_reference[spec['name']][cid].values():
                    encoded.append(a['prompt_tokens'] if 'prompt_tokens' in a else a['state_tokens'] + a['head_tokens'])
                    state.append(a['state_tokens'])
            output['token_audits'][model][spec['name']] = dict(encoded_tokens_per_question=range_stat(encoded),
                                                              state_tokens_per_question=range_stat(state), complete=True)
            for b in manifest['batch_sizes']:
                rounds = grouped[spec['name'], b]
                cell = dict(model=model, workload=spec['name'], batch_size=b, requests_per_round=64,
                            decisions_per_round=spec['decisions'], rounds=8, reference=spec['reference'])
                for metric in ['seconds', 'requests_per_second', 'decisions_per_second', 'batch_p50_ms',
                               'batch_p95_ms', 'reference_agreement', 'peak_allocated_gib', 'peak_reserved_gib']:
                    cell[metric] = estimate([x[metric] for x in rounds])
                output['cells'].append(cell)
    output.update(gpu_uuid=identity, measured_code_sha256=code_identity, model_metadata=model_identities,
                  raw_files=all_raw, failures=0, full_input_coverage=True,
                  measured_requests=sum(c['requests_per_round'] * c['rounds'] for c in output['cells']),
                  measured_decisions=sum(c['decisions_per_round'] * c['rounds'] for c in output['cells']))
    return output


def range_stat(values):
    a = np.asarray(values, dtype=float)
    if not np.isfinite(a).all():
        raise ValueError('Invalid numeric data')
    return dict(min=float(a.min()), median=float(np.median(a)), max=float(a.max()))


def interval(value, scale=1):
    return f'{value["median"] * scale:.2f} [{value["ci95"][0] * scale:.2f}, {value["ci95"][1] * scale:.2f}]'


def report(root, summary):
    lines = ['# Controlled local decision performance (v1)', '',
             'All timings below are new local measurements using the [predeclared protocol](PERFORMANCE_PROTOCOL.md). '
             'They compare the stated adapters, not optimized serving engines or architecture-only speed. Jev is not evaluated.', '',
             f'The completed matrix contains {summary["measured_requests"]:,} measured logical requests and '
             f'{summary["measured_decisions"]:,} decisions, excluding warm-up. All inputs are complete; failures: 0. '
             'There are 11 workloads, four checkpoints, three batch sizes, and eight rounds on the same physical A100 80GB PCIe.', '',
             'Timing includes uncached prompt encoding and native structured-answer construction, with GPU synchronization. '
             'It excludes model loading, the input audit, file I/O, external network/queue time, and post-call validation. '
             'Each model used fresh worker processes, fixed CPU affinity/threads and disjoint warm-up inputs. '
             'GPU occupancy was monitored; the wider host remained shared.', '',
             'Cells show the median of eight round statistics and a 95% bootstrap interval over rounds. '
             'Intervals describe this fixed workload on this host; eight rounds are too few to certify rare-tail behavior. '
             'Reference-agreement intervals measure repeat variation on the same 64 states, not uncertainty over new dataset samples; '
             'a zero-width interval does not imply known population accuracy. '
             'p95 is descriptive, not a service-level guarantee. All round values, ranges, memory and token counts are in '
             '[summary.json](../performance/v1/summary.json).', '',
             '## Sequential request latency (batch size 1)', '',
             'A request includes every question in its state. Latency is never divided by the question count.', '',
             '| Workload | Model | Request p50 ms [95% CI] | Request p95 ms [95% CI] | Reference agreement % [95% CI] |',
             '|---|---|---:|---:|---:|']
    for c in summary['cells']:
        if c['batch_size'] == 1:
            lines.append(f'| {c["workload"]} | {NAMES[c["model"]]} | {interval(c["batch_p50_ms"])} | '
                         f'{interval(c["batch_p95_ms"])} | {interval(c["reference_agreement"], 100)} |')
    for batch in [8, 32]:
        lines += ['', f'## Fixed-batch throughput (batch size {batch})', '',
                  'Throughput is work divided by cumulative synchronized prediction time, excluding validation/file writes. '
                  'It is not maximum serving capacity under an arrival-rate or tail-latency constraint.', '',
                  '| Workload | Model | Requests/s [95% CI] | Decisions/s [95% CI] | Peak allocated GiB (median) | Reference agreement % |',
                  '|---|---|---:|---:|---:|---:|']
        for c in summary['cells']:
            if c['batch_size'] == batch:
                lines.append(f'| {c["workload"]} | {NAMES[c["model"]]} | {interval(c["requests_per_second"])} | '
                             f'{interval(c["decisions_per_second"])} | {c["peak_allocated_gib"]["median"]:.2f} | '
                             f'{c["reference_agreement"]["median"] * 100:.2f} |')
    lines += ['', '## Hardware observations', '',
              'These telemetry ranges span the monitored block, including input audit, warm-up, idle gaps and measurement. '
              'They are not active-kernel-only clock or power summaries. Raw phase labels and monotonic call boundaries '
              'support finer inspection. The observer ran on CPU 24, separately from worker cores 20–23 and their '
              'SMT siblings 84–87; no block may pass with an observed foreign GPU process or a sustained CPU/SMT '
              'threshold violation. Brief interference and shared memory-bandwidth effects remain possible.', '',
              '| Model | GPU telemetry samples | Foreign GPU process observations | SM clock MHz min–max | Temperature C min–max | Host 1-minute load min–max |',
              '|---|---:|---:|---:|---:|---:|']
    for model, t in summary['telemetry'].items():
        lines.append(f'| {NAMES[model]} | {t["samples"]} | 0 | {t["sm_clock_mhz"]["min"]:.0f}–{t["sm_clock_mhz"]["max"]:.0f} | '
                     f'{t["temperature_c"]["min"]:.0f}–{t["temperature_c"]["max"]:.0f} | '
                     f'{t["host_load_1min"]["min"]:.2f}–{t["host_load_1min"]["max"]:.2f} |')
    lines += ['', '## Interpretation and limits', '',
              '- Compare quality and speed within each workload. Reference agreement on a fixed 64-state subset is not a new overall accuracy leaderboard.',
              '- Source annotation caveats remain: synthetic workflow scores are teacher agreement. The original full v0.2 accuracy results are unchanged.',
              '- Shared-host CPU/memory contention, unlocked device clocks and finite telemetry sampling remain limitations despite observed GPU isolation and fixed CPU affinity.',
              '- Prompt lengths differ between tokenizers. All models receive the same semantic request; this is not identical FLOPs or token counts.',
              '- The LLM baseline performs direct next-token candidate scoring without generated reasoning. It is not vLLM, TensorRT-LLM, or a best-possible serving implementation.',
              '- No generated tokens/s, TTFT/TPOT, p99 certification, network latency, concurrency scaling, or MLPerf compliance is claimed.',
              '- No best-run selection or cross-task blended speed winner is reported. Full raw rounds, input IDs, telemetry, code/model hashes and failed-run policy support reproducibility.', '',
              'Instrumentation is confined to [performance.py](../benchmarks/performance.py), '
              '[performance_report.py](../benchmarks/performance_report.py), their tests, and the performance output directory. '
              'Existing accuracy adapters and results were not modified.', '']
    (ROOT / 'docs/PERFORMANCE_RESULTS.en.md').write_text('\n'.join(lines))
    with (root / 'metrics.csv').open('w') as f:
        metrics = ['batch_p50_ms', 'batch_p95_ms', 'requests_per_second', 'decisions_per_second', 'reference_agreement', 'peak_allocated_gib']
        fields = ['model', 'workload', 'batch_size', 'requests_per_round', 'decisions_per_round', 'rounds']
        fields += [m + suffix for m in metrics for suffix in ['_median', '_ci95_low', '_ci95_high', '_min', '_max']]
        w = csv.DictWriter(f, fields, lineterminator='\n')
        w.writeheader()
        for c in summary['cells']:
            row = {k: c[k] for k in fields[:6]}
            for m in metrics:
                row.update({m + '_median': c[m]['median'], m + '_ci95_low': c[m]['ci95'][0],
                            m + '_ci95_high': c[m]['ci95'][1], m + '_min': c[m]['min'], m + '_max': c[m]['max']})
            w.writerow(row)
    homepage(summary)


def homepage(summary):
    lines = ['<!-- BEGIN GENERATED PERFORMANCE -->', '## Controlled local decision speed — all workloads', '',
             'These are our own new measurements on one A100 80GB PCIe, using the existing four adapters. '
             'Each cell shows the median over eight rounds and its 95% bootstrap interval. '
             'Encoding and structured-answer construction are included; model loading, network/queue time and validation are excluded. '
             'The full [performance report](docs/PERFORMANCE_RESULTS.en.md) includes p95, reference agreement, memory, token counts and limits. '
             'See the [frozen protocol](docs/PERFORMANCE_PROTOCOL.md) and [raw records](performance/v1/raw).', '',
             '| Workload | Model | Batch 1 request p50 ms | Batch 8 requests/s | Batch 32 requests/s |',
             '|---|---|---:|---:|---:|']
    cells = {(c['workload'], c['model'], c['batch_size']): c for c in summary['cells']}
    workloads = list(dict.fromkeys(c['workload'] for c in summary['cells']))
    for workload in workloads:
        for model in NAMES:
            lines.append(f'| {workload} | {NAMES[model]} | {interval(cells[workload, model, 1]["batch_p50_ms"])} | '
                         f'{interval(cells[workload, model, 8]["requests_per_second"])} | '
                         f'{interval(cells[workload, model, 32]["requests_per_second"])} |')
    lines += ['', 'Requests include all questions in a state. Fixed-batch throughput is completed requests divided by summed '
              'prediction time; it is not server capacity. No generated-token speed, optimal-serving-engine result, '
              'architecture-only speedup, or overall cross-task winner is claimed. Jev was not run.', '',
              '<!-- END GENERATED PERFORMANCE -->']
    path = ROOT / 'README.md'
    text = path.read_text()
    marker = '<!-- BEGIN GENERATED PERFORMANCE -->'
    if marker in text:
        start = text.index(marker)
        end = text.index('<!-- END GENERATED PERFORMANCE -->', start) + len('<!-- END GENERATED PERFORMANCE -->')
        text = text[:start] + '\n'.join(lines) + text[end:]
    else:
        text = text.replace('## Run provenance', '\n'.join(lines) + '\n\n## Run provenance', 1)
    path.write_text(text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='performance/v1')
    args = p.parse_args()
    root = Path(args.root).resolve()
    summary = summarize(root)
    write(root / 'summary.json', summary)
    report(root, summary)
    print('Validated', len(summary['raw_files']), 'raw cells;', summary['measured_decisions'], 'decisions')


if __name__ == '__main__':
    main()
