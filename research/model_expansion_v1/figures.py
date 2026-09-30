"""Publication vector figures from verified result counts and paired intervals."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from system1bench.common import read,sha,write

HERE=ROOT/'research/model_expansion_v1'
OUT=ROOT/'paper/figures'
MODELS=['kev_08b','kev_4b','kev_9b','nanojev','qwen35_9b']
NAMES=['Kev-0.8B','Kev-4B','Kev-9B','NanoJev · games','Qwen3.5-9B · direct']
COLORS=['#91aab5','#367d8d','#173f59','#bd8742','#ae6484']
MARKERS=['o','s','^','D','X']
INK='#20343f'
GRID='#e3e8ea'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelcolor':INK,
    'text.color':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':'#96a3aa',
    'axes.linewidth':.7,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
    'savefig.facecolor':'white','figure.facecolor':'white'})

def clean(ax):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='x',color=GRID,lw=.7,zorder=0)
    ax.tick_params(axis='y',length=0,pad=10)
    ax.tick_params(axis='x',length=3,width=.7)

def save(fig,name):
    for extension in ('pdf','svg','png'):
        path=OUT/(name+'.'+extension)
        fig.savefig(path,dpi=320,bbox_inches='tight',pad_inches=.12)
        if extension=='svg':
            # Normalize generated XML whitespace; path line breaks remain intact.
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)

def accuracy(summary):
    fig,axes=plt.subplots(1,5,figsize=(14.6,5.0),sharey=True)
    fields=['refund/action','access/action','routing/action','contractnli/answer','scifact3/answer']
    titles=['Refund action','Access action','Routing action','Legal inference','Scientific evidence']
    volumes=[96,96,96,144,339]
    rows=[]
    for i,(ax,field,title,n) in enumerate(zip(axes,fields,titles,volumes)):
        for j,model in enumerate(MODELS):
            data=summary['models'][model]['panels'][field]['base']
            val=data['accuracy']*100
            lo,hi=np.array(data['accuracy_ci'])*100
            ax.errorbar(val,j,xerr=[[max(0,val-lo)],[max(0,hi-val)]],fmt=MARKERS[j],
                color=COLORS[j],markersize=7,elinewidth=1.45,capsize=2.2,markeredgewidth=.9,zorder=3)
            ax.annotate(f'{val:.1f}',(val,j),xytext=(0,9),textcoords='offset points',
                ha='center',va='bottom',fontsize=9.5,color=INK)
            rows.append(dict(model=model,panel=field,n=data['n'],accuracy=val,ci=[lo,hi]))
        ax.set_title(title+'\n'+f'n = {n}',fontsize=11.5,pad=20,fontweight='semibold')
        ax.set_xlim(-2,102)
        ax.set_xticks([0,25,50,75,100])
        ax.set_xlabel('Accuracy / agreement (%)',fontsize=9.4,labelpad=10)
        ax.set_ylim(4.48,-.58)
        ax.set_yticks(range(5),NAMES)
        ax.tick_params(axis='x',labelsize=9)
        clean(ax)
    axes[0].tick_params(axis='y',labelsize=10.5)
    fig.subplots_adjust(left=.145,right=.995,top=.69,bottom=.26,wspace=.22)
    fig.text(.145,.98,'Capability is workload-specific',fontsize=18,fontweight='semibold',va='top')
    fig.text(.145,.86,'EXECUTABLE POLICY',fontsize=9,color='#62757f',fontweight='bold')
    fig.text(.685,.86,'NATURAL-SOURCE REFERENCE',fontsize=9,color='#62757f',fontweight='bold')
    fig.text(.145,.10,'Points: complete-input base decisions. Whiskers: pointwise 95% cluster bootstrap; state / document / claim clusters.',fontsize=9,color='#596c76')
    fig.text(.145,.04,'No cross-source average. NanoJev: game-specialized release. Qwen: direct code likelihood, thinking off. SciFact NOINFO: derived absence of annotation.',fontsize=8.5,color='#596c76')
    save(fig,'fig_model_expansion_accuracy')
    return rows

def stability(summary):
    fig,axes=plt.subplots(1,2,figsize=(13.2,4.9),sharey=True)
    correct_color,wrong_color,changed_color='#24596d','#e8edef','#c9954f'
    rows=[]
    for ax,field,title in zip(axes,['contractnli/answer','scifact3/answer'],['Legal inference · 144 pairs','Scientific evidence · 339 pairs']):
        for j,model in enumerate(MODELS):
            r=summary['models'][model]['panels'][field]['reverse']
            good,bad,changed=[r[k]['rate']*100 for k in ('correct_stable','wrong_stable','flip')]
            n=r['common_valid']
            ax.barh(j,good,height=.57,color=correct_color,zorder=2)
            ax.barh(j,bad,left=good,height=.57,color=wrong_color,hatch='///',edgecolor='#b2bdc3',linewidth=.4,zorder=2)
            ax.barh(j,changed,left=good+bad,height=.57,color=changed_color,zorder=2)
            for start,width,count,color in [(0,good,r['correct_stable']['count'],'white'),(good,bad,r['wrong_stable']['count'],INK)]:
                if width>11:
                    ax.text(start+width/2,j,str(count),ha='center',va='center',fontsize=10,color=color)
            ci=np.array(r['correct_stable']['ci'])*100
            ax.errorbar(good,j,xerr=[[max(0,good-ci[0])],[max(0,ci[1]-good)]],fmt='none',ecolor=INK,elinewidth=1.2,capsize=2.5,zorder=4)
            ax.text(103,j,f"{r['flip']['count']}/{n}",va='center',fontsize=10,color='#93662a')
            rows.append(dict(model=model,panel=field,n=n,correct_stable=good,wrong_stable=bad,changed=changed,correct_stable_ci=ci.tolist()))
        ax.set_title(title,loc='left',fontweight='semibold',fontsize=12,pad=17)
        ax.set_xlim(0,118)
        ax.set_xticks([0,25,50,75,100])
        ax.set_xlabel('Paired outcomes (%)',labelpad=11)
        ax.set_ylim(4.6,-.5)
        ax.set_yticks(range(5),NAMES)
        clean(ax)
        ax.text(103,-.68,'Flips',fontsize=9,color='#93662a')
    handles=[Patch(facecolor=correct_color,label='Correct and stable'),Patch(facecolor=wrong_color,hatch='///',edgecolor='#b2bdc3',label='Wrong and stable'),Patch(facecolor=changed_color,label='Changed answer')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.15,.86),ncol=3,frameon=False,fontsize=10,handlelength=1.5,columnspacing=2.1)
    fig.subplots_adjust(left=.16,right=.995,top=.68,bottom=.21,wspace=.19)
    fig.text(.16,.98,'An unchanged answer can be reliably wrong',fontsize=18,fontweight='semibold',va='top')
    fig.text(.16,.065,'Criterion insertion order is reversed; semantic labels are retained. Qwen display order and answer codes change jointly.',fontsize=9,color='#596c76')
    fig.text(.16,.012,'Stacks: exact common-valid counts. Black whiskers: correct-and-stable pointwise 95% cluster intervals. All models have 0 exact-repeat flips.',fontsize=8.5,color='#596c76')
    save(fig,'fig_model_expansion_stability')
    return rows

def scaling(summary):
    comparisons=summary['paired_model_comparisons']['kev_9b-minus-kev_4b']
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.5))
    fields=['refund/action','access/action','routing/action','contractnli/answer','scifact3/answer']
    for ax,keys,metric,title in [(axes[0],fields,'base','Base correctness'),(axes[1],fields[:3],'counterfactual_joint','Both counterfactual actions correct')]:
        for j,key in enumerate(keys):
            entry=comparisons[key][metric]
            x=entry['delta']*100
            lo,hi=np.array(entry['ci'])*100
            ax.errorbar(x,j,xerr=[[max(0,x-lo)],[max(0,hi-x)]],fmt='o',markersize=7.5,
                color='#24596d',mfc='#24596d' if x>=0 else 'white',mew=1.4,elinewidth=1.5,capsize=3,zorder=3)
            ax.annotate(f'{x:+.1f} pp',(x,j),xytext=(0,10),textcoords='offset points',ha='center',fontsize=9.5)
        ax.axvline(0,color='#617985',lw=1,ls=(0,(3,3)),zorder=1)
        ax.set_xlim(-35,30)
        ax.set_ylim(len(keys)-.5,-.6)
        ax.set_yticks(range(len(keys)),[{'refund/action':'Refund','access/action':'Access','routing/action':'Routing','contractnli/answer':'Legal','scifact3/answer':'Science'}[k] for k in keys])
        ax.set_xticks([-30,-15,0,15,30])
        ax.set_xlabel('Kev-9B minus Kev-4B (percentage points)',fontsize=10,labelpad=10)
        ax.set_title(title,loc='left',fontsize=12,fontweight='semibold',pad=17)
        clean(ax)
    fig.subplots_adjust(left=.09,right=.99,top=.69,bottom=.26,wspace=.35)
    fig.text(.09,.97,'A larger release does not dominate every workload',fontsize=17,fontweight='semibold',va='top')
    fig.text(.09,.86,'Paired same-input differences, not an unpaired leaderboard or an architectural scaling law.',fontsize=10,color='#596c76')
    fig.text(.09,.065,'Whiskers: pointwise 95% paired cluster bootstrap. Each policy has 96 base pairs; legal 144, science 339.',fontsize=9,color='#596c76')
    fig.text(.09,.012,'Checkpoint size is confounded with different training histories. New-seed replication is reported separately; no causal size claim.',fontsize=8.5,color='#596c76')
    save(fig,'fig_model_expansion_scale')

def replication(discovery,replica):
    fig,axes=plt.subplots(1,2,figsize=(11.7,4.7),sharey=True)
    panels=discovery['paired_model_comparisons']['kev_9b-minus-kev_4b']
    rows=[]
    for ax,endpoint,title in zip(axes,['base_action','counterfactual_joint'],['Base action correctness','Both counterfactual actions correct']):
        for j,family in enumerate(['refund','access','routing']):
            metric='base' if endpoint=='base_action' else endpoint
            old=panels[family+'/action'][metric]
            new=replica['primary_effects'][family+'/'+endpoint]
            for offset,value,color,marker in [(-.14,old,'#91aab5','o'),(.14,new,'#173f59','s')]:
                x=value['delta']*100
                ci=np.array(value['ci95'] if 'ci95' in value else value['ci'])*100
                ax.errorbar(x,j+offset,xerr=[[max(0,x-ci[0])],[max(0,ci[1]-x)]],fmt=marker,color=color,
                    markersize=6.5,elinewidth=2,capsize=2.7,zorder=3)
            guard=np.array(new['ci_family_guard'])*100
            ax.plot(guard,[j+.14,j+.14],color='#173f59',lw=.75,zorder=2)
            ax.text(31,j+.14,f"{new['left_correct']} → {new['right_correct']}",va='center',fontsize=9.5,color=INK)
            rows.append(dict(family=family,endpoint=endpoint,discovery=old,replication=new))
        ax.axvline(0,color='#617985',lw=1,ls=(0,(3,3)),zorder=1)
        ax.set_xlim(-36,49)
        ax.set_xticks([-30,-15,0,15,30])
        ax.set_ylim(2.55,-.65)
        ax.set_yticks(range(3),['Refund','Access','Routing'])
        ax.set_title(title,loc='left',fontsize=12,fontweight='semibold',pad=17)
        ax.set_xlabel('Kev-9B minus Kev-4B (percentage points)',fontsize=10,labelpad=11)
        ax.text(31,-.73,'New correct / 96',fontsize=9,color='#62757f')
        clean(ax)
    handles=[plt.Line2D([],[],marker='o',color='#91aab5',lw=1.5,label='Discovery states'),
             plt.Line2D([],[],marker='s',color='#173f59',lw=1.5,label='New-seed replication')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.085,.88),ncol=2,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.10,right=.99,top=.68,bottom=.27,wspace=.16)
    fig.text(.10,.98,'Opposite workload shifts persist on new policy states',fontsize=17,fontweight='semibold',va='top')
    fig.text(.10,.11,'Each endpoint: 96 paired states. Thick whiskers: pointwise 95% CI; thin extensions: replication six-effect 99.1667% guard.',fontsize=9,color='#596c76')
    fig.text(.10,.045,'Routing declines in both samples, but its guarded replication intervals reach zero. Same grammar; training history confounds size.',fontsize=9,color='#596c76')
    save(fig,'fig_model_expansion_replication')
    return rows

def main():
    summary=read(HERE/'summary.json')
    assert set(summary['models'])==set(MODELS)
    assert all(summary['models'][model]['count']==4905 and summary['models'][model]['errors']==0 for model in MODELS)
    assert set(read(HERE/'verification.json')['models'])==set(MODELS)
    payload=dict(summary_sha256=sha(HERE/'summary.json'),verification_sha256=sha(HERE/'verification.json'),
        generator_sha256=sha(__file__),accuracy=accuracy(summary),stability=stability(summary))
    scaling(summary)
    replica_path=ROOT/'research/model_expansion_replication_v1/summary.json'
    if replica_path.exists():
        replica=read(replica_path)
        assert read(replica_path.parent/'verification.json')['complete_input_reconstruction']
        payload['replication_summary_sha256']=sha(replica_path)
        payload['replication_verification_sha256']=sha(replica_path.parent/'verification.json')
        payload['replication']=replication(summary,replica)
    write(HERE/'figure_data.json',payload)
    print('Rendered PDF/SVG/PNG: accuracy, stability, paired scale differences',flush=True)

if __name__=='__main__':
    main()
