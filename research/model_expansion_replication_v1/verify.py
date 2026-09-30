"""Independent stdlib integer replay; licensed input audit only when available."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'research/model_expansion_replication_v1'
sys.path.insert(0,str(ROOT))

def read(path):
    return json.loads(path.read_text())

def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def state_key(family,state):
    return digest(dict(family=family,facts=state['facts'],parameters=state['parameters']))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--public-only',action='store_true')
    args=parser.parse_args()
    manifest=read(HERE/'manifest.json')
    assert sha(HERE/'PROTOCOL.md')==manifest['protocol_sha256']
    assert sha(HERE/'freeze.py')==manifest['preparer_sha256']
    assert sha(ROOT/'research/confirmation.py')==manifest['canonical_generator_sha256']
    expected={}
    input_path=HERE/'frozen.json'
    discovery_path=ROOT/'research/model_expansion_v1/frozen.json'
    source_audit=input_path.exists() and discovery_path.exists() and not args.public_only
    if source_audit:
        from research.confirmation import oracle,independent_oracle
        assert sha(input_path)==manifest['prepared_sha256']
        assert sha(discovery_path)==manifest['discovery_prepared_sha256']
        old={state_key(c['family'],c['state']) for s in read(discovery_path)['suites']
             if s['name'].startswith('policy_') for c in s['cases']}
        new=set()
        for suite in read(input_path)['suites']:
            groups=defaultdict(dict)
            for c in suite['cases']:
                family=c['family']
                actual={k:str(v['label']) for k,v in c['gold'].items()}
                first=oracle(family,c['state']['facts'],c['state']['parameters'])
                second=independent_oracle(family,c['state']['facts'],c['state']['parameters'])
                assert first==second and {k:str(v) for k,v in first.items()}==actual
                request_hash=digest({k:c[k] for k in ('state','questions')})
                assert request_hash==c['request_sha256']
                assert c['generator_seed'] in manifest['seeds']
                groups[c['group']][c['condition']]=c
                for qid in c['questions']:
                    expected[suite['name'],c['id'],qid]=(request_hash,actual[qid])
            assert len(groups)==96
            for cases in groups.values():
                assert set(cases)=={'original','repeat','reversed','counterfactual'}
                base,cf=cases['original'],cases['counterfactual']
                assert base['state']==cases['repeat']['state']==cases['reversed']['state']
                assert base['questions']==cases['repeat']['questions']
                assert base['gold']==cases['repeat']['gold']==cases['reversed']['gold']
                assert base['state']['parameters']==cf['state']['parameters']
                assert sum(v!=cf['state']['facts'][k] for k,v in base['state']['facts'].items())==1
                assert base['gold']['action']!=cf['gold']['action']
                for c in (base,cf):
                    key=state_key(c['family'],c['state'])
                    assert key not in old and key not in new
                    new.add(key)
        assert len(new)==576 and len(expected)==3456
    summary=read(HERE/'summary.json')
    assert summary['manifest_sha256']==sha(HERE/'manifest.json')
    assert summary['analyzer_sha256']==sha(HERE/'analyze.py')
    assert summary['supplementary_analyzer_sha256']==sha(ROOT/'research/model_expansion_v1/analyze.py')
    all_rows={}
    receipt=dict(complete_input_reconstruction=source_audit,verifier_sha256=sha(Path(__file__)),
        manifest_sha256=sha(HERE/'manifest.json'),summary_sha256=sha(HERE/'summary.json'),
        prior_state_overlap=0 if source_audit else None,
        two_gold_oracles_checked=source_audit,models={},primary_effects={})
    for name in ('kev_4b','kev_9b'):
        folder=HERE/'results'/name
        meta=read(folder/'metadata.json')
        assert meta['status']=='DONE' and meta['count']==3456 and meta['errors']==0
        assert meta['signature']['manifest_sha256']==sha(HERE/'manifest.json')
        assert meta['signature']['runner_sha256']==sha(HERE/'run.py')
        assert meta['signature']['adapter_sha256']==sha(ROOT/'system1bench/decision_models.py')
        assert meta['signature']['model']['checkpoint']['revision']==manifest['model_pins'][name]['revision']
        assert sha(folder/'raw.jsonl')==meta['raw_sha256']==summary['models'][name]['raw_sha256']
        assert summary['models'][name]['metadata_sha256']==sha(folder/'metadata.json')
        rows=[json.loads(line) for line in (folder/'raw.jsonl').read_text().splitlines()]
        keys={(r['suite'],r['id'],r['qid']) for r in rows}
        assert len(keys)==len(rows)==3456
        if expected:
            assert keys==set(expected)
        indexed={}
        requests=set()
        for row in rows:
            assert row['error'] is None and row['model']==name
            if expected:
                assert (row['request_sha256'],row['gold'])==expected[row['suite'],row['id'],row['qid']]
            p=row['probabilities']
            assert set(p)==set(row['labels']) and abs(sum(p.values())-1)<1e-9
            assert all(math.isfinite(v) and 0<=v<=1 for v in p.values())
            assert p[row['prediction']]==max(p.values())
            assert row['audit']['complete'] and row['audit']['prompt_tokens']>0
            assert len(row['audit']['token_sha256'])==64
            key=row['family'],row['group'],row['qid'],row['condition']
            assert key not in indexed
            indexed[key]=row
            requests.add((row['suite'],row['id']))
        assert len(requests)==1152
        panels={}
        for family in ('refund','access','routing'):
            for qid in ('action','review','severity'):
                bases=[r for k,r in indexed.items() if k[0]==family and k[2]==qid and k[3]=='original']
                assert len(bases)==96
                is_correct=lambda r:r['prediction']==r['gold']
                base_count=sum(is_correct(r) for r in bases)
                panel=family+'/'+qid
                target=summary['models'][name]['panels'][panel]
                assert target['base']['correct']==base_count
                cell=dict(base_correct=base_count,n=96)
                for cond,field in [('repeat','repeat'),('reversed','reverse'),('counterfactual','counterfactual')]:
                    pairs=[(b,indexed[family,b['group'],qid,cond]) for b in bases]
                    changes=sum(a['prediction']!=b['prediction'] for a,b in pairs)
                    joint=sum(is_correct(a) and is_correct(b) for a,b in pairs)
                    wrong_stable=sum(a['prediction']==b['prediction'] and not is_correct(a) and not is_correct(b) for a,b in pairs)
                    right_stable=sum(a['prediction']==b['prediction'] and is_correct(a) and is_correct(b) for a,b in pairs)
                    assert target[field]['flip']['count']==changes
                    assert target[field]['correct_stable']['count']==right_stable
                    assert target[field]['wrong_stable']['count']==wrong_stable
                    if cond=='counterfactual':
                        assert target[field]['both_reference_correct']['count']==joint
                        if qid=='action':
                            assert all(a['gold']!=b['gold'] for a,b in pairs)
                    else:
                        assert changes+wrong_stable+right_stable==96
                    if cond=='repeat':
                        assert all(a['request_sha256']==b['request_sha256'] and
                                   a['audit']['token_sha256']==b['audit']['token_sha256'] for a,b in pairs)
                    cell[cond]=dict(changes=changes,both_correct=joint,wrong_stable=wrong_stable)
                panels[panel]=cell
        receipt['models'][name]=dict(rows=3456,requests=1152,errors=0,panels=panels)
        patterns={}
        for family in ('refund','access','routing'):
            groups={k[1] for k in indexed if k[0]==family and k[3]=='original'}
            outcomes=[{q:indexed[family,g,q,'original']['prediction']==indexed[family,g,q,'original']['gold']
                       for q in ('action','review','severity')} for g in groups]
            cell=dict(n=len(groups),common_valid=len(groups),all_three_correct=sum(all(v.values()) for v in outcomes),
                severity_correct_action_wrong=sum(v['severity'] and not v['action'] for v in outcomes),
                review_and_severity_correct_action_wrong=sum(v['review'] and v['severity'] and not v['action'] for v in outcomes))
            assert all(summary['models'][name]['exploratory_cross_head'][family][k]==v for k,v in cell.items())
            patterns[family]=cell
        receipt['models'][name]['cross_head']=patterns
        all_rows[name]=indexed
        print('INDEPENDENTLY VERIFIED',name,3456,flush=True)
    left,right=all_rows['kev_4b'],all_rows['kev_9b']
    assert set(left)==set(right)
    assert all(left[k]['gold']==right[k]['gold'] and left[k]['request_sha256']==right[k]['request_sha256'] for k in left)
    for family in ('refund','access','routing'):
        keys=sorted(k for k in left if k[0]==family and k[2]=='action' and k[3]=='original')
        for endpoint in ('base_action','counterfactual_joint'):
            pairs=[]
            for k in keys:
                a,b=left[k]['prediction']==left[k]['gold'],right[k]['prediction']==right[k]['gold']
                if endpoint=='counterfactual_joint':
                    cf=(*k[:3],'counterfactual')
                    a=a and left[cf]['prediction']==left[cf]['gold']
                    b=b and right[cf]['prediction']==right[cf]['gold']
                pairs.append((a,b))
            effect=dict(n=len(pairs),left_correct=sum(a for a,b in pairs),right_correct=sum(b for a,b in pairs),
                wins=sum(b and not a for a,b in pairs),losses=sum(a and not b for a,b in pairs),ties=sum(a==b for a,b in pairs))
            key=family+'/'+endpoint
            cell=summary['primary_effects'][key]
            assert all(cell[k]==v for k,v in effect.items())
            assert abs(cell['delta']-(effect['right_correct']-effect['left_correct'])/effect['n'])<1e-12
            receipt['primary_effects'][key]=effect
    if not args.check_only:
        (HERE/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('INPUT EXCLUSION / TWO ORACLES',source_audit,flush=True)

if __name__=='__main__':
    main()
