// DOM unit checks, not a substitute for browser-based visual verification.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {visualMarkup,buildRanking,barDomain,tradeoffRows,buildScatter,matrixCell,matrixColumns} from './charts.js';
const elements=new Map();
const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',hidden:false,value:'',addEventListener(){},showModal(){},close(){}});return elements.get(id);};
const catalog=JSON.parse(fs.readFileSync('data/catalog.json','utf8'));
let source=fs.readFileSync('app.js','utf8').replace(/^import .*;\r?\n/,'');
const context=vm.createContext({renderVisuals:(root,options)=>{root.innerHTML=visualMarkup(options);},document:{getElementById:get,querySelectorAll:()=>[],addEventListener(){}},history:{replaceState(){}},location:{search:''},URLSearchParams,Date,fetch:async()=>({ok:true,json:async()=>catalog}),console});
await vm.runInContext(`(async()=>{${source}\n globalThis.verify=(v,m,f='all',s='')=>{view=v;metric=m;family=f;search=s;render();return {rows:rankedRows(),html:$('tableBody').innerHTML,empty:$('empty').hidden};};})()`,context);
assert.equal(get('modelCount').textContent,23);
for(const [v,m,n] of [['overall','overall_domain_equal',23],['domains','legal',23],['robustness','all_heads',23],['transfer','cladder',19],['probability','excess_brier',19],['speed','three_fields',Object.keys(catalog.speed).length]]){
 const r=context.verify(v,m);assert.equal(r.rows.length,n);assert(!r.html.includes('undefined'));assert(!r.html.includes('NaN'));
 assert.equal((get('visuals').innerHTML.match(/class="ranked-row"/g)||[]).length,Math.min(6,n));
 assert(!get('visuals').innerHTML.includes('NaN'));assert(!get('visuals').innerHTML.includes('undefined'));
 const scores=r.rows.map(x=>x.c.score);for(let i=1;i<scores.length;i++)assert(['probability','speed'].includes(v)?scores[i]>=scores[i-1]:scores[i]<=scores[i-1]);
}
assert.equal(context.verify('overall','overall_domain_equal','all','nonexistent search').empty,false);
assert.equal(context.verify('overall','overall_domain_equal','general').html.match(/class="model-button"/g).length,9);
context.verify('datasets','');assert.equal((get('tableBody').innerHTML.match(/<tr>/g)||[]).length,10);
console.log('PASS: six rankings, sorting, 23/19 model coverage, search, family filter and dataset table');
const qrows=context.verify('overall','overall_domain_equal').rows;
const speedRows=context.verify('speed','three_fields').rows;
const points=tradeoffRows(catalog,qrows,{view:'overall',metric:'overall_domain_equal'});
assert.equal(points.length,14);
for(const p of points){assert.equal(p.x,catalog.speed[p.id].workloads.three_fields.mean_ms);assert.equal(p.y,catalog.quality.models[p.id].metrics.overall_domain_equal.score);}
for(const width of [349,900]){const svg=buildScatter(points,{width,label:id=>catalog.quality.models[id].label,kind:id=>/^(qwen|llama)/.test(id)?'general':'decision',yName:'领域等权综合分'});assert.equal((svg.match(/class="scatter-point"/g)||[]).length,14);assert(!svg.includes('NaN'));}
for(const r of speedRows){const c=matrixCell(r.m,'three_fields',{view:'speed'});assert.equal(c.score,catalog.speed[r.id].workloads.three_fields.mean_ms);}
const percentDomain=barDomain(qrows,'percent');assert.equal(percentDomain,1);
const bar=buildRanking(qrows.slice(0,6),{type:'percent',metricName:'综合分',label:id=>id,kind:()=> 'decision',max:1});
for(const r of qrows.slice(0,6))assert(bar.includes(`width="${r.c.score*1000}"`));
assert.equal(matrixColumns('transfer').length,4);
console.log('PASS: zero-based bar geometry, six linked chart views, source-exact 14-point scatter, intervals and responsive coordinates');
