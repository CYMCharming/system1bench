"""Frozen all-case execution-context diagnostic; no historical outputs changed."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import time

from system1bench.common import ROOT, decode, digest, labels, read, request, sha, write
from system1bench.llm_adapter import LLMAdapter

HERE = ROOT / 'research/batch_context_v1'
SOURCE = ROOT / 'research/scifact3_census_v1'
CONDITIONS = ('base', 'reversed_option_order')
PLANS = ('original4', 'repeat4', 'within_reverse4', 'shuffled4', 'singleton')


def schedules(cases):
    ids = [c['id'] for c in cases]
    original = [ids[i:i + 4] for i in range(0, len(ids), 4)]
    shuffled = list(ids)
    random.Random(20260930).shuffle(shuffled)
    return dict(original4=original, repeat4=original,
                within_reverse4=[list(reversed(b)) for b in original],
                shuffled4=[shuffled[i:i + 4] for i in range(0, len(ids), 4)],
                singleton=[[x] for x in ids])


def inputs():
    source_manifest = read(SOURCE / 'manifest.json')
    assert sha(SOURCE / 'frozen.json') == source_manifest['prepared_sha256']
    frozen = read(SOURCE / 'frozen.json')
    suites = {s['name'].removeprefix('scifact3_'): s for s in frozen['suites']}
    for condition in CONDITIONS:
        assert len(suites[condition]['cases']) == 339
        assert len({c['id'] for c in suites[condition]['cases']}) == 339
        for c in suites[condition]['cases']:
            assert digest(request(c)) == c['request_sha256']
            assert len(c['questions']) == 1
    assert [c['id'] for c in suites['base']['cases']] == [c['id'] for c in suites['reversed_option_order']['cases']]
    return frozen, suites


def prepare():
    _, suites = inputs()
    schedule = {k: schedules(suites[k]['cases']) for k in CONDITIONS}
    for cond in CONDITIONS:
        wanted = {c['id'] for c in suites[cond]['cases']}
        for plan, batches in schedule[cond].items():
            actual = [i for b in batches for i in b]
            assert len(actual) == len(set(actual)) == 339 and set(actual) == wanted
    target = HERE / 'manifest.json'
    if target.exists():
        raise FileExistsError('Protocol already frozen')
    write(HERE / 'schedule.json', schedule)
    write(target, dict(protocol='batch-context-v1', prepared_at=datetime.now(timezone.utc).isoformat(),
                       protocol_sha256=sha(HERE / 'PROTOCOL.md'), schedule_sha256=sha(HERE / 'schedule.json'),
                       runner_sha256=sha(__file__), adapter_sha256=sha(ROOT / 'system1bench/llm_adapter.py'),
                       source_frozen_sha256=sha(SOURCE / 'frozen.json'),
                       source_manifest_sha256=sha(SOURCE / 'manifest.json'),
                       conditions=CONDITIONS, plans=PLANS, pairs=339, requests_per_model=3390))
    print('FROZEN', sha(target), flush=True)


def run(model):
    frozen, suites = inputs()
    manifest = read(HERE / 'manifest.json')
    checks = {'protocol_sha256': HERE / 'PROTOCOL.md', 'schedule_sha256': HERE / 'schedule.json',
              'runner_sha256': Path(__file__), 'adapter_sha256': ROOT / 'system1bench/llm_adapter.py',
              'source_frozen_sha256': SOURCE / 'frozen.json', 'source_manifest_sha256': SOURCE / 'manifest.json'}
    assert all(sha(p) == manifest[k] for k, p in checks.items())
    schedule = read(HERE / 'schedule.json')
    output = HERE / 'results' / model
    if output.exists():
        raise FileExistsError('Immutable run already exists; no unverified resumption')
    adapter = LLMAdapter(model, read(ROOT / '.aris/compute/performance_paths.json')[model])
    prior = read(SOURCE / 'results/local' / model / 'metadata.json')['signature']['model']
    for key in ('model_files_sha256', 'chat_template_sha256', 'prompt_version', 'dtype', 'attention',
                'candidate_code_token_ids', 'system_prompt'):
        assert adapter.metadata[key] == prior[key], key
    metadata = dict(status='RUNNING', started_at=datetime.now(timezone.utc).isoformat(),
                    manifest_sha256=sha(HERE / 'manifest.json'), model=adapter.metadata, files={})
    write(output / 'metadata.json', metadata)
    prompt_hashes = {}
    for condition in CONDITIONS:
        cases = {c['id']: c for c in suites[condition]['cases']}
        for plan in PLANS:
            rows, batch_records = [], []
            for bid, member_ids in enumerate(schedule[condition][plan]):
                batch = [cases[x] for x in member_ids]
                q = batch[0]['questions']
                assert all(digest(c['questions']) == digest(q) for c in batch)
                audits = [adapter.audit(c['state'], q, frozen['budget']) for c in batch]
                adapter.synchronize()
                started = time.perf_counter()
                predictions = adapter.predict([request(c)['state'] for c in batch], q,
                                              batch[0]['language'], frozen['budget'], len(batch))
                adapter.synchronize()
                assert len(predictions) == len(batch)
                batch_records.append(dict(id=bid, member_ids=member_ids,
                                          padded_width=max(a[next(iter(q))]['prompt_tokens'] for a in audits),
                                          seconds=time.perf_counter() - started))
                for c, answer, audit in zip(batch, predictions, audits):
                    qid = next(iter(q))
                    h = audit[qid]['prompt_token_sha256']
                    key = (condition, c['id'])
                    if key in prompt_hashes:
                        assert prompt_hashes[key] == h
                    else:
                        prompt_hashes[key] = h
                    prediction, _ = decode(q[qid], answer['answers'][qid])
                    rows.append(dict(id=c['id'], qid=qid, request_sha256=c['request_sha256'],
                                     prompt_token_sha256=h, prompt_tokens=audit[qid]['prompt_tokens'],
                                     labels=labels(q[qid]), gold=str(c['gold'][qid]['label']),
                                     prediction=prediction, candidate_logits=answer['answers'][qid]['candidate_logits'],
                                     batch_id=bid))
            assert len(rows) == len({r['id'] for r in rows}) == 339
            path = output / f'{condition}__{plan}.json'
            write(path, dict(condition=condition, plan=plan, rows=rows, batches=batch_records))
            metadata['files'][path.name] = dict(sha256=sha(path), requests=len(rows))
            write(output / 'metadata.json', metadata)
            print('DONE', model, condition, plan, len(rows), flush=True)
    metadata.update(status='DONE', finished_at=datetime.now(timezone.utc).isoformat())
    write(output / 'metadata.json', metadata)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--model', choices=('qwen3_8b', 'llama31_8b_instruct'))
    a = p.parse_args()
    if a.prepare:
        prepare()
    elif a.model:
        run(a.model)
    else:
        p.error('Choose --prepare or --model')
