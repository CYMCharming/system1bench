"""Paper-ready source-backed vector figures. No illustrative or invented scores."""
import os
from pathlib import Path
import sys
os.environ['SOURCE_DATE_EPOCH']='1791072000'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.startlux_transfer_v1.analyze import LABELS as TRANSFER_LABELS,TASKS
from research.startlux_transfer_v1.run import read,save
from research.leaderboard_v3.build import LABELS,MODELS
from system1bench.common import sha

HERE=Path(__file__).resolve().parent
OUT=ROOT/'paper/figures'
INK='#183444';MUTED='#627884';GRID='#E2E9E9'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'text.color':INK,'axes.labelcolor':INK,
 'axes.edgecolor':'#A3B2B9','xtick.color':MUTED,'ytick.color':INK,'axes.linewidth':.7,
 'figure.facecolor':'white','savefig.facecolor':'white','pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
 'svg.hashsalt':'system1bench-v3'})
COLORS=LinearSegmentedColormap.from_list('evidence',['#F3F6F7','#C6DCE3','#6696A9','#244E64'])

def color(m):
    if m.startswith(('startlux','intern')): return '#2D6688'
    if m.startswith('kev'): return '#177D7D'
    if m.startswith(('qwen','llama')): return '#896490'
    if m.startswith('jev'): return '#263F55'
    return '#7893A1'

def short(m,mark_training=True):
    label=LABELS.get(m,TRANSFER_LABELS.get(m,m)).replace('StartLux-Decision','StartLux').replace('Intern-Decision','Intern').replace(' (earlier release)','').replace(' (direct)','')
    return label+(' †' if mark_training and m.startswith('startlux') else '')

def frame(ax,n):
    ax.spines[['top','right','left']].set_visible(False)
    ax.set_axisbelow(True);ax.grid(axis='x',color=GRID,lw=.7)
    ax.tick_params(axis='y',length=0,pad=7)
    ax.set_ylim(n-.55,-.55)

def title(fig,title,subtitle):
    fig.text(.02,.965,title,fontsize=22,fontweight='semibold',va='top')
    fig.text(.02,.918,subtitle,fontsize=11,color=MUTED,va='top')

def export(fig,stem):
    paths={};OUT.mkdir(parents=True,exist_ok=True)
    for ext in ('svg','pdf','png'):
        path=OUT/(stem+'.'+ext)
        fig.savefig(path,dpi=320,bbox_inches='tight',pad_inches=.17,
                    metadata={'Date':'2026-10-04'} if ext=='svg' else None)
        paths[path.name]=sha(path)
    plt.close(fig);return paths

def bars(ax,order,cells,percentage=True,axis_max=None,mark_training=True):
    factor=100 if percentage else 1
    xmax=100 if percentage else max(.2,.1*np.ceil(max(factor*cells[m]['ci95'][1] if cells[m].get('ci95') else factor*cells[m]['score'] for m in order)/.1))
    if axis_max is not None:xmax=axis_max
    for i,m in enumerate(order):
        value=factor*cells[m]['score']
        ax.barh(i,value,height=.48,color=color(m),zorder=2)
        if cells[m].get('ci95'):
            lo,hi=[factor*x for x in cells[m]['ci95']]
            ax.errorbar(value,i,xerr=[[max(0,value-lo)],[max(0,hi-value)]],fmt='o',color=INK,
                        ms=2.6,elinewidth=.9,capsize=2,zorder=3)
        label=f'{value:.1f}' if percentage else f'{value:.3f}'
        ax.text(xmax*1.035,i,label,va='center',fontsize=10,fontweight='semibold')
    ax.set_xlim(0,xmax*1.17)
    ax.set_xticks(np.arange(0,xmax+1e-12,5) if percentage and xmax!=100 else np.linspace(0,xmax,5))
    ax.set_yticks(range(len(order)),[short(m,mark_training) for m in order],fontsize=10)
    frame(ax,len(order))

def overview(data):
    metric='overall_domain_equal'
    order=sorted(MODELS,key=lambda m:(data['rankings'][metric][m],MODELS.index(m)))
    fig=plt.figure(figsize=(18.5,12))
    gs=fig.add_gridspec(1,2,width_ratios=[1.1,1],left=.19,right=.98,top=.82,bottom=.17,wspace=.21)
    ax=fig.add_subplot(gs[0,0]);mat=fig.add_subplot(gs[0,1])
    bars(ax,order,{m:data['models'][m]['metrics'][metric] for m in order})
    ax.set_yticklabels([f"{data['rankings'][metric][m]:>2}.  {short(m)}" for m in order])
    ax.set_title('DOMAIN-EQUAL INDEX',loc='left',fontsize=12,fontweight='semibold',pad=22)
    matrix=np.array([[100*data['models'][m]['metrics'][t]['score'] for t in ('policy_action','legal','science')] for m in order])
    mat.imshow(matrix,aspect='auto',cmap=COLORS,vmin=0,vmax=100)
    for i in range(len(order)):
        for j in range(3):
            rgb=COLORS(matrix[i,j]/100)[:3]
            linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            lum=sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))
            mat.text(j,i,f'{matrix[i,j]:.1f}',ha='center',va='center',fontsize=11,
                     color='white' if lum<.179 else '#000000',fontweight='semibold')
    mat.set_xticks(range(3),['Policy action\nn=288','Contract labels †\nn=144','Science evidence\nn=339'],fontsize=10)
    mat.xaxis.tick_top();mat.tick_params(length=0,pad=13);mat.set_yticks([])
    mat.spines[:].set_visible(False)
    mat.set_xticks(np.arange(-.5,3,.999999),minor=True);mat.set_yticks(np.arange(-.5,len(order),1),minor=True)
    mat.grid(which='minor',color='white',linewidth=2);mat.tick_params(which='minor',length=0)
    title(fig,'Eighteen models. Identical decisions.',
          '4,905 decisions per model, including repeated and paired conditions. Historical runs are reused; no new tasks enter the index.')
    fig.text(.19,.105,'Index = (policy + contract + science) / 3. Pointwise 95% paired-cluster bootstrap intervals; overlapping intervals are not a significance test.',fontsize=10,color=MUTED)
    fig.text(.19,.071,'† StartLux declares ContractNLI train-split use. Contract/science measure source-label agreement; scientific NOINFO lacks independent adjudication.',fontsize=10,color=MUTED)
    fig.text(.19,.036,'Direct Qwen/LLM inference, no thinking. Heterogeneous training histories do not isolate architecture or scale. Exact counts: rankings.csv.',fontsize=10,color=MUTED)
    return export(fig,'fig_leaderboard_v3_overview')

def domains(data):
    fig,axes=plt.subplots(1,3,figsize=(24,12))
    fig.subplots_adjust(left=.12,right=.98,top=.81,bottom=.16,wspace=.64)
    for ax,metric,name,n in zip(axes,('policy_action','legal','science'),('Policy action','Contract labels †','Science evidence'),(288,144,339)):
        order=sorted(MODELS,key=lambda m:(data['rankings'][metric][m],MODELS.index(m)))
        bars(ax,order,{m:data['models'][m]['metrics'][metric] for m in order})
        ax.set_title(f'{name}  |  n={n}',loc='left',fontsize=14,fontweight='semibold',pad=20)
    title(fig,'One overall score does not identify the best domain model.','Each panel is independently ranked on the same original cases. Values are percentages; no latency or confidence weighting.')
    fig.text(.12,.085,'Policy labels are executable; contract/science are source-reference agreements. † Declared ContractNLI train exposure for StartLux.',fontsize=11,color=MUTED)
    fig.text(.12,.043,'These panels reuse the identical main requests. New causal, code, financial and tool-use tasks appear in a separate transfer panel.',fontsize=11,color=MUTED)
    return export(fig,'fig_leaderboard_v3_domains')

def transfer_domains(data):
    assert data['complete']
    cohort=data['cohort']
    fig,axes=plt.subplots(2,2,figsize=(20,15))
    fig.subplots_adjust(left=.17,right=.98,top=.85,bottom=.12,wspace=.55,hspace=.38)
    names=('Causal judgments | n=144','Python output choice | n=128','Financial entity sentiment | n=128','Tool-use timing | n=128')
    for ax,t,name in zip(axes.flat,TASKS,names):
        cells={m:data['transfer'][m]['metrics'][t]['original'] for m in cohort}
        order=sorted(cohort,key=lambda m:(-cells[m]['score'],cohort.index(m)))
        bars(ax,order,cells,mark_training=False);ax.set_title(name,loc='left',fontsize=15,fontweight='semibold',pad=18)
    title(fig,'Decision transfer, separated by task.','Fixed 13-model cohort. Original-case accuracy with pointwise 95% source-cluster intervals. Candidate-order robustness is reported separately.')
    fig.text(.17,.07,'Code: output-choice adaptation, not CRUXEval-O/pass@1. Finance: supplied-span classification. Tools: three gold classes, four candidates; no direct positives.',fontsize=10,color=MUTED)
    fig.text(.17,.035,'Focused samples; not Decision Index reproduction or end-to-end agent evaluation. † Training-overlap disclosures accompany the main legal panel.',fontsize=10,color=MUTED)
    return export(fig,'fig_transfer_v1_domains')

def probability(data):
    cohort=data['cohort'];fig,axes=plt.subplots(1,2,figsize=(20,10))
    fig.subplots_adjust(left=.16,right=.98,top=.8,bottom=.19,wspace=.51)
    for ax,metric,name,percent in zip(axes,('excess_brier','impossible_mass'),
                                    ('Excess Brier loss','Probability assigned to impossible outcomes'),(False,True)):
        cells={m:data['transfer'][m]['metrics']['known_distribution'][metric] for m in cohort}
        order=sorted(cohort,key=lambda m:(cells[m]['score'],cohort.index(m)))
        mass_max=5*np.ceil(max(cells[m]['ci95'][1]*100 for m in order)/5) if percent else None
        bars(ax,order,cells,percentage=percent,axis_max=mass_max,mark_training=False)
        ax.set_yticklabels([short(m,False)+(f" [{data['transfer'][m]['metrics']['known_distribution']['valid']}/96]"
            if data['transfer'][m]['metrics']['known_distribution']['valid']!=96 else '') for m in order])
        if metric=='excess_brier':
            ref=data['transfer'][cohort[0]]['metrics']['known_distribution']['uniform_all_candidates']['excess_brier']['score']
            ax.axvline(ref,color=INK,lw=.9,ls='--',zorder=1)
            ax.text(.98,1.01,f'Uniform / no evidence: {ref:.3f}',transform=ax.transAxes,ha='right',fontsize=9,color=MUTED)
        ax.set_title(name+'  ↓',loc='left',fontsize=14,fontweight='semibold',pad=21)
        ax.set_xlabel('Lower is better'+('  ·  % probability mass' if percent else '  ·  sum (predicted − exact)²'),labelpad=15)
    title(fig,'Default distributions versus exact event probabilities.','96 exact-probability cases, 48 paired settings. Not single-outcome accuracy, not correctness-confidence calibration; no fitting on test probabilities.')
    fig.text(.16,.11,'Reference probabilities are checked as exact fractions. Error bars: 95% paired-setting bootstrap intervals. Invalid outputs are reported with valid denominators.',fontsize=10,color=MUTED)
    fig.text(.16,.063,'This small diagnostic comes from the Intern repository; it is not an independent broad probability benchmark or evidence of general decision competence.',fontsize=10,color=MUTED)
    return export(fig,'fig_transfer_v1_probability')

def paper_panels(main_data,transfer):
    """Individual panels remain legible at a normal two-column paper width."""
    outputs={}
    specs=[(key,name,f'n={n} original cases',main_data['models'],'main') for key,name,n in
           [('policy_action','Policy action',288),('legal','Contract reference agreement',144),('science','Science reference agreement',339)]]
    specs += [(key,name,f'n={n} original cases',transfer['transfer'],'transfer') for key,name,n in
              [('cladder','Causal judgments',144),('cruxeval','Python output choice',128),
               ('finentity','Financial entity sentiment',128),('when2call','Tool-use timing',128)]]
    specs += [(key,name,'96 cases / 48 paired settings',transfer['transfer'],'pilot') for key,name in
              [('excess_brier','Excess Brier loss'),('impossible_mass','Impossible-outcome probability')]]
    for key,name,scope,models,track in specs:
        cohort=list(models)
        if track=='main': cells={m:models[m]['metrics'][key] for m in cohort}
        elif track=='transfer': cells={m:models[m]['metrics'][key]['original'] for m in cohort}
        else: cells={m:models[m]['metrics']['known_distribution'][key] for m in cohort}
        order=sorted(cohort,key=lambda m:(cells[m]['score'] if track=='pilot' else -cells[m]['score'],cohort.index(m)))
        fig,ax=plt.subplots(figsize=(7.2,8.5 if track=='main' else 6.9))
        fig.subplots_adjust(left=.3,right=.98,top=.83,bottom=.17)
        mass_max=5*np.ceil(max(cells[m]['ci95'][1]*100 for m in order)/5) if key=='impossible_mass' else None
        bars(ax,order,cells,percentage=key!='excess_brier',axis_max=mass_max,mark_training=track=='main')
        fig.text(.035,.965,name+('  ↓' if track=='pilot' else ''),fontsize=17,fontweight='semibold',va='top')
        fig.text(.035,.914,scope+(' · lower is better' if track=='pilot' else ' · %'),fontsize=10,color=MUTED)
        if track=='main': note='† StartLux declares ContractNLI train exposure.\nSame main requests; no new tasks in the composite index.'
        elif track=='transfer': note='Focused adaptation, not native benchmark reproduction.\n95% source-cluster intervals; see exact counts and source caveats.'
        else: note='Exact-fraction references; 95% paired-setting intervals.\nVendor-authored diagnostic; default candidate-distribution semantics.'
        fig.text(.3,.082,note,fontsize=8.5,color=MUTED,linespacing=1.6)
        stem=('fig_leaderboard_v3_paper_' if track=='main' else 'fig_transfer_v1_paper_')+key
        outputs.update(export(fig,stem))
    return outputs

def tool_classes(data):
    cohort=data['cohort'];task='when2call'
    order=sorted(cohort,key=lambda m:-data['transfer'][m]['metrics'][task]['original']['score'])
    classes=('cannot_answer','request_for_info','tool_call')
    matrix=np.array([[100*data['transfer'][m]['metrics'][task]['strata'][c]['score'] for c in classes]+
                     [100*data['transfer'][m]['metrics'][task]['original']['score']] for m in order])
    fig,ax=plt.subplots(figsize=(10.5,9))
    fig.subplots_adjust(left=.26,right=.97,top=.78,bottom=.17)
    ax.imshow(matrix,aspect='auto',cmap=COLORS,vmin=0,vmax=100)
    for i,m in enumerate(order):
        cells=[data['transfer'][m]['metrics'][task]['strata'][c] for c in classes]+[data['transfer'][m]['metrics'][task]['original']]
        for j,c in enumerate(cells):
            rgb=COLORS(matrix[i,j]/100)[:3]
            linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            lum=sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))
            ax.text(j,i,f"{matrix[i,j]:.1f}%\n{c['correct']}/{c['n']}",ha='center',va='center',
                    color='white' if lum<.179 else '#000000',fontsize=10)
    ax.set_xticks(range(4),['Cannot answer\nn=43','Ask for information\nn=42','Call a tool\nn=43','Overall accuracy\nn=128'])
    ax.xaxis.tick_top();ax.tick_params(length=0,pad=12)
    ax.set_yticks(range(len(order)),[short(m,False) for m in order])
    ax.set_xticks(np.arange(-.5,4,1),minor=True);ax.set_yticks(np.arange(-.5,len(order),1),minor=True)
    ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',length=0)
    ax.spines[:].set_visible(False)
    title(fig,'Knowing how to act is not knowing when to stop.','Original When2Call cases: class recall, exact counts and overall accuracy. Same 128 problems for every model.')
    fig.text(.26,.097,'Four response candidates, but only three gold classes in this test source.\nNo direct-answer positives: no direct-answer recall or end-to-end agent claim.',fontsize=10,color=MUTED,linespacing=1.6)
    return export(fig,'fig_transfer_v1_tool_classes')

def main():
    main_data=read(HERE/'scores.json');transfer=read(ROOT/'research/startlux_transfer_v1/summary.json')
    assert len(main_data['models'])==18 and transfer['complete']
    outputs={}
    for name,fn,data in [('overview',overview,main_data),('domains',domains,main_data),
                         ('transfer',transfer_domains,transfer),('probability',probability,transfer),('tool_classes',tool_classes,transfer)]:
        outputs[name]=fn(data)
    outputs['paper_sized_panels']=paper_panels(main_data,transfer)
    save(HERE/'figure_manifest.json',dict(generator_sha256=sha(__file__),scores_sha256=sha(HERE/'scores.json'),
         transfer_sha256=sha(ROOT/'research/startlux_transfer_v1/summary.json'),outputs=outputs))
    print('RENDERED',list(outputs))

if __name__=='__main__': main()
