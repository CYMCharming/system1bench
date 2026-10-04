"""Fetch revision-pinned source artifacts; no model inference or source execution."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'cladder.zip': ('https://raw.githubusercontent.com/causalNLP/cladder/3d2d1169b4b939a09048a6a75956c8972a93cc38/data/cladder-v1.zip', None),
    'cladder_LICENSE': ('https://raw.githubusercontent.com/causalNLP/cladder/3d2d1169b4b939a09048a6a75956c8972a93cc38/LICENSE', None),
    'finentity.json': ('https://raw.githubusercontent.com/yixuantt/FinEntity/3b6cedc5485b669c2ed168f1d949f517636eb7b8/data/FinEntity.json', None),
    'finentity_README.md': ('https://raw.githubusercontent.com/yixuantt/FinEntity/3b6cedc5485b669c2ed168f1d949f517636eb7b8/readme.md', None),
    'cruxeval.jsonl': ('https://raw.githubusercontent.com/facebookresearch/cruxeval/190faf16d175b5847b0af05d937872b1fb395942/data/cruxeval.jsonl', None),
    'crux_generations.json': ('https://raw.githubusercontent.com/facebookresearch/cruxeval/190faf16d175b5847b0af05d937872b1fb395942/samples/model_generations/sample_codellama-7b_temp0.2_output/generations.json', None),
    'crux_flags.json': ('https://raw.githubusercontent.com/facebookresearch/cruxeval/190faf16d175b5847b0af05d937872b1fb395942/samples/evaluation_results/sample_scored_codellama-7b_temp0.2_output.json', None),
    'crux_LICENSE': ('https://raw.githubusercontent.com/facebookresearch/cruxeval/190faf16d175b5847b0af05d937872b1fb395942/LICENSE', None),
    'when2call.jsonl': ('https://huggingface.co/datasets/nvidia/When2Call/resolve/0582f7749df63a96fdc3070932e83e72396ace53/test/when2call_test_mcq.jsonl', '8c3694e583eeeb8dbc297e6cd90da70efc68efa4b6adb7227523e828c6b7b14c'),
    'when2call_README.md': ('https://huggingface.co/datasets/nvidia/When2Call/resolve/0582f7749df63a96fdc3070932e83e72396ace53/README.md', None),
    'pilot_inputs.jsonl': ('https://raw.githubusercontent.com/InternLM/Intern-Decision/3572c8a68b5df5dafe02d0e093989ba8ec0183bc/benchmarks/known-distribution-pilot-v1/inputs.jsonl', '54a2c97dffd972aa0c2ca0ba9386d79a63e369a1bd4f6913ed533ae32f0aff91'),
    'pilot_references.jsonl': ('https://raw.githubusercontent.com/InternLM/Intern-Decision/3572c8a68b5df5dafe02d0e093989ba8ec0183bc/benchmarks/known-distribution-pilot-v1/references.jsonl', '2aed5e4ac334a4caa234bf784796008a6d2be285619564bbc01df3dc7d765eb6'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'data/startlux_transfer_v1/raw')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        name, (url, expected) = item
        target = args.out / name
        if not target.exists():
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        blob = target.read_bytes()
        actual = hashlib.sha256(blob).hexdigest()
        assert expected is None or actual == expected, name
        print('SOURCE', name, len(blob), actual, flush=True)
        return name, dict(url=url, sha256=actual, size=len(blob))

    with ThreadPoolExecutor(4) as pool:
        receipt = dict(pool.map(fetch, FILES.items()))
    dest = args.out / 'source_receipt.json'
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + '\n'
    if dest.exists():
        assert json.loads(dest.read_text(encoding='utf-8')) == receipt
    else:
        dest.write_text(payload, encoding='utf-8')


if __name__ == '__main__':
    main()
