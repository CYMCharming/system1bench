// Text-free, hash-bound reference token diagnostics; existing scores stay intact.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(here);
const folder='research/option_length_tokens_v1/',parent='research/option_length_v1/';
const bytes=p=>fs.readFileSync(path.join(root,p));
const hash=p=>crypto.createHash('sha256').update(bytes(p)).digest('hex');
const textHash=p=>crypto.createHash('sha256').update(bytes(p).toString('utf8').replace(/\r\n/g,'\n')).digest('hex');
const read=p=>JSON.parse(bytes(p));
const result=read(folder+'results.json'),binding=read(folder+'bindings.json');
const raw=zlib.gunzipSync(bytes(folder+'token_lengths.json.gz')),projection=JSON.parse(raw);
assert.equal(result.version,1);assert.equal(binding.version,1);assert.equal(projection.version,1);
for(const [key,file]of Object.entries({observations_sha256:parent+'observations.json.gz',token_lengths_sha256:folder+'token_lengths.json.gz',bindings_sha256:folder+'bindings.json',parent_bindings_sha256:parent+'bindings.json',analyzer_sha256:folder+'analyze.py',protocol_sha256:folder+'PROTOCOL.md',dependency_sha256:parent+'analyze.py'}))assert.equal(result.sources[key],hash(file),file);
assert.equal(binding.collector_sha256,hash(folder+'collect_tokens.py'));
assert.equal(binding.source_observations.sha256,hash(parent+'observations.json.gz'));
assert.equal(binding.artifact.sha256,hash(folder+'token_lengths.json.gz'));
assert.equal(binding.artifact.uncompressed_sha256,crypto.createHash('sha256').update(raw).digest('hex'));
assert.equal(projection.source_observations_sha256,binding.source_observations.sha256);
assert.deepEqual(projection.tokenizers,binding.tokenizers);
assert.equal(Object.keys(projection.lengths).length,binding.candidate_count);
assert.equal(binding.candidate_count,893);assert.equal(binding.item_count,2310);
for(const [key,entry]of Object.entries(result.tokenizers)){
 const metadata=projection.tokenizers[key];
 assert.deepEqual(entry.metadata,metadata);assert.equal(metadata.reference_only,true);
 assert.equal(metadata.native_model_tokens,false);assert.equal(metadata.add_special_tokens,false);
 assert.equal(metadata.truncation,false);assert.match(metadata.revision,/^[0-9a-f]{40}$/);
 assert.equal(textHash(metadata.admission_source),metadata.admission_sha256);
 assert.equal(Object.keys(entry.models).length,23);
 for(const row of Object.values(entry.models))for(const scope of [row.variable,row.overall,...Object.values(row.tasks)])for(const stats of Object.values(scope)){
  assert.equal(stats.n,stats.absolute.n);
  for(const value of [stats.score,stats.character.score,stats.absolute.excess])assert(value===null||Number.isFinite(value));
  assert(stats.score===null||stats.score>=-100-1e-9&&stats.score<=100+1e-9);
  if(stats.ci95)assert(stats.ci95.length===2&&stats.ci95[0]<=stats.ci95[1]);
  for(const bin of stats.absolute.bins){
   assert.equal(bin.n,stats.n);assert(bin.chance===null||bin.chance>=0&&bin.chance<=1);
   assert(bin.ratio===null?bin.chance===0||bin.chance===null:Math.abs(bin.ratio-bin.rate/bin.chance)<1e-10);
  }
 }
 for(const row of Object.values(entry.models))assert.equal(row.variable.all.n,entry.cohorts.variable.n);
}
assert.equal(result.default_tokenizer,'qwen3');assert.equal(result.tokenizers.qwen3.cohorts.variable.n,207);
assert.equal(result.reference_sensitivity.n,202);
assert(!/hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+/.test(JSON.stringify(result)));
fs.mkdirSync(path.join(here,'data'),{recursive:true});
// Whitespace-only compaction; all fields and exact numeric values remain intact.
fs.writeFileSync(path.join(here,'data/length-tokens.json'),JSON.stringify(result)+'\n');
fs.copyFileSync(path.join(root,folder+'scores.csv'),path.join(here,'data/length-token-scores.csv'));
console.log('Verified absolute + relative reference-token lengths: 23 models, 207 shared default questions');
