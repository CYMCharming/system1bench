# Performance experiment record

## Protocol development (before official measurement)

The v0.2 accuracy data, inference adapters and original predictions are retained
unchanged. Performance requests were selected deterministically without using
labels or predictions, then bound by request and source hashes.

An initial mechanical pilot exercised short sequential and maximum-shape batched
requests for all four checkpoints. It was used to verify fit, complete inputs and
callability. Its timings are excluded from the performance matrix.

A same-family provisional method review identified three controls to strengthen:
move periodic monitoring off worker CPU cores, observe per-core/SMT contention,
and enforce a shared software/hardware identity across models and resumed runs.
These were addressed before official measurement. A second mechanical pilot
exercises the revised observer on one Laya and one LLM checkpoint.

The draft warm-up minimum was revised before official measurement from ten to
three calls, with the one-second cumulative minimum retained. Long-context batch
calls already last several seconds. The manifest preserves the previous hash,
amendment timestamp and rationale. This fixed rule is applied to every cell;
no latency-based outlier removal or warm-up convergence claim is made.

Focused tests cover the timing boundary, removal of audit-primed encoding caches,
invalid/missing outputs, duplicate work counts, CPU contention accounting,
round-level bootstrap, full-matrix aggregation, missing cells and mixed environments.
Temporary synthetic test data are not experiment results.

## Official measurement

The run contract is frozen after methodology checks and before the first official
block. Each block records its own start/end time, status and raw artifact hashes.
A complete result requires 32 successful fresh-process blocks and 1,056 cells:
4 checkpoints × 8 rounds × 11 workload strata × 3 batch sizes.

Failures or detected contention invalidate a block; investigate and retain failed
artifacts. Never select the fastest retry. Any deviation or restart is documented
here before inclusion in the final analysis.

## Instrumentation changes

New scripts under `benchmarks/` handle measurement, external telemetry, environment
contracts and CPU-only reporting. New `tests/test_performance.py` fixtures verify
that path. No original adapter, frozen request, scoring definition or historical
accuracy output is modified by performance instrumentation.

## Mechanical preflight contention (excluded)

The revised monitor passed the Laya pilot but invalidated the Qwen pilot when
sustained residual CPU activity exceeded the 15% threshold on cores 16–19.
Inspection observed an unrelated long-running host process using those cores.
No other user's process was modified. Before official measurements, the worker
affinity was moved to currently idle cores 20–23 on the same GPU-local NUMA node,
with siblings 84–87 monitored and observer core 24. The threshold is unchanged.
Failed pilot artifacts remain locally archived and are excluded from all results.

The replacement-affinity Qwen pilot completed successfully with no observer
errors. The earlier Laya external-observer pilot also completed successfully.
An additional regression verifies that an unexpected clean observer exit is
rejected; all nine performance tests pass. These checks precede formal timing.
