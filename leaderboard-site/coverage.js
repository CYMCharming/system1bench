const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const taskNames={refund:'退款',access:'访问',routing:'分流',legal:'法律',science:'科学',cladder:'因果',cruxeval:'代码',finentity:'金融',when2call:'工具',clinc150_full:'CLINC',banking77_full:'BANKING'};
export function coverageMarkup(data){
 const c=data?.comprehensive;if(!c)return '';
 const entries=Object.entries(c.coverage).sort((a,b)=>({complete:0,pending:1,native_options_exceeded:2})[a[1].status]-({complete:0,pending:1,native_options_exceeded:2})[b[1].status]||a[1].label.localeCompare(b[1].label));
 const status={complete:'已入综合榜',pending:'补测中',native_options_exceeded:'选项超限 · 不入综合榜'};
 const rows=entries.map(([id,m])=>`<tr><th scope="row"><button data-model="${esc(id)}">${esc(m.label.replace(/ \(Unsloth BF16 distribution\)/,''))}</button><small class="coverage-status ${m.status}">${status[m.status]} · ${m.classification_tasks}/11</small></th>${c.tasks.map(task=>{
  const metric=data.quality.models[id].metrics[task]??data.transfer[id==='jev-1.13.0'?'jev':id]?.metrics[task]?.original??c.intent[id]?.metrics[task];
  const exceeded=m.status==='native_options_exceeded'&&task.endsWith('_full');
  return metric?`<td class="covered" title="${metric.correct}/${metric.n}"><strong>${(metric.score*100).toFixed(1)}</strong><small>${metric.correct}/${metric.n}</small></td>`:`<td class="${exceeded?'unsupported':'pending'}" title="${exceeded?'原生选项上限 '+m.choice_limit:'排队或评测中；尚无完整成绩'}">${exceeded?'不支持':'—'}</td>`;
 }).join('')}</tr>`).join('');
 return `<section class="coverage-panel"><div class="coverage-heading"><div><span class="section-kicker">EVALUATION COVERAGE</span><h3>模型 × 数据集</h3></div><p><strong>${c.complete_models} / ${c.eligible_models}</strong> 个兼容模型已完成<br>${c.total_models-c.eligible_models} 个选项超限，保留单项成绩</p></div><p class="coverage-note">综合榜只列完整覆盖 11 个分类任务的模型。未完成不记零，也不按已测项目求平均。下表数字为准确率（%），小字为正确数／样本数；“—”表示尚无完整成绩。</p><details${c.all_eligible_complete?'':' open'}><summary>查看全部 ${c.total_models} 个模型的覆盖与分数</summary><div class="coverage-scroll"><table class="coverage-table"><thead><tr><th>模型 / 进度</th>${c.tasks.map(t=>`<th>${taskNames[t]}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></details><p class="coverage-note">${c.all_eligible_complete?'全部兼容模型已完成。':'仍有 '+(c.eligible_models-c.complete_models)+' 个兼容模型在补测；当前综合榜不是最终全量排名。'}CLINC：151 选项、5,500 条；BANKING：77 选项、3,080 条。概率诊断和速度不计入综合分。Laya 的迁移补测采用完整选项文本适配，详见模型信息。</p></section>`;
}
