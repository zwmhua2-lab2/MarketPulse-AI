"""create group 3 AI decision and paper trading core"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_0003"
down_revision: str | None = "20260904_0002"
branch_labels = None
depends_on = None


def _id(name: str) -> sa.Column:
    return sa.Column(name, sa.String(64), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "decision_snapshots",
        _id("snapshot_id"),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("config_version", sa.String(64), nullable=False),
        sa.Column("snapshot_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "ai_decisions",
        _id("decision_id"),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("config_version", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("raw_prompt", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "trade_plans",
        _id("plan_id"),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("decision_id", sa.String(64), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "trade_plan_scenarios",
        _id("scenario_id"),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
    )
    op.create_table(
        "execution_intents",
        _id("intent_id"),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_orders",
        _id("order_id"),
        sa.Column("intent_id", sa.String(64), nullable=False, unique=True),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("limit_price", sa.Float()),
        sa.Column("reserved_cash", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reserved_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "fills",
        _id("fill_id"),
        sa.Column("order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("intent_id", sa.String(64), nullable=False, unique=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("fee", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "positions",
        _id("position_id"),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("average_cost", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trade_id", sa.String(64)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_mode", "instrument_id", name="uq_positions_mode_instrument"),
    )
    op.create_table(
        "trades",
        _id("trade_id"),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "accounts",
        _id("account_id"),
        sa.Column("run_mode", sa.String(16), nullable=False, unique=True),
        sa.Column("cash_balance", sa.Float(), nullable=False),
        sa.Column("reserved_cash", sa.Float(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ledger_entries",
        _id("entry_id"),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("fill_id", sa.String(64), nullable=False, unique=True),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("cash_delta", sa.Float(), nullable=False),
        sa.Column("fee", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "outbox_records",
        _id("outbox_id"),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table, columns in {
        "decision_snapshots": ["instrument_id", "run_mode"],
        "ai_decisions": ["snapshot_id", "status"],
        "trade_plans": ["instrument_id", "decision_id", "status"],
        "execution_intents": ["plan_id", "instrument_id"],
        "paper_orders": ["intent_id", "instrument_id", "status"],
        "fills": ["intent_id"],
        "positions": ["run_mode", "instrument_id"],
        "accounts": ["run_mode"],
        "ledger_entries": ["account_id"],
        "outbox_records": ["aggregate_id", "event_type"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index(
        "uq_trade_plans_one_active",
        "trade_plans",
        ["run_mode", "instrument_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    for table in [
        "outbox_records",
        "ledger_entries",
        "accounts",
        "trades",
        "positions",
        "fills",
        "paper_orders",
        "execution_intents",
        "trade_plan_scenarios",
        "trade_plans",
        "ai_decisions",
        "decision_snapshots",
    ]:
        op.drop_table(table)
