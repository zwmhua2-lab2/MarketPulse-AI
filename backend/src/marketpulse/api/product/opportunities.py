"""Authenticated Opportunity Collection and Trace Product reads.

This module owns no Opportunity persistence and performs no activation.  It
projects the accepted Edge durable records inside one Host-borrowed read-only
snapshot and delegates revision reconstruction/folding to SE-02D.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings
from marketpulse.db.models import (
    AIDecisionRecord,
    EdgeAttributionEventRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityEvidenceRecord,
    MarketEventRecord,
    StrategyCandidateRecord,
)
from marketpulse.edge.aggregation_snapshot import (
    SnapshotIntegrityError,
    fold_evidence_records,
    fold_outcome_records,
    validate_canonical_outcome,
)
from marketpulse.edge.attribution import AttributionEventType
from marketpulse.edge.forward import forward_due_at
from marketpulse.edge.models import AttributionSubjectType, EvidenceSource, ForwardHorizon
from marketpulse.ids import new_id

from .context import ProductReadContext
from .cursor import (
    OpportunityCursor,
    ProductCursorError,
    decode_opportunity_cursor,
    encode_opportunity_cursor,
)
from .models import (
    PRODUCT_READ_CONTRACT_VERSION,
    DecisionTraceDTO,
    EvidenceIdentityDTO,
    ForwardOutcomeTraceDTO,
    MarketEventTraceDTO,
    OperationalAvailability,
    OperationalContextDTO,
    OpportunityCollectionReadResponse,
    OpportunityDTO,
    OpportunityPageDTO,
    OpportunityTraceDataDTO,
    OpportunityTraceReadResponse,
    ProductInternalErrorResponse,
    ProductUnavailableResponse,
    ProjectionMetaDTO,
    ProjectionState,
    RangeContextDTO,
    ReadFailureReason,
    ReadSurfaceClass,
    StrategyCandidateTraceDTO,
    TraceNodeDTO,
    TraceNodeState,
    TradingDecisionBranchDTO,
)

router = APIRouter(tags=["product-read"])
logger = logging.getLogger(__name__)

COLLECTION_PROJECTION = "OpportunityCollectionRead"
TRACE_PROJECTION = "OpportunityTraceRead"
OPERATIONAL_PROVENANCE = EvidenceSource.FORWARD_PAPER.value


class _OpportunitySourceUnavailableError(Exception):
    """Typed boundary for failures while acquiring the durable Product source."""


_SOURCE_DRIVER_ERRORS = (
    asyncio.TimeoutError,
    OSError,
    asyncpg.exceptions.CannotConnectNowError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.ConnectionFailureError,
    asyncpg.exceptions.InvalidAuthorizationSpecificationError,
    asyncpg.exceptions.InvalidPasswordError,
)


def _is_source_unavailable_error(exc: BaseException) -> bool:
    """Classify only the finite durable-source acquisition error chain."""

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (SQLAlchemyError, *_SOURCE_DRIVER_ERRORS)):
            return True
        cause = current.__cause__
        current = cause if cause is not None else current.__context__
    return False


async def _source_await(awaitable: object) -> object:
    """Translate only failures from an actual durable-source await."""

    try:
        return await awaitable
    except Exception as exc:
        if _is_source_unavailable_error(exc):
            raise _OpportunitySourceUnavailableError(
                "opportunity source acquisition failed"
            ) from exc
        raise


@asynccontextmanager
async def _source_transaction(context: ProductReadContext):
    """Enter and leave the Product durable source at the source boundary."""

    if context.sessions is None:
        raise _OpportunitySourceUnavailableError("product session factory unavailable")
    session_context = context.sessions()
    session = await _source_await(session_context.__aenter__())
    transaction_context = session.begin()
    try:
        await _source_await(transaction_context.__aenter__())
    except BaseException as exc:
        await _source_await(session_context.__aexit__(type(exc), exc, exc.__traceback__))
        raise
    try:
        yield session
    except BaseException as exc:
        try:
            await _source_await(transaction_context.__aexit__(type(exc), exc, exc.__traceback__))
        finally:
            await _source_await(session_context.__aexit__(type(exc), exc, exc.__traceback__))
        raise
    else:
        try:
            await _source_await(transaction_context.__aexit__(None, None, None))
        finally:
            await _source_await(session_context.__aexit__(None, None, None))


class OpportunityRange(StrEnum):
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    CUSTOM = "custom"


_PRESET_DURATIONS: dict[OpportunityRange, timedelta] = {
    OpportunityRange.FIFTEEN_MINUTES: timedelta(minutes=15),
    OpportunityRange.THIRTY_MINUTES: timedelta(minutes=30),
    OpportunityRange.ONE_HOUR: timedelta(hours=1),
    OpportunityRange.FOUR_HOURS: timedelta(hours=4),
    OpportunityRange.SIX_HOURS: timedelta(hours=6),
    OpportunityRange.TWENTY_FOUR_HOURS: timedelta(hours=24),
    OpportunityRange.SEVEN_DAYS: timedelta(days=7),
    OpportunityRange.THIRTY_DAYS: timedelta(days=30),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _invalid_request(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=[{"loc": ["query"], "msg": detail, "type": "value_error"}],
    )


@dataclass(frozen=True)
class _ResolvedRange:
    requested_range: OpportunityRange
    effective_start: datetime
    effective_end: datetime
    source_type: EvidenceSource
    cursor: OpportunityCursor | None


def _resolve_range(
    *,
    requested_range: OpportunityRange,
    start: datetime | None,
    end: datetime | None,
    source_type: EvidenceSource,
    cursor_value: str | None,
) -> _ResolvedRange:
    """Validate range/cursor before touching Host or source availability."""
    if requested_range is OpportunityRange.CUSTOM:
        if start is None or end is None:
            raise _invalid_request("custom range requires both start and end")
        if start.tzinfo is None or end.tzinfo is None:
            raise _invalid_request("custom range timestamps must be timezone-aware")
        effective_start, effective_end = _as_utc(start), _as_utc(end)
        if effective_start >= effective_end:
            raise _invalid_request("custom range start must precede end")
    else:
        if start is not None or end is not None:
            raise _invalid_request("start and end are valid only for range=custom")
        effective_end = _now()
        effective_start = effective_end - _PRESET_DURATIONS[requested_range]

    decoded: OpportunityCursor | None = None
    if cursor_value is not None:
        try:
            decoded = decode_opportunity_cursor(cursor_value)
        except ProductCursorError as exc:
            raise _invalid_request("invalid opportunity cursor") from exc
        if decoded.requested_range != requested_range.value:
            raise _invalid_request("opportunity cursor range does not match request")
        if decoded.source_type != source_type.value:
            raise _invalid_request("opportunity cursor provenance does not match request")
        if requested_range is OpportunityRange.CUSTOM and (
            decoded.effective_start != effective_start or decoded.effective_end != effective_end
        ):
            raise _invalid_request("opportunity custom range does not match cursor")
        effective_start, effective_end = decoded.effective_start, decoded.effective_end
    return _ResolvedRange(
        requested_range=requested_range,
        effective_start=effective_start,
        effective_end=effective_end,
        source_type=source_type,
        cursor=decoded,
    )


def _range_context(value: _ResolvedRange) -> RangeContextDTO:
    return RangeContextDTO(
        requested_range=value.requested_range.value,
        effective_start=value.effective_start,
        effective_end=value.effective_end,
        time_authority_field="detected_at",
    )


def _operational_context(
    *, settings: Settings, context: ProductReadContext | None, now: datetime
) -> OperationalContextDTO:
    host = None if context is None else context.host
    return OperationalContextDTO(
        run_mode=settings.run_mode if host is None else host.run_mode.value,
        runtime_instance_id=None if host is None else host.instance_id,
        host_state=None if host is None else host.state,
        operational_provenance=OPERATIONAL_PROVENANCE,
        context_snapshot_at=now,
    )


def _evidence_identity(evidence: object) -> EvidenceIdentityDTO:
    return EvidenceIdentityDTO(
        evidence_id=evidence.evidence_id,
        evidence_revision=evidence.evidence_revision,
        evidence_hash=evidence.evidence_hash,
        feature_snapshot_hash=evidence.feature_snapshot_hash,
    )


def _opportunity_dto(
    evidence: object, *, logical_detected_at: datetime | None = None
) -> OpportunityDTO:
    return OpportunityDTO(
        opportunity_id=evidence.opportunity_id,
        candidate_id=evidence.candidate_id,
        family_id=evidence.family_id.value,
        family_version=evidence.family_version,
        instrument_id=evidence.instrument_id,
        market_type=evidence.market_type.value,
        detected_at=_as_utc(
            evidence.detected_at if logical_detected_at is None else logical_detected_at
        ),
        evidence_at=_as_utc(evidence.evidence_at),
        expires_at=_as_utc(evidence.expires_at),
        source_type=evidence.source_type.value,
        source_identity=evidence.source_identity,
        evidence_contract_version=evidence.evidence_contract_version,
        current_canonical_evidence=_evidence_identity(evidence),
    )


def _logical_detected_at(fold: object) -> datetime:
    """Logical Opportunity time is the first accepted revision's detection fact.

    Evidence revisions may correct their own recorded fields.  A later revision
    must never mint a new logical Opportunity or move its collection range/sort
    position, so revision 1 remains the durable detection-time authority.
    """
    revisions = (*fold.folded, fold.canonical)
    first = min(revisions, key=lambda item: item.evidence_revision)
    return _as_utc(first.detected_at)


def _host_absent_collection(
    *, settings: Settings, range_value: _ResolvedRange
) -> OpportunityCollectionReadResponse:
    now = _now()
    return OpportunityCollectionReadResponse(
        meta=ProjectionMetaDTO(
            projection=COLLECTION_PROJECTION,
            read_surface_class=ReadSurfaceClass.A,
            operational_availability=OperationalAvailability.NOT_ACTIVATED,
            projection_state=ProjectionState.UNAVAILABLE,
            snapshot_at=now,
            is_partial=False,
        ),
        operational_context=_operational_context(settings=settings, context=None, now=now),
        range_context=_range_context(range_value),
        data=None,
    )


def _host_absent_trace(*, settings: Settings) -> OpportunityTraceReadResponse:
    now = _now()
    return OpportunityTraceReadResponse(
        meta=ProjectionMetaDTO(
            projection=TRACE_PROJECTION,
            read_surface_class=ReadSurfaceClass.A,
            operational_availability=OperationalAvailability.NOT_ACTIVATED,
            projection_state=ProjectionState.UNAVAILABLE,
            snapshot_at=now,
            is_partial=False,
        ),
        operational_context=_operational_context(settings=settings, context=None, now=now),
        data=None,
    )


def _unavailable(
    *, projection: str, reason: ReadFailureReason, correlation_id: str
) -> JSONResponse:
    body = ProductUnavailableResponse(
        projection=projection,
        contract_version=PRODUCT_READ_CONTRACT_VERSION,
        read_surface_class=ReadSurfaceClass.A,
        read_failure_reason=reason,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump(mode="json")
    )


def _internal_error(*, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ProductInternalErrorResponse(correlation_id=correlation_id).model_dump(mode="json"),
    )


async def _begin_snapshot(session: object) -> datetime:
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        return _as_utc(await session.scalar(text("SELECT statement_timestamp()")))
    # SQLite is a focused-test adapter only; deployed Product reads use PostgreSQL above.
    return _as_utc(await session.scalar(select(func.current_timestamp())))


async def _collection_page(
    context: ProductReadContext, *, range_value: _ResolvedRange, limit: int
) -> OpportunityPageDTO:
    async with _source_transaction(context) as session:
        try:
            as_of = await _source_await(_begin_snapshot(session))
            root = aliased(EdgeOpportunityEvidenceRecord)
            provenance = aliased(EdgeOpportunityEvidenceRecord)
            root_scope = [
                root.evidence_revision == 1,
                provenance.source_type == range_value.source_type.value,
                root.detected_at >= range_value.effective_start,
                root.detected_at < range_value.effective_end,
            ]
            if range_value.cursor is not None:
                cursor = range_value.cursor
                root_scope.append(
                    or_(
                        root.detected_at < cursor.detected_at,
                        and_(
                            root.detected_at == cursor.detected_at,
                            root.opportunity_id < cursor.opportunity_id,
                        ),
                    )
                )
            rooted_ids = set(
                (
                    await _source_await(session.scalars(
                        select(root.opportunity_id)
                        .join(provenance, provenance.opportunity_id == root.opportunity_id)
                        .where(*root_scope)
                        .distinct()
                    ))
                ).all()
            )
            root_exists = (
                select(root.opportunity_id)
                .where(
                    root.opportunity_id == EdgeOpportunityEvidenceRecord.opportunity_id,
                    root.evidence_revision == 1,
                )
                .exists()
            )
            malformed_scope = [
                EdgeOpportunityEvidenceRecord.evidence_revision != 1,
                ~root_exists,
                EdgeOpportunityEvidenceRecord.source_type == range_value.source_type.value,
                EdgeOpportunityEvidenceRecord.detected_at >= range_value.effective_start,
                EdgeOpportunityEvidenceRecord.detected_at < range_value.effective_end,
            ]
            if range_value.cursor is not None:
                cursor = range_value.cursor
                malformed_scope.append(
                    or_(
                        EdgeOpportunityEvidenceRecord.detected_at < cursor.detected_at,
                        and_(
                            EdgeOpportunityEvidenceRecord.detected_at == cursor.detected_at,
                            EdgeOpportunityEvidenceRecord.opportunity_id < cursor.opportunity_id,
                        ),
                    )
                )
            malformed_ids = set(
                (
                    await _source_await(session.scalars(
                        select(EdgeOpportunityEvidenceRecord.opportunity_id)
                        .where(*malformed_scope)
                        .distinct()
                    ))
                ).all()
            )
            scoped_ids = rooted_ids | malformed_ids
            records = (
                []
                if not scoped_ids
                else list(
                    (
                        await _source_await(session.scalars(
                            select(EdgeOpportunityEvidenceRecord).where(
                                EdgeOpportunityEvidenceRecord.opportunity_id.in_(scoped_ids)
                            )
                        ))
                    ).all()
                )
            )
            folds = fold_evidence_records(records)
            canonical = [
                (fold, _logical_detected_at(fold))
                for fold in folds.values()
                if fold.canonical.source_type == range_value.source_type
                and range_value.effective_start
                <= _logical_detected_at(fold)
                < range_value.effective_end
            ]
            canonical.sort(key=lambda item: (item[1], item[0].opportunity_id), reverse=True)
            if range_value.cursor is not None:
                after = range_value.cursor
                canonical = [
                    item
                    for item in canonical
                    if (item[1], item[0].opportunity_id) < (after.detected_at, after.opportunity_id)
                ]
            page, extra = canonical[:limit], canonical[limit:]
            next_cursor = None
            if extra and page:
                last, last_detected_at = page[-1]
                next_cursor = encode_opportunity_cursor(
                    OpportunityCursor(
                        requested_range=range_value.requested_range.value,
                        effective_start=range_value.effective_start,
                        effective_end=range_value.effective_end,
                        source_type=range_value.source_type.value,
                        detected_at=last_detected_at,
                        opportunity_id=last.opportunity_id,
                    )
                )
            return OpportunityPageDTO(
                items=[
                    _opportunity_dto(fold.canonical, logical_detected_at=detected_at)
                    for fold, detected_at in page
                ],
                next_cursor=next_cursor,
                as_of=as_of,
            )
        except _OpportunitySourceUnavailableError as exc:
            raise _OpportunitySourceUnavailableError(
                "opportunity source operation failed"
            ) from exc


def _node(
    state: TraceNodeState, data: object | None = None, basis: str | None = None
) -> TraceNodeDTO[object]:
    return TraceNodeDTO[object](state=state, data=data, evidence_basis=basis)


def _forward_nodes(
    *, evidence: object, outcome_records: list[EdgeForwardOutcomeRecord], as_of: datetime
) -> dict[str, TraceNodeDTO[ForwardOutcomeTraceDTO]]:
    nodes: dict[str, TraceNodeDTO[ForwardOutcomeTraceDTO]] = {}
    for horizon in ForwardHorizon:
        due_at = forward_due_at(evidence.evidence_at, horizon)
        records = [record for record in outcome_records if record.horizon == horizon.value]
        folds = fold_outcome_records(records)
        fold = folds.get((evidence.opportunity_id, evidence.evidence_id))
        outcome = None if fold is None else fold.canonical
        validate_canonical_outcome(evidence, outcome, horizon=horizon)
        if outcome is not None:
            nodes[horizon.value] = TraceNodeDTO(
                state=TraceNodeState.PRESENT,
                data=ForwardOutcomeTraceDTO(
                    outcome_id=outcome.outcome_id,
                    outcome_revision=outcome.outcome_revision,
                    outcome_record_hash=outcome.outcome_record_hash,
                    calculation_status=outcome.calculation_status.value,
                    due_at=_as_utc(outcome.due_at),
                ),
                evidence_basis="canonical_forward_outcome_revision",
            )
        elif as_of < due_at:
            nodes[horizon.value] = TraceNodeDTO(state=TraceNodeState.NOT_YET_DUE)
        else:
            nodes[horizon.value] = TraceNodeDTO(state=TraceNodeState.CAPABILITY_NOT_INTEGRATED)
    return nodes


def _decision_node(
    *,
    opportunity_id: str,
    evidence_by_id: dict[str, object],
    attributions: list[EdgeAttributionEventRecord],
    decisions: dict[str, AIDecisionRecord],
) -> TraceNodeDTO[TradingDecisionBranchDTO]:
    ai_events = [row for row in attributions if row.subject_type == AttributionSubjectType.AI.value]
    event_types = {row.event_type for row in ai_events}
    if AttributionEventType.AI_NOT_REACHED.value in event_types:
        if event_types != {AttributionEventType.AI_NOT_REACHED.value} or any(
            row.subject_id is not None
            or row.evidence_id is not None
            or row.opportunity_id != opportunity_id
            for row in ai_events
        ):
            raise SnapshotIntegrityError((f"conflicting_ai_attribution:{opportunity_id}",))
        return TraceNodeDTO(state=TraceNodeState.NOT_REACHED, evidence_basis="AI_NOT_REACHED")
    if not ai_events:
        return TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)

    grouped: dict[str, list[EdgeAttributionEventRecord]] = {}
    for row in ai_events:
        if row.evidence_id is not None:
            evidence = evidence_by_id.get(row.evidence_id)
            if evidence is None or evidence.opportunity_id != opportunity_id:
                raise SnapshotIntegrityError(
                    (f"invalid_ai_attribution_evidence:{opportunity_id}:{row.evidence_id}",)
                )
        if row.subject_id is None:
            continue
        grouped.setdefault(row.subject_id, []).append(row)
    traces: list[DecisionTraceDTO] = []
    for decision_id, rows in grouped.items():
        if any(row.opportunity_id != opportunity_id for row in rows):
            raise SnapshotIntegrityError(
                (f"invalid_ai_attribution_subject:{opportunity_id}:{decision_id}",)
            )
        event_semantics = {row.event_type for row in rows}
        if len(event_semantics) != 1:
            raise SnapshotIntegrityError(
                (f"conflicting_ai_attribution_event:{opportunity_id}:{decision_id}",)
            )
        exact_evidence_ids = {row.evidence_id for row in rows if row.evidence_id is not None}
        if len(exact_evidence_ids) > 1:
            raise SnapshotIntegrityError(
                (f"conflicting_ai_attribution:{opportunity_id}:{decision_id}",)
            )
        if decision_id not in decisions:
            continue
        exact_evidence_id = next(iter(exact_evidence_ids), None)
        decision_bound_evidence: TraceNodeDTO[EvidenceIdentityDTO]
        if exact_evidence_id is None:
            decision_bound_evidence = TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
        else:
            evidence = evidence_by_id[exact_evidence_id]
            decision_bound_evidence = TraceNodeDTO(
                state=TraceNodeState.PRESENT,
                data=_evidence_identity(evidence),
                evidence_basis="exact_edge_attribution",
            )
        traces.append(
            DecisionTraceDTO(
                decision_id=decision_id,
                status=decisions[decision_id].status,
                attribution_event_type=next(iter(event_semantics)),
                decision_bound_evidence=decision_bound_evidence,
            )
        )
    if not traces:
        return TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
    traces.sort(key=lambda item: item.decision_id)
    return TraceNodeDTO(
        state=TraceNodeState.PRESENT,
        data=TradingDecisionBranchDTO(decisions=traces),
        evidence_basis="exact_edge_attribution",
    )


async def _trace(
    context: ProductReadContext, *, opportunity_id: str, source_type: EvidenceSource
) -> OpportunityTraceDataDTO | None:
    async with _source_transaction(context) as session:
        try:
            as_of = await _source_await(_begin_snapshot(session))
            evidence_records = list(
                (
                    await _source_await(session.scalars(
                        select(EdgeOpportunityEvidenceRecord).where(
                            EdgeOpportunityEvidenceRecord.opportunity_id == opportunity_id
                        )
                    ))
                ).all()
            )
            if not evidence_records:
                return None
            evidence_fold = fold_evidence_records(evidence_records).get(opportunity_id)
            if evidence_fold is None or evidence_fold.canonical.source_type != source_type:
                return None
            evidence = evidence_fold.canonical
            outcome_records = list(
                (
                    await _source_await(session.scalars(
                        select(EdgeForwardOutcomeRecord).where(
                            EdgeForwardOutcomeRecord.opportunity_id == opportunity_id
                        )
                    ))
                ).all()
            )
            candidate = await _source_await(
                session.get(StrategyCandidateRecord, evidence.candidate_id)
            )
            market_event = (
                None
                if candidate is None
                else await _source_await(session.get(MarketEventRecord, candidate.event_id))
            )
            attributions = list(
                (
                    await _source_await(session.scalars(
                        select(EdgeAttributionEventRecord).where(
                            EdgeAttributionEventRecord.opportunity_id == opportunity_id
                        )
                    ))
                ).all()
            )
            decision_ids = {
                row.subject_id
                for row in attributions
                if row.subject_id is not None
                and row.subject_type == AttributionSubjectType.AI.value
            }
            decision_rows = (
                []
                if not decision_ids
                else list(
                    (
                        await _source_await(session.scalars(
                            select(AIDecisionRecord).where(
                                AIDecisionRecord.decision_id.in_(decision_ids)
                            )
                        ))
                    ).all()
                )
            )
            decisions = {row.decision_id: row for row in decision_rows}
            evidence_by_id = {
                revision.evidence_id: revision
                for revision in (evidence_fold.canonical, *evidence_fold.folded)
            }
        except _OpportunitySourceUnavailableError as exc:
            raise _OpportunitySourceUnavailableError(
                "opportunity source operation failed"
            ) from exc
        candidate_node: TraceNodeDTO[StrategyCandidateTraceDTO]
        event_node: TraceNodeDTO[MarketEventTraceDTO]
        if candidate is None:
            candidate_node = TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
            event_node = TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
        else:
            candidate_node = TraceNodeDTO(
                state=TraceNodeState.PRESENT,
                data=StrategyCandidateTraceDTO(
                    candidate_id=candidate.candidate_id,
                    event_id=candidate.event_id,
                    strategy_id=candidate.strategy_id,
                    strategy_version=candidate.strategy_version,
                    created_at=_as_utc(candidate.created_at),
                ),
                evidence_basis="evidence.candidate_id",
            )
            if market_event is None:
                event_node = TraceNodeDTO(state=TraceNodeState.NO_PROVABLE_RECORD)
            else:
                event_node = TraceNodeDTO(
                    state=TraceNodeState.PRESENT,
                    data=MarketEventTraceDTO(
                        event_id=market_event.event_id,
                        event_type=market_event.event_type,
                        event_time=_as_utc(market_event.event_time),
                        instrument_id=market_event.instrument_id,
                        market_type=market_event.market_type,
                    ),
                    evidence_basis="strategy_candidate.event_id",
                )
        return OpportunityTraceDataDTO(
            market_event=event_node,
            strategy_candidate=candidate_node,
            opportunity=_opportunity_dto(
                evidence, logical_detected_at=_logical_detected_at(evidence_fold)
            ),
            current_canonical_evidence=_evidence_identity(evidence),
            forward_outcomes=_forward_nodes(
                evidence=evidence, outcome_records=outcome_records, as_of=as_of
            ),
            trading_decision=_decision_node(
                opportunity_id=opportunity_id,
                evidence_by_id=evidence_by_id,
                attributions=attributions,
                decisions=decisions,
            ),
            as_of=as_of,
        )


@router.get(
    "/opportunities",
    response_model=OpportunityCollectionReadResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ProductUnavailableResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ProductInternalErrorResponse},
    },
)
async def opportunity_collection_read(
    request: Request,
    range_value: OpportunityRange = Query(default=OpportunityRange.ONE_HOUR, alias="range"),  # noqa: B008
    start: datetime | None = Query(default=None),  # noqa: B008
    end: datetime | None = Query(default=None),  # noqa: B008
    source_type: EvidenceSource = Query(default=EvidenceSource.FORWARD_PAPER),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> OpportunityCollectionReadResponse | JSONResponse:
    try:
        resolved = _resolve_range(
            requested_range=range_value,
            start=start,
            end=end,
            source_type=source_type,
            cursor_value=cursor,
        )
        context = ProductReadContext.from_request(request)
        if context.host is None:
            return _host_absent_collection(settings=settings, range_value=resolved)
        page = await _collection_page(context, range_value=resolved, limit=limit)
        now = _now()
        return OpportunityCollectionReadResponse(
            meta=ProjectionMetaDTO(
                projection=COLLECTION_PROJECTION,
                read_surface_class=ReadSurfaceClass.A,
                operational_availability=OperationalAvailability.ACTIVE,
                projection_state=ProjectionState.EMPTY if not page.items else ProjectionState.FRESH,
                snapshot_at=page.as_of,
                observed_at=now,
                is_partial=False,
                next_cursor=page.next_cursor,
            ),
            operational_context=_operational_context(settings=settings, context=context, now=now),
            range_context=_range_context(resolved),
            data=page,
        )
    except HTTPException:
        raise
    except SnapshotIntegrityError as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_collection_integrity_failed correlation_id=%s",
            correlation_id,
            exc_info=exc,
        )
        return _unavailable(
            projection=COLLECTION_PROJECTION,
            reason=ReadFailureReason.SNAPSHOT_FAILED,
            correlation_id=correlation_id,
        )
    except _OpportunitySourceUnavailableError as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_collection_source_failed correlation_id=%s", correlation_id, exc_info=exc
        )
        return _unavailable(
            projection=COLLECTION_PROJECTION,
            reason=ReadFailureReason.SOURCE_UNAVAILABLE,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_collection_internal_failed correlation_id=%s", correlation_id, exc_info=exc
        )
        return _internal_error(correlation_id=correlation_id)


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityTraceReadResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Opportunity absent in selected provenance"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ProductUnavailableResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ProductInternalErrorResponse},
    },
)
async def opportunity_trace_read(
    request: Request,
    opportunity_id: str,
    source_type: EvidenceSource = Query(default=EvidenceSource.FORWARD_PAPER),  # noqa: B008
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> OpportunityTraceReadResponse | JSONResponse:
    try:
        context = ProductReadContext.from_request(request)
        if context.host is None:
            return _host_absent_trace(settings=settings)
        data = await _trace(context, opportunity_id=opportunity_id, source_type=source_type)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="opportunity not found"
            )
        now = _now()
        return OpportunityTraceReadResponse(
            meta=ProjectionMetaDTO(
                projection=TRACE_PROJECTION,
                read_surface_class=ReadSurfaceClass.A,
                operational_availability=OperationalAvailability.ACTIVE,
                projection_state=ProjectionState.FRESH,
                snapshot_at=data.as_of,
                observed_at=now,
                is_partial=False,
            ),
            operational_context=_operational_context(settings=settings, context=context, now=now),
            data=data,
        )
    except HTTPException:
        raise
    except SnapshotIntegrityError as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_trace_integrity_failed correlation_id=%s", correlation_id, exc_info=exc
        )
        return _unavailable(
            projection=TRACE_PROJECTION,
            reason=ReadFailureReason.SNAPSHOT_FAILED,
            correlation_id=correlation_id,
        )
    except _OpportunitySourceUnavailableError as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_trace_source_failed correlation_id=%s", correlation_id, exc_info=exc
        )
        return _unavailable(
            projection=TRACE_PROJECTION,
            reason=ReadFailureReason.SOURCE_UNAVAILABLE,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        correlation_id = new_id().hex
        logger.error(
            "opportunity_trace_internal_failed correlation_id=%s", correlation_id, exc_info=exc
        )
        return _internal_error(correlation_id=correlation_id)
