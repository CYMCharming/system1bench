import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from benchmarks.jev_api import Client, MODEL
from system1bench.common import digest, request


class JevAPITests(unittest.TestCase):
    def case(self):
        c = {'id': 'toy', 'state': 'public text', 'questions': {'q': {'type': 'noul', 'instructions': 'Yes?'}},
             'gold': {'q': {'label': 'true'}}, 'secret_metadata': 'must not send'}
        c['request_sha256'] = digest(request(c))
        return c

    def execute(self, responses, continue_invalid_decision=False):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'credential'; f.write_text('test-key-not-real')
            c = Client(f, rate=100000, continue_invalid_decision=continue_invalid_decision)
            s = Mock(); s.post.side_effect = responses
            with patch.object(c, 'session', return_value=s), patch('benchmarks.jev_api.time.sleep'):
                r = c.predict(('toy', self.case()))
            self.assertEqual(set(s.post.call_args.kwargs['json']), {'state', 'questions', 'model'})
            self.assertNotIn('test-key-not-real', json.dumps(r))
            return r, c

    def response(self, status=200, model=MODEL, p=.7):
        return Mock(status_code=status, headers={}, json=lambda: {'model': model, 'answers': {'q': {'type': 'noul', 'noul': p}}, 'usage': {'input_tokens': 10, 'output_tokens': 2}})

    def test_retry_keeps_first_failure_and_counts_usage(self):
        r, c = self.execute([self.response(429), self.response()])
        self.assertEqual([a['status'] for a in r['attempts']], [429, 200])
        self.assertIsNone(r['error']); self.assertEqual(c.tokens, 10)

    def test_version_drift_stops_and_retains_returned_model(self):
        r, c = self.execute([self.response(model='different-version')])
        self.assertTrue(c.stop.is_set()); self.assertEqual(r['error'], 'ResponseValidationError')
        self.assertEqual(r['response']['model'], 'different-version')

    def test_invalid_probability_is_not_scored(self):
        r, c = self.execute([self.response(p=1.1)])
        self.assertTrue(c.stop.is_set()); self.assertEqual(r['error'], 'ResponseValidationError')

    def test_diagnostic_run_retains_invalid_decision_without_stopping(self):
        r, c = self.execute([self.response(p=1.1)], continue_invalid_decision=True)
        self.assertFalse(c.stop.is_set())
        self.assertEqual(r['error'], 'InvalidDecision')
        self.assertEqual(r['response']['answers']['q']['noul'], 1.1)
        self.assertEqual(c.tokens, 10)

    def test_diagnostic_run_still_stops_on_model_drift(self):
        r, c = self.execute([self.response(model='different-version')], continue_invalid_decision=True)
        self.assertTrue(c.stop.is_set())
        self.assertEqual(r['error'], 'ResponseValidationError')

    def test_auth_failure_stops_without_logging_body(self):
        r, c = self.execute([self.response(401)])
        self.assertTrue(c.stop.is_set()); self.assertEqual(r['error'], 'HTTP_401')
        self.assertIsNone(r['response'])


if __name__ == '__main__':
    unittest.main()
