"""Download OKX 5m candles into research/data/ as CSV.

Read-only sandbox: no backend imports, no DB, no Docker.

OKX note: requests without a User-Agent get HTTP 403 from the public
market-data endpoints, so every request here sends one.

The public history endpoint returns at most 100 bars per call and the whole
pull is latency-bound, so the range is split into chunks fetched by a small
thread pool behind one global rate limiter (~8 req/s, under the 20 req/2s
documented cap).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://www.okx.com/api/v5/market/history-candles"
UA = "Mozilla/5.0 (compatible; marketpulse-research/0.1)"
BAR_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000}
COLUMNS = ["ts", "open", "high", "low", "close", "volume", "vol_ccy", "vol_ccy_quote", "confirm"]
RATE_PER_SEC = 8.0


class RateLimiter:
    def __init__(self, per_sec: float) -> None:
        self._interval = 1.0 / per_sec
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next)
            self._next = slot + self._interval
        delay = slot - time.monotonic()
        if delay > 0:
            time.sleep(delay)


LIMITER = RateLimiter(RATE_PER_SEC)


def http_get(params: dict, timeout: int = 25) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last_err = None
    for attempt in range(6):
        LIMITER.wait()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if body.get("code") != "0":
                raise RuntimeError(f"okx code={body.get('code')} msg={body.get('msg')}")
            return body
        except Exception as exc:  # noqa: BLE001 - retry any transport/parse error
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"request failed after retries: {last_err}")


def fetch_chunk(inst_id: str, bar: str, start_ms: int, end_ms: int) -> list[list[str]]:
    """All bars with start_ms <= ts <= end_ms, newest first from the API."""

    cursor = end_ms
    rows: dict[int, list[str]] = {}
    while True:
        body = http_get({"instId": inst_id, "bar": bar, "after": str(cursor + 1), "limit": "100"})
        data = body.get("data") or []
        if not data:
            break
        for r in data:
            ts = int(r[0])
            if start_ms <= ts <= end_ms:
                rows[ts] = r
        oldest = min(int(r[0]) for r in data)
        if oldest <= start_ms:
            break
        cursor = oldest
    return [rows[ts] for ts in sorted(rows)]


def fetch(inst_id: str, bar: str, days: int, workers: int = 8) -> list[list[str]]:
    step = BAR_MS[bar]
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - days * 86_400_000
    span = step * 100 * 60  # 60 pages per chunk
    chunks = []
    end = (now_ms // step) * step
    while end > cutoff:
        start = max(cutoff, end - span)
        chunks.append((start, end))
        end = start - step
    print(f"  {inst_id} {bar}: {len(chunks)} chunks, {workers} workers", flush=True)

    rows: dict[int, list[str]] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_chunk, inst_id, bar, a, b) for a, b in chunks]
        for fut in futures:
            for r in fut.result():
                rows[int(r[0])] = r
            done += 1
            if done % 5 == 0:
                print(f"  {inst_id} {bar}: {done}/{len(chunks)} chunks, {len(rows)} bars", flush=True)
    out = [rows[ts] for ts in sorted(rows) if ts >= cutoff]
    print(f"  {inst_id} {bar}: done, {len(out)} bars", flush=True)
    return out


def write_csv(path: str, rows: list[list[str]]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(r[: len(COLUMNS)])
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coins", default="BTC-USDT,ETH-USDT")
    ap.add_argument("--bar", default="5m")
    ap.add_argument("--days", type=int, default=730)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "data"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    for coin in [c.strip() for c in args.coins.split(",") if c.strip()]:
        print(f"[fetch] {coin} {args.bar} last {args.days}d", flush=True)
        rows = fetch(coin, args.bar, args.days, args.workers)
        path = os.path.join(args.outdir, f"{coin}_{args.bar}.csv")
        write_csv(path, rows)
        print(f"[fetch] wrote {path} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
