from __future__ import annotations

from datetime import datetime

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import OutboxRecord, RuntimeControlRecord
from marketpulse.g3.models import RunMode
from marketpulse.g3.service import stable_id

from .models import OperatorState, SystemState


def effective_state(
    record: RuntimeControlRecord | None,
    *,
    core_data_ok: bool = True,
) -> SystemState:
    """Derive the effective runtime state from persisted operator intent + system facts.

    Operator intent always wins: a restart can never silently turn a human
    EMERGENCY_STOP or PAUSED back into RUNNING.
    """
    if record is None:
        return SystemState.STARTING
    operator = OperatorState(record.operator_state)
    system = SystemState(record.system_state)
    if operator is OperatorState.EMERGENCY_STOP:
        return SystemState.EMERGENCY_STOP
    if system is SystemState.SAFE_MODE:
        return SystemState.SAFE_MODE
    if operator is OperatorState.PAUSED:
        return SystemState.PAUSED
    if system is SystemState.PAUSED:
        return SystemState.PAUSED
    if system in (SystemState.STARTING, SystemState.RECOVERING):
        return system
    if system is SystemState.ERROR:
        return SystemState.ERROR
    if not core_data_ok or system is SystemState.DATA_DEGRADED:
        return SystemState.DATA_DEGRADED
    return SystemState.RUNNING


class SystemStateService:
    """Persisted G4 runtime control. PostgreSQL is the only restart-recovery source of truth."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.clock = clock or SystemClock()

    async def ensure(self, run_mode: RunMode) -> RuntimeControlRecord:
        async with self.sessions() as session, session.begin():
            return await self._ensure_in(session, run_mode)

    async def _ensure_in(
        self, session: AsyncSession, run_mode: RunMode
    ) -> RuntimeControlRecord:
        record = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == run_mode)
        )
        if record is None:
            now = self.clock.now()
            record = RuntimeControlRecord(
                run_mode=run_mode,
                operator_state=OperatorState.NORMAL,
                system_state=SystemState.STARTING,
                runtime_version=0,
                reason="bootstrapped",
                updated_at=now,
                heartbeat_at=now,
                payload={},
            )
            session.add(record)
            await session.flush()
        return record

    async def load(
        self,
        run_mode: RunMode,
        *,
        session: AsyncSession | None = None,
        for_update: bool = False,
    ) -> RuntimeControlRecord:
        if session is not None:
            return await self._load_in(session, run_mode, for_update=for_update)
        async with self.sessions() as inner, inner.begin():
            return await self._load_in(inner, run_mode, for_update=for_update)

    async def _load_in(
        self, session: AsyncSession, run_mode: RunMode, *, for_update: bool
    ) -> RuntimeControlRecord:
        await self._ensure_in(session, run_mode)
        statement = select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == run_mode)
        if for_update:
            statement = statement.with_for_update()
        record = await session.scalar(statement)
        assert record is not None  # guaranteed by _ensure_in
        return record

    async def transition(
        self,
        run_mode: RunMode,
        *,
        system_state: SystemState | None = None,
        operator_state: OperatorState | None = None,
        reason: str | None = None,
        session: AsyncSession | None = None,
        payload: dict | None = None,
        emit_outbox: bool = True,
    ) -> RuntimeControlRecord:
        """Atomically move operator/system state. Caller may supply the transaction."""
        if session is not None:
            return await self._transition_in(
                session,
                run_mode,
                system_state=system_state,
                operator_state=operator_state,
                reason=reason,
                payload=payload,
                emit_outbox=emit_outbox,
            )
        async with self.sessions() as inner, inner.begin():
            return await self._transition_in(
                inner,
                run_mode,
                system_state=system_state,
                operator_state=operator_state,
                reason=reason,
                payload=payload,
                emit_outbox=emit_outbox,
            )

    async def _transition_in(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        *,
        system_state: SystemState | None,
        operator_state: OperatorState | None,
        reason: str | None,
        payload: dict | None,
        emit_outbox: bool,
    ) -> RuntimeControlRecord:
        record = await self._load_in(session, run_mode, for_update=True)
        now = self.clock.now()
        previous = {
            "operator_state": record.operator_state,
            "system_state": record.system_state,
            "runtime_version": record.runtime_version,
        }
        if system_state is not None:
            record.system_state = system_state
        if operator_state is not None:
            record.operator_state = operator_state
        record.runtime_version += 1
        record.reason = reason
        record.updated_at = now
        record.heartbeat_at = now
        if payload:
            record.payload = {**record.payload, **payload}
        if emit_outbox:
            session.add(
                OutboxRecord(
                    outbox_id=stable_id(
                        "outbox", "SYSTEM_STATE_CHANGED", run_mode, record.runtime_version
                    ),
                    aggregate_id=str(run_mode),
                    event_type="SYSTEM_STATE_CHANGED",
                    payload={
                        "run_mode": run_mode,
                        "previous": previous,
                        "operator_state": record.operator_state,
                        "system_state": record.system_state,
                        "runtime_version": record.runtime_version,
                        "reason": reason,
                        "changed_at": now.isoformat(),
                    },
                    created_at=now,
                )
            )
        return record

    async def heartbeat(self, run_mode: RunMode, session: AsyncSession | None = None) -> datetime:
        now = self.clock.now()
        if session is not None:
            record = await self._load_in(session, run_mode, for_update=True)
            record.heartbeat_at = now
            return now
        async with self.sessions() as inner, inner.begin():
            record = await self._load_in(inner, run_mode, for_update=True)
            record.heartbeat_at = now
            return now

    @staticmethod
    def snapshot(record: RuntimeControlRecord | None) -> dict:
        if record is None:
            return {}
        state = inspect(record)
        return {
            "run_mode": record.run_mode,
            "operator_state": record.operator_state,
            "system_state": record.system_state,
            "runtime_version": record.runtime_version,
            "reason": record.reason,
            "updated_at": record.updated_at.isoformat(),
            "heartbeat_at": record.heartbeat_at.isoformat(),
            "detached": state.detached,
        }
