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

Legacy conversion (Candidate A, N01-7-F01-R1; authority proof closed by N01-7-F01-R2) --------

The durable snapshot is the *sole* protection-lifetime authority, so a position that predates this
revision would otherwise be reported POSITION_UNPROTECTED even though a plan was protecting it.
This migration therefore performs the one-time deterministic conversion required by the approved
Candidate A compatibility matrix, and only for the states that have exactly one unambiguous
answer:

* CASE A -- existing FLAT position (`quantity <= 0`): left NULL, which is the legal state.
* CASE B -- existing OPEN position with exactly one *fully authoritative* ACTIVE plan: the plan's
  SL/TP are copied onto the position row, together with the plan's `created_at` as the deterministic
  `protection_updated_at`.
* CASE C -- existing OPEN position whose authority is missing, ambiguous or corrupt (no plan row,
  more than one ACTIVE plan, an identity mismatch between row and payload, an incomplete payload,
  non-finite or inverted levels): left NULL. The migration refuses to guess; the runtime then
  reports POSITION_UNPROTECTED, latches SAFE_MODE, refuses resume and cancels risk-increasing
  BUYs, while an explicit risk-reducing manual close stays available.

"Fully authoritative" is the same bar the accepted pre-migration runtime applies in
`marketpulse.g4.planning.load_active_plan()`, and it is deliberately never *looser* than that bar:
this conversion promotes a plan's levels from "a plan row that merely exists" to a durable
protection authority, so a plan the runtime would have refused must be refused here too. There
must never be a state where the runtime says invalid but the migration says authoritative. The
proof therefore has three parts, all of them frozen inside this file (a shipped migration must not
change meaning when application code later moves):

1. the payload parses as a JSON object and matches the frozen `TradePlan` authority shape: every
   field the model requires without a default is present with the right JSON type, and every
   optional field that *is* present has the right type;
2. every one of `plan_id`, `snapshot_id`, `decision_id`, `instrument_id`, `symbol`, `run_mode`,
   `state_version`, `plan_version`, `status`, `created_at` and `expires_at` agrees between the
   `trade_plans` row and its serialized payload -- the exact identity list `load_active_plan()`
   compares before it trusts a durable plan;
3. the protection contract is business-valid: finite levels, `stop_loss < take_profit`, and a
   finite ordered `entry_zone` (`marketpulse.g4.planning.plan_business_errors`).

(R1 proved only part of (1) and a subset of (2) -- `plan_id`, `run_mode`, `instrument_id`,
`plan_version`, `status` -- so a payload that disagreed on `snapshot_id`, `decision_id`, `symbol`,
`state_version`, `created_at` or `expires_at` could still be backfilled even though the runtime
rejected it. N01-7-F01-R2 closes that gap; the finding is N01-7-F01-R1-R01.)

The one deliberate difference from the runtime is the TTL: `now < expires_at` is *not* consulted,
because a legacy plan is expected to be long expired and TTL is the risk-increasing freshness
authority, never a protection-lifetime authority. Ignoring the TTL means "do not compare `now`
with `expires_at`"; it never means "do not compare `expires_at` with its row", which is part (2)
above. Nothing here restores BUY / ADD / pending risk-increasing authority either: the plan row
itself is untouched, so TTL + `state_version` keep gating every risk-increasing action exactly as
before.

The conversion is a pure function of the row data (it copies `trade_plans.created_at` into
`protection_updated_at` instead of reading a clock), so a downgrade/upgrade cycle reproduces
identical values.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
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
           tp.snapshot_id     AS snapshot_id,
           tp.decision_id     AS decision_id,
           tp.symbol          AS symbol,
           tp.state_version   AS state_version,
           tp.plan_version    AS plan_version,
           tp.status          AS status,
           tp.created_at      AS created_at,
           tp.expires_at      AS expires_at,
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

#: Row columns that must agree with the identically named serialized payload key. This is exactly
#: the list `marketpulse.g4.planning.load_active_plan()` compares before it trusts a durable plan;
#: a plan it would have refused must never be promoted to durable protection authority.
_LEGACY_IDENTITY_FIELDS = (
    "plan_id",
    "snapshot_id",
    "decision_id",
    "instrument_id",
    "symbol",
    "run_mode",
    "state_version",
    "plan_version",
    "status",
)

#: Serialized instants, compared as parsed instants (never as raw text) and never against a clock.
_LEGACY_INSTANT_FIELDS = ("created_at", "expires_at")

#: Enum member sets the runtime's `TradePlan.model_validate` accepts; anything else fails closed.
_LEGACY_RUN_MODES = frozenset({"LIVE_PAPER", "REPLAY", "TEST"})
_LEGACY_PLAN_STATUSES = frozenset(
    {"ACTIVE", "EXPIRED", "CANCELLED", "REPLACED", "CAPACITY_BLOCKED"}
)

#: Optional `TradePlan` fields with a default: absent is legal, present must still be a valid member.
_LEGACY_OPTIONAL_ENUMS = {
    "order_type": frozenset({"MARKET", "LIMIT"}),
    "side": frozenset({"BUY", "SELL"}),
}


def _legacy_number(value: Any) -> bool:
    """JSON number, excluding `bool` (a Python `bool` is an `int`) and every non-finite value."""
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _legacy_integer(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def _legacy_instant(value: Any) -> datetime | None:
    """Parse the timezone-aware ISO-8601 instant a serialized `TradePlan` carries.

    A naive or unparsable value is not a serialized `TradePlan`, so it is rejected rather than
    guessed at: comparing a naive instant with a `timestamptz` column would be meaningless anyway.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _legacy_identity_mismatch(row: Any, payload: dict[str, Any]) -> bool:
    """True when the payload disagrees with its own row on any authoritative identity field."""
    for field in _LEGACY_IDENTITY_FIELDS:
        value = payload.get(field)
        if field == "plan_version":
            if not _legacy_integer(value) or value < 1 or value != row["plan_version"]:
                return True
        elif field == "state_version":
            if not _legacy_integer(value) or value != row["state_version"]:
                return True
        elif field in ("run_mode", "status"):
            # `isinstance` first: an unhashable payload value must fail closed, not raise.
            allowed = _LEGACY_RUN_MODES if field == "run_mode" else _LEGACY_PLAN_STATUSES
            if not isinstance(value, str) or value not in allowed or value != row[field]:
                return True
        elif not isinstance(value, str) or value != row[field]:
            return True
    for field in _LEGACY_INSTANT_FIELDS:
        # Identity only: the TTL exception below is about `now`, never about this comparison.
        if _legacy_instant(payload.get(field)) != row[field]:
            return True
    return False


def _legacy_shape_invalid(payload: dict[str, Any]) -> bool:
    """True when the payload is not a frozen `TradePlan` authority shape.

    Mirrors `TradePlan.model_validate` (which `load_active_plan()` runs and which fails closed) plus
    `plan_business_errors`, so a pseudo-plan that merely carries `plan_id` / `stop_loss` /
    `take_profit` can never be mistaken for an authoritative TradePlan.
    """
    entry_zone = payload.get("entry_zone")
    if not isinstance(entry_zone, dict):
        return True
    lower, upper = entry_zone.get("lower"), entry_zone.get("upper")
    if not _legacy_number(lower) or not _legacy_number(upper) or lower > upper:
        return True
    stop_loss, take_profit = payload.get("stop_loss"), payload.get("take_profit")
    if not _legacy_number(stop_loss) or not _legacy_number(take_profit):
        return True
    if not stop_loss < take_profit:
        return True
    if not _legacy_number(payload.get("intended_notional")):
        return True
    for field, allowed in _LEGACY_OPTIONAL_ENUMS.items():
        # `isinstance` first: an unhashable payload value must fail closed, not raise.
        if field in payload and (
            not isinstance(payload[field], str) or payload[field] not in allowed
        ):
            return True
    if "invalidation" in payload and not (
        payload["invalidation"] is None or isinstance(payload["invalidation"], str)
    ):
        return True
    if "probe" in payload and not isinstance(payload["probe"], bool):
        return True
    scenarios = payload.get("backup_scenarios")
    return "backup_scenarios" in payload and not (
        isinstance(scenarios, list) and all(isinstance(item, str) for item in scenarios)
    )


def _legacy_authority(row: Any) -> tuple[str, int, float, float] | None:
    """Derive the durable authority of one legacy candidate, or None when it is not unambiguous.

    None is the CASE C answer and is never an exception: an authority the conversion cannot prove
    is left NULL, so the runtime reaches its normal POSITION_UNPROTECTED / SAFE_MODE verdict
    instead of the migration inventing a protection level.

    Three independent proofs are required, and each one is frozen in this file rather than imported
    from application code, so a later application refactor can never change what an already-shipped
    migration did -- and so the migration can never accept a plan the runtime would have refused:

      1. the payload is a JSON object matching the frozen `TradePlan` authority shape;
      2. it agrees with its `trade_plans` row on every authoritative identity field, including both
         serialized instants;
      3. its protection contract is business-valid.

    The TTL (`now < expires_at`) is deliberately not consulted; see the module docstring.
    """
    try:
        payload = json.loads(row["payload"])
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if _legacy_identity_mismatch(row, payload):
        return None
    if _legacy_shape_invalid(payload):
        return None
    return (
        row["plan_id"],
        row["plan_version"],
        float(payload["stop_loss"]),
        float(payload["take_profit"]),
    )


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
                "updated_at": rows[0]["created_at"],
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
