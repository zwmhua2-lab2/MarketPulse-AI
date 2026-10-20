"""R2 offline evaluation kernel -- one file, one job: falsify a K-line hypothesis.

Contract
--------
* A family is ``f(df) -> bool Series`` over a 5m OHLCV frame. It may only look
  at the current and earlier bars (no lookahead is enforced by construction:
  the signal is read at bar ``i`` close).
* Entry is the **next** bar open (``i+1``), never the signal bar close.
* Exit is the close of bar ``i + h``, i.e. exactly one horizon after entry.
* Cost is the production SPOT long round trip (5 bps slippage each side,
  10 bps fee each side), copied from ``marketpulse.edge.forward`` and pinned by
  ``test_parity.py``.
* Baseline is the unconditional forward return of every bar in the same
  coin/horizon/window.
* The delta CI is a paired day-block bootstrap, 10,000 resamples. Blocks are
  UTC days; each resample pools the same days for the event and baseline legs,
  so the two legs stay paired.

Usage
-----
    python kernel.py                 # exploration window only (first 70%)
    python kernel.py --confirm       # confirmation window, logged to confirm_log.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

FEE_RATE = 0.001
SLIPPAGE_FRACTION = 5 / 10_000
HORIZON_BARS = {"5m": 1, "15m": 3, "1h": 12}
N_BOOT = 10_000
MIN_CLUSTERS = 30
EXPLORE_FRACTION = 0.7
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HERE = os.path.dirname(__file__)


def cost_adjusted_forward_return(*, reference_ask, end_bid):
    """Copy of ``marketpulse.edge.forward.cost_adjusted_forward_return``.

    The production module drags SQLAlchemy in through its package ``__init__``,
    so the sandbox copies the four lines and pins them with test_parity.py.
    Works on scalars and numpy arrays alike.
    """

    entry_exec = reference_ask * (1 + SLIPPAGE_FRACTION)
    exit_exec = end_bid * (1 - SLIPPAGE_FRACTION)
    entry_cash_cost = entry_exec * (1 + FEE_RATE)
    exit_cash_value = exit_exec * (1 - FEE_RATE)
    return exit_cash_value / entry_cash_cost - 1


def load(coin: str, bar: str = "5m") -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{coin}_{bar}.csv")
    df = pd.read_csv(path, dtype={"ts": "int64"})
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return df


def forward_returns(df: pd.DataFrame, bars: int) -> np.ndarray:
    """Cost-adjusted return of entering at bar i+1 open and exiting at bar i+bars close."""

    n = len(df)
    entry = np.full(n, np.nan)
    exit_ = np.full(n, np.nan)
    entry[:-1] = df["open"].to_numpy()[1:]
    exit_[: n - bars] = df["close"].to_numpy()[bars:]
    out = cost_adjusted_forward_return(reference_ask=entry, end_bid=exit_)
    return np.asarray(out, dtype=float)


def day_arrays(df: pd.DataFrame, fwd: np.ndarray, mask: np.ndarray):
    """Split sums per UTC day for the paired block bootstrap."""

    days = df["time"].dt.floor("D").to_numpy()
    order = np.argsort(days, kind="stable")
    days_sorted = days[order]
    uniq, start = np.unique(days_sorted, return_index=True)
    bounds = list(start[1:]) + [len(days_sorted)]

    fwd_s = fwd[order]
    mask_s = mask[order]
    base_ok = np.isfinite(fwd_s)
    base_sum = np.add.reduceat(np.where(base_ok, fwd_s, 0.0), start)
    base_n = np.add.reduceat(base_ok.astype(float), start)
    ev_ok = base_ok & mask_s
    ev_sum = np.add.reduceat(np.where(ev_ok, fwd_s, 0.0), start)
    ev_n = np.add.reduceat(ev_ok.astype(float), start)
    return uniq, ev_sum, ev_n, base_sum, base_n


def paired_day_bootstrap(ev_sum, ev_n, base_sum, base_n, rng, n_boot=N_BOOT):
    """Delta = pooled event mean - pooled baseline mean, resampling UTC days."""

    idx = rng.integers(0, len(ev_sum), size=(n_boot, len(ev_sum)))
    e_n = ev_n[idx].sum(axis=1)
    b_n = base_n[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ev_mean = ev_sum[idx].sum(axis=1) / e_n
        base_mean = base_sum[idx].sum(axis=1) / b_n
    return ev_mean, base_mean, ev_mean - base_mean


@dataclass
class Row:
    version: str
    coin: str
    horizon: str
    n_raw: int
    n_clusters: int
    expectancy: float
    baseline: float
    delta: float
    lo: float
    hi: float

    @property
    def ok(self) -> bool:
        return self.n_clusters >= MIN_CLUSTERS

    def fmt(self) -> str:
        if not self.ok:
            return (
                f"{self.version:<26} {self.coin:<9} {self.horizon:>3} {self.n_raw:>7} {self.n_clusters:>6} "
                f"{'样本不足':>10} {'样本不足':>10} {'样本不足':>10} {'样本不足':>22}"
            )
        return (
            f"{self.version:<26} {self.coin:<9} {self.horizon:>3} {self.n_raw:>7} {self.n_clusters:>6} "
            f"{self.expectancy * 1e4:>10.2f} {self.baseline * 1e4:>10.2f} {self.delta * 1e4:>10.2f} "
            f"[{self.lo * 1e4:>9.2f}, {self.hi * 1e4:>8.2f}]"
        )


def evaluate(df, mask, fwd, version, coin, horizon, rng, n_boot=N_BOOT) -> Row:
    mask = np.asarray(mask, dtype=bool) & np.isfinite(fwd)
    n_raw = int(mask.sum())
    _, ev_sum, ev_n, base_sum, base_n = day_arrays(df, fwd, mask)
    n_clusters = int((ev_n > 0).sum())
    if n_raw == 0:
        return Row(version, coin, horizon, 0, 0, np.nan, np.nan, np.nan, np.nan, np.nan)
    ev_mean, base_mean, delta = paired_day_bootstrap(ev_sum, ev_n, base_sum, base_n, rng, n_boot)
    return Row(
        version, coin, horizon, n_raw, n_clusters,
        float(ev_sum.sum() / ev_n.sum()), float(base_sum.sum() / base_n.sum()),
        float(np.nanmean(delta)), float(np.nanpercentile(delta, 2.5)), float(np.nanpercentile(delta, 97.5)),
    )


HEADER = (
    f"{'family_version':<26} {'coin':<9} {'hz':>3} {'n_raw':>7} {'n_days':>6} "
    f"{'expectancy':>10} {'baseline':>10} {'delta':>10} {'95% CI (bps)':>22}"
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="evaluate the last 30%% confirmation window")
    ap.add_argument("--coins", default="BTC-USDT,ETH-USDT")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)

    sys.path.insert(0, HERE)
    from families import FAMILIES

    window = "confirm" if args.confirm else "explore"
    rows: list[Row] = []
    rng = np.random.default_rng(20261020)
    for coin in [c.strip() for c in args.coins.split(",") if c.strip()]:
        df = load(coin)
        cut = int(len(df) * EXPLORE_FRACTION)
        part = df.iloc[cut:].reset_index(drop=True) if args.confirm else df.iloc[:cut].reset_index(drop=True)
        print(
            f"# window={window} coin={coin} bars={len(df)} window_bars={len(part)} "
            f"{part['time'].iloc[0]} .. {part['time'].iloc[-1]}",
            flush=True,
        )
        for version, fn in FAMILIES.items():
            mask = np.asarray(fn(part), dtype=bool)
            for horizon, bars in HORIZON_BARS.items():
                fwd = forward_returns(part, bars)
                rows.append(evaluate(part, mask, fwd, version, coin, horizon, rng, args.boot))

    print(HEADER)
    print("-" * len(HEADER))
    for row in rows:
        print(row.fmt())

    if args.confirm:
        stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(os.path.join(HERE, "confirm_log.txt"), "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(f"{stamp}\twindow=confirm\t{row.version}\t{row.coin}\t{row.horizon}\tn_raw={row.n_raw}\tn_days={row.n_clusters}\n")
        print(f"\n# appended {len(rows)} rows to confirm_log.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
