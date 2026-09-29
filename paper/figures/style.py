"""Shared vector-figure style; quantitative inputs always come from saved artifacts."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
COLORS={'english':'#176A8A','multilingual':'#3C8F82','llama31_8b_instruct':'#C26542','qwen3_8b':'#9A628A','jev-1.13.0':'#424C78'}
MARKERS={'english':'o','multilingual':'s','llama31_8b_instruct':'^','qwen3_8b':'D','jev-1.13.0':'P'}
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8.5,
                     'axes.labelsize':8.5,'xtick.labelsize':7.5,'ytick.labelsize':7.5,
                     'legend.fontsize':7.5,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
                     'savefig.dpi':320,'axes.linewidth':.55,'lines.linewidth':1.2,'figure.dpi':150,
                     'axes.edgecolor':'#42505B','text.color':'#24333D','axes.labelcolor':'#24333D',
                     'xtick.color':'#56616A','ytick.color':'#56616A'})

def data():return json.loads((ROOT/'research/insights.json').read_text())

def save(fig,name):
    for ext in ['pdf','svg','png']:fig.savefig(OUT/(name+'.'+ext),bbox_inches='tight',pad_inches=.06)
    plt.close(fig)

def interval(ax,x,record,y,color,marker='o',scale=100):
    value=record['estimate']*scale;low,high=[z*scale for z in record['ci95']]
    ax.errorbar(value,y,xerr=[[max(0,value-low)],[max(0,high-value)]],fmt=marker,color=color,markersize=4,capsize=2,elinewidth=.8)

def legend(fig,d,ncol=5):
    from matplotlib.lines import Line2D
    fig.legend([Line2D([],[],color=COLORS[m],marker=MARKERS[m],linestyle='-',markersize=4) for m in d['models']],
               [d['model_names'][m] for m in d['models']],loc='upper center',bbox_to_anchor=(.53,1.02),frameon=False,ncol=ncol)
