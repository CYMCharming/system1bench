"""Fresh-input, native-API matched latency; fail closed on contamination."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, sha
from system1bench.decision_models import validate_distribution
from research.model_expansion_v3.adapter import get_adapter
from research.startlux_transfer_v1.run import read, save
from benchmarks.performance import gpu_info, foreign_gpu_pids
from benchmarks.performance_telemetry import cpu_snapshot, cpu_delta

HERE = Path(__file__).resolve().parent
MODELS = ['intern_08b', 'intern_2b', 'intern_4b', 'kev_08b', 'kev_4b', 'kev_9b',
          'startlux_4b', 'qwen35_08b', 'qwen35_4b', 'qwen35_9b', 'qwen3_8b',
          'llama32_1b_public', 'llama32_3b_public', 'nanojev']
STATE = ('Customer support policy: refund a damaged item purchased within 30 days. '
         'Otherwise deny the refund. Require human review for orders above 200 dollars. '
         'Severity is 0 for no damage, 1 for cosmetic damage, 2 for unusable items. '
         'Case: purchase was 12 days ago, the item is unusable, and the order cost 85 dollars.')
BASE = {
    'action': dict(type='choice', instructions='Select the action required by the policy.',
                   criteria={'refund': 'Issue the refund.', 'deny': 'Deny the refund.', 'hold': 'Hold for more information.'}),
    'review': dict(type='noul', instructions='Does this case require human review?',
                   criteria={'false': 'Human review is not required.', 'true': 'Human review is required.'}),
    'severity': dict(type='score', instructions='Select the severity category from the policy.',
                     criteria=['No damage.', 'Cosmetic damage.', 'The item cannot be used.'])}


def workloads():
    eight = {**BASE, **{f'field_{i}': dict(BASE['action' if i % 2 else 'review']) for i in range(5)}}
    return {'one_field': {'action': BASE['action']}, 'three_fields': BASE, 'eight_fields': eight}


def clean_gpu(gpu, uuid):
    info = gpu_info(gpu)
    assert info['uuid'] == uuid, 'Physical GPU changed'
    assert not foreign_gpu_pids(uuid, os.getpid()), 'Foreign GPU compute process; no speed score'
    return info


def main():
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=MODELS, required=True)
    parser.add_argument('--gpu', type=int, default=1)
    args = parser.parse_args()
    os.sched_setaffinity(0, {20, 21, 22, 23})
    cores = [20, 21, 22, 23]
    siblings = sorted({int(n) for c in cores for n in
        Path(f'/sys/devices/system/cpu/cpu{c}/topology/thread_siblings_list').read_text().strip().split(',')} - set(cores))
    assert siblings
    device = gpu_info(args.gpu)
    clean_gpu(args.gpu, device['uuid'])
    pin = read(ROOT / '.aris/startlux_transfer_paths.json')[args.model]
    adapter = get_adapter(args.model, pin)
    adapter.torch.backends.cudnn.allow_tf32 = False
    contract = dict(model=args.model, adapter=adapter.metadata, device=device,
        protocol_sha256=sha(HERE / 'PROTOCOL.md'), runner_sha256=sha(__file__),
        adapter_sha256=sha(ROOT / 'research/model_expansion_v3/adapter.py'),
        native_adapter_sha256=sha(ROOT / 'research/startlux_transfer_v1/adapter.py'),
        shared_adapter_sha256=sha(ROOT / 'system1bench/decision_models.py'),
        expansion_adapter_sha256=sha(ROOT / 'research/model_expansion_v2/adapter.py'),
        cpu_affinity=cores, cpu_smt_siblings=siblings, seed=20261005,
        workloads_sha256=digest([STATE, workloads()]), warmup_requests=10, rounds=5, requests_per_round=20,
        exclusive_gpu_process_checks=True, whole_host_exclusive=False, cpu_contention_threshold=.15,
        timings_include='fresh tokenization, native prediction and synchronization; output validation after timing')
    folder = HERE / 'results' / args.model
    if (folder / 'summary.json').exists():
        assert read(folder / 'summary.json')['status'] == 'DONE', 'Do not overwrite an incomplete attempt'
        print('ALREADY_DONE', args.model, flush=True)
        return
    save(folder / 'metadata.json', dict(status='RUNNING', contract=contract,
        started_at=datetime.now(timezone.utc).isoformat()))
    rows, cells, telemetry = [], {}, []
    for workload, questions in workloads().items():
        audit = adapter.audit(STATE, questions)
        getattr(adapter, 'cache', {}).clear()

        def invoke():
            getattr(adapter, 'cache', {}).clear()
            adapter.synchronize()
            started = time.perf_counter_ns()
            output = adapter.predict(STATE, questions)
            adapter.synchronize()
            elapsed = (time.perf_counter_ns() - started) / 1e6
            assert set(output) == set(questions)
            for qid, question in questions.items(): validate_distribution(question, output[qid])
            return elapsed

        for _ in range(10): invoke()
        clean_gpu(args.gpu, device['uuid'])
        before = cpu_snapshot(os.getpid(), cores + siblings)
        means, use = [], []
        for round_id in range(5):
            clean_gpu(args.gpu, device['uuid'])
            round_times = []
            for index in range(20):
                elapsed = invoke()
                row = dict(model=args.model, workload=workload, round=round_id, index=index,
                           fields=len(questions), milliseconds=elapsed, valid=True)
                rows.append(row)
                round_times.append(elapsed)
            telemetry.append(dict(workload=workload, round=round_id, gpu=clean_gpu(args.gpu, device['uuid'])))
            means.append(float(np.mean(round_times)))
            use.extend(round_times)
            print('MEASURED', args.model, workload, round_id, round(float(np.mean(round_times)), 3), flush=True)
        after = cpu_snapshot(os.getpid(), cores + siblings)
        contention = cpu_delta(before, after, cores, siblings)
        # Saturated neighbours cannot become a model's measured speed result.
        assert contention['other_busy_fraction_on_worker_cores'] <= .15, 'CPU contention; no speed score'
        assert contention['smt_sibling_busy_fraction'] <= .15, 'SMT contention; no speed score'
        resampled = np.random.default_rng(20261005).choice(means, (2000, 5), replace=True).mean(axis=1)
        unique = {a['token_sha256']: a['prompt_tokens'] for a in audit.values()}
        cells[workload] = dict(n=100, fields=len(questions), mean_ms=float(np.mean(use)),
            median_ms=float(np.median(use)), p95_ms=float(np.quantile(use, .95)),
            mean_round_ci95_ms=np.quantile(resampled, [.025, .975]).tolist(),
            requests_per_second=100000 / sum(use), fields_per_second=len(questions) * 100000 / sum(use),
            round_mean_ms=means, distinct_prompt_encodings=len(unique), prompt_token_lengths=sorted(unique.values()),
            cpu_contention=contention)
    raw = folder / 'raw.jsonl'
    raw.write_text(''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in rows))
    save(folder / 'telemetry.json', telemetry)
    save(folder / 'summary.json', dict(status='DONE', model=args.model, workloads=cells,
        raw_sha256=sha(raw), metadata_sha256=sha(folder / 'metadata.json'),
        telemetry_sha256=sha(folder / 'telemetry.json'), finished_at=datetime.now(timezone.utc).isoformat()))
    print('COMPLETE_SPEED', args.model, flush=True)


if __name__ == '__main__': main()
