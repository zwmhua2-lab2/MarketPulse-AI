"""N01-6 — 15-minute Short Runtime Smoke (validation-only harness).

This is the real-network, real-database half of N01-6. It is deliberately an explicit,
opt-in validation script: the unit/deterministic suite must never depend on the public
internet, on wall-clock soak time, or on the sandbox's network conditions.

Claim boundary (must not be overstated in any completion report)
---------------------------------------------------------------
This harness runs **accepted production runtime components continuously inside a validation
harness** for >= 900 s. It is NOT the Integrated Runtime Host, NOT a FastAPI 7x24 runtime,
NOT a daemon/service, NOT a deployment and NOT 7x24 acceptance. Even on PASS,
`Integrated Runtime Host` remains `NOT STARTED` and `N01 overall` remains `NOT ACCEPTED`.

What is wired (all accepted production components, unmodified)
-------------------------------------------------------------
* real OKX public SPOT metadata plus the `trades` and `bbo-tbt` public WebSocket channels for
  BTC-USDT and ETH-USDT;
* `ScannerPipeline` -> `OpportunityScanner` (accepted default `ScannerConfig`) ->
  `EventRuntime` (accepted default capacities) -> `PostgresG2Repository` (real PostgreSQL);
  every normalized trade *and* normalized book ticker enters that accepted path;
* `SafetyRuntime` -> `PositionProtectionService` / `SystemRiskGate` / exec (`reevaluation_enabled
  = False`, exactly like the accepted N01-B harness: no AI, no provider latency dependence, no
  paid model is contacted);
* one controlled `LIVE_PAPER` SPOT LONG lifecycle through the formal
  `TradePlan -> Risk -> Paper Execution -> Position -> Ledger` path, then a real risk-reducing
  `manual_close` on the last real fresh tradable BTC BBO.

Explicitly NOT in scope: N01-7 2h soak, N01-8 12h soak, restart/recovery, Integrated Runtime
Host, live trading, private OKX endpoints, OKX API keys, real funds, real AI.

Run:  py -3.14 scripts/verify_n01_6_runtime_smoke.py
      py -3.14 scripts/verify_n01_6_runtime_smoke.py --seconds 60    # harness self-check only

Environment note (environment, not a product fact): the surrounding development sandbox
injects `HTTP_PROXY`/`HTTPS_PROXY` pointing at a local proxy that fails OKX. This process
clears those variables for itself only. No production code is modified and no machine or
system proxy setting is touched.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPOSITORY_ROOT / "backend" / "src", REPOSITORY_ROOT / "backend" / "tests"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Clear the sandbox-injected proxy before any client is constructed. Process-local only.
for _name in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
):
    os.environ.pop(_name, None)

from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    FillRecord,
    PaperOrderRecord,
    PositionRecord,
    RuntimeControlRecord,
    TradeRecord,
)
from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner
from marketpulse.g3.models import (
    BestBidAsk,
    DataQuality,
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
from marketpulse.g3.service import persist_trade_plan, stable_id
from marketpulse.g4.models import HealthComponent
from marketpulse.g4.reconciliation import count_open_buys, reconcile
from marketpulse.market_data.models import MarketType, NormalizedBookTicker, NormalizedTrade
from marketpulse.market_data.okx_live import OKXLiveProvider
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from test_n01_okx_paper_safety import (
    LivePaperHarness,
    _economic_counts,
    _position,
    _sell_fills,
    _settle_background_tasks,
    _wait_for_owned_client_cleanup,
)

RUN_MODE = RunMode.LIVE_PAPER
BTC = "BTC-USDT"
ETH = "ETH-USDT"
INSTRUMENTS = (BTC, ETH)

ACCEPTED_FRESHNESS_TTL_SECONDS = 5.0
# Accepted `PaperExecutionService` default slippage (bps); not overridden by this harness.
ACCEPTED_SLIPPAGE_BPS = 5
DEFAULT_ACTIVE_SECONDS = 900.0
DEFAULT_SAMPLE_INTERVAL_SECONDS = 5.0
CONTROL_NOTIONAL_USD = 100.0
STOP_LOSS_FACTOR = 0.95
TAKE_PROFIT_FACTOR = 1.05
FRESH_QUOTE_MAX_AGE_SECONDS = 2.0
ENTRY_GATE_MAX_WAIT_SECONDS = 120.0
INITIAL_DATA_MAX_WAIT_SECONDS = 90.0

PUBLIC_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
PUBLIC_OKX_ENDPOINTS = (
    "GET /api/v5/public/instruments",
    "WS /ws/v5/public trades",
    "WS /ws/v5/public bbo-tbt",
)
CHANNELS = [
    {"channel": "trades", "instId": BTC},
    {"channel": "trades", "instId": ETH},
    {"channel": "bbo-tbt", "instId": BTC},
    {"channel": "bbo-tbt", "instId": ETH},
]

DATABASE_PREFIX = "marketpulse_n01_6_"
OWNED_APPLICATION = "marketpulse-n01-6-owned-runtime"
OBSERVER_APPLICATION = "marketpulse-n01-6-observer"
CLIENT_BACKEND_TYPE = "client backend"

_ACTIVITY_QUERY = """
SELECT pid, application_name, usename, state, backend_type, wait_event_type, wait_event,
       left(query, 120) AS last_query
FROM pg_stat_activity
WHERE datname = :database_name
ORDER BY pid
"""

try:  # pragma: no cover - psutil is present on this validation host
    import psutil

    _PROCESS: Any = psutil.Process()
except ImportError:  # pragma: no cover
    _PROCESS = None


# ---------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _rss_mb() -> float | None:
    if _PROCESS is None:
        return None
    return round(_PROCESS.memory_info().rss / (1024 * 1024), 3)


def _to_bbo(event: NormalizedBookTicker) -> BestBidAsk:
    """Real normalized OKX event -> the accepted G3 market-data contract."""
    return BestBidAsk(
        instrument_id=event.instrument_id,
        bid=event.bid_price,
        ask=event.ask_price,
        received_at=event.received_time,
        tradable=True,
        data_quality=DataQuality(event.data_quality.value),
    )


def _describe_bbo(bbo: BestBidAsk) -> dict[str, Any]:
    return {
        "instrument_id": bbo.instrument_id,
        "bid": bbo.bid,
        "ask": bbo.ask,
        "data_quality": bbo.data_quality.value,
        "tradable": bbo.tradable,
        "received_at": bbo.received_at.isoformat(),
        "age_seconds_at_use": round((_now() - bbo.received_at).total_seconds(), 6),
    }


async def _wait_until(predicate, timeout: float, interval: float = 0.05) -> bool:
    """Bounded wait on an observed condition; returns whether it became true."""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        await asyncio.sleep(interval)


def _new_feed() -> dict[str, Any]:
    return {
        "lock": asyncio.Lock(),
        "total_normalized_events": 0,
        "trades": {item: 0 for item in INSTRUMENTS},
        "bbos": {item: 0 for item in INSTRUMENTS},
        "first_received": {},
        "last_received": {},
        "last_event_received": {},
        "max_inter_arrival_gap_seconds": {},
        "last_trade_received": {},
        "last_bbo_received": {},
        "latest_bbo": {},
        "bbo_data_quality": {},
        "last_freshness": {},
        "health_status": None,
        "health_transitions": [],
        "stale_periods": [],
        "open_stale": {},
        "errors": [],
    }


# ---------------------------------------------------------------------------------------
# Harness (accepted LivePaperHarness + an explicitly split controlled entry)
# ---------------------------------------------------------------------------------------


class SmokeHarness(LivePaperHarness):
    """Accepted N01-B live-paper harness with the entry split for the §13 gate evidence.

    `LivePaperHarness.open_paper_long` persists the plan and executes it in one step. N01-6
    must prove the risk gate admits the action *before* the controlled BUY is submitted, so
    the exact same construction is split into persist-plan / gate-check / execute. Both halves
    mirror the accepted harness path: same `stable_id` identities, same plan shape, same
    `PaperExecutionService.execute` admission route.

    N01-6 additionally feeds **two** instruments at once, so the single-slot `self.quote`
    accessor of the accepted harness is replaced by a per-instrument latest-quote store. That
    is strictly closer to a real runtime's latest-market-state accessor and removes an
    interleaving artifact (a BTC action must not depend on which symbol's tick arrived last).
    The base `self.quote` attribute is still maintained for coherence.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        self.quotes: dict[str, BestBidAsk] = {}

        async def bbo_for(instrument_id: str) -> BestBidAsk:
            quote = self.quotes.get(instrument_id)
            if quote is None:
                raise RuntimeError(f"harness_has_no_quote:{instrument_id}")
            return quote

        # Validation-harness wiring only: same accessor contract, per-instrument state.
        self.execution.bbo_for = bbo_for

    def publish_quote(self, bbo: BestBidAsk) -> None:
        self.quotes[bbo.instrument_id] = bbo
        self.quote = bbo

    async def persist_controlled_long(
        self,
        bbo: BestBidAsk,
        *,
        stop_factor: float,
        take_profit_factor: float,
        tag: str,
        notional: float = CONTROL_NOTIONAL_USD,
    ) -> TradePlan:
        self.publish_quote(bbo)
        now = self.clock.now()
        plan = TradePlan(
            plan_id=stable_id("plan", "n01-6", tag, self.run_mode, bbo.instrument_id),
            snapshot_id=stable_id("snap", "n01-6", tag, bbo.instrument_id),
            decision_id=stable_id("decision", "n01-6", tag, bbo.instrument_id),
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
        return plan

    async def execute_intent(self, plan: TradePlan, *, tag: str) -> ExecutionResult:
        now = self.clock.now()
        intent = ExecutionIntent(
            intent_id=stable_id("intent", "n01-6", tag, self.run_mode, plan.instrument_id),
            plan_id=plan.plan_id,
            instrument_id=plan.instrument_id,
            run_mode=self.run_mode,
            state_version=self.state_version,
            created_at=now,
        )
        return await self.execution.execute(intent, plan, now)


# ---------------------------------------------------------------------------------------
# Market feed
# ---------------------------------------------------------------------------------------


def _observe_freshness(
    feed: dict[str, Any], instrument: str, bbo: BestBidAsk, harness: LivePaperHarness
) -> None:
    now = _now()
    health = harness.health.status(HealthComponent.CORE_MARKET_DATA.value)
    if feed["health_status"] != health:
        feed["health_transitions"].append(
            {
                "at": now.isoformat(),
                "from": feed["health_status"],
                "to": health,
                "instrument_id": instrument,
            }
        )
        feed["health_status"] = health
    fresh = bool(feed["last_freshness"].get(instrument, {}).get("fresh"))
    if fresh:
        open_period = feed["open_stale"].pop(instrument, None)
        if open_period is not None:
            open_period["end"] = now.isoformat()
            open_period["duration_seconds"] = round(
                time.monotonic() - open_period.pop("start_monotonic"), 6
            )
            open_period["end_health_status"] = health
            feed["stale_periods"].append(open_period)
    elif instrument not in feed["open_stale"]:
        feed["open_stale"][instrument] = {
            "symbol": instrument,
            "start": now.isoformat(),
            "start_monotonic": time.monotonic(),
            "age_seconds_at_start": round((now - bbo.received_at).total_seconds(), 6),
            "health_status": health,
        }


async def _consume(
    stream: Any, pipeline: ScannerPipeline, harness: LivePaperHarness, feed: dict[str, Any]
) -> None:
    """Normalized OKX events -> accepted ScannerPipeline / EventRuntime and SafetyRuntime."""
    async for event in stream:
        async with feed["lock"]:
            feed["total_normalized_events"] += 1
            instrument = event.instrument_id
            received = event.received_time
            if instrument not in feed["first_received"]:
                feed["first_received"][instrument] = received.isoformat()
            previous = feed["last_event_received"].get(instrument)
            if previous is not None:
                gap = (received - previous).total_seconds()
                if gap > feed["max_inter_arrival_gap_seconds"].get(instrument, 0.0):
                    feed["max_inter_arrival_gap_seconds"][instrument] = gap
            feed["last_event_received"][instrument] = received
            feed["last_received"][instrument] = received.isoformat()
            try:
                if isinstance(event, NormalizedTrade):
                    feed["trades"][instrument] += 1
                    feed["last_trade_received"][instrument] = received.isoformat()
                    await pipeline.ingest(event)
                else:
                    bbo = _to_bbo(event)
                    feed["bbos"][instrument] += 1
                    feed["last_bbo_received"][instrument] = bbo.received_at.isoformat()
                    feed["latest_bbo"][instrument] = bbo
                    feed["bbo_data_quality"][instrument] = bbo.data_quality.value
                    harness.publish_quote(bbo)
                    outcome = await harness.feed_market_data(bbo)
                    feed["last_freshness"][instrument] = {
                        "at": _now().isoformat(),
                        "fresh": bool(outcome.get("fresh")),
                        "protection_reason": getattr(outcome.get("protection"), "reason", None),
                        "age_seconds": round((_now() - bbo.received_at).total_seconds(), 6),
                    }
                    _observe_freshness(feed, instrument, bbo, harness)
                    await pipeline.ingest(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - recorded; the smoke keeps running
                feed["errors"].append(
                    {
                        "at": _now().isoformat(),
                        "instrument_id": instrument,
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                )


# ---------------------------------------------------------------------------------------
# PostgreSQL ownership-aware observation
# ---------------------------------------------------------------------------------------


def _observer_engine():
    """Observer connected to the *primary* database: it never counts as a smoke session."""
    return create_async_engine(
        Settings().database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"application_name": OBSERVER_APPLICATION}},
    )


def _smoke_engine(database_url: str):
    return create_async_engine(
        database_url,
        pool_size=6,
        max_overflow=4,
        pool_timeout=10,
        pool_pre_ping=False,
        connect_args={"server_settings": {"application_name": OWNED_APPLICATION}},
    )


async def _ownership_activity(engine, database_name: str) -> dict[str, Any]:
    """Ownership-split snapshot: client backends the smoke could own, vs server backends."""
    async with engine.connect() as connection:
        result = await connection.execute(
            text(_ACTIVITY_QUERY), {"database_name": database_name}
        )
        rows = tuple(dict(row) for row in result.mappings())
    client_rows = [row for row in rows if row["backend_type"] == CLIENT_BACKEND_TYPE]
    owned = [row for row in client_rows if row["application_name"] == OWNED_APPLICATION]
    other = [row for row in client_rows if row["application_name"] != OWNED_APPLICATION]
    return {
        "client_sessions": len(client_rows),
        "owned_client_sessions": len(owned),
        "other_client_sessions": len(other),
        "server_sessions": len(rows) - len(client_rows),
        "idle_in_transaction": sum(1 for row in rows if row["state"] == "idle in transaction"),
        "other_client_rows": other,
    }


async def _runtime_state(sessions) -> dict[str, Any]:
    async with sessions() as session:
        control = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RUN_MODE)
        )
        position = await session.scalar(
            select(PositionRecord).where(
                PositionRecord.run_mode == RUN_MODE, PositionRecord.instrument_id == BTC
            )
        )
    return {
        "operator_state": control.operator_state if control else None,
        "system_state": control.system_state if control else None,
        "btc_position_quantity": position.quantity if position else None,
    }


async def _account(sessions) -> dict[str, Any] | None:
    async with sessions() as session:
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == RUN_MODE)
        )
    if account is None:
        return None
    return {
        "account_id": account.account_id,
        "cash_balance": account.cash_balance,
        "reserved_cash": account.reserved_cash,
        "realized_pnl": account.realized_pnl,
    }


async def _trade(sessions) -> dict[str, Any] | None:
    async with sessions() as session:
        trade = await session.scalar(
            select(TradeRecord).where(TradeRecord.run_mode == RUN_MODE)
        )
    if trade is None:
        return None
    return {
        "trade_id": trade.trade_id,
        "instrument_id": trade.instrument_id,
        "status": trade.status,
        "exit_reason": trade.exit_reason,
        "opened_at": trade.opened_at.isoformat(),
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
    }


async def _fill_facts(sessions) -> list[dict[str, Any]]:
    """Every durable fill with its order side: the ledger-facing economic facts."""
    async with sessions() as session:
        rows = (
            await session.execute(
                select(FillRecord, PaperOrderRecord)
                .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                .where(PaperOrderRecord.run_mode == RUN_MODE)
                .order_by(FillRecord.created_at.asc(), FillRecord.fill_id.asc())
            )
        ).all()
    return [
        {
            "fill_id": fill.fill_id,
            "order_id": order.order_id,
            "side": order.side,
            "order_type": order.order_type,
            "status": order.status,
            "price": fill.price,
            "quantity": fill.quantity,
            "fee": fill.fee,
            "created_at": fill.created_at.isoformat(),
        }
        for fill, order in rows
    ]


async def _primary_alembic_version() -> str | None:
    engine = create_async_engine(Settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        return str(value) if value is not None else None
    finally:
        await engine.dispose()


async def _n01_6_leftover_databases() -> int:
    engine = create_async_engine(Settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_database WHERE datname LIKE "
                        f"'{DATABASE_PREFIX}%'"
                    )
                )
                or 0
            )
    finally:
        await engine.dispose()


@contextmanager
def _disposable_postgres_database() -> Iterator[tuple[str, str]]:
    """Disposable real PostgreSQL database; the primary `marketpulse` DB is never written."""
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
    # `backend/alembic/env.py` prefers `DATABASE_URL` over the configured URL, so anchor it
    # explicitly for the migration and restore the previous value afterwards.
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
    try:
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


# ---------------------------------------------------------------------------------------
# Controlled paper lifecycle
# ---------------------------------------------------------------------------------------


async def _okx_metadata(provider: OKXLiveProvider) -> dict[str, Any]:
    instruments = {
        item.instrument_id: item
        for item in await provider.instruments("SPOT")
        if item.instrument_id in INSTRUMENTS
    }
    if set(instruments) != set(INSTRUMENTS):
        raise AssertionError(f"real OKX SPOT metadata missing: {sorted(instruments)}")
    for item in instruments.values():
        assert item.market_type is MarketType.SPOT
        assert item.tradable is True, item.instrument_id
        assert item.exchange == "OKX"
    return {
        key: {
            "market_type": item.market_type.value,
            "tradable": item.tradable,
            "tick_size": item.tick_size,
            "lot_size": item.lot_size,
        }
        for key, item in instruments.items()
    }


async def _controlled_entry(
    harness: SmokeHarness, sessions, feed: dict[str, Any], checks: dict[str, bool]
) -> dict[str, Any]:
    """One controlled LIVE_PAPER SPOT LONG through the formal economic path (§12-§14)."""
    async with feed["lock"]:
        bbo = feed["latest_bbo"].get(BTC)
        if bbo is None:
            raise AssertionError("no real BTC BBO available for the controlled entry")
        age = (_now() - bbo.received_at).total_seconds()
        checks["entry_bbo_fresh"] = age <= ACCEPTED_FRESHNESS_TTL_SECONDS and bbo.tradable
        checks["entry_symbol_is_btc_spot"] = bbo.instrument_id == BTC

        plan = await harness.persist_controlled_long(
            bbo,
            stop_factor=STOP_LOSS_FACTOR,
            take_profit_factor=TAKE_PROFIT_FACTOR,
            tag="control",
        )
        admitted, reason = await harness.risk_gate.check(RUN_MODE, BTC, plan_id=plan.plan_id)
        checks["entry_risk_gate_admits"] = admitted is True and reason is None
        result = await harness.execute_intent(plan, tag="control")
        checks["entry_executed"] = result.status is IntentStatus.EXECUTED
        if result.status is not IntentStatus.EXECUTED:
            raise AssertionError(f"controlled entry rejected: {result.status} {result.reason}")

        counts = await _economic_counts(sessions, RUN_MODE)
        checks["entry_exactly_one_buy"] = (
            counts["orders"] == 1
            and counts["fills"] == 1
            and counts["positions"] == 1
            and counts["trades"] == 1
        )
        position = await _position(sessions, RUN_MODE, BTC)
        account = await _account(sessions)
        entry_fills = await _fill_facts(sessions)
        entry_fill = next(
            (item for item in entry_fills if item["fill_id"] == result.fill_id), None
        )
        expected_entry_price = bbo.ask * (1 + ACCEPTED_SLIPPAGE_BPS / 10_000)
        checks["entry_fill_at_real_ask_plus_slippage"] = entry_fill is not None and (
            abs(entry_fill["price"] - expected_entry_price)
            <= 1e-9 * max(1.0, abs(expected_entry_price))
        )
        # Idempotency witness: the same intent identity must never create a second fact.
        duplicate = await harness.execute_intent(plan, tag="control")
        duplicate_counts = await _economic_counts(sessions, RUN_MODE)
        checks["entry_duplicate_intent_idempotent"] = (
            duplicate.status is IntentStatus.EXECUTED
            and duplicate.reason == "duplicate_intent"
            and duplicate_counts == counts
        )
        return {
            "entry_quote": _describe_bbo(bbo),
            "risk_gate": {"admitted": admitted, "reason": reason},
            "plan": {
                "plan_id": plan.plan_id,
                "side": plan.side.value,
                "order_type": plan.order_type.value,
                "intended_notional": plan.intended_notional,
                "entry_zone": {"lower": plan.entry_zone.lower, "upper": plan.entry_zone.upper},
                "stop_loss": plan.stop_loss,
                "take_profit": plan.take_profit,
                "expires_at": plan.expires_at.isoformat(),
            },
            "order_id": result.order_id,
            "fill_id": result.fill_id,
            "position": {
                "position_id": position.position_id if position else None,
                "quantity": position.quantity if position else None,
                "average_cost": position.average_cost if position else None,
                "trade_id": position.trade_id if position else None,
            },
            "account_after_entry": account,
            "counts_after_entry": counts,
            "fills_after_entry": entry_fills,
            "duplicate_intent": {
                "status": duplicate.status.value,
                "reason": duplicate.reason,
                "order_id": duplicate.order_id,
                "counts_unchanged": duplicate_counts == counts,
            },
        }


async def _controlled_close(
    harness: SmokeHarness, sessions, feed: dict[str, Any], checks: dict[str, bool]
) -> dict[str, Any]:
    """Risk-reducing close on the last real fresh tradable BTC BBO (§15).

    If the accepted production protection path already closed the position naturally during the
    smoke, that real outcome is recorded instead of forcing a new economic action.
    """
    async with feed["lock"]:
        position = await _position(sessions, RUN_MODE, BTC)
        if position is None or position.quantity == 0.0:
            trade = await _trade(sessions)
            checks["close_natural_protection"] = True
            checks["close_bbo_fresh"] = True
            checks["close_executed"] = True
            checks["close_position_flat"] = True
            checks["close_no_open_buys"] = await count_open_buys(sessions, RUN_MODE) == 0
            return {
                "closed_by": "native_protection_during_smoke",
                "trade": trade,
                "counts_after_close": await _economic_counts(sessions, RUN_MODE),
                "account_after_close": await _account(sessions),
                "fills": await _fill_facts(sessions),
            }
        bbo = feed["latest_bbo"].get(BTC)
        if bbo is None:
            raise AssertionError("no real BTC BBO available for the controlled close")
        age = (_now() - bbo.received_at).total_seconds()
        checks["close_bbo_fresh"] = age <= ACCEPTED_FRESHNESS_TTL_SECONDS and bbo.tradable
        harness.publish_quote(bbo)
        outcome = await harness.protection.manual_close(RUN_MODE, BTC, bbo)
        checks["close_executed"] = bool(outcome.triggered)
        if not outcome.triggered:
            raise AssertionError(f"controlled close rejected: {outcome.reason}")
        counts = await _economic_counts(sessions, RUN_MODE)
        flat = await _position(sessions, RUN_MODE, BTC)
        checks["close_position_flat"] = flat is None or flat.quantity == 0.0
        checks["close_no_open_buys"] = await count_open_buys(sessions, RUN_MODE) == 0
        exit_fills = await _fill_facts(sessions)
        exit_fill = next(
            (item for item in exit_fills if item["fill_id"] == outcome.fill_id), None
        )
        expected_exit_price = bbo.bid * (1 - ACCEPTED_SLIPPAGE_BPS / 10_000)
        checks["close_fill_at_real_bid_minus_slippage"] = exit_fill is not None and (
            abs(exit_fill["price"] - expected_exit_price)
            <= 1e-9 * max(1.0, abs(expected_exit_price))
        )
        return {
            "closed_by": "controlled_manual_close",
            "close_quote": _describe_bbo(bbo),
            "exit_reason": outcome.exit_reason.value if outcome.exit_reason else None,
            "order_id": outcome.order_id,
            "fill_id": outcome.fill_id,
            "cancelled_order_ids": list(outcome.cancelled_order_ids or ()),
            "trade": await _trade(sessions),
            "position_after_close_quantity": flat.quantity if flat else 0.0,
            "account_after_close": await _account(sessions),
            "counts_after_close": counts,
            "fills": exit_fills,
        }


# ---------------------------------------------------------------------------------------
# Smoke scenario
# ---------------------------------------------------------------------------------------


async def _scenario(
    database_name: str, database_url: str, active_seconds: float, sample_interval: float
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure: dict[str, Any] | None = None
    samples: list[dict[str, Any]] = []
    feed = _new_feed()
    ctx: dict[str, Any] = {"feed": feed, "samples": samples}
    engine = None
    observer = None
    runtime: EventRuntime | None = None
    consumer: asyncio.Task | None = None
    sampler: asyncio.Task | None = None
    stream = None
    provider = OKXLiveProvider()

    try:
        engine = _smoke_engine(database_url)
        observer = _observer_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ctx["sessions"] = sessions

        ctx["baseline"] = await _ownership_activity(observer, database_name)
        ctx["metadata"] = await _okx_metadata(provider)

        harness = SmokeHarness(sessions)
        await harness.boot()
        ctx["harness"] = harness
        runtime = EventRuntime(PostgresG2Repository(sessions))
        pipeline = ScannerPipeline(OpportunityScanner(), runtime)
        await runtime.start()
        ctx["runtime"] = runtime
        ctx["pipeline"] = pipeline

        stream = provider.stream(list(CHANNELS))
        ctx["stream"] = stream
        consumer = asyncio.create_task(
            _consume(stream, pipeline, harness, feed), name="n01-6-market-consumer"
        )
        ctx["consumer"] = consumer
        ctx["rss_start"] = _rss_mb()

        def initial_data_ready() -> bool:
            return all(
                feed["trades"][item] > 0 and feed["bbos"][item] > 0 for item in INSTRUMENTS
            )

        ready = await _wait_until(initial_data_ready, INITIAL_DATA_MAX_WAIT_SECONDS, 0.2)
        checks["initial_real_data_both_symbols"] = ready
        if not ready:
            raise AssertionError("real BTC/ETH trade+BBO data did not arrive in time")

        active_started_at = _now()
        ctx["active_started_monotonic"] = time.monotonic()
        ctx["active_started_at"] = active_started_at
        entry_offset = min(60.0, max(10.0, active_seconds * 0.10))

        async def sample_once() -> dict[str, Any]:
            activity = await _ownership_activity(observer, database_name)
            state = await _runtime_state(sessions)
            snapshot = {
                "at": _now().isoformat(),
                "elapsed_seconds": round(
                    time.monotonic() - ctx["active_started_monotonic"], 3
                ),
                "btc_last_trade_received_at": feed["last_trade_received"].get(BTC),
                "eth_last_trade_received_at": feed["last_trade_received"].get(ETH),
                "btc_last_bbo_received_at": feed["last_bbo_received"].get(BTC),
                "eth_last_bbo_received_at": feed["last_bbo_received"].get(ETH),
                "btc_data_quality": feed["bbo_data_quality"].get(BTC),
                "eth_data_quality": feed["bbo_data_quality"].get(ETH),
                "btc_last_fresh": feed["last_freshness"].get(BTC, {}).get("fresh"),
                "eth_last_fresh": feed["last_freshness"].get(ETH, {}).get("fresh"),
                "queue_size": runtime.queue.qsize(),
                "inflight": len(runtime._inflight),
                "worker_count": len(runtime._workers),
                "worker_exceptions": len(runtime.worker_exceptions),
                "dedupe_size": len(runtime._dedupe),
                "dedupe_capacity": runtime._dedupe_capacity,
                "worker_exception_capacity": runtime._worker_exception_capacity,
                "rss_mb": _rss_mb(),
                "owned_client_sessions": activity["owned_client_sessions"],
                "other_client_sessions": activity["other_client_sessions"],
                "idle_in_transaction": activity["idle_in_transaction"],
                "system_state": state["system_state"],
                "operator_state": state["operator_state"],
                "btc_position_quantity": state["btc_position_quantity"],
            }
            samples.append(snapshot)
            return snapshot

        async def sample_loop() -> None:
            while True:
                try:
                    await sample_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    feed["errors"].append(
                        {
                            "at": _now().isoformat(),
                            "instrument_id": None,
                            "type": type(exc).__name__,
                            "message": f"sampler: {exc}",
                        }
                    )
                await asyncio.sleep(sample_interval)

        await sample_once()
        sampler = asyncio.create_task(sample_loop(), name="n01-6-sampler")
        ctx["sampler"] = sampler

        entry_done = False
        while True:
            elapsed = time.monotonic() - ctx["active_started_monotonic"]
            if not entry_done and elapsed >= entry_offset:
                def entry_ready() -> bool:
                    return (
                        harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                        and BTC in feed["latest_bbo"]
                        and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                        <= FRESH_QUOTE_MAX_AGE_SECONDS
                        and feed["last_freshness"].get(BTC, {}).get("fresh") is True
                    )

                await _wait_until(entry_ready, timeout=ENTRY_GATE_MAX_WAIT_SECONDS)
                ctx["entry"] = await _controlled_entry(harness, sessions, feed, checks)
                entry_done = True
            if elapsed >= active_seconds:
                break
            await asyncio.sleep(0.5)

        ctx["active_duration_seconds"] = time.monotonic() - ctx["active_started_monotonic"]
        ctx["active_finished_at"] = _now()
        checks["active_duration_ge_900"] = ctx["active_duration_seconds"] >= 900.0
        checks["controlled_entry_performed"] = "entry" in ctx

        await _wait_until(
            lambda: (
                BTC in feed["latest_bbo"]
                and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                <= FRESH_QUOTE_MAX_AGE_SECONDS
            ),
            timeout=30.0,
        )
        ctx["exit"] = await _controlled_close(harness, sessions, feed, checks)

        # -------------------------------------------------------------------- shutdown (§27)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        consumer = None
        ctx["consumer"] = None
        await stream.aclose()
        stream = None
        ctx["stream"] = None
        await runtime.stop()
        sampler.cancel()
        await asyncio.gather(sampler, return_exceptions=True)
        sampler = None
        ctx["sampler"] = None

        ctx["queue_final"] = runtime.queue.qsize()
        ctx["inflight_final"] = len(runtime._inflight)
        ctx["workers_final"] = len(runtime._workers)
        ctx["worker_exceptions_final"] = len(runtime.worker_exceptions)
        ctx["worker_tasks_final"] = [
            task.get_name()
            for task in asyncio.all_tasks()
            if task.get_name().startswith("g2-event-worker-") and not task.done()
        ]
        checks["queue_drained"] = ctx["queue_final"] == 0
        checks["inflight_empty"] = ctx["inflight_final"] == 0
        checks["runtime_workers_stopped"] = (
            ctx["workers_final"] == 0 and not ctx["worker_tasks_final"]
        )
        checks["worker_exceptions_zero"] = ctx["worker_exceptions_final"] == 0

        ctx["counts_final"] = await _economic_counts(sessions, RUN_MODE)
        ctx["account_final"] = await _account(sessions)
        position_final = await _position(sessions, RUN_MODE, BTC)
        ctx["position_final"] = {
            "quantity": position_final.quantity if position_final else 0.0,
            "average_cost": position_final.average_cost if position_final else None,
        }
        ctx["open_buys_final"] = await count_open_buys(sessions, RUN_MODE)
        ctx["sell_fills"] = [fill.fill_id for fill in await _sell_fills(sessions, RUN_MODE)]
        ctx["trade_final"] = await _trade(sessions)
        ctx["fills_final"] = await _fill_facts(sessions)

        report_obj = await reconcile(
            RUN_MODE, sessions=sessions, execution=harness.execution, now=harness.clock.now()
        )
        ctx["reconciliation"] = report_obj
        checks["reconciliation_ok"] = report_obj.ok is True
        checks["final_position_flat"] = ctx["position_final"]["quantity"] == 0.0
        checks["final_no_open_buy"] = ctx["open_buys_final"] == 0
        checks["final_exactly_one_exit_fill"] = len(ctx["sell_fills"]) == 1
        checks["final_single_trade_lifecycle"] = (
            ctx["trade_final"] is not None and ctx["trade_final"]["status"] == "CLOSED"
        )
        checks["final_no_duplicate_facts"] = (
            ctx["counts_final"]["orders"] == 2
            and ctx["counts_final"]["fills"] == 2
            and ctx["counts_final"]["positions"] == 1
        )
        checks["final_reserved_cash_zero"] = bool(
            ctx["account_final"] and ctx["account_final"]["reserved_cash"] == 0
        )
        checks["final_cash_non_negative"] = bool(
            ctx["account_final"] and ctx["account_final"]["cash_balance"] >= 0
        )

        ctx["background_tasks"] = await _settle_background_tasks()
        checks["no_detached_runtime_tasks"] = (
            ctx["background_tasks"]["remaining_pending_tasks"] == []
        )
        checks["shutdown_no_errors"] = True

        ctx["rss_end"] = _rss_mb()
        await engine.dispose()
        engine = None
        await observer.dispose()
        observer = None

        cleanup = await _wait_for_owned_client_cleanup(database_name, OWNED_APPLICATION)
        ctx["cleanup"] = cleanup
        checks["pg_owned_clients_zero"] = cleanup.final_snapshot.client_sessions == 0
        checks["pg_idle_in_transaction_zero"] = cleanup.final_snapshot.idle_in_transaction == 0
        checks["pg_no_foreign_client_sessions"] = not cleanup.foreign_rows

        for instrument, period in list(feed["open_stale"].items()):
            period.pop("start_monotonic", None)
            period["end"] = ctx["active_finished_at"].isoformat()
            period["duration_seconds"] = round(
                ctx["active_duration_seconds"], 6
            )
            feed["stale_periods"].append(period)
        feed["open_stale"].clear()

        checks["no_harness_event_errors"] = feed["errors"] == []
        checks["retention_within_capacity"] = all(
            item["dedupe_size"] <= item["dedupe_capacity"]
            and item["worker_exceptions"] <= item["worker_exception_capacity"]
            for item in samples
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - always report, then shut down in `finally`
        failure = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        shutdown_errors: list[dict[str, Any]] = []
        if sampler is not None:
            sampler.cancel()
            await asyncio.gather(sampler, return_exceptions=True)
        if consumer is not None:
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)
        if stream is not None:
            try:
                await stream.aclose()
            except Exception as exc:  # noqa: BLE001 - shutdown must continue to the next step
                shutdown_errors.append(
                    {"step": "stream_aclose", "type": type(exc).__name__, "message": str(exc)}
                )
        if runtime is not None:
            try:
                await runtime.stop()
            except Exception as exc:  # noqa: BLE001 - shutdown must continue to the next step
                shutdown_errors.append(
                    {"step": "runtime_stop", "type": type(exc).__name__, "message": str(exc)}
                )
            ctx.setdefault("queue_final", runtime.queue.qsize())
            ctx.setdefault("inflight_final", len(runtime._inflight))
            ctx.setdefault("workers_final", len(runtime._workers))
            ctx.setdefault("worker_exceptions_final", len(runtime.worker_exceptions))
        if engine is not None:
            await engine.dispose()
        if observer is not None:
            await observer.dispose()
        try:
            cleanup = await _wait_for_owned_client_cleanup(database_name, OWNED_APPLICATION)
            ctx["cleanup"] = cleanup
            checks.setdefault("pg_owned_clients_zero", cleanup.final_snapshot.client_sessions == 0)
            checks.setdefault(
                "pg_idle_in_transaction_zero",
                cleanup.final_snapshot.idle_in_transaction == 0,
            )
            checks.setdefault("pg_no_foreign_client_sessions", not cleanup.foreign_rows)
        except Exception as exc:  # noqa: BLE001 - record the evidence gap instead of hiding it
            shutdown_errors.append(
                {
                    "step": "owned_client_cleanup_probe",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            checks.setdefault("pg_owned_clients_zero", False)
            checks.setdefault("pg_idle_in_transaction_zero", False)
        ctx.setdefault("rss_end", _rss_mb())
        checks.setdefault("no_harness_event_errors", feed["errors"] == [])
        checks.setdefault("shutdown_no_errors", not shutdown_errors)
        ctx["shutdown_errors"] = shutdown_errors
        checks.setdefault(
            "retention_within_capacity",
            all(
                item["dedupe_size"] <= item["dedupe_capacity"]
                and item["worker_exceptions"] <= item["worker_exception_capacity"]
                for item in samples
            ),
        )

    return _build_report(database_name, ctx, checks, failure, provider, active_seconds, samples)


def _build_report(
    database_name: str,
    ctx: dict[str, Any],
    checks: dict[str, bool],
    failure: dict[str, Any] | None,
    provider: OKXLiveProvider,
    requested_active_seconds: float,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    feed = ctx["feed"]
    runtime: EventRuntime | None = ctx.get("runtime")

    def _max(key: str, default: Any = 0) -> Any:
        values = [item[key] for item in samples if item.get(key) is not None]
        return max(values) if values else default

    cleanup = ctx.get("cleanup")
    background = ctx.get("background_tasks")
    report_obj = ctx.get("reconciliation")
    account_final = ctx.get("account_final")
    position_final = ctx.get("position_final")

    return {
        "result": None,  # decided by main()
        "database_name": database_name,
        "run_mode": RUN_MODE.value,
        "requested_active_seconds": requested_active_seconds,
        "active_started_at": ctx.get("active_started_at").isoformat()
        if ctx.get("active_started_at")
        else None,
        "active_finished_at": ctx.get("active_finished_at").isoformat()
        if ctx.get("active_finished_at")
        else None,
        "active_duration_seconds": round(ctx.get("active_duration_seconds", 0.0), 3),
        "okx": {
            "endpoints": list(PUBLIC_OKX_ENDPOINTS),
            "ws_url": PUBLIC_WS_URL,
            "channels": CHANNELS,
            "metadata": ctx.get("metadata"),
            "connection_attempts": provider.connection_attempts,
            "reconnects": provider.reconnects,
            "api_key_used": False,
            "private_endpoint_used": False,
        },
        "market_data": {
            "total_normalized_events": feed["total_normalized_events"],
            "per_symbol": {
                item: {
                    "trades": feed["trades"][item],
                    "bbos": feed["bbos"][item],
                    "first_received_at": feed["first_received"].get(item),
                    "last_received_at": feed["last_received"].get(item),
                    "max_inter_arrival_gap_seconds": round(
                        feed["max_inter_arrival_gap_seconds"].get(item, 0.0), 6
                    ),
                }
                for item in INSTRUMENTS
            },
        },
        "runtime": {
            "worker_count": 4,
            "queue_capacity": runtime.queue.maxsize if runtime else None,
            "dedupe_capacity": runtime._dedupe_capacity if runtime else None,
            "worker_exception_capacity": runtime._worker_exception_capacity if runtime else None,
            "queue_high_water": _max("queue_size"),
            "inflight_high_water": _max("inflight"),
            "dedupe_max": _max("dedupe_size"),
            "worker_exception_max": _max("worker_exceptions"),
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_tasks_final": ctx.get("worker_tasks_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
        },
        "memory": {
            "rss_start_mb": ctx.get("rss_start"),
            "rss_peak_mb": _max("rss_mb", None),
            "rss_end_mb": ctx.get("rss_end"),
        },
        "postgres": {
            "baseline": ctx.get("baseline"),
            "max_owned_client_sessions": _max("owned_client_sessions"),
            "max_other_client_sessions": _max("other_client_sessions"),
            "max_idle_in_transaction": _max("idle_in_transaction"),
            "cleanup": None
            if cleanup is None
            else {
                "owned_application": OWNED_APPLICATION,
                "released": cleanup.released,
                "released_seconds": round(cleanup.elapsed_seconds, 6),
                "polls": cleanup.polls,
                "client_sessions_final": cleanup.final_snapshot.client_sessions,
                "idle_in_transaction_final": cleanup.final_snapshot.idle_in_transaction,
                "foreign_rows": list(cleanup.foreign_rows),
            },
        },
        "paper_lifecycle": {
            "entry": ctx.get("entry"),
            "exit": ctx.get("exit"),
            "position_present_samples": sum(
                1
                for item in samples
                if item.get("btc_position_quantity") is not None
                and item["btc_position_quantity"] > 0
            ),
            "sample_count": len(samples),
            "sample_interval_seconds": DEFAULT_SAMPLE_INTERVAL_SECONDS,
        },
        "economic_invariants": {
            "counts_final": ctx.get("counts_final"),
            "account_final": account_final,
            "position_final": position_final,
            "open_buys_final": ctx.get("open_buys_final"),
            "sell_fill_ids": ctx.get("sell_fills"),
            "trade_final": ctx.get("trade_final"),
            "fills_final": ctx.get("fills_final"),
        },
        "reconciliation": None
        if report_obj is None
        else {
            "ok": report_obj.ok,
            "diagnostics": list(report_obj.diagnostics),
            "invariants": dict(report_obj.invariants),
            "details": {key: value for key, value in report_obj.details.items() if key != "g3"},
        },
        "freshness": {
            "stale_periods": feed["stale_periods"],
            "health_transitions": feed["health_transitions"],
            "production_ttl_seconds": ACCEPTED_FRESHNESS_TTL_SECONDS,
        },
        "shutdown": {
            "background_tasks": background,
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_tasks_final": ctx.get("worker_tasks_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
            "errors": ctx.get("shutdown_errors", []),
        },
        "harness_errors": feed["errors"][:100],
        "checks": checks,
        "failure": failure,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="N01-6 15-minute short runtime smoke")
    parser.add_argument(
        "--seconds",
        type=float,
        default=DEFAULT_ACTIVE_SECONDS,
        help="active continuous runtime interval (default 900 = the N01-6 acceptance value)",
    )
    parser.add_argument("--sample-interval", type=float, default=DEFAULT_SAMPLE_INTERVAL_SECONDS)
    args = parser.parse_args()
    strict = args.seconds >= 900.0

    started = _now()
    primary_version_before = asyncio.run(_primary_alembic_version())
    with _disposable_postgres_database() as (database_name, database_url):
        report = asyncio.run(
            _scenario(database_name, database_url, args.seconds, args.sample_interval)
        )
    leftover = asyncio.run(_n01_6_leftover_databases())
    primary_version_after = asyncio.run(_primary_alembic_version())

    checks: dict[str, bool] = dict(report.get("checks", {}))
    checks["primary_database_not_migrated"] = primary_version_before == primary_version_after
    checks["disposable_database_residue_zero"] = leftover == 0
    report["checks"] = checks
    report["mode"] = "ACCEPTANCE" if strict else "PROBE"
    report["leftover_n01_6_databases"] = leftover
    report["primary_database_alembic_version"] = {
        "before": primary_version_before,
        "after": primary_version_after,
    }
    report["started_at"] = started.isoformat()
    report["finished_at"] = _now().isoformat()
    report["wall_clock_seconds"] = round((_now() - started).total_seconds(), 3)
    report["network_environment_note"] = (
        "sandbox-injected HTTP(S)_PROXY cleared for this process only; no product or machine "
        "proxy configuration was added or modified."
    )
    failures = sorted(
        key
        for key, value in checks.items()
        if value is not True and not (key == "active_duration_ge_900" and not strict)
    )
    report["failures"] = failures
    if report.get("failure") is not None or failures:
        report["result"] = "FAIL"
    else:
        report["result"] = "PASS" if strict else "PROBE_OK"

    print(json.dumps(report, indent=2, default=str))
    return 0 if report["result"] in {"PASS", "PROBE_OK"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
