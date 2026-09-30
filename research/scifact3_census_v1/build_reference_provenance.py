"""Build a source-checked, text-free SciFact3 reference-provenance sidecar.

The frozen requests and their legacy suite-level ``reference`` field are never
modified. Run this for either scifact3_v1 or scifact3_census_v1, then use
``--check`` to verify the generated sidecar without rewriting it.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


LABEL_TYPES = {
    "SUPPORT": "official_abstract_evidence_annotation",
    "CONTRADICT": "official_abstract_evidence_annotation",
    "NOINFO": "derived_cited_pair_without_annotated_abstract_evidence",
}
EXPECTED = {
    "scifact3_v1": {"SUPPORT": 60, "CONTRADICT": 60, "NOINFO": 60},
    "scifact3_census_v1": {"SUPPORT": 138, "CONTRADICT": 71, "NOINFO": 130},
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def build(root, name):
    target = root / "research" / name
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    frozen_path = target / "frozen.json"
    assert sha256(frozen_path) == manifest["prepared_sha256"]
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    suites = {suite["condition"]: suite for suite in frozen["suites"]}
    assert set(suites) == {"base", "exact_repeat", "reversed_option_order", "title_removed"}
    assert all(suite["reference"] == "source_annotation" for suite in suites.values())
    base_cases = suites["base"]["cases"]
    ordered_ids = [case["id"] for case in base_cases]
    assert len(ordered_ids) == len(set(ordered_ids))
    for suite in suites.values():
        assert [case["id"] for case in suite["cases"]] == ordered_ids
        assert [case["gold"] for case in suite["cases"]] == [case["gold"] for case in base_cases]

    source_dir = root / "data" / "external" / "domain_expansion_v1" / "scifact" / "data"
    claims_path = source_dir / "claims_dev.jsonl"
    corpus_path = source_dir / "corpus.jsonl"
    assert sha256(claims_path) == manifest["source_sha256"]["claims_dev.jsonl"]
    assert sha256(corpus_path) == manifest["source_sha256"]["corpus.jsonl"]
    claims = {item["id"]: item for item in load_jsonl(claims_path)}
    documents = {item["doc_id"] for item in load_jsonl(corpus_path)}

    rows = []
    for case in base_cases:
        assert case["source_split"] == "dev"
        claim_id = case["source_id"]["claim_id"]
        doc_id = case["source_id"]["doc_id"]
        label = case["gold"]["answer"]["label"]
        assert label in LABEL_TYPES
        assert case["id"] == f"scifact3-dev:{claim_id}:{doc_id}"
        claim = claims[claim_id]
        assert doc_id in claim["cited_doc_ids"] and doc_id in documents
        evidence = claim["evidence"]
        entry = evidence.get(str(doc_id))
        if label == "NOINFO":
            assert str(doc_id) not in evidence
            assert entry is None
        else:
            assert entry and {item["label"] for item in entry} == {label}
        rows.append({
            "case_id": case["id"],
            "claim_id": claim_id,
            "document_id": doc_id,
            "reference_label": label,
            "reference_type": LABEL_TYPES[label],
            "base_request_sha256": case["request_sha256"],
        })

    counts = dict(Counter(row["reference_label"] for row in rows))
    assert counts == EXPECTED[name]
    return {
        "schema": "system1bench.scifact3.reference_provenance.v1",
        "protocol": frozen["protocol"],
        "source_split": "official_scifact_dev",
        "source_schema_url": "https://github.com/allenai/scifact/blob/master/doc/data.md",
        "source_license_url": "https://github.com/allenai/scifact/blob/master/LICENSE.md",
        "frozen_sha256": manifest["prepared_sha256"],
        "source_sha256": {
            "claims_dev.jsonl": manifest["source_sha256"]["claims_dev.jsonl"],
            "corpus.jsonl": manifest["source_sha256"]["corpus.jsonl"],
        },
        "legacy_suite_reference": "source_annotation",
        "legacy_suite_reference_caveat": (
            "This frozen suite-level field is not a per-case annotation claim. "
            "Use each case's reference_type below."
        ),
        "reference_type_by_label": {
            "SUPPORT": {
                "type": LABEL_TYPES["SUPPORT"],
                "derivation": "Nonempty official evidence entry for this cited document; all rationale labels SUPPORT.",
            },
            "CONTRADICT": {
                "type": LABEL_TYPES["CONTRADICT"],
                "derivation": "Nonempty official evidence entry for this cited document; all rationale labels CONTRADICT.",
            },
            "NOINFO": {
                "type": LABEL_TYPES["NOINFO"],
                "derivation": "Document occurs in cited_doc_ids but has no evidence entry for this claim.",
                "limitations": (
                    "Not independently adjudicated as neutral; does not establish absence "
                    "of evidence in full text or the wider literature."
                ),
            },
        },
        "label_counts": counts,
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=sorted(EXPECTED))
    parser.add_argument("--check", action="store_true", help="Verify existing sidecar without writing")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    target = root / "research" / args.name / "reference_provenance.json"
    expected = json.dumps(build(root, args.name), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        assert target.read_text(encoding="utf-8") == expected
        status = "verified"
    elif target.exists():
        assert target.read_text(encoding="utf-8") == expected, "Existing sidecar differs; refusing overwrite"
        status = "already_current"
    else:
        target.write_text(expected, encoding="utf-8")
        status = "created"
    print(json.dumps({"status": status, "path": str(target),
                      "sha256": sha256(target), "cases": len(json.loads(expected)["cases"])},
                     sort_keys=True))


if __name__ == "__main__":
    main()
