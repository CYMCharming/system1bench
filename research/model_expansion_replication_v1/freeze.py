"""New seeded pairs, excluding all discovery original/counterfactual states."""
from copy import deepcopy
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.confirmation import RULES,OPTIONS,draw,changed_fact,questions,oracle,independent_oracle
from system1bench.common import digest,read,request,sha,write

HERE=ROOT/'research/model_expansion_replication_v1'
SEEDS=[404,505,606]
CONDITIONS=['original','repeat','reversed','counterfactual']

def main():
    discovery=read(ROOT/'research/model_expansion_v1/frozen.json')
    old= {digest(dict(family=c['family'],facts=c['state']['facts'],parameters=c['state']['parameters']))
          for s in discovery['suites'] if s['name'].startswith('policy_') for c in s['cases']}
    suites=[]
    for family in RULES:
        seen=set()
        cases=[]
        for seed in SEEDS:
            rng=random.Random(seed+sum(map(ord,family)))
            for i in range(32):
                target=list(OPTIONS[family])[i%len(OPTIONS[family])]
                for _ in range(10000):
                    facts,params=draw(family,rng)
                    cf,changed=changed_fact(family,facts,params)
                    if cf is None or oracle(family,facts,params)['action']!=target:
                        continue
                    fingerprints={digest(dict(family=family,facts=f,parameters=params)) for f in (facts,cf)}
                    if len(fingerprints)==2 and not fingerprints & (seen|old):
                        seen|=fingerprints
                        break
                else:
                    raise ValueError('No unseen decisive pair')
                assert sum(facts[k]!=cf[k] for k in facts)==1
                assert oracle(family,facts,params)['action']!=oracle(family,cf,params)['action']
                group=f'{family}:{seed}:{i:03d}'
                for condition in CONDITIONS:
                    f=deepcopy(cf if condition=='counterfactual' else facts)
                    q=questions(family)
                    if condition=='reversed':
                        q['action']['criteria']=dict(reversed(list(q['action']['criteria'].items())))
                    state=dict(policy=RULES[family]['en'],parameters=deepcopy(params),facts=f)
                    gold=oracle(family,f,params)
                    assert gold==independent_oracle(family,f,params)
                    case=dict(id=group+':'+condition,state=state,questions=q,
                        gold={k:dict(label=v) for k,v in gold.items()},group=group,family=family,language='en',
                        condition=condition,expansion_condition=condition,generator_seed=seed,changed_field=changed if condition=='counterfactual' else None)
                    case['request_sha256']=digest(request(case))
                    cases.append(case)
        assert len(seen)==192 and not seen&old
        suites.append(dict(name='policy_'+family,source='system1bench_policy_v1',reference='programmatic',domain='executable_policy',cases=cases))
    data=dict(protocol='system1bench-model-expansion-replication-v1',suites=suites,budget=dict(max_len=32768,head_max_len=32768))
    target=HERE/'frozen.json'
    if target.exists():
        assert read(target)==data
    write(target,data)
    original_manifest=read(ROOT/'research/model_expansion_v1/manifest.json')
    manifest=dict(protocol=data['protocol'],prepared_sha256=sha(target),protocol_sha256=sha(HERE/'PROTOCOL.md'),
        preparer_sha256=sha(__file__),canonical_generator_sha256=sha(ROOT/'research/confirmation.py'),
        discovery_prepared_sha256=original_manifest['prepared_sha256'],seeds=SEEDS,
        model_pins={k:original_manifest['model_pins'][k] for k in ('kev_4b','kev_9b')},
        planned_requests_per_model=1152,planned_decisions_per_model=3456,base_states_per_family=96,
        prior_state_overlap=0,selection='New fixed seeds, balanced actions; exclude discovery state/parameter matches, no new model outputs inspected')
    path=HERE/'manifest.json'
    if path.exists():
        assert read(path)==manifest
    write(path,manifest)
    print('FROZEN',3456,'decisions per model; zero original/CF state overlap',flush=True)

if __name__=='__main__':
    main()
