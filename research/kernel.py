"""R2/R3 offline evaluation kernel -- one file, one job: falsify a K-line hypothesis.

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
* Baseline is the unconditional net forward return of every bar in the same
  coin/horizon/window.
* Two gates must both pass, at the Bonferroni-adjusted level ``alpha / m``:
    G1  delta (event net mean - baseline net mean) CI lower bound > 0
    G2  net expectancy CI lower bound > 0   <- this is the one that means money
* ``m`` is the cumulative number of distinct comparisons ever evaluated, kept
  in ``test_registry.json``. It only grows; every run pays for every past look.
* Blocks for the bootstrap are whole days, and never shorter than the horizon
  (1d horizon uses 5-day blocks) so overlap cannot silently narrow the CI.

Usage
-----
    python kernel.py                 # all 730 days (exploration only)
    python kernel.py --coins BTC-USDT --boot 5000
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

FEE_RATE = 0.001
SLIPPAGE_FRACTION = 5 / 10_000
HORIZON_BARS = {"5m": 1, "15m": 3, "1h": 12, "4h": 48, "12h": 144, "1d": 288}
BLOCK_DAYS = {"5m": 1, "15m": 1, "1h": 1, "4h": 1, "12h": 1, "1d": 5}
N_BOOT = 50_000
ALPHA = 0.05
MIN_CLUSTERS = 30
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HERE = os.path.dirname(__file__)
REGISTRY = os.path.join(HERE, "test_registry.json")
WINDOW = "explore-730d"


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


def _entry_exit(df: pd.DataFrame, bars: int):
    n = len(df)
    entry = np.full(n, np.nan)
    exit_ = np.full(n, np.nan)
    entry[:-1] = df["open"].to_numpy()[1:]
    exit_[: n - bars] = df["close"].to_numpy()[bars:]
    return entry, exit_


def forward_returns(df: pd.DataFrame, bars: int) -> np.ndarray:
    """Net (cost-adjusted) return, entry at bar i+1 open, exit at bar i+bars close."""

    entry, exit_ = _entry_exit(df, bars)
    return np.asarray(cost_adjusted_forward_return(reference_ask=entry, end_bid=exit_), dtype=float)


def gross_returns(df: pd.DataFrame, bars: int) -> np.ndarray:
    """Same trade before any fee or slippage."""

    entry, exit_ = _entry_exit(df, bars)
    return exit_ / entry - 1


def block_sum(values: np.ndarray, mask: np.ndarray, block_ids: np.ndarray):
    """Per-block sums, blocks must be non-decreasing (they are, time order)."""

    ok = np.isfinite(values) & mask
    contrib = np.where(ok, values, 0.0)
    counts = ok.astype(float)
    uniq, start = np.unique(block_ids, return_index=True)
    return uniq, np.add.reduceat(contrib, start), np.add.reduceat(counts, start)


def block_ids_for(df: pd.DataFrame, block_days: int) -> np.ndarray:
    day = (df["time"].dt.floor("D").astype("int64") // (86_400 * 10**9)).to_numpy()
    return (day - day.min()) // block_days


def bootstrap(ev_sum, ev_n, base_sum, base_n, rng, n_boot, chunk=10_000):
    """Paired block bootstrap: returns (event net means, deltas)."""

    n_blocks = len(ev_sum)
    ev_means, deltas = [], []
    done = 0
    while done < n_boot:
        size = min(chunk, n_boot - done)
        idx = rng.integers(0, n_blocks, size=(size, n_blocks))
        with np.errstate(invalid="ignore", divide="ignore"):
            ev = ev_sum[idx].sum(axis=1) / ev_n[idx].sum(axis=1)
            base = base_sum[idx].sum(axis=1) / base_n[idx].sum(axis=1)
        ev_means.append(ev)
        deltas.append(ev - base)
        done += size
    return np.concatenate(ev_means), np.concatenate(deltas)


@dataclass
class Row:
    version: str
    coin: str
    horizon: str
    n_raw: int
    n_blocks: int
    gross: float
    net: float
    baseline: float
    delta: float
    d_lo: float
    d_hi: float
    n_lo: float
    n_hi: float

    @property
    def enough(self) -> bool:
        return self.n_blocks >= MIN_CLUSTERS

    @property
    def gate1(self) -> bool:
        return self.enough and np.isfinite(self.d_lo) and self.d_lo > 0

    @property
    def gate2(self) -> bool:
        return self.enough and np.isfinite(self.n_lo) and self.n_lo > 0

    def fmt(self) -> str:
        tag = f"{self.version:<26} {self.coin:<9} {self.horizon:>3} {self.n_raw:>7} {self.n_blocks:>6}"
        if not self.enough:
            return f"{tag} {'样本不足':>9} {'样本不足':>9} {'样本不足':>9} {'样本不足':>9} {'样本不足':>21} {'样本不足':>19} {'不足':>4} {'不足':>4}"
        return (
            f"{tag} {self.gross * 1e4:>9.2f} {self.net * 1e4:>9.2f} {self.baseline * 1e4:>9.2f} "
            f"{self.delta * 1e4:>9.2f} [{self.d_lo * 1e4:>8.2f},{self.d_hi * 1e4:>8.2f}] "
            f"[{self.n_lo * 1e4:>8.2f},{self.n_hi * 1e4:>8.2f}] "
            f"{'PASS' if self.gate1 else '----':>4} {'PASS' if self.gate2 else '----':>4}"
        )


HEADER = (
    f"{'family_version':<26} {'coin':<9} {'hz':>3} {'n_raw':>7} {'n_blk':>6} "
    f"{'gross':>9} {'net':>9} {'baseline':>9} {'delta':>9} {'delta CI (bps)':>20} "
    f"{'net CI (bps)':>19} {'G1':>4} {'G2':>4}"
)


def evaluate(df, mask, net, gross, version, coin, horizon, rng, n_boot, q_lo, q_hi) -> Row:
    mask = np.asarray(mask, dtype=bool)
    n_raw = int((mask & np.isfinite(net)).sum())
    ids = block_ids_for(df, BLOCK_DAYS[horizon])
    _, ev_sum, ev_n = block_sum(net, mask, ids)
    _, base_sum, base_n = block_sum(net, np.ones(len(net), bool), ids)
    n_blocks = int((ev_n > 0).sum())
    if n_raw == 0:
        nan = float("nan")
        return Row(version, coin, horizon, 0, 0, nan, nan, nan, nan, nan, nan, nan, nan)
    ev_mean, delta = bootstrap(ev_sum, ev_n, base_sum, base_n, rng, n_boot)
    return Row(
        version, coin, horizon, n_raw, n_blocks,
        float(np.nanmean(gross[mask & np.isfinite(gross)])),
        float(ev_sum.sum() / ev_n.sum()),
        float(base_sum.sum() / base_n.sum()),
        float(np.nanmean(delta)),
        float(np.nanpercentile(delta, q_lo)), float(np.nanpercentile(delta, q_hi)),
        float(np.nanpercentile(ev_mean, q_lo)), float(np.nanpercentile(ev_mean, q_hi)),
    )


def register(keys: list[str]) -> int:
    """Cumulative m: every distinct comparison ever evaluated, never reset."""

    seen: dict[str, str] = {}
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as fh:
            seen = json.load(fh)
    added = [k for k in keys if k not in seen]
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for k in added:
        seen[k] = stamp
    with open(REGISTRY, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, indent=1, sort_keys=True)
    return len(seen)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="disabled: the 730d file is exploration now")
    ap.add_argument("--coins", default="BTC-USDT,ETH-USDT")
    ap.add_argument("--horizons", default=",".join(HORIZON_BARS))
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)

    if args.confirm:
        print(
            "refused: the 730d file has already been looked at and is exploration by policy.\n"
            "A confirmation window needs earlier history (>=5y) plus data after 2026-10-20.",
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, HERE)
    from families import FAMILIES

    coins = [c.strip() for c in args.coins.split(",") if c.strip()]
    horizons = [h.strip() for h in args.horizons.split(",") if h.strip()]
    keys = [f"{WINDOW}|{v}|{c}|{h}" for c in coins for v in FAMILIES for h in horizons]
    m = register(keys)
    per_test = ALPHA / m
    q_lo, q_hi = 100 * per_test / 2, 100 * (1 - per_test / 2)
    print(
        f"# window={WINDOW} m={m} alpha={ALPHA} per-test={per_test:.2e} "
        f"(CI {q_lo:.4f}..{q_hi:.4f} pct) bootstrap={args.boot} blocks={BLOCK_DAYS}"
    )

    rows: list[Row] = []
    rng = np.random.default_rng(20261021)
    for coin in coins:
        df = load(coin)
        print(f"# {coin}: {len(df)} bars {df['time'].iloc[0]} .. {df['time'].iloc[-1]}", flush=True)
        for version, fn in FAMILIES.items():
            mask = np.asarray(fn(df), dtype=bool)
            for horizon in horizons:
                bars = HORIZON_BARS[horizon]
                rows.append(
                    evaluate(
                        df, mask, forward_returns(df, bars), gross_returns(df, bars),
                        version, coin, horizon, rng, args.boot, q_lo, q_hi,
                    )
                )

    print(HEADER)
    print("-" * len(HEADER))
    for row in rows:
        print(row.fmt())

    passed = [r for r in rows if r.gate1 and r.gate2]
    print(f"\n# rows={len(rows)} gate1={sum(r.gate1 for r in rows)} gate2={sum(r.gate2 for r in rows)} both={len(passed)}")
    for r in passed:
        print(f"# PASS {r.version} {r.coin} {r.horizon} delta={r.delta*1e4:.2f} net={r.net*1e4:.2f} bps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
