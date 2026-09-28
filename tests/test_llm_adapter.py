import unittest
from system1bench.llm_adapter import answer_from_logits, candidates, messages
from system1bench.common import decode


class PromptContractTests(unittest.TestCase):
    def test_reversal_reassigns_codes_preserves_meanings(self):
        q = {'type': 'choice', 'instructions': 'Pick', 'criteria': {'a': 'First meaning', 'b': 'Second meaning'}}
        reverse = {**q, 'criteria': dict(reversed(list(q['criteria'].items())))}
        a, b = candidates(q), candidates(reverse)
        self.assertEqual([x['label'] for x in a], [x['label'] for x in b][::-1])
        self.assertEqual(a[0]['meaning'], b[1]['meaning'])
        self.assertNotEqual(a[0]['code'], b[1]['code'])

    def test_only_inference_fields(self):
        import json
        q = {'type': 'score', 'instructions': 'Rate', 'criteria': ['bad', 'good']}
        payload = json.loads(messages({'text': 'sample'}, q)[1]['content'])
        self.assertEqual(set(payload), {'state', 'question_type', 'instructions', 'candidates'})
        with self.assertRaises(ValueError):
            messages({'text': 'sample'}, {**q, 'gold': 'SECRET'})
        self.assertEqual(payload['candidates'][1], {'code': 'B', 'label': '1', 'meaning': 'good'})

    def test_boolean_semantics(self):
        c = candidates({'type': 'noul', 'instructions': 'Is it true?'})
        self.assertEqual([v['label'] for v in c], ['false', 'true'])
        self.assertIn('does not hold', c[0]['meaning'])

    def test_boolean_custom_criteria_preserved(self):
        q = {'type': 'noul', 'instructions': 'Inspect',
             'criteria': {'true': 'A human must inspect this run.', 'false': 'No attention is warranted.'}}
        self.assertEqual([c['meaning'] for c in candidates(q)],
                         [q['criteria']['false'], q['criteria']['true']])
        self.assertIn('A human must inspect', messages({}, q)[1]['content'])

    def test_extreme_logits_keep_expected_score_in_range(self):
        q = {'type': 'score', 'instructions': 'Rate', 'criteria': ['a', 'b', 'c', 'd']}
        answer = answer_from_logits(q, [30.5, 29.75, 33.75, 50.5])
        self.assertLessEqual(answer['score'], 3)
        self.assertGreater(answer['score'], 2.99)
        pred, probs = decode(q, answer)
        self.assertEqual(pred, '3')
        self.assertAlmostEqual(sum(probs), 1)

    def test_known_logits_and_invalid_values(self):
        import math
        q = {'type': 'choice', 'instructions': 'Pick', 'criteria': {'a': 'a', 'b': 'b'}}
        answer = answer_from_logits(q, [0, math.log(3)])
        self.assertAlmostEqual(answer['probabilities']['b'], 0.75)
        self.assertEqual(decode(q, answer)[0], 'b')
        with self.assertRaises(ValueError):
            answer_from_logits(q, [0, float('nan')])


if __name__ == '__main__':
    unittest.main()
