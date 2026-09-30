# SciFact3 display-order × answer-code follow-up

This exploratory follow-up fills the two missing cells of the 2×2 adapter
prompt design on the **same 180 frozen SciFact3 cited claim--abstract
pairs** (60 per operational label; 180 unique claims and cited documents).
Base and ordinary joint reversal were already observed in the source run;
they are reused by SHA-256. The two new conditions and analysis plan were
frozen before their inference; no source text is copied into this directory.
All four message/code assignments were audited, and the base/both tokenizer
prompt token hashes and lengths match each historical row for both models.
Old and new runs use the same pinned checkpoint/chat template/adapter code,
BF16/SDPA candidate logits and batch size four. New outputs retain raw
candidate logits, conditional semantic probabilities, predictions, errors,
prompt hashes and batch timings. All 720 new decisions are valid.

## Four cells on the same 180 pairs

Each value is reference-correct count/180 under the **native recorded**
decoder. Rows change candidate display order; columns change semantic
label-to-answer-code mapping.

| Model / display | Original codes | Reversed codes |
|---|---:|---:|
| Llama / original | 78 | 71 |
| Llama / reversed | 61 | 69 native; 68 common-tie |
| Qwen / original | 104 | 114 |
| Qwen / reversed | 114 | 101 |

For Qwen, relative to base, display-only changes 30/180 semantic labels
(16.7%, paired claim-cluster 95% interval [11.7, 22.2]), code-only changes
18/180 (10.0%, [5.6, 14.4]), and both changes 60/180 (33.3%, [26.7,
40.6]). The two single factors *each* gain 10 correct decisions (+5.6
percentage points), while the joint ordinary reversal loses three correct
decisions (-1.7 points). The accuracy interaction
`(both-code_only)-(display_only-base)` is **-12.8 points** (95% interval
[-19.4, -6.1]) on this selected sample, revealing a non-additive
model--adapter--prompt response rather than a single dominant factor.
Correction/regression counts versus base are display-only 18/8,
code-only 12/2, and both 21/24.

The class migration is particularly sharp. Qwen's base predicts NOINFO
on 107 cases. Keeping those **same 107 IDs** fixed, display-only retains
79 as NOINFO and sends 12 to SUPPORT/16 to CONTRADICT; code-only retains
90 and sends 9 to SUPPORT/8 to CONTRADICT; both retains only 47 and sends
42 to SUPPORT/18 to CONTRADICT. Every one of the 60 base→both prediction
flips therefore leaves a base-NOINFO decision. Among the 60 **gold-NOINFO**
pairs, Qwen's correct predictions are base/display/code/both
54/48/52/30. Among the 60 **gold-CONTRADICT** pairs, they are
5/18/12/18; some migration fixes errors while other changes create
positive predictions on NOINFO-reference pairs. Aggregate accuracy conceals this
tradeoff. In the separate ContractNLI legal follow-up, Qwen code-only
flips only 10/144 and display-only 36/144; this is a descriptive contrast,
not a controlled test of cross-domain causality, because task wordings,
labels and source selection differ.

Llama behaves differently: native base/display/code/both accuracy is
78/61/71/69, with base-relative 51/85/42 flips. Under one common
semantic tie-break its both cell becomes 68 correct and 46 flips.
Llama's common-tie accuracy interaction is +7.8 points with interval
[-1.1, +16.7], which does not resolve a sign. A fixed direct-generation
control on these exact cases separately reproduces the old base
code-logit decisions for both models; it does **not** constrain how other
prompts or deliberation would behave.

## Tie handling and uncertainty

The native historical `both` question reverses `criteria` and thereby
the first-maximum tie priority. Top-logit ties in base/display/code/both
are Llama 6/1/11/6 and Qwen 1/6/1/0. A common, predeclared-for-this-
follow-up semantic order (SUPPORT, CONTRADICT, NOINFO) changes six
historical Llama-both labels and **no Qwen labels**. We preserve native
historical outputs and restrict factor interpretation to the common-tie
sensitivity; the Qwen non-additivity is unchanged by this decoder issue.
Stored full-precision semantic probabilities and candidate logits yield
the same exact top-tie sets. The historical exact-repeat suite has zero
prediction flips for both models.

All quoted intervals are exploratory, post-hoc-to-existing-outcomes,
pointwise and unadjusted. They use 10,000 paired percentile bootstrap draws with
seed 20260930, resampling the 180 unique source-claim groups and retaining
all four outcomes for each sampled ID. They describe the balanced,
selected, cited-abstract pairs, not natural SciFact prevalence. NOINFO is
derived from absence of annotated **abstract** evidence for an explicitly
cited document; it is not proof that the full paper or external literature
has no evidence. This remains a diagnostic of two fixed model-plus-adapter
systems, not a neural-mechanism or end-to-end scientific fact-checking claim.

Reproduce and audit using `PROTOCOL.md`, `freeze.py`, `frozen.json`,
`manifest.json`, `run.py`, `analyze.py`, `verify_raw.py`, `summary.json` and
`results/{llama31_8b_instruct,qwen3_8b}/`. The source-containing
`research/scifact3_v1/frozen.json` is referenced only by SHA-256 and ID,
not duplicated here. Original base/reversal output SHA-256s are in
`manifest.json` and per-cell paths/hashes are in `summary.json`.

The independent, standard-library `verify_raw.py` replays all four native
and common-tie cells directly from SHA-checked raw gzip files, comparing
correct counts, invalids, exact top-logit ties, and **every base-to-cell
transition** with the saved analysis. It independently reconstructs all
720 frozen message and candidate-assignment hashes from the original source
cases. The model-facing payload whitelist is `state`, `question_type`,
`instructions`, and `candidates`; state contains the intended claim,
paper title and cited abstract, but no reference label, source split,
claim group or source identifier. The script prints only field names and
counts, never source text. The paper-ready main and supplementary sections
are `paper/sections/scifact3_codebook.tex` and
`paper/sections/scifact3_codebook_appendix.tex`, with a vector figure at
`paper/figures/fig_scifact3_codebook.pdf`.
