# System1Bench 数据集说明：测什么、从哪来、如何解读

本文对应 2026-09-28 发布的 v0.2 评测，解释我们实际使用的 **15 个公开数据集／任务集合**。它们经过语言、任务和输出接口拆分后，形成 **28 个主测试套件和 8 个稳定性对照套件**。36 个套件不等于 36 个独立数据集。

我们实际运行了 Laya English、Laya Multilingual、Llama-3.1-8B-Instruct 和 Qwen3-8B；**尚未运行 Jev**。文中带有 Jev 名称的项目是数据或评测框架的来源，不代表借用了其模型成绩。全部实测成绩见[中文结果报告](RESULTS.zh-CN.md)。

## 先理解：这些数据为什么能用来测决策模型？

这里的“决策”是：给模型一份状态或文本，提出问题，再让它在有限的答案中选择。三种接口分别是：

| 接口 | 含义 | 典型用途 |
|---|---|---|
| `choice` | 从指定类别或动作中选一个 | 判断用户意图、把请求分配到某个队列 |
| `noul` | 判断是／否 | 是否紧急、是否需要工具、是否存在风险 |
| `score` | 选择一个有顺序的等级 | 情绪强度、风险等级、满意度 |

传统分类数据可以检查模型是否理解输入；工作流数据更接近实际的路由、审核和分流；安全数据检查模型是否遵循指定的安全标注政策。这三类证据各有用途，不能把分数混成一个“通用决策智力”总分。

它们都属于**静态判断**：不执行选出的动作，也不观察后续收益。因此，成绩不能直接解释为智能体完成任务的成功率、真实业务收益或上线安全保证。

## 一览表

以下“本次用量”均为**每个模型**的主测试用量，不含选项顺序对照。一个输入状态可以对应多个问题，所以“决策数”可能大于“样本数”。来源列是我们实际下载的位置；原始项目、镜像和适配版的区别在后文说明。

| 数据集／集合 | 主要测什么 | 实际下载来源 | 本次用量 |
|---|---|---|---|
| AG News | 新闻主题四分类 | [HF: fancyzhx/ag_news](https://huggingface.co/datasets/fancyzhx/ag_news) | 1,000 条／1,000 次决策 |
| Emotion | 六类文本情绪 | [HF: dair-ai/emotion](https://huggingface.co/datasets/dair-ai/emotion) | 1,000 条／1,000 次决策 |
| Banking77 | 77 类银行客服意图 | [HF: mteb/banking77](https://huggingface.co/datasets/mteb/banking77) | 1,000 条／1,000 次决策 |
| BoolQ | 根据文章回答是非问题 | [HF: google/boolq](https://huggingface.co/datasets/google/boolq) | 1,000 条，两个接口共 2,000 次决策 |
| SST5 | 五级情感倾向 | [HF: SetFit/sst5](https://huggingface.co/datasets/SetFit/sst5) | 1,000 条，两个接口共 2,000 次决策 |
| XNLI | 前提与假设的逻辑关系 | [HF: facebook/xnli](https://huggingface.co/datasets/facebook/xnli) | 英文、中文各 1,000 条，共 2,000 次决策 |
| MASSIVE Intent | 60 类多语言助手意图 | [HF: mteb/amazon_massive_intent](https://huggingface.co/datasets/mteb/amazon_massive_intent) | 英文、中文各 1,000 条，共 2,000 次决策 |
| deepset prompt-injections | 是否属于提示注入 | [HF: deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) | 116 条／116 次决策 |
| LocalLLaMA typed-decisions | 一个工作流状态下的多种判断 | [HF: LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) | 400 个状态／2,000 次决策 |
| CLINC150/OOS | 150 类意图及范围外请求 | [HF: clinc/clinc_oos](https://huggingface.co/datasets/clinc/clinc_oos) | 5,500 条／5,500 次决策 |
| JevBench | 多种原生类型决策题 | [GitHub: fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench) | 231 条／231 次决策 |
| ReflexBench | 产品／工作流的选择题回归测试 | [GitHub: brida-ai/reflexbench](https://github.com/brida-ai/reflexbench) | 95 条／95 次决策 |
| Jev–Laya benchmark | 工单、路由、审核、长文检索等 8 类任务 | [GitHub: harrymunro/jev-laya-benchmark](https://github.com/harrymunro/jev-laya-benchmark) | 1,470 条／3,386 次决策 |
| TurtleBench 适配版 | 基于故事真相判断猜测 | [GitHub: spoonnotfound/decision-model-bench](https://github.com/spoonnotfound/decision-model-bench) | 32 个故事、1,532 条／1,532 次决策 |
| Aegis2 | 用户提示的内容安全判断 | [HF: nvidia/Aegis-AI-Content-Safety-Dataset-2.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0) | 1,928 条／1,928 次决策 |

## 逐项说明

### 1. AG News：新闻主题识别

**来源与任务。** 使用 Hugging Face 的 `fancyzhx/ag_news` 版本。它是 AG News 新闻主题分类数据，输入新闻文本，输出世界新闻、体育、商业、科学与技术四类之一。HF 发布账号是我们下载的入口，不应直接当作所有新闻内容的原始作者。

**我们如何使用。** 从 7,600 条 test 数据中固定抽取 1,000 条，套件名为 `ag_news`。

**与决策模型的关系。** 它能检查简单语义分类和内容分流能力，但没有复杂业务约束，也不评价动作后果。已知 Laya 存在这一训练任务家族的重合，不能把成绩当作完全陌生任务上的泛化证明；这也不等于已经证实具体测试样本被用于训练。

### 2. Emotion：识别文本表达的情绪

**来源与任务。** 使用 `dair-ai/emotion`，将英文短文本归为悲伤、喜悦、喜爱、愤怒、恐惧、惊讶六类。

**我们如何使用。** 从 2,000 条 test 数据中固定抽取 1,000 条，套件名为 `emotion`。

**与决策模型的关系。** 可作为客服情绪识别、情绪分流的基础能力测试。不过它采用弱监督／远程监督标注，单一情绪标签也会简化含混的自然语言。这里测的是与数据标签的一致程度，不能推导心理诊断能力或真实客服处理质量。

### 3. Banking77：细粒度银行客服意图

**来源与任务。** 原始项目来自 [PolyAI 的 task-specific-datasets](https://github.com/PolyAI-LDN/task-specific-datasets)，我们实际下载的是 MTEB 在 Hugging Face 上的 `mteb/banking77` 镜像。输入银行客服请求，在完整的 **77 个意图**中选一个。

**我们如何使用。** MTEB 版本把原始 3,080 条测试数据去重为 3,076 条，我们从中固定抽取 1,000 条，套件名为 `banking77`。另选 100 条做同序重复和选项倒序对照。

**与决策模型的关系。** 很适合测“用户的请求应该进入哪条处理流程”，同时考验大量相近候选项之间的区分能力。但它只判断意图，不检查实际处理操作是否成功。来源条款以原始 Banking77 的 CC BY 4.0 为依据，不能仅依镜像页面的 MIT 描述认定数据授权。

### 4. BoolQ：依据文章回答是／否

**来源与任务。** 使用 Google 发布的 `google/boolq`。输入包含文章和一个自然语言问题，判断文章是否支持肯定答案。

**我们如何使用。** 因为公开 test 不提供可用的标准答案，从 3,270 条 **validation** 数据中固定抽取 1,000 条。同样的文章与问题分别使用 `noul` 和 `choice` 接口，形成 `boolq`、`boolq_choice` 两个套件，共 2,000 次决策。

**与决策模型的关系。** 可以检查“依据已给材料做二元判断”，并观察接口变化是否影响结果。两个套件共用题目，不能算两份独立证据。Laya 已知存在 BoolQ 训练任务家族重合，结果应保留这一限定。

### 5. SST5：五级情感与有序评分

**来源与任务。** SST5 是 Stanford Sentiment Treebank 的五分类情感任务；我们使用 `SetFit/sst5` 镜像。答案从非常负面到非常正面，共五级。

**我们如何使用。** 从 2,210 条 test 数据中固定抽取 1,000 条，分别作为 `sst5` 的 `score` 任务和 `sst5_choice` 的类别选择任务。评分索引为 0–4，共 2,000 次决策。

**与决策模型的关系。** 可测试评价等级、满意度一类的有序输出。“完全选对等级”和“只偏差一级”不是一回事，因此还报告 MAE（平均绝对误差）和相差不超过一级的比例。这里评价文本情感，并没有验证真实用户满意度。

### 6. XNLI：英文与中文的语义推断

**来源与任务。** 原始项目见 [facebookresearch/XNLI](https://github.com/facebookresearch/XNLI)，下载入口为 `facebook/xnli`。给定前提和假设，判断二者是蕴含、中立还是矛盾；“中立”表示前提不足以确定假设真伪。

**我们如何使用。** 从每种语言的 5,010 条 test 数据中取对齐的 1,000 条英文和 1,000 条中文，套件为 `xnli_en`、`xnli_zh`。两种语言对应同一批原始题目。

**与决策模型的关系。** 适合检查证据支持判断、否定关系理解和中英文表现差异。中文部分属于翻译评测，不能代表全部中文原生业务场景；两种语言也不能当作两个独立来源。中文输入不等于全中文提示，本轮问题指令主要仍是英文。

### 7. MASSIVE Intent：多语言助手意图路由

**来源与任务。** 原始数据为 Amazon MASSIVE 多语言助手数据，我们使用 MTEB 提供的 `amazon_massive_intent` 意图分类版本。这里只评价 **60 类意图识别**，不评价原始数据中的所有任务，例如槽位抽取。

**我们如何使用。** 英文和简体中文 test 各有 2,974 条，我们按对齐 ID 选择各 1,000 条，套件为 `massive_en`、`massive_zh`。完整候选表保留 60 类，尽管测试集中实际只出现 59 类。候选名称取自 train 的标签列表，**没有使用训练文本进行训练或提示示范**。英文另有 100 条顺序对照。

**与决策模型的关系。** 很适合测试助手将用户指令路由到正确功能的能力，以及同一任务在中英文中的差异。它不评价功能调用参数、执行效果或多轮对话完成率。

### 8. deepset prompt-injections：一种特定政策下的注入判断

**来源与任务。** 使用 `deepset/prompt-injections`，判断输入是合法请求还是提示注入。整数标签映射经同一发布者的分类器配置核对：`0 = LEGIT`，`1 = INJECTION`。

**我们如何使用。** 使用全部 116 条 test 数据，套件名为 `prompt_injections`，转换成是否注入的二元问题。

**与决策模型的关系。** 可以作为输入守卫的探索性测试，但数据发布者对“合法请求”的定义很窄，主要限于问题和关键词搜索，一些普通角色扮演或指令也可能被标为注入。因此它的分数主要表示**对该数据集标注政策的符合程度**，不能直接等同于通用攻击检出率。标注人员背景未充分确认，数据卡还存在许可证描述冲突，详见[来源审查](DATASET_REVIEW.md)。

### 9. LocalLLaMA typed-decisions：共享状态、多问题的工作流判断

**来源与任务。** 使用 Hugging Face 的 `LocalLLaMA/typed-decisions`。这里的 LocalLLaMA 是数据发布命名空间，与我们作为对照运行的 Llama 模型是不同概念。

**我们如何使用。** 全部 400 个 test 状态包含四种工作流，各 100 个：智能体运行轨迹监控、客户服务、发票处理、安全事件。每个状态回答 5 个问题，共 2,000 次决策，套件名为 `typed_decisions`。例如运行轨迹监控会涉及是否继续、是否需要人工审查、执行结果、风险和紧迫性。

**与决策模型的关系。** 任务形式很接近 Jev/Laya：同一份结构化状态，同时输出类别、布尔值和等级。但参考答案来自合成／教师模型，并非独立核验的真实业务最优动作。高分表示更符合教师参考，不能直接称为真实业务决策准确率。

### 10. CLINC150/OOS：识别意图，也识别“超出服务范围”

**来源与任务。** 原始项目见 [clinc/oos-eval](https://github.com/clinc/oos-eval/)，我们下载 `clinc/clinc_oos`。除 150 个已知意图外，还有 OOS（out of scope，超出范围）类别。

**我们如何使用。** 使用 `plus/test` 全部 5,500 条：4,500 条范围内请求和 1,000 条 OOS。候选列表包含完整的 151 类，套件名为 `clinc150_oos`。

**与决策模型的关系。** 这比单纯分类更接近实际路由：系统需要识别自己不支持的请求。不过这里是**显式给出 OOS 选项的分类**，没有训练置信度阈值来实现自动拒答。报告应同时看范围内准确率，以及 OOS 的精确率、召回率、F1 和 AUROC；只看总准确率会掩盖“乱拒绝”或“不会拒绝”的问题。

### 11. JevBench：原生类型决策的公开题集

**来源与任务。** 使用 GitHub 的 `fstandhartinger/jevbench`。它提供原生 `choice`、`noul`、`score` 等决策问题，形式上与类型化决策模型直接匹配。

**我们如何使用。** 使用公开题集的 original 72 条、easy 48 条、hard 111 条，共 231 条，分别形成 `jevbench_original`、`jevbench_easy`、`jevbench_hard`。original 中 36 条符合条件的选择题另做顺序对照。

**与决策模型的关系。** 适合观察不同类型问题的判断表现，但 original/easy 主要是编写和审阅题，hard 为 AI 编写并经跨模型审阅，不能一概视为独立人工验证的事实真值。本轮也没有复现其私有题集或完整的路由／裁判榜单。其 10 道精确概率题在本框架中按提供的最高概率标签计分，未复现上游的概率推理专用评分，故不能将我们的准确率与该项上游分数直接比较。

### 12. ReflexBench：产品工作流回归用例

**来源与任务。** 使用 `brida-ai/reflexbench` 的 `reflex-public-choice-v1`，共 95 个公开选择题用例。此类用例适合检查产品更新后是否仍作出预期选择。

**我们如何使用。** 套件名为 `reflexbench_reflex-public-choice-v1`，以语义答案字段 `expected` 为参考，不把策略分支字段 `expectedBranch` 当答案。全部 95 条也用于同序和倒序对照。

**与决策模型的关系。** 工作流贴合度较高，但这是公开的开发／回归用例，不是严格隔离的未知测试集。上游另有 110 条父级用例，本轮没有将它们再次算成独立证据。

### 13. Jev–Laya benchmark：八类直接面向决策接口的任务

**来源与任务。** 使用第三方 GitHub 项目 `harrymunro/jev-laya-benchmark`，保留其任务问题定义，将参考答案与模型输入分开。全部 1,470 条输入产生 3,386 次决策。

| 套件 | 输入及要做的判断 | 状态数 | 决策数 |
|---|---|---:|---:|
| `jev_laya_triage` | 客服消息：六类意图、是否紧急、四级挫败情绪 | 167 | 501 |
| `jev_laya_moderation` | 论坛帖子：是否有毒、是否针对具体个人骚扰、四级违规严重性 | 142 | 426 |
| `jev_laya_routing` | 用户请求：六类领域、四级难度、是否需要实时或私有信息／工具 | 137 | 411 |
| `jev_laya_claims` | 文章与主张：支持／矛盾／未提及，以及是否支持的二元判断 | 150 | 300 |
| `jev_laya_reviews` | 商品评论：五星等级、是否推荐 | 150 | 300 |
| `jev_laya_guard` | 用户提示：是否注入／越狱、遵从请求可能产生的四级危害 | 146 | 292 |
| `jev_laya_multilingual` | 非英文客服消息：六类意图、是否紧急 | 128 | 256 |
| `jev_laya_needle` | 长篇备注：客户要求什么处理结果、是否提到商品损坏 | 450 | 900 |

**与决策模型的关系。** 这是本轮最贴近工单分流、审核和请求路由接口的一组任务。多语言部分涵盖西班牙语、法语、德语、葡萄牙语、意大利语、日语和中文，但这 128 条不是同一批题目的七语平行翻译，不能直接做逐题语言对比。

**参考答案的限制。** 工作流题由 GPT 生成，再由同一模型进行不显示原答案的复标；部分分类分歧被过滤，有序评分分歧仍保留，因此“复标”不等于独立人工确认。`needle` 的目标答案由程序构造，450 条包含同一事实在不同长度、位置下的相关变体；统计置信区间按原始 needle 分组。它检查长文中的信息提取，不代表复杂长文推理的全部能力。

### 14. TurtleBench 适配版：根据故事真相判断猜测

**来源与任务。** 我们实际下载的是 `spoonnotfound/decision-model-bench` 中的 `tasks/data/turtlebench-en.jsonl`，即 TurtleBench 的决策模型适配版；不把这个适配仓库的作者直接当作原始 TurtleBench 作者。

**我们如何使用。** 使用 32 个故事的全部 1,532 条英文猜测。模型获得故事表面描述、故事真相和玩家猜测，将猜测分为 Correct（被支持）、Incorrect（被否定）、Unknown（信息不足），套件名为 `turtlebench`。此外报告把 Incorrect 与 Unknown 合并的二分类指标。

**与决策模型的关系。** 可测试依据上下文确认事实、反驳错误及识别证据不足，形式类似“海龟汤”主持人核验玩家猜测。提供故事真相是任务需要的上下文，目标是判断猜测，不能仅因输入含真相就认定泄漏目标标签。同一故事下的问题相关，置信区间按故事分组。我们使用自己的三分类适配提示与合并指标，没有执行原始评测器，不能宣称完全复现原榜单。

### 15. Aegis2：人工标注的提示内容安全

**来源与任务。** 使用 NVIDIA 的 `Aegis-AI-Content-Safety-Dataset-2.0`，相关命名也包括 Nemotron Content Safety V2。它包含提示与回复等安全标注；本轮只测**用户提示本身**。

**我们如何使用。** 排除 test 中 36 条被遮蔽为 `REDACTED` 的输入后，使用 1,928 条具有人类提示标注的样本，套件为 `aegis2_prompt`。问题中列出 21 类安全分类名称，要求判断是否 unsafe；协议将 Safe／Needs Caution 视为非 unsafe，本次保留测试行的实际标签为 safe 或 unsafe。

**与决策模型的关系。** 对输入安全审核有直接参考价值，且提示标签比纯教师合成标签更有人工依据。但我们没有评价回复安全；回复标签混有人类与 LLM 来源，不能将本轮全部称为人工回复审核测试。此适配也没有逐字复现完整标注手册或官方安全模型。

**已发现的数据问题。** 测试数据有 13 条超出首次出现的重复行，其中一组相同提示存在冲突标签。我们保留官方行并按相同提示分组统计，同时报告保留首次出现的去重敏感性分析。test 与 validation 还共享 9 条提示，本轮没有用 validation 拟合或调阈值；未来如果使用它调参，需要先排除重合。

## 为什么 15 个来源会变成 36 个套件？

主测试拆分如下，套件名称及数量均可在[冻结清单](../protocol_manifest.json)中核对：

| 拆分 | 套件数 |
|---|---:|
| AG News、Emotion、Banking77、prompt-injections、typed-decisions，各 1 个 | 5 |
| BoolQ 和 SST5，各 2 种输出接口 | 4 |
| XNLI 和 MASSIVE，各英文／中文 2 个版本 | 4 |
| JevBench original／easy／hard | 3 |
| ReflexBench | 1 |
| Jev–Laya 的 8 个任务 | 8 |
| CLINC、TurtleBench、Aegis2，各 1 个 | 3 |
| **主测试合计** | **28** |

另有四组**选项顺序稳定性对照**。每组分别进行同序重复和真实选项倒序，增加 8 个套件：

| 主套件 | 同序重复 | 选项倒序 |
|---|---:|---:|
| Banking77 | 100 | 100 |
| MASSIVE 英文 | 100 | 100 |
| JevBench original 的选择题 | 36 | 36 |
| ReflexBench public choice | 95 | 95 |
| **决策数合计** | **331** | **331** |

同序重复用于观察运行波动；倒序用于观察答案是否受候选排列影响，语义答案和参考标签保持不变。Llama/Qwen 的倒序还会重新分配候选答案编码。这是一种排列诊断，没有穷举所有排列。“答案一致率”衡量稳定性，“准确率”衡量是否符合参考，两者需要分开看。

最终每个模型共 **22,934 次逻辑状态请求、26,450 次决策**，其中主测试为 25,788 次决策，顺序对照为 662 次。请求数包括重复接口和对照请求，不能读作独立样本数；逻辑请求数也不等于各后端内部前向计算的次数。

## 若关注实际决策能力，建议怎样看这些数据？

| 你关心的问题 | 优先参考的任务 | 还需要留意 |
|---|---|---|
| 用户请求应该路由到哪里？ | Banking77、MASSIVE、CLINC、Jev–Laya routing | 是否保留完整候选表；OOS 能否正确识别 |
| 同一状态下能否完成多种业务判断？ | typed-decisions、Jev–Laya、JevBench、ReflexBench | 合成／编写标签的一致性不等于真实最优动作 |
| 中文表现是否可靠？ | 对齐的 XNLI、MASSIVE 中英文；Jev–Laya 多语言补充 | 翻译数据、指令语言，以及样本是否可逐题对齐 |
| 能否依据材料判断支持与否？ | BoolQ、XNLI、Jev–Laya claims、TurtleBench | 信息不足与事实矛盾应区分 |
| 能否做输入安全守卫？ | Aegis2、Jev–Laya guard、prompt-injections | 各数据的安全／注入定义不同，应分别解读 |
| 是否遗漏长文本里的关键事实？ | Jev–Laya needle | 长度、事实位置及变体之间的相关性 |
| 换个选项顺序是否就改答案？ | 8 个顺序对照套件 | 结合重复运行比较；稳定不等于正确 |

AG News、Emotion、SST5 更适合作为基础语义和评分能力的补充。没有单一数据集能覆盖所有“决策”：若要证明业务价值，还需具体领域的独立人工标注、实际动作后果或交互环境评测。

所有公开集都存在潜在训练重合风险；本轮没有完成训练集去污染认证。Llama/Qwen 的对照采用固定的零样本、受限下一 token 答案选择，Qwen 关闭 thinking，故成绩也不是其经过提示优化或长推理后的最佳能力，详见[对照协议](LLM_BASELINES.md)。

## 数据是怎样找到、检查和固定的？

来源是 GitHub 项目的 README、数据文件、生成器，以及 Hugging Face 的数据卡、元信息和实际数据文件。我们检查了候选答案是否完整、标签映射是否正确、模型输入是否混入参考答案、重复项与相关样本、使用的 split、上下文长度及数据条款。样本选择在新模型推理前冻结，不按模型得分筛题。

标准数据固定随机种子 `20260927`，无放回抽取 1,000 条；小数据集或新增集合按上述规则使用全量。原始文本从上游下载，本仓库不打包再发布这些样本文本；发布评测代码、来源定位和实测输出，以便重新下载和复算。

并非搜索到的每个 “decision benchmark” 都采用。例如：

- `AbdelStark/jev-benchmarks` 中的 AG News／Emotion／Banking 切片与已有来源重叠，没有作为新的独立数据加入。
- BTZSC 的 Banking77 转换版只有 72 个候选，且存在没有正确候选的题组；其中 `label_text` 会暴露目标标签。因此使用完整 77 类的原始任务来源。
- 部分项目把“比较两个给定答案”称为排列测试，或者用人为随机指定的答案评估信息不足的情境。这些不能直接当作真实决策准确率依据。

更完整的纳入、排除与条款说明见[英文数据适用性审查](DATASET_REVIEW.md)。下载版本不是依赖随时变化的网页最新版：精确 revision、文件路径和 SHA256 已固定在[原有数据来源表](../sources.json)与[新增数据来源表](../external_sources.json)中。

## 核对入口

- [中文实测结果](RESULTS.zh-CN.md)：四个模型的实际成绩与统计结果。
- [冻结评测协议](../PROTOCOL.md)：抽样、输入、计分与对照规则。
- [机器可读套件清单](../protocol_manifest.json)：每个套件的请求数、决策数、来源与语言。
- [数据适用性审查](DATASET_REVIEW.md)：来源质量、纳入／排除依据、许可证证据。
- [数据适配代码](../system1bench/prepare.py)与[Jev–Laya 任务定义](../system1bench/jev_laya_tasks.py)：输入哪些字段、模型具体回答什么问题。
- [来源与条款说明](../NOTICE.md)：数据、模型和外部代码的来源声明。

本文是对已冻结协议和已有结果的中文说明，没有引入新测试样本或修改任何评测分数。
