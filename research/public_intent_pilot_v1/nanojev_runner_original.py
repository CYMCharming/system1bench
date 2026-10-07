"""Sequential original-precision intent runs, isolated from historical pilots."""
import argparse
import gc
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, request, sha
from system1bench.decision_models import validate_distribution
from research.startlux_transfer_v1.adapter import get_adapter
from research.public_expansion_v1.run import score

PRIVATE = ROOT / '.aris/public_expansion_v1'
OUTPUT = ROOT / '.aris/public_expansion_v2'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def run(model_id, pin, split, manifest, pins_path):
    frozen_path = PRIVATE / f'{split}.frozen.json'
    if sha(frozen_path) != manifest['artifacts_sha256'][f'{split}.frozen.json']:
        raise ValueError('Frozen source bytes mismatch')
    suites = json.loads(frozen_path.read_text(encoding='utf-8'))['suites']
    cases = [(suite['name'], case) for suite in suites for case in suite['cases']]
    n = sum(len(suite['cases']) for suite in suites)
    folder = OUTPUT / split / model_id
    folder.mkdir(parents=True, exist_ok=True)
    binding = dict(model=model_id, expected_requests=n, pilot=split == 'pilot', split=split,
                   accuracy_only=True, shared_gpu=True, timing_comparable=False,
                   frozen_sha256=sha(frozen_path), data_manifest_sha256=sha(ROOT / 'research/public_expansion_v1/manifest.json'),
                   runner_sha256=sha(Path(__file__)), pins_sha256=sha(pins_path),
                   checkpoint={key: value for key, value in pin.items() if key not in {'path', 'base_path'}},
                   adapter_sha256={name: sha(ROOT / name) for name in
                                   ['system1bench/decision_models.py', 'system1bench/llm_adapter.py',
                                    'research/startlux_transfer_v1/adapter.py', 'research/model_expansion_v2/adapter.py']})
    if (folder / 'binding.json').exists() and json.loads((folder / 'binding.json').read_text()) != binding:
        raise ValueError('Resume binding changed')
    if (folder / 'DONE.json').exists():
        print(model_id + ': already complete; no repeated inference', flush=True)
        return
    save(folder / 'binding.json', binding)
    for key in ['path', 'base_path']:
        if key in pin:
            config = Path(pin[key]) / 'config.json'
            if config.exists() and json.loads(config.read_text()).get('quantization_config'):
                raise ValueError('Quantized checkpoint rejected')
    adapter = get_adapter(model_id, pin, load=False)
    audits = []
    for suite, case in cases:
        result = adapter.audit(**request(case))
        if not result['decision']['complete'] or result['decision']['options'] != len(case['questions']['decision']['criteria']):
            raise ValueError('Full ontology incompatible')
        audits.append(dict(id=case['id'], suite=suite, audit=result))
    save(folder / 'compatibility.json', dict(model=model_id, metadata=adapter.metadata,
                                           audited_requests=n, complete=True, cases=audits))
    del adapter
    print(f'{model_id}: preflight {n}/{n} full151/77 PASS', flush=True)
    adapter = get_adapter(model_id, pin, load=True)
    save(folder / 'model_metadata.json', adapter.metadata)
    raw = folder / 'raw.jsonl'
    rows = [json.loads(line) for line in raw.read_text().splitlines()] if raw.exists() else []
    expected = {case['id']: (suite, digest(request(case))) for suite, case in cases}
    seen = set()
    for row in rows:
        if row['id'] in seen or (row['suite'], row['request_sha256']) != expected.get(row['id']):
            raise ValueError('Resume IDs or payload changed')
        seen.add(row['id'])
    with raw.open('a', encoding='utf-8', newline='\n') as stream:
        for suite, case in cases:
            if case['id'] in seen:
                continue
            row = dict(id=case['id'], suite=suite, request_sha256=digest(request(case)))
            try:
                prediction, probabilities = validate_distribution(case['questions']['decision'], adapter.predict(**request(case))['decision'])
                row.update(prediction=prediction, probabilities=probabilities, error=None)
            except Exception as exc:
                row.update(prediction=None, probabilities=None, error=type(exc).__name__)
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            rows.append(row)
            if len(rows) % 100 == 0 or len(rows) == n:
                save(folder / 'status.json', dict(model=model_id, n=n, completed=len(rows),
                                                updated_at=datetime.now(timezone.utc).isoformat()))
                print(f'{model_id}: {len(rows)}/{n}', flush=True)
    summary = {suite['name']: score(suite['cases'], [row for row in rows if row['suite'] == suite['name']]) for suite in suites}
    save(folder / 'summary.json', dict(model=model_id, pilot=split == 'pilot', official_full_test=split == 'full',
                                     accuracy_only=True, latency_not_reported=True, metrics=summary))
    save(folder / 'DONE.json', dict(model=model_id, n=n,
                                   **{key + '_sha256': sha(folder / name) for key, name in
                                      [('binding', 'binding.json'), ('raw', 'raw.jsonl'), ('metadata', 'model_metadata.json'),
                                       ('summary', 'summary.json'), ('compatibility', 'compatibility.json')]}))
    print(f'{model_id}: DONE {n}/{n}', flush=True)
    del adapter
    gc.collect()
    import torch
    torch.cuda.empty_cache()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--split', choices=['pilot', 'full'], default='pilot')
    args = parser.parse_args()
    pins_path = ROOT / '.aris/startlux_transfer_paths.json'
    pins = json.loads(pins_path.read_text())
    manifest = json.loads((ROOT / 'research/public_expansion_v1/manifest.json').read_text())
    for model_id in args.models:
        if model_id not in pins:
            raise ValueError('No pinned original checkpoint: ' + model_id)
        try:
            run(model_id, pins[model_id], args.split, manifest, pins_path)
        except Exception as exc:
            save(OUTPUT / args.split / model_id / 'admission_error.json',
                 dict(model=model_id, error=type(exc).__name__, detail=str(exc), scored=False))
            print(f'{model_id}: NOT ADMITTED {type(exc).__name__}: {exc}', flush=True)
            gc.collect()
            import torch
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
