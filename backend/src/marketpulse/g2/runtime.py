from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass
from typing import Protocol

from marketpulse.clock import Clock
from marketpulse.market_data.models import AuxiliaryContext, NormalizedMarketEvent

from .models import (
    FeatureSnapshot,
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
    ) -> bool: ...


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


class EventRuntime:
    """Bounded async priority bus with finite workers and per-instrument serial execution."""

    def __init__(
        self,
        repository: G2Repository,
        state_manager: SymbolStateManager | None = None,
        strategy_engine: StrategyEngine | None = None,
        worker_count: int = 4,
        queue_capacity: int = 2048,
    ) -> None:
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
        self.worker_exceptions: list[BaseException] = []

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
    ) -> ApplyOutcome:
        if event.event_id in self._dedupe:
            return ApplyOutcome(
                event.event_id,
                StateApplyResult.NO_CHANGE,
                False,
                self.state_manager.current(event).state_version,
                self.state_manager.current(event).model_copy(deep=True),
            )
        self._dedupe.add(event.event_id)
        future: asyncio.Future[ApplyOutcome] = asyncio.get_running_loop().create_future()
        await self.queue.put(
            (
                -event.priority,
                next(self._counter),
                _QueuedEvent(event, features, lifecycle_action, future),
            )
        )
        return await future

    async def current_state(self, instrument_id: str, symbol: str) -> SymbolStateRecord:
        stored = await self.repository.get_state(instrument_id)
        if stored:
            return self.state_manager.hydrate(stored)
        return self.state_manager.state_for(instrument_id, symbol)

    async def _worker(self, _: int) -> None:
        while True:
            _, _, queued = await self.queue.get()
            try:
                if queued is None:
                    return
                lock = self._locks.setdefault(queued.event.instrument_id, asyncio.Lock())
                async with lock:
                    outcome = await self._apply(
                        queued.event, queued.features, queued.lifecycle_action
                    )
                queued.future.set_result(outcome)
            except Exception as exc:  # noqa: BLE001 - propagate every worker failure to publisher and test harness
                self.worker_exceptions.append(exc)
                if queued is not None and not queued.future.done():
                    queued.future.set_exception(exc)
            finally:
                self.queue.task_done()

    async def _apply(
        self, event: MarketEvent, features: FeatureSnapshot, action: LifecycleAction
    ) -> ApplyOutcome:
        await self.current_state(event.instrument_id, event.symbol)
        state, transition = self.state_manager.apply(event, action)
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
        candidates = (
            self.strategy_engine.candidates(features, event, state.state_version)
            if transition.result in {StateApplyResult.APPLIED, StateApplyResult.NO_CHANGE}
            else []
        )
        persisted = await self.repository.persist(
            event, timeline, state, transition, candidates, features
        )
        return ApplyOutcome(
            event.event_id,
            transition.result,
            persisted,
            state.state_version,
            state.model_copy(deep=True),
            transition,
        )


class ScannerPipeline:
    """Connect normalized G1 events to rolling features, scanner facts, and G2 runtime."""

    def __init__(
        self,
        scanner: OpportunityScanner,
        runtime: EventRuntime,
        rolling: RollingFeatureEngine | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.scanner = scanner
        self.runtime = runtime
        self.rolling = rolling or RollingFeatureEngine()
        self.clock = clock or scanner.clock
        self.lifecycle = SignalLifecycle()
        self._btc_returns: dict[str, float] = {}
        self.last_detected_events: tuple[MarketEvent, ...] = ()
        # Read-only replay handoff: the exact feature fact already calculated for this frame.
        self.last_features: FeatureSnapshot | None = None

    async def ingest(
        self, market_event: NormalizedMarketEvent, auxiliary: AuxiliaryContext | None = None
    ) -> list[ApplyOutcome]:
        btc_return = self._btc_returns.get("BTC-USDT")
        features = self.rolling.ingest(market_event, auxiliary=auxiliary, btc_return=btc_return)
        self.last_features = features
        if features.symbol == "BTC-USDT" and features.short_return is not None:
            self._btc_returns["BTC-USDT"] = features.short_return
        events = self.scanner.scan(features, received_time=self.clock.now(), state_version=0)
        detected_types = {event.event_type for event in events}
        for active_type in self.lifecycle.active_types(features.instrument_id) - detected_types:
            previous_event_id = self.lifecycle.normalize(features.instrument_id, active_type)
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
        self.last_detected_events = tuple(events)
        outcomes = []
        for event in events:
            action = (
                LifecycleAction.NORMALIZED
                if event.source == "g2.signal_lifecycle"
                else self.lifecycle.action_for(event)
            )
            if action is None:
                continue
            current_version = (
                await self.runtime.current_state(features.instrument_id, features.symbol)
            ).state_version
            versioned_event = event.model_copy(update={"state_version": current_version})
            outcome = await self.runtime.publish(versioned_event, features, action)
            outcomes.append(outcome)
        return outcomes
