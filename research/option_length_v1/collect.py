"""Project frozen option lengths and historical choices; never run inference.

Question/state/candidate text stays private. Public outputs contain IDs,
candidate hashes, description lengths and choices only. Every choice is joined
to the full frozen request hash and gold, and original-task counts are checked
against the published common-suite table before anything is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED = dict(refund=96, access=96, routing=96, legal=144, science=339,
                cladder=144, cruxeval=128, finentity=128, when2call=128)
MAIN_V1 = {'kev_08b', 'kev_4b', 'kev_9b', 'nanojev', 'qwen35_9b'}
MAIN_V2 = {'kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b'}
MAIN_NATIVE = {'startlux_4b', 'startlux_9b', 'startlux_27b', 'intern_4b'}
NATURAL = {'contractnli': 'legal', 'scifact3': 'science'}


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def file_hash(path: Path, text_lf: bool = False) -> str:
    content = path.read_bytes()
    if text_lf:
        content = content.replace(b'\r\n', b'\n')
    return hashlib.sha256(content).hexdigest()


def family(model: str) -> str:
    if model in {'english', 'multilingual'}:
        return 'representation'
    if model.startswith(('llama', 'qwen')):
        return 'general'
    return 'decision'


class SourceReader:
    """Read source artifacts once while retaining deterministic byte receipts."""

    def __init__(self, root: Path):
        self.root = root
        self.receipts = {}

    def record(self, path: Path, *, expected=None, text_lf=False, role='predictions'):
        path = path.resolve()
        relative = path.relative_to(self.root).as_posix()
        value = file_hash(path, text_lf)
        if expected is not None and value != expected:
            raise ValueError('Source hash mismatch: ' + relative)
        entry = dict(path=relative, sha256=value,
                     hash_mode='text_lf' if text_lf else 'bytes', role=role)
        old = self.receipts.setdefault(relative, entry)
        if old != entry:
            raise ValueError('Conflicting source receipt: ' + relative)
        return value

    def json(self, relative: str, role='metadata'):
        path = self.root / relative
        self.record(path, text_lf=True, role=role)
        return read(path)

    def journal(self, relative: str, expected: str):
        path = self.root / relative
        self.record(path, expected=expected, text_lf=True)
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]

    def zipped(self, relative: str, expected: str):
        path = self.root / relative
        self.record(path, expected=expected)
        return json.loads(gzip.decompress(path.read_bytes()))


def frozen_inputs(root: Path, source: SourceReader, main_path=None, transfer_path=None):
    manifest_main = source.json('research/model_expansion_v1/manifest.json')
    manifest_transfer = source.json('research/startlux_transfer_v1/manifest.json')
    specs = {
        'main': ('research/model_expansion_v1/frozen.json',
                 '.aris/option_length_v1/main.frozen.json',
                 manifest_main['prepared_sha256'], main_path),
        'transfer': ('data/startlux_transfer_v1/frozen.json',
                     '.aris/option_length_v1/transfer.frozen.json',
                     manifest_transfer['frozen_sha256'], transfer_path),
    }
    frozen, private = {}, {}
    for panel, (canonical, fallback, expected, override) in specs.items():
        path = Path(override) if override is not None else root / canonical
        if not path.exists() and override is None:
            path = root / fallback
        if file_hash(path) != expected:
            raise ValueError('Frozen input hash mismatch: ' + panel)
        frozen[panel] = read(path)
        private[panel] = dict(canonical_path=canonical, sha256=expected,
                              hash_mode='bytes', source_text_included=False)
    return frozen, private


def selected_cases(frozen):
    """Same nine original tasks plus natural/transfer option-order controls."""
    selected = []
    for suite in frozen['main']['suites']:
        name = suite['name']
        if name.startswith('policy_'):
            task, qid = name.removeprefix('policy_'), 'action'
            cases = [c for c in suite['cases'] if c['expansion_condition'] == 'original']
            condition = 'original'
        else:
            prefix = next((p for p in NATURAL if name.startswith(p + '_')), None)
            if prefix is None or name.endswith('_exact_repeat'):
                continue
            task, qid = NATURAL[prefix], 'answer'
            if name.endswith('_base'):
                condition = 'original'
            elif name.endswith('_reversed_option_order'):
                condition = 'reversed'
            else:
                continue
            cases = suite['cases']
        for case in cases:
            selected.append(('main', name, task, qid, condition, case))
    for suite in frozen['transfer']['suites']:
        task = suite['name']
        if task == 'known_distribution':
            continue
        if task not in EXPECTED:
            raise ValueError('Unexpected transfer task: ' + task)
        for case in suite['cases']:
            condition = case['expansion_condition']
            if condition not in {'original', 'reversed'}:
                raise ValueError('Unexpected transfer condition: ' + condition)
            selected.append(('transfer', task, task, 'decision', condition, case))
    return selected


def historical_main(source, model, history):
    rows = []
    for receipt in history['models'][model]['source_receipts']:
        relative = receipt['path']
        suite = Path(relative).name.removesuffix('.json.gz')
        data = source.zipped(relative, receipt['sha256'])
        # Policy files contain additional conditions beyond the frozen main
        # population. The exact-key whitelist is applied by load_predictions.
        rows.extend(dict(row, suite=suite) for row in data['rows'])
    return rows


def native_main(source, model):
    if model in MAIN_V1:
        folder = 'research/model_expansion_v1/results/' + model
    elif model in MAIN_V2:
        folder = 'research/model_expansion_v2/results/' + model
    elif model in MAIN_NATIVE:
        folder = 'research/startlux_transfer_v1/results/main/' + model
    else:
        folder = 'research/model_expansion_v3/results/main/' + model
    metadata = source.json(folder + '/metadata.json')
    if metadata['status'] != 'DONE' or metadata['errors'] != 0:
        raise ValueError('Incomplete historical main: ' + model)
    rows = source.journal(folder + '/raw.jsonl', metadata['raw_sha256'])
    if len(rows) != 4905:
        raise ValueError('Main journal denominator mismatch: ' + model)
    return rows


def transfer_rows(source, model, completion, transfer, additions):
    if model in completion['transfer_additions']:
        receipt = completion['projections']['transfer/' + model]
        data = source.zipped(receipt['path'], receipt['sha256'])
        if len(data['rows']) != receipt['n']:
            raise ValueError('Projection denominator mismatch: ' + model)
        rows = [dict(zip(data['fields'], row)) for row in data['rows']]
        for row in rows:
            row.setdefault('labels', data['labels'][row['suite']])
    else:
        name = 'jev' if model == 'jev-1.13.0' else model
        base = 'research/model_expansion_v3' if name in additions else 'research/startlux_transfer_v1'
        entry = additions[name] if name in additions else transfer[name]
        folder = base + '/results/transfer/' + name
        metadata = source.json(folder + '/metadata.json')
        if metadata['status'] != 'DONE':
            raise ValueError('Incomplete historical transfer: ' + model)
        if metadata['raw_sha256'] != entry['receipt']['raw_sha256']:
            raise ValueError('Transfer summary receipt mismatch: ' + model)
        rows = source.journal(folder + '/raw.jsonl', entry['receipt']['raw_sha256'])
    if len(rows) != 1152:
        raise ValueError('Transfer journal denominator mismatch: ' + model)
    return rows


def load_predictions(source, frozen, models):
    history = source.json('research/model_expansion_v1/historical_context.json')
    completion = source.json('research/evaluation_completion_v1/results.json')
    transfer = source.json('research/startlux_transfer_v1/summary.json')['transfer']
    additions = source.json('research/model_expansion_v3/summary.json')['transfer']
    expected = {}
    for panel, data in frozen.items():
        expected[panel] = {(suite['name'], case['id'], qid): case
                           for suite in data['suites'] for case in suite['cases']
                           for qid in case['questions']}
    if len(expected['main']) != 4905 or len(expected['transfer']) != 1152:
        raise ValueError('Unexpected frozen population')
    predictions = {}
    for model in models:
        main = historical_main(source, model, history) if model in history['models'] else native_main(source, model)
        for panel, rows in [('main', main), ('transfer', transfer_rows(source, model, completion, transfer, additions))]:
            mapping = {}
            for row in rows:
                key = row['suite'], row['id'], row['qid']
                if key not in expected[panel]:
                    if panel == 'main' and model in history['models']:
                        continue
                    raise ValueError('Unexpected prediction key: ' + repr(key))
                if key in mapping:
                    raise ValueError('Duplicate prediction key: ' + repr(key))
                case = expected[panel][key]
                payload = dict(state=case['state'], questions=case['questions'])
                request_sha = digest(payload)
                if case['request_sha256'] != request_sha or row['request_sha256'] != request_sha:
                    raise ValueError('Request hash mismatch: ' + model + '/' + repr(key))
                if str(case['gold'][key[2]]['label']) != row['gold']:
                    raise ValueError('Gold mismatch: ' + model + '/' + repr(key))
                question = case['questions'][key[2]]
                if question['type'] == 'choice':
                    labels = list(question['criteria'])
                    if row['labels'] != labels:
                        raise ValueError('Ordered labels mismatch: ' + model + '/' + repr(key))
                    if row['error'] is None and row['prediction'] not in labels:
                        raise ValueError('Invalid prediction: ' + model + '/' + repr(key))
                if row['error'] is not None and row['prediction'] is not None:
                    raise ValueError('Failed row has a prediction: ' + model + '/' + repr(key))
                mapping[key] = row
            if set(mapping) != set(expected[panel]):
                raise ValueError('Prediction coverage mismatch: ' + model + '/' + panel)
            predictions[panel, model] = mapping
    return predictions


def collect(root: Path = ROOT, *, main_path=None, transfer_path=None):
    root = root.resolve()
    source = SourceReader(root)
    common = source.json('research/common_suite_v1/scores.json', role='published_accuracy_reference')
    models = {name: dict(label=entry['label'], family=family(name))
              for name, entry in common['models'].items()}
    if len(models) != 23:
        raise ValueError('Expected the complete 23-model common-suite cohort')
    frozen, private = frozen_inputs(root, source, main_path, transfer_path)
    predictions = load_predictions(source, frozen, models)
    selected = selected_cases(frozen)
    items = []
    for panel, suite, task, qid, condition, case in selected:
        question = case['questions'][qid]
        labels = list(question['criteria'])
        descriptions = list(question['criteria'].values())
        if question['type'] != 'choice' or not all(isinstance(s, str) for s in descriptions):
            raise ValueError('Unsupported candidate description representation')
        gold = labels.index(str(case['gold'][qid]['label']))
        choices, errors = {}, {}
        for model in models:
            row = predictions[panel, model][suite, case['id'], qid]
            choices[model] = None if row['prediction'] is None else labels.index(row['prediction'])
            if row['error'] is not None:
                errors[model] = row['error']
        items.append(dict(task=task, id=case['id'], base_id=case.get('base_id', case['id']),
                          qid=qid, group=case['group'], condition=condition,
                          request_sha256=case['request_sha256'], labels=labels, gold=gold,
                          lengths=[sum(not c.isspace() for c in text) for text in descriptions],
                          word_lengths=[len(text.split()) for text in descriptions],
                          candidate_hashes=[hashlib.sha256(text.encode('utf-8')).hexdigest() for text in descriptions],
                          predictions=choices, errors=errors))
    keys = [(x['task'], x['id'], x['condition']) for x in items]
    if len(set(keys)) != len(items) or len(items) != 2310:
        raise ValueError('Unexpected selected observation population')
    original = [x for x in items if x['condition'] == 'original']
    if Counter(x['task'] for x in original) != EXPECTED:
        raise ValueError('Original task denominator mismatch')
    replay = {}
    for model in models:
        replay[model] = {}
        for task, expected_n in EXPECTED.items():
            rows = [x for x in original if x['task'] == task]
            correct = sum(x['predictions'][model] == x['gold'] for x in rows)
            failures = sum(x['predictions'][model] is None for x in rows)
            reference = common['models'][model]['metrics'][task]
            if reference['n'] != expected_n or reference['correct'] != correct:
                raise ValueError('Published accuracy replay mismatch: ' + model + '/' + task)
            replay[model][task] = dict(n=expected_n, correct=correct, failures=failures)
    sources = list(source.receipts.values())
    data = dict(version=1, protocol='option-length-observations-v1', models=models, items=items,
                length_measure=dict(primary='Unicode non-whitespace characters in candidate description only',
                                    secondary='whitespace-separated words in candidate description only',
                                    tokens_available=False,
                                    token_caveat='No common reference tokenizer is included; character and word counts are not native model token counts.'),
                sources=sources, frozen_sources=private,
                text_included=False, new_inference=False)
    if re.search(r'hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+', compact(data).decode('utf-8')):
        raise ValueError('Forbidden credential-like material in projection')
    bindings = dict(version=1, collector_sha256=file_hash(Path(__file__), text_lf=True),
                    frozen_sources=private, sources=sources,
                    original_items=len(original), reversed_items=len(items) - len(original),
                    tasks=EXPECTED, models=23, joins_verified=True,
                    public_accuracy_replay=replay, text_included=False, new_inference=False)
    return data, bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=HERE)
    parser.add_argument('--main', type=Path)
    parser.add_argument('--transfer', type=Path)
    args = parser.parse_args()
    data, bindings = collect(args.root, main_path=args.main, transfer_path=args.transfer)
    payload = compact(data) + b'\n'
    # GzipFile emits the portable OS=255 header, unlike Python 3.11's
    # gzip.compress(mtime=0) fast path whose OS byte is platform-dependent.
    buffer = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0) as stream:
        stream.write(payload)
    compressed = buffer.getvalue()
    bindings['artifact'] = dict(path='research/option_length_v1/observations.json.gz',
                                sha256=hashlib.sha256(compressed).hexdigest(),
                                uncompressed_sha256=hashlib.sha256(payload).hexdigest(),
                                items=len(data['items']))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'observations.json.gz').write_bytes(compressed)
    (args.output / 'bindings.json').write_bytes((json.dumps(bindings, ensure_ascii=False,
                                                          indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print('Verified 23 models x 9 original tasks; exported', len(data['items']),
          'text-free observations with option-order controls.')


if __name__ == '__main__':
    main()
