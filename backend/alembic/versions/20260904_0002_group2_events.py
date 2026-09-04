"""create group 2 event and state persistence"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_0002"
down_revision: str | None = "20260904_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("market_events", sa.Column("event_id", sa.String(64), primary_key=True), sa.Column("symbol", sa.String(64), nullable=False), sa.Column("instrument_id", sa.String(64), nullable=False), sa.Column("market_type", sa.String(16), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("event_time", sa.DateTime(timezone=True), nullable=False), sa.Column("received_time", sa.DateTime(timezone=True), nullable=False), sa.Column("source", sa.String(128), nullable=False), sa.Column("strength", sa.Float(), nullable=False), sa.Column("priority", sa.Integer(), nullable=False), sa.Column("state_version", sa.Integer(), nullable=False), sa.Column("config_version", sa.String(64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("signal_timeline_events", sa.Column("timeline_id", sa.String(64), primary_key=True), sa.Column("event_id", sa.String(64), nullable=False), sa.Column("symbol", sa.String(64), nullable=False), sa.Column("instrument_id", sa.String(64), nullable=False), sa.Column("signal_type", sa.String(64), nullable=False), sa.Column("event_time", sa.DateTime(timezone=True), nullable=False), sa.Column("received_time", sa.DateTime(timezone=True), nullable=False), sa.Column("price", sa.Float()), sa.Column("context", sa.JSON(), nullable=False), sa.Column("strength", sa.Float(), nullable=False), sa.Column("lifecycle_action", sa.String(32), nullable=False), sa.Column("symbol_state", sa.String(32), nullable=False), sa.Column("state_version", sa.Integer(), nullable=False), sa.Column("config_version", sa.String(64), nullable=False), sa.Column("observed_reaction", sa.JSON()))
    op.create_table("symbol_states", sa.Column("instrument_id", sa.String(64), primary_key=True), sa.Column("symbol", sa.String(64), nullable=False), sa.Column("state", sa.String(32), nullable=False), sa.Column("state_version", sa.Integer(), nullable=False), sa.Column("last_event_time", sa.DateTime(timezone=True)), sa.Column("watch_expires_at", sa.DateTime(timezone=True)), sa.Column("cooldown_until", sa.DateTime(timezone=True)), sa.Column("structure_fingerprint", sa.String(128)))
    op.create_table("state_transitions", sa.Column("transition_id", sa.String(64), primary_key=True), sa.Column("instrument_id", sa.String(64), nullable=False), sa.Column("symbol", sa.String(64), nullable=False), sa.Column("from_state", sa.String(32), nullable=False), sa.Column("to_state", sa.String(32), nullable=False), sa.Column("event_id", sa.String(64), nullable=False), sa.Column("event_time", sa.DateTime(timezone=True), nullable=False), sa.Column("state_version", sa.Integer(), nullable=False), sa.Column("result", sa.String(64), nullable=False), sa.Column("reason", sa.String(128), nullable=False))
    op.create_table("strategy_candidates", sa.Column("candidate_id", sa.String(64), primary_key=True), sa.Column("strategy_id", sa.String(64), nullable=False), sa.Column("strategy_version", sa.String(64), nullable=False), sa.Column("applicable", sa.Boolean(), nullable=False), sa.Column("strength", sa.Float(), nullable=False), sa.Column("setup_type", sa.String(64), nullable=False), sa.Column("direction_bias", sa.String(32), nullable=False), sa.Column("entry_context", sa.JSON(), nullable=False), sa.Column("supporting_evidence", sa.JSON(), nullable=False), sa.Column("contradicting_evidence", sa.JSON(), nullable=False), sa.Column("invalidation_hint", sa.Text(), nullable=False), sa.Column("expected_behavior", sa.Text(), nullable=False), sa.Column("instrument_id", sa.String(64), nullable=False), sa.Column("symbol", sa.String(64), nullable=False), sa.Column("event_id", sa.String(64), nullable=False), sa.Column("state_version", sa.Integer(), nullable=False), sa.Column("config_version", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("derived_observations", sa.Column("observation_id", sa.String(64), primary_key=True), sa.Column("instrument_id", sa.String(64), nullable=False), sa.Column("event_time", sa.DateTime(timezone=True), nullable=False), sa.Column("config_version", sa.String(64), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    for table, columns in {"market_events": ["symbol", "instrument_id", "event_type", "event_time"], "signal_timeline_events": ["event_id", "symbol", "instrument_id", "event_time"], "state_transitions": ["instrument_id", "event_id"], "strategy_candidates": ["instrument_id", "event_id"], "derived_observations": ["instrument_id", "event_time"]}.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ["derived_observations", "strategy_candidates", "state_transitions", "symbol_states", "signal_timeline_events", "market_events"]:
        op.drop_table(table)
