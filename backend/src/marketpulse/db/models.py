from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketEventRecord(Base):
    __tablename__ = "market_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_type: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SignalTimelineRecord(Base):
    __tablename__ = "signal_timeline_events"

    timeline_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    lifecycle_action: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_state: Mapped[str] = mapped_column(String(32), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_reaction: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SymbolStateStore(Base):
    __tablename__ = "symbol_states"

    instrument_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    last_event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watch_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    structure_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)


class StateTransitionRecord(Base):
    __tablename__ = "state_transitions"

    transition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)


class StrategyCandidateRecord(Base):
    __tablename__ = "strategy_candidates"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    applicable: Mapped[bool] = mapped_column(nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    setup_type: Mapped[str] = mapped_column(String(64), nullable=False)
    direction_bias: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supporting_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    contradicting_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    invalidation_hint: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DerivedObservationRecord(Base):
    __tablename__ = "derived_observations"

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class DecisionSnapshotRecord(Base):
    __tablename__ = "decision_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class AIDecisionRecord(Base):
    __tablename__ = "ai_decisions"
    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    raw_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[dict] = mapped_column(JSON, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradePlanRecord(Base):
    __tablename__ = "trade_plans"
    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class TradePlanScenarioRecord(Base):
    __tablename__ = "trade_plan_scenarios"
    scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)


class ExecutionIntentRecord(Base):
    __tablename__ = "execution_intents"
    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaperOrderRecord(Base):
    __tablename__ = "paper_orders"
    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    reserved_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    reserved_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FillRecord(Base):
    __tablename__ = "fills"
    fill_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PositionRecord(Base):
    """G3 position plus the durable protection authority of an OPEN LONG.

    `protection_plan_id` / `protection_plan_version` / `protection_stop_loss` /
    `protection_take_profit` / `protection_updated_at` carry the SL/TP authority written by the
    risk-increasing fill that opened (or last increased) the position. Reading the authority from
    this row is what lets protection outlive the originating TradePlan TTL: the plan TTL stays the
    *risk-increasing* freshness authority, while the OPEN position's protection lifetime lives
    here. All five columns are additive and nullable; the CHECK constraints below forbid a
    half-written authority and reject non-finite or inverted levels.
    """

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("run_mode", "instrument_id", name="uq_positions_mode_instrument"),
        CheckConstraint(
            "(protection_plan_id IS NULL AND protection_plan_version IS NULL "
            "AND protection_stop_loss IS NULL AND protection_take_profit IS NULL "
            "AND protection_updated_at IS NULL) "
            "OR (protection_plan_id IS NOT NULL AND protection_plan_version IS NOT NULL "
            "AND protection_stop_loss IS NOT NULL AND protection_take_profit IS NOT NULL "
            "AND protection_updated_at IS NOT NULL)",
            name="ck_positions_protection_complete",
        ),
        CheckConstraint(
            "protection_plan_version IS NULL OR protection_plan_version >= 1",
            name="ck_positions_protection_version_positive",
        ),
        # PostgreSQL does not expose isfinite(double precision) on every target version, so
        # finiteness is expressed with the two infinities: `x < 'Infinity'::float8` rejects NaN and
        # +Infinity together (PostgreSQL orders NaN above every value), and
        # `x > '-Infinity'::float8` rejects -Infinity. The relation rule is deliberately exactly
        # the executable-plan contract (`stop_loss < take_profit`) and adds nothing stricter, so a
        # plan G4 accepts can never produce a position G4 then calls POSITION_UNPROTECTED.
        CheckConstraint(
            "protection_stop_loss IS NULL OR (protection_stop_loss > '-Infinity'::float8 "
            "AND protection_stop_loss < 'Infinity'::float8 "
            "AND protection_take_profit > '-Infinity'::float8 "
            "AND protection_take_profit < 'Infinity'::float8 "
            "AND protection_stop_loss < protection_take_profit)",
            name="ck_positions_protection_prices",
        ),
    )
    position_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_cost: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    protection_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    protection_plan_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protection_stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    protection_take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    protection_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TradeRecord(Base):
    __tablename__ = "trades"
    trade_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # G4: machine-readable close reason (STOP_LOSS / TAKE_PROFIT / AI_CLOSE / AI_REDUCE /
    # MANUAL_CLOSE). Nullable and additive so existing G3 rows stay valid.
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AccountRecord(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False)
    reserved_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LedgerEntryRecord(Base):
    __tablename__ = "ledger_entries"
    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fill_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cash_delta: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class OutboxRecord(Base):
    __tablename__ = "outbox_records"
    outbox_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeControlRecord(Base):
    """G4 system/operator control facts. PostgreSQL is the restart-recovery source of truth."""

    __tablename__ = "runtime_controls"
    run_mode: Mapped[str] = mapped_column(String(16), primary_key=True)
    operator_state: Mapped[str] = mapped_column(String(32), nullable=False)
    system_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    runtime_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SymbolControlRecord(Base):
    """G4 per-instrument operator control (block / unblock). Append-audited via outbox."""

    __tablename__ = "symbol_controls"
    __table_args__ = (
        UniqueConstraint("run_mode", "instrument_id", name="uq_symbol_controls_mode_instrument"),
    )
    control_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class IncidentRecord(Base):
    """G4 minimal persisted incident. Detector output only; never a repair engine."""

    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    instrument_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PositionEventRecord(Base):
    """G4 append-only position lifecycle audit. `dedupe_key` gives DB-level idempotency."""

    __tablename__ = "position_events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    position_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fill_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("run_mode", "dedupe_key", name="uq_position_events_dedupe"),
    )


class EdgeOpportunityEvidenceRecord(Base):
    """SE-02 Edge: immutable opportunity evidence revision. Append-only by contract.

    `uq_edge_evidence_opportunity_revision` collapses "same opportunity + same
    revision" onto a single row, so a different hash for the same revision can only
    fail closed. `fk_edge_evidence_supersedes` proves that a supersedes target both
    exists and belongs to the same opportunity, without a trigger framework.

    The reference quote is optional: an opportunity whose reference BBO is missing
    or stale is still persisted, with `reference_bid` / `reference_ask` /
    `reference_received_at` left NULL. `ck_edge_evidence_reference_consistency`
    keeps that dichotomy exact -- `OK` requires a usable quote, and
    `REFERENCE_MISSING` / `REFERENCE_STALE` require all three columns to be NULL.
    """

    __tablename__ = "edge_opportunity_evidence"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "evidence_revision", name="uq_edge_evidence_opportunity_revision"
        ),
        UniqueConstraint("evidence_id", "opportunity_id", name="uq_edge_evidence_id_opportunity"),
        ForeignKeyConstraint(
            ["supersedes_evidence_id", "opportunity_id"],
            ["edge_opportunity_evidence.evidence_id", "edge_opportunity_evidence.opportunity_id"],
            name="fk_edge_evidence_supersedes",
        ),
        CheckConstraint("evidence_revision >= 1", name="ck_edge_evidence_revision_positive"),
        CheckConstraint("family_id = 'BREAKOUT_RETEST'", name="ck_edge_evidence_family"),
        CheckConstraint("market_type IN ('SPOT', 'SWAP')", name="ck_edge_evidence_market_type"),
        CheckConstraint(
            "source_type IN ('HISTORICAL_REPLAY', 'FORWARD_PAPER')",
            name="ck_edge_evidence_source_type",
        ),
        CheckConstraint(
            "reference_data_status IN ('OK', 'REFERENCE_MISSING', 'REFERENCE_STALE')",
            name="ck_edge_evidence_reference_status",
        ),
        CheckConstraint(
            "(reference_data_status = 'OK' AND reference_bid IS NOT NULL "
            "AND reference_ask IS NOT NULL AND reference_received_at IS NOT NULL "
            "AND reference_bid > 0 AND reference_ask > 0 AND reference_bid <= reference_ask) "
            "OR (reference_data_status IN ('REFERENCE_MISSING', 'REFERENCE_STALE') "
            "AND reference_bid IS NULL AND reference_ask IS NULL "
            "AND reference_received_at IS NULL)",
            name="ck_edge_evidence_reference_consistency",
        ),
        CheckConstraint(
            "supersedes_evidence_id IS NOT NULL OR evidence_revision = 1",
            name="ck_edge_evidence_supersedes_required",
        ),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False)
    family_version: Mapped[str] = mapped_column(String(64), nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_type: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_snapshot_hash_version: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    source_manifest_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reference_data_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feature_snapshot_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EdgeBboObservationRecord(Base):
    """SE-02 Edge: normalized L1 BBO stored only as a forward-horizon reference point.

    `available_at` is the normalized quote receive time, so the frozen V1 causal
    rule requires `available_at = received_at` (`ck_edge_bbo_causal_time`).

    Persistence contract only. No runtime quote capture exists in this batch.
    """

    __tablename__ = "edge_bbo_observations"
    __table_args__ = (
        CheckConstraint("bid > 0 AND ask > 0 AND ask >= bid", name="ck_edge_bbo_prices"),
        CheckConstraint("available_at = received_at", name="ck_edge_bbo_causal_time"),
        CheckConstraint("market_type IN ('SPOT', 'SWAP')", name="ck_edge_bbo_market_type"),
        CheckConstraint(
            "data_quality IN ('FRESH', 'STALE', 'UNAVAILABLE')", name="ck_edge_bbo_data_quality"
        ),
        Index(
            "ix_edge_bbo_instrument_market_available",
            "instrument_id",
            "market_type",
            "available_at",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False)
    market_type: Mapped[str] = mapped_column(String(16), nullable=False)
    bid: Mapped[float] = mapped_column(Float, nullable=False)
    ask: Mapped[float] = mapped_column(Float, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False)
    tradable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EdgeForwardOutcomeRecord(Base):
    """SE-02 Edge: immutable forward-outcome revision. No calculator runs in this batch.

    Only terminal statuses are persisted (`COMPLETE` / `INSUFFICIENT_DATA` /
    `INVALID`). There is no `PENDING` row: while `clock < due_at` no row exists and
    pending is derived from opportunity + horizon + current clock.
    """

    __tablename__ = "edge_forward_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "evidence_id",
            "horizon",
            "outcome_revision",
            name="uq_edge_outcome_evidence_horizon_revision",
        ),
        UniqueConstraint("outcome_id", "opportunity_id", name="uq_edge_outcome_id_opportunity"),
        ForeignKeyConstraint(
            ["evidence_id", "opportunity_id"],
            ["edge_opportunity_evidence.evidence_id", "edge_opportunity_evidence.opportunity_id"],
            name="fk_edge_outcome_evidence",
        ),
        ForeignKeyConstraint(
            ["supersedes_outcome_id", "opportunity_id"],
            ["edge_forward_outcomes.outcome_id", "edge_forward_outcomes.opportunity_id"],
            name="fk_edge_outcome_supersedes",
        ),
        CheckConstraint("outcome_revision >= 1", name="ck_edge_outcome_revision_positive"),
        CheckConstraint("horizon IN ('30s', '5m', '15m', '1h')", name="ck_edge_outcome_horizon"),
        CheckConstraint(
            "calculation_status IN ('COMPLETE', 'INSUFFICIENT_DATA', 'INVALID')",
            name="ck_edge_outcome_calculation_status",
        ),
        CheckConstraint(
            "opportunity_lifecycle_at_horizon IS NULL OR opportunity_lifecycle_at_horizon IN "
            "('ACTIVE', 'EXPIRED')",
            name="ck_edge_outcome_lifecycle",
        ),
        CheckConstraint(
            "source_type IN ('HISTORICAL_REPLAY', 'FORWARD_PAPER')",
            name="ck_edge_outcome_source_type",
        ),
        CheckConstraint(
            "supersedes_outcome_id IS NOT NULL OR outcome_revision = 1",
            name="ck_edge_outcome_supersedes_required",
        ),
    )

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    horizon: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    outcome_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_outcome_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    opportunity_lifecycle_at_horizon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_bbo_observation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    end_bbo_observation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    mfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    executable_long_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_adjusted_forward_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_diagnostics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cost_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calculation_digest_version: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome_record_hash_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EdgeAttributionEventRecord(Base):
    """SE-02 Edge: generic, versioned, append-only attribution lineage.

    Records lineage references only. It never redefines G3/G4 economic semantics.
    """

    __tablename__ = "edge_attribution_events"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('AI', 'PLAN', 'RISK', 'EXECUTION', 'ECONOMIC_RESULT')",
            name="ck_edge_attribution_subject_type",
        ),
    )

    attribution_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
