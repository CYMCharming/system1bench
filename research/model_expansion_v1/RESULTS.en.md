# Five-model expansion: measured results

Five new, pinned official checkpoints; 4,905 decisions each (24,525 total). Three reference tracks remain separate.
These results describe direct/native decision inference, not a reasoning ceiling or a causal architecture comparison.
NanoJev is the unified-games checkpoint; Kev sizes have different training histories. All intervals are pointwise paired/clustered descriptive 95% intervals.

## Base source/reference accuracy

| Model | Refund action (96) | Access action (96) | Routing action (96) | Legal (144) | Science (339) |
|---|---:|---:|---:|---:|---:|---:|
| Kev-0.8B | 56.2% | 66.7% | 76.0% | 48.6% | 49.6% |
| Kev-4B | 87.5% | 96.9% | 81.2% | 66.0% | 80.8% |
| Kev-9B | 100.0% | 99.0% | 70.8% | 70.1% | 80.5% |
| NanoJev (unified games) | 25.0% | 34.4% | 25.0% | 31.9% | 37.2% |
| Qwen3.5-9B (direct) | 72.9% | 89.6% | 89.6% | 75.7% | 83.5% |

Policy action correctness is executable; legal is source annotation agreement; scientific NOINFO is absence of annotated evidence in the cited abstract, not independently adjudicated neutrality.
No aggregate average across these columns is calculated. Full head-specific scores, class confusions, CI, calibration and risk/coverage are in `summary.json`.

## Stability decomposed: science reversal

| Model | Semantic flips | Correct and stable | Wrong and stable | Exact-repeat flips |
|---|---:|---:|---:|---:|
| Kev-0.8B | 103/339 (30.4%) | 134/339 (39.5%) | 102/339 (30.1%) | 0/339 |
| Kev-4B | 12/339 (3.5%) | 265/339 (78.2%) | 62/339 (18.3%) | 0/339 |
| Kev-9B | 20/339 (5.9%) | 263/339 (77.6%) | 56/339 (16.5%) | 0/339 |
| NanoJev (unified games) | 0/339 (0.0%) | 126/339 (37.2%) | 213/339 (62.8%) | 0/339 |
| Qwen3.5-9B (direct) | 40/339 (11.8%) | 250/339 (73.7%) | 49/339 (14.5%) | 0/339 |

Correct-stable + wrong-stable + changed = all common-valid cases. Stability alone is not semantic correctness.

## Counterfactual action adaptation

| Model | Refund: both correct / changed | Access: both correct / changed | Routing: both correct / changed |
|---|---:|---:|---:|
| Kev-0.8B | 35.4% / 90.6% | 20.8% / 34.4% | 44.8% / 64.6% |
| Kev-4B | 85.4% / 99.0% | 87.5% / 87.5% | 78.1% / 93.8% |
| Kev-9B | 100.0% / 100.0% | 97.9% / 97.9% | 57.3% / 58.3% |
| NanoJev (unified games) | 0.0% / 0.0% | 0.0% / 4.2% | 0.0% / 0.0% |
| Qwen3.5-9B (direct) | 68.8% / 94.8% | 84.4% / 89.6% | 84.4% / 84.4% |

The executable correct action changes in all 96 pairs per policy. A model changing its answer is necessary but not sufficient; both answers must be correct.

## Fixed confidence threshold (p_max ≥ 0.9)

| Model | Legal coverage / observed risk | Science coverage / observed risk |
|---|---:|---:|
| Kev-0.8B | 0.0% / N/A (0 selected) | 8.3% / 10.7% (3/28) |
| Kev-4B | 26.4% / 7.9% (3/38) | 42.5% / 6.2% (9/144) |
| Kev-9B | 33.3% / 10.4% (5/48) | 51.6% / 7.4% (13/175) |
| NanoJev (unified games) | 0.0% / N/A (0 selected) | 0.0% / N/A (0 selected) |
| Qwen3.5-9B (direct) | 54.2% / 7.7% (6/78) | 67.6% / 10.0% (23/229) |

This is observed test risk, NOT a prospective safety guarantee. Qwen probabilities are conditional code likelihoods; Kev applies stored calibration temperatures; NanoJev uses temperature 1. No test-fitted calibration is used.

## Boundaries and reproduction

- All unavailable/error decisions are separate statuses. Paired semantic rates use common-valid pairs; strict accuracy uses all source cases.
- Native rendering and next-token prompts preserve the same supplied information but are not identical token sequences.
- Size comparisons are confounded by training; class-level and source-level reversals do not identify a mechanism.
- These sources were already used in earlier research; this is new-model transfer replication, not fresh held-out data.
- Full-input NanoJev overrides its default context ceiling; the actual training-window slice is recorded. No silent truncation.
- Timing is telemetry, not a controlled speedup benchmark.
- Reconstruct original freezes using their source-pinned preparation scripts and licenses, then run `freeze.py`, `run.py --model NAME`, `analyze.py`, `verify.py`.

The complete prospective protocol is `PROTOCOL.md`; input/model identities are in `manifest.json`; raw outputs and environment/weight/code hashes are under `results/`.
