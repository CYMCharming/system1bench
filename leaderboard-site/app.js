import {renderVisuals} from './charts.js';
import {reviewMarkup} from './review.js';
import {intentMarkup} from './intent.js';
import {coverageMarkup} from './coverage.js';
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const repo = 'https://github.com/CYMCharming/system1bench/blob/main/';
const names = {overall_domain_equal:'领域等权综合分',overall_task_equal:'任务等权综合分',refund:'退款政策',access:'访问控制',routing:'工单分流',policy_action:'政策行动',legal:'法律判断',science:'科学证据',all_heads:'三个字段全部正确',policy_counterfactual:'关键事实改变：两次都对',natural_reversal:'换选项顺序：两次都对',action_head:'行动字段',review_head:'人工审核字段',severity_head:'严重程度字段',cladder:'因果 · CLadder',cruxeval:'代码 · CRUXEval',finentity:'金融 · FinEntity',when2call:'工具 · When2Call',excess_brier:'额外 Brier 误差',expected_brier:'期望 Brier 分数',total_variation:'概率分布偏差（TV）',impossible_mass:'不可能事件的概率',one_field:'1 个决策字段',three_fields:'3 个决策字段',eight_fields:'8 个决策字段'};
const views = {
 intent:{title:'意图识别 · 试跑',metrics:['intent_accuracy','intent_macro_f1'],description:'完整 151 / 77 个候选；200 条 CLINC 与 154 条 BANKING 固定试跑。准确率按样本等权，宏 F1 按类别等权。',protocol:'research/public_intent_pilot_v1/README.zh-CN.md'},
 overall:{title:'综合榜 · 八领域',metrics:['overall_domain_equal','overall_task_equal'],description:'政策、法律、科学、因果、代码、金融、工具、意图识别八领域等权。仅纳入完整覆盖 11 个分类任务的模型；选项超限不计入，缺测不记零。',protocol:'research/evaluation_completion_v1/PROTOCOL.md'},
 legacy:{title:'原综合榜 · 三领域',metrics:['overall_domain_equal','overall_task_equal'],description:'保留扩展前的 23 模型榜单：政策、法律、科学三个领域等权。原始成绩未被改写，不与新版综合分直接混排。',protocol:'research/leaderboard_v3/PROTOCOL.md'},
 intentpilot:{title:'意图识别 · 试跑存档',metrics:['intent_accuracy','intent_macro_f1'],description:'完整 151 / 77 个候选；200 条 CLINC 与 154 条 BANKING 固定试跑。不是完整官方测试成绩，不计入综合榜。',protocol:'research/public_intent_pilot_v1/README.zh-CN.md'},
 domains:{title:'领域与任务',metrics:['policy_action','legal','science','refund','access','routing'],description:'按领域与政策子任务分别报告准确率，同时列出正确数和样本数。',protocol:'research/leaderboard_v3/PROTOCOL.md'},
 robustness:{title:'稳健性',metrics:['all_heads','policy_counterfactual','natural_reversal','action_head','review_head','severity_head'],description:'评测多字段联合正确率、关键事实反转和选项换序。配对指标要求原始题与变体均回答正确。',protocol:'research/leaderboard_v3/PROTOCOL.md'},
 transfer:{title:'跨领域评测',metrics:['cladder','cruxeval','finentity','when2call'],description:'因果、代码、金融和工具选择四类任务。分别报告原始题准确率与选项换序配对准确率。',protocol:'research/startlux_transfer_v1/PROTOCOL.md'},
 probability:{title:'概率误差',metrics:['excess_brier','expected_brier','total_variation','impossible_mass'],description:'96 个已知参考分布的合成案例，误差越低越好。此处衡量分布误差，不衡量现实任务中答案正确的置信度。',protocol:'research/startlux_transfer_v1/PROTOCOL.md'},
 speed:{title:'同卡推理速度',metrics:['three_fields','one_field','eight_fields'],description:'同一张 NVIDIA A100 80GB，逐模型独立测量。平均完整请求耗时越低越好；每个负载预热 10 次，再测 5 轮 × 20 次。',protocol:'research/latency_v2/PROTOCOL.md'},
 datasets:{title:'数据集与任务分类',metrics:[],description:'八个分类领域、11 个分类任务，另有独立概率诊断。新增意图识别使用完整官方测试集；历史任务保留已发布的冻结子集。',protocol:'research/evaluation_completion_v1/PROTOCOL.md'}
};
views.intent={title:'意图识别 · 官方完整测试',metrics:['intent_accuracy','intent_macro_f1'],description:'CLINC：5,500 条、151 个选项；BANKING：3,080 条、77 个选项。已完成模型的准确率计入新版综合榜；概率指标和宏 F1 独立展示。',protocol:'research/evaluation_completion_v1/PROTOCOL.md'};
names.intent_accuracy='准确率';names.intent_macro_f1='宏平均 F1';
names.intent_domain='意图识别';names.clinc150_full='CLINC150 + OOS';names.banking77_full='BANKING77';
let data, review, pilot, view='overall', metric='overall_domain_equal', family='all', search='', displayMode='visual',expanded=false;
const kind = id => /^(qwen|llama)/.test(id) ? 'general' : ['english','multilingual'].includes(id) ? 'representation' : 'decision';
const kindName = id => ({general:'通用大模型',representation:'表示模型',decision:'决策专用'})[kind(id)];
const canonical = id => id === 'jev' ? 'jev-1.13.0' : id;
const label = id => (data.quality.models[canonical(id)]?.label ?? id).replace(/ \(Unsloth BF16 distribution\)/,'');
const note = id => id.startsWith('llama32') ? 'Meta 原始权重 · 社区分发' : id==='jev-1.13.0'||id==='jev' ? '托管 API · 不进入同卡速度榜' : kindName(id);
const icon = id => /intern/.test(id) ? 'IN' : /startlux/.test(id) ? 'SL' : /qwen/.test(id) ? 'QW' : /llama/.test(id) ? 'LL' : /kev/.test(id) ? 'KV' : /jev/.test(id) ? 'JV' : 'LY';
const finite = v => typeof v === 'number' && Number.isFinite(v);
const fmt = (v,type='percent') => !finite(v) ? '—' : type==='percent' ? (v*100).toFixed(2) : type==='probability' ? v.toFixed(4) : v.toFixed(2);
const count = c => Number.isInteger(c?.correct)&&Number.isInteger(c?.n) ? `${c.correct} / ${c.n}` : c?.n ? `n = ${c.n}` : c?.components ? '法律、科学两个领域等权' : '等权平均 · 无单一分母';
function cell(c,primary=false,type='percent') {
 return `<td><span class="${primary?'score':'number'}">${fmt(c?.score,type)}${type==='percent'&&finite(c?.score)?'<span class="unit">%</span>':''}</span>${primary&&c?.ci95?`<div class="ci">95% 区间 ${fmt(c.ci95[0],type)}–${fmt(c.ci95[1],type)}</div>`:''}<span class="subvalue">${type==='probability'?'n = 96 · 越低越好':esc(count(c))}</span></td>`;
}
function modelCell(id) {
 return `<td><button class="model-button" data-model="${esc(id)}"><span class="model-icon ${kind(id)}">${icon(id)}</span><span><span class="model-name">${esc(label(id))}${view==='domains'&&metric==='legal'&&id.startsWith('startlux')?'<span class="overlap" title="作者声明使用 ContractNLI 训练；不代表已证实测试泄漏">†</span>':''}</span><span class="model-meta">${note(id)}</span></span></button></td>`;
}
function rankedRows() {
 const source=['transfer','probability'].includes(view)?data.transfer:view==='speed'?data.speed:view==='overall'?data.comprehensive?.models??{}:data.quality.models;
 return Object.entries(source).map(([id,m])=>({id,m,c:view==='transfer'?m.metrics[metric]?.original:view==='probability'?m.metrics.known_distribution?.[metric]:view==='speed'?{score:m.workloads[metric]?.mean_ms}:m.metrics[metric]}))
  .filter(r=>finite(r.c?.score)).sort((a,b)=>(['speed','probability'].includes(view)?1:-1)*(a.c.score-b.c.score)||label(a.id).localeCompare(label(b.id)))
  .map((r,i,arr)=>({...r,rank:i&&Math.abs(r.c.score-arr[i-1].c.score)<1e-12?arr.findIndex(x=>Math.abs(x.c.score-r.c.score)<1e-12)+1:i+1}));
}
function columns() {
 if(view==='overall')return ['policy_action','legal','science','cladder','cruxeval','finentity','when2call','intent_domain'];
 if(view==='legacy')return ['policy_action','legal','science'];
 if(view==='domains')return ['refund','access','routing','legal','science'].filter(x=>x!==metric);
 if(view==='robustness')return ['all_heads','policy_counterfactual','natural_reversal'].filter(x=>x!==metric);
 if(view==='transfer')return views.transfer.metrics.filter(x=>x!==metric);
 if(view==='probability')return views.probability.metrics.filter(x=>x!==metric);
 return [];
}
function datasets() {
 const rows=[['政策','退款政策','合成规则与案例','行动 / 审核 / 严重程度','96','主面板'],['政策','访问控制','合成规则与案例','行动 / 审核 / 严重程度','96','主面板'],['政策','工单分流','合成规则与案例','行动 / 审核 / 严重程度','96','主面板'],['法律','ContractNLI','合同与待判断主张','蕴含 / 矛盾 / 未提及','144','主面板'],['科学','SciFact','科学主张与证据','支持 / 反驳 / 未提供证据','339','主面板'],['因果','CLadder','因果关系与问题','二元判断','144','迁移面板'],['代码','CRUXEval','程序与输入 / 输出','候选执行结果','128','迁移面板'],['金融','FinEntity','文本与目标实体','实体级情绪','128','迁移面板'],['工具','When2Call','上下文与调用候选','工具决策','128','迁移面板'],['概率诊断','Known distribution','已知概率的合成案例','完整概率分布','96','迁移面板']];
 $('tableHead').innerHTML='<tr><th>领域</th><th>数据集 / 任务</th><th>数据类型</th><th>评判内容</th><th>基础样本</th><th>所属面板</th></tr>';
 $('tableBody').innerHTML=rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('');
 rows.splice(rows.length-1,0,['意图','CLINC150 + OOS','官方完整测试集','150 个意图 + 域外请求','5,500','新版综合榜'],['意图','BANKING77','官方完整测试集','77 类银行服务意图','3,080','新版综合榜']);
 $('tableBody').innerHTML=rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('');
 $('resultCount').textContent='8 个分类领域 · 11 个分类任务 / 数据集 + 1 个概率诊断';
 $('boardFoot').innerHTML='基础样本数不包括选项换序、事实反转与多字段展开。科学“未提供证据”依赖当前证据包，不等于证明现实中没有证据。StartLux 声明训练中使用 ContractNLI；法律成绩不能直接解释为完全未见领域迁移。<br>来源、划分与冻结方法见 <a href="'+repo+'research/startlux_transfer_v1/PROTOCOL.md" target="_blank" rel="noopener">迁移协议</a> 和 <a href="'+repo+'research/leaderboard_v3/PROTOCOL.md" target="_blank" rel="noopener">主榜协议</a>。';
}
function render() {
 $('intentPilot').hidden=!['intent','intentpilot'].includes(view);
 $('coverage').hidden=!['overall','datasets'].includes(view);if(!$('coverage').hidden)$('coverage').innerHTML=coverageMarkup(data);
 $('datasetReview').hidden=view!=='datasets';
 if(view==='datasets')$('datasetReview').innerHTML=reviewMarkup(review);
 const config=views[view];
 document.querySelectorAll('[role=tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.view===view)));
 document.querySelectorAll('.side-link[data-view]').forEach(b=>b.classList.toggle('active',view==='datasets'?b.dataset.view==='datasets':b.dataset.view==='overall'));
 $('viewTitle').textContent=config.title;$('viewDefinition').textContent=config.description;$('protocol').href=repo+config.protocol;$('toolbar').hidden=view==='datasets';$('caption').textContent=config.title+'：'+(names[metric]??'数据说明');
 $('empty').hidden=true;$('tableWrap').hidden=displayMode==='visual';
 $('displaySwitch').hidden=view==='datasets';$('visuals').hidden=view==='datasets'||displayMode==='table';
 document.querySelectorAll('[data-display]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.display===displayMode)));
 $('metric').innerHTML=config.metrics.map(m=>`<option value="${m}" ${m===metric?'selected':''}>${names[m]}</option>`).join('');
 const params=new URLSearchParams({view});if(metric)params.set('metric',metric);if(family!=='all')params.set('family',family);if(displayMode==='table')params.set('display','table');history.replaceState(null,'','?'+params.toString());
 if(view==='datasets'){$('tableWrap').hidden=false;$('visuals').innerHTML='';datasets();return;}
 if(['intent','intentpilot'].includes(view)){
  const full=view==='intent';const result=full?{models:data.comprehensive?.intent??{},official_full_test:true,capability_limits:Object.entries(data.comprehensive?.coverage??{}).filter(([,m])=>m.status==='native_options_exceeded').map(([id,m])=>({id,label:m.label,limit:m.choice_limit,score:null}))}:pilot;
  $('tableWrap').hidden=true;$('visuals').hidden=true;$('displaySwitch').hidden=true;$('boardFoot').innerHTML='';$('resultCount').textContent=(result?Object.keys(result.models).length:0)+' 个已完成模型 · '+(full?'官方完整测试':'独立试跑存档');$('intentPilot').innerHTML=intentMarkup(result,{metric,family,search});return;
 }
 const all=rankedRows(),rows=all.filter(r=>(family==='all'||kind(r.id)===family)&&label(r.id).toLowerCase().includes(search.toLowerCase()));
 renderVisuals($('visuals'),{data,rows,all,view,metric,names,label,kind,expanded});
 $('resultCount').innerHTML=`显示 <strong>${rows.length}</strong> / ${all.length} 个已完成模型${view==='speed'?` · 计划测量 ${data.speedExpected} 个 · 平均耗时升序`:' · 按当前指标排序'} · 并列分数并列名次`;
 const extra=columns(),down=['probability','speed'].includes(view);
 $('tableHead').innerHTML=`<tr><th>排名</th><th>模型 <span class="header-hint">点击查看详情</span></th><th class="metric-head">${esc(names[metric])}${view==='speed'?' · 均值 ms':''} ${down?'↓':'↑'}</th>${view==='speed'?'<th>P50 · ms</th><th>P95 · ms</th><th>请求 / 秒</th><th>字段 / 秒</th>':extra.map(m=>`<th>${esc(names[m])}</th>`).join('')}${view==='transfer'?'<th>当前任务：换序两次都对</th>':''}</tr>`;
 $('tableBody').innerHTML=rows.map(r=>{
  let cells;
  if(view==='speed'){const c=r.m.workloads[metric];cells=`<td><span class="score">${fmt(c.mean_ms,'speed')}</span><div class="ci">95% 轮均值区间 ${fmt(c.mean_round_ci95_ms[0],'speed')}–${fmt(c.mean_round_ci95_ms[1],'speed')}</div><span class="subvalue">100 次请求 · ${c.fields} 个字段</span></td>${['median_ms','p95_ms','requests_per_second','fields_per_second'].map(k=>`<td class="number">${fmt(c[k],'speed')}</td>`).join('')}`;}
  else{const type=view==='probability'?'probability':'percent';cells=cell(r.c,true,type)+extra.map(m=>cell(view==='transfer'?r.m.metrics[m]?.original:view==='probability'?r.m.metrics.known_distribution?.[m]:r.m.metrics[m],false,type)).join('');if(view==='transfer')cells+=cell(r.m.metrics[metric]?.paired_both_correct);}
  return `<tr><td><span class="rank ${r.rank<=3?'top':''}">${r.rank}</span></td>${modelCell(r.id)}${cells}</tr>`;
 }).join('');
 if(!rows.length){$('tableWrap').hidden=true;$('visuals').hidden=true;$('empty').hidden=false;$('empty').textContent=all.length?'没有匹配的模型，请修改搜索或重置筛选。':'尚无符合测量条件的完成结果，没有用估计值填充排名。';}
 $('boardFoot').innerHTML=view==='speed'?'条件：A100 80GB PCIe · 单模型顺序运行 · GPU 同占用与 CPU 干扰检查 · 原始浮点权重 · 同步完整请求。相同语义工作负载，模型原生格式与 token 数不同。Qwen3.5 使用参考线性注意力实现；本榜反映当前软件栈，不代表优化内核极限。未测 / 未通过资源检查的不排名；托管 API、27B、外部硬件数据不混排。':view==='probability'?'默认用相对真实分布的额外 Brier 误差，剔除题目固有不确定性。概率是候选集合上的归一化输出，不等于已校准的正确性置信度。95% 区间来自协议中的配对 / 分层自助法。':view==='transfer'?'本面板与主榜覆盖不同，缺测不记零。每模型 1,152 次决策：528 道分类题的原始 / 换序版本，加 96 个概率诊断。StartLux 声明的训练历史需单独考虑；成绩差异不是架构因果证据。':view==='overall'?'领域等权 =（政策行动 + 法律 + 科学）/ 3；任务等权 =（退款 + 访问控制 + 分流 + 法律 + 科学）/ 5。95% 区间是样本层面不确定性，不含提示选择与训练历史偏差。保留之前 18 个模型的原始成绩。':view==='domains'?'每个分数保留分母。法律 †：StartLux 作者声明训练中使用 ContractNLI，不能直接视为纯未见领域能力，也没有据此证明测试泄漏。科学“未提供证据”依赖当前证据包。':'关键事实改变时应正确改判，换选项顺序时应保持正确。法律 / 科学换序总分为两个领域配对正确率的等权平均，无单一正确数分母。';
 if(view==='overall')$('boardFoot').innerHTML='领域等权：8 个领域各占 1/8；政策内 3 个任务等权，意图识别内 2 个任务等权。任务等权：11 个分类任务各占 1/11。仅使用原始选项分类准确率，不重复计入换序题、二元 CLINC 或试跑。综合分无单一分母；尚未为新版综合分建立置信区间，不沿用旧区间。历史数据的冻结子集、来源标签与训练接触风险仍适用。';
 if(view==='legacy')$('boardFoot').innerHTML='旧榜：政策、法律、科学三个领域等权；任务等权为退款、访问、分流、法律、科学五项平均。23 个模型的历史成绩保持不变。此处不含新增分类任务。';
}
function detail(id) {
 const q=data.quality.models[canonical(id)],t=data.transfer[id]??data.transfer[id==='jev-1.13.0'?'jev':id],s=data.speed[id];
 let html=`<h2>${esc(label(id))}</h2><p>${esc(note(id))}。仅列已完成的评测，缺测项不估算。</p>`;
 if(id.startsWith('llama32'))html+=`<p>通过 Unsloth 社区渠道分发 BF16 权重，逐分片 SHA-256 与 Meta 官方权重一致；不表示已证明所有 tokenizer 文件相同。<a href="${repo}research/model_expansion_v3/llama_weight_identity.json" target="_blank" rel="noopener">权重一致性记录</a>。</p>`;
 if(q)html+='<h3>主面板</h3><table><tbody>'+Object.entries(q.metrics).map(([key,c])=>`<tr><td>${esc(names[key]??key)}</td>${cell(c)}</tr>`).join('')+'</tbody></table>';
 const complete=data.comprehensive?.models[canonical(id)],intent=data.comprehensive?.intent[canonical(id)];
 if(complete)html+='<h3>新版综合榜 · 八领域</h3><table><tbody>'+['overall_domain_equal','overall_task_equal',...data.comprehensive.tasks].map(key=>`<tr><td>${esc(names[key]??key)}</td>${cell(complete.metrics[key])}</tr>`).join('')+'</tbody></table>';
 else if(data.comprehensive)html+='<p>新版综合榜状态：'+(data.comprehensive.coverage[canonical(id)].status==='native_options_exceeded'?'原生选项上限不足，不混入综合分。':'尚未完成全部 11 个分类任务。')+'</p>';
 if(intent)html+='<h3>完整意图测试</h3><table><tbody>'+Object.entries(intent.metrics).map(([key,c])=>`<tr><td>${esc(names[key]??key)}</td>${cell(c)}</tr>`).join('')+'</tbody></table>';
 const adaptation=data.comprehensive?.transfer_additions[canonical(id)]?.receipt;
 if(adaptation?.input_adaptation)html+='<p>迁移测试接口：完整选项文本适配。仅去掉 Laya 对单个选项描述的 48-token 截断；权重、选项、顺序与全局输入预算不变。不是未经改动的原生接口。<a href="'+repo+'research/evaluation_completion_v2/PROTOCOL.md" target="_blank" rel="noopener">适配说明</a></p>';
 if(intent?.receipt.calibration_caveat)html+='<p>概率说明：当前 Laya 原生运行时会限制部分发布温度的范围；分类准确率不受正温度缩放影响，但概率不能视为已经校准的置信度，也不保证与旧运行时相同。</p>';
 if(t)html+='<h3>迁移面板</h3><table><tbody>'+views.transfer.metrics.map(key=>`<tr><td>${names[key]}</td>${cell(t.metrics[key].original)}<td>两次都对 ${fmt(t.metrics[key].paired_both_correct.score)}%</td></tr>`).join('')+'</tbody></table>';
 if(s)html+=`<h3>速度 · ${esc(s.hardware)}</h3><table><tbody>`+Object.entries(s.workloads).map(([key,c])=>`<tr><td>${names[key]}</td><td>${fmt(c.mean_ms,'speed')} ms 均值</td><td>${fmt(c.p95_ms,'speed')} ms P95</td></tr><tr><td>提示编码</td><td colspan="2">${c.distinct_prompt_encodings} 种；token 长度 ${c.prompt_token_lengths.join(' / ')}</td></tr>`).join('')+`</tbody></table><p><a href="${repo+s.source}" target="_blank" rel="noopener">速度汇总与校验哈希</a></p>`;
 html+='<h3>来源与版本</h3><p>'+data.sources.filter(x=>!x.path.includes('/latency_v2/')||x.path.includes('/'+id+'/')).map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.path)}</a><br><span class="hash">SHA-256 ${esc(x.sha256)}</span>`).join('<br>')+'</p>';
 $('detailContent').innerHTML=html;$('detail').showModal();
}
document.addEventListener('click',event=>{
 const tab=event.target.closest('[data-view]');if(tab&&data){view=tab.dataset.view;metric=views[view].metrics[0]??'';expanded=false;render();}
 const mode=event.target.closest('[data-display]');if(mode&&data){displayMode=mode.dataset.display;render();}
 const action=event.target.closest('[data-chart-action]');if(action&&data){expanded=!expanded;render();}
 const model=event.target.closest('[data-model]');if(model)detail(model.dataset.model);
});
document.addEventListener('keydown',event=>{const mark=event.target.closest('[data-point]');if(mark&&['Enter',' '].includes(event.key)){event.preventDefault();detail(mark.dataset.model);}});
$('closeDetail').addEventListener('click',()=>$('detail').close());
$('search').addEventListener('input',event=>{search=event.target.value;render();});
$('metric').addEventListener('change',event=>{metric=event.target.value;render();});
$('family').addEventListener('change',event=>{family=event.target.value;render();});
$('reset').addEventListener('click',()=>{search='';family='all';expanded=false;$('search').value='';$('family').value='all';metric=views[view].metrics[0]??'';render();});
try {
 const response=await fetch('/catalog.json');if(!response.ok)throw Error('数据响应 '+response.status);data=await response.json();if(data.version!==1)throw Error('数据版本不兼容');
 try{const result=await fetch('/review.json');if(result.ok){review=await result.json();if(review.version!==1)review=null;}}catch{review=null;}
 try{const result=await fetch('/intent-pilot.json');if(result.ok){pilot=await result.json();if(pilot.version!==1||!pilot.models)pilot=null;}}catch{pilot=null;}
 const params=new URLSearchParams(location.search);if(views[params.get('view')])view=params.get('view');metric=views[view].metrics.includes(params.get('metric'))?params.get('metric'):views[view].metrics[0]??'';
 if(params.get('display')==='table')displayMode='table';
 if(['all','decision','general','representation'].includes(params.get('family')))family=params.get('family');$('family').value=family;
 $('modelCount').textContent=Object.keys(data.quality.models).length;$('release').textContent='发布快照 · '+new Date(data.generatedAt).toLocaleDateString('zh-CN',{timeZone:'Asia/Shanghai'});render();
} catch(error){$('tableWrap').hidden=true;$('visuals').hidden=true;$('toolbar').hidden=true;$('empty').hidden=false;$('empty').textContent='暂时无法读取评测数据，请刷新后重试。';$('viewDefinition').textContent=error.message;}
