"""Reproduce observational option-length diagnostics from text-free records.

This is not an intervention: the candidate meanings have not been changed.
All functions consume frozen choices, never query a model or alter a ranking.
"""
from collections import Counter, defaultdict
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BOOTSTRAPS = 2000
SEED = 20261021
TASKS = dict(refund='退款政策', access='访问控制', routing='工单分流',
             legal='ContractNLI', science='SciFact', cladder='CLadder',
             cruxeval='CRUXEval', finentity='FinEntity', when2call='When2Call')
VARIABLE = {'cruxeval', 'when2call'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ranks(lengths):
    """Normalized midranks; all equal -> .5, a uniform choice -> mean .5."""
    assert len(lengths) > 1
    return [(sum(other < value for other in lengths)
             + .5 * (sum(other == value for other in lengths) - 1))
            / (len(lengths) - 1) for value in lengths]


def interval(values, groups, seed=SEED, repetitions=BOOTSTRAPS):
    """Percentile cluster bootstrap, stratified by task; never double variants."""
    if len(set(groups)) < 2:
        return None
    totals = defaultdict(lambda: [0., 0])
    for value, group in zip(values, groups):
        totals[group][0] += value
        totals[group][1] += 1
    strata = defaultdict(list)
    for group, pair in sorted(totals.items()):
        strata[group[0]].append(pair)
    if all(len(pairs) < 2 for pairs in strata.values()):
        return None
    generator = np.random.default_rng(seed)
    numerator = np.zeros(repetitions)
    denominator = np.zeros(repetitions)
    for pairs in strata.values():
        pairs = np.asarray(pairs)
        indices = generator.integers(0, len(pairs), (repetitions, len(pairs)))
        numerator += pairs[indices, 0].sum(axis=1)
        denominator += pairs[indices, 1].sum(axis=1)
    return np.quantile(numerator / denominator, [.025, .975]).tolist()


def mean(values):
    return float(np.mean(values)) if values else None


def summarize(items, model, *, errors_only=False, length_key='lengths', ci=True):
    """Micro-average one model on informative originals; no failed-choice zeros.

    Error mode keeps the full candidate length ranks so its scale is unchanged,
    but uses uniformly sampled WRONG candidates as its reference distribution.
    The additional wrong_adjusted_score ranks only identifiable wrong choices.
    """
    scores, gold_scores, baselines, clusters = [], [], [], []
    extrema = {key: dict(count=0, chances=[], gold=0) for key in ('shortest', 'longest')}
    four = dict(n=0, count=0, chances=[])
    adjusted, correct, failures, equal = [], 0, 0, 0
    for item in items:
        lengths = item[length_key]
        if len(set(lengths)) == 1:
            equal += 1
            continue
        prediction = item['predictions'][model]
        if prediction is None:
            failures += 1
            continue
        gold = item['gold']
        wrong = [i for i in range(len(lengths)) if i != gold]
        is_wrong = prediction != gold
        if errors_only and not is_wrong:
            continue
        rs = ranks(lengths)
        scores.append(200 * rs[prediction] - 100)
        gold_scores.append(200 * rs[gold] - 100)
        baseline = mean([rs[i] for i in wrong]) if errors_only else .5
        baselines.append(200 * baseline - 100)
        clusters.append((item['task'], item['group']))
        correct += not is_wrong
        candidates = wrong if errors_only else list(range(len(lengths)))
        for key, extreme in [('shortest', min(lengths)), ('longest', max(lengths))]:
            record = extrema[key]
            record['count'] += lengths[prediction] == extreme
            record['gold'] += lengths[gold] == extreme
            record['chances'].append(sum(lengths[i] == extreme for i in candidates) / len(candidates))
        if len(lengths) == 4 and lengths.count(min(lengths)) == 1:
            four['n'] += 1
            four['count'] += lengths[prediction] == min(lengths)
            four['chances'].append(sum(lengths[i] == min(lengths) for i in candidates) / len(candidates))
        wrong_lengths = [lengths[i] for i in wrong]
        if is_wrong and len(wrong) >= 2 and len(set(wrong_lengths)) > 1:
            adjusted.append(200 * ranks(wrong_lengths)[wrong.index(prediction)] - 100)
    n = len(scores)
    result = dict(n=n, correct=int(correct), failures=failures, equal_length_excluded=equal,
                  clusters=len(set(clusters)), score=mean(scores),
                  ci95=interval(scores, clusters) if ci and n else None,
                  gold_score=mean(gold_scores), baseline_score=mean(baselines),
                  wrong_identifiable_n=len(adjusted), wrong_adjusted_score=mean(adjusted),
                  unique_shortest_four=dict(n=four['n'], count=four['count'],
                                           rate=four['count']/four['n'] if four['n'] else None,
                                           chance=mean(four['chances'])))
    for key, record in extrema.items():
        result[key] = dict(count=record['count'], rate=record['count']/n if n else None,
                           chance=mean(record['chances']))
        result['gold_' + key + '_rate'] = record['gold']/n if n else None
    return result


def paired(items, model):
    """Compare the same semantic choice under one existing order reversal."""
    by_pair = defaultdict(dict)
    for item in items:
        by_pair[item['task'], item['base_id']][item['condition']] = item
    pairs = [(v['original'], v['reversed']) for v in by_pair.values()
             if 'original' in v and 'reversed' in v and len(set(v['original']['lengths'])) > 1]
    retained, deltas, n, failures = 0, [], 0, 0
    for original, reverse in pairs:
        a, b = original['predictions'][model], reverse['predictions'][model]
        if a is None or b is None:
            failures += 1
            continue
        assert set(original['candidate_hashes']) == set(reverse['candidate_hashes'])
        retained += original['candidate_hashes'][a] == reverse['candidate_hashes'][b]
        deltas.append(200 * (ranks(reverse['lengths'])[b] - ranks(original['lengths'])[a]))
        n += 1
    return dict(n=n, failures=failures, same_semantic_choice=retained,
                same_choice_rate=retained/n if n else None, length_score_delta=mean(deltas))


def calculate(observations, *, ci=True):
    original = [item for item in observations['items'] if item['condition'] == 'original']
    assert len(original) == 1299 and len(observations['models']) == 23
    keys = [(x['task'], x['id'], x['condition']) for x in observations['items']]
    assert len(keys) == len(set(keys))
    tasks = []
    for task, label in TASKS.items():
        group = [x for x in original if x['task'] == task]
        tasks.append(dict(id=task, label=label, n=len(group),
                          informative_n=sum(len(set(x['lengths'])) > 1 for x in group),
                          option_counts={str(k): n for k, n in sorted(Counter(len(x['lengths']) for x in group).items())},
                          variable_options=task in VARIABLE,
                          candidate_sets=len({tuple(sorted(x['candidate_hashes'])) for x in group})))
    # A failed request is not a neutral selection. Also supply a completely
    # shared successful cohort for an explicit sensitivity comparison.
    shared = [x for x in original if x['task'] in VARIABLE
              and all(p is not None for p in x['predictions'].values())]
    models = {}
    for model, metadata in observations['models'].items():
        def scope(rows):
            return {mode: summarize(rows, model, errors_only=(mode == 'errors'), ci=ci)
                    for mode in ('all', 'errors')}
        model_data = dict(metadata, overall=scope(original),
                          variable=scope(shared),
                          variable_available=scope([x for x in original if x['task'] in VARIABLE]),
                          shared_variable=scope(shared),
                          tasks={task: scope([x for x in original if x['task'] == task]) for task in TASKS},
                          reversal=paired([x for x in observations['items'] if x['task'] in VARIABLE], model))
        # Whitespace-word sensitivity only on the intersection of character-
        # and word-informative variable items. Different eligibility is explicit.
        both = [x for x in original if x['task'] in VARIABLE
                and len(set(x['lengths'])) > 1 and len(set(x['word_lengths'])) > 1]
        model_data['word_sensitivity'] = dict(
            characters=summarize(both, model, ci=False),
            words=summarize(both, model, length_key='word_lengths', ci=False))
        models[model] = model_data
    variable_originals = [x for x in original if x['task'] in VARIABLE]
    informative_variable = [x for x in variable_originals if len(set(x['lengths'])) > 1]
    return dict(version=1, analysis='observational-option-length-v1', date='2026-10-21',
                tasks=tasks, models=models, default_scope='variable',
                original_n=1299, informative_n=sum(t['informative_n'] for t in tasks),
                variable_cohort=dict(source_n=len(variable_originals),
                                     equal_excluded=len(variable_originals)-len(informative_variable),
                                     unavailable_excluded=sum(any(p is None for p in x['predictions'].values())
                                                              for x in informative_variable),
                                     common_n=sum(len(set(x['lengths'])) > 1 for x in shared)),
                model_families=dict(Counter(m['family'] for m in models.values())),
                interval=dict(method='task-stratified source-group cluster percentile bootstrap',
                              level=.95, repetitions=BOOTSTRAPS, seed=SEED,
                              scope='question sampling only, not architecture or model population'),
                caveats=[
                    'Observational selection skew, not a causal option-length preference.',
                    'CRUXEval and When2Call use variable candidate text; other tasks use fixed labels.',
                    'Errors are model-specific subsets, not an independently identified hard-question cohort.',
                    'Existing general LLMs use constrained single-token candidate codes without CoT.',
                    'Characters exclude Unicode whitespace; words use whitespace splitting, not model tokens.',
                    'One order reversal checks position sensitivity, not semantic confounding.',
                    'Jev has three original request failures; failed choices are missing, not neutral.',
                ])


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def run(check=False):
    binding = json.loads((HERE/'bindings.json').read_bytes())
    compressed = HERE/'observations.json.gz'
    assert sha(compressed) == binding['artifact']['sha256']
    observations = json.loads(gzip.decompress(compressed.read_bytes()))
    result = calculate(observations)
    result['sources'] = dict(observations_sha256=sha(compressed), bindings_sha256=sha(HERE/'bindings.json'),
                             analyzer_sha256=sha(Path(__file__)), protocol_sha256=sha(HERE/'PROTOCOL.md'))
    if check:
        assert result == json.loads((HERE/'results.json').read_bytes()), 'Length results drift'
    else:
        write_json(HERE/'results.json', result)
        output = io.StringIO(newline='')
        fields = ['model', 'family', 'scope', 'mode', 'n', 'score', 'ci95_low', 'ci95_high',
                  'gold_score', 'baseline_score', 'shortest_rate', 'longest_rate', 'failures']
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for model, entry in result['models'].items():
            for scope in ('variable', 'variable_available', 'overall', 'shared_variable', *TASKS):
                for mode, stats in (entry['tasks'][scope] if scope in TASKS else entry[scope]).items():
                    row = {k: stats[k] for k in ('n', 'score', 'gold_score', 'baseline_score', 'failures')}
                    row.update(model=model, family=entry['family'], scope=scope, mode=mode,
                               ci95_low=stats['ci95'][0] if stats['ci95'] else None,
                               ci95_high=stats['ci95'][1] if stats['ci95'] else None,
                               shortest_rate=stats['shortest']['rate'], longest_rate=stats['longest']['rate'])
                    writer.writerow(row)
        (HERE/'scores.csv').write_bytes(output.getvalue().encode())
    print('Verified' if check else 'Wrote', '23-model option-length diagnostics')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    run(parser.parse_args().check)
