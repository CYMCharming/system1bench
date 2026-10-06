const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const repo='https://github.com/CYMCharming/system1bench/blob/main/';
export function reviewMarkup(review){
 if(!review)return '<p>审核记录暂未加载。可在 GitHub 查看 research/dataset_audit_v1。</p>';
 const notes=[
 ['政策任务','标签经规则重算一致。原始案例各自唯一，但反转请求有 11 组碰撞；配对结果不能视为完全独立干预。'],
 ['ContractNLI','144 条来自官方测试集，涉及 91 份合同。按文档分组；StartLux 声明用过该数据来源，不能据此声称未见来源泛化。'],
 ['SciFact','339 条涉及 300 个主张、283 份文档。130 条“未提供证据”由标注缺失构造，不是逐篇人工重新判定。新增主张与文档交叉重采样敏感性分析，历史区间保持原样。'],
 ['CLadder','144 条的来源、标签和请求绑定一致；本次没有重新推导全部因果图答案。'],
 ['CRUXEval','128 条候选答案识别题，不是原始生成任务的 pass@1。本适配的逐题均匀随机基线为 36.39%；本次未重新执行全部程序。'],
 ['FinEntity','128 条来自完整语料，给定实体位置后判断情绪，不是实体抽取或独立测试划分。独立再分发许可尚未核实，不公开原始文本。'],
 ['When2Call','128 条来自官方测试集。测的是工具决策选择，不是完整工具执行；该来源没有 direct 类正例，不能计算该类召回率。'],
 ['已知概率诊断','96 条由 48 个设置及其选项换序组成。参考概率已独立重算；这是合成诊断，不代表现实答案置信度的校准。']
 ];
 return `<div class="audit-heading"><h3>数据审核 · ${esc(review.date)}</h3><a href="${repo}research/dataset_audit_v1/existing_findings.md" target="_blank" rel="noopener">完整审核记录 ↗</a></div><p>已核对来源版本、文件指纹、请求与标签绑定、重复和适配范围。未完成逐题语义人工复核，也不能证明模型预训练未接触过这些数据。原成绩未被改写。</p><div class="audit-notes">${notes.map(([name,note])=>`<details><summary>${name}</summary><p>${note}</p></details>`).join('')}</div><h3>新增数据 · 已冻结，尚未计分</h3><div class="admission-grid">${review.datasets.map(d=>`<article><h4>${esc(d.label)}</h4><p>${d.full.toLocaleString()} 条官方测试样本 · ${d.classes} 个选项</p><p>排除规范化重复与训练／验证重叠后的辅助切片：${d.clean.toLocaleString()} 条；预先固定的试跑：${d.pilot} 条。</p><small>${esc(d.license)} · 无成绩，不进入排行榜</small></article>`).join('')}</div><p>保留全部 151／77 个选项，不使用按正确答案挑选的少量候选。当前采用固定标签顺序，尚未做换序实验。CLINC 试跑的域外请求占 25%，不等同于完整测试集比例。StartLux 和 InnerJev 声明训练中使用过这些来源；其他模型的训练接触情况未知。</p><a href="${repo}research/public_expansion_v1/README.zh-CN.md" target="_blank" rel="noopener">来源、排除记录与冻结协议 ↗</a><h3>待评测模型 · 不混入已有成绩</h3><div class="table-scroll"><table><thead><tr><th>模型</th><th>权重版本</th><th>许可</th><th>状态</th></tr></thead><tbody>${review.models.map(m=>`<tr><td><a href="https://huggingface.co/${esc(m.repo)}/tree/${esc(m.revision)}" target="_blank" rel="noopener">${esc(m.label)}</a></td><td><code>${esc(m.revision?.slice(0,12))}</code></td><td>${esc(m.license)}</td><td>未完成评测</td></tr>`).join('')}</tbody></table></div><p>Kev-9B v2 作为新版本单列，不覆盖原 Kev-9B。Clef 使用原生联合决策头，需先验证接口；27B 权重暂受服务器磁盘容量限制。</p><h3>暂不纳入的数据</h3><p>WildJailBreak 的上游与再打包许可不一致；ToolACE 的部分所谓测试样本来自训练集；JEVal 混合不同划分且许可未统一核实。先解决这些问题，再决定是否入榜。</p><details><summary>审核数据指纹</summary>${review.sources.map(s=>`<p><a href="${repo+esc(s.path)}" target="_blank" rel="noopener">${esc(s.path)}</a><br><code class="audit-hash">SHA-256 ${esc(s.sha256)}</code></p>`).join('')}</details>`;
}
