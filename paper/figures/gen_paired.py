from style import data,save,COLORS,MARKERS,interval,plt

d=data(); d={**d,"models":[m for m in d["models"] if set(['boolq', 'sst5', 'xnli_en', 'massive_en']) <= {r["a"] for r in d["paired"] if r["model"]==m}]}; contrasts=list(dict.fromkeys(x['contrast'] for x in d['paired']))
fig,(a,b)=plt.subplots(1,2,figsize=(5.5,6.1),sharey=True,gridspec_kw={'width_ratios':[1.15,1]})
y=0;ticks=[];names=[]
for c in contrasts:
    for m in d['models']:
        r=next(x for x in d['paired'] if x['model']==m and x['contrast']==c)
        interval(a,None,r,y,COLORS[m],MARKERS[m]);interval(b,None,r['disagreement'],y,COLORS[m],MARKERS[m])
        ticks.append(y);names.append(c.split(':')[0]+' · '+d['model_names'][m]);y+=1
    if c!=contrasts[-1]:
        for ax in [a,b]:ax.axhline(y-.45,color='.88',lw=.6)
        y+=.55
for ax in [a,b]:ax.grid(axis='x',color='.92',lw=.5);ax.set_axisbelow(True)
a.set_yticks(ticks,names);a.invert_yaxis();a.axvline(0,color='.4',lw=.8);a.set_xlabel('Paired accuracy change (pp)\nchoice − native / Chinese − English')
b.set_xlim(0,100);b.set_xlabel('Prediction disagreement (%)');b.tick_params(axis='y',left=False)
fig.tight_layout(w_pad=2);save(fig,'fig_paired')
