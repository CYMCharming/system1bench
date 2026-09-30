"""Read-only profile of SciFact cited claim--abstract pairs.

Only pairs explicitly in cited_doc_ids are eligible for a no-evidence label.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def profile():
    claims = load_jsonl(SCIENCE / "claims_dev.jsonl")
    corpus_rows = load_jsonl(SCIENCE / "corpus.jsonl")
    corpus = {row["doc_id"]: row for row in corpus_rows}
    if len(corpus) != len(corpus_rows):
        raise ValueError("Duplicate corpus document ID")
    if len({row["id"] for row in claims}) != len(claims):
        raise ValueError("Duplicate claim ID")

    pairs, problems = [], defaultdict(list)
    for claim in claims:
        claim_id = claim["id"]
        cited = claim["cited_doc_ids"]
        if len(cited) != len(set(cited)):
            problems["duplicate_cited_ids"].append(claim_id)
        citation_ids = set(cited)
        evidence_ids = {int(key) for key in claim["evidence"]}
        for doc_id in sorted(evidence_ids - citation_ids):
            problems["evidence_not_cited"].append((claim_id, doc_id))
        for doc_id in sorted(citation_ids):
            if doc_id not in corpus:
                problems["cited_not_in_corpus"].append((claim_id, doc_id))
                continue
            if not corpus[doc_id]["abstract"]:
                problems["empty_cited_abstract"].append((claim_id, doc_id))
            annotations = claim["evidence"].get(str(doc_id), [])
            if annotations:
                labels = {ann["label"] for ann in annotations}
                if labels - {"SUPPORT", "CONTRADICT"}:
                    problems["unknown_positive_label"].append((claim_id, doc_id, sorted(labels)))
                if len(labels) != 1:
                    problems["conflicting_rationales"].append((claim_id, doc_id, sorted(labels)))
                    continue
                for annotation in annotations:
                    for sentence_id in annotation["sentences"]:
                        if not 0 <= sentence_id < len(corpus[doc_id]["abstract"]):
                            problems["rationale_index_out_of_range"].append(
                                (claim_id, doc_id, sentence_id))
                label = next(iter(labels))
            else:
                label = "NOINFO"
            pairs.append({"claim_id": claim_id, "doc_id": doc_id, "label": label,
                          "rationales": len(annotations)})
    counts = Counter(pair["label"] for pair in pairs)
    by_claim = defaultdict(set)
    by_doc = defaultdict(set)
    for pair in pairs:
        by_claim[pair["claim_id"]].add(pair["label"])
        by_doc[pair["doc_id"]].add(pair["label"])
    return {
        "claims": len(claims), "corpus_documents": len(corpus),
        "cited_pair_occurrences": sum(len(c["cited_doc_ids"]) for c in claims),
        "valid_cited_pairs": len(pairs), "label_pairs": dict(sorted(counts.items())),
        "claims_without_positive_evidence": sum(not c["evidence"] for c in claims),
        "claims_with_both_positive_and_noinfo": sum(
            "NOINFO" in labels and ("SUPPORT" in labels or "CONTRADICT" in labels)
            for labels in by_claim.values()),
        "claims_with_any_citation": len(by_claim),
        "unique_claims_by_label": {label: len({p["claim_id"] for p in pairs if p["label"] == label})
                                   for label in ("SUPPORT", "CONTRADICT", "NOINFO")},
        "unique_docs_by_label": {label: len({p["doc_id"] for p in pairs if p["label"] == label})
                                 for label in ("SUPPORT", "CONTRADICT", "NOINFO")},
        "claims_with_multiple_label_types": sum(len(labels) > 1 for labels in by_claim.values()),
        "docs_with_multiple_label_types": sum(len(labels) > 1 for labels in by_doc.values()),
        "problems": {name: {"count": len(rows), "examples": rows[:10]}
                     for name, rows in sorted(problems.items())},
    }


if __name__ == "__main__":
    print(json.dumps(profile(), indent=2))
