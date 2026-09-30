"""Freeze SciFact3 three-class 2x2 message and code hashes before inference."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, labels, read, request, sha, write  # noqa: E402
from system1bench.llm_adapter import CODES, SYSTEM, candidates, messages  # noqa: E402
from system1bench.run import read_run  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "research/scifact3_v1"
MODES = ("base", "display_only", "code_only", "both")
MODE_SUITES = {"base": "scifact3_base", "both": "scifact3_reversed_option_order"}
MODEL_NAMES = ("llama31_8b_instruct", "qwen3_8b")


def render(state: dict, question: dict, mode: str) -> tuple[list[dict], list[int], list[dict]]:
    options = deepcopy(candidates(question))
    if mode == "display_only":
        options.reverse()
    elif mode == "code_only":
        for option, code in zip(options, reversed(CODES[:len(options)])):
            option["code"] = code
    elif mode == "both":
        options.reverse()
        for index, option in enumerate(options):
            option["code"] = CODES[index]
    elif mode != "base":
        raise ValueError(mode)
    code_by_label = {option["label"]: option["code"] for option in options}
    if (len(code_by_label) != len(options)
        or len(set(code_by_label.values())) != len(options)):
        raise ValueError("Duplicate labels/codes")
    code_indices = [CODES.index(code_by_label[label]) for label in labels(question)]
    payload = dict(state=state, question_type=question["type"],
                   instructions=question["instructions"], candidates=options)
    msgs = [dict(role="system", content=SYSTEM),
            dict(role="user", content=json.dumps(payload, ensure_ascii=False,
                                                 separators=(",", ":")))]
    return msgs, code_indices, options


def selected_source(source: dict) -> tuple[list[dict], list[dict]]:
    suites = {suite["name"]: suite for suite in source["suites"]}
    base = suites["scifact3_base"]["cases"]
    both = suites["scifact3_reversed_option_order"]["cases"]
    if len(base) != 180 or len(both) != 180:
        raise ValueError("Unexpected SciFact3 case count")
    if len({case["id"] for case in base}) != 180:
        raise ValueError("Duplicate source IDs")
    by_id = {case["id"]: case for case in both}
    if len(by_id) != 180 or set(by_id) != {case["id"] for case in base}:
        raise ValueError("Base/reversal IDs mismatch")
    if len({case["group"] for case in base}) != 180:
        raise ValueError("Claim cluster uniqueness changed")
    gold = {label: 0 for label in ("SUPPORT", "CONTRADICT", "NOINFO")}
    for case, rev in zip(base, both):
        if case["id"] != rev["id"] or case["state"] != rev["state"]:
            raise ValueError("Historical source ordering/state mismatch")
        if case["group"] != rev["group"] or case["gold"] != rev["gold"]:
            raise ValueError("Historical group/reference mismatch")
        if digest(request(case)) != case["request_sha256"] or digest(request(rev)) != rev["request_sha256"]:
            raise ValueError("Source request hash mismatch")
        question, reversed_question = case["questions"]["answer"], rev["questions"]["answer"]
        if list(reversed_question["criteria"].items()) != list(reversed(list(question["criteria"].items()))):
            raise ValueError("Historical reversal changes more than order")
        if ({k: v for k, v in question.items() if k != "criteria"}
            != {k: v for k, v in reversed_question.items() if k != "criteria"}):
            raise ValueError("Historical question fields changed")
        if render(case["state"], question, "base")[0] != messages(case["state"], question):
            raise ValueError("Base messages differ from adapter")
        if render(case["state"], question, "both")[0] != messages(rev["state"], reversed_question):
            raise ValueError("Joint messages differ from historical reversal")
        gold[str(case["gold"]["answer"]["label"])] += 1
    if set(gold.values()) != {60}:
        raise ValueError("Balanced selected labels changed")
    return base, both


def main() -> None:
    if (HERE / "frozen.json").exists() or (HERE / "manifest.json").exists():
        raise ValueError("SciFact3 codebook freeze already exists")
    source_manifest = read(SOURCE / "manifest.json")
    if sha(SOURCE / "frozen.json") != source_manifest["prepared_sha256"]:
        raise ValueError("SciFact3 source freeze changed")
    base, both = selected_source(read(SOURCE / "frozen.json"))
    rows = []
    for case, rev in zip(base, both):
        question = case["questions"]["answer"]
        modes = {}
        for mode in MODES:
            msgs, code_indices, options = render(case["state"], question, mode)
            modes[mode] = dict(messages_sha256=digest(msgs),
                               candidate_assignment_sha256=digest(options),
                               canonical_code_indices=code_indices)
        rows.append(dict(id=case["id"], group=case["group"],
                         gold=str(case["gold"]["answer"]["label"]),
                         base_request_sha256=case["request_sha256"],
                         both_request_sha256=rev["request_sha256"],
                         base_question_sha256=digest(question),
                         both_question_sha256=digest(rev["questions"]["answer"]),
                         modes=modes))
    output_hashes = {}
    metadata_hashes = {}
    for model in MODEL_NAMES:
        directory = SOURCE / "results/local" / model
        metadata = read(directory / "metadata.json")
        if metadata["status"] != "DONE" or metadata["signature"]["batch_size"] != 4:
            raise ValueError("Historical SciFact3 model run not batch four/complete")
        metadata_hashes[model] = sha(directory / "metadata.json")
        for mode, suite in MODE_SUITES.items():
            path = directory / f"{suite}.json.gz"
            saved = read_run(path)
            if len(saved["rows"]) != 180:
                raise ValueError("Historical results incomplete")
            for index, (old, frozen_row) in enumerate(zip(saved["rows"], rows)):
                if (old["id"] != frozen_row["id"] or old["batch_id"] != index // 4
                    or old["gold"] != frozen_row["gold"]
                    or old["request_sha256"] != frozen_row[f"{mode}_request_sha256"]):
                    raise ValueError("Historical result case/batch mismatch")
            output_hashes[f"{model}/{mode}"] = sha(path)
    write(HERE / "frozen.json", dict(version="scifact3-codebook-v1", original_cases=180,
                                      claim_groups=180, modes=list(MODES), rows=rows))
    write(HERE / "manifest.json", dict(frozen_sha256=sha(HERE / "frozen.json"),
                                         source_frozen_sha256=sha(SOURCE / "frozen.json"),
                                         source_manifest_sha256=sha(SOURCE / "manifest.json"),
                                         freeze_code_sha256=sha(__file__),
                                         protocol_sha256=sha(HERE / "PROTOCOL.md"),
                                         existing_output_sha256=output_hashes,
                                         source_metadata_sha256=metadata_hashes,
                                         cases=180, claim_groups=180,
                                         new_decisions_per_model=360, batch_size=4))
    print("Frozen 180 SciFact3 pairs; no source text copied")


if __name__ == "__main__":
    main()
