"""Evaluate a new pinned model on the immutable v1 4,905-decision panel."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, labels, read, request, sha, write
from system1bench.decision_models import validate_distribution
from research.model_expansion_v2.adapter import ExpansionAdapter

HERE = ROOT / 'research/model_expansion_v2'
SOURCE = ROOT / 'research/model_expansion_v1'
MODELS = ('kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, choices=MODELS)
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--limit', type=int, default=0, help='Smoke only; cannot write production results')
    args = parser.parse_args()
    manifest, frozen = read(HERE / 'manifest.json'), read(SOURCE / 'frozen.json')
    assert sha(SOURCE / 'frozen.json') == manifest['prepared_sha256']
    assert sha(HERE / 'PROTOCOL.md') == manifest['protocol_sha256']
    assert sha(HERE / 'adapter.py') == manifest['adapter_sha256']
    assert sha(__file__) == manifest['runner_sha256']
    pin = read(ROOT / '.aris/model_expansion_v2_paths.json')[args.model]
    assert pin['revision'] == manifest['model_pins'][args.model]['revision']
    assert pin['repo'] == manifest['model_pins'][args.model]['repo']
    records = [(suite, case) for suite in frozen['suites'] for case in suite['cases']]
    assert sum(len(case['questions']) for _, case in records) == 4905
    if args.limit:
        records = records[:args.limit]
    adapter = ExpansionAdapter(args.model, pin, load=not args.audit_only)
    signature = dict(model=adapter.metadata, manifest_sha256=sha(HERE / 'manifest.json'),
                     runner_sha256=sha(__file__), adapter_sha256=sha(HERE / 'adapter.py'),
                     shared_adapter_sha256=sha(ROOT / 'system1bench/decision_models.py'))
    out = HERE / 'results' / args.model
    if args.audit_only or args.limit:
        for suite, case in records:
            audit = adapter.audit(case['state'], case['questions'])
            answer = None if args.audit_only else adapter.predict(case['state'], case['questions'])
            print(json.dumps(dict(suite=suite['name'], id=case['id'], audit=audit,
                                  probabilities=answer), ensure_ascii=False), flush=True)
        return
    out.mkdir(parents=True, exist_ok=True)
    raw, meta_path = out / 'raw.jsonl', out / 'metadata.json'
    if meta_path.exists():
        metadata = read(meta_path)
        assert metadata['signature'] == signature, 'Changed run signature; cannot resume'
    else:
        metadata = dict(status='RUNNING', signature=signature, expected=4905,
                        started_at=datetime.now(timezone.utc).isoformat())
        write(meta_path, metadata)
    expected = {(suite['name'], case['id'], qid): (suite, case)
                for suite, case in records for qid in case['questions']}
    saved = {}
    if raw.exists():
        for line in raw.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            key = row['suite'], row['id'], row['qid']
            assert key not in saved and key in expected
            suite, case = expected[key]
            assert row['request_sha256'] == case['request_sha256']
            assert row['gold'] == str(case['gold'][row['qid']]['label'])
            saved[key] = row
    for index, (suite, case) in enumerate(records):
        keys = [(suite['name'], case['id'], qid) for qid in case['questions']]
        if all(key in saved for key in keys):
            continue
        assert not any(key in saved for key in keys), 'Partial request record'
        assert digest(request(case)) == case['request_sha256']
        error, audits, answers, elapsed = None, {}, {}, None
        try:
            audits = adapter.audit(case['state'], case['questions'])
        except (ValueError, TypeError) as exc:
            error = 'unsupported_input:' + type(exc).__name__
        if error is None:
            adapter.synchronize()
            start = time.perf_counter()
            try:
                answers = adapter.predict(case['state'], case['questions'])
            except Exception as exc:
                error = 'inference_failure:' + type(exc).__name__
                print('ERROR', index, error, str(exc)[:160], flush=True)
            adapter.synchronize()
            elapsed = time.perf_counter() - start
        rows = []
        for qid, question in case['questions'].items():
            prediction, probabilities, status = None, None, error
            if status is None:
                try:
                    prediction, probabilities = validate_distribution(question, answers[qid])
                except (ValueError, KeyError, TypeError) as exc:
                    status = 'invalid_output:' + type(exc).__name__
            row = dict(model=args.model, suite=suite['name'], id=case['id'], qid=qid,
                       condition=case['expansion_condition'], source=suite['source'],
                       domain=suite.get('domain', case['family']), group=case['group'],
                       document_group=case.get('document_group'), family=case['family'],
                       gold=str(case['gold'][qid]['label']), labels=labels(question),
                       prediction=prediction, probabilities=probabilities, error=status,
                       request_sha256=case['request_sha256'], audit=audits.get(qid),
                       request_seconds=elapsed)
            if probabilities is not None and args.model.startswith('kev'):
                temperature = adapter.metadata['temperature']
                raw_values = [value ** temperature for value in probabilities.values()]
                row['temperature_one_probability_sensitivity'] = dict(zip(
                    probabilities, [value / sum(raw_values) for value in raw_values]))
            rows.append(row)
        with raw.open('a', encoding='utf-8') as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
                saved[(row['suite'], row['id'], row['qid'])] = row
            file.flush()
            os.fsync(file.fileno())
        if index % 25 == 0 or index + 1 == len(records):
            print('PROGRESS', args.model, index + 1, len(records), len(saved), flush=True)
    assert len(saved) == len(expected) == 4905
    metadata.update(status='DONE', count=len(saved),
                    errors=sum(row['error'] is not None for row in saved.values()),
                    finished_at=datetime.now(timezone.utc).isoformat(), raw_sha256=sha(raw))
    write(meta_path, metadata)
    print('COMPLETE', args.model, metadata['count'], metadata['errors'], flush=True)


if __name__ == '__main__':
    main()
