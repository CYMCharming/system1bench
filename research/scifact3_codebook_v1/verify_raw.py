"""Independent, stdlib-only replay of the SciFact3 codebook raw records.

This does not import the inference, freeze, or analysis modules. It reads source
material locally only to reconstruct model-facing message hashes; it emits no
claim, abstract, or reference text.
"""

from __future__ import annotations

import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "research/scifact3_codebook_v1"
SOURCE = ROOT / "research/scifact3_v1"
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")
MODES = ("base", "display_only", "code_only", "both")
MODE_SUITES = {"base": "scifact3_base", "both": "scifact3_reversed_option_order"}
MODELS = ("llama31_8b_instruct", "qwen3_8b")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def content_sha(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def read_gzip(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def adapter_literals() -> tuple[list[str], str]:
    tree = ast.parse((ROOT / "system1bench/llm_adapter.py").read_text())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"CODES", "SYSTEM"}:
                    values[target.id] = ast.literal_eval(node.value)
    assert set(values) == {"CODES", "SYSTEM"}
    return values["CODES"], values["SYSTEM"]


def messages_and_options(case: dict, mode: str, codes: list[str], system: str):
    question = case["questions"]["answer"]
    assert set(question) == {"type", "instructions", "criteria"}
    assert question["type"] == "choice"
    assert tuple(question["criteria"]) == LABELS
    options = [dict(code=codes[i], label=label, meaning=meaning)
               for i, (label, meaning) in enumerate(question["criteria"].items())]
    if mode in {"display_only", "both"}:
        options.reverse()
    if mode == "code_only":
        for option, code in zip(options, reversed(codes[:len(options)])):
            option["code"] = code
    if mode == "both":
        for i, option in enumerate(options):
            option["code"] = codes[i]
    code_for_label = {option["label"]: option["code"] for option in options}
    code_indices = [codes.index(code_for_label[label]) for label in LABELS]
    payload = dict(state=case["state"], question_type=question["type"],
                   instructions=question["instructions"], candidates=options)
    assert set(payload) == {"state", "question_type", "instructions", "candidates"}
    messages = [dict(role="system", content=system),
                dict(role="user", content=json.dumps(payload, ensure_ascii=False,
                                                     separators=(",", ":")))]
    return messages, options, code_indices


def replay() -> None:
    manifest = read(HERE / "manifest.json")
    frozen = read(HERE / "frozen.json")
    summary = read(HERE / "summary.json")
    assert file_sha(HERE / "frozen.json") == manifest["frozen_sha256"] == summary["frozen_sha256"]
    assert file_sha(HERE / "PROTOCOL.md") == manifest["protocol_sha256"] == summary["protocol_sha256"]
    assert file_sha(SOURCE / "frozen.json") == manifest["source_frozen_sha256"]
    source = read(SOURCE / "frozen.json")
    suites = {suite["name"]: suite["cases"] for suite in source["suites"]}
    base = suites[MODE_SUITES["base"]]
    both = suites[MODE_SUITES["both"]]
    specs = {row["id"]: row for row in frozen["rows"]}
    assert len(base) == len(both) == len(specs) == 180
    assert len({row["group"] for row in frozen["rows"]}) == 180
    assert Counter(row["gold"] for row in frozen["rows"]) == Counter({label: 60 for label in LABELS})
    codes, system = adapter_literals()
    state_keys = set()
    forbidden_state_keys = {"gold", "reference", "reference_label", "source_id", "source_split",
                            "split", "group", "dataset", "annotation", "annotated_label"}
    for case, reversed_case in zip(base, both):
        spec = specs[case["id"]]
        assert case["id"] == reversed_case["id"]
        assert case["state"] == reversed_case["state"]
        assert case["group"] == spec["group"]
        assert case["gold"]["answer"]["label"] == spec["gold"]
        assert case["request_sha256"] == spec["base_request_sha256"]
        assert reversed_case["request_sha256"] == spec["both_request_sha256"]
        assert isinstance(case["state"], dict)
        state_keys.update(case["state"])
        assert not (set(case["state"]) & forbidden_state_keys)
        for mode in MODES:
            messages, options, code_indices = messages_and_options(case, mode, codes, system)
            expected = spec["modes"][mode]
            assert content_sha(messages) == expected["messages_sha256"]
            assert content_sha(options) == expected["candidate_assignment_sha256"]
            assert code_indices == expected["canonical_code_indices"]

    report = {}
    for model in MODELS:
        outputs = {}
        new_meta = read(HERE / "results" / model / "metadata.json")
        assert new_meta["status"] == "DONE"
        assert new_meta["signature"]["batch_size"] == 4
        for mode in MODES:
            if mode in MODE_SUITES:
                path = SOURCE / "results/local" / model / (MODE_SUITES[mode] + ".json.gz")
                expected_hash = manifest["existing_output_sha256"][f"{model}/{mode}"]
            else:
                path = HERE / "results" / model / (mode + ".json.gz")
                expected_hash = new_meta["modes"][mode]["sha256"]
            assert file_sha(path) == expected_hash
            saved = read_gzip(path)
            rows = {row["id"]: row for row in saved["rows"]}
            assert len(saved["rows"]) == len(rows) == 180
            assert set(rows) == set(specs)
            outputs[mode] = rows
        model_report = {}
        for view in ("native", "common_tie"):
            predictions = {}
            correct = Counter()
            by_gold_correct = {label: Counter() for label in LABELS}
            invalid = Counter()
            ties = Counter()
            changed = Counter()
            transitions = {mode: Counter() for mode in MODES if mode != "base"}
            base_noinfo_dest = {mode: Counter() for mode in MODES}
            for case_id, spec in specs.items():
                current = {}
                for mode in MODES:
                    row = outputs[mode][case_id]
                    assert row["gold"] == spec["gold"] and row["group"] == spec["group"]
                    expected_request = spec[f"{mode}_request_sha256"] if mode in MODE_SUITES else spec["base_request_sha256"]
                    assert row["request_sha256"] == expected_request
                    if mode not in MODE_SUITES:
                        expected = spec["modes"][mode]
                        assert row["messages_sha256"] == expected["messages_sha256"]
                        assert row["candidate_assignment_sha256"] == expected["candidate_assignment_sha256"]
                        assert row["canonical_code_indices"] == expected["canonical_code_indices"]
                    if row["error"] is not None or row["prediction"] is None:
                        invalid[mode] += 1
                        current[mode] = None
                        continue
                    probabilities = row["answer"]["probabilities"]
                    assert set(probabilities) == set(LABELS)
                    largest = max(probabilities.values())
                    tied_labels = {label for label in LABELS if probabilities[label] == largest}
                    if len(tied_labels) > 1:
                        ties[mode] += 1
                    assert row["prediction"] in tied_labels
                    canonical = next(label for label in LABELS if label in tied_labels)
                    if row["prediction"] != canonical:
                        changed[mode] += 1
                    current[mode] = row["prediction"] if view == "native" else canonical
                    correct[mode] += current[mode] == spec["gold"]
                    by_gold_correct[spec["gold"]][mode] += current[mode] == spec["gold"]
                predictions[case_id] = current
                for mode in transitions:
                    transitions[mode][(current["base"], current[mode])] += 1
                if current["base"] == "NOINFO":
                    for mode in MODES:
                        base_noinfo_dest[mode][current[mode]] += 1
            flips = {mode: sum(n for (before, after), n in transitions[mode].items()
                               if before != after) for mode in transitions}
            expected = summary["models"][model][view]
            assert all(correct[mode] == expected["cells"][mode]["correct"] for mode in MODES)
            assert all(by_gold_correct[label][mode] == expected["by_gold_label"][label][mode]["correct"]
                       for label in LABELS for mode in MODES)
            assert all(invalid[mode] == expected["cells"][mode]["invalid"] for mode in MODES)
            assert all(flips[mode] == expected["comparisons"][f"base_to_{mode}"]["prediction_flips"] for mode in transitions)
            for mode, cells in transitions.items():
                observed_cells = {(before, after): n for (before, after), n in cells.items()}
                saved_cells = {(before, after): n
                               for before, destinations in expected["predicted_class_transitions_from_base"][mode].items()
                               for after, n in destinations.items()}
                assert observed_cells == saved_cells
            if view == "native":
                assert all(ties[mode] == summary["models"][model]["tie_diagnostic"][mode]["top_ties"] for mode in MODES)
                assert all(changed[mode] == summary["models"][model]["tie_diagnostic"][mode]["native_to_common_changed"] for mode in MODES)
            model_report[view] = dict(correct=dict(correct),
                                      by_gold_correct={label: dict(counts) for label, counts in by_gold_correct.items()},
                                      invalid=dict(invalid),
                                      base_flips=flips, top_ties=dict(ties),
                                      native_to_common_changed=dict(changed),
                                      base_noinfo_destinations={mode: dict(counts) for mode, counts in base_noinfo_dest.items()})
        report[model] = model_report
    print(json.dumps(dict(status="VERIFIED", source_state_keys=sorted(state_keys),
                          message_payload_keys=["state", "question_type", "instructions", "candidates"],
                          model_report=report), indent=2))


if __name__ == "__main__":
    replay()
