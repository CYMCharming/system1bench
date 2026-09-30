"""Freeze a prediction-independent, source-balanced strong-baseline subset."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, labels, read, request, sha, write  # noqa: E402

HERE = Path(__file__).resolve().parent
SPECS = [
    # (suite, qid, source, domain, requested n)
    ("ag_news", "answer", "AG News", "News", 12),
    ("emotion", "answer", "Emotion", "Social text", 12),
    ("sst5_choice", "answer", "SST-5", "Reviews", 12),
    ("banking77", "answer", "Banking77", "Banking support", 12),
    ("massive_en", "answer", "MASSIVE", "Assistant commands", 12),
    ("massive_zh", "answer", "MASSIVE", "Assistant commands", 12),
    ("clinc150_oos", "answer", "CLINC150/OOS", "Assistant intents", 12),
    ("boolq_choice", "answer", "BoolQ", "General QA", 12),
    ("xnli_en", "answer", "XNLI", "Natural inference", 12),
    ("xnli_zh", "answer", "XNLI", "Natural inference", 12),
    ("turtlebench", "answer", "TurtleBench", "Puzzle evidence", 12),
    ("prompt_injections", "answer", "Prompt injections", "Prompt security", 12),
    ("aegis2_prompt", "answer", "Aegis2 prompts", "Content safety", 12),
    ("typed_decisions", "urgency", "Typed decisions", "Mixed enterprise", 12),
    ("jevbench_hard", "answer", "JevBench", "Mixed fixtures", 8),
    ("reflexbench_reflex-public-choice-v1", "answer", "ReflexBench", "Product workflow", 12),
    ("jev_laya_claims", "verdict", "Jev–Laya", "Mixed workflow", 12),
    ("jev_laya_needle", "wants", "Jev–Laya", "Mixed workflow", 12),
]


def order_key(suite: str, case: dict) -> tuple[str, str]:
    value = f"strong-baseline-v1\0{suite}\0{case['id']}".encode()
    return hashlib.sha256(value).hexdigest(), str(case["id"])


def choose_cases(suite: dict, n: int) -> list[dict]:
    cases = suite["cases"]
    if suite["name"] == "clinc150_oos":
        rejected = sorted((c for c in cases if c["gold"]["answer"]["label"] == "oos"),
                          key=lambda c: order_key(suite["name"], c))[: n // 2]
        named = sorted((c for c in cases if c["gold"]["answer"]["label"] != "oos"),
                       key=lambda c: order_key(suite["name"], c))[: n - n // 2]
        selected = rejected + named
    else:
        selected = sorted(cases, key=lambda c: order_key(suite["name"], c))[:n]
    if len(selected) != n:
        raise ValueError(f"Insufficient source cases for {suite['name']}")
    return sorted(selected, key=lambda c: order_key(suite["name"], c))


def freeze(frozen: dict) -> dict:
    suites = {s["name"]: s for s in frozen["suites"]}
    if len(suites) != len(frozen["suites"]):
        raise ValueError("Duplicate suite names")
    if len({x[0] for x in SPECS}) != len(SPECS):
        raise ValueError("Duplicate suite specifications")
    result = []
    keys = []
    for name, qid, source, domain, n in SPECS:
        rows = []
        for case in choose_cases(suites[name], n):
            question = case["questions"][qid]
            gold = str(case["gold"][qid]["label"])
            if gold not in labels(question):
                raise ValueError(f"Gold label not in candidates: {name}/{case['id']}")
            if digest(request(case)) != case["request_sha256"]:
                raise ValueError(f"Input fingerprint mismatch: {name}/{case['id']}")
            key = (name, case["id"], qid)
            keys.append(key)
            rows.append(dict(id=case["id"], qid=qid, group=case["group"],
                             language=case["language"], state=case["state"],
                             question=question, gold=gold,
                             request_sha256=case["request_sha256"],
                             question_sha256=digest(question)))
        result.append(dict(suite=name, source=source, domain=domain,
                           original_n=len(suites[name]["cases"]), cases=rows))
    if len(keys) != len(set(keys)) or sum(map(lambda s: len(s["cases"]), result)) != 212:
        raise ValueError("Duplicate or missing selected cases")
    assert len(set(s["source"] for s in result)) == 15
    return dict(version="strong-baseline-v1", population="selected subset only",
                sampling="deterministic hash; CLINC150/OOS 6 rejected + 6 named",
                conditions=["direct", "deliberate"], suites=result)


def main() -> None:
    source = ROOT / "data/frozen.json"
    target = HERE / "frozen.json"
    manifest = HERE / "manifest.json"
    if target.exists() or manifest.exists():
        raise ValueError("Frozen outputs exist; never silently rewrite a launched protocol")
    selected = freeze(read(source))
    # Before writing any artifact, verify the historical comparator's full
    # selected request/reference identity. Predicted labels are not read.
    from system1bench.run import read_run  # noqa: E402

    original_hashes = {}
    for model in ("llama31_8b_instruct", "qwen3_8b"):
        for suite in selected["suites"]:
            path = ROOT / "results" / model / f"{suite['suite']}.json.gz"
            saved = read_run(path)
            by_key = {(r["id"], r["qid"]): r for r in saved["rows"]}
            if len(by_key) != len(saved["rows"]):
                raise ValueError(f"Duplicate original comparator row in {path}")
            for case in suite["cases"]:
                row = by_key[(case["id"], case["qid"])]
                if row["request_sha256"] != case["request_sha256"] or row["gold"] != case["gold"]:
                    raise ValueError(f"Original comparator mismatch in {path}")
            original_hashes[f"{model}/{suite['suite']}"] = sha(path)
    write(target, selected)
    write(manifest, dict(frozen_sha256=sha(target), source_frozen_sha256=sha(source),
                         generator_sha256=sha(__file__), protocol_sha256=sha(HERE / "PROTOCOL.md"),
                         original_output_sha256=original_hashes,
                         count_suites=len(selected["suites"]),
                         count_sources=len({s["source"] for s in selected["suites"]}),
                         count_requests=sum(len(s["cases"]) for s in selected["suites"])))
    print(json.dumps({k: v for k, v in read(manifest).items() if not k.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
