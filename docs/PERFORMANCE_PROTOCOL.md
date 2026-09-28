# Controlled local decision performance: protocol v1

This protocol is fixed before measured runs. It evaluates the existing four
checkpoints and decision adapters, with no changes to historical v0.2 accuracy
inputs or scores. It is a local inference experiment, not an MLPerf submission
or an optimized serving-engine comparison.

## Evidence and design choices

| Primary source | Relevant method | Applied here | Deliberate scope difference |
|---|---|---|---|
| Vijay Janapa Reddi et al., **MLPerf Inference Benchmark**, ISCA 2020, [paper](https://arxiv.org/abs/1911.02549) | Section III and Table II distinguish sequential single-stream latency from offline throughput; quality and performance are jointly constrained | Batch size 1 for sequential request latency; batch sizes 8 and 32 for fixed-workload throughput; preserve full inputs, weights, precision, and check output validity/reference agreement | Custom workloads, sample counts, run duration and p50/p95 summaries; no MLPerf LoadGen, official quality target, early stopping, or compliance claim |
| Woosuk Kwon et al., **Efficient Memory Management for Large Language Model Serving with PagedAttention**, SOSP 2023, [paper](https://arxiv.org/abs/2309.06180) | Section 6.1 reports workload length distributions, hardware/baselines and a declared latency/throughput metric | Publish token counts, candidate counts, questions per state, backend versions and hardware; interpret speed together with task reference agreement | No Poisson arrivals or continuous batching; no normalization by generated output tokens because these are finite decisions |
| Amey Agrawal et al., **Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve**, OSDI 2024, [paper](https://arxiv.org/abs/2403.02310) | Distinguishes prefill from decode and evaluates throughput under latency constraints | Clearly separate decision completion from text generation; report latency and throughput independently | No autoregressive decode stream, TTFT/TPOT claims, server SLO or serving-capacity claim |
| [PyTorch benchmarking recipe](https://docs.pytorch.org/tutorials/recipes/recipes/benchmark.html) and [MLCommons inference policies](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) | Synchronization, warm-up, thread control, preprocessing/postprocessing boundaries and run rules | Synchronized wall-clock prediction time; disjoint warm-up states; fixed thread count; serialization/tokenization and native answer construction in the timed call | Not the full official benchmark suite, duration, query-count or statistical certification requirements |

Local copies of the consulted papers/rules and retrieval hashes are retained.
Published citation metadata identifies their original venues; citing a top
venue does not certify this experiment's quality or acceptance prospects.

## Workload selection, fixed without consulting speed or accuracy

`performance/v1/manifest.json` binds the existing frozen inputs and every
selected request. SHA256 ranking with seed
`system1bench-performance-v1-20260928` selects eight disjoint warm-up states
and then 64 measured states per workload. No labels or model outputs enter
selection. Candidate order and original questions remain unchanged.

| Workload | Source | Candidate counts / questions | Purpose |
|---|---|---|---|
| ag_news | AG News | 4; one choice | Short semantic classification |
| boolq | BoolQ validation | 2; one boolean | Passage-conditioned decision |
| sst5 | SST5 | 5; one ordered score | Ordinal output |
| banking77 | Banking77 | 77; one choice | Large candidate set |
| massive_en / massive_zh | MASSIVE | 60; one choice each | English/Chinese intent inputs |
| clinc150_oos | CLINC plus test | 151; one choice | Largest declared candidate set |
| jev_laya_triage | Jev–Laya triage | 6/2/4; three questions | Shared-state workflow |
| needle_100 / needle_1000 / needle_4000 | Jev–Laya needle, source length targets | 5/2; two questions each | Three context-length strata |

There are 11 workload strata. Needle lengths are upstream construction targets,
not identical tokenizer counts. Actual encoded lengths are reported separately
for each model. All four models receive the same complete semantic requests
within each workload. MASSIVE English/Chinese samples are independently ranked
for this performance experiment, so this is not a new paired-language accuracy
comparison. All measured rows must pass the existing completeness audit.

## Hardware and software controls

- Use the same physical NVIDIA A100 80GB PCIe (GPU 2) for every model, with
  model runs sequential. Record GPU UUID, driver, temperature, SM/memory clocks,
  power, utilization and memory. Never change global clock/power settings.
- Require no other compute process on that GPU before loading. Poll occupancy
  and telemetry approximately once per second and at cell boundaries; an
  observed foreign process or telemetry failure invalidates the block. This
  is observed GPU isolation, not proof that no sub-second interference exists.
- Pin each worker to four GPU-local CPU cores, 20–23; OMP/MKL/OpenBLAS threads
  are four and tokenizer parallelism is disabled. Affinity is not exclusive
  ownership. Telemetry runs in a separate process pinned to physical core 24,
  outside both the worker cores and their SMT siblings (84–87). Its children
  inherit that affinity. Record per-core `/proc/stat` busy time, worker process
  CPU time, main-thread context switches and host load at about 1 Hz. Estimate
  residual busy time on worker cores after subtracting worker CPU time, and
  separately monitor sibling busy time. In two consecutive intervals wholly
  inside the same measured cell, residual or sibling busy fractions above 15%
  of the respective four-core capacity invalidate the entire block. This
  predeclared operational screen detects sustained interference; short cells,
  sub-second interference and shared memory-bandwidth effects remain unresolved.
- Freeze `run_contract.json` before measurement. Enforce source/manifest hashes,
  CPU model, kernel, Python, packages, GPU UUID/name/driver, numerical backend flags
  and thread settings before every block; check the same identity on resume and
  independently when reporting. Record per-batch monotonic start/end times to
  permit alignment with external telemetry. No cross-model environment mixing.
- Reuse the validated environment: PyTorch 2.7.1+cu118, Transformers 5.16.1,
  Laya 0.3.20. Use the same checkpoints and native BF16 configuration as v0.2;
  compare model-file hashes to those accuracy-run metadata files before use.
- Laya uses its native decision API. Llama/Qwen retain fixed zero-shot
  candidate-code scoring, SDPA, no free generation, and Qwen thinking disabled.
  This compares these declared adapter implementations, not optimal vLLM,
  TensorRT-LLM, compiled or architecture-independent speed.

## Measurement matrix and boundary

Every workload uses batches of **1, 8, and 32**, over the same 64 measured
states. There are **eight rounds**, each in fresh worker processes. Four-model
Latin rotations repeat twice, balancing each model's position in the order.
Cell and request orders are deterministically shuffled by round, identically
across models. This reduces order bias without establishing independence
across machines or sessions.

Before each cell, release unused CUDA allocations, then warm up on disjoint
states for **at least three calls and at least one cumulative prediction second**.
Warm-up examples cycle to fill large batches. Warm-up calls are validated but
excluded from measured results. Retain every warm-up duration. There is no
filtering by observed speed. A premeasurement amendment reduced the draft minimum
from ten calls to three while retaining the one-second minimum for every model:
large long-context calls already take multiple seconds. The previous manifest
hash and rationale are recorded in the manifest; mechanics-only pilot records
are excluded. This is a fixed warm-up rule, not a convergence certificate.

For each measured call:

1. Clear the LLM adapter's prompt-token cache and synchronize the GPU, outside
   the timing interval. The input audit has already run and cannot prime the
   timed call. Do not reuse tokenization across measured requests.
2. Start `perf_counter`, call `adapter.predict` with raw state objects and the
   original question definitions, synchronize the GPU, and stop the timer.
3. Validate returned answers and write records outside the interval.

Thus time includes state serialization, tokenization, tensor construction and
transfer, model inference, native decoding/answer construction, and completion
of queued GPU work. It excludes model loading, disk input/output, source-data
audit, HTTP/network transport, external queue waiting and the harness's
post-call validation. This is **resident-model in-process state-to-answer
latency**, not whole-service end-to-end latency. Python cyclic GC is disabled
only during the measured cell and restored afterward. Telemetry polling remains
active and its observer effect is part of the declared environment.

Record every batch time, request ID/hash, answer/probabilities, input audit,
warm-up count/duration, peak allocated/reserved CUDA memory, code/model hashes,
and block status. Errors invalidate the block; retain failed artifacts and
investigate rather than silently dropping or retrying slow/failed samples.

## Metrics and uncertainty

- **Batch 1:** per-request p50 and p95 latency within each 64-request round;
  report the median across eight round statistics, all eight values and range.
  A request includes all questions in its state. Do not divide a multi-question
  request's latency by its question count and call it single-decision latency.
- **Batches 8/32:** logical requests/s and decisions/s are total completed work
  divided by the sum of measured prediction seconds, calculated per cell/round.
  This is fixed-batch in-process throughput, not server capacity or sustainable
  arrival rate under a latency SLO.
- Report a 95% percentile bootstrap interval for each across-round median,
  resampling the eight complete round statistics with replacement (10,000
  draws, fixed seed). The small number of rounds limits interval precision;
  these intervals describe run variation for this fixed workload on this host,
  not generalization to arbitrary data, hardware or serving systems.
- p95 is descriptive at 64 states per round. Do not claim a statistically
  certified tail bound or publish p99 from this sample. No hypothesis tests or
  significance claims are made from overlapping percentile summaries.
- Validate every prediction; report failures, full-input coverage, and
  reference agreement on the same selected states. Report agreement by round
  and batch size so numerical/batching changes are visible. Teacher references
  remain teacher agreement, not human-verified correctness.
- Report memory and per-model token distributions alongside results. Do not
  pool heterogeneous task accuracy or throughput into an overall winner.

## Reproduction

Download/freeze the v0.2 inputs using the existing project instructions. Create
a local JSON mapping `english`/`multilingual` to the pinned Laya snapshot root,
`llama31_8b_instruct` to the local Llama checkpoint, and `qwen3_8b` to Qwen.
Paths and model weights are not published. On equivalent hardware, adapt the
physical GPU and CPU-affinity constants explicitly and report the difference.

```bash
python benchmarks/performance.py freeze --manifest performance/v1/manifest.json
python benchmarks/performance_contract.py --output performance/v1/run_contract.json
python benchmarks/performance.py orchestrate --paths .aris/compute/performance_paths.json
python benchmarks/performance_report.py --root performance/v1
```

The distributed manifest and run contract are already frozen; do not overwrite
them. To reproduce on another machine, use a new output directory and record its
own contract; differing devices/environments are a separate experiment.
Use the recorded Python environment, run the documented environment witness,
and verify a free GPU before measured runs. Mechanical pilots are separate
and are not included in speed statistics.

Instrumentation is confined to the new `benchmarks/performance*.py` runners,
their focused tests, and `performance/v1/` outputs. Existing inference adapters,
frozen accuracy data, and historical accuracy outputs remain unchanged.
