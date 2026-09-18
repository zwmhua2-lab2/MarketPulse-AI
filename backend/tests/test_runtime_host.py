"""PRE-01B-I1 — Integrated Runtime Host Core (focused deterministic gate).

This module is the offline half of PRE-01B-I1. It must never depend on the public internet:
the deterministic suite may not become flaky because of OKX or ISP conditions. Real public OKX
evidence is produced separately by `scripts/verify_pre_01b_runtime_host.py`.

What is proven here, on disposable PostgreSQL databases, using unmodified production code:

* the accepted lifecycle FSM (legal edges only, double-start rejected, double-stop idempotent);
* explicit enable gate and the operational contract (`TEST` requires injection, `REPLAY` is not
  a Host mode, `LIVE_PAPER` requires local-only / one worker / reload off);
* the deterministic 11-step startup order, including discrete recovery-only ingress whose
  warm-up frames never reach the Scanner;
* the readiness conjunction and honest 200/503 API surfaces (live / ready / health / runtime);
* PostgreSQL session advisory-lock fencing of a duplicate Host;
* the backpressure contract: safety-lane fullness is fatal, scanner-lane fullness degrades;
* protection isolation: scanner overload cannot delay or cancel the safety lane;
* provider stream task exit is fatal, while a transient feed gap only closes readiness;
* a durable non-running final state starts the protective runtime but stays non-ready;
* zero Real AI provider constructor calls;
* graceful and forced (cancelled-startup) shutdown leaving no orphan task, connection or
  engine.

PRE-01B-I1-FIX-01 adds the lifecycle-closure half of the same suite:

* the singleton fence connection is never left `idle in transaction` while the fence is held,
  and the fence survives the commit that ends that transaction;
* a fatal child failure becomes a lifespan-owned, already-*settled* terminal result that is
  observable during the run, and the ASGI lifespan turns it into a requested process stop;
* an engine disposal that fails — or that lies about succeeding — is reported instead of being
  mistaken for a clean stop, and one broken cleanup step never stops the others;
* a cancellation delivered mid-shutdown still collects every child, returns every resource and
  establishes a truthful `STOP_FAILED` terminal state before it propagates;
* an injected engine keeps its pool checkout baseline with no lost-checkout warning, even under
  the sibling cancellation that used to lose one;
* Host retention is bounded at the storage itself, not at the read path;
* an enabled Host must cover both accepted instrument symbols (extra symbols stay allowed).

Production code changed by PRE-01B-I1-FIX-01: `runtime_host.py`, `api/app.py`, `db/session.py`.
The gates listed above are unchanged by it, and no existing assertion was weakened to make it
pass.
"""

from __future__ import annotations

import asyncio
import gc
import re
import signal
import time
import warnings
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import anyio
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from marketpulse.clock import SystemClock
from marketpulse.config import Settings
from marketpulse.db.session import DatabaseResources, create_database_resources
from marketpulse.g2.runtime import ScannerPipeline
from marketpulse.g3.models import BestBidAsk, RunMode
from marketpulse.g3.provider import OpenAIResponsesProvider
from marketpulse.g3.service import PaperExecutionService
from marketpulse.g4.models import OperatorState, SystemState
from marketpulse.g4.orchestrator import SafetyRuntime
from marketpulse.g4.provider import OpenAIPositionReviewProvider
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.models import Instrument, MarketType, NormalizedBookTicker
from marketpulse.runtime import HealthRegistry, HostLifecycleState, HostReadinessStatus
from marketpulse.runtime_host import (
    SCANNER_ERROR_SAMPLE_MAXLEN,
    STATE_HISTORY_MAXLEN,
    BoundedLane,
    DuplicateRuntimeHostError,
    HostConfigurationError,
    HostDependencies,
    HostInvariantError,
    HostTerminalResult,
    RuntimeHost,
    _AIDisabledSentinel,
)
from sqlalchemy import text
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BTC = "BTC-USDT"
ETH = "ETH-USDT"
INSTRUMENTS = (BTC, ETH)
DATABASE_PREFIX = "marketpulse_pre_01b_i1_"
# Deliberately tight Host intervals so a deterministic test never waits on a production-scale
# cadence. These are test settings, not contract constants: the accepted defaults stay 5s/60s.
FAST_HEARTBEAT_SECONDS = 0.5
FAST_TELEMETRY_SECONDS = 0.25
FAST_RECONCILIATION_SECONDS = 2.0
TERMINAL_STATES = {
    HostLifecycleState.STOPPED,
    HostLifecycleState.STOP_FAILED,
    HostLifecycleState.FAILED,
}


# ---------------------------------------------------------------------------------------
# Disposable PostgreSQL (same accepted pattern as the N01 suite; the primary DB is untouched)
# ---------------------------------------------------------------------------------------


@contextmanager
def _disposable_postgres_database() -> Iterator[tuple[str, str]]:
    primary_url = Settings().database_url
    database_name = f"{DATABASE_PREFIX}{uuid4().hex[:12]}"
    database_url = f"{primary_url.rsplit('/', 1)[0]}/{database_name}"
    backend = REPOSITORY_ROOT / "backend"

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


def _run(scenario: Callable[[str], Coroutine[Any, Any, None]]) -> None:
    """Own the disposable database outside the event loop, then run one async scenario."""
    with _disposable_postgres_database() as (_, url):
        asyncio.run(scenario(url))


# ---------------------------------------------------------------------------------------
# Controlled provider boundary (a local fake, never a substitute for the real OKX gate)
# ---------------------------------------------------------------------------------------


class ControlledProvider:
    """Deterministic stand-in for the accepted OKX provider boundary.

    Every attribute it exposes is one the accepted `OKXLiveProvider` also exposes, so the Host
    reads it through exactly the same path. Nothing here fabricates an OKX fact: frames are
    explicitly `source="controlled-fake"`, and a "disconnect" is a real end of the generator,
    not a pretend one.
    """

    def __init__(
        self,
        instruments: tuple[str, ...] = INSTRUMENTS,
        *,
        interval: float = 0.05,
        instrument_metadata_delay: float = 0.0,
        disconnect_after: int | None = None,
    ) -> None:
        self.instrument_ids = instruments
        self.interval = interval
        self.instrument_metadata_delay = instrument_metadata_delay
        self.disconnect_after = disconnect_after
        self.connection_attempts = 0
        self.reconnects = 0
        self.frames_emitted = 0
        self.stream_closed = False
        self._resume = anyio.Event()
        self._resume.set()

    async def instruments(self, market_type: str = "SPOT") -> list[Instrument]:
        if self.instrument_metadata_delay:
            await asyncio.sleep(self.instrument_metadata_delay)
        return [
            Instrument(
                base_asset=item.split("-")[0],
                quote_asset=item.split("-")[1],
                market_type=MarketType.SPOT,
                instrument_id=item,
                trading_symbol=item,
            )
            for item in self.instrument_ids
        ]

    def hold_feed(self) -> None:
        """Simulate a transient provider gap: frames stop while the task stays alive."""
        self._resume = anyio.Event()

    def resume_feed(self) -> None:
        self._resume.set()

    def stream(self, channels: list[dict[str, str]]) -> AsyncIterator[NormalizedBookTicker]:
        async def generator() -> AsyncIterator[NormalizedBookTicker]:
            self.connection_attempts += 1
            try:
                while True:
                    await self._resume.wait()
                    now = datetime.now(UTC)
                    for item in self.instrument_ids:
                        self.frames_emitted += 1
                        base, quote = item.split("-")
                        yield NormalizedBookTicker(
                            base_asset=base,
                            quote_asset=quote,
                            market_type=MarketType.SPOT,
                            instrument_id=item,
                            event_time=now,
                            received_time=now,
                            source="controlled-fake",
                            bid_price=100.0,
                            bid_quantity=1.0,
                            ask_price=100.1,
                            ask_quantity=1.0,
                            tradable=True,
                        )
                        if (
                            self.disconnect_after is not None
                            and self.frames_emitted >= self.disconnect_after
                        ):
                            return
                    await asyncio.sleep(self.interval)
            finally:
                self.stream_closed = True

        return generator()


class Harness:
    """Host plus the owned/injected resources for one scenario."""

    def __init__(
        self,
        settings: Settings,
        provider: ControlledProvider,
        *,
        inject_database: bool = True,
        seed_system_state: SystemState = SystemState.RUNNING,
        seed_operator_state: OperatorState = OperatorState.NORMAL,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.inject_database = inject_database
        self.seed_system_state = seed_system_state
        self.seed_operator_state = seed_operator_state
        self.resources = create_database_resources(settings, application_name="pre-01b-i1-owned")
        self.lock_resources = create_database_resources(
            settings, application_name="pre-01b-i1-lock"
        )
        self.health = HealthRegistry()
        self.clock = SystemClock()
        self.host: RuntimeHost | None = None

    async def seed(self) -> None:
        """Make the disposable database look like an already-running deployment."""
        execution = PaperExecutionService(
            self.resources.session_factory,
            _no_quote,
            _version_zero,
            clock=self.clock,
        )
        states = SystemStateService(self.resources.session_factory, clock=self.clock)
        await states.ensure(RunMode.TEST)
        await states.transition(
            RunMode.TEST,
            operator_state=self.seed_operator_state,
            system_state=self.seed_system_state,
            reason="pre_01b_i1_seed",
        )
        await execution.bootstrap_account(RunMode.TEST)

    def build(self) -> RuntimeHost:
        self.host = RuntimeHost(
            self.settings,
            dependencies=HostDependencies(
                provider=self.provider,
                database=self.resources if self.inject_database else None,
                lock_database=self.lock_resources,
                clock=self.clock,
                health=self.health,
            ),
        )
        return self.host

    async def dispose(self) -> None:
        await self.resources.dispose()
        await self.lock_resources.dispose()


async def _no_quote(instrument_id: str) -> BestBidAsk:
    raise RuntimeError(f"harness_has_no_quote:{instrument_id}")


async def _version_zero(instrument_id: str) -> int:
    return 0


def _settings(database_url: str | None = None, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "run_mode": "TEST",
        "runtime_host_enabled": True,
        "runtime_host_instruments": "BTC-USDT,ETH-USDT",
        "runtime_heartbeat_interval_seconds": FAST_HEARTBEAT_SECONDS,
        "runtime_telemetry_interval_seconds": FAST_TELEMETRY_SECONDS,
        "runtime_reconciliation_interval_seconds": FAST_RECONCILIATION_SECONDS,
        "runtime_market_freshness_seconds": 1.0,
        "runtime_shutdown_grace_seconds": 5.0,
        "runtime_shutdown_dispose_seconds": 5.0,
        "runtime_startup_timeout_seconds": 20.0,
    }
    if database_url is not None:
        values["database_url"] = database_url
    values.update(overrides)
    return Settings(**values)


async def _wait_for(predicate: Callable[[], bool], timeout: float = 15.0, interval: float = 0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return predicate()


async def _settled_orphan_tasks() -> list[str]:
    """Task names still alive after the event loop has been given a chance to reap them."""
    for _ in range(10):
        await asyncio.sleep(0.02)
    current = asyncio.current_task()
    return [
        task.get_name() for task in asyncio.all_tasks() if not task.done() and task is not current
    ]


# =======================================================================================
# 1. Configuration gate — fails closed, before any resource is opened
# =======================================================================================


def test_disabled_host_fails_closed_without_opening_anything():
    host = RuntimeHost(_settings(runtime_host_enabled=False))

    async def scenario() -> None:
        with pytest.raises(HostConfigurationError, match="HOST_DISABLED"):
            await host.start()

    asyncio.run(scenario())
    # Refused before any resource was touched: nothing was activated, so nothing is STOPPED.
    assert host.state is HostLifecycleState.CREATED
    report = host.readiness()
    assert report.ready is False
    assert report.status is HostReadinessStatus.FAIL_CLOSED
    assert report.reasons == ["HOST_DISABLED"]


def test_test_mode_requires_injected_dependencies():
    host = RuntimeHost(_settings())

    async def scenario() -> None:
        with pytest.raises(
            HostConfigurationError, match="HOST_TEST_REQUIRES_INJECTED_DEPENDENCIES"
        ):
            await host.start()

    asyncio.run(scenario())
    assert host.state is HostLifecycleState.CREATED


def test_replay_is_not_a_runtime_host_mode():
    host = RuntimeHost(
        _settings(run_mode="REPLAY"), dependencies=HostDependencies(provider=ControlledProvider())
    )

    async def scenario() -> None:
        with pytest.raises(HostConfigurationError, match="REPLAY_IS_NOT_A_RUNTIME_HOST_MODE"):
            await host.start()

    asyncio.run(scenario())


def test_live_paper_requires_the_local_operational_contract():
    host = RuntimeHost(
        _settings(run_mode="LIVE_PAPER", runtime_reload=True),
        dependencies=HostDependencies(provider=ControlledProvider()),
    )

    async def scenario() -> None:
        with pytest.raises(HostConfigurationError, match="LIVE_PAPER_REQUIRES_ONE_WORKER"):
            await host.start()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("runtime_startup_timeout_seconds", 0.0),
        ("runtime_shutdown_grace_seconds", -1.0),
        ("runtime_shutdown_dispose_seconds", 0.0),
        ("runtime_market_freshness_seconds", 0.0),
        ("runtime_heartbeat_interval_seconds", float("inf")),
        ("runtime_reconciliation_interval_seconds", float("nan")),
        ("runtime_telemetry_interval_seconds", -2.0),
        ("runtime_safety_queue_capacity", 0),
        ("runtime_safety_queue_capacity", -3),
    ],
)
def test_non_positive_or_non_finite_host_settings_are_rejected(setting, value):
    host = RuntimeHost(
        _settings(**{setting: value}),
        dependencies=HostDependencies(provider=ControlledProvider()),
    )

    async def scenario() -> None:
        with pytest.raises(HostConfigurationError, match="invalid_host_setting"):
            await host.start()

    asyncio.run(scenario())


@pytest.mark.parametrize("value", [0, -3])
def test_non_positive_scanner_lane_capacity_never_builds_an_unbounded_queue(value):
    """The scanner lane is built eagerly, so a bad capacity can never reach a queue at all."""
    with pytest.raises(HostConfigurationError, match="lane_capacity_must_be_positive"):
        RuntimeHost(
            _settings(runtime_scanner_queue_capacity=value),
            dependencies=HostDependencies(provider=ControlledProvider()),
        )


def test_empty_instrument_list_is_rejected():
    host = RuntimeHost(
        _settings(runtime_host_instruments=" , "),
        dependencies=HostDependencies(provider=ControlledProvider()),
    )

    async def scenario() -> None:
        with pytest.raises(HostConfigurationError, match="NO_INSTRUMENTS_CONFIGURED"):
            await host.start()

    asyncio.run(scenario())


# =======================================================================================
# 2. Lifecycle FSM
# =======================================================================================


def test_illegal_lifecycle_transition_is_an_invariant_violation():
    host = RuntimeHost(_settings())
    with pytest.raises(HostInvariantError, match="illegal_host_transition"):
        host._transition(HostLifecycleState.READY)
    assert host.state is HostLifecycleState.CREATED
    assert host.ownership_snapshot()["state_history"] == [
        (host.ownership_snapshot()["state_history"][0][0], "CREATED")
    ]


def test_double_start_is_an_invariant_violation():
    """One Host per process lifetime; a second start is a caller bug, never a restart."""

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider())
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                with pytest.raises(
                    HostInvariantError, match="double_start_is_an_invariant_violation"
                ):
                    await host.start()
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


def test_stop_is_idempotent_and_disposes_the_engine_it_owns():
    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(), inject_database=False)
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            owned = host._db
            assert owned is not None and owned.disposed is False
            assert host.ownership_snapshot()["owns_database"] is True
            assert host.ownership_snapshot()["engine_disposed"] is False
            await host.stop()
            await host.stop()
            assert host.state is HostLifecycleState.STOPPED
            assert host.ownership_snapshot()["shutdown_failures"] == []
            assert owned.disposed is True
            assert harness.resources.disposed is False  # the Host never owned this one
        finally:
            await harness.dispose()

    _run(scenario)


def test_injected_engine_is_never_disposed_by_the_host():
    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider())
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            await host.stop()
            assert harness.resources.disposed is False
            assert host.ownership_snapshot()["shutdown_failures"] == []
        finally:
            await harness.dispose()

    _run(scenario)


# =======================================================================================
# 3. Deterministic startup, recovery-only ingress and the readiness conjunction
# =======================================================================================


def test_startup_reaches_ready_with_the_accepted_order_and_conjunction():
    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider())
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert host.state is HostLifecycleState.READY, host.readiness().as_payload()
                assert host.readiness().reasons == []
                assert [entry[1] for entry in host.ownership_snapshot()["state_history"]] == [
                    "CREATED",
                    "STARTING",
                    "ACQUIRING_SINGLETON",
                    "RECOVERY_INGRESS",
                    "RECOVERING",
                    "STARTING_RUNTIME",
                    "WAITING_FOR_READINESS",
                    "READY",
                ]
                assert set(host.children_live) == {
                    "provider_stream",
                    f"safety:{BTC}",
                    f"safety:{ETH}",
                    "scanner",
                    "eventruntime_monitor",
                    "heartbeat",
                    "reconciliation",
                    "telemetry",
                }
                snapshot = host.ownership_snapshot()
                assert snapshot["singleton_lock_held"] is True
                assert snapshot["singleton_connection_present"] is True
                assert snapshot["gates"] == {
                    "risk_admission": True,
                    "ingress": True,
                    "safety": True,
                    "scanner": True,
                }
                runtime = host.event_runtime
                assert runtime is not None
                assert runtime.live_worker_count == runtime.worker_count == 4
                assert runtime.done_worker_count == 0

                assert await _wait_for(lambda: host.market_state.fresh_tradable(BTC))
                assert await _wait_for(lambda: host.market_state.fresh_tradable(ETH))
                telemetry = host.telemetry()
                assert telemetry["durable_state"] == {
                    "system_state": "RUNNING",
                    "operator_state": "NORMAL",
                    "blocking_incidents": 0,
                }
                assert telemetry["reconciliation"]["startup_ok"] is True
                assert telemetry["counters"]["safety_overflow"] == 0
                assert telemetry["counters"]["host_invariant_violations"] == 0
                assert telemetry["readiness"]["ready"] is True
                # The P2 surface is bounded, monotonic and honest about its probe.
                assert isinstance(telemetry["process"]["rss_bytes"], int)
                assert telemetry["process"]["rss_mb"] != 0
                assert telemetry["lanes"]["safety"][BTC]["capacity"] == 64
                assert telemetry["eventruntime"]["worker_count_configured"] == 4
            finally:
                await host.stop()
            assert host.state is HostLifecycleState.STOPPED
            assert host.ownership_snapshot()["shutdown_failures"] == []
            assert host.children_live == ()
            assert await _settled_orphan_tasks() == []
        finally:
            await harness.dispose()

    _run(scenario)


def test_warmup_frames_are_never_replayed_into_the_scanner(monkeypatch):
    """Recovery-only ingress updates market state and freshness telemetry and nothing else."""
    observed: list[tuple[str, bool]] = []
    original = ScannerPipeline.ingest
    spy: dict[str, Any] = {"host": None}

    async def spying_ingest(self, market_event, auxiliary=None):
        host = spy["host"]
        observed.append((host.state.value, host.ownership_snapshot()["gates"]["scanner"]))
        return await original(self, market_event, auxiliary)

    monkeypatch.setattr(ScannerPipeline, "ingest", spying_ingest)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(interval=0.02))
        try:
            await harness.seed()
            host = harness.build()
            spy["host"] = host
            await host.start()
            try:
                await asyncio.sleep(0.5)
                assert host.telemetry()["counters"]["scanner_processed"] > 0
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)
    assert observed, "the scanner lane must have produced evidence to judge"
    assert all(scanner_gate for _, scanner_gate in observed), (
        "no frame may reach the scanner while runtime ingress is still closed"
    )
    assert {
        state for state, _ in observed if state in {
            "STARTING",
            "ACQUIRING_SINGLETON",
            "RECOVERY_INGRESS",
            "RECOVERING",
            "STARTING_RUNTIME",
        }
    } == set()


def test_safety_lane_precedes_the_scanner_for_every_forwarded_frame():
    provider = ControlledProvider(interval=0.02)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), provider)
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                order_violations: list[tuple[int, int]] = []
                for _ in range(10):
                    counters = host.telemetry()["counters"]
                    if counters["safety_processed"] > counters["ingress_forwarded_to_safety"]:
                        order_violations.append(
                            (counters["safety_processed"], counters["ingress_forwarded_to_safety"])
                        )
                    await asyncio.sleep(0.05)
                assert order_violations == [], (
                    "safety must never process a frame the ingress has not forwarded"
                )
                # Freeze the producer so every accepted frame can finish draining: only then is
                # an equality assertion a proof instead of a race.
                provider.hold_feed()
                assert await _wait_for(
                    lambda: (
                        host.telemetry()["counters"]["safety_processed"]
                        == host.telemetry()["counters"]["ingress_forwarded_to_safety"]
                        and host.telemetry()["counters"]["scanner_processed"]
                        == host.telemetry()["counters"]["ingress_forwarded_to_safety"]
                        and host.telemetry()["counters"]["ingress_forwarded_to_safety"] > 5
                    )
                ), host.telemetry()["counters"]
                counters = host.telemetry()["counters"]
                assert counters["safety_processed"] == counters["ingress_forwarded_to_safety"]
                assert counters["scanner_processed"] == counters["ingress_forwarded_to_safety"]
                assert counters["safety_overflow"] == 0
                assert counters["scanner_rejected"] == 0
                assert (
                    host.telemetry()["lanes"]["safety"][BTC]["size"] == 0
                    and host.telemetry()["lanes"]["safety"][ETH]["size"] == 0
                    and host.telemetry()["lanes"]["scanner"]["size"] == 0
                )
            finally:
                provider.resume_feed()
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


def test_transient_feed_gap_closes_readiness_and_a_fresh_feed_restores_it():
    provider = ControlledProvider(interval=0.02)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url, runtime_market_freshness_seconds=0.3), provider)
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                provider.hold_feed()
                assert await _wait_for(
                    lambda: host.state is not HostLifecycleState.READY
                ), host.readiness().as_payload()
                report = host.readiness()
                assert report.ready is False
                assert report.status is HostReadinessStatus.FAIL_CLOSED
                assert "MARKET_DATA_STALE" in report.reasons
                # A gap is not a task exit: the provider child and the safety lane stay alive.
                assert "provider_stream" in host.children_live
                assert host.failed is False

                provider.resume_feed()
                assert await _wait_for(
                    lambda: host.state is HostLifecycleState.READY
                ), host.readiness().as_payload()
                assert host.readiness().reasons == []
            finally:
                await host.stop()
            assert host.ownership_snapshot()["shutdown_failures"] == []
        finally:
            await harness.dispose()

    _run(scenario)


def test_durable_safe_mode_starts_the_protective_runtime_but_stays_not_ready():
    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url), ControlledProvider(), seed_system_state=SystemState.SAFE_MODE
        )
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert host.state is HostLifecycleState.FAIL_CLOSED
                report = host.readiness()
                assert report.ready is False
                assert report.status is HostReadinessStatus.FAIL_CLOSED
                assert "DURABLE_STATE_INVALID" in report.reasons
                assert "RECOVERY_INCOMPLETE" in report.reasons
                # The protective runtime is up even though readiness is refused.
                assert "provider_stream" in host.children_live
                assert f"safety:{BTC}" in host.children_live
                assert host.telemetry()["durable_state"]["system_state"] == "SAFE_MODE"
                assert host.telemetry()["reconciliation"]["safe_mode_latched_by_host"] is False
            finally:
                await host.stop()
            assert host.ownership_snapshot()["shutdown_failures"] == []
        finally:
            await harness.dispose()

    _run(scenario)


# =======================================================================================
# 4. Duplicate-Host fence
# =======================================================================================


def test_duplicate_host_is_fenced_by_the_postgres_advisory_lock():
    async def scenario(url: str) -> None:
        first = Harness(_settings(url), ControlledProvider())
        second = Harness(_settings(url), ControlledProvider(interval=0.5))
        try:
            await first.seed()
            host_one = first.build()
            await host_one.start()
            try:
                assert host_one.ownership_snapshot()["singleton_lock_held"] is True
                host_two = second.build()
                with pytest.raises(DuplicateRuntimeHostError):
                    await host_two.start()
                # The refused Host released everything it opened on the way in.
                snapshot = host_two.ownership_snapshot()
                assert host_two.failed is True
                assert snapshot["singleton_lock_held"] is False
                assert snapshot["singleton_connection_present"] is False
                assert host_two.state is HostLifecycleState.STOPPED
                assert second.lock_resources.disposed is False
            finally:
                await host_one.stop()
            assert first.lock_resources.disposed is False
        finally:
            await first.dispose()
            await second.dispose()

    _run(scenario)


# =======================================================================================
# 5. Backpressure and protection isolation
# =======================================================================================


def test_bounded_lane_reports_capacity_high_water_and_counters():
    lane = BoundedLane(name="probe", capacity=2)
    assert lane.try_send(1) is True
    assert lane.try_send(2) is True
    assert lane.try_send(3) is False
    assert lane.telemetry() == {
        "size": 2,
        "capacity": 2,
        "high_water": 2,
        "processed": 0,
        "rejected": 0,
        "overflow": 0,
    }


def test_safety_lane_overflow_is_fatal_never_lossy(monkeypatch):
    async def stalled_safety(self, run_mode, bbo, *, force_reevaluation=False, now=None):
        await asyncio.sleep(60)
        return {}

    monkeypatch.setattr(SafetyRuntime, "on_market_data", stalled_safety)

    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url, runtime_safety_queue_capacity=2), ControlledProvider(interval=0.01)
        )
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            assert await _wait_for(lambda: host.failed), host.failure_reason
            assert (host.failure_reason or "").startswith("critical_child_failure")
            assert host.safety_overflow_count > 0
            assert host.ownership_snapshot()["gates"]["risk_admission"] is False
            assert await _wait_for(lambda: host.state in TERMINAL_STATES)
            assert host.state is HostLifecycleState.STOPPED
            assert host.children_live == ()
            assert await _settled_orphan_tasks() == []
        finally:
            await harness.dispose()

    _run(scenario)


def test_scanner_overload_degrades_without_blocking_the_safety_lane(monkeypatch):
    async def slow_ingest(self, market_event, auxiliary=None):
        await asyncio.sleep(0.5)
        return []

    monkeypatch.setattr(ScannerPipeline, "ingest", slow_ingest)

    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url, runtime_scanner_queue_capacity=2), ControlledProvider(interval=0.01)
        )
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert await _wait_for(
                    lambda: host.telemetry()["counters"]["scanner_rejected"] > 0
                )
                counters = host.telemetry()["counters"]
                assert counters["scanner_rejected"] > 0
                assert counters["safety_processed"] > 0
                assert counters["safety_overflow"] == 0
                assert host.telemetry()["lanes"]["scanner"]["rejected"] > 0
                # Impaired, not failed: readiness is honestly DEGRADED/503 and protection runs.
                assert await _wait_for(
                    lambda: host.readiness().status is HostReadinessStatus.DEGRADED
                )
                assert host.state is HostLifecycleState.DEGRADED
                assert host.readiness().ready is False
                assert host.failed is False
                assert f"safety:{BTC}" in host.children_live
                assert f"safety:{ETH}" in host.children_live
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


# =======================================================================================
# 6. Failure classification: provider task exit, forced shutdown
# =======================================================================================


def test_provider_stream_task_exit_is_fatal():
    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url), ControlledProvider(interval=0.01, disconnect_after=6)
        )
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            assert await _wait_for(lambda: host.failed), host.failure_reason
            assert (host.failure_reason or "").startswith("critical_child_failure")
            assert await _wait_for(lambda: host.state in TERMINAL_STATES)
            assert host.children_live == ()
            assert await _settled_orphan_tasks() == []
        finally:
            await harness.dispose()

    _run(scenario)


def test_cancelled_startup_still_runs_the_bounded_cleanup():
    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url), ControlledProvider(instrument_metadata_delay=30.0)
        )
        try:
            await harness.seed()
            host = harness.build()
            task = asyncio.create_task(host.start())
            assert await _wait_for(
                lambda: host.state is HostLifecycleState.RECOVERY_INGRESS
            )
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await _wait_for(lambda: host.state in TERMINAL_STATES), host.state
            assert host.children_live == ()
            assert host.ownership_snapshot()["singleton_lock_held"] is False
            assert host.ownership_snapshot()["singleton_connection_present"] is False
            assert await _settled_orphan_tasks() == []
        finally:
            await harness.dispose()

    _run(scenario)


# =======================================================================================
# 7. No Real AI is ever constructed
# =======================================================================================


def test_no_real_ai_provider_is_ever_constructed(monkeypatch):
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Host Core V1 must not construct a Real AI provider")

    monkeypatch.setattr(OpenAIResponsesProvider, "__init__", forbidden)
    monkeypatch.setattr(OpenAIPositionReviewProvider, "__init__", forbidden)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider())
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert host.state is HostLifecycleState.READY
                assert isinstance(host._safety, SafetyRuntime)
                assert isinstance(host._safety.reevaluation, _AIDisabledSentinel)
                assert host.telemetry()["safety_reevaluation"] == {
                    "enabled": False,
                    "inflight": 0,
                    "note": "ai_reevaluation_disabled_in_host_core_v1",
                }
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


def test_ai_disabled_sentinel_fails_closed_on_any_use():
    sentinel = _AIDisabledSentinel()
    with pytest.raises(HostInvariantError, match="ai_reevaluation_disabled"):
        _ = sentinel.reevaluate


# =======================================================================================
# 8. Readiness / liveness API surfaces
# =======================================================================================


class _StubHost:
    """Read-only stand-in that pins the HTTP contract of the four API surfaces."""

    def __init__(self, *, ready: bool, status: str) -> None:
        self._ready = ready
        self._status = status

    def live_payload(self) -> dict[str, object]:
        return {"status": "alive", "run_mode": "TEST", "host_state": self._status}

    def ready_payload(self) -> dict[str, object]:
        return {
            "ready": self._ready,
            "status": "READY" if self._ready else self._status,
            "reasons": [] if self._ready else ["MARKET_DATA_STALE"],
            "evaluated_at": "2026-01-01T00:00:00+00:00",
            "run_mode": "TEST",
            "host_state": self._status,
        }

    def health_payload(self) -> dict[str, object]:
        return {
            "status": "ok" if self._ready else "FAIL_CLOSED",
            "run_mode": "TEST",
            "local_only": True,
            "host_state": self._status,
            "ready": self._ready,
            "reasons": [] if self._ready else ["MARKET_DATA_STALE"],
            "checks": {},
        }

    def runtime_payload(self) -> dict[str, object]:
        return {"run_mode": "TEST", "local_only": True, "version": "v1", "host": {"stub": True}}


def test_api_surfaces_stay_distinct(monkeypatch):
    import marketpulse.api.app as app_module

    monkeypatch.setattr(app_module, "settings", _settings(runtime_host_enabled=False))
    client = TestClient(app_module.app)
    app_module.app.state.host = None

    assert client.get("/api/v1/live").status_code == 200
    refused = client.get("/api/v1/ready")
    assert refused.status_code == 503
    refused_payload = refused.json()
    assert refused_payload["ready"] is False
    assert refused_payload["status"] == "FAIL_CLOSED"
    assert refused_payload["reasons"] == ["HOST_DISABLED"]
    assert isinstance(refused_payload["evaluated_at"], str)
    assert refused_payload["run_mode"] == "TEST"
    assert refused_payload["local_only"] is True
    assert refused_payload["host_state"] is None
    assert client.get("/api/v1/health").json()["status"] == "disabled"

    app_module.app.state.host = _StubHost(ready=False, status="FAIL_CLOSED")
    assert client.get("/api/v1/live").status_code == 200
    stale = client.get("/api/v1/ready")
    assert stale.status_code == 503
    stale_payload = stale.json()
    assert stale_payload["ready"] is False
    assert stale_payload["status"] == "FAIL_CLOSED"
    assert stale_payload["reasons"] == ["MARKET_DATA_STALE"]
    assert isinstance(stale_payload["evaluated_at"], str)
    assert stale_payload["local_only"] is True
    assert stale_payload["host_state"] == "FAIL_CLOSED"
    assert client.get("/api/v1/health").json()["status"] == "FAIL_CLOSED"

    app_module.app.state.host = _StubHost(ready=True, status="READY")
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    ready_payload = ready.json()
    assert ready_payload["ready"] is True
    assert ready_payload["status"] == "READY"
    assert ready_payload["reasons"] == []
    assert isinstance(ready_payload["evaluated_at"], str)
    assert ready_payload["local_only"] is True
    assert ready_payload["host_state"] == "READY"
    assert client.get("/api/v1/health").json()["status"] == "ok"

    openapi = client.get("/openapi.json").json()
    ready_responses = openapi["paths"]["/api/v1/ready"]["get"]["responses"]
    assert ready_responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadinessResponse"
    }
    assert ready_responses["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadinessResponse"
    }

    # Detailed telemetry never becomes anonymously reachable.
    assert client.get("/api/v1/runtime").status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "dev-only-change-this-password"},
    )
    authorized = client.get(
        "/api/v1/runtime", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert authorized.status_code == 200
    assert authorized.json()["host"] == {"stub": True}
    app_module.app.state.host = None


def test_lifespan_leaves_no_host_and_reports_not_ready_when_disabled(monkeypatch):
    import marketpulse.api.app as app_module

    monkeypatch.setattr(app_module, "settings", _settings(runtime_host_enabled=False))
    with TestClient(app_module.app) as client:
        assert app_module.app.state.host is None
        assert client.get("/api/v1/live").json()["status"] == "disabled"
        assert client.get("/api/v1/ready").status_code == 503
        assert client.get("/api/v1/ready").json()["reasons"] == ["HOST_DISABLED"]
    assert app_module.app.state.host is None


# =======================================================================================
# 9. Lifecycle closure (PRE-01B-I1-FIX-01): P1-01 … P2-05
# =======================================================================================

#: The application_name the harness gives its dedicated fence engine. Using it here makes the
#: `pg_stat_activity` / `pg_locks` probes below attribute exactly one backend, deterministically.
FENCE_APPLICATION_NAME = "pre-01b-i1-lock"


async def _fence_backend_rows(engine: Any) -> list[tuple[str | None, int]]:
    """`(backend state, advisory locks held)` for the dedicated fence connection.

    Reported by PostgreSQL itself rather than asserted from inside the Host, because the whole
    point of P1-01 is what *another* session observes: a fence connection that is idle but still
    holds a session advisory lock.
    """
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT a.state, count(l.pid) FROM pg_stat_activity a "
                "LEFT JOIN pg_locks l ON l.pid = a.pid AND l.locktype = 'advisory' "
                "WHERE a.application_name = :name AND a.datname = current_database() "
                "GROUP BY a.state"
            ),
            {"name": FENCE_APPLICATION_NAME},
        )
        return [(row[0], row[1]) for row in result.all()]


def test_the_fence_connection_is_never_idle_in_transaction():
    """P1-01: the fence holds a *session* lock without holding a transaction open."""

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(interval=0.02))
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert host.state is HostLifecycleState.READY
                assert host.ownership_snapshot()["singleton_lock_held"] is True

                rows: list[tuple[str | None, int]] = []
                deadline = time.monotonic() + 10.0
                while time.monotonic() < deadline:
                    rows = await _fence_backend_rows(harness.resources.engine)
                    if rows and all(state == "idle" for state, _ in rows):
                        break
                    await asyncio.sleep(0.05)

                assert rows, "the dedicated fence connection must be visible in pg_stat_activity"
                states = {state for state, _ in rows}
                assert "idle in transaction" not in states, rows
                assert states == {"idle"}, rows
                # Ending the transaction must not have ended the fence: PostgreSQL still reports
                # the session's advisory lock as held by that backend.
                assert sum(locks for _, locks in rows) >= 1, rows
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


def test_a_fatal_child_failure_publishes_a_settled_terminal_result_during_the_run():
    """P1-02 (Host half): the fatal outcome is observable while the run is still owned."""

    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url), ControlledProvider(interval=0.01, disconnect_after=6)
        )
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            # No external shutdown and no manual `stop()` happen before this resolves: the
            # result must arrive from the Host's own failure path.
            result = await asyncio.wait_for(host.wait_for_terminal_result(), timeout=25.0)
            assert isinstance(result, HostTerminalResult)
            assert result.reason.startswith("critical_child_failure"), result.reason
            assert result.state is HostLifecycleState.STOPPED
            assert result.shutdown_failures == ()
            # Settled, not mid-flight: by the time the result is published, cleanup already ran.
            assert host.state is HostLifecycleState.STOPPED
            snapshot = host.ownership_snapshot()
            assert snapshot["singleton_lock_held"] is False
            assert snapshot["singleton_connection_present"] is False
            assert snapshot["gates"] == {
                "risk_admission": False,
                "ingress": False,
                "safety": False,
                "scanner": False,
            }
            assert host.children_live == ()
            assert await _settled_orphan_tasks() == []
            # An orderly stop never publishes it: the result means "the runtime died".
            assert host.terminal_result is result
        finally:
            await harness.dispose()

    _run(scenario)


def test_the_lifespan_owns_the_fatal_result_and_requests_the_process_stop(monkeypatch):
    """P1-02 (lifespan half): the real lifespan observes the death and asks the OS to stop.

    Uses the real `RuntimeHost` (real startup, real children, real failure publication) with the
    dependency injection `RunMode.TEST` already requires; only the process-level stop is
    recorded instead of delivered, because raising a real `SIGTERM` inside the test process is
    exactly the external action this test asserts is *requested*.
    """
    import marketpulse.api.app as app_module

    requested: list[int] = []
    provider = ControlledProvider(interval=0.01, disconnect_after=6)

    with _disposable_postgres_database() as (_, url):
        settings = _settings(url)
        harness = Harness(settings, provider)
        captured: dict[str, Any] = {}

        def build_injected_host(settings_arg: Settings) -> RuntimeHost:
            return RuntimeHost(
                settings_arg,
                dependencies=HostDependencies(
                    provider=harness.provider,
                    database=harness.resources,
                    lock_database=harness.lock_resources,
                    clock=harness.clock,
                    health=harness.health,
                ),
            )

        monkeypatch.setattr(app_module, "settings", settings)
        monkeypatch.setattr(app_module, "RuntimeHost", build_injected_host)
        monkeypatch.setattr(app_module.signal, "getsignal", lambda _signal: object())
        monkeypatch.setattr(app_module.signal, "raise_signal", requested.append)

        async def scenario() -> None:
            try:
                await harness.seed()
                with pytest.raises(RuntimeError, match="runtime_host_fatal"):
                    async with app_module.lifespan(app_module.app):
                        host = app_module.app.state.host
                        assert host is not None
                        captured["host"] = host
                        # The run phase. The lifespan's own watcher ends it, so the failure must
                        # reach this boundary without any shutdown being sent to the process.
                        await host.wait_for_terminal_result()
                        await anyio.sleep(5.0)
            finally:
                await harness.dispose()

        asyncio.run(scenario())

    app_module.app.state.host = None
    failure = app_module.app.state.runtime_failure
    app_module.app.state.runtime_failure = None
    assert failure is not None
    assert failure.reason.startswith("critical_child_failure"), failure.reason
    assert failure.state is HostLifecycleState.STOPPED
    # The external signal is requested during the run, and it is the one the accepted contract
    # leaves to the process supervisor (SIGTERM: a nonzero exit code).
    assert requested == [signal.SIGTERM]
    host = captured["host"]
    assert host.state is HostLifecycleState.STOPPED
    assert host.ownership_snapshot()["singleton_lock_held"] is False
    assert host.ownership_snapshot()["shutdown_failures"] == []
    assert harness.resources.disposed is True


def test_an_engine_dispose_failure_is_reported_and_never_called_stopped(monkeypatch):
    """P1-03: a failed disposal is `STOP_FAILED` with the failure named, not a clean stop."""
    original_dispose = DatabaseResources.dispose
    calls = {"n": 0}

    async def failing_dispose(self: DatabaseResources) -> None:
        calls["n"] += 1
        if calls["n"] == 1:  # the Host-owned engine is disposed first
            raise RuntimeError("injected_engine_dispose_failure")
        await original_dispose(self)

    monkeypatch.setattr(DatabaseResources, "dispose", failing_dispose)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(), inject_database=False)
        host = harness.build()
        owned: DatabaseResources | None = None
        try:
            await harness.seed()
            await host.start()
            owned = host._db
            assert owned is not None and owned.disposed is False
            await host.stop()
            failures = host.ownership_snapshot()["shutdown_failures"]
            assert "engine_dispose_failed:RuntimeError" in failures, failures
            assert host.state is HostLifecycleState.STOP_FAILED
            # Truthfulness: the flag follows the engine, not the call's optimism.
            assert owned.disposed is False
        finally:
            # The injection deliberately left the Host-owned engine undisposed. Dispose it for
            # real here, so this test cannot leak a pooled connection into a later test's GC.
            for candidate in (host._db, owned):
                if candidate is not None and not candidate.disposed:
                    await original_dispose(candidate)
            await harness.dispose()

    _run(scenario)


def test_a_disposal_that_lies_about_succeeding_is_reported(monkeypatch):
    """P1-03: `dispose()` returning without disposing must still fail the terminal state."""
    original_dispose = DatabaseResources.dispose
    calls = {"n": 0}

    async def lying_dispose(self: DatabaseResources) -> None:
        calls["n"] += 1
        if calls["n"] == 1:  # returns quietly, never sets `disposed`
            return
        await original_dispose(self)

    monkeypatch.setattr(DatabaseResources, "dispose", lying_dispose)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(), inject_database=False)
        host = harness.build()
        owned: DatabaseResources | None = None
        try:
            await harness.seed()
            await host.start()
            owned = host._db
            assert owned is not None
            await host.stop()
            failures = host.ownership_snapshot()["shutdown_failures"]
            assert "engine_dispose_incomplete" in failures, failures
            assert host.state is HostLifecycleState.STOP_FAILED
            assert owned.disposed is False
        finally:
            # Same reason as the failing-dispose test: leave no pooled connection behind.
            for candidate in (host._db, owned):
                if candidate is not None and not candidate.disposed:
                    await original_dispose(candidate)
            await harness.dispose()

    _run(scenario)


def test_one_broken_cleanup_step_never_stops_the_others(monkeypatch):
    """P1-03: cleanup steps are independent, and a failure is recorded, never swallowed."""
    original_release = RuntimeHost._release_singleton_lock

    async def broken_release(self: RuntimeHost) -> None:
        raise RuntimeError("injected_singleton_release_failure")

    monkeypatch.setattr(RuntimeHost, "_release_singleton_lock", broken_release)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(), inject_database=False)
        host = harness.build()
        owned: DatabaseResources | None = None
        try:
            await harness.seed()
            await host.start()
            owned = host._db
            assert owned is not None and owned.disposed is False
            await host.stop()
            failures = host.ownership_snapshot()["shutdown_failures"]
            assert "singleton_release_failed:RuntimeError" in failures, failures
            assert host.state is HostLifecycleState.STOP_FAILED
            # The broken step did not stop the step behind it: the engine was still disposed.
            assert owned.disposed is True
        finally:
            # The injection left the fence connection open; close it for real so this test leaks
            # nothing into a later test's garbage collection.
            if host.ownership_snapshot()["singleton_connection_present"]:
                await original_release(host)
            await harness.dispose()

    _run(scenario)


def test_a_cancelled_stop_still_disposes_everything_and_stays_truthful():
    """P1-04: cancellation may not escape before the shielded final disposal finished."""

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(interval=0.02))
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            assert host.state is HostLifecycleState.READY

            task = asyncio.create_task(host.stop())
            assert await _wait_for(
                lambda: host.state is HostLifecycleState.STOPPING, timeout=5.0, interval=0.001
            ), host.state
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            snapshot = host.ownership_snapshot()
            assert "shutdown_cancelled" in snapshot["shutdown_failures"], snapshot[
                "shutdown_failures"
            ]
            # Truthful, never a disguised clean stop.
            assert host.state is HostLifecycleState.STOP_FAILED
            assert host._stop_completed is True
            # Mandatory disposal still ran: fence released, provider closed, children collected.
            assert snapshot["singleton_lock_held"] is False
            assert snapshot["singleton_connection_present"] is False
            assert host.children_live == ()
            assert harness.provider.stream_closed is True
            assert await _settled_orphan_tasks() == []
            # A second call is cleanup, not a second shutdown.
            await host.stop()
            assert host.state is HostLifecycleState.STOP_FAILED
        finally:
            await harness.dispose()

    _run(scenario)


class _SessionExitGate:
    """Deterministically holds a Host-owned session inside its own `close()`.

    Cancellation landing inside `AsyncSession.close()` is the exact seam that used to lose a
    pooled checkout (P2-01): the connection is never returned. Holding that call makes the race
    reproducible instead of probabilistic, so the shield can be proven rather than hoped for.
    """

    def __init__(self) -> None:
        self.enabled = anyio.Event()
        self.entered = anyio.Event()
        self.released = anyio.Event()

    async def hold(self) -> None:
        if not self.enabled.is_set() or self.released.is_set():
            return
        self.entered.set()
        await self.released.wait()


def test_an_injected_engine_keeps_its_checkout_baseline_under_sibling_cancellation(monkeypatch):
    """P2-01: a sibling cancellation must not cost the injected engine a checkout.

    Attribution: only the fenced-instrument-free loops below touch the DB (the provider stream,
    the safety lane and the scanner are all neutralised), so every checkout observed here belongs
    to a shielded Host-owned session, and the injected engine is the one whose baseline is read.
    """
    gate = _SessionExitGate()
    safety_gate = anyio.Event()
    original_close = AsyncSession.close

    async def gated_close(self: AsyncSession) -> None:
        # Only a session that still has an open transaction is holding a pooled connection at
        # `close()` time — that is exactly the checkout a cancelled close loses.
        if self.in_transaction():
            await gate.hold()
        await original_close(self)

    async def gated_safety(self, run_mode, bbo, *, force_reevaluation=False, now=None):
        await safety_gate.wait()
        raise RuntimeError("injected_safety_failure")

    async def inert_ingest(self, market_event, auxiliary=None):
        return []

    monkeypatch.setattr(AsyncSession, "close", gated_close)
    monkeypatch.setattr(SafetyRuntime, "on_market_data", gated_safety)
    monkeypatch.setattr(ScannerPipeline, "ingest", inert_ingest)

    async def scenario(url: str) -> None:
        harness = Harness(
            _settings(url, runtime_safety_queue_capacity=4096), ControlledProvider(interval=0.01)
        )
        try:
            await harness.seed()
            host = harness.build()
            pool = harness.resources.engine.pool
            assert pool.checkedout() == 0
            await host.start()
            try:
                # From here every Host-owned session is held inside its exit.
                gate.enabled.set()
                assert await _wait_for(gate.entered.is_set, timeout=10.0), "no shielded session ran"
                # Now fail a sibling. anyio cancels the rest of the group, so the cancellation is
                # attempted against a child that is mid-session.
                safety_gate.set()
                assert await _wait_for(
                    lambda: not any(name.startswith("safety:") for name in host.children_live),
                    timeout=20.0,
                ), host.children_live
                assert "safety_lane_failure" in {
                    entry.get("reason") for entry in host.health.checks.values()
                }, host.health.snapshot()
                await asyncio.sleep(0.5)
                # The failing sibling is gone and the cancellation has been attempted, yet the
                # shielded session holder is untouched and its connection is still checked out:
                # the in-flight unit was not interrupted.
                assert set(host.children_live) & {"heartbeat", "reconciliation"}, host.children_live
                assert pool.checkedout() >= 1

                gate.released.set()
                assert await _wait_for(lambda: host.failed, timeout=25.0), host.failure_reason
                assert await _wait_for(
                    lambda: host.state in TERMINAL_STATES, timeout=25.0
                ), host.readiness().as_payload()
                # Baseline restored: nothing was lost, so nothing is left checked out.
                assert pool.checkedout() == 0
                assert host.children_live == ()
                assert await _settled_orphan_tasks() == []
            finally:
                gate.released.set()
                gate.enabled.set()
                await host.stop()
        finally:
            await harness.dispose()

    # Flush anything an earlier test left to the collector *before* capturing, so the assertion
    # below is about this scenario's own objects rather than about unrelated pending garbage.
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _run(scenario)
        gc.collect()
    assert [str(item.message) for item in caught if issubclass(item.category, SAWarning)] == []


def test_a_scanner_error_storm_cannot_grow_host_retention(monkeypatch):
    """P2-03: the bound lives on the storage, so no uptime can grow either collection."""
    error_types = [type(f"InjectedScannerError{n:02d}", (RuntimeError,), {}) for n in range(24)]
    counter = {"n": 0}

    async def failing_ingest(self, market_event, auxiliary=None):
        cls = error_types[counter["n"] % len(error_types)]
        counter["n"] += 1
        raise cls("injected_scanner_failure")

    monkeypatch.setattr(ScannerPipeline, "ingest", failing_ingest)

    async def scenario(url: str) -> None:
        harness = Harness(_settings(url), ControlledProvider(interval=0.01))
        try:
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert await _wait_for(
                    lambda: host._scanner_errors > SCANNER_ERROR_SAMPLE_MAXLEN * 3
                ), host._scanner_errors
                await asyncio.sleep(FAST_TELEMETRY_SECONDS * 2)
                assert len(host._scanner_error_samples) == SCANNER_ERROR_SAMPLE_MAXLEN
                assert host._scanner_error_samples.maxlen == SCANNER_ERROR_SAMPLE_MAXLEN
                assert host._state_history.maxlen == STATE_HISTORY_MAXLEN
                samples = host.telemetry()["counters"]["scanner_event_error_samples"]
                assert isinstance(samples, list) and len(samples) <= 8
                # Impaired, never failed: per-event isolation is the accepted contract.
                assert host.failed is False
                assert host.state in {HostLifecycleState.READY, HostLifecycleState.DEGRADED}
            finally:
                await host.stop()
        finally:
            await harness.dispose()

    _run(scenario)


def test_host_retention_storage_is_bounded_by_construction():
    """P2-03: the bound is on storage, so a telemetry slice can never be the whole guarantee."""
    host = RuntimeHost(_settings())
    assert host._state_history.maxlen == STATE_HISTORY_MAXLEN
    assert host._scanner_error_samples.maxlen == SCANNER_ERROR_SAMPLE_MAXLEN

    overflow = STATE_HISTORY_MAXLEN * 3
    for index in range(overflow):
        host._state_history.append((f"t{index}", "READY"))
        host._scanner_error_samples.append(f"E{index}")

    assert len(host._state_history) == STATE_HISTORY_MAXLEN
    assert len(host._scanner_error_samples) == SCANNER_ERROR_SAMPLE_MAXLEN
    assert host.ownership_snapshot()["state_history"][-1] == (f"t{overflow - 1}", "READY")
    assert list(host._scanner_error_samples)[-1] == f"E{overflow - 1}"


def test_database_resources_dispose_is_truthful_and_idempotent():
    """P1-03 / P2-04: the owned-engine bundle is the only thing that can dispose its engine."""
    engine = _StubEngine()
    resources = DatabaseResources(engine=engine)  # type: ignore[arg-type]

    asyncio.run(resources.dispose())
    assert resources.disposed is True
    assert engine.dispose_calls == 1
    asyncio.run(resources.dispose())
    assert engine.dispose_calls == 1  # a second call is a no-op, not a re-dispose

    failing = DatabaseResources(engine=_StubEngine(fail=True))  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="injected_engine_dispose_failure"):
        asyncio.run(failing.dispose())
    assert failing.disposed is False  # a failed disposal is never reported as disposed


def test_the_legacy_factory_only_helpers_are_gone_and_unreferenced():
    """P2-04: no helper may hand out a factory whose owning engine handle is lost."""
    import marketpulse.db.session as session_module

    assert not hasattr(session_module, "create_session_factory")
    assert not hasattr(session_module, "get_db")

    offenders: list[str] = []
    for path in sorted((REPOSITORY_ROOT / "backend" / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "create_session_factory" in source or re.search(r"\bget_db\b", source):
            offenders.append(str(path.relative_to(REPOSITORY_ROOT)))
    assert offenders == []


@pytest.mark.parametrize(
    ("instruments", "missing"),
    [
        ("BTC-USDT", "ETH-USDT"),
        ("ETH-USDT", "BTC-USDT"),
        ("SOL-USDT,XRP-USDT", "BTC-USDT,ETH-USDT"),
    ],
)
def test_an_enabled_host_must_cover_both_v1_instruments(instruments, missing):
    """P2-05: the V1 activation contract is a conjunction, and it fails closed."""
    host = RuntimeHost(
        _settings(runtime_host_instruments=instruments),
        dependencies=HostDependencies(provider=ControlledProvider()),
    )

    async def scenario() -> None:
        with pytest.raises(
            HostConfigurationError, match=f"V1_REQUIRED_INSTRUMENTS_MISSING:{missing}"
        ):
            await host.start()

    asyncio.run(scenario())
    assert host.state is HostLifecycleState.CREATED


def test_additional_instruments_beyond_the_v1_pair_remain_allowed():
    """P2-05: the contract is a floor, not a fixed list."""
    instruments = (BTC, ETH, "SOL-USDT")

    async def scenario(url: str) -> None:
        provider = ControlledProvider(instruments)
        harness = Harness(
            _settings(url, runtime_host_instruments="BTC-USDT,ETH-USDT,SOL-USDT"), provider
        )
        try:
            assert harness.provider.instrument_ids == instruments
            await harness.seed()
            host = harness.build()
            await host.start()
            try:
                assert host.state is HostLifecycleState.READY, host.readiness().as_payload()
                assert set(host.children_live) >= {
                    "provider_stream",
                    "scanner",
                    f"safety:{BTC}",
                    f"safety:{ETH}",
                    "safety:SOL-USDT",
                }
            finally:
                await host.stop()
            assert host.ownership_snapshot()["shutdown_failures"] == []
        finally:
            await harness.dispose()

    with _disposable_postgres_database() as (_, url):
        asyncio.run(scenario(url))


class _StubEngine:
    """Minimal stand-in for `AsyncEngine`; only `dispose()` is part of this contract."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1
        if self.fail:
            raise RuntimeError("injected_engine_dispose_failure")
