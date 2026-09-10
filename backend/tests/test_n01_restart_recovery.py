"""N01-C — real PostgreSQL restart / recovery / reconciliation validation.

The parent pytest process only creates isolated databases and observes child output.  Process A
and Process B are separate Python OS processes: the only cross-process inputs are a disposable
database URL and a named deterministic scenario.  In particular, no harness, ORM object, health
registry, or in-memory quote is transferred from A to B.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.db.models import (
    AccountRecord,
    FillRecord,
    IncidentRecord,
    LedgerEntryRecord,
    PaperOrderRecord,
    PositionRecord,
    RuntimeControlRecord,
    TradeRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    ExecutionIntent,
    IntentStatus,
    OrderSide,
    OrderStatus,
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
    IncidentType,
    OperatorState,
    SystemState,
)
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.recovery import RecoveryManager
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.runtime import HealthRegistry
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

BTC = "BTC-USDT"
RUN_MODE = RunMode.LIVE_PAPER
STATE_VERSION = 7
PROCESS_A_NOW = datetime(2026, 9, 11, 12, tzinfo=UTC)
PROCESS_B_NOW = PROCESS_A_NOW + timedelta(minutes=30)
GAP_THRESHOLD = timedelta(seconds=10)
APPLICATION_PREFIX = "marketpulse-n01-c-owned"
OBSERVER_APPLICATION = "marketpulse-n01-c-observer"
CLEANUP_DEADLINE_SECONDS = 1.0
CLEANUP_POLL_SECONDS = 0.002


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now.astimezone(UTC)

    def now(self) -> datetime:
        return self._now


@dataclass
class ProcessHarness:
    database_url: str
    clock: FixedClock
    application_name: str
    quote: BestBidAsk | None = None
    fail_bbo: bool = False
    engine: Any = field(init=False)
    sessions: async_sessionmaker[AsyncSession] = field(init=False)

    def __post_init__(self) -> None:
        self.engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,
            connect_args={"server_settings": {"application_name": self.application_name}},
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.health = HealthRegistry()
        for component in HealthComponent:
            self.health.set(component.value, HealthStatus.HEALTHY.value)
        self.state_service = SystemStateService(self.sessions, clock=self.clock)
        self.incidents = IncidentManager(self.sessions, clock=self.clock)

        async def bbo_for(instrument_id: str) -> BestBidAsk:
            if self.fail_bbo:
                raise RuntimeError("deterministic_recovery_bbo_failure")
            if self.quote is None or self.quote.instrument_id != instrument_id:
                raise RuntimeError(f"deterministic_recovery_bbo_missing:{instrument_id}")
            return self.quote

        async def state_version_for(_instrument_id: str) -> int:
            return STATE_VERSION

        self.bbo_for = bbo_for
        self.execution = PaperExecutionService(
            self.sessions,
            bbo_for,
            state_version_for,
            initial_balance=10_000.0,
            clock=self.clock,
        )
        self.risk_gate = SystemRiskGate(
            self.sessions, self.state_service, self.incidents, self.health, clock=self.clock
        )
        self.execution.risk_gate = self.risk_gate
        self.protection = PositionProtectionService(
            self.sessions, self.execution, self.incidents, self.health, clock=self.clock
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


def _quote(now: datetime, bid: float, ask: float) -> BestBidAsk:
    """DETERMINISTIC RECOVERY BBO — intentionally not a real OKX observation."""
    return BestBidAsk(instrument_id=BTC, bid=bid, ask=ask, received_at=now)


def _plan(scenario: str, tag: str, *, order_type: OrderType, entry: PriceZone) -> TradePlan:
    return TradePlan(
        plan_id=stable_id("n01-c", scenario, tag, "plan"),
        snapshot_id=stable_id("n01-c", scenario, tag, "snapshot"),
        decision_id=stable_id("n01-c", scenario, tag, "decision"),
        instrument_id=BTC,
        symbol=BTC,
        run_mode=RUN_MODE,
        state_version=STATE_VERSION,
        plan_version=1,
        status=PlanStatus.ACTIVE,
        created_at=PROCESS_A_NOW,
        expires_at=PROCESS_A_NOW + timedelta(hours=2),
        side=OrderSide.BUY,
        order_type=order_type,
        entry_zone=entry,
        stop_loss=80.0,
        take_profit=140.0,
        intended_notional=100.0 if order_type is OrderType.MARKET else 50.0,
    )


def _intent(scenario: str, tag: str, plan: TradePlan) -> ExecutionIntent:
    return ExecutionIntent(
        intent_id=stable_id("n01-c", scenario, tag, "intent"),
        plan_id=plan.plan_id,
        instrument_id=BTC,
        run_mode=RUN_MODE,
        state_version=STATE_VERSION,
        created_at=PROCESS_A_NOW,
    )


async def _snapshot(sessions: async_sessionmaker[AsyncSession]) -> dict[str, Any]:
    """Machine-readable economic facts; position-event/outbox audit rows are intentionally excluded."""
    async with sessions() as session:
        account = await session.scalar(select(AccountRecord).where(AccountRecord.run_mode == RUN_MODE))
        positions = list(
            (await session.scalars(select(PositionRecord).where(PositionRecord.run_mode == RUN_MODE))).all()
        )
        orders = list(
            (await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.run_mode == RUN_MODE))).all()
        )
        trades = list(
            (await session.scalars(select(TradeRecord).where(TradeRecord.run_mode == RUN_MODE))).all()
        )
        fills = list(
            (
                await session.scalars(
                    select(FillRecord)
                    .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                    .where(PaperOrderRecord.run_mode == RUN_MODE)
                )
            ).all()
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
        control = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RUN_MODE)
        )
        incidents = list(
            (await session.scalars(select(IncidentRecord).where(IncidentRecord.run_mode == RUN_MODE))).all()
        )
    return {
        "orders": len(orders),
        "fills": len(fills),
        "positions": len(positions),
        "trades": len(trades),
        "accounts": 0 if account is None else 1,
        "ledger": ledger,
        "open_buys": sum(
            order.status == OrderStatus.OPEN and order.side == OrderSide.BUY for order in orders
        ),
        "reserved_cash": None if account is None else account.reserved_cash,
        "position_quantity": sum(position.quantity for position in positions),
        "order_statuses": {order.order_id: str(order.status) for order in orders},
        "fill_prices": {fill.order_id: fill.price for fill in fills},
        "control": None
        if control is None
        else {
            "operator_state": str(control.operator_state),
            "system_state": str(control.system_state),
            "heartbeat_at": control.heartbeat_at.isoformat(),
        },
        "incidents": sorted(
            (
                {
                "type": str(incident.incident_type),
                "status": str(incident.status),
                "reason": incident.reason,
                }
                for incident in incidents
            ),
            key=lambda item: (item["type"], item["status"], item["reason"]),
        ),
    }


async def _process_a(database_url: str, scenario: str) -> dict[str, Any]:
    harness = ProcessHarness(
        database_url,
        FixedClock(PROCESS_A_NOW),
        f"{APPLICATION_PREFIX}-process-a-{scenario}",
    )
    try:
        harness.quote = _quote(PROCESS_A_NOW, 99.0, 100.0)
        await harness.state_service.ensure(RUN_MODE)
        await harness.state_service.transition(
            RUN_MODE,
            operator_state=OperatorState.NORMAL,
            system_state=SystemState.RUNNING,
            reason="n01_c_process_a_boot",
        )
        await harness.execution.bootstrap_account(RUN_MODE)

        position_plan = _plan(
            scenario, "position", order_type=OrderType.MARKET, entry=PriceZone(lower=90, upper=120)
        )
        await persist_trade_plan(harness.sessions, position_plan)
        position_result = await harness.execution.execute(
            _intent(scenario, "position", position_plan), position_plan, PROCESS_A_NOW
        )
        assert position_result.status is IntentStatus.EXECUTED, position_result.reason

        pending_order_id: str | None = None
        if scenario in {"healthy", "invalid_buy", "safe_mode"}:
            pending_plan = _plan(
                scenario,
                "pending-buy",
                order_type=OrderType.LIMIT,
                entry=PriceZone(lower=90, upper=105),
            )
            await persist_trade_plan(harness.sessions, pending_plan)
            pending_result = await harness.execution.execute(
                _intent(scenario, "pending-buy", pending_plan), pending_plan, PROCESS_A_NOW
            )
            assert pending_result.status is IntentStatus.EXECUTED, pending_result.reason
            pending_order_id = pending_result.order_id
            assert pending_order_id is not None

        if scenario == "safe_mode":
            await harness.state_service.transition(
                RUN_MODE, system_state=SystemState.SAFE_MODE, reason="n01_c_durable_safe_mode"
            )
        elif scenario == "paused":
            await harness.state_service.transition(
                RUN_MODE,
                operator_state=OperatorState.PAUSED,
                system_state=SystemState.PAUSED,
                reason="n01_c_durable_paused",
            )

        durable_heartbeat = PROCESS_A_NOW - timedelta(minutes=5)
        async with harness.sessions() as session, session.begin():
            await session.execute(
                update(RuntimeControlRecord)
                .where(RuntimeControlRecord.run_mode == RUN_MODE)
                .values(heartbeat_at=durable_heartbeat)
            )
        return {
            "pid": os.getpid(),
            "scenario": scenario,
            "pending_order_id": pending_order_id,
            "durable_heartbeat": durable_heartbeat.isoformat(),
            "before_exit": await _snapshot(harness.sessions),
        }
    finally:
        await harness.dispose()


async def _process_b(database_url: str, scenario: str) -> dict[str, Any]:
    harness = ProcessHarness(
        database_url,
        FixedClock(PROCESS_B_NOW),
        f"{APPLICATION_PREFIX}-process-b-{scenario}",
    )
    try:
        if scenario == "stop":
            harness.quote = _quote(PROCESS_B_NOW, 79.0, 80.0)
        elif scenario == "invalid_buy":
            harness.quote = _quote(PROCESS_B_NOW, 120.0, 121.0)
        else:
            harness.quote = _quote(PROCESS_B_NOW, 99.0, 100.0)
        harness.fail_bbo = scenario == "bbo_failure"

        reconcile_snapshots: dict[str, dict[str, Any]] = {}

        async def tracked_reconcile(run_mode: RunMode):
            reconcile_snapshots["before"] = await _snapshot(harness.sessions)
            report = await reconcile(
                run_mode,
                sessions=harness.sessions,
                execution=harness.execution,
                now=PROCESS_B_NOW,
                clock=harness.clock,
            )
            reconcile_snapshots["after"] = await _snapshot(harness.sessions)
            return report

        recovery = RecoveryManager(
            harness.sessions,
            harness.state_service,
            harness.incidents,
            harness.health,
            harness.protection,
            harness.execution,
            tracked_reconcile,
            clock=harness.clock,
            gap_threshold=GAP_THRESHOLD,
        )
        before_recovery = await _snapshot(harness.sessions)
        first = await recovery.recover(RUN_MODE, bbo_for=harness.bbo_for, now=PROCESS_B_NOW)
        after_first = await _snapshot(harness.sessions)
        second = await recovery.recover(RUN_MODE, bbo_for=harness.bbo_for, now=PROCESS_B_NOW)
        after_second = await _snapshot(harness.sessions)
        return {
            "pid": os.getpid(),
            "scenario": scenario,
            "before_recovery": before_recovery,
            "reconcile_snapshots": reconcile_snapshots,
            "first": first.model_dump(mode="json"),
            "after_first": after_first,
            "second": second.model_dump(mode="json"),
            "after_second": after_second,
            "recovery_bbo": None if harness.fail_bbo else harness.quote.model_dump(mode="json"),
        }
    finally:
        await harness.dispose()


def _child_main(phase: str, database_url: str, scenario: str) -> None:
    result = asyncio.run(
        _process_a(database_url, scenario) if phase == "a" else _process_b(database_url, scenario)
    )
    print(json.dumps(result, sort_keys=True))


def _run_child(phase: str, database_url: str, scenario: str) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--child", phase, database_url, scenario],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    stdout, stderr = process.communicate(timeout=60)
    assert process.returncode == 0, stderr or stdout
    assert process.poll() == 0  # child is reaped; no Process A/B Python process survives.
    payload_lines = [line for line in stdout.splitlines() if line.startswith("{")]
    assert len(payload_lines) == 1, stdout
    payload = json.loads(payload_lines[0])
    assert payload["pid"] == process.pid
    return payload


async def _execute_admin(url: str, statement: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@contextmanager
def _disposable_postgres_database() -> Iterator[tuple[str, str]]:
    from marketpulse.config import Settings

    primary_url = Settings().database_url
    database_name = f"marketpulse_n01_c_{uuid4().hex[:12]}"
    database_url = f"{primary_url.rsplit('/', 1)[0]}/{database_name}"
    backend = Path(__file__).resolve().parents[1]
    asyncio.run(_execute_admin(primary_url, f'CREATE DATABASE "{database_name}"'))
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    try:
        command.upgrade(config, "head")
        yield database_name, database_url
    finally:
        asyncio.run(
            _execute_admin(
                primary_url,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{database_name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute_admin(primary_url, f'DROP DATABASE "{database_name}"'))


async def _client_activity(database_name: str) -> list[dict[str, Any]]:
    from marketpulse.config import Settings

    observer = create_async_engine(
        Settings().database_url,
        poolclass=NullPool,
        connect_args={"server_settings": {"application_name": OBSERVER_APPLICATION}},
    )
    try:
        async with observer.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT pid, application_name, state, backend_type, xact_start "
                    "FROM pg_stat_activity WHERE datname = :database_name ORDER BY pid"
                ),
                {"database_name": database_name},
            )
            return [dict(row) for row in result.mappings()]
    finally:
        await observer.dispose()


def _assert_postgres_cleanup(database_name: str) -> None:
    deadline = time.monotonic() + CLEANUP_DEADLINE_SECONDS
    latest: list[dict[str, Any]] = []
    while True:
        latest = asyncio.run(_client_activity(database_name))
        clients = [row for row in latest if row["backend_type"] == "client backend"]
        idle_in_transaction = [row for row in clients if row["state"] == "idle in transaction"]
        if not clients and not idle_in_transaction:
            return
        if time.monotonic() >= deadline:
            pytest.fail(f"N01-C PostgreSQL client cleanup failed: {latest}")
        time.sleep(CLEANUP_POLL_SECONDS)


def _economic(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: snapshot[key] for key in ("orders", "fills", "positions", "trades", "accounts", "ledger")}


def _assert_common_boundary(process_a: dict[str, Any], process_b: dict[str, Any]) -> None:
    assert process_a["pid"] != process_b["pid"]
    assert process_a["before_exit"] == process_b["before_recovery"]
    first = process_b["first"]
    assert first["execution_gap"] is not None
    gap = first["execution_gap"]
    assert gap["last_heartbeat"] == process_a["durable_heartbeat"]
    assert gap["recovery_time"] == PROCESS_B_NOW.isoformat()
    assert gap["downtime_seconds"] > GAP_THRESHOLD.total_seconds()
    assert gap["affected_instruments"] == [BTC]
    assert gap["active_risk"]["open_positions"] == [BTC]
    assert "EXECUTION_GAP" in " ".join(
        item["type"] for item in process_b["after_first"]["incidents"]
    )
    # The formally invoked reconcile() is detector-only: no economic row is repaired or invented.
    assert process_b["reconcile_snapshots"]["before"] == process_b["reconcile_snapshots"]["after"]


@pytest.mark.parametrize(
    "scenario",
    ("healthy", "invalid_buy", "stop", "safe_mode", "paused", "bbo_failure"),
)
def test_n01_c_real_postgres_restart_recovery_across_two_python_processes(scenario: str) -> None:
    with _disposable_postgres_database() as (database_name, database_url):
        process_a = _run_child("a", database_url, scenario)
        process_b = _run_child("b", database_url, scenario)
        _assert_postgres_cleanup(database_name)

    print(
        "N01-C process-boundary "
        f"scenario={scenario} process_a_pid={process_a['pid']} process_a_exit=0 "
        f"process_b_pid={process_b['pid']} process_b_exit=0 "
        f"durable_heartbeat={process_a['durable_heartbeat']}"
    )

    _assert_common_boundary(process_a, process_b)
    before = process_a["before_exit"]
    after_first = process_b["after_first"]
    after_second = process_b["after_second"]
    first = process_b["first"]

    if scenario == "healthy":
        assert first["reconciliation"]["ok"] is True
        assert first["final_system_state"] == SystemState.RUNNING
        assert _economic(before) == _economic(after_first) == _economic(after_second)
        assert before["open_buys"] == after_first["open_buys"] == 1
        assert before["reserved_cash"] == after_first["reserved_cash"]
        assert before["position_quantity"] == after_first["position_quantity"]
        assert all(not item["triggered"] for item in first["protection"])
        assert first["protection"][0]["reason"] == "HOLD"
    elif scenario == "invalid_buy":
        assert first["reconciliation"]["ok"] is True
        assert first["final_system_state"] == SystemState.RUNNING
        assert before["fills"] == after_first["fills"] == after_second["fills"]
        assert before["ledger"] == after_first["ledger"] == after_second["ledger"]
        assert after_first["open_buys"] == 0
        assert after_first["reserved_cash"] == 0
        assert after_first["position_quantity"] == before["position_quantity"]
        assert any(
            item["cancelled"] and "BUY_PRICE_OUTSIDE_ENTRY_ZONE" in item["issues"]
            for item in first["order_revalidation"]
        )
        assert all(not item["triggered"] for item in first["protection"])
    elif scenario == "stop":
        assert first["reconciliation"]["ok"] is True
        assert first["final_system_state"] == SystemState.RUNNING
        assert after_first["position_quantity"] == 0
        assert after_first["fills"] == before["fills"] + 1
        assert after_first["ledger"] == before["ledger"] + 1
        assert after_second == after_first  # second recovery creates no duplicate protective exit.
        outcome = first["protection"][0]
        assert outcome["triggered"] is True and outcome["fill_id"] is not None
        # ExecutionResult does not expose a price in its ProtectionOutcome; the durable Fill is
        # the economic source of truth.  It must be derived from Process B's fresh executable bid.
        assert after_first["fill_prices"][outcome["order_id"]] == pytest.approx(
            process_b["recovery_bbo"]["bid"] * (1 - 5 / 10_000)
        )
    elif scenario == "safe_mode":
        assert first["reconciliation"]["ok"] is True
        assert first["final_system_state"] == SystemState.SAFE_MODE
        assert after_first["control"]["system_state"] == SystemState.SAFE_MODE
        assert after_first["open_buys"] == 0
        assert after_first["fills"] == before["fills"]
        assert after_first["reserved_cash"] == 0
    elif scenario == "paused":
        # Current detector semantics see the transient RECOVERING state paired with durable
        # PAUSED operator intent as inconsistent, and therefore fail closed to SAFE_MODE.  The
        # N01-C contract here is durable operator intent: restart must never erase PAUSED into
        # RUNNING, not a new policy that silently bypasses the existing detector.
        assert first["reconciliation"]["ok"] is False
        assert first["final_system_state"] == SystemState.SAFE_MODE
        assert after_first["control"]["operator_state"] == OperatorState.PAUSED
        assert after_first["control"]["system_state"] == SystemState.SAFE_MODE
        assert _economic(before) == _economic(after_first) == _economic(after_second)
    else:
        assert first["reconciliation"]["ok"] is True
        assert first["final_system_state"] == SystemState.DATA_DEGRADED
        assert first["final_system_state"] != SystemState.RUNNING
        assert after_first["fills"] == before["fills"] == after_second["fills"]
        assert any(item["type"] == IncidentType.CORE_DATA_STALE for item in after_first["incidents"])

    # Same recovered durable state is economically idempotent. Audit timestamps may legitimately differ.
    assert _economic(after_second) == _economic(after_first)


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--child" or sys.argv[2] not in {"a", "b"}:
        raise SystemExit("usage: test_n01_restart_recovery.py --child <a|b> <database_url> <scenario>")
    _child_main(sys.argv[2], sys.argv[3], sys.argv[4])
