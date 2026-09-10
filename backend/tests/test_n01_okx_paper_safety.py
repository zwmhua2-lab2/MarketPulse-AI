"""N01-B — OKX Reconnect / Freshness + Paper Safety Continuity (deterministic focused gate).

This module is the offline half of N01-B. It must never depend on the public internet: the
unit/deterministic regression suite may not become flaky because of OKX or ISP conditions.

What is proven here, on a disposable PostgreSQL database, using unmodified production code:

* `CORE_MARKET_DATA` freshness is driven by real production `SafetyRuntime` /
  `PositionProtectionService` semantics (`received_at` + TTL, not just a quality flag).
* A controlled aged quote (identity-preserving, `received_at` beyond the accepted TTL) blocks
  every risk-increasing action through the single programmatic `SystemRiskGate`, opens /
  preserves the official `CORE_DATA_STALE` incident, and fabricates no Fill / exit / position
  mutation. Risk-reducing SELL stays ungated but still cannot fill without an executable fresh
  BBO, which is exactly the accepted product boundary.
* A later fresh quote restores health and resolves the stale incident, and stale data stops
  being an admission blocker.
* Economic facts stay duplicate-safe across stale → fresh transitions and duplicate events.
* The OKX reconnect loop reacts to a controlled disconnect by opening a *second* connection and
  delivering a post-reconnect event, then leaves no owned pending stream task behind.

Real OKX evidence (real SPOT metadata, real `bbo-tbt` events, a real controlled reconnect and a
real post-reconnect fresh BBO) is produced separately and deliberately by
`scripts/verify_n01_b_okx_paper_safety.py`. The loopback server used below is explicitly a
LOCAL FAKE WS and is never a substitute for that real OKX gate.

Production code changed: NO.
"""

import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from inspect import getasyncgenstate
from pathlib import Path
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from marketpulse.clock import SystemClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    FillRecord,
    IncidentRecord,
    LedgerEntryRecord,
    PaperOrderRecord,
    PositionRecord,
    TradeRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    ExecutionIntent,
    ExecutionResult,
    IntentStatus,
    OrderSide,
    OrderType,
    PlanStatus,
    PriceZone,
    RunMode,
    TradePlan,
)
from marketpulse.g3.service import PaperExecutionService, persist_trade_plan, stable_id
from marketpulse.g4.incidents import IncidentManager
from marketpulse.g4.models import (
    HealthComponent,
    HealthStatus,
    IncidentStatus,
    IncidentType,
    OperatorState,
    PositionReevaluation,
    ReevaluationAction,
    SystemState,
)
from marketpulse.g4.orchestrator import SafetyRuntime
from marketpulse.g4.planning import PlanManager
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.provider import DeterministicFakePositionReviewProvider
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.reevaluation import PositionReevaluationService
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.models import Instrument, MarketType
from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.runtime import HealthRegistry
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from websockets.asyncio.server import serve

RUN_MODE = RunMode.LIVE_PAPER
BTC = "BTC-USDT"
ETH = "ETH-USDT"
STATE_VERSION = 7
# The accepted production freshness TTL is 5s (`SafetyRuntime._mark_freshness`,
# `PositionProtectionService.freshness_ttl`). The controlled stale injection below ages the
# quote well beyond it while preserving bid / ask / instrument identity.
PRODUCTION_FRESHNESS_TTL_SECONDS = 5.0
CONTROLLED_STALE_AGE_SECONDS = 30.0
SLIPPAGE_BPS = 5

PROXY_ENVIRONMENT_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _clear_proxy_environment(monkeypatch) -> None:
    """Keep loopback-only validation offline.

    A proxy injected by the surrounding development sandbox must never be used to reach a
    `127.0.0.1` WebSocket server, otherwise this deterministic regression would depend on an
    external process. Production code is untouched: this only edits this process' environment.
    """
    for name in PROXY_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def _quote(
    instrument_id: str,
    bid: float,
    ask: float,
    *,
    age_seconds: float = 0.0,
    now: datetime | None = None,
) -> BestBidAsk:
    """Build a tradable FRESH-quality quote, optionally aged by `received_at` only.

    Ageing only `received_at` is deliberate: it exercises the production TTL path instead of
    short-circuiting on `data_quality`. This is a CONTROLLED STALE INJECTION, not an OKX fact.
    """
    reference = now or datetime.now(UTC)
    return BestBidAsk(
        instrument_id=instrument_id,
        bid=bid,
        ask=ask,
        received_at=reference - timedelta(seconds=age_seconds),
    )


# ---------------------------------------------------------------------------------------
# Live-paper harness (mirrors the accepted G4 harness wiring; LIVE_PAPER + real PostgreSQL)
# ---------------------------------------------------------------------------------------


@dataclass
class LivePaperHarness:
    sessions: async_sessionmaker[AsyncSession]
    run_mode: RunMode = RUN_MODE
    initial_balance: float = 10_000.0
    state_version: int = STATE_VERSION

    def __post_init__(self) -> None:
        self.clock = SystemClock()
        self.health = HealthRegistry()
        for component in HealthComponent:
            self.health.set(component.value, HealthStatus.HEALTHY.value)
        self.state_service = SystemStateService(self.sessions, clock=self.clock)
        self.incidents = IncidentManager(self.sessions, clock=self.clock)
        self.quote: BestBidAsk | None = None

        async def bbo_for(instrument_id: str) -> BestBidAsk:
            if self.quote is None or self.quote.instrument_id != instrument_id:
                raise RuntimeError(f"harness_has_no_quote:{instrument_id}")
            return self.quote

        async def state_version_for(instrument_id: str) -> int:
            return self.state_version

        self.execution = PaperExecutionService(
            self.sessions,
            bbo_for,
            state_version_for,
            initial_balance=self.initial_balance,
            clock=self.clock,
        )
        self.risk_gate = SystemRiskGate(
            self.sessions, self.state_service, self.incidents, self.health, clock=self.clock
        )
        self.execution.risk_gate = self.risk_gate
        self.protection = PositionProtectionService(
            self.sessions, self.execution, self.incidents, self.health, clock=self.clock
        )
        self.plans = PlanManager(self.sessions, self.execution, clock=self.clock)
        self.review_provider = DeterministicFakePositionReviewProvider(
            PositionReevaluation(action=ReevaluationAction.HOLD, reason="n01_b_harness_hold")
        )
        self.reevaluation = PositionReevaluationService(
            self.sessions,
            self.review_provider,
            self.plans,
            self.risk_gate,
            self.protection,
            self.incidents,
            self.execution,
            self.health,
            clock=self.clock,
        )
        # N01-B must not depend on AI latency or availability: re-evaluation stays disabled.
        self.safety = SafetyRuntime(
            execution=self.execution,
            protection=self.protection,
            reevaluation=self.reevaluation,
            health=self.health,
            clock=self.clock,
            reevaluation_enabled=False,
        )

    async def boot(self) -> None:
        await self.state_service.ensure(self.run_mode)
        await self.state_service.transition(
            self.run_mode,
            operator_state=OperatorState.NORMAL,
            system_state=SystemState.RUNNING,
            reason="n01_b_boot",
        )
        await self.execution.bootstrap_account(self.run_mode)

    async def feed_market_data(self, bbo: BestBidAsk) -> dict[str, Any]:
        """Publish the latest market state through the production `SafetyRuntime` path.

        The upstream latest-market-state accessor is advanced first, exactly as a real market
        data loop would, so any protection / limit-fill lookup sees the same quote.
        """
        self.quote = bbo
        return await self.safety.on_market_data(self.run_mode, bbo)

    async def open_paper_long(
        self,
        bbo: BestBidAsk,
        *,
        stop_factor: float,
        take_profit_factor: float,
        tag: str = "position",
        notional: float = 100.0,
    ) -> TradePlan:
        """Open a LIVE_PAPER spot LONG through the accepted TradePlan → Intent → Execution chain."""
        self.quote = bbo
        now = self.clock.now()
        plan = TradePlan(
            plan_id=stable_id("plan", "n01-b", tag, self.run_mode, bbo.instrument_id),
            snapshot_id=stable_id("snap", "n01-b", tag, bbo.instrument_id),
            decision_id=stable_id("decision", "n01-b", tag, bbo.instrument_id),
            instrument_id=bbo.instrument_id,
            symbol=bbo.instrument_id,
            run_mode=self.run_mode,
            state_version=self.state_version,
            plan_version=1,
            status=PlanStatus.ACTIVE,
            created_at=now,
            expires_at=now + timedelta(minutes=30),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            entry_zone=PriceZone(lower=bbo.ask * 0.9, upper=bbo.ask * 1.1),
            stop_loss=bbo.bid * stop_factor,
            take_profit=bbo.bid * take_profit_factor,
            intended_notional=notional,
        )
        await persist_trade_plan(self.sessions, plan)
        intent = ExecutionIntent(
            intent_id=stable_id("intent", "n01-b", tag, self.run_mode, bbo.instrument_id),
            plan_id=plan.plan_id,
            instrument_id=plan.instrument_id,
            run_mode=self.run_mode,
            state_version=self.state_version,
            created_at=now,
        )
        result = await self.execution.execute(intent, plan, now)
        assert result.status is IntentStatus.EXECUTED, result.reason
        return plan

    async def propose_risk_increasing_buy(self, plan: TradePlan, *, tag: str) -> ExecutionResult:
        """Attempt one further risk-increasing BUY through the real G3 admission path."""
        now = self.clock.now()
        intent = ExecutionIntent(
            intent_id=stable_id("intent", "n01-b", tag, self.run_mode, plan.instrument_id),
            plan_id=plan.plan_id,
            instrument_id=plan.instrument_id,
            run_mode=self.run_mode,
            state_version=self.state_version,
            created_at=now,
        )
        result = await self.execution.execute(intent, plan, now)
        assert result.reason is not None
        return result


async def _position(
    sessions: async_sessionmaker[AsyncSession], run_mode: RunMode, instrument_id: str
) -> PositionRecord | None:
    async with sessions() as session:
        return await session.scalar(
            select(PositionRecord).where(
                PositionRecord.run_mode == run_mode,
                PositionRecord.instrument_id == instrument_id,
            )
        )


async def _incident(
    sessions: async_sessionmaker[AsyncSession],
    run_mode: RunMode,
    instrument_id: str,
    incident_type: IncidentType,
) -> IncidentRecord | None:
    async with sessions() as session:
        return await session.scalar(
            select(IncidentRecord)
            .where(
                IncidentRecord.run_mode == run_mode,
                IncidentRecord.instrument_id == instrument_id,
                IncidentRecord.incident_type == incident_type,
            )
            .order_by(IncidentRecord.opened_at.desc())
        )


async def _sell_fills(sessions: async_sessionmaker[AsyncSession], run_mode: RunMode) -> list[FillRecord]:
    async with sessions() as session:
        return list(
            (
                await session.scalars(
                    select(FillRecord)
                    .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                    .where(
                        PaperOrderRecord.run_mode == run_mode,
                        PaperOrderRecord.side == OrderSide.SELL,
                    )
                )
            ).all()
        )


async def _economic_counts(
    sessions: async_sessionmaker[AsyncSession], run_mode: RunMode
) -> dict[str, int]:
    """Durable economic facts. Reconnect / duplicate events must never create new ones."""
    async with sessions() as session:
        orders = int(
            await session.scalar(
                select(func.count())
                .select_from(PaperOrderRecord)
                .where(PaperOrderRecord.run_mode == run_mode)
            )
            or 0
        )
        fills = int(
            await session.scalar(
                select(func.count())
                .select_from(FillRecord)
                .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                .where(PaperOrderRecord.run_mode == run_mode)
            )
            or 0
        )
        positions = int(
            await session.scalar(
                select(func.count())
                .select_from(PositionRecord)
                .where(PositionRecord.run_mode == run_mode)
            )
            or 0
        )
        trades = int(
            await session.scalar(
                select(func.count()).select_from(TradeRecord).where(TradeRecord.run_mode == run_mode)
            )
            or 0
        )
        accounts = int(
            await session.scalar(
                select(func.count())
                .select_from(AccountRecord)
                .where(AccountRecord.run_mode == run_mode)
            )
            or 0
        )
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == run_mode)
        )
        ledger = 0
        if account is not None:
            ledger = int(
                await session.scalar(
                    select(func.count())
                    .select_from(LedgerEntryRecord)
                    .where(LedgerEntryRecord.account_id == account.account_id)
                )
                or 0
            )
    return {
        "orders": orders,
        "fills": fills,
        "positions": positions,
        "trades": trades,
        "accounts": accounts,
        "ledger_entries": ledger,
    }


# ---------------------------------------------------------------------------------------
# Disposable PostgreSQL database (fully isolated; never touches the user's MarketPulse DB)
# ---------------------------------------------------------------------------------------


@contextmanager
def _disposable_postgres_database() -> Iterator[tuple[str, str]]:
    primary_url = Settings().database_url
    database_name = f"marketpulse_n01_b_{uuid4().hex[:12]}"
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


async def _leftover_disposable_databases() -> int:
    engine = create_async_engine(Settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_database "
                        "WHERE datname LIKE 'marketpulse_n01_b_%'"
                    )
                )
                or 0
            )
    finally:
        await engine.dispose()


def _task_signature(task: asyncio.Task) -> str:
    coroutine = task.get_coro()
    return f"{task.get_name()}::{getattr(coroutine, '__qualname__', type(coroutine).__name__)}"


async def _settle_background_tasks(grace_seconds: float = 5.0) -> dict[str, Any]:
    """Prove background tasks terminate, without a scheduler-timing guess.

    Closing a stream cancels the work it owns, but the cancellation is only observed on the next
    event-loop turn. `websockets` additionally runs one internal `Connection.keepalive` task per
    connection, which is cancelled by the close and settles shortly afterwards. An instantaneous
    "no pending task" assertion would therefore be timing-dependent rather than a property of the
    code under test.

    This waits on the *concrete* task objects with a hard bound and then reports what actually
    remains: an empty remaining set proves the tasks terminate (no leak, no detached stream),
    while the observed set records what was transiently in flight. No polling, no retry loop.
    """
    pending = [
        task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()
    ]
    observed = sorted(_task_signature(task) for task in pending)
    if pending:
        await asyncio.wait(pending, timeout=grace_seconds)
    remaining = sorted(
        _task_signature(task)
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task() and not task.done()
    )
    return {
        "observed_transient_tasks": observed,
        "remaining_pending_tasks": remaining,
        "grace_seconds": grace_seconds,
    }


# ---------------------------------------------------------------------------------------
# LOCAL FAKE WS — reconnect-loop regression only (never evidence of real OKX behaviour)
# ---------------------------------------------------------------------------------------


def _local_instrument(instrument_id: str) -> Instrument:
    return Instrument(
        base_asset=instrument_id.split("-")[0],
        quote_asset="USDT",
        market_type=MarketType.SPOT,
        instrument_id=instrument_id,
        trading_symbol=instrument_id,
        tradable=True,
    )


def _local_bbo_frame(instrument_id: str, sequence: int) -> str:
    return json.dumps(
        {
            "arg": {"channel": "bbo-tbt", "instId": instrument_id},
            "data": [
                {
                    "instId": instrument_id,
                    "bidPx": str(100_000 + sequence),
                    "bidSz": "1",
                    "askPx": str(100_001 + sequence),
                    "askSz": "1",
                    "ts": str(int(time.time() * 1000)),
                }
            ],
        }
    )


def test_n01_b_okx_provider_reconnects_on_controlled_disconnect_and_cleans_up(monkeypatch):
    """LOCAL FAKE WS: the accepted reconnect loop must open a second real connection.

    Each accepted connection stamps its own socket sequence into the payload, so the
    post-reconnect event proves it arrived on connection #2 rather than being replayed by
    connection #1. This is a deterministic regression of the reconnect accounting path.
    """
    _clear_proxy_environment(monkeypatch)

    async def scenario(instrument_id: str) -> dict[str, Any]:
        accepted_connections: list[int] = []

        async def handler(websocket) -> None:
            accepted_connections.append(len(accepted_connections) + 1)
            sequence = accepted_connections[-1]
            async for message in websocket:
                payload = json.loads(message)
                if payload.get("op") != "subscribe":
                    continue
                await websocket.send(
                    json.dumps(
                        {
                            "event": "subscribe",
                            "arg": payload["args"][0],
                            "connId": f"local-{sequence}",
                        }
                    )
                )
                await websocket.send(_local_bbo_frame(instrument_id, sequence))

        async with serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            provider = OKXLiveProvider(
                ws_url=f"ws://127.0.0.1:{port}/",
                reconnect_delay=0.01,
                disconnect_after_events=1,
            )
            # Validation-only seam: the real provider learns its instruments from OKX REST.
            provider._instruments[instrument_id] = _local_instrument(instrument_id)
            stream = provider.stream([{"channel": "bbo-tbt", "instId": instrument_id}])
            try:
                first = await asyncio.wait_for(anext(stream), timeout=10)
                attempts_after_first = provider.connection_attempts
                reconnects_after_first = provider.reconnects
                second = await asyncio.wait_for(anext(stream), timeout=10)
            finally:
                await stream.aclose()
            assert getasyncgenstate(stream) == "AGEN_CLOSED"
        background_tasks = await _settle_background_tasks()
        return {
            "accepted_connections": accepted_connections,
            "attempts_after_first": attempts_after_first,
            "reconnects_after_first": reconnects_after_first,
            "connection_attempts": provider.connection_attempts,
            "reconnects": provider.reconnects,
            "first": first,
            "second": second,
            "background_tasks": background_tasks,
        }

    for instrument_id in (BTC, ETH):
        evidence = asyncio.run(scenario(instrument_id))
        first = evidence["first"]
        second = evidence["second"]
        assert evidence["accepted_connections"] == [1, 2]
        assert evidence["attempts_after_first"] == 1
        assert evidence["reconnects_after_first"] == 0
        assert evidence["connection_attempts"] >= 2
        assert evidence["reconnects"] >= 1
        for event in (first, second):
            assert event.instrument_id == instrument_id
            assert event.market_type is MarketType.SPOT
            assert event.data_quality.value == "FRESH"
            assert event.bid_price > 0 and event.ask_price > 0
            assert event.ask_price >= event.bid_price
            assert event.received_time.tzinfo is not None
        # Sequence 2 can only come from the second accepted connection.
        assert first.bid_price == 100_001 and second.bid_price == 100_002
        assert second.received_time >= first.received_time
        assert evidence["background_tasks"]["remaining_pending_tasks"] == [], evidence[
            "background_tasks"
        ]


# ---------------------------------------------------------------------------------------
# FRESH → CONTROLLED STALE → FRESH on real PostgreSQL through real production safety code
# ---------------------------------------------------------------------------------------


def test_n01_b_freshness_boundary_blocks_risk_increasing_actions_and_fails_closed():
    async def scenario(database_name: str, database_url: str) -> dict[str, Any]:
        baseline = await _database_activity(database_name)
        engine = create_async_engine(database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        harness = LivePaperHarness(sessions)
        try:
            await harness.boot()
            fresh_1 = _quote(BTC, 100_000.0, 100_001.0)
            plan = await harness.open_paper_long(
                fresh_1, stop_factor=0.90, take_profit_factor=1.10
            )
            position_before = await _position(sessions, RUN_MODE, BTC)
            assert position_before is not None and position_before.quantity > 0
            counts_before = await _economic_counts(sessions, RUN_MODE)
            assert counts_before["orders"] == 1 and counts_before["fills"] == 1
            assert counts_before["positions"] == 1 and counts_before["trades"] == 1

            # --- Real-fresh pathway ---------------------------------------------------
            fresh_outcome = await harness.feed_market_data(fresh_1)
            assert fresh_outcome["fresh"] is True
            assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
            assert fresh_outcome["protection"].triggered is False
            assert fresh_outcome["protection"].reason == "HOLD"
            admitted, admit_reason = await harness.risk_gate.check(
                RUN_MODE, BTC, plan_id=plan.plan_id
            )
            assert (admitted, admit_reason) == (True, None)

            # --- CONTROLLED STALE INJECTION (identity preserved, received_at beyond TTL) --
            stale = _quote(
                BTC, fresh_1.bid, fresh_1.ask, age_seconds=CONTROLLED_STALE_AGE_SECONDS
            )
            assert (harness.clock.now() - stale.received_at).total_seconds() > (
                PRODUCTION_FRESHNESS_TTL_SECONDS
            )
            assert stale.instrument_id == fresh_1.instrument_id
            assert (stale.bid, stale.ask) == (fresh_1.bid, fresh_1.ask)
            stale_outcome = await harness.feed_market_data(stale)
            assert stale_outcome["fresh"] is False
            assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "UNAVAILABLE"
            assert stale_outcome["protection"].triggered is False
            assert stale_outcome["protection"].reason == "CORE_MARKET_DATA_STALE"
            incident = await _incident(sessions, RUN_MODE, BTC, IncidentType.CORE_DATA_STALE)
            assert incident is not None
            assert incident.status == IncidentStatus.OPEN.value

            # Existing position stays durable; no fabricated protective Fill / exit.
            position_after_stale = await _position(sessions, RUN_MODE, BTC)
            assert position_after_stale is not None
            assert position_after_stale.quantity == position_before.quantity
            assert position_after_stale.average_cost == position_before.average_cost
            assert position_after_stale.trade_id == position_before.trade_id
            assert await _economic_counts(sessions, RUN_MODE) == counts_before
            assert await _sell_fills(sessions, RUN_MODE) == []

            # A duplicate network event and a direct protection re-evaluation change nothing.
            duplicate = await harness.feed_market_data(stale)
            assert duplicate["protection"].reason == "CORE_MARKET_DATA_STALE"
            direct = await harness.protection.evaluate(RUN_MODE, BTC, stale)
            assert direct.triggered is False and direct.reason == "CORE_MARKET_DATA_STALE"
            assert await _economic_counts(sessions, RUN_MODE) == counts_before

            # Risk-reducing SELL stays ungated, yet cannot fabricate a protective fill.
            async with sessions() as session, session.begin():
                sell_reason = await harness.risk_gate.evaluate(
                    session,
                    run_mode=RUN_MODE,
                    instrument_id=BTC,
                    side=OrderSide.SELL,
                    plan_id=plan.plan_id,
                    now=harness.clock.now(),
                )
            assert sell_reason is None
            manual = await harness.protection.manual_close(RUN_MODE, BTC, stale)
            assert manual.triggered is False and manual.reason == "CORE_MARKET_DATA_STALE"
            assert await _economic_counts(sessions, RUN_MODE) == counts_before

            # Risk-increasing action must fail closed through the single programmatic gate.
            blocked, block_reason = await harness.risk_gate.check(
                RUN_MODE, BTC, plan_id=plan.plan_id
            )
            assert blocked is False
            assert block_reason == "RUNTIME_STATE_DATA_DEGRADED"
            rejected = await harness.propose_risk_increasing_buy(plan, tag="stale-blocked")
            assert rejected.status is IntentStatus.REJECTED
            assert rejected.reason == "RUNTIME_STATE_DATA_DEGRADED"
            assert await _economic_counts(sessions, RUN_MODE) == counts_before

            # --- Fresh recovery -------------------------------------------------------
            fresh_2 = _quote(BTC, 100_000.0, 100_001.0)
            recovery = await harness.feed_market_data(fresh_2)
            assert recovery["fresh"] is True
            assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
            resolved = await _incident(sessions, RUN_MODE, BTC, IncidentType.CORE_DATA_STALE)
            assert resolved is not None and resolved.status == IncidentStatus.RESOLVED.value
            assert resolved.resolved_at is not None
            assert recovery["protection"].triggered is False
            assert recovery["protection"].reason == "HOLD"
            assert await _economic_counts(sessions, RUN_MODE) == counts_before

            re_admitted, re_reason = await harness.risk_gate.check(
                RUN_MODE, BTC, plan_id=plan.plan_id
            )
            assert (re_admitted, re_reason) == (True, None)

            report = await reconcile(
                RUN_MODE, sessions=sessions, execution=harness.execution, now=harness.clock.now()
            )
            assert report.ok is True, report.diagnostics
            return {
                "baseline": baseline,
                "counts_before": counts_before,
                "counts_after": await _economic_counts(sessions, RUN_MODE),
                "reconciliation_ok": report.ok,
                "stale_reason": stale_outcome["protection"].reason,
                "gate_block_reason": block_reason,
            }
        finally:
            await engine.dispose()

    with _disposable_postgres_database() as (database_name, database_url):
        evidence = asyncio.run(scenario(database_name, database_url))
        activity_after = asyncio.run(_database_activity(database_name))
    assert evidence["baseline"]["idle_in_transaction"] == 0
    assert activity_after == evidence["baseline"]
    assert asyncio.run(_leftover_disposable_databases()) == 0
    assert evidence["counts_after"] == evidence["counts_before"]
    print({"n01_b_freshness_boundary": evidence, "db_after": activity_after})


def test_n01_b_post_transition_controlled_fresh_bbo_still_triggers_protection():
    """CONTROLLED FRESH BBO: the SL engine still fires after a stale → fresh transition.

    The quote is deterministic and clearly not real OKX data; it only proves the protection
    engine remains executable across the freshness state transition. Real post-reconnect
    freshness recovery is evidenced by the real OKX validation script instead.
    """
    async def scenario(database_name: str, database_url: str) -> dict[str, Any]:
        baseline = await _database_activity(database_name)
        engine = create_async_engine(database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        harness = LivePaperHarness(sessions)
        try:
            await harness.boot()
            fresh_1 = _quote(BTC, 100_000.0, 100_001.0)
            plan = await harness.open_paper_long(
                fresh_1, stop_factor=0.999, take_profit_factor=1.50, tag="trigger"
            )
            position = await _position(sessions, RUN_MODE, BTC)
            assert position is not None and position.quantity > 0

            await harness.feed_market_data(fresh_1)
            stale = _quote(
                BTC, fresh_1.bid, fresh_1.ask, age_seconds=CONTROLLED_STALE_AGE_SECONDS
            )
            stale_outcome = await harness.feed_market_data(stale)
            assert stale_outcome["protection"].reason == "CORE_MARKET_DATA_STALE"
            assert await _sell_fills(sessions, RUN_MODE) == []

            recovery = await harness.feed_market_data(_quote(BTC, 100_000.0, 100_001.0))
            assert recovery["fresh"] is True and recovery["protection"].reason == "HOLD"

            controlled = _quote(BTC, plan.stop_loss - 1.0, plan.stop_loss + 1.0)
            outcome = await harness.feed_market_data(controlled)
            assert outcome["protection"].triggered is True
            assert outcome["protection"].exit_reason.value == "STOP_LOSS"
            assert outcome["protection"].fill_id is not None

            sells = await _sell_fills(sessions, RUN_MODE)
            assert len(sells) == 1
            assert sells[0].price == controlled.bid * (1 - SLIPPAGE_BPS / 10_000)
            assert sells[0].price < controlled.bid

            flat = await _position(sessions, RUN_MODE, BTC)
            assert flat is not None and flat.quantity == 0.0
            async with sessions() as session:
                trade = await session.scalar(
                    select(TradeRecord).where(TradeRecord.run_mode == RUN_MODE)
                )
            assert trade is not None and trade.exit_reason == "STOP_LOSS"

            counts = await _economic_counts(sessions, RUN_MODE)
            assert counts["fills"] == 2 and counts["trades"] == 1
            duplicate = await harness.feed_market_data(controlled)
            assert duplicate["protection"].reason == "NO_POSITION"
            assert await _economic_counts(sessions, RUN_MODE) == counts

            report = await reconcile(
                RUN_MODE, sessions=sessions, execution=harness.execution, now=harness.clock.now()
            )
            assert report.ok is True, report.diagnostics
            return {"baseline": baseline, "counts": counts, "reconciliation_ok": report.ok}
        finally:
            await engine.dispose()

    with _disposable_postgres_database() as (database_name, database_url):
        evidence = asyncio.run(scenario(database_name, database_url))
        activity_after = asyncio.run(_database_activity(database_name))
    assert evidence["baseline"]["idle_in_transaction"] == 0
    assert activity_after == evidence["baseline"]
    assert asyncio.run(_leftover_disposable_databases()) == 0
    print({"n01_b_controlled_trigger": evidence, "db_after": activity_after})
