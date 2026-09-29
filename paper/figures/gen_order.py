"""Exact correctness transitions and paired prediction flips under reversal."""
from style import data,save,COLORS,MARKERS,plt

d=data()
sources=[('banking77','Banking77','dataset'),('massive_en','MASSIVE English','dataset'),
         ('jevbench_original','JevBench original','authored'),
         ('reflexbench_reflex-public-choice-v1','ReflexBench','authored')]
names={'english':'Laya EN','multilingual':'Laya Multi','llama31_8b_instruct':'Llama 8B',
       'qwen3_8b':'Qwen 8B','jev-1.13.0':'Jev 1.13'}
fig,(a,b)=plt.subplots(1,2,figsize=(5.5,6.25),sharey=True,gridspec_kw={'width_ratios':[1.08,1]})
ticks=[];labels=[];y=0
for s,title,ref in sources:
    rows=[next(r for r in d['order'] if r['suite']==s and r['model']==m) for m in d['models']]
    n=rows[0]['reversed_order']['n']
    a.text(-36,y-.67,f'{title}  ·  n={n}  ·  {ref}',fontsize=7.7,weight='bold',color='#26343E',
           bbox={'facecolor':'white','edgecolor':'none','pad':1.2},zorder=6)
    for m,r in zip(d['models'],rows):
        paired=r['reversed_order'];base=r['same_order']['disagreement'];flip=paired['disagreement']
        regress=100*paired['a_only_correct']/n;correct=100*paired['b_only_correct']/n
        a.barh(y,-regress,height=.39,color='#B9775B',edgecolor='white',linewidth=.3,zorder=3)
        a.barh(y,correct,height=.39,color='#2C7791',edgecolor='white',linewidth=.3,zorder=3)
        for record,filled in [(base,False),(flip,True)]:
            v=100*record['estimate'];lo,hi=[100*x for x in record['ci95']]
            b.plot([lo,hi],[y,y],color=COLORS[m],lw=1.1,alpha=1 if filled else .5,zorder=2)
            b.scatter([v],[y],s=24 if filled else 19,marker=MARKERS[m],
                      facecolors=COLORS[m] if filled else 'white',edgecolors=COLORS[m],
                      linewidths=.85,zorder=4)
        ticks.append(y);labels.append(names[m]);y+=1
    y+=1.23
for ax in (a,b):
    ax.invert_yaxis();ax.set_ylim(y-.3,-1.2)
    ax.set_axisbelow(True);ax.grid(axis='x',color='#E4E9EB',linewidth=.55)
    ax.tick_params(axis='y',length=0,pad=5)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#A9B4B9')
a.axvline(0,color='#3F4E57',lw=.75)
a.set_xlim(-36,36);a.set_xticks([-30,-15,0,15,30]);a.set_xticklabels(['30','15','0','15','30'])
b.set_xlim(-2,72);b.set_xticks([0,20,40,60]);b.tick_params(axis='y',labelleft=False)
a.set_yticks(ticks,labels)
a.set_xlabel('Regressions  ←  %  →  Corrections',labelpad=7)
b.set_xlabel('Prediction flips (%)',labelpad=7)
a.set_title('Correctness turnover',loc='left',weight='bold',fontsize=9,pad=8)
b.set_title('Repeat vs reversal',loc='left',weight='bold',fontsize=9,pad=8)
fig.subplots_adjust(left=.24,right=.985,top=.965,bottom=.09,wspace=.19)
save(fig,'fig_order')
