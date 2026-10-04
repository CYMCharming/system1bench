"""Input-bound resumable native/hosted evaluator for main and transfer panels."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import decode,digest,labels,request,sha
from system1bench.decision_models import validate_distribution
from research.startlux_transfer_v1.adapter import get_adapter

HERE=Path(__file__).resolve().parent

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    tmp.replace(path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',required=True)
    p.add_argument('--panel',choices=['main','transfer'],default='transfer')
    p.add_argument('--audit-only',action='store_true')
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--credential',type=Path)
    a=p.parse_args(); manifest=read(HERE/'manifest.json')
    assert a.model in manifest['cohort']
    assert sha(HERE/'PROTOCOL.md')==manifest['protocol_sha256']
    for name,value in manifest['code_sha256'].items(): assert sha(HERE/name)==value
    if a.panel=='main':
        assert a.model in manifest['model_pins']
        source=ROOT/'research/model_expansion_v1/frozen.json'
        assert sha(source)==read(ROOT/'research/model_expansion_v2/manifest.json')['prepared_sha256']
        expected=4905
    else:
        source=ROOT/'data/startlux_transfer_v1/frozen.json'
        assert sha(source)==manifest['frozen_sha256']; expected=manifest['expected_decisions']
    frozen=read(source)
    records=[(s,c) for s in frozen['suites'] for c in s['cases']]
    assert sum(len(c['questions']) for s,c in records)==expected
    if a.model=='jev':
        assert a.credential and not a.audit_only
        from benchmarks.jev_api import Client,MODEL
        client=Client(a.credential,rate=8,max_usd=3,continue_invalid_decision=True)
        adapter=None
        model_meta=dict(model=MODEL,adapter='jev_official_hosted',client_payload_complete=True,
                        server_tokenization_verified=False,controlled_speed_measurement=False)
    else:
        paths=read(ROOT/'.aris/startlux_transfer_paths.json'); pin=paths[a.model]
        if a.model in manifest['model_pins']:
            assert all(pin[k]==v for k,v in manifest['model_pins'][a.model].items())
        adapter=get_adapter(a.model,pin,load=not a.audit_only); model_meta=adapter.metadata
    signature=dict(model=model_meta,manifest_sha256=sha(HERE/'manifest.json'),frozen_sha256=sha(source),
        runner_sha256=sha(__file__),adapter_sha256=sha(HERE/'adapter.py'),
        shared_adapter_sha256=sha(ROOT/'system1bench/decision_models.py'),
        expansion_adapter_sha256=sha(ROOT/'research/model_expansion_v2/adapter.py'),panel=a.panel)
    if a.limit: records=records[:a.limit]
    out=HERE/'results'/a.panel/a.model
    raw,meta_path=out/'raw.jsonl',out/'metadata.json'
    saved={}
    if not a.limit and not a.audit_only:
        if meta_path.exists():
            meta=read(meta_path); assert meta['signature']==signature,'Run signature changed'
        else:
            meta=dict(status='RUNNING',signature=signature,expected=expected,started_at=datetime.now(timezone.utc).isoformat())
            save(meta_path,meta)
        if raw.exists():
            expected_keys={(s['name'],c['id'],qid):c for s,c in records for qid in c['questions']}
            for line in raw.read_text(encoding='utf-8').splitlines():
                r=json.loads(line); key=r['suite'],r['id'],r['qid']
                assert key in expected_keys and key not in saved
                c=expected_keys[key]
                assert r['request_sha256']==c['request_sha256'] and r['gold']==str(c['gold'][r['qid']]['label'])
                saved[key]=r
    for index,(suite,case) in enumerate(records):
        keys=[(suite['name'],case['id'],qid) for qid in case['questions']]
        if all(k in saved for k in keys): continue
        assert not any(k in saved for k in keys),'Partial request record'
        assert digest(request(case))==case['request_sha256']
        error,audits,answers=None,{},{}
        if adapter:
            audits=adapter.audit(case['state'],case['questions'])
            if a.audit_only:
                if index%100==0: print('AUDIT',a.model,index,len(records),flush=True)
                continue
            adapter.synchronize()
        start=time.perf_counter(); hosted=None
        try:
            if adapter: answers=adapter.predict(case['state'],case['questions'])
            else:
                hosted=client.predict((suite['name'],case))
                if hosted is None: raise RuntimeError('API stopped or budget exhausted')
                error=hosted['error']
                if not error:
                    for qid,v in hosted['response']['answers'].items():
                        q=case['questions'][qid]; reported_probs=v['probabilities']
                        if abs(sum(reported_probs.values())-1)>len(reported_probs)*.000051:
                            raise ValueError('BeyondHostedRoundingTolerance')
                        _,norm=decode(q,v)
                        answers[qid]=dict(zip(labels(q),norm))
            if adapter: adapter.synchronize()
        except Exception as exc:
            error='inference_failure:'+type(exc).__name__
            print('ERROR',a.model,index,error,flush=True)
            if a.limit: raise
        elapsed=time.perf_counter()-start; rows=[]
        for qid,q in case['questions'].items():
            pred,prob,status=None,None,error
            if status is None:
                try: pred,prob=validate_distribution(q,answers[qid])
                except (ValueError,KeyError,TypeError) as exc: status='invalid_output:'+type(exc).__name__
            row=dict(model=a.model,suite=suite['name'],id=case['id'],qid=qid,
                condition=case['expansion_condition'],source=suite['source'],domain=suite.get('domain',case['family']),
                group=case['group'],document_group=case.get('document_group'),family=case['family'],
                gold=str(case['gold'][qid]['label']),labels=labels(q),prediction=pred,probabilities=prob,error=status,
                request_sha256=case['request_sha256'],audit=audits.get(qid),request_seconds=elapsed,
                base_id=case.get('base_id'),source_metadata=case.get('metadata'),gold_distribution=case['gold'][qid].get('distribution'))
            if hosted:
                row['hosted_evidence']={k:hosted[k] for k in ('model','payload_sha256','error','attempts','payload_complete','server_tokenization_verified')}
            rows.append(row)
        if a.limit:
            assert all(r['error'] is None for r in rows)
            print(json.dumps(rows,ensure_ascii=False),flush=True); continue
        with raw.open('a',encoding='utf-8') as stream:
            for row in rows:
                stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
                saved[(row['suite'],row['id'],row['qid'])]=row
            stream.flush(); os.fsync(stream.fileno())
        if index%25==0 or index+1==len(records): print('PROGRESS',a.panel,a.model,index+1,len(records),len(saved),flush=True)
        if adapter: getattr(adapter,'cache',{}).clear()
        if not adapter and client.stop.is_set(): raise RuntimeError('API stopped; incomplete run retained')
    if a.limit or a.audit_only: return
    assert len(saved)==expected
    meta.update(status='DONE',count=len(saved),errors=sum(r['error'] is not None for r in saved.values()),
                finished_at=datetime.now(timezone.utc).isoformat(),raw_sha256=sha(raw))
    save(meta_path,meta)
    print('COMPLETE',a.panel,a.model,expected,meta['errors'],flush=True)

if __name__=='__main__': main()
