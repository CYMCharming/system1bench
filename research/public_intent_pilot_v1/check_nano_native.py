"""Six-case direct upstream replay of the unusual NanoJev pilot outputs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.aris/vendor/nanojev-scripts'))
from predict_toy_decisions import DecisionPredictor
import torch


def main():
    torch.set_num_threads(4)
    torch.manual_seed(0)
    pin = json.loads((ROOT / '.aris/startlux_transfer_paths.json').read_text())['nanojev']
    model = DecisionPredictor(pin['path'], max_length=32768, precision='bf16', disable_native_triton=False)
    suites = json.loads((ROOT / '.aris/public_expansion_v1/pilot.frozen.json').read_text())['suites']
    raw = {row['id']: row for row in map(json.loads, (ROOT / '.aris/public_expansion_v2/pilot/nanojev/raw.jsonl').read_text().splitlines())}
    checks = []
    for suite in suites:
        for index in [0, len(suite['cases']) // 2, len(suite['cases']) - 1]:
            case = suite['cases'][index]
            payload = {'states': [{'id': 'input', 'state': case['state'], 'questions': case['questions']}]}
            direct = model.predict(payload)['states'][0]['answers']['decision']['probabilities']
            total = sum(direct.values())
            normalized = {key: float(value) / total for key, value in direct.items()}
            stored = raw[case['id']]['probabilities']
            if set(normalized) != set(stored):
                raise ValueError('Native label mapping mismatch')
            delta = max(abs(normalized[key] - stored[key]) for key in normalized)
            native_prediction = max(normalized, key=normalized.get)
            if delta > 1e-6 or native_prediction != raw[case['id']]['prediction']:
                raise ValueError('Direct native output does not replay')
            checks.append({'id': case['id'], 'suite': suite['name'], 'max_probability_delta': delta,
                           'prediction_matches': True, 'candidate_count': len(normalized)})
    result = {'model': 'nanojev', 'sampled_cases': 6, 'full_pilot_cases': 354,
              'direct_upstream_replay': True, 'checks': checks,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Selected first/middle/last per suite; not a complete rerun or a causal explanation of low accuracy.'}
    (ROOT / '.aris/public_expansion_v2/pilot/nanojev/direct_replay.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(result))


if __name__ == '__main__':
    main()
