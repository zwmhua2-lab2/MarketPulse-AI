"""SE-02B: append-only attribution lineage from an opportunity into the trading chain.

The chain this module observes is the already-accepted one::

    Opportunity Evidence -> DecisionSnapshot -> AI Decision -> Trade Plan
        -> Risk Admission -> Execution Intent -> Order / Fill -> Trade / Economic Result

Attribution *observes*. It is never a second Risk engine, Execution engine, trade
state machine or accounting authority: every business decision stays with the
component that already owns it, and this module only appends the lineage fact
inside that component's own transaction.

Frozen properties (task §10):

* append-only -- the only writer is ``append_attribution_event``;
* deterministic -- identity is content addressed over the exact subject, event
  type, payload and occurrence time;
* idempotent -- re-emitting the identical event returns ``IDEMPOTENT``;
* linked to the exact ``opportunity_id`` (and ``evidence_id`` where applicable);
* restart-safe -- a deferred order's lineage is resolved from durable facts by
  :func:`link_for_durable_order`, never from a live in-memory recorder;
* non-authoritative -- no existing business or economic fact is rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    EdgeAttributionEventRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.g3.models import DecisionStatus, Direction

from .capture import OPPORTUNITY_FAMILY_STRATEGY_ID
from .identity import evidence_id as derive_evidence_id
from .models import (
    EVIDENCE_CONTRACT_VERSION,
    AttributionSubjectType,
    OpportunityIdentity,
    build_attribution_event,
)
from .repository import append_attribution_event

# --- Accepted SE-02 event vocabulary ----------------------------------------------------

# Authorities that can refuse a risk-increasing action. A rejection keeps the
# exact authority so the two refusals are never collapsed into a generic
# "REJECTED".
RISK_AUTHORITY_SYSTEM_RISK_GATE = "SystemRiskGate"
RISK_AUTHORITY_CAPACITY_POLICY = "CapacityPolicy"


class AttributionEventType(StrEnum):
    """Event vocabulary of the accepted SE-02 attribution contract."""

    # AI
    AI_NOT_REACHED = "AI_NOT_REACHED"
    AI_ACCEPTED_LONG = "AI_ACCEPTED_LONG"
    AI_REJECTED_WAIT = "AI_REJECTED_WAIT"
    AI_REJECTED_SHORT_ANALYSIS_ONLY = "AI_REJECTED_SHORT_ANALYSIS_ONLY"
    AI_NOT_SELECTED_THIS_FAMILY = "AI_NOT_SELECTED_THIS_FAMILY"
    AI_INVALID = "AI_INVALID"
    AI_STALE = "AI_STALE"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    # Plan
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_NOT_CREATED = "PLAN_NOT_CREATED"
    # Risk
    RISK_ACCEPTED = "RISK_ACCEPTED"
    RISK_REJECTED = "RISK_REJECTED"
    # Execution
    EXECUTION_REJECTED = "EXECUTION_REJECTED"
    ORDER_OPEN = "ORDER_OPEN"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    BUY_FILLED = "BUY_FILLED"
    # Economic lineage
    TRADE_OPEN = "TRADE_OPEN"
    TRADE_CLOSED = "TRADE_CLOSED"
    ACTUAL_ECONOMIC_RESULT_AVAILABLE = "ACTUAL_ECONOMIC_RESULT_AVAILABLE"


@dataclass(frozen=True)
class OpportunityLink:
    """The exact opportunity an attribution event belongs to.

    ``evidence_id`` is the captured evidence revision the lineage descends from.
    It is deterministic, not looked up: given the accepted identity contract the
    first runtime revision of an opportunity always has the same evidence id, so
    a caller can link the full lineage without an extra query.
    """

    opportunity_id: str
    evidence_id: str | None = None


def link_for_opportunity(
    opportunity: OpportunityIdentity, *, evidence_revision: int = 1
) -> OpportunityLink:
    """Build the deterministic link for one opportunity revision.

    This re-derives the accepted ``evidence_id`` formula instead of inventing a
    new one; the value equals what ``build_evidence_revision`` produced for that
    revision.
    """

    return OpportunityLink(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=derive_evidence_id(
            opportunity_id=opportunity.opportunity_id,
            evidence_revision=evidence_revision,
            evidence_contract_version=EVIDENCE_CONTRACT_VERSION,
        ),
    )


def family_is_selected(*, selected_strategy_ids: list[str]) -> bool:
    """Did the accepted AI result explicitly select the opportunity family?

    ``AI_ACCEPTED_LONG`` must never be inferred from the mere existence of a later
    TradePlan (task §7.4), and it must never be inferred from the family strategy
    being *present in the snapshot* either: the snapshot only proves that the AI
    could see the strategy, not that it selected it. Only an explicit entry in the
    provider's ``selected_strategy_ids`` counts (task §7.1 - §7.2).
    """

    return OPPORTUNITY_FAMILY_STRATEGY_ID in selected_strategy_ids


async def link_for_durable_order(
    session: AsyncSession, order_id: str
) -> OpportunityLink | None:
    """Resolve one durable order's exact opportunity lineage from durable facts.

    This is the restart-safe replacement for "the in-memory recorder that created
    the order is still alive" (task §8.1 - §8.3). A deferred LIMIT order can fill
    long after the process that opened it is gone, so the linkage is read back
    from durable facts instead:

    * the ``ORDER_OPEN`` attribution fact of *this* ``order_id`` -- written in the
      same transaction that made the order durable, and therefore the exact
      observed linkage rather than a re-derivation;
    * verified against the accepted ``edge_opportunity_evidence`` revision it
      names, so lineage can only descend from an opportunity that was really
      captured.

    Returns ``None`` when the order has no recorded linkage, when the recorded
    linkage is missing or names several different opportunities, or when the
    named evidence revision does not exist. Callers must treat ``None`` as "this
    order has no attributable opportunity" and must never fabricate a link.
    """

    rows = list(
        (
            await session.scalars(
                select(EdgeAttributionEventRecord).where(
                    EdgeAttributionEventRecord.subject_type
                    == AttributionSubjectType.EXECUTION.value,
                    EdgeAttributionEventRecord.event_type
                    == AttributionEventType.ORDER_OPEN.value,
                    EdgeAttributionEventRecord.subject_id == order_id,
                )
            )
        ).all()
    )
    links = {(row.opportunity_id, row.evidence_id) for row in rows}
    if len(links) != 1:
        # No ORDER_OPEN fact at all, or contradictory facts for one order.
        return None
    opportunity_id, evidence_id = links.pop()
    if not opportunity_id or not evidence_id:
        return None
    captured = await session.scalar(
        select(EdgeOpportunityEvidenceRecord.evidence_id).where(
            EdgeOpportunityEvidenceRecord.evidence_id == evidence_id,
            EdgeOpportunityEvidenceRecord.opportunity_id == opportunity_id,
        )
    )
    if captured is None:
        return None
    return OpportunityLink(opportunity_id=opportunity_id, evidence_id=evidence_id)


def ai_attribution_event_type(
    *,
    status: DecisionStatus | None,
    direction: Direction | None,
    provider_error: bool = False,
    applies_to_family: bool = True,
) -> AttributionEventType:
    """Map one accepted AI outcome onto the frozen AI attribution vocabulary.

    ``status is None`` means no decision was observed for the opportunity at all.
    """

    if status is None:
        return AttributionEventType.AI_NOT_REACHED
    if status is DecisionStatus.STALE_DECISION:
        return AttributionEventType.AI_STALE
    if status in {DecisionStatus.INVALID_SCHEMA, DecisionStatus.INVALID_BUSINESS}:
        # A provider failure and a schema/business violation are different
        # attribution facts even though both persist the same accepted status.
        return (
            AttributionEventType.AI_PROVIDER_ERROR
            if provider_error
            else AttributionEventType.AI_INVALID
        )
    if status is DecisionStatus.VALID:
        if direction is Direction.SHORT_BIAS:
            # Analysis only: V1 never turns SHORT_BIAS into an executable plan.
            return AttributionEventType.AI_REJECTED_SHORT_ANALYSIS_ONLY
        if not applies_to_family:
            return AttributionEventType.AI_NOT_SELECTED_THIS_FAMILY
        if direction is Direction.LONG_BIAS:
            return AttributionEventType.AI_ACCEPTED_LONG
        return AttributionEventType.AI_REJECTED_WAIT
    # Any status outside the accepted decision lifecycle can never mean
    # acceptance, so it is recorded as an invalid decision rather than silently
    # claiming the AI accepted the opportunity.
    return AttributionEventType.AI_INVALID


class EdgeAttributionRecorder:
    """Appends attribution lineage for one opportunity.

    Every method takes the caller's ``AsyncSession`` so the lineage fact is
    written inside the transaction that already owns the business subject. The
    caller therefore keeps its own transaction boundary: there is no second
    commit and no distributed transaction.
    """

    def __init__(self, link: OpportunityLink, *, clock: Clock | None = None) -> None:
        self.link = link
        self.clock = clock or SystemClock()

    async def record(
        self,
        session: AsyncSession,
        *,
        subject_type: AttributionSubjectType,
        event_type: AttributionEventType,
        payload: dict[str, Any] | None = None,
        subject_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        """Append one attribution event. Returns ``INSERTED`` or ``IDEMPOTENT``."""

        event = build_attribution_event(
            subject_type=subject_type,
            event_type=event_type.value,
            subject_id=subject_id,
            opportunity_id=self.link.opportunity_id,
            evidence_id=self.link.evidence_id,
            payload=dict(payload or {}),
            occurred_at=occurred_at or self.clock.now(),
            recorded_at=self.clock.now(),
        )
        return await append_attribution_event(session, event)

    # --- AI ---------------------------------------------------------------------------

    async def record_ai_decision(
        self,
        session: AsyncSession,
        *,
        decision_id: str | None,
        status: DecisionStatus | None,
        direction: Direction | None,
        selected_strategy_ids: list[str] | None = None,
        provider_error: bool = False,
        occurred_at: datetime | None = None,
    ) -> str:
        event_type = ai_attribution_event_type(
            status=status,
            direction=direction,
            provider_error=provider_error,
            applies_to_family=family_is_selected(
                selected_strategy_ids=list(selected_strategy_ids or []),
            ),
        )
        return await self.record(
            session,
            subject_type=AttributionSubjectType.AI,
            event_type=event_type,
            subject_id=decision_id,
            payload={
                "decision_id": decision_id,
                "decision_status": None if status is None else status.value,
                "direction": None if direction is None else direction.value,
                "provider_error": provider_error,
                "selected_strategy_ids": list(selected_strategy_ids or []),
                "family_strategy_id": OPPORTUNITY_FAMILY_STRATEGY_ID,
            },
            occurred_at=occurred_at,
        )

    # --- Plan -------------------------------------------------------------------------

    async def record_plan_created(
        self,
        session: AsyncSession,
        *,
        plan_id: str,
        decision_id: str,
        snapshot_id: str,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.PLAN,
            event_type=AttributionEventType.PLAN_CREATED,
            subject_id=plan_id,
            payload={
                "plan_id": plan_id,
                "decision_id": decision_id,
                "snapshot_id": snapshot_id,
            },
            occurred_at=occurred_at,
        )

    async def record_plan_not_created(
        self,
        session: AsyncSession,
        *,
        reason: str,
        decision_id: str | None = None,
        snapshot_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.PLAN,
            event_type=AttributionEventType.PLAN_NOT_CREATED,
            subject_id=None,
            payload={
                "reason": reason,
                "decision_id": decision_id,
                "snapshot_id": snapshot_id,
            },
            occurred_at=occurred_at,
        )

    # --- Risk -------------------------------------------------------------------------

    async def record_risk_accepted(
        self,
        session: AsyncSession,
        *,
        intent_id: str,
        plan_id: str,
        order_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.RISK,
            event_type=AttributionEventType.RISK_ACCEPTED,
            subject_id=intent_id,
            payload={"intent_id": intent_id, "plan_id": plan_id, "order_id": order_id},
            occurred_at=occurred_at,
        )

    async def record_risk_rejected(
        self,
        session: AsyncSession,
        *,
        authority: str,
        reason: str,
        intent_id: str,
        plan_id: str,
        occurred_at: datetime | None = None,
    ) -> str:
        """Record a risk refusal with its exact authority and exact reason.

        Capacity-policy refusals and authoritative gate refusals are separate
        authorities; neither is collapsed into a generic rejection.
        """

        return await self.record(
            session,
            subject_type=AttributionSubjectType.RISK,
            event_type=AttributionEventType.RISK_REJECTED,
            subject_id=intent_id,
            payload={
                "intent_id": intent_id,
                "plan_id": plan_id,
                "authority": authority,
                "reason": reason,
            },
            occurred_at=occurred_at,
        )

    # --- Execution --------------------------------------------------------------------

    async def record_execution_rejected(
        self,
        session: AsyncSession,
        *,
        reason: str,
        intent_id: str,
        plan_id: str,
        occurred_at: datetime | None = None,
    ) -> str:
        """Record an execution validation rejection.

        Stale data, expired plans, changed state versions and out-of-zone prices
        are execution validation outcomes, not risk refusals.
        """

        return await self.record(
            session,
            subject_type=AttributionSubjectType.EXECUTION,
            event_type=AttributionEventType.EXECUTION_REJECTED,
            subject_id=intent_id,
            payload={"intent_id": intent_id, "plan_id": plan_id, "reason": reason},
            occurred_at=occurred_at,
        )

    async def record_order_open(
        self,
        session: AsyncSession,
        *,
        order_id: str,
        intent_id: str,
        plan_id: str,
        quantity: float,
        limit_price: float | None,
        occurred_at: datetime | None = None,
    ) -> str:
        """An OPEN order is evidence of admission, never of a fill."""

        return await self.record(
            session,
            subject_type=AttributionSubjectType.EXECUTION,
            event_type=AttributionEventType.ORDER_OPEN,
            subject_id=order_id,
            payload={
                "order_id": order_id,
                "intent_id": intent_id,
                "plan_id": plan_id,
                "quantity": quantity,
                "limit_price": limit_price,
            },
            occurred_at=occurred_at,
        )

    async def record_order_cancelled(
        self,
        session: AsyncSession,
        *,
        order_id: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.EXECUTION,
            event_type=AttributionEventType.ORDER_CANCELLED,
            subject_id=order_id,
            payload={"order_id": order_id, "reason": reason},
            occurred_at=occurred_at,
        )

    async def record_buy_filled(
        self,
        session: AsyncSession,
        *,
        order_id: str,
        fill_id: str,
        price: float,
        quantity: float,
        fee: float,
        occurred_at: datetime | None = None,
    ) -> str:
        """Only an actual BUY fill proves that trading occurred."""

        return await self.record(
            session,
            subject_type=AttributionSubjectType.EXECUTION,
            event_type=AttributionEventType.BUY_FILLED,
            subject_id=fill_id,
            payload={
                "order_id": order_id,
                "fill_id": fill_id,
                "price": price,
                "quantity": quantity,
                "fee": fee,
            },
            occurred_at=occurred_at,
        )

    # --- Economic lineage -------------------------------------------------------------

    async def record_trade_opened(
        self,
        session: AsyncSession,
        *,
        trade_id: str,
        fill_id: str,
        price: float,
        quantity: float,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.ECONOMIC_RESULT,
            event_type=AttributionEventType.TRADE_OPEN,
            subject_id=trade_id,
            payload={
                "trade_id": trade_id,
                "fill_id": fill_id,
                "price": price,
                "quantity": quantity,
            },
            occurred_at=occurred_at,
        )

    async def record_trade_closed(
        self,
        session: AsyncSession,
        *,
        trade_id: str,
        fill_id: str,
        exit_reason: str | None,
        realized_pnl: float,
        occurred_at: datetime | None = None,
    ) -> str:
        return await self.record(
            session,
            subject_type=AttributionSubjectType.ECONOMIC_RESULT,
            event_type=AttributionEventType.TRADE_CLOSED,
            subject_id=trade_id,
            payload={
                "trade_id": trade_id,
                "fill_id": fill_id,
                "exit_reason": exit_reason,
                "realized_pnl": realized_pnl,
            },
            occurred_at=occurred_at,
        )

    async def record_economic_result(
        self,
        session: AsyncSession,
        *,
        fill_id: str,
        ledger_entry_id: str,
        realized_pnl: float,
        fee: float,
        cash_delta: float,
        exit_reason: str | None,
        occurred_at: datetime | None = None,
    ) -> str:
        """Observe the immutable economic result the accounting path already produced."""

        return await self.record(
            session,
            subject_type=AttributionSubjectType.ECONOMIC_RESULT,
            event_type=AttributionEventType.ACTUAL_ECONOMIC_RESULT_AVAILABLE,
            subject_id=fill_id,
            payload={
                "fill_id": fill_id,
                "ledger_entry_id": ledger_entry_id,
                "realized_pnl": realized_pnl,
                "fee": fee,
                "cash_delta": cash_delta,
                "exit_reason": exit_reason,
            },
            occurred_at=occurred_at,
        )
