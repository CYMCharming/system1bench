"""Paired and tie-audited SciFact3 display/code factorial analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402
from system1bench.run import read_run  # noqa: E402
from freeze import HERE, MODE_SUITES, MODEL_NAMES, MODES, SOURCE  # noqa: E402

LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
NEW_MODES = ("display_only", "code_only")
PAIRS = (("display_only", "base"), ("code_only", "base"), ("both", "base"),
         ("both", "display_only"), ("both", "code_only"))
DRAW_COUNT = 10_000
SEED = 20260930


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[min(lower + 1, len(ordered) - 1)] * weight


def probabilities(row: dict) -> dict | None:
    if row["error"] is not None or row["prediction"] is None:
        return None
    raw = row["answer"]["probabilities"]
    if set(raw) != set(LABELS):
        raise ValueError("Missing semantic probabilities")
    return raw


def canonical_prediction(row: dict) -> str | None:
    ps = probabilities(row)
    return max(LABELS, key=ps.__getitem__) if ps is not None else None


def top_ties(row: dict, mode: str) -> tuple[str, ...]:
    ps = probabilities(row)
    if ps is None:
        return ()
    from_probabilities = tuple(label for label in LABELS if ps[label] == max(ps.values()))
    order = LABELS[::-1] if mode == "both" else LABELS
    logits = row["answer"]["candidate_logits"]
    if len(logits) != 3:
        raise ValueError("Raw candidate logits missing")
    by_label = dict(zip(order, logits))
    from_logits = tuple(label for label in LABELS if by_label[label] == max(by_label.values()))
    if from_probabilities != from_logits or row["prediction"] not in from_logits:
        raise ValueError("Probability/logit/native prediction mismatch")
    return from_logits


def load_model(model: str, frozen: dict, manifest: dict) -> tuple[dict, dict]:
    directory = HERE / "results" / model
    metadata = read(directory / "metadata.json")
    signature = metadata["signature"]
    if (metadata["status"] != "DONE" or signature["batch_size"] != 4
        or signature["codebook_frozen_sha256"] != manifest["frozen_sha256"]
        or signature["protocol_sha256"] != manifest["protocol_sha256"]
        or signature["runner_sha256"] != sha(HERE / "run.py")):
        raise ValueError("New result incomplete or signature changed")
    old_metadata_path = SOURCE / "results/local" / model / "metadata.json"
    if sha(old_metadata_path) != manifest["source_metadata_sha256"][model]:
        raise ValueError("Original result metadata changed")
    old_metadata = read(old_metadata_path)
    if (old_metadata["signature"]["model"]["model_files_sha256"]
            != signature["model"]["model_files_sha256"]
        or old_metadata["signature"]["model"]["chat_template_sha256"]
            != signature["model"]["chat_template_sha256"]
        or old_metadata["signature"]["source_code_sha256"]["system1bench/llm_adapter.py"]
            != signature["adapter_sha256"]):
        raise ValueError("Original/new checkpoint, template or adapter mismatch")
    specs = {row["id"]: row for row in frozen["rows"]}
    if len(specs) != 180:
        raise ValueError("Frozen cases changed")
    outputs = {}
    provenance = {}
    for mode in MODES:
        if mode in MODE_SUITES:
            path = SOURCE / "results/local" / model / f"{MODE_SUITES[mode]}.json.gz"
            expected_hash = manifest["existing_output_sha256"][f"{model}/{mode}"]
        else:
            path = directory / f"{mode}.json.gz"
            expected_hash = metadata["modes"][mode]["sha256"]
        if sha(path) != expected_hash:
            raise ValueError("Output file hash mismatch")
        saved = read_run(path)
        rows = {row["id"]: row for row in saved["rows"]}
        if len(rows) != 180 or set(rows) != set(specs):
            raise ValueError("Missing/duplicate paired IDs")
        for case_id, row in rows.items():
            spec = specs[case_id]
            request_hash = (spec[f"{mode}_request_sha256"] if mode in MODE_SUITES
                            else spec["base_request_sha256"])
            if (row["gold"] != spec["gold"] or row["group"] != spec["group"]
                or row["request_sha256"] != request_hash):
                raise ValueError("Source case/reference mismatch")
            if mode in NEW_MODES:
                mode_spec = spec["modes"][mode]
                if (row["messages_sha256"] != mode_spec["messages_sha256"]
                    or row["candidate_assignment_sha256"] != mode_spec["candidate_assignment_sha256"]
                    or row["canonical_code_indices"] != mode_spec["canonical_code_indices"]):
                    raise ValueError("New prompt/code assignment changed")
            top_ties(row, mode)
        outputs[mode] = rows
        provenance[mode] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path),
                                origin="reused_original" if mode in MODE_SUITES else "new_inference")
    return outputs, dict(metadata=metadata, provenance=provenance)


def effect_rates(counts: Counter) -> dict[str, float]:
    n = counts["n"]
    accuracy = {mode: 100 * counts[f"correct/{mode}"] / n for mode in MODES}
    rates = {f"accuracy/{mode}": value for mode, value in accuracy.items()}
    rates.update({
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
        rates[f"flip/{key}"] = 100 * counts[f"flip/{key}"] / n
    return rates


def measure(frozen: dict, outputs: dict, view: str) -> dict:
    if view not in ("native", "common_tie"):
        raise ValueError(view)
    specs = {row["id"]: row for row in frozen["rows"]}
    observations = {}
    by_gold = {label: {mode: Counter() for mode in MODES} for label in LABELS}
    code_choices = {mode: Counter() for mode in MODES}
    transitions = {mode: defaultdict(Counter) for mode in MODES if mode != "base"}
    gold_transitions = {gold: {mode: defaultdict(Counter) for mode in MODES if mode != "base"}
                        for gold in LABELS}
    for case_id, spec in specs.items():
        selected = {}
        for mode in MODES:
            row = outputs[mode][case_id]
            pred = row["prediction"] if view == "native" else canonical_prediction(row)
            selected[mode] = pred
            by_gold[spec["gold"]][mode]["n"] += 1
            by_gold[spec["gold"]][mode]["correct"] += pred == spec["gold"]
            by_gold[spec["gold"]][mode][f"predicted/{pred}"] += 1
            if pred is None:
                code_choices[mode]["invalid"] += 1
            else:
                code_index = spec["modes"][mode]["canonical_code_indices"][LABELS.index(pred)]
                code_choices[mode]["ABC"[code_index]] += 1
        observations[case_id] = selected
        for mode in transitions:
            transitions[mode][str(selected["base"])][str(selected[mode])] += 1
            gold_transitions[spec["gold"]][mode][str(selected["base"])][str(selected[mode])] += 1
    groups = defaultdict(Counter)
    for case_id, selected in observations.items():
        spec = specs[case_id]
        counts = groups[spec["group"]]
        counts["n"] += 1
        for mode, pred in selected.items():
            counts[f"correct/{mode}"] += pred == spec["gold"]
            counts[f"invalid/{mode}"] += pred is None or outputs[mode][case_id]["error"] is not None
            ps = probabilities(outputs[mode][case_id])
            counts[f"gold_probability/{mode}"] += ps[spec["gold"]] if ps else 0.0
        for left, right in PAIRS:
            key = f"{right}_to_{left}"
            left_correct = selected[left] == spec["gold"]
            right_correct = selected[right] == spec["gold"]
            counts[f"flip/{key}"] += selected[left] != selected[right]
            counts[f"correction/{key}"] += left_correct and not right_correct
            counts[f"regression/{key}"] += right_correct and not left_correct
    if len(groups) != 180:
        raise ValueError("Unique claim clusters changed")
    cluster_values = [groups[group] for group in sorted(groups)]
    totals = sum(cluster_values, Counter())
    observed = effect_rates(totals)
    bootstrap = {key: [] for key in observed}
    rng = random.Random(SEED)
    for _ in range(DRAW_COUNT):
        sampled = sum((cluster_values[rng.randrange(len(cluster_values))]
                       for _ in cluster_values), Counter())
        draw = effect_rates(sampled)
        for key, value in draw.items():
            bootstrap[key].append(value)
    intervals = {key: [percentile(values, .025), percentile(values, .975)]
                 for key, values in bootstrap.items()}
    cells = {mode: dict(correct=totals[f"correct/{mode}"], n=totals["n"],
                        accuracy_percent=observed[f"accuracy/{mode}"],
                        cluster_ci95_percent=intervals[f"accuracy/{mode}"],
                        invalid=totals[f"invalid/{mode}"],
                        mean_gold_probability_percent=100*totals[f"gold_probability/{mode}"]/totals["n"],
                        code_choice_counts=dict(code_choices[mode]))
             for mode in MODES}
    comparisons = {}
    for left, right in PAIRS:
        key = f"{right}_to_{left}"
        comparisons[key] = dict(prediction_flips=totals[f"flip/{key}"],
                                flip_percent=observed[f"flip/{key}"],
                                flip_cluster_ci95_percent=intervals[f"flip/{key}"],
                                corrections=totals[f"correction/{key}"],
                                regressions=totals[f"regression/{key}"],
                                accuracy_delta_percent_points=(observed[f"accuracy/{left}"]
                                                               - observed[f"accuracy/{right}"]))
    effects = {key.removeprefix("effect/"): dict(
        delta_percent_points=observed[key], cluster_ci95_percent_points=intervals[key]
    ) for key in observed if key.startswith("effect/")}

    def nested_transitions(source: dict) -> dict:
        return {mode: {before: dict(after) for before, after in matrix.items()}
                for mode, matrix in source.items()}

    return dict(cells=cells, comparisons=comparisons, factorial_effects=effects,
                by_gold_label={gold: {mode: dict(counts) for mode, counts in modes.items()}
                               for gold, modes in by_gold.items()},
                predicted_class_transitions_from_base=nested_transitions(transitions),
                transitions_by_gold_label={gold: nested_transitions(modes)
                                           for gold, modes in gold_transitions.items()})


def summarize_model(model: str, frozen: dict, manifest: dict) -> dict:
    outputs, provenance = load_model(model, frozen, manifest)
    tie_diagnostic = {}
    for mode in MODES:
        rows = outputs[mode]
        tied = [case_id for case_id, row in rows.items() if len(top_ties(row, mode)) > 1]
        changed = [case_id for case_id, row in rows.items()
                   if row["prediction"] != canonical_prediction(row)]
        if not set(changed).issubset(tied):
            raise ValueError("Non-tie native prediction changed")
        tie_diagnostic[mode] = dict(top_ties=len(tied), native_to_common_changed=len(changed),
                                    tied_case_ids=tied, changed_case_ids=changed)
    repeat_path = SOURCE / "results/local" / model / "scifact3_exact_repeat.json.gz"
    repeat = {row["id"]: row for row in read_run(repeat_path)["rows"]}
    if set(repeat) != set(outputs["base"]):
        raise ValueError("Repeat IDs differ")
    repeat_flips = sum(repeat[case_id]["prediction"] != outputs["base"][case_id]["prediction"]
                       for case_id in repeat)
    return dict(model=model, cases=180, claim_clusters=180,
                native=measure(frozen, outputs, "native"),
                common_tie=measure(frozen, outputs, "common_tie"),
                tie_diagnostic=tie_diagnostic,
                exact_repeat=dict(path=str(repeat_path.relative_to(ROOT)),
                                  sha256=sha(repeat_path), prediction_flips_vs_base=repeat_flips),
                provenance=provenance["provenance"],
                new_inference_seconds={mode: provenance["metadata"]["modes"][mode]["inference_seconds"]
                                       for mode in NEW_MODES})


def main() -> None:
    manifest = read(HERE / "manifest.json")
    if (sha(HERE / "frozen.json") != manifest["frozen_sha256"]
        or sha(SOURCE / "frozen.json") != manifest["source_frozen_sha256"]
        or sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]):
        raise ValueError("Freeze/source/protocol changed")
    frozen = read(HERE / "frozen.json")
    summary = dict(version="scifact3-codebook-v1",
                   frozen_sha256=manifest["frozen_sha256"],
                   protocol_sha256=manifest["protocol_sha256"],
                   analysis_code_sha256=sha(__file__),
                   bootstrap=dict(draws=DRAW_COUNT, seed=SEED,
                                  unit="source_claim_unique_pair",
                                  interval="percentile_95"),
                   models={model: summarize_model(model, frozen, manifest)
                           for model in MODEL_NAMES})
    target = HERE / "summary.json"
    if target.exists():
        raise ValueError("Existing summary; never overwrite")
    write(target, summary)
    for model, info in summary["models"].items():
        print(model)
        for view in ("native", "common_tie"):
            print(" ", view,
                  {mode: info[view]["cells"][mode]["correct"] for mode in MODES},
                  "flips", {mode: info[view]["comparisons"][f"base_to_{mode}"]["prediction_flips"]
                            for mode in ("display_only", "code_only", "both")})
        print("  ties", {mode: info["tie_diagnostic"][mode]["top_ties"] for mode in MODES})


if __name__ == "__main__":
    main()
