"""Independent exact-count checks for the all-model shared-task ranking."""
from fractions import Fraction
import json
from pathlib import Path
import unittest

from research.common_suite_v1.analyze import calculate, compose_model

ROOT = Path(__file__).resolve().parents[1]


class CommonSuiteTests(unittest.TestCase):
    def setUp(self):
        self.result = calculate()

    def test_all_twenty_three_models_have_the_identical_nine_tasks(self):
        result = self.result
        self.assertEqual(set(result['excluded_tasks']), {'clinc150_full', 'banking77_full'})
        self.assertEqual(len(result['models']), 23)
        self.assertEqual(len(result['domains']), 7)
        self.assertEqual(len(result['tasks']), 9)
        for model in result['models'].values():
            self.assertEqual(model['classification_tasks'], 9)
            self.assertTrue(model['complete'])
            self.assertFalse({'intent_domain', 'clinc150_full', 'banking77_full'} & set(model['metrics']))
            self.assertEqual(sum(model['metrics'][t]['n'] for t in result['tasks']), 1299)

    def test_fraction_arithmetic_independently_replays_every_composite(self):
        # Independent exact rational arithmetic, not the generator's averaging helper.
        for model in self.result['models'].values():
            m = model['metrics']
            task_fractions = {t: Fraction(m[t]['correct'], m[t]['n']) for t in self.result['tasks']}
            policy = (task_fractions['refund'] + task_fractions['access'] + task_fractions['routing']) / 3
            seven = (policy + task_fractions['legal'] + task_fractions['science'] + task_fractions['cladder']
                     + task_fractions['cruxeval'] + task_fractions['finentity'] + task_fractions['when2call']) / 7
            nine = sum(task_fractions.values()) / 9
            self.assertAlmostEqual(m['overall_domain_equal']['score'], float(seven), places=12)
            self.assertAlmostEqual(m['overall_task_equal']['score'], float(nine), places=12)
            self.assertNotIn('ci95', m['overall_domain_equal'])
            self.assertNotIn('n', m['overall_domain_equal'])

    def test_previously_excluded_families_are_now_present_without_zero_filling(self):
        for identity in ['startlux_4b', 'startlux_9b', 'startlux_27b', 'intern_08b', 'intern_2b', 'intern_4b']:
            self.assertIn(identity, self.result['models'])
            self.assertEqual(self.result['coverage'][identity]['missing_tasks'], [])

    def test_task_counts_match_both_historical_and_full_suite_records(self):
        quality = json.loads((ROOT / 'research/model_expansion_v3/scores.json').read_text())
        full = json.loads((ROOT / 'research/evaluation_completion_v1/results.json').read_text())
        for identity, model in self.result['models'].items():
            for task in ['refund', 'access', 'routing', 'legal', 'science']:
                for field in ['correct', 'n', 'score']:
                    self.assertEqual(model['metrics'][task][field], quality['models'][identity]['metrics'][task][field])
            if identity in full['models']:
                for task in self.result['tasks']:
                    self.assertEqual(model['metrics'][task]['correct'], full['models'][identity]['metrics'][task]['correct'])

    def test_missing_or_wrong_denominator_is_rejected(self):
        model = next(iter(self.result['models'].values()))
        cells = {t: dict(model['metrics'][t]) for t in self.result['tasks']}
        del cells['when2call']
        with self.assertRaises(AssertionError):
            compose_model('invalid', cells)
        cells['when2call'] = dict(model['metrics']['when2call'], n=127)
        with self.assertRaises(AssertionError):
            compose_model('invalid', cells)

    def test_published_result_is_reproducible(self):
        published = json.loads((ROOT / 'research/common_suite_v1/scores.json').read_text(encoding='utf-8'))
        self.assertEqual(published, self.result)


if __name__ == '__main__':
    unittest.main()
