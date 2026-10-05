"""Verify completed runs and extend scores without changing the 18 old models."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import sha
from research.startlux_transfer_v1 import analyze as base
from research.startlux_transfer_v1.run import read, save
from research.leaderboard_v2 import build as bootstrap
from research.leaderboard_v3.build import model_metrics

HERE = Path(__file__).resolve().parent
LABELS = dict(intern_08b='Intern-Decision-0.8B', intern_2b='Intern-Decision-2B',
    llama32_1b_public='Llama-3.2-1B-Instruct (Unsloth BF16 distribution)',
    llama32_3b_public='Llama-3.2-3B-Instruct (Unsloth BF16 distribution)',
    qwen3_17b='Qwen3-1.7B', qwen3_8b='Qwen3-8B')


def main():
    manifest = read(HERE / 'manifest.json')
    cohort = manifest['cohort']
    main_frozen = read(ROOT / 'research/model_expansion_v1/frozen.json')
    transfer_frozen = read(ROOT / 'data/startlux_transfer_v1/frozen.json')
    assert sha(ROOT / 'research/model_expansion_v1/frozen.json') == manifest['prepared_main_sha256']
    assert sha(ROOT / 'data/startlux_transfer_v1/frozen.json') == manifest['frozen_sha256']
    assert sha(ROOT / 'research/startlux_transfer_v1/run.py') == manifest['base_runner_sha256']
    base.HERE = HERE
    summary = dict(complete=True, main={}, transfer={}, admissions={}, pending=[],
                   manifest_sha256=sha(HERE / 'manifest.json'), analyzer_sha256=sha(__file__))
    mappings = {}
    for model in cohort:
        for panel, frozen in [('main', main_frozen), ('transfer', transfer_frozen)]:
            metadata = HERE / 'results' / panel / model / 'metadata.json'
            if not metadata.exists() or read(metadata)['status'] != 'DONE':
                summary['pending'].append(dict(model=model, panel=panel))
                summary['complete'] = False
                continue
            rows, receipt = base.verify(model, panel, manifest, frozen)
            admission = HERE / 'admissions' / (model + '.json')
            assert sha(admission) == read(metadata)['signature']['model']['checkpoint']['admission_sha256']
            summary['admissions'][model] = sha(admission)
            if panel == 'transfer':
                summary[panel][model] = dict(label=LABELS[model], receipt=receipt, metrics=base.metrics(rows))
            else:
                mapping = {}
                for row in rows:
                    key = bootstrap.key(row, row['suite'])
                    assert key not in mapping
                    mapping[key] = dict(row, correct=int(base.correct(row)))
                assert len(mapping) == 4905
                mappings[model] = mapping
                summary[panel][model] = dict(label=LABELS[model], receipt=receipt, metrics=model_metrics(mapping))
    save(HERE / 'summary.json', summary)
    if not summary['complete']:
        print('INCOMPLETE; existing published ranking untouched', len(summary['pending']), flush=True)
        return
    bootstrap.MODELS = list(cohort)
    bounds = bootstrap.cluster_bootstrap(mappings)
    previous = ROOT / 'research/leaderboard_v3/scores.json'
    data = read(previous)
    original_models = json.loads(json.dumps(data['models']))
    data.update(protocol='original-weight-expansion-v4',
                previous_scores_sha256=sha(previous), expansion_summary_sha256=sha(HERE / 'summary.json'))
    for i, model in enumerate(cohort):
        metrics = summary['main'][model]['metrics']
        metrics['overall_domain_equal']['ci95'] = np.quantile(bounds[:, i], [.025, .975]).tolist()
        if model in original_models:
            # Qwen3-8B already exists in v3: this is an independent replication
            # and new transfer coverage, never a silent replacement of its score.
            summary.setdefault('main_replications', {})[model] = dict(
                metrics=metrics, previous_metrics=original_models[model]['metrics'],
                overall_score_delta=metrics['overall_domain_equal']['score'] -
                    original_models[model]['metrics']['overall_domain_equal']['score'])
            continue
        data['models'][model] = dict(label=LABELS[model], origin='new_original_weight_measured',
            metrics=metrics, decisions=4905, errors=summary['main'][model]['receipt']['errors'],
            known_training_overlap='not established', checkpoint=manifest['model_pins'][model],
            admission_sha256=summary['admissions'][model])
    assert all(data['models'][name] == value for name, value in original_models.items())
    for metric in data['rankings']:
        data['rankings'][metric] = bootstrap.rank({m: d['metrics'][metric]['score'] for m, d in data['models'].items()})
    save(HERE / 'summary.json', summary)
    data['expansion_summary_sha256'] = sha(HERE / 'summary.json')
    save(HERE / 'scores.json', data)
    print('VERIFIED', len(data['models']), 'models; all earlier measurements unchanged', flush=True)


if __name__ == '__main__':
    main()
