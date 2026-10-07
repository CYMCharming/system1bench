import unittest

from research.public_intent_pilot_v1.analyze import summarize
from research.public_intent_pilot_v1.verify import verify


class IntentPilotTests(unittest.TestCase):
    def test_failures_remain_in_accuracy_denominator(self):
        rows = [{'gold': 'a', 'prediction': 'a', 'probabilities': {'a': .8, 'b': .2}, 'error': None},
                {'gold': 'b', 'prediction': None, 'probabilities': None, 'error': 'Failure'}]
        result = summarize(rows, ['a', 'b'])
        self.assertEqual(result['accuracy'], .5)
        self.assertEqual(result['macro_f1'], .5)
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['probability_n'], 1)

    def test_zero_gold_mass_not_falsely_finite_nll(self):
        result = summarize([{'gold': 'b', 'prediction': 'a', 'probabilities': {'a': 1., 'b': 0.}, 'error': None}], ['a', 'b'])
        self.assertIsNone(result['nll'])
        self.assertEqual(result['zero_gold_probability'], 1)
        self.assertEqual(result['brier'], 2)

    def test_class_balance_not_replaced_by_overall_accuracy(self):
        rows = [{'gold': 'a', 'prediction': 'a', 'probabilities': {'a': 1., 'b': 0.}, 'error': None}] * 9
        rows += [{'gold': 'b', 'prediction': 'a', 'probabilities': {'a': 1., 'b': 0.}, 'error': None}]
        result = summarize(rows, ['a', 'b'])
        self.assertEqual(result['accuracy'], .9)
        self.assertLess(result['macro_f1'], .5)

    def test_public_results_replay(self):
        verify()


if __name__ == '__main__':
    unittest.main()
