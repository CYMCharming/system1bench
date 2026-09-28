"""Generate the public CSV and Chinese report exclusively from verified metrics."""
import argparse
import csv
import io

from .common import ROOT, read, sha


MODEL_NAMES = {"english": "Laya English", "multilingual": "Laya Multilingual",
               "llama31_8b_instruct": "Llama-3.1-8B-Instruct", "qwen3_8b": "Qwen3-8B"}


def name(model):
    return MODEL_NAMES.get(model, model)


def table_header(first, models, last=None):
    headers = first + [name(m) for m in models] + (last or [])
    return ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|"]


def homepage(summary, manifest, models):
    per_model = sum(s['decisions'] for s in manifest['suites'])
    total = per_model * len(models)
    full = sum(s['complete_input']['n'] for m in summary['models'].values() for s in m['suites'].values())
    failures = sum(s['all']['failures'] for m in summary['models'].values() for s in m['suites'].values())
    text = ['<!-- BEGIN GENERATED RESULTS -->', '## Measured results — all tasks', '',
            '**Every score below comes from our own local model runs in this repository. No third-party model scores are copied. Jev has not been evaluated.**', '',
            f"{len(models)} checkpoints × {per_model:,} decisions = **{total:,} measured decisions**, including controls. Failures: **{failures}**; complete inputs: **{full:,}/{total:,}**.", '',
            'Laya uses native decision heads. The Llama and Qwen baselines use zero-shot constrained next-token answer selection; Qwen thinking is disabled. See the [exact comparison protocol](docs/LLM_BASELINES.md). These are fixed direct-decision baselines, not best-achievable LLM scores.', '',
            'Values are accuracy against each source reference. **Teacher/synthetic and authored/AI-reviewed rows measure reference agreement**, not independently human-verified correctness. We publish all suites without an overall blended score. Full confidence intervals, F1, Brier/ECE, ordinal errors, language/length slices and timings are in the [report](docs/RESULTS.zh-CN.md), [CSV](results/metrics.csv) and [JSON](results/summary.json).', '']
    for title, control in [('Main tasks', False), ('Same-order repeats and reversed-option controls', True)]:
        count = sum((s['track'] == 'order_robustness') == control for s in manifest['suites'])
        text += [f'### {title} ({count} suites)', ''] + table_header(['Task', 'Decisions / model'], models, ['Reference'])
        for spec in manifest['suites']:
            if (spec['track'] == 'order_robustness') != control:
                continue
            vals = [percent(summary['models'][m]['suites'][spec['name']]['all']['accuracy']) for m in models]
            text.append('| ' + ' | '.join([spec['name'], str(spec['decisions'])] + vals + [spec['reference']]) + ' |')
        text.append('')
    text += ['### Option-order agreement', '', 'Agreement compares predictions on the same inputs; it is not accuracy. The LLM reversal also reassigns answer codes.', '',
             '| Model / task | N | Original → repeat | Repeat → reversed |', '|---|---:|---:|---:|']
    for m in models:
        for task, r in summary['models'][m]['robustness'].items():
            text.append(f"| {name(m)} / {task} | {r['n']} | {percent(r['base_vs_repeat_agreement'])} | {percent(r['repeat_vs_reversed_agreement'])} |")
    text += ['', '### Explicit out-of-scope detection (CLINC150 + OOS)', '',
             '| Model | In-scope accuracy | OOS precision | OOS recall | OOS F1 |', '|---|---:|---:|---:|---:|']
    for m in models:
        o = summary['models'][m]['suites']['clinc150_oos']['oos_metrics']
        text.append(f"| {name(m)} | {percent(o['in_scope']['accuracy'])} | {percent(o['precision'])} | {percent(o['recall'])} | {o['f1']:.4f} |")
    text += ['', '### Ordinal scoring (SST5, fixed 0–4 scale)', '',
             'Lower MAE is better; within-one agreement allows an error of one scale point.', '',
             '| Model | Argmax MAE ↓ | Expected-score MAE ↓ | Within one ↑ |', '|---|---:|---:|---:|']
    for m in models:
        a = summary['models'][m]['suites']['sst5']['all']
        text.append(f"| {name(m)} | {a['ordinal_argmax_mae']:.4f} | {a['ordinal_expected_mae']:.4f} | {percent(a['ordinal_within_one'])} |")
    text += ['', '<!-- END GENERATED RESULTS -->']
    return '\n'.join(text)


def percent(x):
    return f"{x * 100:.2f}%"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="results")
    args = p.parse_args()
    root = ROOT / args.results
    summary = read(root / "summary.json")
    present = {p.name for p in root.iterdir() if p.is_dir() and (p / "metadata.json").exists()}
    if present != set(summary["models"]):
        raise ValueError("Summary omits model directories; finish runs and recompute metrics")
    if summary["protocol_sha256"] != sha(ROOT / "protocol_manifest.json"):
        raise ValueError("Summary protocol mismatch")
    for model, result in summary["models"].items():
        if result["metadata_sha256"] != sha(root / model / "metadata.json"):
            raise ValueError("Summary metadata mismatch; recompute metrics")
        metadata = read(root / model / "metadata.json")
        for name, suite in metadata["suites"].items():
            if sha(root / model / (name + ".json.gz")) != suite["sha256"]:
                raise ValueError("Raw result changed; refuse to render stale claims")
    models = [m for m in MODEL_NAMES if m in summary["models"]] + [m for m in summary["models"] if m not in MODEL_NAMES]
    manifest = read(ROOT / "protocol_manifest.json")
    requests = sum(s["requests"] for s in manifest["suites"])
    decisions = sum(s["decisions"] for s in manifest["suites"])
    failures = sum(s["all"]["failures"] for m in summary["models"].values() for s in m["suites"].values())
    complete = sum(s["complete_input"]["n"] for m in summary["models"].values() for s in m["suites"].values())
    text = ["# System1Bench：本仓库实测结果（v0.2）", "",
            "**System 1 决策模型评测基准。所有数值来自本仓库实际运行，未运行 Jev，也未引用第三方模型成绩。**", "",
            f"覆盖15个公开来源、{len(manifest['suites'])}个任务与对照套件。每个检查点{requests:,}次请求、{decisions:,}个决策；{len(models)}个检查点合计{decisions * len(models):,}个决策，失败{failures}个。来源、语言、原语和参考标签质量分别报告，不计算混合总分。", "",
            "两款Laya（English/Multilingual）检查点均来自 `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`，使用 Laya0.3.20；不是 `laya-typed-decisions` 检查点。", "",
            "Llama/Qwen采用固定零样本候选代码logit评分，Qwen关闭thinking；每题独立前向，不生成推理链。候选内softmax不是校准置信度。详见 [LLM_BASELINES.md](LLM_BASELINES.md)。", "",
            "## 各任务结果", "",
            "以下为全部预定样本的准确率/参考标签符合率；括号是95%分组bootstrap区间。多题状态按状态聚类，TurtleBench按故事聚类，needle按原始needle聚类。合成数据结果不能解释成人类验证的实际决策正确率。", "",
            *table_header(["任务", "决策数"], models, ["参考标签"])]
    for spec in manifest["suites"]:
        if spec["track"] == "order_robustness":
            continue
        values = []
        for m in models:
            s = summary["models"][m]["suites"][spec["name"]]["all"]
            lo, hi = s["accuracy_ci95_cluster"]
            values.append(f"{percent(s['accuracy'])} ({percent(lo)}–{percent(hi)})")
        text.append(f"| {spec['name']} | {spec['decisions']} | " + " | ".join(values) + f" | {spec['reference']} |")
    text += ["", "## 输入是否完整", "",
             f"Laya设 `max_len=8192`、`head_max_len=4096`；LLM设32768-token上限且禁止截断。语义输入相同，分词器及包装不同。逐题审计中{complete:,}/{decisions * len(models):,}个决策输入完整。Laya每个候选描述另有48-token上限。以下只比较所有检查点共同完整的同一批决策。", "",
             *table_header(["任务", "所有模型共同完整 / 全部"], models)]
    for spec in manifest["suites"]:
        if spec["track"] == "order_robustness":
            continue
        shared = summary.get("shared_complete_input", {}).get(spec["name"], {})
        if len(shared) != len(models):
            continue
        values = [percent(shared[m]["accuracy"]) if shared[m]["n"] else "—" for m in models]
        text.append(f"| {spec['name']} | {shared[models[0]]['n']} / {spec['decisions']} | " + " | ".join(values) + " |")
    text += ["", "逐题审计和各检查点自己的完整输入子集都在JSON结果中。选项缩短、题干缩短、状态缩短和候选碰撞分别计数。‘完整输入’只描述编码保留情况，不保证模型能正确利用所有信息。", "",
             "## 开放集：CLINC150/OOS", "", "通过151类中的显式 `oos` 选项判断范围外请求；没有在测试集拟合拒答阈值。AUROC来自P(oos)。", "",
             "| 检查点 | 范围内准确率 | OOS precision | OOS recall | OOS F1 | OOS AUROC |", "|---|---:|---:|---:|---:|---:|"]
    for m in models:
        o = summary["models"][m]["suites"]["clinc150_oos"]["oos_metrics"]
        text.append(f"| {m} | {percent(o['in_scope']['accuracy'])} | {percent(o['precision'])} | {percent(o['recall'])} | {o['f1']:.4f} | {o['auroc']:.4f} |")
    text += ["", "## 有序评分：SST5（固定0–4量表）", "",
             "MAE越小越好；within-one允许相差一个等级。不同量表的任务不混合成一个MAE排行榜。", "",
             "| 检查点 | 众数等级MAE | 期望等级MAE | 相差不超过1级 |", "|---|---:|---:|---:|"]
    for m in models:
        a = summary["models"][m]["suites"]["sst5"]["all"]
        text.append(f"| {m} | {a['ordinal_argmax_mae']:.4f} | {a['ordinal_expected_mae']:.4f} | {percent(a['ordinal_within_one'])} |")
    text += ["", "## 选项顺序稳定性", "",
             "对同一输入先保持选项顺序重复调用，再真实反转候选字典；标签ID和gold不变。‘重复一致率’提供数值/批次变化的对照。LLM的反转同时重分配答案代码；这是一次反转诊断，不代表对所有排列都不变。", "",
             "| 检查点 / 任务 | N | 原始↔重复一致率 | 重复↔反转一致率 | 重复准确率 | 反转准确率 |", "|---|---:|---:|---:|---:|---:|"]
    for m in models:
        for name, r in summary["models"][m]["robustness"].items():
            text.append(f"| {m} / {name} | {r['n']} | {percent(r['base_vs_repeat_agreement'])} | {percent(r['repeat_vs_reversed_agreement'])} | {percent(r['repeat_accuracy'])} | {percent(r['reversed_accuracy'])} |")
    text += ["", "## 英中成对输入", "", "XNLI与MASSIVE对齐了同一批英文、中文样本。下面的‘预测一致’不等于正确；两种语言可能一起预测错误。", "",
             "| 检查点 / 数据集 | 对数 | 英中预测一致 | 两种语言都正确 |", "|---|---:|---:|---:|"]
    for m in models:
        for name, r in summary["models"][m]["bilingual"].items():
            text.append(f"| {m} / {name} | {r['n']} | {percent(r['prediction_agreement'])} | {percent(r['both_correct'])} |")
    text += ["", "## 分层指标与敏感性", "",
             "`results/summary.json` 提供原语（choice/noul/score）、语言、任务family、问题ID、needle长度及位置分层，并报告Brier、ECE、高置信错误、完整标签集macro-F1和有序评分MAE。概率指标仅统计有效输出；准确率将失败算错。", "",
             "| 检查点 | Aegis全部行准确率 | Aegis按原始顺序去重后 | Turtle三分类 | Turtle合并Incorrect/Unknown |", "|---|---:|---:|---:|---:|"]
    for m in models:
        ss = summary["models"][m]["suites"]
        a, t = ss["aegis2_prompt"], ss["turtlebench"]
        text.append(f"| {m} | {percent(a['all']['accuracy'])} | {percent(a['first_occurrence_deduplicated']['accuracy'])} | {percent(t['all']['accuracy'])} | {percent(t['binary_merged_accuracy'])} |")
    text += ["", "Aegis保留1,928条有效官方测试行（含13条重复超额记录、一个标签冲突组）；去重敏感性固定保留原始文件首次出现行，不根据预测选标签。Turtle二分类是本框架的标签合并适配值，不宣称复现上游榜单。", "",
             "## 性能与复现边界", "", "| 检查点 | 累计批次推理秒数 | 推理失败 |", "|---|---:|---:|"]
    for m in models:
        ss = summary["models"][m]["suites"]
        text.append(f"| {m} | {sum(s['inference_seconds'] for s in ss.values()):.2f} | {sum(s['all']['failures'] for s in ss.values())} |")
    text += ["", "LLM输入审计时完成分词并缓存，每个问题独立前向。时间只累加已同步的批次predict调用，包括首批的初始化影响；不含下载、模型加载、输入审计、结果落盘。各模型在A100上运行且机器还有其他任务，不能据此宣称在线服务延迟或稳定的硬件速度排名。", "",
             "模型文件在推理前计算SHA256；源代码、题目顺序、完整输入、原始结果都绑定哈希。逐套件原子落盘，失败保留；源数据与Laya可按固定revision重建；本地LLM快照保留推理前逐文件哈希，上游版本补充核对见 [LLM_BASELINES.md](LLM_BASELINES.md)。", "",
             "## 结论适用范围", "",
             "这份结果覆盖多种静态决策任务，可用于发现语义分类、结构化workflow、开放集和顺序敏感性方面的差异。它不证明模型在真实交互任务中具有对应成功率。AG News/BoolQ属于Laya已知训练任务族；其他公开数据未排除训练污染。JevBench难例、LocalLLaMA及Jev–Laya合成标签都有参考偏差；Reflex为开发fixture。", "",
             "大部分问题说明为英文，中文输入能力不等于全中文指令能力。每个检查点只跑一套固定种子和配置，区间不包含训练随机性、提示选择或标注误差。Laya英文检查点会对无效的高候选数temperature作内部clamp，输出概率不能自动视为已校准。", "",
             "deepset prompt-injections只宜解释为其数据集策略下的标签符合率：同一发布方将合法输入狭义定义为问题/关键词搜索，普通角色扮演或指令也可能标成注入。0/1的极性由固定版本的发布方分类器配置佐证；数据卡内部许可冲突仍未解决，仓库不分发其文本。", "",
             "详细数据来源、许可与适用性见 [DATASET_REVIEW.md](DATASET_REVIEW.md)，新增对照审查见 [BASELINE_AUDIT.md](BASELINE_AUDIT.md)，原Laya审查见 [EXPERIMENT_AUDIT.md](EXPERIMENT_AUDIT.md)。"]
    dest = ROOT / "docs/RESULTS.zh-CN.md" if args.results == "results" else root / "RESULTS.zh-CN.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(text) + "\n")
    buf = io.StringIO()
    fields = ["model", "suite", "track", "reference", "n", "correct", "accuracy", "ci95_low", "ci95_high", "failures", "macro_f1", "brier", "ece10", "complete_n", "complete_accuracy", "shared_complete_n", "shared_complete_accuracy", "valid_probability_n", "ordinal_n", "ordinal_argmax_mae", "ordinal_expected_mae", "ordinal_within_one", "inference_seconds"]
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for m in models:
        for name, s in summary["models"][m]["suites"].items():
            a = s["all"]
            full = s["complete_input"]
            shared = summary.get("shared_complete_input", {}).get(name, {}).get(m, {})
            writer.writerow(dict(model=m, suite=name, track=s["track"], reference=s["reference"],
                                 **{k: a.get(k) for k in ["n", "correct", "accuracy", "failures", "macro_f1", "brier", "ece10"]},
                                 ci95_low=a["accuracy_ci95_cluster"][0], ci95_high=a["accuracy_ci95_cluster"][1],
                                 complete_n=full["n"], complete_accuracy=full.get("accuracy"),
                                 shared_complete_n=shared.get("n"), shared_complete_accuracy=shared.get("accuracy"),
                                 **{k: a.get(k) for k in ["valid_probability_n", "ordinal_n", "ordinal_argmax_mae", "ordinal_expected_mae", "ordinal_within_one"]},
                                 inference_seconds=s["inference_seconds"]))
    (root / "metrics.csv").write_text(buf.getvalue())
    if args.results == "results":
        readme = ROOT / "README.md"
        original = readme.read_text()
        start, end = '<!-- BEGIN GENERATED RESULTS -->', '<!-- END GENERATED RESULTS -->'
        before, remaining = original.split(start, 1)
        _, after = remaining.split(end, 1)
        readme.write_text(before + homepage(summary, manifest, models) + after)
    print("Wrote", dest.name, "and metrics.csv")


if __name__ == "__main__":
    main()
