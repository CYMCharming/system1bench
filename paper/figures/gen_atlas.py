"""Publication atlas: keep domain, decision function and reference provenance separate."""
import json
from matplotlib.patches import Rectangle
from style import ROOT, plt, save, data

atlas=json.loads((ROOT/'paper/source_atlas.json').read_text())
analysis=data()
sources=atlas['sources']
axes=atlas['task_axes']
seen=[suite for source in sources for suite in source['suites']]
expected=[suite for group in analysis['taxonomy'].values() for suite in group]
assert len(sources)==15 and len(seen)==28 and len(set(seen))==28
assert set(seen)==set(expected), (set(seen)-set(expected),set(expected)-set(seen))
for source in sources:
    assert source['tasks'] and set(source['tasks']) <= {x['id'] for x in axes}
    assert source['reference'] in {'D','H','T','A','P','T/P'}

# A matrix of coverage, never a matrix of accuracies. Its row grain is a source
# collection; multiple dots in a row are intentional, not independent sources.
fig=plt.figure(figsize=(7.25,6.3),facecolor='white')
ax=fig.add_axes([.025,.065,.95,.895])
ax.set_xlim(0,12.25);ax.set_ylim(1.45,16.3);ax.axis('off')
ink='#26343E';muted='#62727C';rule='#D8E0E3';navy='#1F5B77';gold='#BD8A36'
x_source=.10;x_domain=2.38;x_task=5.31;x_ref=10.96;x_suites=11.73
step=.59
ax.text(x_source,15.55,'SOURCE',weight='bold',fontsize=8.0,color=ink)
ax.text(x_domain,15.55,'DOMAIN',weight='bold',fontsize=8.0,color=ink)
ax.text(7.64,15.55,'DECISION FUNCTION',weight='bold',fontsize=8.0,color=ink,ha='center')
ax.text(x_ref,15.55,'REF.',weight='bold',fontsize=8.0,color=ink,ha='center')
ax.text(x_suites,15.55,'SUITES',weight='bold',fontsize=8.0,color=ink,ha='center')
short=['Semantic','Routing','Evidence','Ordinal','Safety','Workflow','Reject','Retrieve']
for j,item in enumerate(axes):
    x=x_task+j*.69
    ax.text(x,14.9,short[j],ha='center',va='center',rotation=45,fontsize=6.7,color=ink)
ax.plot([0,12.2],[14.28,14.28],color=ink,lw=.8)
groups=[('Language and affect',0,3),('Service and routing',3,6),('Evidence and inference',6,9),
        ('Safety',9,11),('Typed workflow fixtures',11,15)]
cursor=14.02
for title,start,end in groups:
    ax.text(x_source,cursor,title.upper(),fontsize=6.7,weight='bold',color=navy,va='center')
    ax.plot([2.32,12.2],[cursor-.09,cursor-.09],color=rule,lw=.55)
    cursor-=.42
    for idx in range(start,end):
        source=sources[idx]
        row_y=cursor
        if idx%2==0:
            ax.add_patch(Rectangle((0,row_y-.26),12.2,.52,facecolor='#F6F8F8',edgecolor='none',zorder=-2))
        ax.text(x_source,row_y,source['name'],fontsize=8.6,weight='medium',color=ink,va='center')
        ax.text(x_domain,row_y,source['domain'],fontsize=8.0,color=muted,va='center')
        for j,item in enumerate(axes):
            if item['id'] in source['tasks']:
                ax.scatter([x_task+j*.69],[row_y],s=49,c=navy,edgecolors='white',linewidths=.45,zorder=3)
            else:
                ax.scatter([x_task+j*.69],[row_y],s=8,c='#D6DEE2',edgecolors='none',zorder=2)
        ref=source['reference']
        ax.text(x_ref,row_y,ref,ha='center',va='center',fontsize=7.8,weight='bold',
                color=gold if ref!='D' else muted)
        ax.text(x_suites,row_y,str(len(source['suites'])),ha='center',va='center',fontsize=8.2,color=ink)
        cursor-=step
    cursor-=.13

ax.plot([0,12.2],[2.08,2.08],color=ink,lw=.7)
ax.text(.10,1.78,'●  Task appears in source',fontsize=7.3,color=navy,va='center')
ax.text(3.25,1.78,'D  dataset  ·  H  human prompt  ·  T  synthetic teacher  ·  A  authored/reviewed  ·  P  programmatic',
        fontsize=6.8,color=muted,va='center')
save(fig,'fig_atlas')
