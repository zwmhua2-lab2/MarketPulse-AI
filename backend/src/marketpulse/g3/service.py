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

from marketpulse.clock import Clock, SystemClock
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
    OrderCancelResult,
    OrderSide,
    OrderStatus,
    OrderType,
    PlanStatus,
    RiskGate,
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

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()

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
        now = now or self.clock.now()
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
        self,
        ttl: timedelta = timedelta(minutes=5),
        single_order_cap: float = 0.10,
        clock: Clock | None = None,
    ) -> None:
        self.ttl = ttl
        self.single_order_cap = single_order_cap
        self.clock = clock or SystemClock()
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
        now = now or self.clock.now()
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
        clock: Clock | None = None,
    ) -> None:
        self.sessions, self.provider, self.model = sessions, provider, model
        self.prompt_version, self.schema_version = prompt_version, schema_version
        self.clock = clock or SystemClock()

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
            except Exception as exc:
                if getattr(exc, "replay_record_missing", False):
                    raise
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
                    created_at=self.clock.now(),
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
        risk_gate: RiskGate | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.sessions, self.bbo_for, self.state_version_for = sessions, bbo_for, state_version_for
        self.initial_balance, self.fee_rate, self.slippage_bps, self.freshness_ttl = (
            initial_balance,
            fee_rate,
            slippage_bps,
            freshness_ttl,
        )
        # G4 injects the system risk gate; `None` preserves the accepted G3 standalone behaviour.
        self.risk_gate = risk_gate
        self.clock = clock or SystemClock()
        self.after_settlement: Callable[[], None] | None = None
        # `bbo_for` is an upstream-owned, in-process latest-market-state accessor.  Execution
        # never performs exchange I/O itself.  A bounded lookup makes that boundary explicit:
        # a miswired provider must fail closed rather than hold settlement locks indefinitely.
        self.action_time_lookup_timeout = 0.25
        # Test-only deterministic interleaving seam; production leaves it unset.
        self.before_order_lock: Callable[[], Awaitable[None]] | None = None

    async def bootstrap_account(self, run_mode: RunMode) -> None:
        now = self.clock.now()
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
        self,
        intent: ExecutionIntent,
        plan: TradePlan,
        now: datetime | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> ExecutionResult:
        """Execute one intent. When `session` is supplied the caller owns the transaction."""
        now = now or self.clock.now()
        if session is not None:
            return await self._execute_once(intent, plan, now, session=session)
        try:
            return await self._execute_once(intent, plan, now)
        except IntegrityError:
            async with self.sessions() as fallback:
                order = await fallback.scalar(
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
        self,
        intent: ExecutionIntent,
        plan: TradePlan,
        now: datetime,
        session: AsyncSession | None = None,
    ) -> ExecutionResult:
        if session is None:
            async with self.sessions() as inner, inner.begin():
                return await self._execute_once(intent, plan, now, session=inner)
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
        gate_reason = await self._risk_gate_reason(session, intent, plan.side, now)
        if gate_reason is not None:
            session.add(
                ExecutionIntentRecord(
                    intent_id=intent.intent_id,
                    plan_id=intent.plan_id,
                    instrument_id=intent.instrument_id,
                    run_mode=intent.run_mode,
                    state_version=intent.state_version,
                    status=IntentStatus.REJECTED,
                    reason=gate_reason,
                    created_at=now,
                )
            )
            return ExecutionResult(
                intent_id=intent.intent_id, status=IntentStatus.REJECTED, reason=gate_reason
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
            select(AccountRecord).where(AccountRecord.run_mode == intent.run_mode).with_for_update()
        )
        if account is None:
            raise RuntimeError("account_not_bootstrapped")
        price = (
            (bbo.ask * (1 + self.slippage_bps / 10_000))
            if plan.side is OrderSide.BUY
            else (bbo.bid * (1 - self.slippage_bps / 10_000))
        )
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord)
                    .where(PositionRecord.run_mode == intent.run_mode)
                    .with_for_update()
                )
            ).all()
        )
        position = next(
            (item for item in positions if item.instrument_id == intent.instrument_id), None
        )
        limit_price = plan.entry_zone.lower if plan.side is OrderSide.BUY else plan.entry_zone.upper
        if plan.order_type is OrderType.LIMIT:
            price = limit_price
        quantity = plan.intended_notional / price
        equity_and_marks = await self._execution_equity(account, positions, bbo, now)
        if equity_and_marks is None:
            session.add(
                ExecutionIntentRecord(
                    intent_id=intent.intent_id,
                    plan_id=intent.plan_id,
                    instrument_id=intent.instrument_id,
                    run_mode=intent.run_mode,
                    state_version=intent.state_version,
                    status=IntentStatus.REJECTED,
                    reason="CORE_POSITION_MARK_STALE",
                    created_at=now,
                )
            )
            return ExecutionResult(
                intent_id=intent.intent_id,
                status=IntentStatus.REJECTED,
                reason="CORE_POSITION_MARK_STALE",
            )
        equity, marks = equity_and_marks
        pending_buy_exposure = await self._open_buy_exposure(
            session, intent.run_mode, intent.instrument_id
        )
        open_sell_reserved = await self._open_sell_reserved_quantity(
            session, intent.run_mode, intent.instrument_id
        )
        if self._capacity_blocked(
            account,
            position,
            plan,
            quantity,
            equity,
            (position.quantity * marks.get(intent.instrument_id, 0.0)) if position else 0.0,
            pending_buy_exposure,
            open_sell_reserved,
        ):
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

    async def _risk_gate_reason(
        self,
        session: AsyncSession,
        intent: ExecutionIntent,
        side: OrderSide,
        now: datetime,
    ) -> str | None:
        """Admit risk-increasing BUY only. Risk-reducing exits are never blocked here."""
        if self.risk_gate is None or side is not OrderSide.BUY:
            return None
        return await self.risk_gate.evaluate(
            session,
            run_mode=intent.run_mode,
            instrument_id=intent.instrument_id,
            side=side,
            plan_id=intent.plan_id,
            now=now,
        )

    async def _risk_gate_reason_for_order(
        self,
        session: AsyncSession,
        order: PaperOrderRecord,
        now: datetime,
    ) -> str | None:
        """Admit risk-increasing limit BUY fills only; SELL risk reduction is never gated."""
        if self.risk_gate is None or order.side != OrderSide.BUY:
            return None
        return await self.risk_gate.evaluate(
            session,
            run_mode=order.run_mode,
            instrument_id=order.instrument_id,
            side=OrderSide(order.side),
            plan_id=order.plan_id,
            now=now,
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
        self,
        account: AccountRecord,
        position: PositionRecord | None,
        plan: TradePlan,
        quantity: float,
        equity: float,
        current_symbol_market_value: float,
        pending_buy_exposure: float,
        open_sell_reserved: float,
    ) -> bool:
        """Apply the bounded G3 capacity policy while the account row is locked."""
        if plan.side is OrderSide.BUY:
            cost = plan.intended_notional * (1 + self.fee_rate)
            exposure = current_symbol_market_value + pending_buy_exposure + plan.intended_notional
            return (
                cost > account.cash_balance - account.reserved_cash
                or plan.intended_notional > equity * 0.10
                or exposure > equity * 0.20
            )
        return position is None or quantity > position.quantity - open_sell_reserved + 1e-12

    def _is_fresh_bbo(self, bbo: BestBidAsk, now: datetime) -> bool:
        return (
            bbo.tradable
            and bbo.data_quality is DataQuality.FRESH
            and now - bbo.received_at <= self.freshness_ttl
        )

    async def _execution_equity(
        self,
        account: AccountRecord,
        positions: list[PositionRecord],
        current_bbo: BestBidAsk,
        now: datetime,
    ) -> tuple[float, dict[str, float]] | None:
        """Return fresh-mark equity for every held symbol, or fail closed."""
        marks: dict[str, float] = {}
        for position in positions:
            if position.quantity <= 1e-12:
                continue
            bbo = (
                current_bbo
                if position.instrument_id == current_bbo.instrument_id
                else await self.bbo_for(position.instrument_id)
            )
            if bbo.instrument_id != position.instrument_id or not self._is_fresh_bbo(bbo, now):
                return None
            marks[position.instrument_id] = (bbo.bid + bbo.ask) / 2
        return account.cash_balance + sum(
            position.quantity * marks[position.instrument_id]
            for position in positions
            if position.quantity > 1e-12
        ), marks

    async def _open_buy_exposure(
        self, session: AsyncSession, run_mode: RunMode, instrument_id: str
    ) -> float:
        value = await session.scalar(
            select(
                func.coalesce(
                    func.sum(PaperOrderRecord.quantity * PaperOrderRecord.limit_price), 0.0
                )
            ).where(
                PaperOrderRecord.run_mode == run_mode,
                PaperOrderRecord.instrument_id == instrument_id,
                PaperOrderRecord.status == OrderStatus.OPEN,
                PaperOrderRecord.side == OrderSide.BUY,
            )
        )
        return float(value)

    async def _open_sell_reserved_quantity(
        self, session: AsyncSession, run_mode: RunMode, instrument_id: str
    ) -> float:
        value = await session.scalar(
            select(func.coalesce(func.sum(PaperOrderRecord.reserved_quantity), 0.0)).where(
                PaperOrderRecord.run_mode == run_mode,
                PaperOrderRecord.instrument_id == instrument_id,
                PaperOrderRecord.status == OrderStatus.OPEN,
                PaperOrderRecord.side == OrderSide.SELL,
            )
        )
        return float(value)

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
        reserve_cash = (
            plan.intended_notional * (1 + self.fee_rate) if plan.side is OrderSide.BUY else 0
        )
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
                limit_price=plan.entry_zone.lower
                if plan.side is OrderSide.BUY
                else plan.entry_zone.upper,
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
        order_id = stable_id("order", intent.intent_id)
        order = PaperOrderRecord(
            order_id=order_id,
            intent_id=intent.intent_id,
            plan_id=intent.plan_id,
            instrument_id=intent.instrument_id,
            run_mode=intent.run_mode,
            side=plan.side,
            order_type=plan.order_type,
            status=OrderStatus.OPEN,
            quantity=quantity,
            limit_price=None,
            reserved_cash=0,
            reserved_quantity=0,
            created_at=now,
        )
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
        session.add(order)
        return await self._settle_order(session, account, position, order, price, now)

    async def execute_risk_reducing_exit(
        self,
        *,
        intent_id: str,
        plan_id: str,
        instrument_id: str,
        run_mode: RunMode,
        quantity: float,
        exit_reason: str,
        now: datetime | None = None,
        on_settled: Callable[[AsyncSession, PaperOrderRecord, str], Awaitable[None]] | None = None,
        session: AsyncSession | None = None,
    ) -> ExecutionResult:
        """G4 risk-reducing SELL at the current executable Best Bid.

        Stop/TP are trigger prices only: the fill always uses a fresh BBO bid, never the stop,
        the take-profit or a snapshot price. Nothing is fabricated when data is stale or when
        the position is already flat.
        """
        now = now or self.clock.now()
        if session is not None:
            return await self._risk_reducing_exit_once(
                intent_id=intent_id,
                plan_id=plan_id,
                instrument_id=instrument_id,
                run_mode=run_mode,
                quantity=quantity,
                exit_reason=exit_reason,
                now=now,
                on_settled=on_settled,
                session=session,
            )
        async with self.sessions() as inner, inner.begin():
            return await self._risk_reducing_exit_once(
                intent_id=intent_id,
                plan_id=plan_id,
                instrument_id=instrument_id,
                run_mode=run_mode,
                quantity=quantity,
                exit_reason=exit_reason,
                now=now,
                on_settled=on_settled,
                session=inner,
            )

    async def _risk_reducing_exit_once(
        self,
        *,
        intent_id: str,
        plan_id: str,
        instrument_id: str,
        run_mode: RunMode,
        quantity: float,
        exit_reason: str,
        now: datetime,
        on_settled: Callable[[AsyncSession, PaperOrderRecord, str], Awaitable[None]] | None,
        session: AsyncSession,
    ) -> ExecutionResult:
        existing = await session.scalar(
            select(PaperOrderRecord).where(PaperOrderRecord.intent_id == intent_id)
        )
        if existing:
            fill = await session.scalar(select(FillRecord).where(FillRecord.intent_id == intent_id))
            return ExecutionResult(
                intent_id=intent_id,
                status=IntentStatus.EXECUTED,
                reason="duplicate_intent",
                order_id=existing.order_id,
                fill_id=fill.fill_id if fill else None,
            )
        bbo = await self.bbo_for(instrument_id)
        if bbo.instrument_id != instrument_id or not self._is_fresh_bbo(bbo, now):
            return ExecutionResult(
                intent_id=intent_id,
                status=IntentStatus.REJECTED,
                reason="CORE_MARKET_DATA_STALE",
            )
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == run_mode).with_for_update()
        )
        if account is None:
            raise RuntimeError("account_not_bootstrapped")
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord)
                    .where(PositionRecord.run_mode == run_mode)
                    .with_for_update()
                )
            ).all()
        )
        position = next((item for item in positions if item.instrument_id == instrument_id), None)
        if position is None or position.quantity <= 1e-12 or quantity <= 1e-12:
            return ExecutionResult(
                intent_id=intent_id, status=IntentStatus.REJECTED, reason="POSITION_NOT_OPEN"
            )
        price = bbo.bid * (1 - self.slippage_bps / 10_000)
        order = PaperOrderRecord(
            order_id=stable_id("order", intent_id),
            intent_id=intent_id,
            plan_id=plan_id,
            instrument_id=instrument_id,
            run_mode=run_mode,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.OPEN,
            quantity=min(quantity, position.quantity),
            limit_price=None,
            reserved_cash=0,
            reserved_quantity=0,
            created_at=now,
        )
        session.add(
            ExecutionIntentRecord(
                intent_id=intent_id,
                plan_id=plan_id,
                instrument_id=instrument_id,
                run_mode=run_mode,
                state_version=0,
                status=IntentStatus.EXECUTED,
                reason=exit_reason,
                created_at=now,
            )
        )
        session.add(order)
        return await self._settle_order(
            session,
            account,
            position,
            order,
            price,
            now,
            exit_reason=exit_reason,
            on_settled=on_settled,
        )

    async def _settle_order(
        self,
        session: AsyncSession,
        account: AccountRecord,
        position: PositionRecord | None,
        order: PaperOrderRecord,
        price: float,
        now: datetime,
        *,
        exit_reason: str | None = None,
        on_settled: Callable[[AsyncSession, PaperOrderRecord, str], Awaitable[None]] | None = None,
    ) -> ExecutionResult:
        """Persist one all-or-none fill and every G3 settlement record atomically."""
        if order.status != OrderStatus.OPEN:
            raise RuntimeError("only_open_orders_can_settle")
        fill_id = stable_id("fill", order.intent_id)
        gross, fee = price * order.quantity, price * order.quantity * self.fee_rate
        trade_id: str | None = position.trade_id if position else None
        realized = 0.0
        if order.side == OrderSide.BUY:
            if account.reserved_cash + 1e-12 < order.reserved_cash:
                raise RuntimeError("reserved_cash_underflow")
            account.reserved_cash -= order.reserved_cash
            if abs(account.reserved_cash) <= 1e-12:
                account.reserved_cash = 0.0
            account.cash_balance -= gross + fee
            if position is None or position.quantity <= 1e-12:
                trade_id = stable_id("trade", order.run_mode, order.instrument_id, fill_id)
                if position is None:
                    position = PositionRecord(
                        position_id=stable_id("pos", order.run_mode, order.instrument_id),
                        run_mode=order.run_mode,
                        instrument_id=order.instrument_id,
                        quantity=order.quantity,
                        average_cost=price,
                        realized_pnl=0,
                        trade_id=trade_id,
                        updated_at=now,
                    )
                    session.add(position)
                else:
                    position.quantity = order.quantity
                    position.average_cost = price
                    position.trade_id = trade_id
                    position.updated_at = now
                session.add(
                    TradeRecord(
                        trade_id=trade_id,
                        run_mode=order.run_mode,
                        instrument_id=order.instrument_id,
                        status="OPEN",
                        opened_at=now,
                        closed_at=None,
                    )
                )
            else:
                position.average_cost = ((position.quantity * position.average_cost) + gross) / (
                    position.quantity + order.quantity
                )
                position.quantity += order.quantity
                position.updated_at = now
            cash_delta, entry_type = -(gross + fee), "BUY_FILL"
        else:
            if position is None or order.quantity > position.quantity + 1e-12:
                raise RuntimeError("sell_position_underflow")
            realized = (price - position.average_cost) * order.quantity - fee
            position.quantity -= order.quantity
            position.realized_pnl += realized
            position.updated_at = now
            account.realized_pnl += realized
            account.cash_balance += gross - fee
            if position.quantity <= 1e-12:
                position.quantity = 0
                position.average_cost = 0
                if trade_id:
                    values: dict[str, object] = {"status": "CLOSED", "closed_at": now}
                    if exit_reason is not None:
                        values["exit_reason"] = exit_reason
                    await session.execute(
                        update(TradeRecord).where(TradeRecord.trade_id == trade_id).values(**values)
                    )
            cash_delta, entry_type = gross - fee, "SELL_FILL"
        order.status = OrderStatus.FILLED
        order.reserved_cash = 0.0
        order.reserved_quantity = 0.0
        account.updated_at = now
        session.add(
            FillRecord(
                fill_id=fill_id,
                order_id=order.order_id,
                intent_id=order.intent_id,
                price=price,
                quantity=order.quantity,
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
                    "order_id": order.order_id,
                    "instrument_id": order.instrument_id,
                    "realized_pnl": realized,
                },
            )
        )
        for event_type, aggregate in (
            ("ORDER_FILLED", order.order_id),
            ("POSITION_CHANGED", position.position_id),
        ):
            session.add(
                OutboxRecord(
                    outbox_id=stable_id("outbox", event_type, aggregate, fill_id),
                    aggregate_id=aggregate,
                    event_type=event_type,
                    payload={"fill_id": fill_id, "instrument_id": order.instrument_id},
                    created_at=now,
                )
            )
        if on_settled is not None:
            await on_settled(session, order, fill_id)
        if self.after_settlement:
            self.after_settlement()
        return ExecutionResult(
            intent_id=order.intent_id,
            status=IntentStatus.EXECUTED,
            order_id=order.order_id,
            fill_id=fill_id,
        )

    async def process_open_orders(
        self, run_mode: RunMode, bbo: BestBidAsk, now: datetime | None = None
    ) -> list[ExecutionResult]:
        """Process candidate OPEN limits; final qualification uses action-time facts only."""
        candidate_now = now or self.clock.now()
        if not self._is_fresh_bbo(bbo, candidate_now):
            return []
        async with self.sessions() as session:
            order_ids = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord.order_id).where(
                            PaperOrderRecord.run_mode == run_mode,
                            PaperOrderRecord.instrument_id == bbo.instrument_id,
                            PaperOrderRecord.order_type == OrderType.LIMIT,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                    )
                ).all()
            )
        results: list[ExecutionResult] = []
        for order_id in order_ids:
            result = await self._process_open_order(order_id, bbo, now)
            if result is not None:
                results.append(result)
        return results

    async def _process_open_order(
        self, order_id: str, bbo: BestBidAsk, now: datetime | None
    ) -> ExecutionResult | None:
        async with self.sessions() as session, session.begin():
            # Preview without a row lock so the G4 gate can take the global runtime-control lock
            # first. Every caller then re-reads the order with FOR UPDATE before mutating it,
            # and the gate's lock makes the preview observation atomic against control changes.
            preview = await session.scalar(
                select(PaperOrderRecord).where(PaperOrderRecord.order_id == order_id)
            )
            if (
                preview is None
                or preview.status != OrderStatus.OPEN
                or preview.order_type != OrderType.LIMIT
                or preview.instrument_id != bbo.instrument_id
            ):
                return None
            # Preserve the global G4 order: RuntimeControl -> Order -> Plan -> Account -> Positions.
            # This is an ordering/admission preview only; the gate is evaluated again using
            # action-time facts before settlement.
            candidate_now = now or self.clock.now()
            gate_reason = await self._risk_gate_reason_for_order(session, preview, candidate_now)
            if gate_reason is not None:
                return ExecutionResult(
                    intent_id=preview.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason=gate_reason,
                    order_id=preview.order_id,
                )
            if self.before_order_lock is not None:
                await self.before_order_lock()
            order = await session.scalar(
                select(PaperOrderRecord)
                .where(PaperOrderRecord.order_id == order_id)
                .execution_options(populate_existing=True)
                .with_for_update()
            )
            if (
                order is None
                or order.status != OrderStatus.OPEN
                or order.order_type != OrderType.LIMIT
                or order.instrument_id != bbo.instrument_id
            ):
                return None
            if order.limit_price is None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="LIMIT_PRICE_MISSING",
                    order_id=order.order_id,
                )
            plan_record = await session.scalar(
                select(TradePlanRecord)
                .where(TradePlanRecord.plan_id == order.plan_id)
                .execution_options(populate_existing=True)
                .with_for_update()
            )
            account = await session.scalar(
                select(AccountRecord)
                .where(AccountRecord.run_mode == order.run_mode)
                .execution_options(populate_existing=True)
                .with_for_update()
            )
            if account is None:
                raise RuntimeError("account_not_bootstrapped")
            positions = list(
                (
                    await session.scalars(
                        select(PositionRecord)
                        .where(PositionRecord.run_mode == order.run_mode)
                        .execution_options(populate_existing=True)
                        .with_for_update()
                    )
                ).all()
            )
            position = next(
                (item for item in positions if item.instrument_id == order.instrument_id), None
            )
            action_bbos = await self._load_action_time_bbos(order.instrument_id, positions)
            if action_bbos is None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="ACTION_TIME_BBO_UNAVAILABLE",
                    order_id=order.order_id,
                )
            action_bbo = action_bbos[order.instrument_id]
            state_version = await self._action_time_state_version(order.instrument_id)
            if state_version is None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="ACTION_TIME_STATE_UNAVAILABLE",
                    order_id=order.order_id,
                )
            # Capture the execution clock only after all bounded current-state lookups.  The
            # following guards and the settlement write share this transaction and lock set.
            action_now = now or self.clock.now()
            gate_reason = await self._risk_gate_reason_for_order(session, order, action_now)
            if gate_reason is not None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason=gate_reason,
                    order_id=order.order_id,
                )
            # The runtime-control row is now locked by this transaction.  Refresh time once
            # more so final market/plan/capacity qualification is adjacent to settlement.
            action_now = now or self.clock.now()
            if action_bbo.instrument_id != order.instrument_id or not self._is_fresh_bbo(
                action_bbo, action_now
            ):
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="CORE_MARKET_DATA_STALE",
                    order_id=order.order_id,
                )
            equity_and_marks = self._equity_from_action_time_bbos(
                account, positions, action_bbos, action_now
            )
            if equity_and_marks is None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="CORE_POSITION_MARK_STALE",
                    order_id=order.order_id,
                )
            plan_guard_reason = self._limit_fill_plan_guard(
                order, plan_record, action_bbo, action_now, state_version
            )
            if plan_guard_reason is not None:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason=plan_guard_reason,
                    order_id=order.order_id,
                )
            price = action_bbo.ask if order.side == OrderSide.BUY else action_bbo.bid
            eligible = (order.side == OrderSide.BUY and price <= order.limit_price) or (
                order.side == OrderSide.SELL and price >= order.limit_price
            )
            if not eligible:
                return None
            equity, marks = equity_and_marks
            if order.side == OrderSide.BUY:
                pending_exposure = await self._open_buy_exposure(
                    session, order.run_mode, order.instrument_id
                )
                position_value = (
                    position.quantity * marks.get(order.instrument_id, 0.0) if position else 0.0
                )
                if (
                    price * order.quantity > equity * 0.10
                    or position_value + pending_exposure > equity * 0.20
                    or account.reserved_cash + 1e-12 < order.reserved_cash
                ):
                    return ExecutionResult(
                        intent_id=order.intent_id,
                        status=IntentStatus.EXECUTED,
                        reason="CAPACITY_BLOCKED",
                        order_id=order.order_id,
                    )
            elif position is None or order.quantity > position.quantity + 1e-12:
                return ExecutionResult(
                    intent_id=order.intent_id,
                    status=IntentStatus.EXECUTED,
                    reason="SELL_RESERVATION_EXCEEDS_POSITION",
                    order_id=order.order_id,
                )
            return await self._settle_order(session, account, position, order, price, action_now)

    def _limit_fill_plan_guard(
        self,
        order: PaperOrderRecord,
        plan_record: TradePlanRecord | None,
        bbo: BestBidAsk,
        now: datetime,
        state_version: int,
    ) -> str | None:
        """Fail closed on any order/plan drift before a risk-changing limit fill."""
        if plan_record is None:
            return "PLAN_MISSING"
        if (
            plan_record.run_mode != order.run_mode
            or plan_record.instrument_id != order.instrument_id
        ):
            return "PLAN_ORDER_MISMATCH"
        if plan_record.status != PlanStatus.ACTIVE:
            return "PLAN_NOT_ACTIVE"
        if now >= plan_record.expires_at:
            return "PLAN_EXPIRED"
        if state_version != plan_record.state_version:
            return "STATE_VERSION_CHANGED"
        try:
            plan = TradePlan.model_validate(plan_record.payload)
        except Exception:  # noqa: BLE001 - invalid durable plan evidence must fail closed
            return "PLAN_PAYLOAD_INVALID"
        if (
            plan.plan_id != plan_record.plan_id
            or plan.run_mode != order.run_mode
            or plan.instrument_id != order.instrument_id
        ):
            return "PLAN_PAYLOAD_MISMATCH"
        if order.side == OrderSide.BUY:
            price = bbo.ask
            if price <= plan.stop_loss:
                return "BUY_STOP_LOSS_BREACHED"
            if not plan.entry_zone.contains(price):
                return "BUY_PRICE_OUTSIDE_ENTRY_ZONE"
        return None

    async def _load_action_time_bbo(self, instrument_id: str) -> BestBidAsk | None:
        try:
            return await asyncio.wait_for(
                self.bbo_for(instrument_id), timeout=self.action_time_lookup_timeout
            )
        except TimeoutError:
            return None
        except Exception as exc:
            if getattr(exc, "replay_record_missing", False):
                raise
            return None

    async def _load_action_time_bbos(
        self, instrument_id: str, positions: list[PositionRecord]
    ) -> dict[str, BestBidAsk] | None:
        instrument_ids = {instrument_id}
        instrument_ids.update(
            position.instrument_id for position in positions if position.quantity > 1e-12
        )
        quotes: dict[str, BestBidAsk] = {}
        for current_instrument_id in sorted(instrument_ids):
            quote = await self._load_action_time_bbo(current_instrument_id)
            if quote is None:
                return None
            quotes[current_instrument_id] = quote
        return quotes

    async def _action_time_state_version(self, instrument_id: str) -> int | None:
        try:
            return await asyncio.wait_for(
                self.state_version_for(instrument_id), timeout=self.action_time_lookup_timeout
            )
        except TimeoutError:
            return None
        except Exception as exc:
            if getattr(exc, "replay_record_missing", False):
                raise
            return None

    def _equity_from_action_time_bbos(
        self,
        account: AccountRecord,
        positions: list[PositionRecord],
        bbo_by_instrument: dict[str, BestBidAsk],
        now: datetime,
    ) -> tuple[float, dict[str, float]] | None:
        marks: dict[str, float] = {}
        for position in positions:
            if position.quantity <= 1e-12:
                continue
            bbo = bbo_by_instrument.get(position.instrument_id)
            if (
                bbo is None
                or bbo.instrument_id != position.instrument_id
                or not self._is_fresh_bbo(bbo, now)
            ):
                return None
            marks[position.instrument_id] = (bbo.bid + bbo.ask) / 2
        return account.cash_balance + sum(
            position.quantity * marks[position.instrument_id]
            for position in positions
            if position.quantity > 1e-12
        ), marks

    async def revalidate_open_buy_capacity(
        self,
        order: PaperOrderRecord,
        bbo: BestBidAsk,
        now: datetime,
        *,
        session: AsyncSession,
    ) -> list[str]:
        """Re-evaluate G3 cash/capacity facts for one recovered OPEN BUY.

        The caller owns the transaction and order lock. This deliberately excludes the G4
        runtime-state gate because RECOVERING is a transient fill block, not a cancellation
        reason. It reuses the same account/position/equity mathematics as the fill path.
        """
        issues: list[str] = []
        if order.side != OrderSide.BUY or order.status != OrderStatus.OPEN:
            return issues
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == order.run_mode).with_for_update()
        )
        if account is None:
            return ["ACCOUNT_MISSING"]
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord)
                    .where(PositionRecord.run_mode == order.run_mode)
                    .with_for_update()
                )
            ).all()
        )
        equity_and_marks = await self._execution_equity(account, positions, bbo, now)
        if equity_and_marks is None:
            return ["CORE_POSITION_MARK_STALE"]
        equity, marks = equity_and_marks
        position = next(
            (item for item in positions if item.instrument_id == order.instrument_id), None
        )
        pending_exposure = await self._open_buy_exposure(
            session, order.run_mode, order.instrument_id
        )
        position_value = (
            position.quantity * marks.get(order.instrument_id, 0.0) if position else 0.0
        )
        if order.limit_price is None:
            issues.append("LIMIT_PRICE_MISSING")
        if bbo.ask * order.quantity > equity * 0.10 + 1e-12:
            issues.append("SINGLE_ORDER_CAP_EXCEEDED")
        if position_value + pending_exposure > equity * 0.20 + 1e-12:
            issues.append("SYMBOL_EXPOSURE_CAP_EXCEEDED")
        if account.reserved_cash + 1e-12 < order.reserved_cash:
            issues.append("RESERVATION_MISSING")
        return issues

    async def cancel_order(
        self,
        order_id: str,
        now: datetime | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> OrderCancelResult:
        """Cancel an OPEN order and release its reservation in the same transaction.

        When `session` is supplied the caller owns the transaction, which lets G4 cancel every
        risk-increasing order and flip the runtime control state in one atomic commit.
        """
        now = now or self.clock.now()
        if session is not None:
            return await self._cancel_order_once(order_id, now, session)
        async with self.sessions() as inner, inner.begin():
            return await self._cancel_order_once(order_id, now, inner)

    async def _cancel_order_once(
        self, order_id: str, now: datetime, session: AsyncSession
    ) -> OrderCancelResult:
        order = await session.scalar(
            select(PaperOrderRecord).where(PaperOrderRecord.order_id == order_id).with_for_update()
        )
        if order is None:
            raise ValueError("order_not_found")
        if order.status != OrderStatus.OPEN:
            return OrderCancelResult(
                order_id=order_id,
                status=OrderStatus(order.status),
                cancelled=False,
                reason="order_not_open",
            )
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == order.run_mode).with_for_update()
        )
        if account is None:
            raise RuntimeError("account_not_bootstrapped")
        if account.reserved_cash + 1e-12 < order.reserved_cash:
            raise RuntimeError("reserved_cash_underflow")
        account.reserved_cash -= order.reserved_cash
        if abs(account.reserved_cash) <= 1e-12:
            account.reserved_cash = 0.0
        account.updated_at = now
        order.status = OrderStatus.CANCELLED
        order.reserved_cash = 0.0
        order.reserved_quantity = 0.0
        session.add(
            OutboxRecord(
                outbox_id=stable_id("outbox", "ORDER_CANCELLED", order.order_id),
                aggregate_id=order.order_id,
                event_type="ORDER_CANCELLED",
                payload={"instrument_id": order.instrument_id},
                created_at=now,
            )
        )
        return OrderCancelResult(order_id=order_id, status=OrderStatus.CANCELLED, cancelled=True)

    async def reconciliation(self, run_mode: RunMode) -> dict[str, Any]:
        """Return G3 accounting invariants and diagnostics without attempting repair."""
        tolerance = 1e-8
        async with self.sessions() as session:
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == run_mode)
            )
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(PaperOrderRecord.run_mode == run_mode)
                    )
                ).all()
            )
            fills = list(
                (
                    await session.scalars(
                        select(FillRecord)
                        .join(PaperOrderRecord, FillRecord.order_id == PaperOrderRecord.order_id)
                        .where(PaperOrderRecord.run_mode == run_mode)
                    )
                ).all()
            )
            ledgers = list(
                (
                    await session.scalars(
                        select(LedgerEntryRecord).where(
                            LedgerEntryRecord.account_id == (account.account_id if account else "")
                        )
                    )
                ).all()
            )
            positions = list(
                (
                    await session.scalars(
                        select(PositionRecord).where(PositionRecord.run_mode == run_mode)
                    )
                ).all()
            )
        diagnostics: list[str] = []
        open_buys = [
            order
            for order in orders
            if order.status == OrderStatus.OPEN and order.side == OrderSide.BUY
        ]
        open_sells = [
            order
            for order in orders
            if order.status == OrderStatus.OPEN and order.side == OrderSide.SELL
        ]
        expected_reserved_cash = sum(order.reserved_cash for order in open_buys)
        reserved_cash_matches_open_buys = bool(
            account and abs(account.reserved_cash - expected_reserved_cash) <= tolerance
        )
        if not reserved_cash_matches_open_buys:
            diagnostics.append("reserved_cash_mismatch")
        positions_by_instrument = {position.instrument_id: position for position in positions}
        open_sell_reserved: dict[str, float] = {}
        for order in open_sells:
            open_sell_reserved[order.instrument_id] = (
                open_sell_reserved.get(order.instrument_id, 0.0) + order.reserved_quantity
            )
        sell_reservations_within_positions = all(
            quantity
            <= (
                positions_by_instrument[instrument].quantity
                if instrument in positions_by_instrument
                else 0.0
            )
            + tolerance
            for instrument, quantity in open_sell_reserved.items()
        )
        if not sell_reservations_within_positions:
            diagnostics.append("open_sell_reservation_exceeds_position")
        orders_by_id = {order.order_id: order for order in orders}
        net_fill_quantity: dict[str, float] = {}
        fill_counts_by_order: dict[str, int] = {}
        for fill in fills:
            order = orders_by_id.get(fill.order_id)
            if order is None:
                diagnostics.append(f"fill_without_order:{fill.fill_id}")
                continue
            multiplier = 1 if order.side == OrderSide.BUY else -1
            net_fill_quantity[order.instrument_id] = (
                net_fill_quantity.get(order.instrument_id, 0.0) + multiplier * fill.quantity
            )
            fill_counts_by_order[fill.order_id] = fill_counts_by_order.get(fill.order_id, 0) + 1
        position_quantities_match_fills = all(
            abs(
                (
                    positions_by_instrument[instrument].quantity
                    if instrument in positions_by_instrument
                    else 0.0
                )
                - quantity
            )
            <= tolerance
            for instrument, quantity in net_fill_quantity.items()
        ) and all(
            abs(position.quantity - net_fill_quantity.get(position.instrument_id, 0.0)) <= tolerance
            for position in positions
        )
        if not position_quantities_match_fills:
            diagnostics.append("position_quantity_mismatch")
        ledger_counts: dict[str, int] = {}
        for ledger in ledgers:
            ledger_counts[ledger.fill_id] = ledger_counts.get(ledger.fill_id, 0) + 1
        fills_have_one_ledger_entry = all(
            ledger_counts.get(fill.fill_id, 0) == 1 for fill in fills
        ) and all(ledger.fill_id in {fill.fill_id for fill in fills} for ledger in ledgers)
        if not fills_have_one_ledger_entry:
            diagnostics.append("fill_ledger_mismatch")
        filled_orders_match_fills = all(
            fill_counts_by_order.get(order.order_id, 0) == 1
            for order in orders
            if order.status == OrderStatus.FILLED
        ) and all(
            orders_by_id.get(fill.order_id) is not None
            and orders_by_id[fill.order_id].status == OrderStatus.FILLED
            and abs(orders_by_id[fill.order_id].quantity - fill.quantity) <= tolerance
            and orders_by_id[fill.order_id].intent_id == fill.intent_id
            for fill in fills
        )
        if not filled_orders_match_fills:
            diagnostics.append("filled_order_fill_mismatch")
        available_cash = (account.cash_balance - account.reserved_cash) if account else 0.0
        available_cash_non_negative = bool(account and available_cash >= -tolerance)
        if not available_cash_non_negative:
            diagnostics.append("available_cash_negative_or_missing_account")
        return {
            "ok": not diagnostics,
            "reserved_cash_matches_open_buys": reserved_cash_matches_open_buys,
            "sell_reservations_within_positions": sell_reservations_within_positions,
            "position_quantities_match_fills": position_quantities_match_fills,
            "available_cash_non_negative": available_cash_non_negative,
            "fills_have_one_ledger_entry": fills_have_one_ledger_entry,
            "filled_orders_match_fills": filled_orders_match_fills,
            "available_cash": available_cash,
            "diagnostics": diagnostics,
        }
