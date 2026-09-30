"""Native-width, source-hash-bound supplementary stability figure."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

def main(source, out):
    source = Path(source)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '150510bd536cb453372cdc6c2ed3a5a8e8ad4896d5de3d8ddf873f757bd5c857'
    data = json.loads(source.read_text())
    assert data['pairs'] == 339
    models = ['qwen3_8b', 'llama31_8b_instruct']
    colors = ['#9A628A', '#C26542']
    plans = ['repeat4', 'within_reverse4', 'shuffled4', 'singleton']
    names = ['Same batches, repeat', 'Same members, row reversal', 'New co-batches, size 4', 'Single-request execution']
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':8.5, 'axes.labelsize':8.5,
                         'xtick.labelsize':8.5,'ytick.labelsize':8.5,'pdf.fonttype':42,'svg.fonttype':'none',
                         'text.color':'#24333D','axes.edgecolor':'#CBD2D6','axes.labelcolor':'#24333D'})
    fig = plt.figure(figsize=(5.4, 5.45), facecolor='white')
    fig.text(.025, .97, 'EXECUTION CONTEXT  /  SCIENTIFIC EVIDENCE', fontsize=9, weight='bold')
    fig.text(.025, .938, '339 identical inputs per condition; 5 plans; 2 fixed local adapters', fontsize=8.5)
    ax = fig.add_axes([.44,.615,.535,.245])
    values = np.array([[data['models'][m]['execution'][c][p]['flips'] for m in models for c in ['base','reversed_option_order']] for p in plans])
    ax.imshow(values, cmap=ListedColormap(['#F3F5F6','#E9EDF2','#DCE5EB','#CCDCE5','#BED2DE','#ABC8D8','#93BDCF','#7CACBF']), vmin=0, vmax=7, aspect='auto')
    ax.set_xticks(range(4), ['Base','Reversal','Base','Reversal'])
    ax.xaxis.tick_top()
    ax.tick_params(axis='both', length=0)
    ax.set_yticks(range(4), names)
    for j in range(4):
        for k in range(4):
            ax.text(k,j,str(values[j,k]), ha='center',va='center',fontsize=10,weight='bold')
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.axvline(1.5,color='white',lw=3)
    ax.text(.25,1.23,'Qwen3 8B',transform=ax.transAxes,ha='center',color=colors[0],weight='bold',fontsize=9)
    ax.text(.75,1.23,'Llama 3.1 8B',transform=ax.transAxes,ha='center',color=colors[1],weight='bold',fontsize=9)
    fig.text(.025,.895,'a  Prediction flips vs. original batches (count / 339)',weight='bold',fontsize=9)
    fig.text(.025,.565,'b  NOINFO reference agreement: reversal minus base (pp)',weight='bold',fontsize=9)
    bottom = fig.add_axes([.30,.155,.675,.335])
    all_plans = ['original4'] + plans
    labels = ['Original batches','Identical repeat','Within-batch reversal','Repacked batches','Single request']
    for mi, (model,color) in enumerate(zip(models,colors)):
        for j,plan in enumerate(all_plans):
            stats = data['models'][model]['intervention'][plan]['NOINFO']
            val = stats['difference_pp']
            lo,hi = stats['claim_cluster_95']
            y = 4-j+(.12 if mi == 0 else -.12)
            bottom.plot([lo,hi],[y,y],color=color,lw=1.3,alpha=.75)
            bottom.plot(val,y,marker='o' if mi == 0 else 's',markersize=4,color=color)
    bottom.set_yticks(range(5),list(reversed(labels)))
    bottom.set_xlim(-46,1)
    bottom.set_xticks([-45,-30,-15,0])
    bottom.axvline(0,color='#8C979F',linewidth=.8)
    bottom.set_xlabel('Difference in reference agreement (percentage points)')
    bottom.grid(axis='x',color='#EDF0F2',linewidth=.6)
    bottom.set_axisbelow(True)
    bottom.tick_params(length=0)
    for name in ('top','right','left'):
        bottom.spines[name].set_visible(False)
    fig.text(.025,.507,'Qwen3 8B',color=colors[0],weight='bold',fontsize=8.5)
    fig.text(.225,.507,'Llama 3.1 8B',color=colors[1],weight='bold',fontsize=8.5)
    fig.text(.475,.507,'Lines: paired claim-cluster 95% intervals',fontsize=8.5)
    fig.text(.025,.06,'NOINFO: 130 derived cited-annotation-absence references; not adjudicated neutrality.',fontsize=8.5)
    fig.text(.025,.025,'Fixed plan order; same-source follow-up; no isolated execution-mechanism claim.',fontsize=8.5)
    out = Path(out)
    out.mkdir(parents=True,exist_ok=True)
    for ext in ('pdf','svg','png'):
        fig.savefig(out / f'fig_batch_context.{ext}',dpi=320)
    print('FIGURE SOURCE SHA256',hashlib.sha256(source.read_bytes()).hexdigest())

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source',default=str(Path(__file__).resolve().parents[2] / 'research/batch_context_v1/summary.json'))
    p.add_argument('--out',default=str(Path(__file__).resolve().parent))
    a = p.parse_args()
    main(a.source,a.out)
