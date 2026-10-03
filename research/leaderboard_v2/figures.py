"""Publication-ready fourteen-model figures derived only from verified scores."""
from pathlib import Path
import os
import sys

os.environ['SOURCE_DATE_EPOCH']='1790899200'  # 2026-10-02 UTC; stable PDF/SVG metadata.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'research/leaderboard_v2'
OUT=ROOT/'paper/figures'
sys.path.insert(0,str(HERE))
from build import LABELS,MODELS,read,sha,write

INK='#183444'
MUTED='#627884'
GRID='#E2E9E9'
PALETTE={'jev-1.13.0':'#183A55','kev_08b':'#187D84','kev_4b':'#187D84',
         'kev_9b':'#187D84','nanojev':'#BE8950','english':'#7792A0',
         'multilingual':'#7792A0','llama31_8b_instruct':'#986291',
         'qwen3_8b':'#986291','qwen35_9b':'#986291',
         'kev_27b':'#0D7278','qwen35_08b':'#986291','qwen35_4b':'#986291',
         'qwen38_27b':'#986291'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'axes.edgecolor':'#A3B2B9',
    'axes.linewidth':.7,'text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,
    'ytick.color':INK,'figure.facecolor':'white','savefig.facecolor':'white',
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
plt.rcParams['svg.hashsalt']='system1bench-leaderboard-v2'

def mix(color,amount):
    return tuple((1-amount)*np.ones(3)+amount*np.array(to_rgb(color)))

def setup(ax,n=14):
    ax.spines[['top','right','left']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='x',color=GRID,lw=.7)
    ax.tick_params(axis='y',length=0,pad=6)
    ax.tick_params(axis='x',length=3,width=.7)
    ax.set_ylim(n-.5,-.5)

def save(fig,name):
    paths=[]
    for ext in ('pdf','svg','png'):
        path=OUT/('fig_leaderboard_v2_'+name+'.'+ext)
        metadata={'Date':'2026-10-02'} if ext=='svg' else None
        fig.savefig(path,dpi=320,bbox_inches='tight',pad_inches=.13,metadata=metadata)
        if ext=='svg':
            path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
        paths.append(path)
    plt.close(fig)
    return paths

def rows(data,metric):
    return sorted(MODELS,key=lambda m:(data['rankings'][metric][m],MODELS.index(m)))

def small_bar(ax,data,metric,title,subtitle,show_rank=True):
    order=rows(data,metric)
    values=[100*data['models'][m]['metrics'][metric]['score'] for m in order]
    ax.barh(range(len(MODELS)),[100]*len(MODELS),height=.58,color='#F0F4F4',zorder=1)
    for y,(model,value) in enumerate(zip(order,values)):
        ax.barh(y,value,height=.58,color=PALETTE[model],zorder=2)
        ax.text(min(value+2,103),y,f'{value:.1f}',va='center',fontsize=9.3,
                fontweight='semibold' if y==0 else 'normal',color=INK,zorder=4)
    ax.set_xlim(0,116)
    ax.set_xticks([0,25,50,75,100])
    ax.set_yticks(range(len(MODELS)),[f"{data['rankings'][metric][m]:>2}.  {LABELS[m]}" if show_rank
                               else LABELS[m] for m in order],fontsize=8.5)
    ax.set_title(title,loc='left',fontsize=13,fontweight='semibold',pad=23,color=INK)
    ax.text(0,1.025,subtitle,transform=ax.transAxes,fontsize=9,color=MUTED,va='bottom')
    setup(ax)

def overview(data):
    order=rows(data,'overall_domain_equal')
    fig=plt.figure(figsize=(17.4,9.8))
    axes=fig.add_gridspec(1,2,width_ratios=[1.07,1.23],left=.17,right=.985,top=.78,bottom=.15,wspace=.18)
    ax=fig.add_subplot(axes[0,0])
    mat=fig.add_subplot(axes[0,1])
    for y,model in enumerate(order):
        cell=data['models'][model]['metrics']['overall_domain_equal']
        value=100*cell['score']
        low,high=[100*v for v in cell['ci95']]
        ax.barh(y,100,height=.57,color='#F0F4F4',zorder=1)
        ax.barh(y,value,height=.57,color=PALETTE[model],zorder=2)
        ax.errorbar(value,y,xerr=[[max(0,value-low)],[max(0,high-value)]],fmt='o',
                    markersize=3.3,color=INK,elinewidth=1.05,capsize=2.2,zorder=4)
        ax.text(105,y,f'{value:.1f}',va='center',fontsize=10,fontweight='semibold',color=INK)
    ax.set_xlim(0,117)
    ax.set_xticks([0,25,50,75,100])
    ax.set_yticks(range(len(MODELS)),[f"{data['rankings']['overall_domain_equal'][m]:>2}.  {LABELS[m]}" for m in order],fontsize=10)
    ax.set_title('Three-domain index / 100',loc='left',fontsize=13,fontweight='semibold',pad=18)
    setup(ax)
    mat.set_xlim(-.55,4.55)
    mat.set_ylim(len(MODELS)-.5,-.5)
    mat.axis('off')
    columns=[('refund','REFUND','96'),('access','ACCESS','96'),('routing','ROUTING','96'),
             ('legal','LEGAL','144'),('science','SCIENCE','339')]
    domain_colors=['#26818A','#26818A','#26818A','#986291','#4577A2']
    for j,(key,label,n) in enumerate(columns):
        mat.text(j,-.93,label,ha='center',va='center',fontsize=9.3,fontweight='bold',color=MUTED)
        mat.text(j,-.60,f'n = {n}',ha='center',va='center',fontsize=8.7,color=MUTED)
        for y,model in enumerate(order):
            v=100*data['models'][model]['metrics'][key]['score']
            rect=plt.Rectangle((j-.43,y-.34),.86,.68,facecolor=mix(domain_colors[j],.08+.31*v/100),edgecolor='none')
            mat.add_patch(rect)
            mat.text(j,y,f'{v:.1f}',ha='center',va='center',fontsize=10.2,
                     fontweight='semibold' if y<3 else 'normal',color=INK)
    mat.plot([2.5,2.5],[-.45,len(MODELS)-.6],color='#B6C4C9',lw=.9)
    mat.plot([3.5,3.5],[-.45,len(MODELS)-.6],color='#B6C4C9',lw=.9)
    fig.text(.17,.96,'Fourteen models. One fixed set of decisions.',fontsize=19,fontweight='semibold',va='top')
    fig.text(.17,.905,'The summary rank changes when the work receives different weights.',fontsize=11,color=MUTED)
    fig.text(.17,.82,'EQUAL DOMAIN WEIGHTS',fontsize=9.5,color='#54717D',fontweight='bold')
    fig.text(.60,.82,'BASE ANSWER AGREEMENT  /  %',fontsize=9.5,color='#54717D',fontweight='bold')
    fig.text(.17,.105,'Policy index = mean of three action tasks. Overall index = mean of policy, legal and science. Whiskers: pointwise paired 95% cluster intervals.',fontsize=9.1,color=MUTED)
    fig.text(.17,.055,'Same 4,905 matched decisions per model. Source annotations and derived NOINFO differ from executable policy correctness; no deployment claim.',fontsize=9.1,color=MUTED)
    return save(fig,'overview')

def domains(data):
    fig,axes=plt.subplots(1,3,figsize=(18.4,10.4))
    for ax,metric,title,subtitle in zip(axes,['policy_action','legal','science'],
        ['01  Executable policy','02  Contract inference','03  Scientific evidence'],
        ['288 actions · 96 each rule','144 source annotations','339 cited claim–abstract pairs']):
        small_bar(ax,data,metric,title,subtitle)
    fig.subplots_adjust(left=.15,right=.985,top=.79,bottom=.15,wspace=.68)
    fig.text(.13,.965,'The lead changes with the domain',fontsize=19,fontweight='semibold',va='top')
    fig.text(.13,.91,'Every panel independently ranks the same fourteen model checkpoints.',fontsize=11,color=MUTED)
    fig.text(.13,.09,'Bars: base correctness / source-label agreement (%). Policy has executable references; legal uses source labels; scientific NOINFO is derived.',fontsize=9.5,color=MUTED)
    fig.text(.13,.045,'Point scores on a fixed reused sample; no shared performance standard for the three reference types.',fontsize=9.1,color=MUTED)
    return save(fig,'domains')

def heads(data):
    fig,axes=plt.subplots(1,3,figsize=(18.4,10.4))
    for ax,metric,title in zip(axes,['action_head','review_head','severity_head'],
        ['01  Action','02  Human review','03  Severity']):
        small_bar(ax,data,metric,title,'288 original policy states · equal rule coverage')
    fig.subplots_adjust(left=.15,right=.985,top=.79,bottom=.15,wspace=.68)
    fig.text(.13,.965,'A decision is more than its final action',fontsize=19,fontweight='semibold',va='top')
    fig.text(.13,.91,'Three typed outputs are evaluated separately on the same policy states.',fontsize=11,color=MUTED)
    fig.text(.13,.09,'Each bar reports strict reference correctness for its own output head, not confidence or a model-internal risk score.',fontsize=9.5,color=MUTED)
    fig.text(.13,.045,'The separate all-three-correct system measure for every model is available in the CSV and Chinese report.',fontsize=9.1,color=MUTED)
    return save(fig,'heads')

def robustness(data):
    fig,axes=plt.subplots(1,2,figsize=(16.2,10.0))
    small_bar(axes[0],data,'natural_reversal','01  Stay correct when form changes',
              'Mean of legal (144) and science (339) joint correctness')
    small_bar(axes[1],data,'policy_counterfactual','02  Switch correctly when facts change',
              'Both actions correct · 288 decisive policy pairs')
    fig.subplots_adjust(left=.17,right=.985,top=.79,bottom=.16,wspace=.56)
    fig.text(.16,.96,'Reliability needs two different tests',fontsize=19,fontweight='semibold',va='top')
    fig.text(.16,.90,'Preserve a correct answer under benign reordering; update a correct action when a decisive fact changes.',fontsize=10.6,color=MUTED)
    fig.text(.16,.095,'Reversal scores use all original pairs, including unavailable output as failure; Qwen also remaps displayed answer codes.',fontsize=9.1,color=MUTED)
    fig.text(.16,.05,'The two bars have different populations and references. Read them as independent rankings, never as an added-up score.',fontsize=9.1,color=MUTED)
    return save(fig,'robustness')

def matched_pairs(data):
    pairs=[('kev_08b','qwen35_08b','0.8B'),('kev_4b','qwen35_4b','4B'),
           ('kev_9b','qwen35_9b','9B*'),('kev_27b','qwen38_27b','27B†')]
    domains=[('policy_action','EXECUTABLE POLICY'),('legal','CONTRACT LABELS'),
             ('science','SCIENTIFIC EVIDENCE')]
    diffs=[[100*(data['models'][kev]['metrics'][metric]['score']-
                 data['models'][qwen]['metrics'][metric]['score'])
            for metric,_ in domains] for kev,qwen,_ in pairs]
    span=max(15,5*np.ceil(max(abs(v) for row in diffs for v in row)/5))
    fig,axes=plt.subplots(1,3,figsize=(17.5,6.5),sharey=True)
    for j,(ax,(_,title)) in enumerate(zip(axes,domains)):
        ax.axvline(0,color=INK,lw=1.25,zorder=2)
        ax.set_xlim(-span*1.17,span*1.17)
        ax.set_ylim(3.6,-.7)
        ax.set_xticks([-span,0,span])
        ax.set_xticklabels([f'−{span:.0f}','0',f'+{span:.0f}'])
        ax.grid(axis='x',color=GRID,lw=.7,zorder=0)
        ax.spines[['top','right','left']].set_visible(False)
        ax.tick_params(axis='y',length=0)
        for i,row in enumerate(diffs):
            d=row[j]
            ax.plot([0,d],[i,i],color=PALETTE['kev_27b'],lw=3,alpha=.48,zorder=3)
            ax.scatter([d],[i],s=120,color=PALETTE['kev_27b'] if d>=0 else '#B36373',
                       edgecolor='white',linewidth=.9,zorder=4)
            offset=1.3 if d>=0 else -1.3
            ax.text(d+offset,i,f'{d:+.1f}',ha='left' if d>=0 else 'right',va='center',
                    fontsize=10.5,fontweight='semibold',color=INK)
        ax.set_title(title,loc='left',fontsize=11,fontweight='semibold',color=INK,pad=16)
        ax.set_xlabel('Kev minus Qwen  /  percentage points',fontsize=9.5,color=MUTED,labelpad=13)
    axes[0].set_yticks(range(4),[label for _,_,label in pairs],fontsize=11.5)
    fig.subplots_adjust(left=.085,right=.985,top=.70,bottom=.25,wspace=.23)
    fig.text(.085,.94,'Same-size contrasts are not the same experiment',fontsize=19,fontweight='semibold',va='top')
    fig.text(.085,.865,'Each dot is a paired-sample difference in the original-condition score; positive values favor Kev.',fontsize=11,color=MUTED)
    fig.text(.085,.79,'Kev-0.8/4/9B vs Qwen3.5; Kev-27B vs Qwen3.8. All pairs share identical requests, but not a common training history.',fontsize=10,color=MUTED)
    fig.text(.085,.125,'* Kev-9B is the earlier pinned checkpoint. † Kev-27B v2 shares an already post-trained Qwen3.8-27B base.',fontsize=9.5,color=MUTED)
    fig.text(.085,.08,'Descriptive differences only: no causal claim about scale, pretraining, or decision-model architecture.',fontsize=9.5,color=MUTED)
    return save(fig,'paired')

def overlap(summary):
    cells=summary['complementarity']['kev_27b-minus-qwen38_27b']
    tasks=[('refund/action','Refund action'),('access/action','Access action'),
           ('routing/action','Routing action'),('contractnli/answer','Contract labels'),
           ('scifact3/answer','Science evidence')]
    parts=[('both_correct','Both correct','#A9CED0'),
           ('kev_only','Kev only','#0D7278'),
           ('qwen_only','Qwen only','#91659A'),
           ('neither_correct','Both wrong','#D9DFE3')]
    fig,ax=plt.subplots(figsize=(15.6,6.8))
    for y,(task,label) in enumerate(tasks):
        cell=cells[task]
        assert sum(cell[key] for key,_,_ in parts)==cell['n']
        left=0
        for key,_,color in parts:
            value=100*cell[key]/cell['n']
            if value:
                ax.barh(y,value,left=left,height=.62,color=color,edgecolor='white',linewidth=1.3)
                if value>=5:
                    ax.text(left+value/2,y,str(cell[key]),ha='center',va='center',
                            fontsize=10,fontweight='semibold',
                            color='white' if key in ('kev_only','qwen_only') else INK)
            left+=value
        ax.text(104,y,f"{100*cell['oracle_upper_bound']:.1f}%",va='center',
                fontsize=11,fontweight='semibold',color=INK)
    ax.set_yticks(range(len(tasks)),[f'{label}   ·   n={cells[task]["n"]}' for task,label in tasks],fontsize=10.5)
    ax.set_ylim(len(tasks)-.6,-.6)
    ax.set_xlim(0,115)
    ax.set_xticks([0,25,50,75,100])
    ax.set_xticklabels(['0%','25%','50%','75%','100%'])
    ax.grid(axis='x',color=GRID,lw=.65,zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y',length=0,pad=9)
    ax.spines[['top','right','left']].set_visible(False)
    fig.subplots_adjust(left=.22,right=.96,top=.68,bottom=.19)
    fig.text(.22,.95,'Equal scores can conceal different mistakes',fontsize=19,
             fontweight='semibold',va='top')
    fig.text(.22,.88,'Kev-27B v2 and Qwen3.8-27B, paired on the same original questions',
             fontsize=11,color=MUTED)
    for j,(_,label,color) in enumerate(parts):
        x=.22+j*.16
        fig.text(x,.76,'■',color=color,fontsize=16,va='center')
        fig.text(x+.019,.76,label,color=INK,fontsize=10,va='center')
    fig.text(.845,.76,'ORACLE CEILING',color=MUTED,fontsize=9,fontweight='bold')
    fig.text(.22,.105,'Numbers inside segments are case counts. Scientific base accuracy is 285/339 for each model, yet each uniquely solves 21 cases.',
             fontsize=9.4,color=MUTED)
    fig.text(.22,.055,'The right column is a retrospective best-of-two upper bound, not a tested selector or deployable routing result.',
             fontsize=9.4,color=MUTED)
    return save(fig,'overlap')

def main():
    data=read(HERE/'scores.json')
    assert data['matched_decisions_per_model']==4905 and len(data['models'])==14
    expansion=ROOT/'research/model_expansion_v2/summary.json'
    assert sha(expansion)==data['source_sha256']['model_expansion_v2_summary.json']
    outputs={}
    for name,fn in [('overview',overview),('domains',domains),('heads',heads),
                    ('robustness',robustness),('paired',matched_pairs)]:
        outputs[name]={p.name:sha(p) for p in fn(data)}
    outputs['overlap']={p.name:sha(p) for p in overlap(read(expansion))}
    manifest=dict(scores_sha256=sha(HERE/'scores.json'),generator_sha256=sha(Path(__file__)),
                  output_files_sha256=outputs,
                  scope='Six source-backed PDF/SVG/PNG figures; ranked panels, matched-size contrasts and error overlap')
    write(HERE/'figure_manifest.json',manifest)
    print('RENDERED',list(outputs),flush=True)

if __name__=='__main__':
    main()
