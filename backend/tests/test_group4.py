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
    SignalTimelineRecord,
    SymbolControlRecord,
    SymbolStateStore,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g2.models import FeatureSnapshot, SymbolState, SymbolStateRecord
from marketpulse.g3.models import (
    AIAnalysis,
    BestBidAsk,
    DataQuality,
    DecisionStatus,
    Direction,
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
from marketpulse.g3.protection_snapshot import authority_from_plan, read_position_protection
from marketpulse.g3.provider import DeterministicFakeAIProvider
from marketpulse.g3.service import (
    DecisionService,
    DecisionSnapshotBuilder,
    G3Workflow,
    PaperExecutionService,
    TradePlanManager,
    persist_trade_plan,
    stable_id,
)
from marketpulse.g4.control import SystemControlService
from marketpulse.g4.incidents import IncidentManager
from marketpulse.g4.models import (
    ExitReason,
    HealthComponent,
    HealthStatus,
    IncidentStatus,
    IncidentType,
    OperatorState,
    PositionEventType,
    PositionReevaluation,
    ReevaluationAction,
    SystemState,
)
from marketpulse.g4.orchestrator import SafetyRuntime
from marketpulse.g4.planning import PlanManager, derive_followup_plan, load_active_plan
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.provider import DeterministicFakePositionReviewProvider
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.recovery import RecoveryManager
from marketpulse.g4.reevaluation import PositionReevaluationService
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.models import MarketType
from marketpulse.runtime import HealthRegistry
from sqlalchemy import delete, select, text, update
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
            SESSIONS, bbo_for, state_version_for, initial_balance=1000.0, clock=self.clock
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
        self.safety = SafetyRuntime(
            execution=self.execution,
            protection=self.protection,
            reevaluation=self.reevaluation,
            health=self.health,
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
# FG-B F03 — protection must not wait for AI
# ==============================================================================


def test_fg_b_slow_ai_does_not_delay_later_stop_loss_and_becomes_stale():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def slow_close(_snapshot):
            entered.set()
            await release.wait()
            return PositionReevaluation(action=ReevaluationAction.CLOSE, reason="late-close")

        h.review_provider._response = slow_close
        first = asyncio.create_task(
            h.safety.on_market_data(
                RunMode.REPLAY, await h.bbo_for("SOL-USDT"), now=NOW, force_reevaluation=True
            )
        )
        await entered.wait()
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        protected = await h.safety.on_market_data(
            RunMode.REPLAY, await h.bbo_for("SOL-USDT"), now=NOW
        )
        assert protected["protection"].triggered
        assert not first.done()  # still blocked in the provider when SL has already settled
        release.set()
        first_result = await first
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            trade = await session.scalar(
                select(TradeRecord).where(
                    TradeRecord.run_mode == RunMode.REPLAY,
                    TradeRecord.instrument_id == "SOL-USDT",
                )
            )
            sell_orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            sell_fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            sell_ledgers = list(
                (
                    await session.scalars(
                        select(LedgerEntryRecord)
                        .join(FillRecord, LedgerEntryRecord.fill_id == FillRecord.fill_id)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            close_events = list(
                (
                    await session.scalars(
                        select(PositionEventRecord).where(
                            PositionEventRecord.run_mode == RunMode.REPLAY,
                            PositionEventRecord.instrument_id == "SOL-USDT",
                            PositionEventRecord.event_type == PositionEventType.CLOSE,
                        )
                    )
                ).all()
            )
            decision = await session.scalar(
                select(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
            )
        return first_result, position, trade, sell_orders, sell_fills, sell_ledgers, close_events, decision

    first_result, position, trade, sell_orders, sell_fills, sell_ledgers, close_events, decision = (
        asyncio.run(case())
    )
    stale = first_result["reevaluation"]
    assert stale is not None and stale.reason.startswith("STALE_DECISION")
    assert position.quantity == 0 and trade.status == "CLOSED"
    assert len(sell_orders) == len(sell_fills) == len(sell_ledgers) == len(close_events) == 1
    assert decision.status == DecisionStatus.STALE_DECISION.value


def test_fg_b_slow_ai_does_not_delay_later_take_profit():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def slow_hold(_snapshot):
            entered.set()
            await release.wait()
            return PositionReevaluation(action=ReevaluationAction.HOLD, reason="late-hold")

        h.review_provider._response = slow_hold
        first = asyncio.create_task(
            h.safety.on_market_data(
                RunMode.REPLAY, await h.bbo_for("SOL-USDT"), now=NOW, force_reevaluation=True
            )
        )
        await entered.wait()
        h.quotes["SOL-USDT"] = (141.0, 142.0)
        protected = await h.safety.on_market_data(
            RunMode.REPLAY, await h.bbo_for("SOL-USDT"), now=NOW
        )
        assert protected["protection"].triggered
        assert not first.done()
        release.set()
        first_result = await first
        async with SESSIONS() as session:
            trade = await session.scalar(
                select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
            )
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
        return first_result, trade, fills

    first_result, trade, fills = asyncio.run(case())
    assert first_result["reevaluation"].reason.startswith("STALE_DECISION")
    assert trade.status == "CLOSED" and trade.exit_reason == ExitReason.TAKE_PROFIT.value
    assert len(fills) == 1


def test_fg_b_ai_reevaluation_is_single_flight_during_bbo_burst():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def slow_hold(_snapshot):
            entered.set()
            await release.wait()
            return PositionReevaluation(action=ReevaluationAction.HOLD, reason="late-hold")

        h.review_provider._response = slow_hold
        first = asyncio.create_task(
            h.safety.on_market_data(
                RunMode.REPLAY, await h.bbo_for("SOL-USDT"), now=NOW, force_reevaluation=True
            )
        )
        await entered.wait()
        quote = await h.bbo_for("SOL-USDT")
        burst = await asyncio.gather(
            *[
                h.safety.on_market_data(
                    RunMode.REPLAY,
                    quote,
                    now=NOW,
                    force_reevaluation=True,
                )
                for _ in range(12)
            ]
        )
        calls_while_blocked = h.review_provider.calls
        inflight_while_blocked = set(h.safety._reevaluation_inflight)
        release.set()
        await first
        return burst, calls_while_blocked, inflight_while_blocked, h.review_provider.calls, h.safety

    burst, calls_while_blocked, inflight_while_blocked, calls_after_release, safety = asyncio.run(case())
    assert len(burst) == 12 and all(item["reevaluation"] is None for item in burst)
    assert calls_while_blocked == calls_after_release == 1
    assert inflight_while_blocked == {(RunMode.REPLAY, "SOL-USDT")}
    assert safety._reevaluation_inflight == set()


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
            # Acquire the pending BUY once under an explicitly unique predicate, then stay on
            # order_id: the protective exit SELL later shares this plan_id (N01-G4-F01).
            add_order = await session.scalar(
                select(PaperOrderRecord).where(
                    PaperOrderRecord.plan_id == add_plan.plan_id,
                    PaperOrderRecord.side == OrderSide.BUY,
                    PaperOrderRecord.order_type == OrderType.LIMIT,
                )
            )
            reserved_before = add_order.reserved_cash
            add_order_id = add_order.order_id
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        async with SESSIONS() as session:
            add_order_after = await session.get(PaperOrderRecord, add_order_id)
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
        # SOL protection/close still allowed: block only blocks risk-increasing BUY/ADD. The
        # open position's SL/TP protection (risk reduction) must remain effective even though
        # block_symbol bumps the durable SymbolStateStore version.
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
# FG-B F06 — canonical Account -> Position(s) risk-reducing lock order
# ==============================================================================


def test_fg_b_cross_symbol_protective_closes_complete_under_account_lock_interleaving():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, "BTC-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_position(h, "ETH-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["BTC-USDT"] = (79.0, 80.0)
        h.quotes["ETH-USDT"] = (79.0, 80.0)
        account_locked = asyncio.Event()
        release = asyncio.Event()

        async def hold_btc_account_lock(_run_mode, instrument_id):
            if instrument_id == "BTC-USDT":
                account_locked.set()
                await release.wait()

        h.protection.after_risk_reducing_account_lock = hold_btc_account_lock
        btc = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "BTC-USDT", await h.bbo_for("BTC-USDT"), now=NOW
            )
        )
        await account_locked.wait()
        eth = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "ETH-USDT", await h.bbo_for("ETH-USDT"), now=NOW
            )
        )
        await asyncio.sleep(0)
        assert not eth.done()  # ETH cannot lock its Position before the shared Account fence.
        release.set()
        results = await asyncio.wait_for(asyncio.gather(btc, eth), timeout=5)
        async with SESSIONS() as session:
            positions = list(
                (
                    await session.scalars(
                        select(PositionRecord).where(
                            PositionRecord.run_mode == RunMode.REPLAY,
                            PositionRecord.instrument_id.in_(("BTC-USDT", "ETH-USDT")),
                        )
                    )
                ).all()
            )
            trades = list(
                (
                    await session.scalars(
                        select(TradeRecord).where(
                            TradeRecord.run_mode == RunMode.REPLAY,
                            TradeRecord.instrument_id.in_(("BTC-USDT", "ETH-USDT")),
                        )
                    )
                ).all()
            )
            fills = list(
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
            ledgers = list(
                (
                    await session.scalars(
                        select(LedgerEntryRecord)
                        .join(FillRecord, LedgerEntryRecord.fill_id == FillRecord.fill_id)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(PaperOrderRecord.side == OrderSide.SELL)
                    )
                ).all()
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return results, positions, trades, fills, ledgers, account, await h.reconcile(RunMode.REPLAY)

    results, positions, trades, fills, ledgers, account, report = asyncio.run(case())
    assert all(item.triggered for item in results)
    assert all(item.quantity == 0 for item in positions)
    assert all(item.status == "CLOSED" for item in trades)
    assert len(fills) == len(ledgers) == 2
    assert account.cash_balance > 0 and account.reserved_cash == 0
    assert report.ok


def test_fg_b_mixed_protection_and_ai_reduce_share_canonical_lock_order():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, "BTC-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        await open_position(h, "ETH-USDT", notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["BTC-USDT"] = (79.0, 80.0)
        account_locked = asyncio.Event()
        release = asyncio.Event()

        async def hold_btc_account_lock(_run_mode, instrument_id):
            if instrument_id == "BTC-USDT":
                account_locked.set()
                await release.wait()

        h.protection.after_risk_reducing_account_lock = hold_btc_account_lock
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.REDUCE, reason="reduce", reduce_pct=0.5
        )
        btc = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "BTC-USDT", await h.bbo_for("BTC-USDT"), now=NOW
            )
        )
        await account_locked.wait()
        ai_reduce = asyncio.create_task(
            h.reevaluation.evaluate(
                RunMode.REPLAY,
                "ETH-USDT",
                await h.bbo_for("ETH-USDT"),
                now=NOW,
                force=True,
            )
        )
        await asyncio.sleep(0)
        assert not ai_reduce.done()
        release.set()
        protection, reduction = await asyncio.wait_for(asyncio.gather(btc, ai_reduce), timeout=5)
        async with SESSIONS() as session:
            btc_position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "BTC-USDT",
                )
            )
            eth_position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "ETH-USDT",
                )
            )
            sells = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id.in_(("BTC-USDT", "ETH-USDT")),
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
        return protection, reduction, btc_position, eth_position, sells, await h.reconcile(RunMode.REPLAY)

    protection, reduction, btc_position, eth_position, sells, report = asyncio.run(case())
    assert protection.triggered
    assert reduction.applied and reduction.action is ReevaluationAction.REDUCE
    assert btc_position.quantity == 0
    assert 0 < eth_position.quantity < 50 / 100.05
    assert len(sells) == 2 and report.ok


def test_fg_b_same_symbol_concurrent_protection_triggers_remain_exactly_once():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.safety.reevaluation_enabled = False
        stop = BestBidAsk(instrument_id="SOL-USDT", bid=79, ask=80, received_at=NOW)
        take_profit = BestBidAsk(instrument_id="SOL-USDT", bid=141, ask=142, received_at=NOW)
        outcomes = await asyncio.gather(
            h.safety.on_market_data(RunMode.REPLAY, stop, now=NOW),
            h.safety.on_market_data(RunMode.REPLAY, take_profit, now=NOW),
        )
        async with SESSIONS() as session:
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
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
        return outcomes, fills, position, await h.reconcile(RunMode.REPLAY)

    outcomes, fills, position, report = asyncio.run(case())
    assert sum(item["protection"].triggered for item in outcomes) == 1
    assert len(fills) == 1 and position.quantity == 0 and report.ok


def test_fg_b_protection_vs_cancel_uses_order_account_position_lock_order():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        pending_plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            pending = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending_plan.plan_id)
            )
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        orders_locked = asyncio.Event()
        release = asyncio.Event()

        async def hold_after_orders(_run_mode, instrument_id):
            if instrument_id == "SOL-USDT":
                orders_locked.set()
                await release.wait()

        h.protection.after_risk_reducing_orders_lock = hold_after_orders
        close = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        )
        await orders_locked.wait()
        cancel = asyncio.create_task(h.execution.cancel_order(pending.order_id, NOW))
        await asyncio.sleep(0)
        assert not cancel.done()  # Protection owns Order before it can request Account.
        release.set()
        protection, cancellation = await asyncio.wait_for(
            asyncio.gather(close, cancel), timeout=5
        )
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == pending.order_id)
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
            trades = list(
                (
                    await session.scalars(
                        select(TradeRecord).where(
                            TradeRecord.run_mode == RunMode.REPLAY,
                            TradeRecord.instrument_id == "SOL-USDT",
                        )
                    )
                ).all()
            )
            sells = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
            ledgers = list(
                (
                    await session.scalars(
                        select(LedgerEntryRecord)
                        .join(FillRecord, LedgerEntryRecord.fill_id == FillRecord.fill_id)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.instrument_id == "SOL-USDT",
                            PaperOrderRecord.side == OrderSide.SELL,
                        )
                    )
                ).all()
            )
        return protection, cancellation, order, account, position, trades, sells, ledgers, await h.reconcile(RunMode.REPLAY)

    protection, cancellation, order, account, position, trades, sells, ledgers, report = asyncio.run(
        case()
    )
    assert protection.triggered and not cancellation.cancelled
    assert order.status == OrderStatus.CANCELLED and order.reserved_cash == 0
    assert account.reserved_cash == 0 and position.quantity == 0
    assert len(trades) == len(sells) == len(ledgers) == 1 and trades[0].status == "CLOSED"
    assert report.ok


def test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen():
    async def case():
        h = Harness()
        await h.boot()
        opening_plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        pending_plan = await open_limit_buy(h, notional=20, limit=95)
        # The pending BUY is the only LIMIT BUY under this plan, so this acquisition is unique by
        # construction. Every assertion below then reads that exact order by order_id, because
        # plan_id is not a unique order identity here (N01-G4-F01). Candidate A (N01-7-F01-R1)
        # additionally changed *which* plan the protective exit is attributed to -- the position's
        # durable snapshot, i.e. `opening_plan`, rather than the merely-ACTIVE `pending_plan` -- so
        # the exit order is read by the identity the protection outcome itself reports.
        async with SESSIONS() as session:
            pending_order_ids = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord.order_id).where(
                            PaperOrderRecord.plan_id == pending_plan.plan_id,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.order_type == OrderType.LIMIT,
                        )
                    )
                ).all()
            )
        assert len(pending_order_ids) == 1
        pending_order_id = pending_order_ids[0]
        h.quotes["SOL-USDT"] = (79.0, 80.0)  # SL and BUY limit eligibility are both present.
        orders_locked = asyncio.Event()
        release = asyncio.Event()

        async def hold_after_orders(_run_mode, instrument_id):
            if instrument_id == "SOL-USDT":
                orders_locked.set()
                await release.wait()

        h.protection.after_risk_reducing_orders_lock = hold_after_orders
        close = asyncio.create_task(
            h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        )
        await orders_locked.wait()
        fill = asyncio.create_task(
            h.execution.process_open_orders(RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW)
        )
        await asyncio.sleep(0)
        assert not fill.done()  # The fill path waits on the same Order, not an Account cycle.
        release.set()
        protection, fills = await asyncio.wait_for(asyncio.gather(close, fill), timeout=5)
        async with SESSIONS() as session:
            # plan_id is NOT a unique order identity here: the protective exit SELL shares it with
            # the pending BUY. Read the pending BUY by its own primary key, never by plan_id alone.
            pending_order = await session.get(PaperOrderRecord, pending_order_id)
            protective_sell = (
                await session.get(PaperOrderRecord, protection.order_id)
                if protection.order_id is not None
                else None
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
        return (
            protection,
            fills,
            pending_order,
            protective_sell,
            position,
            buy_fills,
            opening_plan,
            await h.reconcile(RunMode.REPLAY),
        )

    (
        protection,
        fills,
        pending_order,
        protective_sell,
        position,
        buy_fills,
        opening_plan,
        report,
    ) = asyncio.run(case())
    assert protection.triggered and fills == []
    # The exact pending BUY (stable identity = order_id) was cancelled, not the protective SELL.
    assert protection.cancelled_order_ids == [pending_order.order_id]
    assert pending_order.side == OrderSide.BUY
    assert pending_order.order_type == OrderType.LIMIT
    assert pending_order.status == OrderStatus.CANCELLED
    assert pending_order.reserved_cash == 0
    assert protective_sell is not None
    assert protective_sell.side == OrderSide.SELL
    assert protective_sell.status == OrderStatus.FILLED
    # The exit is attributed to the authority that protected the position -- the durable snapshot,
    # i.e. the plan that opened it -- not to the plan that merely happened to be ACTIVE.
    assert protective_sell.plan_id == opening_plan.plan_id
    assert position.quantity == 0
    assert len(buy_fills) == 1  # only the original position entry; pending BUY never reopens it
    assert buy_fills[0].order_id != pending_order.order_id
    assert report.ok


def test_fg_b_ai_close_claims_pending_buy_order_before_account():
    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        pending_plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            pending = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending_plan.plan_id)
            )
        claimed = asyncio.Event()
        release = asyncio.Event()
        original = h.protection._lock_risk_increasing_orders
        calls = 0

        async def hold_first_order_claim(session, run_mode, instrument_id):
            nonlocal calls
            orders = await original(session, run_mode, instrument_id)
            calls += 1
            if calls == 1:
                claimed.set()
                await release.wait()
            return orders

        h.protection._lock_risk_increasing_orders = hold_first_order_claim
        h.review_provider._response = PositionReevaluation(
            action=ReevaluationAction.CLOSE, reason="ai-close"
        )
        close = asyncio.create_task(
            h.reevaluation.evaluate(
                RunMode.REPLAY,
                "SOL-USDT",
                await h.bbo_for("SOL-USDT"),
                now=NOW,
                force=True,
            )
        )
        await claimed.wait()
        cancel = asyncio.create_task(h.execution.cancel_order(pending.order_id, NOW))
        await asyncio.sleep(0)
        assert not cancel.done()
        release.set()
        outcome, cancellation = await asyncio.wait_for(asyncio.gather(close, cancel), timeout=5)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == pending.order_id)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return outcome, cancellation, order, position, calls, await h.reconcile(RunMode.REPLAY)

    outcome, cancellation, order, position, calls, report = asyncio.run(case())
    assert outcome.applied and outcome.action is ReevaluationAction.CLOSE
    assert not cancellation.cancelled and order.status == OrderStatus.CANCELLED
    assert position.quantity == 0 and calls >= 2 and report.ok


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
    """Candidate A (N01-7-F01-R1): recovery latches SAFE_MODE when the OPEN position has no
    durable protection authority, regardless of what the plan rows say.

    Superseded premise: this test used to remove the ACTIVE plan and expect SAFE_MODE. A plan row
    is no longer any part of the protection-lifetime authority, so losing it proves nothing; the
    position's own snapshot is what recovery must refuse to proceed without.
    """

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _null_snapshot()
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

        async def noop_cancel(session, run_mode, instrument_id, now, *, orders=None):
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


def test_reconciliation_uses_one_repeatable_read_snapshot_across_g3_and_g4():
    """G4's actual G3 call shares one real read-only REPEATABLE READ transaction."""

    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        base_snapshot_taken = asyncio.Event()
        allow_extended_reads = asyncio.Event()
        original_reconciliation = h.execution.reconciliation
        original_reconciliation_once = h.execution._reconciliation_once
        transaction_state: tuple[str | None, str | None] | None = None
        g4_transaction_identity: tuple[int, int] | None = None
        g3_transaction_identity: tuple[int, int] | None = None

        async def capture_g3_transaction_identity(run_mode, session):
            nonlocal g3_transaction_identity
            transaction = session.get_transaction()
            assert transaction is not None
            g3_transaction_identity = (id(session), id(transaction))
            return await original_reconciliation_once(run_mode, session)

        async def pause_after_g3_snapshot(run_mode, *, session=None):
            nonlocal g4_transaction_identity, transaction_state
            transaction = session.get_transaction()
            assert transaction is not None
            g4_transaction_identity = (id(session), id(transaction))
            transaction_state = (
                await session.scalar(text("SHOW transaction_isolation")),
                await session.scalar(text("SHOW transaction_read_only")),
            )
            result = await original_reconciliation(run_mode, session=session)
            base_snapshot_taken.set()
            await asyncio.wait_for(allow_extended_reads.wait(), timeout=2)
            return result

        h.execution._reconciliation_once = capture_g3_transaction_identity
        h.execution.reconciliation = pause_after_g3_snapshot
        try:
            report_task = asyncio.create_task(h.reconcile(RunMode.REPLAY))
            await asyncio.wait_for(base_snapshot_taken.wait(), timeout=2)
            async with SESSIONS() as writer, writer.begin():
                await writer.execute(
                    update(TradePlanRecord)
                    .where(TradePlanRecord.plan_id == plan.plan_id)
                    .values(status=PlanStatus.REPLACED)
                )
            allow_extended_reads.set()
            report = await asyncio.wait_for(report_task, timeout=2)
        finally:
            h.execution.reconciliation = original_reconciliation
            h.execution._reconciliation_once = original_reconciliation_once
        current = await h.reconcile(RunMode.REPLAY)
        return report, current, transaction_state, g4_transaction_identity, g3_transaction_identity

    (
        snapshot_report,
        current_report,
        transaction_state,
        g4_transaction_identity,
        g3_transaction_identity,
    ) = asyncio.run(case())
    assert transaction_state == ("repeatable read", "on")
    assert g4_transaction_identity is not None
    assert g3_transaction_identity == g4_transaction_identity
    assert snapshot_report.ok
    assert snapshot_report.invariants["open_order_plan_valid"] is True
    # The completed concurrent transaction is visible to a fresh report, proving the first
    # report deliberately retained its earlier snapshot rather than racing the writer.
    assert current_report.ok is False
    assert current_report.invariants["open_order_plan_valid"] is False


def test_reconciliation_account_order_cancellation_race_uses_one_snapshot():
    """An account read cannot tear from a committed order-cancellation reservation release."""

    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan.plan_id)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            assert order is not None
            assert account is not None
            reserved_cash = order.reserved_cash
            order_id = order.order_id
            assert account.reserved_cash == pytest.approx(reserved_cash)

        account_read_completed = asyncio.Event()
        release_order_read = asyncio.Event()
        original_reconciliation_once = h.execution._reconciliation_once

        async def pause_before_order_read(run_mode, session):
            original_scalars = session.scalars
            order_read_paused = False

            async def paused_scalars(*args, **kwargs):
                nonlocal order_read_paused
                if not order_read_paused:
                    # `_reconciliation_once()` has completed its account scalar query and its
                    # first scalars query is PaperOrderRecord.  Pause before that order query.
                    order_read_paused = True
                    account_read_completed.set()
                    await asyncio.wait_for(release_order_read.wait(), timeout=2)
                return await original_scalars(*args, **kwargs)

            session.scalars = paused_scalars
            try:
                return await original_reconciliation_once(run_mode, session)
            finally:
                session.scalars = original_scalars

        h.execution._reconciliation_once = pause_before_order_read
        try:
            report_task = asyncio.create_task(h.reconcile(RunMode.REPLAY))
            await asyncio.wait_for(account_read_completed.wait(), timeout=2)
            async with SESSIONS() as writer, writer.begin():
                account = await writer.scalar(
                    select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
                )
                order = await writer.get(PaperOrderRecord, order_id)
                assert account is not None
                assert order is not None
                account.reserved_cash = 0.0
                order.status = OrderStatus.CANCELLED
                order.reserved_cash = 0.0
                order.reserved_quantity = 0.0
            assert report_task.done() is False
            release_order_read.set()
            snapshot_report = await asyncio.wait_for(report_task, timeout=2)
        finally:
            h.execution._reconciliation_once = original_reconciliation_once

        fresh_report = await h.reconcile(RunMode.REPLAY)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.get(PaperOrderRecord, order_id)
        return snapshot_report, fresh_report, account, order, reserved_cash

    snapshot_report, fresh_report, account, order, reserved_cash = asyncio.run(case())
    assert snapshot_report.details["open_orders"] == 1
    assert snapshot_report.details["open_buys"] == 1
    assert snapshot_report.invariants["reserved_cash_matches_open_buys"] is True
    assert "reserved_cash_mismatch" not in snapshot_report.diagnostics
    assert fresh_report.details["open_orders"] == 0
    assert fresh_report.details["open_buys"] == 0
    assert fresh_report.invariants["reserved_cash_matches_open_buys"] is True
    assert account is not None and account.reserved_cash == 0
    assert order is not None
    assert order.status == OrderStatus.CANCELLED
    assert order.reserved_cash == 0
    assert reserved_cash > 0


def test_g4_reconciliation_propagates_durable_reserved_cash_corruption():
    """G4 remains detector-only when a durable account/order reservation mismatch exists."""

    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan.plan_id)
            )
            assert account is not None
            assert order is not None
            reserved_cash = account.reserved_cash
            order_id = order.order_id
            assert reserved_cash > 0
            assert order.status == OrderStatus.OPEN
            assert order.reserved_cash == pytest.approx(reserved_cash)

        baseline = await h.reconcile(RunMode.REPLAY)
        async with SESSIONS() as writer, writer.begin():
            account = await writer.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await writer.get(PaperOrderRecord, order_id)
            assert account is not None
            assert order is not None
            account.reserved_cash = reserved_cash + 1.0

        async with SESSIONS() as session:
            corrupted_account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            corrupted_order = await session.get(PaperOrderRecord, order_id)
        report = await h.reconcile(RunMode.REPLAY)
        async with SESSIONS() as session:
            post_report_account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            post_report_order = await session.get(PaperOrderRecord, order_id)
        return (
            baseline,
            report,
            reserved_cash,
            corrupted_account,
            corrupted_order,
            post_report_account,
            post_report_order,
        )

    (
        baseline,
        report,
        reserved_cash,
        corrupted_account,
        corrupted_order,
        post_report_account,
        post_report_order,
    ) = asyncio.run(case())
    assert baseline.ok is True
    assert baseline.invariants["reserved_cash_matches_open_buys"] is True
    assert corrupted_account is not None
    assert corrupted_order is not None
    assert corrupted_account.reserved_cash == pytest.approx(reserved_cash + 1.0)
    assert corrupted_order.status == OrderStatus.OPEN
    assert corrupted_order.reserved_cash == pytest.approx(reserved_cash)
    assert abs(corrupted_account.reserved_cash - corrupted_order.reserved_cash) > 1e-8
    assert report.ok is False
    assert report.invariants["reserved_cash_matches_open_buys"] is False
    assert report.details["g3"]["reserved_cash_matches_open_buys"] is False
    assert "reserved_cash_mismatch" in report.diagnostics
    assert post_report_account is not None
    assert post_report_order is not None
    assert post_report_account.reserved_cash == pytest.approx(reserved_cash + 1.0)
    assert post_report_order.status == OrderStatus.OPEN
    assert post_report_order.reserved_cash == pytest.approx(reserved_cash)


def test_g4_reconciliation_failure_cleans_outer_transaction_for_immediate_writer():
    """A failed G4 report releases its caller-owned transaction before another writer commits."""

    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=20, limit=95)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == plan.plan_id)
            )
            assert account is not None
            assert order is not None
            reserved_cash = account.reserved_cash
            order_id = order.order_id
            assert reserved_cash > 0
            assert order.status == OrderStatus.OPEN
            assert order.reserved_cash == pytest.approx(reserved_cash)

        baseline = await h.reconcile(RunMode.REPLAY)
        observed: dict[str, object] = {}
        original_reconciliation = h.execution.reconciliation
        original_reconciliation_once = h.execution._reconciliation_once

        async def capture_g4_owned_transaction(run_mode, *, session=None):
            assert session is not None
            transaction = session.get_transaction()
            assert transaction is not None
            observed["session"] = session
            observed["transaction"] = transaction
            observed["transaction_state"] = (
                await session.scalar(text("SHOW transaction_isolation")),
                await session.scalar(text("SHOW transaction_read_only")),
            )
            return await original_reconciliation(run_mode, session=session)

        async def fail_after_actual_account_read(run_mode, session):
            original_scalars = session.scalars
            raised = False

            async def raise_before_order_read(*args, **kwargs):
                nonlocal raised
                if not raised:
                    raised = True
                    observed["account_read_completed"] = True
                    raise RuntimeError("injected g4 reconciliation failure")
                return await original_scalars(*args, **kwargs)

            session.scalars = raise_before_order_read
            try:
                return await original_reconciliation_once(run_mode, session)
            finally:
                session.scalars = original_scalars

        h.execution.reconciliation = capture_g4_owned_transaction
        h.execution._reconciliation_once = fail_after_actual_account_read
        try:
            with pytest.raises(RuntimeError, match="injected g4 reconciliation failure"):
                await h.reconcile(RunMode.REPLAY)
        finally:
            h.execution.reconciliation = original_reconciliation
            h.execution._reconciliation_once = original_reconciliation_once

        async def cancel_with_independent_writer():
            async with SESSIONS() as writer, writer.begin():
                account = await writer.scalar(
                    select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
                )
                order = await writer.get(PaperOrderRecord, order_id)
                assert account is not None
                assert order is not None
                account.reserved_cash = 0.0
                order.status = OrderStatus.CANCELLED
                order.reserved_cash = 0.0
                order.reserved_quantity = 0.0

        await asyncio.wait_for(cancel_with_independent_writer(), timeout=2)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.get(PaperOrderRecord, order_id)
        fresh = await h.reconcile(RunMode.REPLAY)
        return baseline, fresh, observed, account, order

    baseline, fresh, observed, account, order = asyncio.run(case())
    transaction = observed["transaction"]
    session = observed["session"]
    assert baseline.ok is True
    assert observed["transaction_state"] == ("repeatable read", "on")
    assert observed["account_read_completed"] is True
    assert session.in_transaction() is False
    assert transaction.is_active is False
    assert account is not None and account.reserved_cash == 0
    assert order is not None
    assert order.status == OrderStatus.CANCELLED
    assert order.reserved_cash == 0
    assert order.reserved_quantity == 0
    assert fresh.ok is True
    assert fresh.details["open_orders"] == 0
    assert fresh.details["open_buys"] == 0
    assert fresh.invariants["reserved_cash_matches_open_buys"] is True
    assert "reserved_cash_mismatch" not in fresh.diagnostics


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


def _assert_resume_refused_for_missing_authority(resume) -> None:
    """A resume must be refused while an OPEN position has no durable authority.

    Two independent detectors can report first -- the resume gate's own protection check, and G4
    reconciliation (invariant #13, which Candidate A re-based on the durable condition itself) --
    so every legitimate refusal reason is accepted, but a refusal is mandatory.
    """
    assert not resume.accepted
    assert (
        resume.reason in ("POSITION_UNPROTECTED", "INCIDENT_POSITION_UNPROTECTED")
        or resume.reason.startswith("RECONCILIATION_FAILED")
    ), resume.reason


def test_safe_mode_recovery_rejects_missing_durable_authority_for_open_position():
    """Candidate A (N01-7-F01-R1): the durable condition is the position snapshot, not the plan.

    Superseded by Candidate A — formerly
    `test_safe_mode_recovery_rejects_corrupt_active_plan_payload_for_open_position`, which asserted
    refusal for a corrupt / identity-inconsistent plan payload. A plan row is no longer part of the
    protection-lifetime authority at all, so this safeguard is re-based on the condition that
    actually justifies it, and the plan manipulation is kept only as *context* proving the refusal
    is caused by the missing authority and not by the plan defect.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _null_snapshot()
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
    _assert_resume_refused_for_missing_authority(corrupt_outcome)
    _assert_resume_refused_for_missing_authority(identity_outcome)
    assert control.system_state == SystemState.SAFE_MODE.value
    assert incident is not None


def test_safe_mode_recovery_accepts_profit_lock_stop_above_long_average_cost():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=99.95, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (120.0, 121.0)
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_invalid",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        profit_lock_payload = plan.model_dump(mode="json")
        profit_lock_payload["stop_loss"] = 110.0
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=profit_lock_payload)
            )
        outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
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
        return outcome, control, position

    outcome, control, position = asyncio.run(case())
    assert outcome.accepted and outcome.system_state is SystemState.PAUSED
    assert control.system_state == SystemState.PAUSED.value
    assert position.average_cost == pytest.approx(100.0)


def test_safe_mode_recovery_rejects_open_position_without_durable_authority():
    """Candidate A (N01-7-F01-R1): re-based from
    `test_safe_mode_recovery_rejects_parsed_plan_with_invalid_stop_take_profit_relation`.

    A plan whose SL/TP relationship is broken is no longer a protection-lifetime defect: the OPEN
    position's own snapshot decides. The safeguard is therefore exercised against the condition
    that does justify it — an OPEN position with no durable authority — while the broken plan row
    stays in place as context proving the verdict is not plan-driven.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _null_snapshot()
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_invalid",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        invalid_payload = plan.model_dump(mode="json")
        invalid_payload["stop_loss"] = 140.0
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
    _assert_resume_refused_for_missing_authority(outcome)
    assert control.system_state == SystemState.SAFE_MODE.value


def test_safe_mode_recovery_resolves_position_unprotected_after_durable_authority_restored():
    """Candidate A (N01-7-F01-R1): re-based from
    `test_safe_mode_recovery_resolves_position_unprotected_after_valid_plan_restored`.

    Clearing a POSITION_UNPROTECTED latch must re-prove the durable condition rather than trust the
    incident flag, and must resolve only once that condition is genuinely gone. Under Candidate A
    the durable condition is the position snapshot, so the test removes and restores that snapshot;
    a plan payload can no longer revive protection.
    """

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
        await _null_snapshot()
        refused = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        await _restore_snapshot(plan)
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
    assert not refused.accepted
    assert refused.reason == "POSITION_UNPROTECTED" or refused.reason.startswith(
        "RECONCILIATION_FAILED"
    ), refused.reason
    assert recovered.accepted and recovered.system_state is SystemState.PAUSED
    assert incident.status == "RESOLVED"


def test_manual_resume_accepts_profit_lock_stop_after_safe_mode_recovery():
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
        profit_lock_payload = plan.model_dump(mode="json")
        profit_lock_payload["stop_loss"] = 110.0
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=profit_lock_payload)
            )
            # Resume must inspect durable facts, not only the resolved incident flag.
            await session.execute(
                update(IncidentRecord)
                .where(IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED)
                .values(status="RESOLVED", resolved_at=NOW)
            )
        h.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.UNAVAILABLE.value)
        stale_core_data = await h.control.resume(RunMode.REPLAY, now=NOW)
        h.health.set(HealthComponent.CORE_MARKET_DATA.value, HealthStatus.HEALTHY.value)
        h.quotes["SOL-USDT"] = (120.0, 121.0)
        assert (await h.reconcile(RunMode.REPLAY)).ok
        resumed = await h.control.resume(RunMode.REPLAY, now=NOW)
        return recovered, stale_core_data, resumed

    recovered, stale_core_data, resumed = asyncio.run(case())
    assert recovered.accepted and recovered.system_state is SystemState.PAUSED
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


_ORDERING_INSTRUMENT = "SOL-USDT"
_ORDERING_CONFIG_VERSION = "g4-ordering-regression"
_ORDERING_ORDER_IDS = ("ord-a", "ord-b", "ord-c")


def test_reevaluation_snapshot_orders_timeline_and_open_orders_deterministically():
    """Equal event_time / equal created_at must not leave snapshot list order to the database."""

    def timeline_rows(index_order: list[int]) -> list[SignalTimelineRecord]:
        return [
            SignalTimelineRecord(
                timeline_id=f"tl-{index:02d}",
                event_id=f"evt-{index:02d}",
                symbol=_ORDERING_INSTRUMENT,
                instrument_id=_ORDERING_INSTRUMENT,
                signal_type="BREAKOUT",
                # Index 21 deliberately shares event_time with index 20: the deterministic
                # timeline_id tie-break has to decide, not PostgreSQL heap order.
                event_time=NOW + timedelta(seconds=20 if index == 21 else index),
                received_time=NOW + timedelta(seconds=index),
                price=100.0,
                context={},
                strength=0.5,
                lifecycle_action="START",
                symbol_state="SETUP",
                state_version=7,
                config_version=_ORDERING_CONFIG_VERSION,
            )
            for index in index_order
        ]

    def open_orders(plan_id: str, insert_order: tuple[str, ...]) -> list[PaperOrderRecord]:
        created_at = {
            "ord-a": NOW,
            "ord-b": NOW + timedelta(seconds=5),
            "ord-c": NOW + timedelta(seconds=5),
        }
        return [
            PaperOrderRecord(
                order_id=order_id,
                intent_id=f"intent-{order_id}",
                plan_id=plan_id,
                instrument_id=_ORDERING_INSTRUMENT,
                run_mode=RunMode.REPLAY.value,
                side=OrderSide.BUY.value,
                order_type=OrderType.LIMIT.value,
                status=OrderStatus.OPEN.value,
                quantity=1.0,
                limit_price=95.0,
                reserved_cash=95.0,
                reserved_quantity=0.0,
                created_at=created_at[order_id],
            )
            for order_id in insert_order
        ]

    async def case(*, descending_insert: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
        h = Harness()
        await h.boot()
        plan, _ = await open_position(
            h, notional=50, bid=99, ask=100, stop=80, tp=140
        )
        index_order = list(range(25))
        if descending_insert:
            index_order.reverse()
        async with SESSIONS() as session, session.begin():
            await session.execute(
                delete(SignalTimelineRecord).where(
                    SignalTimelineRecord.config_version == _ORDERING_CONFIG_VERSION
                )
            )
            session.add_all(timeline_rows(index_order))
            session.add_all(open_orders(plan.plan_id, ("ord-c", "ord-a", "ord-b")))
        await h.reevaluation.evaluate(
            RunMode.REPLAY,
            _ORDERING_INSTRUMENT,
            await h.bbo_for(_ORDERING_INSTRUMENT),
            now=NOW,
            force=True,
        )
        async with SESSIONS() as session:
            snapshots = list(
                (
                    await session.scalars(
                        select(DecisionSnapshotRecord).where(
                            DecisionSnapshotRecord.run_mode == RunMode.REPLAY,
                            DecisionSnapshotRecord.instrument_id == _ORDERING_INSTRUMENT,
                        )
                    )
                ).all()
            )
        reviews = [
            record
            for record in snapshots
            if record.payload.get("trading_context", {}).get("triggering_event") == "MANUAL"
        ]
        assert len(reviews) == 1, f"expected exactly one review snapshot, got {len(reviews)}"
        payload = reviews[0].payload
        return (
            tuple(item["event_id"] for item in payload["market_evolution"]["timeline"]),
            tuple(item["order_id"] for item in payload["trading_context"]["open_orders"]),
        )

    async def scenario() -> tuple[
        tuple[tuple[str, ...], tuple[str, ...]], tuple[tuple[str, ...], tuple[str, ...]]
    ]:
        try:
            return await case(descending_insert=False), await case(descending_insert=True)
        finally:
            await Harness().clean()
            async with SESSIONS() as session, session.begin():
                await session.execute(
                    delete(SignalTimelineRecord).where(
                        SignalTimelineRecord.config_version == _ORDERING_CONFIG_VERSION
                    )
                )

    ascending, descending = asyncio.run(scenario())

    # The latest 20 of 25 timeline rows are kept (oldest five dropped) and the equal-event_time
    # pair is ordered by timeline_id ascending after the production reverse step.
    assert ascending[0] == tuple(f"evt-{index:02d}" for index in range(5, 25))
    assert descending[0] == ascending[0]
    # created_at ascending, then order_id ascending; ord-b and ord-c share created_at.
    assert ascending[1] == ("ord-a", "ord-b", "ord-c")
    assert descending[1] == ascending[1]


# ==============================================================================
# G5-3 Review Fix #1 — deterministic OPEN BUY cancellation ordering
# ==============================================================================


def _insert_two_open_buys(plan_id: str, *, created_at: datetime) -> list[PaperOrderRecord]:
    """Insert two OPEN BUY orders with equal created_at and insertion order opposite canonical.

    order_id ASC is the deterministic tie-break; inserting ("ord-b", "ord-a") means a heap-order
    scan would yield the wrong list unless the query orders by (created_at ASC, order_id ASC).
    """
    return [
        PaperOrderRecord(
            order_id=order_id,
            intent_id=f"intent-{order_id}",
            plan_id=plan_id,
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY.value,
            side=OrderSide.BUY.value,
            order_type=OrderType.LIMIT.value,
            status=OrderStatus.OPEN.value,
            quantity=1.0,
            limit_price=95.0,
            reserved_cash=95.0,
            reserved_quantity=0.0,
            created_at=created_at,
        )
        for order_id in ("ord-b", "ord-a")
    ]


async def _cancelled_order_ids(event_type: PositionEventType) -> list[str]:
    async with SESSIONS() as session:
        event = await session.scalar(
            select(PositionEventRecord).where(
                PositionEventRecord.run_mode == RunMode.REPLAY,
                PositionEventRecord.instrument_id == "SOL-USDT",
                PositionEventRecord.event_type == event_type.value,
            )
        )
        return event.payload.get("cancelled_order_ids", [])


async def _seed_two_open_buys(plan_id: str, *, created_at: datetime) -> None:
    """Insert two OPEN BUY orders and reserve their cash on the account, atomically."""
    async with SESSIONS() as session, session.begin():
        rows = _insert_two_open_buys(plan_id, created_at=created_at)
        session.add_all(rows)
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
        )
        account.reserved_cash += sum(row.reserved_cash for row in rows)


def test_protection_exit_cancels_open_buys_in_created_at_then_order_id_order():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _seed_two_open_buys(plan.plan_id, created_at=NOW)
        # Move the bid below stop: STOP_LOSS triggers _cancel_risk_increasing.
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return await _cancelled_order_ids(PositionEventType.SL_TRIGGERED)

    cancelled = asyncio.run(case())
    assert cancelled == ["ord-a", "ord-b"]


def test_recorded_cancel_add_cancels_open_buys_in_deterministic_order():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.review_provider = DeterministicFakePositionReviewProvider(
            PositionReevaluation(action=ReevaluationAction.CANCEL_ADD, reason="cancel-add")
        )
        h.reevaluation.provider = h.review_provider
        await _seed_two_open_buys(plan.plan_id, created_at=NOW)
        await h.reevaluation.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW, force=True
        )
        return await _cancelled_order_ids(PositionEventType.CANCEL_ADD)

    cancelled = asyncio.run(case())
    assert cancelled == ["ord-a", "ord-b"]


def test_plan_replacement_cancels_stale_open_buys_in_deterministic_order():
    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        next_plan = derive_followup_plan(
            plan, now=NOW, plan_version=2, stop_loss=85.0, take_profit=145.0
        )
        await _seed_two_open_buys(plan.plan_id, created_at=NOW)
        await h.plans.replace(previous=plan, next_plan=next_plan, now=NOW)
        return await _cancelled_order_ids(PositionEventType.PLAN_REPLACED)

    cancelled = asyncio.run(case())
    assert cancelled == ["ord-a", "ord-b"]


# ==============================================================================
# FG-C — Safety Recovery Validity
# ==============================================================================


def test_fg_c_pause_refused_under_emergency_stop():
    """F04: the emergency latch must not be downgraded by pause(), otherwise a later resume()
    would bypass emergency authority. Only emergency_recovery() may clear it."""

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await h.control.emergency_stop(RunMode.REPLAY, "e")
        paused = await h.control.pause(RunMode.REPLAY, "try_pause")
        resumed = await h.control.resume(RunMode.REPLAY)
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        return paused, resumed, control

    paused, resumed, control = asyncio.run(case())
    assert not paused.accepted  # pause must not overwrite EMERGENCY_STOP
    assert paused.operator_state is OperatorState.EMERGENCY_STOP
    assert not resumed.accepted  # resume still blocked by the intact emergency latch
    assert control.operator_state == OperatorState.EMERGENCY_STOP.value
    assert control.system_state == SystemState.EMERGENCY_STOP.value


def _crash_after(state_service, reason: str):
    """Wrap transition so a durable commit is followed by a simulated process death."""
    original = state_service.transition

    async def wrapper(*args, **kwargs):
        result = await original(*args, **kwargs)
        if kwargs.get("reason") == reason:
            raise RuntimeError(f"simulated_crash_after_{reason}")
        return result

    state_service.transition = wrapper
    return original


async def _persist_safe_mode():
    """Persist SAFE_MODE directly (no blocking incident) so only the latch is exercised."""
    h = Harness()
    await h.boot()
    await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
    await h.state_service.transition(
        RunMode.REPLAY, system_state=SystemState.SAFE_MODE, reason="manual_safe_mode"
    )
    return h


async def _recover_landing(quotes):
    """Fresh manager recovers; return (report, durable system_state)."""
    h = Harness()
    h.quotes = quotes
    report = await h.recovery.recover(RunMode.REPLAY, bbo_for=h.bbo_for, now=h.clock.now())
    async with SESSIONS() as session:
        control = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
        )
    return report, control


def test_fg_c_f05_case1_safe_mode_persisted_restart_lands_safe_mode():
    """F05 Case 1: SAFE_MODE persisted -> restart -> still SAFE_MODE."""

    async def case():
        await _persist_safe_mode()
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return report, control

    report, control = asyncio.run(case())
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value
    assert not report.ok


def test_fg_c_f05_case2_crash_after_latch_before_starting():
    """F05 Case 2: latch durable write committed -> crash before STARTING -> fresh -> SAFE_MODE."""

    async def case():
        await _persist_safe_mode()
        h = Harness()
        h.quotes = {"SOL-USDT": (99.0, 100.0)}
        original = _crash_after(h.recovery.state_service, "safe_mode_latch")
        try:
            with pytest.raises(RuntimeError, match="simulated_crash_after_safe_mode_latch"):
                await h.recovery.recover(RunMode.REPLAY, bbo_for=h.bbo_for, now=h.clock.now())
        finally:
            h.recovery.state_service.transition = original
        async with SESSIONS() as session:
            crashed_control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return crashed_control, report, control

    crashed_control, report, control = asyncio.run(case())
    assert crashed_control.system_state == SystemState.SAFE_MODE.value
    assert crashed_control.payload["safe_mode_latch"] is True
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value


def test_fg_c_f05_case3_crash_after_starting():
    """F05 Case 3: STARTING durable commit -> crash -> fresh manager -> SAFE_MODE."""

    async def case():
        await _persist_safe_mode()
        h = Harness()
        h.quotes = {"SOL-USDT": (99.0, 100.0)}
        original = _crash_after(h.recovery.state_service, "recovery_start")
        try:
            with pytest.raises(RuntimeError, match="simulated_crash_after_recovery_start"):
                await h.recovery.recover(RunMode.REPLAY, bbo_for=h.bbo_for, now=h.clock.now())
        finally:
            h.recovery.state_service.transition = original
        async with SESSIONS() as session:
            crashed_control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return crashed_control, report, control

    crashed_control, report, control = asyncio.run(case())
    assert crashed_control.system_state == SystemState.STARTING.value
    assert crashed_control.payload["safe_mode_latch"] is True
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value


def test_fg_c_f05_case4_crash_after_recovering():
    """F05 Case 4: RECOVERING durable commit -> crash -> fresh manager -> SAFE_MODE."""

    async def case():
        await _persist_safe_mode()
        h = Harness()
        h.quotes = {"SOL-USDT": (99.0, 100.0)}
        original = _crash_after(h.recovery.state_service, "recovering")
        try:
            with pytest.raises(RuntimeError, match="simulated_crash_after_recovering"):
                await h.recovery.recover(RunMode.REPLAY, bbo_for=h.bbo_for, now=h.clock.now())
        finally:
            h.recovery.state_service.transition = original
        async with SESSIONS() as session:
            crashed_control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return crashed_control, report, control

    crashed_control, report, control = asyncio.run(case())
    assert crashed_control.system_state == SystemState.RECOVERING.value
    assert crashed_control.payload["safe_mode_latch"] is True
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value


def test_fg_c_f05_case5_successful_recovery_lands_safe_mode_then_restart():
    """F05 Case 5: recovery already landed SAFE_MODE -> new restart -> still SAFE_MODE."""

    async def case():
        await _persist_safe_mode()
        await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return report, control

    report, control = asyncio.run(case())
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value


def test_fg_c_f05_case6_safe_mode_recovery_clears_latch_no_stale_relatch():
    """F05 Case 6: safe_mode_recovery -> PAUSED -> latch cleared -> restart does NOT re-latch."""

    async def case():
        h = await _persist_safe_mode()
        # The position has a valid protection plan, so safe_mode_recovery can clear SAFE_MODE.
        outcome = await h.control.safe_mode_recovery(RunMode.REPLAY, now=h.clock.now())
        async with SESSIONS() as session:
            control_after = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        # New restart: the durable system_state is PAUSED and the latch was cleared, so recover
        # must NOT treat it as SAFE_MODE via a stale latch. (The STARTING/RECOVERING transitions
        # may still trip the pre-existing reconciliation check, but that is unrelated to the
        # latch: the latch itself must stay cleared.)
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            control = await session.scalar(
                select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RunMode.REPLAY)
            )
        return outcome, control_after, control

    outcome, control_after, control = asyncio.run(case())
    assert outcome.accepted and outcome.system_state is SystemState.PAUSED
    assert control_after.system_state == SystemState.PAUSED.value
    assert "safe_mode_latch" not in (control_after.payload or {})
    # The stale latch must not be re-written by the restart: payload stays latch-free.
    assert "safe_mode_latch" not in (control.payload or {})


async def _c01_three_way(quotes):
    """Return the three-way conclusion for the CURRENT durable OPEN LONG + plan state.

    - protection: `protection.evaluate()` reason
    - resume: pause then resume (walks `_open_position_protection_gate`)
    - recovery: fresh manager `recover()` final durable state
    """
    h = Harness()
    h.quotes = quotes
    protection = await h.protection.evaluate(
        RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
    )
    await h.control.pause(RunMode.REPLAY, "c01_gate")
    resume = await h.control.resume(RunMode.REPLAY)
    report, control = await _recover_landing(quotes)
    return protection, resume, report, control


async def _assert_three_way_invalid(quotes):
    protection, resume, report, control = await _c01_three_way(quotes)
    assert not protection.triggered and protection.reason == "POSITION_UNPROTECTED"
    # An OPEN position with no durable authority is refused by two independent detectors: the
    # resume gate's own protection check, and G4 reconciliation (invariant 13). Either may report
    # first, so both legitimate refusal reasons are accepted -- but a refusal is mandatory.
    assert not resume.accepted
    assert (
        resume.reason in ("POSITION_UNPROTECTED", "INCIDENT_POSITION_UNPROTECTED")
        or resume.reason.startswith("RECONCILIATION_FAILED")
    ), resume.reason
    assert report.final_system_state is SystemState.SAFE_MODE
    assert control.system_state == SystemState.SAFE_MODE.value
    return protection, resume, report, control


def test_fg_c_c01_case_a_valid_all_three_valid():
    """C01 Case A: valid plan -> protection HOLD, resume accepted, recovery RUNNING."""

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (99.0, 100.0)  # no trigger
        protection = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        await h.control.pause(RunMode.REPLAY, "c01")
        resume = await h.control.resume(RunMode.REPLAY)
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return protection, resume, report, control

    protection, resume, report, control = asyncio.run(case())
    assert protection.triggered is False and protection.reason == "HOLD"
    assert resume.accepted
    assert report.final_system_state is SystemState.RUNNING
    assert control.system_state == SystemState.RUNNING.value


def test_fg_c_c01_case_b_expired_plan_durable_snapshot_keeps_all_three_valid():
    """C01 Case B (superseded by N01-7-F01 Candidate A): an expired ACTIVE plan no longer leaves
    the OPEN LONG unprotected.

    Formerly `test_fg_c_c01_case_b_expired_all_three_invalid`, which asserted protection
    POSITION_UNPROTECTED / resume refused / recovery SAFE_MODE for an expired-but-otherwise-valid
    plan. That verdict is the defect Candidate A fixes: the plan TTL is the *risk-increasing*
    freshness authority and must never be the protection-lifetime authority. The position carries
    its own durable snapshot, so all three conclusions stay VALID after the planning window closes.

    The FG-C safeguard is deliberately preserved by making the carve-out TTL-only: a missing,
    corrupt, identity-inconsistent or business-invalid plan still fails closed to
    POSITION_UNPROTECTED (cases C / D / E / F below, unchanged).
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # Real TTL expiry (row + payload together), matching _expire_plan below.
        await _expire_plan(plan)
        async with SESSIONS() as session:
            expired_position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return plan, expired_position, await _c01_three_way({"SOL-USDT": (99.0, 100.0)})

    plan, expired_position, (protection, resume, report, control) = asyncio.run(case())
    # The durable snapshot still carries the originating plan's authority after the TTL expired.
    assert expired_position.quantity > 0
    assert expired_position.protection_plan_id == plan.plan_id
    assert expired_position.protection_plan_version == plan.plan_version
    assert expired_position.protection_stop_loss == plan.stop_loss
    assert expired_position.protection_take_profit == plan.take_profit
    assert expired_position.protection_updated_at is not None
    # All three conclusions are therefore VALID, exactly as for a live plan.
    assert protection.triggered is False and protection.reason == "HOLD"
    assert resume.accepted
    assert report.final_system_state is SystemState.RUNNING
    assert control.system_state == SystemState.RUNNING.value


def test_fg_c_c01_case_c_corrupt_payload_identity_all_three_invalid():
    """C01 Case C (re-based on Candidate A / N01-7-F01-R1): a corrupt plan payload can no longer
    un-protect an OPEN LONG.

    Under Candidate A the plan row is not a protection-lifetime authority, so plan corruption alone
    is not an unprotected-position condition. The original three-way fail-closed safeguard is
    preserved by exercising it on the state that genuinely justifies it: an OPEN position with no
    durable authority, with the corrupt plan row still present as context.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        corrupt = plan.model_dump(mode="json")
        corrupt["plan_id"] = "different-plan-id"
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=corrupt)
            )
        await _null_snapshot()
        return await _assert_three_way_invalid({"SOL-USDT": (99.0, 100.0)})

    asyncio.run(case())


def test_fg_c_c01_case_d_invalid_entry_zone_all_three_invalid():
    """C01 Case D (re-based on Candidate A): an invalid entry zone never formed a protection
    authority, so re-base the three-way safeguard on the absent durable authority."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        bad = plan.model_dump(mode="json")
        bad["entry_zone"] = {"lower": 120.0, "upper": 90.0}
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=bad)
            )
        await _null_snapshot()
        return await _assert_three_way_invalid({"SOL-USDT": (99.0, 100.0)})

    asyncio.run(case())


def test_fg_c_c01_case_e_invalid_stop_take_profit_all_three_invalid():
    """C01 Case E (re-based on Candidate A): an inverted SL/TP plan never formed a protection
    authority, so re-base the three-way safeguard on the absent durable authority."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        bad = plan.model_dump(mode="json")
        bad["stop_loss"] = 140.0
        bad["take_profit"] = 80.0
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(payload=bad)
            )
        await _null_snapshot()
        return await _assert_three_way_invalid({"SOL-USDT": (99.0, 100.0)})

    asyncio.run(case())


def test_fg_c_c01_case_f_no_active_plan_fail_closed():
    """C01 Case F (re-based on Candidate A): 'no unique ACTIVE plan' is a risk-increasing
    freshness condition, not a protection-lifetime one.

    Multiple ACTIVE rows are already impossible at the DB level via `uq_trade_plans_one_active`;
    this case exercises the remaining "no unique valid active plan" path, which must fail closed
    for a position that carries no durable authority of its own.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(status=PlanStatus.REPLACED)
            )
        await _null_snapshot()
        return await _assert_three_way_invalid({"SOL-USDT": (99.0, 100.0)})

    asyncio.run(case())


def test_fg_c_c01_case_g_natural_state_version_advance_still_valid():
    """C01 Case G (review correction): natural SymbolStateStore version advancement must NOT
    invalidate open-position protection. plan.state_version=7, store advances to 8 via normal
    market evolution -> protection HOLD, resume accepted, and recovery RUNNING while the position
    remains OPEN throughout all three checks.
    """

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        # Natural symbol-state version advancement (NOT a block): store moves 7 -> 8 while the
        # open position's plan stays pinned to state_version 7.
        async with SESSIONS() as session, session.begin():
            await session.merge(
                SymbolStateStore(
                    instrument_id="SOL-USDT",
                    symbol="SOL-USDT",
                    state="ACTIVE",
                    state_version=8,
                )
            )
        # Protection: a fresh, non-triggering BBO must HOLD despite version advancement.
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        protection = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        async with SESSIONS() as session:
            position_after_protection = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            trade_after_protection = await session.scalar(
                select(TradeRecord).where(TradeRecord.trade_id == position_after_protection.trade_id)
            )
        # Resume: the protection gate must accept the still-open position.
        await h.control.pause(RunMode.REPLAY, "c01_g")
        resume = await h.control.resume(RunMode.REPLAY)
        # Recovery uses a fresh Harness/RecoveryManager and must preserve that open position.
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        async with SESSIONS() as session:
            position_after_recovery = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            trade_after_recovery = await session.scalar(
                select(TradeRecord).where(TradeRecord.trade_id == position_after_recovery.trade_id)
            )
        return (
            protection,
            position_after_protection,
            trade_after_protection,
            resume,
            report,
            control,
            position_after_recovery,
            trade_after_recovery,
        )

    (
        protection,
        position_after_protection,
        trade_after_protection,
        resume,
        report,
        control,
        position_after_recovery,
        trade_after_recovery,
    ) = asyncio.run(case())
    assert protection.triggered is False
    assert protection.reason == "HOLD"
    assert position_after_protection.quantity > 0
    assert trade_after_protection.status == "OPEN"
    assert resume.accepted
    assert report.final_system_state is SystemState.RUNNING
    assert control.system_state == SystemState.RUNNING.value
    assert position_after_recovery.quantity > 0
    assert trade_after_recovery.status == "OPEN"


def test_fg_c_c01_case_h_stale_risk_increasing_buy_rejected():
    """C01 Case H (separate contract): stale risk-increasing BUY authority is still rejected by
    the existing G3 fill-time guard / recovery order revalidation, independent of protection.

    A pending BUY whose plan.state_version is behind the current SymbolStateStore version must
    be cancelled by recovery order revalidation (state_version_stale), while the open position's
    protection stays valid.
    """

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        add_plan = await open_limit_buy(h, notional=20, limit=95, version=7)
        # Advance the symbol authority so the pending ADD's plan is stale (risk-increasing).
        async with SESSIONS() as session, session.begin():
            await session.merge(
                SymbolStateStore(
                    instrument_id="SOL-USDT",
                    symbol="SOL-USDT",
                    state="ACTIVE",
                    state_version=8,
                )
            )
        # Fresh recovery: the stale BUY must be cancelled, position protection must remain valid.
        h2 = Harness()
        h2.quotes = {"SOL-USDT": (99.0, 100.0)}
        report = await h2.recovery.recover(RunMode.REPLAY, bbo_for=h2.bbo_for, now=h2.clock.now())
        async with SESSIONS() as session:
            add_order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.plan_id == add_plan.plan_id)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return report, add_order, position

    report, add_order, position = asyncio.run(case())
    assert add_order.status == OrderStatus.CANCELLED  # stale risk-increasing BUY rejected
    # The open position is still protected (version advancement did not invalidate protection),
    # so recovery lands RUNNING with the position intact.
    assert report.final_system_state is SystemState.RUNNING
    assert position.quantity > 0


# ---------------------------------------------------------------------------------------
# N01-7-F01 / N01-7-F01-R1 -- durable OPEN-position protection snapshot (Candidate A)
#
# Contract: an OPEN LONG keeps its stop-loss / take-profit authority independently of the
# originating TradePlan TTL. G3 settlement persists that authority on the `positions` row inside
# the fill's economic transaction, and every G4 consumer reads it back through the single shared
# resolver `marketpulse.g4.planning.resolve_open_position_protection`. The plan therefore stays
# only the authority *source*; the position owns the durability.
#
# N01-7-F01-R1 (fast follow) removes the last plan-first carve-out. The durable snapshot is now the
# *sole* protection-lifetime authority: a merely valid ACTIVE TradePlan can never override,
# replace or unprotect it, and plan TTL expiry is not a protection-lifetime event. The verdicts
# that used to be driven by the plan row are therefore re-based on the condition that actually
# justifies them -- the absence, or corruption, of the position's own durable authority:
#
#   * no durable authority            -> POSITION_UNPROTECTED, SAFE_MODE, resume refused (F01-13,
#                                        F01-21, F01-R1-05);
#   * a legacy pre-migration position -> converted once, deterministically, by migration
#                                        `20260912_0006` (CASE B) and never re-derived at runtime.
#
# F01-R1 additionally pins the two ACTIVE-plan mutation classes (F01-R1-01 / F01-R1-02: activating a
# new plan must not move the authority) and the economic exit identity (F01-R1-03 / F01-R1-04:
# unique per trade lifecycle, never the degenerate `plan_id="" / plan_version=0` pair).
# ---------------------------------------------------------------------------------------


async def _position_row(instrument: str = "SOL-USDT") -> PositionRecord:
    async with SESSIONS() as session:
        return await session.scalar(
            select(PositionRecord).where(
                PositionRecord.run_mode == RunMode.REPLAY,
                PositionRecord.instrument_id == instrument,
            )
        )


async def _open_incident(instrument: str = "SOL-USDT") -> IncidentRecord | None:
    """The latest durable POSITION_UNPROTECTED incident for the instrument, or None."""
    async with SESSIONS() as session:
        return await session.scalar(
            select(IncidentRecord)
            .where(
                IncidentRecord.run_mode == RunMode.REPLAY,
                IncidentRecord.instrument_id == instrument,
                IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED,
            )
            .order_by(IncidentRecord.opened_at.desc(), IncidentRecord.incident_id.desc())
        )


async def _expire_plan(plan: TradePlan) -> None:
    """Close the plan's planning window for real: the durable row *and* its serialized payload.

    `load_active_plan` reads a row whose payload disagrees with its columns as corrupt, which is a
    different (and still fail-closed) case from TTL expiry. An elapsed planning window moves
    `expires_at` in both places, so this is what puts the TTL carve-out on the code path under test.
    """
    expires_at = NOW - timedelta(seconds=1)
    payload = plan.model_dump(mode="json")
    payload["expires_at"] = expires_at.isoformat()
    async with SESSIONS() as session, session.begin():
        await session.execute(
            update(TradePlanRecord)
            .where(TradePlanRecord.plan_id == plan.plan_id)
            .values(expires_at=expires_at, payload=payload)
        )


async def _null_snapshot(instrument: str = "SOL-USDT") -> None:
    """Remove the durable authority while leaving the position itself OPEN."""
    async with SESSIONS() as session, session.begin():
        await session.execute(
            update(PositionRecord)
            .where(
                PositionRecord.run_mode == RunMode.REPLAY,
                PositionRecord.instrument_id == instrument,
            )
            .values(
                protection_plan_id=None,
                protection_plan_version=None,
                protection_stop_loss=None,
                protection_take_profit=None,
                protection_updated_at=None,
            )
        )


async def _restore_snapshot(authority: TradePlan, instrument: str = "SOL-USDT") -> None:
    """Restore the durable authority of `authority` onto the OPEN position row.

    Candidate A makes the position snapshot the only durable protection fact, so a test that needs
    the authority to come *back* must write it back here; there is no plan-side state that would
    revive it.
    """
    async with SESSIONS() as session, session.begin():
        await session.execute(
            update(PositionRecord)
            .where(
                PositionRecord.run_mode == RunMode.REPLAY,
                PositionRecord.instrument_id == instrument,
            )
            .values(
                protection_plan_id=authority.plan_id,
                protection_plan_version=authority.plan_version,
                protection_stop_loss=authority.stop_loss,
                protection_take_profit=authority.take_profit,
                protection_updated_at=NOW,
            )
        )


async def _mutate_plan_then_evaluate(mutate) -> tuple[PositionRecord, object]:
    """Open a protected LONG, mutate its durable plan, then ask protection for a verdict."""
    h = Harness()
    await h.boot()
    plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
    await mutate(plan)
    h.quotes["SOL-USDT"] = (99.0, 100.0)  # a non-triggering quote for every valid authority
    outcome = await h.protection.evaluate(
        RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
    )
    return await _position_row(), outcome


def _assert_snapshot_is(position: PositionRecord, authority: TradePlan) -> None:
    """The durable snapshot carries exactly the authority of `authority`."""
    assert position.protection_plan_id == authority.plan_id
    assert position.protection_plan_version == authority.plan_version
    assert position.protection_stop_loss == authority.stop_loss
    assert position.protection_take_profit == authority.take_profit
    assert position.protection_updated_at is not None


def _assert_snapshot_cleared(position: PositionRecord) -> None:
    assert position.protection_plan_id is None
    assert position.protection_plan_version is None
    assert position.protection_stop_loss is None
    assert position.protection_take_profit is None
    assert position.protection_updated_at is None


def _untracked_position(**overrides) -> PositionRecord:
    """A transient PositionRecord carrying a complete, legal durable snapshot."""
    values = {
        "position_id": "pos-unit-f01",
        "run_mode": RunMode.REPLAY,
        "instrument_id": "SOL-USDT",
        "quantity": 1.0,
        "average_cost": 100.0,
        "realized_pnl": 0.0,
        "trade_id": "trade-unit-f01",
        "updated_at": NOW,
        "protection_plan_id": "plan-unit-f01",
        "protection_plan_version": 1,
        "protection_stop_loss": 80.0,
        "protection_take_profit": 140.0,
        "protection_updated_at": NOW,
    }
    values.update(overrides)
    return PositionRecord(**values)


def test_f01_01_market_buy_fill_persists_the_durable_protection_snapshot():
    """F01-01: the risk-increasing market fill that opens the position writes the authority."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        return plan, await _position_row()

    plan, position = asyncio.run(case())
    assert position.quantity > 0
    _assert_snapshot_is(position, plan)
    # Written inside the fill's own economic transaction, at the fill time.
    assert position.protection_updated_at == NOW


def test_f01_02_limit_buy_fill_persists_the_durable_protection_snapshot():
    """F01-02: the limit-fill path (which re-validates the plan at fill time) writes it too."""

    async def case():
        h = Harness()
        await h.boot()
        plan = await open_limit_buy(h, notional=10, limit=95)
        h.quotes["SOL-USDT"] = (94.0, 95.0)  # ask 95 <= limit 95 -> eligible fill
        fills = await h.execution.process_open_orders(
            RunMode.REPLAY, await h.bbo_for("SOL-USDT"), NOW
        )
        return plan, fills, await _position_row()

    plan, fills, position = asyncio.run(case())
    assert [result.status for result in fills] == [IntentStatus.EXECUTED]
    assert position.quantity > 0
    _assert_snapshot_is(position, plan)


def test_f01_03_partial_reduce_keeps_the_durable_protection_snapshot():
    """F01-03: a partial risk-reducing exit must not drop the residual position's authority."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        quantity_before = (await _position_row()).quantity
        outcome = await h.protection.risk_reducing_exit(
            RunMode.REPLAY,
            "SOL-USDT",
            await h.bbo_for("SOL-USDT"),
            exit_reason=ExitReason.AI_REDUCE,
            event_type=PositionEventType.REDUCE,
            quantity=0.2,
            now=NOW,
        )
        return plan, quantity_before, outcome, await _position_row()

    plan, quantity_before, outcome, position = asyncio.run(case())
    assert outcome.triggered
    assert 0 < position.quantity < quantity_before
    _assert_snapshot_is(position, plan)


def test_f01_04_full_close_clears_the_durable_protection_snapshot():
    """F01-04: the snapshot must never outlive the position it protects."""

    async def case():
        h = Harness()
        await h.boot()
        await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return outcome, await _position_row()

    outcome, position = asyncio.run(case())
    assert outcome.triggered is True and outcome.exit_reason is ExitReason.STOP_LOSS
    assert position.quantity == 0.0
    _assert_snapshot_cleared(position)


def test_f01_05_plan_ttl_expiry_leaves_the_durable_snapshot_unchanged():
    """F01-05: TTL expiry is not a write. The authority survives the planning window verbatim."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        before = await _position_row()
        await _expire_plan(plan)
        return plan, before, await _position_row()

    plan, before, after = asyncio.run(case())
    _assert_snapshot_is(before, plan)
    _assert_snapshot_is(after, plan)
    assert after.protection_updated_at == before.protection_updated_at


def test_f01_06_expired_plan_still_holds_and_opens_no_unprotected_incident():
    """F01-06: an expired plan with a durable snapshot is protected, not unprotected."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return outcome, await _open_incident()

    outcome, incident = asyncio.run(case())
    assert outcome.triggered is False and outcome.reason == "HOLD"
    assert incident is None


def test_f01_07_expired_plan_still_triggers_stop_loss_and_closes():
    """F01-07: the stop-loss the plan installed keeps working after the plan TTL expires."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        position = await _position_row()
        async with SESSIONS() as session:
            trade = await session.scalar(
                select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
            )
            close_events = list(
                (
                    await session.scalars(
                        select(PositionEventRecord).where(
                            PositionEventRecord.run_mode == RunMode.REPLAY,
                            PositionEventRecord.event_type == PositionEventType.CLOSE,
                        )
                    )
                ).all()
            )
        return plan, outcome, position, trade, close_events

    plan, outcome, position, trade, close_events = asyncio.run(case())
    assert outcome.triggered is True and outcome.exit_reason is ExitReason.STOP_LOSS
    assert outcome.fill_id is not None
    assert position.quantity == 0.0
    _assert_snapshot_cleared(position)
    assert trade.status == "CLOSED" and trade.exit_reason == "STOP_LOSS"
    # The exit is attributed to the authority that actually protected the position, not to an
    # empty plan identity that no longer exists.
    assert [event.plan_id for event in close_events] == [plan.plan_id]


def test_f01_08_expired_plan_still_triggers_take_profit_and_closes():
    """F01-08: the same holds for the take-profit side."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        h.quotes["SOL-USDT"] = (140.0, 141.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return outcome, await _position_row()

    outcome, position = asyncio.run(case())
    assert outcome.triggered is True and outcome.exit_reason is ExitReason.TAKE_PROFIT
    assert position.quantity == 0.0
    _assert_snapshot_cleared(position)


def test_f01_09_expired_plan_still_allows_resume():
    """F01-09: the resume protection gate accepts an OPEN LONG protected only by its snapshot."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        paused = await h.control.pause(RunMode.REPLAY, "f01_09")
        resume = await h.control.resume(RunMode.REPLAY)
        return paused, resume

    paused, resume = asyncio.run(case())
    assert paused.accepted
    assert resume.accepted, resume.reason
    assert resume.system_state is SystemState.RUNNING


def test_f01_10_expired_plan_still_recovers_to_running():
    """F01-10: a fresh restart must not degrade the runtime because the plan TTL elapsed."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        report, control = await _recover_landing({"SOL-USDT": (99.0, 100.0)})
        return report, control, await _position_row()

    report, control, position = asyncio.run(case())
    assert report.final_system_state is SystemState.RUNNING, report.reason
    assert control.system_state == SystemState.RUNNING.value
    assert position.quantity > 0


def test_f01_11_reconciliation_accepts_an_expired_plan_with_a_durable_snapshot():
    """F01-11: invariant 13 must not fire while the durable authority is present."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        return await h.reconcile(RunMode.REPLAY)

    report = asyncio.run(case())
    assert report.invariants["open_position_protection_survives_plan_ttl"] is True
    assert "open_position_unprotected_after_plan_ttl" not in report.diagnostics
    assert report.ok is True, report.diagnostics


def test_f01_12_reconciliation_flags_an_open_position_without_a_durable_authority():
    """F01-12 (re-based on N01-7-F01-R1): invariant 13 must fire when nothing protects the LONG.

    The invariant consumes the canonical durable-position contract directly, so its finding is the
    position that has no authority -- an expired ACTIVE plan is no longer part of the verdict and
    therefore no longer appears in the finding detail.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        await _null_snapshot()
        return await h.reconcile(RunMode.REPLAY)

    report = asyncio.run(case())
    assert report.invariants["open_position_protection_survives_plan_ttl"] is False
    assert "open_position_unprotected_after_plan_ttl" in report.diagnostics
    assert report.ok is False
    assert report.details["ttl_unprotected_positions"] == [
        {"instrument_id": "SOL-USDT", "reason": "NO_DURABLE_AUTHORITY"}
    ]


def test_f01_13_missing_durable_snapshot_still_fails_closed_to_unprotected():
    """F01-13: no snapshot -> POSITION_UNPROTECTED and the official incident, never a guess."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        await _null_snapshot()
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return outcome, await _open_incident()

    outcome, incident = asyncio.run(case())
    assert outcome.triggered is False and outcome.reason == "POSITION_UNPROTECTED"
    assert incident is not None
    assert incident.status == IncidentStatus.OPEN.value
    assert incident.reason == "open_position_without_durable_protection"


def test_f01_14_superseded_plan_row_cannot_unprotect_a_durable_snapshot():
    """F01-14 (flipped by N01-7-F01-R1): the durable snapshot decides, not the ACTIVE plan row.

    Formerly `test_f01_14_replaced_active_plan_still_fails_closed_even_with_a_snapshot`, which
    relied on the plan-first carve-out this fast follow removes. Candidate A forbids exactly that:
    a plan row whose ACTIVE status changed without atomically moving the snapshot must not change
    live protection. The fail-closed counterpart -- an OPEN position with *no* durable authority --
    stays covered by F01-13 / F01-21 / F01-R1-04 / F01-R1-05.
    """

    async def case():
        async def mutate(plan):
            async with SESSIONS() as session, session.begin():
                await session.execute(
                    update(TradePlanRecord)
                    .where(TradePlanRecord.plan_id == plan.plan_id)
                    .values(status=PlanStatus.REPLACED)
                )

        return await _mutate_plan_then_evaluate(mutate)

    position, outcome = asyncio.run(case())
    assert position.protection_plan_id is not None  # the snapshot is intact...
    assert outcome.triggered is False and outcome.reason == "HOLD"  # ...and therefore authoritative


def test_f01_15_corrupt_plan_payload_cannot_unprotect_a_durable_snapshot():
    """F01-15 (flipped by N01-7-F01-R1): identity-inconsistent plan payload is a plan defect.

    Formerly `..._corrupt_plan_payload_identity_still_fails_closed_with_a_snapshot`. Since the plan
    row is no longer a protection-lifetime authority, its corruption cannot disable a stop-loss the
    position already carries. The position's own corruption still fails closed (F01-21).
    """

    async def case():
        async def mutate(plan):
            corrupt = plan.model_dump(mode="json")
            corrupt["plan_id"] = "different-plan-id"
            async with SESSIONS() as session, session.begin():
                await session.execute(
                    update(TradePlanRecord)
                    .where(TradePlanRecord.plan_id == plan.plan_id)
                    .values(payload=corrupt)
                )

        return await _mutate_plan_then_evaluate(mutate)

    position, outcome = asyncio.run(case())
    assert position.protection_plan_id is not None
    assert outcome.triggered is False and outcome.reason == "HOLD"


def test_f01_16_business_invalid_plan_levels_cannot_unprotect_a_durable_snapshot():
    """F01-16 (flipped by N01-7-F01-R1): a plan whose own SL/TP relationship is broken is a plan
    defect too, and cannot retroactively invalidate an authority already committed to the position.

    Formerly `..._business_invalid_plan_levels_still_fails_closed_with_a_snapshot`. A position that
    was opened by a plan which could not form an authority never gets a snapshot in the first place
    and is therefore already POSITION_UNPROTECTED (F01-13).
    """

    async def case():
        async def mutate(plan):
            bad = plan.model_dump(mode="json")
            bad["stop_loss"] = 140.0
            bad["take_profit"] = 80.0
            async with SESSIONS() as session, session.begin():
                await session.execute(
                    update(TradePlanRecord)
                    .where(TradePlanRecord.plan_id == plan.plan_id)
                    .values(payload=bad)
                )

        return await _mutate_plan_then_evaluate(mutate)

    position, outcome = asyncio.run(case())
    assert position.protection_plan_id is not None
    assert outcome.triggered is False and outcome.reason == "HOLD"


def test_f01_17_state_version_advance_keeps_the_durable_snapshot_authority():
    """F01-17: symbol-state advancement is risk-increasing freshness, never protection lifetime."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        async with SESSIONS() as session, session.begin():
            await session.merge(
                SymbolStateStore(
                    instrument_id="SOL-USDT",
                    symbol="SOL-USDT",
                    state="ACTIVE",
                    state_version=8,
                )
            )
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return plan, outcome, await _position_row()

    plan, outcome, position = asyncio.run(case())
    assert outcome.triggered is False and outcome.reason == "HOLD"
    _assert_snapshot_is(position, plan)


def test_f01_18_plan_replacement_moves_the_durable_snapshot_to_the_new_version():
    """F01-18: a superseding plan version becomes the position's authority immediately."""

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        next_plan = derive_followup_plan(plan, now=NOW, plan_version=2, stop_loss=85.0)
        replaced, _ = await h.plans.replace(previous=plan, next_plan=next_plan, now=NOW)
        return plan, replaced, await _position_row()

    plan, next_plan, position = asyncio.run(case())
    assert next_plan.plan_id != plan.plan_id
    _assert_snapshot_is(position, next_plan)
    assert position.protection_stop_loss == 85.0


def test_f01_19_plan_replacement_without_a_legal_authority_clears_the_snapshot():
    """F01-19: a replacement that cannot form a legal authority clears it instead of going stale.

    The new stop (200) sits above the take-profit (140) and above the mark (bid 99), so leaving the
    superseded level live would make protection trigger on a level no accepted plan ever had.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        broken = derive_followup_plan(plan, now=NOW, plan_version=2, stop_loss=200.0)
        await h.plans.replace(previous=plan, next_plan=broken, now=NOW)
        h.quotes["SOL-USDT"] = (99.0, 100.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return broken, outcome, await _position_row()

    broken, outcome, position = asyncio.run(case())
    assert broken.stop_loss >= broken.take_profit
    _assert_snapshot_cleared(position)
    assert outcome.triggered is False and outcome.reason == "POSITION_UNPROTECTED"


def test_f01_20_authority_from_plan_never_raises_and_matches_the_plan_contract():
    """F01-20: acceptance is exactly the executable-plan contract, never stricter, never a raise."""

    assert authority_from_plan(make_plan("SOL-USDT", stop=80, tp=140)) is not None
    # Inverted or non-finite levels cannot form an authority; None is the fail-closed answer.
    assert authority_from_plan(make_plan("SOL-USDT", stop=140.0, tp=80.0)) is None
    assert authority_from_plan(make_plan("SOL-USDT", stop=float("nan"))) is None
    assert authority_from_plan(make_plan("SOL-USDT", tp=float("inf"))) is None
    # No positivity rule exists in the frozen contract: an ordered zero/negative pair is legal.
    non_positive = authority_from_plan(make_plan("SOL-USDT", stop=-10.0, tp=0.0))
    assert non_positive is not None
    assert (non_positive.stop_loss, non_positive.take_profit) == (-10.0, 0.0)


def test_f01_21_read_position_protection_fails_closed_on_a_partial_snapshot():
    """F01-21: a half-written, inverted or non-finite durable snapshot is corruption, not trust."""

    complete = read_position_protection(_untracked_position())
    assert complete is not None and complete.stop_loss == 80.0
    for column in (
        "protection_plan_id",
        "protection_plan_version",
        "protection_stop_loss",
        "protection_take_profit",
        "protection_updated_at",
    ):
        assert read_position_protection(_untracked_position(**{column: None})) is None
    assert (
        read_position_protection(
            _untracked_position(protection_stop_loss=140.0, protection_take_profit=80.0)
        )
        is None
    )
    assert read_position_protection(_untracked_position(protection_stop_loss=float("nan"))) is None


def test_f01_22_failed_protective_exit_does_not_clear_the_durable_snapshot():
    """F01-22: the snapshot clear lives in the settlement transaction, so a failed exit keeps it.

    Fix AC #2: a full close clears the durable authority inside the same transaction that writes
    the protective fill. If that fill fails and rolls back, the OPEN position must keep the exact
    authority it held before the attempt — a half-cleared snapshot would silently un-protect it.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        h.execution.after_settlement = lambda: (_ for _ in ()).throw(RuntimeError("injected"))
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        with pytest.raises(RuntimeError):
            await h.protection.evaluate(
                RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
            )
        h.execution.after_settlement = None
        return plan, await _position_row()

    plan, position = asyncio.run(case())
    assert position.quantity > 0
    _assert_snapshot_is(position, plan)


def test_f01_23_manual_close_remains_available_when_unprotected():
    """F01-23: an unprotected OPEN LONG can still be closed manually with a fresh BBO.

    Fix AC #9: a missing snapshot fails closed for automatic protection and for risk-increasing
    actions, but the operator's explicit risk-reducing full close must not be refused.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        await _expire_plan(plan)
        await _null_snapshot()
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

    outcome, trade, position = asyncio.run(case())
    assert outcome.triggered is True and outcome.exit_reason is ExitReason.MANUAL_CLOSE
    assert position.quantity == 0.0
    _assert_snapshot_cleared(position)
    assert trade.exit_reason == ExitReason.MANUAL_CLOSE.value


# ==============================================================================
# N01-7-F01-R1 section 6 -- every production path that can create or change an ACTIVE TradePlan
# ==============================================================================
#
# Complete audit of the write paths for `trade_plans.status = 'ACTIVE'`:
#
#   1. `marketpulse.g3.service.persist_trade_plan` (reached from `G3Workflow.process_setup`):
#      replaces the symbol's ACTIVE row and inserts the new one. It never reads or writes
#      `positions`, so by construction it cannot move the protection authority. Per Candidate A a
#      newly ACTIVE plan is a risk-increasing *proposal*, not a protection contract, so this is the
#      correct behaviour -- but it is the one path that could silently re-protect an OPEN position
#      if it ever grew a snapshot write. F01-R1-01 / F01-R1-02 pin it.
#   2. `marketpulse.g4.planning.PlanManager._replace_in` (reached from `PlanManager.replace`, the
#      G4 reevaluation UPDATE_STOP / UPDATE_TP / REPLACE_PLAN actions and the recovery replay
#      path): atomically supersedes the plan *and* moves the OPEN position's snapshot in the same
#      transaction -- `apply_position_protection` for a legal successor, `clear_position_protection`
#      when the successor cannot yield one. F01-18 / F01-19 pin both branches.
#
# There is no third path: `TradePlanManager.from_analysis` only mutates an in-memory dict, `g4` has
# no other INSERT/UPDATE against `trade_plans`, and the partial unique index
# `uq_trade_plans_one_active` keeps "one ACTIVE plan per symbol" true at the schema level.
# ---------------------------------------------------------------------------------------


def _g3_analysis(
    *,
    stop: float = 80.0,
    tp: float = 140.0,
    entry_lower: float = 90.0,
    entry_upper: float = 120.0,
) -> AIAnalysis:
    """A business-valid LONG analysis: `stop < entry_lower <= entry_upper < take_profit`."""
    return AIAnalysis(
        direction=Direction.LONG_BIAS,
        trends={"5m": "UP", "15m": "UP", "1H": "UP", "4H": "UP", "1D": "UP"},
        confidence=0.8,
        suggested_position_pct=0.15,
        reason="fixture",
        entry_zone=PriceZone(lower=entry_lower, upper=entry_upper),
        stop_loss=stop,
        take_profit=tp,
        invalidation="breaks 80",
        main_plan="buy a confirmed setup",
    )


def _g3_snapshot(state_version: int = 7):
    state = SymbolStateRecord(
        instrument_id="SOL-USDT",
        symbol="SOL-USDT",
        state=SymbolState.SETUP,
        state_version=state_version,
    )
    features = FeatureSnapshot(
        instrument_id="SOL-USDT",
        symbol="SOL-USDT",
        market_type=MarketType.SPOT,
        event_time=NOW,
        current_price=100,
    )
    bbo = BestBidAsk(instrument_id="SOL-USDT", bid=99, ask=100, received_at=NOW)
    return DecisionSnapshotBuilder().build(
        run_mode=RunMode.REPLAY,
        state=state,
        features=features,
        bbo=bbo,
        candidates=[],
        timeline=[{"event_id": "evt"}],
        config_version="fixture",
        trading_context={"current_position": None, "open_orders": []},
        now=NOW,
    )


async def _current_state_version(_instrument: str) -> int:
    return 7


async def _run_g3_setup(
    *,
    stop: float,
    tp: float,
    entry_lower: float = 90.0,
    entry_upper: float = 120.0,
    equity: float = 1_000.0,
):
    """Drive the real G3 SETUP hand-off, which persists a fresh ACTIVE plan for the symbol."""
    workflow = G3Workflow(
        DecisionService(
            SESSIONS,
            DeterministicFakeAIProvider(
                _g3_analysis(stop=stop, tp=tp, entry_lower=entry_lower, entry_upper=entry_upper)
            ),
            model="r1-fixture",
        ),
        TradePlanManager(clock=FixedClock()),
        SESSIONS,
    )
    return await workflow.process_setup(_g3_snapshot(), _current_state_version, equity)


async def _active_plan_row(instrument: str = "SOL-USDT") -> TradePlanRecord | None:
    async with SESSIONS() as session:
        return await session.scalar(
            select(TradePlanRecord).where(
                TradePlanRecord.run_mode == RunMode.REPLAY,
                TradePlanRecord.instrument_id == instrument,
                TradePlanRecord.status == PlanStatus.ACTIVE,
            )
        )


async def _sell_orders(instrument: str = "SOL-USDT") -> list[PaperOrderRecord]:
    """Every risk-reducing SELL order, in a deterministic order that does not depend on heap order."""
    async with SESSIONS() as session:
        return list(
            (
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(
                        PaperOrderRecord.run_mode == RunMode.REPLAY,
                        PaperOrderRecord.instrument_id == instrument,
                        PaperOrderRecord.side == OrderSide.SELL,
                    )
                    .order_by(PaperOrderRecord.created_at, PaperOrderRecord.order_id)
                )
            ).all()
        )


async def _trades(instrument: str = "SOL-USDT") -> list[TradeRecord]:
    async with SESSIONS() as session:
        return list(
            (
                await session.scalars(
                    select(TradeRecord)
                    .where(
                        TradeRecord.run_mode == RunMode.REPLAY,
                        TradeRecord.instrument_id == instrument,
                    )
                    .order_by(TradeRecord.opened_at, TradeRecord.trade_id)
                )
            ).all()
        )


def test_f01_r1_01_g3_setup_activates_a_new_plan_without_becoming_the_protection_authority():
    """F01-R1-01 (§6): the G3 SETUP hand-off can persist a new ACTIVE plan while a position is OPEN.

    Candidate A: the plan is only ever the authority *source*, and it becomes authority solely by
    being atomically committed onto the position row. The G3 write path never touches `positions`,
    so activating a brand-new plan next to an OPEN LONG must leave the durable snapshot exactly as
    it was. The first assertion group proves the test can actually fail: the new plan really is the
    persisted ACTIVE row, with a different stop (95) than the snapshot (80).
    """

    async def case():
        h = Harness()
        await h.boot()
        opened, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        status, activated = await _run_g3_setup(stop=95.0, tp=140.0, entry_lower=100.0, entry_upper=110.0)
        return opened, status, activated, await _active_plan_row(), await _position_row()

    opened, status, activated, row, position = asyncio.run(case())
    assert status is DecisionStatus.VALID
    assert activated is not None and activated.plan_id != opened.plan_id
    assert row is not None and row.plan_id == activated.plan_id  # the new plan IS the ACTIVE one
    assert row.payload["stop_loss"] == 95.0
    assert row.payload["plan_version"] == 1
    # ...and the OPEN position still carries the plan it was opened with, not the newly ACTIVE one.
    _assert_snapshot_is(position, opened)
    assert position.protection_stop_loss == 80.0


def test_f01_r1_02_live_protection_still_follows_the_snapshot_after_a_new_plan_is_activated():
    """F01-R1-02 (§6): the live verdict follows the snapshot level, not the newly ACTIVE plan's.

    A bid of 90 sits below the new plan's stop (95) but above the snapshot's stop (80). If the
    merely-valid new plan could acquire protection authority, this would trigger a STOP_LOSS and
    close the position; the snapshot being the sole authority means the position holds.
    """

    async def case():
        h = Harness()
        await h.boot()
        opened, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        status, activated = await _run_g3_setup(stop=95.0, tp=140.0, entry_lower=100.0, entry_upper=110.0)
        assert status is DecisionStatus.VALID and activated is not None
        h.quotes["SOL-USDT"] = (90.0, 91.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return opened, activated, outcome, await _position_row()

    opened, activated, outcome, position = asyncio.run(case())
    assert activated.stop_loss == 95.0  # the newly ACTIVE plan's stop
    assert opened.stop_loss == 80.0  # the durable snapshot's stop
    # The quote below (bid 90) sits strictly between the two, so it discriminates them.
    assert outcome.triggered is False and outcome.reason == "HOLD"
    assert position.quantity > 0
    _assert_snapshot_is(position, opened)


def test_f01_r1_03_unprotected_full_closes_stay_unique_across_trade_lifecycles():
    """F01-R1-03 (§7): two *unprotected* full closes on one symbol, in two successive trade
    lifecycles, must be two distinct economic events.

    Before R1 the unprotected fallback identity was the degenerate pair `plan_id="" /
    plan_version=0`, so lifecycle B hashed to lifecycle A's intent. The G3 exit path finds the
    existing order, answers `duplicate_intent` and returns *without settling* -- `_close_position_in`
    then reports `triggered=True` while the position is still open, i.e. a silent no-op wearing the
    outcome of a success. The identity now carries `position_id` + `trade_id` + `exit_reason` +
    `quantity`, so each lifecycle closes for real.
    """

    async def case():
        h = Harness()
        await h.boot()
        outcomes, positions = [], []
        for _ in range(2):
            await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
            await _null_snapshot()
            h.quotes["SOL-USDT"] = (98.0, 99.0)
            outcomes.append(
                await h.control.manual_close(
                    RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
                )
            )
            positions.append(await _position_row())
        return outcomes, positions, await _sell_orders(), await _trades()

    outcomes, positions, orders, trades = asyncio.run(case())
    assert [outcome.triggered for outcome in outcomes] == [True, True]
    assert [outcome.exit_reason for outcome in outcomes] == [
        ExitReason.MANUAL_CLOSE,
        ExitReason.MANUAL_CLOSE,
    ]
    # Two distinct opening trades, both closed by their own lifecycle.
    assert len(trades) == 2
    assert len({trade.trade_id for trade in trades}) == 2
    assert [trade.status for trade in trades] == ["CLOSED", "CLOSED"]
    assert all(trade.exit_reason == ExitReason.MANUAL_CLOSE.value for trade in trades)

    # Two SELL orders, two identities -- and the identity is a pure function of the lifecycle.
    assert len(orders) == 2
    observed = [order.intent_id for order in orders]
    assert len(set(observed)) == 2
    expected = {
        stable_id(
            "exit",
            RunMode.REPLAY,
            "SOL-USDT",
            positions[0].position_id,
            trade.trade_id,
            ExitReason.MANUAL_CLOSE,
            orders[0].quantity,
        )
        for trade in trades
    }
    assert set(observed) == expected
    # The legacy degenerate identity must not reappear: it would collide the two lifecycles again.
    legacy = stable_id(
        "exit", RunMode.REPLAY, "SOL-USDT", "", 0, ExitReason.MANUAL_CLOSE, orders[0].quantity
    )
    assert legacy not in observed
    # The decisive evidence: both positions really reached flat. A `duplicate_intent` no-op would
    # have left the second one OPEN while still reporting `triggered=True` above.
    assert [position.quantity for position in positions] == [0.0, 0.0]


def test_f01_r1_04_protected_exit_identity_carries_the_authority_and_the_trade_lifecycle():
    """F01-R1-04 (§7): a protected exit is identified by the durable authority plus its lifecycle.

    The identity must include `trade_id`, `plan_id`, `plan_version`, `exit_reason` and `quantity`,
    so a protected exit is unique per economic exit rather than per plan artefact.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        position = await _position_row()
        h.quotes["SOL-USDT"] = (98.0, 99.0)
        outcome = await h.control.manual_close(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        return plan, position, outcome, await _sell_orders()

    plan, position, outcome, orders = asyncio.run(case())
    assert outcome.triggered is True and outcome.exit_reason is ExitReason.MANUAL_CLOSE
    assert len(orders) == 1
    assert orders[0].plan_id == plan.plan_id
    assert orders[0].intent_id == stable_id(
        "exit",
        RunMode.REPLAY,
        "SOL-USDT",
        position.trade_id,
        plan.plan_id,
        plan.plan_version,
        ExitReason.MANUAL_CLOSE,
        orders[0].quantity,
    )


def test_f01_r1_05_a_fresh_valid_plan_cannot_protect_a_position_without_a_snapshot():
    """F01-R1-05 (§2 / §6 / §8 CASE C): "merely being valid" never makes a plan authoritative.

    The plan here is fresh (TTL not expired), business-valid and the persisted ACTIVE row, and the
    quote (bid 79) is below the plan's own stop (80) -- so if a valid plan could substitute for the
    snapshot this would close the position. The position row has no durable authority, so the
    verdict is POSITION_UNPROTECTED: the exit does not happen, an incident is opened, and a
    subsequent resume is refused for the real reason instead of the plan-side one.
    """

    async def case():
        h = Harness()
        await h.boot()
        plan, _ = await open_position(h, notional=50, bid=99, ask=100, stop=80, tp=140)
        assert plan.expires_at > NOW and authority_from_plan(plan) is not None
        row = await _active_plan_row()
        assert row is not None and row.plan_id == plan.plan_id
        await _null_snapshot()
        h.quotes["SOL-USDT"] = (79.0, 80.0)
        outcome = await h.protection.evaluate(
            RunMode.REPLAY, "SOL-USDT", await h.bbo_for("SOL-USDT"), now=NOW
        )
        quantity_before = (await _position_row()).quantity
        await h.control.enter_safe_mode(
            RunMode.REPLAY,
            "position_protection_missing",
            incident_type=IncidentType.POSITION_UNPROTECTED,
            instrument_id="SOL-USDT",
            now=NOW,
        )
        resume = await h.control.safe_mode_recovery(RunMode.REPLAY, now=NOW)
        return outcome, quantity_before, await _position_row(), await _open_incident(), resume

    outcome, quantity_before, position, incident, resume = asyncio.run(case())
    assert outcome.triggered is False and outcome.reason == "POSITION_UNPROTECTED"
    assert position.quantity == quantity_before > 0
    assert incident is not None and incident.status == IncidentStatus.OPEN.value
    assert incident.reason == "open_position_without_durable_protection"
    # Resume is refused: the plan is fresh and valid, so what fails is the missing durable
    # authority, not plan freshness. Either the resume gate's own protection check or G4
    # reconciliation (invariant #13, re-based by Candidate A on the durable condition) may report
    # first; both are evidence of the same condition.
    _assert_resume_refused_for_missing_authority(resume)
