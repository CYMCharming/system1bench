"""Matched wording effects on newly held-out routing states."""
import json
from style import ROOT, COLORS, MARKERS, plt, save

summary=json.loads((ROOT/'research/wording_v1/summary.json').read_text())
models=list(summary['models'])
fig,(en,zh)=plt.subplots(1,2,figsize=(5.5,2.65),sharey=True,gridspec_kw={'width_ratios':[1,1]})
for ax,key,title in [(en,'en_xor','English policy'),(zh,'zh_xor','Chinese policy')]:
    ax.axvspan(-5,5,color='#F0F4F5',zorder=0)
    ax.axvline(0,color='#53626B',lw=.8,zorder=1)
    for i,model in enumerate(models):
        effect=summary['models'][model]['effects'][key]
        center=100*effect['estimate'];low,high=[100*v for v in effect['ci95']]
        ax.plot([low,high],[i,i],color=COLORS[model],lw=1.5,zorder=3)
        ax.plot([low,low],[i-.085,i+.085],color=COLORS[model],lw=.8,zorder=3)
        ax.plot([high,high],[i-.085,i+.085],color=COLORS[model],lw=.8,zorder=3)
        ax.scatter([center],[i],s=38,color=COLORS[model],marker=MARKERS[model],
                   edgecolors='white',linewidths=.5,zorder=4)
    ax.set_xlim(-86,86);ax.set_xticks([-80,-40,0,40,80])
    ax.set_yticks(range(5),[summary['models'][m]['name'] for m in models])
    ax.set_ylim(4.48,-.52);ax.set_title(title,loc='left',weight='bold',fontsize=9.1,pad=9)
    ax.grid(axis='x',color='#E4E9EB',lw=.5,zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel('Explicit − compact accuracy (pp)')
    ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color('#A9B4B9')
    ax.tick_params(axis='y',length=0,pad=5)
zh.tick_params(axis='y',labelleft=False)
fig.subplots_adjust(left=.22,right=.985,top=.84,bottom=.23,wspace=.18)
save(fig,'fig_wording')
