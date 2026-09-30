import unittest
from system1bench.decision_models import validate_distribution

class TestDecisionModelContract(unittest.TestCase):
    def test_semantic_labels_not_position(self):
        q = dict(type='choice', criteria={'right':'R','left':'L'})
        label, p = validate_distribution(q, {'left':.7,'right':.3})
        self.assertEqual(label,'left')
        self.assertEqual(list(p),['right','left'])

    def test_mass_nonfinite_and_wrong_labels(self):
        q = dict(type='choice',criteria={'a':'A','b':'B'})
        for probs in ({'a':.5,'b':.6},{'a':float('nan'),'b':.5},{'a':1,'c':0},{'a':1.1,'b':-.1}):
            with self.assertRaises(ValueError):
                validate_distribution(q,probs)

    def test_noul_and_score(self):
        self.assertEqual(validate_distribution(dict(type='noul'),dict(false=.2,true=.8))[0],'true')
        self.assertEqual(validate_distribution(dict(type='score',criteria=['low','high']),{'0':.8,'1':.2})[0],'0')

    def test_normalizes_roundoff_only(self):
        q = dict(type='choice',criteria={'a':'A','b':'B'})
        self.assertAlmostEqual(sum(validate_distribution(q,dict(a=.5,b=.500001))[1].values()),1)

if __name__ == '__main__':
    unittest.main()
