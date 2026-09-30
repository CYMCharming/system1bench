"""Model-blind ContractNLI shortcut and 16k-selection audit.

Official train annotations supply the primary hypothesis-ID prior. Frozen test
annotations are used only for evaluation. Selected-test leave-one-item/document
analyses are explicitly secondary diagnostics, not fair model baselines.
The experiment freeze and all original source files are read-only.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import random
import statistics
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "data/external/domain_expansion_v1"
ARCHIVE = DATA / "contract-nli.zip"
LABELS = ("Entailment", "Contradiction", "NotMentioned")
SEED = 20260930


def sha_bytes(data):
    return sha256(data).hexdigest()


def source_rows(source):
    rows = []
    for document in source["documents"]:
        annotation_sets = document["annotation_sets"]
        assert len(annotation_sets) == 1
        annotations = annotation_sets[0]["annotations"]
        assert set(annotations) == set(source["labels"])
        for hyp_id, annotation in annotations.items():
            gold = annotation["choice"]
            assert gold in LABELS
            rows.append({"document_id": str(document["id"]), "hypothesis_id": hyp_id,
                         "gold": gold, "document_type": document["document_type"],
                         "chars": len(document["text"])})
    assert len(rows) == len(source["documents"]) * len(source["labels"])
    return rows


def modal(counter):
    highest = max(counter.values())
    winners = [label for label in LABELS if counter[label] == highest]
    return winners  # fixed order only for display, never to resolve an evaluated tie


def eval_prediction(rows, prediction):
    correct = sum(prediction[row["hypothesis_id"]] == row["gold"] for row in rows)
    matrix = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    for row in rows:
        matrix[row["gold"]][prediction[row["hypothesis_id"]]] += 1
    return {"correct": correct, "n": len(rows), "accuracy": correct / len(rows),
            "confusion_gold_by_prediction": matrix}


def cluster_ci(rows, predictions, *, draws=10000):
    """Descriptive document-cluster interval; predictions are fixed from train."""
    by_document = defaultdict(lambda: [0, 0])
    for row in rows:
        unit = by_document[row["document_id"]]
        unit[0] += int(predictions[row["hypothesis_id"]] == row["gold"])
        unit[1] += 1
    units = list(by_document.values())
    rng = random.Random(SEED)
    values = []
    for _ in range(draws):
        picked = rng.choices(units, k=len(units))
        values.append(sum(x[0] for x in picked) / sum(x[1] for x in picked))
    values.sort()
    return [values[int(.025 * draws)], values[int(.975 * draws)]]


def heldout_selected_prior(selected, *, unit):
    """Leave out an item or its whole document before counting its hypothesis."""
    assert unit in {"item", "document"}
    scored = 0.0
    ties = 0
    unique = 0
    unique_correct = 0
    empty = 0
    winners_by_case = {}
    for case in selected:
        hold_key = (case["document_id"], case["hypothesis_id"])
        available = [other for other in selected
                     if other["hypothesis_id"] == case["hypothesis_id"]
                     and ((other["document_id"], other["hypothesis_id"]) != hold_key
                          if unit == "item" else other["document_id"] != case["document_id"])]
        counts = Counter(other["gold"] for other in available)
        if not counts:
            empty += 1
            winners = []
        else:
            winners = modal(counts)
            scored += (case["gold"] in winners) / len(winners)
            ties += len(winners) > 1
            unique += len(winners) == 1
            unique_correct += len(winners) == 1 and winners[0] == case["gold"]
        winners_by_case[hold_key] = winners
    return {"expected_correct_uniform_tie": scored,
            "n": len(selected), "expected_accuracy_uniform_tie": scored / len(selected),
            "tied_cases": ties, "unique_majority_cases": unique,
            "unique_majority_correct": unique_correct, "unseen_hypothesis_cases": empty}, winners_by_case


def main():
    frozen_path = HERE / "frozen.json"
    manifest_path = HERE / "manifest.json"
    frozen_bytes = frozen_path.read_bytes()
    manifest = json.loads(manifest_path.read_text())
    assert sha_bytes(frozen_bytes) == manifest["prepared_sha256"]
    assert sha_bytes(ARCHIVE.read_bytes()) == manifest["source_sha256"]["contract-nli.zip"]
    with zipfile.ZipFile(ARCHIVE) as archive:
        train_bytes = archive.read("contract-nli/train.json")
        test_bytes = archive.read("contract-nli/test.json")
    assert test_bytes == (DATA / "test.json").read_bytes()
    assert sha_bytes(test_bytes) == manifest["source_sha256"]["test.json"]
    train = json.loads(train_bytes)
    test = json.loads(test_bytes)
    assert train["labels"] == test["labels"] and len(test["labels"]) == 17
    assert len(train["documents"]) == 423 and len(test["documents"]) == 123
    train_rows = source_rows(train)
    test_rows = source_rows(test)
    assert len(train_rows) == 7191 and len(test_rows) == 2091
    test_lookup = {(r["document_id"], r["hypothesis_id"]): r for r in test_rows}
    assert len(test_lookup) == len(test_rows)
    frozen = json.loads(frozen_bytes)
    base = next(s["cases"] for s in frozen["suites"] if s["name"] == "contractnli_base")
    assert len(base) == 144
    docs_by_id = {str(d["id"]): d for d in test["documents"]}
    selected = []
    for case in base:
        src = case["source_id"]
        key = str(src["document_id"]), src["hypothesis_id"]
        row = test_lookup[key]
        assert case["gold"]["answer"]["label"] == row["gold"]
        assert case["state"]["contract_text"] == docs_by_id[key[0]]["text"]
        assert case["state"]["hypothesis"] == test["labels"][key[1]]["hypothesis"]
        assert row["chars"] <= 16000
        selected.append(row)
    assert len({(r["document_id"], r["hypothesis_id"]) for r in selected}) == 144
    selected_documents = {r["document_id"] for r in selected}
    assert len(selected_documents) == 91
    assert max(Counter(r["document_id"] for r in selected).values()) == 2
    assert Counter(r["gold"] for r in selected) == Counter({label: 48 for label in LABELS})

    # Exact train/test duplicate checks; near-duplicate text is not excluded.
    overlap = {}
    for field in ("id", "url", "file_name"):
        a = {str(d.get(field)).strip().lower() for d in train["documents"] if d.get(field)}
        b = {str(d.get(field)).strip().lower() for d in test["documents"] if d.get(field)}
        overlap[field] = len(a & b)
    a = {sha_bytes(d["text"].encode()) for d in train["documents"]}
    b = {sha_bytes(d["text"].encode()) for d in test["documents"]}
    overlap["exact_text_sha256"] = len(a & b)

    eligibility = []
    for document_type in sorted({d["document_type"] for d in test["documents"]}):
        docs = [d for d in test["documents"] if d["document_type"] == document_type]
        eligible = [d for d in docs if len(d["text"]) <= 16000]
        chosen = [d for d in docs if str(d["id"]) in selected_documents]
        lengths = sorted(len(d["text"]) for d in docs)
        eligibility.append({"document_type": document_type,
                            "all_documents": len(docs), "eligible_documents": len(eligible),
                            "excluded_documents": len(docs) - len(eligible),
                            "exclusion_rate": (len(docs) - len(eligible)) / len(docs),
                            "selected_documents": len(chosen),
                            "selected_pairs": sum(r["document_type"] == document_type for r in selected),
                            "all_median_chars": statistics.median(lengths),
                            "all_min_chars": lengths[0], "all_max_chars": lengths[-1],
                            "eligible_median_chars": statistics.median(len(d["text"]) for d in eligible)})
    assert sum(x["all_documents"] for x in eligibility) == 123
    assert sum(x["eligible_documents"] for x in eligibility) == 99
    assert sum(x["selected_documents"] for x in eligibility) == 91
    assert sum(x["selected_pairs"] for x in eligibility) == 144

    eligible_rows = [r for r in test_rows if r["chars"] <= 16000]
    excluded_rows = [r for r in test_rows if r["chars"] > 16000]
    label_mix = {name: {label: Counter(r["gold"] for r in rows)[label] for label in LABELS}
                 for name, rows in [("full_test", test_rows), ("eligible_test", eligible_rows),
                                    ("excluded_test", excluded_rows), ("selected", selected)]}
    assert len(eligible_rows) == 1683 and len(excluded_rows) == 408

    train_counts = defaultdict(Counter)
    selected_counts = defaultdict(Counter)
    for row in train_rows:
        train_counts[row["hypothesis_id"]][row["gold"]] += 1
    for row in selected:
        selected_counts[row["hypothesis_id"]][row["gold"]] += 1
    assert all(sum(counts.values()) == 423 for counts in train_counts.values())
    assert set(train_counts) == set(selected_counts) == set(test["labels"])
    assert all(len(modal(counts)) == 1 for counts in train_counts.values())
    prediction = {hypothesis_id: modal(counts)[0]
                  for hypothesis_id, counts in train_counts.items()}
    train_prior = {stage: eval_prediction(rows, prediction) for stage, rows in
                   [("full_test", test_rows), ("eligible_test", eligible_rows),
                    ("excluded_test", excluded_rows), ("selected", selected)]}
    train_prior["selected"]["ci95_document_cluster"] = cluster_ci(selected, prediction)
    assert train_prior["selected"]["correct"] == 82
    assert train_prior["full_test"]["correct"] == 1379
    assert train_prior["eligible_test"]["correct"] == 1102

    global_train_label = modal(Counter(r["gold"] for r in train_rows))[0]
    selected_global = sum(r["gold"] == global_train_label for r in selected)
    assert selected_global == 48
    # Selected-test labels enter these *diagnostics*. They cannot be considered
    # an external training set or a fair model baseline, even with the held-out
    # target item/document removed.
    leave_item, item_winners = heldout_selected_prior(selected, unit="item")
    leave_document, doc_winners = heldout_selected_prior(selected, unit="document")
    assert item_winners == doc_winners  # each document has one annotation per ID
    assert leave_document["expected_correct_uniform_tie"] == 92.5
    in_sample_ceiling = sum(max(counts.values()) for counts in selected_counts.values())
    assert in_sample_ceiling == 100
    hypotheses = []
    for hypothesis_id in sorted(train_counts):
        hypotheses.append({"hypothesis_id": hypothesis_id,
                           "train_label_counts": {label: train_counts[hypothesis_id][label]
                                                  for label in LABELS},
                           "train_majority": prediction[hypothesis_id],
                           "selected_label_counts": {label: selected_counts[hypothesis_id][label]
                                                     for label in LABELS},
                           "selected_pairs": sum(selected_counts[hypothesis_id].values())})

    result = {"analysis": "contractnli-model-blind-shortcut-audit-v1",
              "input_sha256": {"contract_archive": sha_bytes(ARCHIVE.read_bytes()),
                               "official_train_member": sha_bytes(train_bytes),
                               "official_test_member": sha_bytes(test_bytes),
                               "frozen": sha_bytes(frozen_bytes)},
              "grain": "one official document--hypothesis annotation; frozen base has 144 unique pairs on 91 contracts",
              "split_exact_overlap": overlap,
              "length_threshold_chars": 16000,
              "eligibility_by_document_type": eligibility,
              "label_mix": label_mix,
              "train_hypothesis_prior": train_prior,
              "global_train_majority_label": global_train_label,
              "global_train_majority_selected_correct": selected_global,
              "selected_test_in_sample_id_majority_ceiling": in_sample_ceiling,
              "selected_test_leave_one_item": leave_item,
              "selected_test_leave_one_document": leave_document,
              "selected_test_leaveout_predictions_identical": item_winners == doc_winners,
              "hypotheses": hypotheses,
              "interpretation": "The official-train hypothesis prior diagnoses label predictability without reading the contract; it is supervised and not a fair comparison to zero-shot model outputs. Selected-test leave-out uses other test labels and is only a leakage/difficulty diagnostic. The sample is class-balanced by construction and 16k-filtered."}
    (HERE / "shortcut_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_report(result)
    print("Frozen 144 pairs and official train/test verified; train-ID prior",
          train_prior["selected"]["correct"], "/144; leave-document tie-averaged",
          leave_document["expected_correct_uniform_tie"], "/144")


def write_report(result):
    f = result["train_hypothesis_prior"]
    lines = [
        "# ContractNLI hypothesis shortcut and length-selection audit",
        "",
        "This is a **model-blind dataset diagnostic**, not a fair model baseline. It reads official `train.json` and `test.json` directly from the original archive, verifies the extracted test bytes and the frozen-file hash, and does not inspect model predictions or alter the freeze. The primary unit is one document–hypothesis annotation; the 144 frozen base cases are 91 contracts with at most two questions each.",
        "",
        "## 16,000-character selection changes the document mix",
        "",
        "| Official document type | Test docs | Eligible ≤16k | Excluded | Exclusion rate | Selected docs | Selected pairs | Median chars (all) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in result["eligibility_by_document_type"]:
        lines.append(f"| {x['document_type']} | {x['all_documents']} | {x['eligible_documents']} | {x['excluded_documents']} | {100*x['exclusion_rate']:.1f}% | {x['selected_documents']} | {x['selected_pairs']} | {x['all_median_chars']:,.0f} |")
    lines += [
        "",
        "Of 123 official test contracts, 99 satisfy the length rule and 91 appear in the frozen sample. The filter excludes 13/23 `sec-html` documents (56.5%), versus 7/76 `search-pdf` (9.2%) and 4/24 `sec-text` (16.7%). Consequently, `sec-html` falls from 18.7% of all test documents to 10.1% of eligible documents and 8.8% of selected documents. `document_type` is a source/extraction-format field, not a legal subject-matter taxonomy; this is selection skew, not proof of a causal effect of HTML format on task difficulty.",
        "",
        "| Annotation population | Entailment | Contradiction | NotMentioned | Total |",
        "|---|---:|---:|---:|---:|",
    ]
    for stage, title in [("full_test", "All official test pairs"),
                         ("eligible_test", "Eligible test pairs"),
                         ("excluded_test", "Excluded test pairs"),
                         ("selected", "Frozen selected pairs")]:
        counts = result["label_mix"][stage]
        lines.append(f"| {title} | {counts['Entailment']} | {counts['Contradiction']} | {counts['NotMentioned']} | {sum(counts.values())} |")
    lines += [
        "",
        "The selected 48/48/48 class balance is intentional and not the official test prevalence. Consequently, shortcut percentages on all test annotations, length-eligible annotations and the selected 144 answer different questions.",
        "",
        "## Fixed-hypothesis label prior learned only from official train",
        "",
        "There are 17 fixed hypothesis IDs, each annotated on all 423 official training contracts. For each ID, take its unique modal train label; never read test labels to train this primary prior. The train and test splits have zero exact overlap by document ID, normalized URL, normalized file name or raw text SHA-256 (near-duplicates were not assessed). All 17 train-mode ties are absent.",
        "",
        "| Evaluation population | Train-ID prior correct | Rate |",
        "|---|---:|---:|",
    ]
    for stage, title in [("full_test", "All official test pairs"),
                         ("eligible_test", "Eligible test pairs"),
                         ("excluded_test", "Excluded test pairs"),
                         ("selected", "Frozen selected pairs")]:
        x = f[stage]
        lines.append(f"| {title} | {x['correct']}/{x['n']} | {100*x['accuracy']:.1f}% |")
    lo, hi = f["selected"]["ci95_document_cluster"]
    lines += [
        "",
        f"On the frozen 144, the train-only hypothesis-ID prior reaches **82/144 = 56.9%** (descriptive 95% contract-cluster bootstrap interval [{100*lo:.1f}%, {100*hi:.1f}%], 10,000 draws). The global training-set majority label is `{result['global_train_majority_label']}`; predicting it everywhere gives {result['global_train_majority_selected_correct']}/144 = 33.3% on this deliberately balanced sample. This shows that the hypothesis ID carries label information, not that a model uses this shortcut. It is a supervised reference-label prior and must not be ranked as a zero-shot or document-reading model baseline.",
        "",
        "For diagnostic context only, using the selected test labels to fit a deterministic majority label for each hypothesis ID gives an in-sample optimum of 100/144 = 69.4% for such an ID-only mapping. A stochastic same-input model could exceed this realized count by chance, not by contract information. Excluding the target item before counting its ID yields a tie-averaged expectation of 92.5/144 = 64.2%; excluding the entire target contract gives exactly the same predictions because each contract has at most one annotation per hypothesis ID. Both leave-out versions have 13 tied cases, 131 unique-majority cases and 86 correct unique-majority decisions. Uniform averaging over tied labels avoids a favorable arbitrary tie-break. These leave-out calculations still learn from *other selected test labels* and are not independent model baselines.",
        "",
        "### Per-hypothesis counts",
        "",
        "Column triples are `Entailment / Contradiction / NotMentioned`; selected counts sum to 144. The train-majority column defines the prior; selected counts are shown only to reveal potential shift and are never used to define that primary prior.",
        "",
        "| Hypothesis ID | Train E/C/N | Train majority | Selected E/C/N | Selected n |",
        "|---|---:|---|---:|---:|",
    ]
    for x in result["hypotheses"]:
        tc = x["train_label_counts"]
        sc = x["selected_label_counts"]
        lines.append(f"| `{x['hypothesis_id']}` | {tc['Entailment']}/{tc['Contradiction']}/{tc['NotMentioned']} | {x['train_majority']} | {sc['Entailment']}/{sc['Contradiction']}/{sc['NotMentioned']} | {x['selected_pairs']} |")
    lines += [
        "",
        "## Interpretation and next diagnostic",
        "",
        "The strongest established risk is construct ambiguity: a system may score above chance partly by exploiting stable hypothesis-ID priors rather than reading contract text. The 16k cap also disproportionately removes `sec-html` documents. Neither observation invalidates the official labels, and this audit does not prove which cue any evaluated model used. The selected test sample is small and class-stratified; the train-only prior has a descriptive cluster interval, not a population guarantee.",
        "",
        "A separate **hypothesis-only probe is frozen but not run** in `hypothesis_only_probe/frozen.json`. Its state contains only the official hypothesis text; it has no `contract_text` field, source URL, document ID or filename in the request body. The question explicitly asks for the most likely ContractNLI label *across NDA documents* when the actual contract is withheld, while retaining the same three label names/order. Thus `NotMentioned` is not made logically correct by an empty contract: this is prior elicitation, not a same-instruction deletion ablation. The 144 cases become 17 unique payloads. If run later, compare each ID's output distribution with the official-train prior and report identical-input variability. The result cannot be subtracted from full-text accuracy as an isolated document-reliance effect. This post-hoc exploratory audit is not a confirmatory legal-reasoning experiment; no model inference was run here.",
        "",
        "Reproduce with `.venv/bin/python research/domain_expansion_v1/shortcut_audit.py`. Machine-readable counts, confusion matrices, input hashes and exact overlap checks are in `shortcut_audit.json`.",
        "",
    ]
    (HERE / "SHORTCUT_AUDIT.en.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
