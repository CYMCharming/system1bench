# Jev 1.13.0: hosted evaluation and matched local references

All Jev values are our actual API calls, pinned to `jev-1.13.0`: 22,934 requests, 26,450 decisions across all 36 frozen task/control suites. Invalid/failed decisions: **8**, retained in accuracy denominators. No third-party scores are used.

Requests match the historical local-model states, questions and candidate order. Complete payloads were transmitted; the provider does not expose a tokenizer audit, so server-side complete-input processing is unverified. Synthetic and authored rows measure agreement with their declared references.

| Suite | Decisions | Laya EN | Laya Multi | Llama 8B | Qwen 8B | Jev 1.13 | Jev 95% cluster CI | Jev failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ag_news | 1000 | 94.30 | 92.40 | 88.90 | 86.80 | 88.60 | [86.60, 90.70] | 0 |
| emotion | 1000 | 59.10 | 53.00 | 50.50 | 54.80 | 59.00 | [55.80, 62.00] | 0 |
| banking77 | 1000 | 55.30 | 51.20 | 54.10 | 66.80 | 79.90 | [77.30, 82.40] | 0 |
| boolq | 1000 | 84.60 | 77.70 | 64.80 | 83.50 | 92.60 | [91.10, 94.20] | 0 |
| boolq_choice | 1000 | 83.60 | 77.40 | 68.70 | 83.30 | 92.20 | [90.60, 93.80] | 0 |
| sst5 | 1000 | 34.60 | 29.50 | 32.00 | 45.70 | 56.50 | [53.20, 59.60] | 0 |
| sst5_choice | 1000 | 49.60 | 35.60 | 42.20 | 43.90 | 55.90 | [52.60, 58.90] | 1 |
| xnli_en | 1000 | 86.00 | 81.70 | 46.20 | 78.70 | 85.90 | [83.90, 88.10] | 0 |
| xnli_zh | 1000 | 61.50 | 74.30 | 40.50 | 69.10 | 73.60 | [70.90, 76.30] | 1 |
| massive_en | 1000 | 54.10 | 42.30 | 57.20 | 66.30 | 77.50 | [74.90, 80.10] | 1 |
| massive_zh | 1000 | 30.40 | 33.20 | 53.50 | 62.60 | 76.00 | [73.40, 78.50] | 0 |
| prompt_injections | 116 | 70.69 | 57.76 | 62.93 | 63.79 | 76.72 | [68.97, 84.48] | 0 |
| typed_decisions | 2000 | 36.35 | 34.90 | 51.20 | 55.50 | 73.90 | [71.65, 76.05] | 5 |
| jevbench_original | 72 | 70.83 | 41.67 | 75.00 | 83.33 | 98.61 | [95.83, 100.00] | 0 |
| jevbench_easy | 48 | 95.83 | 89.58 | 100.00 | 100.00 | 100.00 | [100.00, 100.00] | 0 |
| jevbench_hard | 111 | 29.73 | 32.43 | 34.23 | 46.85 | 72.07 | [63.94, 80.18] | 0 |
| reflexbench_reflex-public-choice-v1 | 95 | 58.95 | 46.32 | 60.00 | 84.21 | 93.68 | [88.42, 97.89] | 0 |
| jev_laya_triage | 501 | 62.48 | 55.69 | 75.65 | 80.04 | 90.02 | [87.62, 92.22] | 0 |
| jev_laya_moderation | 426 | 67.84 | 48.36 | 88.97 | 77.46 | 92.72 | [90.38, 94.84] | 0 |
| jev_laya_routing | 411 | 64.23 | 51.09 | 61.31 | 83.70 | 88.81 | [86.13, 91.48] | 0 |
| jev_laya_claims | 300 | 90.00 | 80.00 | 61.67 | 98.67 | 100.00 | [100.00, 100.00] | 0 |
| jev_laya_reviews | 300 | 70.67 | 42.33 | 83.00 | 87.00 | 87.67 | [84.33, 91.00] | 0 |
| jev_laya_guard | 292 | 60.62 | 33.22 | 88.01 | 83.22 | 93.84 | [91.10, 96.58] | 0 |
| jev_laya_multilingual | 256 | 57.81 | 62.50 | 94.53 | 98.44 | 100.00 | [100.00, 100.00] | 0 |
| jev_laya_needle | 900 | 50.22 | 47.44 | 77.89 | 87.78 | 95.22 | [89.66, 99.89] | 0 |
| clinc150_oos | 5500 | 55.73 | 64.76 | 55.20 | 67.78 | 89.51 | [88.73, 90.33] | 0 |
| turtlebench | 1532 | 42.62 | 41.64 | 42.17 | 44.19 | 74.02 | [68.22, 79.10] | 0 |
| aegis2_prompt | 1928 | 49.59 | 57.05 | 66.80 | 72.67 | 82.42 | [80.67, 84.02] | 0 |
| banking77_repeat | 100 | 49.00 | 44.00 | 62.00 | 72.00 | 81.00 | [73.00, 88.00] | 0 |
| banking77_reversed | 100 | 58.00 | 44.00 | 37.00 | 54.00 | 82.00 | [74.00, 89.00] | 0 |
| massive_en_repeat | 100 | 54.00 | 50.00 | 62.00 | 74.00 | 83.00 | [75.00, 90.00] | 0 |
| massive_en_reversed | 100 | 52.00 | 43.00 | 60.00 | 66.00 | 82.00 | [74.00, 89.00] | 0 |
| jevbench_original_repeat | 36 | 61.11 | 58.33 | 80.56 | 83.33 | 100.00 | [100.00, 100.00] | 0 |
| jevbench_original_reversed | 36 | 58.33 | 55.56 | 66.67 | 86.11 | 100.00 | [100.00, 100.00] | 0 |
| reflexbench_reflex-public-choice-v1_repeat | 95 | 58.95 | 46.32 | 60.00 | 84.21 | 94.74 | [90.53, 98.95] | 0 |
| reflexbench_reflex-public-choice-v1_reversed | 95 | 58.95 | 45.26 | 57.89 | 82.11 | 94.74 | [90.53, 98.95] | 0 |

## Hosted execution observations

- Reported input usage: 23,841,873 tokens; accounted cost: USD 1.00136 at USD 0.042 per million input tokens.
- Accounted usage is not invoice reconciliation: failed responses can omit usage. No account top-up or billing configuration was changed.
- HTTP-200 attempt durations: p50 0.421 s, p95 1.273 s, descriptive p99 2.588 s. These include invalid HTTP-200 answers and the configured proxy/network/service.
- Calls used up to 12 workers and 15 starts/s, with bounded retries and retained failures. These distributions are workload-mixed collection observations, not controlled service latency, inference-only time or an SLO. They do not enter the local GPU frontier.
- Logical request times including local rate-limit waits and retry backoff are separately stored in the machine-readable summary.
- Returned choice/probability inconsistencies were preserved and counted as invalid; no selected option or probability was repaired. Resumption evaluated only previously unexecuted requests under the same runner/contract.

Evidence: [protocol](../research/JEV_PROTOCOL.md), [interventions](../research/JEV_RUN_LOG.md), [summary](../api_results/jev-1.13.0/summary.json), and [per-request attempts](../api_results/jev-1.13.0/requests.jsonl).
