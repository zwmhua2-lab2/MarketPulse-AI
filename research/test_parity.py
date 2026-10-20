"""Pins the sandbox copy of the cost model to production, and guards against lookahead.

    python -m unittest test_parity -v      (from research/)
"""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "backend", "src"))

import kernel  # noqa: E402
from families import FAMILIES, panic_drop_long  # noqa: E402


class CostParity(unittest.TestCase):
    def test_constants_match_production(self):
        from marketpulse.edge import forward as prod

        self.assertEqual(kernel.FEE_RATE, prod.FEE_RATE)
        self.assertEqual(kernel.SLIPPAGE_FRACTION, prod.SLIPPAGE_FRACTION)
        self.assertEqual(kernel.SLIPPAGE_FRACTION, prod.SLIPPAGE_BPS / 10_000)

    def test_random_inputs_match_production(self):
        from marketpulse.edge.forward import cost_adjusted_forward_return as prod

        rng = np.random.default_rng(7)
        ask = rng.uniform(0.01, 200_000, 5_000)
        bid = ask * rng.uniform(0.9, 1.1, 5_000)
        ours = kernel.cost_adjusted_forward_return(reference_ask=ask, end_bid=bid)
        theirs = prod(reference_ask=ask, end_bid=bid)
        np.testing.assert_allclose(ours, theirs, rtol=0, atol=1e-15)

    def test_scalar_matches_production(self):
        from marketpulse.edge.forward import cost_adjusted_forward_return as prod

        for ask, bid in [(100.0, 100.0), (100.0, 101.0), (0.5, 0.49), (83_032.1, 82_664.1)]:
            self.assertAlmostEqual(
                float(kernel.cost_adjusted_forward_return(reference_ask=ask, end_bid=bid)),
                float(prod(reference_ask=ask, end_bid=bid)),
                places=15,
            )


def synthetic(n=2_000, seed=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    high = close * (1 + abs(rng.normal(0, 0.0005, n)))
    low = close * (1 - abs(rng.normal(0, 0.0005, n)))
    return pd.DataFrame(
        {
            "ts": np.arange(n) * 300_000,
            "open": np.r_[close[0], close[:-1]],
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(1, 10, n),
            "time": pd.to_datetime(np.arange(n) * 300_000, unit="ms", utc=True),
        }
    )


class NoLookahead(unittest.TestCase):
    def test_families_ignore_future_bars(self):
        df = synthetic()
        cut = 1_500
        for name, fn in FAMILIES.items():
            base = np.asarray(fn(df), dtype=bool)[: cut + 1]
            mutated = df.copy()
            mutated.loc[cut + 1 :, ["open", "high", "low", "close"]] *= 3.0
            mutated.loc[cut + 1 :, "volume"] *= 50.0
            after = np.asarray(fn(mutated), dtype=bool)[: cut + 1]
            np.testing.assert_array_equal(base, after, err_msg=f"{name} peeks at future bars")

    def test_entry_is_next_bar_open(self):
        df = pd.DataFrame(
            {
                "ts": [0, 300_000, 600_000],
                "open": [10.0, 20.0, 30.0],
                "high": [11.0, 21.0, 31.0],
                "low": [9.0, 19.0, 29.0],
                "close": [10.5, 20.5, 30.5],
                "volume": [1.0, 1.0, 1.0],
                "time": pd.to_datetime([0, 300_000, 600_000], unit="ms", utc=True),
            }
        )
        fwd = kernel.forward_returns(df, 1)
        self.assertFalse(np.isnan(fwd[0]))  # signal at 0 -> entry open 20, exit close 20.5
        self.assertAlmostEqual(
            fwd[0], kernel.cost_adjusted_forward_return(reference_ask=20.0, end_bid=20.5), places=15
        )
        self.assertTrue(np.isnan(fwd[2]))

    def test_panic_family_shape(self):
        df = synthetic()
        sig = panic_drop_long(df)
        self.assertEqual(len(sig), len(df))
        self.assertEqual(sig.dtype, bool)


class BootstrapSanity(unittest.TestCase):
    def _run(self, ev, base, n_boot=2_000):
        rng = np.random.default_rng(11)
        days = len(ev)
        _, _, delta = kernel.paired_day_bootstrap(
            ev.sum(axis=1), np.full(days, ev.shape[1], float),
            base.sum(axis=1), np.full(days, base.shape[1], float),
            rng, n_boot,
        )
        return np.percentile(delta, 2.5), np.percentile(delta, 97.5)

    def test_known_edge_is_detected(self):
        rng = np.random.default_rng(1)
        base = rng.normal(0, 0.01, (120, 200))
        ev = rng.normal(0.01, 0.01, (120, 10))  # +100 bps over baseline every day
        lo, hi = self._run(ev, base)
        self.assertGreater(lo, 0.005)
        self.assertLess(hi, 0.015)

    def test_null_is_not_significant(self):
        rng = np.random.default_rng(2)
        base = rng.normal(0, 0.01, (120, 200))
        ev = rng.normal(0, 0.01, (120, 10))
        lo, hi = self._run(ev, base)
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)


if __name__ == "__main__":
    unittest.main()
