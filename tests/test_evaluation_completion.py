"""Public full-cohort score integrity and variable-ontology projections."""
import contextlib
import io
import unittest

from research.evaluation_completion_v1.analyze import projection
from research.evaluation_completion_v1.verify import main as verify_public


class CompletionTests(unittest.TestCase):
    def test_projection_preserves_variable_candidate_order(self):
        def row(identity, labels, probabilities, error=None):
            return dict(suite='code', id=identity, qid='decision', request_sha256='digest',
                        gold=labels[0], prediction=labels[0] if error is None else None,
                        labels=labels, probabilities=probabilities, error=error)
        rows = [row('one', ['a', 'b'], {'a': .75, 'b': .25}),
                row('two', ['b', 'a', 'c'], {'a': .2, 'b': .7, 'c': .1}),
                row('failed', ['a', 'b'], None, 'RuntimeError')]
        projected = projection(rows)
        self.assertTrue(projected['variable_labels'])
        decoded = [dict(zip(projected['fields'], values)) for values in projected['rows']]
        self.assertEqual(decoded[1]['labels'], ['b', 'a', 'c'])
        self.assertEqual(decoded[1]['probabilities'], [.7, .2, .1])
        self.assertIsNone(decoded[2]['probabilities'])
        self.assertIsNone(decoded[2]['prediction'])

    def test_uniform_ontology_not_repeated_per_row(self):
        row = dict(suite='intent', id='one', qid='decision', request_sha256='digest',
                   gold='a', prediction='a', labels=['a', 'b'],
                   probabilities={'a': .8, 'b': .2}, error=None)
        projected = projection([row])
        self.assertFalse(projected['variable_labels'])
        self.assertNotIn('labels', projected['fields'])
        self.assertEqual(projected['labels']['intent'], ['a', 'b'])

    def test_public_vectors_replay_complete_case_ranking(self):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_public()


if __name__ == '__main__':
    unittest.main()
