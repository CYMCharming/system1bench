import copy
import json
import unittest

from research.public_expansion_v1.prepare import (
    HERE, RAW, SEED, clean_slice, make_case, normalized, pilot, profile, read_sources, verify_receipt,
)
from system1bench.common import request, sha


class PublicExpansionTests(unittest.TestCase):
    def test_normalization_does_not_strip_punctuation(self):
        self.assertEqual(normalized('  ＣＡＲＤ\tPayment  '), 'card payment')
        self.assertNotEqual(normalized('card?'), normalized('card'))

    def test_full_ontology_is_retained_and_gold_not_forwarded(self):
        labels = [f'intent_{i:03d}' for i in range(150)] + ['oos']
        case = make_case('clinc150', 3, 'What is the weather?', 'oos', labels)
        payload = request(case)
        self.assertEqual(set(payload), {'state', 'questions'})
        self.assertEqual(set(payload['state']), {'user_query'})
        self.assertEqual(len(payload['questions']['decision']['criteria']), 151)
        self.assertNotIn('gold', payload)
        self.assertNotIn('metadata', payload)
        self.assertNotIn('source_index', json.dumps(payload))
        changed_reference = copy.deepcopy(case)
        changed_reference['gold']['decision']['label'] = 'option_001'
        changed_reference['metadata']['intent'] = 'secret_changed_gold'
        self.assertEqual(request(changed_reference), payload)

    def test_banking_77_and_binary_scope_semantics(self):
        labels = [f'intent_{i:03d}' for i in range(77)]
        case = make_case('banking77', 0, 'card payment', labels[4], labels)
        self.assertEqual(len(case['questions']['decision']['criteria']), 77)
        self.assertEqual(case['gold']['decision']['label'], 'option_004')
        clinc_labels = [f'intent_{i:03d}' for i in range(150)] + ['oos']
        binary = make_case('clinc150', 0, 'weather', 'oos', clinc_labels, binary=True)
        self.assertEqual(len(binary['state']['supported_intents']), 150)
        self.assertEqual(set(binary['questions']['decision']['criteria']), {'known', 'oos'})
        self.assertEqual(binary['gold']['decision']['label'], 'oos')
        self.assertEqual(binary['metadata']['adaptation'], 'binary_known_vs_oos')

    def test_duplicate_profile_exposes_conflicting_labels_and_split_overlap(self):
        result = profile({'train': [('Pay  CARD', 'pay')],
                          'test': [('pay card', 'pay'), (' PAY\tCARD ', 'refund'), ('new', 'other')]})
        self.assertEqual(result['splits']['test']['normalized_duplicate_excess'], 1)
        self.assertEqual(result['splits']['test']['normalized_conflicting_label_keys'], 1)
        self.assertEqual(result['overlaps']['train_test']['affected_test_rows'], 2)
        self.assertEqual(result['overlaps']['train_test']['conflicting_label_keys'], 1)
        self.assertNotIn('pay card', json.dumps(result))

    def test_pilot_deterministic_and_quota_exact(self):
        labels = ['a', 'b', 'oos']
        cases = [make_case('clinc150', i, f'unique text {i}', labels[i % 3], labels) for i in range(60)]
        first = pilot(cases, 1, 5)
        self.assertEqual(first, pilot(list(reversed(cases)), 1, 5))
        self.assertEqual(len(first), 7)
        self.assertEqual(len({case['group'] for case in first}), 7)
        self.assertEqual(SEED, 20261006)
        with self.assertRaises(ValueError):
            pilot(cases[:2], 3)

    def test_published_manifest_and_receipt(self):
        manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_receipt_sha256'], sha(HERE / 'source_receipt.json'))
        self.assertEqual(manifest['audit_sha256'], sha(HERE / 'audit.json'))
        self.assertEqual(manifest['code_sha256']['prepare.py'], sha(HERE / 'prepare.py'))
        self.assertEqual(manifest['status'], 'prepared_not_evaluated')
        self.assertFalse(manifest['reference_fields_forwarded'])
        for name, n, classes in [('clinc150_full', 5500, 151), ('banking77_full', 3080, 77),
                                 ('clinc150_pilot', 200, 151), ('banking77_pilot', 154, 77),
                                 ('clinc150_binary_ood_adaptation', 5500, 2)]:
            self.assertEqual(manifest['suites'][name]['n'], n)
            self.assertEqual(manifest['suites'][name]['classes'], classes)

    def test_clean_slice_and_pilot_exclude_prior_overlap(self):
        labels = ['a', 'b']
        cases = [make_case('banking77', i, f'text {i}', labels[i % 2], labels) for i in range(10)]
        cases.append(make_case('banking77', 10, ' TEXT  2 ', 'a', labels))
        clean, blocked = clean_slice(cases, [('TEXT 0', 'b')])
        self.assertEqual(len(clean), 9)
        self.assertNotIn(cases[0], clean)
        self.assertNotIn(cases[-1], clean)
        selected = pilot(cases, 1, blocked_groups=blocked)
        self.assertTrue(all(case['group'] not in blocked for case in selected))

    @unittest.skipUnless((RAW / 'clinc_full.json').exists() and (HERE / 'source_receipt.json').exists(),
                         'Raw licensed corpora are intentionally not stored in Git')
    def test_local_downloaded_sources_and_audit_replay(self):
        verify_receipt()
        clinc, banking, _ = read_sources()
        expected = json.loads((HERE / 'audit.json').read_text(encoding='utf-8'))
        self.assertEqual(profile(clinc), expected['clinc150'])
        self.assertEqual(profile(banking), expected['banking77'])
        self.assertEqual(len(clinc['test']), 5500)
        self.assertEqual(len(banking['test']), 3080)


if __name__ == '__main__':
    unittest.main()
