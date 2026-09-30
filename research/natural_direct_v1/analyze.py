"""Verify strict direct generations and paired natural-domain code-logit controls."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.strong_baseline import parse_response  # noqa: E402
from system1bench.common import read, sha, write  # noqa: E402
from system1bench.run import read_run  # noqa: E402
from freeze import HERE, MODELS, SOURCES  # noqa: E402

DRAW_COUNT = 10_000
SEED = 20260930


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[min(lower + 1, len(ordered) - 1)] * weight


def metrics(totals: Counter) -> dict[str, float]:
    n = totals["n"]
    return dict(code_logit_accuracy_percent=100 * totals["old_correct"] / n,
                direct_accuracy_percent=100 * totals["direct_correct"] / n,
                accuracy_delta_percent_points=100 * (totals["direct_correct"] - totals["old_correct"]) / n,
                flip_percent=100 * totals["flip"] / n,
                corrected_percent=100 * totals["corrected"] / n,
                regressed_percent=100 * totals["regressed"] / n,
                invalid_percent=100 * totals["invalid"] / n)


def domain_result(records: list[dict], expected_groups: int, rng: random.Random) -> tuple[dict, list[float]]:
    groups = defaultdict(Counter)
    by_gold = defaultdict(Counter)
    invalid_reasons = Counter()
    for record in records:
        group = groups[record["group"]]
        group["n"] += 1
        old_correct = record["code_logit_prediction"] == record["gold"]
        direct_correct = record["direct_prediction"] == record["gold"]
        group["old_correct"] += old_correct
        group["direct_correct"] += direct_correct
        group["flip"] += record["code_logit_prediction"] != record["direct_prediction"]
        group["corrected"] += direct_correct and not old_correct
        group["regressed"] += old_correct and not direct_correct
        group["invalid"] += record["direct_error"] is not None
        gold = by_gold[record["gold"]]
        gold["n"] += 1
        gold["code_logit_correct"] += old_correct
        gold["direct_correct"] += direct_correct
        gold["direct_invalid"] += record["direct_error"] is not None
        if record["direct_error"] is not None:
            invalid_reasons[record["direct_error"]] += 1
    if len(groups) != expected_groups:
        raise ValueError("Source-cluster count changed")
    cluster_values = [groups[group] for group in sorted(groups)]
    totals = sum(cluster_values, Counter())
    observed = metrics(totals)
    sampled_values = {key: [] for key in observed}
    for _ in range(DRAW_COUNT):
        sampled = sum((cluster_values[rng.randrange(len(cluster_values))]
                       for _ in cluster_values), Counter())
        draw = metrics(sampled)
        for key, value in draw.items():
            sampled_values[key].append(value)
    intervals = {key: [percentile(v, .025), percentile(v, .975)]
                 for key, v in sampled_values.items()}
    return dict(n=totals["n"], source_clusters=len(groups),
                code_logit_correct=totals["old_correct"],
                direct_correct=totals["direct_correct"],
                direct_invalid=totals["invalid"],
                prediction_flips=totals["flip"],
                corrections=totals["corrected"], regressions=totals["regressed"],
                metrics=observed, cluster_ci95=intervals,
                by_gold={label: dict(counts) for label, counts in by_gold.items()},
                invalid_reasons=dict(invalid_reasons)), sampled_values["accuracy_delta_percent_points"]


def load_model(model: str, frozen: dict, manifest: dict) -> tuple[list[dict], dict]:
    path = HERE / "results" / model
    metadata = read(path / "metadata.json")
    if (metadata["status"] != "DONE" or metadata["count"] != 324
        or metadata["raw_sha256"] != sha(path / "raw.jsonl")
        or metadata["signature"]["frozen_sha256"] != manifest["frozen_sha256"]
        or metadata["signature"]["protocol_sha256"] != manifest["protocol_sha256"]
        or metadata["signature"]["runner_sha256"] != sha(HERE / "run.py")
        or metadata["signature"]["parser_code_sha256"] != manifest["parser_code_sha256"]):
        raise ValueError("Direct run incomplete/provenance mismatch")
    expected = {(row["domain"], row["id"]): row for row in frozen["cases"]}
    raw = {}
    for line in (path / "raw.jsonl").read_text().splitlines():
        row = json.loads(line)
        key = (row["domain"], row["id"])
        if key not in expected or key in raw:
            raise ValueError("Unexpected/duplicate raw generation")
        spec = expected[key]
        for field in ("domain", "suite", "id", "group", "gold", "request_sha256",
                      "question_sha256", "messages_sha256"):
            if row[field] != spec[field]:
                raise ValueError("Raw output/input mismatch")
        code, prediction, error = parse_response("direct", row["raw_text"],
                                                  spec["codes"], spec["labels"])
        if row["code"] != code or row["prediction"] != prediction:
            raise ValueError("Stored generation does not independently reparse")
        if error is None and row["error"] is not None:
            raise ValueError("Valid response marked invalid")
        if error is not None and row["error"] is None:
            raise ValueError("Invalid response marked valid")
        if (row["error"] is None) != (row["prediction"] is not None):
            raise ValueError("Invalid coverage/prediction inconsistent")
        raw[key] = row
    if set(raw) != set(expected):
        raise ValueError("Missing raw generation")
    records = []
    old_provenance = {}
    for domain, (directory, suite) in SOURCES.items():
        metadata_path = directory / "results/local" / model / "metadata.json"
        if sha(metadata_path) != manifest["old_metadata_sha256"][f"{domain}/{model}"]:
            raise ValueError("Historical metadata changed")
        old_meta = read(metadata_path)
        if (metadata["signature"]["model_files_sha256"]
                != old_meta["signature"]["model"]["model_files_sha256"]
            or metadata["signature"]["chat_template_sha256"]
                != old_meta["signature"]["model"]["chat_template_sha256"]):
            raise ValueError("Historical/new model mismatch")
        old_path = directory / "results/local" / model / f"{suite}.json.gz"
        if sha(old_path) != manifest["old_output_sha256"][f"{domain}/{model}"]:
            raise ValueError("Historical output hash changed")
        old_rows = {row["id"]: row for row in read_run(old_path)["rows"]}
        for (key_domain, case_id), spec in expected.items():
            if key_domain != domain:
                continue
            old = old_rows[case_id]
            direct = raw[domain, case_id]
            if (old["request_sha256"] != spec["request_sha256"]
                or old["gold"] != spec["gold"]
                or old["audit"]["prompt_token_sha256"] != direct["prompt_token_sha256"]
                or old["audit"]["prompt_tokens"] != direct["prompt_tokens"]):
                raise ValueError("Direct/logit prompt or reference differs")
            records.append(dict(domain=domain, id=case_id, group=spec["group"],
                                gold=spec["gold"],
                                code_logit_prediction=old["prediction"],
                                direct_prediction=direct["prediction"],
                                direct_error=direct["error"]))
        old_provenance[domain] = dict(path=str(old_path.relative_to(ROOT)), sha256=sha(old_path))
    return records, dict(raw_path=str((path / "raw.jsonl").relative_to(ROOT)),
                         raw_sha256=metadata["raw_sha256"],
                         inference_seconds=metadata["synchronized_inference_seconds"],
                         generated_tokens=metadata["generated_tokens"],
                         prompt_tokens=metadata["prompt_tokens"],
                         historical=old_provenance)


def main() -> None:
    manifest = read(HERE / "manifest.json")
    if (sha(HERE / "frozen.json") != manifest["frozen_sha256"]
        or sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]):
        raise ValueError("Freeze/protocol changed")
    frozen = read(HERE / "frozen.json")
    results = {}
    for model in MODELS:
        records, provenance = load_model(model, frozen, manifest)
        rng = random.Random(SEED)
        domains = {}
        effects = {}
        for domain in SOURCES:
            domain_records = [row for row in records if row["domain"] == domain]
            domain_summary, draws = domain_result(
                domain_records, manifest["cluster_counts"][domain], rng
            )
            domains[domain] = domain_summary
            effects[domain] = draws
        macro_draws = [(legal + science) / 2 for legal, science in
                       zip(effects["legal"], effects["science"])]
        macro = (domains["legal"]["metrics"]["accuracy_delta_percent_points"]
                 + domains["science"]["metrics"]["accuracy_delta_percent_points"]) / 2
        results[model] = dict(domains=domains,
                              equal_domain_macro_accuracy_delta_percent_points=macro,
                              macro_cluster_ci95_percent_points=[percentile(macro_draws, .025),
                                                                  percentile(macro_draws, .975)],
                              provenance=provenance)
    summary = dict(version="natural-direct-v1", frozen_sha256=manifest["frozen_sha256"],
                   protocol_sha256=manifest["protocol_sha256"],
                   analysis_code_sha256=sha(__file__),
                   bootstrap=dict(draws=DRAW_COUNT, seed=SEED,
                                  unit={"legal": "source_contract", "science": "source_claim"},
                                  interval="percentile_95"), models=results)
    target = HERE / "summary.json"
    if target.exists():
        raise ValueError("Analysis output exists; never overwrite")
    write(target, summary)
    for model, result in results.items():
        print(model)
        for domain, info in result["domains"].items():
            print(" ", domain, info["code_logit_correct"], "→", info["direct_correct"],
                  "of", info["n"], "invalid", info["direct_invalid"],
                  "flips", info["prediction_flips"],
                  "delta CI", info["cluster_ci95"]["accuracy_delta_percent_points"])
        print("  macro", result["equal_domain_macro_accuracy_delta_percent_points"],
              result["macro_cluster_ci95_percent_points"])


if __name__ == "__main__":
    main()
