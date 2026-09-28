"""Metrics recomputable from public predictions, without downloading raw text."""
import argparse
from collections import Counter, defaultdict

import numpy as np

from .common import ROOT, read, sha, write
from .run import read_run


def cluster_ci(rows, replicates=2000):
    groups = defaultdict(lambda: [0, 0])
    for r in rows:
        groups[r["group"]][0] += int(r["prediction"] == r["gold"] and r["error"] is None)
        groups[r["group"]][1] += 1
    a = np.asarray(list(groups.values()), dtype=float)
    rng = np.random.default_rng(20260927)
    values = []
    for _ in range(0, replicates, 100):
        sample = rng.integers(0, len(a), size=(min(100, replicates - len(values)), len(a)))
        sums = a[sample].sum(axis=1)
        values.extend((sums[:, 0] / sums[:, 1]).tolist())
    return [float(x) for x in np.quantile(values, [0.025, 0.975])]


def auc(targets, scores):
    # Mann–Whitney rank statistic with averaged ranks for tied probabilities.
    pairs = sorted(zip(scores, targets))
    pos = sum(targets)
    neg = len(targets) - pos
    if not pos or not neg:
        return None
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        rank_sum += sum(v for _, v in pairs[i:j]) * ((i + 1 + j) / 2)
        i = j
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def metrics(rows, intervals=False):
    n = len(rows)
    if not n:
        return {"n": 0}
    correct = [r["prediction"] == r["gold"] and r["error"] is None for r in rows]
    valid = [r for r in rows if r["error"] is None]
    result = dict(n=n, correct=sum(correct), accuracy=sum(correct) / n, failures=n - len(valid),
                  valid_probability_n=len(valid), uniform_baseline=float(np.mean([1 / len(r["labels"]) for r in rows])),
                  clusters=len({r["group"] for r in rows}))
    if intervals:
        result["accuracy_ci95_cluster"] = cluster_ci(rows)
    label_sets = {tuple(r["labels"]) for r in rows}
    if len(label_sets) == 1:
        ls = rows[0]["labels"]
        counts = Counter(r["gold"] for r in rows)
        fs = []
        for label in ls:
            tp = sum(r["gold"] == label and r["prediction"] == label and r["error"] is None for r in rows)
            fp = sum(r["gold"] != label and r["prediction"] == label and r["error"] is None for r in rows)
            fn = counts[label] - tp
            fs.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        result.update(macro_f1=float(np.mean(fs)), label_count=len(ls), observed_labels=len(counts),
                      majority_baseline=max(counts.values()) / n)
    if valid:
        briers, confidence, matched = [], [], []
        for r in valid:
            ps = r["probabilities"]
            gold = r["labels"].index(r["gold"])
            briers.append(sum((p - (i == gold)) ** 2 for i, p in enumerate(ps)))
            confidence.append(max(ps))
            matched.append(r["prediction"] == r["gold"])
        conf, acc = np.asarray(confidence), np.asarray(matched)
        bins = np.minimum((conf * 10).astype(int), 9)
        ece = sum(np.mean(bins == i) * abs(float(acc[bins == i].mean()) - float(conf[bins == i].mean())) for i in range(10) if (bins == i).any())
        result.update(brier=float(np.mean(briers)), ece10=float(ece), high_confidence_n=int((conf >= 0.9).sum()),
                      high_confidence_errors=int(((conf >= 0.9) & ~acc).sum()))
        scores = [r for r in valid if r["type"] == "score"]
        if scores:
            errors = [abs(float(r["prediction"]) - float(r["gold"])) for r in scores]
            result.update(ordinal_n=len(scores), ordinal_argmax_mae=float(np.mean(errors)),
                          ordinal_within_one=float(np.mean(np.asarray(errors) <= 1)),
                          ordinal_expected_mae=float(np.mean([abs(float(r["answer"]["score"]) - float(r["gold"])) for r in scores])))
    return result


def oos_metrics(rows):
    tp = sum(r["prediction"] == "oos" and r["gold"] == "oos" and r["error"] is None for r in rows)
    fp = sum(r["prediction"] == "oos" and r["gold"] != "oos" and r["error"] is None for r in rows)
    fn = sum(r["gold"] == "oos" for r in rows) - tp
    valid = [r for r in rows if r["error"] is None]
    return dict(precision=tp / (tp + fp) if tp + fp else 0, recall=tp / (tp + fn),
                f1=2 * tp / (2 * tp + fp + fn),
                auroc=auc([r["gold"] == "oos" for r in valid], [r["probabilities"][r["labels"].index("oos")] for r in valid]),
                in_scope=metrics([r for r in rows if r["gold"] != "oos"]), oos=metrics([r for r in rows if r["gold"] == "oos"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="results")
    args = p.parse_args()
    root = ROOT / args.results
    summary = {"protocol_sha256": sha(ROOT / "protocol_manifest.json"), "models": {}}
    manifest = read(ROOT / "protocol_manifest.json")
    for model in sorted(f.name for f in root.iterdir() if f.is_dir() and (f / "metadata.json").exists()):
        meta = read(root / model / "metadata.json")
        if meta["status"] != "DONE" or meta["signature"]["protocol_sha256"] != summary["protocol_sha256"]:
            raise ValueError("Incomplete or mismatched run")
        all_rows, output = {}, {}
        for spec in manifest["suites"]:
            name = spec["name"]
            path = root / model / (name + ".json.gz")
            if sha(path) != meta["suites"][name]["sha256"]:
                raise ValueError("Result hash mismatch")
            run = read_run(path)
            if run["signature"] != meta["signature"]:
                raise ValueError("Result signature mismatch")
            rows = run["rows"]
            if len(rows) != spec["decisions"] or len({(r["id"], r["qid"]) for r in rows}) != len(rows):
                raise ValueError("Result count or duplicate ID mismatch")
            all_rows[name] = rows
            s = {"track": spec["track"], "reference": spec["reference"], "all": metrics(rows, True),
                 "complete_input": metrics([r for r in rows if r["audit"]["complete"]], True),
                 "truncation": {k: sum(bool(r["audit"][k]) for r in rows) for k in
                                ["option_texts_shortened", "instruction_shortened", "state_shortened", "special_mask_sanitized"]},
                 "option_collision_decisions": sum(r["audit"]["unique_encoded_options"] < r["audit"]["options"] for r in rows),
                 "inference_seconds": meta["suites"][name]["inference_seconds"], "slices": {}}
            for key in ["type", "language", "family", "length_target", "position", "qid"]:
                s["slices"][key] = {str(v): metrics([r for r in rows if r[key] == v]) for v in sorted({r[key] for r in rows if r[key] is not None}, key=str)}
            if name == "clinc150_oos":
                s["oos_metrics"] = oos_metrics(rows)
            if name == "turtlebench":
                s["binary_merged_accuracy"] = sum((r["prediction"] == "Correct") == (r["gold"] == "Correct") and r["error"] is None for r in rows) / len(rows)
            if name == "aegis2_prompt":
                unique = {r["group"]: r for r in reversed(rows)}  # deterministic first official row
                s["first_occurrence_deduplicated"] = metrics(list(unique.values()), True)
            output[name] = s
        robust = {}
        for spec in manifest["suites"]:
            if spec.get("condition") != "reversed":
                continue
            base = spec["base_suite"]
            maps = [{(r["id"], r["qid"]): r for r in all_rows[n]} for n in [base, base + "_repeat", spec["name"]]]
            keys = list(maps[1])
            for key in keys:
                original, repeat, reversed_row = [m[key] for m in maps]
                if original["request_sha256"] != repeat["request_sha256"]:
                    raise ValueError("Same-order control changed the request")
                if repeat["request_sha256"] == reversed_row["request_sha256"]:
                    raise ValueError("Reversal control did not change the request")
                if reversed_row["labels"] != repeat["labels"][::-1] or repeat["gold"] != reversed_row["gold"]:
                    raise ValueError("Reversal control changed semantics or failed to reverse labels")
            robust[base] = dict(n=len(keys),
                                base_vs_repeat_agreement=sum(maps[0][k]["prediction"] == maps[1][k]["prediction"] and maps[0][k]["error"] is None and maps[1][k]["error"] is None for k in keys) / len(keys),
                                repeat_vs_reversed_agreement=sum(maps[1][k]["prediction"] == maps[2][k]["prediction"] and maps[1][k]["error"] is None and maps[2][k]["error"] is None for k in keys) / len(keys),
                                repeat_accuracy=output[base + "_repeat"]["all"]["accuracy"], reversed_accuracy=output[spec["name"]]["all"]["accuracy"])
        bilingual = {}
        for prefix in ["xnli", "massive"]:
            en = {r["id"].split(":")[-1]: r for r in all_rows[prefix + "_en"]}
            zh = {r["id"].split(":")[-1]: r for r in all_rows[prefix + "_zh"]}
            assert en.keys() == zh.keys() and all(en[k]["gold"] == zh[k]["gold"] for k in en)
            bilingual[prefix] = dict(n=len(en), prediction_agreement=sum(en[k]["prediction"] == zh[k]["prediction"] and en[k]["error"] is None and zh[k]["error"] is None for k in en) / len(en),
                                    both_correct=sum(en[k]["prediction"] == en[k]["gold"] and zh[k]["prediction"] == zh[k]["gold"] and en[k]["error"] is None and zh[k]["error"] is None for k in en) / len(en))
        summary["models"][model] = dict(suites=output, robustness=robust, bilingual=bilingual,
                                        metadata_sha256=sha(root / model / "metadata.json"))
    # Compare only common complete cases if either tokenizer truncates a question.
    models = list(summary["models"])
    shared = {}
    if len(models) >= 2:
        for spec in manifest["suites"]:
            name = spec["name"]
            maps = [{(r["id"], r["qid"]): r for r in read_run(root / m / (name + ".json.gz"))["rows"]} for m in models]
            if any(m.keys() != maps[0].keys() for m in maps):
                raise ValueError("Cross-model result IDs mismatch")
            for k in maps[0]:
                if any((m[k]["request_sha256"], m[k]["gold"]) != (maps[0][k]["request_sha256"], maps[0][k]["gold"]) for m in maps):
                    raise ValueError("Cross-model input/reference mismatch")
            keys = [k for k in maps[0] if all(m[k]["audit"]["complete"] for m in maps)]
            shared[name] = {m: metrics([maps[i][k] for k in keys]) for i, m in enumerate(models)}
    summary["shared_complete_input"] = shared
    write(root / "summary.json", summary)
    print("Verified and summarized", len(models), "models", flush=True)


if __name__ == "__main__":
    main()
