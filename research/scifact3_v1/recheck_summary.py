"""Independent stdlib cross-check of SciFact3 summary counts from raw files."""

import gzip
import json
from collections import Counter
from pathlib import Path

from system1bench.common import sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_v1"
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
MODELS = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")


def read(path):
    return json.loads(path.read_text())


def raw_rows(model, condition):
    directory = OUT / "results" / (
        "jev-1.13.0" if model == "jev-1.13.0" else f"local/{model}")
    metadata = read(directory / "metadata.json")
    assert metadata["status"] == "DONE"
    name = f"scifact3_{condition}"
    path = directory / f"{name}.json.gz"
    assert sha(path) == metadata["suites"][name]["sha256"]
    payload = json.loads(gzip.decompress(path.read_bytes()))
    return {row["id"]: row for row in payload["rows"]}


def main():
    frozen = read(OUT / "frozen.json")
    manifest = read(OUT / "manifest.json")
    summary = read(OUT / "summary.json")
    assert sha(OUT / "frozen.json") == manifest["prepared_sha256"]
    base = frozen["suites"][0]["cases"]
    original_two_class = read(ROOT / "research/domain_expansion_v1/frozen.json")
    old_science = next(suite["cases"] for suite in original_two_class["suites"]
                       if suite["name"] == "scifact_base")
    old_pairs = {(c["source_id"]["claim_id"], c["source_id"]["doc_id"])
                 for c in old_science}
    new_by_label = {label: {
        (c["source_id"]["claim_id"], c["source_id"]["doc_id"])
        for c in base if c["gold"]["answer"]["label"] == label}
        for label in ("SUPPORT", "CONTRADICT", "NOINFO")}
    overlap = {label: len(pairs & old_pairs) for label, pairs in new_by_label.items()}
    assert overlap["NOINFO"] == 0
    comparisons = {}
    for model in MODELS:
        rows = {condition: raw_rows(model, condition) for condition in CONDITIONS}
        assert all(set(table) == {case["id"] for case in base}
                   for table in rows.values())
        by_label = {}
        for label in ("SUPPORT", "CONTRADICT", "NOINFO", "all"):
            cases = [case for case in base
                     if label == "all" or case["gold"]["answer"]["label"] == label]
            count = Counter()
            confusion = {condition: Counter() for condition in CONDITIONS}
            for case in cases:
                case_id = case["id"]
                gold = case["gold"]["answer"]["label"]
                decisions = {}
                for condition in CONDITIONS:
                    row = rows[condition][case_id]
                    valid = row["error"] is None and row["prediction"] in (
                        "SUPPORT", "CONTRADICT", "NOINFO")
                    prediction = row["prediction"] if valid else "INVALID"
                    decisions[condition] = (prediction, valid)
                    confusion[condition][(gold, prediction)] += 1
                    count[f"invalid_{condition}"] += int(not valid)
                    count[f"{condition}_correct"] += int(valid and prediction == gold)
                b, t, v, u = (decisions[condition] for condition in CONDITIONS)
                bc, vc, uc = (value[1] and value[0] == gold for value in (b, v, u))
                count["robust_correct"] += int(bc and vc)
                count["title_robust_correct"] += int(bc and uc)
                count["reverse_correction"] += int(not bc and vc)
                count["reverse_regression"] += int(bc and not vc)
                count["title_correction"] += int(not bc and uc)
                count["title_regression"] += int(bc and not uc)
                for suffix, other in (("reverse", v), ("repeat", t), ("title", u)):
                    if b[1] and other[1]:
                        count[f"valid_base_{suffix}"] += 1
                        count[f"flip_base_{suffix}"] += int(b[0] != other[0])
            expected = summary["systems"][model][label]["counts"]
            mapping = {
                "base_correct": "base_correct",
                "exact_repeat_correct": "repeat_correct",
                "reversed_option_order_correct": "reverse_correct",
                "title_removed_correct": "title_correct",
                "robust_correct": "robust_correct",
                "title_robust_correct": "title_robust_correct",
                "reverse_correction": "reverse_correction",
                "reverse_regression": "reverse_regression",
                "title_correction": "title_correction",
                "title_regression": "title_regression",
                "valid_base_reverse": "valid_base_reverse",
                "flip_base_reverse": "flip_base_reverse",
                "valid_base_repeat": "valid_base_repeat",
                "flip_base_repeat": "flip_base_repeat",
                "valid_base_title": "valid_base_title",
                "flip_base_title": "flip_base_title",
                "invalid_base": "invalid_base",
                "invalid_exact_repeat": "invalid_repeat",
                "invalid_reversed_option_order": "invalid_reverse",
                "invalid_title_removed": "invalid_title",
            }
            for actual_name, summary_name in mapping.items():
                assert count[actual_name] == expected[summary_name], (
                    model, label, actual_name, count[actual_name], expected[summary_name])
            for condition in CONDITIONS:
                for (reference, prediction), observed in confusion[condition].items():
                    assert observed == summary["systems"][model][label]["confusion"][condition][reference][prediction]
            by_label[label] = {"n": len(cases),
                               "base_correct": count["base_correct"],
                               "robust_correct": count["robust_correct"],
                               "reverse_flip": count["flip_base_reverse"],
                               "repeat_flip": count["flip_base_repeat"],
                               "title_flip": count["flip_base_title"]}
        comparisons[model] = by_label
    report = {
        "frozen_sha256": manifest["prepared_sha256"],
        "summary_sha256": sha(OUT / "summary.json"),
        "independently_recomputed_models": list(MODELS),
        "raw_count_and_confusion_checks": "all matched",
        "v1_two_class_selected_pairs": len(old_pairs),
        "v2_three_class_selected_pairs": len(base),
        "selected_pair_overlap_by_label": overlap,
        "systems": comparisons,
    }
    target = OUT / "analysis_validation.json"
    if target.exists():
        raise FileExistsError("Analysis validation record exists: refusing overwrite")
    write(target, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
