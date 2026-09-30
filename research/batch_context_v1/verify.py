"""Independent raw reconstruction, including historical-prompt equality."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'research/batch_context_v1'


def load(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    summary = load(HERE / 'summary.json')
    count = 0
    for model, result in summary['models'].items():
        directory = HERE / 'results' / model
        meta = load(directory / 'metadata.json')
        historical = ROOT / 'research/scifact3_census_v1/results/local' / model
        historical_meta = load(historical / 'metadata.json')
        raw = {}
        for condition, execution in result['execution'].items():
            oldfile = historical / f'scifact3_{condition}.json.gz'
            assert sha(oldfile) == historical_meta['suites'][f'scifact3_{condition}']['sha256']
            old = {r['id']: r for r in json.loads(gzip.decompress(oldfile.read_bytes()))['rows']}
            for plan, expected in execution.items():
                path = directory / f'{condition}__{plan}.json'
                assert sha(path) == meta['files'][path.name]['sha256']
                items = load(path)['rows']
                assert len(items) == len({r['id'] for r in items}) == 339
                count += len(items)
                raw[condition, plan] = {r['id']: r for r in items}
                for r in items:
                    prior = old[r['id']]
                    assert r['request_sha256'] == prior['request_sha256']
                    assert r['prompt_token_sha256'] == prior['audit']['prompt_token_sha256']
                    assert r['gold'] == prior['gold']
                    if plan == 'original4':
                        assert r['prediction'] == prior['prediction'], 'Original plan differs from prior census'
                base = raw[condition, 'original4']
                changes = [i for i in base if base[i]['prediction'] != raw[condition, plan][i]['prediction']]
                assert set(changes) == set(expected['changed_ids']) and len(changes) == expected['flips']
                assert sum(r['prediction'] == r['gold'] for r in items) == expected['correct']
        for plan, expected in result['intervention'].items():
            b, r = raw['base', plan], raw['reversed_option_order', plan]
            assert sum(b[i]['prediction'] != r[i]['prediction'] for i in b) == expected['semantic_flips']
            for label in ('all', 'NOINFO'):
                ids = [i for i in b if label == 'all' or b[i]['gold'] == label]
                bb = sum(b[i]['gold'] == b[i]['prediction'] for i in ids)
                rr = sum(r[i]['gold'] == r[i]['prediction'] for i in ids)
                e = expected[label]
                assert (len(ids), bb, rr) == (e['n'], e['base_correct'], e['reverse_correct'])
                assert abs(e['difference_pp'] - (rr-bb)*100/len(ids)) < 1e-12
    assert count == 6780
    print('INDEPENDENTLY VERIFIED: 6780 predictions, paired counts and equal historical request/token hashes')


if __name__ == '__main__':
    main()
