"""Small seeded device/tokenizer witness, run before (never alongside) measurement."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import read  # noqa: E402
from system1bench.llm_adapter import CODES  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paths', required=True, help='Local checkpoint mapping used by the timing runner')
    args = parser.parse_args()
    import torch
    from transformers import AutoTokenizer
    paths = read(args.paths)
    torch.manual_seed(0)
    x = torch.randn(32, 32, device='cuda', dtype=torch.bfloat16)
    y = x @ x
    if not y.isfinite().all() or not y.abs().sum() > 0:
        raise ValueError('Seeded BF16 CUDA witness failed')
    result = dict(packages={p: importlib.metadata.version(p) for p in
                           ['torch', 'transformers', 'laya', 'numpy', 'pyarrow', 'huggingface-hub', 'PyYAML']},
                  device=torch.cuda.get_device_name(), shape=list(y.shape), sum=float(y.float().sum()), tokenizers={})
    for model in ['llama31_8b_instruct', 'qwen3_8b']:
        tokenizer = AutoTokenizer.from_pretrained(paths[model], local_files_only=True, trust_remote_code=False)
        codes = [tokenizer.encode(s, add_special_tokens=False) for s in CODES]
        if any(len(c) != 1 for c in codes) or len({c[0] for c in codes}) != 151:
            raise ValueError('Candidate codes are not 151 distinct single tokens')
        result['tokenizers'][model] = dict(unique_single_token_codes=151, vocabulary=len(tokenizer))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
