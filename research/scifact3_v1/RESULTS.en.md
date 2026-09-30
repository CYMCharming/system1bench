# A three-class scientific-evidence control exposes hidden answer migration

The source-authentic `NOINFO` class makes this a more diagnostic SciFact test than the earlier positive-evidence-only slice. On the fixed, class-balanced 180-pair sample, Qwen3 8B changes **60/180 semantic predictions** when option order is reversed, versus **0/180** on a byte-identical repeat. Yet its total reference-correct count changes only **104→101/180** (−1.7 percentage points; paired 95% interval [−7.8,+4.4]). The near-flat total hides a large category trade-off: `NOINFO` falls **54→30/60** while `CONTRADICT` rises **5→18/60**. This is an observed model–adapter interface response, not evidence that scientific semantics changed.

## What was frozen

The [official SciFact data documentation](https://github.com/allenai/scifact/blob/master/doc/data.md) identifies `cited_doc_ids` as the papers named in the claim's source citation sentence. Its example explicitly distinguishes cited abstracts with evidence annotations from a cited abstract where annotators found no evidence. In the official labeled dev split, the 300 claims yield 340 citation-list occurrences and **339 unique claim–cited-abstract pairs** after removing one repeated citation ID: 138 `SUPPORT`, 71 `CONTRADICT`, and 130 cited-but-no-evidence `NOINFO` candidates. This is not an open-world negative sample from the 5,183-document corpus. Our `NOINFO` is a derived reference label for an explicitly cited paper with no evidence entry; it does not mean the claim is false or that the full paper/literature has no evidence.

A model-blind SHA-256 ranking selected 60 per label, with **180 distinct claim IDs and 180 distinct document IDs**. Each pair received `base`, byte-identical `exact_repeat`, `reversed_option_order`, and `title_removed` requests (720/system). Title removal deletes only `state.paper_title`; the claim, full abstract, instructions and criteria are unchanged. All 720 requests were audited complete for each of four local tokenizers/adapters; hosted Jev received complete HTTP payloads, but its server-side tokenizer is not observable. All five systems returned valid choices on all 720 requests. The [protocol](PROTOCOL.md), [attribution](DATA_LICENSES.md), [source profile](profile.json), [freeze manifest](manifest.json), [independent source validator](validation.json), [input audit](input_audit.json), [hashed raw-derived summary](summary.json), and [independent count recheck](analysis_validation.json) preserve the evidence chain.

The previous SciFact v1 slice contained **only 120 positively annotated SUPPORT/CONTRADICT pairs**, with a two-choice question and no `NOINFO` option. The new three-choice sample shares only 28/60 SUPPORT and 55/60 CONTRADICT selected pairs with it. Consequently, comparing their accuracy percentages as if the task and test set were unchanged would conflate label-space, question, and sampling changes. Neither slice tests retrieval or full-paper verification.

## Five-system paired outcomes

`Robust` means reference-correct on the *same pair* under both base and option reversal. Flips compare semantic labels only when both answers are valid (all pairs were valid here). Pointwise intervals for base/robust accuracy use 10,000 paired, label-stratified bootstrap resamples of the 180 unique claim/document clusters; they describe uncertainty under resampling this deliberately balanced diagnostic, not natural SciFact prevalence.

| Model–adapter system | Base correct /180 (95% interval) | Robust /180 (95% interval) | Reverse flips /180 | Exact-repeat flips /180 | Title-removal flips /180 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Laya English | 81 (45.0% [40.0,50.0]) | 71 (39.4% [35.0,43.9]) | 16 | 0 | 60 |
| Laya Multilingual | 73 (40.6% [35.0,46.7]) | 59 (32.8% [27.8,37.8]) | 38 | 0 | 68 |
| Llama 3.1 8B | 78 (43.3% [37.8,48.9]) | 61 (33.9% [29.4,38.3]) | 42 | 0 | 18 |
| Qwen3 8B | 104 (57.8% [52.8,62.8]) | 80 (44.4% [38.3,50.6]) | 60 | 0 | 16 |
| Jev 1.13 | 148 (82.2% [76.7,87.8]) | 148 (82.2% [76.7,87.8]) | 0 | 2 | 1 |

These are same-case, selected-label diagnostics of a model **plus its native typed-decision adapter**. They are not a ranking of model-only scientific fact-checking competence. In particular, the two code-likelihood LLM adapters reassign answer codes when criteria are reversed; the intervention is not a pure semantic-order effect. Jev's observed 0/180 reversal flips coexists with 2/180 exact-repeat flips, so “invariant in this sample” is more accurate than “deterministic” or “universally robust.”

## Why the aggregate conceals the effect

Qwen's reversal has different signs across the three reference classes, each with the **same 60-pair denominator**:

| Reference class | Base correct /60 | Reversed correct /60 | Paired change (95% interval, percentage points) |
| --- | ---: | ---: | ---: |
| SUPPORT | 45 | 53 | +13.3 [+5.0,+21.7] |
| CONTRADICT | 5 | 18 | +21.7 [+11.7,+31.7] |
| NOINFO | 54 | 30 | −40.0 [−53.3,−28.3] |
| **All three, balanced** | **104/180** | **101/180** | **−1.7 [−7.8,+4.4]** |

The full reference-by-prediction confusion matrices show this is a changed answer distribution, not just an arithmetic curiosity. Each row is an official/derived reference class with 60 items; columns are semantic predicted labels:

| Gold class | Base: SUPPORT | Base: CONTRADICT | Base: NOINFO | Reversed: SUPPORT | Reversed: CONTRADICT | Reversed: NOINFO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SUPPORT | 45 | 1 | 14 | 53 | 1 | 6 |
| CONTRADICT | 16 | 5 | 39 | 31 | 18 | 11 |
| NOINFO | 6 | 0 | 54 | 25 | 5 | 30 |

Qwen's *predicted* NOINFO marginal contracts from **107 to 47**. Every one of its 60 semantic flips starts from a base NOINFO prediction: 42 become SUPPORT and 18 become CONTRADICT; no base SUPPORT or CONTRADICT answer changes. [The figure](../../paper/figures/fig_scifact3.pdf) visualizes the paired class correctness and complete 3×3 semantic transition matrix. Because option reversal changes both criterion order and constrained answer-code mapping for this adapter, a code/marginal response is plausible; this experiment alone cannot assign the change to either factor.

## Title removal is a separate, model-specific control

Removing only the paper title causes **60/180** Laya English labels to change, with a net **81→100/180** reference-correct increase (+10.6 points, paired interval [+3.9,+17.2]). On NOINFO pairs alone, correct answers rise **20→39/60** (+31.7 points [18.3,45.0]); the paired transitions include 21 corrections and 2 regressions. Its base predicted-label marginal is SUPPORT/CONTRADICT/NOINFO = **143/10/27**, compared with **107/10/63** without titles. The same edit does not consistently improve systems: Laya Multilingual changes 68 labels but loses three net correct; Llama changes 18, Qwen 16, and Jev one. Thus the title effect is an informative *state sensitivity*, not a demonstrated title-lexical shortcut or a causal estimate of evidence reliance. Removing the field changes input serialization/context; moreover, the unchanged frozen instruction still mentions the title even when no title field is present. This instruction/state mismatch makes the probe an unnatural visibility stressor, not a clean ablation of a single semantic cue.

For auditability, these are the complete predicted-label marginals in SUPPORT/CONTRADICT/NOINFO order. Each triple sums to 180; invalid counts are zero for every row.

| System | Base | Exact repeat | Reversed options | Title removed |
| --- | ---: | ---: | ---: | ---: |
| Laya English | 143 / 10 / 27 | 143 / 10 / 27 | 149 / 9 / 22 | 107 / 10 / 63 |
| Laya Multilingual | 128 / 35 / 17 | 128 / 35 / 17 | 145 / 20 / 15 | 101 / 57 / 22 |
| Llama 3.1 8B | 123 / 2 / 55 | 123 / 2 / 55 | 163 / 2 / 15 | 119 / 2 / 59 |
| Qwen3 8B | 67 / 6 / 107 | 67 / 6 / 107 | 109 / 24 / 47 | 71 / 8 / 101 |
| Jev 1.13 | 60 / 66 / 54 | 61 / 65 / 54 | 60 / 66 / 54 | 60 / 65 / 55 |

## Interpretation and boundaries

This experiment adds a source-defined “cited but no annotated abstract evidence” state to the earlier positive-only setting and reveals how a stable aggregate can conceal large, class-opposed movements. It does **not** establish performance on all scientific claims, uncited corpus negatives, evidence retrieval, full texts, or deployment. The 60/60/60 diagnostic deliberately overweights rare CONTRADICT cases relative to the source's 138/71/130 candidate-pair distribution; only 64 dev claims have any CONTRADICT citation. The upstream annotations were not re-adjudicated. The title edit and option reversal are paired interface/state interventions with unchanged frozen reference labels, not automatic causal proofs of reasoning or shortcuts. Jev's complete HTTP payload does not verify complete server-side context use.

Analysis source: `analyze.py` reads every gzip output, verifies per-suite and frozen hashes, and computes 10,000 paired cluster-bootstrap draws with a fixed seed. `recheck_summary.py` independently recomputes all reported counts and confusion cells with the standard library. The frozen JSON SHA-256 is `923647f1400c779159e3d062f01c920174427db3555fb0e9fecb7305bef6f169`; the complete raw-file hashes are in `summary.json`. The print-ready figure is regenerated by `paper/figures/gen_scifact3.py` from `summary.json`, `case_level.json` and `manifest.json`; its plotted values are saved in `figure_data.json`.
