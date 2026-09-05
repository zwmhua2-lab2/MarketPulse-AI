from __future__ import annotations

from marketpulse.clock import Clock, SystemClock

from .models import (
    DirectionBias,
    EventType,
    FeatureSnapshot,
    MarketEvent,
    StrategyCandidate,
    deterministic_id,
)


class StrategyEngine:
    """Produces parallel, explainable candidates; it does not mutate state or execute anything."""

    version = "g2-v1"

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()

    def candidates(self, features: FeatureSnapshot, event: MarketEvent, state_version: int) -> list[StrategyCandidate]:
        return [
            self._trend_pullback(features, event, state_version),
            self._breakout_retest(features, event, state_version),
            self._liquidity_sweep(features, event, state_version),
            self._absorption(features, event, state_version),
        ]

    def _candidate(self, name: str, applicable: bool, strength: float, bias: DirectionBias, features: FeatureSnapshot, event: MarketEvent, state_version: int, support: list[str], contradiction: list[str], invalidation: str, expected: str) -> StrategyCandidate:
        return StrategyCandidate(candidate_id=deterministic_id("sc", event.event_id, name, self.version), strategy_id=name, strategy_version=self.version, applicable=applicable, strength=round(max(0.0, min(1.0, strength)), 6), setup_type=name, direction_bias=bias, entry_context={"current_price": features.current_price, "retest_area": features.structure.retest_area.model_dump(mode="json") if features.structure.retest_area else None}, supporting_evidence=support, contradicting_evidence=contradiction, invalidation_hint=invalidation, expected_behavior=expected, instrument_id=features.instrument_id, symbol=features.symbol, event_id=event.event_id, state_version=state_version, config_version=event.config_version, created_at=self.clock.now())

    def _trend_pullback(self, features: FeatureSnapshot, event: MarketEvent, state_version: int) -> StrategyCandidate:
        bullish = (features.short_return or 0) > 0 and (features.buy_sell_imbalance or 0) > 0
        return self._candidate("TREND_PULLBACK", bullish and features.structure.retest_area is not None, min(1, abs(features.short_return or 0) * 80 + max(0, features.buy_sell_imbalance or 0) / 2), DirectionBias.BULLISH if bullish else DirectionBias.NEUTRAL, features, event, state_version, ["positive_short_return" if bullish else "no_trend_confirmation"], [], "loss_of_retest_area", "hold above the retest area after continuation")

    def _breakout_retest(self, features: FeatureSnapshot, event: MarketEvent, state_version: int) -> StrategyCandidate:
        applicable = event.event_type is EventType.BREAKOUT and features.structure.retest_area is not None
        return self._candidate("BREAKOUT_RETEST", applicable, event.strength if applicable else 0, DirectionBias.BULLISH if applicable else DirectionBias.NEUTRAL, features, event, state_version, ["breakout_market_fact"] if applicable else [], [], "return_inside_prior_range", "retest holds around the breakout area")

    def _liquidity_sweep(self, features: FeatureSnapshot, event: MarketEvent, state_version: int) -> StrategyCandidate:
        applicable = event.event_type is EventType.FAILED_BREAKOUT and (features.buy_sell_imbalance or 0) < 0
        return self._candidate("LIQUIDITY_SWEEP_REVERSAL", applicable, event.strength if applicable else 0, DirectionBias.BEARISH if applicable else DirectionBias.NEUTRAL, features, event, state_version, ["failed_breakout", "selling_flow"] if applicable else [], [], "reclaim_of_breakout_level", "rejection persists after range re-entry")

    def _absorption(self, features: FeatureSnapshot, event: MarketEvent, state_version: int) -> StrategyCandidate:
        applicable = abs(features.buy_sell_imbalance or 0) > 0.5 and (features.liquidity_change or 0) > 0
        bias = DirectionBias.BULLISH if (features.buy_sell_imbalance or 0) > 0 else DirectionBias.BEARISH
        return self._candidate("ZONE_ABSORPTION_REJECTION", applicable, min(1, abs(features.buy_sell_imbalance or 0)), bias if applicable else DirectionBias.NEUTRAL, features, event, state_version, ["flow_imbalance", "liquidity_expansion"] if applicable else [], [], "liquidity_or_flow_normalizes", "absorption holds at the candidate zone")
