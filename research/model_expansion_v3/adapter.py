"""Original-weight Intern, Llama and existing-cache Qwen controls.

Reuse the frozen candidate-code baseline, never generate explanations or fit on
test labels. Intern retains its official native multi-field interface.
"""
import json
import os
from pathlib import Path
import platform
import sys

from system1bench.common import digest, sha
from system1bench.decision_models import DecisionAdapter, fingerprints
from system1bench.llm_adapter import CODES
from research.startlux_transfer_v1.adapter import NativeAdapter, get_adapter as previous_adapter

ROOT = Path(__file__).resolve().parents[2]


class InternAdapter(NativeAdapter):
    def __init__(self, name, pin, load=True):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
        import torch
        import transformers
        from transformers import AutoTokenizer
        torch.set_num_threads(4)
        torch.manual_seed(0)
        torch.backends.cuda.matmul.allow_tf32 = False
        self.torch, self.name, self.pin = torch, name, pin
        self.limit, self.path, self.model = 32768, Path(pin['path']), None
        self.tok = AutoTokenizer.from_pretrained(self.path, local_files_only=True, trust_remote_code=False)
        vendor = ROOT / '.aris/vendor/intern_source'
        sys.path.insert(0, str(vendor))
        from src.inputs.schema import compile_row, DECISION_TOKEN
        from src.inference.temperature import load_calibration
        self.compile = compile_row
        self.marker_id = self.tok.convert_tokens_to_ids(DECISION_TOKEN)
        preset_name = {'intern_08b': 'intern-decision-0.8b', 'intern_2b': 'intern-decision-2b'}[name]
        preset = json.loads((vendor / 'benchmarks/temperature-presets.json').read_text())['models'][preset_name]
        calibration = ROOT / '.aris/family_v3' / (name + '_calibration.json')
        calibration.write_text(json.dumps(dict(preset, checkpoint=str(self.path.resolve()))))
        self.metadata = dict(model=name, checkpoint={k: v for k, v in pin.items() if k != 'path'},
            python=platform.python_version(), torch=torch.__version__, transformers=transformers.__version__,
            gpu=torch.cuda.get_device_name(0), seed=0, dtype='bfloat16', context_limit=self.limit,
            truncation=False, text_only=True, batch_requests=1, controlled_speed_measurement=False,
            adapter='intern_official_hf', vendor_commit='3572c8a68b5df5dafe02d0e093989ba8ec0183bc',
            temperature=load_calibration(calibration, self.path), calibration_fit_backend='xtuner',
            inference_backend='hf', attention='sdpa', noul_semantics='native no/yes mapped to false/true',
            calibration_sha256=sha(calibration), quantized=False)
        if load:
            from src.inference.engine import DecisionEngine
            self.model = DecisionEngine(str(self.path), max_length=self.limit,
                calibration_path=str(calibration), backend='hf', device='cuda', dtype='bfloat16',
                attn_implementation='sdpa')
            self.metadata['model_files_sha256'] = fingerprints(self.path)
            self.metadata['vendor_code_sha256'] = {
                str(p.relative_to(vendor)): sha(p) for p in sorted(vendor.rglob('*.py'))}

    def predict(self, state, questions):
        answers = self.model.predict(dict(state=state, questions=questions))['answers']
        return {qid: {'false': a['probabilities']['no'], 'true': a['probabilities']['yes']}
                if questions[qid]['type'] == 'noul' else a['probabilities'] for qid, a in answers.items()}


class GeneralAdapter(DecisionAdapter):
    def __init__(self, name, pin, load=True):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
        import torch
        import transformers
        from transformers import AutoTokenizer, AutoModelForCausalLM
        torch.set_num_threads(4)
        torch.manual_seed(0)
        torch.backends.cuda.matmul.allow_tf32 = False
        self.name, self.pin, self.torch = name, pin, torch
        self.cache, self.model = {}, None
        path = Path(pin['path'])
        receipt_file = ROOT / 'research/model_expansion_v3/admissions' / (name + '.json')
        receipt = json.loads(receipt_file.read_text())
        assert sha(receipt_file) == pin['admission_sha256']
        assert receipt['repo'] == pin['repo'] and receipt['revision'] == pin['revision']
        cfg = json.loads((path / 'config.json').read_text())
        if cfg.get('quantization_config'):
            raise ValueError('Quantized checkpoints are not admitted')
        self.limit = min(32768, cfg['max_position_embeddings'])
        self.tok = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        if not self.tok.chat_template:
            raise ValueError('A native instruct chat template is required; base models are not silently converted')
        self.tok.padding_side = 'left'
        if self.tok.pad_token_id is None:
            self.tok.pad_token = self.tok.eos_token
        codes = [self.tok.encode(c, add_special_tokens=False) for c in CODES]
        if any(len(c) != 1 for c in codes) or len({c[0] for c in codes}) != len(CODES):
            raise ValueError('Non-single-token candidate code')
        self.code_ids = [c[0] for c in codes]
        self.metadata = dict(model=name, checkpoint={k: v for k, v in pin.items() if k != 'path'},
            python=platform.python_version(), torch=torch.__version__, transformers=transformers.__version__,
            gpu=torch.cuda.get_device_name(0), seed=0, context_limit=self.limit, truncation=False,
            batch_requests=1, controlled_speed_measurement=False, dtype='bfloat16', attention='sdpa',
            adapter='llama_constrained_next_token' if name.startswith('llama') else 'qwen3_constrained_next_token',
            enable_thinking=False, text_only=True, quantized=False,
            probability_semantics='conditional candidate-code likelihood, not calibrated correctness',
            chat_template_sha256=digest(self.tok.chat_template))
        if load:
            verified = fingerprints(path)
            assert all(verified[n] == r['sha256'] for n, r in receipt['weights'].items())
            assert all(sha(path / n) == value for n, value in receipt['input_files'].items())
            self.model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
                trust_remote_code=False, dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda').eval()
            self.metadata['model_files_sha256'] = verified


def get_adapter(name, pin, load=True):
    if name in {'intern_08b', 'intern_2b'}:
        return InternAdapter(name, pin, load)
    if name.startswith(('llama32_', 'qwen3_')):
        return GeneralAdapter(name, pin, load)
    return previous_adapter(name, pin, load)
