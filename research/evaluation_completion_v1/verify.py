"""Public-only checks: full prediction vectors, metrics and complete-case ranks."""
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.startlux_transfer_v1.analyze import metrics as transfer_metrics

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def verify_identity(name, receipt):
    identity = receipt['historical_weight_identity']
    if name == 'jev-1.13.0':
        assert identity['model_version'] == name
        return
    original = read(ROOT / identity['source'])
    assert digest(original) == identity['metadata_content_sha256']
    original_weights = original['signature']['model']['model_files_sha256']
    current_weights = receipt['model_files_sha256']
    assert identity['weight_files'] == len(identity['weight_sha256']) > 0
    assert all(original_weights[k] == value == current_weights[k] for k, value in identity['weight_sha256'].items())
    assert all(original['signature']['model']['base_files_sha256'][k] == value == receipt['base_files_sha256'][k]
               for k, value in identity['base_weight_sha256'].items())


def main():
    result, manifest = read(HERE / 'results.json'), read(HERE / 'manifest.json')
    assert result['manifest_sha256'] == sha(HERE / 'manifest.json')
    assert manifest['protocol_sha256'] == sha(HERE / 'PROTOCOL.md')
    for p, expected_hash in manifest['code_sha256'].items():
        assert hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected_hash
    if 'supplement_manifest' in result:
        entry = result['supplement_manifest']
        assert sha(ROOT / entry['path']) == entry['sha256']
        adapted = read(ROOT / entry['path'])
        assert adapted['parent_manifest_sha256'] == result['manifest_sha256']
        assert adapted['inputs'] == manifest['inputs'] and adapted['model_pins'] == manifest['model_pins']
        assert adapted['protocol_sha256'] == sha(ROOT / 'research/evaluation_completion_v2/PROTOCOL.md')
        for p, expected_hash in adapted['code_sha256'].items():
            assert hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected_hash
    assert set(result['coverage']) == set(manifest['cohort']) and len(result['coverage']) == 23
    assert result['complete_models'] == len(result['models'])
    assert result['eligible_models'] == 17 and result['all_eligible_complete'] == (len(result['models']) == 17)
    ref = result['intent_references']
    assert sha(ROOT / ref['path']) == ref['sha256'] and ref['n'] == 8580
    reference_data = json.loads(gzip.decompress((ROOT / ref['path']).read_bytes()))
    references = reference_data['intent']
    transfer_references = {(r['suite'], r['id'], r['qid']): r for r in reference_data['transfer']}
    assert len(transfer_references) == ref['transfer_n'] == 1152
    assert ref['transfer_frozen_sha256'] == manifest['inputs']['transfer']['sha256']
    expected = {(suite, row[0]): row for suite, task in references.items() for row in task['rows']}
    assert len(expected) == 8580
    for key, item in result['projections'].items():
        path = ROOT / item['path']
        assert sha(path) == item['sha256']
        data = json.loads(gzip.decompress(path.read_bytes()))
        assert len(data['rows']) == item['n']
        panel, name = key.split('/')
        if panel == 'transfer':
            entry = result['transfer_additions'][name]
            verify_identity(name, entry['receipt'])
            if name in {'english', 'multilingual'}:
                assert entry['receipt']['binding']['manifest_sha256'] == result['supplement_manifest']['sha256']
                assert entry['receipt']['native_interface_unchanged'] is False
                assert entry['receipt']['adapter'] == 'laya_full_option_text'
            seen, rows = set(), []
            for values in data['rows']:
                row = dict(zip(data['fields'], values))
                k = row['suite'], row['id'], row['qid']
                assert k in transfer_references and k not in seen
                seen.add(k)
                reference = transfer_references[k]
                assert all(row[f] == reference[f] for f in ['request_sha256', 'gold'])
                labels = row.get('labels', data['labels'][row['suite']])
                assert labels == reference['labels']
                if row['error'] is None:
                    ps = row['probabilities']
                    assert len(ps) == len(labels) and all(math.isfinite(p) and 0 <= p <= 1 for p in ps)
                    assert abs(sum(ps) - 1) < 1e-5 and row['prediction'] in labels
                    assert abs(ps[labels.index(row['prediction'])] - max(ps)) < 1e-12
                    row['probabilities'] = dict(zip(labels, ps))
                else:
                    assert row['probabilities'] is None and row['prediction'] is None
                rows.append(dict(reference, **row))
            assert seen == set(transfer_references)
            assert digest(transfer_metrics(rows)) == digest(entry['metrics'])
            continue
        assert panel == 'intent'
        verify_identity(name, result['intent'][name]['receipt'])
        seen, per_suite = set(), {}
        for values in data['rows']:
            row = dict(zip(data['fields'], values))
            k = row['suite'], row['id']
            assert k in expected and k not in seen
            seen.add(k)
            assert [row['id'], row['request_sha256'], row['gold']] == expected[k]
            labels = data['labels'][row['suite']]
            assert labels == references[row['suite']]['labels']
            if row['error'] is None:
                ps = row['probabilities']
                assert len(ps) == len(labels) and all(math.isfinite(p) and 0 <= p <= 1 for p in ps)
                assert abs(sum(ps) - 1) < 1e-5 and row['prediction'] in labels
                assert abs(ps[labels.index(row['prediction'])] - max(ps)) < 1e-12
            else:
                assert row['probabilities'] is None and row['prediction'] is None
            per_suite.setdefault(row['suite'], []).append(row)
        assert seen == set(expected)
        for suite, rows in per_suite.items():
            cell = result['intent'][name]['metrics'][suite]
            correct = sum(r['prediction'] == r['gold'] for r in rows)
            assert correct == cell['correct'] and len(rows) == cell['n']
            assert math.isclose(correct / len(rows), cell['score'], abs_tol=1e-12)
            support, predicted, tp = Counter(), Counter(), Counter()
            for row in rows:
                support[row['gold']] += 1
                if row['prediction'] is not None:
                    predicted[row['prediction']] += 1
                if row['gold'] == row['prediction']:
                    tp[row['gold']] += 1
            f1 = sum(2 * tp[label] / (support[label] + predicted[label])
                     if support[label] + predicted[label] else 0 for label in data['labels'][suite]) / len(data['labels'][suite])
            assert math.isclose(f1, cell['macro_f1'], abs_tol=1e-12)
            assert sum(r['error'] is not None for r in rows) == cell['failures']
    excluded = set(manifest['unsupported_choice_caps'])
    assert not (set(result['models']) & excluded)
    assert set(result['native_limit_evidence']) == excluded
    for name, coverage in result['coverage'].items():
        assert coverage['classification_tasks'] == len(coverage['completed_tasks'])
        assert set(coverage['completed_tasks']) | set(coverage['missing_tasks']) == set(result['tasks'])
        assert not (set(coverage['completed_tasks']) & set(coverage['missing_tasks']))
        if coverage['status'] == 'complete':
            assert name in result['models'] and coverage['classification_tasks'] == 11
    for name, model in result['models'].items():
        assert model['complete'] and model['classification_tasks'] == 11
        metrics = model['metrics']
        assert all(0 <= metrics[t]['score'] <= 1 for t in result['tasks'])
        domain_scores = []
        for tasks in manifest['domains'].values():
            domain_scores.append(sum(metrics[t]['score'] for t in tasks) / len(tasks))
        assert math.isclose(sum(domain_scores) / 8, metrics['overall_domain_equal']['score'], abs_tol=1e-12)
        assert math.isclose(sum(metrics[t]['score'] for t in result['tasks']) / 11,
                            metrics['overall_task_equal']['score'], abs_tol=1e-12)
        for key, old in result['intent'][name]['metrics'].items():
            assert metrics[key] == old
    print('PASS: full 151/77-choice vectors; exact denominators; macro F1; complete-case eight-domain scores;',
          result['complete_models'], '/', result['eligible_models'], 'models complete')


if __name__ == '__main__':
    main()
