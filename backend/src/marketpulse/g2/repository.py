from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    DerivedObservationRecord,
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
    MarketEventRecord,
    SignalTimelineRecord,
    StateTransitionRecord,
    StrategyCandidateRecord,
    SymbolStateStore,
)
from marketpulse.edge.capture import (
    CaptureAnchor,
    CaptureAnchorInputs,
    EdgeCaptureContext,
    ReferenceQuote,
    build_capture_anchor,
    capture_opportunity,
)
from marketpulse.edge.models import EvidenceSource
from marketpulse.edge.repository import (
    append_capture_anchor,
    capture_anchor_from_record,
    load_capture_anchor_for_event,
    record_bbo_observation,
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

logger = logging.getLogger(__name__)


class CaptureAnchorOrphan(RuntimeError):
    """A durable anchor cannot safely be consumed against current G2 preconditions."""


class CaptureAdmissionRejected(RuntimeError):
    """A new FORWARD_PAPER anchor lacks explicit live-session admission proof."""


def _same_model(left: object, right: object) -> bool:
    return left.model_dump(mode="json") == right.model_dump(mode="json")  # type: ignore[attr-defined]


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

    async def resume_capture_anchor(
        self, event: MarketEvent, precondition_state: SymbolStateRecord
    ) -> CaptureAnchorInputs | None:
        return None

    async def persist(
        self,
        event: MarketEvent,
        timeline: SignalTimelineEvent,
        state: SymbolStateRecord,
        transition: StateTransition,
        candidates: list[StrategyCandidate],
        observation: FeatureSnapshot,
        *,
        precondition_state: SymbolStateRecord | None = None,
    ) -> bool:
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
        # Bounded by in-flight G2 event ids in the caller's runtime. It exists
        # only until the admission transaction succeeds or the process dies;
        # it is deliberately not a queue/WAL/recovery mechanism.
        self._pending_capture_anchors: dict[str, CaptureAnchor] = {}

    async def get_state(self, instrument_id: str) -> SymbolStateRecord | None:
        async with self._session_factory() as session:
            record = await session.get(SymbolStateStore, instrument_id)
        if record is None:
            return None
        return SymbolStateRecord(instrument_id=record.instrument_id, symbol=record.symbol, state=record.state, state_version=record.state_version, last_event_time=record.last_event_time, watch_expires_at=record.watch_expires_at, cooldown_until=record.cooldown_until, structure_fingerprint=record.structure_fingerprint)

    async def resume_capture_anchor(
        self, event: MarketEvent, precondition_state: SymbolStateRecord
    ) -> CaptureAnchorInputs | None:
        """Load a pending Forward anchor before EventRuntime invokes Strategy again."""

        if self._capture is None or self._capture.source_type is not EvidenceSource.FORWARD_PAPER:
            return None
        async with self._session_factory() as session:
            anchor = await load_capture_anchor_for_event(session, event.event_id)
        if anchor is None:
            return None
        inputs = anchor.formal_inputs()
        self._validate_anchor_precondition(inputs, event, precondition_state)
        return inputs

    async def resume_pending_capture_anchors(self) -> int:
        """Consume durable, unformalized anchors using PostgreSQL facts only."""

        if self._capture is None or self._capture.source_type is not EvidenceSource.FORWARD_PAPER:
            return 0
        async with self._session_factory() as session:
            anchors = list(
                (
                    await session.scalars(
                        select(EdgeOpportunityCaptureAnchorRecord)
                        .outerjoin(
                            EdgeOpportunityEvidenceRecord,
                            (EdgeOpportunityEvidenceRecord.opportunity_id
                             == EdgeOpportunityCaptureAnchorRecord.opportunity_id)
                            & (EdgeOpportunityEvidenceRecord.evidence_revision
                               == EdgeOpportunityCaptureAnchorRecord.evidence_revision),
                        )
                        .where(EdgeOpportunityEvidenceRecord.evidence_id.is_(None))
                    )
                ).all()
            )
        resumed = 0
        for record in anchors:
            inputs = capture_anchor_from_record(record).formal_inputs()
            if await self.persist(
                inputs.event,
                inputs.timeline,
                inputs.state,
                inputs.transition,
                inputs.candidates,
                inputs.observation,
                precondition_state=inputs.precondition_state,
            ):
                resumed += 1
        return resumed

    @staticmethod
    def _validate_anchor_precondition(
        inputs: CaptureAnchorInputs,
        event: MarketEvent,
        precondition_state: SymbolStateRecord | None,
    ) -> None:
        if not _same_model(inputs.event, event):
            raise CaptureAnchorOrphan("durable capture anchor event facts are incompatible")
        if (
            inputs.precondition_state is not None
            and precondition_state is not None
            and not _same_model(inputs.precondition_state, precondition_state)
        ):
            raise CaptureAnchorOrphan("durable G2 precondition is incompatible with capture anchor")

    @staticmethod
    async def _validate_durable_anchor_precondition(
        session: AsyncSession, inputs: CaptureAnchorInputs
    ) -> None:
        """Fence a resumed anchor against the PostgreSQL G2 source of truth."""

        if inputs.precondition_state is None:
            return
        stored = await session.get(SymbolStateStore, inputs.event.instrument_id)
        actual = (
            SymbolStateRecord(instrument_id=inputs.event.instrument_id, symbol=inputs.event.symbol)
            if stored is None
            else SymbolStateRecord(
                instrument_id=stored.instrument_id,
                symbol=stored.symbol,
                state=stored.state,
                state_version=stored.state_version,
                last_event_time=stored.last_event_time,
                watch_expires_at=stored.watch_expires_at,
                cooldown_until=stored.cooldown_until,
                structure_fingerprint=stored.structure_fingerprint,
            )
        )
        if not _same_model(inputs.precondition_state, actual):
            raise CaptureAnchorOrphan("durable G2 precondition is incompatible with capture anchor")

    async def _admit_or_load_capture_anchor(
        self,
        *,
        precondition_state: SymbolStateRecord | None,
        event: MarketEvent,
        timeline: SignalTimelineEvent,
        state: SymbolStateRecord,
        transition: StateTransition,
        candidates: list[StrategyCandidate],
        observation: FeatureSnapshot,
    ) -> CaptureAnchorInputs | None:
        if self._capture is None or self._capture.source_type is not EvidenceSource.FORWARD_PAPER:
            return None
        async with self._session_factory() as session:
            existing = await load_capture_anchor_for_event(session, event.event_id)
        if existing is not None:
            inputs = existing.formal_inputs()
            self._validate_anchor_precondition(inputs, event, precondition_state)
            return inputs

        if not self._capture.forward_admission_session_id:
            raise CaptureAdmissionRejected(
                "FORWARD_PAPER capture anchor requires explicit live-session admission proof"
            )

        anchor = self._pending_capture_anchors.get(event.event_id)
        if anchor is None:
            quote = (
                None if self._reference_quote_for is None else self._reference_quote_for(event.instrument_id)
            )
            anchor = build_capture_anchor(
                precondition_state=precondition_state,
                event=event,
                timeline=timeline,
                state=state,
                transition=transition,
                candidates=candidates,
                observation=observation,
                context=self._capture,
                reference_quote=quote,
            )
        if anchor is None:
            return None
        self._validate_anchor_precondition(anchor.formal_inputs(), event, precondition_state)
        self._pending_capture_anchors[event.event_id] = anchor
        logger.info("capture_anchor_attempt event_id=%s opportunity_id=%s", event.event_id, anchor.opportunity_id)
        try:
            async with self._session_factory() as session, session.begin():
                inputs = anchor.formal_inputs()
                if inputs.reference_bbo_observation is not None:
                    await record_bbo_observation(session, inputs.reference_bbo_observation)
                await append_capture_anchor(session, anchor)
        except BaseException:
            logger.exception("capture_anchor_failure event_id=%s opportunity_id=%s", event.event_id, anchor.opportunity_id)
            raise
        self._pending_capture_anchors.pop(event.event_id, None)
        logger.info("capture_anchor_admitted event_id=%s opportunity_id=%s", event.event_id, anchor.opportunity_id)
        return anchor.formal_inputs()

    async def persist(
        self,
        event: MarketEvent,
        timeline: SignalTimelineEvent,
        state: SymbolStateRecord,
        transition: StateTransition,
        candidates: list[StrategyCandidate],
        observation: FeatureSnapshot,
        *,
        precondition_state: SymbolStateRecord | None = None,
    ) -> bool:
        anchored = await self._admit_or_load_capture_anchor(
            precondition_state=precondition_state,
            event=event,
            timeline=timeline,
            state=state,
            transition=transition,
            candidates=candidates,
            observation=observation,
        )
        if anchored is not None:
            event = anchored.event
            timeline = anchored.timeline
            state = anchored.state
            transition = anchored.transition
            candidates = anchored.candidates
            observation = anchored.observation
        async with self._session_factory() as session, session.begin():
            if anchored is not None:
                await self._validate_durable_anchor_precondition(session, anchored)
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
                        anchored.reference_quote
                        if anchored is not None
                        else (
                            None
                            if self._reference_quote_for is None
                            else self._reference_quote_for(event.instrument_id)
                        )
                    ),
                )
        return True
