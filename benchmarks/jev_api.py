"""Pinned hosted Jev evaluation with bounded retries and append-only request evidence.

Run separately from resident-GPU timing: HTTP timings include the configured proxy.
Never records authentication headers, raw requests, response headers, or HTTP error bodies.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys
import threading
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, digest, labels, read, request, sha, write  # noqa: E402

ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
MODEL = 'jev-1.13.0'
PRICE = 0.042 / 1_000_000
RETRYABLE = {429, 500, 502, 503, 504, 529}


def now():
    return datetime.now(timezone.utc).isoformat()


class Client:
    def __init__(self, credential, rate=15, max_usd=10, continue_invalid_decision=False):
        self.key = Path(credential).read_text().strip()
        if not self.key:
            raise ValueError('Empty credential')
        self.rate, self.max_usd = rate, max_usd
        self.continue_invalid_decision = continue_invalid_decision
        self.lock = threading.Lock()
        self.next_start, self.tokens = 0.0, 0
        self.local = threading.local()
        self.stop = threading.Event()

    def session(self):
        if not hasattr(self.local, 'session'):
            s = requests.Session()
            s.headers.update({'Authorization': 'Bearer ' + self.key})
            self.local.session = s
        return self.local.session

    def predict(self, item):
        suite, case = item
        payload = dict(model=MODEL, **request(case))
        attempts, response, error = [], None, None
        began = time.perf_counter()
        for attempt in range(5):
            if self.stop.is_set():
                return None
            with self.lock:
                if self.tokens * PRICE >= self.max_usd:
                    self.stop.set()
                    return None
                delay = max(0., self.next_start - time.perf_counter())
                self.next_start = max(self.next_start, time.perf_counter()) + 1 / self.rate
            if delay:
                time.sleep(delay)
            start, t = now(), time.perf_counter()
            status, usage, wait = None, None, 0.0
            try:
                r = self.session().post(ENDPOINT, json=payload, timeout=(15, 90), allow_redirects=False)
                status = r.status_code
                if status == 200:
                    body = r.json()
                    response = {k: body.get(k) for k in ['model', 'answers', 'usage']}
                    usage = body.get('usage')
                    if usage and isinstance(usage.get('input_tokens'), int):
                        with self.lock:
                            self.tokens += usage['input_tokens']
                    if body.get('model') != MODEL:
                        raise ValueError('ModelVersionMismatch')
                    if set(body.get('answers', {})) != set(case['questions']):
                        raise ValueError('AnswerSetMismatch')
                    invalid_decision = False
                    for qid, q in case['questions'].items():
                        if body['answers'][qid].get('type') != q['type']:
                            raise ValueError('AnswerTypeMismatch')
                        try:
                            decode(q, body['answers'][qid])
                        except (ValueError, KeyError, TypeError):
                            if not self.continue_invalid_decision:
                                raise
                            invalid_decision = True
                    if usage is None or not isinstance(usage.get('input_tokens'), int) or usage['input_tokens'] < 0:
                        raise ValueError('MissingUsage')
                    response = {k: body[k] for k in ['model', 'answers', 'usage']}
                    # Preserve malformed answers as failures. In diagnostic runs they
                    # should not suppress every later, unrelated request.
                    error = 'InvalidDecision' if invalid_decision else None
                else:
                    error = 'HTTP_' + str(status)
                    if status in {401, 402, 403} or 300 <= status < 400:
                        self.stop.set()
                    if status in RETRYABLE:
                        try:
                            wait = max(float(r.headers.get('retry-after', 0)), 2 ** attempt)
                        except ValueError:
                            wait = 2 ** attempt
            except requests.RequestException as e:
                error = type(e).__name__
                wait = 2 ** attempt
            except (ValueError, KeyError, TypeError):
                error = 'ResponseValidationError'
                self.stop.set()
            elapsed = time.perf_counter() - t
            attempts.append(dict(index=attempt, started_at=start, status=status,
                                 client_seconds=elapsed, error=error, usage=usage))
            if response is not None or wait == 0 or attempt == 4:
                break
            # Never drop failures or substitute a faster successful request.
            time.sleep(min(wait, 60))
        return dict(suite=suite, id=case['id'], request_sha256=case['request_sha256'],
                    payload_sha256=digest(payload), model=MODEL, response=response, error=error,
                    attempts=attempts, total_client_seconds=time.perf_counter() - began,
                    payload_complete=True, server_tokenization_verified=False)


def export(root, frozen, records, signature):
    grouped = {}
    for r in records:
        grouped.setdefault(r['suite'], {})[r['id']] = r
    result = {}
    for suite in frozen['suites']:
        name = suite['name']
        if len(grouped.get(name, {})) != len(suite['cases']):
            continue
        rows = []
        for c in suite['cases']:
            r = grouped[name][c['id']]
            if r['request_sha256'] != c['request_sha256']:
                raise ValueError('Request fingerprint mismatch')
            response = r['response']
            for qid, q in c['questions'].items():
                ans = response['answers'][qid] if response and r['error'] is None else None
                pred, ps = decode(q, ans) if ans else (None, None)
                rows.append(dict(id=c['id'], qid=qid, group=c['group'], family=c['family'], language=c['language'],
                                 request_sha256=c['request_sha256'], questions_sha256=digest(c['questions']),
                                 type=q['type'], labels=labels(q), gold=str(c['gold'][qid]['label']),
                                 answer=ans, prediction=pred, probabilities=ps, error=r['error'],
                                 length_target=c.get('length_target'), position=c.get('position'),
                                 audit={'client_payload_complete': True, 'server_tokenization_verified': False}))
        p = root / (name + '.json.gz')
        payload = dict(signature=signature, rows=rows)
        p.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(), mtime=0))
        result[name] = dict(sha256=sha(p), requests=len(suite['cases']), decisions=len(rows),
                            failures=sum(r['error'] is not None for r in rows))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--credential-file', default='/home/cym/.config/system1bench/jev.key')
    p.add_argument('--frozen', default='data/frozen.json')
    p.add_argument('--output', default='api_results/jev-1.13.0')
    p.add_argument('--workers', type=int, default=12)
    p.add_argument('--rate', type=float, default=15)
    p.add_argument('--max-usd', type=float, default=10)
    p.add_argument('--continue-invalid-decision', action='store_true',
                   help='Record malformed typed answers as invalid and continue the batch')
    args = p.parse_args()
    frozen_path, root = ROOT / args.frozen, ROOT / args.output
    frozen = read(frozen_path)
    if args.frozen == 'data/frozen.json' and sha(frozen_path) != read(ROOT / 'protocol_manifest.json')['prepared_sha256']:
        raise ValueError('Frozen input mismatch')
    root.mkdir(parents=True, exist_ok=True)
    signature = dict(model=MODEL, endpoint=ENDPOINT, frozen_sha256=sha(frozen_path),
                     runner_sha256=sha(Path(__file__)), common_sha256=sha(ROOT / 'system1bench/common.py'),
                     workers=args.workers, max_request_starts_per_second=args.rate,
                     price_usd_per_million_input_tokens=0.042, max_accounted_usd=args.max_usd,
                     attempts_per_request=5, connect_timeout_seconds=15, read_timeout_seconds=90,
                     continue_invalid_decision=args.continue_invalid_decision,
                     client_proxy_used=bool(os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')),
                     full_payload_sent=True, server_tokenizer_available=False,
                     comparison_track='hosted_api_accuracy_and_client_latency')
    contract = root / 'contract.json'
    if contract.exists() and read(contract) != signature:
        raise ValueError('Contract changed; select a fresh output directory')
    write(contract, signature)
    all_items = [(s['name'], c) for s in frozen['suites'] for c in s['cases']]
    journal = root / 'requests.jsonl'
    records = [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    complete = {(r['suite'], r['id']) for r in records}
    wanted = {(s, c['id']): c for s, c in all_items}
    if len(complete) != len(records) or not complete <= wanted.keys():
        raise ValueError('Duplicate/unexpected saved requests')
    for r in records:
        if r['request_sha256'] != wanted[r['suite'], r['id']]['request_sha256']:
            raise ValueError('Saved input changed')
    client = Client(args.credential_file, args.rate, args.max_usd,
                    continue_invalid_decision=args.continue_invalid_decision)
    client.tokens = sum((a.get('usage') or {}).get('input_tokens', 0) for r in records for a in r['attempts'])
    meta_path = root / 'metadata.json'
    started = read(meta_path)['started_at'] if meta_path.exists() else now()
    def status():
        write(meta_path, dict(status='RUNNING', started_at=started, updated_at=now(), signature=signature,
                             planned_requests=len(all_items), completed_requests=len(records),
                             input_tokens=client.tokens, accounted_cost_usd=client.tokens * PRICE,
                             transport_or_response_failed_requests=sum(r['error'] is not None for r in records)))
    status()
    with journal.open('a', buffering=1) as log, ThreadPoolExecutor(max_workers=args.workers) as executor:
        # executor.map consumes in original manifest order; per-attempt timestamps retain completion timing.
        for r in executor.map(client.predict, (x for x in all_items if (x[0], x[1]['id']) not in complete)):
            if r is not None:
                log.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')
                records.append(r)
            if len(records) % 100 == 0 or client.stop.is_set():
                status()
                if r is not None:
                    print('progress', len(records), '/', len(all_items), 'accounted_usd', round(client.tokens * PRICE, 5), flush=True)
    suites = export(root, frozen, records, signature)
    meta = read(meta_path)
    meta.update(status='DONE' if len(records) == len(all_items) else 'INCOMPLETE', finished_at=now(),
                completed_requests=len(records), suites=suites, input_tokens=client.tokens,
                accounted_cost_usd=client.tokens * PRICE, journal_sha256=sha(journal),
                transport_or_response_failed_requests=sum(r['error'] is not None for r in records))
    write(meta_path, meta)
    print(meta['status'], len(records), 'requests;', round(meta['accounted_cost_usd'], 5), 'USD accounted')


if __name__ == '__main__':
    main()
