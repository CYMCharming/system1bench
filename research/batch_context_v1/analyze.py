"""Recompute execution and intervention contrasts from hash-bound raw logits."""
import json
from collections import defaultdict
import numpy as np
from system1bench.common import ROOT, digest, read, sha, write

HERE = ROOT / 'research/batch_context_v1'
PLANS = ('original4', 'repeat4', 'within_reverse4', 'shuffled4', 'singleton')
CONDS = ('base', 'reversed_option_order')


def interval(rows, differences):
    clusters = defaultdict(list)
    for r, value in zip(rows, differences):
        clusters[r['id'].split(':')[1]].append(value)
    sums = np.array([sum(v) for v in clusters.values()], dtype=float)
    counts = np.array([len(v) for v in clusters.values()])
    rng = np.random.default_rng(20260930)
    values = []
    for _ in range(10000):
        idx = rng.integers(0, len(sums), len(sums))
        values.append(100 * sums[idx].sum() / counts[idx].sum())
    return list(np.percentile(values, [2.5, 97.5]))


def main():
    manifest = read(HERE / 'manifest.json')
    schedule = read(HERE / 'schedule.json')
    assert sha(HERE / 'schedule.json') == manifest['schedule_sha256']
    report = dict(protocol_sha256=manifest['protocol_sha256'], manifest_sha256=sha(HERE / 'manifest.json'),
                  analysis_sha256=sha(__file__), pairs=339, models={},
                  caveat='Fixed same-source dev census; NOINFO is derived. Fixed plan order, unchanged BF16 native tie rule; not a causal numerical mechanism test.')
    for model in ('qwen3_8b', 'llama31_8b_instruct'):
        directory = HERE / 'results' / model
        meta = read(directory / 'metadata.json')
        assert meta['status'] == 'DONE' and meta['manifest_sha256'] == sha(HERE / 'manifest.json')
        maps = {}
        for cond in CONDS:
            maps[cond] = {}
            for plan in PLANS:
                path = directory / f'{cond}__{plan}.json'
                assert sha(path) == meta['files'][path.name]['sha256']
                payload = read(path)
                assert payload['condition'] == cond and payload['plan'] == plan
                rows = payload['rows']
                assert len(rows) == len({r['id'] for r in rows}) == 339
                assert [b['member_ids'] for b in payload['batches']] == schedule[cond][plan]
                row_map = {r['id']: r for r in rows}
                for b in payload['batches']:
                    assert [r['id'] for r in rows if r['batch_id'] == b['id']] == b['member_ids']
                    assert max(row_map[i]['prompt_tokens'] for i in b['member_ids']) == b['padded_width']
                for r in rows:
                    z = r['candidate_logits']
                    assert len(z) == len(r['labels']) == 3 and all(np.isfinite(z))
                    assert r['prediction'] == r['labels'][max(range(3), key=z.__getitem__)]
                maps[cond][plan] = row_map
        ids = list(maps['base']['original4'])
        model_report = dict(execution={}, intervention={})
        for cond in CONDS:
            original = maps[cond]['original4']
            original_reversal_flips = {i for i in ids if maps['base']['original4'][i]['prediction'] != maps['reversed_option_order']['original4'][i]['prediction']}
            model_report['execution'][cond] = {}
            for plan in PLANS:
                fresh = maps[cond][plan]
                assert set(fresh) == set(ids)
                for i in ids:
                    for key in ('request_sha256', 'prompt_token_sha256', 'prompt_tokens', 'labels', 'gold'):
                        assert original[i][key] == fresh[i][key]
                flips = [i for i in ids if original[i]['prediction'] != fresh[i]['prediction']]
                margins = [sorted(original[i]['candidate_logits'], reverse=True)[0] - sorted(original[i]['candidate_logits'], reverse=True)[1] for i in flips]
                model_report['execution'][cond][plan] = dict(
                    flips=len(flips), changed_ids=flips,
                    overlap_with_original_reversal_flips=len(set(flips) & original_reversal_flips),
                    original_flip_margins=margins,
                    max_absolute_candidate_logit_change=max(abs(x-y) for i in ids for x,y in zip(original[i]['candidate_logits'], fresh[i]['candidate_logits'])),
                    correct=sum(fresh[i]['prediction'] == fresh[i]['gold'] for i in ids),
                    top_logit_ties=sum(sum(z == max(r['candidate_logits']) for z in r['candidate_logits']) > 1 for r in fresh.values()))
        for plan in PLANS:
            base = maps['base'][plan]
            reverse = maps['reversed_option_order'][plan]
            item = dict(semantic_flips=sum(base[i]['prediction'] != reverse[i]['prediction'] for i in ids))
            for name in ('all', 'NOINFO'):
                use = [i for i in ids if name == 'all' or base[i]['gold'] == name]
                b = sum(base[i]['prediction'] == base[i]['gold'] for i in use)
                r = sum(reverse[i]['prediction'] == reverse[i]['gold'] for i in use)
                differences = [int(reverse[i]['prediction'] == reverse[i]['gold']) - int(base[i]['prediction'] == base[i]['gold']) for i in use]
                item[name] = dict(n=len(use), base_correct=b, reverse_correct=r, difference_pp=100*(r-b)/len(use),
                                  claim_cluster_95=interval([base[i] for i in use], differences))
            model_report['intervention'][plan] = item
        report['models'][model] = model_report
    write(HERE / 'summary.json', report)
    print(json.dumps({m: {'execution_flips': {c: {p: x['flips'] for p,x in v['execution'][c].items()} for c in CONDS},
                         'reversal': v['intervention']} for m,v in report['models'].items()}, indent=2))


if __name__ == '__main__':
    main()
