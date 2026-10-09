"""Frozen, resumable completion of missing model x intent/transfer cells."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, digest, labels, request, sha
from system1bench.decision_models import validate_distribution
from research.evaluation_completion_v1.adapter import get_adapter

HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / '.aris/evaluation_completion_v1'
MODELS = ['english', 'multilingual', 'llama31_8b_instruct', 'qwen3_8b', 'jev-1.13.0',
          'kev_08b', 'kev_4b', 'kev_9b', 'nanojev', 'qwen35_9b', 'kev_27b',
          'qwen35_08b', 'qwen35_4b', 'qwen38_27b', 'startlux_4b', 'startlux_9b',
          'startlux_27b', 'intern_4b', 'intern_08b', 'intern_2b',
          'llama32_1b_public', 'llama32_3b_public', 'qwen3_17b']
CODE = ['research/evaluation_completion_v1/run.py', 'research/evaluation_completion_v1/adapter.py',
        'research/model_expansion_v3/adapter.py', 'research/startlux_transfer_v1/adapter.py',
        'research/model_expansion_v2/adapter.py', 'system1bench/decision_models.py',
        'system1bench/laya_adapter.py', 'system1bench/llm_adapter.py',
        'system1bench/common.py', 'benchmarks/jev_api.py']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
    temp.replace(path)


def prepare():
    pins = read(ROOT / '.aris/startlux_transfer_paths.json')
    historical = read(ROOT / '.aris/compute/performance_paths.json')
    for name in ('english', 'multilingual', 'llama31_8b_instruct'):
        pins[name] = dict(path=historical[name], repo='convaiinnovations/laya' if name != 'llama31_8b_instruct'
                          else 'meta-llama/Llama-3.1-8B-Instruct',
                          revision='55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851' if name != 'llama31_8b_instruct'
                          else 'local_snapshot_identified_by_file_hashes')
    pins['jev-1.13.0'] = dict(repo='https://api.typesafe.ai/v1/systemone', revision='jev-1.13.0')
    save(PRIVATE / 'pins.json', pins)
    intent = read(ROOT / 'research/public_expansion_v1/manifest.json')
    manifest = dict(version=1, created_at=datetime.now(timezone.utc).isoformat(), cohort=MODELS,
                    protocol_sha256=sha(HERE / 'PROTOCOL.md'), code_sha256={p: sha(ROOT / p) for p in CODE},
                    pins_sha256=sha(PRIVATE / 'pins.json'),
                    model_pins={m: {k: v for k, v in pin.items() if k not in {'path', 'base_path'}} for m, pin in pins.items()},
                    inputs={'intent': dict(path='.aris/public_expansion_v1/full.frozen.json',
                                           sha256=intent['artifacts_sha256']['full.frozen.json'], expected=8580),
                            'transfer': dict(path='data/startlux_transfer_v1/frozen.json',
                                             sha256=sha(ROOT / 'data/startlux_transfer_v1/frozen.json'), expected=1152)},
                    domains={'policy': ['refund', 'access', 'routing'], 'legal': ['legal'], 'science': ['science'],
                             'causal': ['cladder'], 'code': ['cruxeval'], 'finance': ['finentity'],
                             'tools': ['when2call'], 'intent': ['clinc150_full', 'banking77_full']},
                    complete_required=True, option_exceeded_excluded=True,
                    unsupported_choice_caps={'startlux_4b': 26, 'startlux_9b': 26, 'startlux_27b': 26,
                                             'intern_08b': 62, 'intern_2b': 62, 'intern_4b': 62})
    destination = HERE / 'manifest.json'
    if destination.exists():
        raise ValueError('Manifest already frozen; do not overwrite')
    save(destination, manifest)


def run(name, panel, audit_only=False):
    manifest = read(HERE / 'manifest.json')
    assert sha(HERE / 'PROTOCOL.md') == manifest['protocol_sha256']
    assert all(sha(ROOT / p) == h for p, h in manifest['code_sha256'].items())
    assert sha(PRIVATE / 'pins.json') == manifest['pins_sha256']
    spec = manifest['inputs'][panel]
    frozen_path = ROOT / spec['path']
    assert sha(frozen_path) == spec['sha256']
    suites = read(frozen_path)['suites']
    cases = [(s, c) for s in suites for c in s['cases']]
    assert sum(len(c['questions']) for _, c in cases) == spec['expected']
    pin = read(PRIVATE / 'pins.json')[name]
    folder = PRIVATE / panel / name
    binding = dict(model=name, panel=panel, expected=spec['expected'],
                   frozen_sha256=sha(frozen_path), manifest_sha256=sha(HERE / 'manifest.json'),
                   checkpoint=manifest['model_pins'][name], code_sha256=manifest['code_sha256'],
                   batch_requests=1, timing_comparable=False, original_precision=True)
    if (folder / 'binding.json').exists():
        assert read(folder / 'binding.json') == binding, 'Resume binding changed'
    save(folder / 'binding.json', binding)
    if (folder / 'DONE.json').exists():
        print(name, panel, 'already DONE', flush=True)
        return
    hosted = name == 'jev-1.13.0'
    adapter = None if hosted else get_adapter(name, pin, load=False)
    audits = []
    for suite, case in cases:
        audit = ({qid: dict(complete=True, options=len(labels(q)), server_tokenization_verified=False)
                  for qid, q in case['questions'].items()} if hosted else adapter.audit(**request(case)))
        for qid, question in case['questions'].items():
            if not audit[qid]['complete'] or audit[qid]['options'] != len(labels(question)):
                raise ValueError('Incomplete input or ontology: ' + case['id'])
        audits.append(dict(id=case['id'], suite=suite['name'], audit=audit))
    save(folder / 'compatibility.json', dict(complete=True, audited_requests=len(cases), cases=audits,
                                           tokenization_verified=not hosted))
    print(name, panel, 'all full-input audits PASS', flush=True)
    if audit_only:
        return
    if hosted:
        from benchmarks.jev_api import Client, MODEL
        client = Client('/home/cym/.config/system1bench/jev.key', rate=8, max_usd=10,
                        continue_invalid_decision=True)
        metadata = dict(model=MODEL, adapter='jev_official_hosted', truncation=False, quantized=False,
                        checkpoint=manifest['model_pins'][name], server_tokenization_verified=False,
                        prediction_semantics='validated official reported choice', dtype='hosted_unknown')
    else:
        if name not in {'english', 'multilingual', 'llama31_8b_instruct'}:
            adapter = get_adapter(name, pin, load=True)
        metadata = adapter.metadata
    save(folder / 'model_metadata.json', metadata)
    raw = folder / 'raw.jsonl'
    rows = [json.loads(line) for line in raw.read_text().splitlines()] if raw.exists() else []
    expected = {(s['name'], c['id'], qid): (digest(request(c)), str(c['gold'][qid]['label']))
                for s, c in cases for qid in c['questions']}
    seen = set()
    for row in rows:
        key = row['suite'], row['id'], row['qid']
        assert key not in seen and expected[key] == (row['request_sha256'], row['gold'])
        seen.add(key)
    if hosted:
        client.tokens = sum((a.get('usage') or {}).get('input_tokens', 0)
                            for r in rows for a in (r.get('hosted_evidence') or {}).get('attempts', []))
    pending = [(s, c) for s, c in cases if not all((s['name'], c['id'], q) in seen for q in c['questions'])]

    def infer(item):
        suite, case = item
        if hosted:
            record = client.predict((suite['name'], dict(case, request_sha256=digest(request(case)))))
            if record is None:
                raise RuntimeError('Hosted stop or budget cap; retain incomplete journal')
            return suite, case, record, None
        try:
            return suite, case, adapter.predict(**request(case)), None
        except Exception as exc:
            return suite, case, None, type(exc).__name__

    executor = ThreadPoolExecutor(max_workers=8) if hosted else None
    results = executor.map(infer, pending) if executor else map(infer, pending)
    try:
        with raw.open('a', encoding='utf-8', newline='\n') as stream:
            for suite, case, output, failure in results:
                for qid, question in case['questions'].items():
                    row = dict(model=name, suite=suite['name'], id=case['id'], qid=qid,
                               request_sha256=digest(request(case)), gold=str(case['gold'][qid]['label']),
                               condition=case.get('expansion_condition', 'original'),
                               base_id=case.get('base_id'), domain=case.get('metadata', {}).get('domain'),
                               gold_distribution=case['gold'][qid].get('distribution'))
                    try:
                        if failure:
                            raise RuntimeError(failure)
                        if hosted:
                            row['hosted_evidence'] = output
                            if output['error']:
                                raise RuntimeError(output['error'])
                            pred, probs = decode(question, output['response']['answers'][qid])
                            probabilities = dict(zip(labels(question), probs))
                        else:
                            pred, probabilities = validate_distribution(question, output[qid])
                        row.update(prediction=pred, probabilities=probabilities, error=None)
                    except Exception as exc:
                        row.update(prediction=None, probabilities=None, error=failure or type(exc).__name__)
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
                    stream.flush()
                    rows.append(row)
                if adapter:
                    getattr(adapter, 'cache', {}).clear()
                if len(rows) % 100 == 0 or len(rows) == spec['expected']:
                    save(folder / 'status.json', dict(model=name, panel=panel, completed=len(rows),
                                                     expected=spec['expected'], updated_at=datetime.now(timezone.utc).isoformat(),
                                                     errors=sum(r['error'] is not None for r in rows)))
                    print(name, panel, len(rows), '/', spec['expected'], flush=True)
    finally:
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
    assert len(rows) == spec['expected']
    save(folder / 'DONE.json', dict(model=name, panel=panel, n=len(rows),
                                   errors=sum(r['error'] is not None for r in rows),
                                   finished_at=datetime.now(timezone.utc).isoformat(),
                                   **{k + '_sha256': sha(folder / f) for k, f in
                                      [('binding', 'binding.json'), ('raw', 'raw.jsonl'),
                                       ('metadata', 'model_metadata.json'), ('compatibility', 'compatibility.json')]}))
    print(name, panel, 'DONE', len(rows), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--models', nargs='+')
    parser.add_argument('--panel', choices=['intent', 'transfer'], default='intent')
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
        return
    for name in args.models or []:
        if not args.worker:
            subprocess.run([sys.executable, str(Path(__file__)), '--models', name, '--panel', args.panel,
                            '--worker', *(['--audit-only'] if args.audit_only else [])], check=False)
            continue
        try:
            run(name, args.panel, args.audit_only)
        except Exception as exc:
            save(PRIVATE / args.panel / name / 'admission_error.json',
                 dict(model=name, panel=args.panel, scored=False, error=type(exc).__name__, detail=str(exc)))
            print(name, args.panel, 'STOPPED', type(exc).__name__, str(exc), flush=True)
            raise


if __name__ == '__main__':
    main()
