"""Build source-verified blinded packets; never populate human judgments."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def csv_write(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main(seed):
    output = HERE / 'local_packets'
    if output.exists():
        raise FileExistsError('Refusing to overwrite packets or human work')
    manifest = load(SOURCE / 'manifest.json')
    assert sha(SOURCE / 'frozen.json') == manifest['prepared_sha256']
    sidecar = load(SOURCE / 'reference_provenance.json')
    assert sidecar['frozen_sha256'] == manifest['prepared_sha256']
    provenance = {r['case_id']: r for r in sidecar['cases']}
    directory = ROOT / 'data/external/domain_expansion_v1/scifact/data'
    for name in ('claims_dev.jsonl', 'corpus.jsonl'):
        assert sha(directory / name) == manifest['source_sha256'][name]
    claims = {r['id']: r for r in (json.loads(x) for x in (directory / 'claims_dev.jsonl').read_text().splitlines())}
    docs = {r['doc_id']: r for r in (json.loads(x) for x in (directory / 'corpus.jsonl').read_text().splitlines())}
    base = next(s for s in load(SOURCE / 'frozen.json')['suites'] if s['condition'] == 'base')['cases']
    strata = {k: [] for k in ('NOINFO', 'SUPPORT', 'CONTRADICT')}
    for case in base:
        p = provenance[case['id']]
        claim, doc = claims[p['claim_id']], docs[p['document_id']]
        label = case['gold']['answer']['label']
        assert label == p['reference_label']
        assert doc['doc_id'] in claim['cited_doc_ids']
        assert case['state'] == dict(claim=claim['claim'], paper_title=doc['title'], paper_abstract='\n'.join(doc['abstract']))
        entry = claim['evidence'].get(str(doc['doc_id']))
        if label == 'NOINFO':
            assert entry is None and str(doc['doc_id']) not in claim['evidence']
        else:
            assert entry and {e['label'] for e in entry} == {label}
        strata[label].append((case, doc))
    rng = random.Random(seed)
    selected = list(strata['NOINFO'])
    assert len(selected) == 130
    for label in ('SUPPORT', 'CONTRADICT'):
        population = list(strata[label])
        rng.shuffle(population)
        selected.extend(population[:15])
    rng.shuffle(selected)
    packet, restricted = [], []
    for idx, (case, doc) in enumerate(selected, 1):
        audit_id = f'AUDIT-{idx:03d}'
        packet.append(dict(audit_id=audit_id, claim=case['state']['claim'], paper_title=doc['title'],
                           numbered_abstract='\n'.join(f'[{j}] {text}' for j,text in enumerate(doc['abstract']))))
        restricted.append(dict(audit_id=audit_id, case_id=case['id'], reference=case['gold']['answer']['label'],
                               stratum='derived' if case['gold']['answer']['label'] == 'NOINFO' else 'calibration',
                               abstract_sentence_count=len(doc['abstract'])))
    output.mkdir()
    fields = ['audit_id', 'claim', 'paper_title', 'numbered_abstract']
    answer_fields = next(csv.reader((HERE / 'ANNOTATION_TEMPLATE.csv').read_text().splitlines()))
    for annotator, offset in (('A', 1), ('B', 2)):
        ordered = list(packet)
        random.Random(seed + offset).shuffle(ordered)
        csv_write(output / f'packet_{annotator}.csv', fields, ordered)
        csv_write(output / f'answers_{annotator}.csv', answer_fields,
                  [dict(audit_id=r['audit_id']) for r in ordered])
    (output / 'NOTICE.txt').write_text('Local blinded review only; not for redistribution without rights review.\nSciFact claims/evidence CC BY 4.0; abstract corpus ODC-By 1.0; underlying abstract rights may differ.\nSources: https://github.com/allenai/scifact/blob/master/LICENSE.md and https://arxiv.org/abs/2004.14974\nNo human annotations have been performed.\n', encoding='utf-8')
    result = dict(seed=seed, status='PREPARED_NOT_ANNOTATED', items=160, derived=130, calibration=30,
                  protocol_sha256=sha(HERE / 'PROTOCOL.md'), builder_sha256=sha(Path(__file__)),
                  frozen_sha256=sha(SOURCE / 'frozen.json'), provenance_sha256=sha(SOURCE / 'reference_provenance.json'),
                  cases=restricted, file_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()})
    (output / 'restricted_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'items', 'derived', 'calibration')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--seed', type=int, default=20260930)
    main(p.parse_args().seed)
