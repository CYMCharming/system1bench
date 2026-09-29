"""Held-out wording experiment for a routing conjunction; no model-made labels."""
from copy import deepcopy
from pathlib import Path
import json
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.confirmation import draw, oracle, independent_oracle, OPTIONS  # noqa: E402
from system1bench.common import digest, request, sha, write  # noqa: E402

SEEDS=(404,505,606)
CONDITIONS=('en_compact','en_explicit','zh_compact','zh_explicit')
POLICIES={
 'en_compact': 'Apply in order: outage and paying -> urgent_support; otherwise category=billing -> billing; otherwise category=technical -> technical; otherwise -> general.',
 'en_explicit': 'Apply in order: only if outage is true AND paying is true -> urgent_support; otherwise category=billing -> billing; otherwise category=technical -> technical; otherwise -> general.',
 'zh_compact': '按顺序执行：outage 且 paying -> urgent_support；否则 category=billing -> billing；否则 category=technical -> technical；否则 -> general。',
 'zh_explicit': '按顺序执行：只有 outage 与 paying 均为 true 时 -> urgent_support；否则 category=billing -> billing；否则 category=technical -> technical；否则 -> general。',
}


def build(existing):
    previous={digest({'facts':c['state']['facts'],'parameters':c['state']['parameters']})
              for suite in existing['suites'] for c in suite['cases'] if c['condition']=='original'}
    cases=[];seen=set(previous)
    for seed in SEEDS:
        rng=random.Random(seed+1000003)
        for cell in [(False,False),(False,True),(True,False),(True,True)]:
            for index in range(8):
                for _ in range(10000):
                    facts,params=draw('routing',rng)
                    facts['outage'],facts['paying']=cell
                    key=digest({'facts':facts,'parameters':params})
                    if key not in seen:
                        seen.add(key);break
                else:raise ValueError('Could not sample unique held-out state')
                truth=oracle('routing',facts,params)
                assert truth==independent_oracle('routing',facts,params)
                group=f'routing-wording:{seed}:{int(cell[0])}{int(cell[1])}:{index:02d}'
                for condition in CONDITIONS:
                    state={'policy':POLICIES[condition],'parameters':deepcopy(params),'facts':deepcopy(facts)}
                    questions={'action':{'type':'choice',
                        'instructions':'Using state.policy, state.parameters and state.facts, which action is required?',
                        'criteria':deepcopy(OPTIONS['routing'])}}
                    case={'id':group+':'+condition,'group':group,'family':'routing_wording',
                          'condition':condition,'language':'zh' if condition.startswith('zh') else 'en',
                          'generator_seed':seed,'boolean_cell':''.join(str(int(x)) for x in cell),
                          'state':state,'questions':questions,'gold':{'action':{'label':truth['action']}}}
                    case['request_sha256']=digest(request(case));cases.append(case)
    frozen={'protocol':'system1bench-routing-wording-v1',
            'budget':{'max_len':8192,'head_max_len':4096},'generator_seeds':list(SEEDS),
            'conditions':list(CONDITIONS),
            'suites':[{'name':'routing_wording','track':'heldout_wording_diagnostic',
                       'reference':'programmatic','source':'system1bench_policy_v1','cases':cases}]}
    assert len(cases)==384 and len({c['group'] for c in cases})==96
    for group in {c['group'] for c in cases}:
        variants=[c for c in cases if c['group']==group]
        assert len(variants)==4 and len({c['gold']['action']['label'] for c in variants})==1
        assert all(c['state']['facts']==variants[0]['state']['facts'] for c in variants)
    return frozen


if __name__=='__main__':
    out=ROOT/'research/wording_v1';out.mkdir(parents=True,exist_ok=True)
    frozen=build(json.loads((ROOT/'research/confirmation_v1/frozen.json').read_text()))
    path=out/'frozen.json'
    if path.exists() and json.loads(path.read_text())!=frozen:raise ValueError('Frozen input changed')
    write(path,frozen)
    write(out/'manifest.json',{'protocol':frozen['protocol'],'generator_sha256':sha(__file__),
        'frozen_sha256':sha(path),'requests_per_model':384,'decisions_per_model':384,
        'base_clusters':96,'seeds':list(SEEDS),'cells_per_seed':{'00':8,'01':8,'10':8,'11':8},
        'primary_estimand':'EN explicit minus EN compact accuracy on XOR boolean cells',
        'secondary_estimands':['EN overall accuracy difference','ZH explicit minus ZH compact on XOR cells',
                                'difference of EN/ZH wording effects on XOR cells'],
        'uncertainty':'paired cluster bootstrap, stratified by generator seed and boolean cell, 10000 draws, seed 20260929'})
    print('Frozen 96 new states, four crossed conditions, 384 action requests per system')
