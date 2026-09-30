# Prospective new-seed policy replication

Designed after the expansion discovery, before new inference. Kev-4B and Kev-9B each made 3,456 new decisions, with zero overlap of original/counterfactual fact–parameter states with discovery. Same rule grammar, official pins and inference settings; different training histories remain a confound.

## All six primary effects: Kev-9B minus Kev-4B

| Family | Endpoint | 4B correct | 9B correct | Paired difference (pp) | Pointwise 95% CI | Six-effect 99.1667% CI |
|---|---|---:|---:|---:|---|---|
| refund | base_action | 87/96 | 96/96 | +9.4 | [+4.2, +15.6] | [+2.1, +17.7] |
| refund | counterfactual_joint | 82/96 | 96/96 | +14.6 | [+8.3, +21.9] | [+6.2, +25.0] |
| access | base_action | 89/96 | 90/96 | +1.0 | [-5.2, +7.3] | [-7.3, +9.4] |
| access | counterfactual_joint | 79/96 | 89/96 | +10.4 | [+2.1, +19.8] | [-1.0, +22.9] |
| routing | base_action | 75/96 | 64/96 | -11.5 | [-19.8, -3.1] | [-24.0, +0.0] |
| routing | counterfactual_joint | 68/96 | 56/96 | -12.5 | [-21.9, -3.1] | [-26.0, +0.0] |

Paired state-cluster bootstrap: 20,000 draws, seed 20261001. For joint success, BOTH the original and the one-fact-changed action must be correct. All pairs have an executable correct-action change.
The simultaneous guard uses nominal 1 − 0.05/6 percentile intervals (Bonferroni); bootstrap approximation is not an exact familywise coverage guarantee. No architecture/size law follows from these checkpoint comparisons.

Supplementary repeated/reversed inputs, all three primitive heads, confidence and exploratory cross-head label patterns are retained in `summary.json`. Integer numerators, input hashes, state exclusion and two programmatic gold oracles are independently checked by `verify.py`. Public replay excludes licensed natural-language source text; complete host validation is recorded in `verification.json`.
