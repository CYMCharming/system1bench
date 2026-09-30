"""Audit identical requests evaluated in the old balanced and fresh census runs."""

import gzip
import json
from collections import Counter
from pathlib import Path

from system1bench.common import sha, write

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "research/scifact3_v1"
NEW = ROOT / "research/scifact3_census_v1"
MODELS = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")


def read(path):
    return json.loads(path.read_text())


def rows(out, model, condition):
    directory = out / "results" / ("jev-1.13.0" if model == "jev-1.13.0" else f"local/{model}")
    metadata = read(directory / "metadata.json")
    assert metadata["status"] == "DONE"
    suite = f"scifact3_{condition}"
    path = directory / f"{suite}.json.gz"
    assert sha(path) == metadata["suites"][suite]["sha256"]
    payload = json.loads(gzip.decompress(path.read_bytes()))
    return ({r["id"]: r for r in payload["rows"]},
            {b["id"]: b["requests"] for b in payload.get("batches", [])})


def decision(row):
    return row["prediction"] if row["error"] is None and row["prediction"] in LABELS else "INVALID"


def main():
    old_frozen = read(OLD / "frozen.json")
    new_frozen = read(NEW / "frozen.json")
    assert sha(OLD / "frozen.json") == read(OLD / "manifest.json")["prepared_sha256"]
    assert sha(NEW / "frozen.json") == read(NEW / "manifest.json")["prepared_sha256"]
    old_cases = {c["id"]: c for c in old_frozen["suites"][0]["cases"]}
    new_cases = {c["id"]: c for c in new_frozen["suites"][0]["cases"]}
    assert len(old_cases) == 180 and set(old_cases) <= set(new_cases)
    result = {
        "old_frozen_sha256": sha(OLD / "frozen.json"),
        "new_frozen_sha256": sha(NEW / "frozen.json"),
        "overlapping_pairs": 180,
        "identical_requests_verified": 720,
        "description": "same case/payload re-evaluated in fresh complete census; changes may reflect run, batch composition, or hosted stochasticity, not changed task content",
        "prompt_hash_scope": "LLM adapters expose prompt_token_sha256; Laya and Jev do not, so null is not a mismatch",
        "batch_scope": "local runner batch_id and actual request count; Jev API requests are independent and have no batch_id",
        "models": {},
    }
    for condition in CONDITIONS:
        old_s = next(s for s in old_frozen["suites"] if s["condition"] == condition)
        new_s = next(s for s in new_frozen["suites"] if s["condition"] == condition)
        new_lookup = {c["id"]: c for c in new_s["cases"]}
        for old_case in old_s["cases"]:
            assert old_case["request_sha256"] == new_lookup[old_case["id"]]["request_sha256"]
            assert old_case["gold"] == new_lookup[old_case["id"]]["gold"]
    for model in MODELS:
        result["models"][model] = {}
        for condition in CONDITIONS:
            (old_rows, old_batches), (new_rows, new_batches) = (
                rows(OLD, model, condition), rows(NEW, model, condition))
            assert set(old_rows) == set(old_cases) and set(old_cases) <= set(new_rows)
            by_gold = {label: {"changed": 0, "old_correct": 0, "fresh_correct": 0} for label in LABELS}
            changes = []
            old_correct = fresh_correct = 0
            prompt_hash_available = prompt_hash_equal = 0
            for case_id, case in old_cases.items():
                old_row, fresh_row = old_rows[case_id], new_rows[case_id]
                assert old_row["request_sha256"] == fresh_row["request_sha256"]
                gold = case["gold"]["answer"]["label"]
                assert old_row["gold"] == fresh_row["gold"] == gold
                old_pred, fresh_pred = decision(old_row), decision(fresh_row)
                old_prompt_hash = old_row.get("audit", {}).get("prompt_token_sha256")
                fresh_prompt_hash = fresh_row.get("audit", {}).get("prompt_token_sha256")
                if old_prompt_hash is not None or fresh_prompt_hash is not None:
                    assert old_prompt_hash is not None and fresh_prompt_hash is not None
                    prompt_hash_available += 1
                    prompt_hash_equal += int(old_prompt_hash == fresh_prompt_hash)
                    assert old_prompt_hash == fresh_prompt_hash, (model, condition, case_id)
                old_correct += int(old_pred == gold)
                fresh_correct += int(fresh_pred == gold)
                by_gold[gold]["old_correct"] += int(old_pred == gold)
                by_gold[gold]["fresh_correct"] += int(fresh_pred == gold)
                if old_pred != fresh_pred:
                    by_gold[gold]["changed"] += 1
                    changes.append({"id": case_id, "gold": gold, "old_prediction": old_pred,
                                    "fresh_prediction": fresh_pred,
                                    "request_sha256": old_row["request_sha256"],
                                    "old_prompt_token_sha256": old_prompt_hash,
                                    "fresh_prompt_token_sha256": fresh_prompt_hash,
                                    "prompt_hash_equal": (old_prompt_hash == fresh_prompt_hash
                                                          if old_prompt_hash is not None else None),
                                    "old_batch_id": old_row.get("batch_id"),
                                    "old_batch_size": old_batches.get(old_row.get("batch_id")),
                                    "fresh_batch_id": fresh_row.get("batch_id"),
                                    "fresh_batch_size": new_batches.get(fresh_row.get("batch_id"))})
            result["models"][model][condition] = {
                "n": 180, "changed": len(changes), "old_correct": old_correct,
                "fresh_correct": fresh_correct, "by_gold": by_gold, "changes": changes,
                "prompt_hash_available": prompt_hash_available,
                "prompt_hash_equal": prompt_hash_equal,
            }
    target = NEW / "overlap_audit.json"
    if target.exists():
        raise FileExistsError("Overlap audit already exists")
    write(target, result)
    for model in MODELS:
        for condition in CONDITIONS:
            row = result["models"][model][condition]
            print(model, condition, "changed", row["changed"], "correct",
                  row["old_correct"], row["fresh_correct"])


if __name__ == "__main__":
    main()
