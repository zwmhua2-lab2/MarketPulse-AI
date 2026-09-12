from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    DerivedObservationRecord,
    MarketEventRecord,
    SignalTimelineRecord,
    StateTransitionRecord,
    StrategyCandidateRecord,
    SymbolStateStore,
)
from marketpulse.edge.capture import (
    EdgeCaptureContext,
    ReferenceQuote,
    capture_opportunity,
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

# Bounded accessor for the caller's *current* reference quote of one instrument.
# It is consulted once per persisted event, so the quote it returns belongs to the
# capture that is happening now. It must be an in-process read of already-held
# market state (no I/O), because it runs inside the G2 persistence transaction.
ReferenceQuoteFor = Callable[[str], ReferenceQuote | None]


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
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        capture: EdgeCaptureContext | None = None,
        reference_quote_for: ReferenceQuoteFor | None = None,
    ) -> None:
        self._session_factory = session_factory
        # SE-02B opportunity capture is opt-in. ``None`` (the default) keeps the
        # accepted G2 behaviour byte-for-byte: no Edge write, no Edge failure mode.
        self._capture = capture
        # The reference quote is a per-capture causal fact, never a constructor
        # constant: one repository instance serves many events, so a quote stored
        # here would silently become the reference of every later opportunity.
        self._reference_quote_for = reference_quote_for

    async def get_state(self, instrument_id: str) -> SymbolStateRecord | None:
        async with self._session_factory() as session:
            record = await session.get(SymbolStateStore, instrument_id)
        if record is None:
            return None
        return SymbolStateRecord(instrument_id=record.instrument_id, symbol=record.symbol, state=record.state, state_version=record.state_version, last_event_time=record.last_event_time, watch_expires_at=record.watch_expires_at, cooldown_until=record.cooldown_until, structure_fingerprint=record.structure_fingerprint)

    async def persist(self, event: MarketEvent, timeline: SignalTimelineEvent, state: SymbolStateRecord, transition: StateTransition, candidates: list[StrategyCandidate], observation: FeatureSnapshot) -> bool:
        async with self._session_factory() as session, session.begin():
            inserted_event_id = await session.scalar(
                insert(MarketEventRecord)
                .values(**event.model_dump(mode="python"))
                .on_conflict_do_nothing(index_elements=[MarketEventRecord.event_id])
                .returning(MarketEventRecord.event_id)
            )
            if inserted_event_id is None:
                return False
            session.add(SignalTimelineRecord(**timeline.model_dump(mode="python")))
            await session.merge(SymbolStateStore(**state.model_dump(mode="python")))
            session.add(StateTransitionRecord(**transition.model_dump(mode="python")))
            session.add_all(StrategyCandidateRecord(**candidate.model_dump(mode="python")) for candidate in candidates)
            session.add(DerivedObservationRecord(observation_id=deterministic_id("obs", observation.instrument_id, observation.event_time.isoformat(), event.event_id), instrument_id=observation.instrument_id, event_time=observation.event_time, config_version=event.config_version, payload=observation.model_dump(mode="json")))
            if self._capture is not None:
                # Same session, same transaction: the durable G2 facts and the Edge
                # opportunity evidence commit together or not at all. An Edge
                # integrity failure propagates so this transaction fails closed --
                # it is never converted into a silent "skip evidence".
                await capture_opportunity(
                    session,
                    event=event,
                    timeline=timeline,
                    state=state,
                    transition=transition,
                    candidates=candidates,
                    observation=observation,
                    context=self._capture,
                    reference_quote=(
                        None
                        if self._reference_quote_for is None
                        else self._reference_quote_for(event.instrument_id)
                    ),
                )
        return True
