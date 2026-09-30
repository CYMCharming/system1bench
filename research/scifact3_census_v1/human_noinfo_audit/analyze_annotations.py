"""Validate independent human forms; refuse blank or fabricated completion."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'local_packets'
LABELS = {'SUPPORT', 'CONTRADICT', 'NOINFO', 'UNCERTAIN'}
REASONS = {'none', 'mixed_evidence', 'insufficient_detail', 'text_quality', 'full_text_needed', 'other'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, fields, items):
    if path.exists():
        raise FileExistsError('Preserve existing reviewer work')
    with path.open('w', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=fields)
        w.writeheader()
        w.writerows(items)


def validate_form(path, expected, adjudication=False):
    items = rows(path)
    assert len(items) == len({r['audit_id'] for r in items}) == len(expected), 'Missing/duplicate IDs'
    assert {r['audit_id'] for r in items} == set(expected), 'Unexpected IDs'
    label_key = 'adjudicated_label' if adjudication else 'label'
    id_key = 'adjudicator_id' if adjudication else 'annotator_id'
    for r in items:
        assert r[label_key] in LABELS, 'Incomplete or invalid human label; no result is computed'
        assert r[id_key].strip() and r['rationale'].strip(), 'Missing human identity/rationale'
        assert r['reason_code'] in REASONS
        if not adjudication:
            assert r['confidence'] in {'high', 'medium', 'low'}
        evidence = r['evidence_sentence_ids'].strip()
        if evidence:
            indices = [int(x.strip()) for x in evidence.split(';')]
            assert len(indices) == len(set(indices)) and all(0 <= i < expected[r['audit_id']]['abstract_sentence_count'] for i in indices)
        if r[label_key] in {'SUPPORT', 'CONTRADICT'}:
            assert evidence, 'Positive evidence judgment needs sentence indices'
    assert len({r[id_key] for r in items}) <= 1, 'One independent reviewer per form'
    return {r['audit_id']: r for r in items}


def agreement(a, b, ids):
    n = len(ids)
    if not n:
        return dict(n=0, agreement=None, cohen_kappa=None)
    observed = sum(a[i]['label'] == b[i]['label'] for i in ids) / n
    expected = sum(sum(a[i]['label'] == k for i in ids) * sum(b[i]['label'] == k for i in ids) for k in LABELS) / n**2
    return dict(n=n, agreement=observed, cohen_kappa=(observed - expected)/(1-expected) if expected < 1 else None)


def source():
    manifest = json.loads((OUT / 'restricted_manifest.json').read_text())
    assert sha(HERE / 'PROTOCOL.md') == manifest['protocol_sha256']
    assert sha(HERE / 'build_packet.py') == manifest['builder_sha256']
    for file in ('packet_A.csv', 'packet_B.csv', 'NOTICE.txt'):
        assert sha(OUT / file) == manifest['file_sha256'][file]
    expected = {r['audit_id']: r for r in manifest['cases']}
    a = validate_form(OUT / 'answers_A.csv', expected)
    b = validate_form(OUT / 'answers_B.csv', expected)
    assert {r['annotator_id'] for r in a.values()}.isdisjoint({r['annotator_id'] for r in b.values()}), 'Reviewers must be distinct'
    return manifest, expected, a, b


def main(mode):
    manifest, expected, a, b = source()
    ids = list(expected)
    queue = [i for i in ids if a[i]['label'] != b[i]['label'] or 'UNCERTAIN' in {a[i]['label'], b[i]['label']}]
    hashes = {name: sha(OUT / name) for name in ('answers_A.csv', 'answers_B.csv', 'restricted_manifest.json')}
    stats = {name: agreement(a, b, [i for i in ids if name == 'all' or expected[i]['stratum'] == name]) for name in ('all', 'derived', 'calibration')}
    if mode == 'prepare-adjudication':
        lock = OUT / 'annotation_lock.json'
        if lock.exists():
            raise FileExistsError('Already locked; preserve independent annotation hashes')
        packets = {r['audit_id']: r for r in rows(OUT / 'packet_A.csv')}
        fields = ['audit_id', 'claim', 'paper_title', 'numbered_abstract', 'reviewer_A_label', 'reviewer_A_rationale', 'reviewer_B_label', 'reviewer_B_rationale']
        save_csv(OUT / 'adjudication_queue.csv', fields,
                 [{**packets[i], 'reviewer_A_label': a[i]['label'], 'reviewer_A_rationale': a[i]['rationale'],
                   'reviewer_B_label': b[i]['label'], 'reviewer_B_rationale': b[i]['rationale']} for i in queue])
        template = next(csv.reader((HERE / 'ADJUDICATION_TEMPLATE.csv').read_text().splitlines()))
        save_csv(OUT / 'adjudication_answers.csv', template, [dict(audit_id=i) for i in queue])
        lock.write_text(json.dumps(dict(input_sha256=hashes, agreement=stats, queue_ids=queue), indent=2) + '\n')
        print(json.dumps(dict(status='INDEPENDENT_FORMS_LOCKED_ADJUDICATION_PENDING', agreement=stats, queue_count=len(queue))))
        return
    lock = json.loads((OUT / 'annotation_lock.json').read_text())
    assert lock['input_sha256'] == hashes, 'Independent forms changed after lock'
    assert lock['queue_ids'] == queue
    adjudicated = validate_form(OUT / 'adjudication_answers.csv', {i: expected[i] for i in queue}, True)
    if adjudicated:
        third = {r['adjudicator_id'] for r in adjudicated.values()}
        assert third.isdisjoint({r['annotator_id'] for r in a.values()} | {r['annotator_id'] for r in b.values()})
    final = {i: adjudicated[i]['adjudicated_label'] if i in adjudicated else a[i]['label'] for i in ids}
    report = dict(status='HUMAN_REVIEW_COMPLETED', agreement=stats,
                  inputs_sha256={**hashes, 'adjudication_answers.csv': sha(OUT / 'adjudication_answers.csv')}, strata={})
    for stratum in ('derived', 'calibration'):
        subset = [i for i in ids if expected[i]['stratum'] == stratum]
        report['strata'][stratum] = dict(n=len(subset), labels={k: sum(final[i] == k for i in subset) for k in sorted(LABELS)},
                                       independent_disagreements=sum(a[i]['label'] != b[i]['label'] for i in subset),
                                       adjudication_required=sum(i in queue for i in subset),
                                       unresolved=sum(final[i] == 'UNCERTAIN' for i in subset),
                                       convention_agreement=sum(final[i] == expected[i]['reference'] for i in subset)/len(subset))
    path = OUT / 'human_review_report.json'
    if path.exists():
        raise FileExistsError('Preserve completed report; version corrections explicitly')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('prepare-adjudication', 'report'))
    main(p.parse_args().mode)
