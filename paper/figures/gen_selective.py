from style import data,save,legend,COLORS,MARKERS,plt

d=data(); d={**d,"models":[m for m in d["models"] if set(['boolq', 'banking77', 'massive_zh', 'clinc150_oos']) <= {r["suite"] for r in d["risk"] if r["model"]==m}]}; sources=['boolq','banking77','massive_zh','clinc150_oos'];fig,axes=plt.subplots(2,2,figsize=(5.5,4.9))
for i,(ax,s) in enumerate(zip(axes.flat,sources)):
    for m in d['models']:
        r=next(x for x in d['risk'] if x['suite']==s and x['model']==m);c=r['curve']
        ax.plot([x['coverage']*100 for x in c],[x['risk']*100 for x in c],color=COLORS[m],lw=1)
        for x in r['landmarks']:
            y=x['estimate']*100;lo,hi=[z*100 for z in x['ci95']]
            ax.errorbar(x['coverage']*100,y,yerr=[[y-lo],[hi-y]],fmt=MARKERS[m],color=COLORS[m],markersize=3,capsize=1.5,elinewidth=.6,alpha=.8)
    ax.set_xlim(0,102);ax.set_ylim(0,103);ax.set_yticks([0,25,50,75,100]);ax.grid(color='.92',lw=.5);ax.set_axisbelow(True)
    ax.text(.05,.9,f'({chr(97+i)})',transform=ax.transAxes)
    if i%2==0:ax.set_ylabel('Accepted-set error (%)')
    if i>=2:ax.set_xlabel('Coverage (%)')
legend(fig,d);fig.tight_layout(rect=(0,0,1,.94));save(fig,'fig_selective')
