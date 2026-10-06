// Native, source-backed visualizations for the existing static benchmark site.
// Every mark is a function of the same reviewed rows used by the exact table.
const esc = v => String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const colors = {decision:'#176745',general:'#6267c5',representation:'#a07532'};
export const types = {decision:'决策专用',general:'通用大模型',representation:'表示模型'};
const valid = v => typeof v==='number'&&Number.isFinite(v);
const num = (v,type) => !valid(v)?'—':type==='percent'?(v*100).toFixed(2):type==='probability'?v.toFixed(4):v.toFixed(2);
const unit = type => type==='percent'?'%':type==='speed'?' ms':'';
export function niceMax(max) {
 if(!(max>0))return 1;
 const power=10**Math.floor(Math.log10(max)),scaled=max/power;
 return (scaled<=1?1:scaled<=2?2:scaled<=2.5?2.5:scaled<=5?5:10)*power;
}
export function barDomain(rows,type) {
 if(type==='percent')return 1;
 return niceMax(Math.max(0,...rows.flatMap(r=>[r.c.score,...(r.c.ci95??[])])));
}
const intervalText = (c,type) => c.ci95?` · 95% 区间 ${num(c.ci95[0],type)}–${num(c.ci95[1],type)}${unit(type)}`:'';
const countText = c => Number.isInteger(c.correct)?` · ${c.correct} / ${c.n}`:c.n?` · n = ${c.n}`:' · 等权综合，无单一分母';
function ticks(max,type) {
 return Array.from({length:5},(_,i)=>{const v=max*i/4;return {v,label:type==='percent'?String(Math.round(v*100)):max<.1?v.toFixed(3):max<1?v.toFixed(2):String(Number(v.toFixed(1)))};});
}
export function buildRanking(rows,{type,metricName,label,kind,max}) {
 const grid=[0,250,500,750,1000].map(x=>`<line x1="${x}" x2="${x}" y1="0" y2="32" class="bar-grid"/>`).join('');
 return `<div class="rank-axis"><span></span><span class="axis-caption">模型</span><div class="axis-ticks">${ticks(max,type).map(t=>`<span>${t.label}</span>`).join('')}</div><span class="axis-caption axis-unit">${type==='percent'?'分数 / %':type==='speed'?'毫秒':'误差'}</span></div><div class="rank-bars">${rows.map(r=>{
  const description=`${label(r.id)} · ${metricName} ${num(r.c.score,type)}${unit(type)}${intervalText(r.c,type)}${countText(r.c)}`;
  const width=r.c.score/max*1000, bounds=r.c.ci95?.map(v=>v/max*1000);
  const ci=bounds?`<line x1="${bounds[0]}" x2="${bounds[1]}" y1="16" y2="16" class="ci-line"/><line x1="${bounds[0]}" x2="${bounds[0]}" y1="10" y2="22" class="ci-line"/><line x1="${bounds[1]}" x2="${bounds[1]}" y1="10" y2="22" class="ci-line"/>`:'';
  return `<button class="ranked-row" data-model="${esc(r.id)}" data-viz-tip="${esc(description)}" aria-label="${esc(description)}"><span class="visual-rank ${r.rank<=3?'leading':''}">${r.rank}</span><span class="visual-model"><strong>${esc(label(r.id))}</strong><span>${types[kind(r.id)]}</span></span><span class="bar-shell"><svg viewBox="0 0 1000 32" preserveAspectRatio="none" aria-hidden="true">${grid}<rect x="0" y="8" width="1000" height="16" rx="3" class="bar-track"/><rect x="0" y="8" width="${width}" height="16" rx="3" fill="${colors[kind(r.id)]}" class="bar-mark" data-score="${r.c.score}"/>${ci}</svg></span><span class="visual-score">${num(r.c.score,type)}<small>${unit(type)}</small></span></button>`;
 }).join('')}</div>`;
}
const shortNames={policy_action:'政策',legal:'法律',science:'科学',all_heads:'多字段',policy_counterfactual:'事实改变',natural_reversal:'选项换序',cladder:'因果',cruxeval:'代码',finentity:'金融',when2call:'工具',one_field:'1 字段',three_fields:'3 字段',eight_fields:'8 字段',direct:'直接',composition:'组合',daily_evidence:'日常证据',disclosure:'信息披露',history:'历史',sequential:'顺序'};
export function matrixColumns(view) {
 return view==='speed'?['one_field','three_fields','eight_fields']:view==='transfer'?['cladder','cruxeval','finentity','when2call']:view==='robustness'?['all_heads','policy_counterfactual','natural_reversal']:view==='probability'?['direct','composition','daily_evidence','disclosure','history','sequential']:['policy_action','legal','science'];
}
export function matrixCell(model,key,{view,metric}) {
 if(view==='speed'){const c=model.workloads[key];return {...c,score:c.mean_ms,ci95:c.mean_round_ci95_ms};}
 if(view==='transfer')return model.metrics[key]?.original;
 if(view==='probability'){const cat=model.metrics.known_distribution.categories[key];return {...cat[metric],n:cat.n};}
 return model.metrics[key];
}
function heatColor(fraction) {
 const p=Math.max(0,Math.min(1,fraction)),a=[239,246,242],b=[23,103,69];
 return '#'+a.map((v,i)=>Math.round(v+(b[i]-v)*p).toString(16).padStart(2,'0')).join('');
}
export function buildMatrix(rows,all,{view,metric,type,label,names}) {
 const keys=matrixColumns(view),low=['speed','probability'].includes(view);
 const max=type==='percent'?1:niceMax(Math.max(0,...all.flatMap(r=>keys.map(k=>matrixCell(r.m,k,{view,metric})?.score??0))));
 const header=keys.map(k=>`<span>${shortNames[k]}</span>`).join('');
 const body=rows.map(r=>`<div class="matrix-row"><button class="matrix-model" data-model="${esc(r.id)}">${esc(label(r.id))}</button>${keys.map(k=>{
  const c=matrixCell(r.m,k,{view,metric}),fraction=low?1-c.score/max:c.score/max;
  const description=`${label(r.id)} · ${shortNames[k]}${view==='probability'?' · '+names[metric]:''} ${num(c.score,type)}${unit(type)}${intervalText(c,type)}${countText(c)}`;
  const overlap=k==='legal'&&r.id.startsWith('startlux')?'<sup title="作者声明使用 ContractNLI 训练；不代表已证实测试泄漏">†</sup>':'';
  return `<button class="matrix-cell ${fraction>.58?'dark':''}" data-model="${esc(r.id)}" data-viz-tip="${esc(description)}" aria-label="${esc(description)}" data-score="${c.score}"><svg viewBox="0 0 100 52" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="52" rx="4" fill="${heatColor(fraction)}"/></svg><span>${type==='percent'?(c.score*100).toFixed(1):type==='probability'?c.score.toFixed(3):c.score.toFixed(1)}${overlap}</span></button>`;
 }).join('')}</div>`).join('');
 return `<div class="matrix-scroll"><div class="ability-matrix columns-${keys.length}"><div class="matrix-head"><span>模型</span>${header}</div>${body}</div></div><div class="heat-legend"><span>0${unit(type)}</span><svg viewBox="0 0 180 12" preserveAspectRatio="none" aria-hidden="true">${Array.from({length:9},(_,i)=>`<rect x="${i*20}" width="20" height="12" fill="${heatColor(low?1-i/8:i/8)}"/>`).join('')}</svg><span>${num(max,type)}${unit(type)}</span><span class="legend-explain">颜色越深${low?'越好':'分数越高'}</span></div>${keys.includes('legal')&&rows.some(r=>r.id.startsWith('startlux'))?'<p class="chart-caveat">† StartLux 声明使用 ContractNLI 训练；不能将法律分数视为纯未见领域能力。</p>':''}`;
}
export function tradeoffRows(data,rows,{view,metric}) {
 const workload=view==='speed'?metric:'three_fields';
 return rows.map(r=>{
  const s=data.speed[r.id]?.workloads[workload],q=data.quality.models[r.id]?.metrics[view==='speed'?'overall_domain_equal':metric];
  return s&&q?{id:r.id,x:s.mean_ms,y:q.score,xci:s.mean_round_ci95_ms,yci:q.ci95,n:s.n,workload}:null;
 }).filter(Boolean);
}
function symbol(type,x,y,size=5.5) {
 const color=colors[type];
 if(type==='general')return `<path d="M ${x} ${y-size-1} L ${x+size+1} ${y} L ${x} ${y+size+1} L ${x-size-1} ${y} Z" fill="none" stroke="${color}" stroke-width="2"/>`;
 if(type==='representation')return `<rect x="${x-size}" y="${y-size}" width="${size*2}" height="${size*2}" rx="1" fill="${color}"/>`;
 return `<circle cx="${x}" cy="${y}" r="${size}" fill="${color}"/>`;
}
export function buildScatter(points,{width=900,label,kind,yName}) {
 const w=Math.max(300,width),h=w<500?330:340,margin={l:56,r:26,t:25,b:62};
 const plotW=w-margin.l-margin.r,plotH=h-margin.t-margin.b,maxX=niceMax(Math.max(1,...points.flatMap(p=>[p.x,...(p.xci??[])])));
 const x=v=>margin.l+v/maxX*plotW,y=v=>margin.t+(1-v)*plotH;
 const gridX=ticks(maxX,'speed').map(t=>`<line x1="${x(t.v)}" x2="${x(t.v)}" y1="${margin.t}" y2="${h-margin.b}" class="scatter-grid"/><text x="${x(t.v)}" y="${h-margin.b+23}" text-anchor="middle" class="plot-tick">${t.label}</text>`).join('');
 const gridY=ticks(1,'percent').map(t=>`<line x1="${margin.l}" x2="${w-margin.r}" y1="${y(t.v)}" y2="${y(t.v)}" class="scatter-grid"/><text x="${margin.l-12}" y="${y(t.v)+4}" text-anchor="end" class="plot-tick">${t.label}</text>`).join('');
 const marks=points.map(p=>{
  const tip=`${label(p.id)} · 平均 ${p.x.toFixed(2)} ms${p.xci?'（95% 轮均值区间 '+p.xci.map(v=>v.toFixed(2)).join('–')+' ms）':''} · ${yName} ${(p.y*100).toFixed(2)}%${p.yci?'（95% 区间 '+p.yci.map(v=>(v*100).toFixed(2)).join('–')+'）':''} · ${p.n} 次速度请求`;
  const ciX=p.xci?`<line x1="${x(p.xci[0])}" x2="${x(p.xci[1])}" y1="${y(p.y)}" y2="${y(p.y)}" class="scatter-ci"/>`:'';
  const ciY=p.yci?`<line x1="${x(p.x)}" x2="${x(p.x)}" y1="${y(p.yci[0])}" y2="${y(p.yci[1])}" class="scatter-ci"/>`:'';
  return `<g class="scatter-point" data-model="${esc(p.id)}" data-point="${esc(p.id)}" data-x="${p.x}" data-y="${p.y}" data-viz-tip="${esc(tip)}" tabindex="0" role="button" aria-label="${esc(tip)}">${ciX}${ciY}<circle cx="${x(p.x)}" cy="${y(p.y)}" r="13" fill="transparent"/>${symbol(kind(p.id),x(p.x),y(p.y))}</g>`;
 }).join('');
 // Only boundary observations get persistent labels; every point has a
 // pointer + keyboard tooltip with its complete model name and both intervals.
 const anchors=points.length?[points.reduce((a,b)=>a.x<b.x?a:b),points.reduce((a,b)=>a.y>b.y?a:b),points.reduce((a,b)=>a.x>b.x?a:b)]:[];
 const labels=w<500?'':[...new Map(anchors.map(p=>[p.id,p])).values()].map(p=>{
  const name=label(p.id),right=p.x>maxX*.7,xx=x(p.x)+(right?-11:11),yy=y(p.y)-13;
  return `<text x="${xx}" y="${Math.max(margin.t+12,yy)}" text-anchor="${right?'end':'start'}" class="point-label">${esc(name)}</text>`;
 }).join('');
 return `<svg class="tradeoff-svg" viewBox="0 0 ${w} ${h}" role="group" aria-label="模型成绩与推理速度散点图">${gridX}${gridY}<line x1="${margin.l}" x2="${w-margin.r}" y1="${h-margin.b}" y2="${h-margin.b}" class="axis-line"/><line x1="${margin.l}" x2="${margin.l}" y1="${margin.t}" y2="${h-margin.b}" class="axis-line"/>${marks}${labels}<text x="${margin.l+plotW/2}" y="${h-13}" text-anchor="middle" class="axis-title">平均完整请求耗时 / ms · 越靠左越快</text><text x="${margin.l}" y="15" class="axis-title">${esc(yName)} / % · 越高越好</text></svg>`;
}
function legend() {
 return `<div class="visual-legend">${Object.entries(types).map(([k,v])=>`<span><i class="legend-mark ${k}"></i>${v}</span>`).join('')}<span class="interval-key"><i></i>95% 区间</span></div>`;
}
export function visualMarkup({data,rows,all,view,metric,names,label,kind,expanded=false}) {
 if(!rows.length||view==='datasets')return '';
 const type=view==='speed'?'speed':view==='probability'?'probability':'percent';
 const visualRows=rows.map(r=>view==='speed'?{...r,c:matrixCell(r.m,metric,{view,metric})}:r);
 const domainRows=all.map(r=>view==='speed'?{...r,c:matrixCell(r.m,metric,{view,metric})}:r);
 const chosen=expanded?visualRows:visualRows.slice(0,6),max=barDomain(domainRows,type);
 const points=['overall','speed'].includes(view)?tradeoffRows(data,rows,{view,metric}):[];
 const matrixTitle=view==='speed'?'字段数量与耗时':view==='probability'?'不同概率问题的表现':view==='robustness'?'可靠性三项对照':view==='transfer'?'四个迁移领域':'领域能力矩阵';
 const matrixScope=view==='speed'?'相同语义 · 1 / 3 / 8 字段 · 毫秒':view==='probability'?'六类案例 · 每类 16 个 · 同一误差尺度':view==='transfer'?'原始选项成绩 · 四领域 · 0–100%':view==='robustness'?'多字段与两类配对检查 · 0–100%':'政策 / 法律 / 科学 · 0–100%';
 return `<div class="visual-header"><div><span class="section-kicker">MODEL COMPARISON</span><h3>排名，一眼看清</h3></div>${legend()}</div><div class="visual-grid"><section class="ranking-plot" aria-labelledby="rankingTitle"><div class="chart-heading"><h4 id="rankingTitle">${esc(names[metric])}</h4><span>${type==='percent'?'越长分数越高':'越短越好'} · 从零起点</span></div>${buildRanking(chosen,{type,metricName:names[metric],label,kind,max})}<div class="viz-readout" aria-live="polite">${chosen.length===rows.length?'当前筛选的全部模型':'当前筛选前 '+chosen.length+' 个模型'} · 悬停或聚焦查看精确数值与区间</div></section><section class="matrix-plot" aria-labelledby="matrixTitle"><div class="chart-heading"><h4 id="matrixTitle">${matrixTitle}</h4><span>${matrixScope}</span></div>${buildMatrix(chosen,domainRows,{view,metric,type,label,names})}<div class="viz-readout" aria-live="polite">${view==='speed'?'当前软件栈；部分模型使用参考内核，不代表优化极限。':'颜色对应真实分数，不是名次；点击可查看完整模型详情。'}</div></section></div>${rows.length>6?`<div class="visual-expand"><span>排名与矩阵使用同一组模型，随筛选一起更新。</span><button data-chart-action="expand">${expanded?'收起为前 6 个':'展开全部 '+rows.length+' 个模型'}</button></div>`:''}${points.length?`<section class="tradeoff-plot" aria-labelledby="tradeoffTitle"><div class="chart-heading"><div><span class="section-kicker">QUALITY × LATENCY</span><h4 id="tradeoffTitle">模型成绩与速度</h4></div><span>${points.length} 个模型有双侧数据 · A100 80GB</span></div><div id="tradeoffCanvas" data-plot-width></div><div class="viz-readout" aria-live="polite">点形区分模型类型；悬停或键盘聚焦查看精确分数。</div><p class="chart-method">主榜固定成绩 × 当前独立测速，非同一次运行；速度按${view==='speed'?names[metric]:'3 个决策字段'}比较。托管 API 与缺测模型不补零、不绘点。区间含义见协议，图形不证明架构因果。</p></section>`:''}`;
}
let resizeObserver;
const boundRoots=new WeakSet();
export function renderVisuals(root,options) {
 resizeObserver?.disconnect();
 root.innerHTML=visualMarkup(options);
 const canvas=root.querySelector('#tradeoffCanvas');
 if(canvas){
  const points=tradeoffRows(options.data,options.rows,options);
  const draw=()=>{canvas.innerHTML=buildScatter(points,{width:canvas.clientWidth,label:options.label,kind:options.kind,yName:options.names[options.view==='speed'?'overall_domain_equal':options.metric]});};
  draw();if(typeof ResizeObserver!=='undefined'){resizeObserver=new ResizeObserver(draw);resizeObserver.observe(canvas);}
 }
 // Register once: filtering and resize replace marks, not this delegated root.
 if(!boundRoots.has(root)){
  for(const eventName of ['pointerover','focusin'])root.addEventListener(eventName,event=>{
   const mark=event.target.closest?.('[data-viz-tip]');if(!mark)return;
   const readout=mark.closest('.ranking-plot,.matrix-plot,.tradeoff-plot')?.querySelector('.viz-readout');
   if(readout){readout.textContent=mark.dataset.vizTip;readout.classList.add('inspecting');}
  });
  boundRoots.add(root);
 }
}
