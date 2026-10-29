import { test } from 'node:test';
// - **GWT-01（C1/C3/X1/X2，端到端）**：Given 固定运行时钟 `2026-10-21T07:47:00.000Z`、模拟 Binance 返回 9 页有效 12 字段 K 线（前 8 页各 1000 条，最后一页 640 条；每条 OHLCV 固定为 `1.00,2.00,0.50,1.50,10.00`），When 执行抓取并保存，Then 只向指定端点发出 9 次 GET、每页 `limit≤1000`、每次带 `BTCUSDT/5m`，CSV 表头精确为 `open_time,open,high,low,close,volume`，数据恰好 8640 行，首行 `1789976700000,1.00,2.00,0.50,1.50,10.00`，末行 `1792568400000,1.00,2.00,0.50,1.50,10.00`，时间步长 `300000` 毫秒，退出码 0。
// - **GWT-02（C1/C2/C3）**：Given 某页请求持续无响应、目标目录中已有已验证的完好 CSV，When 超过 10000 ms（允许模拟时钟）且请求被中止，Then 只请求 1 次、不重试、stderr=`FETCH_ERROR\n`、退出码 1、旧 CSV SHA-256 与失败前相同。
// - **GWT-03（C1/C2/C3）**：Given 任一分页返回 HTTP 429、418、500 或请求抛网络错误（分别测试），When 执行抓取，Then 遇错误立即停止、不重试，stderr=`FETCH_ERROR\n`、退出码 1、旧 CSV 字节不变。
// - **GWT-04（C2/C3/X1）**：Given 8640 条中缺少恰好一根 K 线（例如跨页漏掉第 1000 根）、旧 CSV 完好，When 抓取，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-05（C2/C3/X1）**：Given 第 2 页第一根与第 1 页最后一根开盘时间相同（重复分页边界）、旧 CSV 完好，When 抓取，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-06（C2/C3/X2）**：Given 响应含 11 字段 K 线、非数字开盘价、`high<low` 或负成交量（逐例），旧 CSV 完好，When 抓取，Then 每例退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变。
// - **GWT-07（C2/C3）**：Given 所有行情数据有效、旧 CSV 完好，但临时文件写入或 rename 被模拟为失败（逐例），When 保存，Then 退出码 1、stderr=`FETCH_ERROR\n`、旧 CSV 字节不变，正式文件无半截新数据。
// - **GWT-08（C3）**：Given CLI 参数为 `--save`，When 执行，Then 在网络调用及文件写入前退出 1，stderr=`FETCH_ERROR\n`，旧 CSV 不变。
// - **GWT-09（C5，终审清单）**：CLI、mp_audit 新增及 §7 有限路径资格；实际写入仍须 Issue 白名单，拒绝删除/重命名/复制和未知路径。
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
function gwt09Invalid(diff, untracked) {
  const tokens = value => {
    assert.ok(value === '' || value.endsWith('\0'), 'invalid Git NUL output');
    return value === '' ? [] : value.slice(0, -1).split('\0');
  };
  const original = p => ['fetch-history.mjs', 'test/fetch-history.test.mjs'].includes(p);
  const audit = p => p.startsWith('mp_audit/') && p.slice(9).split('/').every(s => s && s !== '.' && s !== '..');
  // Path eligibility only: this cannot prove Human authorization or inspect change semantics.
  const docs = p => ['ARCHITECTURE.md', 'PRODUCT_REQUIREMENTS.md', 'DECISIONS.md', 'PROJECT_STATE.md'].includes(p);
  const log = p => p === 'dev_log/2026-10-29-v01-architecture-admission.md';
  const existing = p => ['frontend/src/app/router.tsx', 'frontend/src/app/ProductShell.tsx',
    'frontend/src/api/generated.ts', 'backend/src/marketpulse/api/app.py'].includes(p);
  const module = p => ['backend/src/marketpulse/api/product/market_candles.py',
    'backend/tests/test_product_market_candles.py'].includes(p) ||
    (/^frontend\/src\/v01\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:tsx?|css)$/.test(p) &&
      !/(?:^|[/.])config\.(?:tsx?|css)$/.test(p));
  const invalid = [], fields = tokens(diff);
  for (let i = 0; i < fields.length;) {
    const status = fields[i++];
    assert.match(status, /^(?:[AMDUTX]|[RC]\d{1,3})$/, 'invalid Git status');
    const paths = fields.slice(i, i + (/^[RC]/.test(status) ? 2 : 1));
    i += paths.length;
    assert.equal(paths.length, /^[RC]/.test(status) ? 2 : 1, 'missing Git path');
    if (paths.length === 1 && ['A', 'M'].includes(status) && (original(paths[0]) || module(paths[0]))) continue;
    if (status === 'M' && (docs(paths[0]) || existing(paths[0]))) continue;
    if (status === 'A' && log(paths[0])) continue;
    if (status === 'A' && paths.length === 1 && audit(paths[0])) continue;
    invalid.push(paths.join(' -> '));
  }
  for (const p of tokens(untracked)) if (!original(p) && !audit(p) && !module(p) && !log(p)) invalid.push(p);
  return invalid;
}
test('GWT-09', () => {
  const diff = execFileSync('git', ['diff', '--name-status', '-z', '--find-renames', 'origin/main'], {encoding:'utf8'});
  const untracked = execFileSync('git', ['ls-files', '--others', '--exclude-standard', '-z'], {encoding:'utf8'});
  const invalid = gwt09Invalid(diff, untracked);
  if (invalid.length) process.stderr.write(invalid.join('\n') + '\n');
  assert.equal(invalid.length, 0, invalid.join('\n'));
});

// Issue #5 GWT-1: Given Git 变更列表只有 `M\ttest/fetch-history.test.mjs` 与 `A\tmp_audit/audit.mjs`、`A\tmp_audit/R3-V-REPORT.md`，When 执行 GWT-09 的判定，Then 非法路径数 **0**，测试退出码 **0**；不得因为白名单目录不在 V1 抓取器原清单而拒绝。
// GWT-2: Given 只有未跟踪文件 `mp_audit/sample.json`（Git `ls-files --others`）和 GWT-09 本卡允许的测试文件修改，When 执行路径判定，Then 非法路径数 **0**。Given 未跟踪根目录文件 `.gwt09-untracked-probe`，When 执行，Then 非法路径数 **1**，错误包含该文件名，退出码 **1**；现有 QA 未跟踪回归仍 PASS。
// GWT-3: Given `M\tmp_audit/R3-V-REPORT.md`、`D\tmp_audit/sample.json`、`R100\tresearch/old.txt\tmp_audit/old.txt` 三个独立反例，When 逐个执行 GWT-09 判定，Then **每例非法路径数 1**、错误包含该路径、测试退出码 **1**；`mp_audit/` 前缀不得掩盖原有文件变更。
// GWT-4: Given `A\t.github/workflows/unsafe.yml`、`A\tresearch/extra.txt`、`A\ttest/extra.test.mjs`、`A\tmp_audit2/fake.mjs` 四个独立反例，When 逐个执行路径判定，Then **每例非法路径数 1**、独立 GWT-09 退出码 **1**；原有 `fetch-history.mjs` 的允许规则不变化。
// GWT-5: Given 现有抓取测试与 GWT-09 的直接相关回归，When 实际运行 `node --test test/fetch-history.test.mjs`，Then 退出码 **0**，所有原有用例（包含原 QA 未跟踪回归）保持通过；未实际运行不得写 PASS。
// GWT-6: Given 本卡 PR 相对最新 `origin/main` 的 Diff，When 检查 `git diff --name-status origin/main` 和未跟踪文件清单，Then **改动路径仅 `test/fetch-history.test.mjs`，白名单外改动数 0，`mp_audit/**` 改动数 0**，总改动不超过 **300 行**；Issue #4 仍为 open，未对其实施任何操作。
function runGwt09(diff, untracked = '', gitFailure = false) {
  const hook = `import cp from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
cp.execFileSync = (command, args) => {
  if (${gitFailure}) throw Error('GIT_FAILURE');
  if (command !== 'git') throw Error('unexpected command');
  if (args[0] === 'diff') return ${JSON.stringify(diff)};
  if (args[0] === 'ls-files') return ${JSON.stringify(untracked)};
  throw Error('unexpected Git operation');
}; syncBuiltinESMExports();`;
  const env = {...process.env};
  delete env.NODE_TEST_CONTEXT;
  return spawnSync(process.execPath, ['--import', 'data:text/javascript,' + encodeURIComponent(hook),
    '--test', '--test-name-pattern=^GWT-09$', 'test/fetch-history.test.mjs'], {encoding: 'utf8', env});
}
const gwt09Cases = [
  ['GWT-1', 'M\0test/fetch-history.test.mjs\0A\0mp_audit/audit.mjs\0A\0mp_audit/R3-V-REPORT.md\0', '', []],
  ['GWT-2 audit', 'M\0test/fetch-history.test.mjs\0', 'mp_audit/sample.json\0', []],
  ['GWT-2 root', '', '.gwt09-untracked-probe\0', ['.gwt09-untracked-probe']],
  ['GWT-3 M', 'M\0mp_audit/R3-V-REPORT.md\0', '', ['mp_audit/R3-V-REPORT.md']],
  ['GWT-3 D', 'D\0mp_audit/sample.json\0', '', ['mp_audit/sample.json']],
  ['GWT-3 R', 'R100\0research/old.txt\0mp_audit/old.txt\0', '', ['research/old.txt -> mp_audit/old.txt']],
  ...['.github/workflows/unsafe.yml', 'research/extra.txt', 'test/extra.test.mjs', 'mp_audit2/fake.mjs']
    .map(p => ['GWT-4 ' + p, 'A\0' + p + '\0', '', [p]]),
  ['original allow', 'M\0fetch-history.mjs\0', '', []],
  ['copy in', 'C100\0research/old.txt\0mp_audit/old.txt\0', '', ['research/old.txt -> mp_audit/old.txt']],
  ['copy existing', 'C100\0mp_audit/a.txt\0mp_audit/b.txt\0', '', ['mp_audit/a.txt -> mp_audit/b.txt']],
  ['rename within', 'R050\0mp_audit/a.txt\0mp_audit/b.txt\0', '', ['mp_audit/a.txt -> mp_audit/b.txt']],
  ['rename out', 'R100\0mp_audit/old.txt\0fetch-history.mjs\0', '', ['mp_audit/old.txt -> fetch-history.mjs']],
  ['directory itself', 'A\0mp_audit/\0', '', ['mp_audit/']],
  ['NUL paths', 'A\0mp_audit/a\tb\nc.json\0', '', []],
];
// ARCH-V01-01-A01 GWT-04：Given 原有合法、非法及边界测试样例。
// When 执行 GWT-09 相关测试。Then 本次批准的路径通过，原有越界反例仍被拒绝。
const admissionDocs = ['ARCHITECTURE.md', 'PRODUCT_REQUIREMENTS.md', 'DECISIONS.md', 'PROJECT_STATE.md'];
const admissionLog = 'dev_log/2026-10-29-v01-architecture-admission.md';
const v01Existing = ['frontend/src/app/router.tsx', 'frontend/src/app/ProductShell.tsx',
  'frontend/src/api/generated.ts', 'backend/src/marketpulse/api/app.py'];
const v01Modules = ['frontend/src/v01/Market.tsx', 'frontend/src/v01/market.test.ts',
  'frontend/src/v01/style.css', 'backend/src/marketpulse/api/product/market_candles.py',
  'backend/tests/test_product_market_candles.py'];
for (const p of [...admissionDocs, ...v01Existing, ...v01Modules]) {
  gwt09Cases.push(['V01 modify ' + p, `M\0${p}\0`, '', []]);
}
for (const p of [admissionLog, ...v01Modules]) {
  gwt09Cases.push(['V01 add ' + p, `A\0${p}\0`, '', []], ['V01 untracked ' + p, '', `${p}\0`, []]);
}
for (const p of [...admissionDocs, ...v01Existing]) {
  gwt09Cases.push(['V01 no replacement ' + p, `A\0${p}\0`, '', [p]],
    ['V01 no untracked replacement ' + p, '', `${p}\0`, [p]]);
}
gwt09Cases.push(['V01 log immutable', `M\0${admissionLog}\0`, '', [admissionLog]]);
for (const p of ['fetch-history.mjs', 'test/fetch-history.test.mjs', ...admissionDocs, admissionLog,
  ...v01Existing, ...v01Modules]) {
  for (const status of ['D', 'T', 'U', 'X']) gwt09Cases.push(['V01 reject ' + status + ' ' + p,
    `${status}\0${p}\0`, '', [p]]);
  for (const status of ['R100', 'C100']) gwt09Cases.push(['V01 reject ' + status + ' ' + p,
    `${status}\0${p}\0test/fetch-history.test.mjs\0`, '', [`${p} -> test/fetch-history.test.mjs`]]);
}
for (const p of ['AGENTS.md', 'package.json', 'package-lock.json', '.github/workflows/ci.yml',
  'backend/src/marketpulse/runtime_host.py', 'backend/src/marketpulse/g2/scanner.py',
  'backend/src/marketpulse/edge/capture.py', 'backend/src/marketpulse/g3/service.py',
  'backend/src/marketpulse/config.py', 'backend/alembic/new.py', 'backend/tests/conftest.py',
  'frontend/package.json', 'frontend/vite.config.ts', 'frontend/src/auth/RequireAuth.tsx',
  'frontend/src/v010/fake.ts', 'frontend/src/v01/../app/routes.ts', 'frontend/src/v01/a//b.ts',
  'frontend/src/v01/.hidden.ts', 'frontend/src/v01/package.json', 'frontend/src/v01/run.mjs',
  'frontend/src/v01/vitest.config.ts', 'frontend/src/v01/trailing.ts\n',
  'frontend/src/v01/unsafe\\file.ts', 'frontend/src/v01/unsafe\nfile.ts',
  'backend/src/marketpulse/api/product/market_candles.py/extra', 'research/extra.txt',
  'dev_log/unknown.md', '.workbuddy/memory/unknown.md']) {
  gwt09Cases.push(['V01 forbidden ' + p, `M\0${p}\0`, '', [p]],
    ['V01 forbidden add ' + p, `A\0${p}\0`, '', [p]], ['V01 forbidden untracked ' + p, '', `${p}\0`, [p]]);
}
for (const [name, diff, untracked, invalid] of gwt09Cases) test('GWT-09 contract ' + name, () => {
  assert.deepEqual(gwt09Invalid(diff, untracked), invalid);
  const r = runGwt09(diff, untracked);
  assert.equal(r.error, undefined);
  assert.equal(r.status, invalid.length ? 1 : 0, r.stdout + r.stderr);
  for (const p of invalid) assert.ok((r.stdout + r.stderr).includes(p), p);
});
test('GWT-09 contract Git failure', () => {
  const r = runGwt09('', '', true);
  assert.equal(r.status, 1);
  assert.match(r.stdout + r.stderr, /GIT_FAILURE/);
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
