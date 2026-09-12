from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    AccountRecord,
    PaperOrderRecord,
    PositionRecord,
    RuntimeControlRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import OrderSide, OrderStatus, PlanStatus, RunMode
from marketpulse.g3.protection_snapshot import read_position_protection
from marketpulse.g3.service import PaperExecutionService

from .models import OperatorState, ReconciliationReport, SystemState
from .planning import load_active_plan, load_valid_long_active_plan, plan_business_errors

TOLERANCE = 1e-8


async def reconcile(
    run_mode: RunMode,
    *,
    sessions: async_sessionmaker[AsyncSession],
    execution: PaperExecutionService,
    now: datetime | None = None,
    clock: Clock | None = None,
) -> ReconciliationReport:
    """Detector only. Never repairs ledger, position, cash or reservation."""
    clock = clock or SystemClock()
    now = now or clock.now()
    async with sessions() as session, session.begin():
        # PostgreSQL READ COMMITTED would give each SELECT a new snapshot.  This report spans
        # G3 accounting and G4 safety facts, so hold one read-only snapshot for all of them.
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        base = await execution.reconciliation(run_mode, session=session)

        plans = list(
            (
                await session.scalars(
                    select(TradePlanRecord).where(TradePlanRecord.run_mode == run_mode)
                )
            ).all()
        )
        orders = list(
            (
                await session.scalars(
                    select(PaperOrderRecord).where(PaperOrderRecord.run_mode == run_mode)
                )
            ).all()
        )
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord).where(PositionRecord.run_mode == run_mode)
                )
            ).all()
        )
        trades = list(
            (
                await session.scalars(
                    select(TradeRecord).where(TradeRecord.run_mode == run_mode)
                )
            ).all()
        )
        accounts = list(
            (
                await session.scalars(
                    select(AccountRecord).where(AccountRecord.run_mode == run_mode)
                )
            ).all()
        )
        control = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == run_mode)
        )

        # 13. An OPEN LONG must not lose protection merely because its planning window closed.
        # When the symbol's ACTIVE plan is expired but otherwise valid, the position's durable
        # snapshot is the protection authority; a missing snapshot means it is silently
        # unprotected, which is exactly the state this invariant exists to surface. These reads
        # stay inside this single REPEATABLE READ snapshot so the G3 facts and this G4 invariant
        # observe one consistent view (and share this session, which the surrounding context
        # closes exactly once).
        ttl_unprotected: list[dict[str, Any]] = []
        for position in sorted(positions, key=lambda p: p.instrument_id):
            if position.quantity <= TOLERANCE:
                continue
            if (
                await load_valid_long_active_plan(
                    session, run_mode, position.instrument_id, now=now
                )
                is not None
            ):
                continue
            expired = await load_active_plan(session, run_mode, position.instrument_id)
            if expired is None or expired.expires_at > now or plan_business_errors(expired):
                continue
            if read_position_protection(position) is None:
                ttl_unprotected.append(
                    {
                        "instrument_id": position.instrument_id,
                        "plan_id": expired.plan_id,
                        "reason": "NO_SNAPSHOT",
                    }
                )
    diagnostics: list[str] = list(base.get("diagnostics", []))
    invariants: dict[str, bool] = {
        key: bool(base[key])
        for key in (
            "reserved_cash_matches_open_buys",
            "sell_reservations_within_positions",
            "position_quantities_match_fills",
            "available_cash_non_negative",
            "fills_have_one_ledger_entry",
            "filled_orders_match_fills",
        )
    }
    details: dict[str, Any] = {"g3": base}

    # 7. Active plan uniqueness (per instrument).
    active_by_instrument: dict[str, int] = {}
    for plan in plans:
        if plan.status == PlanStatus.ACTIVE:
            active_by_instrument[plan.instrument_id] = (
                active_by_instrument.get(plan.instrument_id, 0) + 1
            )
    duplicate_active = sorted(
        instrument for instrument, count in active_by_instrument.items() if count > 1
    )
    invariants["active_plan_unique"] = not duplicate_active
    if duplicate_active:
        diagnostics.append(f"active_plan_not_unique:{','.join(duplicate_active)}")
    details["active_plans"] = active_by_instrument

    # 8. Every OPEN order must reference a valid, non-expired ACTIVE plan.
    plans_by_id = {plan.plan_id: plan for plan in plans}
    open_orders = [order for order in orders if order.status == OrderStatus.OPEN]
    invalid_open_orders: list[dict[str, Any]] = []
    for order in open_orders:
        plan = plans_by_id.get(order.plan_id)
        if plan is None:
            invalid_open_orders.append({"order_id": order.order_id, "reason": "PLAN_MISSING"})
        elif plan.status != PlanStatus.ACTIVE:
            invalid_open_orders.append(
                {"order_id": order.order_id, "reason": f"PLAN_{plan.status}"}
            )
        elif now >= plan.expires_at:
            invalid_open_orders.append({"order_id": order.order_id, "reason": "PLAN_EXPIRED"})
        elif plan.instrument_id != order.instrument_id or plan.run_mode != order.run_mode:
            invalid_open_orders.append({"order_id": order.order_id, "reason": "PLAN_SCOPE_MISMATCH"})
    invariants["open_order_plan_valid"] = not invalid_open_orders
    if invalid_open_orders:
        diagnostics.append("open_order_plan_invalid")
    details["invalid_open_orders"] = invalid_open_orders

    control_snapshot = {
        "operator_state": control.operator_state if control else None,
        "system_state": control.system_state if control else None,
    }
    # 9. EMERGENCY_STOP must leave no risk-increasing OPEN BUY.
    open_buys = [order for order in open_orders if order.side == OrderSide.BUY]
    emergency_open_buys: list[str] = []
    if control is not None and control.operator_state == OperatorState.EMERGENCY_STOP:
        emergency_open_buys = [order.order_id for order in open_buys]
    invariants["emergency_no_risk_increasing_open_buy"] = not emergency_open_buys
    if emergency_open_buys:
        diagnostics.append("emergency_stop_open_buy_present")
    details["emergency_open_buy_order_ids"] = emergency_open_buys

    # 10. A closed position / closed lifecycle must not retain a stale risk-increasing BUY or an
    # unbacked sell intent.
    positions_by_instrument = {position.instrument_id: position for position in positions}
    open_trade_instruments = {
        trade.instrument_id for trade in trades if trade.status != "CLOSED"
    }
    closed_trade_instruments = {
        trade.instrument_id for trade in trades if trade.status == "CLOSED"
    }
    closed_lifecycle_instruments = closed_trade_instruments - open_trade_instruments
    stale_closed_intents: list[dict[str, Any]] = []
    for order in open_orders:
        position = positions_by_instrument.get(order.instrument_id)
        quantity = position.quantity if position else 0.0
        if order.side == OrderSide.SELL and quantity <= TOLERANCE:
            stale_closed_intents.append({"order_id": order.order_id, "reason": "SELL_WITHOUT_POSITION"})
        elif (
            order.side == OrderSide.BUY
            and quantity <= TOLERANCE
            and order.instrument_id in closed_lifecycle_instruments
        ):
            stale_closed_intents.append(
                {"order_id": order.order_id, "reason": "BUY_AFTER_CLOSED_LIFECYCLE"}
            )
    invariants["closed_position_no_stale_intent"] = not stale_closed_intents
    if stale_closed_intents:
        diagnostics.append("closed_position_stale_intent")
    details["closed_position_stale_intents"] = stale_closed_intents

    # 11. No impossible account / position state.
    impossible_states: list[str] = []
    for account in accounts:
        if account.cash_balance < -TOLERANCE:
            impossible_states.append("negative_cash_balance")
        if account.reserved_cash < -TOLERANCE:
            impossible_states.append("negative_reserved_cash")
    for position in positions:
        if position.quantity < -TOLERANCE:
            impossible_states.append(f"negative_position_quantity:{position.instrument_id}")
        if position.average_cost < -TOLERANCE:
            impossible_states.append(f"negative_average_cost:{position.instrument_id}")
    invariants["account_position_state_valid"] = not impossible_states
    if impossible_states:
        diagnostics.append("account_position_impossible_state")
    details["impossible_states"] = impossible_states

    # 12. Runtime control must be internally consistent.
    control_issues: list[str] = []
    if control is not None:
        try:
            operator = OperatorState(control.operator_state)
        except ValueError:
            operator = None
            control_issues.append("unknown_operator_state")
        try:
            system = SystemState(control.system_state)
        except ValueError:
            system = None
            control_issues.append("unknown_system_state")
        if operator is OperatorState.EMERGENCY_STOP and system is not SystemState.EMERGENCY_STOP:
            control_issues.append("emergency_operator_without_emergency_system_state")
        if operator is OperatorState.PAUSED and system not in (
            SystemState.PAUSED,
            SystemState.DATA_DEGRADED,
            SystemState.SAFE_MODE,
        ):
            control_issues.append("paused_operator_with_running_system_state")
    invariants["runtime_control_consistent"] = not control_issues
    if control_issues:
        diagnostics.append("runtime_control_inconsistent")
    details["runtime_control"] = {**control_snapshot, "issues": control_issues}

    # 13 (report merge). The durable-snapshot reads above already ran inside the single
    # REPEATABLE READ snapshot; here the result only folds into the report.
    invariants["open_position_protection_survives_plan_ttl"] = not ttl_unprotected
    if ttl_unprotected:
        diagnostics.append("open_position_unprotected_after_plan_ttl")
    details["ttl_unprotected_positions"] = ttl_unprotected

    details["open_orders"] = len(open_orders)
    details["open_buys"] = len(open_buys)
    details["positions"] = len(positions)
    details["trades"] = len(trades)

    return ReconciliationReport(
        ok=not diagnostics,
        diagnostics=diagnostics,
        invariants=invariants,
        details=details,
    )


async def count_open_buys(
    sessions: async_sessionmaker[AsyncSession], run_mode: RunMode
) -> int:
    async with sessions() as session:
        value = await session.scalar(
            select(func.count())
            .select_from(PaperOrderRecord)
            .where(
                PaperOrderRecord.run_mode == run_mode,
                PaperOrderRecord.side == OrderSide.BUY,
                PaperOrderRecord.status == OrderStatus.OPEN,
            )
        )
    return int(value or 0)
