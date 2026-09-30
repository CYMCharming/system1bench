"""Independent, stdlib-only point-estimate check of cross-domain results.

The primary analyzer uses NumPy clustered sufficient statistics. This script
recomputes all finite-population counts directly with separate per-case loops.
"""

from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "summary.json").read_text())
by_suite = {r["suite"]: r for r in summary["suites"]}
manifest = json.loads((ROOT / "protocol_manifest.json").read_text())
existing = json.loads((ROOT / "research/insights.json").read_text())
existing_score = {(r["suite"], r["model"]): r["estimate"] for r in existing["scores"]}
models = summary["models"]
assert len(models) == 5 and len(by_suite) == 28


def hashed(path):
    return sha256(path.read_bytes()).hexdigest()


checked_cases = 0
for spec in manifest["suites"]:
    if spec["track"] == "order_robustness":
        continue
    suite = spec["name"]
    result = by_suite[suite]
    records = []
    for model in models:
        root = "api_results" if model.startswith("jev-") else "results"
        path = ROOT / root / model / f"{suite}.json.gz"
        relative = str(path.relative_to(ROOT))
        assert hashed(path) == summary["input_hashes"][relative]
        raw = json.loads(gzip.decompress(path.read_bytes()))["rows"]
        assert len(raw) == spec["decisions"]
        keyed = {(r["id"], r["qid"]): r for r in raw}
        assert len(keyed) == len(raw)
        records.append(keyed)
    assert all(set(records[0]) == set(x) for x in records[1:])
    n = len(records[0])
    model_correct = [0] * 5
    any_correct = covered = vote_correct = unanimous_wrong = 0
    distribution = Counter()
    groups = set()
    for key in records[0]:
        rows = [model_rows[key] for model_rows in records]
        gold = rows[0]["gold"]
        assert all(r["gold"] == gold and r["labels"] == rows[0]["labels"] for r in rows)
        groups.add(rows[0]["group"])
        flags = []
        votes = Counter()
        for i, row in enumerate(rows):
            correct = row["error"] is None and row["prediction"] == gold
            flags.append(correct)
            model_correct[i] += int(correct)
            if row["error"] is None:
                assert row["prediction"] in row["labels"]
                votes[row["prediction"]] += 1
        any_correct += int(any(flags))
        distribution[sum(flags)] += 1
        top_label, top_count = votes.most_common(1)[0] if votes else (None, 0)
        if top_count >= 3:
            covered += 1
            vote_correct += int(top_label == gold)
        unanimous_wrong += int(top_count == 5 and not any(flags))
    assert n == result["n_decisions"] == sum(result["correct_model_count_distribution"].values())
    assert len(groups) == result["n_state_clusters"]
    assert all(distribution[k] == result["correct_model_count_distribution"][str(k)] for k in range(6))
    rates = [c / n for c in model_correct]
    for i, model in enumerate(models):
        assert abs(rates[i] - result["model_accuracy"][model]) < 1e-12
        assert abs(rates[i] - existing_score[(suite, model)]) < 1e-12
    assert result["all_five_wrong_count"] == distribution[0] == n - any_correct
    assert result["all_five_correct_count"] == distribution[5]
    assert result["majority_covered_count"] == covered
    assert result["majority_error_count"] == covered - vote_correct
    assert result["unanimous_wrong_count"] == unanimous_wrong
    point = {
        "best_single": max(rates),
        "oracle": any_correct / n,
        "oracle_headroom": any_correct / n - max(rates),
        "majority_coverage": covered / n,
        "majority_risk": (covered - vote_correct) / covered,
        "majority_yield": vote_correct / n,
        "majority_yield_minus_best": vote_correct / n - max(rates),
        "unanimous_wrong": unanimous_wrong / n,
    }
    for metric, exact in point.items():
        assert abs(result[metric]["estimate"] - exact) < 1e-12, (suite, metric)
    checked_cases += n

assert checked_cases == sum(row["n_decisions"] for row in summary["suites"])
print(f"PASS: {len(by_suite)} suites, {checked_cases} paired decisions, "
      "140 accuracy rates, all point metrics and 140 raw-file hashes")
