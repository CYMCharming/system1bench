# Performance experiment audit

**Date:** 2026-09-29  
**Verdict:** PASS  
**Review independence:** same-family  
**Acceptance status:** provisional

No blocking integrity defect was found in the controlled performance evidence. This is a same-family artifact and claim audit, not a top-conference or MLPerf certification.

## Checks

| Check | Status | Result |
|---|---|---|
| A. Ground-truth provenance | PASS | Seven dataset-provided strata, one explicitly labeled synthetic-teacher stratum, and three programmatic needle strata matched the frozen inputs and historical references. |
| B. Score normalization | PASS | Latency, throughput, and agreement use raw denominators; no metric is normalized by model-output statistics. |
| C. Result existence and claims | PASS | All 32 blocks, 1,056 raw cells, hashes, answers, 132 aggregates, CSV rows, and published numeric rows reconciled. |
| D. Execution reachability | PASS | Raw records demonstrate the timed prediction, validation, input-audit, telemetry, and reporting paths executed. |
| E. Evidence scope | PASS WITH LIMITS | Claims are bounded to 11 fixed strata, four adapters, three batch sizes, eight rounds, one host, and the same 64 states per stratum. |
| F. Evaluation type | PASS | Dataset ground truth, labeled synthetic proxy, and programmatic-by-construction strata are distinguished. |

## Independent reconciliation

The audit rebuilt request selection from the frozen data, matched request and historical-reference hashes, decoded every stored answer, and recomputed timing, throughput, agreement, memory, round quantiles, and the seeded bootstrap intervals. The resulting 132 aggregate cells matched `summary.json`, all 132 CSV rows, and every numeric row in the performance report and README.

The validated matrix contains 32 completed blocks, 1,056 raw cells, 67,584 measured request executions, and 98,304 decisions. A separate reporter replay validated all raw cells and regenerated `summary.json`, `metrics.csv`, the performance report, and README byte-for-byte. The CPU suite passed 27 tests and Ruff passed.

## Telemetry qualification

The frozen rejection rule invalidates a block after two consecutive measured-cell intervals above either the 15% residual-worker-core threshold or the 15% SMT-sibling threshold. Six isolated residual-CPU intervals crossed 15%: five in Laya Multilingual round 0 and one in Llama round 5. Their maximum streak was one, so no block reached the predeclared rejection condition. No measured SMT interval crossed 15%, no foreign GPU compute process was observed, and all telemetry streams completed without errors.

The host was not contention-free. CPU affinity and approximately 1 Hz monitoring establish observed isolation under the declared screen, not exclusive ownership, absence of sub-second interference, or absence of shared memory-bandwidth effects.

## Claim limits

The evidence supports the reported per-workload resident-model, in-process state-to-structured-answer latency, fixed-batch throughput, reference agreement, memory, token ranges, and telemetry observations for the declared adapters and host. Reference-agreement intervals measure repeated execution on the same 64 states; they are not dataset-sampling confidence intervals.

The evidence does not establish generated-token performance, network or queue latency, sustainable serving capacity, p99 guarantees, optimal serving-engine performance, architecture-only speedup, population accuracy, arbitrary-hardware generalization, an overall cross-task winner, exclusive host ownership, or MLPerf compliance. Synthetic-teacher results remain teacher agreement, and needle results remain programmatic agreement by construction.

## Evidence

- Manifest SHA256: `bf7b9d2f3008dbd03ad478a5bdb9a267116680b8580843871d792ffb0cedb1fb`
- Run-contract SHA256: `4edfdb46563938014b444c36f759c3ea4a6753caf5061ef97721981cdabacb69`
- Summary SHA256: `3015ccf5433c8e658066228ebe6586a36df3a55b799fcd1159238f7e5db29f68`
- Metrics CSV SHA256: `4a08b20d72c47feeda260986278c4f133bc791ea7a9b612391c1079d7ac6ac2f`
- Locally archived full same-family review and audited input inventory (not distributed in this repository): `.aris/traces/experiment-audit/2026-09-28_performance/final/`

Required fixes: none.
