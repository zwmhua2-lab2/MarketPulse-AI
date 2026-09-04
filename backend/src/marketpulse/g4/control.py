from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    OutboxRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    SymbolControlRecord,
    SymbolStateStore,
    TradePlanRecord,
)
from marketpulse.g3.models import BestBidAsk, OrderSide, OrderStatus, PlanStatus, RunMode
from marketpulse.g3.service import PaperExecutionService, stable_id
from marketpulse.runtime import HealthRegistry

from .incidents import IncidentManager
from .models import (
    BLOCKING_INCIDENT_TYPES,
    RISK_BLOCKING_COMPONENTS,
    ControlOutcome,
    HealthComponent,
    HealthStatus,
    IncidentType,
    OperatorState,
    PositionEventType,
    ProtectionOutcome,
    ReconciliationReport,
    SystemState,
)
from .protection import PositionProtectionService
from .risk_gate import SystemRiskGate
from .state import SystemStateService, effective_state

ReconcileFn = Callable[[RunMode], Awaitable[ReconciliationReport]]


class SystemControlService:
    """Operator control plane: pause / resume / emergency stop / safe mode / symbol block.

    Every control action persists its own facts and never mutates accounting outside a single
    PostgreSQL transaction.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        state_service: SystemStateService,
        incidents: IncidentManager,
        health: HealthRegistry,
        risk_gate: SystemRiskGate,
        protection: PositionProtectionService,
        execution: PaperExecutionService,
        reconcile: ReconcileFn,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.state_service = state_service
        self.incidents = incidents
        self.health = health
        self.risk_gate = risk_gate
        self.protection = protection
        self.execution = execution
        self.reconcile = reconcile
        self.clock = clock or SystemClock()

    # ------------------------------------------------------------------ pause / resume

    async def pause(
        self, run_mode: RunMode, reason: str = "operator_pause", now: datetime | None = None
    ) -> ControlOutcome:
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            if (
                control.operator_state == OperatorState.PAUSED
                and control.system_state == SystemState.PAUSED
            ):
                return self._outcome("pause", control, True, "already_paused")
            record = await self.state_service.transition(
                run_mode,
                operator_state=OperatorState.PAUSED,
                system_state=SystemState.PAUSED,
                reason=reason,
                session=session,
            )
            return self._outcome("pause", record, True, reason)

    async def resume(
        self, run_mode: RunMode, now: datetime | None = None
    ) -> ControlOutcome:
        """Resume is a gate, not a switch: every precondition must pass or it is refused."""
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            if control.operator_state == OperatorState.EMERGENCY_STOP:
                return self._outcome(
                    "resume", control, False, "emergency_stop_requires_recovery"
                )
            gate_reason = await self._resume_gate(session, run_mode, now)
            if gate_reason is not None:
                return self._outcome("resume", control, False, gate_reason)
            record = await self.state_service.transition(
                run_mode,
                operator_state=OperatorState.NORMAL,
                system_state=SystemState.RUNNING,
                reason="operator_resume",
                session=session,
            )
            return self._outcome("resume", record, True, None)

    async def _resume_gate(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        now: datetime,
        *,
        allow_recoverable_incidents: bool = False,
    ) -> str | None:
        degraded = self.health.blocking(RISK_BLOCKING_COMPONENTS)
        if degraded:
            component, *_ = sorted(degraded)
            return f"HEALTH_{component}_{self.health.status(component)}"
        blocking = await self.incidents.blocking(run_mode, session=session)
        if blocking and not allow_recoverable_incidents:
            return f"INCIDENT_{blocking[0].incident_type}"
        report = await self.reconcile(run_mode)
        if not report.ok:
            return f"RECONCILIATION_FAILED:{','.join(report.diagnostics[:3])}"
        if self.health.status(HealthComponent.CORE_MARKET_DATA.value) != HealthStatus.HEALTHY.value:
            return "CORE_MARKET_DATA_NOT_FRESH"
        return None

    async def _safe_mode_incident_gate(
        self, session: AsyncSession, run_mode: RunMode, now: datetime
    ) -> str | None:
        """Prove each blocking incident's durable condition is gone before resolving it."""
        blocking = await self.incidents.blocking(run_mode, session=session)
        for incident in blocking:
            if incident.incident_type != IncidentType.POSITION_UNPROTECTED:
                # ACCOUNT_INTEGRITY_ERROR and RECOVERY_FAILED are covered by the health and
                # reconciliation checks in _resume_gate.
                continue
            positions = list(
                (
                    await session.scalars(
                        select(PositionRecord).where(
                            PositionRecord.run_mode == run_mode,
                            PositionRecord.quantity > 0,
                        )
                    )
                ).all()
            )
            for position in positions:
                plan = await session.scalar(
                    select(TradePlanRecord).where(
                        TradePlanRecord.run_mode == run_mode,
                        TradePlanRecord.instrument_id == position.instrument_id,
                        TradePlanRecord.status == PlanStatus.ACTIVE,
                    )
                )
                if plan is None or now >= plan.expires_at:
                    return f"INCIDENT_{incident.incident_type}"
        return None

    # ------------------------------------------------------------------ emergency

    async def emergency_stop(
        self, run_mode: RunMode, reason: str = "operator_emergency_stop", now: datetime | None = None
    ) -> ControlOutcome:
        """Block new risk, cancel every risk-increasing OPEN BUY with its reservation.

        Emergency stop is NOT close-all: open positions are kept and protection keeps working.
        """
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            record = await self.state_service.transition(
                run_mode,
                operator_state=OperatorState.EMERGENCY_STOP,
                system_state=SystemState.EMERGENCY_STOP,
                reason=reason,
                session=session,
            )
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord)
                        .where(
                            PaperOrderRecord.run_mode == run_mode,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            cancelled: list[str] = []
            for order in orders:
                result = await self.execution.cancel_order(order.order_id, now, session=session)
                if result.cancelled:
                    cancelled.append(order.order_id)
            await self.incidents.open(
                incident_type=IncidentType.EMERGENCY_STOP_ACTIVATED,
                run_mode=run_mode,
                reason=reason,
                payload={"cancelled_order_ids": cancelled},
                session=session,
            )
            for instrument_id in sorted({order.instrument_id for order in orders}):
                session.add(
                    PositionEventRecord(
                        event_id=stable_id(
                            "pevt", PositionEventType.EMERGENCY_ACTION, run_mode, instrument_id, now
                        ),
                        run_mode=run_mode,
                        instrument_id=instrument_id,
                        event_type=PositionEventType.EMERGENCY_ACTION,
                        dedupe_key=(
                            f"emergency:{run_mode}:{instrument_id}:"
                            f"{record.runtime_version}"
                        ),
                        payload={"reason": reason, "cancelled_order_ids": cancelled},
                        created_at=now,
                    )
                )
            session.add(
                OutboxRecord(
                    outbox_id=stable_id(
                        "outbox", "EMERGENCY_STOP_ACTIVATED", run_mode, record.runtime_version
                    ),
                    aggregate_id=str(run_mode),
                    event_type="EMERGENCY_STOP_ACTIVATED",
                    payload={"reason": reason, "cancelled_order_ids": cancelled},
                    created_at=now,
                )
            )
            return self._outcome(
                "emergency_stop", record, True, reason, cancelled_order_ids=cancelled
            )

    async def emergency_recovery(
        self, run_mode: RunMode, now: datetime | None = None
    ) -> ControlOutcome:
        """NEVER goes straight to RUNNING: validated recovery lands in PAUSED first."""
        now = now or self.clock.now()
        async with self.sessions() as session:
            control = await self.state_service.load(run_mode, session=session)
            if control.operator_state != OperatorState.EMERGENCY_STOP:
                return self._outcome("emergency_recovery", control, False, "not_in_emergency_stop")
            gate_reason = await self._resume_gate(session, run_mode, now)
            if gate_reason is not None:
                return self._outcome("emergency_recovery", control, False, gate_reason)

        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            if control.operator_state != OperatorState.EMERGENCY_STOP:
                return self._outcome("emergency_recovery", control, False, "not_in_emergency_stop")
            record = await self.state_service.transition(
                run_mode,
                operator_state=OperatorState.PAUSED,
                system_state=SystemState.PAUSED,
                reason="emergency_recovery_validated",
                session=session,
            )
            await self.incidents.resolve_type(
                incident_type=IncidentType.EMERGENCY_STOP_ACTIVATED,
                run_mode=run_mode,
                session=session,
            )
            return self._outcome(
                "emergency_recovery", record, True, "recovered_to_paused_awaiting_resume"
            )

    # ------------------------------------------------------------------ safe mode

    async def enter_safe_mode(
        self,
        run_mode: RunMode,
        reason: str,
        *,
        incident_type: IncidentType = IncidentType.ACCOUNT_INTEGRITY_ERROR,
        instrument_id: str | None = None,
        now: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> ControlOutcome:
        now = now or self.clock.now()
        if session is not None:
            return await self._enter_safe_mode_in(
                session, run_mode, reason, incident_type, instrument_id, now
            )
        async with self.sessions() as inner, inner.begin():
            return await self._enter_safe_mode_in(
                inner, run_mode, reason, incident_type, instrument_id, now
            )

    async def _enter_safe_mode_in(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        reason: str,
        incident_type: IncidentType,
        instrument_id: str | None,
        now: datetime,
    ) -> ControlOutcome:
        record = await self.state_service.transition(
            run_mode,
            system_state=SystemState.SAFE_MODE,
            reason=reason,
            session=session,
        )
        await self.incidents.open(
            incident_type=incident_type,
            run_mode=run_mode,
            reason=reason,
            instrument_id=instrument_id,
            session=session,
        )
        return self._outcome("enter_safe_mode", record, True, reason)

    async def safe_mode_recovery(
        self, run_mode: RunMode, now: datetime | None = None
    ) -> ControlOutcome:
        """Clearing safe mode requires the blocking condition gone, then lands in PAUSED."""
        now = now or self.clock.now()
        async with self.sessions() as session:
            control = await self.state_service.load(run_mode, session=session)
            if control.system_state != SystemState.SAFE_MODE:
                return self._outcome("safe_mode_recovery", control, False, "not_in_safe_mode")
            gate_reason = await self._resume_gate(
                session, run_mode, now, allow_recoverable_incidents=True
            )
            if gate_reason is None:
                gate_reason = await self._safe_mode_incident_gate(session, run_mode, now)
            if gate_reason is not None:
                return self._outcome("safe_mode_recovery", control, False, gate_reason)

        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            if control.system_state != SystemState.SAFE_MODE:
                return self._outcome("safe_mode_recovery", control, False, "not_in_safe_mode")
            gate_reason = await self._resume_gate(
                session, run_mode, now, allow_recoverable_incidents=True
            )
            if gate_reason is None:
                gate_reason = await self._safe_mode_incident_gate(session, run_mode, now)
            if gate_reason is not None:
                return self._outcome("safe_mode_recovery", control, False, gate_reason)
            record = await self.state_service.transition(
                run_mode,
                operator_state=OperatorState.PAUSED,
                system_state=SystemState.PAUSED,
                reason="safe_mode_recovery_validated",
                session=session,
            )
            for incident_type in BLOCKING_INCIDENT_TYPES:
                await self.incidents.resolve_type(
                    incident_type=incident_type, run_mode=run_mode, session=session
                )
            return self._outcome(
                "safe_mode_recovery", record, True, "recovered_to_paused_awaiting_resume"
            )

    # ------------------------------------------------------------------ symbol block

    async def block_symbol(
        self,
        run_mode: RunMode,
        instrument_id: str,
        reason: str = "symbol_blocked",
        now: datetime | None = None,
    ) -> ControlOutcome:
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            record = await session.scalar(
                select(SymbolControlRecord).where(
                    SymbolControlRecord.run_mode == run_mode,
                    SymbolControlRecord.instrument_id == instrument_id,
                )
            )
            if record is None:
                session.add(
                    SymbolControlRecord(
                        control_id=stable_id("sctl", run_mode, instrument_id),
                        run_mode=run_mode,
                        instrument_id=instrument_id,
                        blocked=True,
                        reason=reason,
                        updated_at=now,
                        payload={},
                    )
                )
            else:
                record.blocked = True
                record.reason = reason
                record.updated_at = now
            # Reuse the G2 symbol state version so every stale plan fails the fill-time guard
            # instead of silently waiting for a fill that must never happen.
            await session.execute(
                update(SymbolStateStore)
                .where(SymbolStateStore.instrument_id == instrument_id)
                .values(state_version=SymbolStateStore.state_version + 1)
            )
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord)
                        .where(
                            PaperOrderRecord.run_mode == run_mode,
                            PaperOrderRecord.instrument_id == instrument_id,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            cancelled: list[str] = []
            for order in orders:
                result = await self.execution.cancel_order(order.order_id, now, session=session)
                if result.cancelled:
                    cancelled.append(order.order_id)
            session.add(
                PositionEventRecord(
                    event_id=stable_id("pevt", "SYMBOL_BLOCK", run_mode, instrument_id, now),
                    run_mode=run_mode,
                    instrument_id=instrument_id,
                    event_type=PositionEventType.SYMBOL_BLOCK,
                    dedupe_key=f"symbol_block:{run_mode}:{instrument_id}:{now.isoformat()}",
                    payload={"reason": reason, "cancelled_order_ids": cancelled},
                    created_at=now,
                )
            )
            session.add(
                OutboxRecord(
                    outbox_id=stable_id("outbox", "SYMBOL_BLOCKED", run_mode, instrument_id, now),
                    aggregate_id=instrument_id,
                    event_type="SYMBOL_BLOCKED",
                    payload={"reason": reason, "cancelled_order_ids": cancelled},
                    created_at=now,
                )
            )
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            return self._outcome(
                "block_symbol", control, True, reason, cancelled_order_ids=cancelled
            )

    async def unblock_symbol(
        self,
        run_mode: RunMode,
        instrument_id: str,
        reason: str = "symbol_unblocked",
        now: datetime | None = None,
    ) -> ControlOutcome:
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            record = await session.scalar(
                select(SymbolControlRecord).where(
                    SymbolControlRecord.run_mode == run_mode,
                    SymbolControlRecord.instrument_id == instrument_id,
                )
            )
            if record is None:
                session.add(
                    SymbolControlRecord(
                        control_id=stable_id("sctl", run_mode, instrument_id),
                        run_mode=run_mode,
                        instrument_id=instrument_id,
                        blocked=False,
                        reason=reason,
                        updated_at=now,
                        payload={},
                    )
                )
            else:
                record.blocked = False
                record.reason = reason
                record.updated_at = now
            session.add(
                OutboxRecord(
                    outbox_id=stable_id("outbox", "SYMBOL_UNBLOCKED", run_mode, instrument_id, now),
                    aggregate_id=instrument_id,
                    event_type="SYMBOL_UNBLOCKED",
                    payload={"reason": reason},
                    created_at=now,
                )
            )
            return self._outcome("unblock_symbol", control, True, reason)

    # ------------------------------------------------------------------ trading control

    async def manual_close(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk | None = None,
        *,
        now: datetime | None = None,
    ) -> ProtectionOutcome:
        """Full manual close. Allowed in RUNNING / PAUSED / SAFE_MODE / EMERGENCY_STOP."""
        now = now or self.clock.now()
        quote = bbo or await self.execution.bbo_for(instrument_id)
        if self.health.status(HealthComponent.EXECUTION.value) != HealthStatus.HEALTHY.value:
            await self.incidents.open(
                incident_type=IncidentType.CORE_DATA_STALE,
                run_mode=run_mode,
                reason="manual_close_blocked_execution_unavailable",
                instrument_id=instrument_id,
            )
            return ProtectionOutcome(
                instrument_id=instrument_id, triggered=False, reason="EXECUTION_UNAVAILABLE"
            )
        return await self.protection.manual_close(run_mode, instrument_id, quote, now=now)

    async def cancel_order(self, order_id: str, now: datetime | None = None):
        return await self.execution.cancel_order(order_id, now or self.clock.now())

    # ------------------------------------------------------------------ status

    async def status(self, run_mode: RunMode, now: datetime | None = None) -> dict[str, Any]:
        now = now or self.clock.now()
        async with self.sessions() as session:
            control = await self.state_service.load(run_mode, session=session)
            incidents = await self.incidents.blocking(run_mode, session=session)
        core_ok = self.health.status(HealthComponent.CORE_MARKET_DATA.value) == (
            HealthStatus.HEALTHY.value
        )
        state = effective_state(control, core_data_ok=core_ok)
        return {
            "run_mode": run_mode,
            "operator_state": control.operator_state,
            "system_state": control.system_state,
            "effective_state": state.value,
            "runtime_version": control.runtime_version,
            "reason": control.reason,
            "updated_at": control.updated_at,
            "heartbeat_at": control.heartbeat_at,
            "core_data_ok": core_ok,
            "health": self.health.snapshot(),
            "blocking_incidents": [item.incident_type for item in incidents],
        }

    @staticmethod
    def _outcome(
        action: str,
        control,
        accepted: bool,
        reason: str | None,
        *,
        cancelled_order_ids: list[str] | None = None,
    ) -> ControlOutcome:
        return ControlOutcome(
            action=action,
            accepted=accepted,
            operator_state=OperatorState(control.operator_state),
            system_state=SystemState(control.system_state),
            runtime_version=control.runtime_version,
            reason=reason,
            cancelled_order_ids=cancelled_order_ids or [],
        )
