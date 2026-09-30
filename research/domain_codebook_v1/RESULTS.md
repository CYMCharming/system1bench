# ContractNLI candidate-display × answer-code diagnostic

## Status and provenance

This is a diagnostic of the pinned Llama-3.1-8B-Instruct and Qwen3-8B
single-next-token code-likelihood adapters on the **same 144 selected legal
cases / 91 source contracts** in `domain_expansion_v1`. The original base and
ordinary reversal outputs are reused byte-for-byte and SHA-verified; only
the display-only and code-only cells received new inference. All four
rendered message/code mappings were frozen before the initial inference.

There was a transparent **post-pilot correction**. The original domain run
used batch size 4; the first new-mode pilot mistakenly used batch size 8.
The pilot outputs and initial analysis remain in `results/` and
`summary.json`. `AMENDMENT.md` and `batch4_manifest.json` were frozen before
running the corrected batch-4 new cells in `results_batch4/`. The primary
comparison here and in the paper uses those corrected cells. This is not
represented as a wholly prospective four-cell confirmatory experiment:
base/both outcomes were already observed, and the batch/tie corrections
were discovered after inspecting the pilot. The source text is never copied
into this directory, only source IDs and hashes.

The corrected runner checked all 576 four-cell prompt-token hashes per
model against frozen renderings and the historical base/both audit. It also
checked model-file, chat-template and adapter-source SHA-256 equality,
original case order, batch IDs, and batch size. All 576 **new** decisions
are valid; all 1,152 four-cell records have stored probabilities and prompt
hashes, while new records additionally store their selected raw candidate
logits. The historical exact-repeat runs match base in all 144 predictions
for each model. Corrected GPU inference took 68.7 s (Llama) and 74.7 s
(Qwen) for the two new modes, excluding model load/tokenization. These are
not benchmark throughput estimates.

## Four-cell results

Each count below is correct out of 144. Rows change the serialized option
display order; columns change the semantic label-to-code mapping.

| Model / display | Original codes | Reversed codes |
|---|---:|---:|
| Llama / original | 44 | 50 |
| Llama / reversed | 48 | 59 native; 57 common-tie |
| Qwen / original | 65 | 63 |
| Qwen / reversed | 78 | 83 native; 84 common-tie |

Using the original native decoder, base→both flips are 66/144 for Llama and
64/144 for Qwen. For the **single-factor** cells at historical batch size 4:

| Model | Display-only flips vs base | Code-only flips vs base | Code-only corrections / regressions |
|---|---:|---:|---:|
| Llama | 6/144 = 4.2% [1.4, 7.6] | 125/144 = 86.8% [81.1, 92.1] | 44 / 38 |
| Qwen | 36/144 = 25.0% [18.1, 32.2] | 10/144 = 6.9% [2.8, 11.6] | 3 / 5 |

Brackets are 95% percentile intervals from 10,000 paired bootstrap samples
of **91 source-document clusters** (seed 20260930); each draw retains all
matched cases and four outcomes within the selected contracts. The accuracy
interaction under common tie-breaking is +2.1 percentage points for Llama
[-7.0, +10.8] and +5.6 points for Qwen [-2.1, +13.0]. Both intervals cross
zero. Common-tie base→both accuracy effects are +9.0 points [2.1, 16.1]
and +13.2 points [4.4, 21.4], respectively. These are descriptive paired
effects on this selected, balanced, length-capped challenge—not estimates
for legal workloads or natural ContractNLI prevalence.

The chosen *code* distribution helps interpret the stark flip asymmetry.
Llama chooses token A in 138/144 base and 131/144 code-only cases, even
when the code-label mapping is reversed; Qwen instead moves from token C
in 122/144 base cases to token A in 126/144 code-only cases while mostly
preserving its semantic choice. This supports an adapter-specific mapping
susceptibility account, not an architecture-level explanation. Code-token
selection and semantic accuracy are different observables.

## Decoder tie and batch sensitivities

The historical both/reversal question reverses `criteria` order, and the
native decoder selects the first exact maximum. BF16 top-logit ties are
Llama 4/0/9/12 and Qwen 0/4/0/5 in base/display-only/code-only/both. A
**post-hoc common semantic tie-break** over Entailment, Contradiction,
NotMentioned changes only the old both cell: all 12 Llama ties and all 5
Qwen ties change chosen label, moving its accuracy 59→57 and 83→84 and
base→both flips 66→54 and 64→69. This was independently reproduced from
stored full-precision semantic probabilities and candidate logits. The
native historical predictions remain primary records; the standardized
grid isolates prompt/code factors from this decoder convention.

Batch-eight versus batch-four pilots change no Llama new-mode predictions,
but change **three Qwen display-only predictions** and its accuracy 79→78;
code-only has no Qwen prediction changes. The maximum semantic-probability
changes are nonzero even when argmax does not change, so silently mixing
batch shapes would not be a strict paired control.

## Reproducible artifacts

- Frozen prompts/conditions: `frozen.json`, `manifest.json`, `PROTOCOL.md`.
- Corrective provenance: `AMENDMENT.md`, `batch4_manifest.json`,
  `freeze_batch4.py`, `run_batch4.py`.
- Corrected raw data: `results_batch4/{llama31_8b_instruct,qwen3_8b}/`
  with `metadata.json`, `display_only.json.gz`, `code_only.json.gz`.
- Original comparison data:
  `research/domain_expansion_v1/results/local/{llama31_8b_instruct,qwen3_8b}/`
  with `contractnli_base.json.gz`,
  `contractnli_reversed_option_order.json.gz`, and
  `contractnli_exact_repeat.json.gz`; exact hashes in `manifest.json` and
  `summary_batch4.json`.
- Primary audited summary and recomputation: `summary_batch4.json`,
  `analyze_batch4.py`.
- Preserved batch-eight pilot: `results/`, `summary.json`, `run.py`,
  `analyze.py`.
- Paper prose/figure: `paper/sections/domain_codebook.tex`,
  `paper/figures/gen_domain_codebook.py`,
  `paper/figures/fig_domain_codebook.{pdf,svg,png}`.
