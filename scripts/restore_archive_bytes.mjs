// Mechanical line-ending repair only. Never replace actual user edits.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=process.cwd();
const args=['-c',`safe.directory=${root.replaceAll('\\','/')}`];
const prefix='api_results/jev-1.13.0/';
const files=execFileSync('git',[...args,'ls-files','--',prefix],{encoding:'utf8'}).trim().split('\n').filter(Boolean);
let restored=0;
for(const file of files){
 const absolute=path.resolve(root,file);
 if(!absolute.startsWith(path.resolve(root,prefix)+path.sep))throw Error('Outside archive');
 const original=execFileSync('git',[...args,'show','HEAD:'+file],{maxBuffer:128*1024*1024});
 const current=fs.readFileSync(absolute);
 if(current.equals(original))continue;
 const normalized=Buffer.from(current.toString('utf8').replaceAll('\r\n','\n'),'utf8');
 if(!normalized.equals(original))throw Error('Not a line-ending-only change: '+file);
 if(process.argv.includes('--restore'))fs.writeFileSync(absolute,original);
 restored++;
}
console.log(`${process.argv.includes('--restore')?'Restored':'Detected'} ${restored} line-ending-only differences; historical Git bytes retained`);
