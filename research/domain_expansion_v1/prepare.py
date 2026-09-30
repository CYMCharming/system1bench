"""Freeze model-blind legal/scientific paired decisions before inference.

Run from the repository root. This script refuses to overwrite an existing freeze.
The primary unit is a source document--hypothesis or claim--cited-abstract pair.
"""

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from system1bench.common import digest, request, sha, write

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/external/domain_expansion_v1"
OUT = ROOT / "research/domain_expansion_v1"
SEED = "system1bench-domain-expansion-v1-20260930"
LEGAL_CHARS_MAX = 16000
LEGAL_PER_CLASS = 48
SCIENCE_PER_CLASS = 60


def rank(key):
    return hashlib.sha256(f"{SEED}|{key}".encode()).hexdigest()


def base_case(cid, state, question, gold, *, group, family, source_id, source_split):
    return dict(id=cid, state=state, questions={"answer": question},
                gold={"answer": {"label": gold}}, group=group, family=family,
                language="en", source_id=source_id, source_split=source_split)


def legal_cases():
    path = DATA / "test.json"
    source = json.loads(path.read_text())
    hypotheses = source["labels"]
    eligible = [d for d in source["documents"] if len(d["text"]) <= LEGAL_CHARS_MAX]
    candidates = {label: [] for label in ["Contradiction", "Entailment", "NotMentioned"]}
    for document in eligible:
        for hyp_id, annotation in document["annotation_sets"][0]["annotations"].items():
            label = annotation["choice"]
            assert hyp_id in hypotheses and label in candidates
            candidates[label].append((document, hyp_id))
    selected, per_document = [], Counter()
    for label in candidates:
        pool = sorted(candidates[label], key=lambda x: rank(f"legal|{label}|{x[0]['id']}|{x[1]}"))
        chosen_docs = set()
        for document, hyp_id in pool:
            doc_id = str(document["id"])
            if per_document[doc_id] >= 2 or doc_id in chosen_docs:
                continue
            selected.append((document, hyp_id, label))
            chosen_docs.add(doc_id)
            per_document[doc_id] += 1
            if len(chosen_docs) == LEGAL_PER_CLASS:
                break
        if len(chosen_docs) != LEGAL_PER_CLASS:
            raise ValueError(f"Insufficient legal {label}: {len(chosen_docs)}")
    cases = []
    for document, hyp_id, label in sorted(selected, key=lambda x: (int(x[0]["id"]), x[1])):
        hypothesis = hypotheses[hyp_id]["hypothesis"]
        state = {"contract_text": document["text"], "hypothesis": hypothesis}
        question = {"type": "choice",
                    "instructions": ("Compare the hypothesis with the complete NDA text. "
                                     "Does the NDA entail it, contradict it, or leave it not mentioned? "
                                     "Use only the supplied NDA text; do not infer unstated provisions."),
                    "criteria": {
                        "Entailment": "The NDA affirms the hypothesis.",
                        "Contradiction": "The NDA negates the hypothesis.",
                        "NotMentioned": "The NDA neither affirms nor negates the hypothesis."
                    }}
        cases.append(base_case(f"contractnli-test:{document['id']}:{hyp_id}", state, question, label,
                               group=f"contractnli-document:{document['id']}", family="contractnli",
                               source_id={"document_id": document["id"], "hypothesis_id": hyp_id},
                               source_split="test"))
    metadata = dict(total_documents=len(source["documents"]), eligible_documents=len(eligible),
                    excluded_documents_over_16000_chars=len(source["documents"]) - len(eligible),
                    eligible_pairs=sum(map(len, candidates.values())), selected_pairs=len(cases),
                    label_counts=dict(Counter(c["gold"]["answer"]["label"] for c in cases)),
                    distinct_documents=len(per_document), max_pairs_per_document=max(per_document.values()))
    return cases, metadata


def science_cases():
    science = DATA / "scifact/data"
    claims = [json.loads(line) for line in (science / "claims_dev.jsonl").read_text().splitlines()]
    corpus = {row["doc_id"]: row for row in
              (json.loads(line) for line in (science / "corpus.jsonl").read_text().splitlines())}
    candidates = {label: [] for label in ["CONTRADICT", "SUPPORT"]}
    for claim in claims:
        for doc_id, annotations in claim["evidence"].items():
            labels = {a["label"] for a in annotations}
            if len(labels) != 1:
                raise ValueError(f"Ambiguous SciFact pair {claim['id']}--{doc_id}")
            label = next(iter(labels))
            assert label in candidates and int(doc_id) in corpus
            candidates[label].append((claim, corpus[int(doc_id)]))
    selected, used_claims = [], set()
    for label in candidates:
        pool = sorted(candidates[label], key=lambda x: rank(f"science|{label}|{x[0]['id']}|{x[1]['doc_id']}"))
        count = 0
        for claim, document in pool:
            if claim["id"] in used_claims:
                continue
            selected.append((claim, document, label))
            used_claims.add(claim["id"])
            count += 1
            if count == SCIENCE_PER_CLASS:
                break
        if count != SCIENCE_PER_CLASS:
            raise ValueError(f"Insufficient science {label}: {count}")
    cases = []
    for claim, document, label in sorted(selected, key=lambda x: (x[0]["id"], x[1]["doc_id"])):
        state = {"claim": claim["claim"], "paper_title": document["title"],
                 "paper_abstract": "\n".join(document["abstract"])}
        question = {"type": "choice",
                    "instructions": ("For this cited scientific paper, determine whether its abstract "
                                     "supports or contradicts the claim. Use only the supplied "
                                     "abstract; do not rely on outside knowledge."),
                    "criteria": {"SUPPORT": "The abstract supports the claim.",
                                 "CONTRADICT": "The abstract contradicts the claim."}}
        cases.append(base_case(f"scifact-dev:{claim['id']}:{document['doc_id']}", state, question, label,
                               group=f"scifact-claim:{claim['id']}", family="scifact",
                               source_id={"claim_id": claim["id"], "doc_id": document["doc_id"]},
                               source_split="dev"))
    metadata = dict(total_claims=len(claims), annotated_positive_pairs=sum(map(len, candidates.values())),
                    selected_pairs=len(cases), distinct_claims=len(used_claims),
                    label_counts=dict(Counter(c["gold"]["answer"]["label"] for c in cases)),
                    no_information_pairs_included=0)
    return cases, metadata


def suites_for(source, cases):
    suites = []
    for condition in ["base", "exact_repeat", "reversed_option_order"]:
        copied = copy.deepcopy(cases)
        if condition == "reversed_option_order":
            for case in copied:
                q = case["questions"]["answer"]
                q["criteria"] = dict(reversed(list(q["criteria"].items())))
        for case in copied:
            case["request_sha256"] = digest(request(case))
        suites.append(dict(name=f"{source}_{condition}", cases=copied, track="natural_reference",
                           reference="source_annotation", source=source, language="en",
                           domain="legal" if source == "contractnli" else "scientific_evidence",
                           condition=condition))
    assert all(a["request_sha256"] == b["request_sha256"] for a, b in
               zip(suites[0]["cases"], suites[1]["cases"]))
    assert all(a["request_sha256"] != b["request_sha256"] for a, b in
               zip(suites[0]["cases"], suites[2]["cases"]))
    return suites


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen_path, manifest_path = OUT / "frozen.json", OUT / "manifest.json"
    if frozen_path.exists() or manifest_path.exists():
        raise FileExistsError("Domain experiment already frozen: refusing to overwrite")
    legal, legal_meta = legal_cases()
    science, science_meta = science_cases()
    source_sha256 = {str(p.relative_to(DATA)): sha(p) for p in [
        DATA / "contract-nli.zip", DATA / "test.json", DATA / "TERMS", DATA / "LICENSE",
        DATA / "scifact-data.tar.gz", DATA / "scifact/data/claims_dev.jsonl",
        DATA / "scifact/data/corpus.jsonl"]}
    frozen = dict(protocol="system1bench-domain-expansion-v1", seed=SEED,
                  budget={"max_len": 8192, "head_max_len": 4096},
                  suites=suites_for("contractnli", legal) + suites_for("scifact", science))
    write(frozen_path, frozen)
    manifest = dict(protocol=frozen["protocol"], prepared_sha256=sha(frozen_path),
                    preparer_sha256=sha(Path(__file__)), source_sha256=source_sha256,
                    contractnli=legal_meta, scifact=science_meta,
                    planned_requests=sum(len(s["cases"]) for s in frozen["suites"]),
                    conditions=["base", "exact_repeat", "reversed_option_order"],
                    selection="SHA-256 seeded, source-label-balanced; no model outcomes inspected",
                    controls="Exact-repeat request is byte-identical; reversal changes only criteria insertion order")
    write(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
