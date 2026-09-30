"""Human-readable audit trail for the source-preserving analysis."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "summary.json").read_text())
order = ["D", "H", "A", "T", "P"]
names = {
    "D": "Dataset-provided", "H": "Human prompt annotation",
    "A": "Authored or AI-reviewed", "T": "Synthetic teacher",
    "P": "Programmatic",
}


def pct(x):
    return f"{x*100:.1f}"


def est_ci(row, name):
    x = row[name]
    return f"{pct(x['estimate'])} [{pct(x['ci95'][0])}, {pct(x['ci95'][1])}]"


lines = [
    "# Cross-domain error complementarity (exploratory)",
    "",
    "This analysis reads the frozen historical raw predictions for five paired systems on all 28 main suites. "
    "It verifies 140 raw-result files against their metadata hashes, matches every decision key and common reference/input fields, "
    "and reconciles all 140 accuracies against the independent existing `research/insights.json` analysis. "
    "A separate stdlib-only validation recomputes point metrics over 25,788 paired decisions and checks all 140 raw-file hashes. "
    "It does not combine scores across unlike source collections or reference standards.",
    "",
    "## Definitions and boundaries",
    "",
    "- **Best single** is the maximum observed suite accuracy among the five systems; its identity is selected on the same sample.",
    "- **Oracle** is the fraction with at least one correct system output. It knows the reference for each decision and is an unattainable selector ceiling, not a learned routing result.",
    "- **Headroom** = oracle − best single. In each bootstrap replicate, the best system is selected anew, so the interval respects that selection operation. It remains descriptive and does not account for benchmark development using these outcomes.",
    "- **Strict-majority coverage** requires at least three identical valid labels among the fixed five outputs. Failed outputs cast no vote and remain in the five-system denominator. **Risk** is the error fraction conditional on coverage; it must be read with the coverage column.",
    "- **Majority yield** is correct majority answers divided by all decisions, with abstentions left unanswered. It is not a matched selective-risk comparison against the always-answering best single system. When majority coverage is 100%, its difference from best single is directly comparable as reference agreement.",
    "- **Intervals** are pointwise 95% percentile intervals from 5,000 bootstrap resamples of source/state clusters within each suite. Repeated questions of one state stay together; e.g. the 900 needle decisions have only 25 content clusters.",
    "- Source collections can generate several suites or alternate interfaces on overlapping states. Those rows are not independent replications. D/H/A/T/P labels denote reference provenance, not interchangeable validity grades.",
    "",
    "## Per-suite results",
    "",
    "Values are percentages except `n/clusters`. Every row has its own denominator; there is intentionally no overall average.",
    "",
    "| Ref | Suite | n/clusters | Best single | Oracle | Headroom (95% CI; pp) | Majority coverage | Majority risk (95% CI) |",
    "|---|---|---:|---:|---:|---:|---:|---:|",
]
for code in order:
    rows = [row for row in data["suites"] if row["reference_code"] == code]
    lines.append(f"| **{code} · {names[code]}** | | | | | | | |")
    for row in rows:
        lines.append(
            f"| {code} | `{row['suite']}` | {row['n_decisions']}/{row['n_state_clusters']} "
            f"| {pct(row['best_single']['estimate'])} | {pct(row['oracle']['estimate'])} "
            f"| {est_ci(row, 'oracle_headroom')} | {pct(row['majority_coverage']['estimate'])} "
            f"| {est_ci(row, 'majority_risk')} |"
        )
lines += [
    "",
    "## What this adds to the paper",
    "",
    "1. **Potential selectability is source-dependent.** On dataset-provided SST-5/choice, best observed accuracy is 55.9% and the oracle ceiling 87.3%, a 31.4 pp headroom [28.5, 34.4]. On AG News, the analogous headroom is 3.3 pp [2.3, 4.4]. Each headroom is computed within a suite; this contrast is descriptive, not a claim about a population of domains.",
    "2. **Complementarity does not validate voting.** SST-5/choice majority covers 78.6% with 42.7% risk [39.3, 46.1]; on human-annotated Aegis2 prompts, coverage is 100% but risk is 26.0% [24.1, 28.0]. The latter is 501 errors among 1,928 covered decisions. Because coverage is complete, majority agreement is 74.0%, below the best single system's 82.4%. A majority can amplify a shared mistake or outvote the best system.",
    "3. **Small oracle headroom does not imply safe consensus.** The programmatic needle suite has 0.3 pp headroom [0.0, 0.7] but 21.3% majority risk [13.0, 30.1] at 99.8% coverage. Interpret this cautiously because there are 25 original content clusters despite 900 decisions.",
    "",
    "## Reproduction and limitations",
    "",
    "Run `.venv/bin/python research/cross_domain_v1/analyze.py` from the repository root to regenerate `summary.json`, followed by `.venv/bin/python research/cross_domain_v1/validate.py` for an independent exact-count check; with the paper extra installed, run `python paper/figures/gen_cross_domain.py` for PDF/SVG/PNG. The figure was visually inspected both at native PNG resolution and embedded in the compiled paper. It shows all 28 suites with separate D/H/A/T/P provenance bands and no data-selected subset or grand mean.",
    "",
    "The five-system panel mixes hosted Jev and local models for **reference agreement only**; no pooled latency or cost inference is made. Reference quality is not established equally across tracks: D inherits source-dataset labels, H contains human prompt annotations, A includes authored or AI-reviewed fixtures, T synthetic teacher labels, and P executable programmatic labels. Oracle calculations depend on these references being accepted as given. The historical outputs were available before these diagnostics; this is not a preregistered hypothesis test. A genuinely deployable cross-domain selector would require a separately specified training signal, held-out source evaluation, calibration and operational-cost accounting.",
    "",
]
(HERE / "RESULTS.en.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {HERE / 'RESULTS.en.md'}")
