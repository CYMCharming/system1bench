"""Public, observational token-length diagnostics on frozen model choices.

This reuses historical predictions. It neither changes candidate text nor calls
a model. Absolute lengths and within-question ordinal positions are different
estimands; every comparison explicitly binds its shared eligible question set.
"""
from collections import Counter, defaultdict
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from research.option_length_v1.analyze import BOOTSTRAPS, SEED, TASKS, interval, ranks

OBSERVATIONS = ROOT / 'research/option_length_v1/observations.json.gz'
PROJECTION = HERE / 'token_lengths.json.gz'
VARIABLE = {'cruxeval', 'when2call'}
BINS = [dict(id='1_8', label='1–8', lower=1, upper=8),
        dict(id='9_16', label='9–16', lower=9, upper=16),
        dict(id='17_32', label='17–32', lower=17, upper=32),
        dict(id='33_64', label='33–64', lower=33, upper=64),
        dict(id='65_plus', label='65+', lower=65, upper=None)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mean(values):
    return sum(values) / len(values) if values else None


def validate_projection(observations, projection, *, observations_sha256=None):
    """Require exact candidate coverage and explicitly positive token counts."""
    if projection.get('version') != 1 or 'qwen3' not in projection.get('tokenizers', {}):
        raise ValueError('A version-1 projection with the qwen3 reference is required')
    if observations_sha256 is not None and projection.get('source_observations_sha256') != observations_sha256:
        raise ValueError('Observation projection hash mismatch')
    candidates = {value for row in observations['items'] for value in row['candidate_hashes']}
    if candidates != set(projection.get('lengths', {})):
        raise ValueError('Token projection candidate coverage mismatch')
    tokenizers = set(projection['tokenizers'])
    for candidate, values in projection['lengths'].items():
        if set(values) != tokenizers:
            raise ValueError('Reference tokenizer coverage mismatch: ' + candidate)
        if any(type(value) is not int or value < 1 for value in values.values()):
            raise ValueError('Nonempty candidate descriptions require positive integer token lengths')
    for key, metadata in projection['tokenizers'].items():
        if metadata.get('add_special_tokens') is not False or metadata.get('truncation') is not False:
            raise ValueError('Uncontrolled tokenization policy: ' + key)


def prepared_items(observations, projection, tokenizer):
    result = []
    for row in observations['items']:
        if row['condition'] != 'original':
            continue
        lengths = [projection['lengths'][candidate][tokenizer] for candidate in row['candidate_hashes']]
        if len(lengths) != len(row['lengths']) or len(lengths) < 2:
            raise ValueError('Mismatched option lengths')
        result.append(dict(row, token_lengths=lengths))
    return result


def valid_choice(item, model):
    prediction = item['predictions'][model]
    if prediction is not None and (type(prediction) is not int or not 0 <= prediction < len(item['token_lengths'])):
        raise ValueError('Prediction is not an option index')
    if type(item['gold']) is not int or not 0 <= item['gold'] < len(item['token_lengths']):
        raise ValueError('Gold is not an option index')
    return prediction


def in_bin(value, specification):
    return value >= specification['lower'] and (specification['upper'] is None or value <= specification['upper'])


def leave_one_group_out(values, groups):
    """Deletion sensitivity of a mean; each entire source cluster is omitted."""
    totals = defaultdict(lambda: [0., 0])
    for value, group in zip(values, groups):
        totals[group][0] += value
        totals[group][1] += 1
    if len(totals) < 2:
        return None, None
    total, n = sum(values), len(values)
    deleted = [(total - subtotal) / (n - size) for subtotal, size in totals.values()]

    def sign(value):
        return 0 if math.isclose(value, 0., abs_tol=1e-12) else 1 if value > 0 else -1

    return [min(deleted), max(deleted)], all(sign(value) == sign(total/n) for value in deleted)


def absolute_summary(items, model, *, errors_only=False, ci=True):
    """Lengths on all valid selected rows, including all-equal token options.

    The excess is a paired within-question difference. Error-mode opportunities
    contain wrong candidates only, not the complete candidate ontology.
    """
    chosen, gold, baseline, excess, groups, identifiable = [], [], [], [], [], []
    opportunities = [[] for _ in BINS]
    counts = [0] * len(BINS)
    correct = failures = equal = degenerate = 0
    for item in items:
        prediction = valid_choice(item, model)
        if prediction is None:
            failures += 1
            continue
        is_wrong = prediction != item['gold']
        if errors_only and not is_wrong:
            continue
        lengths = item['token_lengths']
        if any(type(value) is not int or value < 1 for value in lengths):
            raise ValueError('Token lengths must be positive integers')
        options = [i for i in range(len(lengths)) if not errors_only or i != item['gold']]
        chance_mean = mean([lengths[i] for i in options])
        delta = lengths[prediction] - chance_mean
        chosen.append(lengths[prediction])
        gold.append(lengths[item['gold']])
        baseline.append(chance_mean)
        excess.append(delta)
        groups.append((item['task'], item['group']))
        correct += not is_wrong
        equal += len(set(lengths)) == 1
        if len({lengths[i] for i in options}) == 1:
            degenerate += 1
        else:
            identifiable.append(delta)
        for index, specification in enumerate(BINS):
            counts[index] += in_bin(lengths[prediction], specification)
            opportunities[index].append(sum(in_bin(lengths[i], specification) for i in options) / len(options))
    n = len(chosen)
    deletion_range, robust = leave_one_group_out(excess, groups)
    bins = []
    for specification, count, chances in zip(BINS, counts, opportunities):
        expected = sum(chances) if n else None
        chance = mean(chances)
        bins.append(dict(specification, chosen_count=int(count), n=n,
                         rate=count/n if n else None, chance=chance,
                         expected_count=expected, ratio=count/expected if expected else None))
    return dict(n=n, correct=int(correct), failures=failures, equal_length_included=int(equal),
                chosen_mean=mean(chosen), gold_mean=mean(gold), baseline_mean=mean(baseline),
                excess=mean(excess), excess_ci95=interval(excess, groups) if ci and n else None,
                excess_median=median(excess) if n else None,
                leave_one_group_out_range=deletion_range, excess_sign_robust_to_one_group=robust,
                baseline_degenerate_n=degenerate, excess_identifiable_n=len(identifiable),
                excess_identifiable=mean(identifiable), bins=bins)


def summarize(items, model, *, errors_only=False, ci=True):
    """Relative token and character ranks on their paired informative subset.

    The nested absolute summary deliberately retains equal-length rows. The
    production rank-comparison scopes preselect a shared informative cohort so
    both quantities use the identical n there; independent all-valid scopes do
    not discard useful absolute lengths merely because their ranks cannot vary.
    """
    values = {key: [] for key in ('token', 'gold_token', 'baseline_token',
                                  'character', 'gold_character', 'baseline_character', 'delta', 'excess_token')}
    groups = []
    correct = failures = token_equal = character_equal = excluded = 0
    for item in items:
        prediction = valid_choice(item, model)
        if prediction is None:
            failures += 1
            continue
        if errors_only and prediction == item['gold']:
            continue
        lengths, characters = item['token_lengths'], item['lengths']
        if len(lengths) != len(characters):
            raise ValueError('Character/token candidate cardinalities differ')
        a, b = len(set(lengths)) == 1, len(set(characters)) == 1
        token_equal += a
        character_equal += b
        if a or b:
            excluded += 1
            continue
        rt, rc = ranks(lengths), ranks(characters)
        options = [i for i in range(len(lengths)) if not errors_only or i != item['gold']]
        t_score, c_score = 200 * rt[prediction] - 100, 200 * rc[prediction] - 100
        values['token'].append(t_score)
        values['character'].append(c_score)
        values['gold_token'].append(200 * rt[item['gold']] - 100)
        values['gold_character'].append(200 * rc[item['gold']] - 100)
        baseline_token = 200 * mean([rt[i] for i in options]) - 100
        values['baseline_token'].append(baseline_token)
        values['baseline_character'].append(200 * mean([rc[i] for i in options]) - 100)
        values['delta'].append(t_score - c_score)
        values['excess_token'].append(t_score - baseline_token)
        groups.append((item['task'], item['group']))
        correct += prediction == item['gold']
    n = len(groups)
    return dict(n=n, correct=int(correct), failures=failures, clusters=len(set(groups)),
                token_equal_excluded=int(token_equal), character_equal_excluded=int(character_equal),
                either_equal_excluded=int(excluded), score=mean(values['token']),
                ci95=interval(values['token'], groups) if ci and n else None,
                gold_score=mean(values['gold_token']), baseline_score=mean(values['baseline_token']),
                relative_excess=dict(score=mean(values['excess_token']),
                                     ci95=interval(values['excess_token'], groups) if ci and n else None),
                character=dict(score=mean(values['character']),
                               ci95=interval(values['character'], groups) if ci and n else None,
                               gold_score=mean(values['gold_character']),
                               baseline_score=mean(values['baseline_character'])),
                rank_delta=dict(score=mean(values['delta']),
                                ci95=interval(values['delta'], groups) if ci and n else None),
                absolute=absolute_summary(items, model, errors_only=errors_only, ci=ci))


def select_cohort(items, models):
    """One success/length-eligibility rule for all models, scopes and modes."""
    valid = [row for row in items if all(valid_choice(row, model) is not None for model in models)]
    informative = [row for row in valid if len(set(row['lengths'])) > 1 and len(set(row['token_lengths'])) > 1]
    receipt = dict(source_n=len(items), shared_valid_n=len(valid), unavailable_excluded=len(items)-len(valid),
                   character_equal_excluded=sum(len(set(row['lengths'])) == 1 for row in valid),
                   token_equal_excluded=sum(len(set(row['token_lengths'])) == 1 for row in valid),
                   either_equal_excluded=len(valid)-len(informative), n=len(informative))
    return informative, valid, receipt


def outlier_sensitivity(variable_items, primary_items, models):
    """Explicit deletion audit; never changes the primary scored population."""
    maximum = max(length for row in variable_items for length in row['token_lengths'])
    hashes = sorted({candidate for row in variable_items
                     for candidate, length in zip(row['candidate_hashes'], row['token_lengths']) if length == maximum})
    groups = {(row['task'], row['group']) for row in variable_items
              if set(hashes) & set(row['candidate_hashes'])}
    remaining = [row for row in primary_items if (row['task'], row['group']) not in groups]
    changes = {}
    for model in models:
        changes[model] = {}
        for mode in ('all', 'errors'):
            before = absolute_summary(primary_items, model, errors_only=mode == 'errors', ci=False)
            after = absolute_summary(remaining, model, errors_only=mode == 'errors', ci=False)
            changes[model][mode] = dict(n_before=before['n'], n_after=after['n'],
                                         excess_before=before['excess'], excess_after=after['excess'],
                                         sign_changed=(before['excess'] * after['excess'] < 0
                                                       if before['excess'] is not None and after['excess'] is not None else None))
    cases = [dict(task=row['task'], id=row['id'], group=row['group'],
                  candidate_count=len(row['token_lengths']),
                  candidate_token_lengths=row['token_lengths'], gold_index=row['gold'])
             for row in variable_items if set(hashes) & set(row['candidate_hashes'])]
    return dict(selection='Maximum reference-token candidate length in original variable-description tasks',
                maximum_candidate_tokens=maximum, candidate_hashes=hashes,
                source_groups=[dict(task=task, group=group) for task, group in sorted(groups)],
                cases=cases, removed_primary_items=len(primary_items)-len(remaining),
                primary_n=len(primary_items), retained_n=len(remaining), models=changes,
                primary_results_unchanged=True,
                caveat='Post-hoc source-group deletion sensitivity, not a revised score or causal effect.')


def calculate(observations, projection, *, ci=True):
    validate_projection(observations, projection)
    if len(observations['models']) != 23:
        raise ValueError('Expected the frozen 23-model cohort')
    result = dict(version=1, analysis='observational-option-token-length-v1', date='2026-10-21',
                  default_tokenizer='qwen3', default_scope='variable', bins=BINS,
                  tasks=[dict(id=task, label=label) for task, label in TASKS.items()],
                  source_observations_sha256=projection['source_observations_sha256'],
                  model_families=dict(Counter(row['family'] for row in observations['models'].values())),
                  interval=dict(method='task-stratified source-group percentile bootstrap of paired differences',
                                level=.95, repetitions=BOOTSTRAPS, seed=SEED,
                                scope='question sampling only; not model population or architecture'),
                  tokenizers={},
                  caveats=[
                      'Observational associations, not causal evidence of a preference for longer or shorter wording.',
                      'Reference tokenizer lengths are not the private native tokenization of each evaluated model.',
                      'Each tokenizer uses one shared all-model successful, character-and-token-informative cohort per scope.',
                      'Absolute all-valid summaries are separate and include equal-token-length questions.',
                      'Relative rank ignores token gaps; absolute excess retains their magnitude.',
                      'Excess and token-minus-character intervals bootstrap paired within-question differences.',
                      'Error subsets differ by model; chance baselines contain only wrong candidates in error mode.',
                      'A bin selection/opportunity ratio is a descriptive association, not a causal preference or accuracy.',
                      'Zero-opportunity or empty bins have null ratios, never fabricated zero preferences.',
                      'Different task contents and fixed-label semantics remain confounded with option length.',
                      'Reference-tokenizer sensitivity can have different eligible n; use its common-intersection comparison.',
                  ])
    for tokenizer, metadata in projection['tokenizers'].items():
        rows = prepared_items(observations, projection, tokenizer)
        if len(rows) != 1299:
            raise ValueError('Expected exactly 1,299 original requests')
        scopes = dict(overall=rows, variable=[row for row in rows if row['task'] in VARIABLE])
        scopes.update({task: [row for row in rows if row['task'] == task] for task in TASKS})
        selected = {scope: select_cohort(items, observations['models']) for scope, items in scopes.items()}
        cohorts = {scope: value[2] for scope, value in selected.items() if scope in {'overall', 'variable'}}
        cohorts['tasks'] = {task: selected[task][2] for task in TASKS}
        models = {}
        for model, model_metadata in observations['models'].items():
            summaries, all_valid = {}, {}
            for scope, (informative, valid, _) in selected.items():
                summaries[scope] = {mode: summarize(informative, model, errors_only=mode == 'errors', ci=ci)
                                    for mode in ('all', 'errors')}
                all_valid[scope] = {mode: absolute_summary(valid, model, errors_only=mode == 'errors', ci=ci)
                                    for mode in ('all', 'errors')}
            models[model] = dict(model_metadata, variable=summaries['variable'], overall=summaries['overall'],
                                 tasks={task: summaries[task] for task in TASKS},
                                 absolute_all_valid=dict(variable=all_valid['variable'], overall=all_valid['overall'],
                                                         tasks={task: all_valid[task] for task in TASKS}))
        result['tokenizers'][tokenizer] = dict(metadata=metadata, cohorts=cohorts, models=models,
                                               outlier_sensitivity=outlier_sensitivity(
                                                   scopes['variable'], selected['variable'][0], observations['models']))
    # A separate common-intersection sensitivity prevents differences between
    # references' eligibility from masquerading as tokenization sensitivity.
    common = [row for row in observations['items'] if row['condition'] == 'original' and row['task'] in VARIABLE
              and all(value is not None for value in row['predictions'].values())
              and len(set(row['lengths'])) > 1
              and all(len({projection['lengths'][key][tokenizer] for key in row['candidate_hashes']}) > 1
                      for tokenizer in projection['tokenizers'])]
    sensitivity = dict(n=len(common), tokenizers={})
    for tokenizer in projection['tokenizers']:
        prepared = [dict(row, token_lengths=[projection['lengths'][key][tokenizer]
                                             for key in row['candidate_hashes']]) for row in common]
        sensitivity['tokenizers'][tokenizer] = {
            model: {mode: summarize(prepared, model, errors_only=mode == 'errors', ci=False)
                    for mode in ('all', 'errors')} for model in observations['models']}
    result['reference_sensitivity'] = sensitivity
    return result


def csv_bytes(result):
    output = io.StringIO(newline='')
    fields = ['tokenizer', 'model', 'family', 'scope', 'mode', 'n', 'token_rank', 'token_rank_ci_low',
              'token_rank_ci_high', 'character_rank', 'paired_rank_delta', 'chosen_mean_tokens',
              'gold_mean_tokens', 'baseline_mean_tokens', 'paired_excess_tokens', 'excess_ci_low', 'excess_ci_high']
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for tokenizer, entry in result['tokenizers'].items():
        for model, data in entry['models'].items():
            for scope in ('variable', 'overall', *TASKS):
                for mode, stats in (data['tasks'][scope] if scope in TASKS else data[scope]).items():
                    absolute = stats['absolute']
                    writer.writerow(dict(tokenizer=tokenizer, model=model, family=data['family'], scope=scope,
                                         mode=mode, n=stats['n'], token_rank=stats['score'],
                                         token_rank_ci_low=stats['ci95'][0] if stats['ci95'] else None,
                                         token_rank_ci_high=stats['ci95'][1] if stats['ci95'] else None,
                                         character_rank=stats['character']['score'], paired_rank_delta=stats['rank_delta']['score'],
                                         chosen_mean_tokens=absolute['chosen_mean'], gold_mean_tokens=absolute['gold_mean'],
                                         baseline_mean_tokens=absolute['baseline_mean'], paired_excess_tokens=absolute['excess'],
                                         excess_ci_low=absolute['excess_ci95'][0] if absolute['excess_ci95'] else None,
                                         excess_ci_high=absolute['excess_ci95'][1] if absolute['excess_ci95'] else None))
    return output.getvalue().encode()


def run(check=False):
    observations_sha = sha(OBSERVATIONS)
    observations = json.loads(gzip.decompress(OBSERVATIONS.read_bytes()))
    compressed = PROJECTION.read_bytes()
    payload = gzip.decompress(compressed)
    projection = json.loads(payload)
    binding = json.loads((HERE/'bindings.json').read_bytes())
    assert hashlib.sha256(compressed).hexdigest() == binding['artifact']['sha256'], 'Token projection digest mismatch'
    assert hashlib.sha256(payload).hexdigest() == binding['artifact']['uncompressed_sha256'], 'Token payload digest mismatch'
    assert binding['source_observations']['sha256'] == observations_sha, 'Source observation digest mismatch'
    assert binding['tokenizers'] == projection['tokenizers'], 'Tokenizer metadata mismatch'
    collector = (HERE/'collect_tokens.py').read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(collector).hexdigest() == binding['collector_sha256'], 'Token collector digest mismatch'
    validate_projection(observations, projection, observations_sha256=observations_sha)
    result = calculate(observations, projection)
    result['sources'] = dict(observations_sha256=observations_sha, token_lengths_sha256=sha(PROJECTION),
                             bindings_sha256=sha(HERE/'bindings.json'),
                             parent_bindings_sha256=sha(ROOT/'research/option_length_v1/bindings.json'),
                             analyzer_sha256=sha(Path(__file__)), protocol_sha256=sha(HERE/'PROTOCOL.md'),
                             dependency_sha256=sha(ROOT/'research/option_length_v1/analyze.py'))
    output = csv_bytes(result)
    if check:
        assert result == json.loads((HERE/'results.json').read_bytes()), 'Token-length results drift'
        assert output == (HERE/'scores.csv').read_bytes(), 'Token-length CSV drift'
    else:
        (HERE/'results.json').write_bytes((json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode())
        (HERE/'scores.csv').write_bytes(output)
    print('Verified' if check else 'Wrote', len(result['tokenizers']), 'reference-tokenizer analyses for 23 models')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    run(parser.parse_args().check)
