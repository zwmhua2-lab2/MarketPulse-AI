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
    SymbolStateStore,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    DataQuality,
    DecisionStatus,
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
    PositionEventType,
    PositionReevaluation,
    ReevaluationAction,
    SystemState,
)
from marketpulse.g4.planning import PlanManager, derive_followup_plan, load_active_plan
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
                SymbolStateStore,
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


# ==============================================================================
# Post-Review Fix regression tests (P0-1 / P0-2 / P0-3 / P1-1 / P1-2 / P1-3)
# ==============================================================================


def test_reevaluation_state_version_change_is_stale():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)

        async def mutate_during_call(snapshot):
            # A durable fact (symbol state version) moved while the AI was thinking.
            h.state_version += 1
            return PositionReevaluation(action=ReevaluationAction.ADD, reason="add", intended_notional=20.0)

        h.review_provider._response = mutate_during_call
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
            decision = await session.scalar(
                select(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
            )
            stale_events = list(
                (
                    await session.scalars(
                        select(PositionEventRecord).where(
                            PositionEventRecord.run_mode == RunMode.REPLAY,
                            PositionEventRecord.event_type == PositionEventType.AI_REEVALUATION,
                        )
                    )
                ).all()
            )
        return outcome, position, decision, stale_events

    outcome, position, decision, stale_events = asyncio.run(case())
    assert outcome.action is ReevaluationAction.HOLD
    assert not outcome.applied
    assert outcome.reason.startswith("STALE_DECISION")
    assert position.quantity > 0  # the ADD was dropped, position unchanged
    assert decision.status == DecisionStatus.STALE_DECISION.value
    assert any(e.payload and e.payload.get("stale_reasons") for e in stale_events)


def test_reevaluation_active_plan_replaced_is_stale():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)

        async def mutate_during_call(snapshot):
            # Another actor replaced the active plan during the AI call.
            next_plan = derive_followup_plan(
                plan, now=NOW, plan_version=plan.plan_version + 1, stop_loss=85.0
            )
            await h.plans.replace(
                previous=plan,
                next_plan=next_plan,
                event_type=PositionEventType.PLAN_REPLACED,
                now=NOW,
            )
            return PositionReevaluation(action=ReevaluationAction.ADD, reason="add", intended_notional=20.0)

        h.review_provider._response = mutate_during_call
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
            active_plans = list(
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
        return outcome, position, len(active_plans)

    outcome, position, active_count = asyncio.run(case())
    assert outcome.action is ReevaluationAction.HOLD
    assert not outcome.applied
    assert outcome.reason.startswith("STALE_DECISION")
    assert position.quantity > 0
    assert active_count == 1  # only the replacement plan; no stale ADD applied


def test_restart_preserves_persisted_safe_mode_latch():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # Persist SAFE_MODE directly (no blocking incident) so only the latch is exercised.
        await h.state_service.transition(
            RunMode.REPLAY, system_state=SystemState.SAFE_MODE, reason="manual_safe_mode"
        )
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        return report, control

    report, control = asyncio.run(case())
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value
    assert not report.ok


def test_restart_unprotected_position_enters_safe_mode():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # Remove the active plan so the open position has no protection.
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(
                    TradePlanRecord.run_mode == RunMode.REPLAY,
                    TradePlanRecord.instrument_id == "SOL-USDT",
                )
                .values(status=PlanStatus.REPLACED)
            )
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED,
                    IncidentRecord.status == "OPEN",
                )
            )
        return report, control, incident

    report, control, incident = asyncio.run(case())
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value
    assert incident is not None
    assert not report.ok


def test_recovery_stale_quality_bbo_lands_data_degraded():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h2 = Harness()

        async def stale_bbo_for(instrument):
            # Fresh timestamp but stale data quality: must NOT be treated as fresh.
            return BestBidAsk(
                instrument_id=instrument,
                bid=99,
                ask=100,
                received_at=h2.clock.now(),
                data_quality=DataQuality.STALE,
            )

        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=stale_bbo_for, now=h2.clock.now())
        return report

    report = asyncio.run(case())
    assert report.final_system_state is SystemState.DATA_DEGRADED
    assert not report.ok


def test_recovery_cancels_stale_open_buy_and_releases_reservation():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        add_plan = await open_limit_buy(h, notional=20, limit=95, version=7)
        # Bump the symbol state version so the add plan's state_version is stale.
        async with SESSIONS() as session, session.begin():
            await session.merge(
                SymbolStateStore(
                    instrument_id="SOL-USDT",
                    symbol="SOL-USDT",
                    state="ACTIVE",
                    state_version=8,
                )
            )
            add_order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            reserved_before = add_order.reserved_cash
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            add_order_after = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return report, reserved_before, add_order_after, account

    _report, reserved_before, add_order_after, account = asyncio.run(case())
    assert reserved_before > 0
    assert add_order_after.status == OrderStatus.CANCELLED
    assert account.reserved_cash == 0  # reservation released, cash not frozen


def test_recovery_active_symbols_exclude_historical_closed():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, "SOL-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        # Fully close the position, then replace the plan so no active risk fact remains.
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        await h.protection.evaluate(RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW)
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(
                    TradePlanRecord.run_mode == RunMode.REPLAY,
                    TradePlanRecord.instrument_id == "SOL-USDT",
                )
                .values(status=PlanStatus.REPLACED)
            )
        h2 = Harness()
        h2.quotes = {}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        return report

    report = asyncio.run(case())
    assert "SOL-USDT" not in report.active_symbols


def test_reconciliation_detects_stale_risk_increasing_buy():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_limit_buy(h, notional=20, limit=95)
        # Simulate a crash where the position closed but the stale add BUY was never cancelled.
        original_cancel = h.protection._cancel_risk_increasing

        async def noop_cancel(session, run_mode, instrument_id, now):
            return []

        h.protection._cancel_risk_increasing = noop_cancel
        h.quotes["SOL-USDT"] = (98.0, 99.0)
        outcome = await h.control.manual_close(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        h.protection._cancel_risk_increasing = original_cancel
        report = await h.reconcile(RunMode.REPLAY)
        return outcome, report

    outcome, report = asyncio.run(case())
    assert outcome.triggered  # position fully closed
    assert not report.ok
    assert report.invariants["closed_position_no_stale_intent"] is False
    stale = report.details["closed_position_stale_intents"]
    assert any(item["reason"] == "BUY_AFTER_CLOSED_LIFECYCLE" for item in stale)


# ==============================================================================
# Post-Review Fix #2 regression tests
# ==============================================================================


def test_recovery_cancels_buy_when_current_ask_left_entry_zone():
    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan.plan_id)
            )
            reserved_before = order.reserved_cash
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (120.0, 121.0)}
        report = await h2.recovery.recover(
            RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now()
        )
        async with SESSIONS() as session:
            order = await session.get(PaperOrderRecord, order.order_id)
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            fills = list(
                (await session.scalars(select(FillRecord).where(FillRecord.order_id == order.order_id))).all()
            )
        return report, reserved_before, order, account, fills

    report, reserved_before, order, account, fills = asyncio.run(case())
    assert reserved_before > 0
    assert order.status == OrderStatus.CANCELLED and order.reserved_cash == 0
    assert account.reserved_cash == 0 and account.cash_balance == pytest.approx(1000.0)
    assert fills == []
    revalidation = next(item for item in report.order_revalidation if item["order_id"] == order.order_id)
    assert "BUY_PRICE_OUTSIDE_ENTRY_ZONE" in revalidation["issues"]


def test_recovery_cancels_buy_when_stop_already_breached():
    async def case():
        h = Harness()
        await h.boot()
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        plan = make_plan(
            "SOL-USDT",
            notional=20,
            stop=80,
            tp=140,
            entry_zone=PriceZone(lower=70, upper=120),
            order_type=OrderType.LIMIT,
        )
        await persist_trade_plan(SESSIONS, plan)
        result = await h.execution.execute(intent_for(plan), plan, NOW)
        assert result.status is IntentStatus.EXECUTED
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (78.0, 79.0)}
        report = await h2.recovery.recover(
            RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now()
        )
        async with SESSIONS() as session:
            order = await session.get(PaperOrderRecord, result.order_id)
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return report, order, account, position

    report, order, account, position = asyncio.run(case())
    assert order.status == OrderStatus.CANCELLED
    assert account.reserved_cash == 0
    assert position is None or position.quantity == 0
    revalidation = next(item for item in report.order_revalidation if item["order_id"] == order.order_id)
    assert "BUY_STOP_LOSS_BREACHED" in revalidation["issues"]


def test_recovery_cancels_open_buy_for_persisted_symbol_block():
    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session, session.begin():
            session.add(
                SymbolControlRecord(
                    control_id=stable_id("sctl", RunMode.REPLAY, "SOL-USDT"),
                    run_mode=RunMode.REPLAY,
                    instrument_id="SOL-USDT",
                    blocked=True,
                    reason="persisted_block",
                    updated_at=NOW,
                    payload={},
                )
            )
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(
            RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now()
        )
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan.plan_id)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return report, order, account

    report, order, account = asyncio.run(case())
    assert order.status == OrderStatus.CANCELLED and account.reserved_cash == 0
    revalidation = next(item for item in report.order_revalidation if item["order_id"] == order.order_id)
    assert "SYMBOL_BLOCKED" in revalidation["issues"]


def test_reevaluation_atomic_guard_blocks_post_check_plan_race():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.UPDATE_STOP, reason="old response", stop_loss=90.0
        )
        checked = asyncio.Event()
        release = asyncio.Event()
        original_detect = h.reevaluation._detect_stale

        async def pass_then_pause(*args, **kwargs):
            reasons = await original_detect(*args, **kwargs)
            assert reasons == []
            checked.set()
            await release.wait()
            return reasons

        h.reevaluation._detect_stale = pass_then_pause
        evaluate_task = asyncio.create_task(
            h.reevaluation.evaluate(
                RunMode.REPLAY,
                "SOL-USDT",
                await h.bbo_for("SOL-USDT"),
                now=NOW,
                force=True,
            )
        )
        await checked.wait()
        newer = derive_followup_plan(
            plan, now=NOW, plan_version=plan.plan_version + 1, stop_loss=85.0
        )
        await h.plans.replace(previous=plan, next_plan=newer, now=NOW)
        release.set()
        outcome = await evaluate_task
        async with SESSIONS() as session:
            active = await load_active_plan(session, RunMode.REPLAY, "SOL-USDT")
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            decision = await session.scalar(
                select(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
            )
        return outcome, newer, active, position, account, decision

    outcome, newer, active, position, account, decision = asyncio.run(case())
    assert outcome.action is ReevaluationAction.HOLD and not outcome.applied
    assert outcome.reason.startswith("STALE_DECISION")
    assert active.plan_id == newer.plan_id and active.stop_loss == 85.0
    assert position.quantity == pytest.approx(50 / 100.05)
    assert account.cash_balance == pytest.approx(949.95) and account.reserved_cash == 0
    assert decision.status == DecisionStatus.STALE_DECISION.value


def test_reevaluation_uses_action_clock_after_provider_delay():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)

        async def delayed_response(snapshot):
            h.clock.advance(16 * 60)
            return PositionReevaluation(
                action=ReevaluationAction.ADD, reason="late add", intended_notional=20.0
            )

        h.review_provider._response = delayed_response
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        async with SESSIONS() as session:
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                        )
                    )
                ).all()
            )
            decision = await session.scalar(
                select(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
            )
        return outcome, orders, decision

    outcome, orders, decision = asyncio.run(case())
    assert outcome.action is ReevaluationAction.HOLD and not outcome.applied
    assert "plan_expired_at_action" in outcome.reason
    assert len(orders) == 1  # only the original position-opening BUY; zero delayed ADD
    assert decision.created_at == NOW + timedelta(minutes=16)


def test_recovery_bbo_exception_with_open_position_persists_incident():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h2 = Harness()

        async def failing_bbo(_instrument):
            raise RuntimeError("provider_down")

        report = await h2.recovery.recover(
            RunMode.REPLAY, bbo_for=failing_bbo, now=h2.clock.now()
        )
        async with SESSIONS() as session:
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.CORE_DATA_STALE,
                    IncidentRecord.instrument_id == "SOL-USDT",
                    IncidentRecord.status == "OPEN",
                )
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            order_ids = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord.order_id).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY
                        )
                    )
                ).all()
            )
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord).where(FillRecord.order_id.in_(order_ids))
                    )
                ).all()
            )
        return report, h2, incident, position, fills

    report, h2, incident, position, fills = asyncio.run(case())
    assert incident is not None
    assert h2.health.status(HealthComponent.CORE_MARKET_DATA.value) == HealthStatus.UNAVAILABLE
    assert report.final_system_state is SystemState.DATA_DEGRADED and not report.ok
    assert position.quantity > 0
    assert len(fills) == 1  # only the original paper fill; recovery fabricated nothing


def test_safe_mode_recovery_resolves_only_after_durable_checks_pass():
    async def case():
        h = Harness()
        await h.boot()
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "transient_recovery_failure",
            incident_type=IncidentType.RECOVERY_FAILED,
            now=NOW,
        )
        outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session:
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.RECOVERY_FAILED
                )
            )
        return outcome, incident

    outcome, incident = asyncio.run(case())
    assert outcome.accepted
    assert outcome.system_state is SystemState.PAUSED
    assert outcome.operator_state is OperatorState.PAUSED
    assert incident.status == "RESOLVED"


def test_safe_mode_recovery_rejects_corrupt_active_plan_payload_for_open_position():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_missing",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload={"corrupt": "not-a-trade-plan"})
            )
        corrupt_outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        mismatched_identity = plan.model_dump(mode="json")
        mismatched_identity["plan_id"] = "different-plan-id"
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=mismatched_identity)
            )
        identity_outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED,
                    IncidentRecord.status == "OPEN",
                )
            )
        return corrupt_outcome, identity_outcome, control, incident

    corrupt_outcome, identity_outcome, control, incident = asyncio.run(case())
    assert not corrupt_outcome.accepted and corrupt_outcome.reason == "POSITION_UNPROTECTED"
    assert not identity_outcome.accepted and identity_outcome.reason == "POSITION_UNPROTECTED"
    assert control.system_state == SystemState.SAFE_MODE.value
    assert incident is not None


def test_safe_mode_recovery_rejects_parsed_plan_with_invalid_long_protection_relation():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_invalid",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        invalid_payload = plan.model_dump(mode="json")
        invalid_payload["stop_loss"] = 110.0
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=invalid_payload)
            )
        outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        return outcome, control

    outcome, control = asyncio.run(case())
    assert not outcome.accepted and outcome.reason == "POSITION_UNPROTECTED"
    assert control.system_state == SystemState.SAFE_MODE.value


def test_safe_mode_recovery_resolves_position_unprotected_after_valid_plan_restored():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_missing",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload={"corrupt": "not-a-trade-plan"})
            )
        refused = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=plan.model_dump(mode="json"))
            )
        recovered = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session:
            incident = await session.scalar(
                select(IncidentRecord).where(
                    IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED,
                    IncidentRecord.instrument_id == "SOL-USDT",
                )
            )
        return refused, recovered, incident

    refused, recovered, incident = asyncio.run(case())
    assert not refused.accepted and refused.reason == "POSITION_UNPROTECTED"
    assert recovered.accepted and recovered.system_state is SystemState.PAUSED
    assert incident.status == "RESOLVED"


def test_manual_resume_requires_current_valid_protection_after_safe_mode_recovery():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_missing",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        recovered = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        invalid_payload = plan.model_dump(mode="json")
        invalid_payload["stop_loss"] = 110.0
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=invalid_payload)
            )
            # Simulate an erroneous manual incident resolution: Resume must still inspect facts.
            await session.execute(
                update(IncidentRecord)
                .where(IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED)
                .values(status="RESOLVED", resolved_at=NOW)
            )
        unprotected = await h.control.resume(RunMode.REPLAY, now=NOW)
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=plan.model_dump(mode="json"))
            )
        h.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.UNAVAILABLE.value)
        stale_core_data = await h.control.resume(RunMode.REPLAY, now=NOW)
        h.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.HEALTHY.value)
        assert (await h.reconcile(RunMode.REPLAY)).ok
        resumed = await h.control.resume(RunMode.REPLAY, now=NOW)
        return recovered, unprotected, stale_core_data, resumed

    recovered, unprotected, stale_core_data, resumed = asyncio.run(case())
    assert recovered.accepted and recovered.system_state is SystemState.PAUSED
    assert not unprotected.accepted and unprotected.reason == "POSITION_UNPROTECTED"
    assert not stale_core_data.accepted
    assert stale_core_data.reason == "HEALTH_CORE_MARKET_DATA_UNAVAILABLE"
    assert resumed.accepted and resumed.system_state is SystemState.RUNNING


def test_reevaluation_rejects_plan_update_with_breached_stop():
    async def case():
        h = Harness()
        await h.boot()
        original, _ = await open_position(
            h, notional=50, bid=99, ask=100, stop=80, tp=140
        )
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.UPDATE_STOP,
            reason="invalid stop",
            stop_loss=101.0,
        )
        outcome = await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        async with SESSIONS() as session:
            active = await load_active_plan(session, RunMode.REPLAY, "SOL-USDT")
        return outcome, original, active

    outcome, original, active = asyncio.run(case())
    assert not outcome.applied
    assert outcome.reason == "PLAN_VALIDATION_FAILED:stop_already_breached"
    assert active.plan_id == original.plan_id and active.stop_loss == 80
