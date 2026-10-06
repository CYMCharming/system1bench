# 开源决策模型与候选任务：来源审查

审查日期：2026-10-06。本文记录候选选择及原始来源，不把厂商成绩当成我们的成绩。完整固定版本见 [official_sources.json](official_sources.json)，接入状态见 [candidates.json](candidates.json)。原始记录去重、分割重叠、冻结请求和测试由本目录的独立接入审计记录负责；本次来源核查不等于逐条人工重标。

## 本轮优先加入哪些任务

| 数据集 | 官方测试集 | 决策问题 | 许可 | 本轮定位 |
| --- | ---: | --- | --- | --- |
| CLINC150+OOS | 5,500：4,500 范围内、1,000 范围外 | 请求不属于任何已支持业务时，模型能否识别，而不是硬选一个相似业务 | CC-BY-3.0 | 冻结完整 151 类官方测试集；报告范围外召回及范围内误拒率 |
| BANKING77 | 3,080，77 类 | 相近的银行客服意图能否正确区分 | CC-BY-4.0 | 冻结完整 77 类官方测试集；报告宏平均 F1 及每类召回 |

两者可直接从[CLINC 官方数据](https://github.com/clinc/oos-eval/tree/828f8093932c8fe6ca7936c3d2e52903b1c523de/data)和[BANKING77 官方 CSV](https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data)重建，不依赖厂商二次分割。候选全集不根据答案筛选，选项编号与答案脱钩。与现有三个小规模规则任务相比，它们增加了细粒度意图区分和业务范围外识别；与 FinEntity 的给定实体跨度情绪分类不是同一能力。

**不能把新数据集一概称为模型没见过的数据。** StartLux 已声明使用两者的训练分割；InnerJev-4B 的训练资料也列有 BANKING77 768 题和 CLINC150 905 题。这不证明测试泄漏，但要在这些模型的相应成绩旁保留“同源训练已披露”。Jev 和 Clef 没有在已读资料中公布完整来源清单，不能据此称其未见过。[StartLux 固定声明](https://github.com/StartLuxLabs/StartLux-Decision/blob/0e7a2e81b9c92756e26d8edd843a44d50e362669/README.md)、[InnerJev 固定训练卡](https://huggingface.co/datasets/jylin001206/InnerJev-4B-Training-Data/blob/b689deecf7b8b2f6001e5f0ef9779069be1b4bc7/README.md)。

## 核查三个已有项目后，哪些任务暂不照搬

- **Kev breadth-v1**：有跨推理、语言、检索、工具及偏好的 14 个来源，但不应整包转载。清单说明部分来源不能公开再分发或许可未明确；其私有镜像不赋予我们转载权。CLINC 可以单独从原始许可来源重建。其 BFCL 改编只预测选哪些函数，不生成参数，不能标为完整函数调用能力。[固定来源清单](https://github.com/jaredpalmer/kev/blob/5e42a7a03f28134853dd3ff77461457e921e5ec1/evals/breadth-v1/manifest.json)。
- **Intern / StartLux 的 ToolACE test**：310 条来自公开的 ToolACE 训练集。内部文件名叫 test 并不使它成为官方留出测试；可作已暴露诊断，不加入独立泛化主榜。[StartLux 说明](https://github.com/StartLuxLabs/StartLux-Decision/blob/0e7a2e81b9c92756e26d8edd843a44d50e362669/README.md)。
- **WildJailBreak**：有价值的安全分类候选，但 Intern 清单的 Apache-2.0 与原始发布者当前 ODC-BY 及访问条款不一致。应取得原始数据访问权、核对原始标签后接入，不通过厂商副本绕过门槛。其 harmful/benign 分类也不是实际越狱成功率。[原始发布者](https://huggingface.co/datasets/allenai/wildjailbreak)。
- **公共 Jevbench 和 96 题概率 pilot**：前者是公开开发诊断，不含完整官方榜的密封集、速度、费用；后者实际是 48 组配对设置。两者都不能被包装为大型独立确认测试。[Intern 复现指南](https://github.com/InternLM/Intern-Decision/blob/3572c8a68b5df5dafe02d0e093989ba8ec0183bc/docs/EVALUATION.md)。
- **JEVal**：可以提供双语与领域补充线索，但 release 的 test 集合包含上游 train/dev/test，且明确没有统一授权。需逐来源审核、与现有样本去重后再决定接入，不能把整个集合叫作统一留出集。[固定数据卡](https://huggingface.co/datasets/carlosxiang/JEVal/blob/5f623cfd03c3f13fbec566a99d76dad10cb9dd98/README.md)。

## 模型候选顺序

1. **Clef-flash 9B**：优先。Cloudflare 在 2026-10-01 正式发布，原始 BF16 权重及原生联合问题头公开、Apache-2.0、无访问门槛。它提供现有 pointer / 首 token 读出之外的联合 schema head 对照，适合研究多问题干扰。固定 revision `17f0b0ad64efb65d273590632833508766b2aae6`；必须使用官方 `systemone`，先审核自定义代码和适配语义。[官方模型卡](https://huggingface.co/Cloudflare/clef-flash/blob/17f0b0ad64efb65d273590632833508766b2aae6/README.md)。
2. **Kev-9B v2**：作为独立新版本补充，不覆盖当前 Kev-9B 历史行。版本 2 在 2026-09-30 发布，增加文档、技能及开发工具训练，校准也改变。固定原始权重 revision `b5d8c18e44c60888d138b65cb6507ff0a5a448a0`；当前 v1.0 的元数据提交不同，版本名不代替权重哈希。[固定 v2 卡](https://github.com/jaredpalmer/kev/blob/5e42a7a03f28134853dd3ff77461457e921e5ec1/docs/model-cards/kev-9b.md)。
3. **Clef 27B / InnerJev-4B-Full / StartLux-2B**：分别补充大模型联合读出、自推理蒸馏以及小模型规模对照。InnerJev 4B 有完整 BF16 权重；默认 27B 的 4090 启动脚本会量化，不能用它满足“原模型非量化”的比较要求。StartLux-2B 为现有家族缺失规模，模型权重仍受 CC-BY-NC-4.0 约束。[Clef](https://huggingface.co/Cloudflare/clef/blob/2f3de3dd85f379784083b0814d997ab627200f0c/README.md)、[InnerJev](https://huggingface.co/jylin001206/InnerJev-4B-Full/blob/a8d77e5a3cebfc92feeae93821efa6a22739c9e8/README.md)、[StartLux-2B](https://huggingface.co/startlux-models/StartLux-Decision-2B/tree/3e2e456409a7fe44be69eee231566f7830872ea2)。

SecJev 和 Jeff 可作领域专门化对照，但暂不优先并入通用主榜。SecJev 的代码、适配和数据使用自定义协议及各上游条件；其遥测来源标签和输入显式策略任务不是生产攻击检测率。Jeff 已有 SciFact 相关评测暴露，需要先核对我们科学任务的重叠。[SecJev 协议](https://github.com/UESTC1010/SecJev/blob/24d96fd8e8759db61147a689776619ea2f668498/LICENSE)、[Jeff 官方说明](https://github.com/Gestalt-Lab/jeff/tree/14ee67e2814a19ebd0a67f508ac1b0f424ba1ebc)。这些新项目不能仅因 README 宣称领先就被称为有广泛影响力。

## 能提出哪些新问题

- 相似类别很多时，模型是准确分辨，还是仅在少数候选中看起来准确？固定完整 77 / 151 类空间，避免“已知正确答案后构造候选”的捷径。
- 范围外请求能否可靠交给人工？同时看漏识别范围外请求和误拒正常请求；高总体准确率不能掩盖其中一项。
- 同源任务成绩与跨来源成绩的差距有多大？公开标注训练来源，不把这种差异直接解释成架构优劣。
- 同一个 state 同时问更多问题，联合 schema head 是否更稳定？新 Clef 与已有 Kev / Intern / StartLux 使用相同请求和硬件协议后，才能判断实际速度、分数及干扰权衡。

上述问题是实验设计动机，不是已经测得的结论。新候选模型尚无我们测量的分数；网站应显示待适配或待评测，不能填入厂商数字。
