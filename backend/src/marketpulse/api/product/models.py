"""Frozen shared contracts for UI-RD01 Product read surfaces."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from marketpulse.runtime import HostLifecycleState

PRODUCT_READ_CONTRACT_VERSION = "ui-rd01-product-read-v1"


class ReadSurfaceClass(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class OperationalAvailability(StrEnum):
    ACTIVE = "ACTIVE"
    ACCEPTED_NOT_INTEGRATED = "ACCEPTED_NOT_INTEGRATED"
    NOT_ACTIVATED = "NOT_ACTIVATED"


class ProjectionState(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    EMPTY = "EMPTY"
    UNAVAILABLE = "UNAVAILABLE"
    CAPABILITY_NOT_INTEGRATED = "CAPABILITY_NOT_INTEGRATED"


class TraceNodeState(StrEnum):
    PRESENT = "PRESENT"
    NOT_OCCURRED = "NOT_OCCURRED"
    NOT_REACHED = "NOT_REACHED"
    NOT_YET_DUE = "NOT_YET_DUE"
    NO_PROVABLE_RECORD = "NO_PROVABLE_RECORD"
    CAPABILITY_NOT_INTEGRATED = "CAPABILITY_NOT_INTEGRATED"


class ReadFailureReason(StrEnum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"


class OperationalContextDTO(BaseModel):
    run_mode: str
    runtime_instance_id: str | None
    host_state: HostLifecycleState | None
    operational_provenance: str
    context_snapshot_at: datetime


class ProjectionMetaDTO(BaseModel):
    projection: str
    contract_version: str = PRODUCT_READ_CONTRACT_VERSION
    read_surface_class: ReadSurfaceClass
    operational_availability: OperationalAvailability
    projection_state: ProjectionState
    read_failure_reason: ReadFailureReason | None = None
    snapshot_at: datetime
    observed_at: datetime | None = None
    is_partial: bool
    next_cursor: str | None = None


class RangeContextDTO(BaseModel):
    requested_range: str
    effective_start: datetime
    effective_end: datetime
    time_authority_field: str


class FreshnessDTO(BaseModel):
    observed_at: datetime | None
    evaluated_at: datetime
    age_seconds: float | None
    stale_after_seconds: float | None
    freshness_basis: str


class SourceContextDTO(BaseModel):
    source_type: str
    source_identity: str
    snapshot_at: datetime


class TraceNodeDTO[T](BaseModel):
    state: TraceNodeState
    data: T | None = None
    evidence_basis: str | None = None


class SystemSectionDTO[T](BaseModel):
    state: ProjectionState
    snapshot_at: datetime
    source: SourceContextDTO
    read_failure_reason: ReadFailureReason | None = None
    data: T | None = None


class LiveDTO(BaseModel):
    alive: bool
    run_mode: str
    local_only: bool
    instance_id: str
    host_state: HostLifecycleState


class ReadyDTO(BaseModel):
    ready: bool
    status: str
    reasons: list[str]
    evaluated_at: datetime


class HealthCheckDTO(BaseModel):
    name: str
    status: str
    updated_at: datetime | None
    reason: str | None


class HealthDTO(BaseModel):
    overall_status: str
    checks: list[HealthCheckDTO]


class RuntimeGatesDTO(BaseModel):
    risk_admission: bool
    ingress: bool
    safety: bool
    scanner: bool


class RuntimeTimestampsDTO(BaseModel):
    created_at: datetime
    started_at: datetime | None
    recovery_ready_at: datetime | None
    last_heartbeat_at: datetime | None
    last_reconciliation_at: datetime | None


class RuntimeDTO(BaseModel):
    lifecycle_state: HostLifecycleState
    uptime_seconds: float | None
    instruments: list[str]
    active_risk_instruments: list[str]
    children_live: list[str]
    gates: RuntimeGatesDTO
    timestamps: RuntimeTimestampsDTO


class ProviderSubscriptionDTO(BaseModel):
    channel: str
    instrument_id: str


class ProviderDTO(BaseModel):
    status: str
    connection_attempts: int | None
    reconnects: int | None
    constructed_by_host: bool
    subscriptions: list[ProviderSubscriptionDTO]


class MarketInstrumentDTO(BaseModel):
    instrument_id: str
    present: bool
    fresh: bool
    quality: str


class MarketProviderDTO(BaseModel):
    provider: ProviderDTO
    market: list[MarketInstrumentDTO]


class LaneTelemetryDTO(BaseModel):
    name: str
    size: int
    capacity: int
    high_water: int
    processed: int
    rejected: int
    overflow: int


class LanesDTO(BaseModel):
    scanner_lane: LaneTelemetryDTO
    safety_lanes: list[LaneTelemetryDTO]


class DatabaseSingletonDTO(BaseModel):
    application_name: str
    engine_disposed: bool | None
    owns_engine: bool
    singleton_lock_held: bool
    singleton_connection_present: bool
    singleton_lock_lost: bool


class RecoveryDTO(BaseModel):
    status: str
    ok: bool
    started_at: datetime
    finished_at: datetime | None
    ready_at: datetime | None
    reason: str | None
    final_system_state: str
    operator_state: str
    reconciliation_ok: bool | None


class ReconciliationDTO(BaseModel):
    startup_ok: bool
    last_ok: bool
    last_result: str | None
    diagnostics: list[str]
    safe_mode_latched_by_host: bool
    snapshot_at: datetime
    last_reconciliation_at: datetime | None


class OperatorSystemStateDTO(BaseModel):
    operator_state: str | None
    system_state: str | None
    blocking_incident_count: int


class IncidentDTO(BaseModel):
    incident_id: str
    incident_type: str
    run_mode: str
    instrument_id: str | None
    status: str
    reason: str
    opened_at: datetime
    resolved_at: datetime | None


class IncidentPageDTO(BaseModel):
    items: list[IncidentDTO] = Field(default_factory=list)
    next_cursor: str | None = None


class AIActivationDTO(BaseModel):
    activated: bool = False
    reevaluation_enabled: bool = False
    status: str = "NOT_ACTIVATED"
    note: str


class SystemIncidentDataDTO(BaseModel):
    live: SystemSectionDTO[LiveDTO]
    ready: SystemSectionDTO[ReadyDTO]
    health: SystemSectionDTO[HealthDTO]
    runtime: SystemSectionDTO[RuntimeDTO]
    market_provider: SystemSectionDTO[MarketProviderDTO]
    lanes: SystemSectionDTO[LanesDTO]
    database_singleton: SystemSectionDTO[DatabaseSingletonDTO]
    recovery: SystemSectionDTO[RecoveryDTO]
    reconciliation: SystemSectionDTO[ReconciliationDTO]
    operator_system_state: SystemSectionDTO[OperatorSystemStateDTO]
    incidents: SystemSectionDTO[IncidentPageDTO]
    ai_activation: SystemSectionDTO[AIActivationDTO]


class SystemIncidentReadResponse(BaseModel):
    meta: ProjectionMetaDTO
    operational_context: OperationalContextDTO
    data: SystemIncidentDataDTO | None


class CurrentMarketQuoteDTO(BaseModel):
    instrument_id: str
    bid: float | None
    ask: float | None
    received_at: datetime | None
    tradable: bool
    data_quality: str
    age_seconds: float | None
    snapshot_at: datetime


class CurrentMarketDataDTO(BaseModel):
    quotes: list[CurrentMarketQuoteDTO] = Field(default_factory=list)


class ScannerEventDTO(BaseModel):
    event_id: str
    instrument_id: str
    symbol: str
    market_type: str
    event_type: str
    event_time: datetime
    received_time: datetime
    strength: float
    priority: int
    state_version: int
    config_version: str
    producer_source: str
    runtime_binding_status: str = "NOT_RECORDED"


class ScannerEventPageDTO(BaseModel):
    items: list[ScannerEventDTO] = Field(default_factory=list)
    next_cursor: str | None = None
    as_of: datetime


class MarketScannerDataDTO(BaseModel):
    current_market: SystemSectionDTO[CurrentMarketDataDTO]
    scanner_events: SystemSectionDTO[ScannerEventPageDTO]


class MarketScannerReadResponse(BaseModel):
    meta: ProjectionMetaDTO
    operational_context: OperationalContextDTO
    range_context: RangeContextDTO
    data: MarketScannerDataDTO | None


class EvidenceIdentityDTO(BaseModel):
    evidence_id: str
    evidence_revision: int
    evidence_hash: str
    feature_snapshot_hash: str


class OpportunityDTO(BaseModel):
    opportunity_id: str
    candidate_id: str
    family_id: str
    family_version: str
    instrument_id: str
    market_type: str
    detected_at: datetime
    evidence_at: datetime
    expires_at: datetime
    source_type: str
    source_identity: str
    evidence_contract_version: str
    current_canonical_evidence: EvidenceIdentityDTO


class OpportunityPageDTO(BaseModel):
    items: list[OpportunityDTO] = Field(default_factory=list)
    next_cursor: str | None = None
    as_of: datetime


class OpportunityCollectionReadResponse(BaseModel):
    meta: ProjectionMetaDTO
    operational_context: OperationalContextDTO
    range_context: RangeContextDTO
    data: OpportunityPageDTO | None


class MarketEventTraceDTO(BaseModel):
    event_id: str
    event_type: str
    event_time: datetime
    instrument_id: str
    market_type: str


class StrategyCandidateTraceDTO(BaseModel):
    candidate_id: str
    event_id: str
    strategy_id: str
    strategy_version: str
    created_at: datetime


class ForwardOutcomeTraceDTO(BaseModel):
    outcome_id: str
    outcome_revision: int
    outcome_record_hash: str
    calculation_status: str
    due_at: datetime


class DecisionTraceDTO(BaseModel):
    decision_id: str
    status: str
    attribution_event_type: str
    decision_bound_evidence: TraceNodeDTO[EvidenceIdentityDTO]


class TradingDecisionBranchDTO(BaseModel):
    decisions: list[DecisionTraceDTO] = Field(default_factory=list)


class OpportunityTraceDataDTO(BaseModel):
    market_event: TraceNodeDTO[MarketEventTraceDTO]
    strategy_candidate: TraceNodeDTO[StrategyCandidateTraceDTO]
    opportunity: OpportunityDTO
    current_canonical_evidence: EvidenceIdentityDTO
    forward_outcomes: dict[str, TraceNodeDTO[ForwardOutcomeTraceDTO]]
    trading_decision: TraceNodeDTO[TradingDecisionBranchDTO]
    as_of: datetime


class OpportunityTraceReadResponse(BaseModel):
    meta: ProjectionMetaDTO
    operational_context: OperationalContextDTO
    data: OpportunityTraceDataDTO | None


class ProductUnavailableResponse(BaseModel):
    """Formal ``503`` body for an endpoint-wide Product snapshot failure."""

    projection: str
    contract_version: str
    read_surface_class: ReadSurfaceClass
    read_failure_reason: ReadFailureReason
    correlation_id: str


class ProductInternalErrorResponse(BaseModel):
    """Frozen ``500`` body: no product or diagnostic detail leaves the process."""

    correlation_id: str


# UI-RD01-I03 TradingAuditRead typed contract.  These DTOs deliberately expose
# only the frozen allow-list, never durable JSON payloads or ORM objects.
class TradingTraceabilityStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NOT_PROVABLE = "NOT_PROVABLE"


class TradingTraceMissingLink(StrEnum):
    DECISION = "DECISION"
    OPPORTUNITY_BINDING = "OPPORTUNITY_BINDING"
    PLAN = "PLAN"
    INTENT = "INTENT"
    ORDER = "ORDER"
    FILL = "FILL"
    LEDGER = "LEDGER"
    RISK_ATTRIBUTION = "RISK_ATTRIBUTION"
    REJECTION_CLASSIFICATION = "REJECTION_CLASSIFICATION"
    ORDER_CANCELLATION_EVENT = "ORDER_CANCELLATION_EVENT"


class TradingTraceabilityDTO(BaseModel):
    status: TradingTraceabilityStatus
    missing_links: list[TradingTraceMissingLink] = Field(default_factory=list)


class TradingProtectionState(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PROTECTED = "PROTECTED"
    UNPROTECTED = "UNPROTECTED"
    UNKNOWN = "UNKNOWN"


class TradingPositionState(StrEnum):
    OPEN = "OPEN"
    FLAT = "FLAT"


class TradingProtectionAuthorityDTO(BaseModel):
    plan_id: str
    plan_version: int
    stop_loss: float
    take_profit: float
    updated_at: datetime


class TradingPositionProtectionDTO(BaseModel):
    state: TradingProtectionState
    authority: TradingProtectionAuthorityDTO | None = None


class TradingPositionDTO(BaseModel):
    position_id: str
    instrument_id: str
    state: TradingPositionState
    quantity: float
    average_cost: float
    trade_id: str | None
    updated_at: datetime
    protection: TradingPositionProtectionDTO


class TradingAccountDTO(BaseModel):
    account_id: str
    cash_balance: float
    reserved_cash: float
    available_cash: float
    realized_pnl: float
    updated_at: datetime


class TradingOpportunityBindingDTO(BaseModel):
    opportunity_id: str
    evidence_id: str
    evidence_revision: int
    evidence_hash: str
    feature_snapshot_hash: str


class TradingDecisionDTO(BaseModel):
    decision_id: str
    snapshot_id: str
    status: str
    model: str
    created_at: datetime
    opportunity_binding: TraceNodeDTO[TradingOpportunityBindingDTO]


class TradingPlanDTO(BaseModel):
    plan_id: str
    snapshot_id: str
    decision_id: str
    instrument_id: str
    symbol: str
    plan_version: int
    status: str
    created_at: datetime
    expires_at: datetime
    ttl_expired: bool
    order_type: str
    side: str
    entry_zone: dict[str, float]
    stop_loss: float
    take_profit: float
    intended_notional: float
    invalidation: str | None
    decision: TraceNodeDTO[TradingDecisionDTO]


class TradingCollectionDTO[T](BaseModel):
    state: ProjectionState
    items: list[T] | None


class TradingOpenOrderDTO(BaseModel):
    order_id: str
    intent_id: str
    plan_id: str | None
    instrument_id: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    reserved_cash: float
    reserved_quantity: float
    created_at: datetime


class TradingPendingIntentCapabilityDTO(BaseModel):
    state: ProjectionState
    items: None = None


class TradingIntentRejectionDTO(BaseModel):
    kind: Literal["RISK", "EXECUTION"]
    attribution_event_id: str
    authority: str | None
    reason: str
    occurred_at: datetime


class TradingTimelineItemBase(BaseModel):
    timeline_event_id: str
    entity_kind: str
    entity_id: str
    event_type: str
    occurred_at: datetime
    traceability: TradingTraceabilityDTO


class TradingPlanTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["PLAN"] = "PLAN"
    event_type: Literal["PLAN_CREATED"] = "PLAN_CREATED"
    plan_id: str
    snapshot_id: str
    decision_id: str
    instrument_id: str
    symbol: str
    plan_version: int
    created_at: datetime
    expires_at: datetime


class TradingRiskTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["RISK"] = "RISK"
    event_type: Literal["RISK_ACCEPTED", "RISK_REJECTED"]
    attribution_event_id: str
    intent_id: str
    plan_id: str | None
    order_id: str | None
    authority: str | None
    reason: str | None
    opportunity_id: str | None
    evidence_id: str | None


class TradingExecutionTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["EXECUTION"] = "EXECUTION"
    event_type: Literal["EXECUTION_REJECTED"] = "EXECUTION_REJECTED"
    attribution_event_id: str
    intent_id: str
    plan_id: str | None
    reason: str
    opportunity_id: str | None
    evidence_id: str | None


class TradingIntentTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["INTENT"] = "INTENT"
    event_type: Literal["INTENT_EXECUTED", "INTENT_REJECTED"]
    intent_id: str
    plan_id: str | None
    instrument_id: str
    status: str
    reason: str | None
    created_at: datetime
    initial_rejection: TraceNodeDTO[TradingIntentRejectionDTO]


class TradingOrderCreatedTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["ORDER"] = "ORDER"
    event_type: Literal["ORDER_CREATED"] = "ORDER_CREATED"
    order_id: str
    intent_id: str
    plan_id: str | None
    instrument_id: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    created_at: datetime


class TradingOrderCancelledTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["ORDER"] = "ORDER"
    event_type: Literal["ORDER_CANCELLED"] = "ORDER_CANCELLED"
    order_id: str
    instrument_id: str
    cancelled_at: datetime


class TradingFillTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["FILL"] = "FILL"
    event_type: Literal["FILL_OCCURRED"] = "FILL_OCCURRED"
    fill_id: str
    order_id: str
    intent_id: str
    instrument_id: str
    side: str
    price: float
    quantity: float
    fee: float
    created_at: datetime


class TradingLedgerTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["LEDGER"] = "LEDGER"
    event_type: Literal["SETTLEMENT_RECORDED"] = "SETTLEMENT_RECORDED"
    entry_id: str
    fill_id: str
    instrument_id: str
    entry_type: str
    cash_delta: float
    fee: float
    settlement_realized_pnl: float
    created_at: datetime


class TradingTradeOpenTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["TRADE_OPEN"] = "TRADE_OPEN"
    event_type: Literal["TRADE_OPEN"] = "TRADE_OPEN"
    trade_id: str
    instrument_id: str
    opened_at: datetime


class TradingTradeCloseTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["TRADE_CLOSE"] = "TRADE_CLOSE"
    event_type: Literal["TRADE_CLOSE"] = "TRADE_CLOSE"
    trade_id: str
    instrument_id: str
    closed_at: datetime
    exit_reason: str | None


class TradingPositionEventTimelineItemDTO(TradingTimelineItemBase):
    entity_kind: Literal["POSITION_EVENT"] = "POSITION_EVENT"
    event_type: Literal[
        "SL_TRIGGERED",
        "TP_TRIGGERED",
        "AI_REEVALUATION",
        "ADD",
        "REDUCE",
        "CLOSE",
        "MANUAL_CLOSE",
        "PLAN_UPDATED",
        "PLAN_REPLACED",
        "CANCEL_ADD",
        "RISK_BLOCKED",
    ]
    event_id: str
    instrument_id: str
    position_id: str | None
    plan_id: str | None
    order_id: str | None
    fill_id: str | None
    created_at: datetime


TradingTimelineItem = Annotated[
    TradingPlanTimelineItemDTO
    | TradingRiskTimelineItemDTO
    | TradingExecutionTimelineItemDTO
    | TradingIntentTimelineItemDTO
    | TradingOrderCreatedTimelineItemDTO
    | TradingOrderCancelledTimelineItemDTO
    | TradingFillTimelineItemDTO
    | TradingLedgerTimelineItemDTO
    | TradingTradeOpenTimelineItemDTO
    | TradingTradeCloseTimelineItemDTO
    | TradingPositionEventTimelineItemDTO,
    Field(discriminator="event_type"),
]


class TradingTimelinePageDTO(BaseModel):
    state: ProjectionState
    items: list[TradingTimelineItem] = Field(default_factory=list)
    timeline_upper_bound: datetime


class TradingAuditDataDTO(BaseModel):
    account: TraceNodeDTO[TradingAccountDTO]
    positions: TradingCollectionDTO[TradingPositionDTO]
    active_plans: TradingCollectionDTO[TradingPlanDTO]
    open_orders: TradingCollectionDTO[TradingOpenOrderDTO]
    pending_intents: TradingPendingIntentCapabilityDTO
    timeline: TradingTimelinePageDTO


class TradingAuditReadResponse(BaseModel):
    meta: ProjectionMetaDTO
    operational_context: OperationalContextDTO
    data: TradingAuditDataDTO | None
