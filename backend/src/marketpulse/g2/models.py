from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from marketpulse.market_data.models import DataQuality, MarketType


@dataclass(frozen=True)
class AdvisoryWorkRef:
    """The only post-commit handoff from G2 to the Host-owned Advisory ingress."""

    decision_invocation_id: str
    decision_deadline_at: datetime


@dataclass(frozen=True)
class G2PersistResult:
    """Durable G2 commit outcome, with an optional already-durable Advisory handoff."""

    persisted: bool
    advisory_work_ref: AdvisoryWorkRef | None = None

    def __bool__(self) -> bool:
        """Keep legacy truthiness callers compatible while exposing the typed contract."""

        return self.persisted


class EventType(StrEnum):
    PRICE_ACCELERATION = "PRICE_ACCELERATION"
    VOLATILITY_ANOMALY = "VOLATILITY_ANOMALY"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    FLOW_IMBALANCE = "FLOW_IMBALANCE"
    BREAKOUT = "BREAKOUT"
    FAILED_BREAKOUT = "FAILED_BREAKOUT"
    LIQUIDITY_CHANGE = "LIQUIDITY_CHANGE"
    OI_ANOMALY = "OI_ANOMALY"
    LIQUIDATION_CONTEXT = "LIQUIDATION_CONTEXT"
    RELATIVE_BTC_STRENGTH = "RELATIVE_BTC_STRENGTH"
    STRUCTURE_CHANGE = "STRUCTURE_CHANGE"


class LifecycleAction(StrEnum):
    START = "START"
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    NORMALIZED = "NORMALIZED"


class SymbolState(StrEnum):
    IDLE = "IDLE"
    DETECTED = "DETECTED"
    WATCHING = "WATCHING"
    SETUP = "SETUP"


class StateApplyResult(StrEnum):
    APPLIED = "APPLIED"
    NO_CHANGE = "NO_CHANGE"
    REJECT_STALE_OPERATION = "REJECT_STALE_OPERATION"
    REJECT_LATE_EVENT = "REJECT_LATE_EVENT"
    REJECT_COOLDOWN = "REJECT_COOLDOWN"


class DirectionBias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Zone(BaseModel):
    lower: float
    upper: float
    kind: str
    observed_at: datetime

    @field_validator("lower", "upper")
    @classmethod
    def finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("zone value must be finite")
        return value


class MarketStructure(BaseModel):
    recent_swing_high: float | None = None
    recent_swing_low: float | None = None
    support_zones: list[Zone] = Field(default_factory=list)
    resistance_zones: list[Zone] = Field(default_factory=list)
    range_lower: float | None = None
    range_upper: float | None = None
    breakout_level: float | None = None
    retest_area: Zone | None = None


class FeatureSnapshot(BaseModel):
    instrument_id: str
    symbol: str
    market_type: MarketType
    event_time: datetime
    current_price: float | None = None
    short_return: float | None = None
    price_acceleration: float | None = None
    volatility: float | None = None
    window_volume: float = 0.0
    relative_volume: float | None = None
    volume_acceleration: float | None = None
    aggressive_buy_volume: float = 0.0
    aggressive_sell_volume: float = 0.0
    buy_sell_imbalance: float | None = None
    flow_strength_change: float | None = None
    spread: float | None = None
    basic_depth: float | None = None
    liquidity_change: float | None = None
    oi: float | None = None
    oi_change: float | None = None
    funding_rate: float | None = None
    liquidation_availability: DataQuality = DataQuality.UNAVAILABLE
    relative_btc_strength: float | None = None
    structure_changed: bool = False
    structure: MarketStructure = Field(default_factory=MarketStructure)


class MarketEvent(BaseModel):
    event_id: str
    symbol: str
    instrument_id: str
    market_type: MarketType
    event_type: EventType
    event_time: datetime
    received_time: datetime
    source: str
    strength: float = Field(ge=0, le=1)
    priority: int = Field(ge=0, le=100)
    state_version: int = Field(ge=0)
    config_version: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_time", "received_time")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)


class SignalTimelineEvent(BaseModel):
    timeline_id: str
    event_id: str
    symbol: str
    instrument_id: str
    signal_type: EventType
    event_time: datetime
    received_time: datetime
    price: float | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    strength: float = Field(ge=0, le=1)
    lifecycle_action: LifecycleAction
    symbol_state: SymbolState
    state_version: int = Field(ge=0)
    config_version: str
    observed_reaction: dict[str, Any] | None = None


class SymbolStateRecord(BaseModel):
    instrument_id: str
    symbol: str
    state: SymbolState = SymbolState.IDLE
    state_version: int = 0
    last_event_time: datetime | None = None
    watch_expires_at: datetime | None = None
    cooldown_until: datetime | None = None
    structure_fingerprint: str | None = None


class StateTransition(BaseModel):
    transition_id: str
    instrument_id: str
    symbol: str
    from_state: SymbolState
    to_state: SymbolState
    event_id: str
    event_time: datetime
    state_version: int
    result: StateApplyResult
    reason: str


class StrategyCandidate(BaseModel):
    candidate_id: str
    strategy_id: str
    strategy_version: str
    applicable: bool
    strength: float = Field(ge=0, le=1)
    setup_type: str
    direction_bias: DirectionBias
    entry_context: dict[str, Any] = Field(default_factory=dict)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    invalidation_hint: str
    expected_behavior: str
    instrument_id: str
    symbol: str
    event_id: str
    state_version: int
    config_version: str
    created_at: datetime


def deterministic_id(prefix: str, *parts: object) -> str:
    encoded = json.dumps([str(part) for part in parts], separators=(",", ":"), ensure_ascii=True)
    return f"{prefix}_{hashlib.sha256(encoded.encode()).hexdigest()[:24]}"
