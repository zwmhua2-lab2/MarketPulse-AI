"""Durable, authenticated UI-RD01-I03 TradingAuditRead projection."""

from __future__ import annotations

import asyncio
import math
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings
from marketpulse.db.models import (
    AccountRecord,
    AdvisoryDecisionInvocationRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    EdgeAttributionEventRecord,
    EdgeOpportunityEvidenceRecord,
    ExecutionIntentRecord,
    FillRecord,
    LedgerEntryRecord,
    OutboxRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import OrderStatus, PlanStatus, TradePlan
from marketpulse.ids import new_id

from .context import ProductReadContext
from .cursor import (
    ProductCursorError,
    TradingAuditCursor,
    decode_trading_audit_cursor,
    encode_trading_audit_cursor,
)
from .models import (
    PRODUCT_READ_CONTRACT_VERSION,
    OperationalAvailability,
    OperationalContextDTO,
    ProductInternalErrorResponse,
    ProductUnavailableResponse,
    ProjectionMetaDTO,
    ProjectionState,
    ReadFailureReason,
    ReadSurfaceClass,
    TraceNodeDTO,
    TraceNodeState,
    TradingAccountDTO,
    TradingAuditDataDTO,
    TradingAuditReadResponse,
    TradingCollectionDTO,
    TradingDecisionDTO,
    TradingExecutionTimelineItemDTO,
    TradingFillTimelineItemDTO,
    TradingIntentRejectionDTO,
    TradingIntentTimelineItemDTO,
    TradingLedgerTimelineItemDTO,
    TradingOpenOrderDTO,
    TradingOpportunityBindingDTO,
    TradingOrderCancelledTimelineItemDTO,
    TradingOrderCreatedTimelineItemDTO,
    TradingPendingIntentCapabilityDTO,
    TradingPlanDTO,
    TradingPlanTimelineItemDTO,
    TradingPositionDTO,
    TradingPositionEventTimelineItemDTO,
    TradingPositionProtectionDTO,
    TradingPositionState,
    TradingProtectionAuthorityDTO,
    TradingProtectionState,
    TradingRiskTimelineItemDTO,
    TradingTimelineItem,
    TradingTimelinePageDTO,
    TradingTraceabilityDTO,
    TradingTraceabilityStatus,
    TradingTraceMissingLink,
    TradingTradeCloseTimelineItemDTO,
    TradingTradeOpenTimelineItemDTO,
)

router = APIRouter(tags=["product-read"])
PROJECTION = "TradingAuditRead"
# Keep the accepted G3 reconciliation tolerance; this Product read must not define a
# second accounting policy.
EPSILON = 1e-8
SOURCE_ERRORS = (asyncio.TimeoutError, OSError, SQLAlchemyError, asyncpg.PostgresError)


class SnapshotError(RuntimeError):
    pass


class SourceError(RuntimeError):
    pass


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _context(
    settings: Settings, context: ProductReadContext | None, at: datetime
) -> OperationalContextDTO:
    host = None if context is None else context.host
    return OperationalContextDTO(
        run_mode=settings.run_mode if host is None else host.run_mode.value,
        runtime_instance_id=None if host is None else host.instance_id,
        host_state=None if host is None else host.state,
        operational_provenance=settings.run_mode if host is None else host.run_mode.value,
        context_snapshot_at=at,
    )


def _unavailable(reason: ReadFailureReason, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=ProductUnavailableResponse(
            projection=PROJECTION,
            contract_version=PRODUCT_READ_CONTRACT_VERSION,
            read_surface_class=ReadSurfaceClass.A,
            read_failure_reason=reason,
            correlation_id=correlation_id,
        ).model_dump(mode="json"),
    )


@asynccontextmanager
async def _snapshot(context: ProductReadContext):
    if context.sessions is None:
        raise SourceError("session factory unavailable")
    try:
        async with context.sessions() as session, session.begin():
            if session.get_bind().dialect.name == "postgresql":
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                at = _utc(await session.scalar(text("SELECT statement_timestamp()")))
            else:
                at = _utc(await session.scalar(select(func.current_timestamp())))
            yield session, at
    except SnapshotError:
        raise
    except SOURCE_ERRORS as exc:
        raise SourceError("durable source unavailable") from exc


def _trace() -> TradingTraceabilityDTO:
    return TradingTraceabilityDTO(status=TradingTraceabilityStatus.COMPLETE)


def _trace_for(
    *, applicable: set[TradingTraceMissingLink], proven: set[TradingTraceMissingLink]
) -> TradingTraceabilityDTO:
    """A52 core: only applicable, unproven durable links are reported."""
    missing = sorted(applicable - proven, key=lambda item: item.value)
    if not applicable:
        return TradingTraceabilityDTO(status=TradingTraceabilityStatus.COMPLETE)
    if not proven:
        return TradingTraceabilityDTO(
            status=TradingTraceabilityStatus.NOT_PROVABLE, missing_links=missing
        )
    return TradingTraceabilityDTO(
        status=TradingTraceabilityStatus.COMPLETE
        if not missing
        else TradingTraceabilityStatus.PARTIAL,
        missing_links=missing,
    )


def _matrix_links(
    row: str,
    *,
    side: str | None = None,
    has_plan: bool = True,
    initial: bool = False,
    fill_proven: bool = True,
    explicit: set[str] | None = None,
) -> set[TradingTraceMissingLink]:
    """A54-A73 applicability; invoked only through the projection builder."""
    base = {
        "PLAN_CREATED": {"DECISION", "OPPORTUNITY_BINDING"},
        "INTENT_REJECTED": {"PLAN", "DECISION", "OPPORTUNITY_BINDING", "REJECTION_CLASSIFICATION"},
        "POSITION_EVENT": set(explicit or set()),
    }
    if row in base:
        if row == "INTENT_REJECTED" and not has_plan:
            raise SnapshotError("rejected intent has invalid empty plan")
        names = base[row]
    elif row == "ORDER_CANCELLED":
        if not has_plan:
            raise SnapshotError("cancelled order has invalid empty plan")
        names = {"ORDER", "INTENT", "PLAN", "DECISION", "OPPORTUNITY_BINDING"}
        if side == "BUY":
            names.add("RISK_ATTRIBUTION")
    elif row in {"RISK", "EXECUTION"}:
        names = {"INTENT", "PLAN", "DECISION", "OPPORTUNITY_BINDING"}
        if not initial:
            names.add("ORDER")
    elif row in {"INTENT_EXECUTED", "ORDER_CREATED", "FILL", "LEDGER"}:
        names = {"INTENT"} if row == "ORDER_CREATED" else {"ORDER"}
        if row == "FILL":
            names |= {"INTENT", "LEDGER"}
        elif row == "LEDGER":
            names |= {"INTENT", "FILL"}
        if side == "BUY":
            names |= {"PLAN", "DECISION", "OPPORTUNITY_BINDING", "RISK_ATTRIBUTION"}
        elif has_plan:
            names |= {"PLAN", "DECISION", "OPPORTUNITY_BINDING"}
    elif row in {"TRADE_OPEN", "TRADE_CLOSE"}:
        if not fill_proven:
            return {TradingTraceMissingLink.FILL}
        names = {"ORDER", "INTENT", "LEDGER"}
        if row == "TRADE_OPEN" or has_plan:
            names |= {"PLAN", "DECISION", "OPPORTUNITY_BINDING"}
        if row == "TRADE_OPEN":
            names.add("RISK_ATTRIBUTION")
    else:
        raise SnapshotError("unknown traceability matrix row")
    return {TradingTraceMissingLink(name) for name in names}


def _historical_binding(
    snapshot: object, evidence_by_id: dict[str, object]
) -> TraceNodeDTO[TradingOpportunityBindingDTO]:
    """A25/A26: exact Decision-bound snapshot binding; never canonical substitution."""
    fields = (
        "opportunity_id",
        "evidence_id",
        "evidence_revision",
        "evidence_hash",
        "feature_snapshot_hash",
    )
    values = {field: getattr(snapshot, field, None) for field in fields}
    if all(value is None for value in values.values()):
        return TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
    if any(value is None for value in values.values()):
        raise SnapshotError("incomplete decision binding")
    durable = evidence_by_id.get(str(values["evidence_id"]))
    if durable is None or any(getattr(durable, field, None) != values[field] for field in fields):
        raise SnapshotError("decision binding mismatch")
    return TraceNodeDTO(
        state=TraceNodeState.PRESENT,
        evidence_basis="exact_decision_snapshot_binding",
        data=TradingOpportunityBindingDTO(**values),
    )


def _resolve_decision_binding(
    decision: object,
    snapshots: dict[str, object],
    invocations: dict[str, object],
    evidence: dict[str, object],
    attribution: list[object],
) -> TraceNodeDTO[TradingOpportunityBindingDTO]:
    """A25/A26 durable resolver; callers supply one snapshot population."""
    snapshot_id = getattr(decision, "snapshot_id", "")
    snapshot = snapshots.get(snapshot_id)
    if (
        snapshot is None
        or getattr(snapshot, "run_mode", None) != getattr(decision, "run_mode", None)
        or getattr(snapshot, "state_version", None) != getattr(decision, "state_version", None)
    ):
        raise SnapshotError("decision snapshot missing or incoherent")
    snapshot_invocation_id = getattr(snapshot, "decision_invocation_id", None)
    decision_invocation_id = getattr(decision, "decision_invocation_id", None)
    if (
        snapshot_invocation_id is not None
        and decision_invocation_id is not None
        and snapshot_invocation_id != decision_invocation_id
    ):
        raise SnapshotError("decision invocation mismatch")
    snapshot_digest = getattr(snapshot, "input_binding_digest", None)
    decision_digest = getattr(decision, "input_binding_digest", None)
    if (
        snapshot_digest is not None
        and decision_digest is not None
        and snapshot_digest != decision_digest
    ):
        raise SnapshotError("decision input binding digest mismatch")
    direct = _historical_binding(snapshot, evidence)
    invocation_id = snapshot_invocation_id or decision_invocation_id
    if invocation_id is None:
        return direct
    invocation = invocations.get(invocation_id)
    if invocation is None:
        raise SnapshotError("explicit invocation missing")
    if getattr(invocation, "decision_invocation_id", invocation_id) != invocation_id:
        raise SnapshotError("invocation identity mismatch")
    if getattr(invocation, "snapshot_id", None) != snapshot_id:
        raise SnapshotError("invocation snapshot mismatch")
    if (
        snapshot_digest is not None
        and getattr(invocation, "input_binding_digest", None) != snapshot_digest
    ):
        raise SnapshotError("invocation digest mismatch")
    if (
        decision_digest is not None
        and getattr(invocation, "input_binding_digest", None) != decision_digest
    ):
        raise SnapshotError("decision invocation digest mismatch")
    if direct.data is None:
        raise SnapshotError("explicit invocation lacks direct binding")
    for field in (
        "opportunity_id",
        "evidence_id",
        "evidence_revision",
        "evidence_hash",
        "feature_snapshot_hash",
    ):
        if getattr(invocation, field, None) != getattr(direct.data, field):
            raise SnapshotError("invocation binding mismatch")
    for row in attribution:
        has_explicit_binding = (
            getattr(row, "opportunity_id", None) is not None
            or getattr(row, "evidence_id", None) is not None
        )
        if (
            getattr(row, "subject_type", "AI") == "AI"
            and getattr(row, "subject_id", None) == getattr(decision, "decision_id", None)
            and has_explicit_binding
            and (
                getattr(row, "opportunity_id", None) != direct.data.opportunity_id
                or getattr(row, "evidence_id", None) != direct.data.evidence_id
            )
        ):
            raise SnapshotError("attribution binding conflict")
    return direct


def _event_traceability(
    row: str,
    *,
    side: str | None = None,
    has_plan: bool = True,
    fill_proven: bool = True,
    initial: bool = False,
    no_plan_bundle_valid: bool = True,
    proven: set[TradingTraceMissingLink] | None = None,
    explicit: set[str] | None = None,
    intent_id: str | None = None,
    order_intent_id: str | None = None,
    order_id: str | None = None,
    fill_order_id: str | None = None,
) -> TradingTraceabilityDTO:
    """Projection-builder entrypoint: contradictions fail before trace gaps."""
    if intent_id is not None and order_intent_id is not None and intent_id != order_intent_id:
        raise SnapshotError("order intent identity mismatch")
    if order_id is not None and fill_order_id is not None and order_id != fill_order_id:
        raise SnapshotError("fill order identity mismatch")
    if side == "SELL" and not has_plan and not no_plan_bundle_valid:
        raise SnapshotError("invalid no-plan sell bundle")
    if row == "TRADE_OPEN" and fill_proven and side != "BUY":
        raise SnapshotError("trade open fill role")
    if row == "TRADE_CLOSE" and fill_proven and side != "SELL":
        raise SnapshotError("trade close fill role")
    applicable = _matrix_links(
        row,
        side=side,
        has_plan=has_plan,
        initial=initial,
        fill_proven=fill_proven,
        explicit=explicit,
    )
    return _trace_for(applicable=applicable, proven=proven or set())


def _proven_lineage(
    *,
    plan: object | None = None,
    intent: object | None = None,
    order: object | None = None,
    fill: object | None = None,
    ledger: object | None = None,
    decision_nodes: dict[str, TraceNodeDTO[TradingDecisionDTO]] | None = None,
    risk_attribution: bool = False,
    rejection_classification: bool = False,
) -> set[TradingTraceMissingLink]:
    """Derive A53 proof only from exact durable facts supplied by the projection."""
    proven: set[TradingTraceMissingLink] = set()
    for link, fact in (
        (TradingTraceMissingLink.INTENT, intent),
        (TradingTraceMissingLink.ORDER, order),
        (TradingTraceMissingLink.FILL, fill),
        (TradingTraceMissingLink.LEDGER, ledger),
    ):
        if fact is not None:
            proven.add(link)
    if plan is not None:
        proven.add(TradingTraceMissingLink.PLAN)
        decision = (decision_nodes or {}).get(getattr(plan, "decision_id", None))
        if (
            decision is not None
            and decision.state is TraceNodeState.PRESENT
            and decision.data is not None
        ):
            proven.add(TradingTraceMissingLink.DECISION)
            if decision.data.opportunity_binding.state is TraceNodeState.PRESENT:
                proven.add(TradingTraceMissingLink.OPPORTUNITY_BINDING)
    if risk_attribution:
        proven.add(TradingTraceMissingLink.RISK_ATTRIBUTION)
    if rejection_classification:
        proven.add(TradingTraceMissingLink.REJECTION_CLASSIFICATION)
    return proven


def _position(row: PositionRecord) -> TradingPositionDTO:
    if row.quantity < 0:
        raise SnapshotError("negative position")
    fields = (
        row.protection_plan_id,
        row.protection_plan_version,
        row.protection_stop_loss,
        row.protection_take_profit,
        row.protection_updated_at,
    )
    flat = row.quantity == 0
    if flat and any(value is not None for value in fields):
        raise SnapshotError("flat protection contradiction")
    if flat:
        protection = TradingPositionProtectionDTO(state=TradingProtectionState.NOT_REQUIRED)
    elif all(value is None for value in fields):
        protection = TradingPositionProtectionDTO(state=TradingProtectionState.UNPROTECTED)
    elif (
        isinstance(row.protection_plan_id, str)
        and bool(row.protection_plan_id)
        and isinstance(row.protection_plan_version, int)
        and row.protection_plan_version >= 1
        and row.protection_updated_at is not None
        and all(
            math.isfinite(float(v)) for v in (row.protection_stop_loss, row.protection_take_profit)
        )
        and row.protection_stop_loss < row.protection_take_profit
    ):
        protection = TradingPositionProtectionDTO(
            state=TradingProtectionState.PROTECTED,
            authority=TradingProtectionAuthorityDTO(
                plan_id=row.protection_plan_id,
                plan_version=row.protection_plan_version,
                stop_loss=row.protection_stop_loss,
                take_profit=row.protection_take_profit,
                updated_at=_utc(row.protection_updated_at),
            ),
        )
    else:
        protection = TradingPositionProtectionDTO(state=TradingProtectionState.UNKNOWN)
    return TradingPositionDTO(
        position_id=row.position_id,
        instrument_id=row.instrument_id,
        state=TradingPositionState.FLAT if flat else TradingPositionState.OPEN,
        quantity=row.quantity,
        average_cost=row.average_cost,
        trade_id=row.trade_id,
        updated_at=_utc(row.updated_at),
        protection=protection,
    )


def _project_active_plans(
    rows: list[TradePlanRecord],
    snapshot_at: datetime,
    instrument_id: str | None = None,
    decision_nodes: dict[str, TraceNodeDTO[TradingDecisionDTO]] | None = None,
) -> list[TradingPlanDTO]:
    """A21-A24 fail-closed ACTIVE plan projection, independently testable."""
    items: list[TradingPlanDTO] = []
    for row in rows:
        if row.status != PlanStatus.ACTIVE:
            continue
        try:
            plan = TradePlan.model_validate(row.payload)
        except Exception as exc:
            raise SnapshotError("invalid active plan") from exc
        if any(
            (
                plan.plan_id != row.plan_id,
                plan.snapshot_id != row.snapshot_id,
                plan.decision_id != row.decision_id,
                plan.instrument_id != row.instrument_id,
                plan.run_mode.value != row.run_mode,
                plan.state_version != row.state_version,
                plan.plan_version != row.plan_version,
                plan.created_at != row.created_at,
                plan.expires_at != row.expires_at,
            )
        ):
            raise SnapshotError("active plan identity mismatch")
        items.append(
            TradingPlanDTO(
                plan_id=row.plan_id,
                snapshot_id=row.snapshot_id,
                decision_id=row.decision_id,
                instrument_id=row.instrument_id,
                symbol=row.symbol,
                plan_version=row.plan_version,
                status=row.status,
                created_at=_utc(row.created_at),
                expires_at=_utc(row.expires_at),
                ttl_expired=snapshot_at >= _utc(row.expires_at),
                order_type=plan.order_type.value,
                side=plan.side.value,
                entry_zone=plan.entry_zone.model_dump(),
                stop_loss=plan.stop_loss,
                take_profit=plan.take_profit,
                intended_notional=plan.intended_notional,
                invalidation=plan.invalidation,
                decision=(decision_nodes or {}).get(
                    row.decision_id, TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
                ),
            )
        )
    items.sort(key=lambda row: (row.instrument_id, row.plan_id))
    return [row for row in items if instrument_id is None or row.instrument_id == instrument_id]


def _project_decision_nodes(
    rows: list[AIDecisionRecord],
    snapshots: dict[str, DecisionSnapshotRecord],
    invocations: dict[str, AdvisoryDecisionInvocationRecord],
    evidence: dict[str, EdgeOpportunityEvidenceRecord],
    attribution: list[EdgeAttributionEventRecord],
) -> dict[str, TraceNodeDTO[TradingDecisionDTO]]:
    """Sanitized A25 decision projection with its exact durable A26 binding."""
    nodes: dict[str, TraceNodeDTO[TradingDecisionDTO]] = {}
    for row in rows:
        if row.decision_id in nodes:
            raise SnapshotError("duplicate decision identity")
        nodes[row.decision_id] = TraceNodeDTO(
            state=TraceNodeState.PRESENT,
            evidence_basis="durable_ai_decision",
            data=TradingDecisionDTO(
                decision_id=row.decision_id,
                snapshot_id=row.snapshot_id,
                status=row.status,
                model=row.model,
                created_at=_utc(row.created_at),
                opportunity_binding=_resolve_decision_binding(
                    row, snapshots, invocations, evidence, attribution
                ),
            ),
        )
    return nodes


def _initial_rejection(
    intent: object, attribution: list[object]
) -> TraceNodeDTO[TradingIntentRejectionDTO]:
    if getattr(intent, "status", None) == "EXECUTED":
        return TraceNodeDTO(
            state=TraceNodeState.NOT_OCCURRED, evidence_basis="durable_intent_status"
        )
    candidates = [
        row
        for row in attribution
        if getattr(row, "subject_id", None) == getattr(intent, "intent_id", None)
        and getattr(row, "event_type", None) in {"RISK_REJECTED", "EXECUTION_REJECTED"}
        and getattr(row, "occurred_at", None) == getattr(intent, "created_at", None)
    ]
    if not candidates:
        return TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
    if len(candidates) != 1:
        raise SnapshotError("conflicting initial rejection")
    row = candidates[0]
    payload = getattr(row, "payload", {})
    if not isinstance(payload, dict) or any(
        (
            payload.get("intent_id") != getattr(intent, "intent_id", None),
            payload.get("plan_id") != getattr(intent, "plan_id", None),
            payload.get("reason") != getattr(intent, "reason", None),
        )
    ):
        raise SnapshotError("initial rejection mismatch")
    risk = row.event_type == "RISK_REJECTED"
    authority = payload.get("authority")
    if risk and not isinstance(authority, str):
        raise SnapshotError("risk rejection authority missing")
    if not risk and authority is not None:
        raise SnapshotError("execution rejection authority present")
    return TraceNodeDTO(
        state=TraceNodeState.PRESENT,
        evidence_basis="exact_edge_attribution",
        data=TradingIntentRejectionDTO(
            kind="RISK" if risk else "EXECUTION",
            attribution_event_id=row.attribution_event_id,
            authority=authority,
            reason=intent.reason,
            occurred_at=_utc(row.occurred_at),
        ),
    )


def _timeline_key(item: TradingTimelineItem) -> tuple[datetime, str, str]:
    return (item.occurred_at, item.entity_kind, item.timeline_event_id)


def _timeline_page(
    items: list[TradingTimelineItem],
    *,
    upper: datetime,
    limit: int,
    cursor: TradingAuditCursor | None,
    run_mode: str,
    instrument_id: str | None,
) -> tuple[list[TradingTimelineItem], str | None]:
    visible = [item for item in items if item.occurred_at <= upper]
    if instrument_id is not None:
        visible = [
            item for item in visible if getattr(item, "instrument_id", None) == instrument_id
        ]
    visible.sort(key=_timeline_key, reverse=True)
    if cursor is not None:
        cursor_key = (cursor.occurred_at, cursor.entity_kind, cursor.timeline_event_id)
        visible = [item for item in visible if _timeline_key(item) < cursor_key]
    # Materialize one extra ordered item solely to make the cursor continuation proof explicit.
    window = visible[: limit + 1]
    page = window[:limit]
    next_cursor = None
    if len(window) > limit and page:
        last = page[-1]
        next_cursor = encode_trading_audit_cursor(
            TradingAuditCursor(
                run_mode,
                instrument_id,
                upper,
                last.occurred_at,
                last.entity_kind,
                last.timeline_event_id,
            )
        )
    return page, next_cursor


def _trade_traceability(
    trade: TradeRecord,
    *,
    event_type: str,
    attribution: list[EdgeAttributionEventRecord],
    fill_by_id: dict[str, FillRecord],
    order_by_id: dict[str, PaperOrderRecord],
    intent_by_id: dict[str, ExecutionIntentRecord],
    ledger_by_fill: dict[str, LedgerEntryRecord],
    plan_by_id: dict[str, TradePlanRecord],
    decision_nodes: dict[str, TraceNodeDTO[TradingDecisionDTO]],
    risk_accepted_intents: set[tuple[str, str]],
) -> TradingTraceabilityDTO:
    row_name = "TRADE_OPEN" if event_type == "TRADE_OPEN" else "TRADE_CLOSE"
    matches = [
        row
        for row in attribution
        if getattr(row, "subject_type", None) == "ECONOMIC_RESULT"
        and getattr(row, "subject_id", None) == trade.trade_id
        and getattr(row, "event_type", None) == event_type
    ]
    if not matches:
        return _event_traceability(row_name, fill_proven=False)
    if len(matches) != 1 or not isinstance(matches[0].payload, dict):
        raise SnapshotError("trade attribution conflict")
    payload = matches[0].payload
    fill = fill_by_id.get(payload.get("fill_id"))
    if payload.get("trade_id") != trade.trade_id or fill is None:
        raise SnapshotError("trade attribution fill mismatch")
    order = order_by_id.get(fill.order_id)
    if order is None or order.intent_id != fill.intent_id:
        raise SnapshotError("trade fill order mismatch")
    intent = intent_by_id.get(order.intent_id)
    if (
        intent is None
        or intent.plan_id != order.plan_id
        or intent.instrument_id != order.instrument_id
    ):
        raise SnapshotError("trade order intent mismatch")
    plan = plan_by_id.get(order.plan_id) if order.plan_id else None
    if plan is not None and plan.instrument_id != order.instrument_id:
        raise SnapshotError("trade plan instrument mismatch")
    return _event_traceability(
        row_name,
        side=order.side,
        has_plan=bool(order.plan_id),
        fill_proven=True,
        proven=_proven_lineage(
            plan=plan,
            intent=intent,
            order=order,
            fill=fill,
            ledger=ledger_by_fill.get(fill.fill_id),
            decision_nodes=decision_nodes,
            risk_attribution=order.side == "BUY"
            and (intent.intent_id, intent.plan_id) in risk_accepted_intents,
        ),
    )


def _build_timeline(
    *,
    plans: list[TradePlanRecord],
    intents: list[ExecutionIntentRecord],
    orders: list[PaperOrderRecord],
    fills: list[FillRecord],
    ledgers: list[LedgerEntryRecord],
    outbox: list[OutboxRecord],
    trades: list[TradeRecord],
    position_events: list[PositionEventRecord],
    attribution: list[EdgeAttributionEventRecord],
    decision_nodes: dict[str, TraceNodeDTO[TradingDecisionDTO]] | None = None,
) -> list[TradingTimelineItem]:
    """Typed, all-source timeline assembly before one global keyset page is selected."""
    order_by_id = {row.order_id: row for row in orders}
    intent_by_id = {row.intent_id: row for row in intents}
    fill_by_id = {row.fill_id: row for row in fills}
    plan_by_id = {row.plan_id: row for row in plans}
    ledger_by_fill = {row.fill_id: row for row in ledgers}
    orders_by_intent: dict[str, list[PaperOrderRecord]] = {}
    for order in orders:
        orders_by_intent.setdefault(order.intent_id, []).append(order)
    risk_accepted_intents = {
        (row.subject_id, row.payload.get("plan_id"))
        for row in attribution
        if row.event_type == "RISK_ACCEPTED"
        and isinstance(row.payload, dict)
        and row.payload.get("intent_id") == row.subject_id
    }

    def intent_for(order: object) -> object | None:
        intent = intent_by_id.get(getattr(order, "intent_id", None))
        if intent is None or any(
            getattr(intent, field, None) != getattr(order, field, None)
            for field in ("plan_id", "instrument_id")
        ):
            return None
        return intent

    def plan_for(intent: object | None, order: object | None = None) -> object | None:
        if intent is None or not getattr(intent, "plan_id", None):
            return None
        plan = plan_by_id.get(getattr(intent, "plan_id", None))
        if plan is None or plan.instrument_id != getattr(intent, "instrument_id", None):
            return None
        if order is not None and plan.instrument_id != getattr(order, "instrument_id", None):
            return None
        return plan

    def exact_order_for(intent: object) -> object | None:
        matches = [
            order
            for order in orders_by_intent.get(getattr(intent, "intent_id", None), [])
            if order.plan_id == getattr(intent, "plan_id", None)
            and order.instrument_id == getattr(intent, "instrument_id", None)
        ]
        return matches[0] if len(matches) == 1 else None

    def risk_accepted_for(intent: object | None) -> bool:
        return (
            intent is not None
            and (getattr(intent, "intent_id", None), getattr(intent, "plan_id", None))
            in risk_accepted_intents
        )

    def explicit_position_event_lineage(
        event: object,
    ) -> tuple[object | None, object | None, object | None]:
        """Resolve only coherent explicit PositionEvent links for A52/A53 proof."""
        plan_id = getattr(event, "plan_id", None)
        order_id = getattr(event, "order_id", None)
        fill_id = getattr(event, "fill_id", None)
        instrument_id = getattr(event, "instrument_id", None)

        plan = plan_by_id.get(plan_id) if plan_id is not None else None
        order = order_by_id.get(order_id) if order_id is not None else None
        fill = fill_by_id.get(fill_id) if fill_id is not None else None

        if plan is not None and (
            getattr(plan, "plan_id", None) != plan_id
            or getattr(plan, "instrument_id", None) != instrument_id
        ):
            raise SnapshotError("position event plan lineage mismatch")
        if order is not None and (
            getattr(order, "order_id", None) != order_id
            or getattr(order, "instrument_id", None) != instrument_id
        ):
            raise SnapshotError("position event order lineage mismatch")
        if fill is not None and getattr(fill, "fill_id", None) != fill_id:
            raise SnapshotError("position event fill identity mismatch")

        fill_order = order_by_id.get(getattr(fill, "order_id", None)) if fill is not None else None
        if fill_order is not None and (
            getattr(fill_order, "order_id", None) != getattr(fill, "order_id", None)
            or getattr(fill_order, "instrument_id", None) != instrument_id
        ):
            raise SnapshotError("position event fill lineage mismatch")
        if (
            order_id is not None
            and fill is not None
            and getattr(fill, "order_id", None) != order_id
        ):
            raise SnapshotError("position event order/fill mismatch")
        if plan_id is not None and order is not None and getattr(order, "plan_id", None) != plan_id:
            raise SnapshotError("position event plan/order mismatch")
        if (
            plan_id is not None
            and fill_order is not None
            and getattr(fill_order, "plan_id", None) != plan_id
        ):
            raise SnapshotError("position event plan/fill mismatch")
        return plan, order, fill if fill_order is not None else None

    def lineage_for_order(
        order: object, *, include_order: bool = False
    ) -> set[TradingTraceMissingLink]:
        intent = intent_for(order)
        return _proven_lineage(
            plan=plan_for(intent, order),
            intent=intent,
            order=order if include_order else None,
            decision_nodes=decision_nodes,
            risk_attribution=getattr(order, "side", None) == "BUY" and risk_accepted_for(intent),
        )

    cancelled = {
        row.aggregate_id: row
        for row in outbox
        if row.event_type == "ORDER_CANCELLED" and row.aggregate_id in order_by_id
    }
    items: list[TradingTimelineItem] = []
    for plan in plans:
        items.append(
            TradingPlanTimelineItemDTO(
                timeline_event_id=f"plan:create:{plan.plan_id}",
                entity_id=plan.plan_id,
                occurred_at=_utc(plan.created_at),
                plan_id=plan.plan_id,
                snapshot_id=plan.snapshot_id,
                decision_id=plan.decision_id,
                instrument_id=plan.instrument_id,
                symbol=plan.symbol,
                plan_version=plan.plan_version,
                created_at=_utc(plan.created_at),
                expires_at=_utc(plan.expires_at),
                traceability=_event_traceability(
                    "PLAN_CREATED", proven=_proven_lineage(plan=plan, decision_nodes=decision_nodes)
                ),
            )
        )
    for intent in intents:
        has_plan = bool(intent.plan_id)
        initial_rejection = _initial_rejection(intent, attribution)
        items.append(
            TradingIntentTimelineItemDTO(
                timeline_event_id=f"intent:{intent.intent_id}",
                entity_id=intent.intent_id,
                event_type="INTENT_EXECUTED" if intent.status == "EXECUTED" else "INTENT_REJECTED",
                occurred_at=_utc(intent.created_at),
                intent_id=intent.intent_id,
                plan_id=intent.plan_id or None,
                instrument_id=intent.instrument_id,
                status=intent.status,
                reason=intent.reason,
                created_at=_utc(intent.created_at),
                initial_rejection=initial_rejection,
                traceability=_event_traceability(
                    "INTENT_EXECUTED" if intent.status == "EXECUTED" else "INTENT_REJECTED",
                    side=getattr(
                        order_by_id.get(
                            next(
                                (
                                    order.order_id
                                    for order in orders
                                    if order.intent_id == intent.intent_id
                                ),
                                "",
                            )
                        ),
                        "side",
                        None,
                    ),
                    has_plan=has_plan,
                    no_plan_bundle_valid=True,
                    proven=_proven_lineage(
                        plan=plan_for(intent),
                        order=exact_order_for(intent),
                        decision_nodes=decision_nodes,
                        risk_attribution=risk_accepted_for(intent),
                        rejection_classification=initial_rejection.state is TraceNodeState.PRESENT,
                    ),
                ),
            )
        )
    for order in orders:
        intent = intent_by_id.get(order.intent_id)
        if intent is None or intent.plan_id != order.plan_id:
            raise SnapshotError("order intent mismatch")
        has_plan = bool(order.plan_id)
        order_trace = _event_traceability(
            "ORDER_CREATED",
            side=order.side,
            has_plan=has_plan,
            proven=lineage_for_order(order),
        )
        if order.status == "CANCELLED" and order.order_id not in cancelled:
            order_trace = _trace_for(
                applicable={
                    *order_trace.missing_links,
                    TradingTraceMissingLink.ORDER_CANCELLATION_EVENT,
                },
                proven=set(),
            )
        items.append(
            TradingOrderCreatedTimelineItemDTO(
                timeline_event_id=f"order:create:{order.order_id}",
                entity_id=order.order_id,
                occurred_at=_utc(order.created_at),
                order_id=order.order_id,
                intent_id=order.intent_id,
                plan_id=order.plan_id or None,
                instrument_id=order.instrument_id,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                limit_price=order.limit_price,
                created_at=_utc(order.created_at),
                traceability=order_trace,
            )
        )
        cancellation = cancelled.get(order.order_id)
        if cancellation is not None:
            items.append(
                TradingOrderCancelledTimelineItemDTO(
                    timeline_event_id=f"outbox:{cancellation.outbox_id}",
                    entity_id=order.order_id,
                    occurred_at=_utc(cancellation.created_at),
                    order_id=order.order_id,
                    instrument_id=order.instrument_id,
                    cancelled_at=_utc(cancellation.created_at),
                    traceability=_event_traceability(
                        "ORDER_CANCELLED",
                        side=order.side,
                        has_plan=has_plan,
                        proven=lineage_for_order(order, include_order=True),
                    ),
                )
            )
    for fill in fills:
        order = order_by_id.get(fill.order_id)
        if order is None or order.intent_id != fill.intent_id:
            raise SnapshotError("fill order mismatch")
        items.append(
            TradingFillTimelineItemDTO(
                timeline_event_id=f"fill:{fill.fill_id}",
                entity_id=fill.fill_id,
                occurred_at=_utc(fill.created_at),
                fill_id=fill.fill_id,
                order_id=fill.order_id,
                intent_id=fill.intent_id,
                instrument_id=order.instrument_id,
                side=order.side,
                price=fill.price,
                quantity=fill.quantity,
                fee=fill.fee,
                created_at=_utc(fill.created_at),
                traceability=_event_traceability(
                    "FILL",
                    side=order.side,
                    has_plan=bool(order.plan_id),
                    proven=_proven_lineage(
                        plan=plan_for(intent_for(order), order),
                        intent=intent_for(order),
                        order=order,
                        ledger=ledger_by_fill.get(fill.fill_id),
                        decision_nodes=decision_nodes,
                        risk_attribution=order.side == "BUY"
                        and risk_accepted_for(intent_for(order)),
                    ),
                ),
            )
        )
    for ledger in ledgers:
        fill = fill_by_id.get(ledger.fill_id)
        if fill is None:
            raise SnapshotError("ledger fill missing")
        order = order_by_id.get(fill.order_id)
        if order is None:
            raise SnapshotError("ledger order missing")
        settlement = (
            ledger.payload.get("settlement_realized_pnl")
            if isinstance(ledger.payload, dict)
            else None
        )
        if settlement is None:
            settlement = 0.0
        items.append(
            TradingLedgerTimelineItemDTO(
                timeline_event_id=f"ledger:{ledger.entry_id}",
                entity_id=ledger.entry_id,
                occurred_at=_utc(ledger.created_at),
                entry_id=ledger.entry_id,
                fill_id=ledger.fill_id,
                instrument_id=order.instrument_id,
                entry_type=ledger.entry_type,
                cash_delta=ledger.cash_delta,
                fee=ledger.fee,
                settlement_realized_pnl=settlement,
                created_at=_utc(ledger.created_at),
                traceability=_event_traceability(
                    "LEDGER",
                    side=order.side,
                    has_plan=bool(order.plan_id),
                    proven=_proven_lineage(
                        plan=plan_for(intent_for(order), order),
                        intent=intent_for(order),
                        order=order,
                        fill=fill_by_id.get(ledger.fill_id),
                        decision_nodes=decision_nodes,
                        risk_attribution=order.side == "BUY"
                        and risk_accepted_for(intent_for(order)),
                    ),
                ),
            )
        )
    for row in attribution:
        if row.event_type not in {"RISK_ACCEPTED", "RISK_REJECTED", "EXECUTION_REJECTED"}:
            continue
        payload = row.payload if isinstance(row.payload, dict) else {}
        intent = intent_by_id.get(payload.get("intent_id"))
        if intent is None:
            continue
        if row.subject_id != intent.intent_id:
            raise SnapshotError("attribution intent mismatch")
        initial = row.occurred_at == intent.created_at
        if row.event_type.startswith("RISK"):
            reason = payload.get("reason")
            authority = payload.get("authority")
            deferred_order = exact_order_for(intent) if not initial else None
            if row.event_type == "RISK_REJECTED" and (
                not isinstance(reason, str) or not isinstance(authority, str)
            ):
                raise SnapshotError("risk rejection payload invalid")
            items.append(
                TradingRiskTimelineItemDTO(
                    timeline_event_id=f"attribution:{row.attribution_event_id}",
                    entity_id=intent.intent_id,
                    event_type=row.event_type,
                    occurred_at=_utc(row.occurred_at),
                    attribution_event_id=row.attribution_event_id,
                    intent_id=intent.intent_id,
                    plan_id=payload.get("plan_id") or None,
                    order_id=payload.get("order_id"),
                    authority=authority,
                    reason=reason,
                    opportunity_id=row.opportunity_id,
                    evidence_id=row.evidence_id,
                    traceability=_event_traceability(
                        "RISK",
                        initial=initial,
                        proven=_proven_lineage(
                            plan=plan_for(intent),
                            intent=intent,
                            order=(
                                deferred_order
                                if getattr(deferred_order, "order_id", None)
                                == payload.get("order_id")
                                else None
                            ),
                            decision_nodes=decision_nodes,
                        ),
                    ),
                )
            )
        else:
            reason = payload.get("reason")
            if not isinstance(reason, str):
                raise SnapshotError("execution rejection payload invalid")
            items.append(
                TradingExecutionTimelineItemDTO(
                    timeline_event_id=f"attribution:{row.attribution_event_id}",
                    entity_id=intent.intent_id,
                    occurred_at=_utc(row.occurred_at),
                    attribution_event_id=row.attribution_event_id,
                    intent_id=intent.intent_id,
                    plan_id=payload.get("plan_id") or None,
                    reason=reason,
                    opportunity_id=row.opportunity_id,
                    evidence_id=row.evidence_id,
                    traceability=_event_traceability(
                        "EXECUTION",
                        initial=initial,
                        proven=_proven_lineage(
                            plan=plan_for(intent),
                            intent=intent,
                            order=exact_order_for(intent) if not initial else None,
                            decision_nodes=decision_nodes,
                        ),
                    ),
                )
            )
    for trade in trades:
        items.append(
            TradingTradeOpenTimelineItemDTO(
                timeline_event_id=f"trade:open:{trade.trade_id}",
                entity_id=trade.trade_id,
                occurred_at=_utc(trade.opened_at),
                trade_id=trade.trade_id,
                instrument_id=trade.instrument_id,
                opened_at=_utc(trade.opened_at),
                traceability=_trade_traceability(
                    trade,
                    event_type="TRADE_OPEN",
                    attribution=attribution,
                    fill_by_id=fill_by_id,
                    order_by_id=order_by_id,
                    intent_by_id=intent_by_id,
                    ledger_by_fill=ledger_by_fill,
                    plan_by_id=plan_by_id,
                    decision_nodes=decision_nodes or {},
                    risk_accepted_intents=risk_accepted_intents,
                ),
            )
        )
        if trade.closed_at is not None:
            items.append(
                TradingTradeCloseTimelineItemDTO(
                    timeline_event_id=f"trade:close:{trade.trade_id}",
                    entity_id=trade.trade_id,
                    occurred_at=_utc(trade.closed_at),
                    trade_id=trade.trade_id,
                    instrument_id=trade.instrument_id,
                    closed_at=_utc(trade.closed_at),
                    exit_reason=trade.exit_reason,
                    traceability=_trade_traceability(
                        trade,
                        event_type="TRADE_CLOSED",
                        attribution=attribution,
                        fill_by_id=fill_by_id,
                        order_by_id=order_by_id,
                        intent_by_id=intent_by_id,
                        ledger_by_fill=ledger_by_fill,
                        plan_by_id=plan_by_id,
                        decision_nodes=decision_nodes or {},
                        risk_accepted_intents=risk_accepted_intents,
                    ),
                )
            )
    allowed = {
        "SL_TRIGGERED",
        "TP_TRIGGERED",
        "AI_REEVALUATION",
        "ADD",
        "REDUCE",
        "CLOSE",
        "MANUAL_CLOSE",
        "PLAN_UPDATED",
        "PLAN_REPLACED",
        "CANCEL_ADD",
        "RISK_BLOCKED",
    }
    for event in position_events:
        if event.event_type in allowed:
            plan, order, fill = explicit_position_event_lineage(event)
            explicit = {
                name
                for name, value in {
                    "PLAN": event.plan_id,
                    "ORDER": event.order_id,
                    "FILL": event.fill_id,
                }.items()
                if value is not None
            }
            items.append(
                TradingPositionEventTimelineItemDTO(
                    timeline_event_id=f"position-event:{event.event_id}",
                    entity_id=event.event_id,
                    event_type=event.event_type,
                    occurred_at=_utc(event.created_at),
                    event_id=event.event_id,
                    instrument_id=event.instrument_id,
                    position_id=event.position_id,
                    plan_id=event.plan_id,
                    order_id=event.order_id,
                    fill_id=event.fill_id,
                    created_at=_utc(event.created_at),
                    traceability=_event_traceability(
                        "POSITION_EVENT",
                        explicit=explicit,
                        proven=_proven_lineage(
                            plan=plan,
                            order=order,
                            fill=fill,
                            decision_nodes=decision_nodes,
                        ),
                    ),
                )
            )
    return items


def _validate(
    account: AccountRecord | None,
    positions: list[PositionRecord],
    intents: list[ExecutionIntentRecord],
    orders: list[PaperOrderRecord],
    fills: list[FillRecord],
    ledgers: list[LedgerEntryRecord],
    trades: list[TradeRecord],
) -> None:
    if account is None:
        if positions or intents or orders or fills or ledgers or trades:
            raise SnapshotError("economic facts without account")
        return
    by_order = {row.order_id: row for row in orders}
    by_intent = {row.intent_id: row for row in intents}
    by_fill = {row.fill_id: row for row in fills}
    ledger_by_fill = {row.fill_id: row for row in ledgers}
    if (
        len(by_order) != len(orders)
        or len(by_fill) != len(fills)
        or len(ledger_by_fill) != len(ledgers)
    ):
        raise SnapshotError("duplicate economic identity")
    open_buys = sum(
        row.reserved_cash for row in orders if row.status == OrderStatus.OPEN and row.side == "BUY"
    )
    if (
        abs(account.reserved_cash - open_buys) > EPSILON
        or account.cash_balance - account.reserved_cash < -EPSILON
    ):
        raise SnapshotError("account reservation")
    for fill in fills:
        order = by_order.get(fill.order_id)
        if (
            order is None
            or order.intent_id != fill.intent_id
            or fill.intent_id not in by_intent
            or fill.fill_id not in ledger_by_fill
        ):
            raise SnapshotError("fill orphan")
        if order.status != OrderStatus.FILLED or abs(order.quantity - fill.quantity) > EPSILON:
            raise SnapshotError("fill/order mismatch")
    if any(ledger.fill_id not in by_fill for ledger in ledgers):
        raise SnapshotError("ledger orphan")
    if any(
        order.status == OrderStatus.FILLED
        and order.order_id not in {fill.order_id for fill in fills}
        for order in orders
    ):
        raise SnapshotError("filled order without fill")
    net_fill_quantity: dict[str, float] = {}
    for fill in fills:
        order = by_order[fill.order_id]
        multiplier = 1.0 if order.side == "BUY" else -1.0
        net_fill_quantity[order.instrument_id] = (
            net_fill_quantity.get(order.instrument_id, 0.0) + multiplier * fill.quantity
        )
    positions_by_instrument = {position.instrument_id: position for position in positions}
    if any(
        abs(
            (
                positions_by_instrument[instrument].quantity
                if instrument in positions_by_instrument
                else 0.0
            )
            - quantity
        )
        > EPSILON
        for instrument, quantity in net_fill_quantity.items()
    ) or any(
        abs(position.quantity - net_fill_quantity.get(position.instrument_id, 0.0)) > EPSILON
        for position in positions
    ):
        raise SnapshotError("position/fill mismatch")
    for order in orders:
        if order.status == OrderStatus.OPEN and order.side == "SELL":
            position = next(
                (row for row in positions if row.instrument_id == order.instrument_id), None
            )
            if position is None or order.reserved_quantity > position.quantity + EPSILON:
                raise SnapshotError("open sell reservation")
    order_intent_ids = {row.intent_id for row in orders}
    for intent in intents:
        # A56/A80: an EXECUTED Intent without its exact Order is an economic contradiction,
        # never a traceability gap.
        if intent.status == "EXECUTED" and intent.intent_id not in order_intent_ids:
            raise SnapshotError("executed intent without order")
    for order in orders:
        # A51/A62: the internal empty-plan marker may only be projected for the accepted
        # no-plan SELL bundle (exact Fill/Ledger closure is enforced above).
        if order.plan_id:
            continue
        intent = by_intent.get(order.intent_id)
        if (
            order.side != "SELL"
            or order.order_type != "MARKET"
            or order.status != "FILLED"
            or intent is None
            or intent.status != "EXECUTED"
            or intent.plan_id != ""
            or intent.instrument_id != order.instrument_id
        ):
            raise SnapshotError("empty-plan order without accepted no-plan bundle")


def _ownership(*, anchors: list[str | None], current_run_mode: str) -> str:
    """A77 ownership classification for rows without a direct run_mode."""
    if not anchors or any(value is None for value in anchors):
        return "UNSCOPED"
    values = {value for value in anchors if value is not None}
    if len(values) != 1:
        return "CONFLICTING_SCOPE"
    return "PROVEN_CURRENT" if current_run_mode in values else "PROVEN_OTHER"


async def _read(
    context: ProductReadContext,
    *,
    instrument_id: str | None,
    limit: int,
    cursor: TradingAuditCursor | None,
):
    run_mode = context.host.run_mode.value
    if cursor is not None and (
        cursor.run_mode != run_mode or cursor.instrument_id != instrument_id
    ):
        raise HTTPException(422, "cursor scope does not match request")
    async with _snapshot(context) as (session, snapshot_at):
        upper = snapshot_at if cursor is None else cursor.timeline_upper_bound
        account = await session.scalar(
            select(AccountRecord).where(AccountRecord.run_mode == run_mode)
        )
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord).where(PositionRecord.run_mode == run_mode)
                )
            ).all()
        )
        plans = list(
            (
                await session.scalars(
                    select(TradePlanRecord).where(TradePlanRecord.run_mode == run_mode)
                )
            ).all()
        )
        decision_ids = {row.decision_id for row in plans}
        decisions = (
            list(
                (
                    await session.scalars(
                        select(AIDecisionRecord).where(
                            AIDecisionRecord.decision_id.in_(decision_ids)
                        )
                    )
                ).all()
            )
            if decision_ids
            else []
        )
        if len(decisions) != len(decision_ids):
            raise SnapshotError("active plan decision missing")
        snapshot_ids = {row.snapshot_id for row in decisions}
        snapshots = (
            list(
                (
                    await session.scalars(
                        select(DecisionSnapshotRecord).where(
                            DecisionSnapshotRecord.snapshot_id.in_(snapshot_ids)
                        )
                    )
                ).all()
            )
            if snapshot_ids
            else []
        )
        snapshot_by_id = {row.snapshot_id: row for row in snapshots}
        invocation_ids = {
            value
            for value in (
                *(row.decision_invocation_id for row in decisions),
                *(row.decision_invocation_id for row in snapshots),
            )
            if value is not None
        }
        invocations = (
            list(
                (
                    await session.scalars(
                        select(AdvisoryDecisionInvocationRecord).where(
                            AdvisoryDecisionInvocationRecord.decision_invocation_id.in_(
                                invocation_ids
                            )
                        )
                    )
                ).all()
            )
            if invocation_ids
            else []
        )
        evidence_ids = {row.evidence_id for row in snapshots if row.evidence_id is not None}
        evidence = (
            list(
                (
                    await session.scalars(
                        select(EdgeOpportunityEvidenceRecord).where(
                            EdgeOpportunityEvidenceRecord.evidence_id.in_(evidence_ids)
                        )
                    )
                ).all()
            )
            if evidence_ids
            else []
        )
        attribution = list((await session.scalars(select(EdgeAttributionEventRecord))).all())
        decision_nodes = _project_decision_nodes(
            decisions,
            snapshot_by_id,
            {row.decision_invocation_id: row for row in invocations},
            {row.evidence_id: row for row in evidence},
            attribution,
        )
        all_accounts = list((await session.scalars(select(AccountRecord))).all())
        all_intents = list((await session.scalars(select(ExecutionIntentRecord))).all())
        all_orders = list((await session.scalars(select(PaperOrderRecord))).all())
        intents = [row for row in all_intents if row.run_mode == run_mode]
        orders = [row for row in all_orders if row.run_mode == run_mode]
        outbox = list((await session.scalars(select(OutboxRecord))).all())
        trades = list(
            (
                await session.scalars(select(TradeRecord).where(TradeRecord.run_mode == run_mode))
            ).all()
        )
        position_events = list(
            (
                await session.scalars(
                    select(PositionEventRecord).where(PositionEventRecord.run_mode == run_mode)
                )
            ).all()
        )
        # Fill/Ledger have no run_mode. Load the whole population first so an orphan cannot disappear in a join.
        all_fills = list((await session.scalars(select(FillRecord))).all())
        all_ledgers = list((await session.scalars(select(LedgerEntryRecord))).all())
        order_modes = {row.order_id: row.run_mode for row in all_orders}
        intent_modes = {row.intent_id: row.run_mode for row in all_intents}
        fills = []
        fill_modes: dict[str, str] = {}
        for fill in all_fills:
            ownership = _ownership(
                anchors=[order_modes.get(fill.order_id), intent_modes.get(fill.intent_id)],
                current_run_mode=run_mode,
            )
            if ownership in {"CONFLICTING_SCOPE", "UNSCOPED"}:
                raise SnapshotError("unscoped/conflicting fill")
            fill_modes[fill.fill_id] = order_modes[fill.order_id]
            if ownership == "PROVEN_CURRENT":
                fills.append(fill)
        account_modes = {row.account_id: row.run_mode for row in all_accounts}
        ledgers = []
        for ledger in all_ledgers:
            ownership = _ownership(
                anchors=[account_modes.get(ledger.account_id), fill_modes.get(ledger.fill_id)],
                current_run_mode=run_mode,
            )
            if ownership in {"CONFLICTING_SCOPE", "UNSCOPED"}:
                raise SnapshotError("unscoped/conflicting ledger")
            if ownership == "PROVEN_CURRENT":
                ledgers.append(ledger)
        _validate(account, positions, intents, orders, fills, ledgers, trades)
        timeline_items, next_cursor = _timeline_page(
            _build_timeline(
                plans=plans,
                intents=intents,
                orders=orders,
                fills=fills,
                ledgers=ledgers,
                outbox=outbox,
                trades=trades,
                position_events=position_events,
                attribution=attribution,
                decision_nodes=decision_nodes,
            ),
            upper=upper,
            limit=limit,
            cursor=cursor,
            run_mode=run_mode,
            instrument_id=instrument_id,
        )
        position_items = sorted(
            (
                _position(row)
                for row in positions
                if instrument_id is None or row.instrument_id == instrument_id
            ),
            key=lambda row: row.instrument_id,
        )
        account_node = (
            TraceNodeDTO[TradingAccountDTO](state=TraceNodeState.NO_PROVABLE_RECORD)
            if account is None
            else TraceNodeDTO(
                state=TraceNodeState.PRESENT,
                evidence_basis="durable_account",
                data=TradingAccountDTO(
                    account_id=account.account_id,
                    cash_balance=account.cash_balance,
                    reserved_cash=account.reserved_cash,
                    available_cash=account.cash_balance - account.reserved_cash,
                    realized_pnl=account.realized_pnl,
                    updated_at=_utc(account.updated_at),
                ),
            )
        )
        open_items = sorted(
            (
                TradingOpenOrderDTO(
                    order_id=row.order_id,
                    intent_id=row.intent_id,
                    plan_id=row.plan_id or None,
                    instrument_id=row.instrument_id,
                    side=row.side,
                    order_type=row.order_type,
                    quantity=row.quantity,
                    limit_price=row.limit_price,
                    reserved_cash=row.reserved_cash,
                    reserved_quantity=row.reserved_quantity,
                    created_at=_utc(row.created_at),
                )
                for row in orders
                if row.status == OrderStatus.OPEN
                and (instrument_id is None or row.instrument_id == instrument_id)
            ),
            key=lambda row: (row.created_at, row.order_id),
            reverse=True,
        )
        plan_items = _project_active_plans(plans, snapshot_at, instrument_id, decision_nodes)
        data = TradingAuditDataDTO(
            account=account_node,
            positions=TradingCollectionDTO(
                state=ProjectionState.FRESH if position_items else ProjectionState.EMPTY,
                items=position_items,
            ),
            active_plans=TradingCollectionDTO(
                state=ProjectionState.FRESH if plan_items else ProjectionState.EMPTY,
                items=plan_items,
            ),
            open_orders=TradingCollectionDTO(
                state=ProjectionState.FRESH if open_items else ProjectionState.EMPTY,
                items=open_items,
            ),
            pending_intents=TradingPendingIntentCapabilityDTO(
                state=ProjectionState.CAPABILITY_NOT_INTEGRATED
            ),
            timeline=TradingTimelinePageDTO(
                state=ProjectionState.FRESH if timeline_items else ProjectionState.EMPTY,
                items=timeline_items,
                timeline_upper_bound=upper,
            ),
        )
        return data, snapshot_at, next_cursor


@router.get(
    "/trading-audit",
    response_model=TradingAuditReadResponse,
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid query/cursor"},
        503: {"model": ProductUnavailableResponse},
        500: {"model": ProductInternalErrorResponse},
    },
)
async def trading_audit_read(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
    instrument_id: str | None = Query(None, min_length=1, max_length=64),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> TradingAuditReadResponse | JSONResponse:
    try:
        decoded = None if cursor is None else decode_trading_audit_cursor(cursor)
        context = ProductReadContext.from_request(request)
        if context.host is None:
            now = datetime.now(UTC)
            return TradingAuditReadResponse(
                meta=ProjectionMetaDTO(
                    projection=PROJECTION,
                    read_surface_class=ReadSurfaceClass.A,
                    operational_availability=OperationalAvailability.NOT_ACTIVATED,
                    projection_state=ProjectionState.UNAVAILABLE,
                    snapshot_at=now,
                    is_partial=False,
                ),
                operational_context=_context(settings, None, now),
                data=None,
            )
        data, snapshot_at, next_cursor = await _read(
            context, instrument_id=instrument_id, limit=limit, cursor=decoded
        )
        return TradingAuditReadResponse(
            meta=ProjectionMetaDTO(
                projection=PROJECTION,
                read_surface_class=ReadSurfaceClass.A,
                operational_availability=OperationalAvailability.ACTIVE,
                projection_state=ProjectionState.FRESH,
                snapshot_at=snapshot_at,
                observed_at=None,
                is_partial=False,
                next_cursor=next_cursor,
            ),
            operational_context=_context(settings, context, datetime.now(UTC)),
            data=data,
        )
    except HTTPException:
        raise
    except ProductCursorError:
        raise HTTPException(422, "invalid trading audit cursor") from None
    except SnapshotError:
        return _unavailable(ReadFailureReason.SNAPSHOT_FAILED, new_id().hex)
    except SourceError:
        return _unavailable(ReadFailureReason.SOURCE_UNAVAILABLE, new_id().hex)
    except Exception:  # noqa: BLE001 -- deliberately sanitized Product boundary
        return JSONResponse(
            status_code=500,
            content=ProductInternalErrorResponse(correlation_id=new_id().hex).model_dump(
                mode="json"
            ),
        )
