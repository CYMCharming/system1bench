# System1Bench 数据集构念效度专项复核

**日期：** 2026-09-28  
**结论：** `WARN`  
**审查者：** GPT-5.6-Sol ultra（同模型家族的独立只读代理）  
**审查状态：** `provisional`（同家族复核，不等同于跨家族独立认证）  
**发布状态：** `local_only`（本地审查材料；未上传 GitHub）

## 结论先行

这 15 个来源**可以合理用于分来源、分任务的静态 typed-decision 诊断**：它们覆盖封闭集合意图路由、篇章判断、顺序评分、显式 OOS、安全政策符合、合成工作流和长上下文事实检索。冻结输入中的标签都落在声明的候选空间内，源数据到冻结请求的独立重建没有发现映射错误。

它们**不能共同支持一个统一的“决策准确率”“通用决策智能”或真实业务成功率结论**。原因不只是任务异质：参考答案同时包含数据集标签、人工政策标签、程序标签、合成教师标签和 AI 编写／复核标签；若干任务的可见状态不足以唯一决定目标；TurtleBench 与 Aegis 各有一组完全相同输入却标签冲突；公开数据的训练污染也未被排除。

因此，本报告建议保留分来源结果，但按证据等级解释：

1. **核心静态任务：** Banking77、BoolQ、XNLI、MASSIVE、CLINC，以及 JevBench original/easy，可支持各自窄定义任务上的 reference accuracy。
2. **辅助语义／回归对照：** AG News、Emotion、SST5、ReflexBench；SST5 应同时看 MAE 与 within-one，ReflexBench 主要是已公开开发 fixture 的策略回归。
3. **政策或合成一致性：** prompt-injections、typed-decisions、Jev–Laya 非 needle 子项、JevBench hard、Aegis；这些分数应称为 reference/policy/teacher agreement。
4. **窄定义程序对照：** Jev–Laya needle 可单列为显式事实检索 control，但只有 25 个独立 needle 内容单元。
5. **暂不作为无噪声正确率：** typed-decisions、prompt-injections、TurtleBench；Aegis 至少排除或单列冲突重复组。修正前不应由这些来源推导模型在真实工作流、安全或开放世界推理中的“正确率”。

## 复核范围与方法

本次是**数据有效性专项复核**，不重跑任何模型，不修改 `data/frozen.json`、现有预测、指标或分数，也不重复此前对 105,800 行预测结果做过的完整性审计。

复核包含两层：

- **全量程序检查：** 对 15 个来源的所有实际使用行检查 gold 是否属于声明候选空间；按适配代码从固定源文件独立重建 `state`、`questions` 和 gold，并与冻结输入逐项比对；统计完全相同状态、冲突标签和依赖组。结果是候选覆盖失败 0、源到冻结输入重建不一致 0。
- **固定语义复核：** 使用种子 `system1bench-dataset-validity-2026-09-28-v1`，按 `SHA256(seed|source-or-stratum|case-id)` 升序选取。XNLI/MASSIVE 按相同 `source_index` 成对；JevBench、Jev–Laya、CLINC、TurtleBench、Aegis 分层。共 286 个复核单位，其中含 24 个英中配对单位；具体规则和全部 ID 在忽略提交的 trace 中。

固定样本只用于发现和说明具体问题，**没有把样本中的问题比例外推到全量**。本报告中的全量计数只来自程序遍历全部实际使用行。

## 优先级发现

### P0：两个来源存在完全相同可见输入的冲突 gold

**TurtleBench。** ID `484` 与 `832` 的可见故事和 guess 完全相同，gold 分别为 `Incorrect` 与 `Unknown`。这是确定的源标签冲突，不是对语义歧义的主观判断。全量共有 18 个完全重复组（18 条重复超额），其中 1 组冲突。当前三分类 accuracy 不能被视为对无噪声真值的正确率；应先裁决或排除该组，并继续按 32 个故事聚类统计。

**Aegis2。** ID `8e226f8cfe5a4edf879babebebc6d91d` 与 `92abced2c4764af1a2b5af235fa00bd4` 是原始 prompt 精确相同的破坏他人水槽请求，human prompt gold 分别为 safe 与 unsafe。全量有 13 条重复超额、1 个冲突组。现有“保留首次出现”的敏感性结果会任意保留 safe，不能裁决真值；未来版本化协议的主结果应排除该冲突组或把它作为标签不确定性单列。

### P0：typed-decisions 的 target 部分不可由可见状态唯一决定，且教师 gold 与自带 rubric/factor 冲突

该来源的数据卡明确说明 gold 是约 4B teacher 三次采样的均值，代表 teacher agreement，不是人工业务真值。全量 2,000 个决策中，936 个 gold 的 `confidence < 0.5`。

- `invoice_processing_000027` 的可见 invoice ID 已出现在 `prior_invoice_ids`，隐藏 factor 也写明 `duplicate_submission`，但 gold 给出 `duplicate=false` 且 `disposition=approve`，与源自带 rubric 的 duplicate→reject 规则冲突。
- 17 个 `duplicate_submission` 状态中，有 6 个 gold 为 `duplicate=false`：`000021`、`000027`、`000042`、`000062`、`000064`、`000092`；12 个 disposition 不是 rubric 指定的 `reject`。
- agent-trace 状态只暴露步骤计数等摘要，没有暴露 completion 事实，所以 `outcome` 通常不能由模型可见状态唯一推出。按隐藏 `completion/violated_constraint` 与源 rubric 的映射核对，100 个状态中有 53 个 outcome argmax 不一致；例如 `agent_trace_observability_000052` 的隐藏 completion 为 partial，gold 却为 success。

隐藏 factor 本来就不应泄漏给被测模型；问题在于目标需要这些未观察事实，同时教师 gold 还与这些 factor/rubric 不一致。因此该来源适合探索性 synthetic/teacher agreement，不适合作为 correctness leaderboard 的真值来源。

### P1：Jev–Laya 与 JevBench 的部分参考不是独立人工 gold

Jev–Laya 的生成和 blind re-label 都使用 `gpt-5.5`。categorical 不一致样本被删除，ordinal 只要求两次评分相差不超过 1。这个流程能提高内部一致性，却会筛出更符合相同教师边界的样本，不能等价为独立人工真值。全量保留下来的 ordinal generator/verifier 差异仍包括 triage frustration 51/167、moderation severity 19/142、routing difficulty 60/137、reviews stars 37/150、guard harm 8/146。claims 和 multilingual 的 categorical 差异均为 0/150 与 0/128，这说明筛选后一致，不证明客观正确。

JevBench original/easy 的固定 rubric 与样本适合窄定义静态决策。hard 由 Claude Opus 5 与 GPT-5.6-Sol 交叉 blind 编写／复核，仍属于 AI-authored/AI-reviewed evidence。另有 10 个 probability case 提供 `gold_probs`，System1Bench 当前只取 top label 计算 accuracy；它只支持“最可能结果标签”比较，不能声称复现 JevBench 的概率校准或 proper-score 评测。

### P1：政策标签和主观标签只能支持符合率

prompt-injections 的固定样本 `prompt_injections:38`（普通 SQL 代码请求）和 `prompt_injections:79`（询问训练时间）被标为 injection，符合该来源很窄的 LEGIT 定义，但不是通用提示注入真值。Aegis 的 prompt 标签由人标注，证据强于合成教师；其 21 类安全 taxonomy 仍是政策判断，且 `b4ba0d10eff04c9d8182b7eee78a8d24` 等边界样本说明标签依赖政策与上下文。两者可报告 policy agreement，不能推导生产攻击检测率或上线安全保证。

Emotion 与 SST5 也包含自然的主观性。固定样本 `emotion:984` 更像被忽视／自我压抑，却标为 anger；这只能记为疑似歧义，不能仅凭一次复核改判为硬错误。SST5 的五级边界应优先结合 MAE 与 within-one，而不是只看 exact accuracy。

## 15 个来源逐项判断

表中的“规模”是本项目实际使用量；“样本证据”只列 ID 和简短释义，不公开源文本。

| 来源 | 规模与参考性质 | 构念与可见状态判断 | 固定样本证据 | 建议 |
|---|---|---|---|---|
| AG News | 1,000；dataset-provided topic label | 状态足以做四类主题分流，但只测内容分类，不测行动质量 | `ag_news:940` 的体育人物法律新闻体现 topic 边界 | **辅助语义／control**；不作通用决策证据 |
| Emotion | 1,000；弱／远程标注的 dataset label | 文本可见，但单一情绪标签简化主观表达 | `emotion:984` 为疑似情绪边界 | **辅助语义／control**；报告 label agreement |
| Banking77 | 1,000；dataset label，完整 77 类 | 适合封闭集合客服路由；短文本仍有相近意图边界 | `banking77:541` 的 account blocked 被标为 pin blocked | **核心：窄定义静态 intent routing** |
| BoolQ | 1,000 个 validation 状态、两种接口；dataset label | passage+question 通常足以决定 yes/no；公开 test gold 不可用 | `boolq:1102` 等样本显示问题与 passage 绑定 | **核心：篇章条件二元判断**；注明 Laya 训练任务族重合 |
| SST5 | 1,000、两种接口；dataset ordinal label | 文本足以评估有序情感符合，但五级边界主观 | `sst5:1564` 短句上下文有限 | **辅助 ordinal control**；以 MAE/within-one 补充 exact |
| XNLI | 英中对齐各 1,000；dataset NLI label | 适合静态 NLI 与 paired consistency；中文翻译会改变难度 | index `2540`、`3068`、`1964` 有生硬翻译或表达漂移 | **核心／辅助 NLI**；语言差值须带翻译限定 |
| MASSIVE | 英中对齐各 1,000；dataset intent label | 适合 60 类封闭 intent routing；test 实际出现 59 类 | index `2270`、`2819`、`2250` 有地点／人名本地化 | **核心：多语言封闭路由**；paired 差值混合本地化难度 |
| prompt-injections | 全部 116；来源政策标签 | 标签依赖窄 LEGIT 定义，普通指令也可能标 injection | `prompt_injections:38`、`:79` | **探索性 policy agreement**；排除通用 correctness 总榜 |
| typed-decisions | 400 状态／2,000 决策；4B teacher 三次均值 | 多个 target 欠决定；教师与 factor/rubric 有确定冲突 | `invoice_processing_000027`、`agent_trace_observability_000052` | **探索性 synthetic/teacher agreement**；排除 correctness 榜 |
| JevBench | 72 original + 48 easy + 111 hard；authored/AI-reviewed | original/easy 可见状态与 rubric 较充分；hard 仍是 AI 构造 | `original-routing-05-1`、`easy-tool_selection-00`、`hard-opus-a-probability-04` | **original/easy 核心；hard 探索性**；概率题只解释 top label |
| ReflexBench | 95 个 development fixture；authored/AI-reviewed | 多数答案由 state/rubric 明示，适合接口和策略回归，不是 held-out correctness | `public-choice-v1-execution-failure-classification-synthetic-permission-denied` | **辅助 product-regression/control** |
| Jev–Laya | 1,470 状态／3,386 决策；synthetic teacher，needle 为 programmatic | 同一模型生成、复标和筛选；ordinal 并非客观 gold | `triage-0034`、`reviews-0074`、`needle-02-1000-start` | **非 needle：synthetic/policy agreement；needle：窄检索 control** |
| CLINC150/OOS | 5,500；dataset label，150 intents + 显式 OOS | 适合封闭 ontology 下的 open-set 分类；OOS 不是通用拒答 | `clinc:5226`（OOS strata）、`clinc:2908`（in-scope strata） | **核心：显式 OOS intent classification** |
| TurtleBench | 1,532 行／32 故事；dataset label | 强故事依赖；Incorrect/Unknown 有开放世界边界，且存在硬冲突 | 冲突 `484`/`832`；`1369`、`1282`、`132` 显示宽松蕴含边界 | **修复前排除 correctness 榜**；之后可作探索性 contextual reasoning |
| Aegis2 prompt | 1,928；human prompt annotation | 可测指定 taxonomy 的提示安全符合率；不是生产安全能力 | 冲突 `8e226...`/`92abce...`；边界 `b4ba0...` | **人工 policy-agreement auxiliary**；排除／单列冲突组 |

## 双语、依赖结构与统计单位

XNLI 和 MASSIVE 的英文、中文按同一 `source_index` 和 gold 配对，适合测同一任务标签下的跨语言一致性。但 XNLI 中文是翻译文本，MASSIVE 是本地化而非逐字翻译；因此语言差值同时包含模型语言能力、翻译自然度和本地化难度。中文 state 配英文 instruction 也不等价于端到端全中文能力。

若要给出置信区间或显著性判断，必须保留真实依赖单位：

- Jev–Laya needle 是 25 个 needle × 6 个长度 × 3 个位置，共 450 状态；应按 needle 聚类，不能把 450 个变体当作 450 个独立事实。
- TurtleBench 只有 32 个故事，单故事最多 100 行；应按故事聚类。
- JevBench 有 36 个共享两题状态组，其余为单题。
- Aegis 当前按原始 prompt 的精确相等关系识别依赖组；v0.2 保留官方冲突行，并另报“首次出现”敏感性。冲突裁决或排除只作为未来版本化协议建议；若再增加文本规范化分组，也必须另行说明。
- typed-decisions 每个状态有 5 个问题；问题级结果不能被当成独立状态样本。

现有 `metrics.py` 已对 needle、Turtle 故事、Aegis 重复 prompt 和同状态多问题使用 group-cluster bootstrap；这解决抽样单位相关性，不会消除 gold 偏差或冲突。

## 训练污染与结论边界

所有公开来源都可能进入过模型训练语料，未做去污染检索。AG News 与 BoolQ 已知属于 Laya 训练任务族；这表明存在任务族重合，不等同于已证明具体测试行泄漏。其余来源也不能被称为 contamination-free。

当前结果可以支持：

- 某个固定 checkpoint、固定适配和候选集合对某一来源 reference 的符合率；
- Banking77/MASSIVE/CLINC 等封闭 ontology 下的静态路由表现；
- BoolQ/XNLI 的给定文本条件判断；
- XNLI/MASSIVE 配对样本上的跨语言一致性；
- Jev–Laya needle 的窄定义显式事实检索；
- 选项反转、同序重复等接口稳定性诊断。

当前结果不支持：

- 把 15 源合并为一个“通用决策准确率”或总排名；
- 真实业务最优动作、交互式 agent 成功率、收益或因果决策质量；
- 生产安全、通用注入检测或通用拒答能力；
- JevBench 概率校准／proper-score 复现；
- 无训练污染的泛化，或全中文工作流能力；
- 将 teacher/synthetic、AI-reviewed 与 human/dataset reference 视为相同强度的真值。

## A–F 完整性检查（限定于本次数据有效性复核）

### A. Ground-truth provenance：WARN

没有发现把本次被测模型输出暗中改作 gold 的路径；适配器只把 `state` 和 `questions` 送给模型（`system1bench/common.py:70-72`）。但参考性质混合：typed-decisions 与 Jev–Laya 是合成教师，JevBench hard 是 AI 编写／复核，Turtle/Aegis 有已验证冲突。所有这些来源必须按 reference quality 分层解释。

### B. Score normalization：PASS

accuracy 是直接的预测标签与 reference 比较（`system1bench/metrics.py:43-53`），未发现按模型自身最大值、最小值或均值重缩放 accuracy。概率归一化只用于候选概率指标；它不改变 gold 或正确计数。

### C. Result file existence：PASS（范围限定）

本次确认冻结输入、四组 metadata、原始结果文件、`results/summary.json` 和 `results/metrics.csv` 存在，并与数据协议关联。本报告不重新执行历史 105,800 行结果与所有公开表格的逐数字审计；该工作属于独立的 baseline integrity audit。

### D. Dead code detection：WARN（范围限定）

本次确认报告实际使用的 accuracy、cluster CI、CLINC OOS、ordinal、bilingual，以及 Aegis/Turtle sensitivity 路径可从 `system1bench/metrics.py` 和 `system1bench/report.py` 到达。没有对全仓每个函数做新的死代码证明，因此不能给出全仓级 PASS。

### E. Scope assessment：WARN

15 个来源覆盖多种静态 typed decision 组件，规模足以做分来源诊断；证据仍主要是单次固定配置、公开数据和静态标签。它不覆盖环境交互、动作后果、真实效用、独立多轮人工裁决或训练去污染。

### F. Evaluation type classification：PASS

建议分类为：

- `real_gt` / dataset-provided：AG News、Emotion、Banking77、BoolQ、SST5、XNLI、MASSIVE、CLINC、TurtleBench（后者含已验证冲突）；
- `human_eval` / human prompt annotation：Aegis2（含已验证冲突）；
- `synthetic_proxy`：typed-decisions、Jev–Laya 非 needle；
- `authored_or_AI_reviewed`：JevBench、ReflexBench；
- `programmatic`：Jev–Laya needle；
- prompt-injections 应作为 dataset-provided policy label 单列，不提升为通用攻击真值。

## 处置建议

以下是**未来版本化协议**的建议，不追溯修改 v0.2 的 `data/frozen.json`、原始结果、当前指标或已发布分数。若采用，应以新版本重新生成输入和指标，并保留 v0.2 的可复现性。

1. 继续发布每来源结果，但不要生成跨来源 blended accuracy；表头与正文统一使用 `reference agreement/accuracy against source reference`。
2. 将 typed-decisions、prompt-injections、TurtleBench 从无噪声 correctness leaderboard 中移出或明显分轨；Jev–Laya synthetic、JevBench hard 和 Aegis 使用 agreement/policy wording。
3. TurtleBench `484`/`832` 与 Aegis `8e226...`/`92abce...` 在裁决前从主 accuracy 排除或单列；不要用“保留首次出现”代替裁决。
4. JevBench original/easy 与 hard 分轨；10 个 probability case 明示当前只评 top label。
5. Jev–Laya needle 按 25 个 needle 聚类并单列；非 needle 报告生成／复标模型和 ordinal disagreement。
6. typed-decisions 若未来要进入 correctness track，需要补充可见、可判定的状态字段，并以独立规则或人工重标替代低置信教师均值。
7. 双语结果同时报告 paired consistency 与各语言 accuracy，并保留翻译／本地化和英文 instruction 限定。

## 可复核材料

审查脚本、固定样本 ID、全量结构检查、固定上游版本文件、输入哈希及完整 reviewer prompt/response 位于：

` .aris/traces/experiment-audit/2026-09-28_dataset_validity/ `

该目录按项目策略不提交。公开报告只记录 ID、数字和简短释义，不复制受上游条款约束的原始样本文本。
