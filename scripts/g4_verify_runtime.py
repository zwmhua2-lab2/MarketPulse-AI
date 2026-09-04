"""G4 real-runtime smoke.

Two independent, paper-only verifications:

  protect         Real OKX BTC-USDT BBO drives a paper stop-loss protective exit.
  setup/recover   Two-process restart: create paper state, then a fresh process rebuilds
                  it from PostgreSQL only.

Never touches live trading. Run with: py -3.14 scripts/g4_verify_runtime.py <subcommand>
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    ExecutionIntentRecord,
    FillRecord,
    LedgerEntryRecord,
    OutboxRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    RuntimeControlRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    ExecutionIntent,
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
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.recovery import RecoveryManager
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.runtime import HealthRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

RM = RunMode.LIVE_PAPER
SESSIONS = async_sessionmaker(
    create_async_engine(Settings().database_url, poolclass=NullPool), expire_on_commit=False
)
_BBO: dict[str, BestBidAsk] = {}


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


async def _bbo(instrument: str) -> BestBidAsk:
    return _BBO[instrument]


async def fetch_real_bbo(instrument: str = "BTC-USDT") -> BestBidAsk:
    provider = OKXLiveProvider()
    tickers = await provider.spot_tickers()
    for ticker in tickers:
        if ticker.get("instId") == instrument:
            return BestBidAsk(
                instrument_id=instrument,
                bid=float(ticker["bidPx"]),
                ask=float(ticker["askPx"]),
                received_at=datetime.now(UTC),
            )
    raise RuntimeError(f"instrument not found: {instrument}")


def make_harness() -> SimpleNamespace:
    health = HealthRegistry()
    for name in ("DATABASE", "EXECUTION", "CORE_MARKET_DATA", "AI_AUXILIARY"):
        health.set(name, "HEALTHY")
    clock = _SystemClock()
    state_service = SystemStateService(SESSIONS, clock=clock)
    incidents = IncidentManager(SESSIONS, clock=clock)

    async def state_version_for(_: str) -> int:
        return 7

    execution = PaperExecutionService(SESSIONS, _bbo, state_version_for, initial_balance=10_000.0)
    risk_gate = SystemRiskGate(SESSIONS, state_service, incidents, health, clock=clock)
    execution.risk_gate = risk_gate
    protection = PositionProtectionService(SESSIONS, execution, incidents, health, clock=clock)

    async def _reconcile(run_mode: RunMode):
        return await reconcile(run_mode, sessions=SESSIONS, execution=execution, now=clock.now())

    recovery = RecoveryManager(
        SESSIONS,
        state_service,
        incidents,
        health,
        protection,
        execution,
        _reconcile,
        clock=clock,
    )
    return SimpleNamespace(
        health=health,
        clock=clock,
        state_service=state_service,
        incidents=incidents,
        execution=execution,
        risk_gate=risk_gate,
        protection=protection,
        recovery=recovery,
        reconcile=_reconcile,
    )


async def _clean() -> None:
    async with SESSIONS() as session, session.begin():
        order_ids = list(
            (
                await session.scalars(
                    select(PaperOrderRecord.order_id).where(PaperOrderRecord.run_mode == RM)
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
                    LedgerEntryRecord.__table__.delete().where(
                        LedgerEntryRecord.fill_id.in_(fill_ids)
                    )
                )
            await session.execute(
                FillRecord.__table__.delete().where(FillRecord.order_id.in_(order_ids))
            )
            await session.execute(
                PaperOrderRecord.__table__.delete().where(
                    PaperOrderRecord.order_id.in_(order_ids)
                )
            )
        for table in (PositionRecord, TradeRecord, AccountRecord, TradePlanRecord):
            await session.execute(table.__table__.delete().where(table.run_mode == RM))
        await session.execute(
            ExecutionIntentRecord.__table__.delete().where(
                ExecutionIntentRecord.run_mode == RM
            )
        )
        await session.execute(OutboxRecord.__table__.delete())
        await session.execute(PositionEventRecord.__table__.delete())
        await session.execute(RuntimeControlRecord.__table__.delete().where(
            RuntimeControlRecord.run_mode == RM
        ))


async def boot(h: SimpleNamespace) -> None:
    await _clean()
    await h.state_service.ensure(RM)
    await h.state_service.transition(RM, system_state="RUNNING", operator_state="NORMAL", reason="smoke_boot")
    await h.execution.bootstrap_account(RM)


async def open_paper_position(h: SimpleNamespace, bbo: BestBidAsk, *, stop: float, tp: float) -> TradePlan:
    plan = TradePlan(
        plan_id=stable_id("plan", "smoke", RM, "pos"),
        snapshot_id="smoke-snap",
        decision_id="smoke-decision",
        instrument_id=bbo.instrument_id,
        symbol=bbo.instrument_id,
        run_mode=RM,
        state_version=7,
        plan_version=1,
        status=PlanStatus.ACTIVE,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        entry_zone=PriceZone(lower=bbo.ask * 0.9, upper=bbo.ask * 1.1),
        stop_loss=stop,
        take_profit=tp,
        intended_notional=100.0,
    )
    await persist_trade_plan(SESSIONS, plan)
    intent = ExecutionIntent(
        intent_id=stable_id("intent", "smoke", RM, "pos"),
        plan_id=plan.plan_id,
        instrument_id=plan.instrument_id,
        run_mode=RM,
        state_version=7,
        created_at=datetime.now(UTC),
    )
    result = await h.execution.execute(intent, plan, datetime.now(UTC))
    assert result.status is IntentStatus.EXECUTED, result.reason
    return plan


async def cmd_protect() -> None:
    h = make_harness()
    await boot(h)
    bbo = await fetch_real_bbo("BTC-USDT")
    _BBO[bbo.instrument_id] = bbo
    # Stop is set just above the live bid so the protective exit is guaranteed to trigger,
    # and the fill must use the live bid (never the fabricated stop price).
    plan = await open_paper_position(h, bbo, stop=bbo.bid * 1.0001, tp=bbo.bid * 2.0)
    outcome = await h.protection.evaluate(RM, bbo.instrument_id, bbo)
    async with SESSIONS() as session:
        position = await session.scalar(
            select(PositionRecord).where(
                PositionRecord.run_mode == RM, PositionRecord.instrument_id == bbo.instrument_id
            )
        )
        trade = await session.scalar(select(TradeRecord).where(TradeRecord.run_mode == RM))
        sells = list(
            (
                await session.scalars(
                    select(PaperOrderRecord).where(
                        PaperOrderRecord.run_mode == RM,
                        PaperOrderRecord.side == OrderSide.SELL,
                    )
                )
            ).all()
        )
    sell_fills = []
    async with SESSIONS() as session:
        for order in sells:
            fill = await session.scalar(
                select(FillRecord).where(FillRecord.order_id == order.order_id)
            )
            if fill is not None:
                sell_fills.append(fill)
    print("=== REAL OKX PAPER PROTECTION SMOKE ===")
    print(f"live_bid={bbo.bid} live_ask={bbo.ask} stop={plan.stop_loss}")
    print(f"triggered={outcome.triggered} exit_reason={outcome.exit_reason}")
    print(f"position_after={position.quantity} trade_exit_reason={trade.exit_reason}")
    print(f"sell_fill_count={len(sell_fills)}")
    if sell_fills:
        print(f"fill_price={sell_fills[0].price} (must be < live_bid, not == stop)")
    print("live_order_placed=False (paper execution only)")
    assert outcome.triggered and outcome.exit_reason and outcome.exit_reason.value == "STOP_LOSS"
    assert position.quantity == 0 and trade.exit_reason == "STOP_LOSS"
    assert len(sell_fills) == 1 and sell_fills[0].price < bbo.bid


async def cmd_setup() -> None:
    h = make_harness()
    await boot(h)
    bbo = await fetch_real_bbo("BTC-USDT")
    _BBO[bbo.instrument_id] = bbo
    await open_paper_position(h, bbo, stop=bbo.bid * 0.98, tp=bbo.bid * 1.02)
    print(f"setup_done instrument={bbo.instrument_id} bid={bbo.bid}")


async def cmd_recover() -> None:
    h = make_harness()  # brand-new in-memory services

    async def real_bbo_for(instrument: str) -> BestBidAsk:
        return await fetch_real_bbo(instrument)

    report = await h.recovery.recover(RM, bbo_for=real_bbo_for)
    print("=== TWO-PROCESS RESTART RECOVERY SMOKE ===")
    print(f"ok={report.ok} final_state={report.final_system_state}")
    print(f"active_symbols={report.active_symbols}")
    print(f"reconciliation_ok={report.reconciliation.ok}")
    print(f"execution_gap={report.execution_gap}")
    print(
        "protection="
        + str(
            [
                (p.instrument_id, p.triggered, p.exit_reason.value if p.exit_reason else None)
                for p in report.protection
            ]
        )
    )
    assert report.ok and report.active_symbols == ["BTC-USDT"]
    assert report.reconciliation.ok


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["protect", "setup", "recover"])
    args = parser.parse_args()
    if args.cmd == "protect":
        await cmd_protect()
    elif args.cmd == "setup":
        await cmd_setup()
    else:
        await cmd_recover()


if __name__ == "__main__":
    asyncio.run(main())
