"""Read-only completion check; never emit an incomplete model's scores."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, request, sha


def main():
    name = sys.argv[1]
    out = ROOT / '.aris/public_expansion_v1/runs' / name
    done = json.loads((out / 'DONE.json').read_text())
    for key, filename in [('binding_sha256', 'binding.json'), ('raw_sha256', 'raw.jsonl'),
                          ('metadata_sha256', 'model_metadata.json'), ('summary_sha256', 'summary.json'),
                          ('compatibility_sha256', 'compatibility.json')]:
        if done[key] != sha(out / filename):
            raise ValueError('Completion receipt hash mismatch: ' + filename)
    rows = [json.loads(line) for line in (out / 'raw.jsonl').read_text().splitlines()]
    frozen = json.loads((ROOT / '.aris/public_expansion_v1/pilot.frozen.json').read_text())
    expected = {case['id']: (suite['name'], digest(request(case)))
                for suite in frozen['suites'] for case in suite['cases']}
    if done['n'] != 354 or len(rows) != 354 or len({row['id'] for row in rows}) != 354:
        raise ValueError('Completion count invalid')
    for row in rows:
        if (row['suite'], row['request_sha256']) != expected[row['id']]:
            raise ValueError('Request replay mismatch')
    print(json.dumps(dict(model=name, verified=True, n=354,
                         summary=json.loads((out / 'summary.json').read_text())), ensure_ascii=False))


if __name__ == '__main__':
    main()
