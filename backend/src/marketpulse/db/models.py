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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    __table_args__ = (
        CheckConstraint(
            "(decision_invocation_id IS NULL AND evidence_id IS NULL "
            "AND input_binding_digest IS NULL AND decision_requested_at IS NULL "
            "AND decision_deadline_at IS NULL) "
            "OR (decision_invocation_id IS NOT NULL AND evidence_id IS NOT NULL "
            "AND input_binding_digest IS NOT NULL AND decision_requested_at IS NOT NULL "
            "AND decision_deadline_at IS NOT NULL)",
            name="ck_decision_snapshots_advisory_binding_atomic",
        ),
        CheckConstraint(
            "evidence_revision IS NULL OR evidence_revision >= 1",
            name="ck_decision_snapshots_advisory_evidence_revision",
        ),
        CheckConstraint(
            "deadline_duration_ms IS NULL OR deadline_duration_ms > 0",
            name="ck_decision_snapshots_advisory_deadline_positive",
        ),
        CheckConstraint(
            "decision_deadline_at IS NULL OR decision_deadline_at > decision_requested_at",
            name="ck_decision_snapshots_advisory_deadline_order",
        ),
    )
    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    # --- PRE-01B-I2 Shadow binding facts (D2 §24.2). Additive and nullable so every
    # legacy non-Advisory snapshot stays valid; a Shadow snapshot carries the complete
    # binding or none of it (`ck_decision_snapshots_advisory_binding_atomic`).
    decision_invocation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feature_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    snapshot_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_binding_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    advisory_config_epoch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline_policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AIDecisionRecord(Base):
    """Normalized provider-result artifact.

    Still the accepted G3 normalized-result row for the legacy decision path. Under
    PRE-01B-I2 it is additionally the *optional* normalized provider artifact of one
    Advisory Attempt, and it is explicitly **not** the no-provider terminal authority:
    the Invocation row owns that. `ck_ai_decisions_advisory_origin_pair` forces a new
    Advisory row to carry both `decision_invocation_id` and `attempt_id`, so a provider
    result can never exist without durable Attempt provenance (D2 §14.2 item 3).
    """

    __tablename__ = "ai_decisions"
    __table_args__ = (
        CheckConstraint(
            "(decision_invocation_id IS NULL AND attempt_id IS NULL) "
            "OR (decision_invocation_id IS NOT NULL AND attempt_id IS NOT NULL)",
            name="ck_ai_decisions_advisory_origin_pair",
        ),
        UniqueConstraint(
            "decision_invocation_id",
            "decision_id",
            "attempt_id",
            name="uq_ai_decisions_advisory_origin",
        ),
        Index(
            "uq_ai_decisions_advisory_invocation",
            "decision_invocation_id",
            unique=True,
            postgresql_where=text("decision_invocation_id IS NOT NULL"),
        ),
        ForeignKeyConstraint(
            ["decision_invocation_id", "attempt_id"],
            [
                "advisory_decision_attempts.decision_invocation_id",
                "advisory_decision_attempts.attempt_id",
            ],
            name="fk_ai_decisions_advisory_attempt",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
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
    # --- PRE-01B-I2 Attempt-origin linkage (D2 §24.2). Additive and nullable.
    decision_invocation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_binding_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pair_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    arm_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    configured_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_reported_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
        CheckConstraint(
            "advisory_admission_state IN ('LEGACY_PRE_I2', 'UNSTAGED', 'GATE_A_DISABLED', "
            "'INVOCATION_CREATED', 'ADMISSION_FAILED_FINAL')",
            name="ck_advisory_evidence_state",
        ),
        CheckConstraint(
            "advisory_treatment_participation IS NULL OR advisory_treatment_participation IN "
            "('PARTICIPATE_LONG', 'NO_LONG', 'NO_LONG_UNBOUND')",
            name="ck_advisory_evidence_participation",
        ),
        CheckConstraint(
            "advisory_admission_state <> 'UNSTAGED' OR (advisory_admission_reason_code IS NULL "
            "AND advisory_treatment_participation IS NULL "
            "AND advisory_admission_seed_version IS NULL "
            "AND advisory_admission_seed_digest IS NULL AND advisory_admission_seed IS NULL "
            "AND advisory_decision_invocation_id IS NULL)",
            name="ck_advisory_evidence_unstaged_bare",
        ),
        CheckConstraint(
            "advisory_admission_state NOT IN ('LEGACY_PRE_I2', 'GATE_A_DISABLED') "
            "OR (advisory_admission_reason_code IS NULL "
            "AND advisory_treatment_participation IS NULL "
            "AND advisory_admission_seed_version IS NULL "
            "AND advisory_admission_seed_digest IS NULL AND advisory_admission_seed IS NULL "
            "AND advisory_decision_invocation_id IS NULL)",
            name="ck_advisory_evidence_classification_bare",
        ),
        CheckConstraint(
            "(advisory_admission_seed_version IS NULL AND advisory_admission_seed_digest IS NULL "
            "AND advisory_admission_seed IS NULL) "
            "OR (advisory_admission_seed_version IS NOT NULL "
            "AND advisory_admission_seed_digest IS NOT NULL "
            "AND advisory_admission_seed IS NOT NULL)",
            name="ck_advisory_evidence_seed_atomic",
        ),
        CheckConstraint(
            "advisory_admission_state <> 'ADMISSION_FAILED_FINAL' "
            "OR advisory_admission_reason_code <> 'ADMISSION_STAGING_FAILED_UNBOUND' "
            "OR (advisory_admission_seed_version IS NULL "
            "AND advisory_admission_seed_digest IS NULL AND advisory_admission_seed IS NULL "
            "AND advisory_decision_invocation_id IS NULL "
            "AND advisory_treatment_participation = 'NO_LONG_UNBOUND')",
            name="ck_advisory_evidence_unbound_terminal",
        ),
        CheckConstraint(
            "advisory_admission_state <> 'ADMISSION_FAILED_FINAL' "
            "OR advisory_admission_reason_code = 'ADMISSION_STAGING_FAILED_UNBOUND' "
            "OR (advisory_admission_seed_version IS NOT NULL "
            "AND advisory_admission_seed_digest IS NOT NULL "
            "AND advisory_admission_seed IS NOT NULL)",
            name="ck_advisory_evidence_terminal_requires_seed",
        ),
        CheckConstraint(
            "advisory_admission_state <> 'INVOCATION_CREATED' "
            "OR (advisory_admission_seed_version IS NOT NULL "
            "AND advisory_admission_seed_digest IS NOT NULL "
            "AND advisory_admission_seed IS NOT NULL "
            "AND advisory_decision_invocation_id IS NOT NULL)",
            name="ck_advisory_evidence_invocation_created",
        ),
        CheckConstraint(
            "advisory_decision_invocation_id IS NULL "
            "OR advisory_admission_state = 'INVOCATION_CREATED'",
            name="ck_advisory_evidence_invocation_only_created",
        ),
        ForeignKeyConstraint(
            ["advisory_decision_invocation_id"],
            ["advisory_decision_invocations.decision_invocation_id"],
            name="fk_advisory_evidence_invocation",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_edge_opportunity_evidence_advisory_state", "advisory_admission_state"),
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
    # --- PRE-01B-I2 durable Advisory admission accounting (D2 §24.2) ------------------
    # These columns are deliberately outside `evidence_hash`, the Evidence immutable
    # payload and the revision identity: the accepted SE-02A Evidence contract is
    # unchanged. Rows that existed before the upgrade are fixed to `LEGACY_PRE_I2` and
    # every new row's PostgreSQL default is the bare marker `UNSTAGED`; neither is ever
    # retroactively rebound to an experiment/pair/arm. A valid frozen-`DISABLED` startup
    # epoch lets the original formal Evidence INSERT write the literal
    # `GATE_A_DISABLED` in the same statement, which is the only classification that may
    # bypass the admission SAVEPOINT.
    advisory_admission_state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'UNSTAGED'")
    )
    advisory_admission_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    advisory_treatment_participation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    advisory_admission_seed_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    advisory_admission_seed_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    advisory_admission_seed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    advisory_decision_invocation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AdvisoryDecisionInvocationRecord(Base):
    """PRE-01B-I2: one row per logical Advisory decision invocation.

    This row — and only this row — is the logical final-result authority. A reader must
    never infer the result by ordering Attempt or `ai_decisions` timestamps: the five
    final fields (`final_status`, `final_reason_code`, `finalized_at`, `final_attempt_id`,
    `final_decision_id`) are written once, in one transaction, under the Invocation row
    lock, and the completeness / named-nullability CHECKs below make a half-written or
    doubly-written terminal state unrepresentable (D2 §14.2).

    Both cycle-closing foreign keys into this table are `DEFERRABLE INITIALLY DEFERRED`
    so the admission SAVEPOINT (Evidence <-> Invocation) and the finalizer transaction
    (Invocation <-> Attempt <-> AIDecision) can each commit atomically.
    """

    __tablename__ = "advisory_decision_invocations"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id", "pair_id", "arm_id", name="uq_advisory_invocation_experiment_pair_arm"
        ),
        CheckConstraint(
            "state IN ('ADMITTED', 'ACTIVE', 'RETRY_PENDING', 'FINAL')",
            name="ck_advisory_invocation_state",
        ),
        CheckConstraint("evidence_revision >= 1", name="ck_advisory_invocation_revision_positive"),
        CheckConstraint(
            "decision_deadline_at > decision_requested_at",
            name="ck_advisory_invocation_deadline_order",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_advisory_invocation_updated_order"),
        CheckConstraint(
            "(state = 'FINAL' AND final_status IS NOT NULL AND final_reason_code IS NOT NULL "
            "AND finalized_at IS NOT NULL) "
            "OR (state <> 'FINAL' AND final_status IS NULL AND final_reason_code IS NULL "
            "AND finalized_at IS NULL AND final_attempt_id IS NULL AND final_decision_id IS NULL)",
            name="ck_advisory_invocation_final_completeness",
        ),
        CheckConstraint(
            "(final_attempt_id IS NULL AND final_decision_id IS NULL AND ("
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'DEADLINE_EXPIRED_BEFORE_PROVIDER') OR "
            "(final_status = 'CAPACITY_BLOCKED' AND final_reason_code = 'ADVISORY_QUEUE_REJECTED') OR "
            "(final_status = 'CAPACITY_BLOCKED' AND final_reason_code = 'ADVISORY_DB_CAPACITY_UNAVAILABLE') OR "
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'EVIDENCE_SUPERSEDED_BEFORE_PROVIDER') OR "
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'OPPORTUNITY_STALE_BEFORE_PROVIDER') OR "
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'ACTIVATION_DISABLED_BEFORE_PROVIDER') OR "
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'BINDING_INVALID_BEFORE_PROVIDER') OR "
            "(final_status = 'STALE_DECISION' AND final_reason_code = 'EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER') OR "
            "(final_status = 'INVALID_SCHEMA' AND final_reason_code = 'SHUTDOWN_BEFORE_PROVIDER')"
            ")) OR final_attempt_id IS NOT NULL",
            name="ck_advisory_invocation_no_attempt_reason",
        ),
        CheckConstraint(
            "final_decision_id IS NULL OR final_attempt_id IS NOT NULL",
            name="ck_advisory_invocation_final_decision_requires_attempt",
        ),
        ForeignKeyConstraint(
            ["snapshot_id"],
            ["decision_snapshots.snapshot_id"],
            name="fk_advisory_invocation_snapshot",
        ),
        ForeignKeyConstraint(
            ["evidence_id", "opportunity_id"],
            [
                "edge_opportunity_evidence.evidence_id",
                "edge_opportunity_evidence.opportunity_id",
            ],
            name="fk_advisory_invocation_evidence",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["decision_invocation_id", "final_attempt_id"],
            [
                "advisory_decision_attempts.decision_invocation_id",
                "advisory_decision_attempts.attempt_id",
            ],
            name="fk_advisory_invocation_final_attempt",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["decision_invocation_id", "final_decision_id", "final_attempt_id"],
            [
                "ai_decisions.decision_invocation_id",
                "ai_decisions.decision_id",
                "ai_decisions.attempt_id",
            ],
            name="fk_advisory_invocation_final_decision",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_advisory_decision_invocations_state", "state", "decision_deadline_at"),
        Index("ix_advisory_decision_invocations_opportunity", "opportunity_id"),
    )

    decision_invocation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    experiment_definition_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    pair_id: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_arm_id: Mapped[str] = mapped_column(String(64), nullable=False)
    treatment_arm_id: Mapped[str] = mapped_column(String(64), nullable=False)
    arm_id: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_participation: Mapped[str] = mapped_column(String(32), nullable=False)
    input_binding_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    treatment_version: Mapped[str] = mapped_column(String(64), nullable=False)
    configured_provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    configured_model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    final_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_attempt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    final_decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdvisoryDecisionAttemptRecord(Base):
    """PRE-01B-I2: one row per provider attempt; durable *before* the provider call.

    A real provider call always has a preceding durable Attempt row (D2 §14.3), so no
    provider outcome can exist without provenance. Retry adds a row here and never a new
    Invocation or final identity; `fk_advisory_attempt_prior` keeps the retry lineage
    inside one Invocation, matching the frozen "same invocation / same input binding /
    same original deadline" rule.

    Its lifecycle literal set is the union of the tokens the accepted contract names
    verbatim: `STARTED` (§14.3), the terminal audit markers `DUPLICATE_SUPPRESSED` /
    `LATE_RESULT` (§14.4) and the process-loss markers `PROCESS_LOST` / `ABANDONED`
    (§15, §20.2). `COMPLETED` marks an attempt whose normalized outcome was persisted.

    Token/cost provenance is explicitly three-state: either a usage/cost fact is present,
    or `usage_unavailable_reason` records *why* it is unknown. A silent NULL is what the
    contract forbids, and the CHECKs make that unrepresentable.
    """

    __tablename__ = "advisory_decision_attempts"
    __table_args__ = (
        UniqueConstraint(
            "decision_invocation_id",
            "attempt_number",
            name="uq_advisory_attempt_invocation_number",
        ),
        UniqueConstraint(
            "decision_invocation_id", "attempt_id", name="uq_advisory_attempt_invocation_attempt"
        ),
        CheckConstraint("attempt_number >= 1", name="ck_advisory_attempt_number_positive"),
        CheckConstraint(
            "attempt_state IN ('STARTED', 'COMPLETED', 'PROCESS_LOST', 'ABANDONED', "
            "'DUPLICATE_SUPPRESSED', 'LATE_RESULT')",
            name="ck_advisory_attempt_state",
        ),
        CheckConstraint(
            "prior_attempt_id IS NULL OR attempt_number > 1",
            name="ck_advisory_attempt_prior_number",
        ),
        CheckConstraint(
            "retry_reason IS NULL OR retry_class IS NOT NULL", name="ck_advisory_attempt_retry_pair"
        ),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_advisory_attempt_latency"),
        CheckConstraint(
            "(input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL) "
            "OR usage_unavailable_reason IS NULL",
            name="ck_advisory_attempt_usage_exclusive",
        ),
        CheckConstraint(
            "(input_tokens IS NULL OR input_tokens >= 0) "
            "AND (output_tokens IS NULL OR output_tokens >= 0) "
            "AND (total_tokens IS NULL OR total_tokens >= 0)",
            name="ck_advisory_attempt_usage_non_negative",
        ),
        CheckConstraint(
            "(monetary_cost IS NULL AND pricing_version IS NULL) "
            "OR (monetary_cost IS NOT NULL AND pricing_version IS NOT NULL)",
            name="ck_advisory_attempt_cost_pair",
        ),
        CheckConstraint(
            "monetary_cost IS NULL OR monetary_cost >= 0",
            name="ck_advisory_attempt_cost_non_negative",
        ),
        ForeignKeyConstraint(
            ["decision_invocation_id"],
            ["advisory_decision_invocations.decision_invocation_id"],
            name="fk_advisory_attempt_invocation",
        ),
        ForeignKeyConstraint(
            ["decision_invocation_id", "prior_attempt_id"],
            [
                "advisory_decision_attempts.decision_invocation_id",
                "advisory_decision_attempts.attempt_id",
            ],
            name="fk_advisory_attempt_prior",
        ),
    )

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_invocation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_state: Mapped[str] = mapped_column(String(32), nullable=False)
    retry_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retry_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prior_attempt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_response_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    configured_provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    configured_model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_reported_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_binding_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_unavailable_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    monetary_cost: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    pricing_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    validation_errors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    redacted_request_envelope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    redacted_response_envelope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


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


class EdgeOpportunityCaptureAnchorRecord(Base):
    """SE-ARCH-FIX-01 durable Forward Paper admission fact (append-only)."""

    __tablename__ = "edge_opportunity_capture_anchors"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "evidence_revision", name="uq_edge_capture_anchor_opportunity_revision"
        ),
        ForeignKeyConstraint(
            ["reference_bbo_observation_id"],
            ["edge_bbo_observations.observation_id"],
            name="fk_edge_capture_anchor_reference_bbo",
        ),
        CheckConstraint("evidence_revision >= 1", name="ck_edge_capture_anchor_revision_positive"),
        CheckConstraint(
            "source_type = 'FORWARD_PAPER'", name="ck_edge_capture_anchor_forward_paper"
        ),
        CheckConstraint(
            "reference_data_status IN ('OK', 'REFERENCE_MISSING', 'REFERENCE_STALE')",
            name="ck_edge_capture_anchor_reference_status",
        ),
        CheckConstraint(
            "(reference_data_status = 'OK' AND reference_bbo_observation_id IS NOT NULL) "
            "OR (reference_data_status IN ('REFERENCE_MISSING', 'REFERENCE_STALE') "
            "AND reference_bbo_observation_id IS NULL)",
            name="ck_edge_capture_anchor_reference_bbo_consistency",
        ),
        Index("ix_edge_capture_anchor_event_id", "event_id"),
    )

    opportunity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_data_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_bbo_observation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    source_manifest_id: Mapped[str] = mapped_column(String(64), nullable=False)
    forward_admission_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    forward_admission_event_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    forward_admission_proof_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor_payload_version: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    anchor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_hash_version: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EdgeOpportunityCaptureAnchorOrphanRecord(Base):
    """Append-only, restart-visible classification of an unconsumable capture anchor."""

    __tablename__ = "edge_opportunity_capture_anchor_orphans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["opportunity_id", "evidence_revision"],
            [
                "edge_opportunity_capture_anchors.opportunity_id",
                "edge_opportunity_capture_anchors.evidence_revision",
            ],
            name="fk_edge_capture_anchor_orphan_anchor",
        ),
        CheckConstraint(
            "classification = 'UNVERIFIABLE_ORPHAN'",
            name="ck_edge_capture_anchor_orphan_classification",
        ),
        CheckConstraint("evidence_revision >= 1", name="ck_edge_capture_anchor_orphan_revision_positive"),
    )

    opportunity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    expected_precondition: Mapped[dict] = mapped_column(JSON, nullable=False)
    actual_precondition: Mapped[dict] = mapped_column(JSON, nullable=False)
    orphan_version: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_hash_version: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EdgeForwardOutcomeRecord(Base):
    """SE-02 Edge: immutable forward-outcome revision. No calculator runs in this batch.

    Only terminal statuses are persisted (`COMPLETE` / `INSUFFICIENT_DATA` /
    `INVALID`). There is no `PENDING` row: while `clock < due_at` no row exists and
    pending is derived from opportunity + horizon + current clock.

    A revision chain is scoped to `(opportunity_id, evidence_id, horizon)`:
    `fk_edge_outcome_supersedes` carries all three keys, so PostgreSQL itself refuses
    a supersedes link that crosses evidence revisions, horizons or opportunities.
    Revision adjacency is not enforceable by a foreign key and stays a service-layer
    rule.
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
        UniqueConstraint(
            "outcome_id",
            "opportunity_id",
            "evidence_id",
            "horizon",
            name="uq_edge_outcome_id_scope",
        ),
        ForeignKeyConstraint(
            ["evidence_id", "opportunity_id"],
            ["edge_opportunity_evidence.evidence_id", "edge_opportunity_evidence.opportunity_id"],
            name="fk_edge_outcome_evidence",
        ),
        ForeignKeyConstraint(
            ["supersedes_outcome_id", "opportunity_id", "evidence_id", "horizon"],
            [
                "edge_forward_outcomes.outcome_id",
                "edge_forward_outcomes.opportunity_id",
                "edge_forward_outcomes.evidence_id",
                "edge_forward_outcomes.horizon",
            ],
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
