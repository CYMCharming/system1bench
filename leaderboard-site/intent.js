const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>typeof v==='number'&&Number.isFinite(v)?(v*100).toFixed(2)+'%':'—';
const decimal=v=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(4):'—';
const repo='https://github.com/CYMCharming/system1bench/blob/main/research/public_intent_pilot_v1/';
const kind=id=>/^(qwen|llama)/.test(id)?'general':['english','multilingual'].includes(id)?'representation':'decision';
function pilotMarkup(data,{metric='intent_accuracy',family='all',search=''}={}){
 if(!data?.models)return '<p class="intent-empty">意图识别结果暂未加载。原排行榜不受影响。</p>';
 const entries=Object.entries(data.models).filter(([id,m])=>(family==='all'||family===kind(id))&&m.label.toLowerCase().includes(search.toLowerCase()));
 if(!entries.length)return '<p class="intent-empty">没有匹配的已完成模型，请修改搜索或重置筛选。</p>';
 const field=metric==='intent_macro_f1'?'macro_f1':'accuracy';
 const metricName=field==='accuracy'?'准确率':'宏平均 F1';
 const full=data.official_full_test===true,clinc=full?'clinc150_full':'clinc150_pilot',bank=full?'banking77_full':'banking77_pilot';
 const charts=[[clinc,'CLINC150 + OOS',full?5500:200,151],[bank,'BANKING77',full?3080:154,77]].map(([suite,name,n,classes])=>{
  const sorted=[...entries].sort((a,b)=>b[1].metrics[suite][field]-a[1].metrics[suite][field]||a[1].label.localeCompare(b[1].label));
  return `<section class="intent-chart" aria-label="${name} ${metricName}"><div class="intent-chart-head"><div><span class="section-kicker">${classes} WAY · PILOT</span><h3>${name}</h3></div><span>${n} 条 · ${metricName}</span></div><div class="intent-axis"><span>0</span><span>25</span><span>50</span><span>75</span><span>100%</span></div>${sorted.map(([id,m])=>{const value=m.metrics[suite];return `<div class="intent-row ${kind(id)}" data-intent-model="${esc(id)}"><div class="intent-model"><strong>${esc(m.label)}</strong><span>${field==='accuracy'?`${value.correct} / ${value.n} 条正确`:`${classes} 类等权 · ${value.n} 条`}</span></div><div class="intent-bar" role="img" aria-label="${esc(m.label)} ${metricName} ${pct(value[field])}"><svg viewBox="0 0 1000 24" preserveAspectRatio="none" aria-hidden="true" width="100%" height="24"><rect x="0" y="0" width="${value[field]*1000}" height="24" class="intent-bar-fill" data-score="${value[field]}"/></svg></div><strong class="intent-value">${pct(value[field])}</strong></div>`}).join('')}<p>固定完整候选集合；宏 F1 让每个类别权重相同，准确率让每条样本权重相同。</p></section>`;
 }).join('');
 const breakdown=entries.map(([id,m])=>{const c=m.metrics[clinc];return `<tr class="${kind(id)}"><td>${esc(m.label)}</td><td>${pct(c.known_correct/c.known_n)}<small>${c.known_correct} / ${c.known_n}</small></td><td>${pct(c.oos_recall)}<small>${c.oos_correct} / ${c.oos_n}</small></td><td>${pct(c.false_oos/c.known_n)}<small>${c.false_oos} / ${c.known_n} · 越低越好</small></td></tr>`}).join('');
 const domains=data.models[entries[0][0]].metrics[clinc].domains;
 const domainNames={banking:'银行',credit_cards:'信用卡',kitchen_and_dining:'餐饮',home:'家居',auto_and_commute:'车辆与通勤',travel:'出行',work:'工作',small_talk:'日常交流',meta:'助手设置',utility:'实用功能',out_of_scope:'域外请求'};
 const domainRows=domains.map(d=>`<tr><td>${esc(domainNames[d.domain]??d.domain)}</td>${entries.map(([,m])=>{const cell=m.metrics[clinc].domains.find(x=>x.domain===d.domain);return `<td>${pct(cell.correct/cell.n)}<small>${cell.correct} / ${cell.n}</small></td>`}).join('')}</tr>`).join('');
 const probabilities=entries.map(([,m])=>[clinc,bank].map(suite=>{const c=m.metrics[suite];return `<tr><td>${esc(m.label)}</td><td>${suite.startsWith('clinc')?'CLINC':'BANKING'}</td><td>${decimal(c.brier)}</td><td>${c.zero_gold_probability?'∞（真值概率为零）':decimal(c.nll)}</td><td>${c.probability_n} / ${c.n}</td></tr>`}).join('')).join('');
 return `<div class="intent-status"><span>独立试跑</span><p>仅限固定的 200 / 154 条；未加入原综合分，不是完整官方测试成绩。</p><a href="/intent-pilot.json" download>下载聚合数据 ↓</a></div><div class="intent-grid">${charts}</div><section class="intent-section"><div class="intent-chart-head"><h3>已知意图与域外请求</h3><span>CLINC · 同一批请求</span></div><div class="table-scroll"><table><thead><tr><th>模型</th><th>已知意图准确率</th><th>域外请求召回率</th><th>已知请求误拒绝率</th></tr></thead><tbody>${breakdown}</tbody></table></div></section><details class="intent-section"><summary>CLINC 分领域结果 · 每个已知领域 15 条</summary><div class="table-scroll"><table><thead><tr><th>领域</th>${entries.map(([,m])=>`<th>${esc(m.label)}</th>`).join('')}</tr></thead><tbody>${domainRows}</tbody></table></div></details><details class="intent-section"><summary>概率误差与输出完整性</summary><div class="table-scroll"><table><thead><tr><th>模型</th><th>任务</th><th>Brier ↓</th><th>NLL ↓</th><th>有效输出 / 全部请求</th></tr></thead><tbody>${probabilities}</tbody></table></div><p>候选概率的口径不同，不直接解释为已校准的正确性置信度。多分类 Brier 范围为 0–2，不跨任务混排。准确率始终保留失败请求；这里另列概率指标的有效分母。</p></details><div class="intent-notes"><p>每个已知意图仅 1 条、每个银行意图仅 2 条；CLINC 试跑域外比例 25%，完整测试为 18.18%。这是诊断性比较，不提供未建立的泛化置信区间。Qwen 关闭思考、使用候选代码读出，Kev 使用原生指针头；差异不是架构因果证据。</p><a href="${repo}README.zh-CN.md" target="_blank" rel="noopener">方法、配对结果与适用范围 ↗</a> · <a href="${repo}prediction_projection.json" target="_blank" rel="noopener">逐题预测与概率 ↗</a></div>`;
}
export function intentMarkup(data,options={}){
 let html=pilotMarkup(data,options);
 if(data?.official_full_test){
  html=html.replaceAll('WAY · PILOT','WAY · OFFICIAL TEST')
   .replace('<span>独立试跑</span>','<span>官方完整测试</span>')
   .replace('仅限固定的 200 / 154 条；未加入原综合分，不是完整官方测试成绩。','完整 5,500 / 3,080 条；准确率计入新版综合榜，保留全部候选和失败请求分母。')
   .replace('/intent-pilot.json','/catalog.json')
   .replace('CLINC 分领域结果 · 每个已知领域 15 条','CLINC 分领域结果 · 每个已知领域 450 条')
   .replace('每个已知意图仅 1 条、每个银行意图仅 2 条；CLINC 试跑域外比例 25%，完整测试为 18.18%。这是诊断性比较，不提供未建立的泛化置信区间。Qwen 关闭思考、使用候选代码读出，Kev 使用原生指针头；差异不是架构因果证据。','CLINC 每个已知意图 30 条、域外请求 1,000 条（18.18%）；BANKING 每类 40 条。采用固定完整候选，不是减选项版本。官方测试存在已披露的训练／测试精确重合，未知预训练接触不能当作干净。不同原生读出方式的差异不是架构因果证据。')
   .replace(repo+'README.zh-CN.md','https://github.com/CYMCharming/system1bench/blob/main/research/evaluation_completion_v1/PROTOCOL.md')
   .replace(repo+'prediction_projection.json','https://github.com/CYMCharming/system1bench/tree/main/research/evaluation_completion_v1/projections');
 }
 const {family='all',search=''}=options;
 const limits=(data?.capability_limits??[]).filter(m=>(family==='all'||family===kind(m.id))&&m.label.toLowerCase().includes(search.toLowerCase()));
 const table=limits.length?`<section class="intent-section"><h3>原生接口不支持 · 不记零分</h3><div class="table-scroll"><table><thead><tr><th>模型</th><th>当前接口上限</th><th>本任务候选数</th><th>状态</th></tr></thead><tbody>${limits.map(m=>`<tr><td>${esc(m.label)}</td><td>${m.limit} 个选项 / 答案符号</td><td>151 / 77</td><td>输入被官方接口拒绝</td></tr>`).join('')}</tbody></table></div><p>对应固定版本的原生单请求接口，不等于模型无法判断这些意图。层级分类、多次调用或改写接口须另列协议和成绩。</p></section>`:'';
 const nano=!data?.official_full_test&&(family==='all'||family==='decision')&&data?.models?.nanojev&&data.models.nanojev.label.toLowerCase().includes(search.toLowerCase())?`<p class="intent-notes">NanoJev 在此试跑的输出高度集中：CLINC 的 200 条中有 187 条选择同一标签。已核查全部输入长度与候选完整性，另有 <a href="${repo}nano_native_replay.json" target="_blank" rel="noopener">6 条直接官方复算</a>与记录一致。这不是全量重跑；低分的具体原因仍需实验，不据此推断整个架构的能力。</p>`:'';
 return html+table+nano;
}
