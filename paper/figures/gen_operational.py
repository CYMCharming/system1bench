import json
from matplotlib.ticker import LogLocator, NullFormatter
from style import data,save,legend,COLORS,MARKERS,ROOT,plt

d=data();p=json.loads((ROOT/'performance/v1/summary.json').read_text());models=[m for m in d['models'] if not m.startswith('jev')]
work=['boolq','banking77','massive_zh','clinc150_oos','needle_100','needle_4000']
fig,axes=plt.subplots(2,3,figsize=(5.5,4.5))
for i,(ax,w) in enumerate(zip(axes.flat,work)):
    for m in models:
        c=next(c for c in p['cells'] if c['model']==m and c['workload']==w and c['batch_size']==1)
        x=c['batch_p50_ms']['median'];lo,hi=c['batch_p50_ms']['ci95'];y=c['reference_agreement']['median']*100
        ax.errorbar(x,y,xerr=[[x-lo],[hi-x]],fmt=MARKERS[m],color=COLORS[m],markersize=5,capsize=2)
    ax.set_xscale('log');ax.xaxis.set_major_locator(LogLocator(base=10,subs=(1.0,),numticks=3));ax.xaxis.set_minor_formatter(NullFormatter());ax.set_ylim(0,103);ax.set_yticks([0,25,50,75,100]);ax.grid(color='.92',lw=.5);ax.set_axisbelow(True)
    ax.text(.05,.07,f'({chr(97+i)})',transform=ax.transAxes)
    if i%3==0:ax.set_ylabel('Reference agreement (%)')
    if i>=3:ax.set_xlabel('Request p50 latency (ms)')
legend(fig,{**d,'models':models},4);fig.tight_layout(rect=(0,0,1,.95));save(fig,'fig_operational')
