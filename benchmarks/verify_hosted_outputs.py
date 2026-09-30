"""CPU-only public replay against historical local input/reference fingerprints.

This checks the API evidence without downloading licensed source text. Full payload
reconstruction is a separate, stronger check performed by jev_report.py after preparation.
"""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, read, sha  # noqa: E402


def verify():
    root = ROOT/'api_results/jev-1.13.0'
    meta, contract = read(root/'metadata.json'), read(root/'contract.json')
    assert meta['status']=='DONE' and meta['signature']==contract
    # Current clients evolve; historical measurements remain bound to the
    # exact source bytes that made them, not whatever client is current today.
    candidates = [ROOT/'benchmarks/jev_api.py', root/'runner_archive/jev_api.py']
    assert any(path.is_file() and sha(path)==contract['runner_sha256'] for path in candidates)
    assert sha(root/'requests.jsonl')==meta['journal_sha256']
    records = [json.loads(line) for line in (root/'requests.jsonl').read_text().splitlines()]
    calls = {(r['suite'],r['id']):r for r in records}
    assert len(calls)==len(records)==meta['completed_requests']
    local_meta = read(ROOT/'results/english/metadata.json')
    assert set(local_meta['suites'])==set(meta['suites'])
    all_requests, failures, decisions = set(), 0, 0
    for suite in meta['suites']:
        raw_path = root/(suite+'.json.gz')
        ref_path = ROOT/'results/english'/(suite+'.json.gz')
        assert sha(raw_path)==meta['suites'][suite]['sha256']
        assert sha(ref_path)==local_meta['suites'][suite]['sha256']
        raw = json.loads(gzip.decompress(raw_path.read_bytes()))
        ref = json.loads(gzip.decompress(ref_path.read_bytes()))
        assert raw['signature']==contract
        refs = {(r['id'],r['qid']):r for r in ref['rows']}
        rows = {(r['id'],r['qid']):r for r in raw['rows']}
        assert len(rows)==len(raw['rows']) and set(rows)==set(refs)
        questions = {}
        for (cid,qid),r in rows.items():
            other = refs[cid,qid]
            for key in ['id','qid','group','family','language','request_sha256','questions_sha256','type','labels','gold']:
                assert r[key]==other[key], (suite,cid,qid,key)
            q = {'type':r['type']}
            if r['type']=='choice':
                q['criteria'] = dict.fromkeys(r['labels'],'')
            elif r['type']=='score':
                q['criteria'] = r['labels']
            questions.setdefault(cid,{})[qid] = q
            call = calls[suite,cid]
            assert call['error']==r['error'] and call['model']=='jev-1.13.0'
            if r['error'] is None:
                pred,probs = decode(q,call['response']['answers'][qid])
                assert pred==r['prediction'] and probs==r['probabilities']
                assert r['answer']==call['response']['answers'][qid]
            else:
                assert r['prediction'] is None and r['probabilities'] is None
                failures += 1
            decisions += 1
        for cid,qq in questions.items():
            all_requests.add((suite,cid))
            call = calls[suite,cid]
            if call['error'] is None:
                assert set(call['response']['answers'])==set(qq)
            elif call['error']=='ResponseValidationError':
                invalid = set(call['response']['answers'])!=set(qq)
                for qid,q in qq.items():
                    try:
                        decode(q,call['response']['answers'][qid])
                    except (ValueError,KeyError,TypeError):
                        invalid = True
                assert invalid, ('Unreproduced validation failure',suite,cid)
        assert len(rows)==meta['suites'][suite]['decisions']
    assert all_requests==set(calls)
    summary = read(root/'summary.json')
    tokens = sum((a.get('usage') or {}).get('input_tokens',0) for r in records for a in r['attempts'])
    assert tokens==meta['input_tokens']==summary['input_tokens']
    assert decisions==summary['decisions'] and failures==summary['failures']
    assert summary['metadata_sha256']==sha(root/'metadata.json')
    assert summary['contract_sha256']==sha(root/'contract.json')
    assert summary['http_status_counts']==dict(Counter(str(a['status']) for r in records for a in r['attempts']))
    print(f'Public replay verified {len(calls):,} requests, {decisions:,} decisions, {failures} invalid decisions; full payload reconstruction requires source preparation.')


if __name__=='__main__':
    verify()
