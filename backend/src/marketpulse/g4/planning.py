from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    TradePlanRecord,
)
from marketpulse.g3.models import (
    OrderSide,
    OrderStatus,
    PlanStatus,
    PositionProtectionAuthority,
    RunMode,
    TradePlan,
)
from marketpulse.g3.protection_snapshot import (
    apply_position_protection,
    authority_from_plan,
    clear_position_protection,
    read_position_protection,
)
from marketpulse.g3.service import PaperExecutionService, stable_id

from .models import PositionEventType

DEFAULT_PLAN_TTL = timedelta(minutes=15)


class StalePlanError(RuntimeError):
    """The expected plan is no longer the current ACTIVE plan."""


def derive_followup_plan(
    previous: TradePlan,
    *,
    now: datetime,
    plan_version: int,
    ttl: timedelta = DEFAULT_PLAN_TTL,
    **changes: Any,
) -> TradePlan:
    """Build the next immutable plan version. History is never overwritten in place."""
    payload = previous.model_dump()
    for key in ("plan_id", "created_at", "expires_at", "status", "plan_version"):
        payload.pop(key, None)
    payload.update(changes)
    payload["expires_at"] = now + ttl
    payload["plan_version"] = plan_version
    payload["status"] = PlanStatus.ACTIVE
    payload["created_at"] = now
    fingerprint = stable_id("plan", previous.plan_id, plan_version, *sorted(changes.items()))
    return TradePlan(plan_id=fingerprint, **payload)


class PlanManager:
    """Atomic plan versioning: old plan REPLACED, new plan ACTIVE, stale BUY intents cancelled."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        execution: PaperExecutionService,
        clock: Clock | None = None,
    ) -> None:
        self.sessions = sessions
        self.execution = execution
        self.clock = clock or SystemClock()

    async def replace(
        self,
        *,
        previous: TradePlan,
        next_plan: TradePlan,
        event_type: PositionEventType = PositionEventType.PLAN_REPLACED,
        now: datetime | None = None,
        session: AsyncSession | None = None,
        cancel_stale_risk_increasing: bool = True,
    ) -> tuple[TradePlan, list[str]]:
        if session is not None:
            return await self._replace_in(
                session,
                previous=previous,
                next_plan=next_plan,
                event_type=event_type,
                now=now or self.clock.now(),
                cancel_stale_risk_increasing=cancel_stale_risk_increasing,
            )
        now = now or self.clock.now()
        async with self.sessions() as inner, inner.begin():
            return await self._replace_in(
                inner,
                previous=previous,
                next_plan=next_plan,
                event_type=event_type,
                now=now,
                cancel_stale_risk_increasing=cancel_stale_risk_increasing,
            )

    async def _replace_in(
        self,
        session: AsyncSession,
        *,
        previous: TradePlan,
        next_plan: TradePlan,
        event_type: PositionEventType,
        now: datetime,
        cancel_stale_risk_increasing: bool,
    ) -> tuple[TradePlan, list[str]]:
        if (
            previous.run_mode != next_plan.run_mode
            or previous.instrument_id != next_plan.instrument_id
            or next_plan.plan_version != previous.plan_version + 1
        ):
            raise ValueError("replacement_plan_scope_or_version_invalid")

        replaced = await session.execute(
            update(TradePlanRecord)
            .where(
                TradePlanRecord.plan_id == previous.plan_id,
                TradePlanRecord.run_mode == previous.run_mode,
                TradePlanRecord.instrument_id == previous.instrument_id,
                TradePlanRecord.plan_version == previous.plan_version,
                TradePlanRecord.status == PlanStatus.ACTIVE,
            )
            .values(status=PlanStatus.REPLACED)
            .returning(TradePlanRecord.plan_id)
        )
        if replaced.scalar_one_or_none() is None:
            raise StalePlanError("expected_active_plan_changed")
        session.add(
            TradePlanRecord(
                plan_id=next_plan.plan_id,
                snapshot_id=next_plan.snapshot_id,
                decision_id=next_plan.decision_id,
                instrument_id=next_plan.instrument_id,
                symbol=next_plan.symbol,
                run_mode=next_plan.run_mode,
                state_version=next_plan.state_version,
                plan_version=next_plan.plan_version,
                status=next_plan.status,
                created_at=next_plan.created_at,
                expires_at=next_plan.expires_at,
                payload=next_plan.model_dump(mode="json"),
            )
        )
        # Surface the partial-unique-index conflict inside the caller-owned transaction. The
        # caller can then roll the whole stale action back instead of overwriting a newer plan.
        await session.flush()
        cancelled: list[str] = []
        if cancel_stale_risk_increasing:
            cancelled = await self.cancel_stale_risk_increasing(
                run_mode=next_plan.run_mode,
                instrument_id=next_plan.instrument_id,
                now=now,
                session=session,
                stale_plan_ids={previous.plan_id},
            )
        # The new version is now the plan that protects this symbol, so the OPEN position's durable
        # authority must move with it. Skipping this would leave a stop-loss update live on the
        # plan while protection kept triggering on the superseded level. Taken last to keep the
        # global lock order (Plan -> ... -> Positions); a replacement that cannot yield a legal
        # authority clears the snapshot and therefore fails closed to POSITION_UNPROTECTED, which
        # is the same verdict `load_valid_long_active_plan` already returns for that plan.
        position = await session.scalar(
            select(PositionRecord)
            .where(
                PositionRecord.run_mode == next_plan.run_mode,
                PositionRecord.instrument_id == next_plan.instrument_id,
            )
            .with_for_update()
        )
        if position is not None and position.quantity > 1e-12:
            authority = authority_from_plan(next_plan)
            if authority is None:
                clear_position_protection(position)
            else:
                apply_position_protection(position, authority, now=now)
        session.add(
            PositionEventRecord(
                event_id=stable_id("pevt", event_type, next_plan.plan_id),
                run_mode=next_plan.run_mode,
                instrument_id=next_plan.instrument_id,
                plan_id=next_plan.plan_id,
                event_type=event_type,
                dedupe_key=f"plan:{next_plan.plan_id}:{event_type}",
                payload={
                    "previous_plan_id": previous.plan_id,
                    "plan_version": next_plan.plan_version,
                    "changes": {
                        "stop_loss": next_plan.stop_loss,
                        "take_profit": next_plan.take_profit,
                        "invalidation": next_plan.invalidation,
                    },
                    "cancelled_order_ids": cancelled,
                },
                created_at=now,
            )
        )
        return next_plan, cancelled

    async def cancel_stale_risk_increasing(
        self,
        *,
        run_mode: RunMode,
        instrument_id: str,
        now: datetime,
        session: AsyncSession,
        stale_plan_ids: set[str] | None = None,
    ) -> list[str]:
        """Cancel OPEN BUY orders whose plan is stale so reservations are never frozen forever."""
        orders = list(
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
                )
            ).all()
        )
        cancelled: list[str] = []
        for order in orders:
            plan = await session.scalar(
                select(TradePlanRecord).where(TradePlanRecord.plan_id == order.plan_id)
            )
            stale = (
                plan is None
                or plan.status != PlanStatus.ACTIVE
                or now >= plan.expires_at
                or (stale_plan_ids is not None and order.plan_id in stale_plan_ids)
            )
            if not stale:
                continue
            result = await self.execution.cancel_order(order.order_id, now, session=session)
            if result.cancelled:
                cancelled.append(order.order_id)
        return cancelled


async def load_active_plan(
    session: AsyncSession,
    run_mode: RunMode,
    instrument_id: str,
    *,
    for_update: bool = False,
) -> TradePlan | None:
    """Load exactly one durable ACTIVE plan whose serialized identity still agrees with its row."""
    statement = select(TradePlanRecord).where(
        TradePlanRecord.run_mode == run_mode,
        TradePlanRecord.instrument_id == instrument_id,
        TradePlanRecord.status == PlanStatus.ACTIVE,
    )
    if for_update:
        statement = statement.with_for_update()
    records = list((await session.scalars(statement)).all())
    if len(records) != 1:
        return None
    record = records[0]
    try:
        plan = TradePlan.model_validate(record.payload)
    except Exception:  # noqa: BLE001 - a corrupt durable plan must fail closed, never guess
        return None
    if (
        plan.plan_id != record.plan_id
        or plan.snapshot_id != record.snapshot_id
        or plan.decision_id != record.decision_id
        or plan.instrument_id != record.instrument_id
        or plan.symbol != record.symbol
        or plan.run_mode != record.run_mode
        or plan.state_version != record.state_version
        or plan.plan_version != record.plan_version
        or plan.status != record.status
        or plan.created_at != record.created_at
        or plan.expires_at != record.expires_at
    ):
        return None
    return plan


def plan_business_errors(plan: TradePlan) -> list[str]:
    """Shared executable plan checks; invalidation text intentionally remains advisory."""
    errors: list[str] = []
    if (
        plan.entry_zone.lower > plan.entry_zone.upper
        or not math.isfinite(plan.stop_loss)
        or not math.isfinite(plan.take_profit)
        or plan.stop_loss >= plan.take_profit
    ):
        errors.append("plan_price_relationship_invalid")
    return errors


async def load_valid_long_active_plan(
    session: AsyncSession,
    run_mode: RunMode,
    instrument_id: str,
    *,
    now: datetime,
    for_update: bool = False,
) -> TradePlan | None:
    """Return an executable ACTIVE plan only when it genuinely protects the current LONG.

    This is the single canonical open-position protection-plan validity contract shared by
    recovery / resume / protection. Every condition must hold, otherwise the plan is not trusted
    and the caller fails closed (POSITION_UNPROTECTED / safe state):

      1. exactly one ACTIVE plan
      2. durable row / serialized payload identity agree
      3. run_mode / instrument scope agree
      4. TTL not expired
      5. entry zone finite / valid
      6. stop_loss finite
      7. take_profit finite
      8. stop_loss < take_profit
      9. TradePlan schema / business validation passes

    NOTE (Acceptance Fix #1 review correction): SymbolStateStore.state_version is the
    *risk-increasing freshness* authority (BUY/ADD, pending risk-increasing orders, fill-time
    revalidation, recovery order revalidation, stale proposal authority). It is NOT an
    open-position protection lifetime authority — normal symbol-state version advancement must
    never invalidate the SL/TP protection of an already-open position, or risk-reducing exits
    would be disabled.
    """
    plan = await load_active_plan(
        session, run_mode, instrument_id, for_update=for_update
    )
    if plan is None or now >= plan.expires_at:
        return None
    if plan_business_errors(plan):
        return None
    return plan


async def resolve_open_position_protection(
    session: AsyncSession,
    position: PositionRecord,
    *,
    now: datetime,
) -> PositionProtectionAuthority | None:
    """The one authority that decides whether this OPEN LONG is protected right now.

    The plan that currently protects the position wins, so every verdict that existed before the
    durable snapshot is preserved unchanged. The durable snapshot is then consulted only when the
    *one* reason the plan is unusable is TTL expiry: an expired plan is the normal end of a short
    planning window and must never leave a real position unprotected, whereas a missing,
    unreadable, identity-inconsistent or business-invalid plan is evidence of a data problem and
    keeps failing closed to POSITION_UNPROTECTED exactly as before.

    `None` means unprotected: callers must open POSITION_UNPROTECTED and allow only risk-reducing
    exits. `authority_from_plan` accepts exactly the levels `plan_business_errors` accepts, so a
    plan that survives the check above always yields an authority.
    """
    plan = await load_valid_long_active_plan(
        session, position.run_mode, position.instrument_id, now=now
    )
    if plan is not None:
        return authority_from_plan(plan)
    durable = read_position_protection(position)
    if durable is None:
        return None
    expired = await load_active_plan(session, position.run_mode, position.instrument_id)
    if expired is None or expired.expires_at > now or plan_business_errors(expired):
        return None
    return durable
