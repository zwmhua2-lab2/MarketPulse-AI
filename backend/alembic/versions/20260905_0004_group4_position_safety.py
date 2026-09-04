"""create group 4 position safety, system control, incident and recovery facts"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_0004"
down_revision: str | None = "20260904_0003"
branch_labels = None
depends_on = None


def _id(name: str) -> sa.Column:
    return sa.Column(name, sa.String(64), primary_key=True)


def upgrade() -> None:
    op.add_column("trades", sa.Column("exit_reason", sa.String(32), nullable=True))

    op.create_table(
        "runtime_controls",
        sa.Column("run_mode", sa.String(16), primary_key=True),
        sa.Column("operator_state", sa.String(32), nullable=False),
        sa.Column("system_state", sa.String(32), nullable=False),
        sa.Column("runtime_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "symbol_controls",
        _id("control_id"),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_mode", "instrument_id", name="uq_symbol_controls_mode_instrument"),
    )
    op.create_table(
        "incidents",
        _id("incident_id"),
        sa.Column("incident_type", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "position_events",
        _id("event_id"),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("position_id", sa.String(64), nullable=True),
        sa.Column("plan_id", sa.String(64), nullable=True),
        sa.Column("order_id", sa.String(64), nullable=True),
        sa.Column("fill_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_mode", "dedupe_key", name="uq_position_events_dedupe"),
    )

    for table, columns in {
        "runtime_controls": ["system_state"],
        "symbol_controls": ["run_mode", "instrument_id"],
        "incidents": ["incident_type", "run_mode", "instrument_id", "status"],
        "position_events": ["run_mode", "instrument_id", "plan_id", "event_type"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ["position_events", "incidents", "symbol_controls", "runtime_controls"]:
        op.drop_table(table)
    op.drop_column("trades", "exit_reason")
