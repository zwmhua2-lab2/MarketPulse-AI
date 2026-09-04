from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession


class RunMode(StrEnum):
    LIVE_PAPER = "LIVE_PAPER"
    REPLAY = "REPLAY"
    TEST = "TEST"


class Direction(StrEnum):
    LONG_BIAS = "LONG_BIAS"
    SHORT_BIAS = "SHORT_BIAS"
    WAIT = "WAIT"


class DecisionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALID = "VALID"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    INVALID_BUSINESS = "INVALID_BUSINESS"
    STALE_DECISION = "STALE_DECISION"
    CAPACITY_BLOCKED = "CAPACITY_BLOCKED"


class PlanStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REPLACED = "REPLACED"
    CAPACITY_BLOCKED = "CAPACITY_BLOCKED"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class IntentStatus(StrEnum):
    CREATED = "CREATED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"


class DataQuality(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


class PriceZone(BaseModel):
    lower: float
    upper: float

    _finite_lower = field_validator("lower")(_finite)
    _finite_upper = field_validator("upper")(_finite)

    def contains(self, price: float) -> bool:
        return self.lower <= price <= self.upper


class BestBidAsk(BaseModel):
    instrument_id: str
    bid: float
    ask: float
    received_at: datetime
    tradable: bool = True
    data_quality: DataQuality = DataQuality.FRESH

    _finite_bid = field_validator("bid")(_finite)
    _finite_ask = field_validator("ask")(_finite)

    @field_validator("received_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        return value.astimezone(UTC)


class StrategyContext(BaseModel):
    candidate_id: str
    strategy_id: str
    strength: float = Field(ge=0, le=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    expected_behavior: str
    invalidation_hint: str


class DecisionSnapshot(BaseModel):
    snapshot_id: str
    instrument_id: str
    symbol: str
    run_mode: RunMode
    state: str
    state_version: int = Field(ge=0)
    config_version: str
    snapshot_version: str
    created_at: datetime
    market_context: dict[str, Any]
    market_evolution: dict[str, Any]
    strategies: list[StrategyContext]
    trading_context: dict[str, Any]


class AIAnalysis(BaseModel):
    direction: Direction
    trends: dict[str, str]
    entry_zone: PriceZone | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    invalidation: str | None = None
    confidence: float = Field(ge=0, le=1)
    suggested_position_pct: float = Field(ge=0, le=1)
    reason: str
    supporting_evidence: list[str] = Field(default_factory=list)
    risk_evidence: list[str] = Field(default_factory=list)
    main_plan: str | None = None
    backup_scenarios: list[str] = Field(default_factory=list)
    selected_strategy_ids: list[str] = Field(default_factory=list)
    probe: bool = False

    _finite_stop = field_validator("stop_loss")(_finite)
    _finite_tp = field_validator("take_profit")(_finite)


class TradePlan(BaseModel):
    plan_id: str
    snapshot_id: str
    decision_id: str
    instrument_id: str
    symbol: str
    run_mode: RunMode
    state_version: int
    plan_version: int = 1
    status: PlanStatus = PlanStatus.ACTIVE
    created_at: datetime
    expires_at: datetime
    order_type: OrderType = OrderType.MARKET
    side: OrderSide = OrderSide.BUY
    entry_zone: PriceZone
    stop_loss: float
    take_profit: float
    intended_notional: float
    # G4 UPDATE_INVALIDATION stores the durable invalidation text on the plan version.
    invalidation: str | None = None
    probe: bool = False
    backup_scenarios: list[str] = Field(default_factory=list)


class ExecutionIntent(BaseModel):
    intent_id: str
    plan_id: str
    instrument_id: str
    run_mode: RunMode
    state_version: int
    created_at: datetime


class ExecutionResult(BaseModel):
    intent_id: str
    status: IntentStatus
    reason: str | None = None
    order_id: str | None = None
    fill_id: str | None = None


class OrderCancelResult(BaseModel):
    """Result of the G3 order-layer cancellation operation."""

    order_id: str
    status: OrderStatus
    cancelled: bool
    reason: str | None = None


@runtime_checkable
class RiskGate(Protocol):
    """Admission boundary owned by G4. `None` allows the action, a string blocks it."""

    async def evaluate(
        self,
        session: AsyncSession,
        *,
        run_mode: RunMode,
        instrument_id: str,
        side: OrderSide,
        plan_id: str | None,
        now: datetime,
    ) -> str | None: ...
