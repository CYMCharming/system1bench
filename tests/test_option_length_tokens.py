"""Exact synthetic arithmetic and independent public token-analysis checks."""
import copy
import csv
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
import unittest

from research.option_length_tokens_v1.analyze import (
    BINS, OBSERVATIONS, PROJECTION, absolute_summary, calculate, csv_bytes,
    leave_one_group_out, prepared_items, select_cohort, summarize, validate_projection,
)


HERE = Path(__file__).resolve().parents[1] / 'research/option_length_tokens_v1'


def row(tokens, prediction, gold=0, *, characters=None, group='source-1', model='model'):
    return dict(token_lengths=tokens, lengths=characters or list(tokens),
                gold=gold, predictions={model: prediction}, task='synthetic', group=group)


def exact_rank(lengths, index):
    value = lengths[index]
    return sum(Fraction(1 if value > other else 0) if value != other else Fraction(1, 2)
               for j, other in enumerate(lengths) if j != index) / (len(lengths)-1)


def without_intervals(value):
    if isinstance(value, dict):
        return {k: without_intervals(v) for k, v in value.items() if k not in {'ci95', 'excess_ci95'}}
    if isinstance(value, list):
        return [without_intervals(v) for v in value]
    return value


class TokenLengthMathTests(unittest.TestCase):
    def test_absolute_gaps_and_relative_positions_are_distinct(self):
        a = summarize([row([1, 2, 100], 1, 2)], 'model', ci=False)
        b = summarize([row([1, 50, 100], 1, 2)], 'model', ci=False)
        self.assertEqual(a['score'], b['score'])
        self.assertEqual(a['score'], 0.)
        self.assertEqual(a['absolute']['chosen_mean'], 2.)
        self.assertEqual(b['absolute']['chosen_mean'], 50.)
        self.assertAlmostEqual(a['absolute']['excess'], float(Fraction(-97, 3)))
        self.assertAlmostEqual(b['absolute']['excess'], float(Fraction(-1, 3)))

    def test_token_character_rank_difference_is_paired(self):
        result = summarize([row([1, 4, 10], 2, 1, characters=[10, 1, 2])], 'model', ci=False)
        self.assertEqual(result['score'], 100.)
        self.assertEqual(result['character']['score'], 0.)
        self.assertEqual(result['rank_delta']['score'], 100.)
        self.assertEqual(result['absolute']['chosen_mean'], 10.)
        self.assertEqual(result['absolute']['gold_mean'], 4.)
        self.assertEqual(result['absolute']['baseline_mean'], 5.)
        self.assertEqual(result['absolute']['excess'], 5.)

    def test_ties_use_midranks_not_arbitrary_index_tiebreaks(self):
        result = summarize([row([2, 2, 8], 0, 2, characters=[1, 2, 3])], 'model', ci=False)
        self.assertEqual(result['score'], -50.)
        self.assertEqual(result['character']['score'], -100.)
        self.assertEqual(result['rank_delta']['score'], 50.)
        self.assertEqual(result['gold_score'], 100.)
        self.assertEqual(result['baseline_score'], 0.)

    def test_equal_token_lengths_have_absolute_information_but_no_rank_comparison(self):
        result = summarize([row([4, 4, 4], 1, 0, characters=[1, 2, 3])], 'model')
        self.assertEqual(result['n'], 0)
        self.assertEqual(result['token_equal_excluded'], 1)
        self.assertIsNone(result['score'])
        self.assertIsNone(result['rank_delta']['score'])
        absolute = result['absolute']
        self.assertEqual(absolute['n'], 1)
        self.assertEqual(absolute['equal_length_included'], 1)
        self.assertEqual(absolute['chosen_mean'], 4.)
        self.assertEqual(absolute['excess'], 0.)
        self.assertIsNone(absolute['excess_ci95'])
        self.assertEqual(absolute['baseline_degenerate_n'], 1)
        self.assertIsNone(absolute['excess_identifiable'])
        char_equal = summarize([row([1, 4, 10], 2, characters=[3, 3, 3])], 'model', ci=False)
        self.assertEqual(char_equal['n'], 0)
        self.assertEqual(char_equal['absolute']['n'], 1)
        self.assertEqual(char_equal['absolute']['excess'], 5.)

    def test_errors_use_wrong_candidate_opportunities_and_a_paired_excess(self):
        item = row([1, 9, 65], 1, 2)
        result = summarize([item], 'model', errors_only=True, ci=False)
        absolute = result['absolute']
        self.assertEqual(result['score'], 0.)
        self.assertEqual(result['baseline_score'], -50.)
        self.assertEqual(result['relative_excess']['score'], 50.)
        self.assertEqual(absolute['baseline_mean'], 5.)
        self.assertEqual(absolute['excess'], 4.)
        self.assertEqual(absolute['bins'][0]['chance'], .5)
        self.assertEqual(absolute['bins'][0]['ratio'], 0.)
        self.assertEqual(absolute['bins'][1]['chance'], .5)
        self.assertEqual(absolute['bins'][1]['ratio'], 2.)
        self.assertEqual(absolute['bins'][4]['chance'], 0.)
        self.assertIsNone(absolute['bins'][4]['ratio'])
        all_answers = summarize([item], 'model', ci=False)
        self.assertEqual(all_answers['absolute']['baseline_mean'], 25.)
        self.assertEqual(all_answers['absolute']['excess'], -16.)

    def test_binary_errors_have_mechanically_zero_excess_not_identifiable_preference(self):
        binary = absolute_summary([row([1, 100], 0, 1)], 'model', errors_only=True, ci=False)
        self.assertEqual(binary['n'], 1)
        self.assertEqual(binary['excess'], 0.)
        self.assertEqual(binary['baseline_degenerate_n'], 1)
        self.assertEqual(binary['excess_identifiable_n'], 0)
        self.assertIsNone(binary['excess_identifiable'])
        equal_wrong = absolute_summary([row([3, 3, 10], 0, 2)], 'model', errors_only=True, ci=False)
        self.assertEqual(equal_wrong['baseline_degenerate_n'], 1)
        self.assertIsNone(equal_wrong['excess_identifiable'])

    def test_bins_cover_boundaries_and_uniform_choices_have_unit_ratios(self):
        tokens = [1, 8, 9, 16, 17, 32, 33, 64, 65, 90]
        result = absolute_summary([row(tokens, p, group=f's-{p}') for p in range(10)], 'model', ci=False)
        self.assertEqual(sum(x['chosen_count'] for x in result['bins']), 10)
        self.assertAlmostEqual(sum(x['chance'] for x in result['bins']), 1.)
        for record in result['bins']:
            self.assertEqual(record['chosen_count'], 2)
            self.assertEqual(record['rate'], .2)
            self.assertAlmostEqual(record['chance'], .2)
            self.assertAlmostEqual(record['expected_count'], 2.)
            self.assertAlmostEqual(record['ratio'], 1.)

    def test_bin_opportunity_is_question_weighted_not_pooled_candidates(self):
        items = [row([1, 65], 0, 1), row([1, 2, 3, 65], 3, 0, group='source-2')]
        result = absolute_summary(items, 'model', ci=False)
        small = result['bins'][0]
        large = result['bins'][4]
        self.assertEqual(small['rate'], .5)
        self.assertEqual(small['chance'], .625)
        self.assertEqual(small['ratio'], .8)
        self.assertEqual(large['chance'], .375)
        self.assertAlmostEqual(large['ratio'], 4 / 3)

    def test_failed_and_empty_choices_do_not_turn_into_zero_length(self):
        result = summarize([row([1, 4, 10], None), row([1, 4, 10], 2, group='source-2')], 'model', ci=False)
        self.assertEqual(result['n'], 1)
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['absolute']['chosen_mean'], 10.)
        empty = summarize([], 'model')
        self.assertEqual(empty['absolute']['n'], 0)
        for key in ('chosen_mean', 'gold_mean', 'baseline_mean', 'excess', 'excess_ci95', 'excess_median'):
            self.assertIsNone(empty['absolute'][key])
        for record in empty['absolute']['bins']:
            self.assertIsNone(record['chance'])
            self.assertIsNone(record['expected_count'])
            self.assertIsNone(record['ratio'])

    def test_paired_interval_does_not_subtract_independent_mean_intervals(self):
        items = [row([1, 3], 1, group='source-1'), row([99, 101], 1, group='source-2')]
        result = summarize(items, 'model')
        self.assertEqual(result['absolute']['excess_ci95'], [1., 1.])
        self.assertEqual(result['rank_delta']['ci95'], [0., 0.])

    def test_source_group_deletion_exposes_outlier_sign_reversal(self):
        items = [row([1, 3], 0), row([1, 3], 0, group='source-2'), row([1, 21], 1, group='outlier')]
        result = absolute_summary(items, 'model', ci=False)
        self.assertAlmostEqual(result['excess'], 8 / 3)
        self.assertEqual(result['excess_median'], -1.)
        self.assertEqual(result['leave_one_group_out_range'], [-1., 4.5])
        self.assertFalse(result['excess_sign_robust_to_one_group'])
        self.assertEqual(leave_one_group_out([-1., -1., 10.], [('t', 'a')] * 2 + [('t', 'b')]),
                         ([-1., 10.], False))
        self.assertEqual(leave_one_group_out([1., 1.], [('t', 'a')] * 2), (None, None))

    def test_common_cohort_intersects_success_and_both_length_definitions(self):
        items = [row([1, 2], 0, characters=[1, 2]), row([2, 2], 0, characters=[1, 2]),
                 row([1, 2], 0, characters=[2, 2]), row([2, 2], 0, characters=[2, 2]), row([1, 2], None)]
        for item in items:
            item['predictions']['other'] = 0
        informative, valid, receipt = select_cohort(items, ['model', 'other'])
        self.assertEqual(len(informative), 1)
        self.assertEqual(len(valid), 4)
        self.assertEqual(receipt['unavailable_excluded'], 1)
        self.assertEqual(receipt['character_equal_excluded'], 2)
        self.assertEqual(receipt['token_equal_excluded'], 2)
        self.assertEqual(receipt['either_equal_excluded'], 3)

    def test_projection_rejects_missing_candidates_uncontrolled_encoding_and_bad_counts(self):
        observations = {'items': [{'candidate_hashes': ['a', 'b']}]}
        projection = dict(version=1, source_observations_sha256='source',
                          tokenizers={'qwen3': dict(add_special_tokens=False, truncation=False)},
                          lengths={'a': {'qwen3': 1}, 'b': {'qwen3': 2}})
        validate_projection(observations, projection, observations_sha256='source')
        with self.assertRaises(ValueError):
            validate_projection(observations, projection, observations_sha256='changed-source')
        for field, value in [('a', 0), ('a', True), ('b', -1)]:
            broken = copy.deepcopy(projection)
            broken['lengths'][field]['qwen3'] = value
            with self.assertRaises(ValueError):
                validate_projection(observations, broken)
        missing = copy.deepcopy(projection)
        del missing['lengths']['b']
        with self.assertRaises(ValueError):
            validate_projection(observations, missing)
        uncontrolled = copy.deepcopy(projection)
        uncontrolled['tokenizers']['qwen3']['add_special_tokens'] = True
        with self.assertRaises(ValueError):
            validate_projection(observations, uncontrolled)


class TokenLengthPublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observations = json.loads(gzip.decompress(OBSERVATIONS.read_bytes()))
        cls.projection = json.loads(gzip.decompress(PROJECTION.read_bytes()))
        cls.bindings = json.loads((HERE / 'bindings.json').read_bytes())
        cls.published = json.loads((HERE / 'results.json').read_bytes())
        cls.replay = calculate(cls.observations, cls.projection, ci=False)

    def test_text_free_positive_counts_and_source_projection_hashes_are_bound(self):
        bindings, projection = self.bindings, self.projection
        self.assertEqual(hashlib.sha256(PROJECTION.read_bytes()).hexdigest(), bindings['artifact']['sha256'])
        self.assertEqual(hashlib.sha256(gzip.decompress(PROJECTION.read_bytes())).hexdigest(),
                         bindings['artifact']['uncompressed_sha256'])
        source_sha = hashlib.sha256(OBSERVATIONS.read_bytes()).hexdigest()
        self.assertEqual(projection['source_observations_sha256'], source_sha)
        validate_projection(self.observations, projection, observations_sha256=source_sha)
        self.assertFalse(projection['text_included'])
        self.assertFalse(projection['model_weights_used'])
        self.assertFalse(projection['new_inference'])
        self.assertEqual(len(projection['lengths']), 893)
        self.assertEqual(set(projection['tokenizers']), {'qwen3', 'llama32'})

    def test_public_reproduction_matches_all_noninterval_values_and_exact_csv(self):
        expected = {key: value for key, value in self.published.items() if key != 'sources'}
        self.assertEqual(without_intervals(self.replay), without_intervals(expected))
        self.assertEqual(csv_bytes(self.published), (HERE / 'scores.csv').read_bytes())
        rows = list(csv.DictReader(io.StringIO((HERE / 'scores.csv').read_text(encoding='utf-8'))))
        self.assertEqual(len(rows), 2 * 23 * 11 * 2)
        source_paths = dict(observations_sha256=OBSERVATIONS, token_lengths_sha256=PROJECTION,
                            bindings_sha256=HERE/'bindings.json',
                            parent_bindings_sha256=HERE.parent/'option_length_v1/bindings.json',
                            analyzer_sha256=HERE/'analyze.py', protocol_sha256=HERE/'PROTOCOL.md',
                            dependency_sha256=HERE.parent/'option_length_v1/analyze.py')
        for key, path in source_paths.items():
            self.assertEqual(self.published['sources'][key], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_all_primary_models_and_metrics_have_identical_explicit_cohorts(self):
        for reference, entry in self.published['tokenizers'].items():
            expected = 207 if reference == 'qwen3' else 202
            cohort = entry['cohorts']['variable']
            self.assertEqual(cohort['source_n'], 256)
            self.assertEqual(cohort['shared_valid_n'], 254)
            self.assertEqual(cohort['n'], expected)
            self.assertEqual(cohort['shared_valid_n'] - cohort['either_equal_excluded'], expected)
            for model in entry['models'].values():
                self.assertEqual(model['variable']['all']['n'], expected)
                self.assertEqual(model['variable']['all']['absolute']['n'], expected)
                self.assertEqual(model['absolute_all_valid']['variable']['all']['n'], 254)
                for stats in [model['overall']['all'], *[cell['all'] for cell in model['tasks'].values()]]:
                    self.assertEqual(stats['n'], stats['absolute']['n'])
        self.assertEqual(self.published['reference_sensitivity']['n'], 202)

    def test_primary_absolute_and_relative_means_independently_replay_exactly(self):
        for reference, entry in self.published['tokenizers'].items():
            originals = [x for x in prepared_items(self.observations, self.projection, reference)
                         if x['task'] in {'cruxeval', 'when2call'}]
            selected, _, _ = select_cohort(originals, self.observations['models'])
            for name, model in entry['models'].items():
                for mode in ('all', 'errors'):
                    rows = [x for x in selected if mode == 'all' or x['predictions'][name] != x['gold']]
                    expected = model['variable'][mode]
                    self.assertEqual(expected['n'], len(rows))
                    token_scores, character_scores, chosen, gold, baseline = [], [], [], [], []
                    for item in rows:
                        prediction = item['predictions'][name]
                        options = [i for i in range(len(item['token_lengths'])) if mode == 'all' or i != item['gold']]
                        token_scores.append(200 * exact_rank(item['token_lengths'], prediction) - 100)
                        character_scores.append(200 * exact_rank(item['lengths'], prediction) - 100)
                        chosen.append(Fraction(item['token_lengths'][prediction]))
                        gold.append(Fraction(item['token_lengths'][item['gold']]))
                        baseline.append(sum(Fraction(item['token_lengths'][i]) for i in options) / len(options))
                    self.assertAlmostEqual(expected['score'], float(sum(token_scores)/len(rows)), places=10)
                    self.assertAlmostEqual(expected['character']['score'], float(sum(character_scores)/len(rows)), places=10)
                    self.assertAlmostEqual(expected['absolute']['chosen_mean'], float(sum(chosen)/len(rows)), places=10)
                    self.assertAlmostEqual(expected['absolute']['gold_mean'], float(sum(gold)/len(rows)), places=10)
                    self.assertAlmostEqual(expected['absolute']['baseline_mean'], float(sum(baseline)/len(rows)), places=10)
                    self.assertAlmostEqual(expected['absolute']['excess'], float(sum(a-b for a, b in zip(chosen, baseline))/len(rows)), places=10)
                    bins = expected['absolute']['bins']
                    self.assertEqual(sum(cell['chosen_count'] for cell in bins), len(rows))
                    self.assertAlmostEqual(sum(cell['chance'] for cell in bins), 1., places=12)
                    self.assertEqual(len(bins), len(BINS))

    def test_extreme_candidate_source_deletion_is_explicit_and_does_not_replace_primary(self):
        for reference, entry in self.published['tokenizers'].items():
            audit = entry['outlier_sensitivity']
            self.assertTrue(audit['primary_results_unchanged'])
            self.assertEqual(audit['removed_primary_items'], 1)
            self.assertEqual(audit['primary_n'] - audit['retained_n'], 1)
            self.assertEqual(audit['maximum_candidate_tokens'], 702 if reference == 'qwen3' else 234)
            originals = [x for x in prepared_items(self.observations, self.projection, reference)
                         if x['task'] in {'cruxeval', 'when2call'}]
            selected, _, _ = select_cohort(originals, self.observations['models'])
            excluded = {(x['task'], x['group']) for x in audit['source_groups']}
            for name, changes in audit['models'].items():
                for mode, result in changes.items():
                    remaining = [x for x in selected if (x['task'], x['group']) not in excluded
                                 and (mode == 'all' or x['predictions'][name] != x['gold'])]
                    self.assertEqual(result['n_after'], len(remaining))
                    differences = []
                    for item in remaining:
                        options = [i for i in range(len(item['token_lengths']))
                                   if mode == 'all' or i != item['gold']]
                        baseline = sum(Fraction(item['token_lengths'][i]) for i in options) / len(options)
                        differences.append(Fraction(item['token_lengths'][item['predictions'][name]]) - baseline)
                    exact = sum(differences) / len(differences)
                    self.assertAlmostEqual(result['excess_after'], float(exact), places=10)
                    self.assertEqual(result['excess_before'], entry['models'][name]['variable'][mode]['absolute']['excess'])
            self.assertTrue(audit['models']['intern_4b']['all']['sign_changed'])


if __name__ == '__main__':
    unittest.main()
