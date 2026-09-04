import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
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
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    DataQuality,
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
from marketpulse.g4.control import SystemControlService
from marketpulse.g4.incidents import IncidentManager
from marketpulse.g4.models import (
    ExitReason,
    HealthComponent,
    HealthStatus,
    IncidentType,
    OperatorState,
    PositionReevaluation,
    ReevaluationAction,
    SystemState,
)
from marketpulse.g4.planning import PlanManager, load_active_plan
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.provider import DeterministicFakePositionReviewProvider
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.recovery import RecoveryManager
from marketpulse.g4.reevaluation import PositionReevaluationService
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.runtime import HealthRegistry
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
SESSIONS = async_sessionmaker(
    create_async_engine(Settings().database_url, poolclass=NullPool), expire_on_commit=False
)


class FixedClock:
    def __init__(self, current: datetime = NOW) -> None:
        self._current = current.astimezone(UTC)

    def now(self) -> datetime:
        return self._current

    def advance(self, seconds: float) -> None:
        self._current += timedelta(seconds=seconds)


@dataclass
class Harness:
    clock: FixedClock = field(default_factory=FixedClock)
    quotes: dict[str, tuple[float, float]] = field(default_factory=dict)
    state_version: int = 7

    def __post_init__(self) -> None:
        self.health = HealthRegistry()
        self.health.set(HealthComponent.DATABASE.value, HealthStatus.HEALTHY.value)
        self.health.set(HealthComponent.EXECUTION.value, HealthStatus.HEALTHY.value)
        self.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.HEALTHY.value)
        self.health.set(HealthComponent.AI_AUXILIARY.value, HealthStatus.HEALTHY.value)
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
            SESSIONS, bbo_for, state_version_for, initial_balance=1000.0
        )
        self.risk_gate = SystemRiskGate(
            SESSIONS, self.state_service, self.incidents, self.health, clock=self.clock
        )
        self.execution.risk_gate = self.risk_gate
        self.protection = PositionProtectionService(
            SESSIONS, self.execution, self.incidents, self.health, clock=self.clock
        )
        self.plans = PlanManager(SESSIONS, self.execution, clock=self.clock)

        async def _reconcile(run_mode: RunMode):
            return await reconcile(
                run_mode, sessions=SESSIONS, execution=self.execution, now=self.clock.now()
            )

        self.reconcile = _reconcile
        self.control = SystemControlService(
            SESSIONS,
            self.state_service,
            self.incidents,
            self.health,
            self.risk_gate,
            self.protection,
            self.execution,
            _reconcile,
            clock=self.clock,
        )
        self.review_provider = DeterministicFakePositionReviewProvider(
            PositionReevaluation(action=ReevaluationAction.HOLD, reason="hold-default")
        )
        self.reevaluation = PositionReevaluationService(
            SESSIONS,
            self.review_provider,
            self.plans,
            self.risk_gate,
            self.protection,
            self.incidents,
            self.execution,
            self.health,
            clock=self.clock,
        )
        self.recovery = RecoveryManager(
            SESSIONS,
            self.state_service,
            self.incidents,
            self.health,
            self.protection,
            self.execution,
            _reconcile,
            clock=self.clock,
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
                RuntimeControlRecord,
            ):
                await session.execute(delete(table))
            await session.execute(delete(OutboxRecord))
            await session.execute(delete(PositionRecord).where(PositionRecord.run_mode == RunMode.REPLAY))
            await session.execute(delete(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY))
            await session.execute(delete(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY))
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


async def open_position(
    h: Harness,
    instrument: str = "SOL-USDT",
    *,
    notional: float = 50.0,
    bid: float = 99.0,
    ask: float = 100.0,
    stop: float = 80.0,
    tp: float = 140.0,
    version: int = 7,
) -> tuple[TradePlan, object]:
    h.quotes[instrument] = (bid, ask)
    plan = make_plan(instrument, notional=notional, stop=stop, tp=tp, version=version)
    await persist_trade_plan(SESSIONS, plan)
    result = await h.execution.execute(intent_for(plan, version), plan, NOW)
    assert result.status is IntentStatus.EXECUTED, result.reason
    return plan, result


async def open_limit_buy(
    h: Harness,
    instrument: str = "SOL-USDT",
    *,
    notional: float = 20.0,
    limit: float = 95.0,
    version: int = 7,
) -> TradePlan:
    h.quotes.setdefault(instrument, (99.0, 100.0))
    # For a LIMIT BUY the order limit price is plan.entry_zone.lower.
    plan = make_plan(
        instrument,
        notional=notional,
        order_type=OrderType.LIMIT,
        entry_zone=PriceZone(lower=limit, upper=120),
        version=version,
    )
    await persist_trade_plan(SESSIONS, plan)
    result = await h.execution.execute(intent_for(plan, version), plan, NOW)
    assert result.status is IntentStatus.EXECUTED, result.reason
    return plan


async def open_limit_sell(
    h: Harness,
    instrument: str = "SOL-USDT",
    *,
    notional: float = 10.0,
    limit: float = 120.0,
    version: int = 7,
) -> TradePlan:
    h.quotes.setdefault(instrument, (99.0, 100.0))
    # For a LIMIT SELL the order limit price is plan.entry_zone.upper.
    plan = make_plan(
        instrument,
        notional=notional,
        order_type=OrderType.LIMIT,
        side=OrderSide.SELL,
        entry_zone=PriceZone(lower=90, upper=limit),
        version=version,
    )
    await persist_trade_plan(SESSIONS, plan)
    result = await h.execution.execute(intent_for(plan, version), plan, NOW)
    assert result.status is IntentStatus.EXECUTED, result.reason
    return plan


# ==============================================================================
# A / B / C — Stop Loss, Take Profit, duplicate protection
# ==============================================================================


def test_stop_loss_and_take_profit_protective_exit():
    async def case(side: str):
        h = Harness()
        await h.boot()
        _, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # move the bid below stop / above tp
        if side == "sl":
            h.quotes["SOL-USDT"] = (79.0, 80.0)
        else:
            h.quotes["SOL-USDT"] = (141.0, 142.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            trade = await session.scalar(
                select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
            )
            sells = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            sell_fills = []
            for order in sells:
                fill = await session.scalar(
                    select(FillRecord).where(FillRecord.order_id == order.order_id)
                )
                if fill is not None:
                    sell_fills.append(fill)
        return outcome, position, trade, sell_fills

    for side, reason in (("sl", ExitReason.STOP_LOSS), ("tp", ExitReason.TAKE_PROFIT)):
        outcome, position, trade, sell_fills = asyncio.run(case(side))
        assert outcome.triggered and outcome.exit_reason is reason
        assert position.quantity == 0
        assert trade.status == "CLOSED" and trade.exit_reason == reason.value
        assert len(sell_fills) == 1


def test_duplicate_protection_is_idempotent():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        bbo = await h.bbo_for("SOL-USDT")
        first = await h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW)
        second = await h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW)
        async with SESSIONS() as session:
            sell_fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return first, second, sell_fills, position

    first, second, sell_fills, position = asyncio.run(case())
    assert first.triggered and not second.triggered
    assert len(sell_fills) == 1
    assert position.quantity == 0


def test_concurrent_duplicate_protection():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        bbo = await h.bbo_for("SOL-USDT")
        results = await asyncio.gather(
            h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW),
            h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW),
            h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW),
        )
        async with SESSIONS() as session:
            sell_fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return results, sell_fills, position

    results, sell_fills, position = asyncio.run(case())
    triggered = [r for r in results if r.triggered]
    assert len(triggered) == 1
    assert len(sell_fills) == 1
    assert position.quantity == 0


# ==============================================================================
# D — SL cancels pending add
# ==============================================================================


def test_stop_loss_cancels_pending_add():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        add_plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            add_order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            reserved_before = add_order.reserved_cash
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        async with SESSIONS() as session:
            add_order_after = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return outcome, add_order_after, account, position, reserved_before

    outcome, add_order_after, account, position, reserved_before = asyncio.run(case())
    assert outcome.triggered
    assert reserved_before > 0
    assert add_order_after.status == OrderStatus.CANCELLED
    assert account.reserved_cash == 0
    assert position.quantity == 0


# ==============================================================================
# E / F — Pause blocks buy, resume gate
# ==============================================================================


def test_pause_blocks_buy_and_limit_fill_but_allows_protection():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        add_plan = await open_limit_buy(h, notional=10, limit=95)
        paused = await h.control.pause(RunMode.REPLAY, "test_pause")
        # new BUY is rejected
        buy_plan = make_plan("SOL-USDT", notional=20)
        await persist_trade_plan(SESSIONS, buy_plan)
        buy_result = await h.execution.execute(intent_for(buy_plan), buy_plan, NOW)
        # an eligible limit buy must not fill while paused
        h.quotes["SOL-USDT"] = (89.0, 90.0)
        fills = await h.execution.process_open_orders(
            RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW
        )
        async with SESSIONS() as session:
            add_order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
        # protection still works while paused
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return paused, buy_result, add_order, fills, outcome

    paused, buy_result, add_order, fills, outcome = asyncio.run(case())
    assert paused.accepted
    assert buy_result.status is IntentStatus.REJECTED
    assert buy_result.reason == "RUNTIME_STATE_PAUSED"
    assert add_order.status == OrderStatus.OPEN
    assert all(result.reason == "RUNTIME_STATE_PAUSED" for result in fills)
    assert outcome.triggered  # SL closed the position even while paused


def test_resume_gate_passes_and_refuses_on_reconciliation_failure():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.pause(RunMode.REPLAY, "p")
        ok = await h.control.resume(RunMode.REPLAY)
        # break a ledger invariant, then pause and refuse resume
        async with SESSIONS() as session, session.begin():
            await session.execute(delete(LedgerEntryRecord))
        await h.control.pause(RunMode.REPLAY, "p2")
        refused = await h.control.resume(RunMode.REPLAY)
        return ok, refused

    ok, refused = asyncio.run(case())
    assert ok.accepted and ok.system_state is SystemState.RUNNING
    assert not refused.accepted
    assert refused.reason and refused.reason.startswith("RECONCILIATION_FAILED")


# ==============================================================================
# G / H — Emergency stop and recovery
# ==============================================================================


def test_emergency_stop_preserves_position_and_security():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_limit_buy(h, notional=20, limit=95)
        # an OPEN SELL (risk reducing) must survive emergency
        await open_limit_sell(h, notional=10, limit=120)
        result = await h.control.emergency_stop(RunMode.REPLAY, "test_emergency")
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            open_buys = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                    )
                ).all()
            )
            open_sells = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.SELL,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                    )
                ).all()
            )
        # new buy must be blocked
        buy_plan = make_plan("SOL-USDT", notional=20)
        await persist_trade_plan(SESSIONS, buy_plan)
        buy_result = await h.execution.execute(intent_for(buy_plan), buy_plan, NOW)
        return result, position, account, open_buys, open_sells, buy_result

    result, position, account, open_buys, open_sells, buy_result = asyncio.run(case())
    assert result.accepted and result.operator_state is OperatorState.EMERGENCY_STOP
    assert position.quantity > 0  # NOT auto-closed
    assert len(open_buys) == 0  # all risk-increasing BUY cancelled
    assert len(open_sells) == 1  # risk-reducing SELL preserved
    assert account.reserved_cash == 0
    assert buy_result.status is IntentStatus.REJECTED
    assert buy_result.reason == "RUNTIME_STATE_EMERGENCY_STOP"


def test_emergency_recovery_never_goes_straight_to_running():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.emergency_stop(RunMode.REPLAY, "e")
        direct = await h.control.resume(RunMode.REPLAY)
        recovered = await h.control.emergency_recovery(RunMode.REPLAY)
        resumed = await h.control.resume(RunMode.REPLAY)
        return direct, recovered, resumed

    direct, recovered, resumed = asyncio.run(case())
    assert not direct.accepted  # resume refused while emergency
    assert recovered.accepted
    assert recovered.system_state is SystemState.PAUSED  # never RUNNING directly
    assert resumed.accepted and resumed.system_state is SystemState.RUNNING


# ==============================================================================
# I — Symbol block
# ==============================================================================


def test_symbol_block_blocks_only_that_symbol():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, "SOL-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        blocked = await h.control.block_symbol(RunMode.REPLAY, "SOL-USDT", "test_block")
        # SOL ADD blocked
        sol_add = make_plan("SOL-USDT", notional=10)
        await persist_trade_plan(SESSIONS, sol_add)
        sol_result = await h.execution.execute(intent_for(sol_add), sol_add, NOW)
        # BTC normal
        h.quotes["BTC-USDT"] = (50000.0, 50100.0)
        btc_plan = make_plan(
            "BTC-USDT",
            notional=10,
            stop=40000,
            tp=60000,
            entry_zone=PriceZone(lower=49000, upper=51000),
        )
        await persist_trade_plan(SESSIONS, btc_plan)
        btc_result = await h.execution.execute(intent_for(btc_plan), btc_plan, NOW)
        # SOL protection/close still allowed
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return blocked, sol_result, btc_result, outcome

    blocked, sol_result, btc_result, outcome = asyncio.run(case())
    assert blocked.accepted
    assert sol_result.status is IntentStatus.REJECTED and sol_result.reason == "SYMBOL_BLOCKED"
    assert btc_result.status is IntentStatus.EXECUTED
    assert outcome.triggered


# ==============================================================================
# J — Manual close
# ==============================================================================


def test_manual_close_allowed_under_pause_and_emergency():
    async def case(state: str):
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        if state == "paused":
            await h.control.pause(RunMode.REPLAY, "p")
        else:
            await h.control.emergency_stop(RunMode.REPLAY, "e")
        h.quotes["SOL-USDT"] = (98.0, 99.0)
        outcome = await h.control.manual_close(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        async with SESSIONS() as session:
            trade = await session.scalar(
                select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return outcome, trade, position

    for state in ("paused", "emergency"):
        outcome, trade, position = asyncio.run(case(state))
        assert outcome.triggered and outcome.exit_reason is ExitReason.MANUAL_CLOSE
        assert trade.exit_reason == ExitReason.MANUAL_CLOSE.value
        assert position.quantity == 0


# ==============================================================================
# K — Stale market data
# ==============================================================================


def test_stale_market_data_fails_closed_then_recovers():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        stale = BestBidAsk(
            instrument_id="SOL-USDT",
            bid=79,
            ask=80,
            received_at=NOW - timedelta(seconds=60),
            data_quality=DataQuality.STALE,
        )
        outcome = await h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", stale, now=NOW)
        async with SESSIONS() as session:
            position_after_stale = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        # fresh data restores evaluation and the breached stop now fires
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        fresh = await h.bbo_for("SOL-USDT")
        recovered = await h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", fresh, now=NOW)
        return outcome, position_after_stale, recovered

    outcome, position_after_stale, recovered = asyncio.run(case())
    assert not outcome.triggered and outcome.reason == "CORE_MARKET_DATA_STALE"
    assert position_after_stale.quantity > 0  # nothing fabricated
    assert recovered.triggered and recovered.exit_reason is ExitReason.STOP_LOSS


# ==============================================================================
# L / M / N — Position re-evaluation (HOLD / ADD / REDUCE / CLOSE)
# ==============================================================================


def test_reevaluation_hold_changes_nothing():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        before = await h.reconcile(RunMode.REPLAY)
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        after = await h.reconcile(RunMode.REPLAY)
        return before, outcome, after

    before, outcome, after = asyncio.run(case())
    assert outcome.action is ReevaluationAction.HOLD and outcome.applied
    assert before.invariants == after.invariants


def test_reevaluation_add_respects_capacity_and_pause():
    async def case(paused: bool):
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.ADD, reason="add", intended_notional=20.0
        )
        if paused:
            await h.control.pause(RunMode.REPLAY, "p")
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return outcome, position

    ok_outcome, ok_position = asyncio.run(case(False))
    assert ok_outcome.applied and ok_position.quantity > 0
    blocked_outcome, _ = asyncio.run(case(True))
    assert not blocked_outcome.applied
    assert blocked_outcome.reason == "RUNTIME_STATE_PAUSED"


def test_reevaluation_reduce_and_close():
    async def case(action: ReevaluationAction):
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        async with SESSIONS() as session:
            before = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            qty_before = before.quantity
        h.review_provider._response = (
            PositionReevaluation(action=action, reason="reduce", reduce_pct=0.5)
            if action is ReevaluationAction.REDUCE
            else PositionReevaluation(action=action, reason="close")
        )
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        async with SESSIONS() as session:
            after = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return outcome, qty_before, after.quantity

    reduce_outcome, qty_before, qty_after_reduce = asyncio.run(case(ReevaluationAction.REDUCE))
    assert reduce_outcome.applied and 0 < qty_after_reduce < qty_before
    close_outcome, _, qty_after_close = asyncio.run(case(ReevaluationAction.CLOSE))
    assert close_outcome.applied and qty_after_close == 0


# ==============================================================================
# O — Plan replacement
# ==============================================================================


def test_plan_replacement_keeps_one_active_and_cancels_stale():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_limit_buy(h, notional=10, limit=95)
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.UPDATE_STOP, reason="tighten stop", stop_loss=95.0
        )
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        async with SESSIONS() as session:
            active = list(
                (
                    await session.scalars(
                        select(TradePlanRecord).where(
                            TradePlanRecord.run_mode == RunMode.REPLAY,
                            TradePlanRecord.instrument_id == "SOL-USDT",
                            TradePlanRecord.status == PlanStatus.ACTIVE,
                        )
                    )
                ).all()
            )
            old = await session.get(TradePlanRecord, plan.plan_id)
            new_plan = await load_active_plan(session, RunMode.REPLAY, "SOL-USDT")
        return outcome, active, old, new_plan

    outcome, active, old, new_plan = asyncio.run(case())
    assert outcome.applied and outcome.plan_id == new_plan.plan_id
    assert old.status == PlanStatus.REPLACED
    assert len(active) == 1
    assert new_plan.stop_loss == 95.0
    assert new_plan.take_profit == 140.0  # unchanged


# ==============================================================================
# P — Reconciliation failure triggers safe mode without repair
# ==============================================================================


def test_reconciliation_failure_enters_safe_mode_without_repair():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # inject inconsistency: delete one ledger entry
        async with SESSIONS() as session, session.begin():
            ledgers = list((await session.scalars(select(LedgerEntryRecord))).all())
            await session.delete(ledgers[0])
        report = await h.reconcile(RunMode.REPLAY)
        outcome = await h.control.enter_safe_mode(
            RunMode.REPLAY, "reconciliation_failed", incident_type=IncidentType.ACCOUNT_INTEGRITY_ERROR
        )
        async with SESSIONS() as session:
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.ACCOUNT_INTEGRITY_ERROR,
                    IncidentRecord.status == "OPEN",
                )
            )
            ledgers_after = list((await session.scalars(select(LedgerEntryRecord))).all())
        # new risk blocked
        buy_plan = make_plan("SOL-USDT", notional=10)
        await persist_trade_plan(SESSIONS, buy_plan)
        buy_result = await h.execution.execute(intent_for(buy_plan), buy_plan, NOW)
        return report, outcome, incident, len(ledgers_after), buy_result

    report, outcome, incident, ledger_count, buy_result = asyncio.run(case())
    assert not report.ok
    assert "fill_ledger_mismatch" in report.diagnostics
    assert outcome.accepted and outcome.system_state is SystemState.SAFE_MODE
    assert incident is not None
    assert ledger_count == 0  # NOT auto-repaired: the deleted ledger stays deleted
    assert buy_result.status is IntentStatus.REJECTED
    assert buy_result.reason == "RUNTIME_STATE_SAFE_MODE"


# ==============================================================================
# Q / R / S — Restart recovery, stop breach, execution gap
# ==============================================================================


def test_restart_recovery_reconstructs_from_postgres_only():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, "SOL-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_limit_buy(h, notional=10, limit=95)
        # simulate restart: a brand-new harness with fresh in-memory services
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return report, control, position

    report, control, position = asyncio.run(case())
    assert report.ok
    assert "SOL-USDT" in report.active_symbols
    assert report.final_system_state is SystemState.RUNNING
    assert control.system_state == SystemState.RUNNING.value
    assert position.quantity > 0


def test_restart_stop_breach_exits_at_current_bbo():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # restart with the bid already through the stop
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (70.0, 71.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            trade = await session.scalar(
                select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
            )
            sell_fill = await session.scalar(
                select(FillRecord)
                .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                .where(
                    PaperOrderRecord.run_mode == RunMode.REPLAY,
                    PaperOrderRecord.side == OrderSide.SELL,
                )
            )
        return report, position, trade, sell_fill

    report, position, trade, sell_fill = asyncio.run(case())
    assert len(report.protection) >= 1
    triggered = [p for p in report.protection if p.triggered]
    assert triggered
    assert position.quantity == 0
    assert trade.exit_reason == ExitReason.STOP_LOSS.value
    # filled at current executable bid, never the fabricated 80 stop price
    assert sell_fill is not None and sell_fill.price < 71.0


def test_execution_gap_recorded_without_fabricated_fills():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # mark a stale heartbeat to simulate downtime directly in the recovery source of truth
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(RuntimeControlRecord)
                .where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
                .values(heartbeat_at=NOW - timedelta(seconds=3600))
            )
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(PaperOrderRecord.run_mode == RunMode.REPLAY)
                    )
                ).all()
            )
        return report, fills

    report, fills = asyncio.run(case())
    assert report.execution_gap is not None
    assert report.execution_gap["downtime_seconds"] >= 3600
    assert len(fills) == 1  # only the original entry fill; no historical fills fabricated


# ==============================================================================
# T / U — concurrency
# ==============================================================================


def test_concurrent_emergency_vs_buy_fill_is_consistent():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        add_plan = await open_limit_buy(h, notional=10, limit=90)
        h.quotes["SOL-USDT"] = (89.0, 90.0)  # eligible fill
        bbo = await h.bbo_for("SOL-USDT")
        results = await asyncio.gather(
            h.control.emergency_stop(RunMode.REPLAY, "race"),
            h.execution.process_open_orders(RunMode.REPLAY, bbo, NOW),
        )
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        report = await h.reconcile(RunMode.REPLAY)
        return results, control, order, position, account, report

    _, control, order, position, account, report = asyncio.run(case())
    assert control.operator_state == OperatorState.EMERGENCY_STOP.value
    # Either the fill committed before the emergency cancelled it, or it was cancelled first.
    assert order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED)
    assert report.invariants["emergency_no_risk_increasing_open_buy"] is True
    assert position.quantity >= 0
    assert account.reserved_cash >= 0


def test_concurrent_manual_close_vs_sl_closes_at_most_once():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        bbo = await h.bbo_for("SOL-USDT")
        results = await asyncio.gather(
            h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW),
            h.control.manual_close(RunMode.REPLAY, "SOL-USDT", bbo, now=NOW),
        )
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            sell_fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
        return results, position, sell_fills

    _, position, sell_fills = asyncio.run(case())
    assert position.quantity == 0
    assert len(sell_fills) == 1


# ==============================================================================
# Failure injection — transaction rollback
# ==============================================================================


def test_protective_settlement_failure_rolls_back_atomically():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        async with SESSIONS() as session:
            position_before = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            qty_before = position_before.quantity
            fills_before = len(list((await session.scalars(select(FillRecord))).all()))
        h.execution.after_settlement = lambda: (_ for _ in ()).throw(RuntimeError("injected"))
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        with pytest.raises(RuntimeError):
            await h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        h.execution.after_settlement = None
        async with SESSIONS() as session:
            position_after = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            fills_after = list((await session.scalars(select(FillRecord))).all())
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return qty_before, fills_before, position_after, fills_after, account

    qty_before, fills_before, position_after, fills_after, account = asyncio.run(case())
    assert position_after.quantity == qty_before
    assert len(fills_after) == fills_before
    assert account.reserved_cash == 0
    assert account.cash_balance >= 0


def test_emergency_cancel_failure_rolls_back():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_limit_buy(h, notional=10, limit=95)
        original = h.execution.cancel_order

        async def failing_cancel(order_id, now=None, *, session=None):
            raise RuntimeError("cancel_injected")

        h.execution.cancel_order = failing_cancel
        with pytest.raises(RuntimeError):
            await h.control.emergency_stop(RunMode.REPLAY, "injected")
        h.execution.cancel_order = original
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            open_buys = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                    )
                ).all()
            )
        return control, account, open_buys

    control, account, open_buys = asyncio.run(case())
    # the whole emergency transaction rolled back: still RUNNING, BUY still open, cash reserved
    assert control.system_state == SystemState.RUNNING.value
    assert len(open_buys) == 1
    assert account.reserved_cash > 0


def test_plan_replace_failure_rolls_back():
    async def case():
        h = Harness()
        await h.boot()
        _, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.UPDATE_TP, reason="move tp", take_profit=160.0
        )
        original = h.plans.replace

        async def failing_replace(*args, **kwargs):
            raise RuntimeError("replace_injected")

        h.plans.replace = failing_replace
        with pytest.raises(RuntimeError):
            await h.reevaluation.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
            )
        h.plans.replace = original
        async with SESSIONS() as session:
            active = list(
                (
                    await session.scalars(
                        select(TradePlanRecord).where(
                            TradePlanRecord.run_mode == RunMode.REPLAY,
                            TradePlanRecord.instrument_id == "SOL-USDT",
                            TradePlanRecord.status == PlanStatus.ACTIVE,
                        )
                    )
                ).all()
            )
        return active

    active = asyncio.run(case())
    assert len(active) == 1  # old plan untouched, no half-replaced state
