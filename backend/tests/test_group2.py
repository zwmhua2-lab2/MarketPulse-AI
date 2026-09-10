import asyncio
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    DerivedObservationRecord,
    MarketEventRecord,
    SignalTimelineRecord,
    StateTransitionRecord,
    StrategyCandidateRecord,
    SymbolStateStore,
)
from marketpulse.g2.models import (
    EventType,
    FeatureSnapshot,
    LifecycleAction,
    MarketEvent,
    MarketStructure,
    StateApplyResult,
    SymbolState,
    Zone,
)
from marketpulse.g2.repository import InMemoryG2Repository, PostgresG2Repository
from marketpulse.g2.rolling import RollingFeatureEngine
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner, ScannerConfig
from marketpulse.g2.state_machine import StateMachineConfig, SymbolStateManager
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.g2.timeline import SignalLifecycle
from marketpulse.market_data.models import MarketType, NormalizedTrade
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 9, 4, 12, tzinfo=UTC)


def _features(at: datetime = NOW, price: float = 101) -> FeatureSnapshot:
    return FeatureSnapshot(instrument_id="SOL-USDT", symbol="SOL-USDT", market_type=MarketType.SPOT, event_time=at, current_price=price, short_return=0.01, buy_sell_imbalance=0.8)


def _event(kind: EventType, version: int, at: datetime = NOW, strength: float = 0.8, event_id: str | None = None) -> MarketEvent:
    return MarketEvent(event_id=event_id or f"event-{kind}-{version}-{at.timestamp()}", symbol="SOL-USDT", instrument_id="SOL-USDT", market_type=MarketType.SPOT, event_type=kind, event_time=at, received_time=at, source="fixture", strength=strength, priority=80, state_version=version, config_version="fixture", payload={"current_price": 101})


def _trade(trade_id: str, at: datetime, *, instrument_id: str = "SOL-USDT") -> NormalizedTrade:
    base_asset = instrument_id.split("-")[0]
    return NormalizedTrade(
        base_asset=base_asset,
        quote_asset="USDT",
        market_type=MarketType.SPOT,
        instrument_id=instrument_id,
        event_time=at,
        received_time=at,
        source="fixture",
        trade_id=trade_id,
        price=100,
        quantity=1,
        side="buy",
    )


def _repository_truth(repository: InMemoryG2Repository) -> dict[str, object]:
    return {
        "states": {
            key: value.model_dump(mode="json") for key, value in sorted(repository.states.items())
        },
        "events": [item.model_dump(mode="json") for item in repository.events.values()],
        "timeline": [item.model_dump(mode="json") for item in repository.timeline],
        "transitions": [item.model_dump(mode="json") for item in repository.transitions],
        "candidates": [item.model_dump(mode="json") for item in repository.candidates],
    }


def test_rolling_features_are_incremental_and_scanner_emits_market_facts_only():
    engine = RollingFeatureEngine()
    snapshot = None
    for offset, price in enumerate([100, 100.1, 100.3, 101, 102, 104]):
        event = NormalizedTrade(base_asset="SOL", quote_asset="USDT", market_type=MarketType.SPOT, instrument_id="SOL-USDT", event_time=NOW + timedelta(seconds=offset), received_time=NOW + timedelta(seconds=offset), source="fixture", trade_id=str(offset), price=price, quantity=1 + offset, side="buy")
        snapshot = engine.ingest(event)
    assert snapshot and snapshot.current_price == 104
    assert snapshot.short_return and snapshot.short_return > 0
    events = OpportunityScanner(ScannerConfig(price_acceleration_threshold=0.0001, flow_imbalance_threshold=0.1)).scan(snapshot)
    assert events
    assert all(item.event_type.value not in {"BUY", "SELL", "OPEN_LONG", "OPEN_SHORT"} for item in events)


def test_state_machine_positive_evolution_late_event_ttl_and_cooldown():
    manager = SymbolStateManager(StateMachineConfig(watch_ttl=timedelta(minutes=1), cooldown=timedelta(minutes=2)))
    _, first = manager.apply(_event(EventType.VOLUME_ANOMALY, 0), LifecycleAction.START)
    _, second = manager.apply(_event(EventType.FLOW_IMBALANCE, 1, NOW + timedelta(seconds=1)), LifecycleAction.STRENGTHENED)
    _, third = manager.apply(_event(EventType.BREAKOUT, 2, NOW + timedelta(seconds=2)), LifecycleAction.STRENGTHENED)
    assert (first.to_state, second.to_state, third.to_state) == (SymbolState.DETECTED, SymbolState.WATCHING, SymbolState.SETUP)
    _, late = manager.apply(_event(EventType.BREAKOUT, 3, NOW + timedelta(seconds=1)), LifecycleAction.START)
    assert late.result is StateApplyResult.REJECT_LATE_EVENT
    _, invalidated = manager.apply(_event(EventType.FAILED_BREAKOUT, 3, NOW + timedelta(seconds=3)), LifecycleAction.NORMALIZED)
    assert invalidated.to_state is SymbolState.WATCHING
    expiry = manager.expire("SOL-USDT", NOW + timedelta(minutes=2))
    assert expiry and expiry.to_state is SymbolState.IDLE
    _, cooldown = manager.apply(_event(EventType.VOLUME_ANOMALY, 5, NOW + timedelta(minutes=2, seconds=1), strength=0.5), LifecycleAction.START)
    assert cooldown.result is StateApplyResult.REJECT_COOLDOWN
    _, stale_operation = manager.apply(_event(EventType.VOLUME_ANOMALY, 999, NOW + timedelta(minutes=5)), LifecycleAction.START)
    assert stale_operation.result is StateApplyResult.REJECT_STALE_OPERATION


def test_signal_lifecycle_suppresses_duplicate_noise():
    lifecycle = SignalLifecycle(strength_delta=0.1)
    event = _event(EventType.VOLUME_ANOMALY, 0, strength=0.5)
    assert lifecycle.action_for(event) is LifecycleAction.START
    assert lifecycle.action_for(event.model_copy(update={"event_id": "near-duplicate", "strength": 0.55})) is None
    assert lifecycle.action_for(event.model_copy(update={"event_id": "stronger", "strength": 0.7})) is LifecycleAction.STRENGTHENED
    assert lifecycle.normalize("SOL-USDT", EventType.VOLUME_ANOMALY) == "stronger"


def test_v1_strategies_emit_parallel_candidates_for_positive_and_failed_breakout():
    retest = Zone(lower=100, upper=101, kind="RESISTANCE", observed_at=NOW)
    features = _features().model_copy(update={"structure": MarketStructure(breakout_level=100, range_upper=100, retest_area=retest)})
    positive = StrategyEngine().candidates(features, _event(EventType.BREAKOUT, 0), 1)
    assert next(item for item in positive if item.strategy_id == "BREAKOUT_RETEST").applicable
    failed_features = features.model_copy(update={"buy_sell_imbalance": -0.8})
    failed = StrategyEngine().candidates(failed_features, _event(EventType.FAILED_BREAKOUT, 0), 1)
    assert next(item for item in failed if item.strategy_id == "LIQUIDITY_SWEEP_REVERSAL").applicable


def test_runtime_dedupes_reconnect_event_and_keeps_same_symbol_serial():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=2)
        await runtime.start()
        first = _event(EventType.VOLUME_ANOMALY, 0, event_id="reconnect-stable-id")
        first_outcome = await runtime.publish(first, _features())
        duplicate = await runtime.publish(first, _features())
        second = _event(EventType.BREAKOUT, 1, NOW + timedelta(seconds=1), event_id="same-symbol-next")
        second_outcome = await runtime.publish(second, _features(NOW + timedelta(seconds=1)))
        await runtime.stop()
        return repository, runtime, first_outcome, duplicate, second_outcome

    repository, runtime, first, duplicate, second = asyncio.run(scenario())
    assert first.persisted and not duplicate.persisted and second.persisted
    assert len(repository.events) == 2 and len(repository.timeline) == 2
    assert repository.states["SOL-USDT"].state is SymbolState.SETUP
    assert not runtime.worker_exceptions


def test_same_symbol_concurrent_priority_application_remains_legal():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=2)
        first = _event(EventType.VOLUME_ANOMALY, 0, event_id="same-symbol-first").model_copy(update={"priority": 90})
        second = _event(EventType.BREAKOUT, 1, NOW + timedelta(seconds=1), event_id="same-symbol-second").model_copy(update={"priority": 80})
        first_task = asyncio.create_task(runtime.publish(first, _features()))
        second_task = asyncio.create_task(runtime.publish(second, _features(NOW + timedelta(seconds=1))))
        await asyncio.sleep(0)
        await runtime.start()
        results = await asyncio.gather(first_task, second_task)
        await runtime.stop()
        return repository, runtime, results

    repository, runtime, results = asyncio.run(scenario())
    assert [result.result for result in results] == [StateApplyResult.APPLIED, StateApplyResult.APPLIED]
    assert repository.states["SOL-USDT"].state is SymbolState.SETUP
    assert not runtime.worker_exceptions


def test_different_symbols_process_without_global_state_conflict():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=3)
        await runtime.start()
        sol = _event(EventType.VOLUME_ANOMALY, 0, event_id="sol")
        btc = sol.model_copy(update={"event_id": "btc", "instrument_id": "BTC-USDT", "symbol": "BTC-USDT"})
        results = await asyncio.gather(runtime.publish(sol, _features()), runtime.publish(btc, _features().model_copy(update={"instrument_id": "BTC-USDT", "symbol": "BTC-USDT"})))
        await runtime.stop()
        return repository, results

    repository, results = asyncio.run(scenario())
    assert all(result.persisted for result in results)
    assert set(repository.states) == {"SOL-USDT", "BTC-USDT"}


def test_hundred_symbol_runtime_has_bounded_worker_pool_and_drains_queue():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=4, queue_capacity=128)
        await runtime.start()
        tasks = []
        for number in range(100):
            instrument_id = f"ASSET{number}-USDT"
            event = _event(EventType.VOLUME_ANOMALY, 0, event_id=f"hundred-{number}").model_copy(update={"instrument_id": instrument_id, "symbol": instrument_id})
            features = _features().model_copy(update={"instrument_id": instrument_id, "symbol": instrument_id})
            tasks.append(asyncio.create_task(runtime.publish(event, features)))
        results = await asyncio.gather(*tasks)
        queue_size = runtime.queue.qsize()
        worker_count = len(runtime._workers)
        await runtime.stop()
        return runtime, results, queue_size, worker_count

    runtime, results, queue_size, worker_count = asyncio.run(scenario())
    assert len(results) == 100 and all(result.persisted for result in results)
    assert queue_size == 0 and worker_count == 4 and not runtime.worker_exceptions


def test_normalized_market_data_reaches_scanner_timeline_state_and_strategy():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository)
        pipeline = ScannerPipeline(OpportunityScanner(ScannerConfig(flow_imbalance_threshold=0.1)), runtime)
        await runtime.start()
        event = NormalizedTrade(base_asset="ETH", quote_asset="USDT", market_type=MarketType.SPOT, instrument_id="ETH-USDT", event_time=NOW, received_time=NOW, source="fixture", trade_id="one", price=3_000, quantity=10, side="buy")
        outcomes = await pipeline.ingest(event)
        await runtime.stop()
        return repository, outcomes

    repository, outcomes = asyncio.run(scenario())
    assert outcomes and outcomes[0].persisted
    assert len(repository.events) == len(repository.timeline) == len(outcomes)
    assert repository.candidates and all(candidate.direction_bias.value in {"BULLISH", "BEARISH", "NEUTRAL"} for candidate in repository.candidates)


def test_pipeline_normalizes_active_lifecycle_types_in_stable_event_type_order():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=1)
        pipeline = ScannerPipeline(OpportunityScanner(), runtime)
        pipeline.scanner.scan = lambda *_args, **_kwargs: []
        for event_type in (EventType.VOLUME_ANOMALY, EventType.BREAKOUT, EventType.FLOW_IMBALANCE):
            assert pipeline.lifecycle.action_for(_event(event_type, 0)) is LifecycleAction.START
        await runtime.start()
        outcomes = await pipeline.ingest(
            NormalizedTrade(
                base_asset="SOL",
                quote_asset="USDT",
                market_type=MarketType.SPOT,
                instrument_id="SOL-USDT",
                event_time=NOW + timedelta(seconds=1),
                received_time=NOW + timedelta(seconds=1),
                source="fixture",
                trade_id="normalization-order",
                price=101,
                quantity=1,
                side="buy",
            )
        )
        await runtime.stop()
        return pipeline, outcomes

    pipeline, outcomes = asyncio.run(scenario())
    normalized = [
        event.event_type for event in pipeline.last_detected_events if event.source == "g2.signal_lifecycle"
    ]
    assert normalized == sorted(normalized, key=lambda event_type: event_type.value)
    assert [outcome.transition.reason for outcome in outcomes] == [
        "already_idle",
        "already_idle",
        "already_idle",
    ]


def test_pipeline_reaches_and_persists_ttl_expiry_before_next_input():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(
            repository,
            state_manager=SymbolStateManager(
                StateMachineConfig(watch_ttl=timedelta(minutes=1))
            ),
            worker_count=1,
        )
        await runtime.start()
        first = await runtime.publish(_event(EventType.VOLUME_ANOMALY, 0), _features())
        second = await runtime.publish(
            _event(EventType.FLOW_IMBALANCE, 1, NOW + timedelta(seconds=1)),
            _features(NOW + timedelta(seconds=1)),
        )
        clock = ReplayClock(NOW + timedelta(minutes=2))
        pipeline = ScannerPipeline(OpportunityScanner(clock=clock), runtime, clock=clock)
        pipeline.scanner.scan = lambda *_args, **_kwargs: []
        outcomes = await pipeline.ingest(
            NormalizedTrade(
                base_asset="SOL",
                quote_asset="USDT",
                market_type=MarketType.SPOT,
                instrument_id="SOL-USDT",
                event_time=clock.now(),
                received_time=clock.now(),
                source="fixture",
                trade_id="ttl-reachability",
                price=100,
                quantity=1,
                side="buy",
            )
        )
        await runtime.stop()
        return repository, first, second, outcomes

    repository, first, second, outcomes = asyncio.run(scenario())
    assert first.persisted and second.persisted
    assert len(outcomes) == 1
    expiry = outcomes[0]
    assert expiry.persisted and expiry.transition is not None
    assert expiry.transition.reason == "watch_ttl_expired"
    assert repository.events[expiry.event_id].source == "g2.state_ttl"
    assert repository.timeline[-1].lifecycle_action is LifecycleAction.NORMALIZED
    assert repository.states["SOL-USDT"].state is SymbolState.IDLE


def test_duplicate_normalized_trade_does_not_mutate_rolling_state_twice():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=1)
        pipeline = ScannerPipeline(OpportunityScanner(), runtime)
        pipeline.scanner.scan = lambda *_args, **_kwargs: []
        trade = NormalizedTrade(
            base_asset="SOL",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="SOL-USDT",
            event_time=NOW,
            received_time=NOW,
            source="fixture",
            trade_id="duplicate-trade",
            price=100,
            quantity=2,
            side="buy",
        )
        await runtime.start()
        first = await pipeline.ingest(trade)
        second = await pipeline.ingest(trade)
        await runtime.stop()
        return pipeline, first, second

    pipeline, first, second = asyncio.run(scenario())
    assert first == [] and second == []
    assert len(pipeline.rolling._states["SOL-USDT"].trades) == 1


def test_runtime_failure_does_not_commit_state_or_dedupe_and_retry_succeeds():
    class FailOnceRepository(InMemoryG2Repository):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def persist(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("injected persist failure")
            return await super().persist(*args, **kwargs)

    async def scenario():
        repository = FailOnceRepository()
        runtime = EventRuntime(repository, worker_count=1)
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="retry-after-failure")
        await runtime.start()
        with pytest.raises(RuntimeError, match="injected persist failure"):
            await runtime.publish(event, _features())
        failed_state = runtime.state_manager.snapshot_for(event.instrument_id, event.symbol)
        dedupe_after_failure = set(runtime._dedupe)
        retried = await runtime.publish(event, _features())
        await runtime.stop()
        return repository, runtime, failed_state, dedupe_after_failure, retried

    repository, runtime, failed_state, dedupe_after_failure, retried = asyncio.run(scenario())
    assert failed_state.state is SymbolState.IDLE and failed_state.state_version == 0
    assert "retry-after-failure" not in dedupe_after_failure
    assert not runtime._inflight
    assert retried.persisted and retried.state.state is SymbolState.DETECTED
    assert repository.calls == 2 and set(repository.events) == {"retry-after-failure"}


def test_runtime_rejected_persistence_does_not_commit_state_or_dedupe():
    class RejectOnceRepository(InMemoryG2Repository):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def persist(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return False
            return await super().persist(*args, **kwargs)

    async def scenario():
        repository = RejectOnceRepository()
        runtime = EventRuntime(repository, worker_count=1)
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="retry-after-rejection")
        await runtime.start()
        rejected = await runtime.publish(event, _features())
        rejected_state = runtime.state_manager.snapshot_for(event.instrument_id, event.symbol)
        rejected_dedupe = set(runtime._dedupe)
        retried = await runtime.publish(event, _features())
        await runtime.stop()
        return repository, rejected, rejected_state, rejected_dedupe, retried

    repository, rejected, rejected_state, rejected_dedupe, retried = asyncio.run(scenario())
    assert not rejected.persisted and rejected.transition is None
    assert rejected.result is StateApplyResult.NO_CHANGE
    assert rejected_state.state is SymbolState.IDLE and rejected_state.state_version == 0
    assert not rejected_dedupe
    assert retried.persisted and repository.calls == 2


def test_concurrent_duplicate_publishers_share_failed_attempt_then_retry():
    class FailOnceRepository(InMemoryG2Repository):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def persist(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("injected shared failure")
            return await super().persist(*args, **kwargs)

    async def scenario():
        repository = FailOnceRepository()
        runtime = EventRuntime(repository, worker_count=1)
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="shared-failed-attempt")
        first = asyncio.create_task(runtime.publish(event, _features()))
        await asyncio.sleep(0)
        second = asyncio.create_task(runtime.publish(event, _features()))
        await asyncio.sleep(0)
        await runtime.start()
        results = await asyncio.gather(first, second, return_exceptions=True)
        failed_state = runtime.state_manager.snapshot_for(event.instrument_id, event.symbol)
        failed_dedupe = set(runtime._dedupe)
        failed_inflight = dict(runtime._inflight)
        failed_truth = _repository_truth(repository)
        retried = await runtime.publish(event, _features())
        await runtime.stop()
        return (
            repository,
            results,
            failed_state,
            failed_dedupe,
            failed_inflight,
            failed_truth,
            retried,
        )

    (
        repository,
        results,
        failed_state,
        failed_dedupe,
        failed_inflight,
        failed_truth,
        retried,
    ) = asyncio.run(scenario())
    assert repository.calls == 2
    assert all(isinstance(result, RuntimeError) for result in results)
    assert failed_state.state is SymbolState.IDLE and failed_state.state_version == 0
    assert not failed_dedupe and not failed_inflight
    assert not failed_truth["events"] and not failed_truth["timeline"]
    assert not failed_truth["transitions"] and not failed_truth["candidates"]
    assert retried.persisted


def test_trade_dedupe_is_global_bounded_fifo_without_hit_refresh():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=1)
        pipeline = ScannerPipeline(
            OpportunityScanner(), runtime, trade_dedupe_capacity=3
        )
        pipeline.scanner.scan = lambda *_args, **_kwargs: []
        await runtime.start()
        for ordinal, trade_id in enumerate(("A", "B", "C")):
            await pipeline.ingest(_trade(trade_id, NOW + timedelta(seconds=ordinal)))
        before_duplicate = tuple(pipeline._trade_dedupe_fifo)
        features_before_duplicate = pipeline.last_features
        btc_returns_before_duplicate = dict(pipeline._btc_returns)
        lifecycle_before_duplicate = pipeline.lifecycle.active_types("SOL-USDT")
        runtime_dedupe_before_duplicate = set(runtime._dedupe)
        repository_before_duplicate = _repository_truth(repository)
        pipeline.last_detected_events = (_event(EventType.VOLUME_ANOMALY, 0),)
        duplicate = await pipeline.ingest(_trade("A", NOW + timedelta(seconds=3)))
        after_duplicate = tuple(pipeline._trade_dedupe_fifo)
        assert pipeline.last_features is features_before_duplicate
        assert pipeline._btc_returns == btc_returns_before_duplicate
        assert pipeline.lifecycle.active_types("SOL-USDT") == lifecycle_before_duplicate
        assert runtime._dedupe == runtime_dedupe_before_duplicate
        assert _repository_truth(repository) == repository_before_duplicate
        await pipeline.ingest(_trade("D", NOW + timedelta(seconds=4), instrument_id="ETH-USDT"))
        after_d = tuple(pipeline._trade_dedupe_fifo)
        await pipeline.ingest(_trade("A", NOW + timedelta(seconds=5)))
        await runtime.stop()
        return pipeline, duplicate, before_duplicate, after_duplicate, after_d

    pipeline, duplicate, before_duplicate, after_duplicate, after_d = asyncio.run(scenario())
    assert duplicate == []
    assert pipeline.last_detected_events == ()
    assert before_duplicate == after_duplicate
    assert [key[-1] for key in after_d] == ["B", "C", "D"]
    assert [key[-1] for key in pipeline._trade_dedupe_fifo] == ["C", "D", "A"]
    assert len(pipeline._trade_dedupe) == 3
    assert len(pipeline.rolling._states["SOL-USDT"].trades) == 4


def test_trade_dedupe_default_capacity_is_frozen_at_8192():
    pipeline = ScannerPipeline(OpportunityScanner(), EventRuntime(InMemoryG2Repository()))
    assert pipeline._trade_dedupe_capacity == 8192


def test_trade_identity_enters_fifo_only_after_successful_input_processing():
    class FailOnceRepository(InMemoryG2Repository):
        async def persist(self, *args, **kwargs):
            raise RuntimeError("injected pipeline persistence failure")

    async def scenario():
        repository = FailOnceRepository()
        runtime = EventRuntime(repository, worker_count=1)
        pipeline = ScannerPipeline(OpportunityScanner(), runtime, trade_dedupe_capacity=3)
        pipeline.scanner.scan = lambda features, *_args, **_kwargs: [
            _event(EventType.VOLUME_ANOMALY, 0, features.event_time, event_id="failing-input")
        ]
        trade = _trade("retryable", NOW)
        await runtime.start()
        with pytest.raises(RuntimeError, match="injected pipeline persistence failure"):
            await pipeline.ingest(trade)
        await runtime.stop()
        return pipeline, trade

    pipeline, trade = asyncio.run(scenario())
    assert pipeline._trade_key(trade) not in pipeline._trade_dedupe
    assert not pipeline._trade_dedupe_fifo
    assert "SOL-USDT" not in pipeline.rolling._states


def test_f07_normalization_trace_is_hash_seed_independent_in_subprocesses():
    script = """
import asyncio
import json
from datetime import UTC, datetime, timedelta
from marketpulse.g2.models import EventType, FeatureSnapshot, LifecycleAction, MarketEvent
from marketpulse.g2.repository import InMemoryG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner
from marketpulse.market_data.models import MarketType, NormalizedTrade

NOW = datetime(2026, 9, 4, 12, tzinfo=UTC)
def event(kind):
    return MarketEvent(event_id=f"active-{kind.value}", symbol="SOL-USDT", instrument_id="SOL-USDT", market_type=MarketType.SPOT, event_type=kind, event_time=NOW, received_time=NOW, source="fixture", strength=0.8, priority=80, state_version=0, config_version="fixture")
async def main():
    repository = InMemoryG2Repository()
    runtime = EventRuntime(repository, worker_count=1)
    pipeline = ScannerPipeline(OpportunityScanner(), runtime)
    pipeline.scanner.scan = lambda *_args, **_kwargs: []
    for kind in (EventType.VOLUME_ANOMALY, EventType.FLOW_IMBALANCE, EventType.BREAKOUT):
        pipeline.lifecycle.action_for(event(kind))
    await runtime.start()
    await pipeline.ingest(NormalizedTrade(base_asset="SOL", quote_asset="USDT", market_type=MarketType.SPOT, instrument_id="SOL-USDT", event_time=NOW + timedelta(seconds=1), received_time=NOW + timedelta(seconds=1), source="fixture", trade_id="subprocess", price=100, quantity=1, side="buy"))
    await runtime.stop()
    normalized = [item for item in pipeline.last_detected_events if item.source == "g2.signal_lifecycle"]
    print(json.dumps({"normalized_event_types": [item.event_type.value for item in normalized], "normalized_event_ids": [item.event_id for item in normalized], "timeline_ids": [item.timeline_id for item in repository.timeline], "transition_ids": [item.transition_id for item in repository.transitions], "transition_to_states": [item.to_state.value for item in repository.transitions], "state_versions": [item.state_version for item in repository.transitions]}, sort_keys=True, separators=(",", ":")))
asyncio.run(main())
"""
    root = Path(__file__).resolve().parents[2]
    outputs = []
    for seed in ("1", "2", "777"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(root / "backend" / "src")
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    canonical = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in outputs]
    digests = [hashlib.sha256(item.encode()).hexdigest() for item in canonical]
    assert outputs[0] == outputs[1] == outputs[2]
    assert digests[0] == digests[1] == digests[2]
    assert outputs[0]["normalized_event_types"] == ["BREAKOUT", "FLOW_IMBALANCE", "VOLUME_ANOMALY"]


async def _ttl_pipeline_case(target: SymbolState, offset: timedelta) -> tuple[InMemoryG2Repository, list, object, datetime]:
    clock = ReplayClock(NOW)
    repository = InMemoryG2Repository()
    runtime = EventRuntime(
        repository,
        state_manager=SymbolStateManager(
            StateMachineConfig(watch_ttl=timedelta(minutes=1), setup_ttl=timedelta(minutes=2))
        ),
        worker_count=1,
    )
    pipeline = ScannerPipeline(OpportunityScanner(clock=clock), runtime, clock=clock)
    active_types = [EventType.VOLUME_ANOMALY, EventType.FLOW_IMBALANCE]
    if target is SymbolState.SETUP:
        active_types.append(EventType.BREAKOUT)

    def scan(features, *_args, **_kwargs):
        return [
            _event(
                event_type,
                0,
                features.event_time,
                strength=0.9 if event_type is EventType.BREAKOUT else 0.8,
                event_id=f"ttl-{event_type.value}-{features.event_time.isoformat()}",
            )
            for event_type in active_types[: stage[0]]
        ]

    pipeline.scanner.scan = scan
    stage = [0]
    await runtime.start()
    try:
        for ordinal in range(len(active_types)):
            stage[0] = ordinal + 1
            if ordinal:
                clock.advance_to(NOW + timedelta(seconds=ordinal))
            await pipeline.ingest(_trade(f"ttl-state-{ordinal}", clock.now()))
        before = repository.states["SOL-USDT"].model_copy(deep=True)
        assert before.state is target and before.watch_expires_at is not None
        clock.advance_to(before.watch_expires_at + offset)
        outcomes = await pipeline.ingest(_trade("ttl-boundary", clock.now()))
    finally:
        await runtime.stop()
    return repository, outcomes, before, clock.now()


def test_f09_pipeline_ttl_covers_watching_setup_and_clock_boundaries():
    async def scenario():
        watching = await _ttl_pipeline_case(SymbolState.WATCHING, timedelta())
        setup = await _ttl_pipeline_case(SymbolState.SETUP, timedelta())
        before = await _ttl_pipeline_case(SymbolState.WATCHING, -timedelta(microseconds=1))
        return watching, setup, before

    watching, setup, before = asyncio.run(scenario())
    for (repository, outcomes, prior, now), configured_ttl in (
        (watching, timedelta(minutes=1)),
        (setup, timedelta(minutes=2)),
    ):
        ttl_events = [event for event in repository.events.values() if event.source == "g2.state_ttl"]
        ttl_timeline = [item for item in repository.timeline if item.event_id == ttl_events[0].event_id]
        ttl_transitions = [item for item in repository.transitions if item.event_id == ttl_events[0].event_id]
        assert now == prior.watch_expires_at
        assert prior.watch_expires_at == prior.last_event_time + configured_ttl
        assert len(outcomes) == len(ttl_events) == len(ttl_timeline) == len(ttl_transitions) == 1
        assert ttl_transitions[0].from_state is prior.state
        assert ttl_transitions[0].to_state is SymbolState.IDLE
        assert ttl_transitions[0].reason == "watch_ttl_expired"
        assert ttl_transitions[0].state_version == prior.state_version + 1
        assert repository.states["SOL-USDT"].state is SymbolState.IDLE
        assert repository.states["SOL-USDT"].cooldown_until is not None
    repository, outcomes, prior, now = before
    assert now == prior.watch_expires_at - timedelta(microseconds=1)
    assert not outcomes
    assert not [event for event in repository.events.values() if event.source == "g2.state_ttl"]
    assert repository.states["SOL-USDT"] == prior


def test_f09_replay_clock_ttl_trace_is_deterministic():
    async def scenario():
        first = await _ttl_pipeline_case(SymbolState.WATCHING, timedelta())
        second = await _ttl_pipeline_case(SymbolState.WATCHING, timedelta())
        return first, second

    first, second = asyncio.run(scenario())
    def ttl_truth(result):
        repository, _outcomes, _prior, _now = result
        event = next(item for item in repository.events.values() if item.source == "g2.state_ttl")
        timeline = next(item for item in repository.timeline if item.event_id == event.event_id)
        transition = next(item for item in repository.transitions if item.event_id == event.event_id)
        state = repository.states["SOL-USDT"]
        return (
            event.event_id,
            timeline.timeline_id,
            transition.transition_id,
            event.event_time,
            transition.state_version,
            state.state,
            state.state_version,
        )
    assert ttl_truth(first) == ttl_truth(second)


def test_f11_failure_retry_matches_clean_runtime_business_truth():
    class FailOnceRepository(InMemoryG2Repository):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def persist(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("injected equivalence failure")
            return await super().persist(*args, **kwargs)

    async def scenario():
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="equivalent-event")
        failed_repository = FailOnceRepository()
        failed_runtime = EventRuntime(
            failed_repository,
            strategy_engine=StrategyEngine(ReplayClock(NOW)),
            worker_count=1,
        )
        await failed_runtime.start()
        with pytest.raises(RuntimeError, match="injected equivalence failure"):
            await failed_runtime.publish(event, _features())
        assert failed_runtime.state_manager.snapshot_for(event.instrument_id, event.symbol).state is SymbolState.IDLE
        assert event.event_id not in failed_runtime._dedupe
        assert not failed_runtime._inflight
        assert not failed_repository.events and not failed_repository.timeline
        assert not failed_repository.transitions and not failed_repository.candidates
        retried = await failed_runtime.publish(event, _features())
        await failed_runtime.stop()

        clean_repository = InMemoryG2Repository()
        clean_runtime = EventRuntime(
            clean_repository,
            strategy_engine=StrategyEngine(ReplayClock(NOW)),
            worker_count=1,
        )
        await clean_runtime.start()
        clean = await clean_runtime.publish(event, _features())
        await clean_runtime.stop()
        return failed_repository, clean_repository, retried, clean

    failed_repository, clean_repository, retried, clean = asyncio.run(scenario())
    assert retried.persisted and clean.persisted
    assert _repository_truth(failed_repository) == _repository_truth(clean_repository)


def test_f11_fresh_runtime_observes_true_durable_duplicate_without_speculation():
    async def scenario():
        repository = InMemoryG2Repository()
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="durable-duplicate")
        first_runtime = EventRuntime(repository, worker_count=1)
        await first_runtime.start()
        first = await first_runtime.publish(event, _features())
        await first_runtime.stop()
        truth_before = _repository_truth(repository)

        second_runtime = EventRuntime(repository, worker_count=1)
        await second_runtime.start()
        duplicate = await second_runtime.publish(event, _features())
        durable_state = repository.states[event.instrument_id].model_copy(deep=True)
        memory_state = second_runtime.state_manager.snapshot_for(event.instrument_id, event.symbol)
        await second_runtime.stop()
        return repository, truth_before, first, duplicate, durable_state, memory_state

    repository, truth_before, first, duplicate, durable_state, memory_state = asyncio.run(scenario())
    assert first.persisted and not duplicate.persisted
    assert duplicate.result is StateApplyResult.NO_CHANGE and duplicate.transition is None
    assert memory_state == durable_state
    assert _repository_truth(repository) == truth_before


async def _cross_finding_truth() -> dict[str, object]:
    clock = ReplayClock(NOW)
    repository = InMemoryG2Repository()
    runtime = EventRuntime(
        repository,
        state_manager=SymbolStateManager(StateMachineConfig(watch_ttl=timedelta(minutes=1))),
        strategy_engine=StrategyEngine(clock),
        worker_count=1,
    )
    pipeline = ScannerPipeline(
        OpportunityScanner(clock=clock), runtime, clock=clock, trade_dedupe_capacity=3
    )
    stages = [
        [EventType.VOLUME_ANOMALY],
        [EventType.VOLUME_ANOMALY, EventType.FLOW_IMBALANCE],
        [EventType.VOLUME_ANOMALY, EventType.FLOW_IMBALANCE, EventType.BREAKOUT],
    ]
    stage = [0]

    def scan(features, *_args, **_kwargs):
        return [
            _event(
                event_type,
                0,
                features.event_time,
                strength=0.9 if event_type is EventType.BREAKOUT else 0.8,
                event_id=f"cross-{event_type.value}-{features.event_time.isoformat()}",
            )
            for event_type in stages[stage[0]]
        ]

    pipeline.scanner.scan = scan
    await runtime.start()
    try:
        await pipeline.ingest(_trade("A", clock.now()))
        clock.advance_to(NOW + timedelta(seconds=1))
        stage[0] = 1
        await pipeline.ingest(_trade("B", clock.now()))
        watching = repository.states["SOL-USDT"].model_copy(deep=True)
        before_duplicate = _repository_truth(repository)
        rolling_before_duplicate = len(pipeline.rolling._states["SOL-USDT"].trades)
        clock.advance_to(NOW + timedelta(seconds=2))
        duplicate = await pipeline.ingest(_trade("A", clock.now()))
        assert duplicate == [] and pipeline.last_detected_events == ()
        assert _repository_truth(repository) == before_duplicate
        assert len(pipeline.rolling._states["SOL-USDT"].trades) == rolling_before_duplicate
        assert watching.watch_expires_at is not None
        clock.advance_to(watching.watch_expires_at)
        stage[0] = 2
        outcomes = await pipeline.ingest(_trade("C", clock.now()))
    finally:
        await runtime.stop()
    ttl = [item for item in repository.transitions if item.reason == "watch_ttl_expired"]
    assert len(ttl) == 1
    assert outcomes[0].transition is not None and outcomes[0].transition.reason == "watch_ttl_expired"
    assert outcomes[1].transition is not None and outcomes[1].transition.to_state is SymbolState.DETECTED
    state = repository.states["SOL-USDT"]
    assert state.state_version == watching.state_version + 2
    return {
        "rolling": [
            item.model_dump(mode="json") for item in pipeline.rolling._states["SOL-USDT"].trades
        ],
        "repository": _repository_truth(repository),
        "state": state.model_dump(mode="json"),
        "state_version": state.state_version,
    }


def test_cross_finding_duplicate_ttl_and_post_expiry_input_are_deterministic():
    async def scenario():
        return await _cross_finding_truth(), await _cross_finding_truth()

    first, second = asyncio.run(scenario())
    assert first == second


async def _f10_real_scanner_business_truth(*, include_duplicate: bool) -> dict[str, object]:
    """Exercise the concrete G1->rolling->scanner->runtime path without a scanner stub."""
    clock = ReplayClock(NOW)
    repository = InMemoryG2Repository()
    rolling = RollingFeatureEngine()
    runtime = EventRuntime(
        repository,
        strategy_engine=StrategyEngine(clock),
        worker_count=1,
    )
    pipeline = ScannerPipeline(
        OpportunityScanner(clock=clock),
        runtime,
        rolling=rolling,
        clock=clock,
    )
    first = _trade("f10-A", NOW)
    duplicate = _trade("f10-A", NOW + timedelta(seconds=1))
    second = _trade("f10-B", NOW + timedelta(seconds=2))
    await runtime.start()
    try:
        await pipeline.ingest(first)
        before_duplicate = _repository_truth(repository)
        rolling_before_duplicate = [
            item.model_dump(mode="json") for item in rolling._states["SOL-USDT"].trades
        ]
        if include_duplicate:
            clock.advance_to(duplicate.received_time)
            outcomes = await pipeline.ingest(duplicate)
            assert outcomes == []
            assert pipeline.last_detected_events == ()
            assert _repository_truth(repository) == before_duplicate
            assert [
                item.model_dump(mode="json") for item in rolling._states["SOL-USDT"].trades
            ] == rolling_before_duplicate
        clock.advance_to(second.received_time)
        await pipeline.ingest(second)
    finally:
        await runtime.stop()
    state = repository.states["SOL-USDT"]
    return {
        "feature": pipeline.last_features.model_dump(mode="json"),
        "rolling_trades": [
            item.model_dump(mode="json") for item in rolling._states["SOL-USDT"].trades
        ],
        "repository": _repository_truth(repository),
        "state": state.model_dump(mode="json"),
        "state_version": state.state_version,
    }


def test_f10_real_scanner_duplicate_trade_is_business_equivalent_to_omission():
    async def scenario():
        return (
            await _f10_real_scanner_business_truth(include_duplicate=True),
            await _f10_real_scanner_business_truth(include_duplicate=False),
        )

    with_duplicate, without_duplicate = asyncio.run(scenario())
    assert with_duplicate == without_duplicate


def test_event_runtime_dedupe_is_bounded_and_evicted_ids_use_durable_idempotency():
    async def scenario():
        repository = InMemoryG2Repository()
        runtime = EventRuntime(repository, worker_count=1, dedupe_capacity=2)
        first = _event(EventType.VOLUME_ANOMALY, 0, event_id="runtime-dedupe-A")
        second = _event(
            EventType.FLOW_IMBALANCE,
            1,
            NOW + timedelta(seconds=1),
            event_id="runtime-dedupe-B",
        )
        third = _event(
            EventType.BREAKOUT,
            2,
            NOW + timedelta(seconds=2),
            event_id="runtime-dedupe-C",
        )
        await runtime.start()
        try:
            outcomes = [
                await runtime.publish(first, _features()),
                await runtime.publish(second, _features(NOW + timedelta(seconds=1))),
                await runtime.publish(third, _features(NOW + timedelta(seconds=2))),
            ]
            retained = (set(runtime._dedupe), tuple(runtime._dedupe_fifo))
            truth_before_duplicate = _repository_truth(repository)
            state_before_duplicate = repository.states["SOL-USDT"].model_copy(deep=True)
            duplicate = await runtime.publish(first, _features())
        finally:
            await runtime.stop()
        return (
            outcomes,
            retained,
            truth_before_duplicate,
            state_before_duplicate,
            duplicate,
            repository,
            runtime,
        )

    (
        outcomes,
        retained,
        truth_before_duplicate,
        state_before_duplicate,
        duplicate,
        repository,
        runtime,
    ) = asyncio.run(scenario())
    assert all(outcome.persisted for outcome in outcomes)
    assert retained == ({"runtime-dedupe-B", "runtime-dedupe-C"}, ("runtime-dedupe-B", "runtime-dedupe-C"))
    assert len(runtime._dedupe) <= runtime._dedupe_capacity == 2
    assert not duplicate.persisted and duplicate.result is StateApplyResult.NO_CHANGE
    assert duplicate.transition is None
    assert _repository_truth(repository) == truth_before_duplicate
    assert repository.states["SOL-USDT"] == state_before_duplicate


def test_event_runtime_retains_only_recent_worker_failures_and_remains_usable():
    class FailingRepository(InMemoryG2Repository):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def persist(self, *args, **kwargs):
            self.calls += 1
            if self.calls <= 5:
                raise RuntimeError(f"injected failure {self.calls}")
            return await super().persist(*args, **kwargs)

    async def scenario():
        repository = FailingRepository()
        runtime = EventRuntime(repository, worker_count=1, worker_exception_capacity=2)
        await runtime.start()
        try:
            failures = []
            for ordinal in range(5):
                with pytest.raises(RuntimeError, match=f"injected failure {ordinal + 1}"):
                    await runtime.publish(
                        _event(
                            EventType.VOLUME_ANOMALY,
                            0,
                            event_id=f"worker-failure-{ordinal}",
                        ),
                        _features(),
                    )
                failures.append(tuple(str(item) for item in runtime.worker_exceptions))
            recovered = await runtime.publish(
                _event(EventType.VOLUME_ANOMALY, 0, event_id="worker-failure-recovered"),
                _features(),
            )
        finally:
            await runtime.stop()
        return runtime, failures, recovered

    runtime, failures, recovered = asyncio.run(scenario())
    assert all(len(retained) <= 2 for retained in failures)
    assert tuple(str(item) for item in runtime.worker_exceptions) == (
        "injected failure 4",
        "injected failure 5",
    )
    assert recovered.persisted
    assert not runtime._inflight


def test_event_runtime_cancel_before_enqueue_removes_inflight_and_allows_retry():
    class TrackingQueue(asyncio.PriorityQueue):
        def __init__(self, maxsize: int) -> None:
            super().__init__(maxsize=maxsize)
            self.put_attempts: asyncio.Queue[object] = asyncio.Queue()
            self.accepted: asyncio.Queue[object] = asyncio.Queue()

        async def put(self, item) -> None:
            self.put_attempts.put_nowait(item)
            await super().put(item)
            self.accepted.put_nowait(item)

    class BlockingRepository(InMemoryG2Repository):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def persist(self, event, *args, **kwargs):
            if event.event_id == "queue-holder":
                self.started.set()
                await self.release.wait()
            return await super().persist(event, *args, **kwargs)

    async def scenario():
        repository = BlockingRepository()
        runtime = EventRuntime(repository, worker_count=1, queue_capacity=1)
        runtime.queue = TrackingQueue(maxsize=1)
        holder = _event(EventType.VOLUME_ANOMALY, 0, event_id="queue-holder")
        occupier = _event(
            EventType.FLOW_IMBALANCE,
            1,
            NOW + timedelta(seconds=1),
            event_id="queue-occupier",
        )
        cancelled_event = _event(
            EventType.VOLUME_ANOMALY,
            0,
            event_id="cancel-before-enqueue",
        ).model_copy(update={"instrument_id": "BTC-USDT", "symbol": "BTC-USDT"})
        cancelled_features = _features().model_copy(
            update={"instrument_id": "BTC-USDT", "symbol": "BTC-USDT"}
        )
        await runtime.start()
        try:
            holder_task = asyncio.create_task(runtime.publish(holder, _features()))
            await asyncio.wait_for(runtime.queue.put_attempts.get(), timeout=1)
            await asyncio.wait_for(runtime.queue.accepted.get(), timeout=1)
            await asyncio.wait_for(repository.started.wait(), timeout=1)

            occupier_task = asyncio.create_task(
                runtime.publish(occupier, _features(NOW + timedelta(seconds=1)))
            )
            await asyncio.wait_for(runtime.queue.put_attempts.get(), timeout=1)
            await asyncio.wait_for(runtime.queue.accepted.get(), timeout=1)
            assert runtime.queue.full()

            cancelled_task = asyncio.create_task(
                runtime.publish(cancelled_event, cancelled_features)
            )
            await asyncio.wait_for(runtime.queue.put_attempts.get(), timeout=1)
            cancelled_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await cancelled_task
            inflight_after_cancel = dict(runtime._inflight)
            queued_after_cancel = runtime.queue.qsize()

            repository.release.set()
            await holder_task
            await occupier_task
            retried = await runtime.publish(cancelled_event, cancelled_features)
        finally:
            repository.release.set()
            await runtime.stop()
        return runtime, inflight_after_cancel, queued_after_cancel, retried, repository

    runtime, inflight_after_cancel, queued_after_cancel, retried, repository = asyncio.run(scenario())
    assert "cancel-before-enqueue" not in inflight_after_cancel
    assert queued_after_cancel == 1
    assert retried.persisted
    assert "cancel-before-enqueue" in repository.events
    assert not runtime._inflight
    assert not runtime.worker_exceptions


def test_event_runtime_cancel_after_enqueue_keeps_shared_work_and_duplicate_waiter():
    class BlockingRepository(InMemoryG2Repository):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def persist(self, event, *args, **kwargs):
            self.started.set()
            await self.release.wait()
            return await super().persist(event, *args, **kwargs)

    async def scenario():
        repository = BlockingRepository()
        runtime = EventRuntime(repository, worker_count=1)
        event = _event(EventType.VOLUME_ANOMALY, 0, event_id="cancel-after-enqueue")
        duplicate_waiter_entered = asyncio.Event()
        original_shield = asyncio.shield

        def observed_shield(awaitable):
            duplicate_waiter_entered.set()
            return original_shield(awaitable)

        await runtime.start()
        try:
            original = asyncio.create_task(runtime.publish(event, _features()))
            await asyncio.wait_for(repository.started.wait(), timeout=1)
            original.cancel()
            with pytest.raises(asyncio.CancelledError):
                await original

            asyncio.shield = observed_shield
            duplicate = asyncio.create_task(runtime.publish(event, _features()))
            await asyncio.wait_for(duplicate_waiter_entered.wait(), timeout=1)
            repository.release.set()
            duplicate_outcome = await asyncio.wait_for(duplicate, timeout=1)
            return runtime, repository, duplicate_outcome
        finally:
            asyncio.shield = original_shield
            repository.release.set()
            await runtime.stop()

    runtime, repository, duplicate_outcome = asyncio.run(scenario())
    assert duplicate_outcome.persisted
    assert list(repository.events) == ["cancel-after-enqueue"]
    assert not runtime._inflight
    assert not runtime.worker_exceptions


async def _postgres_execute(url: str, statement: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@contextmanager
def _g2_disposable_postgres_database():
    primary_url = Settings().database_url
    database_name = f"marketpulse_n01_g2_{uuid4().hex[:12]}"
    database_url = f"{primary_url.rsplit('/', 1)[0]}/{database_name}"
    backend = Path(__file__).resolve().parents[1]
    asyncio.run(_postgres_execute(primary_url, f'CREATE DATABASE "{database_name}"'))
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    try:
        command.upgrade(config, "head")
        yield database_url
    finally:
        asyncio.run(
            _postgres_execute(
                primary_url,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{database_name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_postgres_execute(primary_url, f'DROP DATABASE "{database_name}"'))


def test_postgres_g2_concurrent_duplicate_is_atomic_and_both_runtimes_remain_usable():
    class BarrierRepository(PostgresG2Repository):
        def __init__(self, sessions, barrier: asyncio.Barrier) -> None:
            super().__init__(sessions)
            self._barrier = barrier

        async def persist(self, *args, **kwargs):
            await self._barrier.wait()
            return await super().persist(*args, **kwargs)

    async def scenario(database_url: str):
        engine = create_async_engine(database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        barrier = asyncio.Barrier(2)
        first_runtime = EventRuntime(BarrierRepository(sessions, barrier), worker_count=1)
        second_runtime = EventRuntime(BarrierRepository(sessions, barrier), worker_count=1)
        duplicate = _event(EventType.VOLUME_ANOMALY, 0, event_id="postgres-concurrent-duplicate")
        await first_runtime.start()
        await second_runtime.start()
        try:
            outcomes = await asyncio.wait_for(
                asyncio.gather(
                    first_runtime.publish(duplicate, _features()),
                    second_runtime.publish(duplicate, _features()),
                ),
                timeout=5,
            )
            first_follow_up = _event(
                EventType.VOLUME_ANOMALY,
                0,
                event_id="postgres-runtime-one-follow-up",
            ).model_copy(update={"instrument_id": "BTC-USDT", "symbol": "BTC-USDT"})
            second_follow_up = _event(
                EventType.VOLUME_ANOMALY,
                0,
                event_id="postgres-runtime-two-follow-up",
            ).model_copy(update={"instrument_id": "ETH-USDT", "symbol": "ETH-USDT"})
            first_features = _features().model_copy(
                update={"instrument_id": "BTC-USDT", "symbol": "BTC-USDT"}
            )
            second_features = _features().model_copy(
                update={"instrument_id": "ETH-USDT", "symbol": "ETH-USDT"}
            )
            follow_ups = await asyncio.gather(
                first_runtime.publish(first_follow_up, first_features),
                second_runtime.publish(second_follow_up, second_features),
            )
            async with sessions() as session:
                counts = {
                    "events": await session.scalar(
                        select(func.count()).select_from(MarketEventRecord)
                    ),
                    "timeline": await session.scalar(
                        select(func.count()).select_from(SignalTimelineRecord)
                    ),
                    "transitions": await session.scalar(
                        select(func.count()).select_from(StateTransitionRecord)
                    ),
                    "observations": await session.scalar(
                        select(func.count()).select_from(DerivedObservationRecord)
                    ),
                    "states": await session.scalar(
                        select(func.count()).select_from(SymbolStateStore)
                    ),
                    "candidates": await session.scalar(
                        select(func.count()).select_from(StrategyCandidateRecord)
                    ),
                }
        finally:
            await first_runtime.stop()
            await second_runtime.stop()
            await engine.dispose()
        return outcomes, follow_ups, counts, first_runtime, second_runtime

    with _g2_disposable_postgres_database() as database_url:
        outcomes, follow_ups, counts, first_runtime, second_runtime = asyncio.run(
            scenario(database_url)
        )
    assert sorted(outcome.persisted for outcome in outcomes) == [False, True]
    assert all(outcome.persisted for outcome in follow_ups)
    assert counts == {
        "events": 3,
        "timeline": 3,
        "transitions": 3,
        "observations": 3,
        "states": 3,
        "candidates": 12,
    }
    assert not first_runtime.worker_exceptions
    assert not second_runtime.worker_exceptions
    assert not first_runtime._inflight
    assert not second_runtime._inflight
