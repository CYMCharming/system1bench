# Dataset and benchmark suitability review

Search date: 2026-09-28. Sources: GitHub repository trees, README/data/generator
files, Hugging Face dataset cards, immutable data files and metadata. Selection
was frozen before the new Laya runs and did not depend on their scores.

## What “suitable” means here

A static decision model needs a supplied state, a question with a finite answer
space, and independently sourced reference labels. A dataset can test a useful
component of decision-making without measuring agent task completion. We check
candidate coverage, label mapping, provenance, split, leakage through adapter
fields, duplicate grouping, context fit and redistribution terms. This review
does **not** certify every annotation as correct or guarantee no training overlap.

## Included sources

Exact revisions, source files and SHA256 hashes are in `sources.json` and
`external_sources.json`. Standard sample sizes are per language/task group.

| Source | v0.1 coverage | Suitability / limits | License evidence and distribution policy |
|---|---|---|---|
| [AG News](https://huggingface.co/datasets/fancyzhx/ag_news) | 1,000 / 7,600 test | Four-way topic classification; Laya training-task overlap known | Card says unknown; source news rights vary. Download only; no news text bundled |
| [Emotion](https://huggingface.co/datasets/dair-ai/emotion) | 1,000 / 2,000 test | Six-way short-text emotion; distant/weak annotation, not expert decision gold | Card says other; underlying social-media terms remain. Download only |
| [Banking77](https://huggingface.co/datasets/mteb/banking77) | 1,000 / 3,076 test | Full77 intents; MTEB copy deduplicates original3,080 to3,076; no candidate inferred from individual gold | MTEB card says MIT but original [PolyAI](https://github.com/PolyAI-LDN/task-specific-datasets) Banking77 is CC BY4.0. Treat upstream terms as controlling; do not redistribute text |
| [BoolQ](https://huggingface.co/datasets/google/boolq) | 1,000 / 3,270 validation, two encodings | Reading comprehension yes/no; test gold is not public; known Laya training-task family overlap | Card CC BY-SA3.0; downloaded passages not bundled |
| [SST5](https://huggingface.co/datasets/SetFit/sst5) | 1,000 / 2,210 test, two encodings | Five-level sentiment; exact index and MAE have different interpretations | SetFit card does not establish source-text rights; download only |
| [XNLI](https://huggingface.co/datasets/facebook/xnli) | aligned1,000 EN +1,000 ZH /5,010 each | Entailment/neutral/contradiction; exact pinned ID mapping; Chinese is translated evaluation | [Original XNLI](https://github.com/facebookresearch/XNLI) provides CC BY-NC4.0 dataset terms; no raw text redistribution |
| [MASSIVE](https://huggingface.co/datasets/mteb/amazon_massive_intent) | aligned1,000 EN +1,000 ZH /2,974 each |60-way intent; test observes59 classes. Full ontology from train **labels only**, no training utterance used | Apache2.0 card; download only for a consistent release policy |
| [deepset prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) |116 test | Exploratory reference-agreement diagnostic. The publisher defines legitimate requests as questions/keyword searches, so ordinary role-play/instructions can receive injection labels. Annotation personnel not established; not production attack correctness | Pinned card conflicts: nested dataset_info license CC BY4.0, top-level Apache2.0. Unresolved; no source text redistribution |
| [LocalLLaMA typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) |400 test states /2,000 decisions | Shared-state multi-question workflow, synthetic teacher references; report agreement, not human-grounded correctness | Apache2.0 card; no source states bundled |
| [CLINC150/OOS](https://huggingface.co/datasets/clinc/clinc_oos) |5,500 plus-test:4,500 in scope +1,000 OOS |150 intents plus explicit OOS; use original card's label order, OOS ID42. No blank/duplicate test texts found | CC BY3.0; source data download only |
| [JevBench](https://github.com/fstandhartinger/jevbench/tree/fd54ea7dc02bbe29c6ac8f6e015a54cdcff26805) |231 public:72 original +48 easy +111 hard |Native typed questions; original/easy authored/reviewed; hard AI-authored and cross-model reviewed. Not official private/router/judge leaderboard replication | Public files/provenance MIT; retain source pins. Only numerical outputs/IDs published |
| [ReflexBench](https://github.com/brida-ai/reflexbench/tree/0c3535de20124d278502c6d5e261916876ecfadd) |95 public-choice development fixtures |Use semantic `expected`, not policy `expectedBranch`. Product regression data; not pristine heldout. Do not double-count110 parent fixtures | Apache2.0 explicitly covers Brida-authored fixtures; source pin retained |
| [Jev–Laya benchmark](https://github.com/harrymunro/jev-laya-benchmark/tree/0f977d20641e347bffee05745fed265858930489) |1,470 items /3,386 decisions,8 tasks |GPT-generated and same-model blind reannotation, categorical filtering, ordinal disagreements allowed. Needle450 contains correlated variants; cluster by needle. Seven-language128 is not parallel translation | MIT. Original questions vendored with upstream license and attribution; raw samples download only |
| [TurtleBench adapter](https://github.com/spoonnotfound/decision-model-bench/tree/b04899d53eee353225f6774a170968e17652a8b8) |1,532 English rows /32 stories |Story-grounded guesses; supplied solution is intended context, not leaked evaluation target. Keep3-way labels, additionally report merged Incorrect/Unknown metric. Bootstrap by story | Apache2.0 upstream copy and notices recorded by adapter. Raw text download only |
| [Aegis2 / Nemotron Content Safety V2](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0) |1,928 human-labeled test prompts |Exclude36 REDACTED inputs.13 duplicate excess rows; one duplicate group has conflicting labels. Preserve official rows, cluster identical prompts, also report deterministic first-occurrence sensitivity | CC BY4.0 card. Prompt-only labels are human; response labels mix human/LLM and are not evaluated. No source text redistribution |

Aegis test/validation share9 prompt texts. We do not use validation or tune any
threshold in v0.1. Future validation fitting must exclude those overlapping
prompts. The pinned card describes an augmented validation set, while the
downloaded core validation file has1,245 rows; file bytes control this review.

The prompt-injections parquet labels are unnamed integers. The mapping used here
(`0 = LEGIT/false`, `1 = INJECTION/true`) is corroborated by the same publisher's
[classifier config at immutable revision80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1](https://huggingface.co/deepset/deberta-v3-base-injection/blob/80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1/config.json).
Its [model card at that revision](https://huggingface.co/deepset/deberta-v3-base-injection/blob/80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1/README.md)
lists deepset/prompt-injections and explicitly describes the narrow legitimate
request definition. This establishes label polarity, not annotation validity or
a resolution of the dataset card's conflicting licenses. Interpret the116-row
result as agreement with that dataset's policy, not an attack-detection guarantee.

JevBench's10 exact-probability cases are currently scored by their provided
top-label target. v0.1 does not reproduce its proper-score probability-reasoning
metric. Low/medium/high confidence labels elsewhere are not empirical calibration.
TurtleBench's extra binary number is our merged-label adaptation; this harness
does not execute the upstream evaluator and its three-class prompt can differ.

## Examined but not included as an additional scored source

| Repository / dataset | Finding | Decision |
|---|---|---|
| [AbdelStark/jev-benchmarks](https://github.com/AbdelStark/jev-benchmarks/tree/0d610cc53e79bcbec691312b0c4adb4a0e371642) |Useful comparison harness; AG News/Emotion/Banking through BTZSC,100 each |Use original datasets, not duplicate its300-item slice as new evidence |
| [btzsc/btzsc](https://huggingface.co/datasets/btzsc/btzsc/tree/fef2a2ac62b69c58670047dddf045c53d7c3cb5e) |Banking77:3,080 texts×72 hypotheses,200 texts no positive. MASSIVE:59 hypotheses,2,970 unique texts,169 zero-positive groups and4 repeated-text groups. `label_text` repeats **gold**, not candidate class |Reject blanket aggregation and never use `label_text` as a request candidate. Original sources avoid these schema traps |
| [nibzard/decision-model-benchmark](https://github.com/nibzard/decision-model-benchmark/tree/c349ba73641f3fa63acecb6f5d0023dabfe23c00) |Actual candidate-permutation controls useful. S5 uses randomly planted reference on underdetermined items; no-good-option gold=-1. No repository LICENSE |Independently implement generic option reversal on licensed sources; do not copy its generator/data or score arbitrary gold as correctness |
| [kyr0/typed-decision-bench](https://github.com/kyr0/typed-decision-bench/tree/1ef8b4602b8c74025c709b1d99cdd61b3d270fe6) |275 suites/27,598 cases vs stale217/21,700 quality summary. “Permutation” asks to compare supplied answers. “Calibration” is confidence-level classification. Expected utility already supplied in input. Mixed third-party GPQA terms; linked notice absent |Defer source-by-source audit. Do not relabel its meta-judgments as actual model invariance or calibrated decision quality |
| [instax-dutta/sysone-bench](https://github.com/instax-dutta/sysone-bench/tree/9447a17fccb524957d1211ecdf46153821ff0810) |1,190 cases/1,550 decisions; AI draft plus one human reviewer. Upstream rights registry inconsistent, e.g. Banking77 MIT |Do not redistribute consolidated suite or double-count borrowed datasets |
| [apolinario/decision-index](https://github.com/apolinario/decision-index/tree/87d4650b42b377c0291a89c1f1a879f9b31082bf) |Useful38-task pinned reconstruction; explicitly forbids redistribution of integrated suite under one license. Interactive environments unrun |Reference for future loaders, not blanket copied gold or source text |
| [sumleo/RLCDAlignBench](https://github.com/sumleo/RLCDAlignBench/tree/473b72f290234a49484c4d89c03aababcd74f758) |44 alignment-detection tasks; actual HF data gated; mixed reference scorers/teacher labels; metadata CC BY-NC4.0, source text separate |Deferred pending access and task-specific label/context review |
| [model-collapse/jev-bench](https://github.com/model-collapse/jev-bench/tree/fcec62f13ce961115af0d16317f0ff15986a9a25) |2,934 claimed gold/silver rows; included Banking77 license description needs checking |Deferred; “gold” label is not proof of unbiased annotation |
| [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast/tree/1231850a0bf1a0c0341fe408ef1668dbbfdfac46) |Browser agent/demo, dynamic action choices; no static uniquely correct action dataset |Not suitable for this static benchmark without an interactive environment protocol |
| [Negation minimal pairs](https://github.com/mahartmann/negationminpairs/tree/1defc22b5d26be434c1ba265a0ef149abe4febad) |Potentially useful English/Chinese XNLI-derived diagnostic; no repository LICENSE verified |Deferred; do not assume redistribution rights |
| [ToxicChat](https://huggingface.co/datasets/lmsys/toxic-chat) |5,083 test rows,2,853 human-annotated and2,230 not human; CC BY-NC4.0 |Useful later with explicit annotation stratum; Aegis human-prompt track selected for v0.1 |
| [CLUE](https://huggingface.co/datasets/clue/clue) |TNEWS test labels all-1; labeled validation10,000/15 classes, IFLYTEK validation2,599/119. Source rights unclear |No fabricated test gold; Chinese covered by XNLI/MASSIVE in v0.1 |
| [CrossWOZ](https://github.com/thu-coai/CrossWOZ) |Chinese human dialogs, Apache2.0, meaningful multi-turn decisions |Promising future extension, requires dialog state/action and multi-label protocol |
| [WildGuardMix](https://huggingface.co/datasets/allenai/wildguardmix) |Gated access; prompt vs response labels serve different tasks |Deferred |
| [Do-Not-Answer](https://huggingface.co/datasets/LibrAI/do-not-answer) |Card/repository code and data licensing differ |Deferred pending exact terms and scoring adaptation |

## What the release does not establish

No Jev API was called. No new labels were created from Laya output. No prompts,
sample choices, confidence thresholds or checkpoint choices were tuned using
these new test predictions. No claim of annotation perfection, training-set
decontamination, independent third-party certification, production guardrail
safety, or general agent decision accuracy is supported by this release.
