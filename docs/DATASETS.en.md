# System1Bench datasets: purpose, provenance, and interpretation

English edition of the [Chinese dataset guide](DATASETS.zh-CN.md), covering the frozen v0.2 evaluation dated 2026-09-28.

System1Bench uses **15 public source datasets/collections**, expanded into **28 main suites and 8 stability controls**. These are not 36 independent datasets. Actual runs cover Laya English, Laya Multilingual, Llama-3.1-8B-Instruct, and Qwen3-8B. **Jev has not been evaluated.** Names containing “Jev” identify source collections or interfaces, not imported model scores.

This guide describes sources and intended uses. See the [source suitability review](DATASET_REVIEW.md), [English results](RESULTS.en.md), and [LLM comparison protocol](LLM_BASELINES.md).

## What these tasks measure

Each task supplies a state or text, a question, and a finite answer space:

| Interface | Meaning | Typical use |
|---|---|---|
| `choice` | Select one category or action | Intent classification or workflow routing |
| `noul` | Make a yes/no judgment | Urgency, tool requirements, or a risk flag |
| `score` | Select an ordered rating | Risk, frustration, or satisfaction level |

Traditional NLP data tests semantic components. Workflow collections resemble routing and review interfaces. Safety data tests compliance with a particular annotation policy. These are static judgments: actions are not executed and downstream outcomes are not observed. Scores therefore do not establish interactive agent success, business utility, or deployment safety. Different sources and reference qualities should remain separate rather than becoming a blended “decision intelligence” score.

## Source overview

Counts are **per model**, for main tasks only. One state can contain multiple questions. The download locations below are the versions actually used; a mirror or adapter is not necessarily the original creator.

| Dataset/collection | Main task | Actual download source | Evaluation size |
|---|---|---|---|
| AG News | Four-way news topic classification | [fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news) | 1,000 rows / 1,000 decisions |
| Emotion | Six-way text emotion classification | [dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion) | 1,000 rows / 1,000 decisions |
| Banking77 | 77 banking support intents | [mteb/banking77](https://huggingface.co/datasets/mteb/banking77) | 1,000 rows / 1,000 decisions |
| BoolQ | Passage-conditioned yes/no questions | [google/boolq](https://huggingface.co/datasets/google/boolq) | 1,000 states, two interfaces / 2,000 decisions |
| SST5 | Five-level sentiment | [SetFit/sst5](https://huggingface.co/datasets/SetFit/sst5) | 1,000 states, two interfaces / 2,000 decisions |
| XNLI | Entailment, neutral, or contradiction | [facebook/xnli](https://huggingface.co/datasets/facebook/xnli) | 1,000 English + 1,000 Chinese / 2,000 decisions |
| MASSIVE Intent | 60 multilingual assistant intents | [mteb/amazon_massive_intent](https://huggingface.co/datasets/mteb/amazon_massive_intent) | 1,000 English + 1,000 Chinese / 2,000 decisions |
| deepset prompt-injections | Injection-policy classification | [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) | 116 rows / 116 decisions |
| LocalLLaMA typed-decisions | Multiple decisions over a shared workflow state | [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) | 400 states / 2,000 decisions |
| CLINC150/OOS | 150 in-scope intents plus out-of-scope requests | [clinc/clinc_oos](https://huggingface.co/datasets/clinc/clinc_oos) | 5,500 rows / 5,500 decisions |
| JevBench | Native typed decisions | [fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench) | 231 rows / 231 decisions |
| ReflexBench | Product/workflow choice regression fixtures | [brida-ai/reflexbench](https://github.com/brida-ai/reflexbench) | 95 rows / 95 decisions |
| Jev–Laya benchmark | Eight workflow/retrieval tasks | [harrymunro/jev-laya-benchmark](https://github.com/harrymunro/jev-laya-benchmark) | 1,470 states / 3,386 decisions |
| TurtleBench adapter | Story-grounded guess checking | [spoonnotfound/decision-model-bench](https://github.com/spoonnotfound/decision-model-bench) | 1,532 rows across 32 stories / 1,532 decisions |
| Aegis2 | Prompt content safety | [nvidia/Aegis-AI-Content-Safety-Dataset-2.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0) | 1,928 rows / 1,928 decisions |

## Individual sources

### 1. AG News

**Origin and task.** We use the Hugging Face `fancyzhx/ag_news` distribution of the AG News topic-classification dataset. News text is assigned to world, sports, business, or science/technology. The hosting account is the download entry point, not the original author of every news article.

**Our use.** A fixed sample of 1,000 out of 7,600 test rows, in `ag_news`.

**Interpretation.** Useful for simple semantic classification and content routing. It does not test complex constraints or action outcomes. AG News is a known Laya training-task family; results do not establish transfer to a completely unfamiliar task. Task-family overlap alone does not prove that particular test rows were used for training.

### 2. Emotion

**Origin and task.** `dair-ai/emotion` classifies short English text into sadness, joy, love, anger, fear, or surprise.

**Our use.** A fixed sample of 1,000 out of 2,000 test rows, in `emotion`.

**Interpretation.** A component test for emotion-sensitive support routing. Weak/distant supervision and a single emotion label simplify ambiguous language. Agreement with these labels does not establish psychological diagnosis or successful customer handling.

### 3. Banking77

**Origin and task.** The original dataset comes from [PolyAI's task-specific-datasets](https://github.com/PolyAI-LDN/task-specific-datasets). We download the MTEB mirror `mteb/banking77`. Each banking support request is assigned to one of the complete **77 intents**.

**Our use.** The mirror deduplicates the original 3,080 test rows to 3,076; we select a fixed 1,000-row sample for `banking77`. Another 100 of these rows receive same-order repeat and reversed-option controls.

**Interpretation.** Closely related to selecting the appropriate support workflow, with many similar candidates. It tests intent, not successful execution. Original Banking77 terms are CC BY 4.0; the mirror's MIT description is insufficient to override upstream data terms.

### 4. BoolQ

**Origin and task.** Google's `google/boolq` provides a passage and a natural yes/no question.

**Our use.** Public test gold is unavailable, so we select 1,000 of 3,270 **validation** rows. Identical states are evaluated using `noul` and `choice`, producing `boolq` and `boolq_choice`, with 2,000 decisions.

**Interpretation.** Tests passage-conditioned binary judgments and interface sensitivity. The two suites reuse questions and are not independent evidence. BoolQ is another known Laya training-task family.

### 5. SST5

**Origin and task.** The five-class Stanford Sentiment Treebank task, downloaded through the `SetFit/sst5` mirror. Labels range from very negative to very positive.

**Our use.** A fixed 1,000 of 2,210 test rows, evaluated as ordinal `score` in `sst5` and categorical `choice` in `sst5_choice`. Indices are 0–4, for 2,000 decisions.

**Interpretation.** Useful for ordered outputs such as ratings. Exact-level accuracy differs from being one level away, so MAE and within-one agreement are also reported. This is text sentiment, not verified real customer satisfaction.

### 6. XNLI

**Origin and task.** The original project is [facebookresearch/XNLI](https://github.com/facebookresearch/XNLI); we download `facebook/xnli`. Given a premise and hypothesis, select entailment, neutral, or contradiction. Neutral means that the premise does not settle the hypothesis.

**Our use.** Aligned samples of 1,000 English and 1,000 Chinese rows from 5,010 test rows per language, in `xnli_en` and `xnli_zh`.

**Interpretation.** Tests evidence support, negation, and cross-language consistency. Chinese evaluation text is translated and does not represent every native Chinese workflow. Both languages refer to the same source items. Most question instructions remain English, so this is not an all-Chinese prompt evaluation.

### 7. MASSIVE Intent

**Origin and task.** The underlying dataset is Amazon MASSIVE. We use MTEB's `amazon_massive_intent` subset to evaluate **60-way intent classification**, not every original task such as slot extraction.

**Our use.** Aligned English and Simplified Chinese samples of 1,000 rows each from 2,974 test rows per language, in `massive_en` and `massive_zh`. The full 60-class ontology is retained although test data observes only 59 classes. Only training **label names** are used to reconstruct the ontology; no training utterances are used for learning or demonstrations. English also has 100-row order controls.

**Interpretation.** Relevant to selecting an assistant function and comparing languages. It does not test tool arguments, execution, or multistep dialogue completion. Localized names and places can also affect paired language comparisons.

### 8. deepset prompt-injections

**Origin and task.** `deepset/prompt-injections` labels legitimate requests and injections. Integer polarity was checked against the same publisher's classifier: `0 = LEGIT`, `1 = INJECTION`.

**Our use.** All 116 test rows, converted to a boolean question in `prompt_injections`.

**Interpretation.** An exploratory input-policy diagnostic. The publisher narrowly defines legitimate input as questions or keyword searches, so ordinary role-play or instructions may be labeled injection. Scores primarily reflect agreement with that policy, not general attack-detection accuracy. Annotation personnel are not fully established, and the dataset card has conflicting license declarations; see the [source review](DATASET_REVIEW.md).

### 9. LocalLLaMA typed-decisions

**Origin and task.** Hugging Face's `LocalLLaMA/typed-decisions` provides structured states with multiple questions. The LocalLLaMA publisher namespace is distinct from the Llama model used as our baseline.

**Our use.** All 400 test states: 100 each for agent-trace observability, customer service, invoice processing, and security incidents. Five questions per state produce 2,000 decisions in `typed_decisions`. Agent monitoring includes action, human review, outcome, risk, and urgency judgments.

**Interpretation.** The interface closely resembles Jev/Laya, but answers are synthetic teacher references rather than independently verified optimal actions. Use teacher agreement; do not read the score as real business correctness.

### 10. CLINC150/OOS

**Origin and task.** Original project: [clinc/oos-eval](https://github.com/clinc/oos-eval/). Download: `clinc/clinc_oos`. It adds out-of-scope requests to 150 in-scope intent classes.

**Our use.** All 5,500 `plus/test` rows: 4,500 in scope and 1,000 OOS. All 151 candidates are preserved in `clinc150_oos`.

**Interpretation.** Useful for routing requests while recognizing those outside a fixed service ontology. This is classification with an explicit OOS option; it is not abstention using a calibrated threshold. Inspect in-scope accuracy and OOS precision, recall, F1, and AUROC separately. Aggregate accuracy can hide excessive rejection or a failure to reject.

### 11. JevBench

**Origin and task.** `fstandhartinger/jevbench` provides public native `choice`, `noul`, `score`, and other decision cases.

**Our use.** Public original/easy/hard sets contain 72/48/111 cases, for 231 decisions in three suites. The 36 eligible original choice cases also receive order controls.

**Interpretation.** Suitable for examining typed question behavior, with different reference quality across tiers. Original/easy cases are authored/reviewed; hard cases are AI-authored and cross-model reviewed. We do not reproduce private sets or the full router/judge leaderboard. Ten exact-probability cases are scored using their provided top-label target, not the upstream proper-score probability metric. These numbers should not be directly compared to that upstream metric.

### 12. ReflexBench

**Origin and task.** The `reflex-public-choice-v1` collection in `brida-ai/reflexbench` contains public product/workflow regression fixtures.

**Our use.** All 95 cases in `reflexbench_reflex-public-choice-v1`, using semantic `expected` rather than policy-branch `expectedBranch`. All 95 also receive same-order and reversed-order controls.

**Interpretation.** Useful for interface and policy regression, but these are public development fixtures rather than pristine held-out examples. An additional 110 parent fixtures are not counted again as independent evidence.

### 13. Jev–Laya benchmark

**Origin and task.** The third-party `harrymunro/jev-laya-benchmark` repository provides eight tasks. Original question definitions are preserved, while references are kept separate from model inputs. The 1,470 states yield 3,386 decisions.

| Suite | Input and judgments | States | Decisions |
|---|---|---:|---:|
| `jev_laya_triage` | Support message: six-way intent, urgency, four-level frustration | 167 | 501 |
| `jev_laya_moderation` | Forum post: toxicity, targeted harassment, four-level severity | 142 | 426 |
| `jev_laya_routing` | User request: six domains, four difficulty levels, need for live/private information or tools | 137 | 411 |
| `jev_laya_claims` | Passage/claim: supported, contradicted, or unmentioned; binary support | 150 | 300 |
| `jev_laya_reviews` | Product review: five-star rating and recommendation | 150 | 300 |
| `jev_laya_guard` | Prompt: injection/jailbreak attempt and four-level harm if followed | 146 | 292 |
| `jev_laya_multilingual` | Non-English support message: six-way intent and urgency | 128 | 256 |
| `jev_laya_needle` | Long notes: requested customer outcome and mention of damaged goods | 450 | 900 |

**Interpretation.** These tasks closely resemble triage, moderation, and routing interfaces. Multilingual cases cover Spanish, French, German, Portuguese, Italian, Japanese, and Chinese, but the 128 states are not parallel translations of the same questions.

Workflow cases were GPT-generated and blindly relabeled by the same model. Categorical disagreements were filtered, while limited ordinal disagreements remained. This is not independent human verification. Needle references are programmatic; its 450 states are correlated length/position variants over 25 original needles. Statistics cluster by original needle. The task tests explicit fact retrieval, not every form of long-context reasoning.

### 14. TurtleBench adapter

**Origin and task.** We download `tasks/data/turtlebench-en.jsonl` from `spoonnotfound/decision-model-bench`, a decision-model adaptation of TurtleBench. The adapter repository's author should not automatically be identified as the original TurtleBench author.

**Our use.** All 1,532 English guesses across 32 stories. Given the surface story, underlying solution, and guess, select Correct (supported), Incorrect (contradicted), or Unknown (insufficient information). An additional binary metric merges Incorrect and Unknown.

**Interpretation.** Tests contextual support and recognition of insufficient evidence, like a lateral-thinking puzzle host checking guesses. The supplied solution is intended context; the target is the guess label. Statistics cluster by story. Our prompt and merged-label metric do not reproduce the upstream evaluator exactly.


### 15. Aegis2

**Origin and task.** NVIDIA's `Aegis-AI-Content-Safety-Dataset-2.0`, also associated with Nemotron Content Safety V2, contains prompt/response safety annotations. Our task evaluates **the user prompt only**.

**Our use.** Exclude 36 `REDACTED` test inputs and use 1,928 prompts with human prompt labels in `aegis2_prompt`. The instruction lists 21 safety categories. Safe/Needs Caution are treated as non-unsafe by the protocol; retained test rows actually have safe/unsafe labels.

**Interpretation.** Relevant to input-safety policy agreement. Response annotations mix human and LLM sources and are not evaluated. The adapter does not fully reproduce the annotation manual or official guardrail model.

**Known data issues.** There are 13 excess duplicate rows and one group with conflicting labels. Historical results retain official rows, cluster exact repeated prompts, and report first-occurrence deduplication sensitivity. First occurrence is not an adjudication of the conflicting label. Test and validation share nine prompt texts; validation was not used for fitting or threshold selection. Future validation tuning must exclude overlap.

## How 15 sources become 36 suites

| Expansion | Suites |
|---|---:|
| AG News, Emotion, Banking77, prompt-injections, typed-decisions | 5 |
| BoolQ and SST5, two interfaces each | 4 |
| XNLI and MASSIVE, two languages each | 4 |
| JevBench original/easy/hard | 3 |
| ReflexBench | 1 |
| Eight Jev–Laya tasks | 8 |
| CLINC, TurtleBench, Aegis2 | 3 |
| **Main suites** | **28** |

Four sources each receive a repeat and a genuine reversal, adding eight suites:

| Base suite | Same-order repeat | Reversed options |
|---|---:|---:|
| Banking77 | 100 | 100 |
| MASSIVE English | 100 | 100 |
| JevBench original choice | 36 | 36 |
| ReflexBench public choice | 95 | 95 |
| **Decisions** | **331** | **331** |

Repeats control for run variation; reversals test candidate-order sensitivity while preserving semantic labels and gold. LLM reversals also reassign answer codes. This is one permutation diagnostic, not exhaustive invariance. Stability and correctness are distinct metrics.

Each model therefore has **22,934 logical state requests and 26,450 decisions**: 25,788 main decisions plus 662 order-control decisions. Requests include reused states and controls, not independent unique samples. They also need not equal backend forward-pass counts.

## Which tasks are most relevant?

| Question | Relevant tasks | Main qualification |
|---|---|---|
| Where should a request be routed? | Banking77, MASSIVE, CLINC, Jev–Laya routing | Preserve complete candidates and distinguish OOS behavior |
| Can a shared state support several workflow judgments? | typed-decisions, Jev–Laya, JevBench, ReflexBench | Synthetic/authored agreement is not verified optimal action |
| How does Chinese performance compare? | Paired XNLI/MASSIVE; multilingual Jev–Laya as a supplement | Translation/localization, instruction language, and alignment matter |
| Does evidence support a claim? | BoolQ, XNLI, Jev–Laya claims, TurtleBench | Separate missing evidence from contradiction; inspect label quality |
| Can a model apply an input-safety policy? | Aegis2, Jev–Laya guard, prompt-injections | Different safety/injection definitions require separate interpretation |
| Does long context hide a relevant fact? | Jev–Laya needle | Account for length, position, and correlated variants |
| Does candidate order change the answer? | Eight order controls | Compare against repeats; stable answers can still be wrong |

AG News, Emotion, and SST5 supplement these with basic semantics and ordinal judgment. Business-value claims require domain-specific independent labels, observed action outcomes, or an interactive environment. Public-data training overlap has not been ruled out. Llama/Qwen use a fixed zero-shot direct-decision interface, with Qwen thinking off; these are not best-achievable scores after prompt optimization or deliberation.

## Discovery, review, and reproducibility

Sources were found through GitHub READMEs, data/generator files, and Hugging Face cards, metadata, and actual data files. Checks cover candidate coverage, label polarity, target leakage through input fields, splits, duplicates/dependencies, context fit, and data terms. Selection was frozen before new inference and did not depend on measured accuracy.

Standard datasets use sampling without replacement with seed `20260927`; smaller or additional collections follow the full-data rules above. Source text is downloaded upstream rather than bundled for redistribution. Exact revisions, file paths, and SHA256 are in [sources.json](../sources.json) and [external_sources.json](../external_sources.json).

Not every discovered benchmark was adopted. `AbdelStark/jev-benchmarks` reuses AG News/Emotion/Banking slices, so these were not counted again. The BTZSC Banking77 conversion has only 72 candidates, missing-positive groups, and a gold-revealing `label_text` field; the complete original task ontology avoids those traps. Other projects use underdetermined planted gold or describe supplied-answer comparisons as permutation tests. Full inclusion/exclusion and licensing evidence is in [DATASET_REVIEW.md](DATASET_REVIEW.md).

## Verification links

- [Frozen protocol](../PROTOCOL.md) and [suite manifest](../protocol_manifest.json).
- [Adaptation code](../system1bench/prepare.py) and [Jev–Laya task definitions](../system1bench/jev_laya_tasks.py).
- [English results](RESULTS.en.md) and [LLM comparison protocol](LLM_BASELINES.md).
- [Source terms and attribution](../NOTICE.md).

This documentation introduces no new evaluation samples and changes no historical score.
