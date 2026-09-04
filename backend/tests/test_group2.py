import asyncio
from datetime import UTC, datetime, timedelta

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
from marketpulse.g2.repository import InMemoryG2Repository
from marketpulse.g2.rolling import RollingFeatureEngine
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner, ScannerConfig
from marketpulse.g2.state_machine import StateMachineConfig, SymbolStateManager
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.g2.timeline import SignalLifecycle
from marketpulse.market_data.models import MarketType, NormalizedTrade

NOW = datetime(2026, 9, 4, 12, tzinfo=UTC)


def _features(at: datetime = NOW, price: float = 101) -> FeatureSnapshot:
    return FeatureSnapshot(instrument_id="SOL-USDT", symbol="SOL-USDT", market_type=MarketType.SPOT, event_time=at, current_price=price, short_return=0.01, buy_sell_imbalance=0.8)


def _event(kind: EventType, version: int, at: datetime = NOW, strength: float = 0.8, event_id: str | None = None) -> MarketEvent:
    return MarketEvent(event_id=event_id or f"event-{kind}-{version}-{at.timestamp()}", symbol="SOL-USDT", instrument_id="SOL-USDT", market_type=MarketType.SPOT, event_type=kind, event_time=at, received_time=at, source="fixture", strength=strength, priority=80, state_version=version, config_version="fixture", payload={"current_price": 101})


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
