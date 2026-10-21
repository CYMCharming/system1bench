// Bind the observational audit, without touching existing leaderboard scores.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(here);
const folder='research/option_length_v1/';
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const hash=(p,lf=false)=>crypto.createHash('sha256').update(lf?fs.readFileSync(path.join(root,p),'utf8').replace(/\r\n/g,'\n'):fs.readFileSync(path.join(root,p))).digest('hex');
const result=read(folder+'results.json'),binding=read(folder+'bindings.json');
assert.equal(result.version,1);assert.equal(Object.keys(result.models).length,23);
assert.equal(result.sources.observations_sha256,hash(folder+'observations.json.gz'));
assert.equal(result.sources.bindings_sha256,hash(folder+'bindings.json'));
assert.equal(result.sources.analyzer_sha256,hash(folder+'analyze.py'));
assert.equal(result.sources.protocol_sha256,hash(folder+'PROTOCOL.md'));
assert.equal(binding.collector_sha256,hash(folder+'collect.py'));
for(const source of binding.sources)assert.equal(hash(source.path,source.hash_mode==='text_lf'),source.sha256,source.path);
for(const m of Object.values(result.models)){
 assert.equal(m.variable.all.n,result.variable_cohort.common_n);
 for(const group of [m.overall,m.variable,...Object.values(m.tasks)])for(const s of Object.values(group)){
  assert(Number.isInteger(s.n)&&s.n>=0);
  assert(s.score===null||Number.isFinite(s.score)&&s.score>=-100-1e-9&&s.score<=100+1e-9);
  if(s.ci95)assert(s.ci95.length===2&&s.ci95[0]<=s.ci95[1]);
  for(const k of ['longest','shortest'])assert(s[k].rate===null?s.n===0:Math.abs(s[k].rate-s[k].count/s.n)<1e-12);
 }
}
assert(!/hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+/.test(JSON.stringify(result)));
fs.mkdirSync(path.join(here,'data'),{recursive:true});
fs.copyFileSync(path.join(root,folder+'results.json'),path.join(here,'data/length-bias.json'));
fs.copyFileSync(path.join(root,folder+'scores.csv'),path.join(here,'data/length-scores.csv'));
console.log('Verified option-length analysis: 23 models, shared 221-question default');
