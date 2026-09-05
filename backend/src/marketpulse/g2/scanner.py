from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marketpulse.clock import Clock, SystemClock

from .models import EventType, FeatureSnapshot, MarketEvent, deterministic_id


@dataclass(frozen=True)
class ScannerConfig:
    version: str = "g2-v1"
    price_acceleration_threshold: float = 0.003
    volatility_threshold: float = 0.002
    relative_volume_threshold: float = 2.0
    flow_imbalance_threshold: float = 0.65
    liquidity_change_threshold: float = 0.35
    oi_change_threshold: float = 0.02
    relative_btc_threshold: float = 0.003
    strength_floor: float = 0.25


class OpportunityScanner:
    """Independent market-fact detectors. It deliberately has no trade direction output."""

    def __init__(self, config: ScannerConfig | None = None, clock: Clock | None = None) -> None:
        self.config = config or ScannerConfig()
        self.clock = clock or SystemClock()

    def scan(self, features: FeatureSnapshot, received_time: datetime | None = None, state_version: int = 0) -> list[MarketEvent]:
        received_time = received_time or self.clock.now()
        candidates: list[tuple[EventType, float, dict[str, object]]] = []
        candidates.extend(self._price(features))
        candidates.extend(self._volume(features))
        candidates.extend(self._flow(features))
        candidates.extend(self._breakout(features))
        candidates.extend(self._liquidity(features))
        candidates.extend(self._derivatives(features))
        candidates.extend(self._relative_strength(features))
        return [self._event(features, kind, strength, payload, received_time, state_version) for kind, strength, payload in candidates]

    def _price(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        result = []
        if value.price_acceleration is not None and abs(value.price_acceleration) >= self.config.price_acceleration_threshold:
            result.append((EventType.PRICE_ACCELERATION, self._strength(abs(value.price_acceleration), self.config.price_acceleration_threshold), {"price_acceleration": value.price_acceleration, "current_price": value.current_price}))
        if value.volatility is not None and value.volatility >= self.config.volatility_threshold:
            result.append((EventType.VOLATILITY_ANOMALY, self._strength(value.volatility, self.config.volatility_threshold), {"volatility": value.volatility, "current_price": value.current_price}))
        return result

    def _volume(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        if value.relative_volume is None or value.relative_volume < self.config.relative_volume_threshold:
            return []
        return [(EventType.VOLUME_ANOMALY, self._strength(value.relative_volume, self.config.relative_volume_threshold), {"relative_volume": value.relative_volume, "window_volume": value.window_volume})]

    def _flow(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        if value.buy_sell_imbalance is None or abs(value.buy_sell_imbalance) < self.config.flow_imbalance_threshold:
            return []
        return [(EventType.FLOW_IMBALANCE, self._strength(abs(value.buy_sell_imbalance), self.config.flow_imbalance_threshold), {"buy_sell_imbalance": value.buy_sell_imbalance, "flow_strength_change": value.flow_strength_change})]

    def _breakout(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        structure = value.structure
        result: list[tuple[EventType, float, dict[str, object]]] = []
        if value.structure_changed and structure.breakout_level is not None:
            result.append((EventType.STRUCTURE_CHANGE, 0.4, {"breakout_level": structure.breakout_level, "range_lower": structure.range_lower, "range_upper": structure.range_upper}))
        if value.current_price is None or structure.breakout_level is None:
            return result
        if value.current_price > structure.breakout_level:
            result.append((EventType.BREAKOUT, self._strength((value.current_price - structure.breakout_level) / structure.breakout_level, 0.001), {"breakout_level": structure.breakout_level, "current_price": value.current_price, "retest_area": structure.retest_area.model_dump(mode="json") if structure.retest_area else None}))
            return result
        if structure.range_upper and value.current_price < structure.range_upper and structure.retest_area and value.current_price > structure.retest_area.upper:
            result.append((EventType.FAILED_BREAKOUT, 0.5, {"range_upper": structure.range_upper, "current_price": value.current_price}))
        return result

    def _liquidity(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        if value.liquidity_change is None or abs(value.liquidity_change) < self.config.liquidity_change_threshold:
            return []
        return [(EventType.LIQUIDITY_CHANGE, self._strength(abs(value.liquidity_change), self.config.liquidity_change_threshold), {"liquidity_change": value.liquidity_change, "spread": value.spread, "basic_depth": value.basic_depth})]

    def _derivatives(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        result = []
        if value.oi_change is not None and abs(value.oi_change) >= self.config.oi_change_threshold:
            result.append((EventType.OI_ANOMALY, self._strength(abs(value.oi_change), self.config.oi_change_threshold), {"oi": value.oi, "oi_change": value.oi_change, "funding_rate": value.funding_rate}))
        result.append((EventType.LIQUIDATION_CONTEXT, 0.0, {"availability": value.liquidation_availability})) if value.liquidation_availability == "UNAVAILABLE" else None
        return result

    def _relative_strength(self, value: FeatureSnapshot) -> list[tuple[EventType, float, dict[str, object]]]:
        if value.relative_btc_strength is None or abs(value.relative_btc_strength) < self.config.relative_btc_threshold:
            return []
        return [(EventType.RELATIVE_BTC_STRENGTH, self._strength(abs(value.relative_btc_strength), self.config.relative_btc_threshold), {"relative_btc_strength": value.relative_btc_strength})]

    def _event(self, features: FeatureSnapshot, kind: EventType, strength: float, payload: dict[str, object], received_time: datetime, state_version: int) -> MarketEvent:
        bucket = int(features.event_time.timestamp())
        event_id = deterministic_id("me", features.instrument_id, kind, bucket, self.config.version, payload)
        return MarketEvent(
            event_id=event_id,
            symbol=features.symbol,
            instrument_id=features.instrument_id,
            market_type=features.market_type,
            event_type=kind,
            event_time=features.event_time,
            received_time=received_time,
            source="g2.opportunity_scanner",
            strength=round(min(1.0, max(0.0, strength)), 6),
            priority=round(min(100.0, max(0.0, strength * 100))),
            state_version=state_version,
            config_version=self.config.version,
            payload=payload,
        )

    def _strength(self, actual: float, threshold: float) -> float:
        return max(self.config.strength_floor, min(1.0, actual / (threshold * 3)))
