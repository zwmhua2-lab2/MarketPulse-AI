"""Frozen shared contracts for UI-RD01 Product read surfaces."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

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
