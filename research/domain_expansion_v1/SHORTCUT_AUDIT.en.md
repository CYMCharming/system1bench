# ContractNLI hypothesis shortcut and length-selection audit

This is a **model-blind dataset diagnostic**, not a fair model baseline. It reads official `train.json` and `test.json` directly from the original archive, verifies the extracted test bytes and the frozen-file hash, and does not inspect model predictions or alter the freeze. The primary unit is one document–hypothesis annotation; the 144 frozen base cases are 91 contracts with at most two questions each.

## 16,000-character selection changes the document mix

| Official document type | Test docs | Eligible ≤16k | Excluded | Exclusion rate | Selected docs | Selected pairs | Median chars (all) |
|---|---:|---:|---:|---:|---:|---:|---:|
| search-pdf | 76 | 69 | 7 | 9.2% | 64 | 104 | 8,300 |
| sec-html | 23 | 10 | 13 | 56.5% | 8 | 14 | 16,383 |
| sec-text | 24 | 20 | 4 | 16.7% | 19 | 26 | 9,297 |

Of 123 official test contracts, 99 satisfy the length rule and 91 appear in the frozen sample. The filter excludes 13/23 `sec-html` documents (56.5%), versus 7/76 `search-pdf` (9.2%) and 4/24 `sec-text` (16.7%). Consequently, `sec-html` falls from 18.7% of all test documents to 10.1% of eligible documents and 8.8% of selected documents. `document_type` is a source/extraction-format field, not a legal subject-matter taxonomy; this is selection skew, not proof of a causal effect of HTML format on task difficulty.

| Annotation population | Entailment | Contradiction | NotMentioned | Total |
|---|---:|---:|---:|---:|
| All official test pairs | 968 | 220 | 903 | 2091 |
| Eligible test pairs | 748 | 178 | 757 | 1683 |
| Excluded test pairs | 220 | 42 | 146 | 408 |
| Frozen selected pairs | 48 | 48 | 48 | 144 |

The selected 48/48/48 class balance is intentional and not the official test prevalence. Consequently, shortcut percentages on all test annotations, length-eligible annotations and the selected 144 answer different questions.

## Fixed-hypothesis label prior learned only from official train

There are 17 fixed hypothesis IDs, each annotated on all 423 official training contracts. For each ID, take its unique modal train label; never read test labels to train this primary prior. The train and test splits have zero exact overlap by document ID, normalized URL, normalized file name or raw text SHA-256 (near-duplicates were not assessed). All 17 train-mode ties are absent.

| Evaluation population | Train-ID prior correct | Rate |
|---|---:|---:|
| All official test pairs | 1379/2091 | 65.9% |
| Eligible test pairs | 1102/1683 | 65.5% |
| Excluded test pairs | 277/408 | 67.9% |
| Frozen selected pairs | 82/144 | 56.9% |

On the frozen 144, the train-only hypothesis-ID prior reaches **82/144 = 56.9%** (descriptive 95% contract-cluster bootstrap interval [49.3%, 64.3%], 10,000 draws). The global training-set majority label is `Entailment`; predicting it everywhere gives 48/144 = 33.3% on this deliberately balanced sample. This shows that the hypothesis ID carries label information, not that a model uses this shortcut. It is a supervised reference-label prior and must not be ranked as a zero-shot or document-reading model baseline.

For diagnostic context only, using the selected test labels to fit a deterministic majority label for each hypothesis ID gives an in-sample optimum of 100/144 = 69.4% for such an ID-only mapping. A stochastic same-input model could exceed this realized count by chance, not by contract information. Excluding the target item before counting its ID yields a tie-averaged expectation of 92.5/144 = 64.2%; excluding the entire target contract gives exactly the same predictions because each contract has at most one annotation per hypothesis ID. Both leave-out versions have 13 tied cases, 131 unique-majority cases and 86 correct unique-majority decisions. Uniform averaging over tied labels avoids a favorable arbitrary tie-break. These leave-out calculations still learn from *other selected test labels* and are not independent model baselines.

### Per-hypothesis counts

Column triples are `Entailment / Contradiction / NotMentioned`; selected counts sum to 144. The train-majority column defines the prior; selected counts are shown only to reveal potential shift and are never used to define that primary prior.

| Hypothesis ID | Train E/C/N | Train majority | Selected E/C/N | Selected n |
|---|---:|---|---:|---:|
| `nda-1` | 91/112/220 | NotMentioned | 1/8/2 | 11 |
| `nda-10` | 159/2/262 | NotMentioned | 2/0/1 | 3 |
| `nda-11` | 59/1/363 | NotMentioned | 0/0/2 | 2 |
| `nda-12` | 263/0/160 | Entailment | 3/0/2 | 5 |
| `nda-13` | 311/0/112 | Entailment | 5/0/2 | 7 |
| `nda-15` | 327/0/96 | Entailment | 5/0/3 | 8 |
| `nda-16` | 181/1/241 | NotMentioned | 2/0/4 | 6 |
| `nda-17` | 91/76/256 | NotMentioned | 1/8/6 | 15 |
| `nda-18` | 93/0/330 | NotMentioned | 2/0/7 | 9 |
| `nda-19` | 300/11/112 | Entailment | 5/1/4 | 10 |
| `nda-2` | 23/309/91 | Contradiction | 0/18/2 | 20 |
| `nda-20` | 118/194/111 | Contradiction | 2/4/8 | 14 |
| `nda-3` | 270/4/149 | Entailment | 1/0/1 | 2 |
| `nda-4` | 364/7/52 | Entailment | 6/0/0 | 6 |
| `nda-5` | 345/13/65 | Entailment | 6/0/2 | 8 |
| `nda-7` | 259/111/53 | Entailment | 4/9/0 | 13 |
| `nda-8` | 276/0/147 | Entailment | 3/0/2 | 5 |

## Interpretation and next diagnostic

The strongest established risk is construct ambiguity: a system may score above chance partly by exploiting stable hypothesis-ID priors rather than reading contract text. The 16k cap also disproportionately removes `sec-html` documents. Neither observation invalidates the official labels, and this audit does not prove which cue any evaluated model used. The selected test sample is small and class-stratified; the train-only prior has a descriptive cluster interval, not a population guarantee.

A separate **hypothesis-only probe is frozen but not run** in `hypothesis_only_probe/frozen.json`. Its state contains only the official hypothesis text; it has no `contract_text` field, source URL, document ID or filename in the request body. The question explicitly asks for the most likely ContractNLI label *across NDA documents* when the actual contract is withheld, while retaining the same three label names/order. Thus `NotMentioned` is not made logically correct by an empty contract: this is prior elicitation, not a same-instruction deletion ablation. The 144 cases become 17 unique payloads. If run later, compare each ID's output distribution with the official-train prior and report identical-input variability. The result cannot be subtracted from full-text accuracy as an isolated document-reliance effect. This post-hoc exploratory audit is not a confirmatory legal-reasoning experiment; no model inference was run here.

Reproduce with `.venv/bin/python research/domain_expansion_v1/shortcut_audit.py`. Machine-readable counts, confusion matrices, input hashes and exact overlap checks are in `shortcut_audit.json`.
