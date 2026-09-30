"""Reuse explicitly dated historical baselines only after exact input matching."""
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import read,sha,write
from analyze import analyze

HERE=ROOT/'research/model_expansion_v1'
MODELS=['english','multilingual','llama31_8b_instruct','qwen3_8b','jev-1.13.0']

def source_file(model,suite):
    if suite.startswith('policy_'):
        area=ROOT/'research/confirmation_v1'
        folder=area/('api' if model.startswith('jev') else 'results')/model
    elif suite.startswith('contractnli_'):
        area=ROOT/'research/domain_expansion_v1/results'
        if model.startswith('jev'):
            folders=[area/'jev-1.13.0-continue-invalid',area/'jev-1.13.0']
            folder=next(path for path in folders if (path/(suite+'.json.gz')).exists())
        else:
            folder=area/'local'/model
    else:
        area=ROOT/'research/scifact3_census_v1/results'
        folder=area/model if model.startswith('jev') else area/'local'/model
    return folder/(suite+'.json.gz'),folder/'metadata.json'

def main():
    suites=read(HERE/'frozen.json')['suites']
    result=dict(scope='Historical same-payload context, reused not re-run; do not mix timing tracks',
        model_expansion_manifest_sha256=sha(HERE/'manifest.json'),reader_sha256=sha(__file__),
        analyzer_sha256=sha(HERE/'analyze.py'),models={})
    for model in MODELS:
        rows,receipts=[],[]
        for suite in suites:
            path,meta_path=source_file(model,suite['name'])
            metadata=read(meta_path)
            assert sha(path)==metadata['suites'][suite['name']]['sha256']
            saved=json.loads(gzip.decompress(path.read_bytes()))
            index={(r['id'],r['qid']):r for r in saved['rows']}
            assert len(index)==len(saved['rows'])
            matched=0
            for case in suite['cases']:
                for qid in case['questions']:
                    old=index[case['id'],qid]
                    assert old['request_sha256']==case['request_sha256']
                    assert old['gold']==str(case['gold'][qid]['label'])
                    p=old['probabilities']
                    if p is not None:
                        assert len(p)==len(old['labels'])
                        p=dict(zip(old['labels'],p))
                    rows.append(dict(model=model,suite=suite['name'],id=case['id'],qid=qid,
                        condition=case['expansion_condition'],source=suite['source'],family=case['family'],
                        group=case['group'],document_group=case.get('document_group'),labels=old['labels'],
                        gold=old['gold'],prediction=old['prediction'],probabilities=p,error=old['error'],
                        audit=old.get('audit') or {},request_sha256=old['request_sha256']))
                    matched+=1
            receipts.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),
                metadata_sha256=sha(meta_path),matched_decisions=matched,
                original_finished_at=metadata.get('finished_at'),original_run_status=metadata['status'],
                original_signature=saved['signature']))
        assert len(rows)==len({(r['suite'],r['id'],r['qid']) for r in rows})==4905
        result['models'][model]=dict(decisions=4905,errors=sum(r['error'] is not None for r in rows),
            source_receipts=receipts,panels=analyze(rows),hosted_internal_tokenization_verified=False if model.startswith('jev') else None)
        print('HISTORICAL SAME-PAYLOAD VERIFIED',model,4905,flush=True)
    write(HERE/'historical_context.json',result)

if __name__=='__main__':
    main()
