"""Freeze a model-blind, three-class SciFact cited-abstract diagnostic.

Run from the repository root. Existing outputs are never overwritten. The
SciFact source data remain in ignored data/external/domain_expansion_v1/.
"""

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from system1bench.common import digest, request, sha, write

from source_profile import load_jsonl, profile

ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"
ARCHIVE = ROOT / "data/external/domain_expansion_v1/scifact-data.tar.gz"
OUT = ROOT / "research/scifact3_v1"
SEED = "system1bench-scifact3-v1-20260930"
LABELS = ("CONTRADICT", "SUPPORT", "NOINFO")
PER_LABEL = 60


def rank(label, claim_id, doc_id):
    return hashlib.sha256(
        f"{SEED}|{label}|{claim_id}|{doc_id}".encode("utf-8")
    ).hexdigest()


def candidates():
    claims = load_jsonl(SCIENCE / "claims_dev.jsonl")
    corpus_rows = load_jsonl(SCIENCE / "corpus.jsonl")
    corpus = {doc["doc_id"]: doc for doc in corpus_rows}
    assert len(corpus) == len(corpus_rows)
    rows = {label: [] for label in LABELS}
    for claim in claims:
        for doc_id in sorted(set(claim["cited_doc_ids"])):
            assert doc_id in corpus
            document = corpus[doc_id]
            evidence = claim["evidence"].get(str(doc_id), [])
            if evidence:
                labels = {annotation["label"] for annotation in evidence}
                assert len(labels) == 1
                label = next(iter(labels))
            else:
                label = "NOINFO"
            assert label in rows
            assert claim["claim"] and document["abstract"]
            rows[label].append((claim, document, label))
    assert {label: len(rows[label]) for label in LABELS} == {
        "CONTRADICT": 71, "SUPPORT": 138, "NOINFO": 130}
    return rows


def select(rows):
    """Scarcity-first deterministic selection with unique claim and document IDs."""
    selected, used_claims, used_docs = [], set(), set()
    for label in LABELS:
        ranked = sorted(rows[label], key=lambda row: rank(
            label, row[0]["id"], row[1]["doc_id"]))
        selected_label = 0
        for claim, document, _ in ranked:
            claim_id, doc_id = claim["id"], document["doc_id"]
            if claim_id in used_claims or doc_id in used_docs:
                continue
            selected.append((claim, document, label))
            used_claims.add(claim_id)
            used_docs.add(doc_id)
            selected_label += 1
            if selected_label == PER_LABEL:
                break
        if selected_label != PER_LABEL:
            raise ValueError(f"Cannot fill {label} with unique claim/doc: {selected_label}")
    assert len(selected) == 3 * PER_LABEL
    return sorted(selected, key=lambda row: (row[0]["id"], row[1]["doc_id"]))


def make_cases(selected):
    cases = []
    for claim, document, label in selected:
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
        cases.append({
            "id": f"scifact3-dev:{claim_id}:{doc_id}",
            "state": state, "questions": {"answer": question},
            "gold": {"answer": {"label": label}},
            "group": f"scifact-claim:{claim_id}",
            "document_group": f"scifact-document:{doc_id}",
            "family": "scifact3", "language": "en",
            "source_id": {"claim_id": claim_id, "doc_id": doc_id},
            "source_split": "dev",
        })
    return cases


def make_suites(cases):
    conditions = ("base", "exact_repeat", "reversed_option_order", "title_removed")
    suites = []
    for condition in conditions:
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
    base, repeat, reverse, titleless = (suite["cases"] for suite in suites)
    for a, b, c, d in zip(base, repeat, reverse, titleless):
        assert a["id"] == b["id"] == c["id"] == d["id"]
        assert a["request_sha256"] == b["request_sha256"]
        assert a["request_sha256"] != c["request_sha256"]
        assert a["request_sha256"] != d["request_sha256"]
        assert a["state"] == b["state"] == c["state"]
        assert {k: v for k, v in a["state"].items() if k != "paper_title"} == d["state"]
        assert a["questions"] == b["questions"] == d["questions"]
        assert a["gold"] == b["gold"] == c["gold"] == d["gold"]
    return suites


def main():
    source_profile = profile()
    if set(source_profile["problems"]) != {"duplicate_cited_ids"}:
        raise ValueError(f"Unexpected source anomalies: {source_profile['problems']}")
    if source_profile["problems"]["duplicate_cited_ids"]["examples"] != [1245]:
        raise ValueError("Source duplicate citation changed")
    rows = candidates()
    selected = select(rows)
    cases = make_cases(selected)
    suites = make_suites(cases)
    label_counts = dict(Counter(c["gold"]["answer"]["label"] for c in cases))
    assert set(label_counts) == set(LABELS)
    assert set(label_counts.values()) == {PER_LABEL}
    claim_ids = {c["source_id"]["claim_id"] for c in cases}
    doc_ids = {c["source_id"]["doc_id"] for c in cases}
    assert len(claim_ids) == len(doc_ids) == len(cases)
    frozen = {
        "protocol": "system1bench-scifact3-v1", "seed": SEED,
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
        "profiler_sha256": sha(OUT / "source_profile.py"),
        "source_profile": source_profile,
        "selection": (
            "SHA-256 seeded rank; scarcity-first CONTRADICT, SUPPORT, NOINFO; "
            "unique claim ID and document ID globally; no model outcomes inspected"
        ),
        "selected_pairs": len(cases), "label_counts": label_counts,
        "distinct_claims": len(claim_ids), "distinct_documents": len(doc_ids),
        "conditions": [suite["condition"] for suite in suites],
        "planned_requests": sum(len(suite["cases"]) for suite in suites),
        "controls": (
            "Repeat request identical; reversal changes only criteria insertion order; "
            "title removal deletes only state.paper_title"
        ),
    }
    paths = [OUT / "frozen.json", OUT / "manifest.json", OUT / "profile.json"]
    if any(path.exists() for path in paths):
        raise FileExistsError("SciFact three-class experiment already frozen; refusing overwrite")
    OUT.mkdir(parents=True, exist_ok=True)
    write(paths[0], frozen)
    manifest["prepared_sha256"] = sha(paths[0])
    write(paths[1], manifest)
    write(paths[2], source_profile)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
