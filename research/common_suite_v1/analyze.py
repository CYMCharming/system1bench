"""Reproduce the 23-model, seven-domain ranking from existing verified counts."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DOMAINS = {
    'policy_action': ['refund', 'access', 'routing'],
    'legal': ['legal'], 'science': ['science'], 'cladder': ['cladder'],
    'cruxeval': ['cruxeval'], 'finentity': ['finentity'], 'when2call': ['when2call'],
}
TASKS = [task for tasks in DOMAINS.values() for task in tasks]
DENOMINATORS = dict(refund=96, access=96, routing=96, legal=144, science=339,
                    cladder=144, cruxeval=128, finentity=128, when2call=128)
QUALITY = 'research/model_expansion_v3/scores.json'
TRANSFER = ['research/startlux_transfer_v1/summary.json',
            'research/model_expansion_v3/summary.json']
COMPLETION = 'research/evaluation_completion_v1/results.json'


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def compose_model(label, cells):
    """Reject incomplete/invalid cells; keep exact counts and no borrowed CIs."""
    assert set(cells) == set(TASKS), 'The common suite requires exactly nine tasks'
    metrics = {}
    for task in TASKS:
        cell = cells[task]
        assert isinstance(cell['correct'], int) and not isinstance(cell['correct'], bool)
        assert isinstance(cell['n'], int) and cell['n'] == DENOMINATORS[task]
        assert 0 <= cell['correct'] <= cell['n']
        score = cell['correct'] / cell['n']
        assert math.isclose(score, cell['score'], abs_tol=1e-12)
        metrics[task] = dict(correct=cell['correct'], n=cell['n'], score=score)
    domain_scores = {
        domain: dict(score=sum(metrics[task]['score'] for task in tasks) / len(tasks), tasks=tasks)
        for domain, tasks in DOMAINS.items()
    }
    metrics['policy_action'] = dict(correct=sum(metrics[t]['correct'] for t in DOMAINS['policy_action']),
                                    n=288, score=domain_scores['policy_action']['score'])
    metrics['overall_domain_equal'] = dict(score=sum(c['score'] for c in domain_scores.values()) / 7,
                                           domains=list(DOMAINS), weighting='seven_domains_equal')
    metrics['overall_task_equal'] = dict(score=sum(metrics[t]['score'] for t in TASKS) / 9,
                                         tasks=TASKS, weighting='nine_tasks_equal')
    return dict(label=label, complete=True, classification_tasks=9, metrics=metrics,
                domain_scores=domain_scores)


def calculate():
    quality = read(QUALITY)
    completion = read(COMPLETION)
    manifest_path = 'research/evaluation_completion_v1/manifest.json'
    manifest = read(manifest_path)
    assert completion['old_quality_sha256'] == sha(QUALITY)
    assert completion['manifest_sha256'] == sha(manifest_path)
    transfer = {}
    for path in TRANSFER:
        assert completion['old_transfer_sha256'][path] == sha(path)
        summary = read(path)
        assert summary['complete']
        transfer.update(summary['transfer'])
    transfer.update(completion['transfer_additions'])
    cohort = list(quality['models'])
    assert len(cohort) == 23 and set(cohort) == set(manifest['cohort']) == set(completion['coverage'])
    models, coverage = {}, {}
    for identity in cohort:
        old = quality['models'][identity]
        assert set(TASKS) <= set(completion['coverage'][identity]['completed_tasks'])
        transfer_id = 'jev' if identity == 'jev-1.13.0' else identity
        # Completion additions use canonical IDs; historical Jev uses "jev".
        entry = transfer.get(identity, transfer.get(transfer_id))
        assert entry is not None, 'Missing transfer results: ' + identity
        cells = {task: old['metrics'][task] if task in DENOMINATORS and task in old['metrics']
                 else entry['metrics'][task]['original'] for task in TASKS}
        model = compose_model(old['label'], cells)
        assert math.isclose(model['metrics']['policy_action']['score'], old['metrics']['policy_action']['score'],
                            abs_tol=1e-12)
        if identity in completion['models']:
            for task in TASKS:
                current = completion['models'][identity]['metrics'][task]
                assert all(model['metrics'][task][key] == current[key] for key in ['correct', 'n', 'score'])
        models[identity] = model
        coverage[identity] = dict(label=old['label'], completed_tasks=TASKS, classification_tasks=9,
                                  total_tasks=9, status='complete', missing_tasks=[])
    paths = [QUALITY, *TRANSFER, COMPLETION, manifest_path,
             'research/common_suite_v1/PROTOCOL.md', 'research/common_suite_v1/analyze.py']
    return dict(version=1, protocol='common-suite-seven-domains-v1',
                derived_from_existing_evaluations=True, excluded_tasks=['clinc150_full', 'banking77_full'],
                domains=DOMAINS, tasks=TASKS, examples_per_model=sum(DENOMINATORS.values()),
                total_models=23, complete_models=23, all_models_complete=True,
                confidence_intervals_available=False, sources={p: sha(p) for p in paths},
                models=models, coverage=coverage)


def csv_export(result):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['rank', 'model_id', 'model', 'overall_domain_equal_percent', 'overall_task_equal_percent',
                     *[domain + '_percent' for domain in DOMAINS],
                     *[task + '_' + field for task in TASKS for field in ['correct', 'n']]])
    rows = sorted(result['models'].items(), key=lambda item: (-item[1]['metrics']['overall_domain_equal']['score'], item[0]))
    previous, rank = None, 0
    for index, (identity, model) in enumerate(rows, 1):
        score = model['metrics']['overall_domain_equal']['score']
        if previous is None or not math.isclose(score, previous, abs_tol=1e-12, rel_tol=0):
            rank = index
        previous = score
        writer.writerow([rank, identity, model['label'],
                         *[format(model['metrics'][metric]['score'] * 100, '.17g')
                           for metric in ['overall_domain_equal', 'overall_task_equal']],
                         *[format(model['domain_scores'][domain]['score'] * 100, '.17g') for domain in DOMAINS],
                         *[model['metrics'][task][field] for task in TASKS for field in ['correct', 'n']]])
    return stream.getvalue().encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify published outputs without writing')
    args = parser.parse_args()
    result = calculate()
    encoded = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    csv_bytes = csv_export(result)
    if args.check:
        assert (HERE / 'scores.json').read_bytes() == encoded
        assert (HERE / 'scores.csv').read_bytes() == csv_bytes
    else:
        (HERE / 'scores.json').write_bytes(encoded)
        (HERE / 'scores.csv').write_bytes(csv_bytes)
    print('PASS: 23/23 models; seven equal domains; nine identical tasks; 1,299 original examples per model')
    for identity, model in sorted(result['models'].items(), key=lambda item: -item[1]['metrics']['overall_domain_equal']['score']):
        print(identity, format(model['metrics']['overall_domain_equal']['score'] * 100, '.4f'))


if __name__ == '__main__':
    main()
