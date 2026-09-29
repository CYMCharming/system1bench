"""Verify full hosted Jev evidence and generate source-separated comparisons."""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from system1bench.common import decode,digest,read,sha,write  # noqa: E402
from system1bench.metrics import metrics  # noqa: E402


def main():
    root=ROOT/'api_results/jev-1.13.0';meta=read(root/'metadata.json');contract=read(root/'contract.json')
    if meta['status']!='DONE':raise ValueError('Full hosted matrix incomplete')
    if meta['signature']!=contract or sha(ROOT/'benchmarks/jev_api.py')!=contract['runner_sha256']:raise ValueError('Runner/contract mismatch')
    frozen=read(ROOT/'data/frozen.json')
    if sha(ROOT/'data/frozen.json')!=contract['frozen_sha256']:raise ValueError('Frozen inputs changed')
    journal=root/'requests.jsonl'
    if sha(journal)!=meta['journal_sha256']:raise ValueError('Journal changed')
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    lookup={(r['suite'],r['id']):r for r in records}
    expected={(s['name'],c['id']) for s in frozen['suites'] for c in s['cases']}
    if len(records)!=len(lookup) or set(lookup)!=expected:raise ValueError('Request matrix incomplete/duplicated')
    summary=dict(model='jev-1.13.0',contract_sha256=sha(root/'contract.json'),metadata_sha256=sha(root/'metadata.json'),
                 suites={},requests=len(records),input_tokens=0,decisions=0,failures=0,transport_errors={},response_validation_failures=[],
                 full_client_payload=True,server_tokenization_verified=False)
    times=[];total=[];statuses=Counter()
    for r in records:
        if r['model']!='jev-1.13.0':raise ValueError('Version mismatch')
        for a in r['attempts']:
            statuses[str(a['status'])]+=1;summary['input_tokens']+=(a.get('usage') or {}).get('input_tokens',0)
            if a['status']==200:times.append(a['client_seconds'])
        total.append(r['total_client_seconds'])
        if r['error']=='ResponseValidationError':summary['response_validation_failures'].append({'suite':r['suite'],'id':r['id']})
    if summary['input_tokens']!=meta['input_tokens']:raise ValueError('Usage mismatch')
    for s in frozen['suites']:
        path=root/(s['name']+'.json.gz')
        if sha(path)!=meta['suites'][s['name']]['sha256']:raise ValueError('Suite checksum')
        raw=json.loads(gzip.decompress(path.read_bytes()))
        if raw['signature']!=contract:raise ValueError('Suite signature')
        rows=raw['rows'];case_by_id={c['id']:c for c in s['cases']}
        if len(rows)!=sum(len(c['questions']) for c in s['cases']) or len({(r['id'],r['qid']) for r in rows})!=len(rows):raise ValueError('Decision matrix')
        for r in rows:
            c=case_by_id[r['id']];call=lookup[s['name'],r['id']]
            payload=dict(model='jev-1.13.0',state=c['state'],questions=c['questions'])
            if digest(payload)!=call['payload_sha256'] or r['request_sha256']!=c['request_sha256'] or r['gold']!=str(c['gold'][r['qid']]['label']):raise ValueError('Payload/reference mismatch')
            if r['error']!=call['error']:raise ValueError('Lost failure')
            if r['error'] is None:
                pred,probs=decode(c['questions'][r['qid']],call['response']['answers'][r['qid']])
                if pred!=r['prediction'] or probs!=r['probabilities'] or r['answer']!=call['response']['answers'][r['qid']]:raise ValueError('Decoded output mismatch')
            elif r['prediction'] is not None:raise ValueError('Invalid output was scored')
        result=metrics(rows,True);summary['suites'][s['name']]=dict(reference=s['reference'],track=s['track'],**result)
        summary['decisions']+=len(rows);summary['failures']+=result['failures']
    summary['http_status_counts']=dict(statuses);summary['accounted_cost_usd']=summary['input_tokens']*.042/1e6
    summary['http_200_attempt_latency_seconds']={k:float(v) for k,v in zip(['p50','p95','p99'],np.quantile(times,[.5,.95,.99]))}
    summary['logical_request_time_including_throttle_retries_seconds']={k:float(v) for k,v in zip(['p50','p95','p99'],np.quantile(total,[.5,.95,.99]))}
    write(root/'summary.json',summary)
    history=read(ROOT/'results/summary.json');models=['english','multilingual','llama31_8b_instruct','qwen3_8b']
    lines=['# Jev 1.13.0: hosted evaluation and matched local references','',
           f'All Jev values are our actual API calls, pinned to `jev-1.13.0`: {summary["requests"]:,} requests, {summary["decisions"]:,} decisions across all 36 frozen task/control suites. Invalid/failed decisions: **{summary["failures"]}**, retained in accuracy denominators. No third-party scores are used.','',
           'Requests match the historical local-model states, questions and candidate order. Complete payloads were transmitted; the provider does not expose a tokenizer audit, so server-side complete-input processing is unverified. Synthetic and authored rows measure agreement with their declared references.','',
           '| Suite | Decisions | Laya EN | Laya Multi | Llama 8B | Qwen 8B | Jev 1.13 | Jev 95% cluster CI | Jev failures |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in frozen['suites']:
        name=s['name'];r=summary['suites'][name];values=[history['models'][m]['suites'][name]['all']['accuracy']*100 for m in models]
        lines.append(f'| {name} | {r["n"]} | '+' | '.join(f'{v:.2f}' for v in values)+f' | {r["accuracy"]*100:.2f} | [{r["accuracy_ci95_cluster"][0]*100:.2f}, {r["accuracy_ci95_cluster"][1]*100:.2f}] | {r["failures"]} |')
    lat=summary['http_200_attempt_latency_seconds']
    lines += ['', '## Hosted execution observations','',
              f'- Reported input usage: {summary["input_tokens"]:,} tokens; accounted cost: USD {summary["accounted_cost_usd"]:.5f} at USD 0.042 per million input tokens.',
              '- Accounted usage is not invoice reconciliation: failed responses can omit usage. No account top-up or billing configuration was changed.',
              f'- HTTP-200 attempt durations: p50 {lat["p50"]:.3f} s, p95 {lat["p95"]:.3f} s, descriptive p99 {lat["p99"]:.3f} s. These include invalid HTTP-200 answers and the configured proxy/network/service.',
              '- Calls used up to 12 workers and 15 starts/s, with bounded retries and retained failures. These distributions are workload-mixed collection observations, not controlled service latency, inference-only time or an SLO. They do not enter the local GPU frontier.',
              '- Logical request times including local rate-limit waits and retry backoff are separately stored in the machine-readable summary.',
              '- Returned choice/probability inconsistencies were preserved and counted as invalid; no selected option or probability was repaired. Resumption evaluated only previously unexecuted requests under the same runner/contract.',
              '', 'Evidence: [protocol](../research/JEV_PROTOCOL.md), [interventions](../research/JEV_RUN_LOG.md), [summary](../api_results/jev-1.13.0/summary.json), and [per-request attempts](../api_results/jev-1.13.0/requests.jsonl).']
    (ROOT/'docs/JEV_RESULTS.en.md').write_text('\n'.join(lines)+'\n')
    print('Verified Jev:',summary['requests'],'requests,',summary['decisions'],'decisions,',summary['failures'],'failed decisions')


if __name__=='__main__':main()
