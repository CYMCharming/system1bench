"""Freeze ID/hash-only natural-domain direct-generation cases before inference."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import digest, labels, read, request, sha, write  # noqa: E402
from system1bench.llm_adapter import candidates, messages  # noqa: E402
from system1bench.run import read_run  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCES = {
    "legal": (ROOT / "research/domain_expansion_v1", "contractnli_base"),
    "science": (ROOT / "research/scifact3_v1", "scifact3_base"),
}
MODELS = ("llama31_8b_instruct", "qwen3_8b")


def source_cases() -> dict[str, list[dict]]:
    selected = {}
    for domain, (directory, suite_name) in SOURCES.items():
        manifest = read(directory / "manifest.json")
        if sha(directory / "frozen.json") != manifest["prepared_sha256"]:
            raise ValueError(f"Changed {domain} source freeze")
        suites = {suite["name"]: suite for suite in read(directory / "frozen.json")["suites"]}
        cases = suites[suite_name]["cases"]
        expected = 144 if domain == "legal" else 180
        if len(cases) != expected or len({case["id"] for case in cases}) != expected:
            raise ValueError(f"Changed {domain} case selection")
        selected[domain] = cases
    return selected


def main() -> None:
    if (HERE / "frozen.json").exists() or (HERE / "manifest.json").exists():
        raise ValueError("Direct-control freeze already exists; never overwrite")
    cases_by_domain = source_cases()
    rows = []
    old_hashes = {}
    old_metadata_hashes = {}
    for domain, cases in cases_by_domain.items():
        directory, suite_name = SOURCES[domain]
        groups = {case["group"] for case in cases}
        if len(groups) != (91 if domain == "legal" else 180):
            raise ValueError("Unexpected source-cluster count")
        for case in cases:
            if digest(request(case)) != case["request_sha256"]:
                raise ValueError("Source request hash mismatch")
            if set(case["questions"]) != {"answer"} or set(case["gold"]) != {"answer"}:
                raise ValueError("Expected one answer question per case")
            question = case["questions"]["answer"]
            gold = str(case["gold"]["answer"]["label"])
            allowed = labels(question)
            if gold not in allowed:
                raise ValueError("Gold outside candidate labels")
            opts = candidates(question)
            rows.append(dict(domain=domain, suite=suite_name, id=case["id"],
                             group=case["group"], gold=gold,
                             request_sha256=case["request_sha256"],
                             question_sha256=digest(question),
                             messages_sha256=digest(messages(case["state"], question)),
                             labels=allowed, codes=[option["code"] for option in opts]))
        expected_by_id = {case["id"]: case for case in cases}
        for model in MODELS:
            outdir = directory / "results/local" / model
            metadata_path = outdir / "metadata.json"
            metadata = read(metadata_path)
            if metadata["status"] != "DONE" or metadata["signature"]["batch_size"] != 4:
                raise ValueError("Incomplete/nonmatched historical model run")
            old_metadata_hashes[f"{domain}/{model}"] = sha(metadata_path)
            path = outdir / f"{suite_name}.json.gz"
            saved = read_run(path)
            by_id = {row["id"]: row for row in saved["rows"]}
            if len(by_id) != len(expected_by_id) or set(by_id) != set(expected_by_id):
                raise ValueError("Historical output IDs mismatch")
            for case_id, case in expected_by_id.items():
                old = by_id[case_id]
                if (old["qid"] != "answer" or old["group"] != case["group"]
                    or old["request_sha256"] != case["request_sha256"]
                    or old["gold"] != str(case["gold"]["answer"]["label"])
                    or old["questions_sha256"] != digest(case["questions"])):
                    raise ValueError("Historical output input/reference mismatch")
                if "prompt_token_sha256" not in old["audit"]:
                    raise ValueError("Historical prompt audit unavailable")
            old_hashes[f"{domain}/{model}"] = sha(path)
    frozen = dict(version="natural-direct-v1", domains=["legal", "science"],
                  models=list(MODELS), cases=rows)
    write(HERE / "frozen.json", frozen)
    write(HERE / "manifest.json", dict(
        frozen_sha256=sha(HERE / "frozen.json"),
        protocol_sha256=sha(HERE / "PROTOCOL.md"),
        freeze_code_sha256=sha(__file__),
        parser_code_sha256=sha(ROOT / "benchmarks/strong_baseline.py"),
        adapter_code_sha256=sha(ROOT / "system1bench/llm_adapter.py"),
        source_frozen_sha256={domain: sha(directory / "frozen.json")
                              for domain, (directory, _) in SOURCES.items()},
        source_manifest_sha256={domain: sha(directory / "manifest.json")
                                for domain, (directory, _) in SOURCES.items()},
        old_output_sha256=old_hashes, old_metadata_sha256=old_metadata_hashes,
        case_counts={domain: len(cases) for domain, cases in cases_by_domain.items()},
        cluster_counts={domain: len({case["group"] for case in cases})
                        for domain, cases in cases_by_domain.items()},
        generations_per_model=len(rows)))
    print("Frozen", len(rows), "ID/hash-only cases")


if __name__ == "__main__":
    main()
