from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from marketpulse.clock import ReplayClock
from marketpulse.g2.models import DirectionBias, LifecycleAction, StateTransition, StrategyCandidate
from marketpulse.g2.repository import InMemoryG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner, ScannerConfig
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.market_data.models import AuxiliaryContext, NormalizedMarketEvent


class ReplayOrderingError(ValueError):
    """Raised when replay input cannot preserve observed processing order."""


@dataclass(frozen=True)
class ReplayFrame:
    ordinal: int
    market_event: NormalizedMarketEvent
    auxiliary: AuxiliaryContext | None = None

    @property
    def processing_time(self) -> datetime:
        received_time = self.market_event.received_time
        if received_time.tzinfo is None:
            raise ReplayOrderingError("ReplayFrame.received_time must be timezone-aware")
        return received_time.astimezone(UTC)


class ReplayEventSource:
    """An ordered, stable view of already-normalized replay input."""

    def __init__(self, frames: Iterable[ReplayFrame]) -> None:
        self.frames = tuple(frames)
        previous_time: datetime | None = None
        for frame in self.frames:
            processing_time = frame.processing_time
            if previous_time is not None and processing_time < previous_time:
                raise ReplayOrderingError(
                    "received_time must be non-decreasing in replay input "
                    f"(ordinal={frame.ordinal})"
                )
            previous_time = processing_time


@dataclass(frozen=True)
class ReplayEventTrace:
    event_id: str
    timeline_id: str
    lifecycle_action: LifecycleAction
    transition_id: str
    transition_from: str
    transition_to: str
    state_version: int
    candidate_ids: tuple[str, ...]
    candidate_created_at: tuple[datetime, ...]
    candidate_applicable: tuple[bool, ...]
    candidate_direction_bias: tuple[DirectionBias, ...]

    def canonical(self) -> tuple[object, ...]:
        return (
            self.event_id,
            self.timeline_id,
            self.lifecycle_action.value,
            self.transition_id,
            self.transition_from,
            self.transition_to,
            self.state_version,
            self.candidate_ids,
            tuple(item.isoformat() for item in self.candidate_created_at),
            self.candidate_applicable,
            tuple(item.value for item in self.candidate_direction_bias),
        )


@dataclass(frozen=True)
class ReplayFrameTrace:
    input_ordinal: int
    processing_time: datetime
    instrument_id: str
    detected_event_ids: tuple[str, ...]
    events: tuple[ReplayEventTrace, ...]

    def canonical(self) -> tuple[object, ...]:
        return (
            self.input_ordinal,
            self.processing_time.isoformat(),
            self.instrument_id,
            self.detected_event_ids,
            tuple(event.canonical() for event in self.events),
        )


@dataclass(frozen=True)
class ReplayTrace:
    frames: tuple[ReplayFrameTrace, ...]

    def canonical(self) -> tuple[object, ...]:
        return tuple(frame.canonical() for frame in self.frames)


@dataclass(frozen=True)
class ReplayResult:
    trace: ReplayTrace
    repository: InMemoryG2Repository


class ReplayG2Runner:
    """Feed normalized history through the existing G2 runtime using ReplayClock."""

    def __init__(self, scanner_config: ScannerConfig | None = None) -> None:
        self.scanner_config = scanner_config or ScannerConfig()

    async def run(self, source: ReplayEventSource | Iterable[ReplayFrame]) -> ReplayResult:
        if not isinstance(source, ReplayEventSource):
            source = ReplayEventSource(source)
        if not source.frames:
            raise ValueError("replay source must contain at least one frame")

        clock = ReplayClock(source.frames[0].processing_time)
        repository = InMemoryG2Repository()
        runtime = EventRuntime(
            repository,
            strategy_engine=StrategyEngine(clock),
            worker_count=1,
        )
        pipeline = ScannerPipeline(
            OpportunityScanner(self.scanner_config, clock),
            runtime,
            clock=clock,
        )
        traces: list[ReplayFrameTrace] = []
        await runtime.start()
        try:
            for frame in source.frames:
                clock.advance_to(frame.processing_time)
                if clock.now() != frame.processing_time:
                    raise RuntimeError("ReplayClock did not advance to the frame received_time")
                timeline_offset = len(repository.timeline)
                candidate_offset = len(repository.candidates)
                await pipeline.ingest(frame.market_event, auxiliary=frame.auxiliary)
                timelines = repository.timeline[timeline_offset:]
                candidates = repository.candidates[candidate_offset:]
                traces.append(
                    ReplayFrameTrace(
                        input_ordinal=frame.ordinal,
                        processing_time=clock.now(),
                        instrument_id=frame.market_event.instrument_id,
                        detected_event_ids=tuple(event.event_id for event in pipeline.last_detected_events),
                        events=tuple(
                            self._event_trace(
                                timeline.lifecycle_action,
                                transition,
                                timeline.timeline_id,
                                candidates,
                            )
                            for timeline, transition in zip(timelines, repository.transitions[timeline_offset:], strict=True)
                        ),
                    )
                )
        finally:
            await runtime.stop()
        if runtime.worker_exceptions:
            raise runtime.worker_exceptions[0]
        return ReplayResult(trace=ReplayTrace(tuple(traces)), repository=repository)

    @staticmethod
    def _event_trace(
        lifecycle_action: LifecycleAction,
        transition: StateTransition,
        timeline_id: str,
        candidates: list[StrategyCandidate],
    ) -> ReplayEventTrace:
        event_candidates = [item for item in candidates if item.event_id == transition.event_id]
        return ReplayEventTrace(
            event_id=transition.event_id,
            timeline_id=timeline_id,
            lifecycle_action=lifecycle_action,
            transition_id=transition.transition_id,
            transition_from=transition.from_state.value,
            transition_to=transition.to_state.value,
            state_version=transition.state_version,
            candidate_ids=tuple(item.candidate_id for item in event_candidates),
            candidate_created_at=tuple(item.created_at for item in event_candidates),
            candidate_applicable=tuple(item.applicable for item in event_candidates),
            candidate_direction_bias=tuple(item.direction_bias for item in event_candidates),
        )
