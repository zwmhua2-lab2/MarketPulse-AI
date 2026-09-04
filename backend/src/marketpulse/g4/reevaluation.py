from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    SignalTimelineRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    DecisionSnapshot,
    DecisionStatus,
    ExecutionIntent,
    IntentStatus,
    OrderSide,
    OrderStatus,
    OrderType,
    PriceZone,
    RunMode,
    TradePlan,
)
from marketpulse.g3.service import PaperExecutionService, stable_id
from marketpulse.runtime import HealthRegistry

from .incidents import IncidentManager
from .models import (
    ExitReason,
    HealthComponent,
    HealthStatus,
    IncidentType,
    PositionEventType,
    PositionReevaluation,
    ReevaluationAction,
    ReevaluationOutcome,
)
from .planning import PlanManager, derive_followup_plan, load_active_plan
from .protection import PositionProtectionService
from .provider import (
    REVIEW_PROMPT_VERSION,
    REVIEW_SCHEMA_VERSION,
    PositionReviewPromptBuilder,
    PositionReviewProvider,
)
from .risk_gate import SystemRiskGate


class MeaningfulEventGate:
    """Decide when a position deserves an AI re-evaluation. Never per tick, never per second."""

    def __init__(
        self,
        *,
        min_interval: timedelta = timedelta(seconds=60),
        price_move_pct: float = 0.01,
    ) -> None:
        self.min_interval = min_interval
        self.price_move_pct = price_move_pct
        self._last: dict[tuple[str, str], tuple[datetime, float, int]] = {}

    def should_evaluate(
        self,
        run_mode: RunMode,
        instrument_id: str,
        *,
        now: datetime,
        price: float,
        state_version: int,
        force: bool = False,
    ) -> tuple[bool, str]:
        key = (run_mode, instrument_id)
        previous = self._last.get(key)
        if force or previous is None:
            return True, "no_previous_evaluation" if previous is None else "forced"
        last_at, last_price, last_version = previous
        if state_version != last_version:
            return True, "state_version_changed"
        if now - last_at < self.min_interval:
            return False, "inside_min_interval"
        if last_price > 0 and abs(price - last_price) / last_price >= self.price_move_pct:
            return True, "price_move_threshold"
        return False, "no_meaningful_change"

    def mark(
        self,
        run_mode: RunMode,
        instrument_id: str,
        *,
        now: datetime,
        price: float,
        state_version: int,
    ) -> None:
        self._last[(run_mode, instrument_id)] = (now, price, state_version)


class PositionReevaluationService:
    """Meaningful-event driven AI review of one open position.

    AI proposes; the program decides. A failed, slow or invalid review changes nothing: the
    existing stop-loss and take-profit stay in force.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        provider: PositionReviewProvider,
        plans: PlanManager,
        risk_gate: SystemRiskGate,
        protection: PositionProtectionService,
        incidents: IncidentManager,
        execution: PaperExecutionService,
        health: HealthRegistry,
        *,
        model: str = "g4-position-review",
        prompt_version: str = REVIEW_PROMPT_VERSION,
        schema_version: str = REVIEW_SCHEMA_VERSION,
        timeout_seconds: float | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.provider = provider
        self.plans = plans
        self.risk_gate = risk_gate
        self.protection = protection
        self.incidents = incidents
        self.execution = execution
        self.health = health
        self.model = model
        self.prompt_version = prompt_version
        self.schema_version = schema_version
        self.timeout_seconds = timeout_seconds
        self.clock = clock or SystemClock()
        self.meaningful = MeaningfulEventGate()

    async def evaluate(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk,
        *,
        triggering_event: str = "MANUAL",
        now: datetime | None = None,
        force: bool = False,
    ) -> ReevaluationOutcome:
        now = now or self.clock.now()
        async with self.sessions() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == run_mode,
                    PositionRecord.instrument_id == instrument_id,
                )
            )
            if position is None or position.quantity <= 1e-12:
                return ReevaluationOutcome(
                    instrument_id=instrument_id,
                    action=ReevaluationAction.HOLD,
                    applied=False,
                    reason="NO_OPEN_POSITION",
                )
            plan = await load_active_plan(session, run_mode, instrument_id)
            if plan is None:
                await self.incidents.open(
                    incident_type=IncidentType.POSITION_UNPROTECTED,
                    run_mode=run_mode,
                    reason="position_without_active_plan",
                    instrument_id=instrument_id,
                    session=session,
                )
                await session.commit()
                return ReevaluationOutcome(
                    instrument_id=instrument_id,
                    action=ReevaluationAction.HOLD,
                    applied=False,
                    reason="NO_ACTIVE_PLAN",
                )
            snapshot = await self._build_snapshot(
                session, run_mode, instrument_id, position, plan, bbo, triggering_event, now
            )
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
                    payload=snapshot.model_dump(mode="json"),
                )
            )
            await session.commit()

        prompt = PositionReviewPromptBuilder().build(snapshot)
        review, error = await self._call_provider(snapshot, prompt)
        await self._persist_decision(snapshot, review, error)
        if review is None:
            self.health.set(
                HealthComponent.AI_AUXILIARY.value,
                HealthStatus.DEGRADED.value,
                instrument_id=instrument_id,
            )
            await self.incidents.open(
                incident_type=IncidentType.AI_REEVALUATION_FAILED,
                run_mode=run_mode,
                reason=error or "ai_reevaluation_failed",
                instrument_id=instrument_id,
            )
            return ReevaluationOutcome(
                instrument_id=instrument_id,
                action=ReevaluationAction.HOLD,
                applied=False,
                reason=error or "AI_REEVALUATION_FAILED",
                snapshot_id=snapshot.snapshot_id,
            )
        self.health.set(
            HealthComponent.AI_AUXILIARY.value,
            HealthStatus.HEALTHY.value,
            instrument_id=instrument_id,
        )
        return await self._dispatch(run_mode, instrument_id, plan, review, snapshot, bbo, now)

    # ------------------------------------------------------------------ provider

    async def _call_provider(
        self, snapshot: DecisionSnapshot, prompt: str
    ) -> tuple[PositionReevaluation | None, str | None]:
        try:
            if self.timeout_seconds is None:
                review = await self.provider.review(snapshot, prompt)
            else:
                review = await asyncio.wait_for(
                    self.provider.review(snapshot, prompt), timeout=self.timeout_seconds
                )
        except TimeoutError:
            return None, "AI_TIMEOUT"
        except Exception as exc:  # noqa: BLE001 - provider failure must fail closed, never guess
            return None, f"AI_ERROR:{type(exc).__name__}"
        errors = review.business_errors()
        if errors:
            return None, f"AI_INVALID_BUSINESS:{','.join(errors)}"
        return review, None

    async def _persist_decision(
        self,
        snapshot: DecisionSnapshot,
        review: PositionReevaluation | None,
        error: str | None,
    ) -> str:
        decision_id = stable_id("predecision", snapshot.snapshot_id, self.model)
        async with self.sessions() as session, session.begin():
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
                    status=(
                        DecisionStatus.VALID if review is not None else DecisionStatus.INVALID_SCHEMA
                        if error and error.startswith("AI_ERROR")
                        else DecisionStatus.INVALID_BUSINESS
                    ),
                    raw_prompt="",
                    raw_response=review.model_dump(mode="json") if review else {},
                    error=error,
                    created_at=self.clock.now(),
                )
            )
        return decision_id

    # ------------------------------------------------------------------ snapshot

    async def _build_snapshot(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        instrument_id: str,
        position: PositionRecord,
        plan: TradePlan,
        bbo: BestBidAsk,
        triggering_event: str,
        now: datetime,
    ) -> DecisionSnapshot:
        state_version = int(await self.execution.state_version_for(instrument_id))
        timeline = list(
            (
                await session.scalars(
                    select(SignalTimelineRecord)
                    .where(SignalTimelineRecord.instrument_id == instrument_id)
                    .order_by(SignalTimelineRecord.event_time.desc())
                    .limit(20)
                )
            ).all()
        )
        open_orders = list(
            (
                await session.scalars(
                    select(PaperOrderRecord).where(
                        PaperOrderRecord.run_mode == run_mode,
                        PaperOrderRecord.instrument_id == instrument_id,
                        PaperOrderRecord.status == OrderStatus.OPEN,
                    )
                )
            ).all()
        )
        market_value = position.quantity * bbo.bid
        unrealized = (bbo.bid - position.average_cost) * position.quantity
        trading_context = {
            "instrument_id": instrument_id,
            "position": {
                "position_id": position.position_id,
                "quantity": position.quantity,
                "average_cost": position.average_cost,
                "realized_pnl": position.realized_pnl,
                "trade_id": position.trade_id,
            },
            "market_value": market_value,
            "unrealized_pnl": unrealized,
            "unrealized_pnl_pct": (unrealized / (position.average_cost * position.quantity))
            if position.average_cost > 0 and position.quantity > 0
            else 0.0,
            "active_plan": plan.model_dump(mode="json"),
            "current_stop_loss": plan.stop_loss,
            "current_take_profit": plan.take_profit,
            "current_invalidation": plan.invalidation,
            "triggering_event": triggering_event,
            "open_orders": [
                {
                    "order_id": order.order_id,
                    "side": order.side,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "limit_price": order.limit_price,
                    "reserved_cash": order.reserved_cash,
                    "reserved_quantity": order.reserved_quantity,
                }
                for order in open_orders
            ],
            "account_context": await self._account_context(session, run_mode),
        }
        snapshot_id = stable_id(
            "snap", run_mode, instrument_id, state_version, triggering_event, uuid4().hex
        )
        return DecisionSnapshot(
            snapshot_id=snapshot_id,
            instrument_id=instrument_id,
            symbol=plan.symbol,
            run_mode=run_mode,
            state="OPEN_POSITION",
            state_version=state_version,
            config_version=REVIEW_SCHEMA_VERSION,
            snapshot_version=REVIEW_PROMPT_VERSION,
            created_at=now,
            market_context={
                "best_bid": bbo.bid,
                "best_ask": bbo.ask,
                "bbo_received_at": bbo.received_at.isoformat(),
                "bbo_quality": bbo.data_quality.value,
                "tradable": bbo.tradable,
            },
            market_evolution={
                "timeline": [
                    {
                        "event_id": item.event_id,
                        "signal_type": item.signal_type,
                        "event_time": item.event_time.isoformat(),
                        "strength": item.strength,
                        "symbol_state": item.symbol_state,
                        "state_version": item.state_version,
                        "price": item.price,
                    }
                    for item in reversed(timeline)
                ]
            },
            strategies=[],
            trading_context=trading_context,
        )

    async def _account_context(self, session: AsyncSession, run_mode: RunMode) -> dict[str, Any]:
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == run_mode)
        )
        if account is None:
            return {}
        return {
            "cash_balance": account.cash_balance,
            "reserved_cash": account.reserved_cash,
            "available_cash": account.cash_balance - account.reserved_cash,
            "realized_pnl": account.realized_pnl,
        }

    # ------------------------------------------------------------------ dispatch

    async def _dispatch(
        self,
        run_mode: RunMode,
        instrument_id: str,
        plan: TradePlan,
        review: PositionReevaluation,
        snapshot: DecisionSnapshot,
        bbo: BestBidAsk,
        now: datetime,
    ) -> ReevaluationOutcome:
        action = review.action
        base = ReevaluationOutcome(
            instrument_id=instrument_id,
            action=action,
            applied=False,
            reason=review.reason,
            snapshot_id=snapshot.snapshot_id,
            previous_plan_id=plan.plan_id,
        )
        if action is ReevaluationAction.HOLD:
            await self._record(
                run_mode,
                instrument_id,
                plan.plan_id,
                PositionEventType.AI_REEVALUATION,
                {"action": action.value, "reason": review.reason},
                now,
            )
            return base.model_copy(update={"applied": True})

        if action is ReevaluationAction.ADD:
            return await self._add(run_mode, instrument_id, plan, review, snapshot, bbo, now)

        if action is ReevaluationAction.REDUCE:
            quantity = await self._position_quantity(run_mode, instrument_id)
            quantity = quantity * (review.reduce_pct or 0.0)
            outcome = await self.protection.risk_reducing_exit(
                run_mode,
                instrument_id,
                bbo,
                exit_reason=ExitReason.AI_REDUCE,
                event_type=PositionEventType.REDUCE,
                quantity=quantity,
                now=now,
            )
            await self._record(
                run_mode,
                instrument_id,
                plan.plan_id,
                PositionEventType.REDUCE,
                {
                    "action": action.value,
                    "reduce_pct": review.reduce_pct,
                    "reason": review.reason,
                    "exit_reason": outcome.exit_reason.value if outcome.exit_reason else None,
                    "fill_id": outcome.fill_id,
                },
                now,
            )
            return base.model_copy(
                update={
                    "applied": outcome.triggered,
                    "reason": outcome.reason,
                    "order_id": outcome.order_id,
                    "fill_id": outcome.fill_id,
                }
            )

        if action is ReevaluationAction.CLOSE:
            outcome = await self.protection.risk_reducing_exit(
                run_mode,
                instrument_id,
                bbo,
                exit_reason=ExitReason.AI_CLOSE,
                event_type=PositionEventType.CLOSE,
                now=now,
            )
            await self._record(
                run_mode,
                instrument_id,
                plan.plan_id,
                PositionEventType.CLOSE,
                {
                    "action": action.value,
                    "reason": review.reason,
                    "exit_reason": outcome.exit_reason.value if outcome.exit_reason else None,
                    "fill_id": outcome.fill_id,
                },
                now,
            )
            return base.model_copy(
                update={
                    "applied": outcome.triggered,
                    "reason": outcome.reason,
                    "order_id": outcome.order_id,
                    "fill_id": outcome.fill_id,
                }
            )

        if action is ReevaluationAction.CANCEL_ADD:
            cancelled = await self._cancel_adds(run_mode, instrument_id, now)
            await self._record(
                run_mode,
                instrument_id,
                plan.plan_id,
                PositionEventType.CANCEL_ADD,
                {"action": action.value, "cancelled_order_ids": cancelled},
                now,
            )
            return base.model_copy(update={"applied": True, "cancelled_order_ids": cancelled})

        return await self._update_plan(run_mode, instrument_id, plan, review, now)

    async def _add(
        self,
        run_mode: RunMode,
        instrument_id: str,
        plan: TradePlan,
        review: PositionReevaluation,
        snapshot: DecisionSnapshot,
        bbo: BestBidAsk,
        now: datetime,
    ) -> ReevaluationOutcome:
        base = ReevaluationOutcome(
            instrument_id=instrument_id,
            action=ReevaluationAction.ADD,
            applied=False,
            reason=review.reason,
            snapshot_id=snapshot.snapshot_id,
            previous_plan_id=plan.plan_id,
        )
        allowed, gate_reason = await self.risk_gate.check(
            run_mode, instrument_id, plan_id=plan.plan_id, now=now
        )
        if not allowed:
            await self._record(
                run_mode,
                instrument_id,
                plan.plan_id,
                PositionEventType.RISK_BLOCKED,
                {"action": "ADD", "reason": gate_reason},
                now,
            )
            return base.model_copy(update={"reason": gate_reason})
        state_version = int(await self.execution.state_version_for(instrument_id))
        next_plan = derive_followup_plan(
            plan,
            now=now,
            plan_version=plan.plan_version + 1,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            entry_zone=PriceZone(lower=bbo.bid * 0.995, upper=bbo.ask * 1.005),
            intended_notional=float(review.intended_notional or 0.0),
            state_version=state_version,
            snapshot_id=snapshot.snapshot_id,
        )
        intent = ExecutionIntent(
            intent_id=stable_id("add", run_mode, instrument_id, next_plan.plan_id),
            plan_id=next_plan.plan_id,
            instrument_id=instrument_id,
            run_mode=run_mode,
            state_version=state_version,
            created_at=now,
        )
        # One transaction: plan replacement + buy execution. A rejection rolls the plan back so
        # an ADD can never leave the position without its stop-loss / take-profit.
        async with self.sessions() as session, session.begin():
            _, cancelled = await self.plans.replace(
                previous=plan,
                next_plan=next_plan,
                event_type=PositionEventType.PLAN_REPLACED,
                now=now,
                session=session,
            )
            result = await self.execution.execute(intent, next_plan, now, session=session)
            if result.status is not IntentStatus.EXECUTED:
                raise RuntimeError(f"add_not_executed:{result.reason}")
            self._add_event(
                session,
                run_mode=run_mode,
                instrument_id=instrument_id,
                plan_id=next_plan.plan_id,
                order_id=result.order_id,
                fill_id=result.fill_id,
                event_type=PositionEventType.ADD,
                dedupe_key=f"add:{intent.intent_id}",
                payload={
                    "reason": review.reason,
                    "notional": review.intended_notional,
                    "cancelled_order_ids": cancelled,
                },
                now=now,
            )
        return base.model_copy(
            update={
                "applied": True,
                "plan_id": next_plan.plan_id,
                "order_id": result.order_id,
                "fill_id": result.fill_id,
                "cancelled_order_ids": cancelled,
            }
        )

    async def _update_plan(
        self,
        run_mode: RunMode,
        instrument_id: str,
        plan: TradePlan,
        review: PositionReevaluation,
        now: datetime,
    ) -> ReevaluationOutcome:
        changes: dict[str, Any] = {}
        event_type = PositionEventType.PLAN_UPDATED
        if review.action is ReevaluationAction.UPDATE_STOP:
            changes["stop_loss"] = float(review.stop_loss)
        elif review.action is ReevaluationAction.UPDATE_TP:
            changes["take_profit"] = float(review.take_profit)
        elif review.action is ReevaluationAction.UPDATE_INVALIDATION:
            changes["invalidation"] = review.invalidation
        else:  # REPLACE_PLAN
            event_type = PositionEventType.PLAN_REPLACED
            changes = {
                "stop_loss": float(review.stop_loss),
                "take_profit": float(review.take_profit),
                "invalidation": review.invalidation,
                "entry_zone": PriceZone(
                    lower=float(review.entry_zone_lower),
                    upper=float(review.entry_zone_upper),
                ),
            }
        next_plan = derive_followup_plan(
            plan, now=now, plan_version=plan.plan_version + 1, **changes
        )
        _, cancelled = await self.plans.replace(
            previous=plan,
            next_plan=next_plan,
            event_type=event_type,
            now=now,
        )
        return ReevaluationOutcome(
            instrument_id=instrument_id,
            action=review.action,
            applied=True,
            reason=review.reason,
            plan_id=next_plan.plan_id,
            previous_plan_id=plan.plan_id,
            cancelled_order_ids=cancelled,
        )

    # ------------------------------------------------------------------ helpers

    async def _position_quantity(self, run_mode: RunMode, instrument_id: str) -> float:
        async with self.sessions() as session:
            value = await session.scalar(
                select(func.coalesce(PositionRecord.quantity, 0.0)).where(
                    PositionRecord.run_mode == run_mode,
                    PositionRecord.instrument_id == instrument_id,
                )
            )
        return float(value or 0.0)

    async def _cancel_adds(
        self, run_mode: RunMode, instrument_id: str, now: datetime
    ) -> list[str]:
        async with self.sessions() as session, session.begin():
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == run_mode,
                            PaperOrderRecord.instrument_id == instrument_id,
                            PaperOrderRecord.side == OrderSide.BUY,
                            PaperOrderRecord.status == OrderStatus.OPEN,
                        )
                    )
                ).all()
            )
            cancelled: list[str] = []
            for order in orders:
                result = await self.execution.cancel_order(order.order_id, now, session=session)
                if result.cancelled:
                    cancelled.append(order.order_id)
        return cancelled

    async def _record(
        self,
        run_mode: RunMode,
        instrument_id: str,
        plan_id: str | None,
        event_type: PositionEventType,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        async with self.sessions() as session, session.begin():
            self._add_event(
                session,
                run_mode=run_mode,
                instrument_id=instrument_id,
                plan_id=plan_id,
                order_id=None,
                fill_id=None,
                event_type=event_type,
                dedupe_key=stable_id("pevt", event_type, run_mode, instrument_id, now.isoformat()),
                payload=payload,
                now=now,
            )

    @staticmethod
    def _add_event(
        session: AsyncSession,
        *,
        run_mode: RunMode,
        instrument_id: str,
        plan_id: str | None,
        order_id: str | None,
        fill_id: str | None,
        event_type: PositionEventType,
        dedupe_key: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        session.add(
            PositionEventRecord(
                event_id=stable_id("pevt", event_type, dedupe_key),
                run_mode=run_mode,
                instrument_id=instrument_id,
                plan_id=plan_id,
                order_id=order_id,
                fill_id=fill_id,
                event_type=event_type,
                dedupe_key=dedupe_key,
                payload=payload,
                created_at=now,
            )
        )
