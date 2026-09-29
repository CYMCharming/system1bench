import numpy as np
from style import data,save,plt

d=data();fig,axes=plt.subplots(len(d['models']),2,figsize=(5.5,1.75*len(d['models'])),sharex=True,sharey=True)
positions=sorted({r['position'] for r in d['needle_by_question']});colors=['#0072B2','#D55E00','#009E73'];markers=['o','s','^'];styles=['-','--',':']
for i,m in enumerate(d['models']):
    for j,q in enumerate(['wants','mentions_damage']):
        ax=axes[i,j]
        for p,col,mark,sty in zip(positions,colors,markers,styles):
            rows=sorted([r for r in d['needle_by_question'] if r['model']==m and r['qid']==q and r['position']==p],key=lambda x:x['length'])
            x=[r['length'] for r in rows];v=np.array([r['estimate']*100 for r in rows]);lo=[r['ci95'][0]*100 for r in rows];hi=[r['ci95'][1]*100 for r in rows]
            ax.plot(x,v,color=col,marker=mark,linestyle=sty,ms=3,label=p)
            ax.fill_between(x,lo,hi,color=col,alpha=.08,lw=0)
        ax.set_xscale('log');ax.set_ylim(-3,103);ax.set_yticks([0,50,100]);ax.grid(color='.92',lw=.5);ax.set_axisbelow(True)
        ax.text(.02,.06,f'({chr(97+i*2+j)})',transform=ax.transAxes,fontsize=8)
    axes[i,0].set_ylabel(d['model_names'][m]+'\nAgreement (%)')
axes[-1,0].set_xlabel('Source target length · choice question');axes[-1,1].set_xlabel('Source target length · boolean question')
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.56,1.005))
fig.tight_layout(rect=(0,0,1,.975),h_pad=.7);save(fig,'fig_context')
