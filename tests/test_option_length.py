"""Independent option-length arithmetic and public-only reproduction checks."""
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from research.option_length_v1.analyze import calculate, interval, paired, ranks, summarize


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'research/option_length_v1'


def item(lengths, prediction, gold, *, task='synthetic', group='source-1',
         identity='case-1', condition='original', hashes=None):
    return dict(task=task, id=identity, base_id='base-1', group=group,
                lengths=lengths, word_lengths=lengths, gold=gold,
                predictions={'model': prediction}, condition=condition,
                candidate_hashes=hashes or [str(i) for i in range(len(lengths))])


def exact_ranks(lengths):
    """Pairwise comparison implementation independent of the sorting helper."""
    answer = []
    for i, value in enumerate(lengths):
        comparisons = [Fraction(int(value > other)) if value != other else Fraction(1, 2)
                       for j, other in enumerate(lengths) if j != i]
        answer.append(sum(comparisons) / len(comparisons))
    return answer


def without_intervals(value):
    if isinstance(value, dict):
        return {k: without_intervals(v) for k, v in value.items() if k != 'ci95'}
    if isinstance(value, list):
        return [without_intervals(v) for v in value]
    return value


class OptionLengthMathTests(unittest.TestCase):
    def test_tied_ranks_agree_with_exact_pairwise_arithmetic(self):
        for lengths in ([1, 2, 2, 4], [1, 1, 3, 3], [4, 4, 4], [10, 1], [3, 2, 1, 2, 3]):
            actual = ranks(lengths)
            expected = exact_ranks(lengths)
            for left, right in zip(actual, expected):
                self.assertAlmostEqual(left, float(right), places=14)
            self.assertEqual(sum(expected) / len(expected), Fraction(1, 2))
        self.assertEqual(ranks([1, 2, 2, 4]), [0., .5, .5, 1.])
        self.assertEqual(ranks([4, 4, 4]), [.5, .5, .5])

    def test_uniform_selection_has_zero_skew_not_zero_gold_skew(self):
        rows = [item([1, 2, 2, 4], p, 3, group=f'source-{p}') for p in range(4)]
        result = summarize(rows, 'model', ci=False)
        self.assertEqual(result['n'], 4)
        self.assertEqual(result['correct'], 1)
        self.assertEqual(result['score'], 0.)
        self.assertEqual(result['baseline_score'], 0.)
        self.assertEqual(result['gold_score'], 100.)
        self.assertEqual(result['shortest']['rate'], .25)
        self.assertEqual(result['longest']['rate'], .25)
        self.assertEqual(result['gold_shortest_rate'], 0.)
        self.assertEqual(result['gold_longest_rate'], 1.)
        self.assertAlmostEqual(result['wrong_adjusted_score'], 0., places=12)

    def test_extremum_chance_counts_ties_per_item(self):
        result = summarize([item([1, 1, 3, 3], 0, 2)], 'model', ci=False)
        self.assertEqual(result['shortest']['chance'], .5)
        self.assertEqual(result['longest']['chance'], .5)
        self.assertEqual(result['shortest']['count'], 1)
        self.assertEqual(result['longest']['count'], 0)
        self.assertEqual(result['unique_shortest_four']['n'], 0)
        self.assertIsNone(result['unique_shortest_four']['rate'])

    def test_all_equal_and_empty_populations_are_missing_not_neutral_evidence(self):
        result = summarize([item([3, 3, 3], 1, 0)], 'model')
        self.assertEqual(result['equal_length_excluded'], 1)
        self.assertEqual(result['n'], 0)
        for key in ('score', 'gold_score', 'baseline_score', 'ci95', 'wrong_adjusted_score'):
            self.assertIsNone(result[key])
        self.assertIsNone(result['shortest']['rate'])
        self.assertIsNone(result['longest']['chance'])
        self.assertIsNone(summarize([], 'model')['ci95'])

    def test_correct_answers_can_be_long_without_being_length_errors(self):
        rows = [item([1, 2, 9], 2, 2)]
        result = summarize(rows, 'model', ci=False)
        self.assertEqual(result['score'], result['gold_score'])
        self.assertEqual(result['score'], 100.)
        self.assertEqual(result['wrong_identifiable_n'], 0)
        self.assertIsNone(result['wrong_adjusted_score'])
        errors = summarize(rows, 'model', errors_only=True)
        self.assertEqual(errors['n'], 0)
        self.assertIsNone(errors['score'])

    def test_wrong_only_random_baseline_is_not_uniform_over_all_choices(self):
        # The gold is the longest option; a random wrong answer is shorter on average.
        rows = [item([1, 2, 2, 4], p, 3, group=f'source-{p}') for p in range(3)]
        result = summarize(rows, 'model', errors_only=True, ci=False)
        self.assertEqual(result['n'], 3)
        self.assertEqual(result['correct'], 0)
        self.assertAlmostEqual(result['score'], -100 / 3)
        self.assertAlmostEqual(result['baseline_score'], -100 / 3)
        self.assertAlmostEqual(result['shortest']['chance'], 1 / 3)
        self.assertEqual(result['longest']['chance'], 0.)
        self.assertAlmostEqual(result['wrong_adjusted_score'], 0., places=12)

    def test_binary_and_equal_wrong_options_cannot_identify_wrong_preference(self):
        binary = summarize([item([1, 10], 0, 1)], 'model', errors_only=True)
        self.assertEqual(binary['score'], binary['baseline_score'])
        self.assertEqual(binary['score'], -100.)
        self.assertEqual(binary['wrong_identifiable_n'], 0)
        self.assertIsNone(binary['wrong_adjusted_score'])
        equal_wrong = summarize([item([1, 1, 5], 0, 2)], 'model', errors_only=True)
        self.assertEqual(equal_wrong['score'], equal_wrong['baseline_score'])
        self.assertEqual(equal_wrong['wrong_identifiable_n'], 0)
        self.assertIsNone(equal_wrong['wrong_adjusted_score'])
        longest_wrong = summarize([item([1, 3, 5], 2, 0)], 'model', errors_only=True)
        self.assertEqual(longest_wrong['wrong_identifiable_n'], 1)
        self.assertEqual(longest_wrong['wrong_adjusted_score'], 100.)

    def test_unique_shortest_four_has_correct_all_and_error_denominators(self):
        row = item([1, 10, 10, 10], 0, 3)
        all_rows = summarize([row], 'model', ci=False)['unique_shortest_four']
        errors = summarize([row], 'model', errors_only=True, ci=False)['unique_shortest_four']
        self.assertEqual((all_rows['n'], all_rows['count'], all_rows['rate']), (1, 1, 1.))
        self.assertEqual(all_rows['chance'], .25)
        self.assertAlmostEqual(errors['chance'], 1 / 3)

    def test_failed_requests_do_not_become_neutral_choices(self):
        rows = [item([1, 2, 4], None, 2), item([1, 2, 4], 2, 2, group='source-2')]
        result = summarize(rows, 'model', ci=False)
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['n'], 1)
        self.assertEqual(result['score'], 100.)

    def test_interval_resamples_source_clusters_and_is_seeded(self):
        self.assertIsNone(interval([], []))
        self.assertIsNone(interval([10., -10.], [('task', 'same-source')] * 2))
        left = interval([0., 100.], [('task', 'one'), ('task', 'two')], seed=123, repetitions=1000)
        # Duplicating each record within its source does not invent more independent units.
        right = interval([0., 0., 100., 100.],
                         [('task', 'one')] * 2 + [('task', 'two')] * 2,
                         seed=123, repetitions=1000)
        self.assertEqual(left, right)
        self.assertEqual(left, interval([0., 100.], [('task', 'one'), ('task', 'two')],
                                        seed=123, repetitions=1000))

    def test_reversal_compares_semantic_hash_not_positional_index(self):
        original = item([1, 3, 5], 2, 1, hashes=['a', 'b', 'c'])
        reverse = item([5, 3, 1], 0, 1, condition='reversed', hashes=['c', 'b', 'a'])
        result = paired([original, reverse], 'model')
        self.assertEqual(result['n'], 1)
        self.assertEqual(result['same_semantic_choice'], 1)
        self.assertEqual(result['same_choice_rate'], 1.)
        self.assertEqual(result['length_score_delta'], 0.)
        reverse['predictions']['model'] = 2
        changed = paired([original, reverse], 'model')
        self.assertEqual(changed['same_semantic_choice'], 0)
        self.assertEqual(changed['length_score_delta'], -200.)


class OptionLengthPublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = (HERE / 'observations.json.gz').read_bytes()
        cls.observations = json.loads(gzip.decompress(cls.payload))
        cls.bindings = json.loads((HERE / 'bindings.json').read_bytes())
        cls.published = json.loads((HERE / 'results.json').read_bytes())
        # JSON object keys such as option counts are strings in the stored artifact.
        cls.replayed = json.loads(json.dumps(calculate(cls.observations, ci=False)))

    def test_projection_is_bound_text_free_and_has_exact_shared_population(self):
        receipt = self.bindings['artifact']
        self.assertEqual(hashlib.sha256(self.payload).hexdigest(), receipt['sha256'])
        self.assertEqual(hashlib.sha256(gzip.decompress(self.payload)).hexdigest(), receipt['uncompressed_sha256'])
        self.assertFalse(self.observations['text_included'])
        self.assertFalse(self.observations['new_inference'])
        self.assertTrue(self.bindings['joins_verified'])
        self.assertEqual(len(self.observations['models']), 23)
        self.assertEqual(len(self.observations['items']), 2310)
        original = [x for x in self.observations['items'] if x['condition'] == 'original']
        self.assertEqual(Counter(x['task'] for x in original), self.bindings['tasks'])
        self.assertEqual(len(original), 1299)
        for row in self.observations['items']:
            self.assertEqual(set(row['predictions']), set(self.observations['models']))
            self.assertFalse({'state', 'criteria', 'instructions', 'description', 'prompt'} & set(row))
            self.assertEqual(len(row['lengths']), len(row['candidate_hashes']))
            self.assertTrue(all(isinstance(x, int) and x >= 0 for x in row['lengths']))

    def test_public_only_reproduction_matches_all_noninterval_values(self):
        # No call to collect() or any private frozen input is needed.
        expected = {k: v for k, v in self.published.items() if k != 'sources'}
        self.assertEqual(without_intervals(self.replayed), without_intervals(expected))
        sources = self.published['sources']
        self.assertEqual(sources['observations_sha256'], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(sources['bindings_sha256'], hashlib.sha256((HERE / 'bindings.json').read_bytes()).hexdigest())

    def test_each_original_accuracy_replays_published_common_suite(self):
        common = json.loads((ROOT / 'research/common_suite_v1/scores.json').read_bytes())
        original = [x for x in self.observations['items'] if x['condition'] == 'original']
        for name, model in common['models'].items():
            for task, expected in self.bindings['public_accuracy_replay'][name].items():
                rows = [x for x in original if x['task'] == task]
                correct = sum(x['predictions'][name] == x['gold'] for x in rows)
                failures = sum(x['predictions'][name] is None for x in rows)
                self.assertEqual((len(rows), correct, failures),
                                 (expected['n'], expected['correct'], expected['failures']))
                self.assertEqual((correct, len(rows)),
                                 (model['metrics'][task]['correct'], model['metrics'][task]['n']))

    def test_baselines_and_counts_independently_replay_variable_scope(self):
        rows = [x for x in self.observations['items'] if x['condition'] == 'original'
                and x['task'] in {'cruxeval', 'when2call'} and len(set(x['lengths'])) > 1
                and all(value is not None for value in x['predictions'].values())]
        self.assertEqual(len(rows), 221)
        for name, model in self.published['models'].items():
            valid = [r for r in rows if r['predictions'][name] is not None]
            expected = model['variable']['all']
            exact_score = sum(200 * exact_ranks(r['lengths'])[r['predictions'][name]] - 100
                              for r in valid) / len(valid)
            exact_gold = sum(200 * exact_ranks(r['lengths'])[r['gold']] - 100
                             for r in valid) / len(valid)
            self.assertEqual(expected['n'], len(valid))
            self.assertAlmostEqual(expected['score'], float(exact_score), places=11)
            self.assertAlmostEqual(expected['gold_score'], float(exact_gold), places=11)
            for name_key, extreme in [('shortest', min), ('longest', max)]:
                count = sum(r['lengths'][r['predictions'][name]] == extreme(r['lengths']) for r in valid)
                chance = sum(Fraction(r['lengths'].count(extreme(r['lengths'])), len(r['lengths']))
                             for r in valid) / len(valid)
                self.assertEqual(expected[name_key]['count'], count)
                self.assertAlmostEqual(expected[name_key]['chance'], float(chance), places=12)


if __name__ == '__main__':
    unittest.main()
