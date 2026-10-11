# All-model common-suite ranking, v1

Defined on 2026-10-09 at the user's request. This is an additional ranking of
the existing 23-model cohort, not a replacement for the eight-domain ranking.
It removes both official full intent tasks: CLINC150 + OOS and BANKING77.
No new inference, test selection, score fitting, or model-specific task removal
is performed. All 23 models are compared on exactly the same nine tasks.

## Tasks and aggregation

| Domain | Classification tasks | Original examples |
| --- | --- | ---: |
| Policy | Refund / access / routing | 96 / 96 / 96 |
| Legal | ContractNLI | 144 |
| Science | SciFact | 339 |
| Causal | CLadder | 144 |
| Code | CRUXEval | 128 |
| Finance | FinEntity | 128 |
| Tools | When2Call | 128 |

Only original-option classification accuracy is aggregated. Policy is the
arithmetic mean of its three task accuracies. The default domain-equal score
is the mean of policy, legal, science, causal, code, finance, and tools: each
domain has weight 1/7. The alternative task-equal score is the mean of the
nine task accuracies: each task has weight 1/9. All inputs are recomputed from
integer correct/total counts and checked against the published accuracies.

There are 1,299 original examples per model. This count is not the denominator
of either weighted composite. Missing results are never imputed or averaged
away; all nine tasks must be complete. Failed predictions retain the fixed
task denominator and count as incorrect, consistently with existing results.
Option permutations, counterfactual variants, joint-field metrics, binary
CLINC, full intent, intent pilots, probability diagnostics, and latency do
not contribute. Neither composite currently has an independently established
confidence interval; historical composite intervals must not be reused.

## Evidence and reproducibility

`analyze.py` reads the existing main-panel scores, the two transfer summaries,
and the completion record. Completion-record transfer additions override
earlier entries for the same model. Jev's transfer ID `jev` is joined only to
the pinned main-panel ID `jev-1.13.0`. Every required task must be marked
completed in the existing coverage record. The original frozen subsets,
candidate sets, checkpoints, inference adapters, and error accounting are
unchanged. SHA-256 receipts bind all source artifacts, this protocol, and the
calculation code. `python research/common_suite_v1/analyze.py --check` verifies
the JSON and CSV exports without modifying them.

For the 17 models in the eight-domain ranking, the nine shared task counts
must exactly match its published counts. The six previously excluded models
(StartLux 4B/9B/27B and Intern 0.8B/2B/4B) are now eligible because no shared
task exceeds their candidate limit. This does not make them eligible for the
separate full 151/77-choice intent tests.

## Interpretation limits

Historical datasets use their published frozen subsets, not necessarily every
example in the original datasets. Laya's completed transfer results use the
documented full-option-text adaptation, not an unmodified native interface;
weights and candidates are unchanged. StartLux declares ContractNLI training
exposure, so its legal score is not evidence of purely unseen-domain transfer.
All other published licensing, source-label, overlap, and training-history
caveats remain applicable. Rankings are descriptive under this fixed suite,
not causal evidence about model architectures. Seven-domain and eight-domain
composites have different task scopes and weights and must never be mixed.
