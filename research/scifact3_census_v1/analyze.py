"""Analyze fresh SciFact cited-pair census outputs against the frozen references.

The full eligible census and its predeclared 159-pair complement are separate
cohorts. Paired percentile intervals cluster by claim (primary) or document
(sensitivity); they are descriptive for this fixed dev source, not cross-source
sampling intervals.
"""

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from system1bench.common import digest, read, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_census_v1"
MODELS = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
SEED = 2026093004
DRAWS = 10_000


def load_rows(model, condition, cases, manifest, manifest_sha, hashes):
    directory = OUT / "results" / ("jev-1.13.0" if model == "jev-1.13.0" else f"local/{model}")
    metadata_path = directory / "metadata.json"
    metadata = read(metadata_path)
    assert metadata["status"] == "DONE", (model, metadata["status"])
    signature = metadata["signature"]
    if model == "jev-1.13.0":
        assert signature["frozen_sha256"] == manifest["prepared_sha256"]
        assert metadata["completed_requests"] == 1356
    else:
        assert signature["prepared_sha256"] == manifest["prepared_sha256"]
        assert signature["protocol_sha256"] == manifest_sha
    suite_name = f"scifact3_{condition}"
    suite_meta = metadata["suites"][suite_name]
    assert suite_meta["requests"] == len(cases) == 339
    path = directory / f"{suite_name}.json.gz"
    assert sha(path) == suite_meta["sha256"]
    payload = json.loads(gzip.decompress(path.read_bytes()))
    raw_signature = payload["signature"]
    if model == "jev-1.13.0":
        assert raw_signature["frozen_sha256"] == manifest["prepared_sha256"]
    else:
        assert raw_signature["prepared_sha256"] == manifest["prepared_sha256"]
        assert raw_signature["protocol_sha256"] == manifest_sha
    rows = payload["rows"]
    assert len(rows) == len(cases)
    keyed = {(row["id"], row["qid"]): row for row in rows}
    assert len(keyed) == len(rows)
    for case in cases:
        row = keyed[(case["id"], "answer")]
        assert row["gold"] == case["gold"]["answer"]["label"]
        assert row["request_sha256"] == case["request_sha256"]
        assert row["labels"] == list(case["questions"]["answer"]["criteria"])
        assert row["group"] == case["group"]
    hashes[str(path.relative_to(ROOT))] = sha(path)
    hashes[str(metadata_path.relative_to(ROOT))] = sha(metadata_path)
    return keyed


def indicators(rows, gold):
    n = len(gold)
    valid = {condition: np.array([
        row["error"] is None and row["prediction"] in LABELS
        for row in rows[condition]
    ], dtype=bool) for condition in CONDITIONS}
    pred = {condition: np.array([
        row["prediction"] if valid[condition][i] else "INVALID"
        for i, row in enumerate(rows[condition])
    ], dtype=object) for condition in CONDITIONS}
    correct = {c: valid[c] & (pred[c] == gold) for c in CONDITIONS}
    b, rep, rev, title = CONDITIONS
    pairs = {c: valid[b] & valid[c] for c in (rep, rev, title)}
    flips = {c: pairs[c] & (pred[b] != pred[c]) for c in (rep, rev, title)}
    triple_reverse = pairs[rep] & valid[rev]
    triple_title = pairs[rep] & valid[title]
    columns = {
        "n": np.ones(n, dtype=int),
        "base_correct": correct[b], "repeat_correct": correct[rep],
        "reverse_correct": correct[rev], "title_correct": correct[title],
        "robust_correct": correct[b] & correct[rev],
        "reverse_correction": ~correct[b] & correct[rev],
        "reverse_regression": correct[b] & ~correct[rev],
        "title_correction": ~correct[b] & correct[title],
        "title_regression": correct[b] & ~correct[title],
        "base_valid": valid[b], "repeat_valid": valid[rep],
        "reverse_valid": valid[rev], "title_valid": valid[title],
        "base_reverse_valid": pairs[rev], "base_repeat_valid": pairs[rep],
        "base_title_valid": pairs[title],
        "reverse_flip": flips[rev], "repeat_flip": flips[rep],
        "title_flip": flips[title],
        "triple_reverse_valid": triple_reverse,
        "excess_reverse_repeat_flip": triple_reverse * (flips[rev].astype(int) - flips[rep].astype(int)),
        "triple_title_valid": triple_title,
        "excess_title_repeat_flip": triple_title * (flips[title].astype(int) - flips[rep].astype(int)),
        "base_noinfo_to_other": (pred[b] == "NOINFO") & valid[rev] & (pred[rev] != "NOINFO"),
        "base_other_to_noinfo": (pred[b] != "NOINFO") & valid[b] & (pred[rev] == "NOINFO"),
    }
    names = tuple(columns)
    matrix = np.column_stack([columns[name] for name in names]).astype(np.int16)
    return names, matrix, pred, valid


def ratios(sums, names):
    loc = {name: i for i, name in enumerate(names)}

    def ratio(num, den):
        a = sums[..., loc[num]] if isinstance(num, str) else num
        b = sums[..., loc[den]] if isinstance(den, str) else den
        return np.divide(a, b, out=np.full(np.shape(a), np.nan, dtype=float), where=b > 0)

    return {
        "base_accuracy_strict": ratio("base_correct", "n"),
        "base_accuracy_valid_only": ratio("base_correct", "base_valid"),
        "repeat_accuracy_strict": ratio("repeat_correct", "n"),
        "reverse_accuracy_strict": ratio("reverse_correct", "n"),
        "title_accuracy_strict": ratio("title_correct", "n"),
        "robust_correct_strict": ratio("robust_correct", "n"),
        "reverse_accuracy_delta": ratio(sums[..., loc["reverse_correct"]] - sums[..., loc["base_correct"]], "n"),
        "title_accuracy_delta": ratio(sums[..., loc["title_correct"]] - sums[..., loc["base_correct"]], "n"),
        "reverse_correction": ratio("reverse_correction", "n"),
        "reverse_regression": ratio("reverse_regression", "n"),
        "title_correction": ratio("title_correction", "n"),
        "title_regression": ratio("title_regression", "n"),
        "reverse_flip_valid": ratio("reverse_flip", "base_reverse_valid"),
        "repeat_flip_valid": ratio("repeat_flip", "base_repeat_valid"),
        "title_flip_valid": ratio("title_flip", "base_title_valid"),
        "excess_reverse_repeat_flip": ratio("excess_reverse_repeat_flip", "triple_reverse_valid"),
        "excess_title_repeat_flip": ratio("excess_title_repeat_flip", "triple_title_valid"),
        "base_noinfo_to_other_per_pair": ratio("base_noinfo_to_other", "n"),
        "base_other_to_noinfo_per_pair": ratio("base_other_to_noinfo", "n"),
    }


def bootstrap_design(indices, ids, rng):
    cluster_ids = sorted({ids[i] for i in indices})
    mapping = {key: j for j, key in enumerate(cluster_ids)}
    membership = np.array([mapping[ids[i]] for i in indices], dtype=int)
    size = len(cluster_ids)
    weights = rng.multinomial(size, np.full(size, 1 / size), size=DRAWS).astype(np.float32)
    return membership, weights, size


def summarize(matrix, names, indices, designs):
    sums = matrix[indices].sum(axis=0)
    point = ratios(sums, names)
    intervals = {}
    for cluster_name, (membership, weights, size) in designs.items():
        cluster_sums = np.zeros((size, matrix.shape[1]), dtype=np.float32)
        np.add.at(cluster_sums, membership, matrix[indices])
        bootstrap_sums = weights @ cluster_sums
        measured = ratios(bootstrap_sums, names)
        intervals[cluster_name] = {}
        for metric, values in measured.items():
            finite = values[np.isfinite(values)]
            intervals[cluster_name][metric] = ([float(x) for x in np.quantile(finite, [0.025, 0.975])]
                                               if len(finite) else None)
    counts = {name: int(sums[j]) for j, name in enumerate(names)}
    assert counts["reverse_correct"] - counts["base_correct"] == (
        counts["reverse_correction"] - counts["reverse_regression"])
    assert counts["title_correct"] - counts["base_correct"] == (
        counts["title_correction"] - counts["title_regression"])
    return {
        "n": len(indices), "counts": counts,
        "metrics": {name: {"estimate": float(value) if np.isfinite(value) else None,
                           "ci95_claim_cluster": intervals["claim"][name],
                           "ci95_document_cluster": intervals["document"][name]}
                    for name, value in point.items()},
    }


def confusion(gold, pred, indices):
    matrix = {label: {candidate: 0 for candidate in (*LABELS, "INVALID")} for label in LABELS}
    for i in indices:
        matrix[str(gold[i])][str(pred[i])] += 1
    return matrix


def transitions(first, second, indices):
    values = (*LABELS, "INVALID")
    matrix = {before: {after: 0 for after in values} for before in values}
    for i in indices:
        matrix[str(first[i])][str(second[i])] += 1
    return matrix


def main():
    summary_path = OUT / "summary.json"
    case_level_path = OUT / "case_level.json"
    if summary_path.exists() or case_level_path.exists():
        raise FileExistsError("Census analysis already exists; refuse overwrite")
    manifest = read(OUT / "manifest.json")
    frozen_path = OUT / "frozen.json"
    assert sha(frozen_path) == manifest["prepared_sha256"]
    assert read(OUT / "validation.json")["frozen_sha256"] == manifest["prepared_sha256"]
    assert read(OUT / "input_audit.json")["frozen_sha256"] == manifest["prepared_sha256"]
    frozen = read(frozen_path)
    suites = {suite["condition"]: suite for suite in frozen["suites"]}
    assert list(suites) == list(CONDITIONS)
    base_cases = suites["base"]["cases"]
    assert len(base_cases) == 339
    for condition in CONDITIONS:
        assert len(suites[condition]["cases"]) == 339
        for base, case in zip(base_cases, suites[condition]["cases"]):
            assert base["id"] == case["id"]
            assert case["request_sha256"] == digest(request(case))
    gold = np.array([case["gold"]["answer"]["label"] for case in base_cases], dtype=object)
    claim_ids = [case["source_id"]["claim_id"] for case in base_cases]
    document_ids = [case["source_id"]["doc_id"] for case in base_cases]
    cohort_indices = {
        "all339": np.arange(339),
        "complement159": np.array([i for i, c in enumerate(base_cases) if not c["prior_three_choice_selected"]]),
        "prior_selected180": np.array([i for i, c in enumerate(base_cases) if c["prior_three_choice_selected"]]),
    }
    assert [len(x) for x in cohort_indices.values()] == [339, 159, 180]
    assert Counter(gold[cohort_indices["complement159"]]) == {"SUPPORT": 78, "CONTRADICT": 11, "NOINFO": 70}
    assert sum(base_cases[i]["prior_two_choice_selected"] for i in cohort_indices["complement159"]) == 37
    rng = np.random.default_rng(SEED)
    designs = {}
    slices = {}
    for cohort_name, cohort in cohort_indices.items():
        slices[cohort_name] = {"all": cohort}
        for label in LABELS:
            slices[cohort_name][label] = cohort[gold[cohort] == label]
        designs[cohort_name] = {}
        for slice_name, indices in slices[cohort_name].items():
            designs[cohort_name][slice_name] = {
                "claim": bootstrap_design(indices, claim_ids, rng),
                "document": bootstrap_design(indices, document_ids, rng),
            }
    hashes = {
        "frozen_sha256": manifest["prepared_sha256"],
        "manifest_sha256": sha(OUT / "manifest.json"),
        "protocol_sha256": sha(OUT / "PROTOCOL.md"),
        "validation_sha256": sha(OUT / "validation.json"),
        "input_audit_sha256": sha(OUT / "input_audit.json"),
    }
    result = {
        "protocol": frozen["protocol"], "models": list(MODELS), "seed": SEED, "draws": DRAWS,
        "definitions": {
            "reference": "positive evidence label or derived lack of annotated abstract evidence for an explicitly cited document",
            "primary_cohort": "all 339 official dev cited claim--document pairs; natural cited-pair label mix",
            "complement": "159 pairs not in prior three-choice 180; 37 positive pairs were in earlier two-choice experiment",
            "strict_correctness": "valid semantic prediction equals reference; invalid/error stays in denominator as not correct",
            "valid_only_correctness": "reference-correct / valid semantic predictions",
            "robust_correct": "reference-correct in both base and reversal",
            "flip": "unequal semantic predictions, conditional on both compared outputs valid",
            "interval": "10,000 paired claim-cluster percentile draws primary; document-cluster sensitivity; fixed dev source only",
        },
        "input_hashes": hashes, "cohorts": {}, "systems": {},
    }
    for cohort_name, slice_map in slices.items():
        result["cohorts"][cohort_name] = {
            "n": len(cohort_indices[cohort_name]),
            "label_counts": dict(Counter(gold[cohort_indices[cohort_name]])),
            "claims": len({claim_ids[i] for i in cohort_indices[cohort_name]}),
            "documents": len({document_ids[i] for i in cohort_indices[cohort_name]}),
            "slices": {name: {"n": len(idx), "claim_clusters": designs[cohort_name][name]["claim"][2],
                              "document_clusters": designs[cohort_name][name]["document"][2]}
                       for name, idx in slice_map.items()},
        }
    case_level = {"frozen_sha256": manifest["prepared_sha256"], "systems": {}}
    for model in MODELS:
        raw = {condition: load_rows(model, condition, suites[condition]["cases"], manifest,
                                    hashes["manifest_sha256"], hashes)
               for condition in CONDITIONS}
        rows = {condition: [raw[condition][case["id"], "answer"] for case in base_cases]
                for condition in CONDITIONS}
        names, data, pred, valid = indicators(rows, gold)
        result["systems"][model] = {}
        for cohort_name, slice_map in slices.items():
            result["systems"][model][cohort_name] = {}
            for slice_name, indices in slice_map.items():
                stats = summarize(data, names, indices, designs[cohort_name][slice_name])
                stats["confusion"] = {c: confusion(gold, pred[c], indices) for c in CONDITIONS}
                stats["prediction_marginals"] = {c: dict(Counter(pred[c][indices])) for c in CONDITIONS}
                stats["base_to_reverse"] = transitions(pred["base"], pred["reversed_option_order"], indices)
                result["systems"][model][cohort_name][slice_name] = stats
        case_level["systems"][model] = [{
            "id": case["id"], "claim_id": claim_ids[i], "document_id": document_ids[i],
            "gold": str(gold[i]), "prior_three_choice_selected": case["prior_three_choice_selected"],
            "prior_two_choice_selected": case["prior_two_choice_selected"],
            "prediction": {c: str(pred[c][i]) for c in CONDITIONS},
            "valid": {c: bool(valid[c][i]) for c in CONDITIONS},
            "errors": {c: rows[c][i]["error"] for c in CONDITIONS},
        } for i, case in enumerate(base_cases)]
    write(summary_path, result)
    write(case_level_path, case_level)
    for model in MODELS:
        for cohort in ("all339", "complement159"):
            counts = result["systems"][model][cohort]["all"]["counts"]
            noinfo = result["systems"][model][cohort]["NOINFO"]["counts"]
            print(model, cohort, "base/reverse", counts["base_correct"], counts["reverse_correct"],
                  "flips", counts["reverse_flip"], "NOINFO base/reverse",
                  noinfo["base_correct"], noinfo["reverse_correct"],
                  "NOINFO-to-other", noinfo["base_noinfo_to_other"], flush=True)


if __name__ == "__main__":
    main()
