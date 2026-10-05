import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)),'dist');
http.createServer((req,res) => {
  const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const target = path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if (!target.startsWith(root+path.sep) || !fs.existsSync(target)) {res.writeHead(404); res.end('Not found'); return;}
  res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.svg':'image/svg+xml'})[path.extname(target)]??'application/octet-stream');
  fs.createReadStream(target).pipe(res);
}).listen(4173,'127.0.0.1',()=>console.log('Leaderboard preview: http://127.0.0.1:4173/'));
