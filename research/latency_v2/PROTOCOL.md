# Matched native-interface latency v2

Offline, resident-weight, batch-one text-only decision requests on one A100 80GB
PCIe (gpu29 GPU 1). All local models use their already pinned original weights,
BF16 computation and SDPA where supported. Native implementations retain their
published temperatures. CUDA graphs, cross-request prefix caches and general-LLM
thinking/generation are disabled. Intern/Qwen3.5/StartLux may use their documented
reference-kernel fallback: this is an implementation-specific ranking, NOT an
optimized-kernel or pure-architecture comparison.

Three fixed workloads request 1, 3 and 8 decision fields from the same short
synthetic customer-support state. The primary speed ranking is the 3-field
choice/Boolean/score request, inspired by Intern-Decision's public latency setup.
The semantic payload is identical, not the tokenizer-specific token count.
Token counts and distinct prompt encodings are disclosed for each adapter.
General LLMs use the frozen constrained-next-token interface, not free-form
autoregressive explanations. Native multi-field models use their native API.

For each workload: 10 warm-up requests, then 5 sequential rounds of 20 requests
(100 measured requests). Model weights are already resident. Each timed request
includes fresh input preparation/tokenization and all requested output fields;
no audit-primed token cache is allowed. GPU synchronization brackets timing.
Probability validation occurs AFTER timing; invalid output fails the measurement
rather than becoming a fast success. All 100 timings are retained.

Use one process and one model at a time on the same physical GPU UUID. Check for
foreign GPU processes before and after every round. Pin the worker to CPU cores
20–23; monitor their SMT siblings and measure unrelated CPU activity using the
existing /proc-based monitor routines. Reject a model block when unrelated core
or sibling busy fraction exceeds 0.15. This is not exclusive CPU ownership or
whole-host isolation; other GPUs on the shared host can remain active.

Report mean, median, P95, requests/s (=100/sum request time), fields/s, complete
request counts and descriptive 95% bootstrap intervals of ROUND mean latency
(2,000 resamples, fixed seed 20261005). Do not pool correlated rounds to invent
uncertainty. Ordering is fixed and recorded, not randomized; no causal claim of
an architecture advantage is supported by this design.

Official RTX 4090 numbers and hosted Jev network/API latency are not mixed into
this local A100 ranking. Missing, failed and not-yet-measured models remain
explicitly unranked. Quality-run elapsed times are never substituted.
