"""Five source-backed, editable paper figures inspired by T2AV-Compass Fig. 1.

No reference pixels, logos, scores, or captions are copied into the artwork.
"""
import csv
import hashlib
import json
import os
from pathlib import Path

os.environ['SOURCE_DATE_EPOCH'] = '1791504000'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Patch, Wedge
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/'paper/figures/compass_v1'
INK = '#26334D'
MUTED = '#738092'
GRID = '#E4E8ED'
MODELS = ['kev_27b','jev-1.13.0','qwen38_27b','kev_9b','qwen35_9b','llama31_8b_instruct']
PALETTE = ['#74AA97','#7989CC','#DFAC83','#9B8AC0','#7EA9C5','#BBBAB8']
HATCHES = ['', '///', '\\\\', '..', 'xx', '--']
DOMAIN_LABELS = ['Policy','Legal','Science','Causal','Code','Finance','Tools','Intent']
DOMAIN_KEYS = ['policy','legal','science','causal','code','finance','tools','intent']
TASK_LABELS = {'clinc150_full':'CLINC150 + OOS','banking77_full':'BANKING77',
               'science':'SciFact3','cladder':'CLadder','when2call':'When2Call','legal':'ContractNLI'}
TASK_COLORS = dict(zip(TASK_LABELS,['#A6B6DD','#A5CCC0','#D8B49A','#BEB0D1','#A6BFCD','#C9C6C0']))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':INK,
    'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':INK,'axes.edgecolor':GRID,
    'axes.linewidth':.7,'figure.facecolor':'white','savefig.facecolor':'white',
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'system1bench-compass-v1'})


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blossom(fig):
    # Quiet research-figure corner marker, always anchored in header space.
    ax = fig.add_axes([.946,.929,.028,.035])
    ax.set_aspect('equal'); ax.axis('off')
    for x,y in [(0,.28),(.28,0),(0,-.28),(-.28,0)]:
        ax.add_patch(Circle((x,y),.2,color='#C5C5D8',lw=0))
    ax.set_xlim(-.6,.6);ax.set_ylim(-.6,.6)


def header(fig, letter, title, subtitle='', compact=False):
    size = 9 if compact else 22
    transform=fig.transSubfigure if isinstance(fig,matplotlib.figure.SubFigure) else fig.transFigure
    fig.text(.035,.955,f'({letter})  {title}',fontsize=size,fontweight='semibold',va='top',transform=transform)
    if subtitle and not compact:
        fig.text(.035,.9,subtitle,fontsize=11,color=MUTED,va='top')
        blossom(fig)


def note(fig, text, compact=False):
    if not compact:
        fig.text(.035,.03,text,fontsize=9,color=MUTED,va='bottom',linespacing=1.7)


def radial(fig, scores, compact=False):
    header(fig,'a','Decision profiles','Six representative models across the same eight domains.',compact)
    ax = fig.add_axes([.04,.20 if not compact else .13,.92,.64 if not compact else .75],projection='polar')
    ax.set_theta_zero_location('N');ax.set_theta_direction(-1)
    ax.set_ylim(0,1.84);ax.axis('off')
    inner,span = .45,.91
    width = .076
    for domain_index, domain in enumerate(DOMAIN_KEYS):
        center = domain_index*2*np.pi/8
        angles = center+(np.arange(len(MODELS))-(len(MODELS)-1)/2)*width
        guide = np.linspace(center-.26,center+.26,80)
        for value in (25,50,75,100):
            ax.plot(guide,np.full_like(guide,inner+span*value/100),color=GRID,lw=.5,zorder=0)
        for idx,model in enumerate(MODELS):
            value = scores['models'][model]['domain_scores'][domain]['score']*100
            ax.bar(angles[idx],span*value/100,bottom=inner,width=width*.91,
                   color=PALETTE[idx],edgecolor='white',linewidth=.55,hatch=HATCHES[idx],zorder=2)
            if not compact:
                deg = np.degrees(angles[idx]) % 360
                rotation = 90-deg
                if rotation < -90:
                    rotation += 180
                if rotation > 90:
                    rotation -= 180
                ax.text(angles[idx],inner+span*value/100+.035,f'{value:.1f}',fontsize=7.2,
                        ha='center',va='center',rotation=rotation,rotation_mode='anchor')
        ax.text(center,1.63,DOMAIN_LABELS[domain_index],ha='center',va='center',
                fontsize=6.8 if compact else 12,fontweight='medium')
    ax.add_patch(Circle((0,0),inner*.84,transform=ax.transData._b,color='white',ec=GRID,lw=.9,zorder=5))
    ax.text(0,0,'S1',ha='center',va='center',fontsize=16 if compact else 25,fontweight='bold',zorder=6)
    ax.text(.5,.447,'BENCH',transform=ax.transAxes,ha='center',va='center',fontsize=5.4 if compact else 9,color=MUTED,zorder=6)
    labels = ['Kev-27B v2','Jev API','Qwen3.8-27B','Kev-9B','Qwen3.5-9B','Llama-3.1-8B']
    handles = [Patch(facecolor=c,edgecolor='white',hatch=h,label=l) for c,h,l in zip(PALETTE,HATCHES,labels)]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.51,.12 if not compact else .02),
               ncol=3,frameon=False,fontsize=6 if compact else 10,handlelength=1.5,columnspacing=1.3)
    note(fig,'Radial length = domain accuracy, 0-100; every sector has the same scale.\nPoint estimates only; no significance claim. Full 17-model values are supplied separately.',compact)


def densities(fig, stats, compact=False):
    header(fig,'b','Input length distribution','Common tokenizer; every candidate is retained.',compact)
    ax = fig.add_axes([.13,.23,.82,.58 if not compact else .6])
    groups = [('Policy',['refund','access','routing'],'#91B9AC'),
              ('Evidence + reasoning',['legal','science','cladder','cruxeval','finentity','when2call'],'#8CA6CE'),
              ('Intent',['clinc150_full','banking77_full'],'#D9A98C')]
    grid = np.linspace(0,5,600)
    bandwidth = .12
    summaries = []
    for (name,tasks,color),linestyle in zip(groups,['solid','dashed','dashdot']):
        values = np.concatenate([stats['tasks'][t]['reference_token_lengths'] for t in tasks])
        logged = np.log10(values)
        density = np.exp(-.5*((grid[:,None]-logged)/bandwidth)**2).mean(axis=1)/(bandwidth*np.sqrt(2*np.pi))
        ax.fill_between(grid,density,color=color,alpha=.32,lw=0)
        ax.plot(grid,density,color=color,lw=1.2 if compact else 2,linestyle=linestyle,label=f'{name} (n={len(values):,})')
        summaries.append(dict(group=name,n=len(values),median=float(np.median(values)),min=int(min(values)),max=int(max(values))))
    ax.set_xlim(1.4,4.1)
    ax.set_ylim(bottom=0)
    ax.set_xticks([np.log10(30),2,np.log10(300),3,np.log10(3000),4],['30','100','300','1k','3k','10k'])
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color=GRID,lw=.65);ax.set_axisbelow(True)
    ax.set_xlabel('Reference input tokens',fontsize=6.8 if compact else 12)
    ax.set_ylabel('Density / log10 token',fontsize=6.5 if compact else 11)
    ax.tick_params(labelsize=6 if compact else 10,length=3)
    ax.legend(frameon=False,fontsize=5.6 if compact else 10,loc='upper right')
    note(fig,'Log-scaled x axis; densities normalized within each group. Gaussian bandwidth = 0.12 log10 units.\nCompact gold-free state + target question JSON, Qwen3.8 tokenizer; not native/server token cost.',compact)
    return summaries


def bar_axes(fig, compact):
    ax = fig.add_axes([.27,.24,.65,.59 if not compact else .59])
    ax.set_xlim(0,108);ax.set_ylim(5.7,-.8)
    ax.set_xticks([0,25,50,75,100],['0','25','50','75','100'])
    ax.spines[['top','right','left']].set_visible(False)
    ax.grid(axis='x',color=GRID,lw=.65);ax.set_axisbelow(True)
    ax.tick_params(axis='y',length=0,pad=8,labelsize=6.6 if compact else 11)
    ax.tick_params(axis='x',labelsize=6 if compact else 10,length=3)
    return ax


def diversity(fig, stats, compact=False):
    header(fig,'c','Query-text deduplication retention','Question text only; not whole-dataset diversity.',compact)
    ax = bar_axes(fig,compact)
    semantic = stats['semantic_queries']
    order = sorted(semantic,key=lambda t:-semantic[t]['retained']['0.8'])
    for i,task in enumerate(order):
        row=semantic[task];value=100*row['retained']['0.8']/row['n']
        ax.barh(i,100,height=.6,color='#F3F4F6',zorder=1)
        ax.barh(i,value,height=.6,color=TASK_COLORS[task],edgecolor='white',lw=.7,zorder=2)
        low,high=[100*row['retained'][str(t)]/row['n'] for t in (.75,.85)]
        ax.plot([low,high],[i,i],color=INK,lw=.8,zorder=3)
        ax.plot([low,high],[i,i],linestyle='',marker='|',color=INK,markersize=6,zorder=3)
        ax.plot(value,i,'o',color=INK,ms=2.8,zorder=4)
        ax.text(102,i,f'{value:.1f}',va='center',ha='left',fontsize=6.8 if compact else 11,fontweight='medium')
    ax.set_yticks(range(6),[TASK_LABELS[t] for t in order])
    ax.set_xlabel('Queries retained after deduplication (%)',fontsize=6.8 if compact else 11)
    note(fig,'128 hash-selected queries per task. MiniLM cosine threshold = 0.80; deterministic greedy retention.\nLines show threshold sensitivity (0.75-0.85), NOT confidence intervals. Query-only proxy, not difficulty.\nContractNLI reuses hypothesis sentences; evidence is excluded, so this is NOT whole-corpus diversity.',compact)
    return order


def balance(fig, stats, compact=False):
    header(fig,'d','Reference-label balance','Declared label space, including labels with zero support.',compact)
    ax = bar_axes(fig,compact)
    order = sorted(stats['semantic_queries'],key=lambda t:-stats['semantic_queries'][t]['retained']['0.8'])
    for i,task in enumerate(order):
        row=stats['tasks'][task];value=row['normalized_label_entropy']*100
        ax.barh(i,100,height=.6,color='#F3F4F6',zorder=1)
        ax.barh(i,value,height=.6,color=TASK_COLORS[task],edgecolor='white',lw=.7,zorder=2)
        ax.text(102,i,f'{value:.1f}',va='center',ha='left',fontsize=6.8 if compact else 11,fontweight='medium')
    if compact:
        labels=[TASK_LABELS[t] for t in order]
    else:
        labels=[f"{TASK_LABELS[t]}\n{stats['tasks'][t]['observed_classes']}/{stats['tasks'][t]['candidate_count']} labels; n={stats['tasks'][t]['n']:,}" for t in order]
    ax.set_yticks(range(6),labels)
    ax.set_xlabel('Normalized reference-label entropy (%)',fontsize=6.8 if compact else 11)
    note(fig,'100 x H(gold labels) / log(K), using every original scored case and the complete K-choice ontology.\nBalance is not accuracy. When2Call has 3/4 observed labels; CLINC includes 1,000 OOS examples.',compact)


def taxonomy_tree():
    return [
        ('Classification','#91B3BD',[
            ('Policy','#A4C6B5',['Refund','Access','Routing']),
            ('Legal','#C5B3D9',['ContractNLI']),
            ('Science','#B9C7DB',['SciFact3']),
            ('Causal','#DCC0A4',['CLadder']),
            ('Code','#B3CDD0',['CRUXEval']),
            ('Finance','#CDC3A7',['FinEntity']),
            ('Tools','#C7B5C8',['When2Call']),
            ('Intent','#A7B7D3',['CLINC150','BANKING77'])]),
        ('Diagnostics','#CFBFC7',[
            ('Invariance','#B7B9D1',['Repeat','Option order','Paraphrase']),
            ('Responsiveness','#D6B6A4',['Counterfactual']),
            ('Joint decision','#AFC6C0',['All heads']),
            ('Probability','#CAB9D8',['Brier','NLL','Total variation']),
            ('Efficiency','#D5C79E',['p50 latency','p95 latency','Throughput'])])]


def sector_label(ax,start,end,radius,label,fontsize,weight='normal'):
    middle=(start+end)/2
    rad=np.radians(middle)
    # Tangential text is flipped on the lower half to keep every label upright.
    rotation=middle-90
    if middle % 360 > 180:
        rotation += 180
    ax.text(radius*np.cos(rad),radius*np.sin(rad),label,ha='center',va='center',
            rotation=rotation,rotation_mode='anchor',fontsize=fontsize,fontweight=weight)


def taxonomy(fig, stats, compact=False):
    header(fig,'e','Evaluation taxonomy','Eleven classification tasks, with separate diagnostic tracks.',compact)
    ax=fig.add_axes([.04,.16 if not compact else .13,.92,.68 if not compact else .76])
    ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-1.25,1.25);ax.set_ylim(-1.22,1.22)
    total=sum(len(leaves) for _,_,groups in taxonomy_tree() for _,_,leaves in groups)
    step=360/total;angle=90
    for root,color,groups in taxonomy_tree():
        root_size=sum(len(leaves) for _,_,leaves in groups)
        root_start=angle-root_size*step
        ax.add_patch(Wedge((0,0),.53,root_start,angle,width=.23,color=color,ec='white',lw=1))
        sector_label(ax,root_start,angle,.414,root,6.2 if compact else 11,'medium')
        for group,group_color,leaves in groups:
            start=angle-len(leaves)*step
            ax.add_patch(Wedge((0,0),.77,start,angle,width=.235,color=group_color,ec='white',lw=1))
            group_display={'Responsiveness':'Change','Joint decision':'Joint'}.get(group,group)
            sector_label(ax,start,angle,.65,group_display,4.8 if compact else 8,'medium')
            for leaf in leaves:
                leaf_start=angle-step
                # Related shades preserve the parent/child taxonomy, not arbitrary gradients.
                ax.add_patch(Wedge((0,0),1.04,leaf_start,angle,width=.265,color=group_color,alpha=.72,ec='white',lw=1))
                leaf_display={'Counterfactual':'Fact\nchange','Option order':'Option\norder',
                              'Total variation':'Total\nvariation','p50 latency':'p50\nlatency',
                              'p95 latency':'p95\nlatency','Throughput':'Through-\nput'}.get(leaf,leaf)
                sector_label(ax,leaf_start,angle,.904,leaf_display,4.4 if compact else 7.4)
                angle=leaf_start
        assert abs(angle-root_start)<1e-8
    ax.add_patch(Circle((0,0),.285,color='white',ec=GRID,lw=.6))
    ax.text(0,.045,'System1',ha='center',va='center',fontsize=8 if compact else 14,fontweight='semibold')
    ax.text(0,-.065,'Bench',ha='center',va='center',fontsize=8 if compact else 14,fontweight='semibold')
    note(fig,'Angular width counts terminal taxonomy leaves, NOT examples, score weights, or model coverage.\nOnly classification enters the eight-domain index. Diagnostics stay separate; coverage differs by track.',compact)


def export(fig, stem):
    outputs={}
    for extension in ('pdf','svg','png'):
        path=OUT/f'{stem}.{extension}'
        metadata={'Date':'2026-10-09'} if extension=='svg' else ({'CreationDate':None,'ModDate':None} if extension=='pdf' else None)
        fig.savefig(path,dpi=360,metadata=metadata)
        outputs[str(path.relative_to(ROOT)).replace('\\','/')]=digest(path)
    return outputs


def main():
    stats=read(HERE/'corpus_statistics.json')
    scores=read(ROOT/'research/evaluation_completion_v1/results.json')
    assert scores['all_eligible_complete'] and scores['complete_models']==17
    assert stats['scored_population']==9879
    OUT.mkdir(parents=True,exist_ok=True)
    figures=[];outputs={};derived={}
    specs=[('a_radial_decision_profiles',radial,scores,(8.8,8.8)),
           ('b_input_length_distribution',densities,stats,(10,6.7)),
           ('c_semantic_query_diversity',diversity,stats,(10,7.3)),
           ('d_reference_label_balance',balance,stats,(10,7.3)),
           ('e_evaluation_taxonomy',taxonomy,stats,(9,9))]
    for stem,draw,data,size in specs:
        fig=plt.figure(figsize=size)
        derived[stem]=draw(fig,data)
        outputs.update(export(fig,stem));figures.append(fig)
    # A two-row editorial adaptation keeps c/d readable at two-column width.
    overview=plt.figure(figsize=(10,7.9))
    grid=overview.add_gridspec(2,6,left=.02,right=.98,top=.91,bottom=.09,height_ratios=[1.12,1],hspace=.01,wspace=.1)
    radial(overview.add_subfigure(grid[0,:2]),scores,compact=True)
    densities(overview.add_subfigure(grid[0,2:4]),stats,compact=True)
    taxonomy(overview.add_subfigure(grid[0,4:]),stats,compact=True)
    diversity(overview.add_subfigure(grid[1,:3]),stats,compact=True)
    balance(overview.add_subfigure(grid[1,3:]),stats,compact=True)
    overview.text(.025,.045,'(a) Shared 0-100 accuracy scale. (b) Reference token counts, not native cost. (c) 128 query-only samples per task; threshold sensitivity, not CI.',fontsize=6.5,color=MUTED)
    overview.text(.025,.023,'(d) Full frozen reference labels. (e) Angles count taxonomy leaves, not sample shares. Full intent tests; historical tasks retain frozen subsets.',fontsize=6.5,color=MUTED)
    outputs.update(export(overview,'overview_five_panels'))
    book=OUT/'System1Bench_Compass_Figures.pdf'
    with PdfPages(book,metadata={'Title':'System1Bench: Compass-inspired paper figures','CreationDate':None,'ModDate':None}) as pdf:
        pdf.savefig(overview)
        for fig in figures:
            pdf.savefig(fig)
    outputs[str(book.relative_to(ROOT)).replace('\\','/')]=digest(book)
    with (HERE/'domain_scores.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['model','label',*DOMAIN_KEYS,'overall_domain_equal','radial_representative'])
        for model,row in scores['models'].items():
            if not row.get('complete'):
                continue
            writer.writerow([model,row['label'],*[row['domain_scores'][d]['score']*100 for d in DOMAIN_KEYS],
                             row['metrics']['overall_domain_equal']['score']*100,model in MODELS])
    manifest=dict(version=1,design_reference='https://arxiv.org/pdf/2512.21094v3#page=1',
        reference_panels=['radial grouped bars','length density','diversity bars','diversity bars','hierarchical rings'],
        adaptation={'c':'query-only semantic retention with an independently pinned encoder',
                    'd':'reference-label entropy, NOT audio/semantic diversity',
                    'e':'classification tasks plus separate measured diagnostic tracks'},
        source_sha256={'corpus_statistics.json':digest(HERE/'corpus_statistics.json'),
                      'research/evaluation_completion_v1/results.json':digest(ROOT/'research/evaluation_completion_v1/results.json')},
        outputs=outputs,selected_radial_models=MODELS,derived=derived,
        new_score_confidence_intervals=None,
        caveats=stats['caveats']+['Taxonomy width is not score weight or sample volume.',
            'Model-selection examples do not establish architecture effects or pretraining-cleanliness.'])
    (HERE/'figure_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    for fig in [*figures,overview]:plt.close(fig)
    print(json.dumps({'pdfs':7,'individual_figures':5,'overview':1,'models_exported':17,'output':str(OUT)}))


if __name__=='__main__':main()
