"""Exploratory paired diagnostics from immutable public predictions; no new inference."""
from collections import defaultdict
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402

MODELS = ['english', 'multilingual', 'llama31_8b_instruct', 'qwen3_8b']
NAMES = {'english': 'Laya EN', 'multilingual': 'Laya Multi', 'llama31_8b_instruct': 'Llama 3.1 8B', 'qwen3_8b': 'Qwen3 8B', 'jev-1.13.0': 'Jev 1.13'}
SEED = 20260929
TAXONOMY = {
    'semantic_classification': ['ag_news', 'emotion', 'banking77', 'massive_en', 'massive_zh'],
    'contextual_judgment': ['boolq', 'boolq_choice', 'xnli_en', 'xnli_zh', 'turtlebench'],
    'ordinal_judgment': ['sst5', 'sst5_choice'],
    'policy_screening': ['prompt_injections', 'aegis2_prompt'],
    'workflow_routing': ['typed_decisions', 'jevbench_original', 'jevbench_easy', 'jevbench_hard', 'reflexbench_reflex-public-choice-v1', 'jev_laya_triage', 'jev_laya_moderation', 'jev_laya_routing', 'jev_laya_claims', 'jev_laya_reviews', 'jev_laya_guard', 'jev_laya_multilingual'],
    'explicit_rejection': ['clinc150_oos'],
    'controlled_retrieval': ['jev_laya_needle'],
}


def correct(r):
    return int(r['error'] is None and r['prediction'] == r['gold'])


def cluster_estimate(values, groups, draws=10000):
    sums = defaultdict(lambda: [0., 0])
    for v, g in zip(values, groups):
        sums[str(g)][0] += float(v); sums[str(g)][1] += 1
    a = np.array(list(sums.values()))
    rng = np.random.default_rng(SEED)
    boots = []
    for begin in range(0, draws, 100):
        ix = rng.integers(0, len(a), (min(100, draws - begin), len(a)))
        z = a[ix].sum(axis=1); boots.extend(z[:, 0] / z[:, 1])
    return dict(estimate=float(np.mean(values)), ci95=np.quantile(boots, [.025, .975]).tolist(),
                n=len(values), clusters=len(a))


def load_rows(model, suite):
    root = ROOT / ('api_results' if model.startswith('jev-') else 'results') / model
    meta = read(root / 'metadata.json')
    if meta['status'] != 'DONE':
        raise ValueError('Incomplete model')
    p = root / (suite + '.json.gz')
    if sha(p) != meta['suites'][suite]['sha256']:
        raise ValueError('Raw file differs from metadata')
    return json.loads(gzip.decompress(p.read_bytes()))['rows']


def pair(rows_a, rows_b, language=False, mapping=None):
    def key(r):
        return (r['id'].split(':')[-1] if language else r['id'], r['qid'])
    a = {key(r): r for r in rows_a}; b = {key(r): r for r in rows_b}
    if a.keys() != b.keys():
        raise ValueError('Unmatched paired cases')
    keys = sorted(a)
    if any((mapping or {}).get(a[k]['gold'], a[k]['gold']) != b[k]['gold'] for k in keys):
        raise ValueError('Paired reference changed')
    return [a[k] for k in keys], [b[k] for k in keys]


def paired(a, b, language=False, mapping=None, include_pairs=False):
    a, b = pair(a, b, language, mapping)
    d = [correct(y) - correct(x) for x, y in zip(a, b)]
    groups = [x['group'] for x in a]
    result = cluster_estimate(d, groups)
    result.update(a_accuracy=float(np.mean([correct(r) for r in a])), b_accuracy=float(np.mean([correct(r) for r in b])),
                  a_only_correct=sum(correct(x) and not correct(y) for x, y in zip(a, b)),
                  b_only_correct=sum(correct(y) and not correct(x) for x, y in zip(a, b)),
                  disagreement=cluster_estimate([(mapping or {}).get(x['prediction'], x['prediction']) != y['prediction'] for x, y in zip(a, b)], groups))
    if include_pairs:
        result['pairs'] = [dict(a_id=x['id'], b_id=y['id'], qid=x['qid'], group=x['group'], included=True,
                               a_correct=correct(x), b_correct=correct(y),
                               flip=(mapping or {}).get(x['prediction'],x['prediction'])!=y['prediction']) for x,y in zip(a,b)]
    return result


def risk_curve(rows):
    valid = [r for r in rows if r['error'] is None]
    groups = defaultdict(lambda: [0, 0])
    for r in valid:
        confidence = max(r['probabilities'])
        groups[confidence][0] += 1; groups[confidence][1] += 1 - correct(r)
    n, errors, curve = 0, 0, []
    for threshold in sorted(groups, reverse=True):
        count, err = groups[threshold]; n += count; errors += err
        curve.append(dict(threshold=threshold, coverage=n / len(rows), risk=errors / n, accepted=n, errors=errors))
    landmarks=[]
    for desired in [.25,.5,.75,1.]:
        point=next((p for p in curve if p['coverage']>=desired),curve[-1])
        accepted=[r for r in valid if max(r['probabilities'])>=point['threshold']]
        landmarks.append(dict(target_coverage=desired,coverage=point['coverage'],threshold=point['threshold'],
                              **cluster_estimate([1-correct(r) for r in accepted],[r['group'] for r in accepted])))
    return dict(n=len(rows), failures=len(rows) - len(valid), curve=curve, landmarks=landmarks,
                interval_scope='conditional on the displayed data-selected threshold; not a threshold-selection guarantee',
                confidence='maximum class probability, not vendor confidence', tie_policy='include every item tied at threshold')


def main():
    manifest = read(ROOT / 'protocol_manifest.json')
    models = list(MODELS)
    jev = ROOT / 'api_results/jev-1.13.0/metadata.json'
    if jev.exists() and read(jev)['status'] == 'DONE':
        models.append('jev-1.13.0')
    out = dict(analysis='system1bench-exploratory-v1', seed=SEED, bootstrap_draws=10000,
               intervals='pointwise 95% percentile paired cluster bootstrap; descriptive, no confirmatory significance claims',
               models=models, model_names=NAMES, taxonomy=TAXONOMY, scores=[], paired=[], order=[], needle=[], needle_by_question=[], risk=[],
               input_hashes={'protocol_manifest.json': sha(ROOT / 'protocol_manifest.json')})
    all_rows = {}
    for model in models:
        data = {s['name']: load_rows(model, s['name']) for s in manifest['suites']}
        all_rows[model] = data
        for s in manifest['suites']:
            name = s['name']
            root = 'api_results' if model.startswith('jev-') else 'results'
            path = f'{root}/{model}/{name}.json.gz'; out['input_hashes'][path] = sha(ROOT / path)
            if s['track'] == 'order_robustness':
                continue
            row = dict(model=model, suite=name, reference=s['reference'], track=s['track'],
                       taxonomy=next(k for k,v in TAXONOMY.items() if name in v),
                       types=sorted({r['type'] for r in data[name]}),
                       **cluster_estimate([correct(r) for r in data[name]], [r['group'] for r in data[name]]))
            out['scores'].append(row)
        for name, a, b, lang in [('BoolQ: choice - noul','boolq','boolq_choice',False),
                                  ('SST5: choice - score','sst5','sst5_choice',False),
                                  ('XNLI: Chinese - English','xnli_en','xnli_zh',True),
                                  ('MASSIVE: Chinese - English','massive_en','massive_zh',True)]:
            mapping = {'false': 'A', 'true': 'B'} if a == 'boolq' else ({str(i): x for i,x in enumerate(['very negative','negative','neutral','positive','very positive'])} if a == 'sst5' else None)
            out['paired'].append(dict(model=model, contrast=name, a=a, b=b, label_mapping=mapping, **paired(data[a],data[b],lang,mapping,True)))
        for base in ['banking77','massive_en','jevbench_original','reflexbench_reflex-public-choice-v1']:
            repeated = data[base + '_repeat']; keys={(r['id'],r['qid']) for r in repeated}
            original=[r for r in data[base] if (r['id'],r['qid']) in keys]
            same=paired(original,repeated,include_pairs=True); changed=paired(repeated,data[base+'_reversed'],include_pairs=True)
            excess=cluster_estimate([int(y['flip'])-int(x['flip']) for x,y in zip(same['pairs'],changed['pairs'])],[x['group'] for x in same['pairs']])
            out['order'].append(dict(model=model,suite=base,same_order=same,reversed_order=changed,excess_discordance=excess))
        needle = data['jev_laya_needle']
        for length in sorted({r['length_target'] for r in needle}):
            for position in sorted({r['position'] for r in needle}):
                rr = [r for r in needle if r['length_target']==length and r['position']==position]
                out['needle'].append(dict(model=model,length=length,position=position,
                                           **cluster_estimate([correct(r) for r in rr],[r['group'] for r in rr])))
                for qid in sorted({r['qid'] for r in rr}):
                    qq=[r for r in rr if r['qid']==qid]
                    out['needle_by_question'].append(dict(model=model,length=length,position=position,qid=qid,
                                                          **cluster_estimate([correct(r) for r in qq],[r['group'] for r in qq])))
        for name in ['boolq','banking77','massive_zh','clinc150_oos']:
            out['risk'].append(dict(model=model,suite=name,**risk_curve(data[name])))
    # Pair model comparisons on every source; retain all contrasts, no winner-only reporting.
    out['model_contrasts'] = []
    for s in manifest['suites']:
        if s['track']=='order_robustness': continue
        for i, a in enumerate(models):
            for b in models[i+1:]:
                out['model_contrasts'].append(dict(suite=s['name'],a_model=a,b_model=b,
                                                  **paired(all_rows[a][s['name']],all_rows[b][s['name']])))
    write(ROOT / 'research/insights.json',out)
    write(ROOT / 'research/task_taxonomy.json',dict(axes=['task_family','output_type','reference_provenance','language','candidate_cardinality','context_length','state_question_multiplicity'],families=TAXONOMY))
    lines=['# Exploratory paired insights','',
           'Computed from frozen public predictions. Pointwise intervals resample source/state clusters, preserving pairs. Historical outcomes were available before this analysis; these are exploratory findings, not preregistered confirmations. All model/source contrasts are retained in `insights.json`.','',
           '| Contrast | Model | B − A (percentage points) | 95% paired interval | Cases / clusters |','|---|---|---:|---:|---:|']
    for x in out['paired']:
        lines.append(f'| {x["contrast"]} | {NAMES[x["model"]]} | {x["estimate"]*100:+.2f} | [{x["ci95"][0]*100:+.2f}, {x["ci95"][1]*100:+.2f}] | {x["n"]} / {x["clusters"]} |')
    lines += ['', '## Candidate reversal controls','', '| Source | Model | Same-order flip % | Reversal flip % | Accuracy change (pp) |','|---|---|---:|---:|---:|']
    for x in out['order']:
        lines.append(f'| {x["suite"]} | {NAMES[x["model"]]} | {100*x["same_order"]["disagreement"]["estimate"]:.2f} | {100*x["reversed_order"]["disagreement"]["estimate"]:.2f} | {100*x["reversed_order"]["estimate"]:+.2f} |')
    lines += ['', '## Interpretation boundaries','',
              '- Output-type changes compare the existing adapters and prompts jointly; they do not isolate a neural decision-head mechanism.',
              '- Language contrasts pair translated task examples while keeping the existing English question templates. They measure this interface, not unrestricted multilingual competence.',
              '- Reversal effects must be interpreted beside same-order repeated controls; original versus repeated requests may differ in execution batch shape.',
              '- Needle curves resample 25 original content units, not 450 supposedly independent variants. Context length is the source target length, not a shared tokenizer length.',
              '- Risk–coverage curves accept all tied probabilities together and use maximum class probability. Their empirical curves are not calibrated deployment thresholds.',
              '- Source/task families are organizational axes. No overall average across incompatible reference types or duplicate interface variants is reported.',
              '- Hosted Jev data, when complete, uses identical requests for accuracy but remains a separate regime for cost and latency.']
    (ROOT/'research/INSIGHTS.en.md').write_text('\n'.join(lines)+'\n')
    print('Analyzed',len(models),'models;',len(out['model_contrasts']),'paired model/source contrasts')


if __name__ == '__main__': main()
