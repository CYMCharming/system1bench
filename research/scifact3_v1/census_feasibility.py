"""Read-only planning statistics for a cited-pair SciFact3 census replication."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"
FROZEN = ROOT / "research/scifact3_v1/frozen.json"
OLD_FROZEN = ROOT / "research/domain_expansion_v1/frozen.json"

claims = [json.loads(line) for line in (SCIENCE / "claims_dev.jsonl").read_text().splitlines()]
selected_cases = json.loads(FROZEN.read_text())["suites"][0]["cases"]
old_suites = json.loads(OLD_FROZEN.read_text())["suites"]
old_cases = next(suite["cases"] for suite in old_suites if suite["name"] == "scifact_base")
old_ids = {(c["source_id"]["claim_id"], c["source_id"]["doc_id"])
           for c in old_cases}
selected_ids = {(c["source_id"]["claim_id"], c["source_id"]["doc_id"])
                for c in selected_cases}
rows = []
for claim in claims:
    for doc_id in sorted(set(claim["cited_doc_ids"])):
        annotations = claim["evidence"].get(str(doc_id), [])
        label = annotations[0]["label"] if annotations else "NOINFO"
        rows.append((claim["id"], doc_id, label))
all_ids = {(claim_id, doc_id) for claim_id, doc_id, _ in rows}
assert len(all_ids) == len(rows) == 339
complement = [r for r in rows if r[:2] not in selected_ids]
assert len(selected_ids) == 180 and len(complement) == 159


def profile(items):
    claims_in = Counter(c for c, _, _ in items)
    docs_in = Counter(d for _, d, _ in items)
    return {"pairs": len(items), "label_pairs": dict(Counter(label for _, _, label in items)),
            "distinct_claims": len(claims_in), "distinct_documents": len(docs_in),
            "max_pairs_per_claim": max(claims_in.values()),
            "max_pairs_per_document": max(docs_in.values()),
            "claims_with_multiple_pairs": sum(n > 1 for n in claims_in.values()),
            "documents_with_multiple_pairs": sum(n > 1 for n in docs_in.values())}


selected = [r for r in rows if r[:2] in selected_ids]
selected_claims = {c for c, _, _ in selected}
selected_docs = {d for _, d, _ in selected}
complement_claims = {c for c, _, _ in complement}
complement_docs = {d for _, d, _ in complement}
print(json.dumps({
    "all": profile(rows), "previous_selected": profile(selected),
    "previously_unevaluated_complement": profile(complement),
    "complement_claims_seen_in_previous_selected": len(complement_claims & selected_claims),
    "complement_documents_seen_in_previous_selected": len(complement_docs & selected_docs),
    "complement_pairs_seen_in_previous_selected": len({r[:2] for r in complement} & selected_ids),
    "complement_pairs_in_prior_two_choice_v1": len({r[:2] for r in complement} & old_ids),
    "complement_prior_two_choice_by_label": dict(Counter(
        label for c, d, label in complement if (c, d) in old_ids)),
}, indent=2))
