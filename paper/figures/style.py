"""Shared vector-figure style; quantitative inputs always come from saved artifacts."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
COLORS={'english':'#0072B2','multilingual':'#009E73','llama31_8b_instruct':'#D55E00','qwen3_8b':'#CC79A7','jev-1.13.0':'#6A51A3'}
MARKERS={'english':'o','multilingual':'s','llama31_8b_instruct':'^','qwen3_8b':'D','jev-1.13.0':'P'}
plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':9,'axes.labelsize':9,
                     'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,
                     'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
                     'savefig.dpi':300,'axes.linewidth':.6,'lines.linewidth':1.3,'figure.dpi':140})

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
