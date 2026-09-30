"""Freeze all eligible cited SciFact dev pairs for post-hoc census replication.

No sampling, no model outcomes. Reuses the exact three-class question and
interventions from scifact3_v1 and asserts byte-identical overlap requests.
"""

import copy
import json
from collections import Counter
from pathlib import Path

from system1bench.common import digest, read, request, sha, write

from source_profile import load_jsonl, profile

ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"
ARCHIVE = ROOT / "data/external/domain_expansion_v1/scifact-data.tar.gz"
OUT = ROOT / "research/scifact3_census_v1"
PRIOR = ROOT / "research/scifact3_v1"
TWO_CHOICE = ROOT / "research/domain_expansion_v1"
CONDITIONS = ("base", "exact_repeat", "reversed_option_order", "title_removed")
LABELS = ("SUPPORT", "CONTRADICT", "NOINFO")


def prior_pair_ids():
    old_manifest = read(PRIOR / "manifest.json")
    assert sha(PRIOR / "frozen.json") == old_manifest["prepared_sha256"]
    old_suites = read(PRIOR / "frozen.json")["suites"]
    selected = {(case["source_id"]["claim_id"], case["source_id"]["doc_id"])
                for case in old_suites[0]["cases"]}
    assert len(selected) == 180
    two_manifest = read(TWO_CHOICE / "manifest.json")
    assert sha(TWO_CHOICE / "frozen.json") == two_manifest["prepared_sha256"]
    two_suites = read(TWO_CHOICE / "frozen.json")["suites"]
    two_cases = next(suite["cases"] for suite in two_suites
                     if suite["name"] == "scifact_base")
    two = {(case["source_id"]["claim_id"], case["source_id"]["doc_id"])
           for case in two_cases}
    assert len(two) == 120
    return selected, two, old_suites, old_manifest, two_manifest


def source_pairs():
    claims = load_jsonl(SCIENCE / "claims_dev.jsonl")
    corpus_rows = load_jsonl(SCIENCE / "corpus.jsonl")
    corpus = {doc["doc_id"]: doc for doc in corpus_rows}
    assert len(corpus) == len(corpus_rows) == 5183
    assert len({claim["id"] for claim in claims}) == len(claims) == 300
    pairs = []
    for claim in claims:
        for doc_id in sorted(set(claim["cited_doc_ids"])):
            assert doc_id in corpus
            annotations = claim["evidence"].get(str(doc_id), [])
            if annotations:
                labels = {item["label"] for item in annotations}
                assert len(labels) == 1 and next(iter(labels)) in LABELS
                label = next(iter(labels))
            else:
                assert str(doc_id) not in claim["evidence"]
                label = "NOINFO"
            pairs.append((claim, corpus[doc_id], label))
    pairs.sort(key=lambda item: (item[0]["id"], item[1]["doc_id"]))
    assert len(pairs) == 339
    assert Counter(label for _, _, label in pairs) == {
        "SUPPORT": 138, "CONTRADICT": 71, "NOINFO": 130}
    assert len({(claim["id"], doc["doc_id"]) for claim, doc, _ in pairs}) == len(pairs)
    return pairs


def make_cases(pairs, previous, prior_two):
    cases = []
    for claim, document, label in pairs:
        claim_id, doc_id = claim["id"], document["doc_id"]
        state = {"claim": claim["claim"], "paper_title": document["title"],
                 "paper_abstract": "\n".join(document["abstract"])}
        question = {
            "type": "choice",
            "instructions": (
                "Assess the relation between the claim and the cited paper's abstract. "
                "Use the abstract as evidence; the title identifies the paper but is not "
                "a substitute for abstract evidence. Choose NOINFO if the abstract "
                "neither supports nor contradicts the claim. Do not use outside knowledge."
            ),
            "criteria": {
                "SUPPORT": "The abstract provides evidence supporting the claim.",
                "CONTRADICT": "The abstract provides evidence contradicting the claim.",
                "NOINFO": "The abstract provides no evidence sufficient to support or contradict the claim."
            },
        }
        pair = (claim_id, doc_id)
        cases.append({
            "id": f"scifact3-dev:{claim_id}:{doc_id}",
            "state": state, "questions": {"answer": question},
            "gold": {"answer": {"label": label}},
            "group": f"scifact-claim:{claim_id}",
            "document_group": f"scifact-document:{doc_id}",
            "family": "scifact3", "language": "en",
            "source_id": {"claim_id": claim_id, "doc_id": doc_id},
            "source_split": "dev",
            "prior_three_choice_selected": pair in previous,
            "prior_two_choice_selected": pair in prior_two,
        })
    return cases


def make_suites(cases):
    suites = []
    for condition in CONDITIONS:
        copied = copy.deepcopy(cases)
        for case in copied:
            if condition == "reversed_option_order":
                criteria = case["questions"]["answer"]["criteria"]
                case["questions"]["answer"]["criteria"] = dict(reversed(list(criteria.items())))
            elif condition == "title_removed":
                del case["state"]["paper_title"]
            case["request_sha256"] = digest(request(case))
        suites.append({"name": f"scifact3_{condition}", "cases": copied,
                       "track": "natural_reference", "reference": "source_annotation",
                       "source": "scifact", "language": "en", "domain": "scientific_evidence",
                       "condition": condition})
    return suites


def main():
    source_profile = profile()
    if set(source_profile["problems"]) != {"duplicate_cited_ids"}:
        raise ValueError(f"Unexpected source anomaly: {source_profile['problems']}")
    previous, prior_two, old_suites, old_manifest, two_manifest = prior_pair_ids()
    pairs = source_pairs()
    cases = make_cases(pairs, previous, prior_two)
    suites = make_suites(cases)
    assert len(suites) == 4 and all(len(suite["cases"]) == 339 for suite in suites)
    # Test the entire existing 180-pair overlap, not just selected examples.
    for condition in CONDITIONS:
        new_cases = {case["id"]: case for case in next(
            suite["cases"] for suite in suites if suite["condition"] == condition)}
        old_cases = next(suite["cases"] for suite in old_suites
                         if suite["condition"] == condition)
        assert len(old_cases) == 180
        for old_case in old_cases:
            new_case = new_cases[old_case["id"]]
            assert request(new_case) == request(old_case)
            assert new_case["request_sha256"] == old_case["request_sha256"]
            assert new_case["gold"] == old_case["gold"]
    selected_cases = [case for case in cases if case["prior_three_choice_selected"]]
    complement = [case for case in cases if not case["prior_three_choice_selected"]]
    assert len(selected_cases) == 180 and len(complement) == 159
    complement_labels = Counter(case["gold"]["answer"]["label"] for case in complement)
    assert complement_labels == {"SUPPORT": 78, "CONTRADICT": 11, "NOINFO": 70}
    complement_prior_two = [case for case in complement if case["prior_two_choice_selected"]]
    assert len(complement_prior_two) == 37
    frozen = {
        "protocol": "system1bench-scifact3-census-v1",
        "design": "post-hoc full eligible cited-pair census replication",
        "budget": {"max_len": 8192, "head_max_len": 4096},
        "suites": suites,
    }
    manifest = {
        "protocol": frozen["protocol"],
        "source_sha256": {
            "scifact-data.tar.gz": sha(ARCHIVE),
            "claims_dev.jsonl": sha(SCIENCE / "claims_dev.jsonl"),
            "corpus.jsonl": sha(SCIENCE / "corpus.jsonl"),
        },
        "preparer_sha256": sha(Path(__file__)),
        "source_profiler_sha256": sha(OUT / "source_profile.py"),
        "prior_three_choice_frozen_sha256": old_manifest["prepared_sha256"],
        "prior_two_choice_frozen_sha256": two_manifest["prepared_sha256"],
        "source_profile": source_profile,
        "selection": "all unique claim--document pairs in official dev cited_doc_ids; sorted by claim ID then document ID; no model-outcome selection",
        "selected_pairs": len(cases),
        "label_counts": dict(Counter(case["gold"]["answer"]["label"] for case in cases)),
        "distinct_claims": len({case["source_id"]["claim_id"] for case in cases}),
        "distinct_documents": len({case["source_id"]["doc_id"] for case in cases}),
        "prior_three_choice_selected_ids": [case["id"] for case in selected_cases],
        "complement_ids": [case["id"] for case in complement],
        "complement_label_counts": dict(complement_labels),
        "complement_prior_two_choice_pairs": len(complement_prior_two),
        "complement_prior_two_choice_label_counts": dict(Counter(
            case["gold"]["answer"]["label"] for case in complement_prior_two)),
        "planned_requests": sum(len(suite["cases"]) for suite in suites),
        "conditions": list(CONDITIONS),
        "controls": "exact repeat identical; reversal only criteria insertion order; title removal only deletes state.paper_title",
        "status_boundary": "complement has no prior three-choice outputs, but 37 positive pairs had prior two-choice outputs; not an independent holdout",
    }
    paths = [OUT / "frozen.json", OUT / "manifest.json", OUT / "profile.json"]
    if any(path.exists() for path in paths):
        raise FileExistsError("SciFact3 census already frozen: refusing overwrite")
    OUT.mkdir(parents=True, exist_ok=True)
    write(paths[0], frozen)
    manifest["prepared_sha256"] = sha(paths[0])
    write(paths[1], manifest)
    write(paths[2], source_profile)
    print(json.dumps({key: value for key, value in manifest.items()
                      if key not in ("prior_three_choice_selected_ids", "complement_ids")}, indent=2))


if __name__ == "__main__":
    main()
