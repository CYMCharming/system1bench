# System1Bench：Compass 风格论文插图

设计参考：T2AV-Compass 的 [arXiv v3 首页 Figure 1](https://arxiv.org/pdf/2512.21094v3#page=1) 及[作者项目页](https://nju-link.github.io/T2AV-Compass/)。借鉴五种图形结构、低饱和配色和分层信息组织；图形重新绘制，没有复制原论文像素、标志、数值或文字。

## 五张图的对应关系

| 原子图 | 我们的图 | 数据和边界 |
|---|---|---|
| a：放射状模型比较 | 八领域决策能力图 | 6 个代表模型、48 个真实领域分数；相同 0–100 标尺。17 个完整模型的精确值另附 CSV。 |
| b：文本 token 长度分布 | 决策请求长度分布 | 9,879 条原始请求；统一 Qwen3.8 tokenizer；完整候选集、目标问题头、无 gold 的紧凑 JSON。不表示任一模型的原生计费/时延。 |
| c：视频提示语义多样性 | 问题文本语义多样性 | 六个任务各取 128 个固定哈希样本，MiniLM 编码，0.80 相似度贪心去重。横线是 0.75–0.85 阈值敏感性，不是置信区间。 |
| d：音频提示语义多样性 | 正确答案类别均衡度 | 同六任务，使用完整冻结评测样本的语义标签；归一化熵 H/log(K)。这不是语义多样性，也不是模型准确率。 |
| e：分层评测维度 | 决策评测分类环图 | 分类任务与稳健性、概率质量、效率分开；角度只编码叶子指标数量，不编码样本占比或综合分权重。 |

原论文 c/d 是音视频两种模态的多样性。System1Bench 没有对应模态，因此保留条形图视觉结构，但独立定义两个有证据的统计量，不搬用原指标名。

## 阅读限制

- 六个放射图代表模型为 Kev-27B v2、Jev 1.13.0 API、Qwen3.8-27B、Kev-9B、Qwen3.5-9B、Llama-3.1-8B：覆盖两组相近规模比较、托管模型与常用 Llama 基线。没有把 17 条曲线挤进一张图；完整 17 模型结果在 `domain_scores.csv`。这不是受控架构或训练史实验。
- 11 分类任务的原始请求数为 9,879。CLINC/BANKING 是完整官方测试；其余是实际使用的历史冻结子集。重复、反转、其它干预和概率实验不重复计入这张语料统计图。
- **问题多样性不等于整个数据集多样性。** ContractNLI 使用有限数量的假设模板配上不同合同；c 不包含合同证据，低问题保留率不能支持“该数据集单一/低质量”的结论。六个任务的问题字段也各有语义：意图取 user_query，科学取 claim，合同取 hypothesis，因果取 question，工具取 user_question。
- MiniLM 是英文通用编码器，查询保留率依赖编码器、字段、抽样和阈值；不是任务难度或无污染证据。不同阈值的计数全部留存。每个任务的抽样仅用于统计，不改任何模型评测集。
- 选项编号在迁移任务里会逐题打乱。d 必须统计 `gold_class` 等语义类别，不能统计 option_0/option_1 的频率。When2Call 四个候选中只有三个有 gold 样本，分母仍使用 log(4)。CRUXEval 的候选输出随题变化，不作统一类别熵比较。
- 放射图和综合榜是点估计；没有新综合分置信区间，也不声称差异有统计显著性。托管 Jev 的 8 次失败依冻结协议计错。
- 分类以外的指标来自项目已有专项评测，各专项覆盖模型和任务数不同。环图不暗示所有 23 个模型的所有诊断实验都齐全。

## 文件与复现

- 成图：`paper/figures/compass_v1/`，每图都有可编辑 SVG、嵌入字体的 PDF、360 dpi PNG。
- `overview_five_panels`：两行组合排版，避免照搬原布局后导致中间两幅条形图难以阅读。
- `System1Bench_Compass_Figures.pdf`：6 页图集，第一页组合图，随后五张独立图。
- `paper/compass_figures.tex`：可直接插入正文的 LaTeX 图注；未替换现有正文图。
- `corpus_statistics.json`：仅统计值、长度、标签计数、模型/源文件哈希，不包含原始输入文本或访问凭据。
- `figure_manifest.json`：数据和输出文件哈希、代表模型名单、参考来源、转换规则。
- `query_similarity.npz`：六个任务各 128 个统计查询之间的相似度矩阵，无原始文本；验证脚本独立回放三个阈值的全部去重计数。

统计在 gpu29 的现有 model-expansion Python 环境运行，CPU 4 线程，无新决策模型推理：

```text
python research/paper_compass_v1/collect.py --root /mnt/sata2/cym/system1bench --output research/paper_compass_v1/corpus_statistics.json
```

统计依赖远端已有原始冻结输入和 Qwen3.8 tokenizer。MiniLM 权重只在项目私有缓存下载，固定到统计文件记录的官方版本；每个完整查询按 254 wordpiece 分块、attention-mask mean pooling、按片段长度汇总并归一化，没有截断。

本地图可从已附统计数据重新生成，无需联网、GPU 或原始文本：

```text
python research/paper_compass_v1/figures.py
python research/paper_compass_v1/verify.py
```

数据可追溯性与标签语义核查按照数据可视化技能执行；最终 PDF 另作渲染检查。
