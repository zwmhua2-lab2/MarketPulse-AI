import asyncio
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.g2.models import EventType, FeatureSnapshot, LifecycleAction, MarketEvent
from marketpulse.g2.repository import InMemoryG2Repository, PostgresG2Repository
from marketpulse.g2.rolling import RollingFeatureEngine
from marketpulse.g2.runtime import EventRuntime
from marketpulse.g2.timeline import SignalLifecycle
from marketpulse.market_data.models import MarketType, NormalizedTrade
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 9, 10, 12, tzinfo=UTC)
N01_INSTRUMENTS = ("BTC-USDT", "ETH-USDT")


def _features(instrument_id: str, offset: int = 0) -> FeatureSnapshot:
    at = NOW + timedelta(seconds=offset)
    return FeatureSnapshot(
        instrument_id=instrument_id,
        symbol=instrument_id,
        market_type=MarketType.SPOT,
        event_time=at,
        current_price=100_000 + offset,
        short_return=0.01,
        buy_sell_imbalance=0.8,
    )


def _event(event_id: str, instrument_id: str, offset: int = 0, version: int = 0) -> MarketEvent:
    at = NOW + timedelta(seconds=offset)
    return MarketEvent(
        event_id=event_id,
        symbol=instrument_id,
        instrument_id=instrument_id,
        market_type=MarketType.SPOT,
        event_type=EventType.VOLUME_ANOMALY,
        event_time=at,
        received_time=at,
        source="n01.fixture",
        strength=0.8,
        priority=80,
        state_version=version,
        config_version="n01-a",
        payload={"offset": offset},
    )


class _TrackingQueue(asyncio.PriorityQueue):
    """Records queue.put boundaries without a scheduler-dependent sleep."""

    def __init__(self, maxsize: int) -> None:
        super().__init__(maxsize=maxsize)
        self.attempted: asyncio.Queue[str] = asyncio.Queue()
        self.accepted: asyncio.Queue[str] = asyncio.Queue()
        self.dequeued: asyncio.Queue[str] = asyncio.Queue()

    async def put(self, item) -> None:
        queued = item[2]
        event_id = queued.event.event_id if queued is not None else "<stop>"
        self.attempted.put_nowait(event_id)
        await super().put(item)
        self.accepted.put_nowait(event_id)

    async def get(self):
        item = await super().get()
        queued = item[2]
        event_id = queued.event.event_id if queued is not None else "<stop>"
        self.dequeued.put_nowait(event_id)
        return item


class _BackpressureRepository(InMemoryG2Repository):
    def __init__(self) -> None:
        super().__init__()
        self.holder_started = asyncio.Event()
        self.release_holder = asyncio.Event()

    async def persist(self, event, *args, **kwargs):
        if event.event_id == "queue-holder":
            self.holder_started.set()
            await self.release_holder.wait()
        return await super().persist(event, *args, **kwargs)


def test_n01_bounded_queue_backpressure_blocks_then_resumes_without_loss():
    async def scenario():
        repository = _BackpressureRepository()
        runtime = EventRuntime(repository, worker_count=1, queue_capacity=1)
        runtime.queue = _TrackingQueue(maxsize=1)
        await runtime.start()
        try:
            holder = asyncio.create_task(
                runtime.publish(_event("queue-holder", "BTC-USDT"), _features("BTC-USDT"))
            )
            assert await asyncio.wait_for(runtime.queue.accepted.get(), timeout=1) == "queue-holder"
            await asyncio.wait_for(repository.holder_started.wait(), timeout=1)

            occupier = asyncio.create_task(
                runtime.publish(_event("queue-occupier", "ETH-USDT"), _features("ETH-USDT", 1))
            )
            assert await asyncio.wait_for(runtime.queue.accepted.get(), timeout=1) == "queue-occupier"
            assert runtime.queue.full()

            blocked = asyncio.create_task(
                runtime.publish(_event("queue-blocked", "BTC-USDT", 2), _features("BTC-USDT", 2))
            )
            assert await asyncio.wait_for(runtime.queue.attempted.get(), timeout=1) == "queue-holder"
            assert await asyncio.wait_for(runtime.queue.attempted.get(), timeout=1) == "queue-occupier"
            assert await asyncio.wait_for(runtime.queue.attempted.get(), timeout=1) == "queue-blocked"
            assert not blocked.done()
            assert runtime.queue.qsize() == 1

            repository.release_holder.set()
            outcomes = await asyncio.wait_for(asyncio.gather(holder, occupier, blocked), timeout=1)
            await runtime.queue.join()
            return runtime, repository, outcomes
        finally:
            repository.release_holder.set()
            await runtime.stop()

    runtime, repository, outcomes = asyncio.run(scenario())
    assert all(outcome.persisted for outcome in outcomes)
    assert set(repository.events) == {"queue-holder", "queue-occupier", "queue-blocked"}
    assert runtime.queue.qsize() == 0
    assert not runtime._inflight
    assert not runtime.worker_exceptions


class _ConcurrencyRepository(InMemoryG2Repository):
    def __init__(self, expected_instruments: set[str]) -> None:
        super().__init__()
        self.expected_instruments = expected_instruments
        self.entered: set[str] = set()
        self.all_entered = asyncio.Event()
        self.release = asyncio.Event()
        self.persist_entry_ids: list[str] = []
        self.active_by_instrument: defaultdict[str, int] = defaultdict(int)
        self.max_active_by_instrument: defaultdict[str, int] = defaultdict(int)

    async def persist(self, event, *args, **kwargs):
        instrument_id = event.instrument_id
        self.persist_entry_ids.append(event.event_id)
        self.active_by_instrument[instrument_id] += 1
        self.max_active_by_instrument[instrument_id] = max(
            self.max_active_by_instrument[instrument_id], self.active_by_instrument[instrument_id]
        )
        self.entered.add(instrument_id)
        if self.expected_instruments <= self.entered:
            self.all_entered.set()
        await self.release.wait()
        self.active_by_instrument[instrument_id] -= 1
        return await super().persist(event, *args, **kwargs)


def test_n01_finite_workers_serialize_same_instrument_and_parallelize_two_instruments():
    async def same_instrument():
        repository = _ConcurrencyRepository({"BTC-USDT"})
        runtime = EventRuntime(repository, worker_count=2, queue_capacity=8)
        runtime.queue = _TrackingQueue(maxsize=8)
        await runtime.start()
        worker_ids = {id(task) for task in runtime._workers}
        try:
            first = asyncio.create_task(
                runtime.publish(_event("serial-first", "BTC-USDT", version=0), _features("BTC-USDT"))
            )
            await asyncio.wait_for(repository.all_entered.wait(), timeout=1)
            assert await asyncio.wait_for(runtime.queue.dequeued.get(), timeout=1) == "serial-first"
            second = asyncio.create_task(
                runtime.publish(
                    _event("serial-second", "BTC-USDT", 1, version=1), _features("BTC-USDT", 1)
                )
            )
            # This is a worker-owned queue.get() witness, not a publisher scheduling guess.
            assert await asyncio.wait_for(runtime.queue.dequeued.get(), timeout=1) == "serial-second"
            assert len(runtime._workers) == 2
            assert {id(task) for task in runtime._workers} == worker_ids
            assert repository.max_active_by_instrument["BTC-USDT"] == 1
            assert repository.persist_entry_ids == ["serial-first"]
            assert repository.active_by_instrument["BTC-USDT"] == 1
            assert not second.done()
            repository.release.set()
            first_outcome = await asyncio.wait_for(first, timeout=1)
            second_outcome = await asyncio.wait_for(second, timeout=1)
            assert repository.persist_entry_ids == ["serial-first", "serial-second"]
            assert first_outcome.transition and first_outcome.transition.state_version == 1
            assert second_outcome.transition and second_outcome.transition.state_version == 2
            assert first_outcome.state_version == 1
            assert second_outcome.state_version == 2
            outcomes = (first_outcome, second_outcome)
            return runtime, repository, outcomes, worker_ids
        finally:
            repository.release.set()
            await runtime.stop()

    async def two_instruments():
        repository = _ConcurrencyRepository(set(N01_INSTRUMENTS))
        runtime = EventRuntime(repository, worker_count=2, queue_capacity=8)
        await runtime.start()
        try:
            tasks = [
                asyncio.create_task(runtime.publish(_event(f"parallel-{item}", item), _features(item)))
                for item in N01_INSTRUMENTS
            ]
            await asyncio.wait_for(repository.all_entered.wait(), timeout=1)
            assert set(repository.entered) == set(N01_INSTRUMENTS)
            assert sum(repository.active_by_instrument.values()) == 2
            repository.release.set()
            outcomes = tuple(await asyncio.wait_for(asyncio.gather(*tasks), timeout=1))
            return runtime, repository, outcomes
        finally:
            repository.release.set()
            await runtime.stop()

    serial_runtime, serial_repository, serial_outcomes, worker_ids = asyncio.run(same_instrument())
    parallel_runtime, parallel_repository, parallel_outcomes = asyncio.run(two_instruments())
    assert all(item.persisted for item in serial_outcomes + parallel_outcomes)
    assert serial_repository.max_active_by_instrument["BTC-USDT"] == 1
    assert all(item == 1 for item in parallel_repository.max_active_by_instrument.values())
    assert len(worker_ids) == 2
    assert not serial_runtime.worker_exceptions
    assert not parallel_runtime.worker_exceptions


class _FailOnceRepository(InMemoryG2Repository):
    def __init__(self, failing_event_id: str) -> None:
        super().__init__()
        self.failing_event_id = failing_event_id
        self.failed = False

    async def persist(self, event, *args, **kwargs):
        if event.event_id == self.failing_event_id and not self.failed:
            self.failed = True
            raise RuntimeError("n01 injected repository failure")
        return await super().persist(event, *args, **kwargs)


def test_n01_duplicate_retry_and_cancellation_ownership_are_deterministic():
    async def scenario():
        repository = _FailOnceRepository("failure-retry")
        runtime = EventRuntime(
            repository, worker_count=1, queue_capacity=2, dedupe_capacity=2, worker_exception_capacity=2
        )
        await runtime.start()
        try:
            first = _event("recent-duplicate", "BTC-USDT")
            persisted = await runtime.publish(first, _features("BTC-USDT"))
            recent_duplicate = await runtime.publish(first, _features("BTC-USDT"))
            await runtime.publish(_event("evict-one", "ETH-USDT"), _features("ETH-USDT", 1))
            await runtime.publish(_event("evict-two", "BTC-USDT", 2), _features("BTC-USDT", 2))
            evicted_duplicate = await runtime.publish(first, _features("BTC-USDT", 3))

            with pytest.raises(RuntimeError, match="injected repository failure"):
                await runtime.publish(_event("failure-retry", "ETH-USDT", 4), _features("ETH-USDT", 4))
            retry = await runtime.publish(_event("failure-retry", "ETH-USDT", 4), _features("ETH-USDT", 4))

            gate_started = asyncio.Event()
            gate_release = asyncio.Event()
            original_persist = repository.persist

            async def blocked_persist(event, *args, **kwargs):
                if event.event_id == "cancelled-owner":
                    gate_started.set()
                    await gate_release.wait()
                    if not getattr(repository, "cancelled_owner_failed", False):
                        repository.cancelled_owner_failed = True
                        raise RuntimeError("n01 injected cancelled-owner failure")
                return await original_persist(event, *args, **kwargs)

            repository.persist = blocked_persist
            cancelled_event = _event("cancelled-owner", "BTC-USDT", 5)
            publisher = asyncio.create_task(runtime.publish(cancelled_event, _features("BTC-USDT", 5)))
            await asyncio.wait_for(gate_started.wait(), timeout=1)
            publisher.cancel()
            with pytest.raises(asyncio.CancelledError):
                await publisher
            duplicate_waiter = asyncio.create_task(runtime.publish(cancelled_event, _features("BTC-USDT", 5)))
            gate_release.set()
            with pytest.raises(RuntimeError, match="cancelled-owner failure"):
                await asyncio.wait_for(duplicate_waiter, timeout=1)
            cancellation_retry = await runtime.publish(cancelled_event, _features("BTC-USDT", 5))
            await runtime.queue.join()
            return runtime, persisted, recent_duplicate, evicted_duplicate, retry, cancellation_retry
        finally:
            if "gate_release" in locals():
                gate_release.set()
            await runtime.stop()

    runtime, persisted, recent, evicted, retry, cancellation_retry = asyncio.run(scenario())
    assert persisted.persisted
    assert not recent.persisted
    assert not evicted.persisted  # durable repository dedupe still wins after FIFO eviction.
    assert retry.persisted
    assert cancellation_retry.persisted
    assert len(runtime._dedupe) <= runtime._dedupe_capacity
    assert len(runtime.worker_exceptions) <= runtime._worker_exception_capacity
    assert not runtime._inflight


@contextmanager
def _disposable_postgres_database():
    primary_url = Settings().database_url
    database_name = f"marketpulse_n01_a_{uuid4().hex[:12]}"
    database_url = f"{primary_url.rsplit('/', 1)[0]}/{database_name}"
    backend = Path(__file__).resolve().parents[1]

    async def execute(url: str, statement: str) -> None:
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                await connection.execute(text(statement))
        finally:
            await engine.dispose()

    asyncio.run(execute(primary_url, f'CREATE DATABASE "{database_name}"'))
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    try:
        command.upgrade(config, "head")
        yield database_name, database_url
    finally:
        asyncio.run(
            execute(
                primary_url,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{database_name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(execute(primary_url, f'DROP DATABASE "{database_name}"'))


async def _database_activity(database_name: str) -> dict[str, int]:
    engine = create_async_engine(Settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT count(*) AS sessions, "
                    "count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction "
                    "FROM pg_stat_activity WHERE datname = :database_name"
                ),
                {"database_name": database_name},
            )
            row = result.one()
            return {"sessions": row.sessions, "idle_in_transaction": row.idle_in_transaction}
    finally:
        await engine.dispose()


def test_n01_twenty_real_postgres_lifecycles_dispose_tasks_queues_inflight_and_connections():
    async def scenario(database_name: str, database_url: str):
        baseline = await _database_activity(database_name)
        cycle_evidence = []
        cycle_activity = []
        for cycle in range(20):
            # The harness owns every connection and deliberately avoids retaining a pool between
            # cycles; explicit disposal below is still required for the AsyncEngine lifecycle.
            engine = create_async_engine(database_url, poolclass=NullPool)
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            runtime = EventRuntime(
                PostgresG2Repository(sessions),
                worker_count=2,
                queue_capacity=4,
                dedupe_capacity=2,
                worker_exception_capacity=2,
            )
            before_tasks = {
                task.get_name()
                for task in asyncio.all_tasks()
                if task.get_name().startswith("g2-event-worker-") and not task.done()
            }
            await runtime.start()
            worker_tasks = tuple(runtime._workers)
            try:
                first = _event(f"cycle-{cycle}-first", "BTC-USDT", cycle * 10)
                second = _event(f"cycle-{cycle}-second", "ETH-USDT", cycle * 10 + 1)
                assert all(
                    item.persisted
                    for item in await asyncio.gather(
                        runtime.publish(first, _features("BTC-USDT", cycle * 10)),
                        runtime.publish(second, _features("ETH-USDT", cycle * 10 + 1)),
                    )
                )
                assert not (
                    await runtime.publish(first, _features("BTC-USDT", cycle * 10 + 2))
                ).persisted
                await runtime.queue.join()
                evidence = {
                    "cycle": cycle + 1,
                    "queue": runtime.queue.qsize(),
                    "inflight": len(runtime._inflight),
                    "workers": len(worker_tasks),
                    "dedupe": len(runtime._dedupe),
                    "worker_exceptions": len(runtime.worker_exceptions),
                }
                assert evidence == {
                    "cycle": cycle + 1,
                    "queue": 0,
                    "inflight": 0,
                    "workers": 2,
                    "dedupe": 2,
                    "worker_exceptions": 0,
                }
                cycle_evidence.append(evidence)
            finally:
                await runtime.stop()
                await engine.dispose()
            assert all(task.done() for task in worker_tasks)
            assert not {
                task.get_name()
                for task in asyncio.all_tasks()
                if task.get_name().startswith("g2-event-worker-") and not task.done()
            } - before_tasks
            activity = await _database_activity(database_name)
            assert activity == baseline
            cycle_activity.append(activity)
        return baseline, cycle_evidence, cycle_activity, await _database_activity(database_name)

    with _disposable_postgres_database() as (database_name, database_url):
        baseline, cycles, cycle_activity, after = asyncio.run(scenario(database_name, database_url))
    assert len(cycles) == 20
    assert cycle_activity == [baseline] * 20
    assert baseline["idle_in_transaction"] == 0
    assert after == baseline
    print(
        {
            "n01_lifecycle_cycles": len(cycles),
            "db_before": baseline,
            "db_cycle_activity": cycle_activity,
            "db_after": after,
        }
    )


def test_n01_fixed_universe_retention_bounds_have_explicit_mechanisms():
    async def runtime_bounds():
        runtime = EventRuntime(
            InMemoryG2Repository(),
            worker_count=2,
            dedupe_capacity=3,
            worker_exception_capacity=2,
        )
        await runtime.start()
        try:
            for offset in range(12):
                instrument_id = N01_INSTRUMENTS[offset % len(N01_INSTRUMENTS)]
                await runtime.publish(
                    _event(f"bounded-{offset}", instrument_id, offset), _features(instrument_id, offset)
                )
            await runtime.queue.join()
            return runtime
        finally:
            await runtime.stop()

    runtime = asyncio.run(runtime_bounds())
    rolling = RollingFeatureEngine()
    lifecycle = SignalLifecycle()
    for instrument_id in N01_INSTRUMENTS:
        for offset in range(130):
            at = NOW + timedelta(seconds=offset)
            rolling.ingest(
                NormalizedTrade(
                    base_asset=instrument_id.split("-")[0],
                    quote_asset="USDT",
                    market_type=MarketType.SPOT,
                    instrument_id=instrument_id,
                    event_time=at,
                    received_time=at,
                    source="n01.fixture",
                    trade_id=f"{instrument_id}-{offset}",
                    price=100 + offset,
                    quantity=1,
                    side="buy",
                )
            )
        for event_type in EventType:
            lifecycle.commit_action(
                _event(f"lifecycle-{instrument_id}-{event_type}", instrument_id).model_copy(
                    update={"event_type": event_type}
                ),
                LifecycleAction.START,
            )

    assert len(runtime._dedupe) <= runtime._dedupe_capacity == 3  # explicit FIFO capacity
    assert len(runtime.worker_exceptions) <= runtime._worker_exception_capacity == 2  # deque maxlen
    assert set(runtime._locks) == set(N01_INSTRUMENTS)  # fixed N01 universe
    assert set(runtime.state_manager._records) == set(N01_INSTRUMENTS)  # fixed N01 universe
    assert set(rolling._states) == set(N01_INSTRUMENTS)  # fixed N01 universe
    assert all(len(state.trades) == state.trades.maxlen == 120 for state in rolling._states.values())
    assert len(lifecycle._active) == len(N01_INSTRUMENTS) * len(EventType)  # finite event type universe
    print(
        {
            "runtime_dedupe": len(runtime._dedupe),
            "runtime_locks": len(runtime._locks),
            "state_records": len(runtime.state_manager._records),
            "rolling_trade_windows": {key: len(value.trades) for key, value in rolling._states.items()},
            "timeline_active": len(lifecycle._active),
        }
    )
