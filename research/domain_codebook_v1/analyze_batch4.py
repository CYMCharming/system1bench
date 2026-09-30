"""Audited batch-four 2x2 results, native and common-tie sensitivity."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402
from system1bench.run import read_run  # noqa: E402
from analyze import BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, PAIRS, percentile, rates  # noqa: E402
from freeze import HERE, MODES, SOURCE  # noqa: E402

LABELS = ("Entailment", "Contradiction", "NotMentioned")
MODELS = ("llama31_8b_instruct", "qwen3_8b")
SOURCES = {"base": "contractnli_base", "both": "contractnli_reversed_option_order"}


def semantic_probabilities(row: dict) -> dict[str, float] | None:
    if row["error"] is not None or row["prediction"] is None:
        return None
    probabilities = row["answer"]["probabilities"]
    if set(probabilities) != set(LABELS):
        raise ValueError("Raw semantic probabilities incomplete")
    return {label: float(probabilities[label]) for label in LABELS}


def common_tie_prediction(row: dict) -> str | None:
    probabilities = semantic_probabilities(row)
    if probabilities is None:
        return None
    return max(LABELS, key=probabilities.__getitem__)


def tie_labels(row: dict, mode: str) -> tuple[str, ...]:
    probabilities = semantic_probabilities(row)
    if probabilities is None:
        return ()
    maximum = max(probabilities.values())
    from_probabilities = tuple(label for label in LABELS if probabilities[label] == maximum)
    order = LABELS[::-1] if mode == "both" else LABELS
    logits = row["answer"]["candidate_logits"]
    if len(logits) != 3:
        raise ValueError("Raw candidate logits missing")
    semantic_logits = dict(zip(order, logits))
    logit_maximum = max(semantic_logits.values())
    from_logits = tuple(label for label in LABELS if semantic_logits[label] == logit_maximum)
    if from_logits != from_probabilities:
        raise ValueError("Logit/probability top-tie mismatch")
    if row["prediction"] not in from_logits:
        raise ValueError("Native decoder disagrees with logits")
    return from_logits


def load_model(model: str, frozen: dict, manifest: dict, amendment: dict) -> tuple[dict, dict]:
    result_directory = HERE / "results_batch4" / model
    metadata = read(result_directory / "metadata.json")
    if metadata["status"] != "DONE" or metadata["signature"]["batch_size"] != 4:
        raise ValueError("Corrected result incomplete or wrong batch size")
    signature = metadata["signature"]
    if (signature["amendment_manifest_sha256"] != sha(HERE / "batch4_manifest.json")
        or signature["amendment_sha256"] != amendment["amendment_sha256"]
        or signature["runner_sha256"] != amendment["corrected_runner_sha256"]
        or signature["codebook_frozen_sha256"] != manifest["frozen_sha256"]):
        raise ValueError("Corrected-run provenance mismatch")
    old_metadata = read(SOURCE / "results" / "local" / model / "metadata.json")
    if (old_metadata["signature"]["batch_size"] != signature["batch_size"]
        or old_metadata["signature"]["model"]["model_files_sha256"]
            != signature["model"]["model_files_sha256"]
        or old_metadata["signature"]["model"]["chat_template_sha256"]
            != signature["model"]["chat_template_sha256"]
        or old_metadata["signature"]["source_code_sha256"]["system1bench/llm_adapter.py"]
            != signature["adapter_sha256"]):
        raise ValueError("Historical/corrected model, adapter or batch mismatch")
    specs = {row["id"]: row for row in frozen["rows"]}
    if len(specs) != 144:
        raise ValueError("Case count changed")
    rows_by_mode = {}
    provenance = {}
    for mode in MODES:
        if mode in SOURCES:
            path = SOURCE / "results" / "local" / model / f"{SOURCES[mode]}.json.gz"
            expected_hash = manifest["existing_output_sha256"][f"{model}/{mode}"]
        else:
            path = result_directory / f"{mode}.json.gz"
            expected_hash = metadata["modes"][mode]["sha256"]
        if sha(path) != expected_hash:
            raise ValueError("Source or corrected output hash mismatch")
        saved = read_run(path)
        rows = {row["id"]: row for row in saved["rows"]}
        if len(rows) != 144 or set(rows) != set(specs):
            raise ValueError("Missing/duplicate paired IDs")
        for case_id, row in rows.items():
            spec = specs[case_id]
            request_hash = (spec[f"{mode}_request_sha256"] if mode in SOURCES
                            else spec["base_request_sha256"])
            if (row["gold"] != spec["gold"] or row["group"] != spec["group"]
                or row["request_sha256"] != request_hash):
                raise ValueError("Reference/group/input mismatch")
            if mode not in SOURCES:
                prompt = spec["modes"][mode]
                if (row["messages_sha256"] != prompt["messages_sha256"]
                    or row["candidate_assignment_sha256"] != prompt["candidate_assignment_sha256"]
                    or row["canonical_code_indices"] != prompt["canonical_code_indices"]):
                    raise ValueError("Corrected prompt/code mismatch")
            tie_labels(row, mode)
        rows_by_mode[mode] = rows
        provenance[mode] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path),
                                origin="reused_original" if mode in SOURCES else "new_batch4")
    return rows_by_mode, dict(metadata=metadata, provenance=provenance)


def measure_view(frozen: dict, rows_by_mode: dict, view: str) -> dict:
    if view not in ("native", "common_tie"):
        raise ValueError(view)
    specs = {row["id"]: row for row in frozen["rows"]}
    groups = defaultdict(list)
    by_gold = {label: {mode: Counter() for mode in MODES} for label in LABELS}
    code_choices = {mode: Counter() for mode in MODES}
    for case_id, spec in specs.items():
        observations = {}
        for mode in MODES:
            row = rows_by_mode[mode][case_id]
            pred = row["prediction"] if view == "native" else common_tie_prediction(row)
            p_gold = (semantic_probabilities(row) or {}).get(spec["gold"], 0.0)
            observations[mode] = dict(prediction=pred, gold=spec["gold"],
                                      invalid=row["error"] is not None or pred is None,
                                      gold_probability=p_gold)
            by_gold[spec["gold"]][mode]["n"] += 1
            by_gold[spec["gold"]][mode]["correct"] += pred == spec["gold"]
            if pred is None:
                code_choices[mode]["invalid"] += 1
            else:
                label_index = LABELS.index(pred)
                code_index = spec["modes"][mode]["canonical_code_indices"][label_index]
                code_choices[mode]["ABC"[code_index]] += 1
        groups[spec["group"]].append(observations)
    if len(groups) != 91:
        raise ValueError("Document cluster count changed")

    group_counts = []
    for group in sorted(groups):
        counts = Counter()
        for observations in groups[group]:
            counts["n"] += 1
            for mode, row in observations.items():
                counts[f"correct/{mode}"] += row["prediction"] == row["gold"]
                counts[f"invalid/{mode}"] += row["invalid"]
                counts[f"gold_probability/{mode}"] += row["gold_probability"]
            for left, right in PAIRS:
                pair = f"{right}_to_{left}"
                lrow, rrow = observations[left], observations[right]
                lcorrect = lrow["prediction"] == lrow["gold"]
                rcorrect = rrow["prediction"] == rrow["gold"]
                counts[f"flip/{pair}"] += lrow["prediction"] != rrow["prediction"]
                counts[f"correction/{pair}"] += lcorrect and not rcorrect
                counts[f"regression/{pair}"] += rcorrect and not lcorrect
        group_counts.append(counts)

    def computed(sums: Counter) -> dict[str, float]:
        result = rates(sums)
        for mode in MODES:
            result[f"gold_probability/{mode}"] = 100 * sums[f"gold_probability/{mode}"] / sums["n"]
        return result

    totals = sum(group_counts, Counter())
    if totals["n"] != 144:
        raise ValueError("Case count changed")
    observed = computed(totals)
    draws = {key: [] for key in observed}
    rng = random.Random(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_DRAWS):
        sampled = sum((group_counts[rng.randrange(len(group_counts))]
                       for _ in group_counts), Counter())
        values = computed(sampled)
        for key, value in values.items():
            draws[key].append(value)
    intervals = {key: [percentile(values, .025), percentile(values, .975)]
                 for key, values in draws.items()}
    cells = {}
    for mode in MODES:
        cells[mode] = dict(correct=totals[f"correct/{mode}"], n=totals["n"],
                           accuracy_percent=observed[f"accuracy/{mode}"],
                           cluster_ci95_percent=intervals[f"accuracy/{mode}"],
                           invalid=totals[f"invalid/{mode}"],
                           mean_gold_probability_percent=observed[f"gold_probability/{mode}"],
                           code_choice_counts=dict(code_choices[mode]))
    comparisons = {}
    for left, right in PAIRS:
        pair = f"{right}_to_{left}"
        comparisons[pair] = dict(prediction_flips=totals[f"flip/{pair}"],
                                 flip_percent=observed[f"flip/{pair}"],
                                 flip_cluster_ci95_percent=intervals[f"flip/{pair}"],
                                 corrections=totals[f"correction/{pair}"],
                                 regressions=totals[f"regression/{pair}"],
                                 accuracy_delta_percent_points=(observed[f"accuracy/{left}"]
                                                                - observed[f"accuracy/{right}"]))
    effects = {key.removeprefix("effect/"): dict(
        delta_percent_points=observed[key], cluster_ci95_percent_points=intervals[key]
    ) for key in observed if key.startswith("effect/")}
    return dict(cells=cells, comparisons=comparisons, factorial_effects=effects,
                by_gold_label={label: {mode: dict(counts) for mode, counts in modes.items()}
                               for label, modes in by_gold.items()})


def summarize_model(model: str, frozen: dict, manifest: dict, amendment: dict) -> dict:
    rows_by_mode, audit = load_model(model, frozen, manifest, amendment)
    ties = {}
    for mode in MODES:
        rows = rows_by_mode[mode]
        tied = [case_id for case_id, row in rows.items() if len(tie_labels(row, mode)) > 1]
        changed = [case_id for case_id, row in rows.items()
                   if row["prediction"] != common_tie_prediction(row)]
        ties[mode] = dict(top_ties=len(tied), native_to_common_changed=len(changed),
                          tied_case_ids=tied, changed_case_ids=changed)
        if not set(changed).issubset(tied):
            raise ValueError("Non-tie prediction changed under tie convention")
    pilot = {}
    for mode in ("display_only", "code_only"):
        path = HERE / "results" / model / f"{mode}.json.gz"
        batch8 = {row["id"]: row for row in read_run(path)["rows"]}
        if set(batch8) != set(rows_by_mode[mode]):
            raise ValueError("Pilot/corrected IDs differ")
        flips = sum(batch8[case_id]["prediction"] != rows_by_mode[mode][case_id]["prediction"]
                    for case_id in batch8)
        max_probability_change = max(
            abs(semantic_probabilities(batch8[case_id])[label]
                - semantic_probabilities(rows_by_mode[mode][case_id])[label])
            for case_id in batch8 for label in LABELS
        )
        pilot[mode] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path),
                           prediction_changes_batch8_to_batch4=flips,
                           max_semantic_probability_change=max_probability_change)
    repeat_path = SOURCE / "results" / "local" / model / "contractnli_exact_repeat.json.gz"
    repeat_rows = {row["id"]: row for row in read_run(repeat_path)["rows"]}
    if set(repeat_rows) != set(rows_by_mode["base"]):
        raise ValueError("Repeat IDs changed")
    repeat_flips = sum(repeat_rows[case_id]["prediction"] != rows_by_mode["base"][case_id]["prediction"]
                       for case_id in repeat_rows)
    return dict(model=model, cases=144, document_groups=91,
                native=measure_view(frozen, rows_by_mode, "native"),
                common_tie=measure_view(frozen, rows_by_mode, "common_tie"),
                tie_diagnostic=ties, batch8_pilot_sensitivity=pilot,
                exact_repeat=dict(path=str(repeat_path.relative_to(ROOT)), sha256=sha(repeat_path),
                                  prediction_flips_vs_base=repeat_flips),
                provenance=audit["provenance"],
                new_inference_seconds={mode: audit["metadata"]["modes"][mode]["inference_seconds"]
                                       for mode in ("display_only", "code_only")})


def main() -> None:
    manifest = read(HERE / "manifest.json")
    amendment = read(HERE / "batch4_manifest.json")
    if (sha(HERE / "frozen.json") != manifest["frozen_sha256"]
        or sha(SOURCE / "frozen.json") != manifest["source_frozen_sha256"]
        or sha(HERE / "AMENDMENT.md") != amendment["amendment_sha256"]):
        raise ValueError("Frozen source or amendment changed")
    frozen = read(HERE / "frozen.json")
    result = dict(version="domain-codebook-v1-batch4-correction",
                  original_protocol_sha256=manifest["protocol_sha256"],
                  amendment_manifest_sha256=sha(HERE / "batch4_manifest.json"),
                  frozen_sha256=manifest["frozen_sha256"],
                  analysis_sha256=sha(__file__),
                  bootstrap=dict(unit="source_document", draws=BOOTSTRAP_DRAWS,
                                 seed=BOOTSTRAP_SEED, interval="percentile_95"),
                  models={model: summarize_model(model, frozen, manifest, amendment)
                          for model in MODELS})
    output = HERE / "summary_batch4.json"
    if output.exists():
        raise ValueError("Corrected summary already exists; never overwrite")
    write(output, result)
    for model, info in result["models"].items():
        print(model)
        for view in ("native", "common_tie"):
            print(" ", view, {mode: info[view]["cells"][mode]["correct"] for mode in MODES},
                  "base-to-both flips", info[view]["comparisons"]["base_to_both"]["prediction_flips"])
        print("  batch8-to-batch4 changes", {mode: info["batch8_pilot_sensitivity"][mode]["prediction_changes_batch8_to_batch4"]
                                               for mode in ("display_only", "code_only")})
    print("Wrote", output)


if __name__ == "__main__":
    main()
