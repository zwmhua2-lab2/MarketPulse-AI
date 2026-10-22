"""N1 fixed-window OKX download. All writes confined to this directory."""
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import json
import pathlib
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
RESEARCH = ROOT.parent
DEADLINE = 1792701780
FIRST = 1515669000000  # Human-confirmed earliest available candle, 2018-01-11 11:10 UTC
STEP = 300000
COLUMNS = 'ts,open,high,low,close,volume,vol_ccy,vol_ccy_quote,confirm'.split(',')
ENDS = {'BTC-USDT': 1729437900000, 'ETH-USDT': 1729438200000}
BASE = 'https://www.okx.com/api/v5/market/history-candles'
UA = 'Mozilla/5.0 (compatible; marketpulse-research/0.1)'
LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
NEXT = 0.0
INTERVAL = 0.13  # strictly below 8 requests/s, shared by all workers and coins
PAUSE_UNTIL = 0.0
LIMIT_HITS = 0
DOWNLOAD_END = 0.0
STOPS = {c: threading.Event() for c in ENDS}
ERRORS = {c: [] for c in ENDS}
PAGES = {c: 0 for c in ENDS}

def log(event, **kw):
    record = dict(epoch=time.time(), utc=dt.datetime.now(dt.timezone.utc).isoformat(), event=event, **kw)
    line = json.dumps(record, ensure_ascii=False)
    with LOG_LOCK:
        with (ROOT / 'run.log').open('a', encoding='utf-8') as fh:
            fh.write(line + '\n')
        print(line, flush=True)

def check(coin):
    if time.time() >= min(DEADLINE - 300, DOWNLOAD_END):
        raise RuntimeError('DOWNLOAD_TIME_LIMIT_OR_DEADLINE')
    if STOPS[coin].is_set():
        raise RuntimeError('COIN_STOPPED')

def slot(coin):
    global NEXT
    # Hold lock through the wait: delayed workers cannot produce catch-up bursts.
    with LOCK:
        while time.monotonic() < max(NEXT, PAUSE_UNTIL):
            check(coin)
            time.sleep(min(0.1, max(NEXT, PAUSE_UNTIL) - time.monotonic()))
        check(coin)
        NEXT = time.monotonic() + INTERVAL

def request(coin, cursor):
    global INTERVAL, PAUSE_UNTIL, LIMIT_HITS
    url = BASE + '?' + urllib.parse.urlencode(dict(instId=coin, bar='5m', limit='100', after=str(cursor)))
    for attempt in range(1, 7):
        slot(coin)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=min(25, max(0.1, min(DOWNLOAD_END, DEADLINE)-time.time()))) as response:
                if response.status != 200:
                    raise RuntimeError(f'HTTP {response.status}')
                raw = response.read().decode('utf-8')
                body = json.loads(raw)
            if body.get('code') != '0' or not isinstance(body.get('data'), list):
                raise RuntimeError(f'ABNORMAL_RESPONSE {raw[:1000]}')
            return body['data']
        except Exception as exc:
            code = getattr(exc, 'code', None)
            log('request_error', instId=coin, after=cursor, error=str(exc), error_code=code, attempt=attempt)
            if code in (429, 418):
                with LOCK:
                    LIMIT_HITS += 1
                    INTERVAL = 0.25
                    PAUSE_UNTIL = time.monotonic() + 30
                if LIMIT_HITS >= 3:
                    for event in STOPS.values():
                        event.set()
                    raise RuntimeError('RATE_LIMIT_THREE_TIMES') from exc
            if attempt == 6 or str(exc).startswith('ABNORMAL_RESPONSE'):
                raise
            until = time.monotonic() + attempt
            while time.monotonic() < until:
                check(coin)
                time.sleep(min(0.1, until-time.monotonic()))

def chunk(coin, number, lo, hi):
    path = ROOT / 'data' / f'{coin}_{number:03d}.tmp'
    cursor, empty, stale = hi + 1, 0, 0
    seen = {}
    try:
        with path.open('x', encoding='utf-8') as fh:
            while True:
                check(coin)
                rows = request(coin, cursor)
                fh.write(json.dumps(dict(after=cursor, data=rows), separators=(',', ':'))+'\n')
                fh.flush()
                with LOCK:
                    PAGES[coin] += 1
                if not rows:
                    empty += 1
                    if empty >= 2:
                        raise RuntimeError(f'TWO_EMPTY_RESPONSES after={cursor}')
                    continue
                empty = 0
                if any(not isinstance(r, list) or len(r) != 9 for r in rows):
                    raise RuntimeError('INVALID_NINE_COLUMN_ROW')
                for row in rows:
                    ts = int(row[0])
                    if ts in seen and seen[ts] != row:
                        raise RuntimeError(f'CONFLICTING_DUPLICATES ts={ts}; both raw records preserved')
                    seen[ts] = row
                oldest = min(int(r[0]) for r in rows)
                if oldest >= cursor:
                    stale += 1
                    if stale >= 3:
                        raise RuntimeError(f'PAGINATION_STALLED after={cursor}')
                    continue
                stale = 0
                if oldest <= lo:
                    break
                cursor = oldest  # after is exclusive; strictly advance into the past
        return dict(coin=coin, number=number, lo=lo, hi=hi, path=str(path), complete=True)
    except Exception as exc:
        STOPS[coin].set()
        record = dict(coin=coin, number=number, lo=lo, hi=hi, path=str(path), complete=False, error=str(exc), after=cursor)
        ERRORS[coin].append(record)
        log('chunk_stopped', **record)
        return record

def assemble(coin, chunks):
    rows = {}
    duplicates, conflicts = 0, 0
    for ch in chunks:
        p = pathlib.Path(ch['path'])
        if not p.exists():
            continue
        for line in p.open(encoding='utf-8'):
            for row in json.loads(line)['data']:
                if len(row) != 9:
                    continue
                ts = int(row[0])
                if not ch['lo'] <= ts <= ch['hi']:
                    continue
                if ts in rows:
                    duplicates += 1
                    if rows[ts] != row:
                        conflicts += 1
                else:
                    rows[ts] = row
    complete = all(c['complete'] for c in chunks) and not ERRORS[coin] and not conflicts
    if conflicts:
        log('CONFLICTING_DUPLICATES_STOP_SPLICE', coin=coin, conflicts=conflicts, raw_records='preserved in data/*.tmp')
    name = f'{coin}_5m_2018-2024.csv'
    # Conflicted raw records stay in journals; never silently select a conflicting row.
    if conflicts:
        return dict(complete=False, rows=len(rows), conflicts=conflicts, duplicates=duplicates, errors=ERRORS[coin])
    path = ROOT / 'data' / (name if complete else name + '.partial')
    temp = pathlib.Path(str(path)+'.tmp')
    removed = 0
    with temp.open('x', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for ts in sorted(rows):
            if str(rows[ts][-1]) == '0':
                removed += 1
            else:
                writer.writerow(rows[ts])
    if path.exists():
        raise RuntimeError(f'REFUSE_OVERWRITE {path}')
    temp.rename(path)
    result = dict(complete=complete, path=str(path), rows=len(rows)-removed, raw_unique_rows=len(rows), removed_confirm0=removed, duplicate_identical=duplicates, conflicts=conflicts, errors=ERRORS[coin], sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    log('coin_download_complete', coin=coin, **result)
    return result

def main():
    global DOWNLOAD_END
    start = time.time()
    if start >= DEADLINE:
        raise SystemExit('DEADLINE_EXPIRED_NOT_STARTED')
    if (ROOT/'run.log').exists():
        raise SystemExit('REFUSE_EXISTING_RUN_LOG')
    (ROOT/'data').mkdir(exist_ok=False)
    DOWNLOAD_END = min(start+3600, DEADLINE-300)
    log('start', start_epoch=start, deadline=DEADLINE, download_deadline=DOWNLOAD_END, command='python -B research/n1-2026-10-23/download.py', initial_readonly_check_epoch=1792691165, human_ruling='执行端曾因缺少 ARCHITECTURE.md 停下，Human 裁决豁免，依据为本仓库 AGENTS.md 的研究沙盒例外。')
    protected = [RESEARCH/'kernel.py', RESEARCH/'families.py', RESEARCH/'test_registry.json', RESEARCH/'run_r3_explore.txt'] + [RESEARCH/'data'/f'{c}_5m.csv' for c in ENDS]
    log('input_hashes', sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
    log('download_contract', first=FIRST, last=ENDS, columns=COLUMNS, bar='5m', limit=100, max_req_per_sec=8, workers=8)
    tasks=[]
    for coin, end in ENDS.items():
        number=0
        while end >= FIRST:
            lo=max(FIRST,end-5999*STEP)
            tasks.append((coin,number,lo,end))
            end=lo-STEP
            number+=1
    # Interleave coins; one shared pool and limiter, each chunk pages backwards.
    tasks.sort(key=lambda t:t[1])
    results={c:[] for c in ENDS}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(chunk,*t) for t in tasks]
        for future in cf.as_completed(futures):
            result=future.result()
            results[result['coin']].append(result)
            log('chunk_done', coin=result['coin'], number=result['number'], complete=result['complete'], chunks_done=sum(len(v) for v in results.values()), chunks_total=len(tasks), pages=PAGES.copy())
    status={c:assemble(c, results[c]) for c in ENDS}
    log('download_finished', elapsed_seconds=time.time()-start, status=status)

if __name__=='__main__':
    main()
