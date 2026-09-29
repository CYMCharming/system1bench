# System1Bench research artifacts

This snapshot distinguishes three evidence classes:

- **Historical exploratory analysis:** five systems on the same 36 task/control suites, with all 280 pairwise model/main-suite contrasts retained. See [insights](INSIGHTS.en.md) and [taxonomy](task_taxonomy.json).
- **Pre-inference-frozen policy diagnostic:** 288 generated base states, eight matched variants and three primitives, plus orthogonal LLM display/code controls. See [protocol](confirmation_v1/PROTOCOL.md), [results](CONFIRMATION_RESULTS.en.md), [inputs](confirmation_v1/frozen.json) and [manifest](confirmation_v1/manifest.json).
- **Post-hoc localization:** [routing boolean slices and all model/condition confusion counts](POSTHOC_DIAGNOSTICS.en.md). These observations motivate future held-out experiments; they are not independent confirmation.

Original raw artifacts are retained, including invalid hosted replies. The [execution log](JEV_RUN_LOG.md) records protocol deviations and conditional sensitivity analyses. No blended leaderboard score is defined. Human construct/bilingual validation has not been performed; same-family automated reviews are provisional.

## Reproduce from public outputs on CPU

From the repository root, after installing the base package:

```bash
python -m unittest discover -s tests -v
python benchmarks/verify_hosted_outputs.py
python research/analyze.py
python research/analyze_confirmation.py
python research/report_confirmation.py
python research/diagnose_policy.py
python -m system1bench.report
```

The public hosted replay verifies response decoding, failure preservation, usage and input/reference fingerprints against the historical local artifacts. Full client-payload reconstruction additionally requires preparing the historical source data; after preparation, run `python benchmarks/jev_report.py`. Public replay cannot prove what the provider processed internally.

To reproduce the plots, install the `paper` extra and execute the `gen_*.py` scripts in [paper/figures](../paper/figures). They read saved JSON analyses and the controlled performance summary, and emit PDF/SVG/PNG. The working manuscript is currently a local draft; this public snapshot includes the research figures and their source code.

## New inference

The original local checkpoint and adapter configuration is documented in [LLM_BASELINES.md](../docs/LLM_BASELINES.md). New confirmation runs use `benchmarks/confirmation_run.py`; LLM codebook runs use `benchmarks/codebook_control.py`. Check each script's `--help` before choosing devices and output paths. Use new output directories for a changed protocol or model. Never replace the published runs.

Hosted inference uses `benchmarks/jev_api.py` and requires a separate account/credential. The credential is read from an external file; do not put it in source control or command-line arguments. The recorded model version is `jev-1.13.0`; server weights/tokenization are not independently observable. Published client times are not comparable to resident-GPU measurements.

Three data-generator seeds replicate input construction, not model training. All matched conditions share source clusters; counts of variants and output primitives must not be treated as independent sample sizes.
