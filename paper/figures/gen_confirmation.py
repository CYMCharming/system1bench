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

fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.8), sharey=True)
for ax, model in zip(axes, ['llama31_8b_instruct', 'qwen3_8b']):
    for j, family in enumerate(families):
        r = next(r for r in d['codebook'] if r['model'] == model and r['family'] == family)
        values = [100*e['discordance']['estimate'] for e in r['contrasts']]
        lo = [v-100*e['discordance']['ci95'][0] for v,e in zip(values,r['contrasts'])]
        hi = [100*e['discordance']['ci95'][1]-v for v,e in zip(values,r['contrasts'])]
        ax.errorbar(np.arange(4)+(j-1)*.08, values, yerr=[lo,hi], marker=['o','s','^'][j],
                    color=['#0072B2','#D55E00','#009E73'][j], capsize=2, label=labels[j], markersize=4)
    ax.set_title(names[model]); ax.set_ylim(-3, 104)
    ax.set_xticks(range(4), ['Repeat', 'Display', 'Code', 'Both'], rotation=25)
    ax.grid(axis='y', alpha=.15)
axes[0].set_ylabel('Prediction flips (%)')
axes[1].legend(frameon=False, fontsize=7, loc='upper right')
fig.tight_layout()
save(fig, 'fig_codebook')
