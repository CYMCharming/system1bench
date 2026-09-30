"""Bridge pinned expansion engines into the standard run_frozen interface."""
import math
from pathlib import Path

from .common import ROOT,read
from .decision_models import DecisionAdapter,validate_distribution

class ExpandedDecisionAdapter:
    def __init__(self,model,checkpoint=None):
        manifest=read(ROOT/'research/model_expansion_v1/manifest.json')
        if model not in manifest['model_pins']:
            raise ValueError('Unknown pinned expansion model')
        pin=dict(manifest['model_pins'][model])
        if checkpoint is None:
            private=ROOT/'.aris/model_expansion_paths.json'
            if not private.exists():
                raise ValueError('Supply an explicit local checkpoint or configure private pinned paths')
            configured=read(private)[model]
            if configured['revision']!=pin['revision']:
                raise ValueError('Configured model revision differs from the public pin')
            pin.update(configured)
        else:
            pin['path']=str(Path(checkpoint))
        self.engine=DecisionAdapter(model,pin)
        self.metadata=dict(self.engine.metadata,standard_runner_bridge=True,
            batch_backend='serial complete requests; one failed request does not invalidate its peers',
            context_policy='min(model window, frozen budget max_len); never truncate')

    def _budget(self,budget):
        limit=min(32768,int(budget['max_len']))
        if limit<=0:
            raise ValueError('Context budget must be positive')
        if limit!=self.engine.limit:
            # Cached prompts were audited under the previous budget.
            cache=getattr(self.engine,'cache',None)
            if cache is not None:
                cache.clear()
        self.engine.limit=limit

    def audit(self,state,questions,budget):
        self._budget(budget)
        try:
            audits=self.engine.audit(state,questions)
            return {qid:dict(value,context_limit=self.engine.limit,complete=True) for qid,value in audits.items()}
        except (ValueError,TypeError):
            return {qid:dict(complete=False,context_limit=self.engine.limit,input_error='unsupported_or_overlong',
                            state_shortened=False,instruction_shortened=False,option_texts_shortened=0) for qid in questions}

    def synchronize(self):
        self.engine.synchronize()

    def predict(self,states,questions,language,budget,batch_size):
        self._budget(budget)
        outputs=[]
        for state in states:
            try:
                if not all(a['complete'] for a in self.audit(state,questions,budget).values()):
                    outputs.append(dict(answers={}))
                    continue
                probabilities=self.engine.predict(state,questions)
                answers={}
                for qid,q in questions.items():
                    prediction,p=validate_distribution(q,probabilities[qid])
                    answer=dict(probabilities=p)
                    if q['type']=='choice':
                        answer['choice']=prediction
                    elif q['type']=='noul':
                        answer['noul']=p['true']
                    else:
                        answer['score']=math.fsum(int(k)*v for k,v in p.items())
                    answers[qid]=answer
                outputs.append(dict(answers=answers))
            except (ValueError,TypeError,KeyError):
                # The standard runner records missing answers as explicit invalid
                # decisions. Valid neighboring requests keep their own outputs.
                outputs.append(dict(answers={}))
        return outputs
