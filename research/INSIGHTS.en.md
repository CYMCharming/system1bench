# Exploratory paired insights

Computed from frozen public predictions. Pointwise intervals resample source/state clusters, preserving pairs. Historical outcomes were available before this analysis; these are exploratory findings, not preregistered confirmations. All model/source contrasts are retained in `insights.json`.

| Contrast | Model | B − A (percentage points) | 95% paired interval | Cases / clusters |
|---|---|---:|---:|---:|
| BoolQ: choice - noul | Laya EN | -1.00 | [-2.30, +0.30] | 1000 / 1000 |
| SST5: choice - score | Laya EN | +15.00 | [+11.40, +18.60] | 1000 / 1000 |
| XNLI: Chinese - English | Laya EN | -24.50 | [-27.80, -21.20] | 1000 / 1000 |
| MASSIVE: Chinese - English | Laya EN | -23.70 | [-26.80, -20.60] | 1000 / 1000 |
| BoolQ: choice - noul | Laya Multi | -0.30 | [-2.20, +1.50] | 1000 / 1000 |
| SST5: choice - score | Laya Multi | +6.10 | [+2.70, +9.50] | 1000 / 1000 |
| XNLI: Chinese - English | Laya Multi | -7.40 | [-10.40, -4.40] | 1000 / 1000 |
| MASSIVE: Chinese - English | Laya Multi | -9.10 | [-11.80, -6.40] | 1000 / 1000 |
| BoolQ: choice - noul | Llama 3.1 8B | +3.90 | [+2.70, +5.20] | 1000 / 1000 |
| SST5: choice - score | Llama 3.1 8B | +10.20 | [+6.40, +14.00] | 1000 / 1000 |
| XNLI: Chinese - English | Llama 3.1 8B | -5.70 | [-8.10, -3.30] | 1000 / 1000 |
| MASSIVE: Chinese - English | Llama 3.1 8B | -3.70 | [-6.00, -1.40] | 1000 / 1000 |
| BoolQ: choice - noul | Qwen3 8B | -0.20 | [-2.20, +1.80] | 1000 / 1000 |
| SST5: choice - score | Qwen3 8B | -1.80 | [-4.60, +1.00] | 1000 / 1000 |
| XNLI: Chinese - English | Qwen3 8B | -9.60 | [-12.30, -6.90] | 1000 / 1000 |
| MASSIVE: Chinese - English | Qwen3 8B | -3.70 | [-5.80, -1.50] | 1000 / 1000 |
| BoolQ: choice - noul | Jev 1.13 | -0.40 | [-1.00, +0.10] | 1000 / 1000 |
| SST5: choice - score | Jev 1.13 | -0.60 | [-1.90, +0.70] | 1000 / 1000 |
| XNLI: Chinese - English | Jev 1.13 | -12.30 | [-15.00, -9.60] | 1000 / 1000 |
| MASSIVE: Chinese - English | Jev 1.13 | -1.50 | [-3.30, +0.40] | 1000 / 1000 |

## Candidate reversal controls

| Source | Model | Same-order flip % | Reversal flip % | Accuracy change (pp) |
|---|---|---:|---:|---:|
| banking77 | Laya EN | 0.00 | 48.00 | +9.00 |
| massive_en | Laya EN | 0.00 | 50.00 | -2.00 |
| jevbench_original | Laya EN | 0.00 | 8.33 | -2.78 |
| reflexbench_reflex-public-choice-v1 | Laya EN | 0.00 | 10.53 | +0.00 |
| banking77 | Laya Multi | 0.00 | 38.00 | +0.00 |
| massive_en | Laya Multi | 0.00 | 46.00 | -7.00 |
| jevbench_original | Laya Multi | 0.00 | 22.22 | -2.78 |
| reflexbench_reflex-public-choice-v1 | Laya Multi | 0.00 | 20.00 | -1.05 |
| banking77 | Llama 3.1 8B | 4.00 | 65.00 | -25.00 |
| massive_en | Llama 3.1 8B | 5.00 | 51.00 | -2.00 |
| jevbench_original | Llama 3.1 8B | 0.00 | 22.22 | -13.89 |
| reflexbench_reflex-public-choice-v1 | Llama 3.1 8B | 0.00 | 17.89 | -2.11 |
| banking77 | Qwen3 8B | 1.00 | 39.00 | -18.00 |
| massive_en | Qwen3 8B | 0.00 | 32.00 | -8.00 |
| jevbench_original | Qwen3 8B | 0.00 | 13.89 | +2.78 |
| reflexbench_reflex-public-choice-v1 | Qwen3 8B | 0.00 | 14.74 | -2.11 |
| banking77 | Jev 1.13 | 1.00 | 3.00 | +1.00 |
| massive_en | Jev 1.13 | 2.00 | 10.00 | -1.00 |
| jevbench_original | Jev 1.13 | 0.00 | 0.00 | +0.00 |
| reflexbench_reflex-public-choice-v1 | Jev 1.13 | 1.05 | 0.00 | +0.00 |

## Interpretation boundaries

- Output-type changes compare the existing adapters and prompts jointly; they do not isolate a neural decision-head mechanism.
- Language contrasts pair translated task examples while keeping the existing English question templates. They measure this interface, not unrestricted multilingual competence.
- Reversal effects must be interpreted beside same-order repeated controls; original versus repeated requests may differ in execution batch shape.
- Needle curves resample 25 original content units, not 450 supposedly independent variants. Context length is the source target length, not a shared tokenizer length.
- Risk–coverage curves accept all tied probabilities together and use maximum class probability. Their empirical curves are not calibrated deployment thresholds.
- Source/task families are organizational axes. No overall average across incompatible reference types or duplicate interface variants is reported.
- Hosted Jev data, when complete, uses identical requests for accuracy but remains a separate regime for cost and latency.
