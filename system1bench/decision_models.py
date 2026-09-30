"""Pinned official native interfaces and a text-only Qwen3.5 direct baseline."""
import json
import math
import os
from pathlib import Path
import platform
import sys

from .common import digest, labels, sha
from .llm_adapter import CODES, messages

ROOT = Path(__file__).resolve().parents[1]

def fingerprints(root, recursive=False):
    paths = [*root.iterdir(), *(root/'tokenizer').rglob('*'), *(root/'backbone_config').rglob('*')] if recursive else root.iterdir()
    return {str(p.relative_to(root)): sha(p) for p in sorted(paths)
            if p.is_file() and p.suffix in {'.json', '.safetensors', '.pt', '.jinja', '.py'} and '__pycache__' not in p.parts}

class DecisionAdapter:
    def __init__(self, name, pin, load=True):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
        import torch
        import transformers
        import peft
        import pydantic
        torch.set_num_threads(4)
        torch.manual_seed(0)
        torch.backends.cuda.matmul.allow_tf32 = False
        self.name, self.pin, self.torch = name, pin, torch
        self.limit = 32768
        self.cache = {}
        self.model = None
        self.metadata = dict(model=name, checkpoint={k:v for k,v in pin.items() if k not in {'path','base_path','downloaded'}},
            python=platform.python_version(), torch=torch.__version__, transformers=transformers.__version__,
            peft=peft.__version__, pydantic=pydantic.__version__, gpu=torch.cuda.get_device_name(0), seed=0, context_limit=self.limit,
            truncation=False, batch_requests=1, controlled_speed_measurement=False)
        path = Path(pin['path'])
        if name.startswith('kev'):
            sys.path.insert(0, str(ROOT / '.aris/vendor'))
            from kev.api import SystemOneRequest, to_record
            from kev.checkpoint import Checkpoint, LoadOptions
            from kev.model import encode, load_tokenizer
            self.request_class, self.to_record, self.encoder = SystemOneRequest, to_record, encode
            self.checkpoint = Checkpoint(str(path))
            self.tok = load_tokenizer(self.checkpoint.meta.base, revision=self.checkpoint.meta.base_revision)
            self.metadata.update(adapter='kev_official_pointer', dtype='bfloat16', attention='sdpa',
                temperature=self.checkpoint.meta.temperature, merge=True, prefix_cache_across_requests=False,
                cuda_graphs=False, fused=False, date_facts=False,
                option_isolation=self.checkpoint.meta.option_isolation,
                vendor_commit='0fe8fc97c2bcc247fa3efb6e5c32af4e99770e91')
            if load:
                self.tok, self.model = self.checkpoint.load('cuda', LoadOptions(dtype=torch.bfloat16,
                    attn='sdpa', merge=True, backend='torch', cuda_graphs=False, fused=False))
        elif name == 'nanojev':
            sys.path.insert(0, str(ROOT / '.aris/vendor/nanojev-scripts'))
            from predict_toy_decisions import DecisionPredictor, prepare_examples
            from transformers import AutoTokenizer
            self.prepare_examples = prepare_examples
            self.tok = AutoTokenizer.from_pretrained(path/'tokenizer', local_files_only=True, trust_remote_code=False)
            cfg = json.loads((path / 'config.json').read_text())
            self.training_limit = cfg.get('max_length', 512)
            self.metadata.update(adapter='nanojev_official_candidate_paths', dtype='fp32_storage_bf16_autocast',
                attention='sdpa', temperature=1.0, trained_max_length=self.training_limit,
                max_length_override=self.limit, disable_native_triton=False,
                vendor_commit='76fdfc9ecdca45a9bcef17991a07d3041a87685a')
            if load:
                self.model = DecisionPredictor(path, max_length=self.limit, precision='bf16', disable_native_triton=False)
        elif name == 'qwen35_9b':
            from transformers import AutoModelForImageTextToText, AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
            self.tok.padding_side = 'left'
            if self.tok.pad_token_id is None:
                self.tok.pad_token = self.tok.eos_token
            ids = [self.tok.encode(c, add_special_tokens=False) for c in CODES]
            if any(len(i) != 1 for i in ids) or len({i[0] for i in ids}) != len(ids):
                raise ValueError('Non-single-token candidate code')
            self.code_ids = [i[0] for i in ids]
            self.metadata.update(adapter='qwen35_constrained_next_token', dtype='bfloat16', attention='sdpa',
                enable_thinking=False, text_only=True, probability_semantics='conditional candidate-code likelihood, not calibrated correctness',
                chat_template_sha256=digest(self.tok.chat_template))
            if load:
                self.model = AutoModelForImageTextToText.from_pretrained(path, local_files_only=True,
                    trust_remote_code=False, dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda').eval()
        else:
            raise ValueError(name)
        if load:
            self.metadata['model_files_sha256'] = fingerprints(path, name == 'nanojev')
            if 'base_path' in pin:
                self.metadata['base_files_sha256'] = fingerprints(Path(pin['base_path']))
            vendor = ROOT / '.aris/vendor' / ('kev' if name.startswith('kev') else 'nanojev-scripts')
            if vendor.is_dir():
                self.metadata['vendor_code_sha256'] = {p.name: sha(p) for p in sorted(vendor.glob('*.py'))}

    def encoded(self, state, questions):
        key = digest([state, questions])
        if key in self.cache:
            return self.cache[key]
        if self.name.startswith('kev'):
            rec, meta = self.to_record(self.request_class(state=state, questions=questions))
            enc = self.encoder(self.tok, rec, max_state=self.limit, max_branch=self.limit,
                               strict=True, option_isolation=self.checkpoint.meta.option_isolation)
            result = enc, meta
        elif self.name == 'nanojev':
            mapped = {k: {**q, 'type': 'boolean' if q['type'] == 'noul' else q['type']} for k,q in questions.items()}
            payload = dict(states=[dict(id='input', state=state, questions=mapped)])
            result = self.prepare_examples(payload, self.tok, self.limit), payload
        else:
            result = {}
            for qid, question in questions.items():
                text = self.tok.apply_chat_template(messages(state, question), tokenize=False,
                    add_generation_prompt=True, enable_thinking=False)
                ids = self.tok.encode(text, add_special_tokens=False)
                if len(ids) > self.limit:
                    raise ValueError('ContextOverflow')
                result[qid] = ids
        self.cache[key] = result
        return result

    def audit(self, state, questions):
        encoded = self.encoded(state, questions)
        if self.name.startswith('kev'):
            enc, meta = encoded
            return {m['id']: dict(complete=True, token_sha256=digest(enc),
                prompt_tokens=len(enc['ids']), state_tokens=enc['seg'].count(0),
                options=len(m['keys']), training_length_exceeded=None) for m in meta}
        if self.name == 'nanojev':
            return {ex['qid']: dict(complete=True, token_sha256=digest(ex['leaf_tokens']),
                prompt_tokens=max(map(len,ex['leaf_tokens'])), candidate_paths=len(ex['leaf_tokens']),
                options=len(ex['candidate_ids']), training_length_exceeded=max(map(len,ex['leaf_tokens'])) > self.training_limit)
                for ex in encoded[0]}
        return {qid: dict(complete=True, token_sha256=digest(ids), prompt_tokens=len(ids),
                         options=len(labels(questions[qid])), training_length_exceeded=None) for qid,ids in encoded.items()}

    def synchronize(self):
        self.torch.cuda.synchronize()

    def predict(self, state, questions):
        encoded = self.encoded(state, questions)
        torch = self.torch
        if self.name.startswith('kev'):
            enc, meta = encoded
            with torch.inference_mode():
                probabilities = self.model.probs(enc)
            return {m['id']: dict(zip(m['keys'], p.tolist())) for m,p in zip(meta, probabilities)}
        if self.name == 'nanojev':
            return {qid: answer['probabilities'] for qid,answer in self.model.predict(encoded[1])['states'][0]['answers'].items()}
        answers = {}
        with torch.inference_mode():
            for qid, ids in encoded.items():
                inp = torch.tensor([ids], device='cuda')
                logits = self.model(input_ids=inp, attention_mask=torch.ones_like(inp),
                    use_cache=False, logits_to_keep=1).logits[0,-1].float()
                allowed = labels(questions[qid])
                raw = logits[torch.tensor(self.code_ids[:len(allowed)],device='cuda')].double()
                answers[qid] = dict(zip(allowed, torch.softmax(raw,0).cpu().tolist()))
        return answers

def validate_distribution(question, dist):
    allowed = labels(question)
    if set(dist) != set(allowed):
        raise ValueError('Candidate label mismatch')
    vals = [float(dist[k]) for k in allowed]
    if not all(math.isfinite(p) and 0 <= p <= 1 for p in vals) or abs(sum(vals)-1) > 1e-5:
        raise ValueError('Invalid probability distribution')
    norm = [p/sum(vals) for p in vals]
    return allowed[max(range(len(norm)),key=norm.__getitem__)], dict(zip(allowed,norm))
