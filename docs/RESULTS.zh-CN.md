# System1Bench：Laya 评测结果（v0.1）

**System 1 决策模型评测基准。首版只有 Laya 实测，未运行 Jev。**

覆盖15个公开来源、36个任务与对照套件。每个检查点22,934次请求、26,450个决策；两个检查点合计52,900个决策，失败0个。来源、语言、原语和参考标签质量分别报告，不计算混合总分。

英文与多语检查点均来自 `convaiinnovations/laya@55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`，使用 Laya0.3.20；不是 `laya-typed-decisions` 检查点。

## 各任务结果

以下为全部预定样本的准确率/参考标签符合率；括号是95%分组bootstrap区间。多题状态按状态聚类，TurtleBench按故事聚类，needle按原始needle聚类。合成数据结果不能解释成人类验证的实际决策正确率。

| 任务 | 决策数 | Laya English | Laya Multilingual | 参考标签 |
|---|---:|---:|---:|---|
| ag_news | 1000 | 94.30% (92.90%–95.70%) | 92.40% (90.80%–94.00%) | dataset_provided |
| emotion | 1000 | 59.10% (55.90%–62.00%) | 53.00% (49.70%–55.90%) | dataset_provided |
| banking77 | 1000 | 55.30% (52.20%–58.40%) | 51.20% (47.90%–54.40%) | dataset_provided |
| boolq | 1000 | 84.60% (82.40%–86.90%) | 77.70% (75.10%–80.20%) | dataset_provided |
| boolq_choice | 1000 | 83.60% (81.40%–85.90%) | 77.40% (74.80%–80.00%) | dataset_provided |
| sst5 | 1000 | 34.60% (31.60%–37.60%) | 29.50% (26.70%–32.40%) | dataset_provided |
| sst5_choice | 1000 | 49.60% (46.30%–52.70%) | 35.60% (32.60%–38.40%) | dataset_provided |
| xnli_en | 1000 | 86.00% (83.80%–88.10%) | 81.70% (79.50%–83.90%) | dataset_provided |
| xnli_zh | 1000 | 61.50% (58.50%–64.40%) | 74.30% (71.60%–76.90%) | dataset_provided |
| massive_en | 1000 | 54.10% (51.00%–57.10%) | 42.30% (39.30%–45.50%) | dataset_provided |
| massive_zh | 1000 | 30.40% (27.40%–33.40%) | 33.20% (30.30%–36.10%) | dataset_provided |
| prompt_injections | 116 | 70.69% (62.93%–79.31%) | 57.76% (49.14%–66.38%) | dataset_provided |
| typed_decisions | 2000 | 36.35% (33.90%–38.80%) | 34.90% (32.65%–37.25%) | synthetic_teacher |
| jevbench_original | 72 | 70.83% (58.33%–81.94%) | 41.67% (29.17%–54.17%) | authored_or_AI_reviewed |
| jevbench_easy | 48 | 95.83% (89.58%–100.00%) | 89.58% (79.17%–97.92%) | authored_or_AI_reviewed |
| jevbench_hard | 111 | 29.73% (20.72%–38.74%) | 32.43% (24.32%–41.44%) | authored_or_AI_reviewed |
| reflexbench_reflex-public-choice-v1 | 95 | 58.95% (49.47%–69.47%) | 46.32% (36.84%–55.79%) | authored_or_AI_reviewed |
| jev_laya_triage | 501 | 62.48% (58.28%–66.47%) | 55.69% (51.69%–59.88%) | synthetic_teacher |
| jev_laya_moderation | 426 | 67.84% (61.97%–73.71%) | 48.36% (43.89%–53.05%) | synthetic_teacher |
| jev_laya_routing | 411 | 64.23% (59.85%–69.10%) | 51.09% (45.99%–56.20%) | synthetic_teacher |
| jev_laya_claims | 300 | 90.00% (85.33%–94.00%) | 80.00% (74.00%–85.67%) | synthetic_teacher |
| jev_laya_reviews | 300 | 70.67% (66.00%–75.33%) | 42.33% (36.33%–48.34%) | synthetic_teacher |
| jev_laya_guard | 292 | 60.62% (54.79%–66.44%) | 33.22% (27.74%–38.70%) | synthetic_teacher |
| jev_laya_multilingual | 256 | 57.81% (51.56%–64.45%) | 62.50% (57.03%–68.36%) | synthetic_teacher |
| jev_laya_needle | 900 | 50.22% (39.77%–61.00%) | 47.44% (35.00%–59.89%) | programmatic |
| clinc150_oos | 5500 | 55.73% (54.42%–57.07%) | 64.76% (63.51%–65.96%) | dataset_provided |
| turtlebench | 1532 | 42.62% (38.74%–46.67%) | 41.64% (37.53%–45.42%) | dataset_provided |
| aegis2_prompt | 1928 | 49.59% (47.29%–51.76%) | 57.05% (54.79%–59.25%) | human_prompt_annotation |

## 输入是否完整

所有新运行统一设 `max_len=8192`、`head_max_len=4096`。逐题编码审计确认：本次52,900/52,900个决策保留了完整状态、题干和候选，没有特殊mask清理。Laya内部每个候选描述仍有48-token上限，但本次输入没有触发。以下核对两个检查点共同完整的同一批决策；结果与全部样本一致。

| 任务 | 两模型共同完整输入的决策数 / 全部 | English | Multilingual |
|---|---:|---:|---:|
| ag_news | 1000 / 1000 | 94.30% | 92.40% |
| emotion | 1000 / 1000 | 59.10% | 53.00% |
| banking77 | 1000 / 1000 | 55.30% | 51.20% |
| boolq | 1000 / 1000 | 84.60% | 77.70% |
| boolq_choice | 1000 / 1000 | 83.60% | 77.40% |
| sst5 | 1000 / 1000 | 34.60% | 29.50% |
| sst5_choice | 1000 / 1000 | 49.60% | 35.60% |
| xnli_en | 1000 / 1000 | 86.00% | 81.70% |
| xnli_zh | 1000 / 1000 | 61.50% | 74.30% |
| massive_en | 1000 / 1000 | 54.10% | 42.30% |
| massive_zh | 1000 / 1000 | 30.40% | 33.20% |
| prompt_injections | 116 / 116 | 70.69% | 57.76% |
| typed_decisions | 2000 / 2000 | 36.35% | 34.90% |
| jevbench_original | 72 / 72 | 70.83% | 41.67% |
| jevbench_easy | 48 / 48 | 95.83% | 89.58% |
| jevbench_hard | 111 / 111 | 29.73% | 32.43% |
| reflexbench_reflex-public-choice-v1 | 95 / 95 | 58.95% | 46.32% |
| jev_laya_triage | 501 / 501 | 62.48% | 55.69% |
| jev_laya_moderation | 426 / 426 | 67.84% | 48.36% |
| jev_laya_routing | 411 / 411 | 64.23% | 51.09% |
| jev_laya_claims | 300 / 300 | 90.00% | 80.00% |
| jev_laya_reviews | 300 / 300 | 70.67% | 42.33% |
| jev_laya_guard | 292 / 292 | 60.62% | 33.22% |
| jev_laya_multilingual | 256 / 256 | 57.81% | 62.50% |
| jev_laya_needle | 900 / 900 | 50.22% | 47.44% |
| clinc150_oos | 5500 / 5500 | 55.73% | 64.76% |
| turtlebench | 1532 / 1532 | 42.62% | 41.64% |
| aegis2_prompt | 1928 / 1928 | 49.59% | 57.05% |

逐题审计和各检查点自己的完整输入子集都在JSON结果中。选项缩短、题干缩短、状态缩短和候选碰撞分别计数。‘完整输入’只描述编码保留情况，不保证模型能正确利用所有信息。

## 开放集：CLINC150/OOS

通过151类中的显式 `oos` 选项判断范围外请求；没有在测试集拟合拒答阈值。AUROC来自P(oos)。

| 检查点 | 范围内准确率 | OOS precision | OOS recall | OOS F1 | OOS AUROC |
|---|---:|---:|---:|---:|---:|
| english | 49.11% | 38.44% | 85.50% | 0.5304 | 0.8573 |
| multilingual | 74.42% | 86.59% | 21.30% | 0.3419 | 0.8539 |

## 选项顺序稳定性

对同一输入先保持选项顺序重复调用，再真实反转候选字典；标签ID和gold不变。‘重复一致率’提供数值/批次变化的对照。这是一次反转诊断，不代表对所有排列都不变。

| 检查点 / 任务 | N | 原始↔重复一致率 | 重复↔反转一致率 | 重复准确率 | 反转准确率 |
|---|---:|---:|---:|---:|---:|
| english / banking77 | 100 | 100.00% | 52.00% | 49.00% | 58.00% |
| english / massive_en | 100 | 100.00% | 50.00% | 54.00% | 52.00% |
| english / jevbench_original | 36 | 100.00% | 91.67% | 61.11% | 58.33% |
| english / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 89.47% | 58.95% | 58.95% |
| multilingual / banking77 | 100 | 100.00% | 62.00% | 44.00% | 44.00% |
| multilingual / massive_en | 100 | 100.00% | 54.00% | 50.00% | 43.00% |
| multilingual / jevbench_original | 36 | 100.00% | 77.78% | 58.33% | 55.56% |
| multilingual / reflexbench_reflex-public-choice-v1 | 95 | 100.00% | 80.00% | 46.32% | 45.26% |

## 英中成对输入

XNLI与MASSIVE对齐了同一批英文、中文样本。下面的‘预测一致’不等于正确；两种语言可能一起预测错误。

| 检查点 / 数据集 | 对数 | 英中预测一致 | 两种语言都正确 |
|---|---:|---:|---:|
| english / xnli | 1000 | 65.10% | 57.30% |
| english / massive | 1000 | 41.30% | 26.50% |
| multilingual / xnli | 1000 | 75.60% | 66.50% |
| multilingual / massive | 1000 | 50.50% | 27.70% |

## 分层指标与敏感性

`results/summary.json` 提供原语（choice/noul/score）、语言、任务family、问题ID、needle长度及位置分层，并报告Brier、ECE、高置信错误、完整标签集macro-F1和有序评分MAE。概率指标仅统计有效输出；准确率将失败算错。

| 检查点 | Aegis全部行准确率 | Aegis按原始顺序去重后 | Turtle三分类 | Turtle合并Incorrect/Unknown |
|---|---:|---:|---:|---:|
| english | 49.59% | 49.61% | 42.62% | 66.71% |
| multilingual | 57.05% | 57.02% | 41.64% | 58.88% |

Aegis保留1,928条有效官方测试行（含13条重复超额记录、一个标签冲突组）；去重敏感性固定保留原始文件首次出现行，不根据预测选标签。Turtle二分类是本框架的标签合并适配值，不宣称复现上游榜单。

## 性能与复现边界

| 检查点 | 累计批次推理秒数 | 推理失败 |
|---|---:|---:|
| english | 223.31 | 0 |
| multilingual | 129.10 | 0 |

时间只累加已同步的批次predict调用，包括首批的初始化影响；不含下载、模型加载、输入审计、结果落盘。两张A100上同时运行且机器还有其他任务，不能据此宣称在线服务延迟或稳定的硬件速度排名。

模型文件在推理前计算SHA256；源代码、题目顺序、完整输入、原始结果都绑定哈希。逐套件原子落盘，失败保留；源数据与模型可按固定revision重建。

## 结论适用范围

这份结果覆盖多种静态决策任务，可用于发现语义分类、结构化workflow、开放集和顺序敏感性方面的差异。它不证明模型在真实交互任务中具有对应成功率。AG News/BoolQ属于Laya已知训练任务族；其他公开数据未排除训练污染。JevBench难例、LocalLLaMA及Jev–Laya合成标签都有参考偏差；Reflex为开发fixture。

大部分问题说明为英文，中文输入能力不等于全中文指令能力。每个检查点只跑一套固定种子和配置，区间不包含训练随机性、提示选择或标注误差。英文检查点会对无效的高候选数temperature作内部clamp，输出概率不能自动视为已校准。

deepset prompt-injections只宜解释为其数据集策略下的标签符合率：同一发布方将合法输入狭义定义为问题/关键词搜索，普通角色扮演或指令也可能标成注入。0/1的极性由固定版本的发布方分类器配置佐证；数据卡内部许可冲突仍未解决，仓库不分发其文本。

详细数据来源、许可与适用性见 [DATASET_REVIEW.md](DATASET_REVIEW.md)，审查见 [EXPERIMENT_AUDIT.md](EXPERIMENT_AUDIT.md)。
