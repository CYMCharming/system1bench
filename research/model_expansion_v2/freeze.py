"""Create an immutable public manifest before any new model inference."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write

HERE = ROOT / 'research/model_expansion_v2'
SOURCE = ROOT / 'research/model_expansion_v1'
PINS = {
    'kev_27b': {'repo': 'jaredpalmer/kev-27b',
                'revision': 'af0e6d551bdc2cc724f3e9d7a8bee1cd4fb8f7bf',
                'base_repo': 'Qwen/Qwen3.8-27B',
                'base_revision': '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'},
    'qwen35_08b': {'repo': 'Qwen/Qwen3.5-0.8B',
                   'revision': '2fc06364715b967f1860aea9cf38778875588b17'},
    'qwen35_4b': {'repo': 'Qwen/Qwen3.5-4B',
                  'revision': '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'},
    'qwen38_27b': {'repo': 'Qwen/Qwen3.8-27B',
                   'revision': '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'},
}


def main():
    old = read(SOURCE / 'manifest.json')
    assert sha(SOURCE / 'frozen.json') == old['prepared_sha256']
    manifest = {
        'protocol': 'system1bench-model-expansion-v2',
        'prepared_sha256': old['prepared_sha256'],
        'previous_manifest_sha256': sha(SOURCE / 'manifest.json'),
        'protocol_sha256': sha(HERE / 'PROTOCOL.md'),
        'adapter_sha256': sha(HERE / 'adapter.py'),
        'runner_sha256': sha(HERE / 'run.py'),
        'shared_adapter_sha256': sha(ROOT / 'system1bench/decision_models.py'),
        'model_pins': PINS,
        'planned_requests_per_model': 2601,
        'planned_decisions_per_model': 4905,
        'source_type': 'the already frozen model_expansion_v1 panel',
        'outcome_selection': False,
    }
    path = HERE / 'manifest.json'
    if path.exists():
        assert read(path) == manifest, 'Frozen manifest must not change'
    else:
        write(path, manifest)
    print('FROZEN', sha(path), len(PINS), flush=True)


if __name__ == '__main__':
    main()
