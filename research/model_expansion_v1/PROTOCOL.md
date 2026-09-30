# Five-model expansion v1 — fixed before new inference

Scope: Kev-0.8B, Kev-4B, Kev-9B, NanoJev and Qwen3.5-9B, plus separately
identified historical Jev/Laya/Qwen3/Llama context. This is an expansion study,
not a new hidden test or a claim to measure best-achievable LLM performance.

## Inputs and references

Keep all 288 executable-policy base states (96 each refund/access/routing),
with original, exact repeat, option reversal and one-fact counterfactual.
Keep all 144 previously frozen ContractNLI cases (48/source label), with base,
repeat and reversal. Keep the complete 339 previously frozen cited SciFact
claim–abstract pairs (138 SUPPORT, 71 CONTRADICT, 130 derived NOINFO), with
base, repeat and reversal. Selection is fixed without new model outcomes.
No cross-source blended accuracy. Case × question × condition × model is the
result grain. Policy is programmatic correctness; ContractNLI is source-label
agreement; SciFact NOINFO is missing annotated evidence, NOT human-adjudicated
neutrality. Existing selection, source licenses and overlap limitations remain.

Phase 1: 2,601 requests / 4,905 decisions per model. Freeze hashes, protocol,
source hashes and source model pins before prediction. Models see only state
and questions, never gold or case source metadata.

## Models and fairness

Use official immutable checkpoint revisions. Record backbone, weight hashes,
vendor code hashes, Python/torch/transformers/PEFT and exact settings. Existing
official cached snapshots are acceptable but not described as latest. NanoJev
checkpoint identity (unified-games vs older navigation) MUST be read from
weights/config/card and disclosed. Do not call all releases general-purpose.

Kev: official Checkpoint/encoder/head, strict complete encoding, BF16 merged
adapter, SDPA, calibrated temperature stored in each checkpoint; no date-fact
augmentation, permutation ensemble, prefix cache across requests or graph/fused
optimizations. One request at a time; question rows may run parallel internally.
Record raw temperature-one distributions algebraically as sensitivity; do not
fit temperatures on test outcomes.

NanoJev: official DecisionPredictor, FP32 parameter storage with BF16 autocast,
SDPA, temperature 1.0, no native-Triton override (torch 2.7 has no override).
Use explicit max_length=32768 (within advertised backbone window) to preserve
complete input. This overrides its trained/served default and is a full-input
OOD transfer diagnostic. Record whether each candidate path exceeds the
checkpoint's training limit; also report the within-training-window slice.
Map `noul` to its Boolean schema without changing proposition/criteria.

Qwen3.5-9B: official post-trained checkpoint, text-only BF16/SDPA; identical
existing coded-choice system prompt, thinking disabled, constrained next-token
candidate likelihood (one question per forward). This is a direct-decision
baseline, not a reasoning ceiling. Conditional code likelihood is not a
calibrated probability of correctness. Extra generation, if run, is separate.

Context ceiling 32768 for all; NO silent truncation or shortening. Overflow,
unsupported schema and failures are explicit statuses, never semantic labels.
Report total coverage and paired common-valid denominators, alongside strict
all-case reference accuracy with unavailable cases counted as non-success.
Native interfaces render structured fields differently; same information does
not imply identical tokens or causal architectural identification.

## Analysis fixed before inference

For each source/policy family, report accuracy, class recall/confusion, Brier,
confidence ≥0.9 error fraction, selective risk/coverage, repeat flips, reversal
semantic flips, both-correct stability, both-wrong stability, correction and
regression. Policy action: jointly correct base/counterfactual and whether
prediction changes when executable gold changes. Stable wrong predictions are
not robustness. No invented numeric cutoff for a publishable story.

Use 5,000 paired cluster bootstrap resamples with seed 20261001: policy base
state, legal document, science claim; science document clustering sensitivity.
Paired same-source differences and pointwise descriptive 95% intervals, not
an overall architecture or parameter-scaling causal effect. Model size is
confounded by training histories. Calibration is evaluated, not assumed.

Pre-specified candidate stories: (1) stable-but-wrong vs correct-and-stable;
(2) scaling improves reference agreement without proportionate policy-update
responsiveness; (3) bigger confidence is not bigger safe automation coverage;
(4) source-specific rank reversals between decision and generative interfaces.
New patterns beyond these are explicitly exploratory. Interesting patterns
require all conditions/counterexamples and follow-up independent data; do not
rewrite the frozen experiment after inspecting outputs.

Timing is descriptive execution telemetry only: native candidate paths,
question packing and LLM forwards differ. No fair speedup claim without a
separate controlled performance track.
