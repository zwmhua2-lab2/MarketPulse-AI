import { writeFile, rename, unlink } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';

const step = 300000;
const count = 8640;
const endpoint = 'https://api.binance.com/api/v3/klines';
const header = 'open_time,open,high,low,close,volume';

function decimal(value, positive) {
  if (typeof value !== 'string' || !/^\d+(?:\.\d+)?$/.test(value)) throw Error('decimal');
  const fraction = value.split('.')[1] ?? '';
  const coefficient = BigInt(value.replace('.', ''));
  if (positive && coefficient === 0n) throw Error('zero price');
  return { coefficient, scale: fraction.length };
}

// Compare decimal strings exactly, without floating-point rounding.
function compare(a, b) {
  const scale = Math.max(a.scale, b.scale);
  return a.coefficient * 10n ** BigInt(scale - a.scale) -
    b.coefficient * 10n ** BigInt(scale - b.scale);
}

function validate(row, expected) {
  if (!Array.isArray(row) || row.length !== 12 || row.some(v => v == null)) throw Error('shape');
  if (!Number.isSafeInteger(row[0]) || row[0] !== expected) throw Error('time');
  const [open, high, low, close] = row.slice(1, 5).map(v => decimal(v, true));
  decimal(row[5], false);
  if ([open, close, low].some(v => compare(high, v) < 0) ||
      [open, close].some(v => compare(low, v) > 0)) throw Error('price range');
  return row.slice(0, 6).join(',');
}

async function page(start, end, limit) {
  const url = new URL(endpoint);
  url.search = new URLSearchParams({
    symbol: 'BTCUSDT', interval: '5m', startTime: String(start),
    endTime: String(end - 1), limit: String(limit),
  });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(url, {method: 'GET', signal: controller.signal, redirect: 'error'});
    if (response.status !== 200) throw Error('http');
    const data = await response.json();
    if (!Array.isArray(data) || data.length !== limit) throw Error('page size');
    return data;
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  if (process.argv.length !== 2) throw Error('arguments');
  const end = Math.floor(Date.now() / step) * step;
  const start = end - count * step;
  const lines = [header];
  for (let offset = 0; offset < count;) {
    const limit = Math.min(1000, count - offset);
    const data = await page(start + offset * step, end, limit);
    for (const row of data) {
      lines.push(validate(row, start + offset * step));
      offset++;
    }
  }
  const destination = resolve('history-5m.csv');
  let temporary = resolve(`.history-5m-${randomUUID()}.tmp`);
  try {
    try {
      await writeFile(temporary, lines.join('\n') + '\n', {encoding: 'utf8', flag: 'wx'});
    } catch (error) {
      // Never remove another writer's file if exclusive creation fails.
      if (error.code === 'EEXIST') temporary = undefined;
      throw error;
    }
    await rename(temporary, destination);
  } finally {
    if (temporary) await unlink(temporary).catch(() => {});
  }
}

try {
  await main();
} catch {
  process.stderr.write('FETCH_ERROR\n');
  process.exitCode = 1;
}
