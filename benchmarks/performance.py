"""Versioned local decision latency/throughput experiments, separate from v0.2 accuracy runs."""
import argparse
import csv
import gc
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, digest, labels, read, sha, write  # noqa: E402

MODELS = ['english', 'multilingual', 'llama31_8b_instruct', 'qwen3_8b']
SEED = 'system1bench-performance-v1-20260928'
WORKLOADS = [(n, n, None) for n in
             ['ag_news', 'boolq', 'sst5', 'banking77', 'massive_en', 'massive_zh',
              'clinc150_oos', 'jev_laya_triage']]
WORKLOADS += [(f'needle_{n}', 'jev_laya_needle', n) for n in [100, 1000, 4000]]


def now():
    return datetime.now(timezone.utc).isoformat()


def ranked(cases, key):
    return sorted(cases, key=lambda c: hashlib.sha256(f'{SEED}|{key}|{c["id"]}'.encode()).hexdigest())


def freeze(destination):
    frozen = read(ROOT / 'data/frozen.json')
    if sha(ROOT / 'data/frozen.json') != read(ROOT / 'protocol_manifest.json')['prepared_sha256']:
        raise ValueError('Frozen accuracy inputs do not match their manifest')
    suites = {s['name']: s for s in frozen['suites']}
    workloads = []
    for name, source, length in WORKLOADS:
        s = suites[source]
        eligible = [c for c in s['cases'] if length is None or c['length_target'] == length]
        selected = ranked(eligible, name)
        warm, measured = selected[:8], selected[8:72]
        if len(measured) != 64 or len({digest(c['questions']) for c in warm + measured}) != 1:
            raise ValueError('Need 64 measured states and one common question schema')
        workloads.append(dict(name=name, source_suite=source, reference=s['reference'],
                              language=measured[0]['language'], source_length_target=length,
                              requests=64, decisions=sum(len(c['questions']) for c in measured),
                              questions_per_state=len(measured[0]['questions']),
                              candidate_counts={k: len(labels(q))
                                                for k, q in measured[0]['questions'].items()},
                              warmup_ids=[c['id'] for c in warm], case_ids=[c['id'] for c in measured],
                              request_hashes={c['id']: c['request_sha256'] for c in warm + measured}))
    value = dict(protocol='system1bench-performance-v1', seed=SEED, created_at=now(),
                 frozen_accuracy_sha256=sha(ROOT / 'data/frozen.json'),
                 accuracy_manifest_sha256=sha(ROOT / 'protocol_manifest.json'),
                 models=MODELS, rounds=8, batch_sizes=[1, 8, 32],
                 warmup_min_calls=3, warmup_min_seconds=1.0,
                 timing='resident-model state-to-structured-answer, uncached LLM prompt encoding included',
                 budget=frozen['budget'], workloads=workloads,
                 model_order_by_round=[MODELS[r % 4:] + MODELS[:r % 4] for r in range(8)])
    if Path(destination).exists():
        raise ValueError('Refuse to overwrite a frozen performance manifest')
    write(destination, value)


def load_workloads(manifest):
    if sha(ROOT / 'data/frozen.json') != manifest['frozen_accuracy_sha256']:
        raise ValueError('Frozen inputs changed')
    suites = {s['name']: {c['id']: c for c in s['cases']} for s in read(ROOT / 'data/frozen.json')['suites']}
    output = {}
    for spec in manifest['workloads']:
        by_id = suites[spec['source_suite']]
        ids = spec['warmup_ids'] + spec['case_ids']
        if len(set(ids)) != len(ids):
            raise ValueError('Warmup and measured IDs must be disjoint and unique')
        for cid in ids:
            c = by_id[cid]
            if digest({'state': c['state'], 'questions': c['questions']}) != spec['request_hashes'][cid]:
                raise ValueError('Selected request changed')
        output[spec['name']] = ([by_id[i] for i in spec['warmup_ids']], [by_id[i] for i in spec['case_ids']])
    return output


def smi(*args):
    return subprocess.check_output(['nvidia-smi', *args], text=True, timeout=15).strip()


def gpu_info(index):
    keys = ['uuid', 'name', 'driver_version', 'memory.total', 'memory.used', 'utilization.gpu',
            'temperature.gpu', 'clocks.sm', 'clocks.mem', 'power.draw', 'power.limit', 'pstate']
    text = smi('-i', str(index), '--query-gpu=' + ','.join(keys), '--format=csv,noheader,nounits')
    return dict(zip(keys, next(csv.reader([text], skipinitialspace=True))))


def foreign_gpu_pids(uuid, allowed_pid):
    text = smi('--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits')
    found = []
    for row in csv.reader(text.splitlines(), skipinitialspace=True):
        if len(row) == 2 and row[0] == uuid and int(row[1]) != allowed_pid:
            found.append(int(row[1]))
    return found


class Monitor:
    """Observer runs on its own physical core; worker only reads status outside timing."""
    def __init__(self, index, uuid, contract_path, output):
        self.output = output
        self.closed = False
        self.phase('setup')
        self.log = (output / 'telemetry.log').open('w')
        self.process = subprocess.Popen(
            [sys.executable, str(ROOT / 'benchmarks/performance_telemetry.py'),
             '--pid', str(os.getpid()), '--gpu', str(index), '--uuid', uuid,
             '--contract', str(contract_path), '--output', str(output)],
            stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while not (output / 'telemetry_status.json').exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                self.close()
                raise RuntimeError('Telemetry failed to start')
            time.sleep(0.05)
        self.check()

    def phase(self, phase, cell=None):
        write(self.output / 'measurement_phase.json', dict(phase=phase, cell=cell))

    def check(self):
        status = read(self.output / 'telemetry_status.json')
        if status['errors']:
            raise RuntimeError('; '.join(status['errors']))
        if self.process.poll() is not None and not self.closed:
            raise RuntimeError('Telemetry exited unexpectedly')

    def close(self):
        if self.process.poll() is not None and not self.closed:
            self.log.close()
            raise RuntimeError('Telemetry exited before shutdown was requested')
        self.closed = True
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=35)
        self.log.close()
        return read(self.output / 'telemetry_status.json')


def timed_predict(adapter, states, questions, language, budget, batch_size, clock=time.perf_counter, trace=None):
    # audit() primes LLMAdapter._cache; no such priming is allowed inside this experiment.
    if hasattr(adapter, '_cache'):
        adapter._cache.clear()
    adapter.synchronize()
    start = clock()
    output = adapter.predict(states, questions, language, budget, batch_size)
    adapter.synchronize()
    end = clock()
    seconds = end - start
    if trace is not None:
        trace.update(start_monotonic=start, end_monotonic=end)
    if seconds <= 0:
        raise ValueError('Non-positive measurement')
    return output, seconds


def validated_answers(cases, outputs):
    if len(outputs) != len(cases):
        raise ValueError('Output count mismatch')
    rows = []
    for case, output in zip(cases, outputs):
        if set(output['answers']) != set(case['questions']):
            raise ValueError('Missing or extra question answers')
        answers = {}
        for qid, q in case['questions'].items():
            answer = output['answers'][qid]
            pred, probs = decode(q, answer)
            answers[qid] = dict(prediction=pred, gold=str(case['gold'][qid]['label']),
                                probabilities=probs, answer=answer)
        rows.append(dict(id=case['id'], request_sha256=case['request_sha256'], answers=answers))
    return rows


def save_gzip(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_bytes(gzip.compress(json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                                             allow_nan=False).encode(), mtime=0))
    temp.replace(path)


def run_block(args):
    import torch
    from benchmarks.performance_contract import validate_contract, source_hashes, environment
    manifest = read(args.manifest)
    if args.model not in manifest['models'] or not 0 <= args.round < manifest['rounds']:
        raise ValueError('Unknown model/round')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != str(args.gpu):
        raise ValueError('Bind CUDA_VISIBLE_DEVICES to the declared physical GPU')
    contract = read(args.contract)
    if set(os.sched_getaffinity(0)) != set(contract['cpu_affinity']):
        raise ValueError('Worker CPU affinity differs from the run contract')
    out = Path(args.output) / f'round{args.round:02d}' / args.model
    if out.exists():
        raise ValueError('Do not overwrite an existing block, including failed blocks')
    out.mkdir(parents=True)
    before = gpu_info(args.gpu)
    if foreign_gpu_pids(before['uuid'], os.getpid()) or float(before['memory.used']) >= 500:
        raise RuntimeError('Selected GPU is not free before loading')
    contract = read(args.contract)
    validate_contract(contract, args.manifest, before)
    if any(os.environ.get(k) != v for k, v in contract['thread_env'].items()):
        raise ValueError('Thread environment differs from run contract')
    workloads = load_workloads(manifest)
    checkpoint = read(args.paths)[args.model]
    module, cls = ('system1bench.laya_adapter', 'LayaAdapter') if args.model in MODELS[:2] else ('system1bench.llm_adapter', 'LLMAdapter')
    started = now()
    adapter = getattr(importlib.import_module(module), cls)(args.model, checkpoint)
    reference = read(ROOT / 'results' / args.model / 'metadata.json')['signature']['model']
    if adapter.metadata['model_files_sha256'] != reference['model_files_sha256']:
        raise ValueError('Model bytes differ from the existing accuracy evaluation')
    if args.model in MODELS[:2] and adapter.metadata['laya_source_sha256'] != reference['laya_source_sha256']:
        raise ValueError('Laya code changed')
    meta = dict(status='RUNNING', started_at=started, model=args.model, round=args.round,
                manifest_sha256=sha(args.manifest), source_sha256=source_hashes(),
                contract_sha256=sha(args.contract), environment=environment(),
                adapter=adapter.metadata, gpu_before=before, cpu_affinity=sorted(os.sched_getaffinity(0)),
                thread_env={k: os.environ.get(k) for k in contract['thread_env']},
                torch_num_threads=torch.get_num_threads(), cells={})
    if meta['environment'] != contract['environment'] or meta['torch_num_threads'] != 4:
        raise ValueError('Backend configuration changed after model load')
    write(out / 'metadata.json', meta)
    monitor = Monitor(args.gpu, before['uuid'], args.contract, out)
    try:
        # Completeness checks are outside measurement. Cached tokens are subsequently discarded.
        audits = {}
        for name, (warm, measured) in workloads.items():
            audits[name] = {}
            for c in warm + measured:
                audit = adapter.audit(c['state'], c['questions'], manifest['budget'])
                if not all(a['complete'] for a in audit.values()):
                    raise ValueError(f'Incomplete input: {name}/{c["id"]}')
                audits[name][c['id']] = audit
        if hasattr(adapter, '_cache'):
            adapter._cache.clear()
        save_gzip(out / 'input_audits.json.gz', audits)
        cells = [(s, b) for s in manifest['workloads'] for b in manifest['batch_sizes']]
        random.Random(f'{SEED}|cells|{args.round}').shuffle(cells)
        if args.pilot:
            cells = [(next(s for s in manifest['workloads'] if s['name'] == 'boolq'), 1),
                     (next(s for s in manifest['workloads'] if s['name'] == 'needle_4000'), 32)]
        for spec, batch_size in cells:
            if foreign_gpu_pids(before['uuid'], os.getpid()):
                raise RuntimeError('Foreign GPU process at cell boundary')
            monitor.check()
            name = spec['name']
            warm, measured = workloads[name]
            measured = list(measured)
            random.Random(f'{SEED}|order|{args.round}|{name}').shuffle(measured)
            if args.pilot:
                measured = measured[:32]
            q, lang = measured[0]['questions'], spec['language']
            torch.cuda.empty_cache()
            monitor.phase('warmup', f'{name}.batch{batch_size}')
            warm_calls, warm_seconds, warm_timings = 0, 0.0, []
            while warm_calls < manifest['warmup_min_calls'] or warm_seconds < manifest['warmup_min_seconds']:
                batch = [warm[(warm_calls * batch_size + i) % len(warm)] for i in range(batch_size)]
                output, sec = timed_predict(adapter, [c['state'] for c in batch], q, lang, manifest['budget'], batch_size)
                validated_answers(batch, output)
                warm_calls += 1
                warm_seconds += sec
                warm_timings.append(sec)
                monitor.check()
                if warm_calls > 1000:
                    raise RuntimeError('Warmup did not reach the prescribed duration')
            adapter.synchronize()
            torch.cuda.reset_peak_memory_stats()
            batches = []
            monitor.phase('measured', f'{name}.batch{batch_size}')
            enabled = gc.isenabled()
            gc.disable()
            try:
                for start in range(0, len(measured), batch_size):
                    monitor.check()
                    batch = measured[start:start + batch_size]
                    states = [c['state'] for c in batch]
                    trace = {}
                    output, seconds = timed_predict(adapter, states, q, lang, manifest['budget'], len(batch), trace=trace)
                    rows = validated_answers(batch, output)  # never included in timed prediction
                    batches.append(dict(index=len(batches), requests=len(batch), decisions=sum(len(r['answers']) for r in rows),
                                        seconds=seconds, rows=rows, **trace))
            finally:
                if enabled:
                    gc.enable()
            monitor.phase('idle')
            adapter.synchronize()
            if foreign_gpu_pids(before['uuid'], os.getpid()):
                raise RuntimeError('Foreign GPU process at cell boundary')
            monitor.check()
            value = dict(model=args.model, round=args.round, workload=name, batch_size=batch_size,
                         manifest_sha256=meta['manifest_sha256'], source_sha256=meta['source_sha256'],
                         warmup_calls=warm_calls, warmup_predict_seconds=warm_seconds, warmup_timings=warm_timings,
                         contract_sha256=meta['contract_sha256'],
                         max_memory_allocated_bytes=torch.cuda.max_memory_allocated(),
                         max_memory_reserved_bytes=torch.cuda.max_memory_reserved(), batches=batches)
            file = f'{name}.batch{batch_size}.json.gz'
            save_gzip(out / file, value)
            meta['cells'][file] = dict(sha256=sha(out / file), seconds=sum(b['seconds'] for b in batches),
                                      requests=sum(b['requests'] for b in batches), decisions=sum(b['decisions'] for b in batches))
            write(out / 'metadata.json', meta)
            print('CELL', args.round, args.model, name, batch_size, meta['cells'][file]['seconds'], flush=True)
        meta['status'] = 'PILOT_DONE' if args.pilot else 'DONE'
    except BaseException as e:
        meta.update(status='FAILED', error=f'{type(e).__name__}: {e}')
        raise
    finally:
        try:
            status = monitor.close()
        except RuntimeError as exc:
            status = dict(errors=[str(exc)], monitor_cpu_affinity=contract['monitor_cpu_affinity'])
        meta['finished_at'] = now()
        meta['telemetry_errors'] = status['errors']
        meta['monitor_cpu_affinity'] = status['monitor_cpu_affinity']
        meta['telemetry_sha256'] = sha(out / 'telemetry.json.gz')
        if (out / 'input_audits.json.gz').exists():
            meta['input_audits_sha256'] = sha(out / 'input_audits.json.gz')
        if status['errors']:
            meta['status'] = 'FAILED'
        write(out / 'metadata.json', meta)
    monitor.check()


def orchestrate(args):
    import fcntl
    from benchmarks.performance_contract import validate_contract
    manifest = read(args.manifest)
    lock = ROOT / '.aris/compute/performance_gpu.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for round_id, order in enumerate(manifest['model_order_by_round']):
            for model in order:
                contract = read(args.contract)
                validate_contract(contract, args.manifest, gpu_info(args.gpu))
                meta_path = Path(args.output) / f'round{round_id:02d}' / model / 'metadata.json'
                if meta_path.exists():
                    m = read(meta_path)
                    if (m['status'] != 'DONE' or m['manifest_sha256'] != sha(args.manifest) or
                            m.get('contract_sha256') != sha(args.contract) or m.get('environment') != contract['environment'] or
                            m.get('source_sha256') != contract['source_sha256'] or m.get('thread_env') != contract['thread_env']):
                        raise RuntimeError('Incomplete block requires investigation; no automatic retry')
                    for file, info in m['cells'].items():
                        if sha(meta_path.parent / file) != info['sha256']:
                            raise RuntimeError('Saved block hash mismatch')
                    continue
                env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(args.gpu), OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
                           OPENBLAS_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1')
                cmd = ['taskset', '-c', ','.join(map(str, contract['cpu_affinity'])), sys.executable, str(Path(__file__)), 'run',
                       '--manifest', str(args.manifest), '--paths', str(args.paths), '--output', str(args.output),
                       '--contract', str(args.contract), '--gpu', str(args.gpu), '--model', model, '--round', str(round_id)]
                print('BLOCK', round_id, model, now(), flush=True)
                subprocess.run(cmd, env=env, cwd=ROOT, check=True)


def main():
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest='command', required=True)
    f = commands.add_parser('freeze')
    f.add_argument('--manifest', default='performance/v1/manifest.json')
    for name in ['run', 'orchestrate']:
        sub = commands.add_parser(name)
        sub.add_argument('--manifest', default='performance/v1/manifest.json')
        sub.add_argument('--contract', default='performance/v1/run_contract.json')
        sub.add_argument('--paths', default='.aris/compute/performance_paths.json')
        sub.add_argument('--output', default='performance/v1/raw')
        sub.add_argument('--gpu', type=int, default=2)
        if name == 'run':
            sub.add_argument('--model', required=True)
            sub.add_argument('--round', type=int, required=True)
            sub.add_argument('--pilot', action='store_true')
    args = p.parse_args()
    if args.command == 'freeze':
        freeze(args.manifest)
    elif args.command == 'run':
        run_block(args)
    else:
        orchestrate(args)


if __name__ == '__main__':
    main()
