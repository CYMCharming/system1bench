"""Pinned public test admission; raw text and private references stay in .aris.

No inference occurs here. Re-running never changes an existing source receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, request, sha

HERE = Path(__file__).resolve().parent
RAW = ROOT / '.aris/public_expansion_v1/raw'
PRIVATE = ROOT / '.aris/public_expansion_v1'
SEED = 20261006
CLINC_REV = '828f8093932c8fe6ca7936c3d2e52903b1c523de'
BANK_REV = '57ec275d8078af65b7731c2a98be812d844a6d6b'
SOURCES = {
    'clinc_full.json': f'https://raw.githubusercontent.com/clinc/oos-eval/{CLINC_REV}/data/data_full.json',
    'clinc_domains.json': f'https://raw.githubusercontent.com/clinc/oos-eval/{CLINC_REV}/data/domains.json',
    'clinc_license.txt': f'https://raw.githubusercontent.com/clinc/oos-eval/{CLINC_REV}/LICENSE',
    'clinc_readme.md': f'https://raw.githubusercontent.com/clinc/oos-eval/{CLINC_REV}/README.md',
    'banking_train.csv': f'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{BANK_REV}/banking_data/train.csv',
    'banking_test.csv': f'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{BANK_REV}/banking_data/test.csv',
    'banking_license.txt': f'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{BANK_REV}/LICENSE',
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def normalized(text):
    """NFKC, casefold and whitespace only; not an estimate of semantic leakage."""
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def read_sources(raw=RAW):
    full = json.loads((raw / 'clinc_full.json').read_text(encoding='utf-8'))
    domains = json.loads((raw / 'clinc_domains.json').read_text(encoding='utf-8'))
    clinc = {split: [tuple(row) for row in full[split]] + [tuple(row) for row in full['oos_' + split]]
             for split in ('train', 'val', 'test')}
    banking = {}
    for split in ('train', 'test'):
        rows = list(csv.DictReader(io.StringIO((raw / f'banking_{split}.csv').read_text(encoding='utf-8'))))
        if rows and set(rows[0]) != {'text', 'category'}:
            raise ValueError('BANKING77 schema drift')
        banking[split] = [(row['text'], row['category']) for row in rows]
    return clinc, banking, domains


def profile(splits):
    result, indexes = {}, {}
    for split, rows in splits.items():
        by_text = defaultdict(list)
        for i, (text, label) in enumerate(rows):
            if not isinstance(text, str) or not isinstance(label, str):
                raise ValueError('Text and label must be strings')
            by_text[normalized(text)].append((i, label))
        indexes[split] = by_text
        duplicates = {key: values for key, values in by_text.items() if len(values) > 1}
        result[split] = dict(n=len(rows), classes=len(set(label for _, label in rows)),
            class_counts=dict(sorted(Counter(label for _, label in rows).items())),
            empty_texts=sum(not normalized(text) for text, _ in rows),
            empty_labels=sum(not label.strip() for _, label in rows),
            normalized_duplicate_keys=len(duplicates),
            normalized_duplicate_excess=sum(len(values) - 1 for values in duplicates.values()),
            normalized_conflicting_label_keys=sum(len(set(label for _, label in values)) > 1 for values in duplicates.values()))
    overlap = {}
    for prior in ('train', 'val'):
        if prior not in indexes:
            continue
        keys = set(indexes[prior]) & set(indexes['test'])
        overlap[prior + '_test'] = dict(normalized_text_keys=len(keys),
            affected_test_rows=sum(len(indexes['test'][key]) for key in keys),
            affected_test_fraction=sum(len(indexes['test'][key]) for key in keys) / len(splits['test']),
            conflicting_label_keys=sum(set(label for _, label in indexes[prior][key]) !=
                                      set(label for _, label in indexes['test'][key]) for key in keys),
            # Text is not republished. Hashes identify the affected groups for a local replay.
            normalized_text_sha256=sorted(hashlib.sha256(key.encode()).hexdigest() for key in keys))
    return dict(splits=result, overlaps=overlap,
                normalization='Unicode NFKC + casefold + whitespace collapse; punctuation retained')


def make_case(dataset, i, text, label, labels, domain_map=None, binary=False):
    if label not in labels:
        raise ValueError('Reference label outside frozen ontology')
    state = {'user_query': text}
    if binary:
        state['supported_intents'] = [value.replace('_', ' ') for value in labels if value != 'oos']
        criteria = {'known': 'The request matches at least one supported intent.',
                    'oos': 'The request does not match any supported intent.'}
        gold = 'oos' if label == 'oos' else 'known'
        instructions = 'Decide whether the request is within the supported intent catalog.'
    else:
        keys = {value: f'option_{position:03d}' for position, value in enumerate(labels)}
        criteria = {keys[value]: ('No supported intent matches the request.' if value == 'oos'
                                  else value.replace('_', ' ')) for value in labels}
        gold = keys[label]
        instructions = 'Select the single intent that best matches the user request. Select the unsupported option only if none of the supported intents match.' if dataset == 'clinc150' else 'Select the single banking intent that best matches the user request.'
    sid = f'{dataset}/test/{i:05d}'
    return dict(id=sid, group=hashlib.sha256(normalized(text).encode()).hexdigest(),
        source=dataset, stratum=label, state=state,
        questions={'decision': {'type': 'choice', 'instructions': instructions, 'criteria': criteria}},
        gold={'decision': {'label': gold}},
        metadata={'source_split': 'test', 'source_index': i, 'intent': label,
                  'domain': (domain_map or {}).get(label, 'out_of_scope' if label == 'oos' else 'banking'),
                  'adaptation': 'binary_known_vs_oos' if binary else 'full_ontology_choice'})


def pilot(cases, per_class, oos_count=None, blocked_groups=frozenset()):
    """Predeclared hash selection without test-label optimization or duplicates."""
    counts, groups, selected = Counter(), set(), []
    for case in sorted(cases, key=lambda item: hashlib.sha256(f'{SEED}:{item["id"]}'.encode()).hexdigest()):
        label = case['stratum']
        quota = oos_count if label == 'oos' and oos_count is not None else per_class
        if counts[label] < quota and case['group'] not in groups and case['group'] not in blocked_groups:
            selected.append(case)
            counts[label] += 1
            groups.add(case['group'])
    labels = set(case['stratum'] for case in cases)
    expected = {label: (oos_count if label == 'oos' and oos_count is not None else per_class) for label in labels}
    if dict(counts) != expected:
        raise ValueError('Pilot quota cannot be met with unique normalized text')
    return sorted(selected, key=lambda case: case['id'])


def clean_slice(cases, prior_rows):
    blocked = {hashlib.sha256(normalized(text).encode()).hexdigest() for text, _ in prior_rows}
    kept, seen = [], set()
    for case in sorted(cases, key=lambda row: row['id']):
        if case['group'] not in blocked and case['group'] not in seen:
            kept.append(case)
            seen.add(case['group'])
    return kept, blocked


def verify_receipt(raw=RAW):
    receipt = json.loads((HERE / 'source_receipt.json').read_text(encoding='utf-8'))
    for name, entry in receipt.items():
        if entry['url'] != SOURCES[name] or sha(raw / name) != entry['sha256']:
            raise ValueError(f'Source receipt mismatch: {name}')
    return receipt


def prepare(raw=RAW):
    receipt = verify_receipt(raw)
    clinc, banking, domains = read_sources(raw)
    domain_map = {intent: domain for domain, intents in domains.items() for intent in intents}
    if len(domain_map) != 150 or len(domains) != 10:
        raise ValueError('CLINC150 domain ontology changed')
    clinc_labels = sorted(domain_map) + ['oos']
    banking_labels = sorted(set(label for _, label in banking['train']))
    if len(banking_labels) != 77 or len(clinc['test']) != 5500 or len(banking['test']) != 3080:
        raise ValueError('Frozen source counts changed')
    for splits, labels in ((clinc, set(clinc_labels)), (banking, set(banking_labels))):
        for rows in splits.values():
            if any(not normalized(text) or label not in labels for text, label in rows):
                raise ValueError('Empty query or unknown label')
    suites = [dict(name='clinc150_full', domain='multi_domain_intent_with_ood',
                   cases=[make_case('clinc150', i, text, label, clinc_labels, domain_map)
                          for i, (text, label) in enumerate(clinc['test'])]),
              dict(name='banking77_full', domain='banking_fine_grained_intent',
                   cases=[make_case('banking77', i, text, label, banking_labels)
                          for i, (text, label) in enumerate(banking['test'])])]
    clean_clinc, blocked_clinc = clean_slice(suites[0]['cases'], clinc['train'] + clinc['val'])
    clean_banking, blocked_banking = clean_slice(suites[1]['cases'], banking['train'])
    clean = [dict(name='clinc150_exact_clean', domain=suites[0]['domain'], cases=clean_clinc),
             dict(name='banking77_exact_clean', domain=suites[1]['domain'], cases=clean_banking)]
    pilots = [dict(name='clinc150_pilot', domain=suites[0]['domain'], cases=pilot(suites[0]['cases'], 1, 50, blocked_clinc)),
              dict(name='banking77_pilot', domain=suites[1]['domain'], cases=pilot(suites[1]['cases'], 2, blocked_groups=blocked_banking))]
    binary = dict(name='clinc150_binary_ood_adaptation', domain='scope_detection',
                  cases=[make_case('clinc150', i, text, label, clinc_labels, domain_map, binary=True)
                         for i, (text, label) in enumerate(clinc['test'])])
    report = {'clinc150': profile(clinc), 'banking77': profile(banking)}
    save(PRIVATE / 'full.frozen.json', {'suites': suites})
    save(PRIVATE / 'exact_clean.frozen.json', {'suites': clean})
    save(PRIVATE / 'pilot.frozen.json', {'suites': pilots})
    save(PRIVATE / 'binary_ood.frozen.json', {'suites': [binary]})
    for kind, groups in (('full', suites), ('exact_clean', clean), ('pilot', pilots), ('binary_ood', [binary])):
        payloads = [dict(id=case['id'], suite=suite['name'], payload=request(case))
                    for suite in groups for case in suite['cases']]
        save(PRIVATE / f'{kind}.payloads.json', payloads)
        save(PRIVATE / f'{kind}.references.json', [dict(id=case['id'], suite=suite['name'], gold=case['gold'], metadata=case['metadata'])
                                                 for suite in groups for case in suite['cases']])
    manifest = dict(version=1, seed=SEED, status='prepared_not_evaluated',
        licenses={'clinc150': 'CC-BY-3.0', 'banking77': 'CC-BY-4.0'},
        split='official test; training and validation used only for integrity audit and ontology verification',
        option_order='fixed canonical alphabetical intent labels; CLINC oos last; original full choices retained',
        reference_fields_forwarded=False, pilot='CLINC 1/in-scope class + 50 oos; BANKING 2/class; normalized text unique and exclude train/val normalized exact overlaps',
        exact_clean='Supplementary slice only: exclude normalized train/val overlaps and retain first source ID per normalized test text; not pretraining-clean evidence',
        notes=['Full151/77-way tasks, not reduced-way variants.', 'Binary CLINC is a separate adaptation over the same 5500 rows; never count it as independent data.',
               'No model inference has been run; no scores are available.', 'Source training exposure must be shown per model; exact-match audit does not establish pretraining cleanliness.'],
        training_exposure={'startlux_family': {'clinc150': 'declared training source; authors claim train/test filtering', 'banking77': 'declared training source; authors claim train/test filtering'},
                           'innerjev_4b': {'clinc150': 'declared training source', 'banking77': 'declared training source'},
                           'kev_family': {'clinc150': 'publisher describes evaluation-only in current v2; checkpoint-specific verification still required', 'banking77': 'unknown'},
                           'other_models': 'unknown; not presumed clean'},
        training_exposure_sources={
            'startlux_family': 'https://raw.githubusercontent.com/StartLuxLabs/StartLux-Decision/0e7a2e81b9c92756e26d8edd843a44d50e362669/README.md',
            'innerjev_4b': 'https://huggingface.co/datasets/jylin001206/InnerJev-4B-Training-Data/raw/b689deecf7b8b2f6001e5f0ef9779069be1b4bc7/README.md',
            'kev_family': 'https://raw.githubusercontent.com/jaredpalmer/kev/5e42a7a03f28134853dd3ff77461457e921e5ec1/docs/model-cards/kev-9b.md'},
        code_sha256={'prepare.py': sha(Path(__file__))},
        source_receipt_sha256=sha(HERE / 'source_receipt.json'),
        source_files={name: value['sha256'] for name, value in receipt.items()},
        suites={suite['name']: dict(n=len(suite['cases']), classes=len(suite['cases'][0]['questions']['decision']['criteria']),
                    cases_sha256=digest(suite['cases']), payloads_sha256=digest([request(case) for case in suite['cases']]))
                for suite in suites + clean + pilots + [binary]},
        artifacts_sha256={name: sha(PRIVATE / name) for name in ('full.frozen.json', 'exact_clean.frozen.json', 'pilot.frozen.json', 'binary_ood.frozen.json',
                         'full.payloads.json', 'exact_clean.payloads.json', 'pilot.payloads.json', 'binary_ood.payloads.json',
                         'full.references.json', 'exact_clean.references.json', 'pilot.references.json', 'binary_ood.references.json')})
    save(HERE / 'audit.json', report)
    manifest['audit_sha256'] = sha(HERE / 'audit.json')
    save(HERE / 'manifest.json', manifest)
    print(json.dumps({'suites': manifest['suites'], 'audit': report}, ensure_ascii=False))


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    existing = json.loads((HERE / 'source_receipt.json').read_text(encoding='utf-8')) if (HERE / 'source_receipt.json').exists() else None
    entries = {}
    for name, url in SOURCES.items():
        path = RAW / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read()
            path.write_bytes(content)
        entry = dict(url=url, sha256=sha(path), bytes=path.stat().st_size)
        if existing and existing.get(name) != entry:
            raise ValueError(f'Refusing to replace frozen receipt for {name}')
        entries[name] = entry
    if not existing:
        save(HERE / 'source_receipt.json', entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Retrieve immutable public source bytes')
    args = parser.parse_args()
    if args.download:
        download()
    prepare()


if __name__ == '__main__':
    main()
