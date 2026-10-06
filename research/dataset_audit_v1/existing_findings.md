# Existing dataset audit — 2026-10-06

Assessment: **Share with caveats**. This is a full-row structural/source-binding audit of the frozen main and transfer panels, with independent programmatic checks. It is **not** independent human adjudication of natural-language reference labels or evidence of contamination-free model training. Historical data, scores and protocols were not modified.

Reproduction: run `python research/dataset_audit_v1/audit_existing.py /mnt/sata2/cym/system1bench` on the source host. The script prints JSON without source writes, inference, importing existing preparation/scoring helpers or executing benchmark code. `existing_results.json` contains the actual output. All 7 domain source byte hashes and all 12 transfer source byte hashes match pinned receipts; all inspected frozen request hashes and label alphabets match. ID reuse across separate repeat/reversal suites is intentional; no suite has duplicate IDs.

| Dataset | Independent checks and exact observations | Interpretation / supported remedy |
|---|---|---|
| Synthetic policy | 288 original states, no duplicate requests. 2,304 variants / 6,912 gold fields all match the independent executable oracle. All 288 counterfactuals change exactly one fact and action. Refund/routing actions each 24 per class; access 33/33/30. | Explicit-policy synthetic execution, not real business outcome validation. Do not call all variants independent examples. |
| ContractNLI | 144 balanced pairs match official test text, hypotheses and choices; 91 text-distinct documents (53 with two pairs, 38 with one). Source test has 123 documents; 24 excluded by the 16,000-character bound. Selected exact document text overlaps with the pinned archive train documents: 0. | Length- and label-conditioned subset, not the native test population. Exact overlap=0 does not establish absence of model training contamination. Known StartLux training on the train split still needs its separate model disclosure. |
| SciFact cited pairs | All 339 unique cited pairs recovered, no source/gold mismatch; 300 claims, 283 documents. Labels: support 138, contradict 71, NOINFO 130. One repeated source citation is correctly de-duplicated. | **Material caveat:** all 130 NOINFO labels derive from absence of source evidence annotations, not an independent reader confirming the supplied abstract neither supports nor contradicts. Source-consistency accuracy is appropriate; externally adjudicated truth claims are not. |
| CLadder | 144 questions / 141 causal-model groups; all source answers and exact request fields match, no rationale/latent parameter fields. Gold IDs 70/74 and display positions 76/68; no fixed correct option. | Generator reference, balanced sample, not independent causal proof. Preserve causal-model grouping. |
| CRUXEval choice adaptation | All 128 gold outputs and code/input fields match source. Independently confirm 570 eligible of 800; 230 have no distinct parseable incorrect published distractor. Candidate counts: 2×56, 3×28, 4×23, 5×8, 6×5, 7×5, 8×2, 10×1. Uniform per-question chance = 0.3639136904761905. | **Material caveat:** choice recognition conditioned on a historical CodeLlama failure pool; not free-generation/pass@1, and random chance is not 10% or 25%. Do not mix with native CRUXEval scores. Code was not executed. |
| FinEntity | 128 document-distinct supplied spans; all source span/label bindings match. Independently reconfirm 2,057 eligible spans; reject 70 invalid span/label records, 2 duplicate-span records, 2 conflicting-span records. | Entire source corpus is used as selection pool, not a claimed independent test split; evaluates given-span classification rather than extraction. Dataset-specific redistribution license not established in this pass. |
| When2Call | 128 upstream problem groups, exact available tools and user-question fields match source. Full source gold counts: 1,295 cannot-answer, 1,062 request-info, 1,295 tool-call; no direct-answer positives. | Tool-response selection rather than agent execution. Direct recall cannot be estimated; direct false selection can. Pinned source card states CC BY 4.0. |
| Intern known-distribution pilot | 96 rows, 48 settings, two option orders each; six categories with 16 rows/category. All exact fractions sum to one, match saved references and preserved input fields. Independent finite-event/Bayes/DP calculations for all 24 families reproduce all 96 reference distributions exactly. | Vendor-provided diagnostic, not a large independent calibration benchmark. Parameter-to-natural-language binding was manually inspected for the first case of each family only; do not call all cases manually adjudicated. Dataset-specific redistribution license not established. |

## Newly observed dependence beyond declared repeats

Policy preparation rejects only duplicate **original** state fingerprints (`research/confirmation.py:106`), not reused counterfactual states. There are **11 non-repeat request collisions**: eight in refund and three in routing; access has none. They involve six connected pairs of base groups. Five of those pairs are reciprocal original/counterfactual input pairs; one routing pair shares only the counterfactual. Examples:

- `refund:101:020:original` equals `refund:101:030:counterfactual`, and the inverse pair also matches.
- `routing:202:014:counterfactual` equals `routing:303:002:counterfactual`.

The complete eleven collision groups are recorded in `existing_results.json`. Original action accuracy still uses 288 distinct inputs; this is **not** a demonstrated wrong score. The paired counterfactual diagnostic, however, is not 288 independent unordered intervention pairs. Preserve the historical score and disclose the dependence. A prospective v2 should de-duplicate the union of original and counterfactual states/pairs before inference; any historical sensitivity interval should cluster connected intervention components, not silently edit the frozen sample.

## SciFact uncertainty sensitivity

SciFact repeats documents across claims: 238 documents appear once, 35 twice, 9 three times and 1 four times. Claim multiplicities: 277 once, 14 twice, 4 three times, 3 four times and 2 five times. The existing main interval uses claim clusters (`research/leaderboard_v2/build.py:116`), not both crossed claim/document clusters.

Completed sidecar (`existing_results.json` → `science_uncertainty_sensitivity`): **23 models × 339 = 7,797 frozen original predictions**, each file SHA checked against its raw receipt, every request hash/gold/group checked against frozen data. All 23 correct/n/score values independently reproduce `research/model_expansion_v3/scores.json`. This uses the historical Qwen3-8B raw run, not its later adapter replication.

5,000 bootstrap resamples, seed 20261006, compare claim-only, document-only and crossed pigeonhole sampling. The crossed method independently resamples 300 claim IDs and 283 document IDs and weights each **observed** pair by the product of their sampled multiplicities; it does not invent missing Cartesian-product observations. The document-only intervals are close to claim-only and are **not uniformly wider**. Crossed interval widths are 1.625–1.770 times the claim-only widths in this run. This is a dependence **stress test**, can be conservative, and does not establish that the original method is wrong or that any one CI is the uniquely correct population interval.

| Model | Source-consistency score | Claim-only 95% | Document-only 95% | Crossed stress-test 95% |
|---|---:|---:|---:|---:|
| Jev 1.13.0 | 85.84% | 81.90–89.44% | 82.17–89.53% | 78.87–91.69% |
| Intern-Decision-4B | 75.81% | 71.12–80.24% | 70.62–80.65% | 67.46–83.58% |
| Kev-27B v2 | 84.07% | 80.00–88.10% | 79.94–88.01% | 76.85–90.60% |

Historical scores and intervals remain untouched. These are pointwise descriptive sensitivity intervals, not paired model-difference significance tests. They do not address NOINFO semantic reference uncertainty.

Reproduction with the optional existing NumPy runtime: `python research/dataset_audit_v1/audit_existing.py /mnt/sata2/cym/system1bench --science-sensitivity`. The basic structural audit requires only the standard library; no additional package was installed for this work.

## Limits and licenses

ContractNLI pinned TERMS/LICENSE identify CC BY 4.0; pinned CLadder and CRUXEval repositories carry MIT license text; pinned When2Call card states CC BY 4.0. This records source declarations, not a legal conclusion about every constituent copyrighted text. FinEntity and Intern-pilot standalone dataset permissions remain unverified; do not infer data licenses from neighboring code licenses. Keep public audit records to hashes, aggregate counts and IDs pending verification.

No full model-training corpus was available. No human double annotation or disagreement adjudication was performed. CLadder graph arithmetic and CRUXEval runtime execution were not independently verified. Only SciFact original model prediction receipts were additionally checked for the sensitivity calculation; this audit does not claim a new full 23-model, all-task prediction receipt review. Natural-language-to-parameter binding for all 96 pilot rows was not exhaustively reread. These gaps should not be converted into a blanket “audit passed” badge.
