from style import data,save,COLORS,MARKERS,interval,plt

d=data(); d={**d,"models":[m for m in d["models"] if set(['banking77', 'massive_en', 'jevbench_original', 'reflexbench_reflex-public-choice-v1']) <= {r["suite"] for r in d["order"] if r["model"]==m}]}; sources=['banking77','massive_en','jevbench_original','reflexbench_reflex-public-choice-v1']
short={'banking77':'Banking77','massive_en':'MASSIVE EN','jevbench_original':'JevBench original','reflexbench_reflex-public-choice-v1':'ReflexBench'}
fig,(a,b)=plt.subplots(1,2,figsize=(5.5,6.3),sharey=True,gridspec_kw={'width_ratios':[1,1]})
y=0;ticks=[];labels=[]
for s in sources:
    for m in d['models']:
        r=next(x for x in d['order'] if x['suite']==s and x['model']==m)
        z=r['same_order']['disagreement']['estimate']*100;v=r['reversed_order']['disagreement']['estimate']*100
        a.plot([z,v],[y,y],color=COLORS[m],alpha=.5,lw=1)
        a.errorbar(z,y,xerr=[[z-r['same_order']['disagreement']['ci95'][0]*100],[r['same_order']['disagreement']['ci95'][1]*100-z]],fmt=MARKERS[m],mfc='white',mec=COLORS[m],color=COLORS[m],markersize=4,capsize=2,elinewidth=.8,zorder=3)
        interval(a,None,r['reversed_order']['disagreement'],y,COLORS[m],MARKERS[m])
        interval(b,None,r['reversed_order'],y,COLORS[m],MARKERS[m])
        ticks.append(y);labels.append((short[s]+' · ' if m==d['models'][0] else '')+d['model_names'][m]);y+=1
    if s!=sources[-1]:
        for ax in [a,b]:ax.axhline(y-.45,color='.88',lw=.6)
        y+=.55
for ax in [a,b]:ax.grid(axis='x',color='.92',lw=.5);ax.set_axisbelow(True)
a.set_yticks(ticks,labels);a.invert_yaxis();a.set_xlim(-3,100);a.set_xticks([0,50,100]);a.set_xlabel('Prediction flips (%)\nopen: repeat; filled: reversed')
b.axvline(0,color='.4',lw=.8);b.set_xlabel('Reversed − repeat accuracy (pp)');b.tick_params(axis='y',left=False)
fig.tight_layout(w_pad=2);save(fig,'fig_order')
