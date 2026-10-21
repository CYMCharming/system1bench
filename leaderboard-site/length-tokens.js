// Token-length diagnostics use reviewed paired statistics, never new inference.
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const num=v=>finite(v)?v.toFixed(2):'—';
const signed=v=>finite(v)?`${Math.abs(v)<.005?'':v>0?'+':''}${(Math.abs(v)<.005?0:v).toFixed(2)}`:'—';
const pct=v=>finite(v)?`${(v*100).toFixed(2)}%`:'—';
const count=v=>Number.isInteger(v)?v.toLocaleString('en-US'):'—';
const ciText=ci=>Array.isArray(ci)&&ci.length===2&&ci.every(finite)?`[${signed(ci[0])}, ${signed(ci[1])}]`:'—';
const colors={decision:'#176745',general:'#6267c5',representation:'#a07532'};
const families={decision:'S1 · 决策专用模型',general:'传统通用大模型',representation:'表示模型 · 单列参考'};
const familyOf=(id,m)=>m.family??(/^(qwen|llama)/.test(id)?'general':['english','multilingual'].includes(id)?'representation':'decision');
const scopeOf=(m,task)=>task==='variable'?m?.variable:task==='all'?m?.overall:m?.tasks?.[task];
const cohortOf=(entry,task)=>task==='variable'?entry?.cohorts?.variable:task==='all'?entry?.cohorts?.overall:entry?.cohorts?.tasks?.[task];
export function tokenLengthRows(data,{family='all',search='',task='variable',mode='all',tokenizer='qwen3'}={}){
 return Object.entries(data?.tokenizers?.[tokenizer]?.models??{}).map(([id,m])=>({id,m,family:familyOf(id,m),s:scopeOf(m,task)?.[mode]}))
  .filter(r=>(family==='all'||r.family===family)&&String(r.m.label??r.id).toLowerCase().includes(search.toLowerCase()))
  .sort((a,b)=>Object.keys(families).indexOf(a.family)-Object.keys(families).indexOf(b.family));
}
function extent(values){
 const max=Math.max(0,...values.filter(finite).map(Math.abs));if(!max)return 1;
 const power=10**Math.floor(Math.log10(max)),scaled=max/power;
 return (scaled<=1?1:scaled<=2?2:scaled<=5?5:10)*power;
}
const axis=(domain,unit='')=>`<div class="token-axis-ticks">${[-domain,-domain/2,0,domain/2,domain].map(v=>`<span>${Math.abs(v)<1e-9?'0':signed(v)}${unit}</span>`).join('')}</div>`;
function forest(value,ci,{domain=100,family='decision',gold=null,baseline=null,tip=''}){
 const x=v=>10+(v+domain)/(2*domain)*980;
 const grid=[-domain,-domain/2,0,domain/2,domain].map(v=>`<line x1="${x(v)}" x2="${x(v)}" y1="0" y2="36" class="${v===0?'token-zero':'token-grid'}"/>`).join('');
 const interval=Array.isArray(ci)&&ci.length===2&&ci.every(finite)?`<line x1="${x(ci[0])}" x2="${x(ci[1])}" y1="18" y2="18" class="token-ci"/><line x1="${x(ci[0])}" x2="${x(ci[0])}" y1="12" y2="24" class="token-ci"/><line x1="${x(ci[1])}" x2="${x(ci[1])}" y1="12" y2="24" class="token-ci"/>`:'';
 const point=finite(value)?`<g tabindex="0" role="img" aria-label="${esc(tip)}" data-length-tip="${esc(tip)}"><rect x="${x(value)-14}" y="6" width="28" height="24" fill="transparent" pointer-events="all"/><line x1="${x(value)}" x2="${x(value)+.01}" y1="18" y2="18" stroke="${colors[family]}" stroke-width="9" stroke-linecap="round" vector-effect="non-scaling-stroke"/>${family==='general'?`<line x1="${x(value)}" x2="${x(value)+.01}" y1="18" y2="18" stroke="white" stroke-width="4" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`:''}</g>`:'';
 const reference=finite(gold)?`<path d="M ${x(gold)} 1 L ${x(gold)-8} 7 L ${x(gold)+8} 7 Z" fill="#4b5b51"/>`:'';
 const chance=finite(baseline)&&Math.abs(baseline)>1e-8?`<line x1="${x(baseline)}" x2="${x(baseline)}" y1="29" y2="36" stroke="#354b3d" stroke-width="2" vector-effect="non-scaling-stroke"/>`:'';
 return `<svg viewBox="0 0 1000 36" preserveAspectRatio="none" role="group" aria-label="${esc(tip)}">${grid}${interval}${reference}${chance}${point}</svg>`;
}
function statsTip(row,mode){
 const s=row.s,a=s?.absolute;
 return `${row.m.label??row.id} · n=${count(s?.n)} · 绝对超额 ${signed(a?.excess)} 参考 token（95% ${ciText(a?.excess_ci95)}） · 选中/机会/真值均长 ${num(a?.chosen_mean)}/${num(a?.baseline_mean)}/${num(a?.gold_mean)} · token长度位置分 ${signed(s?.score)}（95% ${ciText(s?.ci95)}） · 正确答案 ${signed(s?.gold_score)} · ${mode==='errors'?'错项':'全选项'}随机基线 ${signed(s?.baseline_score)} · 相对基线配对差 ${signed(s?.relative_excess?.score)}（95% ${ciText(s?.relative_excess?.ci95)}）`;
}
function overview(rows,{absoluteDomain,mode}){
 const x=(v,d)=>10+(v+d)/(2*d)*980;
 const groupRows=Object.entries(families).map(([family,title])=>{
  const current=rows.filter(r=>r.family===family);if(!current.length)return '';
  const strip=kind=>{
   const domain=kind==='absolute'?absoluteDomain:100;
   const grid=[-domain,0,domain].map(v=>`<line x1="${x(v,domain)}" x2="${x(v,domain)}" y1="2" y2="59" class="${v===0?'token-zero':'token-grid'}"/>`).join('');
   const dots=current.map((row,i)=>{const v=kind==='absolute'?row.s?.absolute?.excess:row.s?.score;if(!finite(v))return '';const xx=x(v,domain),y=16+i%3*15,tip=statsTip(row,mode);return `<g tabindex="0" role="img" data-length-tip="${esc(tip)}" aria-label="${esc(tip)}"><rect x="${xx-13}" y="${y-10}" width="26" height="20" fill="transparent" pointer-events="all"/><line x1="${xx}" x2="${xx+.01}" y1="${y}" y2="${y}" stroke="${colors[family]}" stroke-width="8" stroke-linecap="round" vector-effect="non-scaling-stroke"/>${family==='general'?`<line x1="${xx}" x2="${xx+.01}" y1="${y}" y2="${y}" stroke="white" stroke-width="3" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`:''}</g>`;}).join('');
   return `<svg viewBox="0 0 1000 62" preserveAspectRatio="none" role="group" aria-label="${esc(title)} ${kind==='absolute'?'绝对超额token':'相对长度位置'}">${grid}${dots}</svg>`;
  };
  return `<div class="token-overview-row"><span>${esc(title)}<small>${current.length} 个模型</small></span><div>${strip('absolute')}</div><div>${strip('relative')}</div></div>`;
 }).join('');
 return `<div class="length-overview token-overview"><div class="token-overview-heading"><strong>S1 与传统大模型 · 同屏对照</strong><span>每个点是一个模型，纵向错开不代表数值</span></div><div class="token-overview-row token-overview-axis"><span></span><div><b>绝对超额 · 参考 token</b>${axis(absoluteDomain)}</div><div><b>相对长度位置分</b>${axis(100)}</div></div>${groupRows}<div class="length-readout" aria-live="polite">悬停或聚焦模型点，查看两种指标、区间和样本数。这里没有计算家族均值。</div></div>`;
}
function forestPanel(rows,allRows,{mode}){
 const values=allRows.flatMap(r=>[r.s?.absolute?.excess,...(r.s?.absolute?.excess_ci95??[]),finite(r.s?.absolute?.gold_mean)&&finite(r.s?.absolute?.baseline_mean)?r.s.absolute.gold_mean-r.s.absolute.baseline_mean:null]);
 const absoluteDomain=extent(values);
 const groups=Object.entries(families).map(([family,title])=>{
  const current=rows.filter(r=>r.family===family);if(!current.length)return '';
  return `<div class="token-family"><h4 class="length-family-title ${family}">${esc(title)}<small>${current.length} 个模型</small></h4>${current.map(row=>{
   const s=row.s,a=s?.absolute,tip=statsTip(row,mode),sensitive=a?.excess_sign_robust_to_one_group===false;
   const gold=finite(a?.gold_mean)&&finite(a?.baseline_mean)?a.gold_mean-a.baseline_mean:null;
   return `<div class="token-model-row" data-token-length-row="${esc(row.id)}"><div class="token-model"><strong>${esc(row.m.label??row.id)}</strong><small>${count(s?.n)} 道有效题${sensitive?' · <em>均值对单组敏感</em>':''}</small></div><div class="token-forest-cell" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><span class="token-mobile-label">绝对超额 · 参考 token</span><div class="token-forest-score"><strong>${signed(a?.excess)}</strong><small>95% ${ciText(a?.excess_ci95)}</small></div><div class="token-track">${forest(a?.excess,a?.excess_ci95,{domain:absoluteDomain,family,gold,tip})}</div><div class="token-means">选中 ${num(a?.chosen_mean)} <span>机会 ${num(a?.baseline_mean)} · 真值 ${num(a?.gold_mean)}</span></div></div><div class="token-forest-cell" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><span class="token-mobile-label">相对长度位置分</span><div class="token-forest-score"><strong>${signed(s?.score)}</strong><small>95% ${ciText(s?.ci95)}</small></div><div class="token-track">${forest(s?.score,s?.ci95,{family,gold:s?.gold_score,baseline:s?.baseline_score,tip})}</div><div class="token-means">真值 ${signed(s?.gold_score)} <span>随机基线 ${signed(s?.baseline_score)}</span></div></div></div>`;
  }).join('')}</div>`;
 }).join('');
 return `<section class="length-panel token-panel" id="token-length-forests"><div class="length-panel-head"><div><h3>选中选项：绝对长度与同题相对位置</h3><p>负数偏短，正数偏长，不代表好坏。绝对超额保留 token 差距；相对位置只看长短排名。</p></div><span>点与横线：估计值及 95% 区间</span></div>${overview(rows,{absoluteDomain,mode})}<div class="token-legend"><span><i class="length-glyph"></i>S1</span><span><i class="length-glyph general"></i>传统大模型</span><span><i class="length-glyph representation"></i>表示模型</span><span>▲ 正确答案参照</span>${mode==='errors'?'<span>黑色短线：随机错项基线</span>':''}</div><div class="token-forest-header"><span>模型 · 相同题目范围</span><div><strong>绝对超额 · 参考 token</strong><p>选中长度 − 同题随机机会均长</p>${axis(absoluteDomain)}</div><div><strong>相对长度位置分</strong><p>最短 −100 · 最长 +100</p>${axis(100)}</div></div>${groups}<div class="length-readout" aria-live="polite">聚焦一个点或一列，查看完整数值。两张图的题目与分母一致。</div><p class="length-note">均值可能受极长选项影响；请查看下方“剔除单个来源组”对照。相对分也受题目内容与正确答案长度分布影响，不能据此证明长度造成选择。${mode==='errors'?' 各模型答错的题不同；raw 相对分区间并不是“超过随机错项基线”的检验，配对差见精确表。只有一个错项或错项等长时，绝对超额为 0 也不能证明没有偏好。':''}</p></section>`;
}
function ratioColor(value){
 if(!finite(value))return '#f1f3f1';
 const root=value>=1?[43,82,112]:[161,120,54],base=[248,248,244],t=.5*Math.min(1,Math.abs(Math.log2(Math.max(value,1e-12)))/2);
 return '#'+base.map((v,i)=>Math.round(v+(root[i]-v)*t).toString(16).padStart(2,'0')).join('');
}
function binPanel(rows,data,{mode}){
 const bins=data.bins??[];
 return `<section class="length-panel token-panel" id="token-length-bins"><div class="length-panel-head"><div><h3>哪些绝对 token 长度区间更常被选中？</h3><p>选择率 ÷ 机会率：1× 与随机机会相当，大于 1× 更常被选，小于 1× 更少被选。</p></div><span>按当前同题范围计算</span></div><div class="token-table-scroll"><table class="token-bin-matrix"><thead><tr><th>模型</th>${bins.map(b=>`<th>${esc(b.label)}<small>参考 token</small></th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><th scope="row">${esc(row.m.label??row.id)}<small>n = ${count(row.s?.absolute?.n)}</small></th>${bins.map(bin=>{const b=row.s?.absolute?.bins?.find(x=>x.id===bin.id),ratio=b?.ratio,tip=`${row.m.label??row.id} · ${bin.label} 参考 token · ${finite(ratio)?num(ratio)+'×':'无可用机会比'} · 选中 ${count(b?.chosen_count)} / ${count(b?.n)}（${pct(b?.rate)}） · ${mode==='errors'?'随机错项':'随机选项'}机会 ${pct(b?.chance)} · 期望次数 ${num(b?.expected_count)}`;return `<td><div data-token-bin="${esc(bin.id)}" class="token-bin-cell ${finite(ratio)&&(ratio>=2||ratio<=.5)?'strong':''}" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><svg viewBox="0 0 100 45" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="45" rx="3" fill="${ratioColor(ratio)}"/></svg><strong>${finite(ratio)?num(ratio)+'×':'—'}</strong><small>${count(b?.chosen_count)} / ${count(b?.n)}</small></div></td>`;}).join('')}</tr>`).join('')}</tbody></table></div><div class="token-bin-legend"><span>更少选</span>${[.25,.5,1,2,4].map(v=>`<span><svg viewBox="0 0 20 12" aria-hidden="true"><rect width="20" height="12" fill="${ratioColor(v)}"/></svg>${v}×</span>`).join('')}<span>更多选</span></div><div class="length-readout" aria-live="polite">机会率逐题按候选集合计算，不直接比较各区间的原始选择次数。聚焦单元格查看选择率、机会率及精确分母。</div><p class="length-note">颜色在 0.25×–4× 截断，标出的数值不截断。机会率为 0 或无有效作答时显示 —，不是零偏好。错误模式的机会只含错误候选；此比值不是准确率，也没有在这里建立区间。</p></section>`;
}
function sensitivityTables(rows,data,{mode,task,tokenizer}){
 const matching=rows.map(row=>{const s=row.s,a=s?.absolute;return `<tr><td>${esc(row.m.label??row.id)}<small>n = ${count(s?.n)}</small></td><td>${signed(s?.character?.score)}<small>95% ${ciText(s?.character?.ci95)}</small></td><td>${signed(s?.score)}<small>95% ${ciText(s?.ci95)}</small></td><td>${signed(s?.rank_delta?.score)}<small>95% ${ciText(s?.rank_delta?.ci95)}</small></td><td>${signed(s?.relative_excess?.score)}<small>95% ${ciText(s?.relative_excess?.ci95)}</small></td><td>${num(a?.excess_median)}</td><td>${ciText(a?.leave_one_group_out_range)}<small>${a?.excess_sign_robust_to_one_group===false?'均值方向对单个来源组敏感':a?.excess_sign_robust_to_one_group===true?'剔除单组后方向不变':'—'}</small></td></tr>`;}).join('');
 const allValid=rows.map(row=>{const a=scopeOf(row.m.absolute_all_valid,task)?.[mode];return `<tr><td>${esc(row.m.label??row.id)}</td><td>${count(a?.n)}<small>含 ${count(a?.equal_length_included)} 道等 token 长度题</small></td><td>${num(a?.chosen_mean)}</td><td>${num(a?.baseline_mean)}</td><td>${num(a?.gold_mean)}</td><td>${signed(a?.excess)}<small>95% ${ciText(a?.excess_ci95)}</small></td><td>${count(a?.excess_identifiable_n)}<small>候选无差异 ${count(a?.baseline_degenerate_n)}</small></td></tr>`;}).join('');
 const reference=data.reference_sensitivity,refs=Object.keys(reference?.tokenizers??{});
 const references=refs.length>1?`<details class="length-details token-details"><summary>不同参考分词器：同一题集上的对照</summary><p class="length-note">独立的逐题变化描述任务交集，共 ${count(reference.n)} 道；不随上方任务范围筛选变化。错误模式仍使用各模型自己的错误子集。此表未建立区间，不把两套参考各自不同的分母混作分词差异。</p><div class="token-table-scroll"><table><thead><tr><th>模型</th>${refs.map(id=>`<th>${esc(id)} · 绝对超额 / 相对分</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(row.m.label??row.id)}</td>${refs.map(id=>{const s=reference.tokenizers[id]?.[row.id]?.[mode];return `<td>${signed(s?.absolute?.excess)} token / ${signed(s?.score)}<small>n = ${count(s?.n)}</small></td>`;}).join('')}</tr>`).join('')}</tbody></table></div></details>`:'';
 return `<details class="length-details token-details"><summary>字符 vs token：同题对照、配对差及极长选项敏感性</summary><p class="length-note">字符与 token 分数使用完全相同的题目。token − 字符的区间对逐题差值配对计算；“相对基线配对差”另与同题随机 all／wrong 候选基线比较。剔除单个来源组范围是敏感性范围，不是置信区间。</p><div class="token-table-scroll"><table><thead><tr><th>模型</th><th>字符相对分</th><th>token 相对分</th><th>token − 字符</th><th>相对基线配对差</th><th>绝对超额中位数</th><th>剔除单个来源组后的绝对均值范围</th></tr></thead><tbody>${matching}</tbody></table></div></details><details class="length-details token-details"><summary>绝对长度完整对照：保留等长题，不混入上方主图</summary><p class="length-note">使用当前任务范围中全部 23 模型有效输出的题；保留字符或 token 等长题，因此分母可能大于主图。${mode==='errors'?'“候选无差异”包括仅一个错误候选或所有错误候选等长，这些题的超额 0 没有可识别的长度选择。':''}</p><div class="token-table-scroll"><table><thead><tr><th>模型</th><th>有效题数</th><th>选中均长</th><th>机会均长</th><th>真值均长</th><th>绝对超额 / 95% 区间</th><th>可区分长度的比较数</th></tr></thead><tbody>${allValid}</tbody></table></div></details>${references}`;
}
export function tokenLengthMarkup(data,{family='all',search='',task='variable',mode='all',tokenizer='qwen3'}={}){
 const entry=data?.tokenizers?.[tokenizer];
 if(!entry?.models)return '<div class="length-page token-length-page"><p class="length-empty">Token 长度分析暂未加载，字符分析与排行榜不受影响。</p></div>';
 const options={family,search,task,mode,tokenizer},rows=tokenLengthRows(data,options),allRows=tokenLengthRows(data,{task,mode,tokenizer}),cohort=cohortOf(entry,task),tasks=data.tasks??[],references=Object.entries(data.tokenizers??{});
 const referenceName=entry.metadata?.label??entry.metadata?.repo??tokenizer;
 const control=`<div class="length-controls token-controls"><label class="length-control">主图范围 <select data-length-task aria-label="Token 分析主图范围"><option value="variable" ${task==='variable'?'selected':''}>逐题变化的描述 · 2 项任务</option><option value="all" ${task==='all'?'selected':''}>全部原始任务 · 9 项</option>${tasks.map(t=>`<option value="${esc(t.id)}" ${task===t.id?'selected':''}>${esc(t.label??t.id)}</option>`).join('')}</select></label>${references.length>1?`<label class="length-control">参考分词器 <select data-length-tokenizer aria-label="参考分词器">${references.map(([id,r])=>`<option value="${esc(id)}" ${id===tokenizer?'selected':''}>${esc(r.metadata?.label??r.metadata?.repo??id)}</option>`).join('')}</select></label>`:''}<div class="length-modes" role="group" aria-label="Token 分析作答范围"><button data-length-mode="all" aria-pressed="${mode==='all'}">全部有效作答</button><button data-length-mode="errors" aria-pressed="${mode==='errors'}">仅错误作答</button></div></div>`;
 const scope=task==='variable'?'CRUXEval + When2Call':task==='all'?'9 项原始任务':tasks.find(t=>t.id===task)?.label??task;
 const note=`<p class="token-reference"><strong>参考 token，不是各模型原生 token。</strong>${esc(referenceName)}；同一选项文本统一分词，不运行模型。</p><p class="length-scope"><strong>${esc(scope)}</strong> · 23 模型共同有效、字符与 token 长度均可比较的 ${count(cohort?.n)} 道题${mode==='errors'?'中，各模型各取自己的错误子集':''}。${count(cohort?.source_n)} 道原题，排除 ${count(cohort?.unavailable_excluded)} 道缺有效输出、${count(cohort?.either_equal_excluded)} 道至少一种量尺全等的题。</p>`;
 const content=rows.length?`${forestPanel(rows,allRows,{mode})}${binPanel(rows,data,{mode})}${sensitivityTables(rows,data,{mode,task,tokenizer})}`:'<p class="length-empty">没有匹配的模型，请修改搜索或模型类型筛选。</p>';
 const referencePin=entry.metadata?.repo?`<p class="token-reference-pin">参考文件：${esc(entry.metadata.repo)}${entry.metadata.revision?' · '+esc(String(entry.metadata.revision).slice(0,12)):''}。完整版本与文件校验值见协议。</p>`:'';
 return `<div class="length-page token-length-page">${control}${note}${content}<div class="length-sources"><a href="/length-tokens.json" download>Token 分析数据 · JSON</a><a href="/length-token-scores.csv" download>Token 精确分数 · CSV</a><a href="https://github.com/CYMCharming/system1bench/tree/main/research/option_length_tokens_v1" target="_blank" rel="noopener">协议与复现结果 ↗</a></div>${referencePin}<p class="length-methods">这里检验已有作答与描述长度的相关性，不是“把同一选项改长”的因果实验。通用大模型直接选择答案代码，未使用思维链；不外推至所有推理模式。固定语义标签、训练接触与任务构成仍会影响比较，不以模型家族平均值推断架构效应。</p></div>`;
}
