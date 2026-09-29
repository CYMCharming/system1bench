import numpy as np
from style import data,save,plt

d=data();fig,axes=plt.subplots(len(d['models']),2,figsize=(5.5,8.4),sharex=True,sharey=True)
positions=sorted({r['position'] for r in d['needle_by_question']});colors=['#2C7791','#B9775B','#3F9C83'];markers=['o','s','^'];styles=['-','--',':']
short={'english':'Laya EN','multilingual':'Laya Multi','llama31_8b_instruct':'Llama 8B','qwen3_8b':'Qwen 8B','jev-1.13.0':'Jev 1.13'}
for i,m in enumerate(d['models']):
    for j,q in enumerate(['wants','mentions_damage']):
        ax=axes[i,j]
        for p,col,mark,sty in zip(positions,colors,markers,styles):
            rows=sorted([r for r in d['needle_by_question'] if r['model']==m and r['qid']==q and r['position']==p],key=lambda x:x['length'])
            x=[r['length'] for r in rows];v=np.array([r['estimate']*100 for r in rows]);lo=[r['ci95'][0]*100 for r in rows];hi=[r['ci95'][1]*100 for r in rows]
            ax.plot(x,v,color=col,marker=mark,linestyle=sty,ms=3,label=p)
            ax.fill_between(x,lo,hi,color=col,alpha=.08,lw=0)
        ax.set_xscale('log');ax.set_ylim(-3,103);ax.set_yticks([0,50,100]);ax.grid(color='#E4E9EB',lw=.5);ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#A9B4B9');ax.spines['bottom'].set_color('#A9B4B9')
    axes[i,0].set_ylabel(short[m]+'\nAgreement (%)',fontsize=7.4)
axes[0,0].set_title('Choice intent',fontsize=9,weight='bold',pad=7)
axes[0,1].set_title('Binary damage',fontsize=9,weight='bold',pad=7)
for ax in axes[-1]: ax.set_xlabel('Target length (tokens)',fontsize=8)
handles,labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.59,.996),fontsize=7)
fig.subplots_adjust(left=.23,right=.98,top=.93,bottom=.075,hspace=.24,wspace=.16)
save(fig,'fig_context')
