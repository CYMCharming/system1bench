"""Independent stdlib-only raw-row verification of domain result point estimates."""

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/domain_expansion_v1"
MODELS = ["english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0"]
CONDITIONS = ["base", "exact_repeat", "reversed_option_order"]


def load(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(model, suite):
    directory = OUT / "results" / ("jev-1.13.0-continue-invalid" if model == "jev-1.13.0"
                                    else f"local/{model}")
    metadata = load(directory / "metadata.json")
    assert metadata["status"] == "DONE"
    path = directory / f"{suite}.json.gz"
    assert sha(path) == metadata["suites"][suite]["sha256"]
    obj = json.loads(gzip.decompress(path.read_bytes()))
    indexed = {r["id"]: r for r in obj["rows"]}
    assert len(indexed) == len(obj["rows"])
    return indexed, path


def main():
    manifest = load(OUT / "manifest.json")
    assert sha(OUT / "frozen.json") == manifest["prepared_sha256"]
    summary = load(OUT / "summary.json")
    assert summary["input_hashes"]["frozen_sha256"] == manifest["prepared_sha256"]
    frozen = load(OUT / "frozen.json")
    suites = {suite["name"]: suite for suite in frozen["suites"]}
    assert len(suites) == 6
    checked = 0
    for source, n in [("contractnli", 144), ("scifact", 120)]:
        cases = {condition: suites[f"{source}_{condition}"]["cases"] for condition in CONDITIONS}
        assert all(len(c) == n for c in cases.values())
        assert len({c["id"] for c in cases["base"]}) == n
        for b, t, v in zip(*(cases[condition] for condition in CONDITIONS)):
            assert b["id"] == t["id"] == v["id"]
            assert b["state"] == t["state"] == v["state"]
            assert b["gold"] == t["gold"] == v["gold"]
            assert b["request_sha256"] == t["request_sha256"] != v["request_sha256"]
            bq, vq = b["questions"]["answer"], v["questions"]["answer"]
            assert bq["instructions"] == vq["instructions"]
            assert list(bq["criteria"]) == list(vq["criteria"])[::-1]
            assert bq["criteria"] == vq["criteria"]
        assert len({c["group"] for c in cases["base"]}) == (91 if source == "contractnli" else 120)
        assert Counter(c["gold"]["answer"]["label"] for c in cases["base"]) == (
            {"Entailment": 48, "Contradiction": 48, "NotMentioned": 48} if source == "contractnli"
            else {"SUPPORT": 60, "CONTRADICT": 60})
        for model in MODELS:
            records = {}
            for condition in CONDITIONS:
                name = f"{source}_{condition}"
                records[condition], path = rows(model, name)
                relative = str(path.relative_to(ROOT))
                assert summary["input_hashes"][relative] == sha(path)
            counts = Counter()
            for case in cases["base"]:
                cid = case["id"]
                gold = case["gold"]["answer"]["label"]
                b, t, v = (records[condition][cid] for condition in CONDITIONS)
                for row, case_condition in zip([b, t, v], CONDITIONS):
                    exact_case = next(c for c in cases[case_condition] if c["id"] == cid)
                    assert row["request_sha256"] == exact_case["request_sha256"]
                    assert row["gold"] == gold
                    assert row["error"] is None and row["prediction"] is not None
                bc, vc = b["prediction"] == gold, v["prediction"] == gold
                counts["base_correct"] += bc
                counts["reverse_correct"] += vc
                counts["both_correct"] += bc and vc
                counts["correction"] += not bc and vc
                counts["regression"] += bc and not vc
                counts["repeat_flip"] += b["prediction"] != t["prediction"]
                counts["reverse_flip"] += b["prediction"] != v["prediction"]
            reported = summary["sources"][source]["systems"][model]
            for key, field in [("base_correct", "count_base_correct"),
                               ("reverse_correct", "count_reverse_correct"),
                               ("both_correct", "count_both_correct"),
                               ("correction", "count_correction"),
                               ("regression", "count_regression"),
                               ("repeat_flip", "count_repeat_flip_valid"),
                               ("reverse_flip", "count_reverse_flip_valid")]:
                assert counts[key] == reported[field], (source, model, key)
            assert abs(reported["accuracy_delta"]["estimate"] -
                       (counts["reverse_correct"] - counts["base_correct"]) / n) < 1e-12
            checked += n
    print(f"VERIFIED {checked} paired model/source decisions, six frozen suites, 30 output files")


if __name__ == "__main__":
    main()
