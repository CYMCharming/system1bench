"""Clearly post-hoc parser tolerance check; never rewrites registered outcomes."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import labels, read, sha, write  # noqa: E402
from system1bench.llm_adapter import candidates  # noqa: E402

HERE = Path(__file__).resolve().parent
TAIL = re.compile(r"\bFINAL:\s*([A-Z]{1,2})\s*\Z", re.ASCII)


def main() -> None:
    manifest = read(HERE / "manifest.json")
    frozen = read(HERE / "frozen.json")
    if sha(HERE / "frozen.json") != manifest["frozen_sha256"]:
        raise ValueError("Frozen inputs changed")
    specs = {(s["suite"], c["id"], c["qid"]): c
             for s in frozen["suites"] for c in s["cases"]}
    outcome = {}
    for model in ("llama31_8b_instruct", "qwen3_8b"):
        metadata = read(HERE / "results" / model / "metadata.json")
        path = HERE / "results" / model / "raw.jsonl"
        if metadata["status"] != "DONE" or sha(path) != metadata["raw_sha256"]:
            raise ValueError("Raw run mismatch")
        invalid = []
        primary_correct = 0
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row["mode"] != "deliberate":
                continue
            primary_correct += row["prediction"] == row["gold"]
            if row["error"] is None:
                continue
            case = specs[(row["suite"], row["id"], row["qid"])]
            allowed = labels(case["question"])
            codes = [x["code"] for x in candidates(case["question"])]
            match = TAIL.search(row["raw_text"])
            code = match.group(1) if match else None
            prediction = allowed[codes.index(code)] if code in codes else None
            invalid.append(dict(suite=row["suite"], id=row["id"], reason=row["error"],
                                code=code, recovered_prediction=prediction,
                                recovered_correct=prediction == row["gold"] if prediction else None,
                                primary_prediction=row["prediction"]))
        rescued = [r for r in invalid if r["recovered_prediction"] is not None]
        recovered_correct = sum(r["recovered_correct"] for r in rescued)
        outcome[model] = dict(status="POST_HOC_PARSER_SENSITIVITY_NOT_PRIMARY",
                              invalid=len(invalid), recovered=len(rescued),
                              recovered_correct=recovered_correct,
                              primary_correct=primary_correct,
                              permissive_correct=primary_correct + recovered_correct,
                              denominator=212, invalid_rows=invalid)
    write(HERE / "posthoc_parse_sensitivity.json", outcome)
    for model, result in outcome.items():
        print(model, {k: v for k, v in result.items() if k != "invalid_rows"})


if __name__ == "__main__":
    main()
