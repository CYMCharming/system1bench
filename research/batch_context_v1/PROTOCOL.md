# SciFact3 execution-context stability v1

This is a follow-up diagnostic motivated by observed same-prompt cross-run drift,
not a preregistration of the historical results. Freeze this protocol and schedule
before new inference. Do not overwrite or splice any previous outputs.

Population: all 339 cited claim-document pairs in the existing SciFact3 census,
both base and reversed-option-order conditions, without filtering by labels,
predictions, margins, or earlier changes. This is the same-source dev census,
not a new independent dataset. NOINFO remains derived cited-annotation absence,
not human-adjudicated neutrality.

Models: existing hash-identified Qwen3-8B and Llama-3.1-8B-Instruct checkpoints.
Reuse the unchanged constrained-next-token adapter, prompt template, BF16 and
SDPA execution with explicit position IDs. No sampling, no truncation.

Five execution plans in this fixed order, separately for each condition:
1. original4: census order, contiguous batches of four, final batch of three.
2. repeat4: identical ordered batches to original4, in the same model process.
3. within_reverse4: same batch members and lengths, reversed row order.
4. shuffled4: shuffle all IDs using random.Random(20260930), then batch by four.
5. singleton: census order, one item per forward pass.

Every case must occur exactly once per plan/condition. All model-facing payloads
and unpadded prompt-token hashes must match across plans. Bind source freeze,
protocol, schedule, runner and adapter hashes before inference; bind model
fingerprints and runtime metadata in each run. Retain per-case candidate logits,
semantic predictions, prompt hashes, co-batch IDs and batch widths. No source
text or reference label is sent through metadata to the model.

Primary descriptive endpoints: semantic flips versus original4 in each condition,
maximum per-case candidate-logit change, and original top-two margins of flips.
For each plan also report base-to-reversal flips, correctness changes overall and
within NOINFO, and paired claim-cluster bootstrap intervals (10,000 draws, seed
20260930; descriptive uncertainty on this fixed census). Compare overlap between
execution-context flips and option-reversal flips. No significance fishing,
post-hoc selection, calibrated-confidence or execution-mechanism claim.

The repeat4 control estimates within-process same-packing reproducibility only;
it does not establish reproducibility across processes, GPUs, or runtime versions.
The shuffled/singleton contrasts jointly change padding and kernel shapes, so
they test execution-context sensitivity, not a unique causal batching mechanism.
The fixed plan order is not counterbalanced. BF16 ties use the unchanged native
code-order rule; report ties rather than hiding them. Human adjudication is still
required before interpreting derived NOINFO correctness as definitive truth.
