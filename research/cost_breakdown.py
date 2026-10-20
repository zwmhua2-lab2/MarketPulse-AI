"""Where the ~30 bps goes, and why the baseline sits at the cost.

    python cost_breakdown.py

Fee and slippage are multiplicative, not additive, so the legs are printed
both ways. The measured baseline per horizon then shows the drift term:
baseline_net = (1 + baseline_gross) * K - 1.
"""

from __future__ import annotations

import numpy as np

import kernel

COINS = ["BTC-USDT", "ETH-USDT"]


def legs() -> dict:
    s, f = kernel.SLIPPAGE_FRACTION, kernel.FEE_RATE
    entry = (1 + s) * (1 + f)
    exit_ = (1 - s) * (1 - f)
    k = exit_ / entry
    return {
        "fee_entry_bps": f * 1e4,
        "fee_exit_bps": f * 1e4,
        "slip_entry_bps": s * 1e4,
        "slip_exit_bps": s * 1e4,
        "entry_mult": entry,
        "exit_mult": exit_,
        "K": k,
        "total_bps": (1 - k) * 1e4,
        "additive_bps": (2 * f + 2 * s) * 1e4,
    }


def main() -> int:
    L = legs()
    print("cost model: SPOT long taker round trip, multiplicative")
    print(f"  entry: open * (1+{L['slip_entry_bps']:.2f}bps slip) * (1+{L['fee_entry_bps']:.2f}bps fee) = {L['entry_mult']:.8f}x")
    print(f"  exit : close * (1-{L['slip_exit_bps']:.2f}bps slip) * (1-{L['fee_exit_bps']:.2f}bps fee) = {L['exit_mult']:.8f}x")
    print(f"  K = exit/entry = {L['K']:.8f}  -> cost = {(1-L['K'])*1e4:.2f} bps")
    print(f"  legs: fee {2*L['fee_entry_bps']:.2f} + slippage {2*L['slip_entry_bps']:.2f} = {L['additive_bps']:.2f} bps additive, "
          f"cross term {L['total_bps']-L['additive_bps']:+.2f} bps, total {L['total_bps']:.2f} bps")
    print()
    print(f"{'coin':<9} {'hz':>3} {'drift(gross)':>13} {'cost':>7} {'baseline(net)':>14} {'residual':>9}")
    for coin in COINS:
        df = kernel.load(coin)
        for hz, bars in kernel.HORIZON_BARS.items():
            g = kernel.gross_returns(df, bars)
            n = kernel.forward_returns(df, bars)
            gm, nm = float(np.nanmean(g)), float(np.nanmean(n))
            cost_bps = L["total_bps"]
            residual = nm * 1e4 - (gm * 1e4 - cost_bps)
            print(f"{coin:<9} {hz:>3} {gm*1e4:>13.2f} {cost_bps:>7.2f} {nm*1e4:>14.2f} {residual:>9.3f}")
    print("\n(bps. baseline(net) = drift - cost + residual; residual is the cross term, ~0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
