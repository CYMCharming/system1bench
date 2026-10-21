import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import './prepare-length.mjs';
const here = path.dirname(fileURLToPath(import.meta.url));
const catalog = JSON.parse(fs.readFileSync(path.join(here,'data/catalog.json'),'utf8'));
assert.equal(catalog.version,1);
assert(Object.keys(catalog.quality.models).length >= 18);
assert.equal(catalog.common.complete_models,23);assert.equal(Object.keys(catalog.common.models).length,23);
fs.mkdirSync(path.join(here,'dist'),{recursive:true});
for (const f of ['index.html','style.css','viz.css','review.css','review.js','intent.css','intent.js','coverage.css','coverage.js','research.css','research.js','length.css','length.js','app.js','charts.js','favicon.svg']) fs.copyFileSync(path.join(here,f),path.join(here,'dist',f));
for(const f of ['length-bias.json','length-scores.csv'])fs.copyFileSync(path.join(here,'data',f),path.join(here,'dist',f));
fs.copyFileSync(path.join(here,'data/catalog.json'),path.join(here,'dist/catalog.json'));
const commonCsv=fs.readFileSync(path.join(here,'data/common-scores.csv'));
assert.equal(crypto.createHash('sha256').update(commonCsv).digest('hex'),catalog.sources.find(s=>s.path==='research/common_suite_v1/scores.csv').sha256);
fs.writeFileSync(path.join(here,'dist/common-scores.csv'),commonCsv);
fs.copyFileSync(path.join(here,'data/review.json'),path.join(here,'dist/review.json'));
fs.copyFileSync(path.join(here,'data/intent-pilot.json'),path.join(here,'dist/intent-pilot.json'));
const research=JSON.parse(fs.readFileSync(path.join(here,'data/research.json'),'utf8'));
assert.equal(research.version,1);assert.equal(research.figures.length,5);
for(const f of research.figures)for(const [ext,url]of Object.entries(f.assets)){
  const p=path.join(here,url.slice(1));
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),f.asset_sha256[ext],`Research figure integrity: ${url}`);
}
fs.copyFileSync(path.join(here,'data/research.json'),path.join(here,'dist/research.json'));
fs.cpSync(path.join(here,'assets/paper'),path.join(here,'dist/assets/paper'),{recursive:true});
console.log('Built System1Bench leaderboard');
