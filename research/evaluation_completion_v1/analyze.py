"""Independent full-run replay and complete-case eight-domain ranking."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.public_intent_pilot_v1.analyze import summarize
from research.startlux_transfer_v1.analyze import metrics as transfer_metrics

HERE = Path(__file__).resolve().parent
TASKS = ['refund', 'access', 'routing', 'legal', 'science', 'cladder', 'cruxeval',
         'finentity', 'when2call', 'clinc150_full', 'banking77_full']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def verify(folder, name, panel, frozen, legacy=False):
    done = read(folder / 'DONE.json')
    expected_n = 8580 if panel == 'intent' else 1152
    assert done['n'] == expected_n and done['model'] == name
    files = [('binding', 'binding.json'), ('raw', 'raw.jsonl'), ('metadata', 'model_metadata.json'),
             ('compatibility', 'compatibility.json')]
    if legacy:
        files.append(('summary', 'summary.json'))
    for key, file in files:
        assert done[key + '_sha256'] == sha(folder / file), 'Completion hash: ' + file
    binding = read(folder / 'binding.json')
    if legacy:
        assert binding['frozen_sha256'] == sha(folder.parent / 'full.frozen.json')
        assert binding['data_manifest_sha256'] == sha(folder.parent / 'manifest.json')
        assert binding['runner_sha256'] == sha(folder.parent / 'run_cohort.py')
    else:
        manifest = read(HERE / 'manifest.json')
        if binding['manifest_sha256'] != sha(HERE / 'manifest.json'):
            supplement = HERE.parent / 'evaluation_completion_v2/manifest.json'
            adapted = read(supplement)
            assert panel == 'transfer' and name in {'english', 'multilingual'}
            assert binding['manifest_sha256'] == sha(supplement)
            assert adapted['parent_manifest_sha256'] == sha(HERE / 'manifest.json')
            assert adapted['inputs'] == manifest['inputs'] and adapted['model_pins'] == manifest['model_pins']
            assert all(adapted['code_sha256'][p] == value for p, value in manifest['code_sha256'].items())
            assert adapted['protocol_sha256'] == sha(supplement.parent / 'PROTOCOL.md')
            manifest = adapted
        assert binding['code_sha256'] == manifest['code_sha256']
        assert binding['frozen_sha256'] == manifest['inputs'][panel]['sha256']
        assert binding['checkpoint'] == manifest['model_pins'][name]
    compatibility = read(folder / 'compatibility.json')
    assert compatibility['complete'] and compatibility['audited_requests'] == expected_n
    metadata = read(folder / 'model_metadata.json')
    assert metadata['truncation'] is False and metadata.get('quantized') is not True
    checkpoint = {k: v for k, v in binding['checkpoint'].items() if k != 'downloaded'}
    measured = {k: v for k, v in metadata['checkpoint'].items() if k != 'downloaded'}
    assert measured == checkpoint
    raw = [json.loads(line) for line in (folder / 'raw.jsonl').read_text().splitlines()]
    by_key = {(r['suite'], r['id'], r.get('qid', 'decision')): r for r in raw}
    expected = {(s['name'], c['id'], q): (s, c) for s in frozen['suites'] for c in s['cases'] for q in c['questions']}
    assert len(raw) == len(by_key) == expected_n and set(by_key) == set(expected)
    audited = {(r['suite'], r['id']): r['audit'] for r in compatibility['cases']}
    assert len(audited) == expected_n
    verified = []
    for key, (suite, case) in expected.items():
        row, qid = by_key[key], key[2]
        question = case['questions'][qid]
        labels = list(question['criteria']) if question['type'] == 'choice' else (
            ['false', 'true'] if question['type'] == 'noul' else [str(i) for i in range(len(question['criteria']))])
        assert row['request_sha256'] == digest({'state': case['state'], 'questions': case['questions']})
        audit = audited[key[:2]][qid]
        assert audit['complete'] and audit['options'] == len(labels)
        if not legacy:
            assert row['gold'] == str(case['gold'][qid]['label'])
        probabilities = row['probabilities']
        if row['error'] is None:
            assert set(probabilities) == set(labels)
            assert all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
            assert abs(sum(probabilities.values()) - 1) < 1e-5
            assert row['prediction'] in labels
            assert abs(probabilities[row['prediction']] - max(probabilities.values())) < 1e-12
            if name == 'jev-1.13.0':
                evidence = row['hosted_evidence']
                assert evidence['model'] == name and evidence['error'] is None
                assert evidence['payload_sha256'] == digest(dict(model=name, state=case['state'], questions=case['questions']))
                assert row['prediction'] == evidence['response']['answers'][qid]['choice']
        else:
            assert probabilities is None and row['prediction'] is None
        verified.append(dict(model=name, suite=key[0], id=key[1], qid=qid,
                             request_sha256=row['request_sha256'], gold=str(case['gold'][qid]['label']),
                             prediction=row['prediction'], probabilities=probabilities, error=row['error'],
                             domain=case.get('metadata', {}).get('domain'),
                             intent=case.get('metadata', {}).get('intent'),
                             condition=case.get('expansion_condition', 'original'),
                             base_id=case.get('base_id'), group=case['group'], labels=labels,
                             source_metadata=case.get('metadata'), gold_distribution=case['gold'][qid].get('distribution')))
    if not legacy:
        assert sum(r['error'] is not None for r in verified) == done['errors']
    receipt = dict(done=done, binding=binding, adapter=metadata['adapter'],
                   dtype=metadata['dtype'], model_files_sha256=metadata.get('model_files_sha256', {}),
                   base_files_sha256=metadata.get('base_files_sha256', {}),
                   probability_semantics=metadata.get('probability_semantics', 'native candidate distribution'))
    for field in ['input_adaptation', 'native_interface_unchanged', 'laya_source_sha256',
                  'temperatures', 'historical_budget']:
        if field in metadata:
            receipt[field] = metadata[field]
    if 'configuration' in metadata:
        receipt['released_temperature_by_options'] = metadata['configuration'].get('temperature_by_options', {})
        receipt['calibration_caveat'] = ('Installed Laya runtime validates released per-option temperatures; '
                                       'invalid values may fall back to native bounds. These probabilities '
                                       'are not guaranteed calibrated confidence or identical to the historical runtime.')
    return verified, receipt


def projection(rows):
    suites = {}
    for row in rows:
        suites.setdefault(row['suite'], row['labels'])
    variable = any(suites[r['suite']] != r['labels'] for r in rows)
    fields = ['suite', 'id', 'qid', 'request_sha256', 'gold', 'prediction', 'error', 'probabilities', *(['labels'] if variable else [])]
    records = [[r[k] if k != 'probabilities' else
                ([r[k][label] for label in r['labels']] if r[k] is not None else None)
                for k in fields] for r in rows]
    return dict(version=1, fields=fields, labels=suites, variable_labels=variable, rows=records)


def verify_historical_identity(name, receipt):
    if name == 'jev-1.13.0':
        return dict(model_version=name, identity='pinned hosted response model')
    if name in {'english', 'multilingual'}:
        path = ROOT / 'research/confirmation_v1/results' / name / 'metadata.json'
    elif name == 'llama31_8b_instruct':
        path = ROOT / 'results' / name / 'metadata.json'
    elif name in {'qwen3_8b', 'qwen3_17b', 'llama32_1b_public', 'llama32_3b_public'}:
        path = ROOT / 'research/model_expansion_v3/results/main' / name / 'metadata.json'
    else:
        generation = 'model_expansion_v2' if name in {'kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b'} else 'model_expansion_v1'
        path = ROOT / 'research' / generation / 'results' / name / 'metadata.json'
    old_metadata = read(path)['signature']['model']
    old = old_metadata['model_files_sha256']
    new = receipt['model_files_sha256']
    # Require every previously recorded parameter tensor file, not merely a
    # coincident tokenizer or config. Additional old filename aliases may exist.
    weights = {key: value for key, value in old.items() if key.endswith(('.safetensors', '.pt'))}
    assert weights and all(new.get(key) == value for key, value in weights.items()), 'Historical weight identity changed: ' + name
    base_weights = {key: value for key, value in old_metadata.get('base_files_sha256', {}).items()
                    if key.endswith(('.safetensors', '.pt'))}
    assert all(receipt['base_files_sha256'].get(key) == value for key, value in base_weights.items()), 'Base weight identity changed'
    return dict(source=str(path.relative_to(ROOT)).replace('\\', '/'), metadata_content_sha256=digest(read(path)),
                weight_files=len(weights), weight_sha256=weights, base_weight_sha256=base_weights,
                identity='all previously recorded tensor file bytes identical')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--completion', type=Path)
    parser.add_argument('--supplement', type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    manifest = read(HERE / 'manifest.json')
    source_manifest = read(args.input / 'manifest.json')
    published_manifest = read(ROOT / 'research/public_expansion_v1/manifest.json')
    assert source_manifest['suites'] == published_manifest['suites']
    assert source_manifest['source_files'] == published_manifest['source_files']
    frozen = read(args.input / 'full.frozen.json')
    assert sha(args.input / 'full.frozen.json') == manifest['inputs']['intent']['sha256']
    for suite in frozen['suites']:
        spec = source_manifest['suites'][suite['name']]
        assert len(suite['cases']) == spec['n'] and digest(suite['cases']) == spec['cases_sha256']
    quality_path = 'research/model_expansion_v3/scores.json'
    quality = read(ROOT / quality_path)['models']
    transfer = dict(read(ROOT / 'research/startlux_transfer_v1/summary.json')['transfer'],
                    **read(ROOT / 'research/model_expansion_v3/summary.json')['transfer'])
    intent, additions, projections, evidence = {}, {}, {}, {}
    for name in manifest['cohort']:
        legacy = (args.input / name / 'DONE.json').exists()
        folder = args.input / name if legacy else (args.completion / 'intent' / name if args.completion else None)
        if folder and (folder / 'DONE.json').exists():
            rows, receipt = verify(folder, name, 'intent', frozen, legacy)
            receipt['historical_weight_identity'] = verify_historical_identity(name, receipt)
            metrics = {}
            for suite in frozen['suites']:
                use = [r for r in rows if r['suite'] == suite['name']]
                metrics[suite['name']] = summarize(use, use[0]['labels'])
                metrics[suite['name']]['score'] = metrics[suite['name']]['accuracy']
                if legacy:
                    old = read(folder / 'summary.json')['metrics'][suite['name']]
                    assert all(math.isclose(metrics[suite['name']][k], old[k], abs_tol=1e-12)
                               for k in ['n', 'correct', 'accuracy', 'macro_f1', 'failures'])
            intent[name] = dict(label=quality[name]['label'], metrics=metrics, receipt=receipt)
            projections['intent/' + name] = projection(rows)
        tfolder = args.completion / 'transfer' / name if args.completion else None
        adapted_folder = args.supplement / 'transfer' / name if args.supplement else None
        if adapted_folder and (adapted_folder / 'DONE.json').exists():
            tfolder = adapted_folder
        if tfolder and (tfolder / 'DONE.json').exists():
            transfer_frozen = read(args.completion / 'transfer.frozen.json')
            assert sha(args.completion / 'transfer.frozen.json') == manifest['inputs']['transfer']['sha256']
            rows, receipt = verify(tfolder, name, 'transfer', transfer_frozen)
            receipt['historical_weight_identity'] = verify_historical_identity(name, receipt)
            additions[name] = dict(metrics=transfer_metrics(rows), receipt=receipt)
            transfer[name] = additions[name]
            projections['transfer/' + name] = projection(rows)
        if args.completion:
            efolder = args.completion / 'intent' / name
            if (efolder / 'admission_error.json').exists() and name in manifest['unsupported_choice_caps']:
                error = read(efolder / 'admission_error.json')
                limit = manifest['unsupported_choice_caps'][name]
                assert error['scored'] is False and error['error'] == 'ValueError'
                assert str(limit) in error['detail'] and any(word in error['detail'].lower() for word in ('option', 'choice', 'answer symbols'))
                evidence[name] = dict(native_choice_limit=limit, status='native_options_exceeded',
                                      error_sha256=sha(efolder / 'admission_error.json'), detail=error['detail'])
    models, coverage = {}, {}
    for name in manifest['cohort']:
        cells = {key: quality[name]['metrics'][key] for key in TASKS[:5]}
        t = transfer.get('jev' if name == 'jev-1.13.0' else name)
        if t:
            cells.update({key: t['metrics'][key]['original'] for key in TASKS[5:9]})
        if name in intent:
            cells.update({key: intent[name]['metrics'][key] for key in TASKS[9:]})
        excluded = name in manifest['unsupported_choice_caps']
        coverage[name] = dict(label=quality[name]['label'], completed_tasks=list(cells),
                              classification_tasks=len(cells), total_tasks=11,
                              status='native_options_exceeded' if excluded else 'complete' if len(cells) == 11 else 'pending',
                              choice_limit=manifest['unsupported_choice_caps'].get(name),
                              missing_tasks=[k for k in TASKS if k not in cells], verified_native_limit=name in evidence)
        if excluded or len(cells) != 11:
            continue
        domains = {domain: dict(score=sum(cells[key]['score'] for key in tasks) / len(tasks), components=tasks)
                   for domain, tasks in manifest['domains'].items()}
        models[name] = dict(label=quality[name]['label'], metrics={**cells,
                            'policy_action': domains['policy'], 'intent_domain': domains['intent'],
                            'overall_domain_equal': dict(score=sum(c['score'] for c in domains.values()) / 8, domains=8),
                            'overall_task_equal': dict(score=sum(c['score'] for c in cells.values()) / 11, tasks=11)},
                            domain_scores=domains, complete=True, classification_tasks=11)
    result = dict(version=1, protocol='complete-cohort-eight-domain-v1', official_full_intent=True,
                  evaluated_on='2026-10-09', manifest_sha256=sha(HERE / 'manifest.json'),
                  old_quality_sha256=sha(ROOT / quality_path),
                  old_transfer_sha256={p: sha(ROOT / p) for p in
                                      ['research/startlux_transfer_v1/summary.json', 'research/model_expansion_v3/summary.json']},
                  models=models, intent=intent, transfer_additions=additions, coverage=coverage,
                  native_limit_evidence=evidence, total_models=23, eligible_models=17,
                  complete_models=len(models), all_eligible_complete=len(models) == 17,
                  domains=manifest['domains'], tasks=TASKS,
                  probability_and_latency_excluded_from_overall=True, projections={})
    if args.supplement:
        supplement_manifest = HERE.parent / 'evaluation_completion_v2/manifest.json'
        result['supplement_manifest'] = dict(path=str(supplement_manifest.relative_to(ROOT)).replace('\\', '/'),
                                              sha256=sha(supplement_manifest))
    references = {'intent': {suite['name']: {
        'labels': list(suite['cases'][0]['questions']['decision']['criteria']),
        'rows': [[case['id'], digest({'state': case['state'], 'questions': case['questions']}),
                  str(case['gold']['decision']['label'])] for case in suite['cases']]}
        for suite in frozen['suites']}}
    transfer_frozen = read(args.completion / 'transfer.frozen.json')
    assert sha(args.completion / 'transfer.frozen.json') == manifest['inputs']['transfer']['sha256']
    # Text-free reference contains every grouping/label needed for public replay.
    references['transfer'] = [dict(suite=s['name'], id=c['id'], qid=q,
        request_sha256=digest({'state': c['state'], 'questions': c['questions']}),
        gold=str(c['gold'][q]['label']), group=c['group'], base_id=c.get('base_id'),
        condition=c.get('expansion_condition', 'original'), source_metadata=c.get('metadata'),
        gold_distribution=c['gold'][q].get('distribution'), labels=list(c['questions'][q]['criteria']))
        for s in transfer_frozen['suites'] for c in s['cases'] for q in c['questions']]
    reference_bytes = gzip.compress(json.dumps(references, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0)
    result['intent_references'] = dict(path='research/evaluation_completion_v1/intent_references.json.gz',
                                       sha256=hashlib.sha256(reference_bytes).hexdigest(), n=8580,
                                       frozen_sha256=manifest['inputs']['intent']['sha256'])
    result['intent_references']['transfer_n'] = len(references['transfer'])
    result['intent_references']['transfer_frozen_sha256'] = manifest['inputs']['transfer']['sha256']
    if not args.check_only:
        (HERE / 'intent_references.json.gz').write_bytes(reference_bytes)
    for key, payload in projections.items():
        encoded = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), mtime=0)
        destination = HERE / 'projections' / (key + '.json.gz')
        result['projections'][key] = dict(path=str(destination.relative_to(ROOT)).replace('\\', '/'),
                                         sha256=hashlib.sha256(encoded).hexdigest(), n=len(payload['rows']))
        if not args.check_only:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(encoded)
    if args.check_only:
        assert result == read(HERE / 'results.json')
        for item in result['projections'].values():
            assert sha(ROOT / item['path']) == item['sha256']
        assert sha(ROOT / result['intent_references']['path']) == result['intent_references']['sha256']
    else:
        save(HERE / 'results.json', result)
    print('Verified complete comprehensive models:', len(models), '/ 17; full intent:', len(intent), '/ 17')
    for name in sorted(models, key=lambda n: -models[n]['metrics']['overall_domain_equal']['score']):
        print(name, round(models[name]['metrics']['overall_domain_equal']['score'] * 100, 4))


if __name__ == '__main__':
    main()
