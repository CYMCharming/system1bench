"""Bridge historical Laya/Llama interfaces without modifying frozen sources."""
from pathlib import Path

from research.model_expansion_v3.adapter import get_adapter as existing_adapter
from system1bench.common import decode, labels

BUDGET = {'max_len': 8192, 'head_max_len': 4096}


class HistoricalAdapter:
    def __init__(self, name, pin):
        from system1bench.laya_adapter import LayaAdapter
        from system1bench.llm_adapter import LLMAdapter
        if name in {'english', 'multilingual'}:
            self.native = LayaAdapter(name, pin['path'])
        else:
            self.native = LLMAdapter(name, pin['path'])
        self.metadata = dict(self.native.metadata, checkpoint={k: v for k, v in pin.items() if k != 'path'},
                             truncation=False, quantized=False, batch_requests=1,
                             historical_budget=BUDGET, timing_comparable=False)

    def audit(self, state, questions):
        return self.native.audit(state, questions, BUDGET)

    def predict(self, state, questions):
        output = self.native.predict([state], questions, 'en', BUDGET, 1)[0]['answers']
        result = {}
        for qid, question in questions.items():
            _, probabilities = decode(question, output[qid])
            result[qid] = dict(zip(labels(question), probabilities))
        return result

    def synchronize(self):
        self.native.synchronize()


def get_adapter(name, pin, load=True):
    for key in ('path', 'base_path'):
        if key in pin:
            import json
            config = Path(pin[key]) / 'config.json'
            if config.exists() and json.loads(config.read_text()).get('quantization_config'):
                raise ValueError('Quantized checkpoint rejected')
    if name in {'english', 'multilingual', 'llama31_8b_instruct'}:
        # These historical constructors always load; preflight and inference reuse
        # the same instance, rather than silently creating a different adapter.
        return HistoricalAdapter(name, pin)
    return existing_adapter(name, pin, load)
