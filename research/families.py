"""R2 hypothesis families. One function == one family. Nothing else.

Rules for adding a family (the thing R2 measures):
  1. write ``f(df) -> bool Series`` using only current/earlier bars,
  2. add one line to ``FAMILIES``.
That is the whole integration surface; the kernel needs no change.
"""

from __future__ import annotations

import pandas as pd

# --- v0 placeholders, copied from the panic_drop_long hypothesis card ---------
PANIC_SIGMA_WINDOW = 288      # 24h of 5m bars
PANIC_SIGMA_MULT = 2.0        # placeholder
PANIC_VOL_WINDOW = 12         # 1h of 5m bars
PANIC_VOL_MULT = 2.0          # placeholder


def panic_drop_long(df: pd.DataFrame) -> pd.Series:
    """Panic-down bar on heavy volume: buy the next open, i.e. stand in front of the seller.

    K-line volume is only a proxy for forced liquidation; there is no
    liquidation / open-interest / taker-side data in the sandbox.
    """

    ret = df["close"].pct_change()
    sigma = ret.rolling(PANIC_SIGMA_WINDOW, min_periods=PANIC_SIGMA_WINDOW).std()
    vol_ma = df["volume"].rolling(PANIC_VOL_WINDOW, min_periods=PANIC_VOL_WINDOW).mean()
    signal = (ret <= -PANIC_SIGMA_MULT * sigma) & (df["volume"] >= PANIC_VOL_MULT * vol_ma)
    return signal.fillna(False)


FAMILIES = {
    "panic_drop_long v0": panic_drop_long,
}


# --- family 2: liquidity sweep / failed breakdown -----------------------------
SWEEP_LOOKBACK = 24          # 2h of 5m bars
SWEEP_VOL_WINDOW = 24
SWEEP_CLOSE_STRENGTH = 0.5   # close in the upper half of the bar range


def failed_breakdown_reclaim(df: pd.DataFrame) -> pd.Series:
    """Sweep the prior 2h low, then close back above it: buy the stop run.

    Different trigger from panic_drop_long: it is not "fell a lot", it is
    "took out a level where stops sit, and failed to hold below it".
    """

    prior_low = df["low"].rolling(SWEEP_LOOKBACK, min_periods=SWEEP_LOOKBACK).min().shift(1)
    bar_range = (df["high"] - df["low"]).replace(0.0, float("nan"))
    close_strength = (df["close"] - df["low"]) / bar_range
    vol_ma = df["volume"].rolling(SWEEP_VOL_WINDOW, min_periods=SWEEP_VOL_WINDOW).mean()
    signal = (
        (df["low"] < prior_low)
        & (df["close"] > prior_low)
        & (close_strength >= SWEEP_CLOSE_STRENGTH)
        & (df["volume"] >= vol_ma)
    )
    return signal.fillna(False)


FAMILIES["failed_breakdown_reclaim v0"] = failed_breakdown_reclaim
