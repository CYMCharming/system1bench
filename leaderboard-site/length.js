// Reviewed, observational option-length diagnostics for the existing static site.
// No inference, aggregation, confidence bounds or fallback scores are made here.
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const number=v=>finite(v)?v.toFixed(2):'—';
const signed=v=>finite(v)?`${Math.abs(v)<.005?'':v>0?'+':''}${(Math.abs(v)<.005?0:v).toFixed(2)}`:'—';
const percent=v=>finite(v)?`${(v*100).toFixed(2)}%`:'—';
const count=v=>Number.isInteger(v)?v.toLocaleString('en-US'):'—';
const COLORS={decision:'#176745',general:'#6267c5',representation:'#a07532'};
const FAMILIES={decision:'S1 · 决策专用模型',general:'传统通用大模型',representation:'表示模型 · 单列参考'};
const familyOf=(id,m)=>m.family??(/^(qwen|llama)/.test(id)?'general':['english','multilingual'].includes(id)?'representation':'decision');
const scopeOf=(m,task)=>task==='variable'?m.variable:task==='all'?m.overall:m.tasks?.[task];
const statsOf=(m,task,mode)=>scopeOf(m,task)?.[mode];
const taskList=data=>Array.isArray(data.tasks)?data.tasks:[];
const ciText=s=>Array.isArray(s?.ci95)&&s.ci95.length===2?`95% 区间 [${signed(s.ci95[0])}, ${signed(s.ci95[1])}]`:'未提供区间';
const ciShort=s=>Array.isArray(s?.ci95)&&s.ci95.length===2?`${signed(s.ci95[0])} 至 ${signed(s.ci95[1])}`:'区间未建立';

export function lengthRows(data,{family='all',search='',task='variable',mode='all'}={}){
 return Object.entries(data?.models??{}).map(([id,m])=>({id,m,family:familyOf(id,m),s:statsOf(m,task,mode)}))
  .filter(r=>(family==='all'||r.family===family)&&String(r.m.label??r.id).toLowerCase().includes(search.toLowerCase()));
}

function dotSvg(s,family){
 const x=v=>8+(v+100)/200*984;
 const grid=[-100,-50,0,50,100].map(v=>`<line x1="${x(v)}" x2="${x(v)}" y1="0" y2="34" class="${v===0?'length-zero':'length-grid'}"/>`).join('');
 if(!finite(s?.score))return `<svg viewBox="0 0 1000 34" preserveAspectRatio="none" aria-hidden="true">${grid}</svg>`;
 const color=COLORS[family]??COLORS.decision;
 const ci=Array.isArray(s.ci95)&&s.ci95.every(finite)?`<line x1="${x(s.ci95[0])}" x2="${x(s.ci95[1])}" y1="17" y2="17" class="length-ci"/><line x1="${x(s.ci95[0])}" x2="${x(s.ci95[0])}" y1="12" y2="22" class="length-ci"/><line x1="${x(s.ci95[1])}" x2="${x(s.ci95[1])}" y1="12" y2="22" class="length-ci"/>`:'';
 // Round-capped non-scaling strokes remain circular at every viewport width.
 const point=`<line x1="${x(s.score)}" x2="${x(s.score)+.01}" y1="17" y2="17" stroke="${color}" stroke-width="10" stroke-linecap="round" vector-effect="non-scaling-stroke"/>${family==='general'?`<line x1="${x(s.score)}" x2="${x(s.score)+.01}" y1="17" y2="17" stroke="white" stroke-width="5" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`:''}`;
 const gold=finite(s.gold_score)?`<path d="M ${x(s.gold_score)} 3 L ${x(s.gold_score)-9} 9 L ${x(s.gold_score)+9} 9 Z" fill="#35443a" vector-effect="non-scaling-stroke"/>`:'';
 const baseline=finite(s.baseline_score)&&Math.abs(s.baseline_score)>1e-9?`<line x1="${x(s.baseline_score)}" x2="${x(s.baseline_score)}" y1="25" y2="32" stroke="#35443a" stroke-width="2" vector-effect="non-scaling-stroke"/>`:'';
 return `<svg viewBox="0 0 1000 34" preserveAspectRatio="none" aria-hidden="true">${grid}<line x1="8" x2="992" y1="17" y2="17" class="length-base"/>${ci}${baseline}${gold}${point}</svg>`;
}

function modelName(row,n){return `<span class="length-model-name">${esc(row.m.label??row.id)}<small>${count(n)} 道有效题</small></span>`;}
function rowTip(row,mode){
 const s=row.s;
 if(!s?.n||!finite(s.score))return `${row.m.label??row.id} · 当前范围没有可用的长度比较，不记为零。`;
 return `${row.m.label??row.id} · 长度位置分 ${signed(s.score)} · ${ciText(s)} · 正确答案 ${signed(s.gold_score)} · ${mode==='errors'?'随机选错项':'随机选项'}基线 ${signed(s.baseline_score)} · n = ${count(s.n)}${mode==='errors'?' · 各模型错误题集合不同':''}`;
}
function familyOverview(rows,mode){
 const x=v=>8+(v+100)/200*984;
 const groups=Object.entries(FAMILIES).map(([family,title])=>{
  const current=rows.filter(r=>r.family===family&&finite(r.s?.score));
  if(!current.length)return '';
  const points=current.map((row,i)=>{const y=19+(i%3)*14,xx=x(row.s.score),tip=rowTip(row,mode);return `<g class="length-overview-point" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><rect x="${xx-12}" y="${y-10}" width="24" height="20" fill="transparent" pointer-events="all"/><line x1="${xx}" x2="${xx+.01}" y1="${y}" y2="${y}" stroke="transparent" stroke-width="20" stroke-linecap="round" vector-effect="non-scaling-stroke"/><line x1="${xx}" x2="${xx+.01}" y1="${y}" y2="${y}" stroke="${COLORS[family]}" stroke-width="9" stroke-linecap="round" vector-effect="non-scaling-stroke"/>${family==='general'?`<line x1="${xx}" x2="${xx+.01}" y1="${y}" y2="${y}" stroke="white" stroke-width="4" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`:''}</g>`;}).join('');
  const grid=[-100,-50,0,50,100].map(v=>`<line x1="${x(v)}" x2="${x(v)}" y1="6" y2="60" class="${v===0?'length-zero':'length-grid'}"/>`).join('');
  return `<div class="length-overview-row"><span>${esc(title)}<small>${current.length} 个模型</small></span><span class="length-track"><svg viewBox="0 0 1000 64" preserveAspectRatio="none" aria-label="${esc(title)}模型长度位置分分布" role="group">${grid}${points}</svg></span></div>`;
 }).join('');
 const golds=rows.filter(r=>finite(r.s?.gold_score)).map(r=>r.s.gold_score);
 const gold=golds.length&&golds.every(v=>Math.abs(v-golds[0])<1e-8)?golds[0]:null;
 return `<div class="length-overview" aria-label="S1 与传统大模型同屏比较"><div class="length-overview-title"><strong>S1 与传统大模型 · 同屏对照</strong><span>每个点是一个模型，纵向错开仅为避免重叠</span></div><div class="length-overview-row length-overview-axis"><span></span><div class="length-axis-labels"><span>−100 短</span><span>−50</span><span>0</span><span>+50</span><span>+100 长</span></div></div>${groups}${finite(gold)?`<div class="length-overview-row length-overview-gold"><span>▲ 正确答案参照<small>${signed(gold)}</small></span><span class="length-track"><svg viewBox="0 0 1000 22" preserveAspectRatio="none" aria-hidden="true"><line x1="${x(gold)}" x2="${x(gold)}" y1="5" y2="17" stroke="#35443a" stroke-width="2" vector-effect="non-scaling-stroke"/></svg></span></div>`:''}<div class="length-readout" aria-live="polite">悬停或聚焦一个点：查看模型、长度分、区间和有效题数。</div><p>不是家族均值或架构效应；逐模型精确分数见下方。</p></div>`;
}
function mainPlot(rows,{mode}){
 const groups=Object.entries(FAMILIES).map(([family,title])=>{
  const current=rows.filter(r=>r.family===family).sort((a,b)=>(finite(b.s?.score)?b.s.score:-Infinity)-(finite(a.s?.score)?a.s.score:-Infinity)||String(a.m.label).localeCompare(String(b.m.label)));
  if(!current.length)return '';
  return `<div class="length-family"><h4 class="length-family-title ${family}">${title}<small>${current.length} 个模型</small></h4>${current.map(row=>{const s=row.s,tip=rowTip(row,mode);return `<div class="length-model-row ${family}" data-length-row="${esc(row.id)}" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}">${modelName(row,s?.n)}<span class="length-track">${dotSvg(s,family)}</span><span class="length-value" data-length-score="${finite(s?.score)?s.score:''}">${signed(s?.score)}<small>${ciShort(s)}</small></span></div>`;}).join('')}</div>`;
 }).join('');
 return `<section class="length-panel" id="length-choice-position"><div class="length-panel-head"><div><h3>模型选中的描述有多长</h3><p>左侧偏短，右侧偏长；不是准确率或能力排名。正确答案本身也有长短偏差。</p></div><span>固定量尺 −100 至 +100</span></div><div class="length-legend"><span><i class="length-glyph"></i>S1 决策专用</span><span><i class="length-glyph general"></i>传统大模型</span><span><i class="length-glyph representation"></i>表示模型</span><span><i class="length-ci-key"></i>95% 区间</span><span><b class="length-triangle-key">▲</b>正确答案的长度位置</span>${mode==='errors'?'<span><i class="length-chance-key"></i>随机错项基线</span>':''}</div>${familyOverview(rows,mode)}<div class="length-axis"><span>模型</span><div class="length-axis-labels"><span>−100 短</span><span>−50</span><span>0</span><span>+50</span><span>+100 长</span></div><span>长度位置分</span></div>${groups}<div class="length-readout" aria-live="polite">悬停或用 Tab 聚焦一行，查看完整数值、正确答案位置与基线。</div>${mode==='errors'?'<p class="length-note">仅错误题：各模型答错的题不同，并不是同一套“难题”，不能据此认定它“遇到难题就靠长短猜”。黑色短线是从该题错误选项中随机选择的长度基线。</p>':''}</section>`;
}

function extremesCell(row,key,mode){
 const s=row.s,v=s?.[key],title=key==='shortest'?'选最短':'选最长';
 const tip=`${row.m.label??row.id} · ${title} ${percent(v?.rate)}（${count(v?.count)} / ${count(s?.n)}） · ${mode==='errors'?'随机错项':'随机选择'}基线 ${percent(v?.chance)} · 正确答案为${key==='shortest'?'最短':'最长'} ${percent(s?.[key==='shortest'?'gold_shortest_rate':'gold_longest_rate'])} · 并列最短/最长均计入`;
 const actual=finite(v?.rate)?v.rate*1000:null,expected=finite(v?.chance)?v.chance*1000:null;
 const bars=actual===null?'':`<rect x="0" y="5" width="1000" height="7" rx="2" fill="#eef2ef"/><rect x="0" y="5" width="${actual}" height="7" rx="2" fill="${COLORS[row.family]}"/>${expected===null?'':`<line x1="${expected}" x2="${expected}" y1="1" y2="16" stroke="#253e2d" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`}`;
 return `<div class="length-extreme-cell" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><span class="length-extreme-label">${title}</span><span class="length-extreme-values"><strong>${percent(v?.rate)}</strong><small>基线 ${percent(v?.chance)}</small></span><svg viewBox="0 0 1000 17" preserveAspectRatio="none" aria-hidden="true">${bars}</svg><span class="length-count-note">${count(v?.count)} / ${count(s?.n)} · 正确答案 ${percent(s?.[key==='shortest'?'gold_shortest_rate':'gold_longest_rate'])}</span></div>`;
}
function extremesPlot(rows,{mode}){
 return `<section class="length-panel" id="length-extremes"><div class="length-panel-head"><div><h3>“选最长”与“选最短”</h3><p>实色为实际选择率，黑线为同题随机基线。每行均从 0 到 100%。</p></div><span>并列长度一并计入</span></div><div class="length-extreme-head"><span>模型</span><span>选最短 <small>0 → 100%</small></span><span>选最长 <small>0 → 100%</small></span></div>${rows.map(row=>`<div class="length-extreme-row ${row.family}">${modelName(row,row.s?.n)}${extremesCell(row,'shortest',mode)}${extremesCell(row,'longest',mode)}</div>`).join('')}<div class="length-readout" aria-live="polite">选择率高于随机基线，只说明这个题集上的选择相关性；请同时对照正确答案的长度分布。</div><p class="length-note">随机基线按每题选项数和并列情况分别计算，不一律按 25%。${mode==='errors'?'此处仅错误题的基线排除了正确选项。':''}</p></section>`;
}

function heatColor(score){
 const base=[247,247,243],target=score>=0?[35,78,105]:[156,112,45],t=Math.min(1,Math.abs(score)/100);
 return '#'+base.map((v,i)=>Math.round(v+(target[i]-v)*t).toString(16).padStart(2,'0')).join('');
}
function taskMatrix(rows,data,mode){
 const tasks=taskList(data);
 return `<section class="length-panel" id="length-by-task"><div class="length-panel-head"><div><h3>不同任务下，长短倾向是否一致</h3><p>各任务单独计算；此图保留全部任务，不受“主图范围”筛选影响。</p></div><span>${tasks.length} 项任务 · 同一量尺</span></div><div class="length-task-scroll"><table class="length-task-matrix"><thead><tr><th>模型</th>${tasks.map(t=>`<th>${esc(t.label??t.id)}${t.variable_options?'':'<br>固定描述'}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(row.m.label??row.id)}</td>${tasks.map(t=>{
  const s=row.m.tasks?.[t.id]?.[mode],value=s?.score,tip=`${row.m.label??row.id} · ${t.label??t.id} · 长度位置分 ${signed(value)} · ${ciText(s)} · n = ${count(s?.n)}${t.variable_options?'':' · 选项描述固定：长度和语义类别混杂'}`;
  return `<td><div class="length-task-cell ${finite(value)&&Math.abs(value)>60?'dark':''} ${!finite(value)?'length-missing':''}" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}">${finite(value)?`<svg viewBox="0 0 100 42" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="42" fill="${heatColor(value)}" rx="3"/></svg>`:''}<span>${signed(value)}</span></div></td>`;
 }).join('')}</tr>`).join('')}</tbody></table></div><div class="length-task-key"><span>−100 偏短</span><svg viewBox="0 0 200 10" preserveAspectRatio="none" aria-hidden="true">${Array.from({length:20},(_,i)=>`<rect x="${i*10}" width="10" height="10" fill="${heatColor(-100+i*200/19)}"/>`).join('')}</svg><span>+100 偏长</span><span>— 无可用比较，不是 0</span></div><div class="length-readout" aria-live="polite">聚焦单元格查看样本数与区间。固定描述的任务尤其不能把选项类别偏好直接当成长度偏好。</div></section>`;
}

function exactTable(rows,mode){
 return `<details class="length-details"><summary>查看精确分数、分母与“四选项选最短”</summary><div class="table-scroll"><table><thead><tr><th>模型</th><th>有效题数</th><th>长度位置分 / 95% 区间</th><th>正确答案长度分</th><th>${mode==='errors'?'随机错项':'随机选项'}基线</th><th>错误选项内调整分</th><th>四选项且最短唯一：选最短</th></tr></thead><tbody>${rows.map(({id,m,s})=>`<tr data-length-exact="${esc(id)}"><td>${esc(m.label??id)}</td><td>${count(s?.n)}<small>正确 ${count(s?.correct)}</small></td><td>${signed(s?.score)}<small>${ciShort(s)}</small></td><td>${signed(s?.gold_score)}</td><td>${signed(s?.baseline_score)}</td><td>${signed(s?.wrong_adjusted_score)}<small>可区分错项 n = ${count(s?.wrong_identifiable_n)}</small></td><td>${percent(s?.unique_shortest_four?.rate)}<small>${count(s?.unique_shortest_four?.count)} / ${count(s?.unique_shortest_four?.n)} · 基线 ${percent(s?.unique_shortest_four?.chance)}</small></td></tr>`).join('')}</tbody></table></div><p class="length-note">“错误选项内调整分”只在模型选错且错误选项之间存在长度差异时计算。它不把答错解释为无法判断，也不消除内容与长度的混杂。“四选项且最短唯一”不要求另外三个选项等长。</p></details>`;
}
function datasetTable(data){
 return `<details class="length-details"><summary>题目覆盖与长度可比较性</summary><div class="table-scroll"><table><thead><tr><th>任务</th><th>原始题数</th><th>长度不全相等的题</th><th>候选数</th><th>选项描述</th></tr></thead><tbody>${taskList(data).map(t=>`<tr><td>${esc(t.label??t.id)}</td><td>${count(t.n)}</td><td>${count(t.informative_n)}</td><td>${esc(Object.entries(t.option_counts??{}).map(([k,n])=>`${k} 选项 × ${n} 题`).join('；')||'—')}</td><td>${t.variable_options?'逐题变化':'固定描述；类别与长度混杂'}</td></tr>`).join('')}</tbody></table></div><p class="length-note">所有选项等长的题无法区分长短偏向，不纳入长度位置分。输出失败或无法映射到候选的记录也不能填成中性 0。</p></details>`;
}
function reversalPlot(rows){
 const available=rows.filter(r=>r.m.reversal);
 if(!available.length)return '';
 return `<details class="length-details length-reversal"><summary>只交换选项顺序，模型还会选同一个答案吗？</summary><div class="length-panel" id="length-reversal"><div class="length-panel-head"><div><h3>选项换序后的选择一致率</h3><p>独立范围：CRUXEval + When2Call 中长度可比较、两次均有效的原题／换序对。不受主图任务与作答范围筛选影响。</p></div><span>0 → 100% · 越高越一致</span></div>${available.map(row=>{const r=row.m.reversal,tip=`${row.m.label??row.id} · 换序后同一语义答案 ${count(r.same_semantic_choice)} / ${count(r.n)}（${percent(r.same_choice_rate)}） · 平均长度位置分变化 ${signed(r.length_score_delta)} · 无效配对 ${count(r.failures)}`;return `<div class="length-model-row length-reversal-row" data-length-tip="${esc(tip)}" tabindex="0" role="img" aria-label="${esc(tip)}"><span class="length-model-name">${esc(row.m.label??row.id)}<small>${count(r.same_semantic_choice)} / ${count(r.n)} 对一致</small></span><span class="length-track"><svg viewBox="0 0 1000 34" preserveAspectRatio="none" aria-hidden="true"><rect x="0" y="13" width="1000" height="8" fill="#eff3f0" rx="2"/>${finite(r.same_choice_rate)?`<rect x="0" y="13" width="${r.same_choice_rate*1000}" height="8" fill="${COLORS[row.family]}" rx="2"/>`:''}</svg></span><span class="length-value">${percent(r.same_choice_rate)}<small>长度分变化 ${signed(r.length_score_delta)}</small></span></div>`;}).join('')}<div class="length-readout" aria-live="polite">聚焦一行查看配对数和长度分变化。内容相同只换顺序，可以检查位置敏感性，不能隔离长度与语义的关系。</div><p class="length-note">每个模型使用自身有效配对：通常为 222 对，Jev 为 221 对，不是主图共同的 221 题。长度分变化 = 换序后 − 换序前；一致率不表示正确率。</p></div></details>`;
}
function wordSensitivity(rows){
 const available=rows.filter(r=>r.m.word_sensitivity);
 if(!available.length)return '';
 return `<details class="length-details"><summary>换成按词数衡量，结果是否改变？</summary><p class="length-note">独立敏感性检查：只取字符数与空白分词词数都能区分选项长度的交集，分母按模型有效输出计算。此处不沿用主图区间，也不随主图任务／错误题筛选变化；字符数、词数都不是模型原生 token 数。</p><div class="table-scroll"><table><thead><tr><th>模型</th><th>共同有效题数</th><th>按字符数的长度分</th><th>按词数的长度分</th><th>词数 − 字符数</th></tr></thead><tbody>${available.map(row=>{const w=row.m.word_sensitivity,c=w.characters,v=w.words;return `<tr><td>${esc(row.m.label??row.id)}</td><td>${count(c?.n)} / ${count(v?.n)}</td><td>${signed(c?.score)}</td><td>${signed(v?.score)}</td><td>${finite(c?.score)&&finite(v?.score)?signed(v.score-c.score):'—'}</td></tr>`;}).join('')}</tbody></table></div></details>`;
}

export function lengthMarkup(data,{family='all',search='',task='variable',mode='all'}={}){
 if(!data?.models)return '<div class="length-page"><p class="length-empty">选项长度分析暂未加载，原排行榜不受影响。</p></div>';
 const rows=lengthRows(data,{family,search,task,mode}),tasks=taskList(data),taskTitle=task==='variable'?'逐题变化的选项描述 · CRUXEval + When2Call':task==='all'?'全部 9 项原始任务':tasks.find(t=>t.id===task)?.label??task;
 const controls=`<div class="length-controls"><label class="length-control">主图范围 <select data-length-task aria-label="长度分析主图范围"><option value="variable" ${task==='variable'?'selected':''}>逐题变化的描述 · 2 项任务</option><option value="all" ${task==='all'?'selected':''}>全部原始任务 · 9 项</option>${tasks.map(t=>`<option value="${esc(t.id)}" ${task===t.id?'selected':''}>${esc(t.label??t.id)}${t.variable_options?'':' · 固定描述'}</option>`).join('')}</select></label><div class="length-modes" role="group" aria-label="长度分析作答范围"><button data-length-mode="all" aria-pressed="${mode==='all'}">全部有效作答</button><button data-length-mode="errors" aria-pressed="${mode==='errors'}">仅错误作答</button></div></div>`;
 const cohort=data.variable_cohort;
 const cohortText=task==='variable'&&cohort?`<span class="length-cohort-note">共同 ${count(cohort.common_n)} 题 = ${count(cohort.source_n)} 道原题 − ${count(cohort.equal_excluded)} 道等长题 − ${count(cohort.unavailable_excluded)} 道缺有效输出题${mode==='errors'?'；当前取各模型答错子集':rows.length&&finite(rows[0].s?.gold_score)?`；正确答案长度分 ${signed(rows[0].s.gold_score)}`:''}。</span>`:'';
 const lead=`<p class="length-definition">按同题描述字符数（不计空白）排序：<strong>−100 最短，+100 最长</strong>；并列取中间位置，随机选项期望为 0。正负不代表好坏。</p><p class="length-scope"><strong>${esc(taskTitle)}</strong> · ${rows.length} 个模型 · ${mode==='errors'?'各模型的错误题子集':'原始题的有效作答'}。${cohortText}这里只描述选择相关性，不能证明“把同一个选项改长就会更爱选”。</p>`;
 const content=rows.length?`${mainPlot(rows,{mode})}${extremesPlot(rows,{mode})}${reversalPlot(rows)}${taskMatrix(rows,data,mode)}${exactTable(rows,mode)}${wordSensitivity(rows)}${datasetTable(data)}`:'<p class="length-empty">没有匹配的模型，请修改搜索或模型类型筛选。</p>';
 return `<div class="length-page">${controls}${lead}${content}<div class="length-sources"><a href="/length-bias.json" download>分析数据 · JSON</a><a href="/length-scores.csv" download>精确分数 · CSV</a><a href="https://github.com/CYMCharming/system1bench/tree/main/research/option_length_v1" target="_blank" rel="noopener">协议与复现结果 ↗</a></div><p class="length-methods">通用大模型在这里直接选择答案代码，未使用思维链；不能推及所有推理模式。区间仅表示当前题集的抽样不确定性，不含训练数据与提示方式差异；不能以区间是否重叠替代模型间差异检验。此诊断不改动准确率或综合榜。</p></div>`;
}

const bound=new WeakSet();
export function bindLength(root,onChange){
 if(bound.has(root))return;
 root.addEventListener('change',event=>{const selector=event.target.closest?.('[data-length-task]');if(selector)onChange({task:selector.value});});
 root.addEventListener('click',event=>{const button=event.target.closest?.('[data-length-mode]');if(button)onChange({mode:button.dataset.lengthMode});});
 for(const name of ['pointerover','focusin'])root.addEventListener(name,event=>{
  const mark=event.target.closest?.('[data-length-tip]');if(!mark)return;
  const overview=mark.closest('.length-overview'),panel=mark.closest('.length-panel');
  const readouts=overview?overview.querySelectorAll('.length-readout'):panel?.querySelectorAll('.length-readout');
  const readout=readouts?.[readouts.length-1];
  if(readout){readout.textContent=mark.dataset.lengthTip;readout.classList.add('inspecting');}
 });
 bound.add(root);
}
