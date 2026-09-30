"""Read-only independent packet integrity checks and form-validator tests."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    output = HERE / 'local_packets'
    def rows(name):
        with (output / name).open(newline='', encoding='utf-8') as stream:
            return list(csv.DictReader(stream))
    a, b = rows('packet_A.csv'), rows('packet_B.csv')
    x, y = rows('answers_A.csv'), rows('answers_B.csv')
    assert len(a) == len(b) == len(x) == len(y) == 160
    assert {r['audit_id'] for r in a} == {r['audit_id'] for r in b}
    assert [r['audit_id'] for r in a] != [r['audit_id'] for r in b]
    assert {r['audit_id']: r for r in a} == {r['audit_id']: r for r in b}
    assert all(not v for r in x+y for k,v in r.items() if k != 'audit_id')
    assert set(a[0]) == {'audit_id', 'claim', 'paper_title', 'numbered_abstract'}
    manifest = json.loads((output / 'restricted_manifest.json').read_text())
    assert manifest['status'] == 'PREPARED_NOT_ANNOTATED'
    assert sum(r['stratum'] == 'derived' for r in manifest['cases']) == 130
    assert sum(r['reference'] == 'SUPPORT' for r in manifest['cases']) == 15
    assert sum(r['reference'] == 'CONTRADICT' for r in manifest['cases']) == 15
    spec = importlib.util.spec_from_file_location('annotation_checks', HERE / 'analyze_annotations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = {r['audit_id']: r for r in manifest['cases']}
    for name in ('answers_A.csv', 'answers_B.csv'):
        try:
            module.validate_form(output / name, expected)
        except AssertionError:
            pass
        else:
            raise AssertionError('Blank forms must fail')
    # Synthetic in-memory fixtures only, never human forms or report files.
    aa = {'a': {'label': 'SUPPORT'}, 'b': {'label': 'NOINFO'}}
    bb = {'a': {'label': 'SUPPORT'}, 'b': {'label': 'CONTRADICT'}}
    result = module.agreement(aa, bb, ['a', 'b'])
    assert result['agreement'] == .5 and abs(result['cohen_kappa'] - 1/3) < 1e-12
    assert module.agreement(aa, aa, ['a', 'b'])['cohen_kappa'] == 1
    print('VERIFIED: 160 blinded items, distinct ordering, blank human forms, agreement fixtures, incomplete-form rejection')


if __name__ == '__main__':
    main()
