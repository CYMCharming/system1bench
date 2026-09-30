"""Independent CPU-only validation of the full cited-pair SciFact census."""

import json
from collections import Counter
from pathlib import Path

from system1bench.common import digest, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_census_v1"
PRIOR = ROOT / "research/scifact3_v1"
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"


def rows(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    frozen_path, manifest_path = OUT / "frozen.json", OUT / "manifest.json"
    frozen = json.loads(frozen_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    claims = {row["id"]: row for row in rows(SCIENCE / "claims_dev.jsonl")}
    documents = {row["doc_id"]: row for row in rows(SCIENCE / "corpus.jsonl")}
    assert sha(frozen_path) == manifest["prepared_sha256"]
    assert sha(SCIENCE / "claims_dev.jsonl") == manifest["source_sha256"]["claims_dev.jsonl"]
    assert sha(SCIENCE / "corpus.jsonl") == manifest["source_sha256"]["corpus.jsonl"]
    suites = {suite["condition"]: suite["cases"] for suite in frozen["suites"]}
    assert list(suites) == ["base", "exact_repeat", "reversed_option_order", "title_removed"]
    assert {condition: len(cases) for condition, cases in suites.items()} == {
        condition: 339 for condition in suites}

    ids_by_condition = {condition: [c["id"] for c in cases]
                        for condition, cases in suites.items()}
    assert all(ids == ids_by_condition["base"] for ids in ids_by_condition.values())
    assert len(set(ids_by_condition["base"])) == 339
    label_counts, claim_ids, doc_ids = Counter(), set(), set()
    for base, repeat, reversed_case, titleless in zip(*suites.values()):
        claim_id = base["source_id"]["claim_id"]
        doc_id = base["source_id"]["doc_id"]
        claim = claims[claim_id]
        doc = documents[doc_id]
        assert doc_id in claim["cited_doc_ids"]
        annotations = claim["evidence"].get(str(doc_id), [])
        reference_labels = {annotation["label"] for annotation in annotations}
        if reference_labels:
            assert len(reference_labels) == 1
            source_label = next(iter(reference_labels))
        else:
            assert str(doc_id) not in claim["evidence"]
            source_label = "NOINFO"
        assert base["gold"]["answer"]["label"] == source_label
        assert base["id"] == f"scifact3-dev:{claim_id}:{doc_id}"
        assert base["state"] == {
            "claim": claim["claim"], "paper_title": doc["title"],
            "paper_abstract": "\n".join(doc["abstract"]),
        }
        assert base["group"] == f"scifact-claim:{claim_id}"
        assert base["document_group"] == f"scifact-document:{doc_id}"
        for case in (base, repeat, reversed_case, titleless):
            assert case["request_sha256"] == digest(request(case))
            assert case["gold"] == base["gold"]
            assert case["source_id"] == base["source_id"]
            assert case["prior_three_choice_selected"] == base["prior_three_choice_selected"]
            assert case["prior_two_choice_selected"] == base["prior_two_choice_selected"]
        assert request(repeat) == request(base)
        assert repeat["request_sha256"] == base["request_sha256"]
        assert reversed_case["state"] == base["state"]
        assert reversed_case["questions"]["answer"]["instructions"] == base["questions"]["answer"]["instructions"]
        assert list(reversed_case["questions"]["answer"]["criteria"].items()) == list(reversed(list(
            base["questions"]["answer"]["criteria"].items())))
        assert titleless["state"] == {"claim": claim["claim"], "paper_abstract": "\n".join(doc["abstract"])}
        assert titleless["questions"] == base["questions"]
        assert titleless["request_sha256"] != base["request_sha256"]
        claim_ids.add(claim_id)
        doc_ids.add(doc_id)
        label_counts[source_label] += 1
    assert len(claim_ids) == 300 and len(doc_ids) == 283
    assert label_counts == {"SUPPORT": 138, "CONTRADICT": 71, "NOINFO": 130}
    prior_selected = {case["id"] for case in suites["base"]
                      if case["prior_three_choice_selected"]}
    complement = {case["id"] for case in suites["base"]
                  if not case["prior_three_choice_selected"]}
    assert len(prior_selected) == 180 and len(complement) == 159
    assert set(manifest["prior_three_choice_selected_ids"]) == prior_selected
    assert set(manifest["complement_ids"]) == complement
    prior_frozen = json.loads((PRIOR / "frozen.json").read_text())
    assert sha(PRIOR / "frozen.json") == manifest["prior_three_choice_frozen_sha256"]
    for condition, cases in suites.items():
        old = next(suite["cases"] for suite in prior_frozen["suites"]
                   if suite["condition"] == condition)
        new_by_id = {case["id"]: case for case in cases}
        for old_case in old:
            assert new_by_id[old_case["id"]]["request_sha256"] == old_case["request_sha256"]
            assert request(new_by_id[old_case["id"]]) == request(old_case)
    report = {
        "frozen_sha256": manifest["prepared_sha256"],
        "raw_source_reverified": True,
        "request_hashes_verified": 1356,
        "selected_pairs": 339,
        "label_counts": dict(label_counts),
        "unique_claims": len(claim_ids), "unique_documents": len(doc_ids),
        "prior_three_choice_selected_pairs": len(prior_selected),
        "three_choice_complement_pairs": len(complement),
        "prior_three_choice_overlap_requests_verified": 4 * len(prior_selected),
        "all_pairs_explicitly_cited": True,
        "all_noinfo_pairs_have_no_evidence_entry": True,
        "all_positive_pairs_have_consistent_evidence_labels": True,
        "repeat_byte_identical": True, "reverse_only_criteria_order": True,
        "title_removed_only_state_title": True,
    }
    target = OUT / "validation.json"
    if target.exists():
        raise FileExistsError("Validation record exists: refusing overwrite")
    write(target, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
