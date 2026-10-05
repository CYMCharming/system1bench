from types import SimpleNamespace
import unittest

from research.model_expansion_v3.adapter import InternAdapter


def test_intern_boolean_mapping_preserves_choice_and_score():
    responses = {'review': {'probabilities': {'no': .2, 'yes': .8}},
                 'action': {'probabilities': {'opaque_1': .6, 'opaque_2': .4}},
                 'severity': {'probabilities': {'0': .7, '1': .3}}}
    adapter = InternAdapter.__new__(InternAdapter)
    adapter.model = SimpleNamespace(predict=lambda row: {'answers': responses})
    questions = {'review': {'type': 'noul'}, 'action': {'type': 'choice'}, 'severity': {'type': 'score'}}
    result = adapter.predict('state', questions)
    assert result['review'] == {'false': .2, 'true': .8}
    assert result['action'] == responses['action']['probabilities']
    assert result['severity'] == responses['severity']['probabilities']


def test_new_runner_does_not_mutate_frozen_base_on_import():
    from research.startlux_transfer_v1 import run as base
    original = base.__file__, base.HERE, base.get_adapter
    from research.model_expansion_v3 import run as new
    assert new.HERE != base.HERE
    assert (base.__file__, base.HERE, base.get_adapter) == original


class OriginalFamilyAdapterTests(unittest.TestCase):
    def test_boolean_mapping(self):
        test_intern_boolean_mapping_preserves_choice_and_score()

    def test_frozen_evaluator_isolation(self):
        test_new_runner_does_not_mutate_frozen_base_on_import()


if __name__ == '__main__':
    unittest.main()
