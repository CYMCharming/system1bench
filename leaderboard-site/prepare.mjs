// Bind only verified, public research artifacts into the standalone website.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)), root = path.dirname(here);
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, p))).digest('hex');
// Git may check historical Python source out as CRLF on Windows. Execution
// source identities use the LF bytes on Linux, not a platform checkout's EOL.
const sourceHash = p => crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p),'utf8').replace(/\r\n/g,'\n')).digest('hex');
const previousPath = 'research/leaderboard_v3/scores.json';
let quality = read(previousPath);
let qualityPath = previousPath;
if (fs.existsSync(path.join(root, 'research/model_expansion_v3/scores.json'))) {
  const extended = read('research/model_expansion_v3/scores.json');
  assert.equal(extended.previous_scores_sha256, hash(previousPath));
  for (const [name, value] of Object.entries(quality.models)) assert.deepEqual(extended.models[name], value);
  quality = extended; qualityPath = 'research/model_expansion_v3/scores.json';
}
const transferPath = 'research/startlux_transfer_v1/summary.json';
const transfer = read(transferPath);
assert.equal(transfer.complete, true);
const additions = fs.existsSync(path.join(root, 'research/model_expansion_v3/summary.json')) ? read('research/model_expansion_v3/summary.json') : null;
const transferModels = {...transfer.transfer, ...(additions?.complete ? additions.transfer : {})};
const sources = [qualityPath, transferPath];
if (additions?.complete) sources.push('research/model_expansion_v3/summary.json');
if (additions?.complete) {
  assert.equal(quality.expansion_summary_sha256,hash('research/model_expansion_v3/summary.json'));
  for (const panel of ['main','transfer']) for (const [model, entry] of Object.entries(additions[panel])) {
    const folder=`research/model_expansion_v3/results/${panel}/${model}`;
    const metadata=read(`${folder}/metadata.json`);
    assert.equal(metadata.status,'DONE');assert.equal(metadata.errors,0);
    assert.equal(hash(`${folder}/raw.jsonl`),entry.receipt.raw_sha256);
    assert.equal(hash(`${folder}/metadata.json`),entry.receipt.metadata_sha256);
    assert.equal(metadata.count,panel==='main'?4905:1152);
    assert.equal(hash(`research/model_expansion_v3/admissions/${model}.json`),additions.admissions[model]);
  }
}
const speed = {};
const speedFolder = path.join(root, 'research/latency_v2/results');
let deviceUuid = null;
if (fs.existsSync(speedFolder)) for (const name of fs.readdirSync(speedFolder)) {
  const rel = `research/latency_v2/results/${name}`;
  if (!fs.existsSync(path.join(root, rel, 'summary.json'))) continue;
  const summary = read(`${rel}/summary.json`), metadata = read(`${rel}/metadata.json`);
  assert.equal(summary.status, 'DONE');
  assert.equal(summary.model, name);
  for (const [file, key] of [['raw.jsonl','raw_sha256'],['metadata.json','metadata_sha256'],['telemetry.json','telemetry_sha256']]) assert.equal(hash(`${rel}/${file}`), summary[key]);
  assert.equal(metadata.contract.protocol_sha256, hash('research/latency_v2/PROTOCOL.md'));
  assert.equal(metadata.contract.runner_sha256, sourceHash('research/latency_v2/measure.py'));
  assert.equal(metadata.contract.adapter_sha256, sourceHash('research/model_expansion_v3/adapter.py'));
  assert.equal(metadata.contract.native_adapter_sha256, sourceHash('research/startlux_transfer_v1/adapter.py'));
  assert.equal(metadata.contract.shared_adapter_sha256, sourceHash('system1bench/decision_models.py'));
  assert.equal(metadata.contract.expansion_adapter_sha256, sourceHash('research/model_expansion_v2/adapter.py'));
  deviceUuid ??= metadata.contract.device.uuid;
  assert.equal(metadata.contract.device.uuid, deviceUuid);
  const raw = fs.readFileSync(path.join(root, rel, 'raw.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(raw.length, 300);
  for (const [workload, cell] of Object.entries(summary.workloads)) {
    const rows = raw.filter(r => r.workload === workload);
    assert.equal(rows.length, 100);
    assert.equal(cell.n,100);
    assert(cell.cpu_contention.other_busy_fraction_on_worker_cores<=.15);
    assert(cell.cpu_contention.smt_sibling_busy_fraction<=.15);
    assert(rows.every(r => r.valid && r.milliseconds > 0 && Number.isFinite(r.milliseconds)));
    assert.equal(new Set(rows.map(r => `${r.round}:${r.index}`)).size, 100);
    const mean = rows.reduce((sum,r) => sum+r.milliseconds,0)/100;
    assert(Math.abs(mean-cell.mean_ms) < 1e-9);
  }
  speed[name] = {...summary, hardware:metadata.contract.device.name,
    adapter:metadata.contract.adapter.adapter, dtype:metadata.contract.adapter.dtype,
    source:`${rel}/summary.json`, protocol:'research/latency_v2/PROTOCOL.md'};
  sources.push(`${rel}/summary.json`);
}
const completionPath='research/evaluation_completion_v1/results.json';
const comprehensive=fs.existsSync(path.join(root,completionPath))?read(completionPath):null;
if(comprehensive){
 assert.equal(comprehensive.old_quality_sha256,hash(qualityPath));
 assert.equal(comprehensive.manifest_sha256,hash('research/evaluation_completion_v1/manifest.json'));
 assert.equal(Object.keys(comprehensive.coverage).length,23);
 for(const item of Object.values(comprehensive.projections))assert.equal(hash(item.path),item.sha256);
 for(const [id,m] of Object.entries(comprehensive.models)){
  assert(m.complete&&m.classification_tasks===11);assert.equal(comprehensive.coverage[id].status,'complete');
  assert.equal(Object.keys(m.domain_scores).length,8);
  assert(Math.abs(Object.values(m.domain_scores).reduce((s,c)=>s+c.score,0)/8-m.metrics.overall_domain_equal.score)<1e-12);
 }
 Object.assign(transferModels,comprehensive.transfer_additions);sources.push(completionPath,'research/evaluation_completion_v1/manifest.json');
 if(comprehensive.supplement_manifest){assert.equal(hash(comprehensive.supplement_manifest.path),comprehensive.supplement_manifest.sha256);sources.push(comprehensive.supplement_manifest.path,'research/evaluation_completion_v2/PROTOCOL.md');}
 if(comprehensive.execution_shard_manifest){assert.equal(hash(comprehensive.execution_shard_manifest.path),comprehensive.execution_shard_manifest.sha256);sources.push(comprehensive.execution_shard_manifest.path,'research/evaluation_completion_v3/PROTOCOL.md');}
}
const catalog = {version:1, generatedAt:new Date().toISOString(), quality, comprehensive, transfer:transferModels, speed,
  pendingModels:additions?.pending ?? [], speedExpected:14,
  sources:sources.map(p => ({path:p,sha256:hash(p),url:`https://github.com/CYMCharming/system1bench/blob/main/${p}`}))};
assert(!/hf_[A-Za-z0-9]{25,}|apikey_[A-Za-z0-9_]+/.test(JSON.stringify(catalog)));
fs.mkdirSync(path.join(here,'data'),{recursive:true});
fs.writeFileSync(path.join(here,'data/catalog.json'),JSON.stringify(catalog,null,2)+'\n');
console.log('Prepared verified website data:',Object.keys(quality.models).length,'quality,',Object.keys(transferModels).length,'transfer,',Object.keys(speed).length,'speed models');
