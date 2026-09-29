from style import data,save,COLORS,MARKERS,interval,plt

d=data(); d={**d,"models":[m for m in d["models"] if set(['boolq', 'sst5', 'xnli_en', 'massive_en']) <= {r["a"] for r in d["paired"] if r["model"]==m}]}; contrasts=list(dict.fromkeys(x['contrast'] for x in d['paired']))
fig,(a,b)=plt.subplots(1,2,figsize=(5.5,6.1),sharey=True,gridspec_kw={'width_ratios':[1.1,1]})
short={'english':'Laya EN','multilingual':'Laya Multi','llama31_8b_instruct':'Llama 8B','qwen3_8b':'Qwen 8B','jev-1.13.0':'Jev 1.13'}
y=0;ticks=[];names=[]
for c in contrasts:
    a.text(-30,y-.68,c.split(':')[0].replace('_',' ').upper(),fontsize=8,weight='bold',
           color='#26343E',bbox={'facecolor':'white','edgecolor':'none','pad':1},zorder=6)
    for m in d['models']:
        r=next(x for x in d['paired'] if x['model']==m and x['contrast']==c)
        interval(a,None,r,y,COLORS[m],MARKERS[m]);interval(b,None,r['disagreement'],y,COLORS[m],MARKERS[m])
        ticks.append(y);names.append(short[m]);y+=1
    if c!=contrasts[-1]:
        for ax in [a,b]:ax.axhline(y-.45,color='.88',lw=.6)
        y+=.55
for ax in [a,b]:
    ax.grid(axis='x',color='#E4E9EB',lw=.5);ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color('#A9B4B9')
a.set_yticks(ticks,names);a.invert_yaxis();a.set_ylim(y-.3,-1.15);a.axvline(0,color='#53626B',lw=.8)
a.set_xlim(-31,22);a.set_xlabel('Accuracy change (pp)',fontsize=8)
b.set_xlim(0,100);b.set_xlabel('Prediction disagreement (%)',fontsize=8);b.tick_params(axis='y',left=False,labelleft=False)
a.set_title('Correctness',loc='left',fontsize=9,weight='bold')
b.set_title('Stability',loc='left',fontsize=9,weight='bold')
fig.subplots_adjust(left=.25,right=.98,top=.95,bottom=.09,wspace=.16)
save(fig,'fig_paired')
