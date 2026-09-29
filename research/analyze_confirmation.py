"""Predeclared paired confirmation analysis, clustered and stratified by data seed."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from system1bench.common import read,sha,write  # noqa: E402
from research.analyze import cluster_estimate,correct  # noqa: E402

BASE=ROOT/'research/confirmation_v1'
EFFECTS=['reversal_excess_action_discordance','chinese_action_accuracy','distractor_action_accuracy','paraphrase_action_accuracy','choice_encoded_review_accuracy','choice_encoded_severity_accuracy']


def simultaneous(values,seeds):
    a=np.asarray(values,dtype=float);seeds=np.asarray(seeds);rng=np.random.default_rng(20260929);boot=[]
    for _ in range(100):
        indices=np.concatenate([rng.choice(np.where(seeds==s)[0],size=(100,np.sum(seeds==s)),replace=True) for s in sorted(set(seeds))],axis=1)
        boot.append(a[indices].mean(axis=1))
    boot=np.concatenate(boot);point=a.mean(axis=0);se=boot.std(axis=0,ddof=1);z=np.divide(np.abs(boot-point),se,out=np.zeros_like(boot),where=se>0)
    critical=float(np.quantile(z.max(axis=1),.95))
    return [dict(name=name,estimate=float(point[i]),simultaneous_ci95=[float(max(-1,point[i]-critical*se[i])),float(min(1,point[i]+critical*se[i]))],
                 standard_error=float(se[i]),zero_empirical_variance=bool(se[i]==0),
                 by_seed={str(s):float(a[seeds==s,i].mean()) for s in sorted(set(seeds))}) for i,name in enumerate(EFFECTS)]


def main():
    frozen=read(BASE/'frozen.json');manifest=read(BASE/'manifest.json')
    if sha(BASE/'frozen.json')!=manifest['frozen_sha256']:raise ValueError('Input drift')
    out=dict(protocol=manifest['protocol'],manifest_sha256=sha(BASE/'manifest.json'),families=[],codebook=[],
             interval_scope='simultaneous within six predeclared contrasts of each model/family, stratified by generator seed; not across models/families',
             input_hashes={})
    roots=sorted((BASE/'results').glob('*')) if (BASE/'results').exists() else []
    api=BASE/'api/jev-1.13.0'
    if api.exists():roots.append(api)
    for root in roots:
        if not (root/'metadata.json').exists() or read(root/'metadata.json')['status']!='DONE':continue
        model=root.name;meta=read(root/'metadata.json')
        for s in frozen['suites']:
            path=root/(s['name']+'.json.gz')
            if sha(path)!=meta['suites'][s['name']]['sha256']:raise ValueError('Raw hash')
            out['input_hashes'][str(path.relative_to(ROOT))]=sha(path)
            rows=json.loads(gzip.decompress(path.read_bytes()))['rows'];cases={c['id']:c for c in s['cases']}
            if len(rows)!=len(cases)*3 or len({(r['id'],r['qid']) for r in rows})!=len(rows):raise ValueError('Raw matrix')
            grouped={}
            for r in rows:
                c=cases[r['id']]
                if r['gold']!=c['gold'][r['qid']]['label'] or r['request_sha256']!=c['request_sha256']:raise ValueError('Reference/input mismatch')
                grouped.setdefault(c['group'],{}).setdefault(c['condition'],{})[r['qid']]=r
            base=[];contrasts=[];seeds=[];clusters=[]
            for group,v in sorted(grouped.items()):
                a=v['original'];repeat=v['repeat'];b=v['reversed'];clusters.append(group);seeds.append(cases[a['action']['id']]['generator_seed'])
                flip=lambda x,y:int(x['prediction']!=y['prediction'])
                contrasts.append([flip(repeat['action'],b['action'])-flip(a['action'],repeat['action']),
                                  correct(v['chinese']['action'])-correct(a['action']),correct(v['distractor']['action'])-correct(a['action']),
                                  correct(v['paraphrase']['action'])-correct(a['action']),correct(v['choice_encoded']['review'])-correct(a['review']),
                                  correct(v['choice_encoded']['severity'])-correct(a['severity'])])
                base.append(a)
            base_metrics={q:dict(**cluster_estimate([correct(a[q]) for a in base],clusters),
                                  gold_counts=dict(Counter(a[q]['gold'] for a in base)),
                                  majority_reference_baseline=max(Counter(a[q]['gold'] for a in base).values())/len(base)) for q in ['action','review','severity']}
            variants=[]
            for variant in frozen['variants']:
                for q in ['action','review','severity']:
                    rr=[grouped[g][variant][q] for g in clusters]
                    variants.append(dict(condition=variant,qid=q,**cluster_estimate([correct(r) for r in rr],clusters),
                                         failures=sum(r['error'] is not None for r in rr)))
            joint=cluster_estimate([correct(grouped[g]['original']['action'])*correct(grouped[g]['counterfactual']['action']) for g in clusters],clusters)
            out['families'].append(dict(model=model,family=s['name'],base=base_metrics,primary_effects=simultaneous(contrasts,seeds),
                                        variants=variants,counterfactual_joint=joint,clusters=clusters,generator_seeds=seeds,paired_effect_vectors=contrasts))
    for root in sorted((BASE/'codebook').glob('*')) if (BASE/'codebook').exists() else []:
        if not (root/'metadata.json').exists() or read(root/'metadata.json')['status']!='DONE':continue
        meta=read(root/'metadata.json')
        for s in frozen['suites']:
            path=root/(s['name']+'.json.gz');rows=json.loads(gzip.decompress(path.read_bytes()))['rows']
            if sha(path)!=meta['suites'][s['name']]['sha256']:raise ValueError('Codebook hash')
            out['input_hashes'][str(path.relative_to(ROOT))]=sha(path)
            maps={mode:{r['group']:r for r in rows if r['condition']==mode} for mode in ['baseline','repeat','position_only','code_only','both']};groups=sorted(maps['baseline'])
            if len(rows)!=480 or any(set(m)!=set(groups) for m in maps.values()):raise ValueError('Codebook matrix')
            for g in groups:
                if maps['baseline'][g]['prompt_token_sha256']!=maps['repeat'][g]['prompt_token_sha256']:raise ValueError('Nonidentical repeat')
                if maps['baseline'][g]['code_indices']!=maps['position_only'][g]['code_indices']:raise ValueError('Position changed code identities')
            contrasts=[]
            for mode in ['repeat','position_only','code_only','both']:
                aa=[maps['baseline'][g] for g in groups];bb=[maps[mode][g] for g in groups]
                contrasts.append(dict(mode=mode,accuracy=cluster_estimate([correct(x) for x in bb],groups),
                                      paired_accuracy=cluster_estimate([correct(y)-correct(x) for x,y in zip(aa,bb)],groups),
                                      discordance=cluster_estimate([x['prediction']!=y['prediction'] for x,y in zip(aa,bb)],groups)))
            out['codebook'].append(dict(model=root.name,family=s['name'],n=96,contrasts=contrasts))
    write(BASE/'summary.json',out)
    print('Analyzed',len(out['families']),'model/family cells;',len(out['codebook']),'codebook cells')


if __name__=='__main__':main()
