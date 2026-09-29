"""Orthogonal LLM presentation/code controls on the fresh policy action questions."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from system1bench.common import decode,digest,labels,read,sha,write  # noqa: E402
from system1bench.llm_adapter import CODES,SYSTEM,LLMAdapter,answer_from_logits,candidates  # noqa: E402
from system1bench.run import save_run  # noqa: E402

MODES=['baseline','repeat','position_only','code_only','both']


def render(state,q,mode):
    items=deepcopy(candidates(q))
    if mode=='code_only':
        for x,code in zip(items,reversed(CODES[:len(items)])):x['code']=code
    if mode in ['position_only','both']:
        items.reverse()
        if mode=='both':
            for i,x in enumerate(items):x['code']=CODES[i]
    code_by_label={x['label']:x['code'] for x in items}
    payload=dict(state=state,question_type=q['type'],instructions=q['instructions'],candidates=items)
    msgs=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(payload,ensure_ascii=False,separators=(',',':')))]
    return msgs,[CODES.index(code_by_label[label]) for label in labels(q)]


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);a=p.parse_args()
    import torch
    frozen=ROOT/'research/confirmation_v1/frozen.json';f=read(frozen);manifest=read(frozen.parent/'manifest.json')
    if sha(frozen)!=manifest['frozen_sha256']:raise ValueError('Input mismatch')
    adapter=LLMAdapter(a.model,read(ROOT/'.aris/compute/performance_paths.json')[a.model])
    out=frozen.parent/'codebook'/a.model;out.mkdir(parents=True,exist_ok=True)
    if (out/'metadata.json').exists():raise ValueError('Do not overwrite run')
    sig=dict(model=adapter.metadata,frozen_sha256=sha(frozen),runner_sha256=sha(__file__),adapter_sha256=sha(ROOT/'system1bench/llm_adapter.py'),batch_size=8,modes=MODES)
    meta=dict(status='RUNNING',started_at=datetime.now(timezone.utc).isoformat(),signature=sig,suites={});write(out/'metadata.json',meta)
    for s in f['suites']:
        cases=[c for c in s['cases'] if c['condition']=='original'];rows=[]
        for mode in MODES:
            for begin in range(0,len(cases),8):
                batch=cases[begin:begin+8];seqs=[];code_indices=[]
                for c in batch:
                    msg,codes=render(c['state'],c['questions']['action'],mode)
                    txt=adapter.tok.apply_chat_template(msg,tokenize=False,add_generation_prompt=True,enable_thinking=False)
                    seq=adapter.tok.encode(txt,add_special_tokens=False)
                    if len(seq)>adapter.limit:raise ValueError('Context limit')
                    seqs.append(seq);code_indices.append(codes)
                padded=adapter.tok.pad({'input_ids':seqs},padding=True,return_tensors='pt').to('cuda');pos=padded['attention_mask'].long().cumsum(-1)-1;pos.masked_fill_(padded['attention_mask']==0,0)
                with torch.inference_mode():logits=adapter.model(**padded,position_ids=pos,use_cache=False,logits_to_keep=1).logits[:,-1]
                for i,c in enumerate(batch):
                    z=logits[i].index_select(-1,adapter.code_ids[code_indices[i]]).float().cpu().tolist();q=c['questions']['action'];ans=answer_from_logits(q,z);pred,ps=decode(q,ans)
                    rows.append(dict(id=c['id'],group=c['group'],family=c['family'],generator_seed=c['generator_seed'],condition=mode,qid='action',request_sha256=c['request_sha256'],prompt_token_sha256=digest(seqs[i]),prompt_tokens=len(seqs[i]),code_indices=code_indices[i],gold=c['gold']['action']['label'],prediction=pred,answer=ans,probabilities=ps,error=None))
        path=out/(s['name']+'.json.gz');save_run(path,dict(signature=sig,rows=rows));meta['suites'][s['name']]=dict(sha256=sha(path),decisions=len(rows));write(out/'metadata.json',meta);print(a.model,s['name'],len(rows),'codebook decisions',flush=True)
    meta.update(status='DONE',finished_at=datetime.now(timezone.utc).isoformat());write(out/'metadata.json',meta)


if __name__=='__main__':main()
