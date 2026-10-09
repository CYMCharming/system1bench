"""Separate source-bound supplement, reusing the immutable v1 request runner."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.evaluation_completion_v1 import run as evaluator
from research.evaluation_completion_v2.adapter import get_adapter

HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / '.aris/evaluation_completion_v2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--model', choices=['english', 'multilingual'])
    args = parser.parse_args()
    if args.prepare:
        if (HERE / 'manifest.json').exists():
            raise ValueError('Already frozen; no overwrite')
        parent = evaluator.read(ROOT / 'research/evaluation_completion_v1/manifest.json')
        evaluator.save(PRIVATE / 'pins.json', evaluator.read(ROOT / '.aris/evaluation_completion_v1/pins.json'))
        manifest = dict(parent, version=2, created_at=datetime.now(timezone.utc).isoformat(),
                        cohort=['english', 'multilingual'], parent_manifest_sha256=evaluator.sha(ROOT / 'research/evaluation_completion_v1/manifest.json'),
                        protocol_sha256=evaluator.sha(HERE / 'PROTOCOL.md'), pins_sha256=evaluator.sha(PRIVATE / 'pins.json'))
        manifest['code_sha256'] = dict(parent['code_sha256'], **{
            p: evaluator.sha(ROOT / p) for p in ['research/evaluation_completion_v2/adapter.py', 'research/evaluation_completion_v2/run.py']})
        evaluator.save(HERE / 'manifest.json', manifest)
        return
    evaluator.HERE, evaluator.PRIVATE, evaluator.get_adapter = HERE, PRIVATE, get_adapter
    evaluator.run(args.model, 'transfer')


if __name__ == '__main__':
    main()
