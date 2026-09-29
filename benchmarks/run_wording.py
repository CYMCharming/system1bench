"""Run a frozen held-out wording suite on one resident checkpoint."""
import argparse
from datetime import datetime,timezone
import importlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from system1bench.common import decode,digest,labels,read,sha,write  # noqa: E402
from system1bench.run import save_run  # noqa: E402


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--paths',default='.aris/compute/performance_paths.json')
    args=parser.parse_args()
    data=ROOT/'research/wording_v1/frozen.json'
    frozen=read(data)
    manifest=read(data.parent/'manifest.json')
    if sha(data)!=manifest['frozen_sha256']:raise ValueError('Frozen data changed')
    output=data.parent/'results'/args.model
    if output.exists():raise ValueError('Existing run; select a new output directory')
    output.mkdir(parents=True)
    module='system1bench.laya_adapter' if args.model in {'english','multilingual'} else 'system1bench.llm_adapter'
    cls='LayaAdapter' if args.model in {'english','multilingual'} else 'LLMAdapter'
    adapter=getattr(importlib.import_module(module),cls)(args.model,read(ROOT/args.paths)[args.model])
    signature={'model':adapter.metadata,'frozen_sha256':sha(data),'generator_sha256':manifest['generator_sha256'],
               'runner_sha256':sha(__file__),'common_sha256':sha(ROOT/'system1bench/common.py'),
               'adapter_sha256':sha(ROOT/(module.replace('.','/')+'.py')),
               'batch_size':8,'seed':0,'budget':frozen['budget']}
    metadata={'status':'RUNNING','started_at':datetime.now(timezone.utc).isoformat(),'signature':signature,'suites':{}}
    write(output/'metadata.json',metadata)
    for suite in frozen['suites']:
        rows=[]
        for condition in frozen['conditions']:
            cases=[case for case in suite['cases'] if case['condition']==condition]
            for start in range(0,len(cases),8):
                batch=cases[start:start+8]
                q=batch[0]['questions'];lang=batch[0]['language']
                audits=[adapter.audit(case['state'],q,frozen['budget']) for case in batch]
                if not all(a['complete'] for audit in audits for a in audit.values()):raise ValueError('Incomplete input')
                output_rows=adapter.predict([case['state'] for case in batch],q,lang,frozen['budget'],len(batch))
                if len(output_rows)!=len(batch):raise ValueError('Output count mismatch')
                for case,result,audit in zip(batch,output_rows,audits):
                    answer=result['answers']['action'];prediction,probabilities=decode(q['action'],answer)
                    rows.append({'id':case['id'],'qid':'action','group':case['group'],'family':case['family'],
                                 'language':case['language'],'condition':case['condition'],
                                 'generator_seed':case['generator_seed'],'boolean_cell':case['boolean_cell'],
                                 'request_sha256':case['request_sha256'],'questions_sha256':digest(q),
                                 'type':'choice','labels':labels(q['action']),
                                 'gold':str(case['gold']['action']['label']),'answer':answer,
                                 'prediction':prediction,'probabilities':probabilities,'error':None,
                                 'audit':audit['action']})
        path=output/(suite['name']+'.json.gz')
        save_run(path,{'signature':signature,'rows':rows})
        metadata['suites'][suite['name']]={'sha256':sha(path),'requests':len(suite['cases']),
            'decisions':len(rows),'failures':0}
        write(output/'metadata.json',metadata)
    metadata.update(status='DONE',finished_at=datetime.now(timezone.utc).isoformat())
    write(output/'metadata.json',metadata)
    print(args.model,len(rows),'decisions',flush=True)


if __name__=='__main__':main()
