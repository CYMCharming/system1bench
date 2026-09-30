# 新增模型：身份、评测覆盖与复现

## 当前实际覆盖

本轮新增 Kev-0.8B、Kev-4B、Kev-9B、NanoJev、Qwen3.5-9B，已实测三个参考轨道：明确规则的退款 / 权限 / 工单分流、ContractNLI 法律推断、SciFact 引用摘要证据。首轮每模型 4,905 个决策，总计 24,525；Kev-4B/9B 另在新政策状态各复测 3,456 个，合计新增 31,437 个，均完整输入、零输出错误。

这五个模型**尚未**跑完历史 15 来源 / 36 套件全矩阵。原始全矩阵的五个历史系统与新模型扩展分开发布。旧五系统各 4,905 个同 payload 对照保留逐来源收据，不算新推断，不混做速度比较。

| 本地模型 ID | 官方检查点 | 固定 revision | 本轮推断 |
|---|---|---|---|
| `kev_08b` | [jaredpalmer/kev-0.8b](https://huggingface.co/jaredpalmer/kev-0.8b) | `9a45d25eb2ab761841196625383fa1dff0e56c1e` | 原生指针头，合并 BF16 / SDPA，发行温度 |
| `kev_4b` | [jaredpalmer/kev-4b](https://huggingface.co/jaredpalmer/kev-4b) | `139fdd94f1b6a6ad80cc15e08fcb99cac885a101` | 同上 |
| `kev_9b` | [jaredpalmer/kev-9b](https://huggingface.co/jaredpalmer/kev-9b) | `2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c` | 同上 |
| `nanojev` | [C-Tianyu/NanoJev](https://huggingface.co/C-Tianyu/NanoJev) | `047b927b30882a1138fc504821b82ac145a4b81a` | 统一游戏版，官方候选路径，FP32 存储 / BF16 autocast，温度 1 |
| `qwen35_9b` | [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | 后训练版、文本输入、思考关闭、单步候选代码概率 |

不是把 Kev-9B 的 Base 当作 Qwen3.5-9B 对照，也不是使用名字相似的第三方 Nano 模型。Kev 三个 Base 仓库和完整 revision 在 [manifest](../research/model_expansion_v1/manifest.json)。不同 Kev 版本训练历史不同，不构成受控参数规模实验。NanoJev 是游戏专项训练，跨领域结果不能替代游戏测评。

所有模型的上下文上限设为 32768，不截断、不缩短状态 / 指令 / 选项。NanoJev 默认训练上限的覆盖检查逐样本保存，超上限情况不悄悄删除。未使用发行模型的跨请求前缀缓存、置换集成、日期增强、融合或 CUDA Graph；这不是最高吞吐配置。测得秒数仅是遥测，不可用于速度排行榜。

## 不下载模型也能核验公开结果

在仓库根目录、Python ≥3.11 环境运行：

```bash
pip install -e .
python research/model_expansion_v1/verify.py --check-only --public-only
python research/model_expansion_replication_v1/verify.py --check-only --public-only
```

公开重放检查原始输出哈希、模型 / 推断源码版本、唯一案例、概率、重复 token、各类整数指标和配对差异。它没有重新读取未发布的自然数据正文。`verification.json` 是远程拥有完整授权输入时的核验收据；`--check-only` 不把它改写成较弱的公开核验结果。

统计 / 图表需要 `pip install -e '.[paper]'`。图表脚本从已核验结果生成 PDF、SVG、PNG，数值与绘图源码摘要另存于 `figure_data.json`；不是生图模型绘出的数据图。

## 重跑推断：先重建输入，再准备固定版本

1. 按来源许可获取既有准备脚本要求的数据，恢复 `research/confirmation_v1/frozen.json`、`research/domain_expansion_v1/frozen.json`、`research/scifact3_census_v1/frozen.json`。入口分别为 `research/confirmation.py`、`research/domain_expansion_v1/prepare.py`、`research/scifact3_census_v1/prepare.py`。阅读各自方案 / DATA_LICENSES；必须和已登记的来源哈希相同。受来源许可限制的冻结正文不随 Git 发布。
2. 使用隔离环境安装 `pip install -e '.[decision,paper]'`；不要在同一环境同时选旧 `llm` extra 的 transformers 5.16.1 和新的 `decision` 5.17.0。实际测量环境完整版本、GPU 和权重摘要在每模型的 `metadata.json`，包括 torch 2.7.1+cu118 的二进制变体。需要有足够显存的 CUDA GPU；参考内核回退不等于最高性能实现。
3. 从官方仓库取得上述固定 revision，Kev 还必须取得其固定 Base。官方推断源码分别使用 [jaredpalmer/kev](https://github.com/jaredpalmer/kev) commit `0fe8fc97c2bcc247fa3efb6e5c32af4e99770e91` 和 [TianyuCodings/NanoJev](https://github.com/TianyuCodings/NanoJev) commit `76fdfc9ecdca45a9bcef17991a07d3041a87685a`。把 Kev 包目录置于 `.aris/vendor/kev/`，NanoJev scripts 内容置于 `.aris/vendor/nanojev-scripts/`；非本仓库代码不冒充原创。Kev 官方加载器按 checkpoint 元数据的 Base/revision 从 HF 缓存读取，需要正确缓存对应短 revision 引用。
4. 在私有 `.aris/model_expansion_paths.json` 配置五个 ID，内容从公开 `manifest.json` 的 `model_pins` 复制，加上各自绝对 `path`；Kev 再加 `base_path`。不存 API 密钥，不改公开版本身份。NanoJev `path` 是含 `best.safetensors`、`config.json`、`tokenizer/`、`backbone_config/` 的 checkpoint 根目录。
5. 原始输出目录是不可变测量记录，不要覆盖或删除来‘重跑’。使用独立仓库副本保留协议 / manifest，留空新副本的结果目录，重新核对哈希；推断脚本若发现签名不匹配会拒绝续跑。

在准备好的独立测量副本中：

```bash
python research/model_expansion_v1/freeze.py
python research/model_expansion_v1/run.py --model kev_4b --audit-only
python research/model_expansion_v1/run.py --model kev_4b
# 对其余四个 ID 重复；不要把 audit-only / limit 的 smoke 输出当作正式评测。
python research/model_expansion_v1/analyze.py
python research/model_expansion_v1/verify.py
python research/model_expansion_replication_v1/freeze.py
python research/model_expansion_replication_v1/run.py --model kev_4b
python research/model_expansion_replication_v1/run.py --model kev_9b
python research/model_expansion_replication_v1/analyze.py
python research/model_expansion_replication_v1/verify.py
python research/model_expansion_v1/figures.py
```

统一 runner 也新增了 `system1bench.native_bridge:ExpandedDecisionAdapter`：将一批状态逐请求运行，某一个超长输入不会使同批其他状态全部作废，预算变更会清掉旧编码缓存。这个桥接入口与原始扩展测量 runner 不是同一次测量；单元测试验证接口，而本轮正式结果来自上述固定 `run.py`。

```bash
python benchmarks/run_frozen.py --model kev_4b \
  --adapter system1bench.native_bridge:ExpandedDecisionAdapter \
  --frozen research/model_expansion_v1/frozen.json \
  --manifest research/model_expansion_v1/manifest.json \
  --batch-size 1 --output results/new-independent-run
```

注意：此入口保留标准 runner 对 `noul` / `score` 的输出和评分语义，而扩展研究的 `summary.json` 用候选分布 argmax 做严格标签比较，不能不说明指标就直接拼接两份结果。

## 尚需的论文证据

当前结果足以提出“该坚持 / 该改判”的双轴评测问题，还不够确认内部机制、全部领域泛化或自动部署收益。优先补独立人工审阅的自然配对数据、新的规则语法、Qwen3.5 生成 / 思考强基线、明确业务约束的多输出审计；历史全来源矩阵与受控性能轨道应另开固定方案，不把不同上下文预算或吞吐实现混入本轮。
