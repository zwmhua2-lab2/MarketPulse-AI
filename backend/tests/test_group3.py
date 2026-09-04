import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    ExecutionIntentRecord,
    FillRecord,
    LedgerEntryRecord,
    OutboxRecord,
    PaperOrderRecord,
    PositionRecord,
    TradePlanRecord,
    TradePlanScenarioRecord,
    TradeRecord,
)
from marketpulse.g2.models import FeatureSnapshot, SymbolState, SymbolStateRecord
from marketpulse.g3.models import (
    AIAnalysis,
    BestBidAsk,
    DataQuality,
    Direction,
    ExecutionIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    PlanStatus,
    PriceZone,
    RunMode,
    TradePlan,
)
from marketpulse.g3.provider import DeterministicFakeAIProvider
from marketpulse.g3.service import (
    BoundedAITaskQueue,
    DecisionService,
    DecisionSnapshotBuilder,
    PaperExecutionService,
    TradePlanManager,
    persist_trade_plan,
    stable_id,
)
from marketpulse.market_data.models import MarketType
from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 9, 4, 12, tzinfo=UTC)
# Each test owns a short-lived event loop. NullPool keeps asyncpg connections from
# escaping a closed loop while retaining a real PostgreSQL transaction for every call.
SESSIONS = async_sessionmaker(
    create_async_engine(Settings().database_url, poolclass=NullPool), expire_on_commit=False
)


async def _clean() -> None:
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
        intent_ids = list(
            (
                await session.scalars(
                    select(ExecutionIntentRecord.intent_id).where(
                        ExecutionIntentRecord.run_mode == RunMode.REPLAY
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
        if intent_ids:
            await session.execute(
                delete(ExecutionIntentRecord).where(ExecutionIntentRecord.intent_id.in_(intent_ids))
            )
        await session.execute(
            delete(PositionRecord).where(PositionRecord.run_mode == RunMode.REPLAY)
        )
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
                delete(TradePlanScenarioRecord).where(TradePlanScenarioRecord.plan_id.in_(plan_ids))
            )
            await session.execute(
                delete(TradePlanRecord).where(TradePlanRecord.plan_id.in_(plan_ids))
            )
        await session.execute(
            delete(AIDecisionRecord).where(AIDecisionRecord.run_mode == RunMode.REPLAY)
        )
        await session.execute(
            delete(DecisionSnapshotRecord).where(DecisionSnapshotRecord.run_mode == RunMode.REPLAY)
        )
        await session.execute(delete(OutboxRecord).where(OutboxRecord.created_at == NOW))


def _analysis(direction: Direction = Direction.LONG_BIAS) -> AIAnalysis:
    fields = (
        {
            "entry_zone": PriceZone(lower=90, upper=120),
            "stop_loss": 80,
            "take_profit": 140,
            "invalidation": "breaks 80",
            "main_plan": "buy a confirmed setup",
        }
        if direction is Direction.LONG_BIAS
        else {}
    )
    return AIAnalysis(
        direction=direction,
        trends={"5m": "UP", "15m": "UP", "1H": "UP", "4H": "UP", "1D": "UP"},
        confidence=0.8,
        suggested_position_pct=0.15,
        reason="fixture",
        **fields,
    )


def _snapshot(state_version: int = 7):
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
        trading_context={
            "api_key": "must_not_persist",
            "current_position": None,
            "open_orders": [],
        },
        now=NOW,
    )


def _plan(
    instrument: str,
    version: int = 7,
    *,
    side: OrderSide = OrderSide.BUY,
    notional: float = 10,
    order_type: OrderType = OrderType.MARKET,
) -> TradePlan:
    return TradePlan(
        plan_id=stable_id("plan", instrument, side, notional, order_type),
        snapshot_id="snap",
        decision_id="decision",
        instrument_id=instrument,
        symbol=instrument,
        run_mode=RunMode.REPLAY,
        state_version=version,
        status=PlanStatus.ACTIVE,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        side=side,
        order_type=order_type,
        entry_zone=PriceZone(lower=90, upper=120),
        stop_loss=80,
        take_profit=140,
        intended_notional=notional,
    )


async def _open_limit(
    service: PaperExecutionService, intent: ExecutionIntent, plan: TradePlan, now: datetime = NOW
):
    async with SESSIONS() as session:
        existing = await session.get(TradePlanRecord, plan.plan_id)
    if existing is None:
        await persist_trade_plan(SESSIONS, plan)
    return await service.execute(intent, plan, now)


def test_scenarios_b_c_d_snapshot_prompt_validation_and_bounded_queue():
    snapshot = _snapshot()
    assert snapshot.trading_context["api_key"] == "[REDACTED]"
    manager = TradePlanManager()
    assert (
        manager.from_analysis(
            decision_id="wait",
            snapshot=snapshot,
            analysis=_analysis(Direction.WAIT),
            current_equity=10_000,
            now=NOW,
        )
        is None
    )
    assert (
        manager.from_analysis(
            decision_id="short",
            snapshot=snapshot,
            analysis=_analysis(Direction.SHORT_BIAS),
            current_equity=10_000,
            now=NOW,
        )
        is None
    )
    with pytest.raises(ValidationError):
        AIAnalysis.model_validate({"direction": "LONG_BIAS"})

    async def queue_case():
        queue = BoundedAITaskQueue(capacity=1)
        await queue.put("NEW_SETUP", "setup")
        assert queue.depth == 1
        _, item = await queue.get()
        return item

    assert asyncio.run(queue_case()) == "setup"


def test_scenario_e_stale_ai_is_persisted_and_never_activated():
    async def case():
        await _clean()
        service = DecisionService(
            SESSIONS, DeterministicFakeAIProvider(_analysis()), model="fixture"
        )
        decision_id, status, response = await service.decide(
            _snapshot(), lambda _: asyncio.sleep(0, result=8)
        )
        return decision_id, status, response

    _, status, response = asyncio.run(case())
    assert status.value == "STALE_DECISION" and response is not None


def test_scenarios_a_g_h_i_paper_atomicity_idempotency_and_reconciliation():
    async def case():
        await _clean()
        bbo = BestBidAsk(instrument_id="SOL-USDT", bid=99, ask=100, received_at=NOW)
        service = PaperExecutionService(
            SESSIONS,
            lambda _: asyncio.sleep(0, result=bbo),
            lambda _: asyncio.sleep(0, result=7),
            initial_balance=100,
        )
        await service.bootstrap_account(RunMode.REPLAY)
        plan = _plan("SOL-USDT")
        await persist_trade_plan(SESSIONS, plan)
        intent = ExecutionIntent(
            intent_id="intent-normal",
            plan_id=plan.plan_id,
            instrument_id=plan.instrument_id,
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        first = await service.execute(intent, plan, NOW)
        duplicate = await service.execute(intent, plan, NOW)
        reconciliation = await service.reconciliation(RunMode.REPLAY)
        async with SESSIONS() as session:
            fills = len(
                (
                    await session.scalars(
                        select(FillRecord).where(FillRecord.intent_id == intent.intent_id)
                    )
                ).all()
            )
            ledgers = len(
                (
                    await session.scalars(
                        select(LedgerEntryRecord).where(LedgerEntryRecord.fill_id == first.fill_id)
                    )
                ).all()
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        failing = ExecutionIntent(
            intent_id="intent-rollback",
            plan_id="rollback-plan",
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        failure_plan = _plan("SOL-USDT", notional=5)
        service.after_settlement = lambda: (_ for _ in ()).throw(RuntimeError("injected"))
        with pytest.raises(RuntimeError):
            await service.execute(failing, failure_plan, NOW)
        service.after_settlement = None
        async with SESSIONS() as session:
            rollback_orders = len(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.intent_id == failing.intent_id
                        )
                    )
                ).all()
            )
        return first, duplicate, fills, ledgers, position, reconciliation, rollback_orders

    first, duplicate, fills, ledgers, position, reconciliation, rollback_orders = asyncio.run(
        case()
    )
    assert first.fill_id and duplicate.order_id == first.order_id
    assert fills == ledgers == 1 and position and position.quantity > 0
    assert reconciliation["reserved_cash_matches_open_buys"] and rollback_orders == 0


def test_scenarios_f_j_capacity_and_cross_symbol_account_lock():
    async def case():
        await _clean()

        async def bbo_for(instrument: str):
            return BestBidAsk(instrument_id=instrument, bid=99, ask=100, received_at=NOW)

        service = PaperExecutionService(
            SESSIONS, bbo_for, lambda _: asyncio.sleep(0, result=7), initial_balance=100
        )
        await service.bootstrap_account(RunMode.REPLAY)
        plans = [_plan(f"A{number}-USDT") for number in range(12)]
        intents = [
            ExecutionIntent(
                intent_id=f"intent-race-{number}",
                plan_id=plan.plan_id,
                instrument_id=plan.instrument_id,
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            )
            for number, plan in enumerate(plans)
        ]
        results = await asyncio.gather(
            *(
                service.execute(intent, plan, NOW)
                for intent, plan in zip(intents, plans, strict=True)
            )
        )
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return results, account

    results, account = asyncio.run(case())
    assert any(result.reason == "CAPACITY_BLOCKED" for result in results)
    assert account and account.cash_balance - account.reserved_cash >= -1e-9


def test_scenario_k_weighted_average_reduce_and_full_exit():
    async def case():
        await _clean()
        prices = [100.0, 110.0, 120.0, 120.0]

        async def bbo_for(_: str):
            price = prices.pop(0)
            return BestBidAsk(instrument_id="SOL-USDT", bid=price - 1, ask=price, received_at=NOW)

        service = PaperExecutionService(
            SESSIONS, bbo_for, lambda _: asyncio.sleep(0, result=7), initial_balance=10_000
        )
        await service.bootstrap_account(RunMode.REPLAY)
        total_quantity = 10 / 100.05 + 11 / 110.055
        each_exit_notional = total_quantity * 119 * (1 - 0.0005) / 2
        plans = (
            _plan("SOL-USDT", notional=10),
            _plan("SOL-USDT", notional=11),
            _plan("SOL-USDT", side=OrderSide.SELL, notional=each_exit_notional),
            _plan("SOL-USDT", side=OrderSide.SELL, notional=each_exit_notional),
        )
        for number, plan in enumerate(plans):
            intent = ExecutionIntent(
                intent_id=f"intent-lifecycle-{number}",
                plan_id=plan.plan_id,
                instrument_id=plan.instrument_id,
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            )
            await service.execute(intent, plan, NOW)
        async with SESSIONS() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return position

    position = asyncio.run(case())
    assert position and position.quantity == 0 and position.realized_pnl != 0


def test_basic_reconciliation_open_orders_invariants():
    """G3 Basic Reconciliation：验证四项基础对账不变量（真实 PostgreSQL）。

    1. Reserved Cash   = 所有 OPEN Buy Orders 的 reserved_cash 之和
    2. Reserved Asset  = 所有 OPEN Sell Orders 的 reserved_quantity 之和（冻结资产不超持仓）
    3. Position Quantity = Net Fills（买入成交 - 卖出成交）
    4. Available Cash  = Cash Balance - Reserved Cash
    """

    async def case():
        await _clean()
        bbo = BestBidAsk(instrument_id="SOL-USDT", bid=99, ask=100, received_at=NOW)
        service = PaperExecutionService(
            SESSIONS,
            lambda _: asyncio.sleep(0, result=bbo),
            lambda _: asyncio.sleep(0, result=7),
            initial_balance=1000,
        )
        await service.bootstrap_account(RunMode.REPLAY)
        # 市价买入建立持仓（立即成交）。
        buy_plan = _plan("SOL-USDT", notional=100)
        buy_intent = ExecutionIntent(
            intent_id="rec-buy-market",
            plan_id=buy_plan.plan_id,
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        await service.execute(buy_intent, buy_plan, NOW)
        # 限价卖出：OPEN，冻结部分持仓资产。
        sell_plan = _plan("SOL-USDT", side=OrderSide.SELL, notional=40, order_type=OrderType.LIMIT)
        sell_intent = ExecutionIntent(
            intent_id="rec-sell-limit",
            plan_id=sell_plan.plan_id,
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        await _open_limit(service, sell_intent, sell_plan, NOW)
        # 限价买入：OPEN，冻结现金。
        buy2_plan = _plan("SOL-USDT", notional=50, order_type=OrderType.LIMIT)
        buy2_intent = ExecutionIntent(
            intent_id="rec-buy-limit",
            plan_id=buy2_plan.plan_id,
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        await _open_limit(service, buy2_intent, buy2_plan, NOW)

        reconciliation = await service.reconciliation(RunMode.REPLAY)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            open_buy_orders = list(
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
            open_sell_orders = list(
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
            fill_rows = list(
                (
                    await session.execute(
                        select(FillRecord.quantity, PaperOrderRecord.side)
                        .join(
                            PaperOrderRecord,
                            FillRecord.order_id == PaperOrderRecord.order_id,
                        )
                        .where(PaperOrderRecord.run_mode == RunMode.REPLAY)
                    )
                ).all()
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        reserved_cash_expected = sum(order.reserved_cash for order in open_buy_orders)
        reserved_asset_expected = sum(order.reserved_quantity for order in open_sell_orders)
        net_fills = sum(q for q, side in fill_rows if side == OrderSide.BUY) - sum(
            q for q, side in fill_rows if side == OrderSide.SELL
        )
        return (
            account,
            reconciliation,
            reserved_cash_expected,
            reserved_asset_expected,
            net_fills,
            position,
        )

    (
        account,
        reconciliation,
        reserved_cash_expected,
        reserved_asset_expected,
        net_fills,
        position,
    ) = asyncio.run(case())
    # 1. Reserved Cash = 所有 OPEN Buy Orders 的 reserved_cash 之和
    assert account.reserved_cash == reserved_cash_expected
    assert reconciliation["reserved_cash_matches_open_buys"] is True
    # 2. Reserved Asset = 所有 OPEN Sell Orders 的 reserved_quantity 之和（不超持仓）
    assert reserved_asset_expected <= position.quantity + 1e-9
    # 3. Position Quantity = Net Fills
    assert abs(position.quantity - net_fills) < 1e-8
    # 4. Available Cash = Cash Balance - Reserved Cash
    assert (
        abs(reconciliation["available_cash"] - (account.cash_balance - account.reserved_cash))
        < 1e-9
    )


def test_limit_buy_lifecycle_duplicate_cancel_and_settlement_rollback():
    """真实 PostgreSQL：OPEN BUY → BBO Fill / duplicate / cancel / rollback 原子性。"""

    async def case():
        await _clean()
        quotes = {"SOL-USDT": (99.0, 100.0)}

        async def bbo_for(instrument: str):
            bid, ask = quotes[instrument]
            return BestBidAsk(instrument_id=instrument, bid=bid, ask=ask, received_at=NOW)

        service = PaperExecutionService(
            SESSIONS, bbo_for, lambda _: asyncio.sleep(0, result=7), initial_balance=1000
        )
        await service.bootstrap_account(RunMode.REPLAY)
        plan = _plan("SOL-USDT", notional=50, order_type=OrderType.LIMIT)
        intent = ExecutionIntent(
            intent_id="limit-buy-fill",
            plan_id=plan.plan_id,
            instrument_id=plan.instrument_id,
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        opened = await _open_limit(service, intent, plan, NOW)
        quotes["SOL-USDT"] = (90.0, 91.0)
        not_triggered = await service.process_open_orders(
            RunMode.REPLAY, await bbo_for("SOL-USDT"), NOW
        )
        quotes["SOL-USDT"] = (89.0, 90.0)
        filled = await service.process_open_orders(RunMode.REPLAY, await bbo_for("SOL-USDT"), NOW)
        duplicate = await service.process_open_orders(
            RunMode.REPLAY, await bbo_for("SOL-USDT"), NOW
        )

        quotes["SOL-USDT"] = (99.0, 100.0)
        rollback_plan = _plan("SOL-USDT", notional=10, order_type=OrderType.LIMIT)
        rollback_intent = ExecutionIntent(
            intent_id="limit-buy-rollback",
            plan_id=rollback_plan.plan_id,
            instrument_id=rollback_plan.instrument_id,
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        rollback_opened = await _open_limit(service, rollback_intent, rollback_plan, NOW)
        async with SESSIONS() as session:
            account_before = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            reserved_before = account_before.reserved_cash
            position_before = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            quantity_before = position_before.quantity
        quotes["SOL-USDT"] = (89.0, 90.0)
        service.after_settlement = lambda: (_ for _ in ()).throw(RuntimeError("injected"))
        with pytest.raises(RuntimeError):
            await service.process_open_orders(RunMode.REPLAY, await bbo_for("SOL-USDT"), NOW)
        service.after_settlement = None
        async with SESSIONS() as session:
            rollback_account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            rollback_order_before_cancel = await session.scalar(
                select(PaperOrderRecord).where(
                    PaperOrderRecord.order_id == rollback_opened.order_id
                )
            )
            rollback_position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        cancelled = await service.cancel_order(rollback_opened.order_id, NOW)
        duplicate_cancel = await service.cancel_order(rollback_opened.order_id, NOW)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == opened.order_id)
            )
            rollback_order = await session.scalar(
                select(PaperOrderRecord).where(
                    PaperOrderRecord.order_id == rollback_opened.order_id
                )
            )
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord).where(FillRecord.order_id == opened.order_id)
                    )
                ).all()
            )
            rollback_fills = list(
                (
                    await session.scalars(
                        select(FillRecord).where(FillRecord.order_id == rollback_opened.order_id)
                    )
                ).all()
            )
            ledgers = list(
                (
                    await session.scalars(
                        select(LedgerEntryRecord).where(
                            LedgerEntryRecord.fill_id == fills[0].fill_id
                        )
                    )
                ).all()
            )
        return (
            not_triggered,
            filled,
            duplicate,
            account,
            order,
            rollback_order,
            fills,
            rollback_fills,
            ledgers,
            reserved_before,
            quantity_before,
            rollback_account.reserved_cash,
            rollback_order_before_cancel,
            rollback_position.quantity,
            cancelled,
            duplicate_cancel,
        )

    (
        not_triggered,
        filled,
        duplicate,
        account,
        order,
        rollback_order,
        fills,
        rollback_fills,
        ledgers,
        reserved_before,
        quantity_before,
        reserved_after_error,
        rollback_order_before_cancel,
        quantity_after_error,
        cancelled,
        duplicate_cancel,
    ) = asyncio.run(case())
    assert not not_triggered and len(filled) == 1 and not duplicate
    assert order.status == OrderStatus.FILLED and order.reserved_cash == 0
    assert len(fills) == len(ledgers) == 1
    assert rollback_order_before_cancel.status == OrderStatus.OPEN
    assert reserved_before == reserved_after_error and quantity_before == quantity_after_error
    assert rollback_order.status == OrderStatus.CANCELLED and not rollback_fills
    assert cancelled.cancelled and not duplicate_cancel.cancelled
    assert reserved_before > 0 and account.reserved_cash == 0


def test_limit_sell_reservation_cancel_fill_and_oversell_protection():
    """真实 PostgreSQL：SELL 限价冻结、取消、成交及多个 OPEN SELL 防超卖。"""

    async def case():
        await _clean()
        quote = BestBidAsk(instrument_id="SOL-USDT", bid=99, ask=100, received_at=NOW)
        service = PaperExecutionService(
            SESSIONS,
            lambda _: asyncio.sleep(0, result=quote),
            lambda _: asyncio.sleep(0, result=7),
            initial_balance=1000,
        )
        await service.bootstrap_account(RunMode.REPLAY)
        buy_plan = _plan("SOL-USDT", notional=100)
        await service.execute(
            ExecutionIntent(
                intent_id="sell-base-buy",
                plan_id=buy_plan.plan_id,
                instrument_id="SOL-USDT",
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            ),
            buy_plan,
            NOW,
        )
        cancel_plan = _plan(
            "SOL-USDT", side=OrderSide.SELL, notional=30, order_type=OrderType.LIMIT
        )
        cancel_opened = await _open_limit(
            service,
            ExecutionIntent(
                intent_id="sell-cancel",
                plan_id=cancel_plan.plan_id,
                instrument_id="SOL-USDT",
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            ),
            cancel_plan,
            NOW,
        )
        cancelled = await service.cancel_order(cancel_opened.order_id, NOW)
        sell_plan = _plan("SOL-USDT", side=OrderSide.SELL, notional=84, order_type=OrderType.LIMIT)
        sell_opened = await _open_limit(
            service,
            ExecutionIntent(
                intent_id="sell-fill",
                plan_id=sell_plan.plan_id,
                instrument_id="SOL-USDT",
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            ),
            sell_plan,
            NOW,
        )
        blocked_plan = _plan(
            "SOL-USDT", side=OrderSide.SELL, notional=60, order_type=OrderType.LIMIT
        )
        blocked = await service.execute(
            ExecutionIntent(
                intent_id="sell-oversell",
                plan_id=blocked_plan.plan_id,
                instrument_id="SOL-USDT",
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            ),
            blocked_plan,
            NOW,
        )
        match_bbo = BestBidAsk(instrument_id="SOL-USDT", bid=121, ask=122, received_at=NOW)
        filled = await service.process_open_orders(RunMode.REPLAY, match_bbo, NOW)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == sell_opened.order_id)
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
            ledger = await session.scalar(
                select(LedgerEntryRecord)
                .join(FillRecord, LedgerEntryRecord.fill_id == FillRecord.fill_id)
                .where(FillRecord.order_id == sell_opened.order_id)
            )
        return cancelled, blocked, filled, order, position, ledger

    cancelled, blocked, filled, order, position, ledger = asyncio.run(case())
    assert cancelled.cancelled
    assert blocked.reason == "CAPACITY_BLOCKED"
    assert len(filled) == 1 and order.status == OrderStatus.FILLED
    assert (
        order.reserved_quantity == 0 and position.quantity > 0 and ledger.entry_type == "SELL_FILL"
    )


def test_pending_buy_exposure_fee_reservation_equity_marks_and_reconciliation():
    """真实 PostgreSQL：Pending BUY、手续费冻结、全账户 Fresh Mark 与六项对账。"""

    async def case():
        await _clean()
        quotes = {f"FEE-{index}-USDT": (99.0, 100.0) for index in range(7)}
        quotes["PENDING-USDT"] = (99.0, 100.0)
        quotes["FEE-REJECT-USDT"] = (99.0, 100.0)
        quotes["FRESH-CHECK-USDT"] = (99.0, 100.0)
        stale_instruments: set[str] = set()

        async def bbo_for(instrument: str):
            bid, ask = quotes[instrument]
            return BestBidAsk(
                instrument_id=instrument,
                bid=bid,
                ask=ask,
                received_at=NOW,
                data_quality=(
                    DataQuality.STALE if instrument in stale_instruments else DataQuality.FRESH
                ),
            )

        service = PaperExecutionService(
            SESSIONS, bbo_for, lambda _: asyncio.sleep(0, result=7), initial_balance=1000
        )
        await service.bootstrap_account(RunMode.REPLAY)

        async def open_limit(instrument: str, intent_id: str, notional: float = 100):
            plan = _plan(instrument, notional=notional, order_type=OrderType.LIMIT)
            return await _open_limit(
                service,
                ExecutionIntent(
                    intent_id=intent_id,
                    plan_id=plan.plan_id,
                    instrument_id=instrument,
                    run_mode=RunMode.REPLAY,
                    state_version=7,
                    created_at=NOW,
                ),
                plan,
                NOW,
            )

        first_pending = await open_limit("PENDING-USDT", "pending-1")
        second_pending = await open_limit("PENDING-USDT", "pending-2")
        pending_plan = _plan("PENDING-USDT", notional=1, order_type=OrderType.LIMIT)
        pending_blocked = await service.execute(
            ExecutionIntent(
                intent_id="pending-3",
                plan_id=pending_plan.plan_id,
                instrument_id="PENDING-USDT",
                run_mode=RunMode.REPLAY,
                state_version=7,
                created_at=NOW,
            ),
            pending_plan,
            NOW,
        )
        fee_opened = [await open_limit(f"FEE-{index}-USDT", f"fee-{index}") for index in range(7)]
        fee_blocked = await open_limit("FEE-REJECT-USDT", "fee-reject")
        for instrument in ("PENDING-USDT", *(f"FEE-{index}-USDT" for index in range(7))):
            quotes[instrument] = (89.0, 90.0)
            await service.process_open_orders(RunMode.REPLAY, await bbo_for(instrument), NOW)
        stale_instruments.add("PENDING-USDT")
        stale_equity = await open_limit("FRESH-CHECK-USDT", "stale-equity", 1)
        reconciliation = await service.reconciliation(RunMode.REPLAY)
        async with SESSIONS() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
        return (
            first_pending,
            second_pending,
            pending_blocked,
            fee_opened,
            fee_blocked,
            stale_equity,
            reconciliation,
            account,
        )

    (
        first_pending,
        second_pending,
        pending_blocked,
        fee_opened,
        fee_blocked,
        stale_equity,
        reconciliation,
        account,
    ) = asyncio.run(case())
    assert first_pending.order_id and second_pending.order_id
    assert pending_blocked.reason == "CAPACITY_BLOCKED"
    assert all(result.order_id for result in fee_opened)
    assert fee_blocked.reason == "CAPACITY_BLOCKED"
    assert stale_equity.reason == "CORE_POSITION_MARK_STALE"
    assert account.cash_balance >= -1e-9 and reconciliation["ok"] is True


def test_limit_fill_time_plan_state_and_buy_invalidation_guards():
    """真实 PostgreSQL：OPEN Limit 在 Fill-Time 重锁 Plan 并 fail closed。"""

    async def run_case(
        *,
        plan_status: PlanStatus = PlanStatus.ACTIVE,
        at: datetime = NOW,
        fill_version: int = 7,
        fill_ask: float = 90.0,
    ):
        await _clean()
        version = [7]

        async def bbo_for(_: str):
            return BestBidAsk(instrument_id="SOL-USDT", bid=99, ask=100, received_at=NOW)

        service = PaperExecutionService(
            SESSIONS, bbo_for, lambda _: asyncio.sleep(0, result=version[0]), initial_balance=1000
        )
        await service.bootstrap_account(RunMode.REPLAY)
        plan = _plan("SOL-USDT", notional=50, order_type=OrderType.LIMIT)
        intent = ExecutionIntent(
            intent_id=f"fill-time-{plan_status}-{at.isoformat()}-{fill_version}-{fill_ask}",
            plan_id=plan.plan_id,
            instrument_id="SOL-USDT",
            run_mode=RunMode.REPLAY,
            state_version=7,
            created_at=NOW,
        )
        opened = await _open_limit(service, intent, plan, NOW)
        async with SESSIONS() as session, session.begin():
            await session.execute(
                update(TradePlanRecord)
                .where(TradePlanRecord.plan_id == plan.plan_id)
                .values(status=plan_status)
            )
        version[0] = fill_version
        bbo = BestBidAsk(instrument_id="SOL-USDT", bid=fill_ask - 1, ask=fill_ask, received_at=at)
        results = await service.process_open_orders(RunMode.REPLAY, bbo, at)
        async with SESSIONS() as session:
            order = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == opened.order_id)
            )
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord).where(FillRecord.order_id == opened.order_id)
                    )
                ).all()
            )
            ledgers = (
                list(
                    (
                        await session.scalars(
                            select(LedgerEntryRecord).where(
                                LedgerEntryRecord.fill_id.in_([item.fill_id for item in fills])
                            )
                        )
                    ).all()
                )
                if fills
                else []
            )
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == RunMode.REPLAY,
                    PositionRecord.instrument_id == "SOL-USDT",
                )
            )
        return results, order, account, fills, ledgers, position

    expired = asyncio.run(run_case(at=NOW + timedelta(minutes=6)))
    replaced = asyncio.run(run_case(plan_status=PlanStatus.REPLACED))
    stale_version = asyncio.run(run_case(fill_version=8))
    invalidated = asyncio.run(run_case(fill_ask=89.0))
    valid = asyncio.run(run_case())

    for case, reason in (
        (expired, "PLAN_EXPIRED"),
        (replaced, "PLAN_NOT_ACTIVE"),
        (stale_version, "STATE_VERSION_CHANGED"),
        (invalidated, "BUY_PRICE_OUTSIDE_ENTRY_ZONE"),
    ):
        results, order, account, fills, ledgers, position = case
        assert len(results) == 1 and results[0].reason == reason
        assert order.status == OrderStatus.OPEN and not fills and not ledgers and position is None
        assert account.reserved_cash == order.reserved_cash
    results, order, account, fills, ledgers, position = valid
    assert len(results) == len(fills) == len(ledgers) == 1
    assert (
        order.status == OrderStatus.FILLED and account.reserved_cash == 0 and position.quantity > 0
    )
