# Fresh executable-policy diagnostic

These are actual evaluations on a diagnostic frozen before inference. Each of the three policy families contains 96 unique base states, with three generator seeds and eight matched variants. Every model answers 6,912 decisions; each LLM also answers 1,440 codebook-control decisions. The curated policies test explicit rule composition, not real business outcome utility.

## Original states and one-field counterfactuals

Percent reference accuracy; joint means both the original and counterfactual action are correct. Each row uses 96 paired base-state clusters. Majority is the observed original action-label majority baseline.

| Policy | Model | Action | Review | Severity | Majority | Joint action |
|---|---|---:|---:|---:|---:|---:|
| Access | Laya EN | 34.4 | 44.8 | 43.8 | 34.4 | 2.1 |
| Access | Laya Multi | 29.2 | 40.6 | 29.2 | 34.4 | 0.0 |
| Access | Llama 8B | 34.4 | 40.6 | 68.8 | 34.4 | 0.0 |
| Access | Qwen 8B | 66.7 | 53.1 | 79.2 | 34.4 | 46.9 |
| Access | Jev 1.13 | 100.0 | 89.6 | 95.8 | 34.4 | 100.0 |
| Refund | Laya EN | 25.0 | 77.1 | 31.2 | 25.0 | 0.0 |
| Refund | Laya Multi | 25.0 | 74.0 | 31.2 | 25.0 | 0.0 |
| Refund | Llama 8B | 33.3 | 74.0 | 59.4 | 25.0 | 0.0 |
| Refund | Qwen 8B | 25.0 | 74.0 | 43.8 | 25.0 | 1.0 |
| Refund | Jev 1.13 | 100.0 | 100.0 | 100.0 | 25.0 | 100.0 |
| Routing | Laya EN | 71.9 | 69.8 | 35.4 | 25.0 | 28.1 |
| Routing | Laya Multi | 24.0 | 63.5 | 33.3 | 25.0 | 0.0 |
| Routing | Llama 8B | 25.0 | 63.5 | 59.4 | 25.0 | 0.0 |
| Routing | Qwen 8B | 49.0 | 64.6 | 79.2 | 25.0 | 28.1 |
| Routing | Jev 1.13 | 54.2 | 100.0 | 95.8 | 25.0 | 29.2 |

## All predeclared paired effects

Units are percentage points. Intervals are simultaneous 95% max-standardized-deviation bootstrap intervals across six effects within each model/policy family, stratified by the three generator seeds, with 10,000 resamples. They do not cover all models/families jointly. A zero-variance flag means the empirical bootstrap is degenerate, not that population invariance is established.

| Policy | Model | Effect | Estimate | Simultaneous 95% CI | Zero variance |
|---|---|---|---:|---|---|
| policy_access | Laya EN | reversal_excess_action_discordance | +26.0 | [+15.1, +36.9] | False |
| policy_access | Laya EN | chinese_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Laya EN | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Laya EN | paraphrase_action_accuracy | +6.2 | [-4.2, +16.7] | False |
| policy_access | Laya EN | choice_encoded_review_accuracy | -6.2 | [-19.6, +7.1] | False |
| policy_access | Laya EN | choice_encoded_severity_accuracy | -3.1 | [-18.1, +11.8] | False |
| policy_access | Laya Multi | reversal_excess_action_discordance | +49.0 | [+36.3, +61.6] | False |
| policy_access | Laya Multi | chinese_action_accuracy | +3.1 | [-15.8, +22.0] | False |
| policy_access | Laya Multi | distractor_action_accuracy | +8.3 | [-10.3, +27.0] | False |
| policy_access | Laya Multi | paraphrase_action_accuracy | +3.1 | [-10.4, +16.7] | False |
| policy_access | Laya Multi | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Laya Multi | choice_encoded_severity_accuracy | +24.0 | [+8.8, +39.2] | False |
| policy_access | Llama 8B | reversal_excess_action_discordance | +0.0 | [+0.0, +0.0] | True |
| policy_access | Llama 8B | chinese_action_accuracy | +2.1 | [-1.7, +5.8] | False |
| policy_access | Llama 8B | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Llama 8B | paraphrase_action_accuracy | +11.5 | [+3.1, +19.8] | False |
| policy_access | Llama 8B | choice_encoded_review_accuracy | +1.0 | [-1.6, +3.7] | False |
| policy_access | Llama 8B | choice_encoded_severity_accuracy | -9.4 | [-21.6, +2.8] | False |
| policy_access | Qwen 8B | reversal_excess_action_discordance | +29.2 | [+17.4, +41.0] | False |
| policy_access | Qwen 8B | chinese_action_accuracy | +7.3 | [-5.3, +19.8] | False |
| policy_access | Qwen 8B | distractor_action_accuracy | -14.6 | [-26.3, -2.9] | False |
| policy_access | Qwen 8B | paraphrase_action_accuracy | +5.2 | [-1.3, +11.7] | False |
| policy_access | Qwen 8B | choice_encoded_review_accuracy | -6.2 | [-12.5, +0.0] | False |
| policy_access | Qwen 8B | choice_encoded_severity_accuracy | +0.0 | [-5.2, +5.2] | False |
| policy_access | Jev 1.13 | reversal_excess_action_discordance | +0.0 | [+0.0, +0.0] | True |
| policy_access | Jev 1.13 | chinese_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Jev 1.13 | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Jev 1.13 | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_access | Jev 1.13 | choice_encoded_review_accuracy | -1.0 | [-6.2, +4.2] | False |
| policy_access | Jev 1.13 | choice_encoded_severity_accuracy | +2.1 | [-1.2, +5.4] | False |
| policy_refund | Laya EN | reversal_excess_action_discordance | +10.4 | [+3.3, +17.5] | False |
| policy_refund | Laya EN | chinese_action_accuracy | +4.2 | [-0.6, +8.9] | False |
| policy_refund | Laya EN | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya EN | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya EN | choice_encoded_review_accuracy | -3.1 | [-7.3, +1.0] | False |
| policy_refund | Laya EN | choice_encoded_severity_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya Multi | reversal_excess_action_discordance | +100.0 | [+100.0, +100.0] | True |
| policy_refund | Laya Multi | chinese_action_accuracy | +0.0 | [-4.5, +4.5] | False |
| policy_refund | Laya Multi | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya Multi | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya Multi | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Laya Multi | choice_encoded_severity_accuracy | +16.7 | [+3.1, +30.2] | False |
| policy_refund | Llama 8B | reversal_excess_action_discordance | +88.5 | [+80.8, +96.3] | False |
| policy_refund | Llama 8B | chinese_action_accuracy | +10.4 | [-2.1, +22.9] | False |
| policy_refund | Llama 8B | distractor_action_accuracy | -7.3 | [-13.6, -0.9] | False |
| policy_refund | Llama 8B | paraphrase_action_accuracy | -8.3 | [-15.1, -1.6] | False |
| policy_refund | Llama 8B | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Llama 8B | choice_encoded_severity_accuracy | +0.0 | [-9.9, +9.9] | False |
| policy_refund | Qwen 8B | reversal_excess_action_discordance | +27.1 | [+16.7, +37.5] | False |
| policy_refund | Qwen 8B | chinese_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Qwen 8B | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Qwen 8B | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Qwen 8B | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Qwen 8B | choice_encoded_severity_accuracy | +5.2 | [-0.0, +10.4] | False |
| policy_refund | Jev 1.13 | reversal_excess_action_discordance | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Jev 1.13 | chinese_action_accuracy | -1.0 | [-3.1, +1.0] | False |
| policy_refund | Jev 1.13 | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Jev 1.13 | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Jev 1.13 | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_refund | Jev 1.13 | choice_encoded_severity_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Laya EN | reversal_excess_action_discordance | +24.0 | [+13.0, +34.9] | False |
| policy_routing | Laya EN | chinese_action_accuracy | -16.7 | [-29.8, -3.6] | False |
| policy_routing | Laya EN | distractor_action_accuracy | -46.9 | [-69.1, -24.6] | False |
| policy_routing | Laya EN | paraphrase_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Laya EN | choice_encoded_review_accuracy | -4.2 | [-10.4, +2.1] | False |
| policy_routing | Laya EN | choice_encoded_severity_accuracy | +0.0 | [-12.1, +12.1] | False |
| policy_routing | Laya Multi | reversal_excess_action_discordance | +1.0 | [-1.4, +3.5] | False |
| policy_routing | Laya Multi | chinese_action_accuracy | -2.1 | [-7.0, +2.9] | False |
| policy_routing | Laya Multi | distractor_action_accuracy | +1.0 | [-1.4, +3.5] | False |
| policy_routing | Laya Multi | paraphrase_action_accuracy | +1.0 | [-1.4, +3.5] | False |
| policy_routing | Laya Multi | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Laya Multi | choice_encoded_severity_accuracy | +21.9 | [+2.1, +41.7] | False |
| policy_routing | Llama 8B | reversal_excess_action_discordance | +5.2 | [-0.4, +10.8] | False |
| policy_routing | Llama 8B | chinese_action_accuracy | +5.2 | [-0.2, +10.7] | False |
| policy_routing | Llama 8B | distractor_action_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Llama 8B | paraphrase_action_accuracy | +9.4 | [+2.1, +16.7] | False |
| policy_routing | Llama 8B | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Llama 8B | choice_encoded_severity_accuracy | +0.0 | [-5.0, +5.0] | False |
| policy_routing | Qwen 8B | reversal_excess_action_discordance | +14.6 | [+5.2, +24.0] | False |
| policy_routing | Qwen 8B | chinese_action_accuracy | +7.3 | [+0.6, +14.0] | False |
| policy_routing | Qwen 8B | distractor_action_accuracy | -8.3 | [-15.3, -1.3] | False |
| policy_routing | Qwen 8B | paraphrase_action_accuracy | +6.2 | [-0.0, +12.5] | False |
| policy_routing | Qwen 8B | choice_encoded_review_accuracy | +0.0 | [+0.0, +0.0] | True |
| policy_routing | Qwen 8B | choice_encoded_severity_accuracy | -1.0 | [-3.7, +1.6] | False |
| policy_routing | Jev 1.13 | reversal_excess_action_discordance | +2.1 | [-3.8, +8.0] | False |
| policy_routing | Jev 1.13 | chinese_action_accuracy | +45.8 | [+31.4, +60.2] | False |
| policy_routing | Jev 1.13 | distractor_action_accuracy | -6.2 | [-13.2, +0.7] | False |
| policy_routing | Jev 1.13 | paraphrase_action_accuracy | -2.1 | [-6.2, +2.1] | False |
| policy_routing | Jev 1.13 | choice_encoded_review_accuracy | -1.0 | [-4.0, +1.9] | False |
| policy_routing | Jev 1.13 | choice_encoded_severity_accuracy | +1.0 | [-4.1, +6.2] | False |

## Orthogonal LLM codebook controls

The baseline prompt matches the ordinary adapter. Display changes preserve semantic code mapping; code changes preserve semantic display order; both reproduces ordinary reversal. These comparisons use a separate inference block. Intervals below are pointwise paired cluster intervals, not the primary simultaneous family.

| Policy | Model | Intervention | Prediction flips | 95% CI | Accuracy change (pp) |
|---|---|---|---:|---|---:|
| policy_refund | Llama 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_refund | Llama 8B | position_only | 100.0 | [100.0, 100.0] | -8.3 |
| policy_refund | Llama 8B | code_only | 85.4 | [78.1, 91.7] | -8.3 |
| policy_refund | Llama 8B | both | 82.3 | [74.0, 89.6] | -7.3 |
| policy_access | Llama 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_access | Llama 8B | position_only | 0.0 | [0.0, 0.0] | +0.0 |
| policy_access | Llama 8B | code_only | 55.2 | [44.8, 64.6] | +29.2 |
| policy_access | Llama 8B | both | 0.0 | [0.0, 0.0] | +0.0 |
| policy_routing | Llama 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_routing | Llama 8B | position_only | 0.0 | [0.0, 0.0] | +0.0 |
| policy_routing | Llama 8B | code_only | 62.5 | [53.1, 71.9] | +8.3 |
| policy_routing | Llama 8B | both | 3.1 | [0.0, 7.3] | +3.1 |
| policy_refund | Qwen 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_refund | Qwen 8B | position_only | 71.9 | [62.5, 80.2] | +42.7 |
| policy_refund | Qwen 8B | code_only | 17.7 | [10.4, 26.0] | +13.5 |
| policy_refund | Qwen 8B | both | 27.1 | [18.8, 36.5] | +21.9 |
| policy_access | Qwen 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_access | Qwen 8B | position_only | 36.5 | [27.1, 46.9] | +19.8 |
| policy_access | Qwen 8B | code_only | 15.6 | [8.3, 22.9] | -5.2 |
| policy_access | Qwen 8B | both | 30.2 | [20.8, 39.6] | -14.6 |
| policy_routing | Qwen 8B | repeat | 0.0 | [0.0, 0.0] | +0.0 |
| policy_routing | Qwen 8B | position_only | 21.9 | [13.5, 30.2] | +19.8 |
| policy_routing | Qwen 8B | code_only | 12.5 | [6.2, 19.8] | -11.5 |
| policy_routing | Qwen 8B | both | 14.6 | [8.3, 21.9] | -7.3 |

The original, repeat, reversal, Chinese, distractor, paraphrase, choice-encoded and counterfactual results for every output primitive, including failure counts, per-seed effects and paired vectors, are retained in [summary.json](confirmation_v1/summary.json).

Execution deviation: one Jev refund Chinese request returned HTTP 520. The frozen runner retries selected 5xx codes, whereas the protocol stated 5xx generally; this status received one attempt. Its three decisions remain incorrect in primary results. Refund Chinese-minus-original action correctness is -1/96 (-1.04 pp); the valid-pair sensitivity is 0/95 (0 pp), conditional on a successful response. This is not evidence of a language regression. See [the execution log](JEV_RUN_LOG.md).

Protocol and scope: [PROTOCOL.md](confirmation_v1/PROTOCOL.md). Chinese text was authored and has not received independent bilingual human adjudication. Performance is specific to the evaluated adapter; these experiments do not isolate neural architecture.
