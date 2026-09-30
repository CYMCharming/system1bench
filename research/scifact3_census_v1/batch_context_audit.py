"""Describe co-batch IDs and logit margins for changed Qwen overlap cases."""

import gzip
import json
from pathlib import Path

from system1bench.common import sha, write

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "research/scifact3_v1"
NEW = ROOT / "research/scifact3_census_v1"


def read(path):
    return json.loads(path.read_text())


def payload(out, condition):
    directory = out / "results/local/qwen3_8b"
    metadata = read(directory / "metadata.json")
    suite = f"scifact3_{condition}"
    path = directory / f"{suite}.json.gz"
    assert sha(path) == metadata["suites"][suite]["sha256"]
    return json.loads(gzip.decompress(path.read_bytes()))


def peers(rows, batch_id):
    return [r["id"] for r in rows if r["batch_id"] == batch_id]


def logits(row):
    values = row["answer"]["candidate_logits"]
    return {"candidate_logits": values,
            "top_two_margin": sorted(values, reverse=True)[0] - sorted(values, reverse=True)[1]}


def main():
    overlap = read(NEW / "overlap_audit.json")["models"]["qwen3_8b"]
    report = {"description": "Changed identical-prompt Qwen overlap cases; co-batch sets and raw adapter-code logit margins only; no causal batching claim",
              "conditions": {}}
    for condition in ("base", "reversed_option_order"):
        previous, fresh = payload(OLD, condition), payload(NEW, condition)
        old_rows = {r["id"]: r for r in previous["rows"]}
        new_rows = {r["id"]: r for r in fresh["rows"]}
        entries = []
        for change in overlap[condition]["changes"]:
            case_id = change["id"]
            a, b = old_rows[case_id], new_rows[case_id]
            assert a["request_sha256"] == b["request_sha256"]
            assert a["audit"]["prompt_token_sha256"] == b["audit"]["prompt_token_sha256"]
            first, second = peers(previous["rows"], a["batch_id"]), peers(fresh["rows"], b["batch_id"])
            assert len(first) == len(second) == 4
            entries.append({"id": case_id, "old_batch_peer_ids": first,
                            "fresh_batch_peer_ids": second,
                            "same_ordered_batch": first == second,
                            "same_batch_members": set(first) == set(second),
                            "old": logits(a), "fresh": logits(b)})
        report["conditions"][condition] = entries
    target = NEW / "batch_context_audit.json"
    if target.exists():
        raise FileExistsError("Batch context audit exists")
    write(target, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
