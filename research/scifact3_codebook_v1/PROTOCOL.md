# SciFact3 orthogonal display/code diagnostic v1

This prospective missing-cell follow-up diagnoses the pinned Llama 3.1 8B
Instruct and Qwen3 8B **single-next-token code-likelihood adapters**, not
model families, best prompts, or end-to-end scientific fact checking. The
base and ordinary reversal outcomes are already observed; the two new cells
and analysis rules below are frozen before their inference.

## Fixed 2×2 source and intervention

Use exactly all 180 already frozen `research/scifact3_v1` base claim--cited-
abstract pairs, each from a unique claim and document, balanced 60 each for
SUPPORT, CONTRADICT and NOINFO. The source freeze remains immutable and
contains upstream texts, which are **not copied** into this companion
ID/hash-only freeze. Gold labels, state, task instructions, candidate
meanings and the set of choices remain fixed.

The two factors are semantic candidate display order (original/reversed)
and semantic label-to-code assignment (original/reversed):

| Cell | Display | Code mapping | Inference |
|---|---|---|---|
| base | original | original | reuse historical `scifact3_base` |
| display_only | reversed | original | new |
| code_only | original | reversed | new |
| both | reversed | reversed | reuse historical `scifact3_reversed_option_order` |

`both` must be byte-identical to the historical reversed adapter messages;
`base` must be byte-identical to historical base. Before any new model
inference, compare all four frozen message/code hashes, and compare base and
both **tokenizer prompt token hashes and lengths** against historical output
audits. Preserve source case order and historical batch size four to match
left padding shape. Require the same model-file, chat-template and adapter
code hashes. Use BF16/SDPA, candidate A/B/C next-token logits, float64
conditional softmax, no truncation, no stochastic sampling. Store new raw
candidate logits, semantic probabilities, native predictions, errors, all
hashes, lengths and per-batch time; do not modify the old outputs.

## Paired estimands and decoder sensitivity

For each model and all four cells, report native recorded accuracy, invalid
count, class-specific recall/confusion, prediction flips versus base,
wrong→right corrections, right→wrong regressions, and paired conditional
factor effects. Report the descriptive accuracy interaction
`(both-code_only)-(display_only-base)`; do not treat it as an intrinsic
architectural causal parameter. To directly address Qwen's earlier
NOINFO/CONTRADICT migration, separately report predicted-class transitions
under each single factor, especially among the 60 gold-NOINFO and 60
gold-CONTRADICT cases. A tie-independent secondary observable is the mean
probability assigned to each gold class under the three-code conditional
softmax; it is not calibrated task confidence.

Historical `both` reverses `question.criteria` order, so its native decoder
also reverses first-maximum tie priority. Preserve those native records as
primary historical outputs, but provide a **predeclared here, post-hoc to
the existing base/both outcomes** sensitivity that re-decodes every cell
from saved semantic probabilities with one fixed semantic priority:
SUPPORT, CONTRADICT, NOINFO. Report exact top-logit tie counts and all
native-to-common prediction changes. Interpret the prompt/code 2×2 only
under that common decoder convention, while retaining native results for
continuity. No new model inference is needed for re-decoding.

Use 10,000 paired percentile bootstrap draws (seed 20260930), resampling
the 180 unique source-claim clusters and retaining all four matched cells;
report 95% intervals for accuracy effects and flip rates. Each selected
claim/document is unique, so claim-cluster and pair bootstrap coincide.
Invalid responses remain wrong, never silently excluded. The separate
historical exact-repeat suite checks run/batch stability but is not a fifth
factorial cell. No prompt tuning, case selection from predictions, title
removal, or hosted evaluation occurs here. Selected balanced cited-abstract
pairs do not represent SciFact's natural class prevalence; NOINFO means
absence of annotated abstract evidence for a **cited** document, not proof
of no evidence in the full paper or literature.
