# System1Bench: Benchmarking Jev-Style Decision Models

[![Verify benchmark artifacts](https://github.com/CYMCharming/system1bench/actions/workflows/verify.yml/badge.svg)](https://github.com/CYMCharming/system1bench/actions/workflows/verify.yml)

**System 1 决策模型评测基准** · An independent, reproducible evaluation collection
for models that turn a supplied state into typed `choice`, `noul` and `score`
decisions.

**v0.1 includes real runs of Laya English and Laya Multilingual. Jev has not
been evaluated.** The framework accepts a model adapter for future Jev runs;
“Jev-style” describes the interface/task category, not a shared architecture.

System1Bench combines 15 public source datasets/collections into 36 suites and
controls. It covers semantic classification, bilingual inference, structured
workflow decisions, explicit out-of-scope intent detection, safety, long-context
retrieval and actual option-order perturbations. Scores stay separate by source
and reference quality. There is no blended “decision intelligence” score.

- [Results and Chinese report](docs/RESULTS.zh-CN.md)
- [Protocol and metrics](PROTOCOL.md) · [dataset suitability review](docs/DATASET_REVIEW.md)
- [Machine-readable results](results/summary.json) · [CSV](results/metrics.csv)
- [Integrity review](docs/EXPERIMENT_AUDIT.md)
- [Source pins](sources.json) · [additional source pins](external_sources.json)

## Initial Laya results

45,868 requests / 52,900 decisions across both checkpoints, zero inference
failures. Actual encoding audits found no state, instruction or candidate
truncation in these runs. Selected tasks (all other results are also published):

| Task | Decisions / model | Laya English | Laya Multilingual |
|---|---:|---:|---:|
| AG News |1,000|94.30%|92.40%|
| XNLI Chinese |1,000|61.50%|74.30%|
| CLINC150 + explicit OOS |5,500|55.73%|64.76%|
| JevBench public hard |111|29.73%|32.43%|
| LocalLLaMA typed-decisions |2,000|36.35%|34.90%|

JevBench hard is authored/AI-reviewed and LocalLLaMA is teacher-referenced:
those percentages are reference agreement, not verified human decision quality.
Read the full report for confidence intervals, baselines, OOS trade-offs and
option-order sensitivity; these rows are not a combined leaderboard.

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

## Add Jev or another model

Implement the adapter contract in [ADAPTERS.md](docs/ADAPTERS.md), then use
`--adapter your_package.module:Adapter --model your_model_name`. The runner passes
only state and questions; source references are separate. Keep native raw answers
and declare model/version, prompt conversion, probability semantics and input
budget limitations. No Jev credentials, paid API calls, mocked leaderboard runs
or copied third-party Jev scores are included in v0.1.

## Interpretation

Classification accuracy is a component measure, not end-to-end agent success.
Several workflow references are synthetic/teacher labels; their scores measure
agreement. Public data may overlap model training, and AG News/BoolQ are known
training-task families for Laya. Chinese states mostly use English instructions.

The new runs use an 8,192-token maximum and 4,096-token prompt-head budget, but
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
  note = {Version 0.1; cite the commit and original datasets for reproducibility}
}
```

Code: MIT. External data/models retain their original terms; see [NOTICE.md](NOTICE.md).
