"""Independent public replay of four new raw runs and source-to-score counts."""

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'research/model_expansion_v2'
OLD = ROOT / 'research/model_expansion_v1'
MODELS = ('kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b')
PAIRINGS = (('kev_27b', 'qwen38_27b'), ('kev_08b', 'qwen35_08b'),
            ('kev_4b', 'qwen35_4b'), ('kev_9b', 'qwen35_9b'))


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    content = path.read_bytes()
    if path.suffix in {'.py', '.json', '.jsonl', '.md', '.csv', '.svg'}:
        content = content.replace(b'\r\n', b'\n')
    return hashlib.sha256(content).hexdigest()


def load_rows(directory, model):
    return [json.loads(line) for line in (directory / 'results' / model / 'raw.jsonl').read_text(
        encoding='utf-8').splitlines()]


def identity(row):
    return row['suite'], row['id'], row['qid']


def form(row):
    return {'original': 'base', 'exact_repeat': 'repeat', 'reversed_option_order': 'reverse',
            'reversed': 'reverse'}.get(row['condition'], row['condition'])


def pair_key(row):
    return (row['family'], row['group'] if row['suite'].startswith('policy_') else row['id'],
            row['qid'], form(row))


def correct(row):
    return row['error'] is None and row['prediction'] == row['gold']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='Write host validation receipt')
    parser.add_argument('--public-only', action='store_true', help='Skip excluded licensed source text')
    args = parser.parse_args()
    manifest = read(HERE / 'manifest.json')
    assert manifest['protocol'] == 'system1bench-model-expansion-v2'
    for filename, field in (('PROTOCOL.md', 'protocol_sha256'), ('adapter.py', 'adapter_sha256'),
                            ('run.py', 'runner_sha256')):
        assert sha(HERE / filename) == manifest[field]
    assert sha(ROOT / 'system1bench/decision_models.py') == manifest['shared_adapter_sha256']
    assert sha(OLD / 'manifest.json') == manifest['previous_manifest_sha256']
    baseline_rows = load_rows(OLD, 'qwen35_9b')
    baseline = {identity(row): row for row in baseline_rows}
    assert len(baseline_rows) == len(baseline) == manifest['planned_decisions_per_model'] == 4905
    assert len({(row['suite'], row['id']) for row in baseline_rows}) == 2601
    reconstructed = False
    frozen = OLD / 'frozen.json'
    if frozen.exists() and not args.public_only:
        assert sha(frozen) == manifest['prepared_sha256']
        expected = {}
        for suite in read(frozen)['suites']:
            for case in suite['cases']:
                payload = {key: case[key] for key in ('state', 'questions')}
                request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False,
                    separators=(',', ':')).encode()).hexdigest()
                assert request_hash == case['request_sha256']
                for qid in case['questions']:
                    expected[(suite['name'], case['id'], qid)] = (request_hash,
                        str(case['gold'][qid]['label']))
        assert len(expected) == len(baseline)
        assert all((row['request_sha256'], row['gold']) == expected[key]
                   for key, row in baseline.items())
        reconstructed = True
    summary_path = HERE / 'summary.json'
    summary = read(summary_path) if summary_path.exists() else None
    if summary:
        assert summary['manifest_sha256'] == sha(HERE / 'manifest.json')
        assert summary['analyzer_sha256'] == sha(HERE / 'analyze.py')
        assert summary['shared_analyzer_sha256'] == sha(OLD / 'analyze.py')
    all_rows = {'qwen35_9b': baseline_rows}
    results = {}
    for model in MODELS:
        directory = HERE / 'results' / model
        metadata = read(directory / 'metadata.json')
        raw = directory / 'raw.jsonl'
        assert metadata['status'] == 'DONE' and metadata['count'] == 4905 and metadata['errors'] == 0
        assert metadata['raw_sha256'] == sha(raw)
        signature = metadata['signature']
        assert signature['manifest_sha256'] == sha(HERE / 'manifest.json')
        assert signature['runner_sha256'] == sha(HERE / 'run.py')
        assert signature['adapter_sha256'] == sha(HERE / 'adapter.py')
        assert signature['shared_adapter_sha256'] == manifest['shared_adapter_sha256']
        assert signature['model']['checkpoint']['repo'] == manifest['model_pins'][model]['repo']
        assert signature['model']['checkpoint']['revision'] == manifest['model_pins'][model]['revision']
        rows = load_rows(HERE, model)
        indexed = {identity(row): row for row in rows}
        assert len(rows) == len(indexed) == len(baseline)
        pairs = {}
        for key, row in indexed.items():
            reference = baseline[key]
            assert row['model'] == model and row['error'] is None
            for field in ('gold', 'request_sha256', 'group', 'family', 'labels'):
                assert row[field] == reference[field], (model, key, field)
            assert row['audit']['complete'] is True and row['audit']['prompt_tokens'] > 0
            assert len(row['audit']['token_sha256']) == 64
            probabilities = row['probabilities']
            assert set(probabilities) == set(row['labels'])
            assert all(math.isfinite(value) and 0 <= value <= 1 for value in probabilities.values())
            assert abs(sum(probabilities.values()) - 1) < 1e-9
            assert probabilities[row['prediction']] == max(probabilities.values())
            case = pair_key(row)
            assert case not in pairs
            pairs[case] = row
        counts = {}
        for family in ('refund', 'access', 'routing', 'contractnli', 'scifact3'):
            qids = ('action', 'review', 'severity') if family in ('refund', 'access', 'routing') else ('answer',)
            for qid in qids:
                base = [row for (fam, _, question, cond), row in pairs.items()
                        if fam == family and question == qid and cond == 'base']
                expected_n = 96 if family in ('refund', 'access', 'routing') else 144 if family == 'contractnli' else 339
                assert len(base) == expected_n
                value = sum(map(correct, base))
                panel = family + '/' + qid
                counts[panel] = value
                if summary:
                    assert summary['models'][model]['panels'][panel]['base']['correct'] == value
                for condition in ('repeat', 'reverse', 'counterfactual'):
                    paired = [(row, pairs.get((family, case, qid, condition)))
                              for (fam, case, question, cond), row in pairs.items()
                              if fam == family and question == qid and cond == 'base']
                    paired = [(left, right) for left, right in paired if right is not None]
                    if not paired:
                        continue
                    assert len(paired) == expected_n
                    if condition == 'repeat':
                        assert all(left['request_sha256'] == right['request_sha256'] and
                                   left['audit']['token_sha256'] == right['audit']['token_sha256']
                                   for left, right in paired)
                    if condition == 'counterfactual' and qid == 'action':
                        assert all(left['gold'] != right['gold'] for left, right in paired)
                    if summary:
                        cell = summary['models'][model]['panels'][panel][condition]
                        assert cell['flip']['count'] == sum(left['prediction'] != right['prediction']
                                                           for left, right in paired)
                        if condition == 'counterfactual':
                            assert cell['both_reference_correct']['count'] == sum(
                                correct(left) and correct(right) for left, right in paired)
                        else:
                            assert cell['correct_stable']['count'] == sum(
                                correct(left) and correct(right) and
                                left['prediction'] == right['prediction'] for left, right in paired)
        if summary:
            assert summary['models'][model]['raw_sha256'] == sha(raw)
            assert summary['models'][model]['metadata_sha256'] == sha(directory / 'metadata.json')
        results[model] = counts
        all_rows[model] = rows
        print('VERIFIED_MODEL', model, len(rows), sum(counts.values()), flush=True)
    if summary:
        for left, right in PAIRINGS:
            if left not in all_rows:
                all_rows[left] = load_rows(OLD, left)
            if right not in all_rows:
                all_rows[right] = load_rows(OLD, right)
            a = {pair_key(row): row for row in all_rows[left]}
            b = {pair_key(row): row for row in all_rows[right]}
            assert set(a) == set(b)
            panels = summary['paired_model_comparisons'][left + '-minus-' + right]
            for panel, values in panels.items():
                family, qid = panel.split('/')
                matched = [key for key in a if key[0] == family and key[2] == qid and key[3] == 'base']
                assert len(matched) == values['base']['n']
                delta = sum(int(correct(a[key])) - int(correct(b[key])) for key in matched) / len(matched)
                assert math.isclose(delta, values['base']['delta'], abs_tol=1e-12)
            for task, saved in summary['complementarity'][left + '-minus-' + right].items():
                matched = [key for key in a if key[0] + '/' + key[2] == task and key[3] == 'base']
                both = sum(correct(a[key]) and correct(b[key]) for key in matched)
                left_only = sum(correct(a[key]) and not correct(b[key]) for key in matched)
                right_only = sum(correct(b[key]) and not correct(a[key]) for key in matched)
                neither = len(matched) - both - left_only - right_only
                assert saved['n'] == len(matched)
                assert (saved['both_correct'], saved['kev_only'], saved['qwen_only'],
                        saved['neither_correct']) == (both, left_only, right_only, neither)
                assert math.isclose(saved['oracle_upper_bound'], 1 - neither / len(matched), abs_tol=1e-12)
    receipt = {'status': 'PASS', 'manifest_sha256': sha(HERE / 'manifest.json'),
               'verifier_sha256': sha(Path(__file__)), 'models': results,
               'summary_sha256': sha(summary_path) if summary else None,
               'source_text_reconstructed_on_research_host': reconstructed}
    destination = HERE / 'verification.json'
    if args.write:
        assert reconstructed and summary, 'Host receipt requires full source and finished analysis'
        destination.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    elif destination.exists():
        saved = read(destination)
        for field in ('status', 'manifest_sha256', 'verifier_sha256', 'models', 'summary_sha256'):
            assert saved[field] == receipt[field]
    print('INPUT_RECONSTRUCTION', reconstructed, flush=True)


if __name__ == '__main__':
    main()
