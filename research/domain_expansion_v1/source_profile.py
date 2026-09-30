"""Read-only profile of candidate independent-domain benchmark sources."""
import collections
import json
import statistics
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "data/external").exists())
SOURCE = ROOT / "data/external/domain_expansion_v1"


def describe(values):
    values = sorted(values)
    return {"n": len(values), "min": values[0], "p25": values[len(values) // 4],
            "median": statistics.median(values), "p75": values[3 * len(values) // 4],
            "p90": values[9 * len(values) // 10], "max": values[-1]}


for split in ["dev", "test"]:
    source = json.loads((SOURCE / f"{split}.json").read_text())
    print("CONTRACT", split, "keys", list(source), "documents", len(source["documents"]))
    print("hypotheses", source.get("labels", {}).keys())
    sizes = [len(d["text"]) for d in source["documents"]]
    print("document_chars", describe(sizes))
    print("shorter_than_16000", sum(v <= 16000 for v in sizes),
          "shorter_than_24000", sum(v <= 24000 for v in sizes))
    labels = collections.Counter()
    per_document = []
    annotation_sets = collections.Counter()
    for d in source["documents"]:
        annotation_sets[len(d["annotation_sets"])] += 1
        annotations = d["annotation_sets"][0]["annotations"]
        per_document.append(len(annotations))
        labels.update(a["choice"] for a in annotations.values())
    print("annotation_sets", annotation_sets, "annotations_per_doc", describe(per_document),
          "labels", labels)
    print("first_doc_keys", list(source["documents"][0]))
    print("first_hypothesis", list(source.get("labels", {}).items())[:1])

scifact_dir = SOURCE / "scifact/data"
claims = [json.loads(s) for s in (scifact_dir / "claims_dev.jsonl").read_text().splitlines()]
corpus = {r["doc_id"]: r for r in
          (json.loads(s) for s in (scifact_dir / "corpus.jsonl").read_text().splitlines())}
print("SCIFACT claims", len(claims), "corpus", len(corpus))
print("claim_keys", list(claims[0]))
label_counts = collections.Counter()
multi_label = 0
annotated_pairs = []
for claim in claims:
    for doc_id, sets in claim["evidence"].items():
        labels = {s["label"] for s in sets}
        if len(labels) > 1:
            multi_label += 1
        for label in labels:
            label_counts[label] += 1
        doc = corpus.get(int(doc_id))
        if doc:
            annotated_pairs.append((claim["id"], int(doc_id), len(" ".join(doc["abstract"])), labels))
print("positive_pair_labels", label_counts, "ambiguous_pairs", multi_label,
      "pair_count", len(annotated_pairs))
print("abstract_chars", describe([p[2] for p in annotated_pairs]))
print("distinct_claims_positive", len({p[0] for p in annotated_pairs}),
      "distinct_docs_positive", len({p[1] for p in annotated_pairs}))
for label in ["SUPPORT", "CONTRADICT"]:
    print("positive", label, "distinct_claims",
          len({p[0] for p in annotated_pairs if label in p[3]}),
          "distinct_docs", len({p[1] for p in annotated_pairs if label in p[3]}))
for split in ["test"]:
    source = json.loads((SOURCE / f"{split}.json").read_text())
    for label in ["Entailment", "Contradiction", "NotMentioned"]:
        docs = {d["id"] for d in source["documents"] if len(d["text"]) <= 16000
                and any(a["choice"] == label for a in d["annotation_sets"][0]["annotations"].values())}
        print("contract <=16k", label, "distinct_docs", len(docs))
