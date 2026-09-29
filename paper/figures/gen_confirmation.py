"""Fresh intervention plots from the frozen diagnostic's saved analysis."""
import json
import numpy as np
from style import ROOT, COLORS, MARKERS, plt, save

d = json.loads((ROOT / 'research/confirmation_v1/summary.json').read_text())
models = [m for m in COLORS if any(r['model'] == m for r in d['families'])]
names = dict(zip(COLORS, ['Laya EN', 'Laya Multi', 'Llama 8B', 'Qwen 8B', 'Jev 1.13']))
families = ['policy_refund', 'policy_access', 'policy_routing']
labels = ['Refund', 'Access', 'Routing']
titles = ['Reversal excess flips', 'Chinese − original', 'Distractor − original',
          'Paraphrase − original', 'Choice − binary review', 'Choice − ordinal severity']
fig, axes = plt.subplots(3, 2, figsize=(5.5, 7.1), sharey=True)
for k, ax in enumerate(axes.flat):
    for j, family in enumerate(families):
        for i, model in enumerate(models):
            r = next(r for r in d['families'] if r['model'] == model and r['family'] == family)
            e = r['primary_effects'][k]
            value = e['estimate'] * 100
            lo, hi = np.asarray(e['simultaneous_ci95']) * 100
            ax.errorbar(value, j + (i - (len(models)-1)/2)*.14,
                        xerr=[[max(0, value-lo)], [max(0, hi-value)]],
                        color=COLORS[model], marker=MARKERS[model], markersize=3.5,
                        capsize=1.8, elinewidth=.7, linestyle='none')
    ax.axvline(0, color='.6', linewidth=.6)
    ax.set_yticks(range(3), labels)
    ax.set_title(f'({chr(97+k)}) {titles[k]}', fontsize=9)
    ax.grid(axis='x', alpha=.15)
    ax.set_xlabel('Percentage points')
    ax.set_ylim(2.5, -.5)
from matplotlib.lines import Line2D
fig.legend([Line2D([], [], color=COLORS[m], marker=MARKERS[m], linestyle='none') for m in models],
           [names[m] for m in models], loc='upper center', ncol=3, frameon=False)
fig.tight_layout(rect=(0, 0, 1, .94), h_pad=1.4)
save(fig, 'fig_confirmation')

fig, axes = plt.subplots(3, 2, figsize=(5.5, 4.5), sharex=True, sharey=True)
for j, family in enumerate(families):
    for k, model in enumerate(['llama31_8b_instruct', 'qwen3_8b']):
        ax = axes[j,k]
        r = next(r for r in d['codebook'] if r['model'] == model and r['family'] == family)
        values = [100*e['discordance']['estimate'] for e in r['contrasts']]
        low = [100*e['discordance']['ci95'][0] for e in r['contrasts']]
        high = [100*e['discordance']['ci95'][1] for e in r['contrasts']]
        color=COLORS[model]
        for x,(v,lo,hi) in enumerate(zip(values,low,high)):
            ax.plot([x,x],[lo,hi],color=color,lw=1.15,zorder=2)
            ax.plot([x-.08,x+.08],[lo,lo],color=color,lw=.8,zorder=2)
            ax.plot([x-.08,x+.08],[hi,hi],color=color,lw=.8,zorder=2)
            ax.scatter(x,v,s=32,color=color,edgecolors='white',linewidths=.4,zorder=3)
        ax.set_ylim(-4,104);ax.set_yticks([0,25,50,75,100])
        ax.set_xticks(range(4),['Repeat','Display','Code','Both'])
        ax.grid(axis='y',color='#E4E9EB',lw=.5)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color('#A9B4B9')
        if j==0: ax.set_title(names[model],weight='bold',fontsize=9)
        if k==0: ax.set_ylabel(f'{labels[j]}\nFlip (%)',fontsize=8)
        if k==1: ax.tick_params(axis='y',labelleft=False)
        if j<2: ax.tick_params(axis='x',labelbottom=False)
fig.subplots_adjust(left=.16,right=.98,top=.91,bottom=.13,hspace=.35,wspace=.18)
save(fig, 'fig_codebook')
