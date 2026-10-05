"""Thin binding to the byte-frozen evaluator; no old result or code is changed."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import sha
from research.startlux_transfer_v1 import run as evaluator
from research.model_expansion_v3.adapter import get_adapter

HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((HERE / 'manifest.json').read_text())
    assert sha(evaluator.__file__) == manifest['base_runner_sha256']
    evaluator.HERE = HERE
    evaluator.__file__ = __file__
    evaluator.get_adapter = get_adapter
    evaluator.main()


if __name__ == '__main__':
    main()
