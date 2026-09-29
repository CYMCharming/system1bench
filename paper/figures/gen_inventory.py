import numpy as np
from style import data,save,plt,ROOT
import json

d=data();summary=json.loads((ROOT/'results/summary.json').read_text());suites=[s for names in d['taxonomy'].values() for s in names]
refs={'dataset_provided':'D','human_prompt_annotation':'H','programmatic':'P','synthetic_teacher':'T','authored_or_AI_reviewed':'A'}
short={'reflexbench_reflex-public-choice-v1':'Reflex','jev_laya_multilingual':'JL multilingual'}


def draw(selected,filename):
    matrix=[];labels=[]
    for s in selected:
        rows=[next(r for r in d['scores'] if r['suite']==s and r['model']==m) for m in d['models']]
        matrix.append([r['estimate']*100 for r in rows]);info=summary['models']['english']['suites'][s]['all']
        k=info.get('label_count','mixed');baseline=info.get('majority_baseline');base='—' if baseline is None else f'{baseline*100:.0f}%'
        name=short.get(s,s).replace('jev_laya_','JL ').replace('jevbench_','JB ')
        labels.append(f'{name} [{refs[rows[0]["reference"]]}] K={k}\n n={rows[0]["n"]}, g={rows[0]["clusters"]}, maj={base}')
    a=np.asarray(matrix);fig,ax=plt.subplots(figsize=(5.5,.35*len(selected)+1.3));im=ax.imshow(a,vmin=0,vmax=100,cmap='cividis',aspect='auto')
    ax.set_xticks(range(len(d['models'])),[d['model_names'][m] for m in d['models']],rotation=35,ha='right',fontsize=8);ax.set_yticks(range(len(selected)),labels,fontsize=7.5)
    for i in range(len(selected)):
        for j in range(len(d['models'])):ax.text(j,i,f'{a[i,j]:.1f}',ha='center',va='center',fontsize=8,color='white' if a[i,j]<48 else 'black')
    for i in range(1,len(selected)):
        left=next(k for k,v in d['taxonomy'].items() if selected[i-1] in v);right=next(k for k,v in d['taxonomy'].items() if selected[i] in v)
        if left!=right:ax.axhline(i-.5,color='white',lw=2)
    c=fig.colorbar(im,ax=ax,fraction=.025,pad=.025);c.set_label('Reference agreement (%)',fontsize=8)
    fig.tight_layout();save(fig,filename)


draw(suites,'fig_inventory');draw(suites[:14],'fig_inventory_a');draw(suites[14:],'fig_inventory_b')
