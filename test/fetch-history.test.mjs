import { test } from 'node:test';
// - **GWT-01（C1/C3/X1/X2，端到端）**：Given 固定运行时钟 `2026-10-21T07:47:00.000Z`、模拟 Binance 返回 9 页有效 12 字段 K 线（前 8 页各 1000 条，最后一页 640 条；每条 OHLCV 固定为 `1.00,2.00,0.50,1.50,10.00`），When 执行抓取并保存，Then 只向指定端点发出 9 次 GET、每页 `limit≤1000`、每次带 `BTCUSDT/5m`，CSV 表头精确为 `open_time,open,high,low,close,volume`，数据恰好 8640 行，首行 `1789976700000,1.00,2.00,0.50,1.50,10.00`，末行 `1792568400000,1.00,2.00,0.50,1.50,10.00`，时间步长 `300000` 毫秒，退出码 0。
// - **GWT-02（C1/C2/C3）**：Given 某页请求持续无响应、目标目录中已有已验证的完好 CSV，When 超过 10000 ms（允许模拟时钟）且请求被中止，Then 只请求 1 次、不重试、stderr=`FETCH_ERROR\n`、退出码 1、旧 CSV SHA-256 与失败前相同。
// - **GWT-03（C1/C2/C3）**：Given 任一分页返回 HTTP 429、418、500 或请求抛网络错误（分别测试），When 执行抓取，Then 遇错误立即停止、不重试，stderr=`FETCH_ERROR\n`、退出码 1、旧 CSV 字节不变。
// - **GWT-04（C2/C3/X1）**：Given 8640 条中缺少恰好一根 K 线（例如跨页漏掉第 1000 根）、旧 CSV 完好，When 抓取，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-05（C2/C3/X1）**：Given 第 2 页第一根与第 1 页最后一根开盘时间相同（重复分页边界）、旧 CSV 完好，When 抓取，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-06（C2/C3/X2）**：Given 响应含 11 字段 K 线、非数字开盘价、`high<low` 或负成交量（逐例），旧 CSV 完好，When 抓取，Then 每例退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-07（C2/C3）**：Given 所有行情数据有效、旧 CSV 完好，但临时文件写入或 rename 被模拟为失败（逐例），When 保存，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变，正式文件无半截新数据。
// - **GWT-08（C3）**：Given CLI 参数为 `--save`，When 执行，Then 在网络调用及文件写入前退出 1，stderr=`FETCH_ERROR\n`，旧 CSV 不变。
// - **GWT-09（C5，终审清单）**：Given 对照最新 `main` 的 PR Diff，When 检查 Files changed，Then 只包含 `fetch-history.mjs`、`test/fetch-history.test.mjs`，以及可选的 `ARCHITECTURE.md` 第 7 节一行记录；`.github/**`、`AGENTS.md`、测试配置和依赖文件改动数为 0。
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';

test('QA 回归：测试路径必须为 test/ 且不存在 tests/', () => {
  assert.ok(existsSync('test/fetch-history.test.mjs'));
  assert.equal(existsSync('tests'), false);
});
test('QA 回归：GWT-09 必须拒绝未跟踪文件', async () => {
  const probe = `.gwt09-untracked-${process.pid}`;
  try {
    await writeFile(probe, 'QA probe', {flag: 'wx'});
    const env = {...process.env};
    delete env.NODE_TEST_CONTEXT;
    const result = spawnSync(process.execPath,
      ['--test', '--test-name-pattern=^GWT-09$', 'test/fetch-history.test.mjs'], {encoding: 'utf8', env});
    assert.equal(result.status, 1);
    assert.match(result.stdout + result.stderr, new RegExp(probe));
  } finally { await rm(probe, {force: true}); }
});

const script = resolve('fetch-history.mjs');
const header = 'open_time,open,high,low,close,volume';
const start = 1789976700000;
const end = 1792568700000;
const rows = Array.from({ length: 8640 }, (_, i) =>
  [start + i * 300000, '1.00', '2.00', '0.50', '1.50', '10.00', start + (i + 1) * 300000 - 1, '0', 1, '0', '0', '0']);
const old = header + '\n' + rows.map(r => r.slice(0, 6).join(',')).join('\n') + '\n';
assert.equal(old.trim().split('\n').length, 8641);
rows.forEach((r, i) => assert.equal(r[0], start + i * 300000));
const hash = data => createHash('sha256').update(data).digest('hex');

async function run(mode = 'ok', args = [], existing = true) {
  const dir = await mkdtemp(join(tmpdir(), 'history-test-'));
  try {
    if (existing) await writeFile(join(dir, 'history-5m.csv'), old);
    const preload = `
import fs from 'node:fs/promises';
import { syncBuiltinESMExports } from 'node:module';
const rows = ${JSON.stringify(rows)};
const mode = ${JSON.stringify(mode)};
const log = entry => fs.appendFile('calls.jsonl', JSON.stringify(entry) + '\\n');
Date.now = () => Date.parse('2026-10-21T07:47:00.000Z');
let count = 0;
const originalWrite = fs.writeFile;
fs.writeFile = async (...args) => {
  await log({write: String(args[0])});
  if (mode === 'write') { await originalWrite(args[0], 'partial'); throw Error('disk'); }
  return originalWrite(...args);
};
if (mode === 'rename') fs.rename = async () => { throw Error('rename'); };
syncBuiltinESMExports();
globalThis.fetch = async (url, options) => {
  const u = new URL(url);
  await log({url: String(url), method: options?.method, redirect: options?.redirect});
  count++;
  if (mode === 'timeout') return new Promise((resolve, reject) => {
    const hold = setInterval(() => {}, 1000);
    options.signal.addEventListener('abort', async () => {
      await log({aborted: true}); clearInterval(hold); reject(Error('timeout'));
    }, {once:true});
  });
  if (count === 2 && mode === 'network') throw Error('network');
  if (count === 2 && ['429','418','500'].includes(mode)) return {status:Number(mode)};
  const offset = (Number(u.searchParams.get('startTime')) - ${start}) / 300000;
  const data = rows.slice(offset, offset + Number(u.searchParams.get('limit')));
  if (count === 2 && mode === 'missing') data.shift();
  if (count === 2 && mode === 'duplicate') data[0] = rows[999];
  if (mode === 'fields') data[0].pop();
  if (mode === 'price') data[0][1] = 'oops';
  if (mode === 'range') data[0][2] = '0.1';
  if (mode === 'volume') data[0][5] = '-1';
  if (mode === 'timestamp') data[0][0] += 1;
  if (mode === 'zero') data[0][1] = '0.00';
  if (mode === 'exponent') data[0][1] = '1e0';
  if (mode === 'precision') data[0][1] = '2.0000000000000000001';
  return {status:200, json:async () => {
    if (mode === 'json') throw SyntaxError('json');
    if (mode === 'object') return {};
    return data;
  }};
};`;
    const hook = join(dir, 'mock.mjs');
    await writeFile(hook, preload);
    const result = spawnSync(process.execPath, ['--import', pathToFileURL(hook).href, script, ...args],
      { cwd: dir, encoding: 'utf8', timeout: 15000 });
    assert.equal(result.error, undefined);
    const calls = await readFile(join(dir, 'calls.jsonl'), 'utf8').catch(() => '');
    const csv = await readFile(join(dir, 'history-5m.csv'), 'utf8').catch(() => null);
    return { ...result, csv, calls: calls.trim().split('\n').filter(Boolean).map(JSON.parse), files: await readdir(dir) };
  } finally { await rm(dir, {recursive:true, force:true}); }
}
function failed(result) {
  assert.equal(result.status, 1);
  assert.equal(result.stderr, 'FETCH_ERROR\n');
  assert.equal(result.stdout, '');
  assert.equal(result.csv, old);
  assert.equal(hash(result.csv), hash(old));
}
test('GWT-01', async () => {
  const r = await run('ok', [], false);
  assert.equal(r.status, 0);
  assert.equal(r.stderr, '');
  const requests = r.calls.filter(c => c.url);
  assert.equal(requests.length, 9);
  requests.forEach((c, i) => {
    const u = new URL(c.url);
    assert.equal(u.origin + u.pathname, 'https://api.binance.com/api/v3/klines');
    assert.equal(c.method, 'GET');
    assert.equal(c.redirect, 'error');
    assert.equal(u.searchParams.get('symbol'), 'BTCUSDT');
    assert.equal(u.searchParams.get('interval'), '5m');
    assert.equal(Number(u.searchParams.get('limit')), i === 8 ? 640 : 1000);
    assert.equal(Number(u.searchParams.get('startTime')), start + i * 1000 * 300000);
    assert.equal(Number(u.searchParams.get('endTime')), end - 1);
  });
  const lines = r.csv.trim().split('\n');
  assert.equal(lines[0], header);
  assert.equal(lines.length, 8641);
  assert.equal(lines[1], '1789976700000,1.00,2.00,0.50,1.50,10.00');
  assert.equal(lines.at(-1), '1792568400000,1.00,2.00,0.50,1.50,10.00');
  lines.slice(1).forEach((line, i) => assert.equal(Number(line.split(',')[0]), start + i * 300000));
  assert.equal(r.csv, old);
});
test('GWT-02', async () => {
  const began = performance.now();
  const r = await run('timeout');
  failed(r);
  assert.ok(performance.now() - began >= 10000);
  assert.equal(r.calls.filter(c => c.url).length, 1);
  assert.ok(r.calls.some(c => c.aborted));
});
for (const mode of ['429', '418', '500', 'network']) test('GWT-03 ' + mode, async () => {
  const r = await run(mode);
  failed(r);
  assert.equal(r.calls.filter(c => c.url).length, 2);
  assert.equal(r.calls.filter(c => c.write).length, 0);
});
for (const [id, modes] of [['04', ['missing']], ['05', ['duplicate']],
  ['06', ['fields', 'price', 'range', 'volume']]]) {
  for (const mode of modes) test('GWT-' + id + ' ' + mode, async () => failed(await run(mode)));
}
for (const mode of ['write', 'rename']) test('GWT-07 ' + mode, async () => {
  const r = await run(mode);
  failed(r);
  assert.equal(r.calls.filter(c => c.url).length, 9);
  assert.deepEqual(r.files.sort(), ['calls.jsonl', 'history-5m.csv', 'mock.mjs']);
});
test('GWT-08', async () => {
  const r = await run('ok', ['--save']);
  failed(r);
  assert.deepEqual(r.calls, []);
});
test('GWT-09', () => {
  const files = execFileSync('git', ['diff', '--name-only', 'origin/main'], {encoding:'utf8'}).trim().split('\n').filter(Boolean);
  const untracked = execFileSync('git', ['ls-files', '--others', '--exclude-standard'], {encoding:'utf8'}).trim().split('\n').filter(Boolean);
  for (const file of [...files, ...untracked]) assert.ok(['fetch-history.mjs', 'test/fetch-history.test.mjs'].includes(file), file);
});
test('非法 JSON 保留旧 CSV', async () => failed(await run('json')));
for (const mode of ['timestamp', 'zero', 'exponent', 'precision', 'object']) {
  test('严格格式校验 ' + mode, async () => failed(await run(mode)));
}
test('成功原子替换已有 CSV', async () => {
  const r = await run();
  assert.equal(r.status, 0);
  assert.equal(r.csv, old);
  assert.equal(r.stderr, '');
});
