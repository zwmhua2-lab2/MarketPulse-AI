from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from marketpulse.g2.models import FeatureSnapshot, StrategyCandidate, SymbolStateRecord

from .models import (
    AIAnalysis,
    BestBidAsk,
    DataQuality,
    DecisionSnapshot,
    DecisionStatus,
    Direction,
    ExecutionIntent,
    ExecutionResult,
    IntentStatus,
    OrderSide,
    OrderStatus,
    OrderType,
    PlanStatus,
    RunMode,
    StrategyContext,
    TradePlan,
)
from .provider import AIProvider


def stable_id(prefix: str, *parts: object) -> str:
    value = json.dumps([str(item) for item in parts], separators=(",", ":"), sort_keys=True)
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:24]}"


def redact(value: Any) -> Any:
    """Strip secrets before snapshot/prompt/audit persistence."""
    sensitive = {"api_key", "apikey", "token", "password", "secret", "authorization", "webhook"}
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(word in key.lower() for word in sensitive) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class DecisionSnapshotBuilder:
    version = "g3-v1"

    def build(
        self,
        *,
        run_mode: RunMode,
        state: SymbolStateRecord,
        features: FeatureSnapshot,
        bbo: BestBidAsk,
        candidates: list[StrategyCandidate],
        timeline: list[dict[str, Any]],
        config_version: str,
        trading_context: dict[str, Any],
        now: datetime | None = None,
    ) -> DecisionSnapshot:
        now = now or datetime.now(UTC)
        strategies = [
            StrategyContext(
                candidate_id=item.candidate_id,
                strategy_id=item.strategy_id,
                strength=item.strength,
                supporting_evidence=item.supporting_evidence,
                contradicting_evidence=item.contradicting_evidence,
                expected_behavior=item.expected_behavior,
                invalidation_hint=item.invalidation_hint,
            )
            for item in candidates
        ]
        market = redact(
            {
                "current_price": features.current_price,
                "best_bid": bbo.bid,
                "best_ask": bbo.ask,
                "bbo_received_at": bbo.received_at.isoformat(),
                "bbo_quality": bbo.data_quality,
                "rolling_features": features.model_dump(mode="json"),
                "structure": features.structure.model_dump(mode="json"),
                "relative_btc_strength": features.relative_btc_strength,
                "derivatives": {"oi": features.oi, "funding_rate": features.funding_rate},
                "data_quality": features.liquidation_availability,
            }
        )
        evolution = redact(
            {
                "timeline": timeline[-20:],
                "setup_evidence": [item.candidate_id for item in candidates if item.applicable],
            }
        )
        context = redact(trading_context)
        snapshot_id = stable_id(
            "snap",
            run_mode,
            state.instrument_id,
            state.state_version,
            config_version,
            now.isoformat(),
        )
        return DecisionSnapshot(
            snapshot_id=snapshot_id,
            instrument_id=state.instrument_id,
            symbol=state.symbol,
            run_mode=run_mode,
            state=state.state,
            state_version=state.state_version,
            config_version=config_version,
            snapshot_version=self.version,
            created_at=now,
            market_context=market,
            market_evolution=evolution,
            strategies=strategies,
            trading_context=context,
        )


class PromptBuilder:
    version = "g3-v1"

    def build(self, snapshot: DecisionSnapshot) -> str:
        payload = redact(snapshot.model_dump(mode="json"))
        return "\n\n".join(
            (
                "SYSTEM POLICY\nAnalyze only the supplied frozen snapshot. Never call tools or execute trades. SHORT_BIAS is analysis only.",
                f"MARKET CONTEXT\n{json.dumps(payload['market_context'], sort_keys=True)}",
                f"STRATEGY CONTEXT\n{json.dumps(payload['strategies'], sort_keys=True)}",
                f"TRADING CONTEXT\n{json.dumps(payload['trading_context'], sort_keys=True)}",
                "DECISION TASK\nReturn the versioned structured decision schema only.",
            )
        )


class DecisionValidator:
    def business_errors(self, snapshot: DecisionSnapshot, analysis: AIAnalysis) -> list[str]:
        errors: list[str] = []
        if snapshot.state != "SETUP":
            errors.append("state_not_setup")
        if analysis.direction is Direction.LONG_BIAS:
            if not all(
                (
                    analysis.entry_zone,
                    analysis.stop_loss is not None,
                    analysis.take_profit is not None,
                    analysis.invalidation,
                    analysis.main_plan,
                )
            ):
                errors.append("long_plan_fields_missing")
            elif not (
                analysis.stop_loss
                < analysis.entry_zone.lower
                <= analysis.entry_zone.upper
                < analysis.take_profit
            ):
                errors.append("long_price_relationship_invalid")
        elif analysis.direction is Direction.SHORT_BIAS:
            # Persisted analytical result is valid, but it can never become an executable V1 plan.
            pass
        if snapshot.market_context.get("bbo_quality") != DataQuality.FRESH:
            errors.append("market_data_not_fresh")
        return errors


class BoundedAITaskQueue:
    """Bounded priority queue with observable depth; G3 consumes NEW_SETUP only."""

    priorities: ClassVar[dict[str, int]] = {
        "POSITION_REVIEW": 0,
        "PLAN_REVIEW": 1,
        "NEW_SETUP": 2,
        "LOW": 3,
    }

    def __init__(self, capacity: int = 256) -> None:
        self.queue: asyncio.PriorityQueue[tuple[int, int, datetime, object]] = (
            asyncio.PriorityQueue(maxsize=capacity)
        )
        self._sequence = 0

    @property
    def depth(self) -> int:
        return self.queue.qsize()

    async def put(self, kind: str, payload: object) -> None:
        if kind not in self.priorities:
            raise ValueError("unknown AI task priority")
        self._sequence += 1
        await self.queue.put((self.priorities[kind], self._sequence, datetime.now(UTC), payload))

    async def get(self) -> tuple[datetime, object]:
        _, _, created_at, payload = await self.queue.get()
        return created_at, payload


class TradePlanManager:
    def __init__(
        self, ttl: timedelta = timedelta(minutes=5), single_order_cap: float = 0.10
    ) -> None:
        self.ttl = ttl
        self.single_order_cap = single_order_cap
        self._active: dict[tuple[RunMode, str], TradePlan] = {}

    def from_analysis(
        self,
        *,
        decision_id: str,
        snapshot: DecisionSnapshot,
        analysis: AIAnalysis,
        current_equity: float,
        now: datetime | None = None,
    ) -> TradePlan | None:
        if analysis.direction is not Direction.LONG_BIAS:
            return None
        errors = DecisionValidator().business_errors(snapshot, analysis)
        if errors:
            raise ValueError(",".join(errors))
        now = now or datetime.now(UTC)
        key = (snapshot.run_mode, snapshot.instrument_id)
        previous = self._active.get(key)
        if previous and previous.status is PlanStatus.ACTIVE:
            previous.status = PlanStatus.REPLACED
        notional = min(
            current_equity * self.single_order_cap, current_equity * analysis.suggested_position_pct
        )
        plan = TradePlan(
            plan_id=stable_id("plan", decision_id, 1),
            snapshot_id=snapshot.snapshot_id,
            decision_id=decision_id,
            instrument_id=snapshot.instrument_id,
            symbol=snapshot.symbol,
            run_mode=snapshot.run_mode,
            state_version=snapshot.state_version,
            created_at=now,
            expires_at=now + self.ttl,
            entry_zone=analysis.entry_zone,
            stop_loss=analysis.stop_loss,
            take_profit=analysis.take_profit,
            intended_notional=notional,
            probe=analysis.probe,
            backup_scenarios=analysis.backup_scenarios,
        )
        self._active[key] = plan
        return plan


async def persist_trade_plan(sessions: async_sessionmaker[AsyncSession], plan: TradePlan) -> None:
    """Atomically replace the one active plan for a symbol and persist non-executable backups."""
    async with sessions() as session, session.begin():
        await session.execute(
            update(TradePlanRecord)
            .where(
                TradePlanRecord.run_mode == plan.run_mode,
                TradePlanRecord.instrument_id == plan.instrument_id,
                TradePlanRecord.status == PlanStatus.ACTIVE,
            )
            .values(status=PlanStatus.REPLACED)
        )
        session.add(
            TradePlanRecord(
                plan_id=plan.plan_id,
                snapshot_id=plan.snapshot_id,
                decision_id=plan.decision_id,
                instrument_id=plan.instrument_id,
                symbol=plan.symbol,
                run_mode=plan.run_mode,
                state_version=plan.state_version,
                plan_version=plan.plan_version,
                status=plan.status,
                created_at=plan.created_at,
                expires_at=plan.expires_at,
                payload=plan.model_dump(mode="json"),
            )
        )
        session.add_all(
            TradePlanScenarioRecord(
                scenario_id=stable_id("scenario", plan.plan_id, index),
                plan_id=plan.plan_id,
                ordinal=index,
                scenario=scenario,
            )
            for index, scenario in enumerate(plan.backup_scenarios)
        )


class DecisionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        provider: AIProvider,
        *,
        model: str,
        prompt_version: str = "g3-v1",
        schema_version: str = "g3-v1",
    ) -> None:
        self.sessions, self.provider, self.model = sessions, provider, model
        self.prompt_version, self.schema_version = prompt_version, schema_version

    async def decide(
        self,
        snapshot: DecisionSnapshot,
        current_state_version: Callable[[str], Awaitable[int]],
        *,
        retries: int = 1,
    ) -> tuple[str, DecisionStatus, AIAnalysis | None]:
        prompt = PromptBuilder().build(snapshot)
        response: AIAnalysis | None = None
        error: str | None = None
        for attempt in range(retries + 1):
            try:
                response = await self.provider.analyze(snapshot, prompt)
                break
            except Exception as exc:  # noqa: BLE001 - provider failures are persisted fail-closed
                error = type(exc).__name__
                if attempt == retries:
                    break
        decision_id = stable_id("decision", snapshot.snapshot_id, self.model)
        status = DecisionStatus.INVALID_SCHEMA if response is None else DecisionStatus.VALID
        if response is not None and DecisionValidator().business_errors(snapshot, response):
            status = DecisionStatus.INVALID_BUSINESS
        if (
            response is not None
            and await current_state_version(snapshot.instrument_id) != snapshot.state_version
        ):
            status = DecisionStatus.STALE_DECISION
        async with self.sessions() as session, session.begin():
            session.add(
                DecisionSnapshotRecord(
                    snapshot_id=snapshot.snapshot_id,
                    instrument_id=snapshot.instrument_id,
                    symbol=snapshot.symbol,
                    run_mode=snapshot.run_mode,
                    state_version=snapshot.state_version,
                    config_version=snapshot.config_version,
                    snapshot_version=snapshot.snapshot_version,
                    created_at=snapshot.created_at,
                    payload=redact(snapshot.model_dump(mode="json")),
                )
            )
            session.add(
                AIDecisionRecord(
                    decision_id=decision_id,
                    snapshot_id=snapshot.snapshot_id,
                    run_mode=snapshot.run_mode,
                    state_version=snapshot.state_version,
                    config_version=snapshot.config_version,
                    prompt_version=self.prompt_version,
                    schema_version=self.schema_version,
                    model=self.model,
                    status=status,
                    raw_prompt=prompt,
                    raw_response=redact(response.model_dump(mode="json")) if response else {},
                    error=error,
                    created_at=datetime.now(UTC),
                )
            )
        return decision_id, status, response


class G3Workflow:
    """Explicit G2 SETUP hand-off; deliberately not wired into the G2 runtime until activation is approved."""

    def __init__(
        self,
        decision_service: DecisionService,
        plan_manager: TradePlanManager,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self.decision_service, self.plan_manager, self.sessions = (
            decision_service,
            plan_manager,
            sessions,
        )

    async def process_setup(
        self,
        snapshot: DecisionSnapshot,
        current_state_version: Callable[[str], Awaitable[int]],
        current_equity: float,
    ) -> tuple[DecisionStatus, TradePlan | None]:
        decision_id, status, analysis = await self.decision_service.decide(
            snapshot, current_state_version
        )
        if status is not DecisionStatus.VALID or analysis is None:
            return status, None
        plan = self.plan_manager.from_analysis(
            decision_id=decision_id,
            snapshot=snapshot,
            analysis=analysis,
            current_equity=current_equity,
        )
        if plan is not None:
            await persist_trade_plan(self.sessions, plan)
        return status, plan


class PaperExecutionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        bbo_for: Callable[[str], Awaitable[BestBidAsk]],
        state_version_for: Callable[[str], Awaitable[int]],
        *,
        initial_balance: float = 10_000.0,
        fee_rate: float = 0.001,
        slippage_bps: float = 5,
        freshness_ttl: timedelta = timedelta(seconds=5),
    ) -> None:
        self.sessions, self.bbo_for, self.state_version_for = sessions, bbo_for, state_version_for
        self.initial_balance, self.fee_rate, self.slippage_bps, self.freshness_ttl = (
            initial_balance,
            fee_rate,
            slippage_bps,
            freshness_ttl,
        )
        self.after_settlement: Callable[[], None] | None = None

    async def bootstrap_account(self, run_mode: RunMode) -> None:
        now = datetime.now(UTC)
        async with self.sessions() as session, session.begin():
            if not await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == run_mode)
            ):
                session.add(
                    AccountRecord(
                        account_id=stable_id("acct", run_mode),
                        run_mode=run_mode,
                        cash_balance=self.initial_balance,
                        reserved_cash=0,
                        realized_pnl=0,
                        updated_at=now,
                    )
                )

    async def execute(
        self, intent: ExecutionIntent, plan: TradePlan, now: datetime | None = None
    ) -> ExecutionResult:
        now = now or datetime.now(UTC)
        try:
            return await self._execute_once(intent, plan, now)
        except IntegrityError:
            async with self.sessions() as session:
                order = await session.scalar(
                    select(PaperOrderRecord).where(PaperOrderRecord.intent_id == intent.intent_id)
                )
            if order:
                return ExecutionResult(
                    intent_id=intent.intent_id,
                    status=IntentStatus.EXECUTED,
                    order_id=order.order_id,
                    reason="duplicate_intent",
                )
            raise

    async def _execute_once(
        self, intent: ExecutionIntent, plan: TradePlan, now: datetime
    ) -> ExecutionResult:
        async with self.sessions() as session, session.begin():
            existing = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.intent_id == intent.intent_id)
            )
            if existing:
                fill = await session.scalar(
                    select(FillRecord).where(FillRecord.intent_id == intent.intent_id)
                )
                return ExecutionResult(
                    intent_id=intent.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="duplicate_intent",
                    order_id=existing.order_id,
                    fill_id=fill.fill_id if fill else None,
                )
            bbo = await self.bbo_for(intent.instrument_id)
            reason = self._revalidate(
                plan, intent, bbo, now, await self.state_version_for(intent.instrument_id)
            )
            if reason:
                session.add(
                    ExecutionIntentRecord(
                        intent_id=intent.intent_id,
                        plan_id=intent.plan_id,
                        instrument_id=intent.instrument_id,
                        run_mode=intent.run_mode,
                        state_version=intent.state_version,
                        status=IntentStatus.REJECTED,
                        reason=reason,
                        created_at=now,
                    )
                )
                return ExecutionResult(
                    intent_id=intent.intent_id, status=IntentStatus.REJECTED, reason=reason
                )
            account = await session.scalar(
                select(AccountRecord)
                .where(AccountRecord.run_mode == intent.run_mode)
                .with_for_update()
            )
            if account is None:
                raise RuntimeError("account_not_bootstrapped")
            price = (
                (bbo.ask * (1 + self.slippage_bps / 10_000))
                if plan.side is OrderSide.BUY
                else (bbo.bid * (1 - self.slippage_bps / 10_000))
            )
            quantity = plan.intended_notional / price
            position = await session.scalar(
                select(PositionRecord)
                .where(
                    PositionRecord.run_mode == intent.run_mode,
                    PositionRecord.instrument_id == intent.instrument_id,
                )
                .with_for_update()
            )
            if self._capacity_blocked(account, position, plan, price):
                session.add(
                    ExecutionIntentRecord(
                        intent_id=intent.intent_id,
                        plan_id=intent.plan_id,
                        instrument_id=intent.instrument_id,
                        run_mode=intent.run_mode,
                        state_version=intent.state_version,
                        status=IntentStatus.REJECTED,
                        reason="CAPACITY_BLOCKED",
                        created_at=now,
                    )
                )
                return ExecutionResult(
                    intent_id=intent.intent_id,
                    status=IntentStatus.REJECTED,
                    reason="CAPACITY_BLOCKED",
                )
            if plan.order_type is OrderType.LIMIT:
                return await self._reserve_limit(
                    session, intent, plan, account, position, quantity, now
                )
            return await self._fill_market(
                session, intent, plan, account, position, quantity, price, now
            )

    def _revalidate(
        self,
        plan: TradePlan,
        intent: ExecutionIntent,
        bbo: BestBidAsk,
        now: datetime,
        state_version: int,
    ) -> str | None:
        if plan.status is not PlanStatus.ACTIVE or now >= plan.expires_at:
            return "plan_not_active_or_expired"
        if state_version != intent.state_version or plan.state_version != intent.state_version:
            return "state_version_changed"
        if (
            not bbo.tradable
            or bbo.data_quality is not DataQuality.FRESH
            or now - bbo.received_at > self.freshness_ttl
        ):
            return "core_market_data_stale_or_untradable"
        price = bbo.ask if plan.side is OrderSide.BUY else bbo.bid
        if not plan.entry_zone.contains(price):
            return "price_outside_entry_zone"
        return None

    def _capacity_blocked(
        self, account: AccountRecord, position: PositionRecord | None, plan: TradePlan, price: float
    ) -> bool:
        # Account row is already locked. Current position plus this order must remain under 20% equity.
        equity = account.cash_balance + ((position.quantity * price) if position else 0)
        if plan.side is OrderSide.BUY:
            cost = plan.intended_notional * (1 + self.fee_rate)
            exposure = (position.quantity * price if position else 0) + plan.intended_notional
            return (
                cost > account.cash_balance - account.reserved_cash
                or plan.intended_notional > equity * 0.10
                or exposure > equity * 0.20
            )
        return position is None or plan.intended_notional / price > position.quantity

    async def _reserve_limit(
        self,
        session: AsyncSession,
        intent: ExecutionIntent,
        plan: TradePlan,
        account: AccountRecord,
        position: PositionRecord | None,
        quantity: float,
        now: datetime,
    ) -> ExecutionResult:
        order_id = stable_id("order", intent.intent_id)
        reserve_cash = plan.intended_notional if plan.side is OrderSide.BUY else 0
        reserve_quantity = quantity if plan.side is OrderSide.SELL else 0
        account.reserved_cash += reserve_cash
        session.add(
            ExecutionIntentRecord(
                intent_id=intent.intent_id,
                plan_id=intent.plan_id,
                instrument_id=intent.instrument_id,
                run_mode=intent.run_mode,
                state_version=intent.state_version,
                status=IntentStatus.EXECUTED,
                reason=None,
                created_at=now,
            )
        )
        session.add(
            PaperOrderRecord(
                order_id=order_id,
                intent_id=intent.intent_id,
                plan_id=intent.plan_id,
                instrument_id=intent.instrument_id,
                run_mode=intent.run_mode,
                side=plan.side,
                order_type=plan.order_type,
                status=OrderStatus.OPEN,
                quantity=quantity,
                limit_price=plan.entry_zone.upper
                if plan.side is OrderSide.BUY
                else plan.entry_zone.lower,
                reserved_cash=reserve_cash,
                reserved_quantity=reserve_quantity,
                created_at=now,
            )
        )
        return ExecutionResult(
            intent_id=intent.intent_id, status=IntentStatus.EXECUTED, order_id=order_id
        )

    async def _fill_market(
        self,
        session: AsyncSession,
        intent: ExecutionIntent,
        plan: TradePlan,
        account: AccountRecord,
        position: PositionRecord | None,
        quantity: float,
        price: float,
        now: datetime,
    ) -> ExecutionResult:
        order_id, fill_id = (
            stable_id("order", intent.intent_id),
            stable_id("fill", intent.intent_id),
        )
        gross, fee = price * quantity, price * quantity * self.fee_rate
        trade_id: str | None = position.trade_id if position else None
        realized = 0.0
        if plan.side is OrderSide.BUY:
            account.cash_balance -= gross + fee
            if position is None:
                trade_id = stable_id("trade", intent.run_mode, intent.instrument_id, fill_id)
                position = PositionRecord(
                    position_id=stable_id("pos", intent.run_mode, intent.instrument_id),
                    run_mode=intent.run_mode,
                    instrument_id=intent.instrument_id,
                    quantity=quantity,
                    average_cost=price,
                    realized_pnl=0,
                    trade_id=trade_id,
                    updated_at=now,
                )
                session.add(position)
                session.add(
                    TradeRecord(
                        trade_id=trade_id,
                        run_mode=intent.run_mode,
                        instrument_id=intent.instrument_id,
                        status="OPEN",
                        opened_at=now,
                        closed_at=None,
                    )
                )
            else:
                position.average_cost = ((position.quantity * position.average_cost) + gross) / (
                    position.quantity + quantity
                )
                position.quantity += quantity
                position.updated_at = now
            cash_delta, entry_type = -(gross + fee), "BUY_FILL"
        else:
            assert position is not None
            realized = (price - position.average_cost) * quantity - fee
            position.quantity -= quantity
            position.realized_pnl += realized
            position.updated_at = now
            account.realized_pnl += realized
            account.cash_balance += gross - fee
            if position.quantity <= 1e-12:
                position.quantity = 0
                position.average_cost = 0
                if trade_id:
                    await session.execute(
                        update(TradeRecord)
                        .where(TradeRecord.trade_id == trade_id)
                        .values(status="CLOSED", closed_at=now)
                    )
            cash_delta, entry_type = gross - fee, "SELL_FILL"
        account.updated_at = now
        session.add(
            ExecutionIntentRecord(
                intent_id=intent.intent_id,
                plan_id=intent.plan_id,
                instrument_id=intent.instrument_id,
                run_mode=intent.run_mode,
                state_version=intent.state_version,
                status=IntentStatus.EXECUTED,
                reason=None,
                created_at=now,
            )
        )
        session.add(
            PaperOrderRecord(
                order_id=order_id,
                intent_id=intent.intent_id,
                plan_id=intent.plan_id,
                instrument_id=intent.instrument_id,
                run_mode=intent.run_mode,
                side=plan.side,
                order_type=plan.order_type,
                status=OrderStatus.FILLED,
                quantity=quantity,
                limit_price=None,
                reserved_cash=0,
                reserved_quantity=0,
                created_at=now,
            )
        )
        session.add(
            FillRecord(
                fill_id=fill_id,
                order_id=order_id,
                intent_id=intent.intent_id,
                price=price,
                quantity=quantity,
                fee=fee,
                created_at=now,
            )
        )
        session.add(
            LedgerEntryRecord(
                entry_id=stable_id("ledger", fill_id),
                account_id=account.account_id,
                fill_id=fill_id,
                entry_type=entry_type,
                cash_delta=cash_delta,
                fee=fee,
                created_at=now,
                payload={
                    "order_id": order_id,
                    "instrument_id": intent.instrument_id,
                    "realized_pnl": realized,
                },
            )
        )
        for event_type, aggregate in (
            ("ORDER_FILLED", order_id),
            ("POSITION_CHANGED", position.position_id),
        ):
            session.add(
                OutboxRecord(
                    outbox_id=stable_id("outbox", event_type, aggregate, fill_id),
                    aggregate_id=aggregate,
                    event_type=event_type,
                    payload={"fill_id": fill_id, "instrument_id": intent.instrument_id},
                    created_at=now,
                )
            )
        if self.after_settlement:
            self.after_settlement()
        return ExecutionResult(
            intent_id=intent.intent_id,
            status=IntentStatus.EXECUTED,
            order_id=order_id,
            fill_id=fill_id,
        )

    async def reconciliation(self, run_mode: RunMode) -> dict[str, float | bool]:
        async with self.sessions() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == run_mode)
            )
            reserved = await session.scalar(
                select(func.coalesce(func.sum(PaperOrderRecord.reserved_cash), 0)).where(
                    PaperOrderRecord.run_mode == run_mode,
                    PaperOrderRecord.status == OrderStatus.OPEN,
                )
            )
            return {
                "reserved_cash_matches_open_buys": bool(
                    account and abs(account.reserved_cash - float(reserved)) < 1e-8
                ),
                "available_cash": (account.cash_balance - account.reserved_cash)
                if account
                else 0.0,
            }
