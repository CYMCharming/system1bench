"""Verify and analyze the preregistered ContractNLI 2x2 codebook probe."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402
from system1bench.run import read_run  # noqa: E402
from freeze import HERE, MODES, SOURCE  # noqa: E402

MODE_SUITES = {"base": "contractnli_base", "both": "contractnli_reversed_option_order"}
MODELS = ("llama31_8b_instruct", "qwen3_8b")
PAIRS = (
    ("display_only", "base"), ("code_only", "base"), ("both", "base"),
    ("both", "display_only"), ("both", "code_only"),
)
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260930


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    low = int(position)
    alpha = position - low
    return ordered[low] * (1 - alpha) + ordered[min(low + 1, len(ordered) - 1)] * alpha


def rates(sums: Counter) -> dict[str, float]:
    n = sums["n"]
    accuracy = {mode: 100 * sums[f"correct/{mode}"] / n for mode in MODES}
    result = {f"accuracy/{mode}": value for mode, value in accuracy.items()}
    result.update({
        "effect/display_at_original_code": accuracy["display_only"] - accuracy["base"],
        "effect/code_at_original_display": accuracy["code_only"] - accuracy["base"],
        "effect/display_at_reversed_code": accuracy["both"] - accuracy["code_only"],
        "effect/code_at_reversed_display": accuracy["both"] - accuracy["display_only"],
        "effect/joint": accuracy["both"] - accuracy["base"],
        "effect/interaction": (accuracy["both"] - accuracy["code_only"])
        - (accuracy["display_only"] - accuracy["base"]),
    })
    for left, right in PAIRS:
        key = f"{right}_to_{left}"
        result[f"flip/{key}"] = 100 * sums[f"flip/{key}"] / n
        result[f"correction/{key}"] = 100 * sums[f"correction/{key}"] / n
        result[f"regression/{key}"] = 100 * sums[f"regression/{key}"] / n
    return result


def summarize_model(model: str, frozen: dict, manifest: dict) -> dict:
    metadata_path = HERE / "results" / model / "metadata.json"
    metadata = read(metadata_path)
    if metadata["status"] != "DONE":
        raise ValueError(f"Incomplete new run: {model}")
    signature = metadata["signature"]
    for key in ("source_frozen_sha256", "codebook_frozen_sha256", "protocol_sha256",
                "existing_output_sha256"):
        expected = manifest["frozen_sha256"] if key == "codebook_frozen_sha256" else manifest[key]
        if signature[key] != expected:
            raise ValueError(f"New result signature mismatch: {key}")
    if signature["adapter_sha256"] != sha(ROOT / "system1bench/llm_adapter.py"):
        raise ValueError("Current adapter differs from new run")
    source_meta = read(SOURCE / "results" / "local" / model / "metadata.json")
    if source_meta["signature"]["source_code_sha256"]["system1bench/llm_adapter.py"] != signature["adapter_sha256"]:
        raise ValueError("Original/new adapter code differs")
    if source_meta["signature"]["model"]["model_files_sha256"] != signature["model"]["model_files_sha256"]:
        raise ValueError("Original/new checkpoint differs")
    if source_meta["signature"]["model"]["chat_template_sha256"] != signature["model"]["chat_template_sha256"]:
        raise ValueError("Original/new chat template differs")

    case_specs = {row["id"]: row for row in frozen["rows"]}
    rows_by_mode = {}
    provenance = {}
    for mode in MODES:
        if mode in MODE_SUITES:
            path = SOURCE / "results" / "local" / model / f"{MODE_SUITES[mode]}.json.gz"
            expected_hash = manifest["existing_output_sha256"][f"{model}/{mode}"]
        else:
            path = HERE / "results" / model / f"{mode}.json.gz"
            expected_hash = metadata["modes"][mode]["sha256"]
        actual_hash = sha(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Output hash mismatch: {path}")
        saved = read_run(path)
        rows = {row["id"]: row for row in saved["rows"]}
        if len(rows) != 144 or set(rows) != set(case_specs):
            raise ValueError(f"Missing/duplicate IDs: {path}")
        for case_id, row in rows.items():
            spec = case_specs[case_id]
            if row["group"] != spec["group"] or row["gold"] != spec["gold"]:
                raise ValueError("Paired group/reference mismatch")
            request_hash = (spec[f"{mode}_request_sha256"] if mode in MODE_SUITES
                            else spec["base_request_sha256"])
            if row["request_sha256"] != request_hash:
                raise ValueError("Semantic request mismatch")
            if mode not in MODE_SUITES:
                prompts = spec["modes"][mode]
                if (row["messages_sha256"] != prompts["messages_sha256"]
                    or row["candidate_assignment_sha256"] != prompts["candidate_assignment_sha256"]
                    or row["canonical_code_indices"] != prompts["canonical_code_indices"]):
                    raise ValueError("New prompt/codebook mismatch")
            if row["error"] is None and row["prediction"] not in (
                "Entailment", "Contradiction", "NotMentioned"
            ):
                raise ValueError("Unaccounted invalid prediction")
            if row["error"] is None and row["probabilities"] is None:
                raise ValueError("Missing raw semantic probabilities")
        rows_by_mode[mode] = rows
        provenance[mode] = {"path": str(path.relative_to(ROOT)), "sha256": actual_hash,
                            "origin": "reused_original" if mode in MODE_SUITES else "new_inference"}

    groups = defaultdict(list)
    per_gold = {gold: {mode: Counter() for mode in MODES}
                for gold in ("Entailment", "Contradiction", "NotMentioned")}
    code_choices = {mode: Counter() for mode in MODES}
    for case_id, spec in case_specs.items():
        observations = {mode: rows_by_mode[mode][case_id] for mode in MODES}
        groups[spec["group"]].append(observations)
        gold = spec["gold"]
        for mode, row in observations.items():
            per_gold[gold][mode]["n"] += 1
            if row["prediction"] == gold:
                per_gold[gold][mode]["correct"] += 1
            if row["prediction"] is None:
                code_choices[mode]["invalid"] += 1
            else:
                label_index = ("Entailment", "Contradiction", "NotMentioned").index(row["prediction"])
                code_index = spec["modes"][mode]["canonical_code_indices"][label_index]
                code_choices[mode]["ABC"[code_index]] += 1

    group_counts = []
    for group in sorted(groups):
        counts = Counter()
        for observations in groups[group]:
            counts["n"] += 1
            for mode, row in observations.items():
                counts[f"correct/{mode}"] += row["prediction"] == row["gold"]
                counts[f"invalid/{mode}"] += row["prediction"] is None or row["error"] is not None
            for left, right in PAIRS:
                pair = f"{right}_to_{left}"
                left_row = observations[left]
                right_row = observations[right]
                left_correct = left_row["prediction"] == left_row["gold"]
                right_correct = right_row["prediction"] == right_row["gold"]
                counts[f"flip/{pair}"] += left_row["prediction"] != right_row["prediction"]
                counts[f"correction/{pair}"] += left_correct and not right_correct
                counts[f"regression/{pair}"] += right_correct and not left_correct
        group_counts.append(counts)
    if len(group_counts) != manifest["document_groups"]:
        raise ValueError("Document groups changed")
    totals = sum(group_counts, Counter())
    if totals["n"] != 144:
        raise ValueError("Decision count changed")
    observed = rates(totals)
    values = {key: [] for key in observed}
    rng = random.Random(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_DRAWS):
        sampled = sum((group_counts[rng.randrange(len(group_counts))]
                       for _ in group_counts), Counter())
        draw = rates(sampled)
        for key, value in draw.items():
            values[key].append(value)
    confidence_intervals = {key: [percentile(v, .025), percentile(v, .975)]
                            for key, v in values.items()}

    cells = {}
    for mode in MODES:
        cells[mode] = {"correct": totals[f"correct/{mode}"], "n": totals["n"],
                       "accuracy_percent": observed[f"accuracy/{mode}"],
                       "cluster_ci95_percent": confidence_intervals[f"accuracy/{mode}"],
                       "invalid": totals[f"invalid/{mode}"],
                       "code_choice_counts": dict(code_choices[mode])}
    comparisons = {}
    for left, right in PAIRS:
        pair = f"{right}_to_{left}"
        comparisons[pair] = {
            "prediction_flips": totals[f"flip/{pair}"],
            "flip_percent": observed[f"flip/{pair}"],
            "flip_cluster_ci95_percent": confidence_intervals[f"flip/{pair}"],
            "corrections": totals[f"correction/{pair}"],
            "regressions": totals[f"regression/{pair}"],
            "accuracy_delta_percent_points": observed[f"accuracy/{left}"] - observed[f"accuracy/{right}"],
        }
    effects = {key.removeprefix("effect/"): {
        "delta_percent_points": observed[key], "cluster_ci95_percent_points": confidence_intervals[key]
    } for key in observed if key.startswith("effect/")}

    repeat_path = SOURCE / "results" / "local" / model / "contractnli_exact_repeat.json.gz"
    repeat = {row["id"]: row for row in read_run(repeat_path)["rows"]}
    if set(repeat) != set(case_specs):
        raise ValueError("Exact-repeat IDs changed")
    repeat_flips = sum(repeat[case_id]["prediction"] != rows_by_mode["base"][case_id]["prediction"]
                       for case_id in case_specs)
    repeat_correct = sum(repeat[case_id]["prediction"] == case_specs[case_id]["gold"]
                         for case_id in case_specs)
    return {
        "model": model,
        "cases": totals["n"], "document_groups": len(groups),
        "cells": cells, "comparisons": comparisons, "factorial_effects": effects,
        "by_gold_label": {gold: {mode: dict(counts) for mode, counts in modes.items()}
                          for gold, modes in per_gold.items()},
        "exact_repeat_check": {"path": str(repeat_path.relative_to(ROOT)),
                               "sha256": sha(repeat_path), "prediction_flips_vs_base": repeat_flips,
                               "correct": repeat_correct},
        "provenance": provenance,
        "new_inference_seconds": {mode: metadata["modes"][mode]["inference_seconds"]
                                  for mode in ("display_only", "code_only")},
    }


def main() -> None:
    manifest = read(HERE / "manifest.json")
    if sha(HERE / "frozen.json") != manifest["frozen_sha256"]:
        raise ValueError("Codebook freeze changed")
    if sha(SOURCE / "frozen.json") != manifest["source_frozen_sha256"]:
        raise ValueError("Source freeze changed")
    frozen = read(HERE / "frozen.json")
    result = {"version": "domain-codebook-v1", "protocol_sha256": manifest["protocol_sha256"],
              "frozen_sha256": manifest["frozen_sha256"],
              "bootstrap": {"unit": "source_document", "draws": BOOTSTRAP_DRAWS,
                            "seed": BOOTSTRAP_SEED, "interval": "percentile_95"},
              "models": {model: summarize_model(model, frozen, manifest) for model in MODELS}}
    write(HERE / "summary.json", result)
    for model, summary in result["models"].items():
        print(model)
        for mode in MODES:
            print(" ", mode, summary["cells"][mode]["correct"], "/144",
                  "invalid", summary["cells"][mode]["invalid"])
        print("  base_to_both flips", summary["comparisons"]["base_to_both"]["prediction_flips"])
        print("  interaction", summary["factorial_effects"]["interaction"])
    print("Wrote", HERE / "summary.json")


if __name__ == "__main__":
    main()
