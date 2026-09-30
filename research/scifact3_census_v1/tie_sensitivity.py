"""SHA-verified, source-text-free decoder-tie replay for the SciFact3 census.

Run from the repository or by absolute path with Python 3 standard library.
This is a post-hoc sensitivity, not another inference run or a new estimand.
"""

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "research/scifact3_census_v1"
MODELS = ("llama31_8b_instruct", "qwen3_8b")
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
COUNT_KEYS = dict(base="base_correct", exact_repeat="repeat_correct",
                  reversed_option_order="reverse_correct", title_removed="title_correct")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def load_raw(model: str, condition: str, summary: dict) -> tuple[dict, str]:
    path = HERE / "results/local" / model / f"scifact3_{condition}.json.gz"
    key = str(path.relative_to(ROOT))
    digest = sha(path)
    assert digest == summary["input_hashes"][key], key
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    rows = {row["id"]: row for row in data["rows"]}
    assert len(data["rows"]) == len(rows) == 339
    return rows, digest


def decode(row: dict) -> tuple[str, tuple[str, ...]]:
    """Fixed semantic priority, independent of question/criteria insertion order."""
    assert row["error"] is None and row["prediction"] in LABELS
    assert set(row["labels"]) == set(LABELS) and len(row["labels"]) == 3
    answer = row["answer"]
    probabilities = answer["probabilities"]
    logits = answer["candidate_logits"]
    assert set(probabilities) == set(LABELS) and len(logits) == 3
    top_probability = max(probabilities.values())
    tied = tuple(label for label in LABELS if probabilities[label] == top_probability)
    logit_by_label = dict(zip(row["labels"], logits))
    top_logit = max(logits)
    assert set(tied) == {label for label in LABELS if logit_by_label[label] == top_logit}
    assert row["prediction"] in tied
    return tied[0], tied


def summarize_view(rows: dict, prediction: dict) -> dict:
    counts = Counter()
    by_gold = {label: Counter() for label in LABELS}
    for condition in CONDITIONS:
        for case_id, row in rows[condition].items():
            pred = prediction[condition][case_id]
            counts[f"correct/{condition}"] += pred == row["gold"]
            by_gold[row["gold"]][condition] += pred == row["gold"]
    base = prediction["base"]
    for condition in CONDITIONS[1:]:
        counts[f"base_to_{condition}_flips"] = sum(
            base[case_id] != prediction[condition][case_id] for case_id in base)
    transition = {before: {after: 0 for after in LABELS} for before in LABELS}
    for case_id in base:
        transition[base[case_id]][prediction["reversed_option_order"][case_id]] += 1
    return dict(correct={condition: counts[f"correct/{condition}"] for condition in CONDITIONS},
                by_gold_correct={gold: dict(values) for gold, values in by_gold.items()},
                base_relative_flips={condition: counts[f"base_to_{condition}_flips"]
                                     for condition in CONDITIONS[1:]},
                base_to_reversal=transition)


def main() -> None:
    target = HERE / "tie_sensitivity.json"
    if target.exists():
        raise FileExistsError("Never overwrite the recorded tie sensitivity")
    summary_path = HERE / "summary.json"
    summary = load(summary_path)
    assert summary["cohorts"]["all339"]["n"] == 339
    report = dict(version="scifact3-census-tie-sensitivity-v1",
                  status="VERIFIED", scope="fixed 339 dev cited-pair census",
                  interpretation="post-hoc offline decoder sensitivity; original native records retained",
                  semantic_tie_priority=list(LABELS),
                  summary_sha256=sha(summary_path), models={})
    for model in MODELS:
        loaded = {condition: load_raw(model, condition, summary) for condition in CONDITIONS}
        rows = {condition: pair[0] for condition, pair in loaded.items()}
        ids = set(rows["base"])
        assert all(set(rows[condition]) == ids for condition in CONDITIONS)
        assert all(rows[condition][case_id]["gold"] == rows["base"][case_id]["gold"]
                   for condition in CONDITIONS for case_id in ids)
        native = {condition: {case_id: row["prediction"] for case_id, row in records.items()}
                  for condition, records in rows.items()}
        common = {condition: {} for condition in CONDITIONS}
        ties = {}
        for condition, records in rows.items():
            tied_cases = []
            changed_cases = []
            for case_id, row in records.items():
                fixed, tied = decode(row)
                common[condition][case_id] = fixed
                if len(tied) > 1:
                    tied_cases.append(dict(id=case_id, gold=row["gold"],
                                           tied_labels=list(tied), native=row["prediction"],
                                           common=fixed))
                if fixed != row["prediction"]:
                    changed_cases.append(case_id)
            assert set(changed_cases) <= {case["id"] for case in tied_cases}
            ties[condition] = dict(top_ties=len(tied_cases), native_to_common_changes=len(changed_cases),
                                   tied_cases=tied_cases)
        native_stats = summarize_view(rows, native)
        common_stats = summarize_view(rows, common)
        saved = summary["systems"][model]["all339"]["all"]
        for condition in CONDITIONS:
            assert native_stats["correct"][condition] == saved["counts"][COUNT_KEYS[condition]]
        assert native_stats["base_relative_flips"]["reversed_option_order"] == saved["counts"]["reverse_flip"]
        assert native_stats["base_relative_flips"]["exact_repeat"] == saved["counts"]["repeat_flip"]
        assert native_stats["base_relative_flips"]["title_removed"] == saved["counts"]["title_flip"]
        assert all(native_stats["base_to_reversal"][before][after] == saved["base_to_reverse"][before][after]
                   for before in LABELS for after in LABELS)
        assert all(ties[condition]["native_to_common_changes"] == 0
                   for condition in ("base", "exact_repeat", "title_removed"))
        report["models"][model] = dict(
            n=339, raw_sha256={condition: pair[1] for condition, pair in loaded.items()},
            ties=ties, native=native_stats, common_tie=common_stats,
            accuracy_change_due_to_common_tie={condition: common_stats["correct"][condition]
                                               - native_stats["correct"][condition]
                                               for condition in CONDITIONS},
            reversal_flip_change_due_to_common_tie=(
                common_stats["base_relative_flips"]["reversed_option_order"]
                - native_stats["base_relative_flips"]["reversed_option_order"]),
        )
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("VERIFIED census tie sensitivity", target)


if __name__ == "__main__":
    main()
