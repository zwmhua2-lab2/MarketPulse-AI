"""R3: what derivatives data is free, how far back, how fine -- probe, do not download.

A dozen requests, no files stored, no bulk pull. Every answer below is measured
from an actual response; docs are only used to explain what the numbers mean.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; marketpulse-research/0.1)"


def get(url: str, params: dict | None = None, timeout: int = 20):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:200]
    except Exception as exc:  # noqa: BLE001
        return -1, repr(exc)


def head(url: str):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.headers.get("Content-Length")
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:  # noqa: BLE001
        return -1, repr(exc)


def ts(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def month_span(a: int, b: int) -> str:
    return f"{(b - a) / 1000 / 86400 / 30.4:.1f} months"


def binance_data(rows, key_ts="timestamp"):
    if not rows:
        return None
    return int(rows[0][key_ts]), int(rows[-1][key_ts])


def main() -> int:
    out = []

    def line(s=""):
        out.append(s)
        print(s)

    line("== Binance USD-M futures (public REST) ==")
    st, raw = get("https://fapi.binance.com/fapi/v1/fundingRate", {"symbol": "BTCUSDT", "limit": 1000})
    if st == 200:
        rows = json.loads(raw)
        a, b = int(rows[0]["fundingTime"]), int(rows[-1]["fundingTime"])
        line(f"funding rate history : {len(rows)} rows, {ts(a)} .. {ts(b)}, 8h grid -> paginates, no key")
    else:
        line(f"funding rate history : HTTP {st}")

    for name, path, extra in [
        ("open interest (OI)", "/futures/data/openInterestHist", {"period": "5m"}),
        ("top trader long/short", "/futures/data/topLongShortAccountRatio", {"period": "5m"}),
        ("taker buy/sell volume", "/futures/data/takerlongshortRatio", {"period": "5m"}),
    ]:
        st, raw = get("https://fapi.binance.com" + path, {"symbol": "BTCUSDT", "limit": 500, **extra})
        if st == 200:
            rows = json.loads(raw)
            if rows:
                a, b = int(rows[0]["timestamp"]), int(rows[-1]["timestamp"])
                line(f"{name:<22}: {len(rows)} rows, {ts(a)} .. {ts(b)} ({month_span(a,b)}), 5m grid")
            else:
                line(f"{name:<22}: 200 but empty")
        else:
            line(f"{name:<22}: HTTP {st} {raw[:80]}")

    line()
    line("== Binance public data dumps (data.binance.vision) ==")
    base = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT"
    for day in ["2023-01-01", "2024-01-01", "2026-10-01"]:
        code, size = head(f"{base}/BTCUSDT-metrics-{day}.zip")
        line(f"metrics/{day}: HTTP {code}, bytes={size}")
    code, _ = head(f"{base}/BTCUSDT-metrics-5m-2026-10-01.zip")
    line(f"metrics 5m probe   : HTTP {code} (404 -> daily only in the dump)")
    line("  daily metrics fields: create_time, sum_open_interest, sum_open_interest_value,")
    line("  count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,")
    line("  count_long_short_ratio, sum_taker_long_short_vol_ratio  (one row per day)")

    line()
    line("== OKX public REST ==")
    st, raw = get("https://www.okx.com/api/v5/public/funding-rate-history",
                  {"instId": "BTC-USDT-SWAP", "limit": 100})
    if st == 200 and raw:
        body = json.loads(raw)
        rows = body.get("data") or []
        if rows:
            a, b = int(rows[-1]["fundingTime"]), int(rows[0]["fundingTime"])
            line(f"funding (BTC-USDT-SWAP): {len(rows)} rows, {ts(a)} .. {ts(b)}, 8h grid, paginates via `after`")
            page2 = get("https://www.okx.com/api/v5/public/funding-rate-history",
                        {"instId": "BTC-USDT-SWAP", "limit": 100, "after": str(a)})[1]
            rows2 = json.loads(page2).get("data") or []
            if rows2:
                line(f"  page 2 reaches back to {ts(int(rows2[-1]['fundingTime']))} -> older history exists")
    else:
        line(f"funding: HTTP {st}")

    for name, path, params in [
        ("OI + volume (rubik)", "/api/v5/rubik/stat/contracts/open-interest-volume", {"ccy": "BTC", "period": "5m"}),
        ("long/short acct (rubik)", "/api/v5/rubik/stat/contracts/long-short-account-ratio", {"ccy": "BTC", "period": "5m"}),
        ("taker volume (rubik)", "/api/v5/rubik/stat/taker-volume", {"ccy": "BTC", "instType": "CONTRACTS", "period": "5m"}),
    ]:
        st, raw = get("https://www.okx.com" + path, params)
        if st == 200:
            rows = (json.loads(raw).get("data") or [])
            if rows:
                a, b = int(rows[-1][0]), int(rows[0][0])
                line(f"{name:<24}: {len(rows)} rows, {ts(a)} .. {ts(b)} ({month_span(a,b)}), 5m grid")
        else:
            line(f"{name:<24}: HTTP {st}")

    line()
    line("== liquidation history ==")
    st, raw = get("https://www.okx.com/api/v5/public/liquidation-orders",
                  {"instType": "SWAP", "uly": "BTC-USDT", "state": "filled", "limit": 100})
    if st == 200:
        rows = json.loads(raw).get("data") or []
        det = [d for inst in rows for d in (inst.get("details") or [])]
        if det:
            t = [int(d["ts"]) for d in det]
            line(f"OKX liquidation-orders : {len(det)} fills, {ts(min(t))} .. {ts(max(t))}, "
                 f"span {month_span(min(t), max(t))}")
    else:
        line(f"OKX liquidation-orders : HTTP {st} {raw[:100]}")
    st, raw = get("https://fapi.binance.com/fapi/v1/allForceOrders", {"symbol": "BTCUSDT", "limit": 100})
    line(f"Binance allForceOrders : HTTP {st} (401/403 -> key required, not public)")

    line()
    line("== depth probes (how far back does it actually go) ==")
    now = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    st, raw = get("https://fapi.binance.com/fapi/v1/fundingRate",
                  {"symbol": "BTCUSDT", "startTime": 1560000000000, "limit": 1000})
    if st == 200:
        rows = json.loads(raw)
        if rows:
            line(f"Binance funding from 2019-06: earliest row {ts(int(rows[0]['fundingTime']))}, {len(rows)} rows")
    st, raw = get("https://fapi.binance.com/futures/data/openInterestHist",
                  {"symbol": "BTCUSDT", "period": "5m", "limit": 500,
                   "startTime": now - 30 * 86400 * 1000, "endTime": now})
    if st == 200:
        rows = json.loads(raw)
        line(f"Binance OI, window now-30d : {len(rows)} rows, earliest {ts(int(rows[0]['timestamp']))}" if rows else "Binance OI, window now-30d : empty")

    for day in ["2019-12-01", "2020-06-01", "2021-01-01"]:
        code, size = head(f"{base}/BTCUSDT-metrics-{day}.zip")
        line(f"metrics dump {day}: HTTP {code}, bytes={size}")

    st, raw = get("https://www.okx.com/api/v5/public/funding-rate-history",
                  {"instId": "BTC-USDT-SWAP", "limit": 100, "after": "1577836800000"})
    if st == 200:
        rows = json.loads(raw).get("data") or []
        line(f"OKX funding before 2020-01-01: {len(rows)} rows" + (f", earliest {ts(int(rows[-1]['fundingTime']))}" if rows else " (none -> history starts later)"))

    st, raw = get("https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume",
                  {"ccy": "BTC", "period": "5m", "begin": str(now - 90 * 86400 * 1000), "end": str(now)})
    if st == 200:
        rows = json.loads(raw).get("data") or []
        line(f"OKX rubik OI, window now-90d: {len(rows)} rows" + (f", earliest {ts(int(rows[-1][0]))}" if rows else " (empty -> retention < 90d)"))

    st, raw = get("https://fapi.binance.com/futures/data/openInterestHist",
                  {"symbol": "BTCUSDT", "period": "5m", "limit": 500,
                   "startTime": now - 30 * 86400 * 1000, "endTime": now - 20 * 86400 * 1000})
    rows = json.loads(raw) if st == 200 else []
    line(f"Binance OI, window 30d..20d ago: {len(rows)} rows" + (f", {ts(int(rows[0]['timestamp']))}" if rows else " (empty -> retention ~2d)"))

    st, raw = get("https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume",
                  {"ccy": "BTC", "period": "5m", "begin": str(now - 30 * 86400 * 1000), "end": str(now - 20 * 86400 * 1000)})
    rows = json.loads(raw).get("data") or [] if st == 200 else []
    line(f"OKX rubik OI, window 30d..20d ago: {len(rows)} rows" + (f", {ts(int(rows[-1][0]))}" if rows else " (empty -> retention ~2d)"))

    line()
    line("== other free futures dumps (HEAD only, no download) ==")
    for name, path in [
        ("aggTrades 2020-01-01", "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2020-01-01.zip"),
        ("aggTrades 2026-10-19", "https://data.binance.vision/data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2026-10-19.zip"),
        ("liquidationSnapshot 2021", "https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2021-01-01.zip"),
        ("liquidationSnapshot monthly", "https://data.binance.vision/data/futures/um/monthly/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2021-01.zip"),
        ("metrics 2020-12-01", "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-12-01.zip"),
    ]:
        code, size = head(path)
        line(f"{name:<26}: HTTP {code}, bytes={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
