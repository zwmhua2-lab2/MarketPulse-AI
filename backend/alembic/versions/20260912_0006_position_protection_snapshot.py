"""persist durable position protection authority snapshot

Additive only: five nullable `positions` columns that carry the SL/TP protection authority of an
OPEN LONG, plus three CHECK constraints. The new columns let stop-loss / take-profit protection
outlive the originating TradePlan TTL: protection authority is read from the position row, while
the plan TTL stays the *risk-increasing* freshness authority (BUY / ADD / pending limit fill).

No existing G2/G3/G4/G5 table semantics, risk rules, execution rules or state machine semantics
are modified. Every existing `positions` row keeps working: the columns are NULL until a
risk-increasing fill writes them, or until the one-time legacy conversion below runs.

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

Legacy conversion (Candidate A, N01-7-F01-R1) ------------------------------------------------

The durable snapshot is the *sole* protection-lifetime authority, so a position that predates this
revision would otherwise be reported POSITION_UNPROTECTED even though a plan was protecting it.
This migration therefore performs the one-time deterministic conversion required by the approved
Candidate A compatibility matrix, and only for the states that have exactly one unambiguous
answer:

* CASE A -- existing FLAT position (`quantity <= 0`): left NULL, which is the legal state.
* CASE B -- existing OPEN position with exactly one identity-consistent, business-valid ACTIVE
  plan: the plan's SL/TP are copied onto the position row. For this conversion only the plan TTL
  is intentionally ignored (`expires_at` is not consulted), because a legacy plan is expected to
  be long expired and TTL is the risk-increasing freshness authority, never a protection-lifetime
  authority. This does **not** restore BUY / ADD authority: the plan row itself is untouched, so
  TTL + `state_version` keep gating every risk-increasing action exactly as before.
* CASE C -- existing OPEN position whose authority is missing, ambiguous or corrupt (no plan row,
  more than one ACTIVE plan, an identity mismatch between row and payload, non-finite or inverted
  levels): left NULL. The migration refuses to guess; the runtime then reports
  POSITION_UNPROTECTED, latches SAFE_MODE, refuses resume and cancels risk-increasing BUYs, while
  an explicit risk-reducing manual close stays available.

The conversion is a pure function of the row data (it copies `trade_plans.created_at` into
`protection_updated_at` instead of reading a clock), so a downgrade/upgrade cycle reproduces
identical values.
"""

from __future__ import annotations

import json
import math
from typing import Any

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

#: Legacy OPEN positions with no durable authority yet, joined to their candidate ACTIVE plan.
#: Ordered so the conversion result never depends on physical row order.
_LEGACY_CANDIDATES = sa.text(
    """
    SELECT p.position_id      AS position_id,
           p.run_mode         AS run_mode,
           p.instrument_id    AS instrument_id,
           tp.plan_id         AS plan_id,
           tp.plan_version    AS plan_version,
           tp.status          AS plan_status,
           tp.created_at      AS plan_created_at,
           tp.payload::text   AS payload
    FROM positions p
    JOIN trade_plans tp
      ON tp.run_mode = p.run_mode
     AND tp.instrument_id = p.instrument_id
     AND tp.status = 'ACTIVE'
    WHERE p.quantity > 0
      AND p.protection_plan_id IS NULL
    ORDER BY p.position_id, tp.plan_id
    """
)


def _legacy_authority(row: Any) -> tuple[str, int, float, float] | None:
    """Derive the durable authority of one legacy candidate, or None when it is not unambiguous.

    None is the CASE C answer and is never an exception: an authority the conversion cannot prove
    is left NULL, so the runtime reaches its normal POSITION_UNPROTECTED / SAFE_MODE verdict
    instead of the migration inventing a protection level.

    This mirrors the executable-plan contract (`marketpulse.g4.planning.plan_business_errors`)
    without importing application code, so a later application refactor can never change what an
    already-shipped migration did.
    """
    plan_version = row["plan_version"]
    if isinstance(plan_version, bool) or not isinstance(plan_version, int) or plan_version < 1:
        return None
    try:
        payload = json.loads(row["payload"])
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("plan_id") != row["plan_id"]
        or payload.get("run_mode") != row["run_mode"]
        or payload.get("instrument_id") != row["instrument_id"]
        or payload.get("plan_version") != plan_version
        or payload.get("status") != row["plan_status"]
    ):
        return None
    stop_loss, take_profit = payload.get("stop_loss"), payload.get("take_profit")
    for level in (stop_loss, take_profit):
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            return None
        if not math.isfinite(level):
            return None
    if not stop_loss < take_profit:
        return None
    return row["plan_id"], plan_version, float(stop_loss), float(take_profit)


def backfill_legacy_position_protection(connection: sa.Connection) -> dict[str, int]:
    """Convert every pre-existing OPEN position that has exactly one authoritative plan.

    Returns a deterministic tally used by the migration-cycle gate as evidence.
    """
    tally = {"legacy_open_positions": 0, "converted": 0, "not_authoritative": 0}
    candidates: dict[str, list[Any]] = {}
    for row in connection.execute(_LEGACY_CANDIDATES).mappings():
        candidates.setdefault(row["position_id"], []).append(row)
    tally["legacy_open_positions"] = len(candidates)
    for position_id in sorted(candidates):
        rows = candidates[position_id]
        # More than one ACTIVE plan for one symbol is ambiguous authority: CASE C, never a guess.
        authority = _legacy_authority(rows[0]) if len(rows) == 1 else None
        if authority is None:
            tally["not_authoritative"] += 1
            continue
        plan_id, plan_version, stop_loss, take_profit = authority
        connection.execute(
            sa.text(
                """
                UPDATE positions
                   SET protection_plan_id = :plan_id,
                       protection_plan_version = :plan_version,
                       protection_stop_loss = :stop_loss,
                       protection_take_profit = :take_profit,
                       protection_updated_at = :updated_at
                 WHERE position_id = :position_id
                   AND protection_plan_id IS NULL
                """
            ),
            {
                "plan_id": plan_id,
                "plan_version": plan_version,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "updated_at": rows[0]["plan_created_at"],
                "position_id": position_id,
            },
        )
        tally["converted"] += 1
    return tally


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
    # One-time legacy conversion (CASE A / B / C). Runs after the constraints exist so an illegal
    # authority can never be written, and before the application starts reading the new columns.
    backfill_legacy_position_protection(op.get_bind())


def downgrade() -> None:
    for name, _condition in PROTECTION_CHECKS:
        op.drop_constraint(name, "positions", type_="check")
    for column in reversed(PROTECTION_COLUMNS):
        op.drop_column("positions", column)
