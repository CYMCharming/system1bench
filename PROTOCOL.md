# System1Bench v0.1 — frozen evaluation protocol

Frozen before the new inference runs on 2026-09-28. This release evaluates the
English and multilingual checkpoints in convaiinnovations/laya at
55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851 using Laya 0.3.20. Jev is not evaluated.
The versioned machine-readable specification is `protocol_manifest.json`.

## Scope and reference quality

This is a collection of static typed decisions (`choice`, `noul`, `score`),
not an interactive agent-success benchmark or a measure of general intelligence.
Keep sources, primitives, languages, and reference-quality tracks separate.
There is no single overall ranking/accuracy across the collection.

The nine existing source datasets are AG News, Emotion, Banking77, BoolQ,
SST5, XNLI, MASSIVE, deepset prompt-injections, and LocalLLaMA typed-decisions.
New sources are CLINC150/OOS, JevBench, ReflexBench public choice, the synthetic
jev-laya-benchmark, TurtleBench via decision-model-bench, and Aegis2 prompt safety.
These are 15 source datasets/collections, not 36 independent benchmarks.

## Sampling and input construction

- Standard datasets: fixed 1,000-row samples without replacement, seed 20260927.
  Prompt-injections: all 116 rows. LocalLLaMA: all 400 test states, five questions
  each. XNLI EN/ZH use aligned indices; MASSIVE EN/ZH use aligned IDs and labels.
- Prompt-injections maps0=LEGIT/false and1=INJECTION/true, corroborated by
  deepset/deberta-v3-base-injection config at
  80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1. Its narrow questions/searches-only
  definition of legitimate input makes this an exploratory policy-agreement
  diagnostic. The dataset card's CC BY4.0/Apache2.0 conflict remains unresolved;
  no source text is redistributed. See the source review for immutable links.
- CLINC plus test: all 5,500 rows (4,500 in scope, 1,000 OOS). Full 151-label
  vocabulary from the pinned card's original integer-ID order; OOS is ID 42.
  This tests *explicit OOS-option classification*, not automatic abstention by a
  calibrated confidence threshold. No threshold is fitted on the test set.
- JevBench: public original72/easy48/hard111, preserving native questions.
  Reflex: 95 public-choice development fixtures, not unseen held-out examples.
  Jev–Laya: all 1,470 synthetic items, with the original upstream questions and
  state-field whitelist; ordinal disagreements with the generator/verifier remain.
  TurtleBench: all 1,532 English rows, grouped by story (32 groups).
- Aegis2: all 1,928 non-redacted test prompts, human prompt labels only;
  36 REDACTED rows excluded without inspecting model predictions. The response,
  violated_categories and annotation metadata never enter the inference payload.
  Safe/Needs Caution are non-unsafe; the documented 21 category names appear in
  the instruction. This is a taxonomy-based zero-shot adaptation, not a faithful
  recreation of the complete annotation manual or the official guardrail model.
- Preserve source gold separately from requests. Only `state` and `questions`
  enter the model. Reference rationales, verifier answers, factors, target
  distributions and gold labels are never copied into requests by the adapters.
  Model input and question order have SHA256 digests.

## Token budget

Every new run uses max_len=8192 and head_max_len=4096, batch size8. Actual
padding follows each batch's longest input; this is not 8,192 generated tokens.
The stock model's per-option 48-token cap remains. Audit actual encoded options,
instruction tokens, state space, option collisions and special-mask sanitation.
Report all rows AND the exact no-truncation/no-sanitation subset. Never call the
whole run “full token” unless every relevant audit flag permits that claim.
Long-source context is not shortened by this harness to improve scores.
Shared full-input subset is required for a clean cross-checkpoint comparison
when tokenizer-specific completeness differs.

## Controls

BoolQ noul vs choice and SST5 score vs choice use the same states.
For Banking77, MASSIVE EN, JevBench original choice and Reflex choice, take up to
100 cases using the same fixed seed; perform a same-order repeat and an actual
reversal of the option dictionary. Semantic option IDs and gold stay constant.
Compare reversals to matched repeats; batch shape/precision variation can still
affect results. This single reversal is a diagnostic, not exhaustive invariance.

## Metrics

- Top-label accuracy/agreement: argmax categorical, noul >=0.5, score argmax
  ordinal distribution (not rounded expected index). Invalid/failed predictions
  remain in denominators as incorrect. Report counts of failures.
- 95% case/group-cluster percentile bootstrap intervals, 2,000 resamples, seed
  20260927. All questions on one state, needle variants, duplicate Aegis prompts,
  and TurtleBench story rows are clustered. CIs do not cover annotation bias,
  training overlap, prompt choice, or seed-to-seed model variance.
- Macro F1 over the complete declared label set only when all rows share the
  same label space. Includes zero-support classes (e.g. one MASSIVE intent).
  Uniform-choice baseline is mean(1/K); empirical test-majority baseline is
  descriptive and reported only for a common label space, never trained on test.
- Brier = sum of squared class probability errors per decision. ECE uses10
  equal-width confidence bins. Valid predictions only for probability metrics;
  report their denominator. Probabilities are not claimed to be calibrated.
  Laya rounds to4 decimals: mass tolerance0.02 covers151 classes, then normalize
  only for probability metrics. Preserve raw answers. Never rescale accuracy.
- Ordinal: expected-index MAE, argmax-index MAE and within-one agreement.
- CLINC: in-scope accuracy, explicit OOS precision/recall/F1 and AUROC of P(oos).
  These are empirical results on the dataset's artificial in/OOS prevalence.
- TurtleBench: three-label accuracy plus the adapted upstream binary metric
  obtained by merging Incorrect and Unknown. Do not confuse the two metrics.
- Publish per-primitive, language, family and length/position slices. Synthetic
  reference agreement is not verified real-world task correctness.

## Provenance and recovery

Pin source revisions and verify downloaded bytes. Hash model and Laya source
files before Agent construction. Bind results to prepared inputs, source code,
model bytes and batch config. Finish each suite atomically with its batch times;
an interrupted suite is rerun in full. Completed suites are hash/ID/signature
checked before reuse. Do not combine partial timing with complete denominators.
All checkpoints have fresh runs; previous local results are not relabeled as new.
Reported timing is batch inference wall time, not single-request serving latency.

## Validity and publication

AG News and BoolQ overlap documented Laya training task families. Other public
sources may overlap unknown training corpora; no contamination-free claim.
The general English/multilingual checkpoints are used, not laya-typed-decisions.
Prompts are primarily English even when states are Chinese or other languages.
No official Jev leaderboard number is presented as a new comparative run.
Original data remain download-on-demand under their own terms; public artifacts
contain IDs, hashes, labels, predictions, code and reports, not source texts.
