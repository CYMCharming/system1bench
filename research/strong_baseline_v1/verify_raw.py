"""Independent raw-text reparse and pairing audit for all new generations."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import labels, read, sha  # noqa: E402
from system1bench.llm_adapter import candidates  # noqa: E402

HERE = Path(__file__).resolve().parent


def parse_independent(text: str, mode: str, question: dict) -> tuple[str | None, str | None]:
    code = None
    if mode == "direct":
        if re.fullmatch(r"\s*[A-Z]{1,2}\s*", text, flags=re.ASCII):
            code = text.strip()
    elif mode == "deliberate":
        nonempty = [s.strip() for s in text.splitlines() if s.strip()]
        if nonempty and re.fullmatch(r"FINAL: [A-Z]{1,2}", nonempty[-1], flags=re.ASCII):
            code = nonempty[-1].split(" ", 1)[1]
    else:
        raise ValueError(mode)
    mapping = {c["code"]: label for c, label in zip(candidates(question), labels(question))}
    if code not in mapping:
        return code, None
    return code, mapping[code]


def main() -> None:
    manifest = read(HERE / "manifest.json")
    if sha(HERE / "frozen.json") != manifest["frozen_sha256"]:
        raise ValueError("Frozen file changed")
    frozen = read(HERE / "frozen.json")
    cases = {(s["suite"], c["id"], c["qid"]): c for s in frozen["suites"] for c in s["cases"]}
    assert len(cases) == 212
    for model in ("llama31_8b_instruct", "qwen3_8b"):
        metadata = read(HERE / "results" / model / "metadata.json")
        raw_path = HERE / "results" / model / "raw.jsonl"
        if metadata["status"] != "DONE" or sha(raw_path) != metadata["raw_sha256"]:
            raise ValueError("Raw output file changed")
        rows = [json.loads(line) for line in raw_path.read_text().splitlines()]
        keys = {(r["mode"], r["suite"], r["id"], r["qid"]) for r in rows}
        expected = {(mode, *key) for mode in ("direct", "deliberate") for key in cases}
        if len(rows) != len(keys) or keys != expected:
            raise ValueError("Missing, duplicate or unexpected output rows")
        invalid = Counter()
        for row in rows:
            case = cases[(row["suite"], row["id"], row["qid"])]
            if row["gold"] != case["gold"] or row["request_sha256"] != case["request_sha256"]:
                raise ValueError("Input/reference mismatch")
            code, label = parse_independent(row["raw_text"], row["mode"], case["question"])
            if code != row["code"] or label != row["prediction"]:
                raise ValueError(f"Parser mismatch: {model}/{row['mode']}/{row['id']}")
            if (label is None) != (row["error"] is not None):
                raise ValueError("Invalid flag mismatch")
            if row["completion_tokens"] < 1 or row["prompt_tokens"] < 1 or row["batch_seconds"] <= 0:
                raise ValueError("Impossible token/timing observation")
            if row["error"]:
                invalid[(row["mode"], row["error"])] += 1
        print(model, "verified", len(rows), "rows", "invalid", dict(invalid))


if __name__ == "__main__":
    main()
