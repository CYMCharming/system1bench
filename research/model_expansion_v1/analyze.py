"""Per-source, paired, cluster-aware analysis; no blended intelligence score."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import read, sha, write

HERE = ROOT/'research/model_expansion_v1'
MODELS = ['kev_08b','kev_4b','kev_9b','nanojev','qwen35_9b']
NAMES = dict(kev_08b='Kev-0.8B',kev_4b='Kev-4B',kev_9b='Kev-9B',nanojev='NanoJev (unified games)',qwen35_9b='Qwen3.5-9B (direct)')
BOOTSTRAPS, SEED = 5000, 20261001

def cluster_interval(values, groups):
    if not values:
        return None
    buckets = defaultdict(list)
    for value, group in zip(values,groups):
        buckets[group].append(value)
    data = np.array([[sum(v),len(v)] for v in buckets.values()],dtype=float)
    rng = np.random.default_rng(SEED)
    chosen = rng.integers(0,len(data),(BOOTSTRAPS,len(data)))
    totals = data[chosen].sum(axis=1)
    ratios = totals[:,0]/totals[:,1]
    return [float(v) for v in np.quantile(ratios,[.025,.975])]

def cluster(row, document=False):
    return (row.get('document_group') if document else None) or row['group']

def norm_condition(row):
    return {'original':'base','repeat':'repeat','exact_repeat':'repeat','reversed':'reverse',
            'reversed_option_order':'reverse'}.get(row['condition'],row['condition'])

def case_key(row):
    # Legal document groups can contain TWO distinct hypotheses. They are a
    # bootstrap cluster, never a pairing key. Scientific claims can cite >1 doc.
    return row['group'] if row['suite'].startswith('policy_') else row['id']

def correct(row):
    return row['error'] is None and row['prediction'] == row['gold']

def base_metrics(rows):
    valid = [r for r in rows if r['error'] is None]
    confusion = Counter((r['gold'],r['prediction']) for r in valid)
    classes = sorted({r['gold'] for r in rows})
    recalls, f1 = {}, []
    for label in classes:
        count = sum(r['gold']==label for r in rows)
        tp = confusion[label,label]
        fp = sum(v for (a,b),v in confusion.items() if b==label and a!=label)
        fn = count-tp
        recalls[label] = dict(n=count,correct=tp,recall=tp/count)
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    brier, nll, calibration = [], [], []
    for r in valid:
        p = r['probabilities']
        brier.append(sum((v-int(k==r['gold']))**2 for k,v in p.items()))
        nll.append(-math.log(max(p[r['gold']],1e-15)))
        calibration.append((max(p.values()),correct(r)))
    ece = 0.0
    for i in range(10):
        members = [(p,c) for p,c in calibration if i/10 <= p < (i+1)/10 or i==9 and p==1]
        if members:
            ece += len(members)/len(valid)*abs(sum(p for p,_ in members)/len(members)-sum(c for _,c in members)/len(members))
    high = [r for r in valid if max(r['probabilities'].values()) >= .9]
    errors = sum(not correct(r) for r in high)
    ranked = sorted(valid,key=lambda r:(-max(r['probabilities'].values()),case_key(r)))
    curve = []
    for coverage in (.1,.2,.3,.4,.5,.6,.7,.8,.9,1.0):
        k = max(1,math.ceil(len(ranked)*coverage)) if ranked else 0
        head = ranked[:k]
        curve.append(dict(coverage=k/len(rows),risk=sum(not correct(r) for r in head)/k if k else None,n=k))
    within = [r for r in rows if (r.get('audit') or {}).get('training_length_exceeded') is False]
    return dict(n=len(rows),valid=len(valid),unavailable=len(rows)-len(valid),correct=sum(map(correct,rows)),
        accuracy=sum(map(correct,rows))/len(rows),accuracy_ci=cluster_interval([int(correct(r)) for r in rows],[cluster(r) for r in rows]),
        macro_f1=sum(f1)/len(f1),classes=recalls,
        confusion={label:{prediction:confusion[label,prediction] for prediction in classes} for label in classes},
        brier=sum(brier)/len(valid) if valid else None,nll=sum(nll)/len(valid) if valid else None,ece_10_bins=ece if valid else None,
        confidence90=dict(n=len(high),coverage=len(high)/len(rows),errors=errors,
            error_fraction_all=errors/len(rows),risk=errors/len(high) if high else None),
        risk_coverage_descriptive=curve,training_window_slice=dict(n=len(within),correct=sum(map(correct,within))) if within else None)

def paired_metrics(rows, condition):
    lookup = defaultdict(dict)
    for r in rows:
        lookup[case_key(r)][norm_condition(r)] = r
    pairs = [(v['base'],v[condition]) for v in lookup.values() if 'base' in v and condition in v]
    valid = [(a,b) for a,b in pairs if a['error'] is None and b['error'] is None]
    if not pairs:
        return None
    values = dict(flip=[],correct_stable=[],wrong_stable=[],correction=[],regression=[],delta=[])
    for a,b in valid:
        flip = a['prediction'] != b['prediction']
        ca,cb = correct(a),correct(b)
        values['flip'].append(int(flip))
        values['correct_stable'].append(int(not flip and ca and cb))
        values['wrong_stable'].append(int(not flip and not ca and not cb))
        values['correction'].append(int(not ca and cb))
        values['regression'].append(int(ca and not cb))
        values['delta'].append(int(cb)-int(ca))
    groups = [cluster(a) for a,_ in valid]
    result = dict(n=len(pairs),common_valid=len(valid),unavailable_pairs=len(pairs)-len(valid),
        base_correct=sum(correct(a) for a,_ in pairs),perturbed_correct=sum(correct(b) for _,b in pairs))
    for name,vals in values.items():
        result[name] = dict(count=sum(vals),rate=sum(vals)/len(vals) if vals else None,ci=cluster_interval(vals,groups))
    if condition != 'counterfactual' and valid:
        assert sum(result[k]['count'] for k in ('flip','correct_stable','wrong_stable')) == len(valid)
    result['class_delta'] = {}
    for label in sorted({a['gold'] for a,_ in pairs}):
        subset = [(a,b) for a,b in valid if a['gold']==label]
        vals = [int(correct(b))-int(correct(a)) for a,b in subset]
        result['class_delta'][label] = dict(n=len(subset),base_correct=sum(correct(a) for a,_ in subset),
            perturbed_correct=sum(correct(b) for _,b in subset),delta=sum(vals)/len(vals) if vals else None,
            ci=cluster_interval(vals,[cluster(a) for a,_ in subset]))
    if valid and valid[0][0].get('document_group'):
        result['document_cluster_sensitivity'] = {
            k:cluster_interval(v,[cluster(a,True) for a,_ in valid]) for k,v in values.items()}
    if condition == 'counterfactual':
        action = valid[0][0]['qid']=='action' if valid else False
        if action:
            assert all(a['gold']!=b['gold'] for a,b in pairs)
        joint = [int(correct(a) and correct(b)) for a,b in valid]
        result['both_reference_correct'] = dict(count=sum(joint),rate=sum(joint)/len(joint) if joint else None,ci=cluster_interval(joint,groups))
        result['gold_changed_pairs'] = sum(a['gold']!=b['gold'] for a,b in pairs)
    return result

def analyze(rows):
    panel_rows = defaultdict(list)
    for row in rows:
        panel_rows[row['family']+'/'+row['qid']].append(row)
    panels = {}
    for panel, group in sorted(panel_rows.items()):
        base = [r for r in group if norm_condition(r)=='base']
        panels[panel] = dict(base=base_metrics(base),
            repeat=paired_metrics(group,'repeat'),reverse=paired_metrics(group,'reverse'),
            counterfactual=paired_metrics(group,'counterfactual'))
    return panels

def compare_models(all_rows, left, right):
    """Right minus left on EXACT same request hashes, never unpaired totals."""
    def index(rows):
        return {(r['family']+'/'+r['qid'],case_key(r),norm_condition(r)):r for r in rows}
    a,b = index(all_rows[left]),index(all_rows[right])
    assert set(a)==set(b)
    for key in a:
        assert a[key]['request_sha256']==b[key]['request_sha256'] and a[key]['gold']==b[key]['gold']
    result = {}
    for panel in sorted({k[0] for k in a}):
        keys = [k for k in a if k[0]==panel and k[2]=='base']
        pairs = [(a[k],b[k]) for k in keys if a[k]['error'] is None and b[k]['error'] is None]
        vals = [int(correct(y))-int(correct(x)) for x,y in pairs]
        base = dict(n=len(keys),common_valid=len(pairs),left_correct=sum(correct(x) for x,y in pairs),
            right_correct=sum(correct(y) for x,y in pairs),delta=sum(vals)/len(vals) if vals else None,
            ci=cluster_interval(vals,[cluster(x) for x,y in pairs]))
        if pairs and pairs[0][0].get('document_group'):
            base['document_cluster_ci']=cluster_interval(vals,[cluster(x,True) for x,y in pairs])
        result[panel] = dict(base=base)
        reverse_keys=[(panel,k[1],'reverse') for k in keys]
        if all(k in a and k in b for k in reverse_keys):
            left_joint=[int(correct(a[k]) and correct(a[rev])) for k,rev in zip(keys,reverse_keys)]
            right_joint=[int(correct(b[k]) and correct(b[rev])) for k,rev in zip(keys,reverse_keys)]
            vals=[y-x for x,y in zip(left_joint,right_joint)]
            result[panel]['reversal_joint']=dict(n=len(vals),left_correct=sum(left_joint),
                right_correct=sum(right_joint),delta=sum(vals)/len(vals),
                ci=cluster_interval(vals,[cluster(a[k]) for k in keys]))
        if panel.endswith('/action'):
            cfkeys = [(panel,k[1],'counterfactual') for k in keys]
            if all(k in a and k in b for k in cfkeys):
                vals = [int(correct(b[k]) and correct(b[cf]))-int(correct(a[k]) and correct(a[cf])) for k,cf in zip(keys,cfkeys)]
                result[panel]['counterfactual_joint'] = dict(n=len(vals),delta=sum(vals)/len(vals),
                    ci=cluster_interval(vals,[cluster(a[k]) for k in keys]))
    return result

def cross_head_patterns(rows):
    """Exploratory observable correctness patterns, NOT internal belief claims."""
    out={}
    for family in ('refund','access','routing'):
        cases=defaultdict(dict)
        for row in rows:
            if row['family']==family and norm_condition(row)=='base':
                cases[case_key(row)][row['qid']]=row
        if not cases:
            continue
        assert all(set(v)=={'action','review','severity'} for v in cases.values())
        valid=[v for v in cases.values() if all(r['error'] is None for r in v.values())]
        out[family]=dict(n=len(cases),common_valid=len(valid),
            all_three_correct=sum(all(correct(r) for r in v.values()) for v in valid),
            severity_correct_action_wrong=sum(correct(v['severity']) and not correct(v['action']) for v in valid),
            review_and_severity_correct_action_wrong=sum(correct(v['review']) and correct(v['severity']) and not correct(v['action']) for v in valid),
            interpretation='Exploratory head-specific label agreement only; cannot identify knowledge, intention or causal reasoning')
    return out

def report(summary):
    text = ['# Five-model expansion: measured results','',
        'Five new, pinned official checkpoints; 4,905 decisions each (24,525 total). Three reference tracks remain separate.',
        'These results describe direct/native decision inference, not a reasoning ceiling or a causal architecture comparison.',
        'NanoJev is the unified-games checkpoint; Kev sizes have different training histories. All intervals are pointwise paired/clustered descriptive 95% intervals.','',
        '## Base source/reference accuracy','',
        '| Model | Refund action (96) | Access action (96) | Routing action (96) | Legal (144) | Science (339) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    focus = ['refund/action','access/action','routing/action','contractnli/answer','scifact3/answer']
    for model in MODELS:
        panels = summary['models'][model]['panels']
        text.append('| '+NAMES[model]+' | '+' | '.join(f"{panels[key]['base']['accuracy']:.1%}" for key in focus)+' |')
    text += ['', 'Policy action correctness is executable; legal is source annotation agreement; scientific NOINFO is absence of annotated evidence in the cited abstract, not independently adjudicated neutrality.',
        'No aggregate average across these columns is calculated. Full head-specific scores, class confusions, CI, calibration and risk/coverage are in `summary.json`.','',
        '## Stability decomposed: science reversal','',
        '| Model | Semantic flips | Correct and stable | Wrong and stable | Exact-repeat flips |',
        '|---|---:|---:|---:|---:|']
    for model in MODELS:
        p = summary['models'][model]['panels']['scifact3/answer']
        r = p['reverse']
        text.append('| '+NAMES[model]+' | '+' | '.join(f"{r[key]['count']}/{r['common_valid']} ({r[key]['rate']:.1%})" for key in ('flip','correct_stable','wrong_stable'))+f" | {p['repeat']['flip']['count']}/{p['repeat']['common_valid']} |")
    text += ['', 'Correct-stable + wrong-stable + changed = all common-valid cases. Stability alone is not semantic correctness.',
        '', '## Counterfactual action adaptation','',
        '| Model | Refund: both correct / changed | Access: both correct / changed | Routing: both correct / changed |',
        '|---|---:|---:|---:|']
    for model in MODELS:
        cells = []
        for family in ('refund','access','routing'):
            p = summary['models'][model]['panels'][family+'/action']['counterfactual']
            cells.append(f"{p['both_reference_correct']['rate']:.1%} / {p['flip']['rate']:.1%}")
        text.append('| '+NAMES[model]+' | '+' | '.join(cells)+' |')
    text += ['', 'The executable correct action changes in all 96 pairs per policy. A model changing its answer is necessary but not sufficient; both answers must be correct.','',
        '## Fixed confidence threshold (p_max ≥ 0.9)','',
        '| Model | Legal coverage / observed risk | Science coverage / observed risk |',
        '|---|---:|---:|']
    for model in MODELS:
        cells = []
        for key in ('contractnli/answer','scifact3/answer'):
            c = summary['models'][model]['panels'][key]['base']['confidence90']
            cells.append(f"{c['coverage']:.1%} / "+(f"{c['risk']:.1%} ({c['errors']}/{c['n']})" if c['risk'] is not None else 'N/A (0 selected)'))
        text.append('| '+NAMES[model]+' | '+' | '.join(cells)+' |')
    text += ['', 'This is observed test risk, NOT a prospective safety guarantee. Qwen probabilities are conditional code likelihoods; Kev applies stored calibration temperatures; NanoJev uses temperature 1. No test-fitted calibration is used.','',
        '## Boundaries and reproduction','',
        '- All unavailable/error decisions are separate statuses. Paired semantic rates use common-valid pairs; strict accuracy uses all source cases.',
        '- Native rendering and next-token prompts preserve the same supplied information but are not identical token sequences.',
        '- Size comparisons are confounded by training; class-level and source-level reversals do not identify a mechanism.',
        '- These sources were already used in earlier research; this is new-model transfer replication, not fresh held-out data.',
        '- Full-input NanoJev overrides its default context ceiling; the actual training-window slice is recorded. No silent truncation.',
        '- Timing is telemetry, not a controlled speedup benchmark.',
        '- Reconstruct original freezes using their source-pinned preparation scripts and licenses, then run `freeze.py`, `run.py --model NAME`, `analyze.py`, `verify.py`.',
        '', 'The complete prospective protocol is `PROTOCOL.md`; input/model identities are in `manifest.json`; raw outputs and environment/weight/code hashes are under `results/`.']
    return '\n'.join(text)+'\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--partial',action='store_true')
    args = parser.parse_args()
    result = dict(protocol='system1bench-model-expansion-v1',manifest_sha256=sha(HERE/'manifest.json'),
        analyzer_sha256=sha(__file__),bootstrap=dict(resamples=BOOTSTRAPS,seed=SEED,unit='policy base state / legal document / science claim'),models={})
    all_rows = {}
    for model in MODELS:
        meta = HERE/'results'/model/'metadata.json'
        if not meta.exists() or read(meta)['status']!='DONE':
            if args.partial:
                continue
            raise ValueError('Not complete: '+model)
        metadata = read(meta)
        path = meta.parent/'raw.jsonl'
        assert sha(path)==metadata['raw_sha256']
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows)==len({(r['suite'],r['id'],r['qid']) for r in rows})==4905
        result['models'][model] = dict(count=len(rows),errors=sum(r['error'] is not None for r in rows),
            raw_sha256=sha(path),metadata_sha256=sha(meta),panels=analyze(rows),
            exploratory_cross_head=cross_head_patterns(rows))
        print('ANALYZED',model,flush=True)
        all_rows[model]=rows
    result['paired_model_comparisons'] = {}
    for left,right in [('kev_08b','kev_4b'),('kev_4b','kev_9b'),('kev_9b','qwen35_9b'),('kev_4b','qwen35_9b')]:
        if left in all_rows and right in all_rows:
            result['paired_model_comparisons'][right+'-minus-'+left] = compare_models(all_rows,left,right)
    target = HERE/('preview.json' if args.partial else 'summary.json')
    write(target,result)
    if not args.partial:
        (HERE/'RESULTS.en.md').write_text(report(result))
    for model, data in result['models'].items():
        print(model,{key:round(v['base']['accuracy'],4) for key,v in data['panels'].items()},flush=True)

if __name__=='__main__':
    main()
