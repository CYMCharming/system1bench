# Cross-domain error complementarity (exploratory)

This analysis reads the frozen historical raw predictions for five paired systems on all 28 main suites. It verifies 140 raw-result files against their metadata hashes, matches every decision key and common reference/input fields, and reconciles all 140 accuracies against the independent existing `research/insights.json` analysis. A separate stdlib-only validation recomputes point metrics over 25,788 paired decisions and checks all 140 raw-file hashes. It does not combine scores across unlike source collections or reference standards.

## Definitions and boundaries

- **Best single** is the maximum observed suite accuracy among the five systems; its identity is selected on the same sample.
- **Oracle** is the fraction with at least one correct system output. It knows the reference for each decision and is an unattainable selector ceiling, not a learned routing result.
- **Headroom** = oracle − best single. In each bootstrap replicate, the best system is selected anew, so the interval respects that selection operation. It remains descriptive and does not account for benchmark development using these outcomes.
- **Strict-majority coverage** requires at least three identical valid labels among the fixed five outputs. Failed outputs cast no vote and remain in the five-system denominator. **Risk** is the error fraction conditional on coverage; it must be read with the coverage column.
- **Majority yield** is correct majority answers divided by all decisions, with abstentions left unanswered. It is not a matched selective-risk comparison against the always-answering best single system. When majority coverage is 100%, its difference from best single is directly comparable as reference agreement.
- **Intervals** are pointwise 95% percentile intervals from 5,000 bootstrap resamples of source/state clusters within each suite. Repeated questions of one state stay together; e.g. the 900 needle decisions have only 25 content clusters.
- Source collections can generate several suites or alternate interfaces on overlapping states. Those rows are not independent replications. D/H/A/T/P labels denote reference provenance, not interchangeable validity grades.

## Per-suite results

Values are percentages except `n/clusters`. Every row has its own denominator; there is intentionally no overall average.

| Ref | Suite | n/clusters | Best single | Oracle | Headroom (95% CI; pp) | Majority coverage | Majority risk (95% CI) |
|---|---|---:|---:|---:|---:|---:|---:|
| **D · Dataset-provided** | | | | | | | |
| D | `ag_news` | 1000/1000 | 94.3 | 97.6 | 3.3 [2.3, 4.4] | 99.4 | 8.1 [6.5, 9.9] |
| D | `emotion` | 1000/1000 | 59.1 | 78.2 | 19.1 [16.4, 20.7] | 90.3 | 36.2 [33.0, 39.3] |
| D | `banking77` | 1000/1000 | 79.9 | 85.5 | 5.6 [4.2, 7.1] | 81.6 | 17.5 [15.0, 20.2] |
| D | `boolq` | 1000/1000 | 92.6 | 99.0 | 6.4 [5.0, 8.0] | 100.0 | 11.3 [9.4, 13.3] |
| D | `boolq_choice` | 1000/1000 | 92.2 | 98.9 | 6.7 [5.2, 8.3] | 100.0 | 10.5 [8.6, 12.5] |
| D | `sst5` | 1000/1000 | 56.5 | 78.8 | 22.3 [19.8, 24.9] | 72.0 | 44.4 [40.8, 48.2] |
| D | `sst5_choice` | 1000/1000 | 55.9 | 87.3 | 31.4 [28.5, 34.4] | 78.6 | 42.7 [39.3, 46.1] |
| D | `xnli_en` | 1000/1000 | 86.0 | 98.4 | 12.4 [10.2, 13.7] | 97.1 | 10.2 [8.4, 12.1] |
| D | `xnli_zh` | 1000/1000 | 74.3 | 95.5 | 21.2 [18.6, 23.1] | 92.2 | 20.3 [17.8, 22.9] |
| D | `massive_en` | 1000/1000 | 77.5 | 85.7 | 8.2 [6.5, 10.0] | 73.5 | 15.1 [12.6, 17.8] |
| D | `massive_zh` | 1000/1000 | 76.0 | 83.1 | 7.1 [5.5, 8.7] | 66.8 | 15.4 [12.7, 18.2] |
| D | `prompt_injections` | 116/116 | 76.7 | 98.3 | 21.6 [14.7, 28.4] | 100.0 | 28.4 [20.7, 37.1] |
| D | `clinc150_oos` | 5500/5500 | 89.5 | 96.8 | 7.3 [6.6, 7.9] | 83.4 | 9.6 [8.7, 10.4] |
| D | `turtlebench` | 1532/32 | 74.0 | 94.0 | 20.0 [15.4, 25.1] | 75.8 | 40.6 [34.6, 46.5] |
| **H · Human prompt annotation** | | | | | | | |
| H | `aegis2_prompt` | 1928/1915 | 82.4 | 98.4 | 16.0 [14.4, 17.7] | 100.0 | 26.0 [24.1, 28.0] |
| **A · Authored or AI-reviewed** | | | | | | | |
| A | `jevbench_original` | 72/36 | 98.6 | 100.0 | 1.4 [0.0, 4.2] | 97.2 | 7.1 [0.0, 16.2] |
| A | `jevbench_easy` | 48/48 | 100.0 | 100.0 | 0.0 [0.0, 0.0] | 100.0 | 0.0 [0.0, 0.0] |
| A | `jevbench_hard` | 111/111 | 72.1 | 84.7 | 12.6 [7.2, 18.9] | 82.0 | 57.1 [46.9, 67.4] |
| A | `reflexbench_reflex-public-choice-v1` | 95/95 | 93.7 | 96.8 | 3.2 [0.0, 7.4] | 86.3 | 15.9 [8.4, 24.4] |
| **T · Synthetic teacher** | | | | | | | |
| T | `typed_decisions` | 2000/400 | 73.9 | 91.2 | 17.3 [15.7, 19.1] | 79.1 | 35.7 [32.7, 38.7] |
| T | `jev_laya_triage` | 501/167 | 90.0 | 93.4 | 3.4 [2.0, 5.0] | 96.8 | 17.7 [14.9, 20.7] |
| T | `jev_laya_moderation` | 426/142 | 92.7 | 97.7 | 4.9 [3.1, 6.8] | 98.6 | 7.4 [5.2, 9.9] |
| T | `jev_laya_routing` | 411/137 | 88.8 | 97.1 | 8.3 [5.8, 10.7] | 92.0 | 18.5 [14.4, 22.8] |
| T | `jev_laya_claims` | 300/150 | 100.0 | 100.0 | 0.0 [0.0, 0.0] | 99.3 | 2.3 [0.7, 4.7] |
| T | `jev_laya_reviews` | 300/150 | 87.7 | 95.7 | 8.0 [5.0, 10.0] | 96.0 | 12.5 [9.1, 16.1] |
| T | `jev_laya_guard` | 292/146 | 93.8 | 99.3 | 5.5 [3.1, 8.2] | 96.9 | 14.1 [9.9, 18.6] |
| T | `jev_laya_multilingual` | 256/128 | 100.0 | 100.0 | 0.0 [0.0, 0.0] | 99.2 | 0.8 [0.0, 2.0] |
| **P · Programmatic** | | | | | | | |
| P | `jev_laya_needle` | 900/25 | 95.2 | 95.6 | 0.3 [0.0, 0.7] | 99.8 | 21.3 [13.0, 30.1] |

## What this adds to the paper

1. **Potential selectability is source-dependent.** On dataset-provided SST-5/choice, best observed accuracy is 55.9% and the oracle ceiling 87.3%, a 31.4 pp headroom [28.5, 34.4]. On AG News, the analogous headroom is 3.3 pp [2.3, 4.4]. Each headroom is computed within a suite; this contrast is descriptive, not a claim about a population of domains.
2. **Complementarity does not validate voting.** SST-5/choice majority covers 78.6% with 42.7% risk [39.3, 46.1]; on human-annotated Aegis2 prompts, coverage is 100% but risk is 26.0% [24.1, 28.0]. The latter is 501 errors among 1,928 covered decisions. Because coverage is complete, majority agreement is 74.0%, below the best single system's 82.4%. A majority can amplify a shared mistake or outvote the best system.
3. **Small oracle headroom does not imply safe consensus.** The programmatic needle suite has 0.3 pp headroom [0.0, 0.7] but 21.3% majority risk [13.0, 30.1] at 99.8% coverage. Interpret this cautiously because there are 25 original content clusters despite 900 decisions.

## Reproduction and limitations

Run `.venv/bin/python research/cross_domain_v1/analyze.py` from the repository root to regenerate `summary.json`, followed by `.venv/bin/python research/cross_domain_v1/validate.py` for an independent exact-count check; with the paper extra installed, run `python paper/figures/gen_cross_domain.py` for PDF/SVG/PNG. The figure was visually inspected both at native PNG resolution and embedded in the compiled paper. It shows all 28 suites with separate D/H/A/T/P provenance bands and no data-selected subset or grand mean.

The five-system panel mixes hosted Jev and local models for **reference agreement only**; no pooled latency or cost inference is made. Reference quality is not established equally across tracks: D inherits source-dataset labels, H contains human prompt annotations, A includes authored or AI-reviewed fixtures, T synthetic teacher labels, and P executable programmatic labels. Oracle calculations depend on these references being accepted as given. The historical outputs were available before these diagnostics; this is not a preregistered hypothesis test. A genuinely deployable cross-domain selector would require a separately specified training signal, held-out source evaluation, calibration and operational-cost accounting.

