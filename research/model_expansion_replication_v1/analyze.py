"""All six registered effects, including null/contrary replication outcomes."""
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import read,sha,write
from research.model_expansion_v1.analyze import analyze,correct,cross_head_patterns,norm_condition

HERE=ROOT/'research/model_expansion_replication_v1'
MODELS=['kev_4b','kev_9b']
FAMILIES=['refund','access','routing']
RESAMPLES,SEED=20000,20261001

def effect(pairs):
    left=np.array([int(a) for a,b in pairs])
    right=np.array([int(b) for a,b in pairs])
    delta=right-left
    rng=np.random.default_rng(SEED)
    means=delta[rng.integers(0,len(delta),(RESAMPLES,len(delta)))].mean(axis=1)
    alpha=.05/6
    return dict(n=len(delta),left_correct=int(left.sum()),right_correct=int(right.sum()),
        wins=int((delta==1).sum()),losses=int((delta==-1).sum()),ties=int((delta==0).sum()),
        delta=float(delta.mean()),ci95=np.quantile(means,[.025,.975]).tolist(),
        ci_family_guard=np.quantile(means,[alpha/2,1-alpha/2]).tolist())

def report(s):
    lines=['# Prospective new-seed policy replication','',
        'Designed after the expansion discovery, before new inference. Kev-4B and Kev-9B each made 3,456 new decisions, with zero overlap of original/counterfactual fact–parameter states with discovery. Same rule grammar, official pins and inference settings; different training histories remain a confound.',
        '', '## All six primary effects: Kev-9B minus Kev-4B','',
        '| Family | Endpoint | 4B correct | 9B correct | Paired difference (pp) | Pointwise 95% CI | Six-effect 99.1667% CI |',
        '|---|---|---:|---:|---:|---|---|']
    for key,e in s['primary_effects'].items():
        family,endpoint=key.split('/')
        ci=lambda x:f'[{100*x[0]:+.1f}, {100*x[1]:+.1f}]'
        lines.append(f"| {family} | {endpoint} | {e['left_correct']}/{e['n']} | {e['right_correct']}/{e['n']} | {100*e['delta']:+.1f} | {ci(e['ci95'])} | {ci(e['ci_family_guard'])} |")
    lines+=['',
        'Paired state-cluster bootstrap: 20,000 draws, seed 20261001. For joint success, BOTH the original and the one-fact-changed action must be correct. All pairs have an executable correct-action change.',
        'The simultaneous guard uses nominal 1 − 0.05/6 percentile intervals (Bonferroni); bootstrap approximation is not an exact familywise coverage guarantee. No architecture/size law follows from these checkpoint comparisons.',
        '', 'Supplementary repeated/reversed inputs, all three primitive heads, confidence and exploratory cross-head label patterns are retained in `summary.json`. Integer numerators, input hashes, state exclusion and two programmatic gold oracles are independently checked by `verify.py`. Public replay excludes licensed natural-language source text; complete host validation is recorded in `verification.json`.']
    return '\n'.join(lines)+'\n'

def main():
    all_rows={}
    result=dict(protocol='system1bench-model-expansion-replication-v1',manifest_sha256=sha(HERE/'manifest.json'),
        analyzer_sha256=sha(__file__),supplementary_analyzer_sha256=sha(ROOT/'research/model_expansion_v1/analyze.py'),
        bootstrap=dict(resamples=RESAMPLES,seed=SEED,unit='paired policy base state',primary_effects=6,
                       family_guard_nominal_confidence=1-.05/6),models={},primary_effects={})
    for model in MODELS:
        meta=read(HERE/'results'/model/'metadata.json')
        path=HERE/'results'/model/'raw.jsonl'
        assert meta['status']=='DONE' and sha(path)==meta['raw_sha256']
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows)==len({(r['suite'],r['id'],r['qid']) for r in rows})==3456
        assert Counter(r['error'] for r in rows)=={None:3456}
        all_rows[model]={(r['family'],r['group'],r['qid'],norm_condition(r)):r for r in rows}
        result['models'][model]=dict(count=len(rows),errors=0,raw_sha256=sha(path),
            metadata_sha256=sha(HERE/'results'/model/'metadata.json'),panels=analyze(rows),
            exploratory_cross_head=cross_head_patterns(rows))
    left,right=[all_rows[k] for k in MODELS]
    assert set(left)==set(right)
    assert all(left[k]['request_sha256']==right[k]['request_sha256'] and left[k]['gold']==right[k]['gold'] for k in left)
    for family in FAMILIES:
        keys=sorted(k for k in left if k[0]==family and k[2]=='action' and k[3]=='base')
        assert len(keys)==96
        result['primary_effects'][family+'/base_action']=effect([(correct(left[k]),correct(right[k])) for k in keys])
        pairs=[]
        for k in keys:
            cf=(*k[:3],'counterfactual')
            assert left[k]['gold']!=left[cf]['gold']
            pairs.append((correct(left[k]) and correct(left[cf]),correct(right[k]) and correct(right[cf])))
        result['primary_effects'][family+'/counterfactual_joint']=effect(pairs)
    write(HERE/'summary.json',result)
    (HERE/'RESULTS.en.md').write_text(report(result),encoding='utf-8')
    print(json.dumps(result['primary_effects'],indent=2),flush=True)

if __name__=='__main__':
    main()
