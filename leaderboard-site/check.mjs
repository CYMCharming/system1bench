// DOM unit checks, not a substitute for browser-based visual verification.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const elements=new Map();
const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',hidden:false,value:'',addEventListener(){},showModal(){},close(){}});return elements.get(id);};
const catalog=JSON.parse(fs.readFileSync('data/catalog.json','utf8'));
let source=fs.readFileSync('app.js','utf8');
const context=vm.createContext({document:{getElementById:get,querySelectorAll:()=>[],addEventListener(){}},history:{replaceState(){}},location:{search:''},URLSearchParams,Date,fetch:async()=>({ok:true,json:async()=>catalog}),console});
await vm.runInContext(`(async()=>{${source}\n globalThis.verify=(v,m,f='all',s='')=>{view=v;metric=m;family=f;search=s;render();return {rows:rankedRows(),html:$('tableBody').innerHTML,empty:$('empty').hidden};};})()`,context);
assert.equal(get('modelCount').textContent,23);
for(const [v,m,n] of [['overall','overall_domain_equal',23],['domains','legal',23],['robustness','all_heads',23],['transfer','cladder',19],['probability','excess_brier',19],['speed','three_fields',Object.keys(catalog.speed).length]]){
 const r=context.verify(v,m);assert.equal(r.rows.length,n);assert(!r.html.includes('undefined'));assert(!r.html.includes('NaN'));
 const scores=r.rows.map(x=>x.c.score);for(let i=1;i<scores.length;i++)assert(['probability','speed'].includes(v)?scores[i]>=scores[i-1]:scores[i]<=scores[i-1]);
}
assert.equal(context.verify('overall','overall_domain_equal','all','nonexistent search').empty,false);
assert.equal(context.verify('overall','overall_domain_equal','general').html.match(/class="model-button"/g).length,9);
context.verify('datasets','');assert.equal((get('tableBody').innerHTML.match(/<tr>/g)||[]).length,10);
console.log('PASS: six rankings, sorting, 23/19 model coverage, search, family filter and dataset table');
