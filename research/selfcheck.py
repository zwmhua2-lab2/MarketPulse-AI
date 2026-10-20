"""Step 5 self-check: pull 3 random events and recompute the forward return by hand.

The arithmetic is printed in full (entry -> exit -> fees) so the number in the
kernel table can be checked against the raw bars instead of against itself.

    python selfcheck.py BTC-USDT "panic_drop_long v0" 5m
"""

from __future__ import annotations

import sys

import numpy as np

import kernel
from families import FAMILIES


def main(argv: list[str]) -> int:
    coin = argv[0] if argv else "BTC-USDT"
    version = argv[1] if len(argv) > 1 else next(iter(FAMILIES))
    horizon = argv[2] if len(argv) > 2 else "5m"
    bars = kernel.HORIZON_BARS[horizon]

    df = kernel.load(coin)
    cut = int(len(df) * kernel.EXPLORE_FRACTION)
    part = df.iloc[:cut].reset_index(drop=True)  # same window the table reports
    mask = np.asarray(FAMILIES[version](part), dtype=bool)
    fwd = kernel.forward_returns(part, bars)
    idx = np.flatnonzero(mask & np.isfinite(fwd))
    rng = np.random.default_rng(int(argv[3]) if len(argv) > 3 else 5)
    picks = rng.choice(idx, size=3, replace=False)

    print(f"# {version} | {coin} | {horizon} | exploration window {len(part)} bars")
    for i in sorted(picks):
        i = int(i)
        entry = float(part["open"].iloc[i + 1])
        exit_ = float(part["close"].iloc[i + bars])
        entry_exec = entry * (1 + kernel.SLIPPAGE_FRACTION)
        exit_exec = exit_ * (1 - kernel.SLIPPAGE_FRACTION)
        entry_cash = entry_exec * (1 + kernel.FEE_RATE)
        exit_cash = exit_exec * (1 - kernel.FEE_RATE)
        manual = exit_cash / entry_cash - 1
        print(
            f"\nbar {i} signal={part['time'].iloc[i]}\n"
            f"  signal bar close={float(part['close'].iloc[i]):.2f}\n"
            f"  entry  = open[{i+1}] = {entry:.2f}  -> exec {entry_exec:.6f} -> cash cost {entry_cash:.6f}\n"
            f"  exit   = close[{i+bars}] = {exit_:.2f}  -> exec {exit_exec:.6f} -> cash value {exit_cash:.6f}\n"
            f"  manual = {exit_cash:.6f}/{entry_cash:.6f} - 1 = {manual:.8f} ({manual*1e4:.2f} bps)\n"
            f"  kernel = {fwd[i]:.8f} ({fwd[i]*1e4:.2f} bps)\n"
            f"  match  = {abs(manual - fwd[i]) < 1e-12}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
