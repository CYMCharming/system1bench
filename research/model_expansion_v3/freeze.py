"""Freeze this additive cohort before the first evaluated decision."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import sha
from research.startlux_transfer_v1.run import save

HERE = Path(__file__).resolve().parent
COHORT = ['intern_08b', 'intern_2b', 'llama32_1b_public', 'llama32_3b_public', 'qwen3_17b', 'qwen3_8b']


def main():
    assert not list((HERE / 'results').glob('*/*/raw.jsonl')), 'Do not rewrite a running protocol'
    previous = json.loads((ROOT / 'research/startlux_transfer_v1/manifest.json').read_text())
    pins = {name: json.loads((ROOT / '.aris/family_v3' / (name + '.json')).read_text()) for name in COHORT}
    manifest = dict(seed=previous['seed'], expected_decisions=previous['expected_decisions'],
        frozen_sha256=previous['frozen_sha256'], source_quality_sha256=previous['source_quality_sha256'],
        prepared_main_sha256=json.loads((ROOT / 'research/model_expansion_v2/manifest.json').read_text())['prepared_sha256'],
        protocol_sha256=sha(HERE / 'PROTOCOL.md'), cohort=COHORT,
        base_runner_sha256=sha(ROOT / 'research/startlux_transfer_v1/run.py'),
        base_protocol_sha256=previous['protocol_sha256'],
        code_sha256={n: sha(HERE / n) for n in ('adapter.py', 'run.py')},
        model_pins={n: {k: pins[n][k] for k in ('repo', 'revision')} for n in COHORT},
        admission_policy='per-model upstream weight and input-file verification before inference; receipt bound in run signature')
    save(HERE / 'manifest.json', manifest)
    print('FROZEN', len(COHORT), flush=True)


if __name__ == '__main__':
    main()
