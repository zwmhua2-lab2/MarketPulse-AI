"""N01-G4-INV-01 — Protection vs concurrent limit-fill race: deterministic diagnostics.

READ-ONLY with respect to production code.  This script only *uses* the existing
test seams that already exist in the repository:

  PositionProtectionService.after_risk_reducing_orders_lock
  PositionProtectionService._lock_risk_increasing_orders  (instance-level wrap)
  PaperExecutionService.before_order_lock

and opens *separate* observer connections to capture PostgreSQL lock evidence
(pg_stat_activity / pg_locks / lock_timeout contention probes).

It never mutates backend/src.  Run with:

    py -3.14 scripts/n01_g4_inv_race_diagnostic.py

Output is line-oriented with stable prefixes (D1|, D2|, ...) so raw logs can be
pasted into the investigation dev_log.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    FillRecord,
    IncidentRecord,
    LedgerEntryRecord,
    OutboxRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    RuntimeControlRecord,
    SymbolControlRecord,
    SymbolStateStore,
    TradePlanRecord,
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
    OperatorState,
    SystemState,
)
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.runtime import HealthRegistry
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
DB_URL = Settings().database_url
ENGINE = create_async_engine(DB_URL, poolclass=NullPool)
SESSIONS = async_sessionmaker(ENGINE, expire_on_commit=False)
OBS = create_async_engine(DB_URL, poolclass=NullPool)


def emit(tag: str, payload: object) -> None:
    print(f"{tag}|{json.dumps(payload, default=str)}", flush=True)


class FixedClock:
    def __init__(self, current: datetime = NOW) -> None:
        self._current = current.astimezone(UTC)

    def now(self) -> datetime:
        return self._current


@dataclass
class H:
    clock: FixedClock = field(default_factory=FixedClock)
    quotes: dict[str, tuple[float, float]] = field(default_factory=dict)
    state_version: int = 7

    def __post_init__(self) -> None:
        self.health = HealthRegistry()
        for comp in (
            HealthComponent.DATABASE,
            HealthComponent.EXECUTION,
            HealthComponent.CORE_MARKET_DATA,
            HealthComponent.AI_AUXILIARY,
        ):
            self.health.set(comp.value, HealthStatus.HEALTHY.value)
        self.state_service = SystemStateService(SESSIONS, clock=self.clock)
        self.incidents = IncidentManager(SESSIONS, clock=self.clock)

        async def bbo_for(instrument: str) -> BestBidAsk:
            bid, ask = self.quotes[instrument]
            return BestBidAsk(
                instrument_id=instrument, bid=bid, ask=ask, received_at=self.clock.now()
            )

        async def state_version_for(instrument: str) -> int:
            return self.state_version

        self.bbo_for = bbo_for
        self.execution = PaperExecutionService(
            SESSIONS, bbo_for, state_version_for, initial_balance=1000.0, clock=self.clock
        )
        self.risk_gate = SystemRiskGate(
            SESSIONS, self.state_service, self.incidents, self.health, clock=self.clock
        )
        self.execution.risk_gate = self.risk_gate
        self.protection = PositionProtectionService(
            SESSIONS, self.execution, self.incidents, self.health, clock=self.clock
        )

    async def boot(self) -> None:
        await self.clean()
        await self.state_service.ensure(RunMode.REPLAY)
        await self.state_service.transition(
            RunMode.REPLAY,
            operator_state=OperatorState.NORMAL,
            system_state=SystemState.RUNNING,
            reason="harness_boot",
        )
        await self.execution.bootstrap_account(RunMode.REPLAY)

    async def clean(self) -> None:
        async with SESSIONS() as session, session.begin():
            order_ids = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord.order_id).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY
                        )
                    )
                ).all()
            )
            if order_ids:
                fill_ids = list(
                    (
                        await session.scalars(
                            select(FillRecord.fill_id).where(FillRecord.order_id.in_(order_ids))
                        )
                    ).all()
                )
                if fill_ids:
                    await session.execute(
                        delete(LedgerEntryRecord).where(LedgerEntryRecord.fill_id.in_(fill_ids))
                    )
                await session.execute(delete(FillRecord).where(FillRecord.order_id.in_(order_ids)))
                await session.execute(
                    delete(PaperOrderRecord).where(PaperOrderRecord.order_id.in_(order_ids))
                )
            for table in (
                PositionEventRecord,
                IncidentRecord,
                SymbolControlRecord,
                SymbolStateStore,
                RuntimeControlRecord,
            ):
                await session.execute(delete(table))
            await session.execute(delete(OutboxRecord))
            await session.execute(
                delete(PositionRecord).where(PositionRecord.run_mode == RunMode.REPLAY)
            )
            await session.execute(delete(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY))
            await session.execute(
                delete(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            plan_ids = list(
                (
                    await session.scalars(
                        select(TradePlanRecord.plan_id).where(
                            TradePlanRecord.run_mode == RunMode.REPLAY
                        )
                    )
                ).all()
            )
            if plan_ids:
                await session.execute(
                    delete(TradePlanRecord).where(TradePlanRecord.plan_id.in_(plan_ids))
                )
            await session.execute(
                delete(DecisionSnapshotRecord).where(
                    DecisionSnapshotRecord.run_mode == RunMode.REPLAY
                )
            )
            await session.execute(
                delete(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
            )


def make_plan(
    instrument: str,
    *,
    notional: float = 50.0,
    stop: float = 80.0,
    tp: float = 140.0,
    entry_zone: PriceZone | None = None,
    version: int = 7,
    order_type: OrderType = OrderType.MARKET,
    side: OrderSide = OrderSide.BUY,
) -> TradePlan:
    return TradePlan(
        plan_id=stable_id("plan", uuid4().hex),
        snapshot_id="snap",
        decision_id="decision",
        instrument_id=instrument,
        symbol=instrument,
        run_mode=RunMode.REPLAY,
        state_version=version,
        plan_version=1,
        status=PlanStatus.ACTIVE,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        side=side,
        order_type=order_type,
        entry_zone=entry_zone or PriceZone(lower=90, upper=120),
        stop_loss=stop,
        take_profit=tp,
        intended_notional=notional,
    )


def intent_for(plan: TradePlan, version: int = 7) -> ExecutionIntent:
    return ExecutionIntent(
        intent_id=stable_id("intent", uuid4().hex),
        plan_id=plan.plan_id,
        instrument_id=plan.instrument_id,
        run_mode=RunMode.REPLAY,
        state_version=version,
        created_at=NOW,
    )


async def open_position(h: H, instrument: str = "SOL-USDT", **kw) -> None:
    h.quotes[instrument] = (kw.get("bid", 99.0), kw.get("ask", 100.0))
    plan = make_plan(
        instrument,
        notional=kw.get("notional", 50.0),
        stop=kw.get("stop", 80.0),
        tp=kw.get("tp", 140.0),
        version=kw.get("version", 7),
    )
    await persist_trade_plan(SESSIONS, plan)
    result = await h.execution.execute(intent_for(plan, 7), plan, NOW)
    assert result.status is IntentStatus.EXECUTED, result.reason


async def open_limit_buy(h: H, instrument: str = "SOL-USDT", **kw) -> TradePlan:
    h.quotes.setdefault(instrument, (99.0, 100.0))
    plan = make_plan(
        instrument,
        notional=kw.get("notional", 20.0),
        order_type=OrderType.LIMIT,
        entry_zone=PriceZone(lower=kw.get("limit", 95.0), upper=120),
        version=kw.get("version", 7),
    )
    await persist_trade_plan(SESSIONS, plan)
    result = await h.execution.execute(intent_for(plan, 7), plan, NOW)
    assert result.status is IntentStatus.EXECUTED, result.reason
    return plan


# ---------------------------------------------------------------- observers

async def obs_client_backends() -> list[dict]:
    async with OBS.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select pid, application_name, state, backend_type, "
                    "coalesce(wait_event_type,'') as wait_event_type, "
                    "coalesce(wait_event,'') as wait_event, "
                    "coalesce(left(query,80),'') as query "
                    "from pg_stat_activity "
                    "where datname = current_database() and backend_type = 'client backend' "
                    "order by pid"
                )
            )
        ).mappings().all()
        return [dict(r) for r in rows]


async def obs_order_row_locks() -> list[dict]:
    async with OBS.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select l.locktype, l.mode, l.granted, "
                    "coalesce(l.transactionid::text,'') as xid, "
                    "l.pid, coalesce(a.state,'') as state, "
                    "coalesce(a.wait_event_type,'') as wait_event_type, "
                    "coalesce(a.wait_event,'') as wait_event "
                    "from pg_locks l left join pg_stat_activity a on a.pid = l.pid "
                    "where l.pid <> pg_backend_pid() "
                    "and (l.relation = 'paper_orders'::regclass or l.locktype = 'transactionid') "
                    "order by l.pid, l.locktype"
                )
            )
        ).mappings().all()
        return [dict(r) for r in rows]


async def obs_for_update_probe(order_id: str, timeout_ms: int = 400) -> str:
    """Try to take the row lock from an independent connection; report the outcome."""
    async with OBS.connect() as conn:
        try:
            await conn.execute(text(f"set local lock_timeout = '{timeout_ms}ms'"))
            row = (
                await conn.execute(
                    text("select status from paper_orders where order_id = :oid for update"),
                    {"oid": order_id},
                )
            ).mappings().first()
            await conn.rollback()
            return f"ACQUIRED status={row['status'] if row else None}"
        except Exception as exc:  # noqa: BLE001
            with contextlib.suppress(Exception):
                await conn.rollback()
            return f"BLOCKED {type(exc).__name__}: {str(exc).splitlines()[0]}"


async def obs_order_status(order_id: str) -> tuple[str, float]:
    async with SESSIONS() as session:
        row = (
            await session.execute(
                text("select status, reserved_cash from paper_orders where order_id = :oid"),
                {"oid": order_id},
            )
        ).mappings().first()
        return (row["status"], float(row["reserved_cash"])) if row else ("<missing>", -1.0)


async def fact_counts() -> dict:
    async with SESSIONS() as session:
        out: dict[str, object] = {}
        for label, table in (
            ("orders", "paper_orders"),
            ("positions", "positions"),
            ("trades", "trades"),
            ("accounts", "accounts"),
            ("plans", "trade_plans"),
        ):
            rows = (
                await session.execute(
                    text(f"select run_mode, count(*) as n from {table} group by run_mode")
                )
            ).mappings().all()
            out[label] = {r["run_mode"]: r["n"] for r in rows}
        for label, sql in (
            (
                "fills",
                (
                    "select o.run_mode, count(*) as n from fills f "
                    "join paper_orders o on o.order_id = f.order_id group by o.run_mode"
                ),
            ),
            (
                "ledger",
                (
                    "select o.run_mode, count(*) as n from ledger_entries le "
                    "join fills f on f.fill_id = le.fill_id "
                    "join paper_orders o on o.order_id = f.order_id group by o.run_mode"
                ),
            ),
        ):
            rows = (await session.execute(text(sql))).mappings().all()
            out[label] = {r["run_mode"]: r["n"] for r in rows}
        for label, table in (
            ("runtime_controls", "runtime_controls"),
            ("symbol_controls", "symbol_controls"),
            ("incidents", "incidents"),
            ("outbox", "outbox_records"),
            ("pos_events", "position_events"),
        ):
            out[label] = (
                await session.execute(text(f"select count(*) from {table}"))
            ).scalar()
        return out


async def snapshot(h: H, buy_order_id: str, tag: str) -> dict:
    async with SESSIONS() as session:
        order = (
            await session.execute(
                text(
                    "select order_id, plan_id, status, reserved_cash, quantity, "
                    "limit_price, side, order_type from paper_orders where order_id = :oid"
                ),
                {"oid": buy_order_id},
            )
        ).mappings().first()
        position = (
            await session.execute(
                text(
                    "select position_id, quantity, trade_id from positions "
                    "where run_mode = 'REPLAY' and instrument_id = 'SOL-USDT'"
                )
            )
        ).mappings().first()
        fills = (
            await session.execute(
                text(
                    "select f.fill_id, f.order_id, f.price, f.quantity from fills f "
                    "join paper_orders o on o.order_id = f.order_id "
                    "where o.run_mode = 'REPLAY' and o.instrument_id = 'SOL-USDT' "
                    "order by f.created_at"
                )
            )
        ).mappings().all()
        trades = (
            await session.execute(
                text(
                    "select trade_id, status, exit_reason from trades "
                    "where run_mode = 'REPLAY' and instrument_id = 'SOL-USDT'"
                )
            )
        ).mappings().all()
    emit(tag, {
        "order": dict(order) if order else None,
        "position": dict(position) if position else None,
        "fills": [dict(r) for r in fills],
        "trades": [dict(r) for r in trades],
    })
    return {}


async def setup(h: H) -> str:
    await h.boot()
    await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
    pending = await open_limit_buy(h, notional=20, limit=95)
    h.quotes["SOL-USDT"] = (79.0, 80.0)
    async with SESSIONS() as session:
        buy = await session.scalar(
            select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending.plan_id)
        )
    return buy.order_id


# ---------------------------------------------------------------- diagnostics

async def d1_witness_validity() -> None:
    emit("D1", {"phase": "start"})
    h = H()
    buy_id = await setup(h)
    locked: dict = {}
    orig = h.protection._lock_risk_increasing_orders

    async def wrapper(session, run_mode, instrument_id):
        rows = await orig(session, run_mode, instrument_id)
        locked["rows"] = [
            {"order_id": r.order_id, "status": r.status, "side": r.side,
             "reserved_cash": r.reserved_cash}
            for r in rows
        ]
        locked["backend_pid"] = (
            await session.execute(text("select pg_backend_pid()"))
        ).scalar()
        return rows

    h.protection._lock_risk_increasing_orders = wrapper
    held = asyncio.Event()
    release = asyncio.Event()

    async def hook(_run_mode, instrument_id):
        if instrument_id == "SOL-USDT":
            # evidence while the protection transaction is (supposedly) holding the row lock
            locked["locks_while_held"] = await obs_order_row_locks()
            locked["probe_while_held"] = await obs_for_update_probe(buy_id)
            held.set()
            await release.wait()

    h.protection.after_risk_reducing_orders_lock = hook
    close = asyncio.create_task(
        h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW)
    )
    await held.wait()
    emit("D1", {"locked_rows": locked.get("rows"), "backend_pid": locked.get("backend_pid")})
    emit("D1", {"locks_while_held": locked.get("locks_while_held")})
    emit("D1", {"probe_while_held": locked.get("probe_while_held")})
    release.set()
    await asyncio.wait_for(close, timeout=5)
    emit("D1", {"final_status": await obs_order_status(buy_id)})


async def d2_post_cancel_visibility(repeats: int = 1) -> None:
    for i in range(repeats):
        emit("D2", {"phase": "start", "iteration": i})
        h = H()
        buy_id = await setup(h)
        reached = asyncio.Event()
        release_fill = asyncio.Event()

        async def before_order_lock(reached=reached, release_fill=release_fill):
            reached.set()
            await release_fill.wait()

        h.execution.before_order_lock = before_order_lock
        close = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        )
        fill = asyncio.create_task(
            h.execution.process_open_orders(
                RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW
            )
        )
        await reached.wait()
        emit("D2", {"fill_at_before_order_lock": True,
                    "locks_before_release": await obs_order_row_locks()})
        protection = await asyncio.wait_for(close, timeout=5)
        # wait until protection's cancellation is committed and visible
        for _ in range(200):
            status, _rc = await obs_order_status(buy_id)
            if status == "CANCELLED":
                break
            await asyncio.sleep(0.01)
        emit("D2", {"committed_status_before_fill_release": status,
                    "protection_triggered": protection.triggered,
                    "cancelled_order_ids": getattr(protection, "cancelled_order_ids", None)})
        await snapshot(h, buy_id, "D2.premature")
        release_fill.set()
        fills = await asyncio.wait_for(fill, timeout=5)
        emit("D2", {"fill_returned": [str(f) for f in fills],
                    "final_status": await obs_order_status(buy_id)})
        await snapshot(h, buy_id, "D2.final")
        report = await reconcile(RunMode.REPLAY, sessions=SESSIONS, execution=h.execution,
                                 now=h.clock.now())
        emit("D2", {"reconcile_ok": report.ok})


async def d3_base_scenario(repeats: int = 50, verbose: bool = False) -> None:
    """Exact scenario of the failing test, repeated; invariant = no reopen, CANCELLED."""
    violations = 0
    for i in range(repeats):
        h = H()
        buy_id = await setup(h)
        orders_locked = asyncio.Event()
        release = asyncio.Event()
        locked_rows: dict = {}
        orig = h.protection._lock_risk_increasing_orders

        async def wrapper(session, run_mode, instrument_id, _orig=orig, _locked=locked_rows):
            rows = await _orig(session, run_mode, instrument_id)
            _locked["n"] = len(rows)
            return rows

        h.protection._lock_risk_increasing_orders = wrapper

        async def hook(_run_mode, instrument_id, _ol=orders_locked, _rel=release):
            if instrument_id == "SOL-USDT":
                _ol.set()
                await _rel.wait()

        h.protection.after_risk_reducing_orders_lock = hook
        close = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        )
        await orders_locked.wait()
        fill = asyncio.create_task(
            h.execution.process_open_orders(
                RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW
            )
        )
        await asyncio.sleep(0)
        fill_done_after_one_yield = fill.done()
        release.set()
        protection, fills = await asyncio.wait_for(asyncio.gather(close, fill), timeout=5)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == buy_id)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        bad = (
            order.status != OrderStatus.CANCELLED
            or (position is not None and position.quantity != 0)
            or fills != []
            or not protection.triggered
        )
        if bad or verbose:
            violations += 1 if bad else 0
            emit("D3", {
                "iteration": i,
                "locked_rows": locked_rows.get("n"),
                "fill_done_after_one_yield": fill_done_after_one_yield,
                "fill_returned_count": len(fills),
                "order_status": order.status,
                "order_reserved_cash": order.reserved_cash,
                "position_quantity": position.quantity if position else None,
                "protection_triggered": protection.triggered,
                "INVARIANT_VIOLATION": bad,
            })
            await snapshot(h, buy_id, "D3.violation")
    emit("D3", {"repeats": repeats, "violations": violations})


async def d5_isolation_audit() -> None:
    emit("D5", {"client_backends_before": await obs_client_backends()})
    emit("D5", {"facts_before": await fact_counts()})
    h = H()
    await h.boot()
    emit("D5", {"facts_after_boot_before_scenario": await fact_counts()})
    await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
    _ = await open_limit_buy(h, notional=20, limit=95)
    emit("D5", {"facts_scenario_setup": await fact_counts()})
    emit("D5", {"client_backends_after": await obs_client_backends()})


async def deep_failure_snapshot(h: H, buy_id: str, plan_id: str, protection, fills,
                                tag: str) -> None:
    """§9 required failure snapshot: pending order / position / protection / fill task /
    economic facts / reconciliation."""
    async with SESSIONS() as session:
        orders_by_plan = (
            await session.execute(
                text(
                    "select ctid::text as ctid, order_id, plan_id, side, order_type, status, "
                    "reserved_cash, quantity, limit_price from paper_orders "
                    "where plan_id = :p order by ctid"
                ),
                {"p": plan_id},
            )
        ).mappings().all()
        pending = (
            await session.execute(
                text(
                    "select order_id, plan_id, side, order_type, status, reserved_cash, quantity "
                    "from paper_orders where order_id = :o"
                ),
                {"o": buy_id},
            )
        ).mappings().first()
        positions = (
            await session.execute(
                text(
                    "select position_id, quantity, trade_id, average_cost, realized_pnl "
                    "from positions where run_mode='REPLAY' and instrument_id='SOL-USDT'"
                )
            )
        ).mappings().all()
        all_fills = (
            await session.execute(
                text(
                    "select f.fill_id, f.order_id, o.side, o.status as order_status, f.price, "
                    "f.quantity, f.fee from fills f "
                    "join paper_orders o on o.order_id = f.order_id "
                    "where o.run_mode='REPLAY' and o.instrument_id='SOL-USDT' "
                    "order by f.created_at"
                )
            )
        ).mappings().all()
        trades = (
            await session.execute(
                text(
                    "select trade_id, status, exit_reason, closed_at from trades "
                    "where run_mode='REPLAY' and instrument_id='SOL-USDT'"
                )
            )
        ).mappings().all()
        ledger = (
            await session.execute(
                text(
                    "select le.entry_id, le.entry_type, le.cash_delta, le.fee from ledger_entries le "
                    "join fills f on f.fill_id = le.fill_id "
                    "join paper_orders o on o.order_id = f.order_id "
                    "where o.run_mode='REPLAY' and o.instrument_id='SOL-USDT'"
                )
            )
        ).mappings().all()
        events = (
            await session.execute(
                text(
                    "select event_type, order_id, fill_id, payload from position_events "
                    "where run_mode='REPLAY' and instrument_id='SOL-USDT' order by created_at"
                )
            )
        ).mappings().all()
    report = await reconcile(
        RunMode.REPLAY, sessions=SESSIONS, execution=h.execution, now=h.clock.now()
    )
    emit(tag, {
        "orders_sharing_plan_id_by_ctid": [dict(r) for r in orders_by_plan],
        "pending_order": dict(pending) if pending else None,
        "positions": [dict(r) for r in positions],
        "protection": {
            "triggered": protection.triggered,
            "cancelled_order_ids": getattr(protection, "cancelled_order_ids", None),
            "exit_order_id": getattr(protection, "order_id", None),
            "sell_fill_id": getattr(protection, "fill_id", None),
            "reason": getattr(protection, "reason", None),
        },
        "fill_task_returned": [str(f) for f in fills],
        "buy_fills": [dict(r) for r in all_fills if r["side"] == "BUY"],
        "sell_fills": [dict(r) for r in all_fills if r["side"] == "SELL"],
        "ledger": [dict(r) for r in ledger],
        "trades": [dict(r) for r in trades],
        "position_events": [dict(r) for r in events],
        "reconciliation": {"ok": report.ok,
                           "diagnostics": getattr(report, "diagnostics", None)},
    })


async def d6_assertion_query_probe(repeats: int = 5, force_order: bool = False) -> None:
    """Reproduce the *test assertion* failure mode deterministically, without touching
    production semantics.

    The failing test reads the pending BUY with
        select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending_plan.plan_id)
    and `Session.scalar()` (SQLAlchemy 2.0.52) does NOT raise for a second row; it returns
    the first row in whatever order PostgreSQL produces.  After the protective exit, TWO
    orders share that plan_id (the cancelled LIMIT BUY and the settled protective SELL), so
    the read is order-dependent.
    """
    for i in range(repeats):
        h = H()
        buy_id = await setup(h)
        orders_locked = asyncio.Event()
        release = asyncio.Event()

        async def hook(_run_mode, instrument_id, _ol=orders_locked, _rel=release):
            if instrument_id == "SOL-USDT":
                _ol.set()
                await _rel.wait()

        h.protection.after_risk_reducing_orders_lock = hook
        close = asyncio.create_task(
            h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW)
        )
        await orders_locked.wait()
        fill = asyncio.create_task(
            h.execution.process_open_orders(RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW)
        )
        await asyncio.sleep(0)
        release.set()
        protection, fills = await asyncio.wait_for(asyncio.gather(close, fill), timeout=5)

        if force_order:
            # Diagnostic-only, logically neutral: force a NEW tuple version of the cancelled
            # BUY to the end of the heap so that a sequential scan yields the settled SELL
            # first.  Statuses are unchanged; the next Harness.boot()->clean() removes it.
            async with SESSIONS() as session, session.begin():
                await session.execute(
                    text("update paper_orders set reserved_cash = reserved_cash where order_id = :o"),
                    {"o": buy_id},
                )

        async with SESSIONS() as session:
            phys = (
                await session.execute(
                    text(
                        "select ctid::text as ctid, order_id, side, status from paper_orders "
                        "where plan_id = (select plan_id from paper_orders where order_id = :o) "
                        "order by ctid"
                    ),
                    {"o": buy_id},
                )
            ).mappings().all()
            plan_id = (
                await session.execute(
                    text("select plan_id from paper_orders where order_id = :o"), {"o": buy_id}
                )
            ).scalar()
            stmt_plain = select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan_id)
            stmt_seellast = stmt_plain.order_by(PaperOrderRecord.side.desc())
            plain = await session.scalar(stmt_plain)
            seellast = await session.scalar(stmt_seellast)
            ambiguous_buy = await session.scalar(
                select(PaperOrderRecord).where(
                    PaperOrderRecord.order_id == buy_id
                )
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            buy_fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.BUY,
                        )
                    )
                ).all()
            )
        report = await reconcile(
            RunMode.REPLAY, sessions=SESSIONS, execution=h.execution, now=h.clock.now()
        )
        would_fail = plain.status != OrderStatus.CANCELLED
        if would_fail or force_order:
            await deep_failure_snapshot(h, buy_id, plan_id, protection, fills, "D6.snapshot")
        emit("D6", {
            "iteration": i,
            "forced_order": force_order,
            "rows_by_ctid": [dict(r) for r in phys],
            "plain_scalar_returns": {"order_id": plain.order_id, "side": plain.side,
                                     "status": plain.status},
            "order_by_side_desc_scalar_returns": {"order_id": seellast.order_id,
                                                  "side": seellast.side,
                                                  "status": seellast.status},
            "invariant_buy_order_status": ambiguous_buy.status,
            "invariant_position_quantity": position.quantity if position else None,
            "invariant_buy_fills_count": len(buy_fills),
            "invariant_protection_triggered": protection.triggered,
            "invariant_fill_task_result_count": len(fills),
            "invariant_reconcile_ok": report.ok,
            "TEST_1709_WOULD_FAIL": would_fail,
        })


async def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        if which in ("all", "d5"):
            await d5_isolation_audit()
        if which in ("all", "d1"):
            await d1_witness_validity()
        if which in ("all", "d2"):
            await d2_post_cancel_visibility(repeats=int(sys.argv[2]) if len(sys.argv) > 2 else 1)
        if which in ("all", "d3"):
            await d3_base_scenario(repeats=int(sys.argv[2]) if len(sys.argv) > 2 else 30)
        if which in ("all", "d6"):
            await d6_assertion_query_probe(
                repeats=int(sys.argv[2]) if len(sys.argv) > 2 else 5,
                force_order=(len(sys.argv) > 3 and sys.argv[3] == "force"),
            )
    except Exception:
        emit("FATAL", {"traceback": traceback.format_exc()})
        raise
    finally:
        await ENGINE.dispose()
        await OBS.dispose()


if __name__ == "__main__":
    asyncio.run(main())
