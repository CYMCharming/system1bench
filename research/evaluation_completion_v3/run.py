"""Immutable native single-request shards and explicit, verified journal union."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.evaluation_completion_v1 import run as evaluator
from system1bench.common import digest, labels, request, sha

HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / '.aris/evaluation_completion_v3'
FILES = dict(binding='binding.json', raw='raw.jsonl', metadata='model_metadata.json',
             compatibility='compatibility.json')
MODELS = ('kev_27b', 'qwen38_27b')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def save(path, value):
    evaluator.save(path, value)


def partition_indices(completed, total=8580):
    assert 0 < completed < total
    return [list(range(completed + part, total, 2)) for part in range(2)]


def prepare():
    if (HERE / 'manifest.json').exists():
        raise ValueError('Already frozen; no overwrite')
    parent_path = ROOT / 'research/evaluation_completion_v1/manifest.json'
    parent = read(parent_path)
    frozen_path = ROOT / parent['inputs']['intent']['path']
    assert sha(frozen_path) == parent['inputs']['intent']['sha256']
    frozen = read(frozen_path)
    cases = [(s, c) for s in frozen['suites'] for c in s['cases']]
    assert len(cases) == 8580 and all(list(c['questions']) == ['decision'] for _, c in cases)
    manifest = dict(parent, version=3, cohort=list(MODELS),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    protocol_sha256=sha(HERE / 'PROTOCOL.md'),
                    parent_manifest_sha256=sha(parent_path), plans={})
    manifest['code_sha256'] = dict(parent['code_sha256'], **{
        'research/evaluation_completion_v3/run.py': sha(HERE / 'run.py')})
    pins_path = ROOT / '.aris/evaluation_completion_v1/pins.json'
    assert sha(pins_path) == parent['pins_sha256']
    for name in MODELS:
        original = ROOT / '.aris/evaluation_completion_v1/intent' / name
        prefix = PRIVATE / 'fragments' / name / 'prefix'
        prefix.mkdir(parents=True, exist_ok=False)
        for file in FILES.values():
            shutil.copyfile(original / file, prefix / file)
        prefix_rows = rows(prefix / 'raw.jsonl')
        n = len(prefix_rows)
        assert 0 < n < 8580
        for (suite, case), row in zip(cases, prefix_rows):
            assert (row['suite'], row['id'], row['qid']) == (suite['name'], case['id'], 'decision')
            assert row['request_sha256'] == digest(request(case))
        binding = read(prefix / 'binding.json')
        assert binding['manifest_sha256'] == sha(parent_path)
        receipt = dict(model=name, panel='intent', kind='immutable_completed_prefix', n=n,
                       **{key + '_sha256': sha(prefix / file) for key, file in FILES.items()})
        save(prefix / 'PREFIX.json', receipt)
        plan = dict(prefix_n=n, prefix_receipt=receipt, shards=[])
        for part, indices in enumerate(partition_indices(n)):
            selected = set(indices)
            private = PRIVATE / 'shards' / name / str(part)
            public = HERE / 'shards' / name / str(part)
            private.mkdir(parents=True, exist_ok=False)
            part_frozen = dict(frozen, suites=[dict(s, cases=[c for i, (source, c) in enumerate(cases)
                                                           if i in selected and source['name'] == s['name']])
                                              for s in frozen['suites']])
            part_frozen['suites'] = [s for s in part_frozen['suites'] if s['cases']]
            save(private / 'frozen.json', part_frozen)
            shutil.copyfile(pins_path, private / 'pins.json')
            public.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(HERE / 'PROTOCOL.md', public / 'PROTOCOL.md')
            part_manifest = dict(manifest, cohort=[name], shard=part,
                                 source_indices=indices, original_expected=8580)
            part_manifest.pop('plans')
            part_manifest['inputs'] = dict(manifest['inputs'], intent=dict(
                path=str((private / 'frozen.json').relative_to(ROOT)),
                sha256=sha(private / 'frozen.json'), expected=len(indices)))
            save(public / 'manifest.json', part_manifest)
            plan['shards'].append(dict(part=part, indices=indices, expected=len(indices),
                frozen_sha256=sha(private / 'frozen.json'),
                manifest_path=str((public / 'manifest.json').relative_to(ROOT)),
                manifest_sha256=sha(public / 'manifest.json')))
        manifest['plans'][name] = plan
    save(HERE / 'manifest.json', manifest)
    print('Frozen two disjoint shards per model; original completed prefixes retained', flush=True)


def fragment(folder, receipt):
    for key, file in FILES.items():
        assert sha(folder / file) == receipt[key + '_sha256']
    raw = rows(folder / 'raw.jsonl')
    assert len(raw) == receipt['n']
    return raw, read(folder / 'model_metadata.json'), read(folder / 'binding.json'), read(folder / 'compatibility.json')


def verify_union(folder, name, frozen):
    manifest = read(HERE / 'manifest.json')
    plan = manifest['plans'][name]
    cases = [(s, c) for s in frozen['suites'] for c in s['cases']]
    assert len(cases) == 8580
    prefix_folder = folder / 'fragments/prefix'
    prefix_receipt = read(prefix_folder / 'PREFIX.json')
    assert prefix_receipt == plan['prefix_receipt']
    prefix, metadata, binding, compatibility = fragment(prefix_folder, prefix_receipt)
    assert binding['manifest_sha256'] == manifest['parent_manifest_sha256']
    assert binding['frozen_sha256'] == manifest['inputs']['intent']['sha256']
    audits = {(r['suite'], r['id']): r['audit'] for r in compatibility['cases']}
    union = {i: row for i, row in enumerate(prefix)}
    assert len(prefix) == plan['prefix_n']
    for part in plan['shards']:
        source = folder / 'fragments' / str(part['part'])
        done = read(source / 'DONE.json')
        raw, current, current_binding, current_audit = fragment(source, done)
        assert done['n'] == part['expected'] and done['model'] == name and done['panel'] == 'intent'
        assert current_binding['manifest_sha256'] == part['manifest_sha256']
        assert current_binding['frozen_sha256'] == part['frozen_sha256']
        part_manifest = read(ROOT / part['manifest_path'])
        assert sha(ROOT / part['manifest_path']) == part['manifest_sha256']
        assert part_manifest['code_sha256'] == manifest['code_sha256'] == current_binding['code_sha256']
        assert part_manifest['source_indices'] == part['indices']
        for field in ['checkpoint', 'dtype', 'adapter', 'model_files_sha256', 'base_files_sha256', 'vendor_code_sha256']:
            assert metadata.get(field) == current.get(field), 'Changed native identity: ' + field
        assert all(r['audit'] == audits[r['suite'], r['id']] for r in current_audit['cases'])
        assert current_audit['complete'] and current_audit['audited_requests'] == len(raw)
        for i, row in zip(part['indices'], raw):
            assert i not in union
            union[i] = row
        assert sum(r['error'] is not None for r in raw) == done['errors']
    assert set(union) == set(range(8580))
    for i, row in union.items():
        suite, case = cases[i]
        assert row['model'] == name
        assert (row['suite'], row['id'], row['qid']) == (suite['name'], case['id'], 'decision')
        assert row['request_sha256'] == digest(request(case))
        assert row['gold'] == str(case['gold']['decision']['label'])
        assert audits[suite['name'], case['id']]['decision']['options'] == len(labels(case['questions']['decision']))
    return [union[i] for i in range(8580)], metadata, compatibility


def merge(name):
    manifest = read(HERE / 'manifest.json')
    assert all(sha(ROOT / p) == value for p, value in manifest['code_sha256'].items())
    frozen_path = ROOT / manifest['inputs']['intent']['path']
    assert sha(frozen_path) == manifest['inputs']['intent']['sha256']
    folder = PRIVATE / 'intent' / name
    if (folder / 'DONE.json').exists():
        raise ValueError('Already merged; no overwrite')
    fragments = folder / 'fragments'
    shutil.copytree(PRIVATE / 'fragments' / name / 'prefix', fragments / 'prefix')
    for part in range(2):
        shutil.copytree(PRIVATE / 'shards' / name / str(part) / 'intent' / name, fragments / str(part))
    raw, metadata, compatibility = verify_union(folder, name, read(frozen_path))
    metadata = dict(metadata, execution_method='verified disjoint native single-request shard union')
    binding = dict(model=name, panel='intent', kind='verified_shard_union', expected=8580,
                   manifest_sha256=sha(HERE / 'manifest.json'), frozen_sha256=sha(frozen_path),
                   checkpoint=manifest['model_pins'][name], code_sha256=manifest['code_sha256'],
                   original_precision=True, batch_requests=1, timing_comparable=False)
    save(folder / 'binding.json', binding)
    save(folder / 'model_metadata.json', metadata)
    save(folder / 'compatibility.json', compatibility)
    with (folder / 'raw.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
        for row in raw:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    save(folder / 'DONE.json', dict(model=name, panel='intent', kind='verified_shard_union',
        n=len(raw), errors=sum(r['error'] is not None for r in raw),
        finished_at=datetime.now(timezone.utc).isoformat(),
        **{key + '_sha256': sha(folder / file) for key, file in FILES.items()}))
    print(name, 'VERIFIED UNION', len(raw), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--part', type=int, choices=[0, 1])
    parser.add_argument('--merge', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.merge:
        merge(args.model)
    else:
        assert args.model is not None and args.part is not None
        evaluator.HERE = HERE / 'shards' / args.model / str(args.part)
        evaluator.PRIVATE = PRIVATE / 'shards' / args.model / str(args.part)
        evaluator.run(args.model, 'intent')


if __name__ == '__main__':
    main()
