"""Independent stdlib recomputation of raw outputs and key integer claims."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'research/model_expansion_v1'
MODELS=['kev_08b','kev_4b','kev_9b','nanojev','qwen35_9b']

def read(path):
    return json.loads(path.read_text())

def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()

def condition(row):
    return {'original':'base','repeat':'repeat','exact_repeat':'repeat','reversed':'reverse',
            'reversed_option_order':'reverse'}.get(row['condition'],row['condition'])

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--partial',action='store_true')
    p.add_argument('--check-only',action='store_true',help='Replay public artifacts without rewriting the host input-validation receipt')
    p.add_argument('--public-only',action='store_true',help='Skip private source-text freezes, as on public CI')
    args=p.parse_args()
    manifest=read(HERE/'manifest.json')
    assert sha(HERE/'PROTOCOL.md')==manifest['protocol_sha256']
    assert sha(HERE/'freeze.py')==manifest['preparer_sha256']
    expected={}
    frozen=HERE/'frozen.json'
    if frozen.exists() and not args.public_only:
        assert sha(frozen)==manifest['prepared_sha256']
        for s in read(frozen)['suites']:
            for c in s['cases']:
                payload={k:c[k] for k in ('state','questions')}
                digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                assert digest==c['request_sha256']
                for qid in c['questions']:
                    expected[s['name'],c['id'],qid]=(digest,str(c['gold'][qid]['label']))
        assert len(expected)==4905
    summary_path=HERE/('preview.json' if args.partial else 'summary.json')
    summary=read(summary_path) if summary_path.exists() else None
    if summary:
        assert summary['manifest_sha256']==sha(HERE/'manifest.json')
        assert summary['analyzer_sha256']==sha(HERE/'analyze.py')
    result=dict(complete_input_reconstruction=bool(expected),verifier_sha256=sha(Path(__file__)),
        manifest_sha256=sha(HERE/'manifest.json'),summary_sha256=sha(summary_path) if summary else None,models={})
    all_rows={}
    for name in MODELS:
        path=HERE/'results'/name
        meta_path=path/'metadata.json'
        if not meta_path.exists() or read(meta_path)['status']!='DONE':
            if args.partial:
                continue
            raise ValueError('Incomplete '+name)
        metadata=read(meta_path)
        assert metadata['signature']['manifest_sha256']==sha(HERE/'manifest.json')
        assert metadata['signature']['runner_sha256']==sha(HERE/'run.py')
        assert metadata['signature']['adapter_sha256']==sha(ROOT/'system1bench/decision_models.py')
        assert metadata['signature']['model']['checkpoint']['revision']==manifest['model_pins'][name]['revision']
        assert sha(path/'raw.jsonl')==metadata['raw_sha256']
        if summary:
            assert summary['models'][name]['raw_sha256']==metadata['raw_sha256']
            assert summary['models'][name]['metadata_sha256']==sha(meta_path)
        rows=[json.loads(line) for line in (path/'raw.jsonl').read_text().splitlines()]
        keys={(r['suite'],r['id'],r['qid']) for r in rows}
        assert len(keys)==len(rows)==metadata['count']==4905
        if expected:
            assert keys==set(expected)
        errors=0
        panels=defaultdict(lambda:defaultdict(dict))
        requests=Counter()
        for r in rows:
            key=r['suite'],r['id'],r['qid']
            if expected:
                assert (r['request_sha256'],r['gold'])==expected[key]
            assert r['model']==name
            if r['error'] is not None:
                errors+=1
                assert r['prediction'] is None and r['probabilities'] is None
            else:
                audit=r['audit']
                assert audit['complete'] and len(audit['token_sha256'])==64
                assert audit['prompt_tokens'] > 0
                probabilities=r['probabilities']
                assert set(probabilities)==set(r['labels'])
                assert abs(sum(probabilities.values())-1)<1e-9
                assert all(math.isfinite(v) and 0<=v<=1 for v in probabilities.values())
                assert probabilities[r['prediction']]==max(probabilities.values())
            panel=r['family']+'/'+r['qid']
            # Group != pair ID on natural data. Independent implementation.
            pair_id=r['group'] if r['suite'].startswith('policy_') else r['id']
            cond=condition(r)
            assert cond not in panels[panel][pair_id]
            panels[panel][pair_id][cond]=r
            requests[(r['suite'],r['id'])]+=1
        assert len(requests)==2601 and errors==metadata['errors']
        counts={}
        for panel,cases in panels.items():
            base=[v['base'] for v in cases.values()]
            correct=sum(r['error'] is None and r['prediction']==r['gold'] for r in base)
            cell=dict(n=len(base),base_correct=correct)
            if summary:
                assert summary['models'][name]['panels'][panel]['base']['correct']==correct
            for cond in ('repeat','reverse','counterfactual'):
                pairs=[(v['base'],v[cond]) for v in cases.values() if cond in v]
                valid=[(a,b) for a,b in pairs if a['error'] is None and b['error'] is None]
                if not pairs:
                    continue
                counts_pair=dict(n=len(pairs),valid=len(valid),flips=0,correct_stable=0,wrong_stable=0,both_correct=0)
                for a,b in valid:
                    ca,cb=a['prediction']==a['gold'],b['prediction']==b['gold']
                    changed=a['prediction']!=b['prediction']
                    counts_pair['flips']+=changed
                    counts_pair['correct_stable']+=not changed and ca and cb
                    counts_pair['wrong_stable']+=not changed and not ca and not cb
                    counts_pair['both_correct']+=ca and cb
                    if cond=='repeat':
                        assert a['request_sha256']==b['request_sha256']
                        assert a['audit']['token_sha256']==b['audit']['token_sha256']
                    if cond=='counterfactual' and a['qid']=='action':
                        assert a['gold']!=b['gold']
                if cond!='counterfactual':
                    assert counts_pair['flips']+counts_pair['correct_stable']+counts_pair['wrong_stable']==len(valid)
                cell[cond]=counts_pair
                if summary:
                    calculated=summary['models'][name]['panels'][panel][cond]
                    for raw,field in [('flips','flip'),('correct_stable','correct_stable'),('wrong_stable','wrong_stable')]:
                        assert counts_pair[raw]==calculated[field]['count']
                    if cond=='counterfactual':
                        assert counts_pair['both_correct']==calculated['both_reference_correct']['count']
            counts[panel]=cell
        result['models'][name]=dict(rows=len(rows),requests=len(requests),errors=errors,panels=counts)
        cross_head={}
        for family in ('refund','access','routing'):
            groups={r['group'] for r in rows if r['family']==family and condition(r)=='base'}
            patterns=[]
            for group in groups:
                heads={r['qid']:r for r in rows if r['group']==group and condition(r)=='base'}
                assert set(heads)=={'action','review','severity'}
                if all(r['error'] is None for r in heads.values()):
                    patterns.append({q:r['prediction']==r['gold'] for q,r in heads.items()})
            cross_head[family]=dict(n=len(groups),common_valid=len(patterns),
                all_three_correct=sum(all(v.values()) for v in patterns),
                severity_correct_action_wrong=sum(v['severity'] and not v['action'] for v in patterns),
                review_and_severity_correct_action_wrong=sum(v['review'] and v['severity'] and not v['action'] for v in patterns))
            if summary:
                cell=summary['models'][name]['exploratory_cross_head'][family]
                assert all(cell[k]==v for k,v in cross_head[family].items())
        result['models'][name]['cross_head']=cross_head
        print('INDEPENDENTLY VERIFIED',name,len(rows),errors,flush=True)
        all_rows[name]=rows
    if summary and not args.partial:
        for name,comparison in summary['paired_model_comparisons'].items():
            right_name,left_name=name.split('-minus-')
            def index(items):
                return {(r['family']+'/'+r['qid'],r['group'] if r['suite'].startswith('policy_') else r['id'],condition(r)):r for r in items}
            left,right=index(all_rows[left_name]),index(all_rows[right_name])
            assert set(left)==set(right)
            assert all(left[k]['request_sha256']==right[k]['request_sha256'] and left[k]['gold']==right[k]['gold'] for k in left)
            good=lambda r:r['error'] is None and r['prediction']==r['gold']
            for panel,data in comparison.items():
                keys=[k for k in left if k[0]==panel and k[2]=='base']
                for metric,cond in [('base',None),('reversal_joint','reverse'),('counterfactual_joint','counterfactual')]:
                    if metric not in data:
                        continue
                    vals=[]
                    for k in keys:
                        a,b=good(left[k]),good(right[k])
                        if cond:
                            paired=(panel,k[1],cond)
                            a=a and good(left[paired])
                            b=b and good(right[paired])
                        vals.append(int(b)-int(a))
                    # All expansion rows are valid. Do not silently drop unavailable rows.
                    assert all(r['error'] is None for r in all_rows[left_name]+all_rows[right_name])
                    assert len(vals)==data[metric]['n']
                    assert abs(sum(vals)/len(vals)-data[metric]['delta'])<1e-12
    target=HERE/('verification_preview.json' if args.partial else 'verification.json')
    if not args.check_only:
        target.write_text(json.dumps(result,indent=2)+'\n')
    print('INPUT RECONSTRUCTION',bool(expected),'(source text is excluded from the public Git repository)',flush=True)

if __name__=='__main__':
    main()
