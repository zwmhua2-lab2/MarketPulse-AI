from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from marketpulse.g3.models import BestBidAsk, DataQuality, OrderSide, RunMode

# --------------------------------------------------------------------------------------
# System / operator state
# --------------------------------------------------------------------------------------


class OperatorState(StrEnum):
    """Human control intent. Persisted independently so a restart cannot silently clear it."""

    NORMAL = "NORMAL"
    PAUSED = "PAUSED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class SystemState(StrEnum):
    STARTING = "STARTING"
    RECOVERING = "RECOVERING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DATA_DEGRADED = "DATA_DEGRADED"
    SAFE_MODE = "SAFE_MODE"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    ERROR = "ERROR"


# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------


class HealthComponent(StrEnum):
    DATABASE = "DATABASE"
    CORE_MARKET_DATA = "CORE_MARKET_DATA"
    EXECUTION = "EXECUTION"
    AI_AUXILIARY = "AI_AUXILIARY"


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


#: Components whose failure blocks risk-increasing actions. AI_AUXILIARY is deliberately
#: excluded: an AI outage must never block stop-loss / take-profit protection.
RISK_BLOCKING_COMPONENTS: frozenset[HealthComponent] = frozenset(
    {
        HealthComponent.DATABASE,
        HealthComponent.CORE_MARKET_DATA,
        HealthComponent.EXECUTION,
    }
)


# --------------------------------------------------------------------------------------
# Incidents
# --------------------------------------------------------------------------------------


class IncidentType(StrEnum):
    ACCOUNT_INTEGRITY_ERROR = "ACCOUNT_INTEGRITY_ERROR"
    POSITION_UNPROTECTED = "POSITION_UNPROTECTED"
    CORE_DATA_STALE = "CORE_DATA_STALE"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    EXECUTION_GAP = "EXECUTION_GAP"
    AI_REEVALUATION_FAILED = "AI_REEVALUATION_FAILED"
    EMERGENCY_STOP_ACTIVATED = "EMERGENCY_STOP_ACTIVATED"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


#: Unresolved incidents that block new risk and must be cleared by an explicit action.
BLOCKING_INCIDENT_TYPES: frozenset[IncidentType] = frozenset(
    {
        IncidentType.ACCOUNT_INTEGRITY_ERROR,
        IncidentType.RECOVERY_FAILED,
        IncidentType.POSITION_UNPROTECTED,
    }
)


# --------------------------------------------------------------------------------------
# Position lifecycle
# --------------------------------------------------------------------------------------


class PositionEventType(StrEnum):
    SL_TRIGGERED = "SL_TRIGGERED"
    TP_TRIGGERED = "TP_TRIGGERED"
    AI_REEVALUATION = "AI_REEVALUATION"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    MANUAL_CLOSE = "MANUAL_CLOSE"
    PLAN_UPDATED = "PLAN_UPDATED"
    PLAN_REPLACED = "PLAN_REPLACED"
    CANCEL_ADD = "CANCEL_ADD"
    SYMBOL_BLOCK = "SYMBOL_BLOCK"
    EMERGENCY_ACTION = "EMERGENCY_ACTION"
    RISK_BLOCKED = "RISK_BLOCKED"
    PROTECTION_EVALUATED = "PROTECTION_EVALUATED"
    RECOVERY = "RECOVERY"


class ExitReason(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    AI_CLOSE = "AI_CLOSE"
    AI_REDUCE = "AI_REDUCE"
    MANUAL_CLOSE = "MANUAL_CLOSE"


class ProtectionTrigger(StrEnum):
    NONE = "NONE"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


# --------------------------------------------------------------------------------------
# Position re-evaluation
# --------------------------------------------------------------------------------------


class ReevaluationAction(StrEnum):
    HOLD = "HOLD"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    CANCEL_ADD = "CANCEL_ADD"
    UPDATE_STOP = "UPDATE_STOP"
    UPDATE_TP = "UPDATE_TP"
    UPDATE_INVALIDATION = "UPDATE_INVALIDATION"
    REPLACE_PLAN = "REPLACE_PLAN"


#: Actions that can enlarge exposure and therefore require the full risk gate.
RISK_INCREASING_ACTIONS: frozenset[ReevaluationAction] = frozenset({ReevaluationAction.ADD})

#: Actions that shrink or neutralize exposure; they stay available under PAUSED / SAFE_MODE /
#: EMERGENCY_STOP as long as execution and fresh core market data are usable.
RISK_REDUCING_ACTIONS: frozenset[ReevaluationAction] = frozenset(
    {ReevaluationAction.REDUCE, ReevaluationAction.CLOSE, ReevaluationAction.CANCEL_ADD}
)


class PositionReevaluation(BaseModel):
    """Structured AI verdict for one open position. Always program-validated before acting."""

    action: ReevaluationAction
    reason: str
    confidence: float = Field(ge=0, le=1, default=0.0)
    stop_loss: float | None = None
    take_profit: float | None = None
    invalidation: str | None = None
    entry_zone_lower: float | None = None
    entry_zone_upper: float | None = None
    intended_notional: float | None = None
    reduce_pct: float | None = Field(default=None, ge=0, le=1)

    def business_errors(self) -> list[str]:
        errors: list[str] = []
        action = self.action
        if action is ReevaluationAction.UPDATE_STOP and self.stop_loss is None:
            errors.append("update_stop_requires_stop_loss")
        if action is ReevaluationAction.UPDATE_TP and self.take_profit is None:
            errors.append("update_tp_requires_take_profit")
        if action is ReevaluationAction.UPDATE_INVALIDATION and not self.invalidation:
            errors.append("update_invalidation_requires_text")
        if action is ReevaluationAction.REPLACE_PLAN and not all(
            (
                self.stop_loss is not None,
                self.take_profit is not None,
                self.entry_zone_lower is not None,
                self.entry_zone_upper is not None,
            )
        ):
            errors.append("replace_plan_requires_full_plan")
        if action is ReevaluationAction.REPLACE_PLAN and (
            self.entry_zone_lower is not None
            and self.entry_zone_upper is not None
            and self.entry_zone_lower > self.entry_zone_upper
        ):
            errors.append("replace_plan_entry_zone_invalid")
        if action is ReevaluationAction.REPLACE_PLAN and (
            self.stop_loss is not None
            and self.take_profit is not None
            and self.stop_loss >= self.take_profit
        ):
            errors.append("replace_plan_price_relationship_invalid")
        if action is ReevaluationAction.ADD and not (
            self.intended_notional is not None and self.intended_notional > 0
        ):
            errors.append("add_requires_positive_notional")
        if action is ReevaluationAction.REDUCE and not (
            self.reduce_pct is not None and 0 < self.reduce_pct <= 1
        ):
            errors.append("reduce_requires_positive_pct")
        return errors


# --------------------------------------------------------------------------------------
# Result envelopes
# --------------------------------------------------------------------------------------


class ProtectionOutcome(BaseModel):
    instrument_id: str
    triggered: bool
    trigger: ProtectionTrigger = ProtectionTrigger.NONE
    exit_reason: ExitReason | None = None
    reason: str | None = None
    order_id: str | None = None
    fill_id: str | None = None
    filled_price: float | None = None
    filled_quantity: float | None = None
    cancelled_order_ids: list[str] = Field(default_factory=list)


class ControlOutcome(BaseModel):
    action: str
    accepted: bool
    operator_state: OperatorState
    system_state: SystemState
    runtime_version: int
    reason: str | None = None
    cancelled_order_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ReevaluationOutcome(BaseModel):
    instrument_id: str
    action: ReevaluationAction
    applied: bool
    reason: str | None = None
    decision_id: str | None = None
    snapshot_id: str | None = None
    order_id: str | None = None
    fill_id: str | None = None
    plan_id: str | None = None
    previous_plan_id: str | None = None
    cancelled_order_ids: list[str] = Field(default_factory=list)


class ReconciliationReport(BaseModel):
    ok: bool
    diagnostics: list[str] = Field(default_factory=list)
    invariants: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class RecoveryReport(BaseModel):
    run_mode: RunMode
    ok: bool
    started_at: datetime
    finished_at: datetime | None = None
    steps: list[str] = Field(default_factory=list)
    operator_state: OperatorState = OperatorState.NORMAL
    final_system_state: SystemState = SystemState.STARTING
    reconciliation: ReconciliationReport | None = None
    protection: list[ProtectionOutcome] = Field(default_factory=list)
    plan_revalidation: list[dict[str, Any]] = Field(default_factory=list)
    order_revalidation: list[dict[str, Any]] = Field(default_factory=list)
    execution_gap: dict[str, Any] | None = None
    active_symbols: list[str] = Field(default_factory=list)
    reason: str | None = None


# --------------------------------------------------------------------------------------
# Risk gate
# --------------------------------------------------------------------------------------


class RiskDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    system_state: SystemState = SystemState.STARTING
    operator_state: OperatorState = OperatorState.NORMAL
    price: float | None = None
    order_id: str | None = None
    fill_id: str | None = None


class ProtectionContext(BaseModel):
    """Immutable facts used to decide whether protection must fire."""

    instrument_id: str
    best_bid: float
    best_ask: float
    stop_loss: float
    take_profit: float
    data_quality: DataQuality = DataQuality.FRESH

    @field_validator("best_bid", "best_ask", "stop_loss", "take_profit")
    @classmethod
    def finite(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):  # noqa: PLR0124
            raise ValueError("protection levels must be finite")
        return value


def is_risk_increasing(side: OrderSide) -> bool:
    """V1 spot LONG: BUY increases risk, SELL reduces it."""
    return side == OrderSide.BUY


def bbo_is_fresh(bbo: BestBidAsk, now: datetime, freshness_ttl_seconds: float) -> bool:
    return (
        bbo.tradable
        and bbo.data_quality is DataQuality.FRESH
        and (now - bbo.received_at).total_seconds() <= freshness_ttl_seconds
    )
