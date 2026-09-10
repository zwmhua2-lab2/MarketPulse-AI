"""create SE-02 edge evidence, BBO observation, forward outcome and attribution persistence

Additive only: four new Edge tables plus Edge-specific indexes and constraints. No
existing G2/G3/G4/G5 table semantics, risk rules, execution rules or state machine
semantics are modified.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0005"
down_revision: str | None = "20260905_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "edge_opportunity_evidence",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("opportunity_id", sa.String(64), nullable=False),
        sa.Column("candidate_id", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(64), nullable=False),
        sa.Column("family_version", sa.String(64), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("market_type", sa.String(16), nullable=False),
        sa.Column("evidence_revision", sa.Integer(), nullable=False),
        sa.Column("evidence_contract_version", sa.String(64), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("feature_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("feature_snapshot_hash_version", sa.String(64), nullable=False),
        sa.Column("supersedes_evidence_id", sa.String(64), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_identity", sa.String(128), nullable=False),
        sa.Column("source_manifest_id", sa.String(64), nullable=False),
        sa.Column("reference_bid", sa.Float(), nullable=False),
        sa.Column("reference_ask", sa.Float(), nullable=False),
        sa.Column("reference_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_data_status", sa.String(32), nullable=False),
        sa.Column("reference_data_reason", sa.String(64), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), nullable=False),
        sa.Column("feature_snapshot_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "opportunity_id", "evidence_revision", name="uq_edge_evidence_opportunity_revision"
        ),
        sa.UniqueConstraint("evidence_id", "opportunity_id", name="uq_edge_evidence_id_opportunity"),
        sa.ForeignKeyConstraint(
            ["supersedes_evidence_id", "opportunity_id"],
            ["edge_opportunity_evidence.evidence_id", "edge_opportunity_evidence.opportunity_id"],
            name="fk_edge_evidence_supersedes",
        ),
        sa.CheckConstraint("evidence_revision >= 1", name="ck_edge_evidence_revision_positive"),
        sa.CheckConstraint("family_id = 'BREAKOUT_RETEST'", name="ck_edge_evidence_family"),
        sa.CheckConstraint("market_type IN ('SPOT', 'SWAP')", name="ck_edge_evidence_market_type"),
        sa.CheckConstraint(
            "source_type IN ('HISTORICAL_REPLAY', 'FORWARD_PAPER')",
            name="ck_edge_evidence_source_type",
        ),
        sa.CheckConstraint(
            "reference_data_status IN ('OK', 'DEGRADED', 'UNAVAILABLE')",
            name="ck_edge_evidence_reference_status",
        ),
        sa.CheckConstraint(
            "supersedes_evidence_id IS NOT NULL OR evidence_revision = 1",
            name="ck_edge_evidence_supersedes_required",
        ),
    )

    op.create_table(
        "edge_bbo_observations",
        sa.Column("observation_id", sa.String(64), primary_key=True),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("market_type", sa.String(16), nullable=False),
        sa.Column("bid", sa.Float(), nullable=False),
        sa.Column("ask", sa.Float(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_quality", sa.String(16), nullable=False),
        sa.Column("tradable", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("source_sequence", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("bid > 0 AND ask > 0 AND ask >= bid", name="ck_edge_bbo_prices"),
        sa.CheckConstraint("market_type IN ('SPOT', 'SWAP')", name="ck_edge_bbo_market_type"),
        sa.CheckConstraint(
            "data_quality IN ('FRESH', 'STALE', 'UNAVAILABLE')", name="ck_edge_bbo_data_quality"
        ),
    )

    op.create_table(
        "edge_forward_outcomes",
        sa.Column("outcome_id", sa.String(64), primary_key=True),
        sa.Column("opportunity_id", sa.String(64), nullable=False),
        sa.Column("evidence_id", sa.String(64), nullable=False),
        sa.Column("horizon", sa.String(8), nullable=False),
        sa.Column("outcome_revision", sa.Integer(), nullable=False),
        sa.Column("supersedes_outcome_id", sa.String(64), nullable=True),
        sa.Column("outcome_contract_version", sa.String(64), nullable=False),
        sa.Column("calculation_status", sa.String(32), nullable=False),
        sa.Column("opportunity_lifecycle_at_horizon", sa.String(32), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_identity", sa.String(128), nullable=False),
        sa.Column("reference_bbo_observation_id", sa.String(64), nullable=True),
        sa.Column("end_bbo_observation_id", sa.String(64), nullable=True),
        sa.Column("reference_price", sa.Float(), nullable=True),
        sa.Column("end_bid", sa.Float(), nullable=True),
        sa.Column("end_ask", sa.Float(), nullable=True),
        sa.Column("mfe", sa.Float(), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("reference_return", sa.Float(), nullable=True),
        sa.Column("executable_long_return", sa.Float(), nullable=True),
        sa.Column("cost_adjusted_forward_return", sa.Float(), nullable=True),
        sa.Column("completeness_diagnostics", sa.JSON(), nullable=False),
        sa.Column("cost_policy", sa.String(64), nullable=False),
        sa.Column("cost_model_version", sa.String(64), nullable=False),
        sa.Column("calculator_version", sa.String(64), nullable=False),
        sa.Column("calculation_digest", sa.String(64), nullable=True),
        sa.Column("calculation_digest_version", sa.String(64), nullable=False),
        sa.Column("outcome_record_hash", sa.String(64), nullable=False),
        sa.Column("outcome_record_hash_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "opportunity_id",
            "evidence_id",
            "horizon",
            "outcome_revision",
            name="uq_edge_outcome_evidence_horizon_revision",
        ),
        sa.UniqueConstraint("outcome_id", "opportunity_id", name="uq_edge_outcome_id_opportunity"),
        sa.ForeignKeyConstraint(
            ["evidence_id", "opportunity_id"],
            ["edge_opportunity_evidence.evidence_id", "edge_opportunity_evidence.opportunity_id"],
            name="fk_edge_outcome_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_outcome_id", "opportunity_id"],
            ["edge_forward_outcomes.outcome_id", "edge_forward_outcomes.opportunity_id"],
            name="fk_edge_outcome_supersedes",
        ),
        sa.CheckConstraint("outcome_revision >= 1", name="ck_edge_outcome_revision_positive"),
        sa.CheckConstraint("horizon IN ('30s', '5m', '15m', '1h')", name="ck_edge_outcome_horizon"),
        sa.CheckConstraint(
            "calculation_status IN "
            "('PENDING', 'CALCULATED', 'INCOMPLETE_DATA', 'NOT_APPLICABLE', 'FAILED')",
            name="ck_edge_outcome_calculation_status",
        ),
        sa.CheckConstraint(
            "opportunity_lifecycle_at_horizon IS NULL OR opportunity_lifecycle_at_horizon IN "
            "('ACTIVE', 'EXPIRED', 'INVALIDATED', 'UNKNOWN')",
            name="ck_edge_outcome_lifecycle",
        ),
        sa.CheckConstraint(
            "source_type IN ('HISTORICAL_REPLAY', 'FORWARD_PAPER')",
            name="ck_edge_outcome_source_type",
        ),
        sa.CheckConstraint(
            "supersedes_outcome_id IS NOT NULL OR outcome_revision = 1",
            name="ck_edge_outcome_supersedes_required",
        ),
    )

    op.create_table(
        "edge_attribution_events",
        sa.Column("attribution_event_id", sa.String(64), primary_key=True),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("opportunity_id", sa.String(64), nullable=True),
        sa.Column("evidence_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "subject_type IN ('AI', 'PLAN', 'RISK', 'EXECUTION', 'ECONOMIC_RESULT')",
            name="ck_edge_attribution_subject_type",
        ),
    )

    for table, columns in {
        "edge_opportunity_evidence": ["opportunity_id", "instrument_id"],
        "edge_forward_outcomes": ["opportunity_id", "evidence_id", "horizon"],
        "edge_attribution_events": ["subject_type", "event_type", "opportunity_id"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index(
        "ix_edge_bbo_instrument_market_available",
        "edge_bbo_observations",
        ["instrument_id", "market_type", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_edge_bbo_instrument_market_available", table_name="edge_bbo_observations")
    for table in [
        "edge_attribution_events",
        "edge_forward_outcomes",
        "edge_bbo_observations",
        "edge_opportunity_evidence",
    ]:
        op.drop_table(table)
