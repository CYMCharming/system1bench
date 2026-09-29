"""Generate manuscript tables/macros from verified, repository-tracked analyses."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];P=ROOT/'paper'
d=json.loads((ROOT/'research/insights.json').read_text());models=d['models']
short={'english':'Laya EN','multilingual':'Laya Multi','llama31_8b_instruct':'Llama','qwen3_8b':'Qwen','jev-1.13.0':'Jev'}
escape=lambda s:s.replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
rows=[r for r in d['order'] if r['model'] in ['english','multilingual','llama31_8b_instruct','qwen3_8b']]
flips=[100*r['reversed_order']['disagreement']['estimate'] for r in rows];repeat=[100*r['same_order']['disagreement']['estimate'] for r in rows]
macros={'ModelCount':str(len(models)),'ReversalMin':f'{min(flips):.1f}','ReversalMax':f'{max(flips):.1f}','RepeatMax':f'{max(repeat):.1f}'}
for m in ['english','multilingual','llama31_8b_instruct','qwen3_8b']:
 r=next(r for r in d['paired'] if r['model']==m and r['a']=='sst5')
 macros['SST'+{'english':'EN','multilingual':'Multi','llama31_8b_instruct':'Llama','qwen3_8b':'Qwen'}[m]]=f'{100*r["estimate"]:+.1f}'
(P/'numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in macros.items())+'\n')
lines=[r'\begin{tabular}{l'+'r'*len(models)+'}',r'\toprule','Source & '+' & '.join(short[m] for m in models)+r' \\',r'\midrule']
for s in [s for vv in d['taxonomy'].values() for s in vv]:
 scores=[next(r for r in d['scores'] if r['suite']==s and r['model']==m) for m in models]
 name=s.replace('reflexbench_reflex-public-choice-v1','ReflexBench').replace('jev_laya_','JL: ').replace('jevbench_','JB: ')
 lines.append(escape(name)+' & '+' & '.join(f'{r["estimate"]*100:.1f}' for r in scores)+r' \\')
lines += [r'\bottomrule',r'\end{tabular}'];(P/'tables/full_accuracy.tex').write_text('\n'.join(lines)+'\n')
lines=[r'\begin{tabular}{llrrr}',r'\toprule',r'Source & Model & Repeat flips & Reversal flips & $\Delta$ accuracy \\',r'\midrule']
for s in ['banking77','massive_en']:
 for m in models:
  r=next(x for x in d['order'] if x['suite']==s and x['model']==m)
  lines.append(escape(s)+' & '+short[m]+' & '+f'{100*r["same_order"]["disagreement"]["estimate"]:.1f} & {100*r["reversed_order"]["disagreement"]["estimate"]:.1f} & {100*r["reversed_order"]["estimate"]:+.1f}'+r' \\')
lines += [r'\bottomrule',r'\end{tabular}'];(P/'tables/order_summary.tex').write_text('\n'.join(lines)+'\n')
if 'jev-1.13.0' in models:
 meta=json.loads((ROOT/'api_results/jev-1.13.0/metadata.json').read_text());fail=sum(v['failures'] for v in meta['suites'].values())
 lines=[r'\paragraph{Hosted Jev.} The pinned \texttt{jev-1.13.0} endpoint completed '+f'{meta["completed_requests"]:,}'+r' request executions covering the same 26,450 decisions. '+f'{fail}'+r' decisions failed the declared transport/response validity rule and remain in the accuracy denominator. The API reported '+f'{meta["input_tokens"]:,}'+r' input tokens, corresponding to USD '+f'{meta["accounted_cost_usd"]:.3f}'+r' at the retrieved public price; unavailable usage on failed calls is not included. Every returned version and answer is retained. Server tokenization and weights are not observable. Hosted client times include the proxy, network and service and are reported separately from resident-GPU measurements.']
else:lines=[]
(P/'tables/jev_observation.tex').write_text('\n'.join(lines)+'\n')
print('Built manuscript tables and macros for',len(models),'models')
