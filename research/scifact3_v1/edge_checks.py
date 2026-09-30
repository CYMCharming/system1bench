"""Read-only edge-case checks against raw SciFact dev data."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCIENCE = ROOT / "data/external/domain_expansion_v1/scifact/data"
claims = [json.loads(line) for line in (SCIENCE / "claims_dev.jsonl").read_text().splitlines()]
corpus = {row["doc_id"]: row for row in (
    json.loads(line) for line in (SCIENCE / "corpus.jsonl").read_text().splitlines())}
issues = Counter()
for claim in claims:
    if not claim["claim"]:
        issues["empty_claim"] += 1
    cited = set(claim["cited_doc_ids"])
    for doc_id in cited:
        if doc_id not in corpus:
            issues["missing_corpus"] += 1
        elif not corpus[doc_id]["title"]:
            issues["empty_title"] += 1
        elif not corpus[doc_id]["abstract"]:
            issues["empty_abstract"] += 1
    for doc_key, rationales in claim["evidence"].items():
        if not rationales:
            issues["empty_evidence_list"] += 1
        if int(doc_key) not in cited:
            issues["evidence_not_cited"] += 1
print(json.dumps(dict(issues), indent=2))
