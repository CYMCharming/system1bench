// DOM unit checks, not a substitute for browser-based visual verification.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {visualMarkup,buildRanking,barDomain,tradeoffRows,buildScatter,matrixCell,matrixColumns} from './charts.js';
import {reviewMarkup} from './review.js';
import {intentMarkup} from './intent.js';
import {coverageMarkup} from './coverage.js';
const elements=new Map();
const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',hidden:false,value:'',addEventListener(){},showModal(){},close(){}});return elements.get(id);};
const catalog=JSON.parse(fs.readFileSync('data/catalog.json','utf8'));
let source=fs.readFileSync('app.js','utf8').replace(/^import .*;\r?\n/gm,'');
const review=JSON.parse(fs.readFileSync('data/review.json','utf8'));
const pilot=JSON.parse(fs.readFileSync('data/intent-pilot.json','utf8'));
const context=vm.createContext({intentMarkup,reviewMarkup,coverageMarkup,renderVisuals:(root,options)=>{root.innerHTML=visualMarkup(options);},document:{getElementById:get,querySelectorAll:()=>[],addEventListener(){}},history:{replaceState(){}},location:{search:''},URLSearchParams,Date,fetch:async url=>({ok:true,json:async()=>url==='/review.json'?review:url==='/intent-pilot.json'?pilot:catalog}),console});
await vm.runInContext(`(async()=>{${source}\n globalThis.verify=(v,m,f='all',s='')=>{view=v;metric=m;family=f;search=s;render();return {rows:rankedRows(),html:$('tableBody').innerHTML,empty:$('empty').hidden};};})()`,context);
assert.equal(get('modelCount').textContent,23);
for(const [v,m,n] of [['overall','overall_domain_equal',catalog.comprehensive.complete_models],['legacy','overall_domain_equal',23],['domains','legal',23],['robustness','all_heads',23],['transfer','cladder',Object.keys(catalog.transfer).length],['probability','excess_brier',Object.keys(catalog.transfer).length],['speed','three_fields',Object.keys(catalog.speed).length]]){
 const r=context.verify(v,m);assert.equal(r.rows.length,n);assert(!r.html.includes('undefined'));assert(!r.html.includes('NaN'));
 assert.equal((get('visuals').innerHTML.match(/class="ranked-row"/g)||[]).length,Math.min(6,n));
 assert(!get('visuals').innerHTML.includes('NaN'));assert(!get('visuals').innerHTML.includes('undefined'));
 const scores=r.rows.map(x=>x.c.score);for(let i=1;i<scores.length;i++)assert(['probability','speed'].includes(v)?scores[i]>=scores[i-1]:scores[i]<=scores[i-1]);
}
assert.equal(context.verify('overall','overall_domain_equal','all','nonexistent search').empty,false);
assert.equal(context.verify('legacy','overall_domain_equal','general').html.match(/class="model-button"/g).length,9);
context.verify('datasets','');assert.equal((get('tableBody').innerHTML.match(/<tr>/g)||[]).length,12);
assert.equal(get('datasetReview').hidden,false);assert.equal(review.datasets.length,2);assert(review.models.every(m=>m.score===null));assert(reviewMarkup(review).includes('试跑'));assert(!reviewMarkup(review).includes('undefined'));
context.verify('intentpilot','intent_accuracy');assert(!get('intentPilot').hidden);assert(get('tableWrap').hidden);
context.verify('intent','intent_accuracy');assert(get('intentPilot').innerHTML.includes('官方完整测试'));assert(get('intentPilot').innerHTML.includes('5500'));assert(!get('intentPilot').innerHTML.includes('WAY · PILOT'));
assert.equal((get('intentPilot').innerHTML.match(/class="intent-row /g)||[]).length,Object.keys(catalog.comprehensive.intent).length*2);
assert(!/undefined|NaN/.test(coverageMarkup(catalog)));assert.equal((coverageMarkup(catalog).match(/<tr><th scope=/g)||[]).length,23);
assert(coverageMarkup(catalog).includes('选项超限'));assert.equal(matrixColumns('overall').length,8);
assert.equal(pilot.capability_limits.length,2);assert(pilot.capability_limits.every(m=>m.score===null&&m.status==='native_interface_unsupported'));
assert(intentMarkup(pilot).includes('Intern-Decision-4B'));assert(intentMarkup(pilot).includes('StartLux-Decision-4B'));
for(const metric of ['intent_accuracy','intent_macro_f1']){const html=intentMarkup(pilot,{metric});assert(!/undefined|NaN/.test(html));assert.equal((html.match(/class="intent-row /g)||[]).length,Object.keys(pilot.models).length*2);assert(!html.includes('style='));}
assert.equal((intentMarkup(pilot,{family:'general'}).match(/class="intent-row /g)||[]).length,Object.keys(pilot.models).filter(id=>id.startsWith('qwen')).length*2);
assert(intentMarkup(pilot,{search:'nonexistent'}).includes('没有匹配'));assert(intentMarkup(null).includes('暂未加载'));
console.log('PASS: six rankings, sorting, 23/19 model coverage, search, family filter and dataset table');
const qrows=context.verify('legacy','overall_domain_equal').rows;
const speedRows=context.verify('speed','three_fields').rows;
const points=tradeoffRows(catalog,qrows,{view:'legacy',metric:'overall_domain_equal'});
assert.equal(points.length,14);
for(const p of points){assert.equal(p.x,catalog.speed[p.id].workloads.three_fields.mean_ms);assert.equal(p.y,catalog.quality.models[p.id].metrics.overall_domain_equal.score);}
for(const width of [349,900]){const svg=buildScatter(points,{width,label:id=>catalog.quality.models[id].label,kind:id=>/^(qwen|llama)/.test(id)?'general':'decision',yName:'领域等权综合分'});assert.equal((svg.match(/class="scatter-point"/g)||[]).length,14);assert(!svg.includes('NaN'));}
for(const r of speedRows){const c=matrixCell(r.m,'three_fields',{view:'speed'});assert.equal(c.score,catalog.speed[r.id].workloads.three_fields.mean_ms);}
const percentDomain=barDomain(qrows,'percent');assert.equal(percentDomain,1);
const bar=buildRanking(qrows.slice(0,6),{type:'percent',metricName:'综合分',label:id=>id,kind:()=> 'decision',max:1});
for(const r of qrows.slice(0,6))assert(bar.includes(`width="${r.c.score*1000}"`));
assert.equal(matrixColumns('transfer').length,4);
const completeRows=context.verify('overall','overall_domain_equal').rows;
for(const r of completeRows){assert.equal(r.m.classification_tasks,11);assert(!/^(startlux|intern)/.test(r.id));}
const fullPoints=tradeoffRows(catalog,completeRows,{view:'overall',metric:'overall_domain_equal'});
for(const p of fullPoints)assert.equal(p.y,catalog.comprehensive.models[p.id].metrics.overall_domain_equal.score);
console.log('PASS: zero-based bar geometry, six linked chart views, source-exact 14-point scatter, intervals and responsive coordinates');
