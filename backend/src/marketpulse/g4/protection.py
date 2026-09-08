from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    AccountRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
)
from marketpulse.g3.models import (
    BestBidAsk,
    DataQuality,
    ExecutionResult,
    IntentStatus,
    OrderSide,
    OrderStatus,
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
    ProtectionOutcome,
    ProtectionTrigger,
)
from .planning import load_active_plan

TOLERANCE = 1e-12


class PositionProtectionService:
    """Stop-loss / take-profit protection and every risk-reducing exit path.

    Protection never waits for AI, never goes through the AI queue, and always fills at the
    current executable best bid. Stop and TP levels are trigger prices, not fill prices.
    """

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        execution: PaperExecutionService,
        incidents: IncidentManager,
        health: HealthRegistry,
        *,
        clock: Clock | None = None,
        freshness_ttl: timedelta = timedelta(seconds=5),
    ) -> None:
        self.sessions = sessions
        self.execution = execution
        self.incidents = incidents
        self.health = health
        self.clock = clock or SystemClock()
        self.freshness_ttl = freshness_ttl
        # Test-only controlled-interleaving seam. Production leaves it unset.
        self.after_risk_reducing_account_lock: (
            Callable[[RunMode, str], Awaitable[None]] | None
        ) = None
        self.after_risk_reducing_orders_lock: (
            Callable[[RunMode, str], Awaitable[None]] | None
        ) = None

    # ------------------------------------------------------------------ evaluation

    async def evaluate(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk | None = None,
        *,
        now: datetime | None = None,
    ) -> ProtectionOutcome:
        """Evaluate SL/TP for one open position. Data staleness fails closed, never fabricates."""
        now = now or self.clock.now()
        quote = bbo or await self.execution.bbo_for(instrument_id)
        if not self._fresh(quote, now):
            self.health.set(
                HealthComponent.CORE_MARKET_DATA.value,
                HealthStatus.UNAVAILABLE.value,
                instrument_id=instrument_id,
            )
            await self.incidents.open(
                incident_type=IncidentType.CORE_DATA_STALE,
                run_mode=run_mode,
                reason="core_market_data_stale",
                instrument_id=instrument_id,
                payload={"received_at": quote.received_at.isoformat()},
            )
            return ProtectionOutcome(
                instrument_id=instrument_id,
                triggered=False,
                reason="CORE_MARKET_DATA_STALE",
            )
        self.health.set(
            HealthComponent.CORE_MARKET_DATA.value,
            HealthStatus.HEALTHY.value,
            instrument_id=instrument_id,
        )
        await self.incidents.resolve_type(
            incident_type=IncidentType.CORE_DATA_STALE,
            run_mode=run_mode,
            instrument_id=instrument_id,
        )

        async with self.sessions() as session:
            position = await session.scalar(
                select(PositionRecord).where(
                    PositionRecord.run_mode == run_mode,
                    PositionRecord.instrument_id == instrument_id,
                )
            )
            if position is None or position.quantity <= TOLERANCE:
                return ProtectionOutcome(
                    instrument_id=instrument_id, triggered=False, reason="NO_POSITION"
                )
            plan = await load_active_plan(session, run_mode, instrument_id)
            if plan is None:
                await self.incidents.open(
                    incident_type=IncidentType.POSITION_UNPROTECTED,
                    run_mode=run_mode,
                    reason="open_position_without_active_plan",
                    instrument_id=instrument_id,
                    payload={"quantity": position.quantity},
                    session=session,
                )
                await session.commit()
                return ProtectionOutcome(
                    instrument_id=instrument_id, triggered=False, reason="POSITION_UNPROTECTED"
                )
            trigger = self._trigger(quote.bid, plan)
            if trigger is ProtectionTrigger.NONE:
                return ProtectionOutcome(
                    instrument_id=instrument_id, triggered=False, trigger=trigger, reason="HOLD"
                )
        exit_reason = (
            ExitReason.STOP_LOSS
            if trigger is ProtectionTrigger.STOP_LOSS
            else ExitReason.TAKE_PROFIT
        )
        return await self.close_position(
            run_mode,
            instrument_id,
            quote,
            exit_reason=exit_reason,
            event_type=(
                PositionEventType.SL_TRIGGERED
                if trigger is ProtectionTrigger.STOP_LOSS
                else PositionEventType.TP_TRIGGERED
            ),
            trigger=trigger,
            now=now,
        )

    # ------------------------------------------------------------------ exit paths

    async def manual_close(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk | None = None,
        *,
        now: datetime | None = None,
    ) -> ProtectionOutcome:
        """Operator full close. Allowed under PAUSED / SAFE_MODE / EMERGENCY_STOP."""
        return await self.close_position(
            run_mode,
            instrument_id,
            bbo,
            exit_reason=ExitReason.MANUAL_CLOSE,
            event_type=PositionEventType.MANUAL_CLOSE,
            now=now,
        )

    async def close_position(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk | None = None,
        *,
        exit_reason: ExitReason,
        event_type: PositionEventType,
        quantity: float | None = None,
        trigger: ProtectionTrigger = ProtectionTrigger.NONE,
        now: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> ProtectionOutcome:
        """One atomic transaction: cancel pending adds, exit at fresh bid, write audit events."""
        now = now or self.clock.now()
        quote = bbo or await self.execution.bbo_for(instrument_id)
        if not self._fresh(quote, now):
            await self.incidents.open(
                incident_type=IncidentType.CORE_DATA_STALE,
                run_mode=run_mode,
                reason="risk_reducing_exit_blocked_by_stale_data",
                instrument_id=instrument_id,
            )
            return ProtectionOutcome(
                instrument_id=instrument_id, triggered=False, reason="CORE_MARKET_DATA_STALE"
            )

        if session is not None:
            return await self._close_position_in(
                session,
                run_mode,
                instrument_id,
                quote,
                exit_reason=exit_reason,
                event_type=event_type,
                quantity=quantity,
                trigger=trigger,
                now=now,
            )
        async with self.sessions() as inner, inner.begin():
            return await self._close_position_in(
                inner,
                run_mode,
                instrument_id,
                quote,
                exit_reason=exit_reason,
                event_type=event_type,
                quantity=quantity,
                trigger=trigger,
                now=now,
            )

    async def _close_position_in(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        instrument_id: str,
        quote: BestBidAsk,
        *,
        exit_reason: ExitReason,
        event_type: PositionEventType,
        quantity: float | None,
        trigger: ProtectionTrigger,
        now: datetime,
    ) -> ProtectionOutcome:
        # The complete canonical risk-reducing order is risk-increasing Order(s) -> Account ->
        # Position(s). G3 cancel/limit-fill paths start with Order, so Account first here would
        # invert their Order -> Account edge while protection cancels pending BUYs.
        risk_increasing_orders = await self._lock_risk_increasing_orders(
            session, run_mode, instrument_id
        )
        if self.after_risk_reducing_orders_lock is not None:
            await self.after_risk_reducing_orders_lock(run_mode, instrument_id)
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == run_mode).with_for_update()
        )
        if account is None:
            raise RuntimeError("account_not_bootstrapped")
        if self.after_risk_reducing_account_lock is not None:
            await self.after_risk_reducing_account_lock(run_mode, instrument_id)
        position = await session.scalar(
            select(PositionRecord)
            .where(
                PositionRecord.run_mode == run_mode,
                PositionRecord.instrument_id == instrument_id,
            )
            .with_for_update()
        )
        if position is None or position.quantity <= TOLERANCE:
            return ProtectionOutcome(
                instrument_id=instrument_id, triggered=False, reason="NO_POSITION"
            )
        plan = await load_active_plan(session, run_mode, instrument_id)
        plan_id = plan.plan_id if plan else ""
        plan_version = plan.plan_version if plan else 0

        # A stop-loss or force-close must invalidate every pending risk-increasing BUY first,
        # otherwise a stale add limit order could re-open the position after the exit.
        cancelled = await self._cancel_risk_increasing(
            session, run_mode, instrument_id, now, orders=risk_increasing_orders
        )

        exit_quantity = position.quantity if quantity is None else min(quantity, position.quantity)
        intent_id = stable_id(
            "exit", run_mode, instrument_id, plan_id, plan_version, exit_reason, exit_quantity
        )

        async def on_settled(
            inner: AsyncSession, order: PaperOrderRecord, fill_id: str
        ) -> None:
            self._add_event(
                inner,
                run_mode=run_mode,
                instrument_id=instrument_id,
                position_id=position.position_id,
                plan_id=plan_id or None,
                order_id=order.order_id,
                fill_id=fill_id,
                event_type=event_type,
                dedupe_key=f"protection:{plan_id}:{plan_version}:{exit_reason}:{intent_id}",
                payload={
                    "trigger": trigger.value,
                    "exit_reason": exit_reason,
                    "quantity": order.quantity,
                    "best_bid": quote.bid,
                    "stop_loss": plan.stop_loss if plan else None,
                    "take_profit": plan.take_profit if plan else None,
                    "cancelled_order_ids": cancelled,
                },
                now=now,
            )
            self._add_event(
                inner,
                run_mode=run_mode,
                instrument_id=instrument_id,
                position_id=position.position_id,
                plan_id=plan_id or None,
                order_id=order.order_id,
                fill_id=fill_id,
                event_type=PositionEventType.CLOSE,
                dedupe_key=f"close:{intent_id}",
                payload={"exit_reason": exit_reason, "quantity": order.quantity},
                now=now,
            )

        result: ExecutionResult = await self.execution.execute_risk_reducing_exit(
            intent_id=intent_id,
            plan_id=plan_id,
            instrument_id=instrument_id,
            run_mode=run_mode,
            quantity=exit_quantity,
            exit_reason=exit_reason,
            now=now,
            on_settled=on_settled,
            session=session,
        )
        if result.status is not IntentStatus.EXECUTED:
            return ProtectionOutcome(
                instrument_id=instrument_id,
                triggered=False,
                trigger=trigger,
                reason=result.reason or "EXIT_REJECTED",
                cancelled_order_ids=cancelled,
            )
        return ProtectionOutcome(
            instrument_id=instrument_id,
            triggered=True,
            trigger=trigger,
            exit_reason=exit_reason,
            reason=None,
            order_id=result.order_id,
            fill_id=result.fill_id,
            cancelled_order_ids=cancelled,
        )

    async def risk_reducing_exit(
        self,
        run_mode: RunMode,
        instrument_id: str,
        bbo: BestBidAsk,
        *,
        exit_reason: ExitReason,
        event_type: PositionEventType,
        quantity: float | None = None,
        now: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> ProtectionOutcome:
        """Shared exit path for AI REDUCE / AI CLOSE and recovery stop breaches."""
        return await self.close_position(
            run_mode,
            instrument_id,
            bbo,
            exit_reason=exit_reason,
            event_type=event_type,
            quantity=quantity,
            now=now,
            session=session,
        )

    # ------------------------------------------------------------------ helpers

    def _fresh(self, bbo: BestBidAsk, now: datetime) -> bool:
        return (
            bbo.tradable
            and bbo.data_quality is DataQuality.FRESH
            and (now - bbo.received_at.astimezone(UTC)).total_seconds()
            <= self.freshness_ttl.total_seconds()
        )

    @staticmethod
    def _trigger(best_bid: float, plan: TradePlan) -> ProtectionTrigger:
        if best_bid <= plan.stop_loss:
            return ProtectionTrigger.STOP_LOSS
        if best_bid >= plan.take_profit:
            return ProtectionTrigger.TAKE_PROFIT
        return ProtectionTrigger.NONE

    async def _cancel_risk_increasing(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        instrument_id: str,
        now: datetime,
        *,
        orders: list[PaperOrderRecord] | None = None,
    ) -> list[str]:
        if orders is None:
            orders = await self._lock_risk_increasing_orders(session, run_mode, instrument_id)
        cancelled: list[str] = []
        for order in orders:
            result = await self.execution.cancel_order(order.order_id, now, session=session)
            if result.cancelled:
                cancelled.append(order.order_id)
        return cancelled

    async def _lock_risk_increasing_orders(
        self,
        session: AsyncSession,
        run_mode: RunMode,
        instrument_id: str,
    ) -> list[PaperOrderRecord]:
        """Lock cancellable BUYs before Account for the shared G3/G4 lock graph."""
        return list(
            (
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(
                        PaperOrderRecord.run_mode == run_mode,
                        PaperOrderRecord.instrument_id == instrument_id,
                        PaperOrderRecord.side == OrderSide.BUY,
                        PaperOrderRecord.status == OrderStatus.OPEN,
                    )
                    .order_by(
                        PaperOrderRecord.created_at.asc(),
                        PaperOrderRecord.order_id.asc(),
                    )
                    .with_for_update()
                )
            ).all()
        )

    @staticmethod
    def _add_event(
        session: AsyncSession,
        *,
        run_mode: RunMode,
        instrument_id: str,
        position_id: str | None,
        plan_id: str | None,
        order_id: str | None,
        fill_id: str | None,
        event_type: PositionEventType,
        dedupe_key: str,
        payload: dict,
        now: datetime,
    ) -> None:
        session.add(
            PositionEventRecord(
                event_id=stable_id("pevt", event_type, dedupe_key),
                run_mode=run_mode,
                instrument_id=instrument_id,
                position_id=position_id,
                plan_id=plan_id,
                order_id=order_id,
                fill_id=fill_id,
                event_type=event_type,
                dedupe_key=dedupe_key,
                payload=payload,
                created_at=now,
            )
        )
