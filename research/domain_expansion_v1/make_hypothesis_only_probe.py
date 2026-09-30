"""Freeze a post-hoc, hypothesis-only ContractNLI shortcut probe; no inference.

All 144 requests omit contract text, document identifiers, URLs and filenames.
The 17 official hypotheses yield 17 distinct inference payloads. The original
reference is kept only for retrospective agreement scoring, not as an answer
available from the withheld evidence. Refuses to overwrite an existing freeze.
"""

from collections import Counter, defaultdict
import copy
import json
from pathlib import Path

from system1bench.common import digest, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "research/domain_expansion_v1"
OUT = BASE / "hypothesis_only_probe"
LABELS = ("Entailment", "Contradiction", "NotMentioned")


def main():
    source_path = BASE / "frozen.json"
    source = json.loads(source_path.read_text())
    original = next(s["cases"] for s in source["suites"] if s["name"] == "contractnli_base")
    assert len(original) == 144
    cases = []
    for base in original:
        item = {
            "id": base["id"],
            "state": {"hypothesis": base["state"]["hypothesis"]},
            "questions": {"answer": {
                "type": "choice",
                "instructions": (
                    "Dataset-prior audit: the contract text is intentionally withheld. "
                    "For this hypothesis alone, predict which ContractNLI annotation "
                    "is most likely across NDA documents. You cannot determine the "
                    "actual withheld contract's meaning; choose the most likely "
                    "dataset label, not a legal conclusion."
                ),
                "criteria": {
                    "Entailment": "This hypothesis is affirmed in the withheld contract.",
                    "Contradiction": "This hypothesis is negated in the withheld contract.",
                    "NotMentioned": "The withheld contract neither affirms nor negates this hypothesis.",
                },
            }},
            "gold": copy.deepcopy(base["gold"]),
            "group": base["group"],
            "family": "contractnli_hypothesis_only_probe",
            "language": "en",
            "source_id": copy.deepcopy(base["source_id"]),
            "source_split": base["source_split"],
        }
        assert list(item["questions"]["answer"]["criteria"]) == list(LABELS)
        item["request_sha256"] = digest(request(item))
        assert "contract_text" not in item["state"]
        assert all(forbidden not in json.dumps(request(item)).lower()
                   for forbidden in ("document_id", "file_name", "source_id", "url"))
        cases.append(item)
    hashes = defaultdict(set)
    for case in cases:
        hashes[case["source_id"]["hypothesis_id"]].add(case["request_sha256"])
    assert len(hashes) == 17
    assert all(len(values) == 1 for values in hashes.values())
    assert len({case["request_sha256"] for case in cases}) == 17
    assert Counter(case["gold"]["answer"]["label"] for case in cases) == Counter({x: 48 for x in LABELS})
    freeze = {
        "protocol": "contractnli-hypothesis-only-shortcut-probe-v1",
        "status": "frozen-before-probe-inference; post-hoc to the full-text experiment",
        "source_frozen_sha256": sha(source_path),
        "requests": len(cases),
        "unique_request_payloads": 17,
        "suite": {
            "name": "contractnli_hypothesis_only",
            "track": "posthoc_shortcut_probe",
            "reference": "official_test_annotation_under_withheld_evidence",
            "source": "contractnli",
            "condition": "hypothesis_only_prior_elicitation",
            "cases": cases,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    frozen_path = OUT / "frozen.json"
    manifest_path = OUT / "manifest.json"
    if frozen_path.exists() or manifest_path.exists():
        raise FileExistsError("Hypothesis-only probe already frozen; refusing overwrite")
    write(frozen_path, freeze)
    write(manifest_path, {
        "protocol": freeze["protocol"],
        "status": freeze["status"],
        "frozen_sha256": sha(frozen_path),
        "preparer_sha256": sha(Path(__file__)),
        "source_frozen_sha256": sha(source_path),
        "requests": len(cases),
        "unique_payloads": 17,
        "different_contracts_same_hypothesis_share_request": True,
        "interpretation": (
            "Post-hoc dataset-prior behavior probe. The original contract text is absent "
            "and the original official label is not inferable per case. Compare with the "
            "official-train hypothesis-ID prior; never rank as legal NLI accuracy."
        ),
        "inference_run": False,
    })
    print(f"Frozen {len(cases)} hypothesis-only requests ({len(hashes)} unique payloads) at {frozen_path}")


if __name__ == "__main__":
    main()
