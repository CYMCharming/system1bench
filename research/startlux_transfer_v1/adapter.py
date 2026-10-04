"""Pinned official native inference; evaluation answers never enter the adapter."""
import json
import os
from pathlib import Path
import platform
import sys

from system1bench.common import digest, labels, sha
from system1bench.decision_models import DecisionAdapter, fingerprints
from research.model_expansion_v2.adapter import ExpansionAdapter

ROOT = Path(__file__).resolve().parents[2]

class NativeAdapter:
    def __init__(self, name, pin, load=True):
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
        import torch
        import transformers
        from transformers import AutoTokenizer
        torch.set_num_threads(4); torch.manual_seed(0)
        torch.backends.cuda.matmul.allow_tf32=False
        self.torch,self.name,self.pin=torch,name,pin
        self.limit=32768; self.path=Path(pin['path']); self.model=None
        self.tok=AutoTokenizer.from_pretrained(self.path,local_files_only=True,trust_remote_code=False)
        self.metadata=dict(model=name,checkpoint={k:v for k,v in pin.items() if k!='path'},
            python=platform.python_version(),torch=torch.__version__,transformers=transformers.__version__,
            gpu=torch.cuda.get_device_name(0),seed=0,dtype='bfloat16',context_limit=self.limit,truncation=False,
            text_only=True,batch_requests=1,controlled_speed_measurement=False)
        if name.startswith('startlux'):
            sys.path.insert(0,str(ROOT/'.aris/vendor/startlux_source'))
            from startlux_decision import jevfmt
            from startlux_decision.model import StartLuxDecision
            self.renderer=jevfmt
            cfg=json.loads((self.path/'decision_config.json').read_text())
            self.metadata.update(adapter='startlux_official_native',temperature_by_type=cfg['temperature_by_type'],
                vendor_commit='0e7a2e81b9c92756e26d8edd843a44d50e362669',cuda_graphs=False,images=False,
                prefix_cache_across_requests=False,allow_slow_kernel_fallback=True)
            if load:
                os.environ['STARTLUX_ALLOW_SLOW']='1'
                self.model=StartLuxDecision(str(self.path),device='cuda',max_length=self.limit,graphs=False,images=False)
                self.metadata['fast_kernels_active']=self.model.fast_kernels
        else:
            assert name=='intern_4b'
            sys.path.insert(0,str(ROOT/'.aris/vendor/intern_source'))
            from src.inputs.schema import compile_row,DECISION_TOKEN
            from src.inference.temperature import load_calibration
            self.compile=compile_row; self.marker_id=self.tok.convert_tokens_to_ids(DECISION_TOKEN)
            preset=json.loads((ROOT/'.aris/vendor/intern_source/benchmarks/temperature-presets.json').read_text())['models']['intern-decision-4b']
            # The signed/pinned preset was fitted upstream, never on this evaluation.
            artifact=dict(preset,checkpoint=str(self.path.resolve()))
            calibration=ROOT/'.aris/intern_4b_calibration.json'
            calibration.write_text(json.dumps(artifact))
            self.metadata.update(adapter='intern_official_hf',vendor_commit='3572c8a68b5df5dafe02d0e093989ba8ec0183bc',
                temperature=load_calibration(calibration,self.path),calibration_fit_backend='xtuner',inference_backend='hf',
                attention='sdpa',noul_semantics='native no/yes mapped to false/true',calibration_sha256=sha(calibration))
            if load:
                from src.inference.engine import DecisionEngine
                self.model=DecisionEngine(str(self.path),max_length=self.limit,calibration_path=str(calibration),
                    backend='hf',device='cuda',dtype='bfloat16',attn_implementation='sdpa')
        if load:
            self.metadata['model_files_sha256']=fingerprints(self.path)
            vendor=ROOT/'.aris/vendor'/('startlux_source' if name.startswith('startlux') else 'intern_source')
            self.metadata['vendor_code_sha256']={str(p.relative_to(vendor)):sha(p) for p in sorted(vendor.rglob('*.py'))}

    def audit(self,state,questions):
        if self.name.startswith('startlux'):
            result={}
            for qid,q in questions.items():
                row=self.renderer.from_systemone(state,q,qid)
                ids,order=self.renderer.render_ids(row,self.tok,max_length=self.limit)
                result[qid]=dict(complete=True,prompt_tokens=len(ids),token_sha256=digest(ids),options=len(order))
            return result
        row=dict(state=state,questions=questions)
        if self.model is not None:
            compiled,batch,positions=self.model.backend.encode(row)
            ids=batch['input_ids'][0].tolist(); positions=positions.tolist()
        else:
            compiled=self.compile(row,include_targets=False)
            text=self.tok.apply_chat_template(compiled.messages,tokenize=False,add_generation_prompt=False,
                                              enable_thinking=False,add_vision_id=True)
            ids=self.tok.encode(text,add_special_tokens=False)
            positions=[i-1 for i,t in enumerate(ids) if t==self.marker_id]
        if len(ids)>self.limit: raise ValueError('ContextOverflow')
        if len(positions)!=len(questions) or any(p<0 for p in positions): raise ValueError('DecisionMarkerMismatch')
        return {qid:dict(complete=True,prompt_tokens=len(ids),token_sha256=digest(ids),
                        options=len(labels(questions[qid])),decision_position=p) for qid,p in zip(compiled.fields,positions)}

    def predict(self,state,questions):
        if self.name.startswith('startlux'):
            answers,_=self.model.decide(state,questions)
        else:
            answers=self.model.predict(dict(state=state,questions=questions))['answers']
        result={}
        for qid,answer in answers.items():
            if self.name.startswith('startlux') and questions[qid]['type']=='noul':
                # The official Boolean API exposes P(true), not a probabilities object.
                result[qid]={'false':1-float(answer['noul']),'true':float(answer['noul'])}
                continue
            probs=answer['probabilities']
            if self.name=='intern_4b' and questions[qid]['type']=='noul':
                probs={'false':probs['no'],'true':probs['yes']}
            result[qid]=probs
        return result

    def synchronize(self): self.torch.cuda.synchronize()

def get_adapter(name,pin,load=True):
    if name.startswith(('startlux','intern')): return NativeAdapter(name,pin,load)
    if name in {'kev_27b','qwen35_08b','qwen35_4b','qwen38_27b'}: return ExpansionAdapter(name,pin,load)
    return DecisionAdapter(name,pin,load)
