# System1Bench: Results from our own runs (v0.2)

English translation of the frozen [Chinese results report](RESULTS.zh-CN.md). All historical values are preserved.
**System 1 decision-model benchmark. All values come from actual runs in this repository. Jev has not been evaluated, and no third-party model scores have been imported.**

The evaluation covers 15 public sources and 36 task/control suites. Each checkpoint has 22,934 logical requests and 26,450 decisions; the four checkpoints total 105,800 decisions, with zero failures. Sources, languages, primitives, and reference quality are reported separately, without a blended overall score.

Both Laya checkpoints (English/Multilingual) come from `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, using Laya 0.3.20. They are not the `laya-typed-decisions` checkpoint.

Llama/Qwen use fixed zero-shot candidate-code logit scoring, with Qwen thinking disabled. Each question has a separate forward pass, with no generated chain of thought. Candidate-only softmax is not calibrated confidence. See [LLM_BASELINES.md](LLM_BASELINES.md).

New controlled latency and fixed-batch throughput measurements are reported separately in [Performance results](PERFORMANCE_RESULTS.en.md), with their [protocol](PERFORMANCE_PROTOCOL.md) and [audit record](PERFORMANCE_AUDIT.md). They do not replace the full accuracy evaluation below.

## Results by task

The following values are accuracy/agreement against source references over all scheduled samples. Parentheses show 95% group-bootstrap intervals. Multiple questions share a state cluster; TurtleBench clusters by story, and needle tasks by original needle. Synthetic-reference results do not establish human-verified real-world decision correctness.

| Task | Decisions | Laya English | Laya Multilingual | Llama-3.1-8B-Instruct | Qwen3-8B | Reference |
|---|---:|---:|---:|---:|---:|---:|
| ag_news | 1000 | 94.30% (92.90%–95.70%) | 92.40% (90.80%–94.00%) | 88.90% (86.80%–90.80%) | 86.80% (84.70%–88.80%) | dataset_provided |
| emotion | 1000 | 59.10% (55.90%–62.00%) | 53.00% (49.70%–55.90%) | 50.50% (47.30%–53.70%) | 54.80% (51.70%–57.80%) | dataset_provided |
| banking77 | 1000 | 55.30% (52.20%–58.40%) | 51.20% (47.90%–54.40%) | 54.10% (50.90%–57.40%) | 66.80% (63.80%–69.90%) | dataset_provided |
| boolq | 1000 | 84.60% (82.40%–86.90%) | 77.70% (75.10%–80.20%) | 64.80% (61.80%–67.90%) | 83.50% (81.20%–85.70%) | dataset_provided |
| boolq_choice | 1000 | 83.60% (81.40%–85.90%) | 77.40% (74.80%–80.00%) | 68.70% (65.90%–71.60%) | 83.30% (81.00%–85.70%) | dataset_provided |
| sst5 | 1000 | 34.60% (31.60%–37.60%) | 29.50% (26.70%–32.40%) | 32.00% (29.10%–34.80%) | 45.70% (42.80%–48.80%) | dataset_provided |
| sst5_choice | 1000 | 49.60% (46.30%–52.70%) | 35.60% (32.60%–38.40%) | 42.20% (39.10%–45.10%) | 43.90% (40.90%–46.80%) | dataset_provided |
| xnli_en | 1000 | 86.00% (83.80%–88.10%) | 81.70% (79.50%–83.90%) | 46.20% (43.20%–49.10%) | 78.70% (76.20%–81.10%) | dataset_provided |
| xnli_zh | 1000 | 61.50% (58.50%–64.40%) | 74.30% (71.60%–76.90%) | 40.50% (37.60%–43.40%) | 69.10% (66.30%–71.90%) | dataset_provided |
| massive_en | 1000 | 54.10% (51.00%–57.10%) | 42.30% (39.30%–45.50%) | 57.20% (54.20%–60.00%) | 66.30% (63.40%–69.20%) | dataset_provided |
| massive_zh | 1000 | 30.40% (27.40%–33.40%) | 33.20% (30.30%–36.10%) | 53.50% (50.40%–56.50%) | 62.60% (59.70%–65.40%) | dataset_provided |
| prompt_injections | 116 | 70.69% (62.93%–79.31%) | 57.76% (49.14%–66.38%) | 62.93% (54.31%–71.55%) | 63.79% (55.17%–72.41%) | dataset_provided |
| typed_decisions | 2000 | 36.35% (33.90%–38.80%) | 34.90% (32.65%–37.25%) | 51.20% (48.60%–53.85%) | 55.50% (52.80%–58.25%) | synthetic_teacher |
| jevbench_original | 72 | 70.83% (58.33%–81.94%) | 41.67% (29.17%–54.17%) | 75.00% (62.50%–86.11%) | 83.33% (70.83%–93.06%) | authored_or_AI_reviewed |
| jevbench_easy | 48 | 95.83% (89.58%–100.00%) | 89.58% (79.17%–97.92%) | 100.00% (100.00%–100.00%) | 100.00% (100.00%–100.00%) | authored_or_AI_reviewed |
| jevbench_hard | 111 | 29.73% (20.72%–38.74%) | 32.43% (24.32%–41.44%) | 34.23% (25.23%–43.24%) | 46.85% (36.94%–55.86%) | authored_or_AI_reviewed |
| reflexbench_reflex-public-choice-v1 | 95 | 58.95% (49.47%–69.47%) | 46.32% (36.84%–55.79%) | 60.00% (50.53%–69.47%) | 84.21% (76.84%–91.58%) | authored_or_AI_reviewed |
| jev_laya_triage | 501 | 62.48% (58.28%–66.47%) | 55.69% (51.69%–59.88%) | 75.65% (72.65%–78.84%) | 80.04% (77.45%–82.63%) | synthetic_teacher |
| jev_laya_moderation | 426 | 67.84% (61.97%–73.71%) | 48.36% (43.89%–53.05%) | 88.97% (86.15%–91.55%) | 77.46% (73.71%–80.99%) | synthetic_teacher |
| jev_laya_routing | 411 | 64.23% (59.85%–69.10%) | 51.09% (45.99%–56.20%) | 61.31% (57.18%–65.21%) | 83.70% (79.81%–87.35%) | synthetic_teacher |
| jev_laya_claims | 300 | 90.00% (85.33%–94.00%) | 80.00% (74.00%–85.67%) | 61.67% (56.00%–67.00%) | 98.67% (97.00%–100.00%) | synthetic_teacher |
| jev_laya_reviews | 300 | 70.67% (66.00%–75.33%) | 42.33% (36.33%–48.34%) | 83.00% (79.33%–86.67%) | 87.00% (83.67%–90.67%) | synthetic_teacher |
| jev_laya_guard | 292 | 60.62% (54.79%–66.44%) | 33.22% (27.74%–38.70%) | 88.01% (83.90%–91.78%) | 83.22% (78.42%–87.67%) | synthetic_teacher |
| jev_laya_multilingual | 256 | 57.81% (51.56%–64.45%) | 62.50% (57.03%–68.36%) | 94.53% (91.80%–97.27%) | 98.44% (96.48%–100.00%) | synthetic_teacher |
| jev_laya_needle | 900 | 50.22% (39.77%–61.00%) | 47.44% (35.00%–59.89%) | 77.89% (69.11%–85.89%) | 87.78% (79.11%–95.00%) | programmatic |
| clinc150_oos | 5500 | 55.73% (54.42%–57.07%) | 64.76% (63.51%–65.96%) | 55.20% (53.87%–56.51%) | 67.78% (66.62%–69.00%) | dataset_provided |
| turtlebench | 1532 | 42.62% (38.74%–46.67%) | 41.64% (37.53%–45.42%) | 42.17% (36.36%–48.19%) | 44.19% (38.53%–50.00%) | dataset_provided |
| aegis2_prompt | 1928 | 49.59% (47.29%–51.76%) | 57.05% (54.79%–59.25%) | 66.80% (64.63%–68.86%) | 72.67% (70.62%–74.68%) | human_prompt_annotation |

## Input completeness

Laya uses `max_len=8192` and `head_max_len=4096`; the LLM context ceiling is 32,768 tokens, with truncation prohibited. Semantic inputs are identical, but tokenizers and wrappers differ. Per-question audits found complete inputs for 105,800/105,800 decisions. Laya also has a 48-token cap per candidate description. The table below compares the same decisions with complete inputs across all checkpoints.

| Task | Complete for all models / Total | Laya English | Laya Multilingual | Llama-3.1-8B-Instruct | Qwen3-8B |
|---|---:|---:|---:|---:|---:|
| ag_news | 1000 / 1000 | 94.30% | 92.40% | 88.90% | 86.80% |
| emotion | 1000 / 1000 | 59.10% | 53.00% | 50.50% | 54.80% |
| banking77 | 1000 / 1000 | 55.30% | 51.20% | 54.10% | 66.80% |
| boolq | 1000 / 1000 | 84.60% | 77.70% | 64.80% | 83.50% |
| boolq_choice | 1000 / 1000 | 83.60% | 77.40% | 68.70% | 83.30% |
| sst5 | 1000 / 1000 | 34.60% | 29.50% | 32.00% | 45.70% |
| sst5_choice | 1000 / 1000 | 49.60% | 35.60% | 42.20% | 43.90% |
| xnli_en | 1000 / 1000 | 86.00% | 81.70% | 46.20% | 78.70% |
| xnli_zh | 1000 / 1000 | 61.50% | 74.30% | 40.50% | 69.10% |
| massive_en | 1000 / 1000 | 54.10% | 42.30% | 57.20% | 66.30% |
| massive_zh | 1000 / 1000 | 30.40% | 33.20% | 53.50% | 62.60% |
| prompt_injections | 116 / 116 | 70.69% | 57.76% | 62.93% | 63.79% |
| typed_decisions | 2000 / 2000 | 36.35% | 34.90% | 51.20% | 55.50% |
| jevbench_original | 72 / 72 | 70.83% | 41.67% | 75.00% | 83.33% |
| jevbench_easy | 48 / 48 | 95.83% | 89.58% | 100.00% | 100.00% |
| jevbench_hard | 111 / 111 | 29.73% | 32.43% | 34.23% | 46.85% |
| reflexbench_reflex-public-choice-v1 | 95 / 95 | 58.95% | 46.32% | 60.00% | 84.21% |
| jev_laya_triage | 501 / 501 | 62.48% | 55.69% | 75.65% | 80.04% |
| jev_laya_moderation | 426 / 426 | 67.84% | 48.36% | 88.97% | 77.46% |
| jev_laya_routing | 411 / 411 | 64.23% | 51.09% | 61.31% | 83.70% |
| jev_laya_claims | 300 / 300 | 90.00% | 80.00% | 61.67% | 98.67% |
| jev_laya_reviews | 300 / 300 | 70.67% | 42.33% | 83.00% | 87.00% |
| jev_laya_guard | 292 / 292 | 60.62% | 33.22% | 88.01% | 83.22% |
| jev_laya_multilingual | 256 / 256 | 57.81% | 62.50% | 94.53% | 98.44% |
| jev_laya_needle | 900 / 900 | 50.22% | 47.44% | 77.89% | 87.78% |
| clinc150_oos | 5500 / 5500 | 55.73% | 64.76% | 55.20% | 67.78% |
| turtlebench | 1532 / 1532 | 42.62% | 41.64% | 42.17% | 44.19% |
| aegis2_prompt | 1928 / 1928 | 49.59% | 57.05% | 66.80% | 72.67% |

Per-question audits and each checkpoint's complete-input subset are available in the JSON results. Candidate, instruction, and state shortening, as well as candidate collisions, are counted separately. Input completeness describes preservation during encoding; it does not guarantee that the model uses every piece of information correctly.

## Open set: CLINC150/OOS

Out-of-scope requests are identified through the explicit `oos` option among 151 classes. No rejection threshold was fitted on the test set. AUROC uses P(oos).

| Checkpoint | In-scope accuracy | OOS precision | OOS recall | OOS F1 | OOS AUROC |
|---|---:|---:|---:|---:|---:|
| english | 49.11% | 38.44% | 85.50% | 0.5304 | 0.8573 |
| multilingual | 74.42% | 86.59% | 21.30% | 0.3419 | 0.8539 |
| llama31_8b_instruct | 52.51% | 41.91% | 67.30% | 0.5165 | 0.8021 |
| qwen3_8b | 65.93% | 57.52% | 76.10% | 0.6552 | 0.8854 |

## Ordinal scoring: SST5 (fixed 0–4 scale)

Lower MAE is better; within-one allows an error of one level. Tasks with different scales are not pooled into one MAE ranking.

| Checkpoint | Modal-index MAE | Expected-index MAE | Within one level |
|---|---:|---:|---:|
| english | 0.9270 | 0.9144 | 77.80% |
| multilingual | 1.3000 | 1.2946 | 58.70% |
| llama31_8b_instruct | 1.0350 | 0.9999 | 71.30% |
| qwen3_8b | 0.6560 | 0.6482 | 90.80% |

## Option-order stability

The same inputs are first repeated with unchanged option order, then evaluated with the candidate dictionary genuinely reversed; semantic label IDs and gold remain unchanged. Repeat agreement provides a control for numerical/batch variation. LLM reversal also reassigns answer codes. This single-reversal diagnostic does not establish invariance to every permutation.

| Checkpoint / Task | N | Original↔Repeat agreement | Repeat↔Reversed agreement | Repeat accuracy | Reversed accuracy |
|---|---:|---:|---:|---:|---:|
| english / banking77 | 100 | 100.00% | 52.00% | 49.00% | 58.00% |
| english / massive_en | 100 | 100.00% | 50.00% | 54.00% | 52.00% |
| english / jevbench_original | 36 | 100.00% | 91.67% | 61.11% | 58.33% |
| english / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 89.47% | 58.95% | 58.95% |
| multilingual / banking77 | 100 | 100.00% | 62.00% | 44.00% | 44.00% |
| multilingual / massive_en | 100 | 100.00% | 54.00% | 50.00% | 43.00% |
| multilingual / jevbench_original | 36 | 100.00% | 77.78% | 58.33% | 55.56% |
| multilingual / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 80.00% | 46.32% | 45.26% |
| llama31_8b_instruct / banking77 | 100 | 96.00% | 35.00% | 62.00% | 37.00% |
| llama31_8b_instruct / massive_en | 100 | 95.00% | 49.00% | 62.00% | 60.00% |
| llama31_8b_instruct / jevbench_original | 36 | 100.00% | 77.78% | 80.56% | 66.67% |
| llama31_8b_instruct / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 82.11% | 60.00% | 57.89% |
| qwen3_8b / banking77 | 100 | 99.00% | 61.00% | 72.00% | 54.00% |
| qwen3_8b / massive_en | 100 | 100.00% | 68.00% | 74.00% | 66.00% |
| qwen3_8b / jevbench_original | 36 | 100.00% | 86.11% | 83.33% | 86.11% |
| qwen3_8b / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 85.26% | 84.21% | 82.11% |

## Paired English–Chinese inputs

XNLI and MASSIVE use aligned English and Chinese samples. Prediction agreement does not imply correctness: both languages may receive the same wrong answer.

| Checkpoint / Dataset | Pairs | EN–ZH prediction agreement | Both languages correct |
|---|---:|---:|---:|
| english / xnli | 1000 | 65.10% | 57.30% |
| english / massive | 1000 | 41.30% | 26.50% |
| multilingual / xnli | 1000 | 75.60% | 66.50% |
| multilingual / massive | 1000 | 50.50% | 27.70% |
| llama31_8b_instruct / xnli | 1000 | 77.50% | 35.80% |
| llama31_8b_instruct / massive | 1000 | 68.10% | 48.40% |
| qwen3_8b / xnli | 1000 | 78.20% | 64.00% |
| qwen3_8b / massive | 1000 | 78.80% | 58.50% |

## Stratified metrics and sensitivity

`results/summary.json` provides strata by primitive (choice/noul/score), language, task family, question ID, and needle length/position. It also reports Brier, ECE, high-confidence errors, macro-F1 over the complete label set, and ordinal MAE. Probability metrics use valid outputs only; accuracy counts failures as incorrect.

| Checkpoint | Aegis all-row accuracy | Aegis first-occurrence deduplication | Turtle three-class | Turtle merged Incorrect/Unknown |
|---|---:|---:|---:|---:|
| english | 49.59% | 49.61% | 42.62% | 66.71% |
| multilingual | 57.05% | 57.02% | 41.64% | 58.88% |
| llama31_8b_instruct | 66.80% | 66.84% | 42.17% | 42.17% |
| qwen3_8b | 72.67% | 72.58% | 44.19% | 62.34% |

Aegis retains 1,928 valid official test rows, including 13 excess duplicates and one conflicting-label group. Deduplication sensitivity keeps the first source-file occurrence, without choosing labels based on predictions. Turtle binary results use this harness's label-merging adaptation and do not claim to reproduce the upstream leaderboard.

## Performance and reproducibility limits

| Checkpoint | Cumulative batch inference seconds | Inference failures |
|---|---:|---:|
| english | 223.31 | 0 |
| multilingual | 129.10 | 0 |
| llama31_8b_instruct | 2251.28 | 0 |
| qwen3_8b | 2375.43 | 0 |

LLM prompts are tokenized and cached during the input audit, with a separate forward pass per question. Timing sums synchronized batch predict calls and includes first-batch initialization effects. It excludes downloads, model loading, input audits, and result writes. Models ran on A100 GPUs on a machine with other workloads; these values do not establish online serving latency or a stable hardware speed ranking.

Model files were SHA256-hashed before inference. Source code, question order, complete inputs, and raw outputs are hash-bound. Suites are written atomically and failures retained. Source data and Laya can be reconstructed from pinned revisions. Local LLM snapshots retain pre-inference file hashes; subsequent upstream verification is documented in [LLM_BASELINES.md](LLM_BASELINES.md).

## Scope of conclusions

These results cover multiple static decision tasks and can diagnose differences in semantic classification, structured workflows, open-set behavior, and order sensitivity. They do not establish corresponding success rates in real interactive tasks. AG News/BoolQ are known Laya training-task families; training contamination has not been excluded for other public data. JevBench hard, LocalLLaMA, and Jev–Laya synthetic labels have reference bias; Reflex uses development fixtures.

Most question instructions are English, so Chinese-input performance does not establish all-Chinese instruction performance. Each checkpoint uses one fixed seed/configuration; intervals do not cover training randomness, prompt selection, or annotation error. The Laya English checkpoint internally clamps invalid high-candidate-count temperatures; its probabilities should not automatically be treated as calibrated.

deepset prompt-injections should only be interpreted as label agreement under its dataset policy: the publisher narrowly defines legitimate input as questions/keyword searches, so ordinary role-play or instructions may be labeled injection. The polarity of 0/1 labels is corroborated by a pinned publisher classifier configuration. Conflicting license declarations in the dataset card remain unresolved, and source texts are not redistributed here.

See [DATASET_REVIEW.md](DATASET_REVIEW.md) for sources, licensing, and suitability, [BASELINE_AUDIT.md](BASELINE_AUDIT.md) for the additional baseline review, and [EXPERIMENT_AUDIT.md](EXPERIMENT_AUDIT.md) for the original Laya review.
