"""Independently analyze matched prompted-vs-logit decisions, preserving failures."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402
from system1bench.run import read_run  # noqa: E402

HERE = Path(__file__).resolve().parent
MODELS = ("llama31_8b_instruct", "qwen3_8b")
MODES = ("direct", "deliberate")
RESAMPLES = 10_000
SEED = 481516


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] * (hi - index) + ordered[hi] * (index - lo)


def comparison(pairs: list[tuple[dict, dict]]) -> dict:
    # Both prediction fields are strings or None. None is an invalid decision
    # and counts wrong, never as a match on the reference label.
    n = len(pairs)
    prior_right = sum(old["prediction"] == old["gold"] for old, new in pairs)
    new_right = sum(new["prediction"] == new["gold"] for old, new in pairs)
    corrected = sum(old["prediction"] != old["gold"] and new["prediction"] == new["gold"]
                    for old, new in pairs)
    regressed = sum(old["prediction"] == old["gold"] and new["prediction"] != new["gold"]
                    for old, new in pairs)
    changed = sum(old["prediction"] != new["prediction"] for old, new in pairs)
    return dict(n=n, baseline_correct=prior_right, new_correct=new_right,
                baseline_accuracy=prior_right / n, new_accuracy=new_right / n,
                delta_pp=100 * (new_right - prior_right) / n,
                corrected=corrected, regressed=regressed, changed=changed,
                changed_rate=changed / n,
                invalid=sum(new["error"] is not None for old, new in pairs),
                invalid_reasons=dict(Counter(new["error"] for old, new in pairs if new["error"])))


def source_macro(pairs_by_suite: dict[str, list[tuple[dict, dict]]], source_by_suite: dict[str, str]) -> float:
    per_source = defaultdict(list)
    for suite, pairs in pairs_by_suite.items():
        per_source[source_by_suite[suite]].append(comparison(pairs)["delta_pp"])
    return statistics.mean(statistics.mean(v) for v in per_source.values())


def source_macro_interval(pairs_by_suite: dict[str, list[tuple[dict, dict]]], source_by_suite: dict[str, str]) -> list[float]:
    # Resample independent source groups (not question primitives) within the
    # original suite. Repeated-group cases remain a residual dependence risk;
    # the report gives a group-block sensitivity interval separately.
    rng = random.Random(SEED)
    values = []
    for _ in range(RESAMPLES):
        sampled = {suite: [pairs[rng.randrange(len(pairs))] for _ in pairs]
                   for suite, pairs in pairs_by_suite.items()}
        values.append(source_macro(sampled, source_by_suite))
    return [quantile(values, 0.025), quantile(values, 0.975)]


def overall_interval(pairs_by_suite: dict[str, list[tuple[dict, dict]]]) -> list[float]:
    rng = random.Random(SEED + 2)
    values = []
    for _ in range(RESAMPLES):
        sampled = [pairs[rng.randrange(len(pairs))]
                   for pairs in pairs_by_suite.values() for _ in pairs]
        values.append(comparison(sampled)["delta_pp"])
    return [quantile(values, 0.025), quantile(values, 0.975)]


def group_block_interval(pairs_by_suite: dict[str, list[tuple[dict, dict]]], source_by_suite: dict[str, str],
                         group_by_key: dict[tuple[str, str, str], str]) -> list[float]:
    rng = random.Random(SEED + 1)
    suite_groups = {}
    for suite, pairs in pairs_by_suite.items():
        grouped = defaultdict(list)
        for old, new in pairs:
            grouped[group_by_key[(suite, new["id"], new["qid"])]].append((old, new))
        suite_groups[suite] = list(grouped.values())
    values = []
    for _ in range(RESAMPLES):
        sampled = {}
        for suite, groups in suite_groups.items():
            chosen = [groups[rng.randrange(len(groups))] for _ in groups]
            sampled[suite] = [pair for group in chosen for pair in group]
        values.append(source_macro(sampled, source_by_suite))
    return [quantile(values, 0.025), quantile(values, 0.975)]


def load() -> tuple[dict, dict]:
    manifest = read(HERE / "manifest.json")
    if sha(HERE / "frozen.json") != manifest["frozen_sha256"]:
        raise ValueError("Frozen cases changed")
    if sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]:
        raise ValueError("Protocol changed")
    selected = read(HERE / "frozen.json")
    return selected, manifest


def analyze() -> dict:
    selected, manifest = load()
    source_by_suite = {s["suite"]: s["source"] for s in selected["suites"]}
    group_by_key = {(s["suite"], c["id"], c["qid"]): c["group"]
                    for s in selected["suites"] for c in s["cases"]}
    result = dict(version="strong-baseline-v1", count_suites=len(selected["suites"]),
                  count_sources=len(set(source_by_suite.values())),
                  count_cases=sum(len(s["cases"]) for s in selected["suites"]),
                  confidence="95% paired, suite-stratified bootstrap; 10,000 draws",
                  grouping_sensitivity="95% source-group-block bootstrap within suite; 10,000 draws",
                  models={})
    for model in MODELS:
        metadata = read(HERE / "results" / model / "metadata.json")
        raw_path = HERE / "results" / model / "raw.jsonl"
        if metadata["status"] != "DONE" or sha(raw_path) != metadata["raw_sha256"]:
            raise ValueError(f"Incomplete or changed prompted run: {model}")
        raw = [json.loads(line) for line in raw_path.read_text().splitlines()]
        keyed = {(r["mode"], r["suite"], r["id"], r["qid"]): r for r in raw}
        if len(keyed) != len(raw) or len(raw) != 2 * result["count_cases"]:
            raise ValueError(f"Duplicate/missing prompted decisions: {model}")
        baseline = {}
        for suite in selected["suites"]:
            name = suite["suite"]
            path = ROOT / "results" / model / f"{name}.json.gz"
            if sha(path) != manifest["original_output_sha256"][f"{model}/{name}"]:
                raise ValueError(f"Original comparator file changed: {model}/{name}")
            saved = read_run(path)
            baseline[name] = {(r["id"], r["qid"]): r for r in saved["rows"]}
            if len(baseline[name]) != len(saved["rows"]):
                raise ValueError(f"Duplicate original row: {model}/{name}")
        model_summary = dict(metadata_sha256=sha(HERE / "results" / model / "metadata.json"),
                             raw_sha256=sha(raw_path), modes={})
        for mode in MODES:
            pairs_by_suite = {}
            for suite in selected["suites"]:
                name = suite["suite"]
                pairs = []
                for case in suite["cases"]:
                    key = (mode, name, case["id"], case["qid"])
                    if key not in keyed:
                        raise ValueError(f"Missing prompted row: {key}")
                    new = keyed[key]
                    old = baseline[name][(case["id"], case["qid"])]
                    for field in ("gold", "request_sha256"):
                        if new[field] != case[field] or old[field] != case[field]:
                            raise ValueError(f"Paired {field} mismatch: {key}")
                    if new["question_sha256"] != case["question_sha256"]:
                        raise ValueError(f"Question mismatch: {key}")
                    if new["prediction"] is None and new["error"] is None:
                        raise ValueError(f"Missing prediction not marked invalid: {key}")
                    pairs.append((old, new))
                pairs_by_suite[name] = pairs
            all_pairs = [p for pairs in pairs_by_suite.values() for p in pairs]
            suite_results = {suite: comparison(pairs) for suite, pairs in pairs_by_suite.items()}
            source_results = {}
            for source in sorted(set(source_by_suite.values())):
                source_pairs = [pair for suite, pairs in pairs_by_suite.items()
                                if source_by_suite[suite] == source for pair in pairs]
                source_results[source] = comparison(source_pairs)
            mode_rows = [r for r in raw if r["mode"] == mode]
            unique_batches = {}
            for row in mode_rows:
                if row["batch_id"] in unique_batches and unique_batches[row["batch_id"]] != row["batch_seconds"]:
                    raise ValueError("Inconsistent batch timing")
                unique_batches[row["batch_id"]] = row["batch_seconds"]
            model_summary["modes"][mode] = dict(
                overall=comparison(all_pairs), suites=suite_results, sources=source_results,
                overall_ci95_pp=overall_interval(pairs_by_suite),
                source_macro_delta_pp=source_macro(pairs_by_suite, source_by_suite),
                source_macro_ci95_pp=source_macro_interval(pairs_by_suite, source_by_suite),
                source_macro_group_ci95_pp=group_block_interval(pairs_by_suite, source_by_suite, group_by_key),
                prompt_tokens=sum(r["prompt_tokens"] for r in mode_rows),
                completion_tokens=sum(r["completion_tokens"] for r in mode_rows),
                inference_seconds=sum(unique_batches.values()),
                batch_count=len(unique_batches),
                max_prompt_tokens=max(r["prompt_tokens"] for r in mode_rows),
                max_completion_tokens=max(r["completion_tokens"] for r in mode_rows))
        # Direct/deliberative turnover is a second paired contrast with the same
        # denominator. It is descriptive, not a prompt-selection criterion.
        paired_modes = []
        for suite in selected["suites"]:
            for case in suite["cases"]:
                key = (suite["suite"], case["id"], case["qid"])
                paired_modes.append((keyed[("direct", *key)], keyed[("deliberate", *key)]))
        model_summary["deliberate_vs_direct"] = comparison(paired_modes)
        result["models"][model] = model_summary
    return result


if __name__ == "__main__":
    summary = analyze()
    write(HERE / "summary.json", summary)
    for model, m in summary["models"].items():
        print(model)
        for mode, x in m["modes"].items():
            print(mode, x["overall"], "macro", round(x["source_macro_delta_pp"], 2),
                  "CI", [round(z, 2) for z in x["source_macro_ci95_pp"]],
                  "group CI", [round(z, 2) for z in x["source_macro_group_ci95_pp"]])
        print("deliberate-direct", m["deliberate_vs_direct"])
