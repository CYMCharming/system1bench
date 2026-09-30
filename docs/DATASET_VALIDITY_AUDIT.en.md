# System1Bench dataset construct-validity review

**Date:** 2026-09-28  
**Verdict:** `WARN`  
**Reviewer:** GPT-5.6-Sol ultra, a fresh agent from the same model family  
**Review status:** `provisional`; this is not independent cross-family certification  
**Publication status:** `local_only`; findings and recommendations have not been uploaded to GitHub

English edition of the [Chinese review](DATASET_VALIDITY_AUDIT.zh-CN.md). The [machine-readable verdict](DATASET_VALIDITY_AUDIT.json) records the review scope, input hashes, findings, and recommendations.

## Overall assessment

The 15 sources are **reasonable for separate, narrowly defined static typed-decision diagnostics**: closed-set intent routing, passage judgments, ordinal ratings, explicit OOS classification, safety-policy agreement, synthetic workflows, and long-context fact retrieval. All frozen reference labels belong to their declared candidate spaces. Independent source-to-frozen reconstruction found no mapping errors.

They do **not** jointly establish a single general decision-accuracy score, decision intelligence, or real business success rate. References mix dataset labels, human policy annotations, programmatic targets, synthetic teachers, and AI-authored/reviewed answers. Some targets are not uniquely determined by the visible state. TurtleBench and Aegis each contain a group of identical visible inputs with conflicting labels. Training contamination has not been ruled out.

Interpret results by evidence type:

1. **Core static tasks:** Banking77, BoolQ, XNLI, MASSIVE, CLINC, and JevBench original/easy support accuracy against references for their specific tasks.
2. **Auxiliary semantic/regression controls:** AG News, Emotion, SST5, and ReflexBench. SST5 needs MAE/within-one alongside exact agreement; ReflexBench uses public development fixtures.
3. **Policy or synthetic agreement:** prompt-injections, typed-decisions, non-needle Jev–Laya tasks, JevBench hard, and Aegis should be described as reference/policy/teacher agreement.
4. **Narrow programmatic control:** Jev–Laya needle tests explicit fact retrieval, with only 25 distinct needle content units.
5. **Unsuitable as noise-free correctness evidence before revision:** typed-decisions, prompt-injections, and TurtleBench. Aegis also needs its conflicting group excluded or reported separately in a future protocol. These sources do not establish real workflow, safety, or open-world reasoning correctness.

## Scope and method

This review concerns dataset validity. It reruns no model, changes no frozen input, prediction, metric, or historical score, and does not repeat the earlier full integrity audit of 105,800 prediction rows.

**Full mechanical checks:** Candidate coverage, independent reconstruction of states/questions/gold from pinned source files, comparison to frozen requests, exact-state duplicates, conflicting labels, and dependency groups. Candidate-coverage failures: **0**. Source-to-frozen reconstruction mismatches: **0**.

**Fixed semantic sample:** Sort by `SHA256(seed|source-or-stratum|case-id)` using seed `system1bench-dataset-validity-2026-09-28-v1`. XNLI/MASSIVE use paired source indices; selected collections use task/label strata. There are **286 review units**, including **24 bilingual pair units**. All IDs and selection rules are retained in the local trace.

| Source/stratum | Review units |
|---|---:|
| AG News, Emotion, Banking77, BoolQ, SST5 | 12 each |
| XNLI paired English/Chinese | 12 pairs |
| MASSIVE paired English/Chinese | 12 pairs |
| prompt-injections | 20 |
| typed-decisions | 20 |
| JevBench | 24 |
| ReflexBench | 20 |
| Jev–Laya | 40 |
| CLINC | 24 |
| TurtleBench | 24 |
| Aegis2 | 30 |

Sample findings illustrate specific problems; their observed frequency is **not extrapolated to the full dataset**. Full-population counts below come only from mechanical traversals of all used rows.

## Priority findings

### P0: Two sources contain identical visible inputs with conflicting references

**TurtleBench:** IDs `484` and `832` have identical visible stories and guesses, but references `Incorrect` and `Unknown`. This is an exact source-label contradiction, not a subjective interpretation of ambiguous prose. The full collection has 18 exact duplicate groups/18 excess rows, with one conflicting group. Three-class accuracy is not accuracy against noise-free truth. A future protocol should adjudicate or exclude that group and retain story clustering across 32 stories.

**Aegis2:** IDs `8e226f8cfe5a4edf879babebebc6d91d` and `92abced2c4764af1a2b5af235fa00bd4` contain exactly the same raw prompt about damaging another person's sink. Human prompt labels are safe and unsafe, respectively. The collection has 13 excess duplicates and one conflicting group. First-occurrence deduplication happens to retain safe; it does not adjudicate truth. Future main results should exclude the conflict or report label uncertainty separately.

### P0: Some typed-decisions targets are underdetermined, with teacher/rubric inconsistencies

The source card describes references averaged over three samples from an approximately 4B teacher. They represent teacher agreement, not human business truth. Across all 2,000 decisions, **936 have reference `confidence < 0.5`**. This is the source's confidence field, not a measured human error probability.

- `invoice_processing_000027` has an invoice ID already present in visible `prior_invoice_ids`; its latent factor is also `duplicate_submission`. Yet the reference says `duplicate=false` and `disposition=approve`, contrary to the source rubric's duplicate→reject rule.
- Of 17 states with factor `duplicate_submission`, six have `duplicate=false`: suffixes `000021`, `000027`, `000042`, `000062`, `000064`, and `000092`. Twelve dispositions are not the rubric-prescribed `reject`.
- Agent-trace states show summary counts without the completion fact, so outcome is generally not uniquely recoverable from the visible state. Comparing latent `completion/violated_constraint` factors with the source rubric gives 53 outcome-argmax mismatches among 100 states. For example, `agent_trace_observability_000052` has latent partial completion but reference success.

Latent factors should not be leaked to the evaluated model. The issue is that the target requires unobserved facts, while teacher references can also conflict with those factors/rules. This source belongs in exploratory synthetic/teacher agreement rather than an objective correctness leaderboard.

### P1: Some Jev–Laya and JevBench references are not independent human truth

Jev–Laya uses `gpt-5.5` both for generation and blind relabeling. Categorical disagreements are removed; ordinal labels only need to differ by at most one. This improves internal consistency but selects cases aligned with the same teacher's boundary. It is not independent human verification.

Retained ordinal generator/verifier differences are: triage frustration **51/167**, moderation severity **19/142**, routing difficulty **60/137**, reviews stars **37/150**, and guard harm **8/146**. Claims and multilingual categorical disagreements are **0/150** and **0/128** after filtering; that establishes filtered consistency, not objective truth.

JevBench original/easy cases have reasonably explicit states and rubrics for narrow tasks. Hard cases are cross-authored/blind-reviewed by Claude Opus 5 and GPT-5.6-Sol and remain AI-authored/reviewed evidence. Ten probability cases provide `gold_probs`; this harness scores only their top label. It does not reproduce the upstream proper-score or probability-calibration evaluation.

### P1: Policy and subjective labels support agreement claims

Fixed samples `prompt_injections:38` (an ordinary SQL coding request) and `prompt_injections:79` (a question about training time) are labeled injection. This is consistent with the source's narrow legitimate-input policy, not general injection truth.

Aegis human prompt labels have stronger independent annotation provenance than synthetic teachers, but its 21-category taxonomy still encodes a policy. Boundary cases such as `b4ba0d10eff04c9d8182b7eee78a8d24` depend on context and policy interpretation. Neither dataset establishes production attack detection or deployment safety.

Emotion and SST5 naturally include subjectivity. `emotion:984` appears compatible with feeling overlooked/self-suppression but is labeled anger. This is a suspected ambiguity, not a proven wrong label based on one reviewer. Five-level SST5 judgments should include MAE and within-one agreement.

## Assessment of all 15 sources

Sizes below are the actual evaluation populations. Examples use IDs and short paraphrases rather than reproducing source texts.

| Source | Reference and size | Validity assessment / sample evidence | Recommendation |
|---|---|---|---|
| AG News | 1,000 dataset topic labels | Visible text supports topic classification; `ag_news:940` illustrates sports/legal topic overlap. No action outcomes. | Auxiliary semantic control |
| Emotion | 1,000 weak/distant dataset labels | Single labels simplify subjective emotion; `emotion:984` is an ambiguous boundary. | Auxiliary semantic label agreement |
| Banking77 | 1,000 dataset labels, full 77 classes | Relevant closed-set support routing; `banking77:541` maps an account-blocked request to pin-blocked, showing a boundary. | Core narrowly defined intent routing |
| BoolQ | 1,000 validation states, two interfaces | Passage/question usually support a binary judgment, e.g. `boolq:1102`. Public test gold unavailable. | Core passage-conditioned judgment; disclose Laya task-family overlap |
| SST5 | 1,000 states, two interfaces | Ordered sentiment with subjective boundaries; `sst5:1564` has limited short-text context. | Auxiliary ordinal control with MAE/within-one |
| XNLI | 1,000 aligned pairs, dataset NLI labels | Useful NLI and paired consistency; indices `2540`, `3068`, `1964` show awkward translation or expression drift. | Core/auxiliary NLI; qualify language gaps |
| MASSIVE | 1,000 aligned pairs, full 60 intents | Useful closed-set routing; indices `2270`, `2819`, `2250` show place/name localization. Test observes 59 classes. | Core multilingual routing; account for localization |
| prompt-injections | All 116 policy labels | Narrow legitimate-input definition includes ordinary instructions among injections; examples `:38`, `:79`. | Exploratory policy agreement; exclude from general correctness ranking |
| typed-decisions | 400 states / 2,000 teacher decisions | Underdetermined targets and rubric/factor conflicts; invoice `000027`, agent-trace `000052`. | Exploratory teacher agreement; exclude from objective correctness ranking |
| JevBench | 72 original, 48 easy, 111 hard | Original/easy states/rubrics are relatively explicit; hard remains AI-created. Examples `original-routing-05-1`, `easy-tool_selection-00`, `hard-opus-a-probability-04`. | Original/easy core; hard exploratory; probability cases top-label only |
| ReflexBench | 95 development fixtures | Often explicit state/rubric rules; e.g. `public-choice-v1-execution-failure-classification-synthetic-permission-denied`. | Auxiliary product regression, not unseen generalization |
| Jev–Laya | 1,470 states / 3,386 decisions | Same-model generation/relabeling/filtering; examples `triage-0034`, `reviews-0074`, `needle-02-1000-start`. | Synthetic/policy agreement; needle as narrow retrieval control |
| CLINC150/OOS | 5,500 labels; 150 intents + OOS | Relevant to a fixed ontology; `clinc:5226` OOS and `clinc:2908` in-scope. OOS is not universal unanswerability. | Core explicit OOS intent classification |
| TurtleBench | 1,532 rows / 32 stories | Exact conflict `484`/`832`; `1369`, `1282`, `132` illustrate permissive entailment boundaries. | Exclude from noise-free correctness claims before repair; exploratory contextual reasoning afterward |
| Aegis2 prompt | 1,928 human annotations | Taxonomy-specific policy; conflict `8e226...`/`92abce...`, boundary `b4ba0...`. | Human policy-agreement auxiliary; conflict treatment required in a future version |

## Bilingual comparisons and dependency units

XNLI/MASSIVE use aligned source indices and gold, supporting paired comparisons. XNLI Chinese is translated; MASSIVE is localized rather than translated word-for-word. Language differences therefore combine model capability with translation/localization difficulty. Chinese states with English instructions do not establish end-to-end all-Chinese capability.

Confidence intervals must respect dependence:

- Needle: **25 original needles × 6 lengths × 3 positions = 450 states**, not 450 independent facts.
- TurtleBench: **32 stories**, with up to 100 rows per story.
- JevBench: **36 shared-state groups with two questions**; remaining groups have one question.
- Aegis currently groups by exact raw prompt equality. Historical scores retain conflicting official rows; conflict-specific exclusion/adjudication is a future recommendation. Any normalized-text grouping would also require a new protocol.
- typed-decisions has five questions per state, not five independent states.

Current metrics already use group-cluster bootstrap for needle variants, Turtle stories, repeated Aegis prompts, and questions sharing a state. Clustering addresses dependence, not reference bias or label contradictions.

## Contamination and claim boundaries

All public sources may have appeared in training; no decontamination search establishes otherwise. AG News/BoolQ overlap with known Laya task families, which does not by itself prove row-level test leakage.

Supported claims include fixed-checkpoint agreement under a fixed adapter/candidate space, closed-ontology routing, passage-conditioned judgments, paired language consistency, narrow needle retrieval, and order/repeat stability diagnostics.

Unsupported claims include a blended general decision-accuracy ranking, optimal business actions, interactive agent success, utility or causal decision quality, production safety, general injection detection/refusal, replicated JevBench proper-score calibration, contamination-free generalization, and equivalence of teacher/AI-reviewed/human reference quality.

## Integrity checks A–F, limited to this review

| Check | Verdict | Evidence and scope |
|---|---|---|
| A. Ground-truth provenance | WARN | No path found that silently reuses evaluated-model outputs as gold; `common.py` lines 70–72 whitelist state/questions. Mixed reference types and verified conflicts require separate interpretation. |
| B. Score normalization | PASS | `metrics.py` lines 43–53 compares predicted and reference labels directly. Candidate-probability normalization does not rescale accuracy by model output maxima/means. |
| C. Result existence | PASS, limited | Frozen inputs, four metadata groups, raw files, summary JSON and CSV exist and are protocol-bound. This is not a fresh audit of every historical prediction or table number. |
| D. Metric reachability | WARN, limited | Accuracy, clustered CI, OOS, ordinal, bilingual, and sensitivity paths are reachable through metrics/report code. No new exhaustive dead-code audit of the whole repository was performed. |
| E. Scope | WARN | Multiple static components under one fixed run configuration; no action outcomes, real utility, independent repeated human adjudication, or decontamination. |
| F. Evaluation type | PASS | Dataset-provided, human-prompt, synthetic-proxy, authored/AI-reviewed, programmatic, and source-policy labels remain distinct. |

Evaluation types: dataset-provided labels cover AG News, Emotion, Banking77, BoolQ, SST5, XNLI, MASSIVE, CLINC, and TurtleBench (with conflicts). Aegis has existing human prompt annotations (with conflicts); no new human study was conducted here. typed-decisions and non-needle Jev–Laya are synthetic proxies; JevBench/ReflexBench are authored/AI-reviewed; needle is programmatic. prompt-injections is a dataset-policy source, not universal attack truth.

## Recommendations for a future versioned protocol

These recommendations **do not retroactively modify v0.2** frozen inputs, predictions, metrics, or published scores. Any adopted changes require a new version and preservation of v0.2 reproducibility. They remain local for the user's review.

1. Keep per-source results, without a blended accuracy, using “reference agreement” or “accuracy against source reference” consistently.
2. Move typed-decisions, prompt-injections, and unrepaired TurtleBench out of a noise-free correctness track. Clearly separate synthetic/policy agreement for non-needle Jev–Laya, JevBench hard, and Aegis.
3. Adjudicate, exclude, or separately report the identified Turtle/Aegis conflicts. Keeping the first occurrence is not adjudication.
4. Separate JevBench original/easy from hard; mark its ten probability cases as top-label-only here.
5. Retain needle clustering by 25 original content units and report it separately. Disclose teacher identity and ordinal disagreements for other Jev–Laya tasks.
6. Before typed-decisions enters a correctness track, provide sufficient observable state and replace uncertain teacher averages with independent rule-based or human labels.
7. Retain paired language consistency and separate language accuracy, with translation/localization and English-instruction qualifications.

## Reproduction materials

Local review scripts, selected IDs, full structural checks, pinned upstream files, input hashes, and prompt/response traces are stored under `.aris/traces/experiment-audit/2026-09-28_dataset_validity/`. This directory is ignored by Git. Reports use IDs, numbers, and concise paraphrases instead of redistributing the source texts.
