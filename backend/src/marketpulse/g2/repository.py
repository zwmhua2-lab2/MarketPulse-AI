from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    DerivedObservationRecord,
    MarketEventRecord,
    SignalTimelineRecord,
    StateTransitionRecord,
    StrategyCandidateRecord,
    SymbolStateStore,
)

from .models import (
    FeatureSnapshot,
    MarketEvent,
    SignalTimelineEvent,
    StateTransition,
    StrategyCandidate,
    SymbolStateRecord,
    deterministic_id,
)


class InMemoryG2Repository:
    """Deterministic repository used by fixture tests and bounded local verification."""

    def __init__(self) -> None:
        self.events: dict[str, MarketEvent] = {}
        self.timeline: list[SignalTimelineEvent] = []
        self.states: dict[str, SymbolStateRecord] = {}
        self.transitions: list[StateTransition] = []
        self.candidates: list[StrategyCandidate] = []
        self.observations: list[FeatureSnapshot] = []

    async def get_state(self, instrument_id: str) -> SymbolStateRecord | None:
        record = self.states.get(instrument_id)
        return record.model_copy(deep=True) if record else None

    async def persist(self, event: MarketEvent, timeline: SignalTimelineEvent, state: SymbolStateRecord, transition: StateTransition, candidates: list[StrategyCandidate], observation: FeatureSnapshot) -> bool:
        if event.event_id in self.events:
            return False
        self.events[event.event_id] = event
        self.timeline.append(timeline)
        self.states[state.instrument_id] = state.model_copy(deep=True)
        self.transitions.append(transition)
        self.candidates.extend(candidates)
        self.observations.append(observation)
        return True


class PostgresG2Repository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_state(self, instrument_id: str) -> SymbolStateRecord | None:
        async with self._session_factory() as session:
            record = await session.get(SymbolStateStore, instrument_id)
        if record is None:
            return None
        return SymbolStateRecord(instrument_id=record.instrument_id, symbol=record.symbol, state=record.state, state_version=record.state_version, last_event_time=record.last_event_time, watch_expires_at=record.watch_expires_at, cooldown_until=record.cooldown_until, structure_fingerprint=record.structure_fingerprint)

    async def persist(self, event: MarketEvent, timeline: SignalTimelineEvent, state: SymbolStateRecord, transition: StateTransition, candidates: list[StrategyCandidate], observation: FeatureSnapshot) -> bool:
        async with self._session_factory() as session, session.begin():
            if await session.get(MarketEventRecord, event.event_id):
                return False
            session.add(MarketEventRecord(**event.model_dump(mode="python")))
            session.add(SignalTimelineRecord(**timeline.model_dump(mode="python")))
            await session.merge(SymbolStateStore(**state.model_dump(mode="python")))
            session.add(StateTransitionRecord(**transition.model_dump(mode="python")))
            session.add_all(StrategyCandidateRecord(**candidate.model_dump(mode="python")) for candidate in candidates)
            session.add(DerivedObservationRecord(observation_id=deterministic_id("obs", observation.instrument_id, observation.event_time.isoformat(), event.event_id), instrument_id=observation.instrument_id, event_time=observation.event_time, config_version=event.config_version, payload=observation.model_dump(mode="json")))
        return True
