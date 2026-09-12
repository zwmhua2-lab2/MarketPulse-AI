"""persist durable position protection authority snapshot

Additive only: five nullable `positions` columns that carry the SL/TP protection authority of an
OPEN LONG, plus three CHECK constraints. The new columns let stop-loss / take-profit protection
outlive the originating TradePlan TTL: protection authority is read from the position row, while
the plan TTL stays the *risk-increasing* freshness authority (BUY / ADD / pending limit fill).

No existing G2/G3/G4/G5 table semantics, risk rules, execution rules or state machine semantics
are modified. Every existing `positions` row keeps working: the columns are NULL until a
risk-increasing fill writes them.

Contract enforced here (name / meaning):

* `ck_positions_protection_complete` -- the five columns are all NULL or all NOT NULL, so a
  half-written protection authority can never exist;
* `ck_positions_protection_version_positive` -- `protection_plan_version >= 1`;
* `ck_positions_protection_prices` -- both levels are finite and `stop_loss < take_profit`.

The level rule is deliberately the *exact* executable-plan contract
(`marketpulse.g4.planning.plan_business_errors` / `marketpulse.g4.models.ProtectionContext`) and
adds nothing stricter. A stricter rule here (for example positivity) would let a plan G4 accepts
produce a position G4 then calls POSITION_UNPROTECTED, silently switching protection off between
two layers that must agree; aligning keeps every existing position's protection status unchanged.

PostgreSQL does not expose `isfinite(double precision)` on every target version, so finiteness is
expressed with the two infinities: `x < 'Infinity'::float8` rejects NaN and +Infinity together
(PostgreSQL orders NaN above every value) and `x > '-Infinity'::float8` rejects -Infinity.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0006"
down_revision: str | None = "20260911_0005"
branch_labels = None
depends_on = None

PROTECTION_COLUMNS = (
    "protection_plan_id",
    "protection_plan_version",
    "protection_stop_loss",
    "protection_take_profit",
    "protection_updated_at",
)

PROTECTION_CHECKS = (
    (
        "ck_positions_protection_complete",
        (
            "(protection_plan_id IS NULL AND protection_plan_version IS NULL "
            "AND protection_stop_loss IS NULL AND protection_take_profit IS NULL "
            "AND protection_updated_at IS NULL) "
            "OR (protection_plan_id IS NOT NULL AND protection_plan_version IS NOT NULL "
            "AND protection_stop_loss IS NOT NULL AND protection_take_profit IS NOT NULL "
            "AND protection_updated_at IS NOT NULL)"
        ),
    ),
    (
        "ck_positions_protection_version_positive",
        "protection_plan_version IS NULL OR protection_plan_version >= 1",
    ),
    (
        "ck_positions_protection_prices",
        (
            "protection_stop_loss IS NULL OR (protection_stop_loss > '-Infinity'::float8 "
            "AND protection_stop_loss < 'Infinity'::float8 "
            "AND protection_take_profit > '-Infinity'::float8 "
            "AND protection_take_profit < 'Infinity'::float8 "
            "AND protection_stop_loss < protection_take_profit)"
        ),
    ),
)


def upgrade() -> None:
    op.add_column("positions", sa.Column("protection_plan_id", sa.String(64), nullable=True))
    op.add_column("positions", sa.Column("protection_plan_version", sa.Integer(), nullable=True))
    op.add_column("positions", sa.Column("protection_stop_loss", sa.Float(), nullable=True))
    op.add_column("positions", sa.Column("protection_take_profit", sa.Float(), nullable=True))
    op.add_column(
        "positions", sa.Column("protection_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    for name, condition in PROTECTION_CHECKS:
        op.create_check_constraint(name, "positions", condition)


def downgrade() -> None:
    for name, _condition in PROTECTION_CHECKS:
        op.drop_constraint(name, "positions", type_="check")
    for column in reversed(PROTECTION_COLUMNS):
        op.drop_column("positions", column)
