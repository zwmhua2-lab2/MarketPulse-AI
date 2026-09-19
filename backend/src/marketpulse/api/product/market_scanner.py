"""Authenticated MarketScannerRead Product projection.

The endpoint deliberately joins no runtime-memory facts to historical database rows.  Current
quotes and Scanner history are separate section snapshots with separate source metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, desc, func, or_, select, text

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings
from marketpulse.db.models import MarketEventRecord
from marketpulse.ids import new_id
from marketpulse.runtime_host import ProductCurrentMarketSnapshot

from .context import ProductReadContext
from .cursor import (
    MarketScannerCursor,
    ProductCursorError,
    decode_market_scanner_cursor,
    encode_market_scanner_cursor,
)
from .models import (
    PRODUCT_READ_CONTRACT_VERSION,
    CurrentMarketDataDTO,
    CurrentMarketQuoteDTO,
    MarketScannerDataDTO,
    MarketScannerReadResponse,
    OperationalAvailability,
    OperationalContextDTO,
    ProductInternalErrorResponse,
    ProductUnavailableResponse,
    ProjectionMetaDTO,
    ProjectionState,
    RangeContextDTO,
    ReadFailureReason,
    ReadSurfaceClass,
    ScannerEventDTO,
    ScannerEventPageDTO,
    SourceContextDTO,
    SystemSectionDTO,
)

# ``system.router`` already owns the Product prefix used by the application registration.
router = APIRouter(tags=["product-read"])
logger = logging.getLogger(__name__)

PROJECTION = "MarketScannerRead"
OPERATIONAL_PROVENANCE = "FORWARD_PAPER"


class ScannerRange(StrEnum):
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    CUSTOM = "custom"


_PRESET_DURATIONS: dict[ScannerRange, timedelta] = {
    ScannerRange.FIFTEEN_MINUTES: timedelta(minutes=15),
    ScannerRange.THIRTY_MINUTES: timedelta(minutes=30),
    ScannerRange.ONE_HOUR: timedelta(hours=1),
    ScannerRange.FOUR_HOURS: timedelta(hours=4),
    ScannerRange.SIX_HOURS: timedelta(hours=6),
    ScannerRange.TWENTY_FOUR_HOURS: timedelta(hours=24),
    ScannerRange.SEVEN_DAYS: timedelta(days=7),
    ScannerRange.THIRTY_DAYS: timedelta(days=30),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _source(*, source_type: str, source_identity: str, snapshot_at: datetime) -> SourceContextDTO:
    return SourceContextDTO(
        source_type=source_type,
        source_identity=source_identity,
        snapshot_at=snapshot_at,
    )


@dataclass(frozen=True)
class _ResolvedRange:
    requested_range: ScannerRange
    effective_start: datetime
    effective_end: datetime
    cursor: MarketScannerCursor | None


@dataclass(frozen=True)
class _ScannerRead:
    page: ScannerEventPageDTO | None
    snapshot_at: datetime


def _invalid_request(detail: str) -> HTTPException:
    """Match FastAPI's declared ``HTTPValidationError`` response schema."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=[{"loc": ["query"], "msg": detail, "type": "value_error"}],
    )


def _resolve_range(
    *,
    requested_range: ScannerRange,
    start: datetime | None,
    end: datetime | None,
    cursor_value: str | None,
) -> _ResolvedRange:
    """Validate the whole request before any Host or database availability branch."""
    if requested_range is ScannerRange.CUSTOM:
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

    decoded: MarketScannerCursor | None = None
    if cursor_value is not None:
        try:
            decoded = decode_market_scanner_cursor(cursor_value)
        except ProductCursorError as exc:
            raise _invalid_request("invalid market scanner cursor") from exc
        if decoded.requested_range != requested_range.value:
            raise _invalid_request("market scanner cursor range does not match request")
        if requested_range is ScannerRange.CUSTOM and (
            decoded.effective_start != effective_start or decoded.effective_end != effective_end
        ):
            raise _invalid_request("market scanner custom range does not match cursor")
        effective_start, effective_end = decoded.effective_start, decoded.effective_end
    return _ResolvedRange(
        requested_range=requested_range,
        effective_start=effective_start,
        effective_end=effective_end,
        cursor=decoded,
    )


def _range_context(value: _ResolvedRange) -> RangeContextDTO:
    return RangeContextDTO(
        requested_range=value.requested_range.value,
        effective_start=value.effective_start,
        effective_end=value.effective_end,
        time_authority_field="event_time",
    )


def _host_absent(*, settings: Settings, range_value: _ResolvedRange) -> MarketScannerReadResponse:
    now = _now()
    return MarketScannerReadResponse(
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
            operational_provenance=OPERATIONAL_PROVENANCE,
            context_snapshot_at=now,
        ),
        range_context=_range_context(range_value),
        data=None,
    )


def _market_section(snapshot: ProductCurrentMarketSnapshot) -> SystemSectionDTO[CurrentMarketDataDTO]:
    return SystemSectionDTO[CurrentMarketDataDTO](
        state=ProjectionState.FRESH,
        snapshot_at=snapshot.snapshot_at,
        source=_source(
            source_type="RUNTIME_HOST",
            source_identity=snapshot.instance_id,
            snapshot_at=snapshot.snapshot_at,
        ),
        data=CurrentMarketDataDTO(
            quotes=[
                CurrentMarketQuoteDTO(
                    instrument_id=quote.instrument_id,
                    bid=quote.bid,
                    ask=quote.ask,
                    received_at=quote.received_at,
                    tradable=quote.tradable,
                    data_quality=quote.data_quality,
                    age_seconds=quote.age_seconds,
                    snapshot_at=snapshot.snapshot_at,
                )
                for quote in snapshot.quotes
            ]
        ),
    )


async def _scanner_page(
    context: ProductReadContext, *, range_value: _ResolvedRange, limit: int
) -> _ScannerRead:
    """Read one immutable page from the Host-borrowed database factory.

    PostgreSQL's statement timestamp is selected in the same READ ONLY / REPEATABLE READ
    transaction as the page, and is the only successful-page ``as_of`` authority.
    """
    failure_observed_at = _now()
    sessions = context.sessions
    if sessions is None:
        return _ScannerRead(page=None, snapshot_at=failure_observed_at)
    statement = select(MarketEventRecord).where(
        MarketEventRecord.event_time >= range_value.effective_start,
        MarketEventRecord.event_time < range_value.effective_end,
    )
    if range_value.cursor is not None:
        after = range_value.cursor
        statement = statement.where(
            or_(
                MarketEventRecord.event_time < after.event_time,
                and_(
                    MarketEventRecord.event_time == after.event_time,
                    MarketEventRecord.event_id < after.event_id,
                ),
            )
        )
    statement = statement.order_by(
        desc(MarketEventRecord.event_time), desc(MarketEventRecord.event_id)
    ).limit(limit + 1)
    try:
        async with sessions() as session, session.begin():
            bind = session.get_bind()
            if bind.dialect.name == "postgresql":
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                )
                db_as_of = _as_utc(
                    await session.scalar(text("SELECT statement_timestamp()"))
                )
            else:
                # SQLite is a focused-test adapter only; production PostgreSQL uses the
                # accepted statement_timestamp() snapshot authority above.
                db_as_of = _as_utc(await session.scalar(select(func.current_timestamp())))
            records = list((await session.scalars(statement)).all())
    except Exception:  # noqa: BLE001 - the section failure is deliberately non-disclosing
        return _ScannerRead(page=None, snapshot_at=failure_observed_at)

    page_records, extra = records[:limit], records[limit:]
    next_cursor = None
    if extra and page_records:
        last = page_records[-1]
        next_cursor = encode_market_scanner_cursor(
            MarketScannerCursor(
                requested_range=range_value.requested_range.value,
                effective_start=range_value.effective_start,
                effective_end=range_value.effective_end,
                event_time=_as_utc(last.event_time),
                event_id=last.event_id,
            )
        )
    return _ScannerRead(
        page=ScannerEventPageDTO(
            items=[
                ScannerEventDTO(
                    event_id=record.event_id,
                    instrument_id=record.instrument_id,
                    symbol=record.symbol,
                    market_type=record.market_type,
                    event_type=record.event_type,
                    event_time=_as_utc(record.event_time),
                    received_time=_as_utc(record.received_time),
                    strength=record.strength,
                    priority=record.priority,
                    state_version=record.state_version,
                    config_version=record.config_version,
                    producer_source=record.source,
                )
                for record in page_records
            ],
            next_cursor=next_cursor,
            as_of=db_as_of,
        ),
        snapshot_at=db_as_of,
    )


def _unavailable_section(
    *, source_type: str, source_identity: str, snapshot_at: datetime, reason: ReadFailureReason
) -> SystemSectionDTO[object]:
    return SystemSectionDTO[object](
        state=ProjectionState.UNAVAILABLE,
        snapshot_at=snapshot_at,
        source=_source(
            source_type=source_type,
            source_identity=source_identity,
            snapshot_at=snapshot_at,
        ),
        read_failure_reason=reason,
        data=None,
    )


def _product_unavailable_response(
    *, reason: ReadFailureReason, correlation_id: str
) -> JSONResponse:
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
    body = ProductInternalErrorResponse(correlation_id=correlation_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump(mode="json")
    )


@router.get(
    "/market-scanner",
    response_model=MarketScannerReadResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ProductUnavailableResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ProductInternalErrorResponse},
    },
)
async def market_scanner_read(
    request: Request,
    range_value: ScannerRange = Query(default=ScannerRange.ONE_HOUR, alias="range"),  # noqa: B008
    start: datetime | None = Query(default=None),  # noqa: B008
    end: datetime | None = Query(default=None),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> MarketScannerReadResponse | JSONResponse:
    """Read the operational Market Scanner projection without activating any runtime resource."""
    try:
        range_context = _resolve_range(
            requested_range=range_value, start=start, end=end, cursor_value=cursor
        )
        context = ProductReadContext.from_request(request)
        if context.host is None:
            return _host_absent(settings=settings, range_value=range_context)

        host = context.host
        market_snapshot: ProductCurrentMarketSnapshot | None
        market_failure_observed_at: datetime | None = None
        try:
            market_snapshot = context.market_snapshot()
        except Exception:  # noqa: BLE001 - classification remains sanitized below
            market_snapshot = None
            market_failure_observed_at = _now()
        scanner_read = await _scanner_page(context, range_value=range_context, limit=limit)

        if market_snapshot is None and scanner_read.page is None:
            correlation_id = new_id().hex
            logger.error(
                "market_scanner_projection_unavailable correlation_id=%s", correlation_id
            )
            return _product_unavailable_response(
                reason=ReadFailureReason.SNAPSHOT_FAILED, correlation_id=correlation_id
            )

        host_source_identity = host.instance_id
        db_source_identity = host.database_application_name
        if market_snapshot is None:
            assert market_failure_observed_at is not None
            current_market = _unavailable_section(
                source_type="RUNTIME_HOST",
                source_identity=host_source_identity,
                snapshot_at=market_failure_observed_at,
                reason=ReadFailureReason.SNAPSHOT_FAILED,
            )
        else:
            current_market = _market_section(market_snapshot)
        if scanner_read.page is None:
            scanner_events = _unavailable_section(
                source_type="POSTGRESQL",
                source_identity=db_source_identity,
                snapshot_at=scanner_read.snapshot_at,
                reason=ReadFailureReason.SOURCE_UNAVAILABLE,
            )
        else:
            scanner_events = SystemSectionDTO[ScannerEventPageDTO](
                state=(
                    ProjectionState.EMPTY
                    if not scanner_read.page.items
                    else ProjectionState.FRESH
                ),
                snapshot_at=scanner_read.snapshot_at,
                source=_source(
                    source_type="POSTGRESQL",
                    source_identity=db_source_identity,
                    snapshot_at=scanner_read.snapshot_at,
                ),
                data=scanner_read.page,
            )
        # This is an API assembly observation, not a shared snapshot claim for the two sources.
        response_observed_at = _now()
        return MarketScannerReadResponse(
            meta=ProjectionMetaDTO(
                projection=PROJECTION,
                read_surface_class=ReadSurfaceClass.A,
                operational_availability=OperationalAvailability.ACTIVE,
                projection_state=ProjectionState.FRESH,
                snapshot_at=response_observed_at,
                observed_at=response_observed_at,
                is_partial=market_snapshot is None or scanner_read.page is None,
                next_cursor=None if scanner_read.page is None else scanner_read.page.next_cursor,
            ),
            operational_context=OperationalContextDTO(
                run_mode=host.run_mode.value,
                runtime_instance_id=host.instance_id,
                host_state=host.state,
                operational_provenance=OPERATIONAL_PROVENANCE,
                context_snapshot_at=response_observed_at,
            ),
            range_context=_range_context(range_context),
            data=MarketScannerDataDTO(
                current_market=current_market,
                scanner_events=scanner_events,
            ),
        )
    except HTTPException:
        raise
    except Exception:
        correlation_id = new_id().hex
        logger.exception("market_scanner_internal_error correlation_id=%s", correlation_id)
        return _product_internal_error_response(correlation_id=correlation_id)
