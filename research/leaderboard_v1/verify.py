"""Independently replay every published leaderboard count from raw decisions."""

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "research/leaderboard_v1"
EXP = ROOT / "research/model_expansion_v1"
OLD = ("english", "multilingual", "llama31_8b_instruct", "qwen3_8b", "jev-1.13.0")
NEW = ("kev_08b", "kev_4b", "kev_9b", "nanojev", "qwen35_9b")
MODELS = OLD + NEW
POLICY = ("refund", "access", "routing")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    content = path.read_bytes()
    if path.suffix in {".md", ".py", ".json", ".jsonl", ".csv", ".svg", ".yml", ".yaml"}:
        content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def near(actual, expected):
    assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12), (actual, expected)


def rows_for(model, history, expansion):
    if model in OLD:
        for receipt in history["models"][model]["source_receipts"]:
            source = ROOT / receipt["path"]
            assert digest(source) == receipt["sha256"]
            suite = source.name.removesuffix(".json.gz")
            records = json.loads(gzip.decompress(source.read_bytes()))["rows"]
            included = 0
            for row in records:
                if suite.startswith("policy_") and row.get("condition", row["id"].rsplit(":", 1)[-1]) not in {
                    "original", "repeat", "reversed", "counterfactual"
                }:
                    continue
                included += 1
                yield suite, row
            assert included == receipt["matched_decisions"]
    else:
        source = EXP / "results" / model / "raw.jsonl"
        metadata = load(source.parent / "metadata.json")
        assert metadata["status"] == "DONE" and metadata["errors"] == 0
        assert digest(source) == metadata["raw_sha256"] == expansion["models"][model]["raw_sha256"]
        for line in source.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            yield row["suite"], row


def key(suite, row):
    if suite.startswith("policy_"):
        condition = {"original": "base", "repeat": "repeat", "reversed": "reverse",
                     "counterfactual": "counterfactual"}[row.get("condition", row["id"].rsplit(":", 1)[-1])]
        case = row["group"]
    else:
        condition = {"base": "base", "exact_repeat": "repeat", "reversed_option_order": "reverse"}[
            suite.split("_", 1)[1]]
        case = row["id"]
    return row["family"], case, row["qid"], condition


def replay(model, history, expansion):
    mapping = {}
    for suite, row in rows_for(model, history, expansion):
        identity = key(suite, row)
        assert identity not in mapping and row["error"] is None
        mapping[identity] = (row["prediction"] == row["gold"], row["gold"],
                             row["request_sha256"], row["group"])
    assert len(mapping) == 4905
    return mapping


def count(mapping, family, qid, condition="base"):
    found = [value[0] for (fam, _, question, cond), value in mapping.items()
             if fam == family and question == qid and cond == condition]
    return sum(found), len(found)


def verify_metrics(mapping, saved):
    metrics = saved["metrics"]

    def check_cell(name, correct, n):
        cell = metrics[name]
        assert (cell["correct"], cell["n"]) == (correct, n), name
        near(cell["score"], correct / n)

    for family in POLICY:
        correct, n = count(mapping, family, "action")
        assert n == 96
        check_cell(family, correct, n)
    for name, family in (("legal", "contractnli"), ("science", "scifact3")):
        correct, n = count(mapping, family, "answer")
        assert n == (144 if name == "legal" else 339)
        check_cell(name, correct, n)
    for name, qid in (("policy_action", "action"), ("action_head", "action"),
                      ("review_head", "review"), ("severity_head", "severity")):
        counts = [count(mapping, family, qid) for family in POLICY]
        check_cell(name, sum(x[0] for x in counts), sum(x[1] for x in counts))
    all_heads = counterfactual = 0
    for family in POLICY:
        cases = {case for fam, case, qid, cond in mapping if fam == family and qid == "action" and cond == "base"}
        assert len(cases) == 96
        for case in cases:
            all_heads += all(mapping[family, case, qid, "base"][0]
                             for qid in ("action", "review", "severity"))
            assert mapping[family, case, "action", "base"][1] != mapping[family, case, "action", "counterfactual"][1]
            counterfactual += (mapping[family, case, "action", "base"][0]
                               and mapping[family, case, "action", "counterfactual"][0])
    check_cell("all_heads", all_heads, 288)
    check_cell("policy_counterfactual", counterfactual, 288)
    stable = []
    for name, family, n in (("legal", "contractnli", 144), ("science", "scifact3", 339)):
        cases = {case for fam, case, qid, cond in mapping if fam == family and qid == "answer" and cond == "base"}
        assert len(cases) == n
        correct = sum(mapping[family, case, "answer", "base"][0]
                      and mapping[family, case, "answer", "reverse"][0] for case in cases)
        component = metrics["natural_reversal"]["components"][name]
        assert (component["correct"], component["n"]) == (correct, n)
        near(component["score"], correct / n)
        stable.append(correct / n)
    near(metrics["natural_reversal"]["score"], sum(stable) / 2)
    primary = sum(metrics[name]["score"] for name in ("policy_action", "legal", "science")) / 3
    alternate = sum(metrics[name]["score"] for name in (*POLICY, "legal", "science")) / 5
    near(metrics["overall_domain_equal"]["score"], primary)
    near(metrics["overall_task_equal"]["score"], alternate)
    lo, hi = metrics["overall_domain_equal"]["ci95"]
    assert 0 <= lo <= primary <= hi <= 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Create the public verification receipt")
    args = parser.parse_args()
    scores = load(HERE / "scores.json")
    history = load(EXP / "historical_context.json")
    expansion = load(EXP / "summary.json")
    assert scores["protocol"] == "system1bench-ten-model-leaderboard-v1"
    assert set(scores["models"]) == set(MODELS) == set(history["models"]) | set(expansion["models"])
    assert scores["matched_decisions_per_model"] == 4905
    assert scores["protocol_sha256"] == digest(HERE / "PROTOCOL.md")
    assert scores["builder_sha256"] == digest(HERE / "build.py")
    for filename, source in (("historical_context.json", EXP / "historical_context.json"),
                             ("model_expansion_summary.json", EXP / "summary.json"),
                             ("model_expansion_verification.json", EXP / "verification.json")):
        assert scores["source_sha256"][filename] == digest(source)
    common = None
    for model in MODELS:
        mapping = replay(model, history, expansion)
        shared = {k: values[1:] for k, values in mapping.items()}
        if common is None:
            common = shared
        else:
            assert shared == common, f"Different cases, golds or request hashes: {model}"
        assert scores["models"][model]["decisions"] == 4905
        assert scores["models"][model]["errors"] == 0
        verify_metrics(mapping, scores["models"][model])
    assert len(scores["rankings"]) == 14
    for metric, ranks in scores["rankings"].items():
        assert set(ranks) == set(MODELS)
        values = {model: scores["models"][model]["metrics"][metric]["score"] for model in MODELS}
        for model in MODELS:
            assert ranks[model] == 1 + sum(value > values[model] + 1e-12 for value in values.values())
    with (HERE / "rankings.csv").open(encoding="utf-8", newline="") as file:
        records = list(csv.DictReader(file))
    assert len(records) == len(MODELS) * len(scores["rankings"])
    assert len({(record["metric"], record["model"]) for record in records}) == len(records)
    for record in records:
        metric, model = record["metric"], record["model"]
        cell = scores["models"][model]["metrics"][metric]
        assert int(record["rank"]) == scores["rankings"][metric][model]
        assert record["label"] == scores["models"][model]["label"]
        assert record["interface"] == scores["models"][model]["interface"]
        assert record["score_pct"] == f"{100 * cell['score']:.6f}"
        assert record["correct"] == str(cell.get("correct", ""))
        assert record["n"] == str(cell.get("n", ""))
        if "ci95" in cell:
            assert record["ci95_low_pct"] == f"{100 * cell['ci95'][0]:.6f}"
            assert record["ci95_high_pct"] == f"{100 * cell['ci95'][1]:.6f}"
        else:
            assert not record["ci95_low_pct"] and not record["ci95_high_pct"]
    manifest = load(HERE / "figure_manifest.json")
    assert manifest["scores_sha256"] == digest(HERE / "scores.json")
    assert manifest["generator_sha256"] == digest(HERE / "figures.py")
    assert len(manifest["output_files_sha256"]) == 4
    image_count = 0
    for panel, versions in manifest["output_files_sha256"].items():
        assert set(versions) == {f"fig_leaderboard_{panel}.{extension}" for extension in ("pdf", "svg", "png")}
        for filename, expected in versions.items():
            assert digest(ROOT / "paper/figures" / filename) == expected
            image_count += 1
    report = (HERE / "REPORT.zh-CN.md").read_text(encoding="utf-8")
    assert all(title in report for title in ("先看综合榜", "按领域", "业务细分", "同一状态下", "稳定与改判"))
    receipt = {"protocol": scores["protocol"], "status": "PASS", "models": len(MODELS),
               "matched_decisions_per_model": 4905, "rankings": len(scores["rankings"]),
               "figure_files": image_count, "verifier_sha256": digest(Path(__file__)),
               "scores_sha256": digest(HERE / "scores.json"),
               "rankings_csv_sha256": digest(HERE / "rankings.csv"),
               "report_sha256": digest(HERE / "REPORT.zh-CN.md"),
               "figure_manifest_sha256": digest(HERE / "figure_manifest.json")}
    destination = HERE / "verification.json"
    if args.write:
        destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        assert load(destination) == receipt, "Leaderboard verification receipt is stale"
    print(f"VERIFIED {len(MODELS)} models, {len(scores['rankings'])} rankings, {image_count} figure files")


if __name__ == "__main__":
    main()
