"""Run the preregistered programmatic confirmation; timing is not a speed benchmark."""
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import importlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from system1bench.common import decode,digest,labels,read,sha,write  # noqa: E402
from system1bench.run import save_run  # noqa: E402


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--paths',default='.aris/compute/performance_paths.json');args=p.parse_args()
    data=ROOT/'research/confirmation_v1/frozen.json';f=read(data);manifest=read(data.parent/'manifest.json')
    if sha(data)!=manifest['frozen_sha256']:raise ValueError('Unfrozen data')
    out=data.parent/'results'/args.model;out.mkdir(parents=True,exist_ok=True)
    if (out/'metadata.json').exists():raise ValueError('Existing run: do not overwrite')
    name='system1bench.laya_adapter:LayaAdapter' if args.model in ['english','multilingual'] else 'system1bench.llm_adapter:LLMAdapter'
    module,cls=name.split(':');adapter=getattr(importlib.import_module(module),cls)(args.model,read(ROOT/args.paths)[args.model])
    signature={'model':adapter.metadata,'frozen_sha256':sha(data),'generator_sha256':manifest['generator_sha256'],
               'runner_sha256':sha(__file__),'common_sha256':sha(ROOT/'system1bench/common.py'),
               'adapter_sha256':sha(ROOT/(module.replace('.','/')+'.py')),'batch_size':8,'seed':0,'budget':f['budget']}
    meta={'status':'RUNNING','started_at':datetime.now(timezone.utc).isoformat(),'signature':signature,'suites':{}}
    write(out/'metadata.json',meta)
    for suite in f['suites']:
        groups=defaultdict(list)
        for c in suite['cases']:groups[(c['condition'],digest(c['questions']),c['language'])].append(c)
        rows=[]
        for (_,_,lang),cases in groups.items():
            for start in range(0,len(cases),8):
                batch=cases[start:start+8];q=batch[0]['questions'];audits=[adapter.audit(c['state'],q,f['budget']) for c in batch]
                if not all(a['complete'] for x in audits for a in x.values()):raise ValueError('Incomplete inputs')
                outputs=adapter.predict([c['state'] for c in batch],q,lang,f['budget'],len(batch))
                if len(outputs)!=len(batch):raise ValueError('Output count')
                for c,result,audit in zip(batch,outputs,audits):
                    for qid,question in q.items():
                        ans=result['answers'][qid];pred,ps=decode(question,ans)
                        rows.append({'id':c['id'],'qid':qid,'group':c['group'],'family':c['family'],'language':c['language'],'condition':c['condition'],'generator_seed':c['generator_seed'],
                                     'request_sha256':c['request_sha256'],'questions_sha256':digest(q),'type':question['type'],'labels':labels(question),'gold':str(c['gold'][qid]['label']),
                                     'answer':ans,'prediction':pred,'probabilities':ps,'error':None,'audit':audit[qid]})
        path=out/(suite['name']+'.json.gz');save_run(path,{'signature':signature,'rows':rows})
        meta['suites'][suite['name']]={'sha256':sha(path),'requests':len(suite['cases']),'decisions':len(rows),'failures':0};write(out/'metadata.json',meta)
        print(args.model,suite['name'],len(rows),'decisions',flush=True)
    meta.update(status='DONE',finished_at=datetime.now(timezone.utc).isoformat());write(out/'metadata.json',meta)


if __name__=='__main__':main()
