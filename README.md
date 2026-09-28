# System1Bench: Benchmarking Jev-Style Decision Models

[![Verify benchmark artifacts](https://github.com/CYMCharming/system1bench/actions/workflows/verify.yml/badge.svg)](https://github.com/CYMCharming/system1bench/actions/workflows/verify.yml)

**System 1 决策模型评测基准** · An independent, reproducible evaluation collection
for models that turn a supplied state into typed `choice`, `noul` and `score`
decisions.

**v0.2 includes our real runs of Laya English, Laya Multilingual,
Llama-3.1-8B-Instruct and Qwen3-8B. Jev has not been evaluated.** The framework accepts a model adapter for future Jev runs;
“Jev-style” describes the interface/task category, not a shared architecture.

System1Bench combines 15 public source datasets/collections into 36 suites and
controls. It covers semantic classification, bilingual inference, structured
workflow decisions, explicit out-of-scope intent detection, safety, long-context
retrieval and actual option-order perturbations. Scores stay separate by source
and reference quality. There is no blended “decision intelligence” score.

- [Results and Chinese report](docs/RESULTS.zh-CN.md)
- [数据集中文解读：用途、来源与适用性](docs/DATASETS.zh-CN.md)
- [Protocol and metrics](PROTOCOL.md) · [dataset suitability review](docs/DATASET_REVIEW.md)
- [Machine-readable results](results/summary.json) · [CSV](results/metrics.csv)
- [v0.2 comparison integrity review](docs/BASELINE_AUDIT.md) · [original Laya review](docs/EXPERIMENT_AUDIT.md)
- [LLM comparison protocol](docs/LLM_BASELINES.md) · [local checkpoint verification](docs/LOCAL_CHECKPOINT_VERIFICATION.json)
- [Source pins](sources.json) · [additional source pins](external_sources.json)

<!-- BEGIN GENERATED RESULTS -->
## Measured results — all tasks

**Every score below comes from our own local model runs in this repository. No third-party model scores are copied. Jev has not been evaluated.**

4 checkpoints × 26,450 decisions = **105,800 measured decisions**, including controls. Failures: **0**; complete inputs: **105,800/105,800**.

Laya uses native decision heads. The Llama and Qwen baselines use zero-shot constrained next-token answer selection; Qwen thinking is disabled. See the [exact comparison protocol](docs/LLM_BASELINES.md). These are fixed direct-decision baselines, not best-achievable LLM scores.

Values are accuracy against each source reference. **Teacher/synthetic and authored/AI-reviewed rows measure reference agreement**, not independently human-verified correctness. We publish all suites without an overall blended score. Full confidence intervals, F1, Brier/ECE, ordinal errors, language/length slices and timings are in the [report](docs/RESULTS.zh-CN.md), [CSV](results/metrics.csv) and [JSON](results/summary.json).

### Main tasks (28 suites)

| Task | Decisions / model | Laya English | Laya Multilingual | Llama-3.1-8B-Instruct | Qwen3-8B | Reference |
|---|---:|---:|---:|---:|---:|---:|
| ag_news | 1000 | 94.30% | 92.40% | 88.90% | 86.80% | dataset_provided |
| emotion | 1000 | 59.10% | 53.00% | 50.50% | 54.80% | dataset_provided |
| banking77 | 1000 | 55.30% | 51.20% | 54.10% | 66.80% | dataset_provided |
| boolq | 1000 | 84.60% | 77.70% | 64.80% | 83.50% | dataset_provided |
| boolq_choice | 1000 | 83.60% | 77.40% | 68.70% | 83.30% | dataset_provided |
| sst5 | 1000 | 34.60% | 29.50% | 32.00% | 45.70% | dataset_provided |
| sst5_choice | 1000 | 49.60% | 35.60% | 42.20% | 43.90% | dataset_provided |
| xnli_en | 1000 | 86.00% | 81.70% | 46.20% | 78.70% | dataset_provided |
| xnli_zh | 1000 | 61.50% | 74.30% | 40.50% | 69.10% | dataset_provided |
| massive_en | 1000 | 54.10% | 42.30% | 57.20% | 66.30% | dataset_provided |
| massive_zh | 1000 | 30.40% | 33.20% | 53.50% | 62.60% | dataset_provided |
| prompt_injections | 116 | 70.69% | 57.76% | 62.93% | 63.79% | dataset_provided |
| typed_decisions | 2000 | 36.35% | 34.90% | 51.20% | 55.50% | synthetic_teacher |
| jevbench_original | 72 | 70.83% | 41.67% | 75.00% | 83.33% | authored_or_AI_reviewed |
| jevbench_easy | 48 | 95.83% | 89.58% | 100.00% | 100.00% | authored_or_AI_reviewed |
| jevbench_hard | 111 | 29.73% | 32.43% | 34.23% | 46.85% | authored_or_AI_reviewed |
| reflexbench_reflex-public-choice-v1 | 95 | 58.95% | 46.32% | 60.00% | 84.21% | authored_or_AI_reviewed |
| jev_laya_triage | 501 | 62.48% | 55.69% | 75.65% | 80.04% | synthetic_teacher |
| jev_laya_moderation | 426 | 67.84% | 48.36% | 88.97% | 77.46% | synthetic_teacher |
| jev_laya_routing | 411 | 64.23% | 51.09% | 61.31% | 83.70% | synthetic_teacher |
| jev_laya_claims | 300 | 90.00% | 80.00% | 61.67% | 98.67% | synthetic_teacher |
| jev_laya_reviews | 300 | 70.67% | 42.33% | 83.00% | 87.00% | synthetic_teacher |
| jev_laya_guard | 292 | 60.62% | 33.22% | 88.01% | 83.22% | synthetic_teacher |
| jev_laya_multilingual | 256 | 57.81% | 62.50% | 94.53% | 98.44% | synthetic_teacher |
| jev_laya_needle | 900 | 50.22% | 47.44% | 77.89% | 87.78% | programmatic |
| clinc150_oos | 5500 | 55.73% | 64.76% | 55.20% | 67.78% | dataset_provided |
| turtlebench | 1532 | 42.62% | 41.64% | 42.17% | 44.19% | dataset_provided |
| aegis2_prompt | 1928 | 49.59% | 57.05% | 66.80% | 72.67% | human_prompt_annotation |

### Same-order repeats and reversed-option controls (8 suites)

| Task | Decisions / model | Laya English | Laya Multilingual | Llama-3.1-8B-Instruct | Qwen3-8B | Reference |
|---|---:|---:|---:|---:|---:|---:|
| banking77_repeat | 100 | 49.00% | 44.00% | 62.00% | 72.00% | dataset_provided |
| banking77_reversed | 100 | 58.00% | 44.00% | 37.00% | 54.00% | dataset_provided |
| massive_en_repeat | 100 | 54.00% | 50.00% | 62.00% | 74.00% | dataset_provided |
| massive_en_reversed | 100 | 52.00% | 43.00% | 60.00% | 66.00% | dataset_provided |
| jevbench_original_repeat | 36 | 61.11% | 58.33% | 80.56% | 83.33% | authored_or_AI_reviewed |
| jevbench_original_reversed | 36 | 58.33% | 55.56% | 66.67% | 86.11% | authored_or_AI_reviewed |
| reflexbench_reflex-public-choice-v1_repeat | 95 | 58.95% | 46.32% | 60.00% | 84.21% | authored_or_AI_reviewed |
| reflexbench_reflex-public-choice-v1_reversed | 95 | 58.95% | 45.26% | 57.89% | 82.11% | authored_or_AI_reviewed |

### Option-order agreement

Agreement compares predictions on the same inputs; it is not accuracy. The LLM reversal also reassigns answer codes.

| Model / task | N | Original → repeat | Repeat → reversed |
|---|---:|---:|---:|
| Laya English / banking77 | 100 | 100.00% | 52.00% |
| Laya English / massive_en | 100 | 100.00% | 50.00% |
| Laya English / jevbench_original | 36 | 100.00% | 91.67% |
| Laya English / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 89.47% |
| Laya Multilingual / banking77 | 100 | 100.00% | 62.00% |
| Laya Multilingual / massive_en | 100 | 100.00% | 54.00% |
| Laya Multilingual / jevbench_original | 36 | 100.00% | 77.78% |
| Laya Multilingual / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 80.00% |
| Llama-3.1-8B-Instruct / banking77 | 100 | 96.00% | 35.00% |
| Llama-3.1-8B-Instruct / massive_en | 100 | 95.00% | 49.00% |
| Llama-3.1-8B-Instruct / jevbench_original | 36 | 100.00% | 77.78% |
| Llama-3.1-8B-Instruct / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 82.11% |
| Qwen3-8B / banking77 | 100 | 99.00% | 61.00% |
| Qwen3-8B / massive_en | 100 | 100.00% | 68.00% |
| Qwen3-8B / jevbench_original | 36 | 100.00% | 86.11% |
| Qwen3-8B / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 85.26% |

### Explicit out-of-scope detection (CLINC150 + OOS)

| Model | In-scope accuracy | OOS precision | OOS recall | OOS F1 |
|---|---:|---:|---:|---:|
| Laya English | 49.11% | 38.44% | 85.50% | 0.5304 |
| Laya Multilingual | 74.42% | 86.59% | 21.30% | 0.3419 |
| Llama-3.1-8B-Instruct | 52.51% | 41.91% | 67.30% | 0.5165 |
| Qwen3-8B | 65.93% | 57.52% | 76.10% | 0.6552 |

### Ordinal scoring (SST5, fixed 0–4 scale)

Lower MAE is better; within-one agreement allows an error of one scale point.

| Model | Argmax MAE ↓ | Expected-score MAE ↓ | Within one ↑ |
|---|---:|---:|---:|
| Laya English | 0.9270 | 0.9144 | 77.80% |
| Laya Multilingual | 1.3000 | 1.2946 | 58.70% |
| Llama-3.1-8B-Instruct | 1.0350 | 0.9999 | 71.30% |
| Qwen3-8B | 0.6560 | 0.6482 | 90.80% |

<!-- END GENERATED RESULTS -->

## Run provenance

The original Laya measurements are retained from v0.1. The two LLM runs are
new in v0.2; no prior result is relabeled as a new run. Every model has
per-suite compressed raw predictions and a completed-run manifest:
[Laya English](results/english/metadata.json),
[Laya Multilingual](results/multilingual/metadata.json),
[Llama-3.1-8B-Instruct](results/llama31_8b_instruct/metadata.json),
[Qwen3-8B](results/qwen3_8b/metadata.json).

## Reproduce

Python 3.11+ and a CUDA GPU are required for the Laya runs. The reference run used
Python 3.12, PyTorch 2.7.1+cu118, Transformers 5.16.1 and Laya 0.3.20. Laya source
hashes and model byte hashes appear in each model's metadata. A shared environment with
incompatible PyTorch/Transformers versions may need a fresh virtual environment.

```bash
git clone https://github.com/CYMCharming/system1bench.git
cd system1bench
python -m venv .venv
source .venv/bin/activate
pip install -e '.[laya]'
python -m system1bench.download
python -m system1bench.prepare
CUDA_VISIBLE_DEVICES=0 python -m system1bench.run --model english --output my-results
CUDA_VISIBLE_DEVICES=0 python -m system1bench.run --model multilingual --output my-results
python -m system1bench.metrics --results my-results
python -m system1bench.report --results my-results
```

Downloads use immutable revisions and verify SHA256. Standard source data are
stored locally under `data/`; they are not covered by this repository's license.
The checked-in `results/` are the published runs. Use a new output directory for
a different environment, checkpoint, code or batch size. Interrupted suites are
rerun atomically; completed suites must match input/configuration fingerprints.

To verify/recompute the published numbers without downloading data or a model:

```bash
pip install -e .
python -m unittest discover -s tests -v
python -m system1bench.metrics
python -m system1bench.report
```

The compressed per-suite results contain source IDs, gold labels, raw answers,
probabilities, request hashes, token audits and per-batch timing. They omit
original text and rationale annotations. A reader can reconstruct requests from
pinned sources and recompute all published metrics independently.

Llama/Qwen reproduction, prompt conversion and probability semantics are documented in
[LLM_BASELINES.md](docs/LLM_BASELINES.md). These local baselines use the exact same frozen inputs.

## Add Jev or another model

Implement the adapter contract in [ADAPTERS.md](docs/ADAPTERS.md), then use
`--adapter your_package.module:Adapter --model your_model_name`. The runner passes
only state and questions; source references are separate. Keep native raw answers
and declare model/version, prompt conversion, probability semantics and input
budget limitations. No Jev credentials, paid API calls, mocked leaderboard runs
or copied third-party model scores are included.

## Interpretation

Classification accuracy is a component measure, not end-to-end agent success.
Several workflow references are synthetic/teacher labels; their scores measure
agreement. Public data may overlap model training, and AG News/BoolQ are known
training-task families for Laya. Chinese states mostly use English instructions.

Laya runs use an 8,192-token maximum and 4,096-token prompt-head budget, but
Laya internally caps each candidate description at 48 tokens. Read the actual
truncation audits and the **shared complete-input subset** before comparing
checkpoints. A larger configured budget alone does not prove full input retention.

## Citation

```bibtex
@misc{system1bench2026,
  author = {CYMCharming},
  title = {System1Bench: Benchmarking Jev-Style Decision Models},
  year = {2026},
  howpublished = {\url{https://github.com/CYMCharming/system1bench}},
  note = {Version 0.2; cite the commit and original datasets for reproducibility}
}
```

Code: MIT. External data/models retain their original terms; see [NOTICE.md](NOTICE.md).
