from __future__ import annotations

import asyncio
import itertools
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from marketpulse.clock import Clock
from marketpulse.market_data.models import (
    AuxiliaryContext,
    NormalizedBookTicker,
    NormalizedMarketEvent,
    NormalizedTrade,
)

from .models import (
    FeatureSnapshot,
    G2PersistResult,
    LifecycleAction,
    MarketEvent,
    SignalTimelineEvent,
    StateApplyResult,
    StateTransition,
    StrategyCandidate,
    SymbolStateRecord,
    deterministic_id,
)
from .rolling import RollingFeatureEngine
from .scanner import OpportunityScanner
from .state_machine import SymbolStateManager
from .strategy import StrategyEngine
from .timeline import SignalLifecycle

if TYPE_CHECKING:
    from marketpulse.advisory.ingress import AdvisoryIngress
    from marketpulse.edge.capture import ForwardAdmissionAuthority, ForwardAdmissionProof
    from marketpulse.edge.forward_service import ForwardPathRecorder


class G2Repository(Protocol):
    async def get_state(self, instrument_id: str) -> SymbolStateRecord | None: ...

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
        forward_admission_proof: ForwardAdmissionProof | None = None,
    ) -> G2PersistResult | bool: ...

    async def resume_capture_anchor(
        self, event: MarketEvent, precondition_state: SymbolStateRecord
    ) -> object | None: ...


@dataclass
class ApplyOutcome:
    event_id: str
    result: StateApplyResult
    persisted: bool
    state_version: int
    state: SymbolStateRecord
    transition: StateTransition | None = None


@dataclass
class _QueuedEvent:
    event: MarketEvent
    features: FeatureSnapshot
    lifecycle_action: LifecycleAction
    future: asyncio.Future[ApplyOutcome]
    forward_admission_proof: ForwardAdmissionProof | None = None


class EventRuntime:
    """Bounded async priority bus with finite workers and per-instrument serial execution."""

    def __init__(
        self,
        repository: G2Repository,
        state_manager: SymbolStateManager | None = None,
        strategy_engine: StrategyEngine | None = None,
        worker_count: int = 4,
        queue_capacity: int = 2048,
        dedupe_capacity: int = 8192,
        worker_exception_capacity: int = 128,
        advisory_ingress: AdvisoryIngress | None = None,
    ) -> None:
        if dedupe_capacity <= 0:
            raise ValueError("dedupe_capacity must be positive")
        if worker_exception_capacity <= 0:
            raise ValueError("worker_exception_capacity must be positive")
        self.repository = repository
        self.state_manager = state_manager or SymbolStateManager()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.worker_count = worker_count
        self.queue: asyncio.PriorityQueue[tuple[int, int, _QueuedEvent | None]] = (
            asyncio.PriorityQueue(maxsize=queue_capacity)
        )
        self._counter = itertools.count()
        self._workers: list[asyncio.Task[None]] = []
        self._locks: dict[str, asyncio.Lock] = {}
        self._dedupe: set[str] = set()
        self._dedupe_fifo: deque[str] = deque()
        self._dedupe_capacity = dedupe_capacity
        self._inflight: dict[str, asyncio.Future[ApplyOutcome]] = {}
        self._worker_exception_capacity = worker_exception_capacity
        self.worker_exceptions: deque[BaseException] = deque(maxlen=worker_exception_capacity)
        # Host-owned and optional: with no injected ingress the accepted G2 path
        # has no Advisory queue or post-commit work.
        self._advisory_ingress = advisory_ingress

    async def start(self) -> None:
        if not self._workers:
            self._workers = [
                asyncio.create_task(self._worker(index), name=f"g2-event-worker-{index}")
                for index in range(self.worker_count)
            ]

    async def stop(self) -> None:
        for _ in self._workers:
            await self.queue.put((101, next(self._counter), None))
        await self.queue.join()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def publish(
        self,
        event: MarketEvent,
        features: FeatureSnapshot,
        lifecycle_action: LifecycleAction = LifecycleAction.START,
        *,
        forward_admission_proof: ForwardAdmissionProof | None = None,
    ) -> ApplyOutcome:
        if event.event_id in self._dedupe:
            return ApplyOutcome(
                event.event_id,
                StateApplyResult.NO_CHANGE,
                False,
                self.state_manager.snapshot_for(event.instrument_id, event.symbol).state_version,
                self.state_manager.snapshot_for(event.instrument_id, event.symbol),
            )
        existing = self._inflight.get(event.event_id)
        if existing is not None:
            return await asyncio.shield(existing)
        future: asyncio.Future[ApplyOutcome] = asyncio.get_running_loop().create_future()
        self._inflight[event.event_id] = future
        queued = False
        try:
            await self.queue.put(
                (
                    -event.priority,
                    next(self._counter),
                    _QueuedEvent(
                        event, features, lifecycle_action, future, forward_admission_proof
                    ),
                )
            )
            queued = True
        except BaseException:
            if not queued and self._inflight.get(event.event_id) is future:
                self._inflight.pop(event.event_id, None)
                future.cancel()
            raise
        return await asyncio.shield(future)

    async def current_state(self, instrument_id: str, symbol: str) -> SymbolStateRecord:
        stored = await self.repository.get_state(instrument_id)
        if stored:
            return self.state_manager.hydrate(stored)
        return self.state_manager.snapshot_for(instrument_id, symbol)

    async def _worker(self, _: int) -> None:
        while True:
            _, _, queued = await self.queue.get()
            try:
                if queued is None:
                    return
                lock = self._locks.setdefault(queued.event.instrument_id, asyncio.Lock())
                async with lock:
                    outcome = await self._apply(
                        queued.event,
                        queued.features,
                        queued.lifecycle_action,
                        queued.forward_admission_proof,
                    )
                if outcome.persisted:
                    self._remember_deduped(queued.event.event_id)
                if not queued.future.done():
                    queued.future.set_result(outcome)
            except Exception as exc:  # noqa: BLE001 - propagate every worker failure to publisher and test harness
                self.worker_exceptions.append(exc)
                if queued is not None and not queued.future.done():
                    queued.future.set_exception(exc)
            finally:
                if queued is not None and self._inflight.get(queued.event.event_id) is queued.future:
                    self._inflight.pop(queued.event.event_id, None)
                self.queue.task_done()

    def _remember_deduped(self, event_id: str) -> None:
        if event_id in self._dedupe:
            return
        if len(self._dedupe) == self._dedupe_capacity:
            self._dedupe.remove(self._dedupe_fifo.popleft())
        self._dedupe.add(event_id)
        self._dedupe_fifo.append(event_id)

    async def _apply(
        self,
        event: MarketEvent,
        features: FeatureSnapshot,
        action: LifecycleAction,
        forward_admission_proof: ForwardAdmissionProof | None = None,
    ) -> ApplyOutcome:
        await self.current_state(event.instrument_id, event.symbol)
        precondition_state = self.state_manager.snapshot_for(event.instrument_id, event.symbol)
        state, transition = self.state_manager.prepare_apply(event, action)
        timeline = SignalTimelineEvent(
            timeline_id=deterministic_id("tl", event.event_id, action),
            event_id=event.event_id,
            symbol=event.symbol,
            instrument_id=event.instrument_id,
            signal_type=event.event_type,
            event_time=event.event_time,
            received_time=event.received_time,
            price=features.current_price,
            context=event.payload,
            strength=event.strength,
            lifecycle_action=action,
            symbol_state=state.state,
            state_version=state.state_version,
            config_version=event.config_version,
        )
        anchored = await self.repository.resume_capture_anchor(event, precondition_state)
        if anchored is not None:
            # A durable capture anchor is the only admissible source for retry.
            # It is deliberately checked before StrategyEngine so retry cannot
            # manufacture a new candidate timestamp or causal payload.
            event = anchored.event
            timeline = anchored.timeline
            state = anchored.state
            transition = anchored.transition
            candidates = anchored.candidates
            features = anchored.observation
        else:
            candidates = (
                self.strategy_engine.candidates(features, event, state.state_version)
                if transition.result in {StateApplyResult.APPLIED, StateApplyResult.NO_CHANGE}
                else []
            )
        persist_result = await self.repository.persist(
            event,
            timeline,
            state,
            transition,
            candidates,
            features,
            precondition_state=precondition_state,
            forward_admission_proof=forward_admission_proof,
        )
        persisted = bool(persist_result)
        if persisted:
            self.state_manager.commit(state)
            work_ref = getattr(persist_result, "advisory_work_ref", None)
            if work_ref is not None and self._advisory_ingress is not None:
                await self._advisory_ingress.post_commit_offer(work_ref)
        else:
            state = self.state_manager.snapshot_for(event.instrument_id, event.symbol)
        return ApplyOutcome(
            event.event_id,
            transition.result if persisted else StateApplyResult.NO_CHANGE,
            persisted,
            state.state_version,
            state.model_copy(deep=True),
            transition if persisted else None,
        )

    async def expire(self, features: FeatureSnapshot, now) -> ApplyOutcome | None:
        """Persist a reachable TTL expiry through the same per-symbol runtime fence."""
        lock = self._locks.setdefault(features.instrument_id, asyncio.Lock())
        async with lock:
            await self.current_state(features.instrument_id, features.symbol)
            prepared = self.state_manager.prepare_expire(
                features.instrument_id, now, features.market_type
            )
            if prepared is None:
                return None
            state, transition, event = prepared
            timeline = SignalTimelineEvent(
                timeline_id=deterministic_id("tl", event.event_id, LifecycleAction.NORMALIZED),
                event_id=event.event_id,
                symbol=event.symbol,
                instrument_id=event.instrument_id,
                signal_type=event.event_type,
                event_time=event.event_time,
                received_time=event.received_time,
                price=features.current_price,
                context={"reason": transition.reason},
                strength=event.strength,
                lifecycle_action=LifecycleAction.NORMALIZED,
                symbol_state=state.state,
                state_version=state.state_version,
                config_version=event.config_version,
            )
            persist_result = await self.repository.persist(
                event, timeline, state, transition, [], features
            )
            persisted = bool(persist_result)
            if persisted:
                self.state_manager.commit(state)
                self._remember_deduped(event.event_id)
                work_ref = getattr(persist_result, "advisory_work_ref", None)
                if work_ref is not None and self._advisory_ingress is not None:
                    await self._advisory_ingress.post_commit_offer(work_ref)
            else:
                state = self.state_manager.snapshot_for(event.instrument_id, event.symbol)
            return ApplyOutcome(
                event.event_id,
                transition.result if persisted else StateApplyResult.NO_CHANGE,
                persisted,
                state.state_version,
                state.model_copy(deep=True),
                transition if persisted else None,
            )

    # ------------------------------------------------------------------ read-only telemetry
    # Added for the Integrated Runtime Host's bounded observation surface. These accessors
    # only report accepted G2 state; they never mutate it and never change G2 business or
    # state-machine semantics.

    @property
    def worker_tasks(self) -> tuple[asyncio.Task[None], ...]:
        """The exact accepted finite worker tasks, so their owner can verify liveness."""
        return tuple(self._workers)

    @property
    def live_worker_count(self) -> int:
        return sum(1 for task in self._workers if not task.done())

    @property
    def done_worker_count(self) -> int:
        return sum(1 for task in self._workers if task.done())

    @property
    def queue_size(self) -> int:
        return self.queue.qsize()

    @property
    def queue_capacity(self) -> int:
        return self.queue.maxsize

    @property
    def inflight_size(self) -> int:
        return len(self._inflight)

    @property
    def dedupe_size(self) -> int:
        return len(self._dedupe)

    @property
    def dedupe_capacity(self) -> int:
        return self._dedupe_capacity

    @property
    def worker_exception_size(self) -> int:
        return len(self.worker_exceptions)

    @property
    def worker_exception_capacity(self) -> int:
        return self._worker_exception_capacity

    def telemetry_snapshot(self) -> dict[str, object]:
        return {
            "worker_count_configured": self.worker_count,
            "worker_count_live": self.live_worker_count,
            "worker_count_done": self.done_worker_count,
            "queue_size": self.queue_size,
            "queue_capacity": self.queue_capacity,
            "inflight": self.inflight_size,
            "dedupe_size": self.dedupe_size,
            "dedupe_capacity": self.dedupe_capacity,
            "worker_exception_size": self.worker_exception_size,
            "worker_exception_capacity": self.worker_exception_capacity,
        }


class ScannerPipeline:
    """Connect normalized G1 events to rolling features, scanner facts, and G2 runtime."""

    def __init__(
        self,
        scanner: OpportunityScanner,
        runtime: EventRuntime,
        rolling: RollingFeatureEngine | None = None,
        clock: Clock | None = None,
        trade_dedupe_capacity: int = 8192,
        forward_admission_authority: ForwardAdmissionAuthority | None = None,
        forward_path_recorder: ForwardPathRecorder | None = None,
    ) -> None:
        if trade_dedupe_capacity <= 0:
            raise ValueError("trade_dedupe_capacity must be positive")
        self.scanner = scanner
        self.runtime = runtime
        self.rolling = rolling or RollingFeatureEngine()
        self.clock = clock or scanner.clock
        self.lifecycle = SignalLifecycle()
        # The forward admission issuer belongs to this live-ingress boundary. It is
        # deliberately optional: a historical replay pipeline never receives one,
        # so it can never mint a Forward admission proof.
        self.forward_admission_authority = forward_admission_authority
        # SE-02C Forward path capture hangs off the same live ingress and is likewise
        # opt-in: with no recorder configured the accepted ingest path is unchanged,
        # and a historical replay pipeline cannot archive a Forward BBO path.
        self.forward_path_recorder = forward_path_recorder
        self._btc_returns: dict[str, float] = {}
        self._trade_dedupe: set[tuple[str, str, str, str]] = set()
        self._trade_dedupe_fifo: deque[tuple[str, str, str, str]] = deque()
        self._trade_dedupe_capacity = trade_dedupe_capacity
        self.last_detected_events: tuple[MarketEvent, ...] = ()
        # Read-only replay handoff: the exact feature fact already calculated for this frame.
        self.last_features: FeatureSnapshot | None = None

    async def ingest(
        self, market_event: NormalizedMarketEvent, auxiliary: AuxiliaryContext | None = None
    ) -> list[ApplyOutcome]:
        trade_key = self._trade_key(market_event)
        if trade_key is not None and trade_key in self._trade_dedupe:
            self.last_detected_events = ()
            return []
        # SE-02C: archive the normalized BBO of this frame while a Forward evidence
        # window covers the instrument. With no recorder wired this is a no-op and
        # the accepted ingest path is byte-for-byte unchanged.
        await self.record_forward_path(market_event)
        btc_return = self._btc_returns.get("BTC-USDT")
        working_rolling = self.rolling.copy()
        features = working_rolling.ingest(
            market_event, auxiliary=auxiliary, btc_return=btc_return
        )
        expiry = await self.runtime.expire(features, self.clock.now())
        events = self.scanner.scan(features, received_time=self.clock.now(), state_version=0)
        detected_types = {event.event_type for event in events}
        normalized_types = sorted(
            self.lifecycle.active_types(features.instrument_id) - detected_types,
            key=lambda event_type: event_type.value,
        )
        for active_type in normalized_types:
            previous_event_id = self.lifecycle.preview_normalize(
                features.instrument_id, active_type
            )
            if previous_event_id:
                now = self.clock.now()
                events.append(
                    MarketEvent(
                        event_id=deterministic_id(
                            "normalized", previous_event_id, market_event.event_time.isoformat()
                        ),
                        symbol=features.symbol,
                        instrument_id=features.instrument_id,
                        market_type=features.market_type,
                        event_type=active_type,
                        event_time=market_event.event_time,
                        received_time=now,
                        source="g2.signal_lifecycle",
                        strength=0,
                        priority=0,
                        state_version=0,
                        config_version=self.scanner.config.version,
                        payload={"normalized_from_event_id": previous_event_id},
                    )
                )
        outcomes = [expiry] if expiry is not None else []
        for event in events:
            action = (
                LifecycleAction.NORMALIZED
                if event.source == "g2.signal_lifecycle"
                else self.lifecycle.preview_action(event)
            )
            if action is None:
                continue
            current_version = (
                await self.runtime.current_state(features.instrument_id, features.symbol)
            ).state_version
            versioned_event = event.model_copy(update={"state_version": current_version})
            outcome = await self.runtime.publish(
                versioned_event,
                features,
                action,
                forward_admission_proof=self.issue_admission_proof(market_event, versioned_event),
            )
            outcomes.append(outcome)
            if outcome.persisted:
                if action is LifecycleAction.NORMALIZED:
                    self.lifecycle.commit_normalize(event.instrument_id, event.event_type)
                else:
                    self.lifecycle.commit_action(event, action)
        self.rolling.commit(working_rolling)
        self.last_detected_events = tuple(events)
        self.last_features = features
        if features.symbol == "BTC-USDT" and features.short_return is not None:
            self._btc_returns["BTC-USDT"] = features.short_return
        if trade_key is not None:
            self._remember_trade(trade_key)
        return outcomes

    def issue_admission_proof(
        self, source_event: NormalizedMarketEvent, event: MarketEvent
    ) -> ForwardAdmissionProof | None:
        """Mint the live-ingress proof for the exact event this ``ingest`` produced.

        The proof binds the ``NormalizedMarketEvent`` this ``ingest`` call received
        -- so a lifecycle-derived event carries the same causal input identity --
        and ``None`` means the input predates this live session. That ``None``
        fails closed downstream: a redelivered old input simply produces no Forward
        anchor instead of being re-stamped as new live Forward input.
        """

        if self.forward_admission_authority is None:
            return None
        return self.forward_admission_authority.issue(source_event=source_event, event=event)

    async def record_forward_path(self, market_event: NormalizedMarketEvent) -> str | None:
        """Offer one normalized ingress frame to the SE-02C Forward path recorder.

        Only a normalized L1 BBO frame can become a Forward path observation, and
        only when this pipeline was actually given a recorder -- a historical
        replay pipeline never is, so it cannot archive a Forward BBO path.
        """

        if self.forward_path_recorder is None or not isinstance(
            market_event, NormalizedBookTicker
        ):
            return None
        return await self.forward_path_recorder.record_event(market_event)

    def _remember_trade(self, trade_key: tuple[str, str, str, str]) -> None:
        """Remember successful inputs in FIFO arrival order without refreshing duplicate hits."""
        if len(self._trade_dedupe) == self._trade_dedupe_capacity:
            self._trade_dedupe.remove(self._trade_dedupe_fifo.popleft())
        self._trade_dedupe.add(trade_key)
        self._trade_dedupe_fifo.append(trade_key)

    @staticmethod
    def _trade_key(event: NormalizedMarketEvent) -> tuple[str, str, str, str] | None:
        if not isinstance(event, NormalizedTrade):
            return None
        return (event.exchange, event.instrument_id, event.market_type.value, event.trade_id)

    # ------------------------------------------------------------------ read-only telemetry

    @property
    def trade_dedupe_size(self) -> int:
        return len(self._trade_dedupe)

    @property
    def trade_dedupe_capacity(self) -> int:
        return self._trade_dedupe_capacity

    def telemetry_snapshot(self) -> dict[str, object]:
        """Bounded retention sizes only; no unbounded series and no business mutation."""
        return {
            "trade_dedupe_size": self.trade_dedupe_size,
            "trade_dedupe_capacity": self.trade_dedupe_capacity,
            "btc_return_cache_size": len(self._btc_returns),
            "last_detected_event_count": len(self.last_detected_events),
        }
