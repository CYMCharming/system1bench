"""Inspect native Laya refusals without truncating or scoring any request."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.evaluation_completion_v1.adapter import get_adapter
from research.evaluation_completion_v1.run import read, save


def main():
    name = sys.argv[1]
    pin = read(ROOT / '.aris/evaluation_completion_v1/pins.json')[name]
    adapter = get_adapter(name, pin)
    failures = []
    for suite in read(ROOT / 'data/startlux_transfer_v1/frozen.json')['suites']:
        for case in suite['cases']:
            audit = adapter.audit(case['state'], case['questions'])
            if not all(value['complete'] for value in audit.values()):
                failures.append(dict(id=case['id'], suite=suite['name'], audit=audit))
    save(ROOT / '.aris/evaluation_completion_v1' / ('audit_' + name + '.json'),
         dict(model=name, failed_inputs=failures, n=len(failures)))
    print(json.dumps(dict(model=name, n=len(failures), first=failures[:3]), indent=2), flush=True)


if __name__ == '__main__':
    main()
