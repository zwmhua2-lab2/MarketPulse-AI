from __future__ import annotations

from collections.abc import Sequence

from marketpulse.market_data.models import NormalizedKline

from .models import MarketStructure, Zone


def analyze_structure(klines: Sequence[NormalizedKline], zone_width_ratio: float = 0.002) -> MarketStructure:
    """Return broad, reproducible candidate zones from confirmed one-minute bars."""
    confirmed = [item for item in klines if item.confirmed]
    if len(confirmed) < 3:
        return MarketStructure()
    recent = confirmed[-20:]
    swing_high_bar = max(recent, key=lambda item: item.high)
    swing_low_bar = min(recent, key=lambda item: item.low)
    high = swing_high_bar.high
    low = swing_low_bar.low
    high_width = max(high * zone_width_ratio, 1e-12)
    low_width = max(low * zone_width_ratio, 1e-12)
    high_zone = Zone(lower=high - high_width, upper=high + high_width, kind="RESISTANCE", observed_at=swing_high_bar.close_time)
    low_zone = Zone(lower=low - low_width, upper=low + low_width, kind="SUPPORT", observed_at=swing_low_bar.close_time)
    return MarketStructure(
        recent_swing_high=high,
        recent_swing_low=low,
        support_zones=[low_zone],
        resistance_zones=[high_zone],
        range_lower=low,
        range_upper=high,
        breakout_level=high,
        retest_area=high_zone,
    )
