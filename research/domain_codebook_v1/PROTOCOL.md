# ContractNLI orthogonal display/code diagnostic v1

This experiment diagnoses **the fixed System1Bench Llama-3.1-8B-Instruct and
Qwen3-8B single-token candidate-code adapters** on the already frozen 144
ContractNLI base cases. It does not estimate an architecture-level mechanism,
the best prompted LLM behavior, or legal practice validity.

## Frozen source and 2×2 design

`research/domain_expansion_v1/frozen.json` is immutable and hashed. Its
`contractnli_base` and `contractnli_reversed_option_order` suites contain the
same 144 state IDs, source-document groups, gold labels and semantic options.
There are 91 document groups; three gold classes are balanced at 48 each.
No cases are excluded or selected using predictions.

The intervention factors are **semantic candidate display order** (original
or reversed) and **semantic label-to-answer-code assignment** (original or
reversed). With original labels `[Entailment, Contradiction, NotMentioned]`:

| Cell | Display order | Label-to-code map | Inference |
|---|---|---|---|
| base | original | original | Reuse existing `contractnli_base` result |
| display-only | reversed | original | New |
| code-only | original | reversed | New |
| both | reversed | reversed | Reuse existing `contractnli_reversed_option_order` result |

The `both` cell is **exactly** the historical ordinary candidate reversal,
not an extra inference. `freeze.py` checks full chat-message equality of base
and both against the source adapter conversion for all 144 cases. Before new
inference, `run.py` checks actual tokenizer prompt token hashes for those
two cells against the existing result audits. New prompts reuse the same
system message, JSON payload shape, native chat template, one-token codes,
BF16/SDPA model loading, candidate logit selection, float64 conditional
softmax, no truncation, and batch size eight. Prompt and code-index hashes
are frozen before inference. Existing checkpoint hashes must match.

The new cells do not change the state, instructions, reference label, set
of candidate meanings, or probability normalization. They change only the
candidate-list order and/or code assignment in the serialized adapter prompt.
Their `request_sha256` refers to the original semantic request; separately
recorded prompt-token hashes distinguish the codebook interventions. All
raw candidate logits, semantic probabilities, decoded predictions, input
hashes, errors and batch timings are retained. Existing base/both result
files are referenced by SHA-256, not overwritten.

## Estimands and uncertainty

Report all four cell accuracies, invalids, prediction flips and correctness
corrections/regressions against base. Pair the same 144 IDs. Also report
pairwise display-only→both and code-only→both flips, so the two conditional
factor changes are observable. The interaction in accuracy is
`(both − code-only) − (display-only − base)` (percentage points); this is a
descriptive finite-sample factorial contrast, not an architectural causal
parameter. 10,000 paired bootstrap draws with seed 20260930 resample the
91 source-document groups and keep all their matched cases/conditions;
report percentile 95% intervals. A repeat of the original prompt is a
diagnostic for run-to-run/batch variation and is not an extra factorial cell.

No prompt selection, new data sampling, post-hoc parsing, answer rescue,
model fine-tuning or hosted evaluation occurs. If an inference error happens,
retain it as invalid/incorrect and report it. The conclusion must remain
restricted to these two pinned local model-plus-adapter systems and the
ContractNLI challenge sample.
