"""Durable OPEN-position protection authority: the shared write/read contract.

An OPEN LONG keeps its stop-loss / take-profit authority independently of the originating
TradePlan TTL. The authority is persisted on the position row by G3 settlement (see
`marketpulse.g3.service.PaperExecutionService._settle_order`) and read back through the single
shared resolver `marketpulse.g4.planning.resolve_open_position_protection`, whose callers are:

* `g4.protection.evaluate` / `_close_position_in` -- the SL/TP trigger authority;
* `g4.control._open_position_protection_gate` -- the resume / safe-mode-recovery gate;
* `g4.recovery` -- transitively, through its `RESTORE_POSITION_PROTECTION` protection restore;
* `g4.reconciliation` -- invariant #13, which surfaces an OPEN LONG whose snapshot is missing.

`g4.reevaluation` deliberately does not read it and needs no change: its `POSITION_UNPROTECTED`
branch fires only when `load_active_plan` finds no ACTIVE plan at all, and
`resolve_open_position_protection` returns `None` for exactly that state (the TTL carve-out below
requires an ACTIVE plan that is merely expired). Both layers therefore already agree.

Placement note: this module holds the write side, and the write happens inside G3's economic
transaction, so it lives with G3. The dependency direction in this codebase is strictly
`g4 -> g3` (`marketpulse.g4.__init__` imports `g4.reconciliation`, which imports
`marketpulse.g3.service`), so a shared helper imported *by* G3 cannot live under `g4` without
creating a real import cycle.

Two distinct concepts must never be merged again:

* plan *risk-increasing* validity -- TTL + `state_version` + plan business validity. It gates
  BUY / ADD / pending risk-increasing limit fills and recovery order revalidation. That contract
  stays in `marketpulse.g4.planning.load_valid_long_active_plan`.
* position *protection lifetime* -- the durable snapshot read by this module. It has no TTL, no
  `state_version` and no AI dependency, because a stop-loss that expires with a planning artifact
  would silently leave a real position unprotected.
"""

from __future__ import annotations

from datetime import datetime

from marketpulse.db.models import PositionRecord

from .models import PositionProtectionAuthority, TradePlan


def authority_from_plan(plan: TradePlan) -> PositionProtectionAuthority | None:
    """Derive the durable protection authority of an executable plan, or None if it cannot.

    None is the fail-closed answer, never an exception: G3 settlement must not gain a new failure
    mode because of an additive snapshot write. A plan whose levels cannot form a legal authority
    is a plan `marketpulse.g4.planning.plan_business_errors` would also reject, so the position
    opens with a NULL snapshot and G4 arrives at exactly the POSITION_UNPROTECTED / safe-state
    verdict it already reaches today for that plan. No position changes protection status.
    """
    try:
        return PositionProtectionAuthority(
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
            stop_loss=plan.stop_loss,
            take_profit=plan.take_profit,
        )
    except (TypeError, ValueError):  # an unusable plan yields no authority, it never raises
        return None


def read_position_protection(position: PositionRecord) -> PositionProtectionAuthority | None:
    """Return the durable protection authority of a position, or None (caller fails closed).

    Reads only facts persisted on the position row, so it deliberately depends on none of:

    * the originating TradePlan TTL (`expires_at`) -- the plan is only the authority *source*;
    * `SymbolStateStore.state_version` -- that is the risk-increasing freshness authority;
    * AI / provider availability, wall clock or restart time.

    A legal OPEN LONG therefore keeps its stop-loss / take-profit authority after the plan TTL
    expires, after a state_version advance, after a restart and while the AI is unavailable.
    A missing or corrupt snapshot returns None: the caller must treat the position as
    POSITION_UNPROTECTED and allow only risk-reducing exits.
    """
    plan_id = position.protection_plan_id
    plan_version = position.protection_plan_version
    stop_loss = position.protection_stop_loss
    take_profit = position.protection_take_profit
    if (
        plan_id is None
        or plan_version is None
        or stop_loss is None
        or take_profit is None
        or position.protection_updated_at is None
    ):
        return None
    try:
        return PositionProtectionAuthority(
            plan_id=plan_id,
            plan_version=plan_version,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
        )
    except (TypeError, ValueError):  # corrupt durable protection must fail closed, never guess
        return None


def apply_position_protection(
    position: PositionRecord,
    authority: PositionProtectionAuthority,
    *,
    now: datetime,
) -> None:
    """Write the protection authority onto the position row. The caller owns the transaction."""
    position.protection_plan_id = authority.plan_id
    position.protection_plan_version = authority.plan_version
    position.protection_stop_loss = authority.stop_loss
    position.protection_take_profit = authority.take_profit
    position.protection_updated_at = now


def clear_position_protection(position: PositionRecord) -> None:
    """Clear the protection authority. Only a full close may do this."""
    position.protection_plan_id = None
    position.protection_plan_version = None
    position.protection_stop_loss = None
    position.protection_take_profit = None
    position.protection_updated_at = None
