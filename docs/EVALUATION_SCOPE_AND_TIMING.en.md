# What System1Bench tested, including speed

Local documentation for the existing v0.2 runs. No models were rerun for this explanation, and these new documents have not been uploaded to GitHub. See the [Chinese edition](EVALUATION_SCOPE_AND_TIMING.zh-CN.md).

## Models and workload

Actual checkpoints: **Laya English, Laya Multilingual, Llama-3.1-8B-Instruct, and Qwen3-8B**. Jev has not been run.

Each checkpoint completed 36 suites from 15 source collections: 28 main suites and eight option-order controls. There are 22,934 logical state requests and 26,450 individual decisions per checkpoint, or 105,800 decisions overall, with zero inference failures. Repeated interfaces, aligned translations, shared-state questions, and controls are not independent samples.

## Capability and reliability measurements

| Area | Tasks or controls | Recorded measurements |
|---|---|---|
| Semantic classification | AG News, Emotion, SST5 | Reference accuracy/agreement; macro-F1 where a common label space permits it |
| Intent routing | Banking77, MASSIVE, CLINC | Classification; complete candidate ontologies |
| Evidence-conditioned judgments | BoolQ, XNLI, Jev–Laya claims, TurtleBench | Binary or multiclass reference agreement; Turtle merged-label sensitivity |
| Structured workflows | typed-decisions, JevBench, ReflexBench, Jev–Laya triage/routing/reviews | Choice, boolean, and ordinal decisions; per-family/question strata |
| Safety policy | Aegis2, prompt-injections, Jev–Laya moderation/guard | Agreement with source safety/injection policies |
| Out-of-scope detection | CLINC150/OOS | In-scope accuracy; explicit OOS precision, recall, F1, AUROC |
| Ordered ratings | SST5 and other score questions | Modal/expected-index MAE and within-one agreement; no pooled cross-scale MAE |
| English/Chinese consistency | Aligned XNLI and MASSIVE | Per-language accuracy, prediction agreement, both-languages-correct rates |
| Other languages | Jev–Laya multilingual | Seven-language triage; not paired translations |
| Long-context retrieval | Jev–Laya needle | Agreement by length and fact position; clustering by original needle |
| Option-order stability | Banking77, MASSIVE EN, JevBench original choice, ReflexBench | Same-order repeat versus actual reversal; agreement and accuracy |
| Probability diagnostics | Valid output distributions | Brier, ECE, high-confidence errors; no presumption of calibrated confidence |
| Input completeness and failures | All suites | Token/option/instruction/state audits, collisions, failure counts, shared complete-input subsets |
| Statistical uncertainty | Source-specific decisions | Group-cluster bootstrap intervals, accounting for shared states/stories/needles/duplicates |

All 105,800 decision inputs passed the recorded completeness audit. That does not establish that the model used every fact correctly, or that a dataset target was justified by the visible facts. The [local dataset review](DATASET_VALIDITY_AUDIT.en.md) identifies reference-quality and underdetermination problems. The complete numerical results are in [RESULTS.en.md](RESULTS.en.md), with further strata in [summary.json](../results/summary.json).

## Was speed measured?

**Yes: synchronized batch prediction time was recorded.** Its scope is limited. The runner audits inputs first, synchronizes the GPU, starts `perf_counter`, calls the adapter's `predict`, synchronizes again, and records elapsed time. See [run.py](../system1bench/run.py), particularly the timing block around lines 93–110.

Each model has 3,041 recorded batches, configured for up to eight logical requests per batch, on an NVIDIA A100 80GB PCIe GPU. The following values sum all 36 suites, including controls. Throughput is derived from those existing batch records; it is not a newly run performance benchmark.

| Model | Cumulative predict seconds | Logical requests/s | Decisions/s |
|---|---:|---:|---:|
| Laya English | 223.31 | 102.70 | 118.44 |
| Laya Multilingual | 129.10 | 177.64 | 204.87 |
| Llama-3.1-8B-Instruct | 2251.28 | 10.19 | 11.75 |
| Qwen3-8B | 2375.43 | 9.65 | 11.13 |

Formulas: `logical requests/s = 22,934 / cumulative predict seconds`; `decisions/s = 26,450 / cumulative predict seconds`. One logical state can contain several questions, so request and decision counts differ. Dividing batch time by the number of requests would give an amortized cost, **not measured single-request response latency**.

The [timing JSON](TIMING_FROM_EXISTING_RUNS.json) retains unrounded values, formulas, metadata hashes, and limits. All 144 compressed raw result files were checked against the recorded suite hashes for this derivation, and batch totals were reconciled with metadata.

## What the timing includes and excludes

- Includes the adapter prediction call, associated CPU work inside that call, and completion of GPU work through synchronization. First-batch effects remain; no standardized warm-up exclusion was applied.
- Excludes downloads, model loading, the separately executed input audit, and result-file writes. It is not total wall time to run the evaluation from a cold start.
- LLM prompts are tokenized and cached during the audit. Llama/Qwen perform a separate next-token-logit forward pass per question, without free-text generation or chain of thought; Qwen thinking is disabled. Laya uses its native batched decision API. These adapter implementations do not define equal-compute workloads.
- The machine hosted other tasks. Workload lengths, candidate counts, and question counts vary. These aggregate timings do not establish dedicated-device steady-state throughput, online serving latency, or a stable hardware speed ranking.

## Speed measurements that were not performed

| Metric | Status and reason |
|---|---|
| Text generation tokens/s | Not measured. Decisions are selected from finite answers; no sustained autoregressive text decoding was performed. |
| Generated first-token latency (TTFT) | Not separately measured as a serving/generation metric. The LLM adapter scores next-token logits. |
| Controlled batch-size-1 request latency | Not measured. Existing runs batch up to eight logical requests. |
| End-to-end request p50/p95/p99 | Not measured. Batch timings are not per-request serving latencies. |
| Dedicated-device throughput/concurrency scaling | Not measured under controlled isolation. |
| Cold-start/model-load latency | Excluded from recorded prediction time. |

A future controlled speed benchmark could use an idle device, explicit warm-up, batch-size-1 and batch-size-8 runs, fixed input-length/candidate-count strata, a declared tokenization boundary, and repeated trials. It should report request latency and decisions/s separately, and only use tokens/s if actual text generation is introduced. This is a proposal, not a completed experiment.

## Other unmeasured claims

These runs do not evaluate interactive agent task completion, consequences of chosen actions, business utility, independent human adjudication of every row, or contamination-free generalization. Llama/Qwen results are fixed direct-decision baselines, not their best performance with deliberation or prompt tuning. The new dataset findings are local, and historical frozen scores remain unchanged.
