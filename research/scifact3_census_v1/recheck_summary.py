"""Independent stdlib-only count/confusion check against fresh census outputs."""

import gzip
import json
from collections import Counter
from pathlib import Path

from system1bench.common import sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_census_v1"
MODELS = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")


def read(path):
    return json.loads(path.read_text())


def raw_rows(model, condition):
    directory = OUT / "results" / ("jev-1.13.0" if model == "jev-1.13.0" else f"local/{model}")
    metadata = read(directory / "metadata.json")
    assert metadata["status"] == "DONE"
    name = f"scifact3_{condition}"
    path = directory / f"{name}.json.gz"
    assert sha(path) == metadata["suites"][name]["sha256"]
    result = json.loads(gzip.decompress(path.read_bytes()))
    return {row["id"]: row for row in result["rows"]}


def main():
    frozen = read(OUT / "frozen.json")
    manifest = read(OUT / "manifest.json")
    summary = read(OUT / "summary.json")
    assert sha(OUT / "frozen.json") == manifest["prepared_sha256"]
    base = frozen["suites"][0]["cases"]
    assert len(base) == 339
    report = {"frozen_sha256": manifest["prepared_sha256"],
              "summary_sha256": sha(OUT / "summary.json"), "models": {},
              "raw_counts_confusions_and_transitions": "all matched"}
    for model in MODELS:
        tables = {condition: raw_rows(model, condition) for condition in CONDITIONS}
        assert all(set(rows) == {case["id"] for case in base} for rows in tables.values())
        report["models"][model] = {}
        for cohort, eligible in (
            ("all339", lambda c: True),
            ("complement159", lambda c: not c["prior_three_choice_selected"]),
            ("prior_selected180", lambda c: c["prior_three_choice_selected"]),
        ):
            report["models"][model][cohort] = {}
            for label in ("all", *LABELS):
                cases = [case for case in base if eligible(case) and
                         (label == "all" or case["gold"]["answer"]["label"] == label)]
                counts = Counter()
                confusion = {condition: Counter() for condition in CONDITIONS}
                transition = Counter()
                margins = {condition: Counter() for condition in CONDITIONS}
                for case in cases:
                    gold = case["gold"]["answer"]["label"]
                    values = {}
                    for condition in CONDITIONS:
                        row = tables[condition][case["id"]]
                        assert row["gold"] == gold and row["request_sha256"] == next(
                            variant["request_sha256"] for variant in frozen["suites"][CONDITIONS.index(condition)]["cases"]
                            if variant["id"] == case["id"])
                        valid = row["error"] is None and row["prediction"] in LABELS
                        pred = row["prediction"] if valid else "INVALID"
                        values[condition] = (pred, valid)
                        confusion[condition][(gold, pred)] += 1
                        margins[condition][pred] += 1
                        counts[{"base": "base_valid", "exact_repeat": "repeat_valid",
                                "reversed_option_order": "reverse_valid", "title_removed": "title_valid"}[condition]] += int(valid)
                        counts[{"base": "base_correct", "exact_repeat": "repeat_correct",
                                "reversed_option_order": "reverse_correct", "title_removed": "title_correct"}[condition]] += int(valid and pred == gold)
                    b, rep, rev, title = (values[c] for c in CONDITIONS)
                    transition[(b[0], rev[0])] += 1
                    counts["robust_correct"] += int(b[0] == gold and rev[0] == gold)
                    counts["reverse_correction"] += int(b[0] != gold and rev[0] == gold)
                    counts["reverse_regression"] += int(b[0] == gold and rev[0] != gold)
                    counts["title_correction"] += int(b[0] != gold and title[0] == gold)
                    counts["title_regression"] += int(b[0] == gold and title[0] != gold)
                    for other, den, num in (
                        (rep, "base_repeat_valid", "repeat_flip"),
                        (rev, "base_reverse_valid", "reverse_flip"),
                        (title, "base_title_valid", "title_flip"),
                    ):
                        if b[1] and other[1]:
                            counts[den] += 1
                            counts[num] += int(b[0] != other[0])
                    counts["base_noinfo_to_other"] += int(b[0] == "NOINFO" and rev[1] and rev[0] != "NOINFO")
                    counts["base_other_to_noinfo"] += int(b[0] != "NOINFO" and b[1] and rev[0] == "NOINFO")
                expected = summary["systems"][model][cohort][label]
                assert len(cases) == expected["n"]
                for key, observed in counts.items():
                    assert observed == expected["counts"][key], (model, cohort, label, key, observed)
                for condition in CONDITIONS:
                    assert dict(margins[condition]) == expected["prediction_marginals"][condition]
                    for (reference, prediction), observed in confusion[condition].items():
                        assert observed == expected["confusion"][condition][reference][prediction]
                for (before, after), observed in transition.items():
                    assert observed == expected["base_to_reverse"][before][after]
                report["models"][model][cohort][label] = {
                    "n": len(cases), "base_correct": counts["base_correct"],
                    "reverse_correct": counts["reverse_correct"],
                    "reverse_flip": counts["reverse_flip"],
                    "repeat_flip": counts["repeat_flip"],
                    "base_noinfo_to_other": counts["base_noinfo_to_other"],
                }
    output = OUT / "analysis_validation.json"
    if output.exists():
        raise FileExistsError("Validation output already exists")
    write(output, report)
    print("Verified", len(MODELS), "systems × 3 cohorts × 4 reference slices against raw files")


if __name__ == "__main__":
    main()
