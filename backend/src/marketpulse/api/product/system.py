"""Authenticated SystemIncidentRead Product projection."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, desc, or_, select

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings
from marketpulse.db.models import IncidentRecord
from marketpulse.runtime import HostReadinessStatus

from .context import ProductReadContext
from .cursor import (
    IncidentCursor,
    ProductCursorError,
    decode_incident_cursor,
    encode_incident_cursor,
    incident_filter_fingerprint,
)
from .models import (
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

router = APIRouter(prefix="/api/v1/product", tags=["product-read"])


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
    state: ProjectionState = ProjectionState.FRESH,
    read_failure_reason: ReadFailureReason | None = None,
) -> SystemSectionDTO[object]:
    snapshot_at = _now()
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
            projection="SystemIncidentRead",
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


async def _incident_page(
    context: ProductReadContext,
    *,
    incident_status: str | None,
    incident_type: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[IncidentPageDTO | None, str | None]:
    """Read the current run-mode incident page; ``None`` represents a source failure."""
    assert context.host is not None
    sessions = context.sessions
    if sessions is None:
        return None, None
    fingerprint = incident_filter_fingerprint(
        incident_status=incident_status, incident_type=incident_type
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
    statement = select(IncidentRecord).where(IncidentRecord.run_mode == context.host.run_mode.value)
    if incident_status is not None:
        statement = statement.where(IncidentRecord.status == incident_status)
    if incident_type is not None:
        statement = statement.where(IncidentRecord.incident_type == incident_type)
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
        return None, None
    page_records, extra = records[:limit], records[limit:]
    next_cursor = None
    if extra and page_records:
        last = page_records[-1]
        next_cursor = encode_incident_cursor(
            IncidentCursor(opened_at=_as_utc(last.opened_at), incident_id=last.incident_id),
            filter_fingerprint=fingerprint,
        )
    return (
        IncidentPageDTO(
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
        next_cursor,
    )


@router.get("/system", response_model=SystemIncidentReadResponse)
async def system_incident_read(
    request: Request,
    incident_status: str | None = Query(default=None),
    incident_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> SystemIncidentReadResponse:
    """Read the typed System/Incident Product projection without owning any runtime resource."""
    context = ProductReadContext.from_request(request)
    if context.host is None:
        return _host_absent(settings)
    try:
        snapshot = context.runtime_snapshot()
        if snapshot is None:  # pragma: no cover - defensive against an invalid Host facade
            raise RuntimeError("host did not provide product snapshot")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="product snapshot unavailable") from exc

    readiness = context.host.readiness()
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
    incident_page, next_cursor = await _incident_page(
        context,
        incident_status=incident_status,
        incident_type=incident_type,
        limit=limit,
        cursor=cursor,
    )
    host_source = ("RUNTIME_HOST", snapshot.instance_id)
    database_source = ("POSTGRESQL", snapshot.database_application_name)
    recovery_data = snapshot.recovery
    recovery_section: SystemSectionDTO[RecoveryDTO]
    if recovery_data is None:
        recovery_section = _section(
            None,
            source_type=host_source[0],
            source_identity=host_source[1],
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
        )
    if incident_page is None:
        incidents_section = _section(
            None,
            source_type=database_source[0],
            source_identity=database_source[1],
            state=ProjectionState.UNAVAILABLE,
            read_failure_reason=ReadFailureReason.SOURCE_UNAVAILABLE,
        )
    else:
        incidents_section = _section(
            incident_page,
            source_type=database_source[0],
            source_identity=database_source[1],
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
        ),
        ready=_section(ready_data, source_type=host_source[0], source_identity=host_source[1]),
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
        ),
        lanes=_section(
            LanesDTO(
                scanner_lane=LaneTelemetryDTO(**snapshot.scanner_lane.__dict__),
                safety_lanes=[LaneTelemetryDTO(**lane.__dict__) for lane in snapshot.safety_lanes],
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
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
        ),
        recovery=recovery_section,
        reconciliation=_section(
            ReconciliationDTO(
                startup_ok=snapshot.reconciliation_startup_ok,
                last_ok=snapshot.reconciliation_last_ok,
                last_result=snapshot.reconciliation_last_result,
                diagnostics=list(snapshot.reconciliation_diagnostics),
                safe_mode_latched_by_host=snapshot.safe_mode_latched_by_host,
                snapshot_at=_now(),
                last_reconciliation_at=snapshot.last_reconciliation_at,
            ),
            source_type=host_source[0],
            source_identity=host_source[1],
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
        ),
        incidents=incidents_section,
        ai_activation=_section(
            AIActivationDTO(note="ai_reevaluation_disabled_in_host_core_v1"),
            source_type=host_source[0],
            source_identity=host_source[1],
        ),
    )
    partial = recovery_data is None or incident_page is None
    meta_now = _now()
    return SystemIncidentReadResponse(
        meta=ProjectionMetaDTO(
            projection="SystemIncidentRead",
            read_surface_class=ReadSurfaceClass.A,
            operational_availability=OperationalAvailability.ACTIVE,
            projection_state=ProjectionState.FRESH,
            snapshot_at=meta_now,
            observed_at=meta_now,
            is_partial=partial,
            next_cursor=next_cursor,
        ),
        operational_context=OperationalContextDTO(
            run_mode=snapshot.run_mode,
            runtime_instance_id=snapshot.instance_id,
            host_state=snapshot.lifecycle_state,
            operational_provenance=snapshot.run_mode,
            context_snapshot_at=meta_now,
        ),
        data=data,
    )
