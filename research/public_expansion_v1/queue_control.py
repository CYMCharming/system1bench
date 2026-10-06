"""CPU preflight the control, then wait for Kev completion before loading it."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.startlux_transfer_v1.adapter import get_adapter
from research.public_expansion_v1.prepare import PRIVATE, save
from system1bench.common import request, sha


def main():
    pins = ROOT / '.aris/startlux_transfer_paths.json'
    pin = json.loads(pins.read_text())['qwen35_4b']
    suites = json.loads((PRIVATE / 'pilot.frozen.json').read_text())['suites']
    adapter = get_adapter('qwen35_4b', pin, load=False)
    reports = []
    for suite in suites:
        case = suite['cases'][0]
        audit = adapter.audit(**request(case))
        if audit['decision']['options'] != len(case['questions']['decision']['criteria']):
            raise ValueError('Control candidate audit failed')
        reports.append(dict(suite=suite['name'], audit=audit))
    if len(adapter.code_ids) != 151 or len(set(adapter.code_ids)) != 151:
        raise ValueError('151 distinct single-token candidate codes required')
    save(PRIVATE / 'runs/control_preflight.json', dict(model='qwen35_4b', representative_requests=reports,
         single_token_candidate_codes=151, passed=True, runner_sha256=sha(ROOT / 'research/public_expansion_v1/run.py'),
         queue_sha256=sha(Path(__file__))))
    del adapter
    print('Qwen3.5-4B tokenizer151 singlecodes/full151+77 format PASS; waiting for Kev DONE before weights', flush=True)
    prior = PRIVATE / 'runs/kev_4b'
    deadline = time.monotonic() + 3600
    while not (prior / 'DONE.json').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('Kev completion not observed within one hour; control was not loaded')
        time.sleep(5)
    done = json.loads((prior / 'DONE.json').read_text())
    if done['n'] != 354 or done['raw_sha256'] != sha(prior / 'raw.jsonl'):
        raise ValueError('Kev DONE integrity failed; control not loaded')
    subprocess.run([sys.executable, str(ROOT / 'research/public_expansion_v1/run.py'), '--model', 'qwen35_4b'],
                   cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
