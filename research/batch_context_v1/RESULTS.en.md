# Execution-context stability follow-up

Completed 2026-09-30. Both models completed all 3,390 planned decisions each,
with no failures or exclusions. All 6,780 rows were independently checked
against hash-bound raw files, the original census requests and unpadded token
hashes. Model-facing input and the adapter were unchanged. The original plan
reproduced the prior census semantic labels; these results are retained as a
separate follow-up, never substituted into the historical study.

## Execution sensitivity

Each entry is **base / reversed-option-condition** semantic flips relative to
original contiguous size-four batches. Each number has denominator 339.

| Execution plan | Qwen3 8B | Llama 3.1 8B |
|---|---:|---:|
| Identical batches, same-process repeat | 0 / 0 | 0 / 0 |
| Same batch members, reversed row order | 0 / 0 | 0 / 0 |
| New seeded co-batches of four | 1 / 4 | 3 / 5 |
| Single-request execution | 3 / 3 | 7 / 5 |

Original top-two logit margins of changed cases are at most 0.5 for Qwen and
0.375 for Llama, including exact ties. These are uncalibrated candidate logits,
not semantic confidence. All native code-order tie decisions are retained.

## Interface effect across execution plans

NOINFO differences below use 130 derived cited-annotation-absence pairs.
Intervals are pointwise, 10,000-draw paired claim-cluster percentile intervals
on the fixed development census; they do not quantify reference validity.

| Plan | Qwen option-reversal flips / 339 | Qwen NOINFO delta, pp [95%] | Llama option-reversal flips / 339 | Llama NOINFO delta, pp [95%] |
|---|---:|---:|---:|---:|
| Original batches | 97 | -33.8 [-42.3, -25.9] | 73 | -26.9 [-34.9, -19.5] |
| Identical repeat | 97 | -33.8 [-42.3, -25.9] | 73 | -26.9 [-34.9, -19.5] |
| Within-batch reversal | 97 | -33.8 [-42.3, -25.9] | 73 | -26.9 [-34.9, -19.5] |
| Repacked batches | 95 | -33.1 [-41.4, -25.4] | 73 | -27.7 [-35.7, -20.0] |
| Single request | 95 | -34.6 [-43.2, -26.6] | 71 | -26.9 [-34.6, -19.4] |

The class-conditional interface pattern persists in all tested plans, whereas
same-condition execution drift is small. This does not identify an isolated
numerical mechanism, establish bitwise determinism, or prove NOINFO neutrality.
Repacking changes padding and kernel shapes together. Plans run in a fixed,
not counterbalanced order; repeats are within-process, not cross-GPU/version.
The option reversal changes display order and answer-code assignments jointly.

Protocol and schedule were frozen before this new inference, after historical
drift was observed. Population is all eligible census pairs without selecting
by outcomes or margins. It is a same-source follow-up, not an independent test
set. See PROTOCOL.md, manifest.json, schedule.json, results/, summary.json and
the independent verifier. The figure source summary SHA-256 is
`150510bd536cb453372cdc6c2ed3a5a8e8ad4896d5de3d8ddf873f757bd5c857`.
