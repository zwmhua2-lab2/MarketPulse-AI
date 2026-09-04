from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    AccountRecord,
    PaperOrderRecord,
    PositionRecord,
    RuntimeControlRecord,
    SymbolStateStore,
    TradePlanRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    DataQuality,
    OrderSide,
    OrderStatus,
    PlanStatus,
    RunMode,
)
from marketpulse.g3.service import PaperExecutionService
from marketpulse.runtime import HealthRegistry

from .incidents import IncidentManager
from .models import (
    HealthComponent,
    HealthStatus,
    IncidentType,
    OperatorState,
    ProtectionOutcome,
    ReconciliationReport,
    RecoveryReport,
    SystemState,
)
from .protection import PositionProtectionService
from .state import SystemStateService

BboFor = Callable[[str], Awaitable[BestBidAsk]]
ReconcileFn = Callable[[RunMode], Awaitable[ReconciliationReport]]


class RecoveryManager:
    """Rebuild every runtime fact from PostgreSQL only. Never from memory, never by guessing."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        state_service: SystemStateService,
        incidents: IncidentManager,
        health: HealthRegistry,
        protection: PositionProtectionService,
        execution: PaperExecutionService,
        reconcile: ReconcileFn,
        *,
        clock: Clock | None = None,
        gap_threshold: timedelta = timedelta(seconds=10),
    ) -> None:
        self.sessions = sessions
        self.state_service = state_service
        self.incidents = incidents
        self.health = health
        self.protection = protection
        self.execution = execution
        self.reconcile = reconcile
        self.clock = clock or SystemClock()
        self.gap_threshold = gap_threshold

    async def recover(
        self,
        run_mode: RunMode,
        *,
        bbo_for: BboFor,
        now: datetime | None = None,
    ) -> RecoveryReport:
        now = now or self.clock.now()
        report = RecoveryReport(
            run_mode=run_mode, ok=False, started_at=now, operator_state=OperatorState.NORMAL
        )
        # Capture the last-known heartbeat BEFORE any transition overwrites it: it is the only
        # evidence we have for how long the process was down. Also latch the pre-restart system
        # state: STARTING/RECOVERING must never erase a persisted SAFE_MODE / PAUSED / EMERGENCY.
        async with self.sessions() as session:
            pre = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == run_mode)
            )
        last_heartbeat = pre.heartbeat_at if pre is not None else None
        pre_system_state = pre.system_state if pre is not None else SystemState.STARTING.value
        await self.state_service.transition(
            run_mode, system_state=SystemState.STARTING, reason="recovery_start", emit_outbox=False
        )
        report.steps.append("STARTING")
        await self.state_service.transition(
            run_mode, system_state=SystemState.RECOVERING, reason="recovering", emit_outbox=False
        )
        report.steps.append("RECOVERING")

        async with self.sessions() as session:
            control = await self.state_service.load(run_mode, session=session)
            report.operator_state = OperatorState(control.operator_state)
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == run_mode)
            )
            if account is None:
                report.steps.append("ACCOUNT_MISSING")
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
            plans = list(
                (
                    await session.scalars(
                        select(TradePlanRecord).where(TradePlanRecord.run_mode == run_mode)
                    )
                ).all()
            )
            symbol_states = list(
                (await session.scalars(select(SymbolStateStore))).all()
            )
            report.steps += ["LOAD_RUNTIME_CONTROL", "LOAD_ACCOUNT", "LOAD_OPEN_ORDERS"]
            report.steps += ["LOAD_POSITIONS", "LOAD_ACTIVE_PLANS", "LOAD_SYMBOL_STATES"]

        active_symbols = sorted(
            {order.instrument_id for order in orders if order.status == OrderStatus.OPEN}
            | {position.instrument_id for position in positions if position.quantity > 0}
            | {plan.instrument_id for plan in plans if plan.status == PlanStatus.ACTIVE}
        )
        report.active_symbols = active_symbols
        report.steps.append("FIND_ACTIVE_SYMBOLS")

        # Fresh market data for every active symbol.
        quotes: dict[str, BestBidAsk] = {}
        fresh_all = True
        for instrument_id in active_symbols:
            try:
                quote = await bbo_for(instrument_id)
                quotes[instrument_id] = quote
                if (
                    quote.tradable
                    and quote.data_quality is DataQuality.FRESH
                    and (now - quote.received_at.astimezone()).total_seconds() <= 5.0
                ):
                    continue
            except Exception as exc:  # noqa: BLE001 - a provider failure must degrade, never crash
                self.health.set(
                    HealthComponent.CORE_MARKET_DATA.value,
                    HealthStatus.UNAVAILABLE.value,
                    instrument_id=instrument_id,
                    error=type(exc).__name__,
                )
                fresh_all = False
                continue
            fresh_all = False
            self.health.set(
                HealthComponent.CORE_MARKET_DATA.value,
                HealthStatus.UNAVAILABLE.value,
                instrument_id=instrument_id,
            )
        if not active_symbols:
            fresh_all = True
        if fresh_all and active_symbols:
            self.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.HEALTHY.value)
        report.steps.append("FETCH_FRESH_MARKET_DATA")

        # Execution gap: downtime with active risk facts is an audit fact, never a source of fills.
        if last_heartbeat is not None and (now - last_heartbeat) > self.gap_threshold:
            if any(
                position.quantity > 0 for position in positions
            ) or any(order.status == OrderStatus.OPEN for order in orders):
                report.execution_gap = {
                    "last_heartbeat": last_heartbeat.isoformat(),
                    "recovery_time": now.isoformat(),
                    "downtime_seconds": (now - last_heartbeat).total_seconds(),
                    "affected_instruments": active_symbols,
                    "active_risk": {
                        "open_positions": [p.instrument_id for p in positions if p.quantity > 0],
                        "open_orders": [o.order_id for o in orders if o.status == OrderStatus.OPEN],
                    },
                }
                await self.incidents.open(
                    incident_type=IncidentType.EXECUTION_GAP,
                    run_mode=run_mode,
                    reason="downtime_with_active_risk",
                    payload=report.execution_gap,
                )
                report.steps.append("EXECUTION_GAP_RECORDED")
        else:
            report.execution_gap = None

        # Reconciliation is a detector, never a repair engine.
        reconciliation = await self.reconcile(run_mode)
        report.reconciliation = reconciliation
        report.steps.append("RECONCILIATION")

        # Revalidate plans / orders and cancel any stale risk-increasing intent.
        plan_revalidation, order_revalidation = await self._revalidate(
            run_mode, orders, plans, symbol_states, quotes, now
        )
        report.plan_revalidation = plan_revalidation
        report.order_revalidation = order_revalidation
        report.steps.append("REVALIDATE_PLANS_ORDERS")

        # Restore protection and immediately evaluate SL/TP against the restored BBO.
        for position in positions:
            if position.quantity <= 0:
                continue
            instrument_id = position.instrument_id
            quote = quotes.get(instrument_id)
            if quote is None:
                continue
            outcome: ProtectionOutcome = await self.protection.evaluate(
                run_mode, instrument_id, quote, now=now
            )
            report.protection.append(outcome)
        report.steps.append("RESTORE_POSITION_PROTECTION")

        # Decide the final effective state. Operator intent, the persisted SAFE_MODE latch, and
        # unresolved blocking incidents all win over a silent promotion to RUNNING.
        blocking_incidents = await self.incidents.blocking(run_mode)
        final_state = await self._final_state(
            control.operator_state,
            pre_system_state,
            reconciliation.ok,
            fresh_all,
            bool(blocking_incidents),
        )
        report.final_system_state = final_state
        if not reconciliation.ok:
            await self.incidents.open(
                incident_type=IncidentType.ACCOUNT_INTEGRITY_ERROR,
                run_mode=run_mode,
                reason="reconciliation_failed_on_recovery",
                payload={"diagnostics": reconciliation.diagnostics},
            )
            report.steps.append("SAFE_MODE_LATCHED")
        # Runtime Risk Gate (§33): a risk-increasing OPEN BUY can never fill in a permanently
        # non-running state. Cancel it deterministically and release its reservation so cash is
        # never frozen forever.
        if final_state in (
            SystemState.SAFE_MODE,
            SystemState.EMERGENCY_STOP,
            SystemState.ERROR,
        ):
            cancelled = await self._cancel_risk_increasing_buys(run_mode, orders, now)
            if cancelled:
                report.steps.append(f"CANCEL_RISK_INCREASING:{len(cancelled)}")
        await self.state_service.transition(
            run_mode,
            system_state=final_state,
            reason=f"recovery_complete:{final_state.value}",
            emit_outbox=False,
        )
        await self.state_service.heartbeat(run_mode)
        report.finished_at = self.clock.now()
        report.ok = reconciliation.ok and final_state is SystemState.RUNNING
        report.reason = (
            None if report.ok else f"recovery_landed_{final_state.value}"
        )
        report.steps.append(f"FINAL_STATE:{final_state.value}")
        return report

    async def _revalidate(
        self,
        run_mode: RunMode,
        orders: list[PaperOrderRecord],
        plans: list[TradePlanRecord],
        symbol_states: list[SymbolStateStore],
        quotes: dict[str, BestBidAsk],
        now: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        plans_by_id = {plan.plan_id: plan for plan in plans}
        versions = {state.instrument_id: state.state_version for state in symbol_states}
        plan_revalidation: list[dict[str, Any]] = []
        order_revalidation: list[dict[str, Any]] = []
        for plan in plans:
            issues = self._plan_issues(plan, versions, now)
            plan_revalidation.append(
                {
                    "plan_id": plan.plan_id,
                    "instrument_id": plan.instrument_id,
                    "status": plan.status,
                    "valid": not issues,
                    "issues": issues,
                }
            )
        for order in orders:
            if order.status != OrderStatus.OPEN:
                continue
            plan = plans_by_id.get(order.plan_id)
            issues: list[str] = []
            if plan is None:
                issues.append("PLAN_MISSING")
            else:
                issues.extend(self._plan_issues(plan, versions, now))
                if plan.instrument_id != order.instrument_id or plan.run_mode != order.run_mode:
                    issues.append("PLAN_SCOPE_MISMATCH")
                if order.side == OrderSide.BUY:
                    quote = quotes.get(order.instrument_id)
                    if quote is None or not self._bbo_fresh(quote, now):
                        issues.append("BBO_NOT_FRESH")
            if issues and order.side == OrderSide.BUY:
                # Stale risk-increasing orders must be cancelled so reservations are never frozen.
                await self.execution.cancel_order(order.order_id, now)
                issues.append("CANCELLED")
            order_revalidation.append(
                {
                    "order_id": order.order_id,
                    "instrument_id": order.instrument_id,
                    "side": order.side,
                    "issues": issues,
                    "cancelled": "CANCELLED" in issues,
                }
            )
        return plan_revalidation, order_revalidation

    @staticmethod
    def _plan_issues(
        plan: TradePlanRecord, versions: dict[str, int], now: datetime
    ) -> list[str]:
        """Strict G4 §33 plan checks: exists / ACTIVE / TTL / state_version / entry / stop."""
        issues: list[str] = []
        if plan.status != PlanStatus.ACTIVE:
            issues.append(f"status:{plan.status}")
            return issues
        if now >= plan.expires_at:
            issues.append("expired")
        version = versions.get(plan.instrument_id)
        if version is not None and plan.state_version != version:
            issues.append("state_version_stale")
        payload = plan.payload or {}
        entry = payload.get("entry_zone") or {}
        lower, upper = entry.get("lower"), entry.get("upper")
        if not (
            isinstance(lower, (int, float))
            and isinstance(upper, (int, float))
            and lower <= upper
        ):
            issues.append("entry_zone_invalid")
        stop, take_profit = payload.get("stop_loss"), payload.get("take_profit")
        if not (
            isinstance(stop, (int, float))
            and isinstance(take_profit, (int, float))
            and stop < take_profit
        ):
            issues.append("protection_invalid")
        return issues

    @staticmethod
    def _bbo_fresh(quote: BestBidAsk, now: datetime) -> bool:
        return (
            quote.tradable
            and quote.data_quality is DataQuality.FRESH
            and (now - quote.received_at.astimezone()).total_seconds() <= 5.0
        )

    async def _cancel_risk_increasing_buys(
        self, run_mode: RunMode, orders: list[PaperOrderRecord], now: datetime
    ) -> list[str]:
        """Cancel every OPEN BUY that can no longer fill in the final non-running state."""
        cancelled: list[str] = []
        for order in orders:
            if order.status != OrderStatus.OPEN or order.side != OrderSide.BUY:
                continue
            result = await self.execution.cancel_order(order.order_id, now)
            if result.cancelled:
                cancelled.append(order.order_id)
        return cancelled

    async def _final_state(
        self,
        operator_state: str,
        pre_system_state: str,
        reconciliation_ok: bool,
        fresh_all: bool,
        has_blocking_incidents: bool,
    ) -> SystemState:
        operator = OperatorState(operator_state)
        pre_system = SystemState(pre_system_state)
        if operator is OperatorState.EMERGENCY_STOP:
            return SystemState.EMERGENCY_STOP
        # A persisted SAFE_MODE latch survives restart; STARTING/RECOVERING must never erase it.
        if pre_system is SystemState.SAFE_MODE:
            return SystemState.SAFE_MODE
        if not reconciliation_ok:
            return SystemState.SAFE_MODE
        # Unresolved blocking incidents (POSITION_UNPROTECTED / RECOVERY_FAILED /
        # ACCOUNT_INTEGRITY_ERROR) must never silently land in RUNNING.
        if has_blocking_incidents:
            return SystemState.SAFE_MODE
        if pre_system is SystemState.PAUSED or operator is OperatorState.PAUSED:
            return SystemState.PAUSED
        if pre_system is SystemState.ERROR:
            return SystemState.ERROR
        if not fresh_all:
            return SystemState.DATA_DEGRADED
        return SystemState.RUNNING


__all__ = ["RecoveryManager"]
