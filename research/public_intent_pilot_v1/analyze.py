"""Independent replay of complete intent pilots; never scores partial runs."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MODELS = {'kev_4b': 'Kev-4B', 'qwen35_4b': 'Qwen3.5-4B', 'kev_9b': 'Kev-9B',
          'qwen35_9b': 'Qwen3.5-9B', 'nanojev': 'NanoJev'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def summarize(rows, labels):
    """No dependence on the inference runner's scoring helper."""
    support = Counter(row['gold'] for row in rows)
    predictions = Counter(row['prediction'] for row in rows if row['prediction'] is not None)
    correct = Counter(row['gold'] for row in rows if row['gold'] == row['prediction'])
    n = len(rows)
    tp = sum(correct.values())
    per_class = [{'label': label, 'n': support[label], 'predicted': predictions[label],
                  'correct': correct[label], 'f1': 2 * correct[label] / (support[label] + predictions[label])
                  if support[label] + predictions[label] else 0.0} for label in labels]
    probability_rows = [row for row in rows if row['probabilities'] is not None]
    brier = sum(sum((p - float(label == row['gold'])) ** 2 for label, p in row['probabilities'].items())
                for row in probability_rows)
    zero = sum(row['probabilities'][row['gold']] == 0 for row in probability_rows)
    nll_clipped = sum(-math.log(max(row['probabilities'][row['gold']], 1e-15)) for row in probability_rows)
    result = {'n': n, 'correct': tp, 'accuracy': tp / n if n else None,
              'macro_f1': sum(row['f1'] for row in per_class) / len(labels),
              'failures': sum(row['error'] is not None for row in rows), 'per_class': per_class,
              'probability_n': len(probability_rows),
              'brier': brier / len(probability_rows) if probability_rows else None,
              'nll': nll_clipped / len(probability_rows) if probability_rows and not zero else None,
              'nll_clipped_1e15': nll_clipped / len(probability_rows) if probability_rows else None,
              'zero_gold_probability': zero}
    domains = sorted({row['domain'] for row in rows if row.get('domain') is not None})
    result['domains'] = [{'domain': domain, 'n': sum(row['domain'] == domain for row in rows),
                          'correct': sum(row['domain'] == domain and row['prediction'] == row['gold'] for row in rows)}
                         for domain in domains]
    if 'option_150' in labels:
        known = [row for row in rows if row['gold'] != 'option_150']
        unknown = [row for row in rows if row['gold'] == 'option_150']
        unknown_tp = sum(row['prediction'] == 'option_150' for row in unknown)
        unknown_fp = sum(row['prediction'] == 'option_150' for row in known)
        result.update(known_n=len(known), known_correct=sum(row['prediction'] == row['gold'] for row in known),
                      oos_n=len(unknown), oos_correct=unknown_tp, false_oos=unknown_fp,
                      oos_recall=unknown_tp / len(unknown),
                      oos_precision=unknown_tp / (unknown_tp + unknown_fp) if unknown_tp + unknown_fp else None)
    return result


def verify_run(input_root, model, frozen, manifest):
    folder = input_root / model
    done = read(folder / 'DONE.json')
    if done.get('n') != 354 or done.get('model') != model:
        raise ValueError('Expected complete 354-request pilot')
    for field, file in [('binding', 'binding.json'), ('raw', 'raw.jsonl'),
                        ('metadata', 'model_metadata.json'), ('summary', 'summary.json'),
                        ('compatibility', 'compatibility.json')]:
        if done[field + '_sha256'] != sha(folder / file):
            raise ValueError('Completion hash mismatch: ' + file)
    binding = read(folder / 'binding.json')
    if binding['frozen_sha256'] != sha(folder / 'pilot.frozen.json'):
        raise ValueError('Frozen byte mismatch')
    if binding['data_manifest_sha256'] != sha(folder / 'data_manifest.json'):
        raise ValueError('Run manifest byte mismatch')
    if binding['runner_sha256'] != sha(folder / 'run_original.py'):
        raise ValueError('Archived runner byte mismatch')
    metadata = read(folder / 'model_metadata.json')
    measured_checkpoint = {key: value for key, value in binding['checkpoint'].items() if key != 'downloaded'}
    if metadata['checkpoint'] != measured_checkpoint or metadata.get('dtype') not in {'bfloat16', 'fp32_storage_bf16_autocast'}:
        raise ValueError('Checkpoint or original precision mismatch')
    if metadata.get('truncation') is not False:
        raise ValueError('Truncation prohibited')
    compatibility = read(folder / 'compatibility.json')
    if not compatibility['complete'] or compatibility['audited_requests'] != 354:
        raise ValueError('Incomplete candidate audit')
    raw = [json.loads(line) for line in (folder / 'raw.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {row['id']: row for row in raw}
    expected = {case['id'] for suite in frozen['suites'] for case in suite['cases']}
    if len(raw) != 354 or len(by_id) != 354 or set(by_id) != expected:
        raise ValueError('Missing, duplicate or unknown request')
    old = read(folder / 'summary.json')
    public_rows, metrics = [], {}
    for suite in frozen['suites']:
        spec = manifest['suites'][suite['name']]
        if len(suite['cases']) != spec['n'] or digest(suite['cases']) != spec['cases_sha256']:
            raise ValueError('Case selection changed')
        labels = list(suite['cases'][0]['questions']['decision']['criteria'])
        if len(labels) != spec['classes']:
            raise ValueError('Reduced candidate ontology')
        rows = []
        for case in suite['cases']:
            raw_row = by_id[case['id']]
            payload = {'state': case['state'], 'questions': case['questions']}
            if raw_row['suite'] != suite['name'] or raw_row['request_sha256'] != digest(payload):
                raise ValueError('Inference request changed')
            probabilities = raw_row['probabilities']
            if probabilities is not None:
                if set(probabilities) != set(labels):
                    raise ValueError('Probability labels incomplete')
                if not all(isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1
                           for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 1e-6:
                    raise ValueError('Invalid probability distribution')
                if raw_row['prediction'] not in labels or probabilities[raw_row['prediction']] != max(probabilities.values()):
                    raise ValueError('Prediction not probability maximum')
                if raw_row['error'] is not None:
                    raise ValueError('Error record cannot supply valid probabilities')
            elif raw_row['prediction'] is not None or raw_row['error'] is None:
                raise ValueError('Invalid failure record')
            row = {'model': model, 'suite': suite['name'], 'id': case['id'],
                   'request_sha256': raw_row['request_sha256'], 'gold': case['gold']['decision']['label'],
                   'intent': case['metadata']['intent'], 'domain': case['metadata'].get('domain'),
                   'prediction': raw_row['prediction'], 'probabilities': probabilities, 'error': raw_row['error']}
            rows.append(row)
        result = summarize(rows, labels)
        for key in ['n', 'correct', 'accuracy', 'macro_f1', 'failures']:
            if not math.isclose(result[key], old['metrics'][suite['name']][key], abs_tol=1e-12):
                raise ValueError('Published runner summary does not replay: ' + key)
        metrics[suite['name']] = result
        public_rows.extend(rows)
    receipt = {'done': done, 'binding': binding, 'metadata_sha256': done['metadata_sha256'],
               'adapter': metadata['adapter'], 'dtype': metadata['dtype'], 'gpu': metadata['gpu'],
               'probability_semantics': metadata.get('probability_semantics', 'native candidate distribution'),
               'model_files_sha256': metadata.get('model_files_sha256', {})}
    return {'label': MODELS[model], 'checkpoint': binding['checkpoint'], 'metrics': metrics, 'receipt': receipt}, public_rows


def paired_comparison(rows):
    out = {}
    indexed = {model: {row['id']: row for row in rows if row['model'] == model} for model in MODELS}
    for suite in ['clinc150_pilot', 'banking77_pilot']:
        ids = [key for key, row in indexed['kev_4b'].items() if row['suite'] == suite]
        cells = Counter()
        for key in ids:
            a, b = indexed['kev_4b'][key], indexed['qwen35_4b'][key]
            if a['gold'] != b['gold'] or a['request_sha256'] != b['request_sha256']:
                raise ValueError('Paired request mismatch')
            cells[(a['prediction'] == a['gold'], b['prediction'] == b['gold'])] += 1
        out[suite] = {'n': len(ids), 'both_correct': cells[True, True], 'both_wrong': cells[False, False],
                      'kev_only_correct': cells[True, False], 'qwen_only_correct': cells[False, True],
                      'kev_minus_qwen_accuracy': (cells[True, False] - cells[False, True]) / len(ids)}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    published = read(ROOT / 'research/public_expansion_v1/manifest.json')
    models, rows = {}, []
    common_frozen = None
    for model in MODELS:
        manifest = read(args.input / model / 'data_manifest.json')
        frozen = read(args.input / model / 'pilot.frozen.json')
        # Each run retains its exact original bytes, including its OS line endings.
        if manifest['suites'] != published['suites'] or manifest['source_files'] != published['source_files']:
            raise ValueError('Run source or case selection differs from published preparation')
        if common_frozen is not None and common_frozen != frozen:
            raise ValueError('Different semantic inputs between models')
        common_frozen = frozen
        models[model], model_rows = verify_run(args.input, model, frozen, manifest)
        rows.extend(model_rows)
    result = {'version': 1, 'verified_on': '2026-10-07', 'pilot': True, 'official_full_test': False,
              'accuracy_only': True, 'latency_not_reported': True, 'models': models,
              'paired': paired_comparison(rows),
              'source_manifest_sha256': {model: sha(args.input / model / 'data_manifest.json') for model in MODELS},
              'preparation_manifest_sha256': sha(ROOT / 'research/public_expansion_v1/manifest.json'),
              'cases_and_requests_identical_across_serializations': True,
              'source_receipt_sha256': published['source_receipt_sha256'],
              'audit_sha256': published['audit_sha256'],
              'projection_sha256': digest(rows)}
    limits = []
    for model, label, limit in [('intern_4b', 'Intern-Decision-4B', 62), ('startlux_4b', 'StartLux-Decision-4B', 26)]:
        folder = args.input / model
        rejected = read(folder / 'admission_error.json')
        binding = read(folder / 'binding.json')
        if rejected['scored'] is not False or rejected['error'] != 'ValueError' or (folder / 'DONE.json').exists():
            raise ValueError('Invalid unsupported-model record')
        limits.append({'id': model, 'label': label, 'limit': limit, 'status': 'native_interface_unsupported',
                       'score': None, 'reason': rejected['detail'], 'checkpoint': binding['checkpoint'],
                       'error_sha256': sha(folder / 'admission_error.json'), 'binding_sha256': sha(folder / 'binding.json'),
                       'runner_sha256': binding['runner_sha256']})
    result['capability_limits'] = limits
    if not args.check_only:
        HERE.mkdir(parents=True, exist_ok=True)
        for filename, value in [('results.json', result), ('prediction_projection.json', rows)]:
            (HERE / filename).write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())
        for model in MODELS:
            (HERE / (model + '_data_manifest.json')).write_bytes((args.input / model / 'data_manifest.json').read_bytes())
            (HERE / (model + '_runner_original.py')).write_bytes((args.input / model / 'run_original.py').read_bytes())
    print(json.dumps({'verified': True, 'models': len(models), 'requests': len(rows), 'paired': result['paired']}))


if __name__ == '__main__':
    main()
