"""Authenticated SystemIncidentRead Product projection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, desc, or_, select

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings
from marketpulse.db.models import IncidentRecord
from marketpulse.g4.models import IncidentStatus, IncidentType
from marketpulse.ids import new_id
from marketpulse.runtime import HostReadinessStatus

from .context import ProductReadContext
from .cursor import (
    IncidentCursor,
    ProductCursorError,
    decode_incident_cursor,
    encode_incident_cursor,
    incident_filter_fingerprint,
)
from .market_scanner import router as market_scanner_router
from .models import (
    PRODUCT_READ_CONTRACT_VERSION,
    AIActivationDTO,
    DatabaseSingletonDTO,
    HealthCheckDTO,
    HealthDTO,
    IncidentDTO,
    IncidentPageDTO,
    LanesDTO,
    LaneTelemetryDTO,
    LiveDTO,
    MarketInstrumentDTO,
    MarketProviderDTO,
    OperationalAvailability,
    OperationalContextDTO,
    OperatorSystemStateDTO,
    ProductInternalErrorResponse,
    ProductUnavailableResponse,
    ProjectionMetaDTO,
    ProjectionState,
    ProviderDTO,
    ProviderSubscriptionDTO,
    ReadFailureReason,
    ReadSurfaceClass,
    ReadyDTO,
    ReconciliationDTO,
    RecoveryDTO,
    RuntimeDTO,
    RuntimeGatesDTO,
    RuntimeTimestampsDTO,
    SourceContextDTO,
    SystemIncidentDataDTO,
    SystemIncidentReadResponse,
    SystemSectionDTO,
)
from .opportunities import router as opportunities_router
from .trading_audit import router as trading_audit_router

router = APIRouter(prefix="/api/v1/product", tags=["product-read"])
router.include_router(market_scanner_router)
router.include_router(opportunities_router)
router.include_router(trading_audit_router)

logger = logging.getLogger(__name__)

#: The single projection this endpoint serves. Also the frozen error-body identity.
PROJECTION = "SystemIncidentRead"


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Normalize a durable timestamp at the Product boundary.

    PostgreSQL returns the project's ``timezone=True`` columns as aware values.  SQLite used by
    focused tests does not retain that marker, so its otherwise-UTC fixture values are restored
    to the declared contract rather than producing a cursor that violates the UTC-aware API.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _source(*, source_type: str, source_identity: str, snapshot_at: datetime) -> SourceContextDTO:
    return SourceContextDTO(
        source_type=source_type,
        source_identity=source_identity,
        snapshot_at=snapshot_at,
    )


def _section(
    data: object,
    *,
    source_type: str,
    source_identity: str,
    snapshot_at: datetime,
    state: ProjectionState = ProjectionState.FRESH,
    read_failure_reason: ReadFailureReason | None = None,
) -> SystemSectionDTO[object]:
    """Build one section around the snapshot instant of *its own* source read.

    ``snapshot_at`` is required and never minted here: a section may not present a
    DTO-construction timestamp as if it were the instant its source data was acquired.
    """
    return SystemSectionDTO[object](
        state=state,
        snapshot_at=snapshot_at,
        source=_source(
            source_type=source_type, source_identity=source_identity, snapshot_at=snapshot_at
        ),
        read_failure_reason=read_failure_reason,
        data=data,
    )


def _host_absent(settings: Settings) -> SystemIncidentReadResponse:
    now = _now()
    return SystemIncidentReadResponse(
        meta=ProjectionMetaDTO(
            projection=PROJECTION,
            read_surface_class=ReadSurfaceClass.A,
            operational_availability=OperationalAvailability.NOT_ACTIVATED,
            projection_state=ProjectionState.UNAVAILABLE,
            snapshot_at=now,
            is_partial=False,
        ),
        operational_context=OperationalContextDTO(
            run_mode=settings.run_mode,
            runtime_instance_id=None,
            host_state=None,
            operational_provenance=settings.run_mode,
            context_snapshot_at=now,
        ),
        data=None,
    )


@dataclass(frozen=True)
class _IncidentRead:
    """One incident-source read: its page (or source failure) and its acquisition instant."""

    page: IncidentPageDTO | None
    next_cursor: str | None
    snapshot_at: datetime


async def _incident_page(
    context: ProductReadContext,
    *,
    incident_status: IncidentStatus | None,
    incident_type: IncidentType | None,
    limit: int,
    cursor: str | None,
) -> _IncidentRead:
    """Read the current run-mode incident page; ``None`` page represents a source failure."""
    assert context.host is not None
    fingerprint = incident_filter_fingerprint(
        incident_status=None if incident_status is None else incident_status.value,
        incident_type=None if incident_type is None else incident_type.value,
    )
    after: IncidentCursor | None = None
    if cursor is not None:
        try:
            after = decode_incident_cursor(cursor, filter_fingerprint=fingerprint)
        except ProductCursorError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="invalid product incident cursor",
            ) from exc
    sessions = context.sessions
    # The DB source owns its own snapshot instant: the moment this query read began. It is not
    # the Host snapshot and is not derived from when the DTO happens to be constructed.
    query_snapshot_at = _now()
    if sessions is None:
        return _IncidentRead(page=None, next_cursor=None, snapshot_at=query_snapshot_at)
    statement = select(IncidentRecord).where(IncidentRecord.run_mode == context.host.run_mode.value)
    if incident_status is not None:
        statement = statement.where(IncidentRecord.status == incident_status.value)
    if incident_type is not None:
        statement = statement.where(IncidentRecord.incident_type == incident_type.value)
    if after is not None:
        statement = statement.where(
            or_(
                IncidentRecord.opened_at < after.opened_at,
                and_(
                    IncidentRecord.opened_at == after.opened_at,
                    IncidentRecord.incident_id < after.incident_id,
                ),
            )
        )
    statement = statement.order_by(
        desc(IncidentRecord.opened_at), desc(IncidentRecord.incident_id)
    ).limit(limit + 1)
    try:
        async with sessions() as session:
            records = list((await session.scalars(statement)).all())
    except Exception:  # noqa: BLE001 - section failure is deliberately non-disclosing
        return _IncidentRead(page=None, next_cursor=None, snapshot_at=query_snapshot_at)
    page_records, extra = records[:limit], records[limit:]
    next_cursor = None
    if extra and page_records:
        last = page_records[-1]
        next_cursor = encode_incident_cursor(
            IncidentCursor(opened_at=_as_utc(last.opened_at), incident_id=last.incident_id),
            filter_fingerprint=fingerprint,
        )
    return _IncidentRead(
        page=IncidentPageDTO(
            items=[
                IncidentDTO(
                    incident_id=record.incident_id,
                    incident_type=record.incident_type,
                    run_mode=record.run_mode,
                    instrument_id=record.instrument_id,
                    status=record.status,
                    reason=record.reason,
                    opened_at=_as_utc(record.opened_at),
                    resolved_at=(
                        None if record.resolved_at is None else _as_utc(record.resolved_at)
                    ),
                )
                for record in page_records
            ],
            next_cursor=next_cursor,
        ),
        next_cursor=next_cursor,
        snapshot_at=query_snapshot_at,
    )


def _product_unavailable_response(
    *, reason: ReadFailureReason, correlation_id: str
) -> JSONResponse:
    """The formal ``503`` body requires an authoritative failure classification."""
    body = ProductUnavailableResponse(
        projection=PROJECTION,
        contract_version=PRODUCT_READ_CONTRACT_VERSION,
        read_surface_class=ReadSurfaceClass.A,
        read_failure_reason=reason,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump(mode="json")
    )


def _product_internal_error_response(*, correlation_id: str) -> JSONResponse:
    """The frozen ``500`` body must contain only the correlation id."""
    body = ProductInternalErrorResponse(correlation_id=correlation_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump(mode="json")
    )


def _product_snapshot_failure(*, exc: BaseException | None) -> JSONResponse:
    """Endpoint-wide ``503 SNAPSHOT_FAILED``: the required Product snapshot was not obtained."""
    correlation_id = new_id().hex
    logger.error(
        "product_read_snapshot_failed projection=%s correlation_id=%s",
        PROJECTION,
        correlation_id,
        exc_info=exc,
    )
    return _product_unavailable_response(
        reason=ReadFailureReason.SNAPSHOT_FAILED, correlation_id=correlation_id
    )


@router.get(
    "/system",
    response_model=SystemIncidentReadResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ProductUnavailableResponse,
            "description": (
                "Endpoint-wide Product read failure. `read_failure_reason` keeps the frozen "
                "distinction between SOURCE_UNAVAILABLE and SNAPSHOT_FAILED."
            ),
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ProductInternalErrorResponse,
            "description": (
                "Unclassified internal failure. Carries a sanitized correlation id only: no "
                "traceback, exception message, SQL, DSN or provider/secret detail."
            ),
        },
    },
)
async def system_incident_read(
    request: Request,
    incident_status: IncidentStatus | None = Query(default=None),  # noqa: B008
    incident_type: IncidentType | None = Query(default=None),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> SystemIncidentReadResponse | JSONResponse:
    """Read the typed System/Incident Product projection without owning any runtime resource.

    This is the endpoint's single internal error boundary. Failure to acquire the required
    Host Product snapshot is an *endpoint-wide* failure and keeps its frozen ``503
    SNAPSHOT_FAILED`` classification; anything still unclassified leaves as a sanitized
    ``500`` correlation id. A section-local source failure never reaches this boundary — it
    stays inside the ``200`` projection as ``is_partial``.
    """
    try:
        return await _read_system_projection(
            request,
            incident_status=incident_status,
            incident_type=incident_type,
            limit=limit,
            cursor=cursor,
            settings=settings,
        )
    except HTTPException:
        raise
    except Exception:  # unclassified failures must not disclose internals
        correlation_id = new_id().hex
        logger.exception(
            "product_read_internal_error projection=%s correlation_id=%s",
            PROJECTION,
            correlation_id,
        )
        return _product_internal_error_response(correlation_id=correlation_id)


async def _read_system_projection(
    request: Request,
    *,
    incident_status: IncidentStatus | None,
    incident_type: IncidentType | None,
    limit: int,
    cursor: str | None,
    settings: Settings,
) -> SystemIncidentReadResponse | JSONResponse:
    context = ProductReadContext.from_request(request)
    if context.host is None:
        return _host_absent(settings)
    try:
        snapshot = context.runtime_snapshot()
    except Exception as exc:  # noqa: BLE001 - acquisition failure is endpoint-wide
        return _product_snapshot_failure(exc=exc)
    if snapshot is None:
        return _product_snapshot_failure(exc=None)

    readiness = snapshot.readiness
    ready_data = ReadyDTO(
        ready=readiness.ready,
        status=readiness.status.value,
        reasons=list(readiness.reasons),
        evaluated_at=readiness.evaluated_at,
    )
    overall_health = (
        "ok"
        if readiness.ready
        else ("DEGRADED" if readiness.status is HostReadinessStatus.DEGRADED else "FAIL_CLOSED")
    )
    incident_read = await _incident_page(
        context,
        incident_status=incident_status,
        incident_type=incident_type,
        limit=limit,
        cursor=cursor,
    )
    incident_page = incident_read.page
    next_cursor = incident_read.next_cursor
    host_source = ("RUNTIME_HOST", snapshot.instance_id)
    database_source = ("POSTGRESQL", snapshot.database_application_name)
    recovery_data = snapshot.recovery
    recovery_section: SystemSectionDTO[RecoveryDTO]
    if recovery_data is None:
        recovery_section = _section(
            None,
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
            state=ProjectionState.UNAVAILABLE,
            read_failure_reason=ReadFailureReason.SNAPSHOT_FAILED,
        )
    else:
        recovery_section = _section(
            RecoveryDTO(
                status=recovery_data.status,
                ok=recovery_data.ok,
                started_at=recovery_data.started_at,
                finished_at=recovery_data.finished_at,
                ready_at=recovery_data.ready_at,
                reason=recovery_data.reason,
                final_system_state=recovery_data.final_system_state.value,
                operator_state=recovery_data.operator_state.value,
                reconciliation_ok=recovery_data.reconciliation_ok,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        )
    if incident_page is None:
        incidents_section = _section(
            None,
            source_type=database_source[0],
            source_identity=database_source[1],
            snapshot_at=incident_read.snapshot_at,
            state=ProjectionState.UNAVAILABLE,
            read_failure_reason=ReadFailureReason.SOURCE_UNAVAILABLE,
        )
    else:
        incidents_section = _section(
            incident_page,
            source_type=database_source[0],
            source_identity=database_source[1],
            snapshot_at=incident_read.snapshot_at,
            state=ProjectionState.EMPTY if not incident_page.items else ProjectionState.FRESH,
        )
    data = SystemIncidentDataDTO(
        live=_section(
            LiveDTO(
                alive=True,
                run_mode=snapshot.run_mode,
                local_only=snapshot.local_only,
                instance_id=snapshot.instance_id,
                host_state=snapshot.lifecycle_state,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        ready=_section(
            ready_data,
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        health=_section(
            HealthDTO(
                overall_status=overall_health,
                checks=[
                    HealthCheckDTO(
                        name=check.name,
                        status=check.status,
                        updated_at=check.updated_at,
                        reason=check.reason,
                    )
                    for check in snapshot.health_checks
                ],
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        runtime=_section(
            RuntimeDTO(
                lifecycle_state=snapshot.lifecycle_state,
                uptime_seconds=snapshot.uptime_seconds,
                instruments=list(snapshot.instruments),
                active_risk_instruments=list(snapshot.active_risk_instruments),
                children_live=list(snapshot.children_live),
                gates=RuntimeGatesDTO(
                    risk_admission=snapshot.risk_admission,
                    ingress=snapshot.ingress,
                    safety=snapshot.safety,
                    scanner=snapshot.scanner,
                ),
                timestamps=RuntimeTimestampsDTO(
                    created_at=snapshot.created_at,
                    started_at=snapshot.started_at,
                    recovery_ready_at=snapshot.recovery_ready_at,
                    last_heartbeat_at=snapshot.last_heartbeat_at,
                    last_reconciliation_at=snapshot.last_reconciliation_at,
                ),
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        market_provider=_section(
            MarketProviderDTO(
                provider=ProviderDTO(
                    status=snapshot.provider_status,
                    connection_attempts=snapshot.provider_connection_attempts,
                    reconnects=snapshot.provider_reconnects,
                    constructed_by_host=snapshot.provider_constructed_by_host,
                    subscriptions=[
                        ProviderSubscriptionDTO(channel=channel, instrument_id=instrument_id)
                        for channel, instrument_id in snapshot.subscriptions
                    ],
                ),
                market=[
                    MarketInstrumentDTO(
                        instrument_id=item.instrument_id,
                        present=item.present,
                        fresh=item.fresh,
                        quality=item.quality,
                    )
                    for item in snapshot.market
                ],
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        lanes=_section(
            LanesDTO(
                scanner_lane=LaneTelemetryDTO(**snapshot.scanner_lane.__dict__),
                safety_lanes=[LaneTelemetryDTO(**lane.__dict__) for lane in snapshot.safety_lanes],
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        database_singleton=_section(
            DatabaseSingletonDTO(
                application_name=snapshot.database_application_name,
                engine_disposed=snapshot.database_engine_disposed,
                owns_engine=snapshot.database_owns_engine,
                singleton_lock_held=snapshot.singleton_lock_held,
                singleton_connection_present=snapshot.singleton_connection_present,
                singleton_lock_lost=snapshot.singleton_lock_lost,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        recovery=recovery_section,
        reconciliation=_section(
            ReconciliationDTO(
                startup_ok=snapshot.reconciliation_startup_ok,
                last_ok=snapshot.reconciliation_last_ok,
                last_result=snapshot.reconciliation_last_result,
                diagnostics=list(snapshot.reconciliation_diagnostics),
                safe_mode_latched_by_host=snapshot.safe_mode_latched_by_host,
                snapshot_at=snapshot.snapshot_at,
                last_reconciliation_at=snapshot.last_reconciliation_at,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        operator_system_state=_section(
            OperatorSystemStateDTO(
                operator_state=(
                    None if snapshot.operator_state is None else snapshot.operator_state.value
                ),
                system_state=None if snapshot.system_state is None else snapshot.system_state.value,
                blocking_incident_count=snapshot.blocking_incident_count,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
        incidents=incidents_section,
        ai_activation=_section(
            AIActivationDTO(note="ai_reevaluation_disabled_in_host_core_v1"),
            source_type=host_source[0],
            source_identity=host_source[1],
            snapshot_at=snapshot.snapshot_at,
        ),
    )
    partial = recovery_data is None or incident_page is None
    # The projection's own instant is the Host snapshot it was projected from. It is never
    # re-minted here: that would present a DTO-construction time as a source snapshot time.
    return SystemIncidentReadResponse(
        meta=ProjectionMetaDTO(
            projection=PROJECTION,
            read_surface_class=ReadSurfaceClass.A,
            operational_availability=OperationalAvailability.ACTIVE,
            projection_state=ProjectionState.FRESH,
            snapshot_at=snapshot.snapshot_at,
            observed_at=snapshot.snapshot_at,
            is_partial=partial,
            next_cursor=next_cursor,
        ),
        operational_context=OperationalContextDTO(
            run_mode=snapshot.run_mode,
            runtime_instance_id=snapshot.instance_id,
            host_state=snapshot.lifecycle_state,
            operational_provenance=snapshot.run_mode,
            context_snapshot_at=snapshot.snapshot_at,
        ),
        data=data,
    )
