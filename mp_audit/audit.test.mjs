import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {cost, gaps, sha, consume, probe, runAudit, metricTimes} from './audit.mjs';

// Given 费用每侧 10 bps、滑点每侧依次为 0/5/10 bps，When 独立计算成本，Then 往返成本四舍五入到 2 位依次为 **19.98 / 29.96 / 39.92 bps**；既有日志基准成本 **29.96 bps**，来源及公式有证据；任何“新成本下 G1/G2 是否通过”的未计算项为 `NOT_VERIFIED`。
test('GWT-1 成本', () => assert.deepEqual([0,5,10].map(cost), [19.98,29.96,39.92]));

// Given 固定研究提交中的注册表与 R3 输出，When 只读统计并核对，Then 注册表累计 **m=60**（`confirm-30pct=12`、`explore-70pct=12`、`explore-730d=36`），R3 头部 `m=60`、`rows=36`，单项阈值 `0.05/60≈0.0008333333`；历史漏登完整性单独标记 `NOT_VERIFIED`。Given 源不可访问或 m 不符，When 核验，Then 对应项明确 `NOT_VERIFIED`，绝不伪称一致或运行回测。
test('GWT-2 源缺失不伪证', async () => { const d=await mkdtemp(join(tmpdir(),'audit-')); try { const r=await runAudit({dir:d,source:async()=>{throw Error('missing')},fetcher:async()=>{throw Error('offline')}}); assert.match(r.report,/m 来源.*NOT_VERIFIED/); assert.match(r.report,/历史漏登.*NOT_VERIFIED/); } finally {await rm(d,{recursive:true,force:true});} });
test('GWT-2 m 不符不伪证', async () => {const d=await mkdtemp(join(tmpdir(),'audit-')); try {const r=await runAudit({dir:d,source:async n=>Buffer.from(n==='test_registry.json'?'{}':n==='run_r3_explore.txt'?'# window=explore-730d m=60\n# rows=36':'x'),fetcher:async()=>{throw Error('offline')}}); assert.match(r.report,/m 来源：NOT_VERIFIED/);} finally {await rm(d,{recursive:true,force:true});}});

// Given 内联模拟时间戳 `[0,300000,600000]` 与 `[0,86400000,172800000]`，When 运行 `node --test mp_audit/*.test.mjs`，Then 两组相邻间隔分别是 `[300000,300000]` 与 `[86400000,86400000]` 毫秒，分别标作仅对样本的 5m、1d；Given 实际两端点可访问，When 小样本实测，Then 报告包含实际时间戳、间隔、HTTP 状态、原始文件 SHA-256 和来源 URL，而非预填 5m/1d 结果。
test('GWT-3 样本间隔', () => {assert.deepEqual(gaps([0,300000,600000]),[300000,300000]); assert.deepEqual(gaps([0,86400000,172800000]),[86400000,86400000]);});
test('GWT-3 ZIP CSV 行序与 UTC', () => {const r=metricTimes(Buffer.from('create_time,symbol\n2026-10-01 00:10:00,BTCUSDT\n2026-10-01 00:00:00,BTCUSDT\n2026-10-01 00:05:00,BTCUSDT')); assert.equal(r.unsorted,true); assert.equal(new Date(r.values[0]).toISOString(),'2026-10-01T00:00:00.000Z'); assert.deepEqual(gaps(r.values),[300000,300000]);});

// Given 原始字节 `abc`，When 计算 SHA-256 并再读回哈希，Then 值为 `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` 且两次一致；真实保存样本必须有同等级的原始字节哈希核对，否则为 `NOT_VERIFIED`。
test('GWT-4 哈希', async () => {const d=await mkdtemp(join(tmpdir(),'audit-')); try {const p=join(d,'abc'); await writeFile(p,Buffer.from('abc')); assert.equal(sha(Buffer.from('abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'); assert.equal(sha(await readFile(p)),sha(Buffer.from('abc')));} finally {await rm(d,{recursive:true,force:true});}});

// Given mock HTTP 403、超时、空数组或无法解码的 ZIP，When 执行审计，Then 对应频率结论为 `NOT_VERIFIED` 并记录具体原因，不出现 `VERIFIED` 假阳性；其余可读静态来源仍能独立核验。
test('GWT-5 HTTP/格式失败', async () => {for (const [fetcher,kind,reason] of [[async()=>new Response('',{status:403}),'json','HTTP 403'],[async()=>{throw Error('timeout')},'json','timeout'],[async()=>new Response('[]'),'json','empty'],[async()=>new Response('bad zip'),'zip','ZIP']]) {const r=await probe('mock',kind,fetcher,{used:0,max:100}); assert.equal(r.state,'NOT_VERIFIED'); assert.match(r.reason,new RegExp(reason));}});

// Given 模拟累计下载预算为 10 字节且即将读取第 11 字节，When 消费响应流，Then 中止、退出码 **1**、错误标识 `AUDIT_LIMIT`，无超额持久化样本，原文件 SHA-256 不变；生产配置固定 **20,971,520 字节**，预算涵盖所有外部请求。
test('GWT-6 累计预算', async () => {const b={used:0,max:10}; await assert.rejects(consume(new Response('12345678901').body,b),/AUDIT_LIMIT/); assert.equal(b.used,10);});
test('GWT-6 越界不发布', async () => {const d=await mkdtemp(join(tmpdir(),'audit-')); try {const marker=join(d,'old'); await writeFile(marker,'old'); const before=sha(await readFile(marker)); await assert.rejects(runAudit({dir:d,max:10,source:async()=>Buffer.from('x'),fetcher:async()=>new Response('12345678901')}),/AUDIT_LIMIT/); assert.equal(sha(await readFile(marker)),before); await assert.rejects(readFile(join(d,'oi-5m.json')),{code:'ENOENT'});} finally {await rm(d,{recursive:true,force:true});}});

// Given `mp_audit/R3-V-REPORT.md` 或目标样本已存在，When 再执行审计，Then 退出码 **1**、错误 `AUDIT_OUTPUT_EXISTS`，该文件 SHA-256 前后相同、全部既有测试文件不变。Given 成功完成一次审计，When 检查 Git diff 与测试文件哈希，Then **白名单外变化文件数=0**，`test/fetch-history.test.mjs` 的前后 SHA-256 一致，新增行数（含测试）**≤300**。
test('GWT-7 目标冲突', async () => {const d=await mkdtemp(join(tmpdir(),'audit-')); try {const p=join(d,'R3-V-REPORT.md'); await writeFile(p,'old'); await assert.rejects(runAudit({dir:d,source:async()=>'',fetcher:async()=>{throw Error('offline')}}),/AUDIT_OUTPUT_EXISTS/); assert.equal(await readFile(p,'utf8'),'old');} finally {await rm(d,{recursive:true,force:true});}});
test('GWT-7 样本冲突', async () => {const d=await mkdtemp(join(tmpdir(),'audit-')); try {const p=join(d,'metrics-2026-10-01.zip'); await writeFile(p,'old'); await assert.rejects(runAudit({dir:d,source:async()=>'',fetcher:async()=>{throw Error('offline')}}),/AUDIT_OUTPUT_EXISTS/); assert.equal(await readFile(p,'utf8'),'old');} finally {await rm(d,{recursive:true,force:true});}});
