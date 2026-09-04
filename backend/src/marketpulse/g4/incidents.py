from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import IncidentRecord
from marketpulse.g3.models import RunMode
from marketpulse.g3.service import stable_id

from .models import BLOCKING_INCIDENT_TYPES, IncidentStatus, IncidentType


class IncidentManager:
    """Minimal persisted incident store. Records facts; never repairs data."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.clock = clock or SystemClock()

    async def open(
        self,
        *,
        incident_type: IncidentType,
        run_mode: RunMode,
        reason: str,
        instrument_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> IncidentRecord:
        """Idempotent per (type, run_mode, instrument): reuses an existing OPEN incident."""
        if session is not None:
            return await self._open_in(
                session,
                incident_type=incident_type,
                run_mode=run_mode,
                reason=reason,
                instrument_id=instrument_id,
                payload=payload,
            )
        async with self.sessions() as inner, inner.begin():
            return await self._open_in(
                inner,
                incident_type=incident_type,
                run_mode=run_mode,
                reason=reason,
                instrument_id=instrument_id,
                payload=payload,
            )

    async def _open_in(
        self,
        session: AsyncSession,
        *,
        incident_type: IncidentType,
        run_mode: RunMode,
        reason: str,
        instrument_id: str | None,
        payload: dict[str, Any] | None,
    ) -> IncidentRecord:
        existing = await session.scalar(
            select(IncidentRecord).where(
                IncidentRecord.incident_type == incident_type,
                IncidentRecord.run_mode == run_mode,
                IncidentRecord.instrument_id == instrument_id,
                IncidentRecord.status == IncidentStatus.OPEN,
            )
        )
        now = self.clock.now()
        if existing is not None:
            existing.payload = {**existing.payload, **self._evidence(now, reason, payload)}
            return existing
        incident = IncidentRecord(
            incident_id=stable_id("incident", incident_type, run_mode, instrument_id, now.isoformat()),
            incident_type=incident_type,
            run_mode=run_mode,
            instrument_id=instrument_id,
            status=IncidentStatus.OPEN,
            reason=reason,
            payload=self._evidence(now, reason, payload),
            opened_at=now,
            resolved_at=None,
        )
        session.add(incident)
        await session.flush()
        return incident

    async def resolve(
        self,
        incident_id: str,
        *,
        session: AsyncSession | None = None,
    ) -> IncidentRecord | None:
        if session is not None:
            return await self._resolve_in(session, incident_id)
        async with self.sessions() as inner, inner.begin():
            return await self._resolve_in(inner, incident_id)

    async def _resolve_in(self, session: AsyncSession, incident_id: str) -> IncidentRecord | None:
        incident = await session.scalar(
            select(IncidentRecord).where(IncidentRecord.incident_id == incident_id)
        )
        if incident is None or incident.status == IncidentStatus.RESOLVED:
            return incident
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = self.clock.now()
        return incident

    async def resolve_type(
        self,
        *,
        incident_type: IncidentType,
        run_mode: RunMode,
        instrument_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[IncidentRecord]:
        if session is not None:
            return await self._resolve_type_in(session, incident_type, run_mode, instrument_id)
        async with self.sessions() as inner, inner.begin():
            return await self._resolve_type_in(inner, incident_type, run_mode, instrument_id)

    async def _resolve_type_in(
        self,
        session: AsyncSession,
        incident_type: IncidentType,
        run_mode: RunMode,
        instrument_id: str | None,
    ) -> list[IncidentRecord]:
        incidents = list(
            (
                await session.scalars(
                    select(IncidentRecord).where(
                        IncidentRecord.incident_type == incident_type,
                        IncidentRecord.run_mode == run_mode,
                        IncidentRecord.status == IncidentStatus.OPEN,
                    )
                )
            ).all()
        )
        now = self.clock.now()
        for incident in incidents:
            if instrument_id is not None and incident.instrument_id != instrument_id:
                continue
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = now
        return incidents

    async def blocking(
        self, run_mode: RunMode, *, session: AsyncSession | None = None
    ) -> list[IncidentRecord]:
        """Unresolved incidents that must block new risk until explicitly cleared."""
        if session is not None:
            return await self._blocking_in(session, run_mode)
        async with self.sessions() as inner:
            return await self._blocking_in(inner, run_mode)

    async def _blocking_in(
        self, session: AsyncSession, run_mode: RunMode
    ) -> list[IncidentRecord]:
        incidents = list(
            (
                await session.scalars(
                    select(IncidentRecord).where(
                        IncidentRecord.run_mode == run_mode,
                        IncidentRecord.status == IncidentStatus.OPEN,
                    )
                )
            ).all()
        )
        return [
            incident
            for incident in incidents
            if IncidentType(incident.incident_type) in BLOCKING_INCIDENT_TYPES
        ]

    @staticmethod
    def _evidence(now: datetime, reason: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        return {"reason": reason, "recorded_at": now.isoformat(), **(payload or {})}
