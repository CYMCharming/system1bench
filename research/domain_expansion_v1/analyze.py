"""Recompute paired legal/scientific reliability from frozen raw outputs."""

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from system1bench.common import digest, read, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/domain_expansion_v1"
MODELS = ["english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0"]
DISPLAY = {"english": "Laya English", "multilingual": "Laya Multilingual",
           "llama31_8b_instruct": "Llama 3.1 8B", "qwen3_8b": "Qwen3 8B",
           "jev-1.13.0": "Jev 1.13"}
SEED = 20260930
DRAWS = 10000


def result_directory(model):
    root = OUT / "results"
    return root / ("jev-1.13.0-continue-invalid" if model == "jev-1.13.0" else f"local/{model}")


def load_rows(model, suite, cases, hashes):
    directory = result_directory(model)
    meta_path = directory / "metadata.json"
    metadata = read(meta_path)
    assert metadata["status"] == "DONE", (model, metadata["status"])
    path = directory / f"{suite}.json.gz"
    assert sha(path) == metadata["suites"][suite]["sha256"]
    data = json.loads(gzip.decompress(path.read_bytes()))
    assert data["signature"]["prepared_sha256"] == hashes["frozen_sha256"] if model != "jev-1.13.0" else data["signature"]["frozen_sha256"] == hashes["frozen_sha256"]
    rows = {(r["id"], r["qid"]): r for r in data["rows"]}
    assert len(rows) == len(cases) == len(data["rows"])
    for case in cases:
        row = rows[case["id"], "answer"]
        assert row["gold"] == case["gold"]["answer"]["label"]
        assert row["request_sha256"] == case["request_sha256"]
        assert row["error"] is not None or row["prediction"] in case["questions"]["answer"]["criteria"]
    hashes[str(path.relative_to(ROOT))] = sha(path)
    return rows


def summarize_cases(cases, rng, group_key="group"):
    groups = defaultdict(list)
    for row in cases:
        groups[row[group_key]].append(row)
    # Columns: denominator, base correct, reverse correct, both correct,
    # correction, regression, exact-repeat correct, reversal valid/flip,
    # repeat valid/flip, triple valid, paired flip difference,
    # invalid base/repeat/reverse.
    matrix = np.zeros((len(groups), 15), dtype=np.int64)
    for i, rows in enumerate(groups.values()):
        for r in rows:
            b, t, v = (r[k] for k in ["base", "exact_repeat", "reversed_option_order"])
            gold = r["gold"]
            pb, pt, pv = b["prediction"], t["prediction"], v["prediction"]
            bc, tc, vc = pb == gold, pt == gold, pv == gold
            valid_b = pb is not None and b["error"] is None
            valid_t = pt is not None and t["error"] is None
            valid_v = pv is not None and v["error"] is None
            triple = valid_b and valid_t and valid_v
            matrix[i] += np.array([
                1, bc, vc, bc and vc, not bc and vc, bc and not vc, tc,
                valid_b and valid_v, valid_b and valid_v and pb != pv,
                valid_b and valid_t, valid_b and valid_t and pb != pt,
                triple, triple * ((pb != pv) - (pb != pt)),
                not valid_b, not valid_t], dtype=np.int64)
            # Reversal invalid has its own count outside the compact bootstrap matrix.
    def measures(sums):
        n = sums[..., 0]
        def ratio(a, b):
            return np.divide(a, b, out=np.full(np.shape(a), np.nan, dtype=float), where=b > 0)
        return np.stack([
            ratio(sums[..., 1], n), ratio(sums[..., 2], n),
            ratio(sums[..., 3], n), ratio(sums[..., 4], n), ratio(sums[..., 5], n),
            ratio(sums[..., 6], n),
            ratio(sums[..., 8], sums[..., 7]), ratio(sums[..., 10], sums[..., 9]),
            ratio(sums[..., 12], sums[..., 11]),
            ratio(sums[..., 2] - sums[..., 1], n),
            ratio(sums[..., 13], n), ratio(sums[..., 14], n),
        ], axis=-1)
    point_counts = matrix.sum(axis=0)
    point = measures(point_counts)
    boots = []
    for start in range(0, DRAWS, 64):
        k = min(64, DRAWS - start)
        ix = rng.integers(0, len(matrix), size=(k, len(matrix)))
        boots.append(measures(matrix[ix].sum(axis=1)))
    boots = np.concatenate(boots, axis=0)
    names = ["base_accuracy", "reverse_accuracy", "robust_correct", "correction", "regression",
             "repeat_accuracy", "reverse_flip_valid", "repeat_flip_valid", "excess_flip_triple_valid",
             "accuracy_delta", "invalid_base", "invalid_repeat"]
    summary = {name: {"estimate": float(point[j]),
                      "ci95": [float(v) for v in np.nanquantile(boots[:, j], [0.025, 0.975])]}
               for j, name in enumerate(names)}
    summary.update(n=int(point_counts[0]), clusters=len(groups),
                   count_base_correct=int(point_counts[1]), count_reverse_correct=int(point_counts[2]),
                   count_both_correct=int(point_counts[3]), count_correction=int(point_counts[4]),
                   count_regression=int(point_counts[5]),
                   count_reverse_flip_valid=int(point_counts[8]),
                   count_repeat_flip_valid=int(point_counts[10]),
                   n_reverse_flip_valid=int(point_counts[7]), n_repeat_flip_valid=int(point_counts[9]),
                   n_triple_valid=int(point_counts[11]),
                   invalid_reverse=sum(r["reversed_option_order"]["error"] is not None for r in cases),
                   reference_label_counts=dict(Counter(r["gold"] for r in cases)))
    assert summary["count_reverse_correct"] - summary["count_base_correct"] == (
        summary["count_correction"] - summary["count_regression"])
    assert summary["count_both_correct"] + summary["count_regression"] == summary["count_base_correct"]
    return summary


def main():
    manifest = read(OUT / "manifest.json")
    frozen_path = OUT / "frozen.json"
    assert sha(frozen_path) == manifest["prepared_sha256"]
    frozen = read(frozen_path)
    suites = {s["name"]: s for s in frozen["suites"]}
    assert len(suites) == 6
    hashes = {"frozen_sha256": manifest["prepared_sha256"], "manifest_sha256": sha(OUT / "manifest.json")}
    result = dict(protocol="system1bench-domain-expansion-v1",
                  definitions={"primary_unit": "source pair; cluster=contract document or claim",
                               "invalid": "invalid/missing prediction counts as not reference-correct; flips require two valid predictions",
                               "robust_correct": "reference-correct in both base and reverse",
                               "excess_flip_triple_valid": "mean[flip(base,reverse)-flip(base,repeat)] over triple-valid pairs",
                               "interval": "10,000-draw source-cluster percentile bootstrap, pointwise descriptive"},
                  models=DISPLAY, seed=SEED, draws=DRAWS, input_hashes=hashes,
                  sources={})
    rng = np.random.default_rng(SEED)
    for source in ["contractnli", "scifact"]:
        base = suites[f"{source}_base"]["cases"]
        source_result = dict(n=len(base), systems={})
        for model in MODELS:
            by_condition = {}
            for condition in ["base", "exact_repeat", "reversed_option_order"]:
                suite = f"{source}_{condition}"
                by_condition[condition] = load_rows(model, suite, suites[suite]["cases"], hashes)
            joined = []
            for c in base:
                if c["request_sha256"] != digest(request(c)):
                    raise ValueError("Frozen request altered")
                cid = c["id"]
                records = {condition: by_condition[condition][cid, "answer"] for condition in by_condition}
                assert records["base"]["gold"] == records["exact_repeat"]["gold"] == records["reversed_option_order"]["gold"]
                joined.append(dict(id=cid, group=c["group"],
                                   abstract_group=str(c["source_id"].get("doc_id", "")),
                                   gold=c["gold"]["answer"]["label"], **records))
            primary = summarize_cases(joined, rng)
            if source == "scifact":
                alternate = summarize_cases(joined, np.random.default_rng(SEED + 1),
                                            group_key="abstract_group")
                assert alternate["n"] == primary["n"] and alternate["clusters"] == 111
                primary["abstract_cluster_sensitivity"] = {
                    "clusters": alternate["clusters"],
                    "accuracy_delta": alternate["accuracy_delta"],
                    "robust_correct": alternate["robust_correct"],
                    "reverse_flip_valid": alternate["reverse_flip_valid"]}
            source_result["systems"][model] = primary
        result["sources"][source] = source_result
    write(OUT / "summary.json", result)
    for source, source_result in result["sources"].items():
        print(source, source_result["n"])
        for model, row in source_result["systems"].items():
            print(DISPLAY[model], "base", row["count_base_correct"],
                  "robust", row["count_both_correct"], "correction", row["count_correction"],
                  "regression", row["count_regression"], "repeat_flip", row["count_repeat_flip_valid"],
                  "reverse_flip", row["count_reverse_flip_valid"], "invalid_reverse", row["invalid_reverse"])


if __name__ == "__main__":
    main()
