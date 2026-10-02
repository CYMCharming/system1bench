"""Publication-ready static rankings; every mark derives from scores.json."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'research/leaderboard_v1'
OUT=ROOT/'paper/figures'
sys.path.insert(0,str(HERE))
from build import LABELS,MODELS,read,sha,write

INK='#183444'
MUTED='#627884'
GRID='#E2E9E9'
PALETTE={'jev-1.13.0':'#183A55','kev_08b':'#187D84','kev_4b':'#187D84',
         'kev_9b':'#187D84','nanojev':'#BE8950','english':'#7792A0',
         'multilingual':'#7792A0','llama31_8b_instruct':'#986291',
         'qwen3_8b':'#986291','qwen35_9b':'#986291'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'axes.edgecolor':'#A3B2B9',
    'axes.linewidth':.7,'text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,
    'ytick.color':INK,'figure.facecolor':'white','savefig.facecolor':'white',
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})

def mix(color,amount):
    return tuple((1-amount)*np.ones(3)+amount*np.array(to_rgb(color)))

def setup(ax,n=10):
    ax.spines[['top','right','left']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='x',color=GRID,lw=.7)
    ax.tick_params(axis='y',length=0,pad=6)
    ax.tick_params(axis='x',length=3,width=.7)
    ax.set_ylim(n-.5,-.5)

def save(fig,name):
    paths=[]
    for ext in ('pdf','svg','png'):
        path=OUT/(name+'.'+ext)
        fig.savefig(path,dpi=320,bbox_inches='tight',pad_inches=.13)
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
    ax.barh(range(10),[100]*10,height=.58,color='#F0F4F4',zorder=1)
    for y,(model,value) in enumerate(zip(order,values)):
        ax.barh(y,value,height=.58,color=PALETTE[model],zorder=2)
        ax.text(min(value+2,103),y,f'{value:.1f}',va='center',fontsize=9.3,
                fontweight='semibold' if y==0 else 'normal',color=INK,zorder=4)
    ax.set_xlim(0,116)
    ax.set_xticks([0,25,50,75,100])
    ax.set_yticks(range(10),[f"{data['rankings'][metric][m]:>2}.  {LABELS[m]}" if show_rank
                               else LABELS[m] for m in order],fontsize=8.5)
    ax.set_title(title,loc='left',fontsize=13,fontweight='semibold',pad=23,color=INK)
    ax.text(0,1.025,subtitle,transform=ax.transAxes,fontsize=9,color=MUTED,va='bottom')
    setup(ax)

def overview(data):
    order=rows(data,'overall_domain_equal')
    fig=plt.figure(figsize=(16.8,7.6))
    axes=fig.add_gridspec(1,2,width_ratios=[1.07,1.23],left=.16,right=.985,top=.73,bottom=.19,wspace=.18)
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
    ax.set_yticks(range(10),[f"{data['rankings']['overall_domain_equal'][m]:>2}.  {LABELS[m]}" for m in order],fontsize=10)
    ax.set_title('Three-domain index / 100',loc='left',fontsize=13,fontweight='semibold',pad=18)
    setup(ax)
    mat.set_xlim(-.55,4.55)
    mat.set_ylim(9.5,-.5)
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
    mat.plot([2.5,2.5],[-.45,9.4],color='#B6C4C9',lw=.9)
    mat.plot([3.5,3.5],[-.45,9.4],color='#B6C4C9',lw=.9)
    fig.text(.16,.96,'Ten models. One fixed set of decisions.',fontsize=19,fontweight='semibold',va='top')
    fig.text(.16,.895,'The summary rank changes when the work receives different weights.',fontsize=11,color=MUTED)
    fig.text(.16,.81,'EQUAL DOMAIN WEIGHTS',fontsize=9.5,color='#54717D',fontweight='bold')
    fig.text(.595,.81,'BASE ANSWER AGREEMENT  /  %',fontsize=9.5,color='#54717D',fontweight='bold')
    fig.text(.16,.115,'Policy index = mean of three action tasks. Overall index = mean of policy, legal and science. Whiskers: pointwise paired 95% cluster intervals.',fontsize=9.1,color=MUTED)
    fig.text(.16,.055,'Same 4,905 matched decisions per model. Source annotations and derived NOINFO differ from executable policy correctness; no deployment claim.',fontsize=9.1,color=MUTED)
    return save(fig,'fig_leaderboard_overview')

def domains(data):
    fig,axes=plt.subplots(1,3,figsize=(17.2,8.2))
    for ax,metric,title,subtitle in zip(axes,['policy_action','legal','science'],
        ['01  Executable policy','02  Contract inference','03  Scientific evidence'],
        ['288 actions · 96 each rule','144 source annotations','339 cited claim–abstract pairs']):
        small_bar(ax,data,metric,title,subtitle)
    fig.subplots_adjust(left=.13,right=.985,top=.75,bottom=.18,wspace=.67)
    fig.text(.13,.965,'The lead changes with the domain',fontsize=19,fontweight='semibold',va='top')
    fig.text(.13,.91,'Every panel independently ranks the same ten model checkpoints.',fontsize=11,color=MUTED)
    fig.text(.13,.09,'Bars: base correctness / source-label agreement (%). Policy has executable references; legal uses source labels; scientific NOINFO is derived.',fontsize=9.5,color=MUTED)
    fig.text(.13,.045,'Point scores on a fixed reused sample; no shared performance standard for the three reference types.',fontsize=9.1,color=MUTED)
    return save(fig,'fig_leaderboard_domains')

def heads(data):
    fig,axes=plt.subplots(1,3,figsize=(17.2,8.2))
    for ax,metric,title in zip(axes,['action_head','review_head','severity_head'],
        ['01  Action','02  Human review','03  Severity']):
        small_bar(ax,data,metric,title,'288 original policy states · equal rule coverage')
    fig.subplots_adjust(left=.13,right=.985,top=.75,bottom=.18,wspace=.67)
    fig.text(.13,.965,'A decision is more than its final action',fontsize=19,fontweight='semibold',va='top')
    fig.text(.13,.91,'Three typed outputs are evaluated separately on the same policy states.',fontsize=11,color=MUTED)
    fig.text(.13,.09,'Each bar reports strict reference correctness for its own output head, not confidence or a model-internal risk score.',fontsize=9.5,color=MUTED)
    fig.text(.13,.045,'The separate all-three-correct system measure for every model is available in the CSV and Chinese report.',fontsize=9.1,color=MUTED)
    return save(fig,'fig_leaderboard_heads')

def robustness(data):
    fig,axes=plt.subplots(1,2,figsize=(14.8,7.8))
    small_bar(axes[0],data,'natural_reversal','01  Stay correct when form changes',
              'Mean of legal (144) and science (339) joint correctness')
    small_bar(axes[1],data,'policy_counterfactual','02  Switch correctly when facts change',
              'Both actions correct · 288 decisive policy pairs')
    fig.subplots_adjust(left=.16,right=.985,top=.74,bottom=.19,wspace=.56)
    fig.text(.16,.96,'Reliability needs two different tests',fontsize=19,fontweight='semibold',va='top')
    fig.text(.16,.90,'Preserve a correct answer under benign reordering; update a correct action when a decisive fact changes.',fontsize=10.6,color=MUTED)
    fig.text(.16,.095,'Reversal scores use all original pairs, including unavailable output as failure; Qwen also remaps displayed answer codes.',fontsize=9.1,color=MUTED)
    fig.text(.16,.05,'The two bars have different populations and references. Read them as independent rankings, never as an added-up score.',fontsize=9.1,color=MUTED)
    return save(fig,'fig_leaderboard_robustness')

def main():
    data=read(HERE/'scores.json')
    assert data['matched_decisions_per_model']==4905 and len(data['models'])==10
    outputs={}
    for name,fn in [('overview',overview),('domains',domains),('heads',heads),('robustness',robustness)]:
        outputs[name]={p.name:sha(p) for p in fn(data)}
    manifest=dict(scores_sha256=sha(HERE/'scores.json'),generator_sha256=sha(Path(__file__)),
                  output_files_sha256=outputs,
                  scope='Four source-backed PDF/SVG/PNG figures; independently ranked panels; no invented rows')
    write(HERE/'figure_manifest.json',manifest)
    print('RENDERED',list(outputs),flush=True)

if __name__=='__main__':
    main()
