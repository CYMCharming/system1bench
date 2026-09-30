"""Analyze the frozen three-class SciFact experiment from hashed raw outputs.

No model inference is performed. The primary unit is a unique claim--document
pair; both claim and document IDs are globally unique in the frozen sample.
"""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np

from system1bench.common import digest, read, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_v1"
MODELS = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")
DISPLAY = {
    "english": "Laya English", "multilingual": "Laya Multilingual",
    "llama31_8b_instruct": "Llama 3.1 8B", "qwen3_8b": "Qwen3 8B",
    "jev-1.13.0": "Jev 1.13",
}
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
SEED = 2026093003
DRAWS = 10_000


def load_raw(model, condition, cases, manifest, hashes):
    directory = OUT / "results" / (
        "jev-1.13.0" if model == "jev-1.13.0" else f"local/{model}")
    metadata = read(directory / "metadata.json")
    if metadata["status"] != "DONE":
        raise RuntimeError(f"{model} not complete: {metadata['status']}")
    signature = metadata["signature"]
    if model == "jev-1.13.0":
        assert signature["frozen_sha256"] == manifest["prepared_sha256"]
        assert metadata["completed_requests"] == 720
    else:
        assert signature["prepared_sha256"] == manifest["prepared_sha256"]
        assert signature["protocol_sha256"] == hashes["manifest_sha256"]
    suite_name = f"scifact3_{condition}"
    suite_meta = metadata["suites"][suite_name]
    assert suite_meta["requests"] == len(cases) == 180
    path = directory / f"{suite_name}.json.gz"
    actual_sha = sha(path)
    assert actual_sha == suite_meta["sha256"]
    payload = json.loads(gzip.decompress(path.read_bytes()))
    raw_signature = payload["signature"]
    if model == "jev-1.13.0":
        assert raw_signature["frozen_sha256"] == manifest["prepared_sha256"]
    else:
        assert raw_signature["prepared_sha256"] == manifest["prepared_sha256"]
        assert raw_signature["protocol_sha256"] == hashes["manifest_sha256"]
    raw_rows = payload["rows"]
    assert len(raw_rows) == len(cases)
    keyed = {(row["id"], row["qid"]): row for row in raw_rows}
    assert len(keyed) == len(raw_rows)
    for case in cases:
        row = keyed[(case["id"], "answer")]
        assert row["gold"] == case["gold"]["answer"]["label"]
        assert row["request_sha256"] == case["request_sha256"]
        assert row["labels"] == list(case["questions"]["answer"]["criteria"])
        assert row["group"] == case["group"]
    hashes[str(path.relative_to(ROOT))] = actual_sha
    hashes[str((directory / "metadata.json").relative_to(ROOT))] = sha(directory / "metadata.json")
    return keyed


def bootstrap_indices(gold):
    rng = np.random.default_rng(SEED)
    by_label = {label: np.flatnonzero(gold == label) for label in LABELS}
    assert all(len(indices) == 60 for indices in by_label.values())
    draws = {label: indices[rng.integers(0, len(indices), size=(DRAWS, len(indices)))]
             for label, indices in by_label.items()}
    draws["all"] = np.concatenate([draws[label] for label in LABELS], axis=1)
    return draws, by_label


def indicator_matrix(records, gold):
    n = len(gold)
    valid = {condition: np.array([
        row["error"] is None and row["prediction"] in LABELS
        for row in records[condition]
    ], dtype=bool) for condition in CONDITIONS}
    prediction = {condition: np.array([
        row["prediction"] if valid[condition][i] else "INVALID"
        for i, row in enumerate(records[condition])
    ], dtype=object) for condition in CONDITIONS}
    correct = {condition: valid[condition] & (prediction[condition] == gold)
               for condition in CONDITIONS}
    b, t, v, u = CONDITIONS
    pair_bv = valid[b] & valid[v]
    pair_bt = valid[b] & valid[t]
    pair_bu = valid[b] & valid[u]
    triple_btv = pair_bv & valid[t]
    triple_btu = pair_bu & valid[t]
    flip_bv = pair_bv & (prediction[b] != prediction[v])
    flip_bt = pair_bt & (prediction[b] != prediction[t])
    flip_bu = pair_bu & (prediction[b] != prediction[u])
    columns = {
        "n": np.ones(n, dtype=int),
        "base_correct": correct[b], "repeat_correct": correct[t],
        "reverse_correct": correct[v], "title_correct": correct[u],
        "robust_correct": correct[b] & correct[v],
        "title_robust_correct": correct[b] & correct[u],
        "reverse_correction": ~correct[b] & correct[v],
        "reverse_regression": correct[b] & ~correct[v],
        "title_correction": ~correct[b] & correct[u],
        "title_regression": correct[b] & ~correct[u],
        "valid_base_reverse": pair_bv, "flip_base_reverse": flip_bv,
        "valid_base_repeat": pair_bt, "flip_base_repeat": flip_bt,
        "valid_base_title": pair_bu, "flip_base_title": flip_bu,
        "triple_base_repeat_reverse": triple_btv,
        "excess_reverse_repeat": triple_btv * (flip_bv.astype(int) - flip_bt.astype(int)),
        "triple_base_repeat_title": triple_btu,
        "excess_title_repeat": triple_btu * (flip_bu.astype(int) - flip_bt.astype(int)),
        "invalid_base": ~valid[b], "invalid_repeat": ~valid[t],
        "invalid_reverse": ~valid[v], "invalid_title": ~valid[u],
    }
    names = list(columns)
    matrix = np.column_stack([columns[name] for name in names]).astype(np.int32)
    return names, matrix, prediction, valid


def measures(sums, names):
    ix = {name: i for i, name in enumerate(names)}

    def ratio(num, den):
        numerator = sums[..., ix[num]] if isinstance(num, str) else num
        denominator = sums[..., ix[den]] if isinstance(den, str) else den
        return np.divide(numerator, denominator,
                         out=np.full(np.shape(numerator), np.nan, dtype=float),
                         where=denominator > 0)

    base = sums[..., ix["base_correct"]]
    reverse = sums[..., ix["reverse_correct"]]
    title = sums[..., ix["title_correct"]]
    return {
        "base_accuracy": ratio("base_correct", "n"),
        "repeat_accuracy": ratio("repeat_correct", "n"),
        "reverse_accuracy": ratio("reverse_correct", "n"),
        "title_removed_accuracy": ratio("title_correct", "n"),
        "robust_correct": ratio("robust_correct", "n"),
        "title_robust_correct": ratio("title_robust_correct", "n"),
        "reverse_correction": ratio("reverse_correction", "n"),
        "reverse_regression": ratio("reverse_regression", "n"),
        "reverse_accuracy_delta": ratio(reverse - base, "n"),
        "title_correction": ratio("title_correction", "n"),
        "title_regression": ratio("title_regression", "n"),
        "title_accuracy_delta": ratio(title - base, "n"),
        "reverse_flip_valid": ratio("flip_base_reverse", "valid_base_reverse"),
        "repeat_flip_valid": ratio("flip_base_repeat", "valid_base_repeat"),
        "title_flip_valid": ratio("flip_base_title", "valid_base_title"),
        "excess_reverse_flip_triple_valid": ratio(
            "excess_reverse_repeat", "triple_base_repeat_reverse"),
        "excess_title_flip_triple_valid": ratio(
            "excess_title_repeat", "triple_base_repeat_title"),
        "invalid_base": ratio("invalid_base", "n"),
        "invalid_repeat": ratio("invalid_repeat", "n"),
        "invalid_reverse": ratio("invalid_reverse", "n"),
        "invalid_title": ratio("invalid_title", "n"),
    }


def summarize(matrix, names, subset, sampled):
    point_sums = matrix[subset].sum(axis=0)
    point = measures(point_sums, names)
    boot_values = {name: [] for name in point}
    for start in range(0, DRAWS, 64):
        idx = sampled[start:start + 64]
        sampled_sums = matrix[idx].sum(axis=1)
        block = measures(sampled_sums, names)
        for name, values in block.items():
            boot_values[name].append(values)
    summary = {}
    for name, value in point.items():
        samples = np.concatenate(boot_values[name])
        finite = samples[np.isfinite(samples)]
        ci = np.quantile(finite, [0.025, 0.975]).tolist() if len(finite) else None
        summary[name] = {
            "estimate": float(value) if np.isfinite(value) else None,
            "ci95": ci,
        }
    counts = {name: int(point_sums[i]) for i, name in enumerate(names)}
    assert counts["reverse_correct"] - counts["base_correct"] == (
        counts["reverse_correction"] - counts["reverse_regression"])
    assert counts["title_correct"] - counts["base_correct"] == (
        counts["title_correction"] - counts["title_regression"])
    return {"n": int(len(subset)), "counts": counts, "metrics": summary}


def confusion(gold, pred, subset):
    matrix = {label: {candidate: 0 for candidate in (*LABELS, "INVALID")}
              for label in LABELS}
    for i in subset:
        matrix[str(gold[i])][str(pred[i])] += 1
    return matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-four", action="store_true",
                        help="Analyze four completed systems into preview-only output files")
    args = parser.parse_args()
    models = tuple(model for model in MODELS if model != "qwen3_8b") if args.preview_four else MODELS
    suffix = "_preview_four" if args.preview_four else ""
    summary_path = OUT / f"summary{suffix}.json"
    cases_path = OUT / f"case_level{suffix}.json"
    if summary_path.exists() or cases_path.exists():
        raise FileExistsError("SciFact3 analysis output already exists: refusing overwrite")
    manifest = read(OUT / "manifest.json")
    frozen_path = OUT / "frozen.json"
    assert sha(frozen_path) == manifest["prepared_sha256"]
    assert read(OUT / "validation.json")["frozen_sha256"] == manifest["prepared_sha256"]
    assert read(OUT / "input_audit.json")["frozen_sha256"] == manifest["prepared_sha256"]
    frozen = read(frozen_path)
    suites = {suite["condition"]: suite for suite in frozen["suites"]}
    assert list(suites) == list(CONDITIONS)
    base_cases = suites["base"]["cases"]
    assert len(base_cases) == 180
    assert len({c["source_id"]["claim_id"] for c in base_cases}) == 180
    assert len({c["source_id"]["doc_id"] for c in base_cases}) == 180
    for condition, suite in suites.items():
        assert len(suite["cases"]) == 180
        for base_case, case in zip(base_cases, suite["cases"]):
            assert base_case["id"] == case["id"]
            assert case["request_sha256"] == digest(request(case))
    gold = np.array([case["gold"]["answer"]["label"] for case in base_cases], dtype=object)
    sampled, by_label = bootstrap_indices(gold)
    hashes = {"frozen_sha256": manifest["prepared_sha256"],
              "manifest_sha256": sha(OUT / "manifest.json"),
              "validation_sha256": sha(OUT / "validation.json"),
              "input_audit_sha256": sha(OUT / "input_audit.json")}
    result = {
        "protocol": frozen["protocol"],
        "models": {model: DISPLAY[model] for model in models},
        "preview_four": args.preview_four,
        "seed": SEED, "draws": DRAWS,
        "definitions": {
            "primary_unit": "one cited claim--abstract pair; selected claim and document IDs are both unique",
            "reference": "source SUPPORT/CONTRADICT evidence entry; derived NOINFO only for a cited doc without evidence entry",
            "correctness": "valid prediction matches the reference; invalid/error is not correct",
            "robust_correct": "reference-correct in both base and reversed-option-order",
            "flip": "unequal selected labels among pairs valid in both compared conditions",
            "excess_flip": "mean of reversal/title flip minus exact-repeat flip on triple-valid cases",
            "interval": "10,000 paired, label-stratified claim/document-cluster percentile bootstrap draws; pointwise descriptive 95% intervals",
            "sampling": "fixed model-blind balanced 60/60/60 selection; intervals do not estimate natural SciFact prevalence",
        },
        "input_hashes": hashes,
        "systems": {},
    }
    case_level = {"frozen_sha256": manifest["prepared_sha256"], "systems": {}}
    for model in models:
        raw = {condition: load_raw(model, condition, suites[condition]["cases"],
                                   manifest, hashes)
               for condition in CONDITIONS}
        records = {condition: [raw[condition][case["id"], "answer"] for case in base_cases]
                   for condition in CONDITIONS}
        names, matrix, predictions, valid = indicator_matrix(records, gold)
        all_indices = np.arange(len(base_cases))
        slices = {"all": summarize(matrix, names, all_indices, sampled["all"])}
        for label in LABELS:
            slices[label] = summarize(matrix, names, by_label[label], sampled[label])
        for slice_name, indices in [("all", all_indices), *by_label.items()]:
            slices[slice_name]["confusion"] = {
                condition: confusion(gold, predictions[condition], indices)
                for condition in CONDITIONS}
            slices[slice_name]["predicted_label_counts"] = {
                condition: dict(Counter(predictions[condition][indices]))
                for condition in CONDITIONS}
        result["systems"][model] = slices
        case_level["systems"][model] = [{
            "id": case["id"], "claim_id": case["source_id"]["claim_id"],
            "document_id": case["source_id"]["doc_id"], "gold": str(gold[i]),
            "prediction": {condition: str(predictions[condition][i]) for condition in CONDITIONS},
            "valid": {condition: bool(valid[condition][i]) for condition in CONDITIONS},
        } for i, case in enumerate(base_cases)]
    write(summary_path, result)
    write(cases_path, case_level)
    for model in models:
        row = result["systems"][model]["all"]
        counts = row["counts"]
        print(DISPLAY[model], "base", counts["base_correct"],
              "robust", counts["robust_correct"],
              "reverse C/R", counts["reverse_correction"], counts["reverse_regression"],
              "title C/R", counts["title_correction"], counts["title_regression"],
              "invalid", counts["invalid_base"], counts["invalid_repeat"],
              counts["invalid_reverse"], counts["invalid_title"])


if __name__ == "__main__":
    main()
