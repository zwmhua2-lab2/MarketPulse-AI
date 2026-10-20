"""Step 1 integrity checks: duplicates, missing bars, timestamp continuity, regime coverage."""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BAR_MS = 300_000


def check(coin: str) -> dict:
    path = os.path.join(DATA_DIR, f"{coin}_5m.csv")
    raw = pd.read_csv(path)
    out: dict = {"coin": coin, "path": path, "rows_raw": len(raw)}

    dup = int(raw["ts"].duplicated().sum())
    missing_confirm = int((raw["confirm"].astype(int) == 0).sum())
    df = raw[raw["confirm"].astype(int) == 1].drop_duplicates("ts").sort_values("ts").reset_index(drop=True)

    ts = df["ts"].to_numpy()
    gaps = np.diff(ts)
    bad_step = gaps[gaps != BAR_MS]
    off_grid = int((ts % BAR_MS != 0).sum())
    expected = int((ts.max() - ts.min()) // BAR_MS + 1)
    missing = expected - len(ts)

    span_days = (ts.max() - ts.min()) / 86_400_000
    ret = df["close"].pct_change().dropna()
    daily = df.set_index(pd.to_datetime(df["ts"], unit="ms", utc=True))["close"].resample("1D").last().pct_change().dropna()

    ohlc_bad = int(
        (
            (df["high"] < df["low"])
            | (df["high"] < df["close"])
            | (df["low"] > df["close"])
            | (df["volume"] < 0)
        ).sum()
    )

    out.update(
        duplicates=dup,
        unconfirmed_dropped=missing_confirm,
        rows_clean=len(df),
        expected_bars=expected,
        missing_bars=missing,
        missing_pct=round(missing / expected * 100, 4),
        non_5m_steps=len(bad_step),
        largest_gap_bars=int(bad_step.max() // BAR_MS) if len(bad_step) else 0,
        off_grid=off_grid,
        ohlc_violations=ohlc_bad,
        first=pd.to_datetime(ts.min(), unit="ms", utc=True).isoformat(),
        last=pd.to_datetime(ts.max(), unit="ms", utc=True).isoformat(),
        span_days=round(span_days, 1),
        up_days=int((daily > 0).sum()),
        down_days=int((daily < 0).sum()),
        flat_days=int((daily == 0).sum()),
        worst_day_pct=round(float(daily.min() * 100), 2),
        best_day_pct=round(float(daily.max() * 100), 2),
    )
    return out


def main() -> int:
    coins = sys.argv[1:] or ["BTC-USDT", "ETH-USDT"]
    lines = []
    for coin in coins:
        try:
            info = check(coin)
        except FileNotFoundError:
            print(f"{coin}: NOT FOUND (still downloading?)")
            continue
        lines.append(f"== {coin} ==")
        for k, v in info.items():
            if k in ("coin", "path"):
                continue
            lines.append(f"  {k:>20}: {v}")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(os.path.dirname(__file__), "integrity_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
