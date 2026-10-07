"""Resumable accuracy-only pilot; no speed claims on a shared GPU."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, request, sha
from system1bench.decision_models import validate_distribution
from research.startlux_transfer_v1.adapter import get_adapter
from research.public_expansion_v1.prepare import HERE, PRIVATE, save


def score(cases, rows):
    by_id = {row['id']: row for row in rows}
    if len(rows) != len(cases) or len(by_id) != len(cases):
        raise ValueError('Incomplete or duplicate predictions')
    allowed = list(cases[0]['questions']['decision']['criteria'])
    support, predicted, correct = Counter(), Counter(), Counter()
    failures = 0
    for case in cases:
        row = by_id[case['id']]
        gold = case['gold']['decision']['label']
        support[gold] += 1
        pred = row.get('prediction')
        if row.get('error') or pred is None:
            failures += 1
        else:
            predicted[pred] += 1
            if pred == gold:
                correct[gold] += 1
    f1s = [2 * correct[label] / (support[label] + predicted[label])
           if support[label] + predicted[label] else 0 for label in allowed]
    return dict(n=len(cases), correct=sum(correct.values()), accuracy=sum(correct.values()) / len(cases),
                macro_f1=sum(f1s) / len(f1s), failures=failures,
                reference_support=dict(support), per_class_correct=dict(correct))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, choices=['kev_4b', 'qwen35_4b'])
    parser.add_argument('--pins', default=str(ROOT / '.aris/startlux_transfer_paths.json'))
    args = parser.parse_args()
    manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
    frozen = PRIVATE / 'pilot.frozen.json'
    if sha(frozen) != manifest['artifacts_sha256']['pilot.frozen.json']:
        raise ValueError('Frozen pilot mismatch')
    suites = json.loads(frozen.read_text(encoding='utf-8'))['suites']
    cases = [(suite['name'], case) for suite in suites for case in suite['cases']]
    assert len(cases) == 354
    pins = json.loads(Path(args.pins).read_text(encoding='utf-8'))
    pin = pins[args.model]
    config_paths = [Path(pin['path']) / 'config.json']
    if 'base_path' in pin:
        config_paths.append(Path(pin['base_path']) / 'config.json')
    for config_path in config_paths:
        if config_path.exists() and json.loads(config_path.read_text()).get('quantization_config'):
            raise ValueError('Quantized checkpoint rejected')
    out = PRIVATE / 'runs' / args.model
    out.mkdir(parents=True, exist_ok=True)
    binding = dict(model=args.model, pilot=True, expected_requests=354,
        task='full ontology intent classification; original candidate order only',
        accuracy_only=True, shared_gpu=True, timing_comparable=False,
        data_manifest_sha256=sha(HERE / 'manifest.json'), frozen_sha256=sha(frozen),
        runner_sha256=sha(Path(__file__)), pins_sha256=sha(args.pins),
        checkpoint={k: v for k, v in pin.items() if k not in {'path', 'base_path'}},
        adapter_sha256={name: sha(ROOT / name) for name in
                       ['system1bench/decision_models.py', 'system1bench/llm_adapter.py',
                        'research/startlux_transfer_v1/adapter.py', 'research/model_expansion_v2/adapter.py']})
    if (out / 'binding.json').exists():
        if json.loads((out / 'binding.json').read_text(encoding='utf-8')) != binding:
            raise ValueError('Resume binding changed')
    else:
        save(out / 'binding.json', binding)
    if (out / 'DONE.json').exists():
        print('Already complete; no inference repeated', flush=True)
        return
    auditor = get_adapter(args.model, pin, load=False)
    audits = []
    for suite, case in cases:
        audit = auditor.audit(**request(case))
        if not audit['decision']['complete'] or audit['decision']['options'] != len(case['questions']['decision']['criteria']):
            raise ValueError('Full candidate compatibility audit failed')
        audits.append(dict(id=case['id'], suite=suite, audit=audit))
    save(out / 'compatibility.json', dict(model=args.model, metadata=auditor.metadata, audited_requests=len(audits),
                                         complete=True, cases=audits))
    del auditor
    print(f'{args.model}: compatibility PASS all 354 requests; full151/77 candidates retained', flush=True)
    model = get_adapter(args.model, pin, load=True)
    save(out / 'model_metadata.json', model.metadata)
    raw = out / 'raw.jsonl'
    rows = [json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()] if raw.exists() else []
    expected = {case['id']: (suite, digest(request(case))) for suite, case in cases}
    by_id = {}
    for row in rows:
        if row['id'] in by_id or (row['suite'], row['request_sha256']) != expected.get(row['id']):
            raise ValueError('Resume contains duplicate, unknown or changed request')
        by_id[row['id']] = row
    with raw.open('a', encoding='utf-8') as stream:
        for suite, case in cases:
            if case['id'] in by_id:
                continue
            payload = request(case)
            row = dict(id=case['id'], suite=suite, request_sha256=digest(payload))
            try:
                probs = model.predict(**payload)['decision']
                pred, dist = validate_distribution(case['questions']['decision'], probs)
                row.update(prediction=pred, probabilities=dist, error=None)
            except Exception as exc:
                row.update(prediction=None, probabilities=None, error=type(exc).__name__)
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            rows.append(row)
            if len(rows) % 20 == 0 or len(rows) == 354:
                save(out / 'status.json', dict(model=args.model, completed=len(rows), expected=354,
                                              accuracy_only=True, updated_at=datetime.now(timezone.utc).isoformat()))
                print(f'{args.model}: {len(rows)}/354 requests recorded', flush=True)
    summary = {suite['name']: score(suite['cases'], [row for row in rows if row['suite'] == suite['name']]) for suite in suites}
    save(out / 'summary.json', dict(model=args.model, pilot=True, official_full_test=False, accuracy_only=True,
                                   latency_not_reported=True, metrics=summary))
    save(out / 'DONE.json', dict(model=args.model, n=354, binding_sha256=sha(out / 'binding.json'),
                               raw_sha256=sha(raw), metadata_sha256=sha(out / 'model_metadata.json'),
                               summary_sha256=sha(out / 'summary.json'), compatibility_sha256=sha(out / 'compatibility.json')))
    print(f'{args.model}: DONE all354 request errors remain in denominator', flush=True)


if __name__ == '__main__':
    main()
