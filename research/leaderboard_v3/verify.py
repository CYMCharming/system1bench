"""Independent replay of all displayed counts and prior-score preservation."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.leaderboard_v2 import verify as prior
from research.leaderboard_v3.build import MODELS,NEW
from research.startlux_transfer_v1.run import read,save
from system1bench.common import sha

HERE=Path(__file__).resolve().parent
EXP=ROOT/'research/startlux_transfer_v1'

def signature_receipt(meta,panel,model):
    manifest=read(EXP/'manifest.json');signature=meta['signature']
    versions={sha(p):read(p) for p in EXP.glob('manifest*.json')}
    measured=versions[signature['manifest_sha256']]
    assert measured['source_quality_sha256']==sha(EXP/'source_quality.json')
    if model in manifest['model_pins']:
        assert signature['model']['checkpoint']==manifest['model_pins'][model]
    for field,stem in [('adapter_sha256','adapter'),('runner_sha256','run')]:
        assert measured['code_sha256'][stem+'.py']==signature[field]
        assert signature[field] in {sha(p) for p in EXP.glob(stem+'*.py')}
    if panel=='transfer':
        assert measured['frozen_sha256']==signature['frozen_sha256']==manifest['frozen_sha256']
        assert measured['protocol_sha256'] in {sha(p) for p in EXP.glob('PROTOCOL*.md')}
        if model=='jev': assert measured['protocol_sha256']==manifest['protocol_sha256']
    else:
        previous=ROOT/'research/model_expansion_v1'
        assert signature['frozen_sha256']==read(previous/'manifest.json')['prepared_sha256']
        if (previous/'frozen.json').exists():assert signature['frozen_sha256']==sha(previous/'frozen.json')

def distribution_receipt(row,model):
    if row['error'] is not None:return
    p=row['probabilities']
    assert set(p)==set(row['labels']) and all(0<=v<=1 for v in p.values())
    assert abs(sum(p.values())-1)<1e-12
    assert row['prediction'] in p and abs(p[row['prediction']]-max(p.values()))<1e-12
    if model=='jev':
        evidence=row['hosted_evidence'];reported=evidence['reported_probabilities']
        assert row['prediction']==evidence['reported_choice']
        assert set(reported)==set(p) and abs(sum(reported.values())-1)<=.02
        assert max(abs(p[k]-reported[k]/sum(reported.values())) for k in p)<1e-12
    else:
        assert row['audit']['complete'] and row['audit']['prompt_tokens']<=32768

def main():
    data=read(HERE/'scores.json');old=read(ROOT/'research/leaderboard_v2/scores.json')
    summary=read(ROOT/'research/startlux_transfer_v1/summary.json')
    assert summary['complete'] and sha(ROOT/'research/startlux_transfer_v1/summary.json')==data['transfer_summary_sha256']
    source=ROOT/'research/model_expansion_v1/results/qwen35_9b/raw.jsonl'
    baseline={prior.key(r['suite'],r):r for r in map(json.loads,source.read_text(encoding='utf-8').splitlines())}
    assert len(baseline)==4905
    checked=0
    for model in MODELS:
        if model in NEW:
            source=ROOT/'research/startlux_transfer_v1/results/main'/model/'raw.jsonl'
            rows=[json.loads(x) for x in source.read_text(encoding='utf-8').splitlines()]
            meta=read(source.parent/'metadata.json')
            signature_receipt(meta,'main',model)
            assert sha(source)==meta['raw_sha256']==summary['main'][model]['receipt']['raw_sha256']
            for row in rows:distribution_receipt(row,model)
            assert len(rows)==4905 and all(r['error'] is None for r in rows)
            mapped={prior.key(r['suite'],r):r for r in rows}
            assert len(mapped)==4905
            assert set(mapped)==set(baseline)
            assert all(mapped[k]['request_sha256']==baseline[k]['request_sha256'] and mapped[k]['gold']==baseline[k]['gold'] for k in mapped)
            expected={};by=defaultdict(list)
            for (family,pair,qid,cond),r in mapped.items(): by[family,qid,cond].append(r)
            right=lambda rows:sum(r['prediction']==r['gold'] for r in rows)
            for family in ('refund','access','routing'):
                expected[family]=right(by[family,'action','base'])/96
                assert data['models'][model]['metrics'][family]['correct']==right(by[family,'action','base'])
            for metric,family,n in [('legal','contractnli',144),('science','scifact3',339)]:
                expected[metric]=right(by[family,'answer','base'])/n
            expected['policy_action']=sum(expected[f] for f in ('refund','access','routing'))/3
            for metric,qid in [('action_head','action'),('review_head','review'),('severity_head','severity')]:
                expected[metric]=sum(right(by[f,qid,'base']) for f in ('refund','access','routing'))/288
            triples,factual=[],[]
            for f in ('refund','access','routing'):
                pairs={pair for family,pair,qid,cond in mapped if family==f and cond=='base'}
                for pair in pairs:
                    triples.append(all(mapped[f,pair,q,'base']['prediction']==mapped[f,pair,q,'base']['gold'] for q in ('action','review','severity')))
                    factual.append(all(mapped[f,pair,'action',c]['prediction']==mapped[f,pair,'action',c]['gold'] for c in ('base','counterfactual')))
            expected['all_heads']=sum(triples)/288;expected['policy_counterfactual']=sum(factual)/288
            stable=[]
            for f,n in [('contractnli',144),('scifact3',339)]:
                pairs={pair for family,pair,qid,cond in mapped if family==f and cond=='base'}
                stable.append(sum(all(mapped[f,p,'answer',c]['prediction']==mapped[f,p,'answer',c]['gold'] for c in ('base','reverse')) for p in pairs)/n)
            expected['natural_reversal']=sum(stable)/2
            expected['overall_domain_equal']=(expected['policy_action']+expected['legal']+expected['science'])/3
            expected['overall_task_equal']=sum(expected[t] for t in ('refund','access','routing','legal','science'))/5
            for metric,v in expected.items(): assert abs(v-data['models'][model]['metrics'][metric]['score'])<1e-12
        else:
            for metric,c in data['models'][model]['metrics'].items():
                assert abs(c['score']-old['models'][model]['metrics'][metric]['score'])<1e-12
        checked+=4905
    # CSV must bind to every metric ranking and every 18-model row.
    csv_rows=list(csv.DictReader((HERE/'rankings.csv').open(encoding='utf-8')))
    assert len(csv_rows)==len(MODELS)*len(data['rankings'])
    for row in csv_rows:
        c=data['models'][row['model']]['metrics'][row['metric']]
        assert abs(float(row['score_pct'])/100-c['score'])<1e-12
        assert int(row['rank'])==data['rankings'][row['metric']][row['model']]
        assert int(row['rank'])==1+sum(data['models'][m]['metrics'][row['metric']]['score']>c['score']+1e-12 for m in MODELS)
        for field,key in [('correct','correct'),('n','n')]:
            assert row[field]==(str(c[key]) if key in c else '')
        for field,bound in [('ci95_low_pct',0),('ci95_high_pct',1)]:
            if 'ci95' in c:assert abs(float(row[field])/100-c['ci95'][bound])<1e-12
            else:assert row[field]==''
    # Recompute proper pilot losses directly, not by calling the analyzer.
    transfer_anchor=None
    for model in summary['cohort']:
        source=ROOT/'research/startlux_transfer_v1/results/transfer'/model/'raw.jsonl'
        prows=[json.loads(x) for x in source.read_text(encoding='utf-8').splitlines()]
        meta=read(source.parent/'metadata.json');assert meta['status']=='DONE' and len(prows)==1152
        signature_receipt(meta,'transfer',model)
        for row in prows:distribution_receipt(row,model)
        assert sha(source)==meta['raw_sha256']==summary['transfer'][model]['receipt']['raw_sha256']
        lookup={(r['suite'],r['id'],r['qid']):r for r in prows};assert len(lookup)==1152
        if transfer_anchor is None: transfer_anchor=lookup
        assert set(lookup)==set(transfer_anchor)
        assert all(lookup[k]['request_sha256']==transfer_anchor[k]['request_sha256'] and
                   lookup[k]['gold']==transfer_anchor[k]['gold'] and lookup[k]['labels']==transfer_anchor[k]['labels'] and
                   lookup[k]['gold_distribution']==transfer_anchor[k]['gold_distribution'] for k in lookup)
        assert sum(r['error'] is not None for r in prows)==meta['errors']
        for task in ('cladder','cruxeval','finentity','when2call'):
            originals=[r for r in prows if r['suite']==task and r['condition']=='original']
            num=sum(r['error'] is None and r['prediction']==r['gold'] for r in originals)
            cell=summary['transfer'][model]['metrics'][task]['original']
            assert (cell['correct'],cell['n'])==(num,len(originals)) and abs(cell['score']-num/len(originals))<1e-12
            pairs=defaultdict(dict)
            for row in prows:
                if row['suite']==task:pairs[row['base_id']][row['condition']]=row
            assert all(set(pair)=={'original','reversed'} for pair in pairs.values())
            joint=sum(all(r['error'] is None and r['prediction']==r['gold'] for r in pair.values()) for pair in pairs.values())
            cell=summary['transfer'][model]['metrics'][task]['paired_both_correct']
            assert (cell['correct'],cell['n'])==(joint,len(pairs))
        groups=defaultdict(list)
        for r in prows:
            if r['suite']=='known_distribution' and r['error'] is None:
                p,q=r['probabilities'],r['gold_distribution']
                groups['excess_brier'].append(sum(p[k]**2-2*p[k]*q[k]+q[k]**2 for k in q))
                groups['impossible_mass'].append(sum(p[k] for k in q if q[k]==0))
        for metric,values in groups.items():
            assert abs(sum(values)/len(values)-summary['transfer'][model]['metrics']['known_distribution'][metric]['score'])<1e-12
    figures=read(HERE/'figure_manifest.json')
    assert figures['scores_sha256']==sha(HERE/'scores.json')
    for outputs in figures['outputs'].values():
        for name,expected in outputs.items(): assert sha(ROOT/'paper/figures'/name)==expected
    save(HERE/'verification.json',dict(status='PASS',models=18,matched_decisions=checked,previous_scores_unchanged=14,
        new_main_counts_independently_replayed=19620,transfer_models=13,pilot_losses_independently_recomputed=True,
        csv_cells=len(csv_rows),figure_files=sum(len(x) for x in figures['outputs'].values()),verifier_sha256=sha(__file__),
        limitations='Numerical/source binding validation, not a new independent label adjudication or causal training study.'))
    print('VERIFIED',checked,'main decision bindings;',len(csv_rows),'CSV cells; all pilot losses')

if __name__=='__main__': main()
