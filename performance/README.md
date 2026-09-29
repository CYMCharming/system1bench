# Local decision performance measurements

This directory is separate from the v0.2 accuracy release. The measured interface
is a resident model's raw-state-to-structured-answer call, including uncached
encoding. It does not generate text tokens or measure a network serving system.

- [Protocol](../docs/PERFORMANCE_PROTOCOL.md): sampling, controls, timing boundary,
  metrics and limits, frozen before official measurements.
- `v1/manifest.json`: exact requests and disjoint warm-up IDs, input fingerprints,
  batch sizes, rounds, order and recorded premeasurement amendment.
- `v1/run_contract.json`: measured code, hardware, software and control settings.
- `v1/raw/roundXX/MODEL/`: synchronized batch times, answers, input audits,
  per-block metadata and external telemetry.
- `v1/summary.json` and `v1/metrics.csv`: validated aggregate statistics.
- [Results](../docs/PERFORMANCE_RESULTS.en.md): human-readable tables generated
  from those records. No pilot or synthetic unit-test records enter these tables.

After obtaining the repository and installing its CPU dependencies, verify the
published performance artifacts without a GPU:

```bash
python -m unittest tests.test_performance -v
python benchmarks/performance_report.py --root performance/v1
```

New inference measurements additionally require the declared model dependencies,
frozen inputs and local checkpoints. Reproduction on another machine must record
its own hardware/software contract and preserve the published experiment.

`methodology_sources.json` records the primary references used to design this
experiment. Their official benchmark requirements are not claimed to be met.

## Instrumentation inventory

| File | Change | Purpose |
|---|---|---|
| `benchmarks/performance.py` | New wrapper | Freeze request selection; synchronize and time the existing adapters; preserve every measured answer and batch |
| `benchmarks/performance_contract.py` | New control | Freeze and enforce measured code, device, software and CPU configuration |
| `benchmarks/performance_telemetry.py` | New observer | Record GPU/CPU/SMT state on a separate CPU core; reject detected sustained contention |
| `benchmarks/performance_report.py` | New analysis | Verify complete raw matrices and references, compute round statistics and intervals, generate tables |
| `tests/test_performance.py` | New regression tests | Verify timing, failure handling, counting, CPU accounting and full-matrix analysis |
| `.github/workflows/verify.yml` | Extended verification | Replay performance reporting from published artifacts without a GPU |
| `performance/v1/` | New experiment artifacts | Bind requests/configuration and retain raw evidence plus derived summaries |
| `benchmarks/environment_witness.py` | New preflight | Exercise the declared device and both candidate-code tokenizers |
| `.gitignore` | Extended exclusions | Keep transient observer status/phase files and empty runtime logs local |
| `README.md` | Generated section | Show all measured workloads and checkpoints with round intervals |
| `docs/PERFORMANCE_PROTOCOL.md` | New protocol | Declare sampling, controls, estimands and limits before timing |
| `docs/PERFORMANCE_RESULTS.en.md` | Generated report | Present measured latency, throughput, quality and hardware evidence |
| `docs/PERFORMANCE_AUDIT.md` | New review record | Record the final artifact/claim review and its independence limits |
| `performance/README.md`, `performance/EXPERIMENT_LOG.md`, `performance/methodology_sources.json` | New documentation | Inventory reproduction commands, interventions and primary-method sources |

## Environment preflight

The full measured versions and numerical backend flags are in
`v1/run_contract.json`. The original environment also passed a seeded BF16 CUDA
matrix product and verified all 151 candidate codes independently in each LLM
tokenizer. The portable version of that preflight is
`benchmarks/environment_witness.py` (new helper; no timing instrumentation).
Activate the Python environment containing the recorded dependencies first;
`python` must resolve to that environment. After providing the local checkpoint
mapping, run it on a free GPU **before** measurement, with no benchmark worker on
that device:

```bash
CUDA_VISIBLE_DEVICES=2 OMP_NUM_THREADS=4 python benchmarks/environment_witness.py --paths .aris/compute/performance_paths.json
```

The mapping file is deliberately local: `english` and `multilingual` point to the
pinned Laya snapshot root; `llama31_8b_instruct` and `qwen3_8b` point to their local
checkpoint directories. Substitute your own mapping path and free physical GPU.
On the recorded A100 environment, the witness shape was `[32, 32]`, sum
`198.2127685546875`, and each tokenizer had 151 distinct single-token codes.
Successful import alone is not treated as environment validation.
