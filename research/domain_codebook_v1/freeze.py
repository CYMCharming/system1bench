"""Freeze exact orthogonal prompt fingerprints before ContractNLI inference."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, labels, read, request, sha, write  # noqa: E402
from system1bench.llm_adapter import CODES, SYSTEM, candidates, messages  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "research/domain_expansion_v1"
MODES = ("base", "display_only", "code_only", "both")
MODE_SUITES = {"base": "contractnli_base", "both": "contractnli_reversed_option_order"}


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
    assigned = {x["label"]: x["code"] for x in options}
    if len(assigned) != len(options) or len(set(assigned.values())) != len(options):
        raise ValueError("Duplicate semantic labels or candidate codes")
    code_indices = [CODES.index(assigned[label]) for label in labels(question)]
    payload = dict(state=state, question_type=question["type"],
                   instructions=question["instructions"], candidates=options)
    msgs = [dict(role="system", content=SYSTEM),
            dict(role="user", content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))]
    return msgs, code_indices, options


def selected_source(frozen: dict) -> tuple[list[dict], list[dict]]:
    suites = {s["name"]: s for s in frozen["suites"]}
    base = suites["contractnli_base"]["cases"]
    both = suites["contractnli_reversed_option_order"]["cases"]
    if len(base) != 144 or len(both) != 144:
        raise ValueError("Unexpected ContractNLI case count")
    if len({c["id"] for c in base}) != 144 or len({c["id"] for c in both}) != 144:
        raise ValueError("Duplicate case IDs")
    reversed_by_id = {c["id"]: c for c in both}
    if set(reversed_by_id) != {c["id"] for c in base}:
        raise ValueError("Base/reversal ID mismatch")
    for case in base:
        rev = reversed_by_id[case["id"]]
        if case["state"] != rev["state"] or case["group"] != rev["group"] or case["gold"] != rev["gold"]:
            raise ValueError("Semantic base/reversal mismatch")
        if digest(request(case)) != case["request_sha256"] or digest(request(rev)) != rev["request_sha256"]:
            raise ValueError("Original source fingerprint mismatch")
        q = case["questions"]["answer"]
        rq = rev["questions"]["answer"]
        if list(rq["criteria"].items()) != list(reversed(list(q["criteria"].items()))):
            raise ValueError("Reversal changes more than option order")
        if {k: v for k, v in q.items() if k != "criteria"} != {k: v for k, v in rq.items() if k != "criteria"}:
            raise ValueError("Reversal changed question metadata")
        if render(case["state"], q, "base")[0] != messages(case["state"], q):
            raise ValueError("Base prompt differs from historical adapter")
        if render(case["state"], q, "both")[0] != messages(rev["state"], rq):
            raise ValueError("Both prompt differs from ordinary reversal")
    return base, both


def main() -> None:
    if (HERE / "frozen.json").exists() or (HERE / "manifest.json").exists():
        raise ValueError("Frozen artifacts already exist; never overwrite")
    source_file = SOURCE / "frozen.json"
    source_manifest = read(SOURCE / "manifest.json")
    if sha(source_file) != source_manifest["prepared_sha256"]:
        raise ValueError("Source frozen file changed")
    base, both = selected_source(read(source_file))
    reversed_by_id = {c["id"]: c for c in both}
    rows = []
    for case in base:
        rev = reversed_by_id[case["id"]]
        q = case["questions"]["answer"]
        renders = {}
        for mode in MODES:
            msg, codes, options = render(case["state"], q, mode)
            renders[mode] = dict(messages_sha256=digest(msg),
                                 candidate_assignment_sha256=digest(options),
                                 canonical_code_indices=codes)
        rows.append(dict(id=case["id"], group=case["group"],
                         gold=str(case["gold"]["answer"]["label"]),
                         base_request_sha256=case["request_sha256"],
                         both_request_sha256=rev["request_sha256"],
                         base_question_sha256=digest(q),
                         both_question_sha256=digest(rev["questions"]["answer"]),
                         modes=renders))
    from system1bench.run import read_run  # noqa: E402

    output_hashes = {}
    for model in ("llama31_8b_instruct", "qwen3_8b"):
        for mode, suite in MODE_SUITES.items():
            path = SOURCE / "results" / "local" / model / f"{suite}.json.gz"
            saved = read_run(path)
            by_id = {r["id"]: r for r in saved["rows"]}
            if len(by_id) != 144:
                raise ValueError("Existing output missing/duplicated rows")
            for row in rows:
                original = by_id[row["id"]]
                if original["gold"] != row["gold"] or original["request_sha256"] != row[f"{mode}_request_sha256"]:
                    raise ValueError("Existing output input/reference mismatch")
            output_hashes[f"{model}/{mode}"] = sha(path)
    selected = dict(version="domain-codebook-v1", source="ContractNLI test",
                    original_cases=144, document_groups=len({x["group"] for x in rows}),
                    modes=list(MODES), rows=rows)
    write(HERE / "frozen.json", selected)
    write(HERE / "manifest.json", dict(frozen_sha256=sha(HERE / "frozen.json"),
                                         source_frozen_sha256=sha(source_file),
                                         source_manifest_sha256=sha(SOURCE / "manifest.json"),
                                         freeze_code_sha256=sha(__file__),
                                         protocol_sha256=sha(HERE / "PROTOCOL.md"),
                                         existing_output_sha256=output_hashes,
                                         cases=144, document_groups=selected["document_groups"],
                                         new_decisions_per_model=288))
    print("Frozen", len(rows), "cases /", selected["document_groups"], "documents")


if __name__ == "__main__":
    main()
