"""Descriptive cross-domain error complementarity from frozen model decisions.

One row is one typed decision. The five model outputs for a row are paired;
bootstrap units are source/state ``group`` values, never output tokens or models.
No accuracy is pooled across suites or reference-provenance classes.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import gzip
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MODELS = ["english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0"]
NAMES = {
    "english": "Laya EN",
    "multilingual": "Laya Multi",
    "llama31_8b_instruct": "Llama 3.1 8B",
    "qwen3_8b": "Qwen3 8B",
    "jev-1.13.0": "Jev 1.13",
}
SEED = 20260930
DRAWS = 5000
REF_CODES = {
    "dataset_provided": "D",
    "human_prompt_annotation": "H",
    "authored_or_AI_reviewed": "A",
    "synthetic_teacher": "T",
    "programmatic": "P",
}


def digest(path):
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_model(model, suite, expected_decisions):
    base = ROOT / ("api_results" if model.startswith("jev-") else "results") / model
    meta = json.loads((base / "metadata.json").read_text())
    assert meta["status"] == "DONE", (model, meta["status"])
    path = base / f"{suite}.json.gz"
    assert digest(path) == meta["suites"][suite]["sha256"], path
    obj = json.loads(gzip.decompress(path.read_bytes()))
    rows = obj["rows"]
    assert len(rows) == expected_decisions, (model, suite, len(rows), expected_decisions)
    keyed = {(r["id"], r["qid"]): r for r in rows}
    assert len(keyed) == len(rows), (model, suite, "duplicate decision key")
    return keyed, str(path.relative_to(ROOT)), digest(path)


def summarize(cases, rng):
    """Estimates and paired cluster intervals for one suite; no cross-suite pool."""
    by_group = defaultdict(list)
    counts = dict.fromkeys(range(6), 0)
    for case in cases:
        ncorrect = sum(case["correct"])
        counts[ncorrect] += 1
        by_group[case["group"]].append(case)

    # Columns: five individual correct, any correct, strict-majority covered,
    # strict-majority correct, unanimously same wrong label, number of cases.
    matrix = np.zeros((len(by_group), 10), dtype=np.int64)
    for i, group_cases in enumerate(by_group.values()):
        for case in group_cases:
            correct = np.asarray(case["correct"], dtype=np.int64)
            votes = Counter(p for p, valid in zip(case["prediction"], case["valid"]) if valid)
            label, vote_count = votes.most_common(1)[0] if votes else (None, 0)
            covered = vote_count >= 3  # strict majority of the fixed five-model panel
            same_wrong = (not any(correct) and len(votes) == 1 and vote_count == 5)
            matrix[i, :5] += correct
            matrix[i, 5] += int(any(correct))
            matrix[i, 6] += int(covered)
            matrix[i, 7] += int(covered and label == case["gold"])
            matrix[i, 8] += int(same_wrong)
            matrix[i, 9] += 1

    def metric(sums):
        n = sums[..., 9]
        per_model = sums[..., :5] / n[..., None]
        oracle = sums[..., 5] / n
        best = per_model.max(axis=-1)
        majority_coverage = sums[..., 6] / n
        majority_yield = sums[..., 7] / n
        majority_risk = np.divide(
            sums[..., 6] - sums[..., 7], sums[..., 6],
            out=np.full_like(majority_coverage, np.nan, dtype=float), where=sums[..., 6] > 0)
        unanimous_wrong = sums[..., 8] / n
        return np.column_stack((best, oracle, oracle - best,
                                majority_coverage, majority_risk, unanimous_wrong,
                                majority_yield, majority_yield - best))

    point = metric(matrix.sum(axis=0)[None, :])[0]
    draws = []
    for start in range(0, DRAWS, 64):
        sample_count = min(64, DRAWS - start)
        ix = rng.integers(0, len(matrix), (sample_count, len(matrix)))
        draws.append(metric(matrix[ix].sum(axis=1)))
    boots = np.concatenate(draws, axis=0)
    keys = ["best_single", "oracle", "oracle_headroom", "majority_coverage",
            "majority_risk", "unanimous_wrong", "majority_yield",
            "majority_yield_minus_best"]
    result = {}
    for j, name in enumerate(keys):
        vals = boots[:, j]
        if np.isnan(point[j]):
            result[name] = {"estimate": None, "ci95": None}
        else:
            lo, hi = np.nanquantile(vals, [0.025, 0.975])
            result[name] = {"estimate": float(point[j]), "ci95": [float(lo), float(hi)]}
    model_rates = matrix[:, :5].sum(axis=0) / matrix[:, 9].sum()
    result["model_accuracy"] = {m: float(model_rates[i]) for i, m in enumerate(MODELS)}
    result["best_model"] = NAMES[MODELS[int(model_rates.argmax())]]
    result["correct_model_count_distribution"] = {str(k): counts[k] for k in range(6)}
    result["n_decisions"] = int(matrix[:, 9].sum())
    result["n_state_clusters"] = int(len(matrix))
    result["majority_covered_count"] = int(matrix[:, 6].sum())
    result["majority_error_count"] = int(matrix[:, 6].sum() - matrix[:, 7].sum())
    result["all_five_wrong_count"] = int(counts[0])
    result["all_five_correct_count"] = int(counts[5])
    result["unanimous_wrong_count"] = int(matrix[:, 8].sum())
    assert counts[0] == result["n_decisions"] - matrix[:, 5].sum()
    assert sum(counts.values()) == result["n_decisions"]
    assert result["best_single"]["estimate"] <= result["oracle"]["estimate"] + 1e-12
    return result


def main():
    manifest_path = ROOT / "protocol_manifest.json"
    atlas_path = ROOT / "paper/source_atlas.json"
    manifest = json.loads(manifest_path.read_text())
    atlas = json.loads(atlas_path.read_text())
    main_suites = [s for s in manifest["suites"] if s["track"] != "order_robustness"]
    atlas_rows = {suite: source for source in atlas["sources"] for suite in source["suites"]}
    assert len(main_suites) == 28
    assert set(atlas_rows) == {s["name"] for s in main_suites}
    rng = np.random.default_rng(SEED)
    output = {
        "analysis": "cross-domain-error-complementarity-v1",
        "population": "28 frozen main suites; five paired systems; one typed decision per row",
        "intervals": "pointwise descriptive 95% percentile cluster bootstrap by source/state group within suite; 5000 draws; no cross-suite inference",
        "seed": SEED, "bootstrap_draws": DRAWS,
        "models": MODELS, "model_names": NAMES,
        "definitions": {
            "best_single": "maximum observed accuracy among the five systems on this suite; same-data selected, descriptive",
            "oracle": "fraction with at least one of five correct outputs; reference-aware selector upper bound, not a deployable router",
            "oracle_headroom": "oracle minus best_single; recompute the maximum within each bootstrap draw",
            "majority_coverage": "fraction with at least three identical valid labels among the fixed five systems",
            "majority_risk": "error fraction among strict-majority-covered decisions; undefined when no majority",
            "majority_yield": "correct strict-majority decisions divided by all decisions; unanswered decisions do not contribute",
            "majority_yield_minus_best": "majority_yield minus same-sample best single-system accuracy; different coverage and not a matched selective-risk comparison",
            "unanimous_wrong": "fraction where all five return the identical wrong valid label",
        },
        "input_hashes": {
            "protocol_manifest.json": digest(manifest_path),
            "paper/source_atlas.json": digest(atlas_path),
        },
        "suites": [],
    }
    for spec in main_suites:
        suite = spec["name"]
        records = {}
        for model in MODELS:
            records[model], path, hash_value = load_model(model, suite, spec["decisions"])
            output["input_hashes"][path] = hash_value
        keys = set(records[MODELS[0]])
        assert all(set(records[model]) == keys for model in MODELS)
        cases = []
        for key in sorted(keys):
            rows = [records[model][key] for model in MODELS]
            common = ("group", "type", "gold", "labels", "language",
                      "request_sha256", "questions_sha256")
            for field in common:
                assert all(r[field] == rows[0][field] for r in rows), (suite, key, field)
            assert all(r["error"] is not None or r["prediction"] in r["labels"]
                       for r in rows), (suite, key, "valid prediction outside label space")
            case = {
                "group": rows[0]["group"], "gold": rows[0]["gold"],
                "prediction": [r["prediction"] for r in rows],
                "valid": [r["error"] is None for r in rows],
                "correct": [int(r["error"] is None and r["prediction"] == r["gold"]) for r in rows],
            }
            cases.append(case)
        source = atlas_rows[suite]
        reference_code = REF_CODES[spec["reference"]]
        if source["reference"] == "T/P":
            assert reference_code in {"T", "P"}
        else:
            assert reference_code == source["reference"], (suite, reference_code, source)
        stats = summarize(cases, rng)
        output["suites"].append({
            "suite": suite, "source": source["name"], "domain": source["domain"],
            "reference_code": reference_code, "reference": spec["reference"],
            "collection_reference_code": source["reference"],
            "language": spec["language"], "task_tags": source["tasks"], **stats,
        })
    assert len(output["suites"]) == 28
    path = OUT / "summary.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {path}; {len(output['suites'])} suites; {len(output['input_hashes'])} input hashes")
    for s in output["suites"]:
        print(f"{s['suite']:<38} {s['reference_code']:<3} "
              f"best={s['best_single']['estimate']*100:5.1f} "
              f"oracle={s['oracle']['estimate']*100:5.1f} "
              f"gap={s['oracle_headroom']['estimate']*100:5.1f} "
              f"maj_cov={s['majority_coverage']['estimate']*100:5.1f} "
              f"maj_risk={s['majority_risk']['estimate']*100:5.1f}")


if __name__ == "__main__":
    main()
