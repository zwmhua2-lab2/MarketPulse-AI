import asyncio
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
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


# --- PostgreSQL lifecycle ownership evidence (N01-VAL-FIX-01) -----------------
#
# Finding N01-VAL-F01. The original gate compared the disposable database's total
# `pg_stat_activity` row count with its pre-run baseline in the same instant that
# `await engine.dispose()` returned, filtering only by `datname`. A captured
# reproduction of that gate's `{'sessions': 1}` observation shows the extra row was
# not a harness connection at all:
#
#   pid 54926, backend_type = 'autovacuum worker', usename = null,
#   application_name = '', state = 'active', wait_event = 'IO/WALSync',
#   last_query = 'autovacuum: ANALYZE pg_catalog.pg_class'
#
# A server-side maintenance backend carries `datname` for the database it works on,
# so a `datname`-only filter cannot distinguish "a connection this test owns" from
# "a server process working on this test's disposable database".
#
# The replacement gate states the ownership boundary explicitly: it requires zero
# CLIENT backends in the disposable database, attributes every client session to a
# specific lifecycle cycle via a unique `application_name`, and waits for that
# exact condition under a hard deadline. The strict zero-residue requirement is
# preserved: no `baseline + 1` tolerance, no rerun-the-test retry and no fixed
# sleep standing in for proof of cleanup. Excluding server-owned maintenance
# backends does not weaken leak detection, because the harness can only ever leak
# client backends; `server_sessions` is retained purely as observation evidence.

LIFECYCLE_APPLICATION_PREFIX = "marketpulse-n01-vf01-lifecycle"
LIFECYCLE_OBSERVER_APPLICATION = "marketpulse-n01-vf01-observer"
LIFECYCLE_LEAK_CONTROL_APPLICATION = "marketpulse-n01-vf01-injected-leak"
LIFECYCLE_CLIENT_BACKEND_TYPE = "client backend"

# Bounded by measurement on this stack (SQLAlchemy 2.0.52 / asyncpg 0.31.0 /
# PostgreSQL in Docker): the longest observed time for a client-closed owned
# backend to leave `pg_stat_activity` was 8.3 ms (N01-VAL-FIX-01 diagnostics:
# 160 harness lifecycles plus 12 x 24 and 10 x 80 burst closes under CPU
# contention). The deadline is ~120x that observed maximum: large enough to absorb
# a slow server-side close, small enough that a leaked connection fails inside one
# second.
LIFECYCLE_CLEANUP_DEADLINE_SECONDS = 1.0
LIFECYCLE_POLL_INTERVAL_SECONDS = 0.002

_ACTIVITY_QUERY = """
SELECT pid, application_name, usename, state, backend_type, wait_event_type, wait_event,
       backend_start, state_change, xact_start, left(query, 120) AS last_query
FROM pg_stat_activity
WHERE datname = :database_name
ORDER BY pid
"""


@dataclass(frozen=True)
class _ActivitySnapshot:
    """One ownership-split observation of the disposable database."""

    rows: tuple[dict[str, object], ...]

    @property
    def client_sessions(self) -> int:
        """Backends the test could own or leak; the only thing the gate must clear."""
        return sum(1 for row in self.rows if row["backend_type"] == LIFECYCLE_CLIENT_BACKEND_TYPE)

    @property
    def server_sessions(self) -> int:
        """Server-owned maintenance backends (autovacuum worker and friends)."""
        return len(self.rows) - self.client_sessions

    @property
    def idle_in_transaction(self) -> int:
        return sum(1 for row in self.rows if row["state"] == "idle in transaction")


@dataclass(frozen=True)
class _CleanupObservation:
    """Outcome of one deadline-bounded wait for an owned lifecycle to fully close."""

    released: bool
    elapsed_seconds: float
    polls: int
    first_snapshot: _ActivitySnapshot
    final_snapshot: _ActivitySnapshot
    transients: tuple[_ActivitySnapshot, ...]
    server_backends: tuple[dict[str, object], ...]
    foreign_rows: tuple[dict[str, object], ...]


def _lifecycle_application_name(cycle_index: int) -> str:
    return f"{LIFECYCLE_APPLICATION_PREFIX}-cycle-{cycle_index + 1:02d}"


def _lifecycle_engine(database_url: str, application_name: str):
    """Engine whose PostgreSQL sessions are self-identifying for this lifecycle."""
    return create_async_engine(
        database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"application_name": application_name}},
    )


def _lifecycle_observer_engine(database_url: str):
    """Pooled read-only observer of the disposable database, on the primary server."""
    return create_async_engine(
        database_url,
        connect_args={"server_settings": {"application_name": LIFECYCLE_OBSERVER_APPLICATION}},
    )


async def _activity_snapshot(engine, database_name: str) -> _ActivitySnapshot:
    async with engine.connect() as connection:
        result = await connection.execute(text(_ACTIVITY_QUERY), {"database_name": database_name})
        rows = tuple(dict(row) for row in result.mappings())
    return _ActivitySnapshot(rows=rows)


async def _wait_for_lifecycle_cleanup(
    engine,
    database_name: str,
    owned_application_name: str,
    *,
    deadline_seconds: float = LIFECYCLE_CLEANUP_DEADLINE_SECONDS,
) -> _CleanupObservation:
    """Wait for one exact eventual condition: no client backend remains in the database.

    This waits on the observed state rather than on the scheduler: every poll is an
    ownership-attributed read, the loop exits as soon as the condition holds, and
    the hard deadline turns "still present" into a failure instead of a retry.
    """
    started = time.perf_counter()
    polls = 0
    first_snapshot: _ActivitySnapshot | None = None
    transients: list[_ActivitySnapshot] = []
    server_backends: dict[object, dict[str, object]] = {}
    foreign_rows: list[dict[str, object]] = []
    while True:
        snapshot = await _activity_snapshot(engine, database_name)
        polls += 1
        if first_snapshot is None:
            first_snapshot = snapshot
        for row in snapshot.rows:
            if row["backend_type"] != LIFECYCLE_CLIENT_BACKEND_TYPE:
                server_backends.setdefault(row["pid"], row)
        if snapshot.client_sessions:
            if len(transients) < 8:
                transients.append(snapshot)
            foreign_rows.extend(
                row
                for row in snapshot.rows
                if row["backend_type"] == LIFECYCLE_CLIENT_BACKEND_TYPE
                and row["application_name"] != owned_application_name
            )
        elapsed = time.perf_counter() - started
        if not snapshot.client_sessions or elapsed >= deadline_seconds:
            return _CleanupObservation(
                released=not snapshot.client_sessions,
                elapsed_seconds=elapsed,
                polls=polls,
                first_snapshot=first_snapshot,
                final_snapshot=snapshot,
                transients=tuple(transients),
                server_backends=tuple(server_backends.values()),
                foreign_rows=tuple(foreign_rows),
            )
        await asyncio.sleep(LIFECYCLE_POLL_INTERVAL_SECONDS)


def test_n01_twenty_real_postgres_lifecycles_dispose_tasks_queues_inflight_and_connections():
    async def scenario(database_name: str, database_url: str):
        observer = _lifecycle_observer_engine(Settings().database_url)
        try:
            baseline = await _activity_snapshot(observer, database_name)
            assert baseline.client_sessions == 0, baseline.rows
            assert baseline.idle_in_transaction == 0, baseline.rows
            cycle_evidence = []
            cleanup_evidence = []
            for cycle in range(20):
                application_name = _lifecycle_application_name(cycle)
                # The harness owns every connection and deliberately avoids retaining a pool
                # between cycles; explicit disposal below is still required for the AsyncEngine
                # lifecycle. The unique application_name makes every session this cycle owns
                # attributable during the cleanup wait below.
                engine = _lifecycle_engine(database_url, application_name)
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
                observation = await _wait_for_lifecycle_cleanup(
                    observer, database_name, application_name
                )
                assert observation.released, {
                    "cycle": cycle + 1,
                    "application_name": application_name,
                    "elapsed_seconds": observation.elapsed_seconds,
                    "remaining_rows": observation.final_snapshot.rows,
                }
                assert not observation.foreign_rows, {
                    "cycle": cycle + 1,
                    "foreign_rows": observation.foreign_rows,
                }
                assert observation.final_snapshot.idle_in_transaction == 0, {
                    "cycle": cycle + 1,
                    "rows": observation.final_snapshot.rows,
                }
                cleanup_evidence.append(
                    {
                        "cycle": cycle + 1,
                        "application_name": application_name,
                        "released_seconds": round(observation.elapsed_seconds, 6),
                        "polls": observation.polls,
                        "transient_snapshots": len(observation.transients),
                        "transient_rows": [snapshot.rows for snapshot in observation.transients],
                        "server_backends_seen": [
                            {
                                "pid": row["pid"],
                                "backend_type": row["backend_type"],
                                "state": row["state"],
                                "usename": row["usename"],
                                "last_query": row["last_query"],
                            }
                            for row in observation.server_backends
                        ],
                    }
                )
            final = await _activity_snapshot(observer, database_name)
            return baseline, cycle_evidence, cleanup_evidence, final
        finally:
            await observer.dispose()

    with _disposable_postgres_database() as (database_name, database_url):
        baseline, cycles, cleanup, final = asyncio.run(scenario(database_name, database_url))
    assert len(cycles) == 20
    assert len(cleanup) == 20
    assert final.client_sessions == 0, final.rows
    assert final.idle_in_transaction == 0, final.rows
    print(
        {
            "n01_lifecycle_cycles": len(cycles),
            "db_baseline": {
                "client_sessions": baseline.client_sessions,
                "server_sessions": baseline.server_sessions,
            },
            "db_lifecycle_cleanup": cleanup,
            "db_final": {
                "client_sessions": final.client_sessions,
                "server_sessions": final.server_sessions,
                "idle_in_transaction": final.idle_in_transaction,
            },
            "cleanup_deadline_seconds": LIFECYCLE_CLEANUP_DEADLINE_SECONDS,
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


def test_n01_injected_leaked_connection_is_detected_then_released():
    """Negative control: a deliberately held connection must never pass the lifecycle gate."""

    async def scenario(database_name: str, database_url: str):
        observer = _lifecycle_observer_engine(Settings().database_url)
        leak_engine = _lifecycle_engine(database_url, LIFECYCLE_LEAK_CONTROL_APPLICATION)
        try:
            clean_before = await _wait_for_lifecycle_cleanup(
                observer, database_name, LIFECYCLE_LEAK_CONTROL_APPLICATION
            )
            leak_session = async_sessionmaker(leak_engine, expire_on_commit=False)()
            await leak_session.execute(text("SELECT 1"))  # opens and then holds a transaction
            leak_pid = await leak_session.scalar(text("SELECT pg_backend_pid()"))
            detected = await _wait_for_lifecycle_cleanup(
                observer, database_name, LIFECYCLE_LEAK_CONTROL_APPLICATION
            )
            foreign = await _wait_for_lifecycle_cleanup(
                observer,
                database_name,
                _lifecycle_application_name(0),
                deadline_seconds=0.05,
            )
            await leak_session.close()
            await leak_engine.dispose()
            released = await _wait_for_lifecycle_cleanup(
                observer, database_name, LIFECYCLE_LEAK_CONTROL_APPLICATION
            )
            return clean_before, leak_pid, detected, foreign, released
        finally:
            await leak_engine.dispose()
            await observer.dispose()

    with _disposable_postgres_database() as (database_name, database_url):
        clean_before, leak_pid, detected, foreign, released = asyncio.run(
            scenario(database_name, database_url)
        )
    assert clean_before.released and not clean_before.first_snapshot.client_sessions
    # The injected connection is held open on purpose: the gate must not report a released
    # lifecycle, and it must name the exact owned session that is still alive.
    assert not detected.released
    assert detected.final_snapshot.client_sessions >= 1
    assert detected.final_snapshot.idle_in_transaction >= 1
    assert detected.elapsed_seconds >= LIFECYCLE_CLEANUP_DEADLINE_SECONDS
    assert any(row["pid"] == leak_pid for row in detected.final_snapshot.rows)
    assert any(
        row["application_name"] == LIFECYCLE_LEAK_CONTROL_APPLICATION
        for row in detected.final_snapshot.rows
    )
    # Asked about an unrelated lifecycle, the same detector attributes the session correctly.
    assert not foreign.released
    assert any(
        row["application_name"] == LIFECYCLE_LEAK_CONTROL_APPLICATION for row in foreign.foreign_rows
    )
    # Closing the injected connection returns the same detector to zero.
    assert released.released
    assert released.final_snapshot.client_sessions == 0
    assert released.final_snapshot.idle_in_transaction == 0
    print(
        {
            "leak_control_pid": leak_pid,
            "detected_client_sessions": detected.final_snapshot.client_sessions,
            "detected_idle_in_transaction": detected.final_snapshot.idle_in_transaction,
            "detected_seconds": round(detected.elapsed_seconds, 6),
            "released_seconds": round(released.elapsed_seconds, 6),
            "cleanup_deadline_seconds": LIFECYCLE_CLEANUP_DEADLINE_SECONDS,
        }
    )
