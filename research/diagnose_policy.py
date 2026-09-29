"""Post-hoc error localization; descriptive counts, no confirmatory p-values."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402


def main():
    base = ROOT/'research/confirmation_v1'
    frozen = read(base/'frozen.json')
    out = {'analysis_scope':'post-hoc descriptive localization after observing primary results; no new inference or confirmatory inference',
           'frozen_sha256':sha(base/'frozen.json'), 'confusions':[], 'routing_boolean_slices':[]}
    roots = list((base/'results').glob('*'))+[base/'api/jev-1.13.0']
    for root in roots:
        meta = read(root/'metadata.json')
        if meta['status'] != 'DONE':
            raise ValueError('Incomplete result')
        for suite in frozen['suites']:
            path = root/(suite['name']+'.json.gz')
            if sha(path) != meta['suites'][suite['name']]['sha256']:
                raise ValueError('Changed result')
            rows = json.loads(gzip.decompress(path.read_bytes()))['rows']
            cases = {c['id']:c for c in suite['cases']}
            for condition in frozen['variants']:
                selected = [r for r in rows if r['qid']=='action' and cases[r['id']]['condition']==condition]
                counts = Counter((r['gold'],r['prediction']) for r in selected)
                out['confusions'].append({'model':root.name,'family':suite['name'],'condition':condition,'n':len(selected),
                                           'cells':[{'gold':g,'prediction':p,'n':n} for (g,p),n in counts.items()]})
                if suite['name']!='policy_routing':
                    continue
                for outage in [False,True]:
                    for paying in [False,True]:
                        rr = [r for r in selected if cases[r['id']]['state']['facts']['outage']==outage and cases[r['id']]['state']['facts']['paying']==paying]
                        out['routing_boolean_slices'].append({'model':root.name,'condition':condition,'outage':outage,'paying':paying,'n':len(rr),
                          'correct':sum(r['error'] is None and r['prediction']==r['gold'] for r in rr),
                          'urgent_support_predictions':sum(r['prediction']=='urgent_support' for r in rr),
                          'failures':sum(r['error'] is not None for r in rr)})
    write(base/'posthoc_diagnostics.json',out)
    lines = ['# Post-hoc policy error localization', '',out['analysis_scope']+'.', '',
             'All five models and eight variants are retained in [the machine-readable diagnostic](confirmation_v1/posthoc_diagnostics.json). Below is the Jev routing slice that motivated this inspection. Counts are descriptive and are not independent confirmation of a causal explanation.', '',
             '| Rendering | outage | paying | N | Correct | Predicted urgent support |', '|---|---|---|---:|---:|---:|']
    for r in out['routing_boolean_slices']:
        if r['model']=='jev-1.13.0' and r['condition'] in ['original','chinese']:
            lines.append(f'| {r["condition"]} | {r["outage"]} | {r["paying"]} | {r["n"]} | {r["correct"]} | {r["urgent_support_predictions"]} |')
    lines += ['', 'The policy requires the conjunction of outage and paying for urgent support. This error concentration motivates testing explicit boolean wording against compact English conjunctions on newly held-out states. The current Chinese condition also changes question and criterion descriptions, so it does not isolate policy wording or language as the cause. No prompt has been revised or rerun on the reported confirmation cases.']
    (ROOT/'research/POSTHOC_DIAGNOSTICS.en.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    main()
