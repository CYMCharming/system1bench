"""Single-request native model evaluation; input-bound, resumable, no silent loss."""
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
from system1bench.decision_models import DecisionAdapter, validate_distribution

HERE = ROOT / 'research/model_expansion_replication_v1'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True, choices=['kev_4b','kev_9b'])
    p.add_argument('--audit-only', action='store_true')
    p.add_argument('--limit', type=int, default=0, help='Smoke only; cannot write production results')
    args = p.parse_args()
    manifest, frozen = read(HERE/'manifest.json'), read(HERE/'frozen.json')
    assert sha(HERE/'frozen.json') == manifest['prepared_sha256']
    assert sha(HERE/'PROTOCOL.md') == manifest['protocol_sha256']
    pin = read(ROOT/'.aris/model_expansion_paths.json')[args.model]
    assert pin['revision'] == manifest['model_pins'][args.model]['revision']
    records = [(s,c) for s in frozen['suites'] for c in s['cases']]
    if args.limit:
        records = records[:args.limit]
    adapter = DecisionAdapter(args.model, pin, load=not args.audit_only)
    signature = dict(model=adapter.metadata, manifest_sha256=sha(HERE/'manifest.json'),
        runner_sha256=sha(__file__), adapter_sha256=sha(ROOT/'system1bench/decision_models.py'))
    out = HERE/'results'/args.model
    if args.audit_only or args.limit:
        for s,c in records:
            audit = adapter.audit(c['state'], c['questions'])
            answer = None if args.audit_only else adapter.predict(c['state'], c['questions'])
            print(json.dumps(dict(suite=s['name'], id=c['id'], audit=audit, probabilities=answer),ensure_ascii=False),flush=True)
        return
    out.mkdir(parents=True,exist_ok=True)
    raw, meta_path = out/'raw.jsonl', out/'metadata.json'
    if meta_path.exists():
        metadata = read(meta_path)
        assert metadata['signature'] == signature, 'Changed run signature; cannot resume'
    else:
        metadata = dict(status='RUNNING', signature=signature, expected=3456,
                        started_at=datetime.now(timezone.utc).isoformat())
        write(meta_path,metadata)
    expected = {(s['name'],c['id'],qid):(s,c) for s,c in records for qid in c['questions']}
    saved = {}
    if raw.exists():
        for line in raw.read_text().splitlines():
            row = json.loads(line)
            key = row['suite'],row['id'],row['qid']
            assert key not in saved and key in expected
            s,c = expected[key]
            assert row['request_sha256'] == c['request_sha256']
            assert row['gold'] == str(c['gold'][row['qid']]['label'])
            saved[key] = row
    for index,(suite,case) in enumerate(records):
        keys = [(suite['name'],case['id'],q) for q in case['questions']]
        if all(key in saved for key in keys):
            continue
        assert not any(key in saved for key in keys), 'Partial request record'
        assert digest(request(case)) == case['request_sha256']
        error, audits, answers, elapsed = None, {}, {}, None
        try:
            audits = adapter.audit(case['state'],case['questions'])
        except (ValueError,TypeError) as exc:
            error = 'unsupported_input:' + type(exc).__name__
        if error is None:
            adapter.synchronize()
            before = time.perf_counter()
            try:
                answers = adapter.predict(case['state'],case['questions'])
            except Exception as exc:
                error = 'inference_failure:' + type(exc).__name__
                print('ERROR', index, error, str(exc)[:160], flush=True)
            adapter.synchronize()
            elapsed = time.perf_counter()-before
        rows = []
        for qid,q in case['questions'].items():
            prediction, probs, status = None, None, error
            if status is None:
                try:
                    prediction,probs = validate_distribution(q,answers[qid])
                except (ValueError,KeyError,TypeError) as exc:
                    status = 'invalid_output:' + type(exc).__name__
            row = dict(model=args.model,suite=suite['name'],id=case['id'],qid=qid,
                condition=case['expansion_condition'],source=suite['source'],domain=suite.get('domain',case['family']),
                group=case['group'],document_group=case.get('document_group'), family=case['family'],
                gold=str(case['gold'][qid]['label']),labels=labels(q),prediction=prediction,
                probabilities=probs,error=status,request_sha256=case['request_sha256'],
                audit=audits.get(qid),request_seconds=elapsed)
            if probs is not None and args.model.startswith('kev'):
                temp = adapter.metadata['temperature']
                values = [v**temp for v in probs.values()]
                row['temperature_one_probability_sensitivity'] = dict(zip(probs,[v/sum(values) for v in values]))
            rows.append(row)
        with raw.open('a',encoding='utf-8') as handle:
            for row in rows:
                handle.write(json.dumps(row,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
                saved[(row['suite'],row['id'],row['qid'])] = row
            handle.flush()
            os.fsync(handle.fileno())
        if index % 25 == 0 or index+1 == len(records):
            print('PROGRESS', args.model, index+1, len(records), len(saved),flush=True)
    assert len(saved) == len(expected) == 3456
    metadata.update(status='DONE', count=len(saved), errors=sum(r['error'] is not None for r in saved.values()),
        finished_at=datetime.now(timezone.utc).isoformat(),raw_sha256=sha(raw))
    write(meta_path,metadata)
    print('COMPLETE',args.model,metadata['count'],metadata['errors'],flush=True)

if __name__ == '__main__':
    main()
