from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import SymbolControlRecord, TradePlanRecord
from marketpulse.g3.models import OrderSide, PlanStatus, RunMode
from marketpulse.runtime import HealthRegistry

from .incidents import IncidentManager
from .models import RISK_BLOCKING_COMPONENTS, HealthComponent
from .state import SystemStateService, effective_state


class SystemRiskGate:
    """Single programmatic admission boundary for every risk-increasing action.

    Locks the persisted runtime control row first so Pause / Emergency Stop / Safe Mode and a
    concurrent BUY fill can never interleave: whoever holds that row decides the outcome.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        state_service: SystemStateService,
        incidents: IncidentManager,
        health: HealthRegistry,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.state_service = state_service
        self.incidents = incidents
        self.health = health
        self.clock = clock or SystemClock()

    async def evaluate(
        self,
        session: AsyncSession,
        *,
        run_mode: RunMode,
        instrument_id: str,
        side: OrderSide,
        plan_id: str | None,
        now: datetime | None = None,
    ) -> str | None:
        """Return `None` to admit the action, or a machine-readable reason to block it."""
        if side is not OrderSide.BUY:
            # V1 spot LONG: risk-reducing SELL is never blocked by pause / emergency / safe mode.
            return None
        now = now or self.clock.now()
        control = await self.state_service.load(run_mode, session=session, for_update=True)
        return await self._admit(session, control, run_mode, instrument_id, plan_id, now)

    async def check(
        self,
        run_mode: RunMode,
        instrument_id: str,
        *,
        plan_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[bool, str | None]:
        """Standalone admission check for G4 orchestration paths (not inside a G3 transaction)."""
        now = now or self.clock.now()
        async with self.sessions() as session, session.begin():
            control = await self.state_service.load(run_mode, session=session, for_update=True)
            reason = await self._admit(
                session, control, run_mode, instrument_id, plan_id, now, side=OrderSide.BUY
            )
        return reason is None, reason

    async def _admit(
        self,
        session: AsyncSession,
        control,
        run_mode: RunMode,
        instrument_id: str,
        plan_id: str | None,
        now: datetime,
        *,
        side: OrderSide = OrderSide.BUY,
    ) -> str | None:
        core_data_ok = self.health.all_healthy({HealthComponent.CORE_MARKET_DATA.value})
        state = effective_state(control, core_data_ok=core_data_ok)
        if state.value != "RUNNING":
            return f"RUNTIME_STATE_{state.value}"

        degraded = self.health.blocking(RISK_BLOCKING_COMPONENTS)
        if degraded:
            component, *_ = sorted(degraded)
            status = self.health.status(component)
            return f"HEALTH_{component}_{status}"

        blocking = await self.incidents.blocking(run_mode, session=session)
        if blocking:
            return f"INCIDENT_{blocking[0].incident_type}"

        blocked = await session.scalar(
            select(SymbolControlRecord).where(
                SymbolControlRecord.run_mode == run_mode,
                SymbolControlRecord.instrument_id == instrument_id,
                SymbolControlRecord.blocked.is_(True),
            )
        )
        if blocked is not None:
            return "SYMBOL_BLOCKED"

        if side is OrderSide.BUY:
            plan_reason = await self._plan_reason(session, run_mode, instrument_id, plan_id, now)
            if plan_reason is not None:
                return plan_reason
        return None

    async def _plan_reason(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        instrument_id: str,
        plan_id: str | None,
        now: datetime,
    ) -> str | None:
        if not plan_id:
            return "PLAN_MISSING"
        plan = await session.scalar(
            select(TradePlanRecord).where(TradePlanRecord.plan_id == plan_id)
        )
        if plan is None:
            return "PLAN_MISSING"
        if plan.run_mode != run_mode or plan.instrument_id != instrument_id:
            return "PLAN_SCOPE_MISMATCH"
        if plan.status != PlanStatus.ACTIVE:
            return f"PLAN_{plan.status}"
        if now >= plan.expires_at:
            return "PLAN_EXPIRED"
        return None
