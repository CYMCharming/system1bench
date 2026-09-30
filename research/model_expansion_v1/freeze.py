"""Deterministic, outcome-independent expansion of existing frozen panels."""
from collections import Counter
import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, read, request, sha, write

HERE = ROOT / 'research/model_expansion_v1'

def build():
    suites = []
    sources = {}
    for relative, names in [
        ('research/confirmation_v1/frozen.json', None),
        ('research/domain_expansion_v1/frozen.json', {'contractnli_base', 'contractnli_exact_repeat', 'contractnli_reversed_option_order'}),
        ('research/scifact3_census_v1/frozen.json', {'scifact3_base', 'scifact3_exact_repeat', 'scifact3_reversed_option_order'}),
    ]:
        sources[relative] = sha(ROOT / relative)
        for original in read(ROOT / relative)['suites']:
            if names is not None and original['name'] not in names:
                continue
            suite = copy.deepcopy(original)
            if names is None:
                suite['cases'] = [c for c in suite['cases'] if c['condition'] in {'original', 'repeat', 'reversed', 'counterfactual'}]
                suite['domain'] = 'executable_policy'
            for case in suite['cases']:
                assert digest(request(case)) == case['request_sha256']
                case['expansion_condition'] = case.get('condition', suite.get('condition', 'base'))
            suites.append(suite)
    frozen = dict(protocol='system1bench-model-expansion-v1', suites=suites, budget=dict(max_len=32768, head_max_len=32768))
    assert sum(len(s['cases']) for s in suites) == 2601
    assert sum(len(c['questions']) for s in suites for c in s['cases']) == 4905
    return frozen, sources

def main():
    frozen, sources = build()
    target = HERE / 'frozen.json'
    if target.exists() and read(target) != frozen:
        raise ValueError('Cannot overwrite a changed freeze')
    write(target, frozen)
    pins = read(ROOT / '.aris/model_expansion_paths.json')
    public = {k: {field: v[field] for field in ('repo', 'revision', 'base_repo', 'base_revision', 'temperature', 'version_selection') if field in v} for k, v in pins.items()}
    manifest = dict(protocol=frozen['protocol'], prepared_sha256=sha(target), source_sha256=sources,
                    protocol_sha256=sha(HERE / 'PROTOCOL.md'), preparer_sha256=sha(__file__),
                    model_pins=public, planned_requests_per_model=2601, planned_decisions_per_model=4905,
                    suite_requests={s['name']: len(s['cases']) for s in frozen['suites']},
                    outcome_selection=False)
    path = HERE / 'manifest.json'
    if path.exists() and read(path) != manifest:
        raise ValueError('Cannot change a registered manifest')
    write(path, manifest)
    print(manifest, flush=True)

if __name__ == '__main__':
    main()
