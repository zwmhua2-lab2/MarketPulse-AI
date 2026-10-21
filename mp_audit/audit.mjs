import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFile, writeFile, link, unlink, stat} from 'node:fs/promises';
import {join} from 'node:path';
import {inflateRawSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';

const COMMIT='5cdc62ddcf42814130440ff47a47a1c3c9648b25';
const FILES=['kernel.py','cost_breakdown.py','cost_breakdown.txt','test_registry.json','run_r3_explore.txt','data_availability.txt'];
const URLS=['https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=5','https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-10-01.zip'];
export const sha=b=>createHash('sha256').update(b).digest('hex');
export const cost=s=>Number(((1-(1-s/10000)*(1-10/10000)/((1+s/10000)*(1+10/10000)))*10000).toFixed(2));
export const gaps=xs=>xs.slice(1).map((x,i)=>x-xs[i]);
const sourceDefault=async name=>execFileSync('git',['show',`${COMMIT}:research/${name}`],{maxBuffer:4*1024*1024});
const fail=(code)=>{throw Error(code)};

export async function consume(stream,budget,writeChunk) {
  const parts=[]; let size=0;
  for await (const part of stream) {
    const b=Buffer.from(part); const remaining=budget.max-budget.used;
    const chunk=b.length>remaining?b.subarray(0,remaining):b;
    budget.used+=chunk.length; size+=chunk.length; parts.push(chunk);
    if(writeChunk) await writeChunk(chunk);
    if(b.length>remaining) fail('AUDIT_LIMIT');
  }
  return Buffer.concat(parts,size);
}

export function zipCsv(raw) {
  if(raw.length>2*1024*1024) fail('ZIP compressed too large');
  const e=raw.lastIndexOf(Buffer.from([0x50,0x4b,0x05,0x06]));
  if(e<0 || e+22>raw.length) fail('ZIP end missing');
  const n=raw.readUInt16LE(e+10), start=raw.readUInt32LE(e+16);
  let p=start;
  for(let i=0;i<n;i++) {
    if(p+46>raw.length || raw.readUInt32LE(p)!==0x02014b50) fail('ZIP central invalid');
    const method=raw.readUInt16LE(p+10), compressed=raw.readUInt32LE(p+20), expanded=raw.readUInt32LE(p+24);
    const nameLen=raw.readUInt16LE(p+28), extra=raw.readUInt16LE(p+30), comment=raw.readUInt16LE(p+32), offset=raw.readUInt32LE(p+42);
    const name=raw.subarray(p+46,p+46+nameLen).toString('utf8'); p+=46+nameLen+extra+comment;
    if(!name.endsWith('.csv')) continue;
    if(compressed>2*1024*1024 || expanded>5*1024*1024) fail('ZIP size limit');
    if(offset+30>raw.length || raw.readUInt32LE(offset)!==0x04034b50) fail('ZIP local invalid');
    const at=offset+30+raw.readUInt16LE(offset+26)+raw.readUInt16LE(offset+28);
    if(at+compressed>raw.length) fail('ZIP truncated');
    const bytes=raw.subarray(at,at+compressed);
    const csv=method===0?bytes:method===8?inflateRawSync(bytes,{maxOutputLength:5*1024*1024}):fail('ZIP method');
    if(csv.length!==expanded) fail('ZIP length mismatch');
    return csv;
  }
  fail('ZIP CSV missing');
}

export function metricTimes(csv) {
  const lines=csv.toString('utf8').trim().split(/\r?\n/), col=lines[0].split(',').indexOf('create_time');
  if(col<0 || lines.length<3) fail('ZIP create_time missing or short');
  const original=lines.slice(1).map(line=>{const s=line.split(',')[col], n=Date.parse(s.replace(' ','T')+'Z'); if(!Number.isFinite(n)) fail('ZIP invalid create_time'); return n;});
  return {values:[...original].sort((a,b)=>a-b),unsorted:original.some((x,i)=>i>0&&x<original[i-1])};
}

function timestamps(raw,kind) {
  if(kind==='json') {
    const rows=JSON.parse(raw.toString('utf8'));
    if(!Array.isArray(rows)||rows.length<2) fail('empty or short array');
    return rows.map(x=>{if(!Number.isSafeInteger(x.timestamp)) fail('invalid timestamp'); return x.timestamp;});
  }
  const csv=zipCsv(raw); return {...metricTimes(csv),csv};
}

export async function probe(url,kind,fetcher,budget) {
  let status='NO_RESPONSE', bytes=0;
  try {
    const response=await fetcher(url,{signal:AbortSignal.timeout(10000)}); status=response.status;
    const raw=await consume(response.body,budget); bytes=raw.length;
    if(!response.ok) fail(`HTTP ${status}`);
    const parsed=timestamps(raw,kind), values=kind==='zip'?parsed.values:parsed, diffs=gaps(values);
    return {state:'VERIFIED',status,raw,hash:sha(raw),csv:parsed.csv,values,diffs,unsorted:parsed.unsorted,bytes:raw.length,url};
  } catch(e) {
    if(e.message==='AUDIT_LIMIT') throw e;
    return {state:'NOT_VERIFIED',status,bytes,reason:e.message,url};
  }
}

async function publish(dir,name,bytes) {
  const target=join(dir,name), temporary=join(dir,`.${name}.${process.pid}.tmp`);
  await writeFile(temporary,bytes,{flag:'wx'});
  try {await link(temporary,target);} catch(e) {if(e.code==='EEXIST') fail('AUDIT_OUTPUT_EXISTS'); throw e;}
  finally {await unlink(temporary);}
  if(sha(await readFile(target))!==sha(bytes)) fail('AUDIT_HASH_MISMATCH');
}

export async function runAudit({dir=join(process.cwd(),'mp_audit'),source=sourceDefault,fetcher=fetch,max=20971520,testResult='NOT_VERIFIED'}={}) {
  const names=['R3-V-REPORT.md','oi-5m.json','metrics-2026-10-01.zip'];
  for(const name of names) {try {await stat(join(dir,name)); fail('AUDIT_OUTPUT_EXISTS');} catch(e) {if(e.message==='AUDIT_OUTPUT_EXISTS') throw e; if(e.code!=='ENOENT') throw e;}}
  const started=new Date(), budget={used:0,max}, originals={};
  for(const name of FILES) {try {const b=await source(name); originals[name]={bytes:b,hash:sha(b)};} catch(e) {originals[name]={error:e.message};}}
  const lines=['# R3 第 4/5 项独立审计',`开始 UTC：${started.toISOString()}`,`固定来源：研究提交 \`${COMMIT}\`（本地 Git 对象只读）`,'','## 固定源原始字节 SHA-256'];
  for(const name of FILES) {
    let second='NOT_VERIFIED';
    if(originals[name].hash) {try {second=sha(await source(name))===originals[name].hash?'一致':'不一致';} catch(e) {second=`NOT_VERIFIED (${e.message})`;}}
    lines.push(`- research/${name}: ${originals[name].hash??`NOT_VERIFIED (${originals[name].error})`}；二次读取 ${second}`);
  }
  const c=originals['cost_breakdown.txt']?.bytes?.toString('utf8')??'', k=originals['kernel.py']?.bytes?.toString('utf8')??'';
  const costOk=/29\.96 bps/.test(c)&&/BTC-USDT\s+5m\s+0\.02\s+29\.96\s+-29\.94/.test(c)&&/FEE_RATE = 0\.001/.test(k)&&/SLIPPAGE_FRACTION = 5 \/ 10_000/.test(k);
  lines.push('','## 成本敏感性',`- ${costOk?'VERIFIED':'NOT_VERIFIED'}：K=(1-s)(1-f)/((1+s)(1+f))，f=10/10000；s=0/5/10 bps → 往返 ${[0,5,10].map(cost).join(' / ')} bps。${costOk?'cost_breakdown.txt 的既有基准 29.96 bps；BTC 5m gross 0.02、net -29.94 bps。':'既有基准或公式来源无法核验。'}`,'- 新成本下 G1/G2：NOT_VERIFIED（没有逐笔原始收益序列，未重跑回测）。');
  let mOk=false, counts={}, mReason='source missing';
  try {const registry=JSON.parse(originals['test_registry.json'].bytes.toString('utf8')), keys=Object.keys(registry), r3=originals['run_r3_explore.txt'].bytes.toString('utf8');
    counts=keys.reduce((out,key)=>{const window=key.split('|')[0];out[window]=(out[window]??0)+1;return out;},{});
    const header=r3.match(/^# window=.*\bm=(\d+)/m), rows=r3.match(/^# rows=(\d+)/m);
    mOk=keys.length===60&&counts['confirm-30pct']===12&&counts['explore-70pct']===12&&counts['explore-730d']===36&&header?.[1]==='60'&&rows?.[1]==='36';
    mReason=`distinct keys=${keys.length}, windows=${JSON.stringify(counts)}, R3 header m=${header?.[1]??'missing'}, rows=${rows?.[1]??'missing'}, 0.05/60=${0.05/60}`;
  } catch(e) {mReason=e.message;}
  lines.push('','## 累计比较次数 m',`- m 来源：${mOk?'VERIFIED':'NOT_VERIFIED'}；${mReason}`,'- 历史漏登完整性：NOT_VERIFIED（注册表不能证明未入账比较不存在）。');
  const samples=[];
  for(const [i,kind] of ['json','zip'].entries()) {
    const r=await probe(URLS[i],kind,fetcher,budget); samples.push(r);
    lines.push('','## '+(i?'日归档 metrics ZIP':'OI 5m REST'),`- ${r.state}；URL：${r.url}；HTTP：${r.status}；响应 ${r.bytes} 字节；${r.reason??`原始 SHA-256 ${r.hash}；记录 ${r.values.length} 条；时间戳首尾 ${r.values.slice(0,5).join(', ')} ... ${r.values.slice(-5).join(', ')}；相邻差值 ${JSON.stringify(Object.fromEntries([...new Set(r.diffs)].map(x=>[x,r.diffs.filter(y=>y===x).length])))} ms（值:次数）；覆盖 ${new Date(r.values[0]).toISOString()} .. ${new Date(r.values.at(-1)).toISOString()}；${r.unsorted?'原始 CSV 行序非时间顺序，按时间排序后计算；':''}仅此样本粒度 ${r.diffs.every(x=>x===300000)?'5m':r.diffs.every(x=>x===86400000)?'1d':'其他/不一致'}`}`);
    if(r.csv) lines.push(`- 解压后 CSV SHA-256：${sha(r.csv)}；仅内存解压。`);
  }
  lines.push('','## 范围与复核','- 资金费率、大小户比例、主动成交、清算、完整回溯深度：NOT_VERIFIED。',`- 测试：\`node --test mp_audit/*.test.mjs\`；${testResult}。`,'- 白名单 diff：仅新增 `mp_audit/**`；最终以 `git diff --name-status origin/main` 与未跟踪清单复核。',`- 累计真实下载响应字节：${budget.used} / ${max}。`,`- 结束 UTC：${new Date().toISOString()}；耗时 ${Date.now()-started.getTime()} ms。`);
  for(const [i,r] of samples.entries()) if(r.raw) await publish(dir,names[i+1],r.raw);
  for(const [i,r] of samples.entries()) if(r.raw) lines.push(`- ${names[i+1]} 二次读取 SHA-256：${sha(await readFile(join(dir,names[i+1])))}；与原始哈希${sha(await readFile(join(dir,names[i+1])))===r.hash?'一致':'不一致'}。`);
  const report=lines.join('\n')+'\n'; await publish(dir,names[0],Buffer.from(report));
  return {report,budget};
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  let testResult='NOT_VERIFIED';
  try {const output=execFileSync(process.execPath,['--test','mp_audit/audit.test.mjs'],{encoding:'utf8'}); testResult=(output.match(/tests \d+/)?.[0]??'tests unknown')+', '+(output.match(/pass \d+/)?.[0]??'pass unknown')+', '+(output.match(/fail \d+/)?.[0]??'fail unknown');}
  catch(e) {testResult=`FAIL (${e.message})`;}
  runAudit({testResult}).then(()=>process.stdout.write('AUDIT_COMPLETE\n')).catch(e=>{process.stderr.write(`${e.message}\n`);process.exitCode=1;});
}
