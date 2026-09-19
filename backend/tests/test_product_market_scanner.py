from __future__ import annotations

import asyncio
import base64
import json
import time
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import marketpulse.api.app as app_module
import marketpulse.runtime_host as runtime_host_module
import pytest
import sqlalchemy.ext.asyncio as sqlalchemy_asyncio
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from marketpulse.api.product.cursor import MarketScannerCursor, encode_market_scanner_cursor
from marketpulse.config import Settings
from marketpulse.db.models import MarketEventRecord
from marketpulse.g3.models import BestBidAsk
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import RuntimeHost
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

START = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)
INJECTED_SECRET = "postgresql://market-scanner:injected-secret@10.0.0.9/marketpulse"
PRIMARY_URL = Settings().database_url
BACKEND = Path(__file__).resolve().parents[1]


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "run_mode": "TEST",
        "runtime_host_enabled": True,
        "runtime_host_instruments": "BTC-USDT,ETH-USDT",
    }
    values.update(overrides)
    return Settings(**values)


async def _sessions() -> tuple[async_sessionmaker[AsyncSession], Any]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(MarketEventRecord.__table__.create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed(sessions: async_sessionmaker[AsyncSession]) -> None:
    rows = [
        MarketEventRecord(
            event_id=event_id,
            symbol="BTC-USDT",
            instrument_id="BTC-USDT",
            market_type="SPOT",
            event_type="BREAKOUT",
            event_time=event_time,
            received_time=event_time + timedelta(seconds=11),
            source="G2_SCANNER",
            strength=0.8,
            priority=7,
            state_version=3,
            config_version="scanner-v1",
            payload={"must_not": "leak"},
        )
        for event_id, event_time in (
            ("event-a", START),
            ("event-c", START + timedelta(minutes=30)),
            ("event-b", START + timedelta(minutes=30)),
            ("event-right-exclusive", END),
            ("event-received-time-is-not-authority", START - timedelta(minutes=1)),
        )
    ]
    async with sessions() as session, session.begin():
        session.add_all(rows)


def _host(sessions: async_sessionmaker[AsyncSession]) -> RuntimeHost:
    host = RuntimeHost(_settings(), instance_id="market-scanner-host")
    host._sessions = sessions
    host._state = HostLifecycleState.READY
    host._started_at = START
    host._started_monotonic = time.monotonic()
    return host


def _url_for(database_name: str) -> str:
    return f"{PRIMARY_URL.rsplit('/', 1)[0]}/{database_name}"


async def _admin_execute(statement: str) -> None:
    engine = create_async_engine(PRIMARY_URL, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@contextmanager
def _postgres_database():
    name = f"marketpulse_i02a_{uuid4().hex[:12]}"
    asyncio.run(_admin_execute(f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    command.upgrade(_alembic_config(url), "head")
    try:
        yield url
    finally:
        asyncio.run(
            _admin_execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
            )
        )
        asyncio.run(_admin_execute(f'DROP DATABASE "{name}"'))


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "dev-only-change-this-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _request(client: TestClient, headers: dict[str, str], query: str = "") -> Any:
    return client.get(f"/api/v1/product/market-scanner{'?' if query else ''}{query}", headers=headers)


def _assert_validation_error(response: Any) -> None:
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    for error in detail:
        assert {"loc", "msg", "type"} <= set(error)
        assert isinstance(error["loc"], list)
        assert isinstance(error["msg"], str)
        assert isinstance(error["type"], str)


def _scanner_cursor(*, event_time: datetime = START) -> str:
    return encode_market_scanner_cursor(
        MarketScannerCursor(
            requested_range="custom",
            effective_start=START,
            effective_end=END,
            event_time=event_time,
            event_id="event-a",
        )
    )


def _alter_cursor(cursor: str, **updates: object) -> str:
    padded = cursor + "=" * (-len(cursor) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    payload.update(updates)
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


@pytest.fixture
def active_scanner_host(monkeypatch: pytest.MonkeyPatch):
    sessions, engine = asyncio.run(_sessions())
    asyncio.run(_seed(sessions))
    host = _host(sessions)
    monkeypatch.setattr(app_module.app.state, "host", host, raising=False)
    try:
        yield host
    finally:
        app_module.app.state.host = None
        asyncio.run(engine.dispose())


def test_market_scanner_requires_authenticated_session() -> None:
    assert TestClient(app_module.app).get("/api/v1/product/market-scanner").status_code == 401


def test_market_scanner_host_absent_preserves_not_activated_and_validates_cursor_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    client = TestClient(app_module.app)
    headers = _headers(client)
    absent = _request(client, headers)
    assert absent.status_code == 200
    body = absent.json()
    assert body["meta"]["operational_availability"] == "NOT_ACTIVATED"
    assert body["meta"]["projection_state"] == "UNAVAILABLE"
    assert body["meta"]["read_failure_reason"] is None
    assert body["data"] is None
    _assert_validation_error(_request(client, headers, "cursor=not-a-product-cursor"))


@pytest.mark.parametrize("value", ["15m", "30m", "1h", "4h", "6h", "24h", "7d", "30d"])
def test_market_scanner_all_presets_and_default_range_are_valid(
    active_scanner_host: RuntimeHost, value: str
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    response = _request(client, headers, f"range={value}")
    assert response.status_code == 200
    assert response.json()["range_context"]["requested_range"] == value
    default = _request(client, headers)
    assert default.status_code == 200
    assert default.json()["range_context"]["requested_range"] == "1h"


@pytest.mark.parametrize(
    "query",
    [
        "range=custom",
        "range=custom&start=2026-09-18T10:00:00",
        "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T10:00:00Z",
        "range=1h&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z",
        "range=invalid",
        "limit=0",
        "limit=501",
    ],
)
def test_market_scanner_rejects_invalid_range_and_limit(
    active_scanner_host: RuntimeHost, query: str
) -> None:
    client = TestClient(app_module.app)
    assert _request(client, _headers(client), query).status_code == 422


def test_market_scanner_typed_quote_is_immutable_and_uses_host_freshness_authority(
    active_scanner_host: RuntimeHost,
) -> None:
    host = active_scanner_host
    host.market_state.update(
        BestBidAsk(
            instrument_id="BTC-USDT",
            bid=100.0,
            ask=101.0,
            received_at=START,
        )
    )
    first_snapshot = host.product_market_snapshot()
    with pytest.raises(FrozenInstanceError):
        first_snapshot.quotes = ()  # type: ignore[misc]
    host.market_state.update(
        BestBidAsk(
            instrument_id="BTC-USDT",
            bid=102.0,
            ask=103.0,
            received_at=START,
        )
    )
    assert first_snapshot.quotes[0].bid == 100.0
    client = TestClient(app_module.app)
    fresh = _request(client, _headers(client))
    quotes = {row["instrument_id"]: row for row in fresh.json()["data"]["current_market"]["data"]["quotes"]}
    assert quotes["BTC-USDT"]["bid"] == 102.0
    assert quotes["BTC-USDT"]["data_quality"] == "FRESH"
    assert quotes["ETH-USDT"] == {
        "instrument_id": "ETH-USDT",
        "bid": None,
        "ask": None,
        "received_at": None,
        "tradable": False,
        "data_quality": "UNAVAILABLE",
        "age_seconds": None,
        "snapshot_at": quotes["ETH-USDT"]["snapshot_at"],
    }
    host.market_state.update(
        BestBidAsk(
            instrument_id="BTC-USDT",
            bid=102.0,
            ask=103.0,
            received_at=START,
        ),
        now_monotonic=time.monotonic() - 99,
    )
    stale = _request(client, _headers(client)).json()
    stale_quote = stale["data"]["current_market"]["data"]["quotes"][0]
    assert stale_quote["data_quality"] == "STALE"
    assert stale_quote["age_seconds"] >= 99


@pytest.mark.parametrize(
    ("age_seconds", "expected_quality"),
    [(4.999, "FRESH"), (5.0, "FRESH"), (5.001, "STALE")],
)
def test_market_scanner_quote_age_and_quality_share_one_monotonic_observation(
    active_scanner_host: RuntimeHost,
    monkeypatch: pytest.MonkeyPatch,
    age_seconds: float,
    expected_quality: str,
) -> None:
    host = active_scanner_host
    received_monotonic = 100.0
    host.market_state.update(
        BestBidAsk(
            instrument_id="BTC-USDT",
            bid=100.0,
            ask=101.0,
            received_at=START,
        ),
        now_monotonic=received_monotonic,
    )
    samples = iter([received_monotonic + age_seconds])
    with monkeypatch.context() as scoped:
        scoped.setattr(
            runtime_host_module,
            "time",
            SimpleNamespace(monotonic=lambda: next(samples)),
        )
        quote = next(
            item
            for item in host.product_market_snapshot().quotes
            if item.instrument_id == "BTC-USDT"
        )
        with pytest.raises(StopIteration):
            next(samples)

    assert quote.age_seconds == pytest.approx(age_seconds)
    assert quote.data_quality == expected_quality


def test_market_scanner_uses_event_time_orders_keysets_and_freezes_cursor_range(
    active_scanner_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    query = "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z&limit=1"
    first = _request(client, headers, query)
    assert first.status_code == 200
    body = first.json()
    page = body["data"]["scanner_events"]
    assert page["state"] == "FRESH"
    assert [row["event_id"] for row in page["data"]["items"]] == ["event-c"]
    assert "payload" not in page["data"]["items"][0]
    assert "runtime_instance_id" not in page["data"]["items"][0]
    assert page["data"]["items"][0]["producer_source"] == "G2_SCANNER"
    assert page["data"]["items"][0]["runtime_binding_status"] == "NOT_RECORDED"
    cursor = body["meta"]["next_cursor"]
    assert cursor
    second = _request(client, headers, f"{query}&cursor={cursor}")
    assert second.status_code == 200
    second_body = second.json()
    assert [row["event_id"] for row in second_body["data"]["scanner_events"]["data"]["items"]] == ["event-b"]
    assert second_body["range_context"] == body["range_context"]
    all_ids = ["event-c", "event-b"]
    next_cursor = second_body["meta"]["next_cursor"]
    while next_cursor:
        next_page = _request(client, headers, f"{query}&cursor={next_cursor}")
        assert next_page.status_code == 200
        next_body = next_page.json()
        all_ids.extend(row["event_id"] for row in next_body["data"]["scanner_events"]["data"]["items"])
        next_cursor = next_body["meta"]["next_cursor"]
    assert all_ids == ["event-c", "event-b", "event-a"]
    assert _request(client, headers, f"range=1h&cursor={cursor}").status_code == 422
    assert _request(
        client,
        headers,
        "range=custom&start=2026-09-18T10:01:00Z&end=2026-09-18T11:00:00Z&cursor=" + cursor,
    ).status_code == 422


def test_market_scanner_rejects_malformed_endpoint_provenance_and_sort_cursors(
    active_scanner_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    cursor = _scanner_cursor()
    for invalid in (
        "not-a-cursor",
        _alter_cursor(cursor, endpoint="system.incidents"),
        _alter_cursor(cursor, v="wrong"),
        _alter_cursor(cursor, provenance="HISTORICAL_REPLAY"),
        _alter_cursor(cursor, event_id=""),
    ):
        _assert_validation_error(_request(client, headers, f"range=1h&cursor={invalid}"))


def test_market_scanner_cursor_sort_tuple_must_stay_in_its_effective_range(
    active_scanner_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    query = "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z"

    assert _request(client, headers, f"{query}&cursor={_scanner_cursor()}").status_code == 200
    for event_time in (END, START - timedelta(microseconds=1), END + timedelta(microseconds=1)):
        _assert_validation_error(
            _request(client, headers, f"{query}&cursor={_scanner_cursor(event_time=event_time)}")
        )

    active_scanner_host._sessions = None
    _assert_validation_error(
        _request(client, headers, f"{query}&cursor={_scanner_cursor(event_time=END)}")
    )

    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    _assert_validation_error(
        _request(client, headers, f"{query}&cursor={_scanner_cursor(event_time=END)}")
    )


def test_market_scanner_empty_partial_endpoint_failure_and_sanitized_500(
    active_scanner_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    host = active_scanner_host
    original_market_snapshot = host.product_market_snapshot
    client = TestClient(app_module.app)
    headers = _headers(client)
    event_range = "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z"
    empty = _request(
        client,
        headers,
        "range=custom&start=2026-09-18T12:00:00Z&end=2026-09-18T13:00:00Z",
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["scanner_events"]["state"] == "EMPTY"

    def _explode() -> object:
        raise RuntimeError(INJECTED_SECRET)

    monkeypatch.setattr(host, "product_market_snapshot", _explode)
    market_partial = _request(client, headers, event_range)
    assert market_partial.status_code == 200
    assert market_partial.json()["meta"]["is_partial"] is True
    assert market_partial.json()["data"]["current_market"]["read_failure_reason"] == "SNAPSHOT_FAILED"
    assert market_partial.json()["data"]["scanner_events"]["state"] == "FRESH"
    monkeypatch.setattr(host, "product_market_snapshot", original_market_snapshot)

    host._sessions = None
    partial = _request(client, headers)
    assert partial.status_code == 200
    assert partial.json()["meta"]["is_partial"] is True
    assert partial.json()["data"]["scanner_events"]["read_failure_reason"] == "SOURCE_UNAVAILABLE"

    monkeypatch.setattr(host, "product_market_snapshot", _explode)
    unavailable = _request(client, headers)
    assert unavailable.status_code == 503
    assert unavailable.json()["read_failure_reason"] == "SNAPSHOT_FAILED"

    def _bad_section(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(INJECTED_SECRET)

    from marketpulse.api.product import market_scanner

    monkeypatch.setattr(host, "product_market_snapshot", original_market_snapshot)
    monkeypatch.setattr(market_scanner, "_market_section", _bad_section)
    with caplog.at_level("ERROR", logger="marketpulse.api.product.market_scanner"):
        internal = _request(client, headers)
    assert internal.status_code == 500
    assert set(internal.json()) == {"correlation_id"}
    assert INJECTED_SECRET not in internal.text


def test_market_scanner_market_failure_uses_its_own_observation_and_assembly_times(
    active_scanner_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    from marketpulse.api.product import market_scanner

    market_failure_at = datetime(2026, 9, 19, 4, 0, tzinfo=UTC)
    database_as_of = datetime(2026, 9, 19, 5, 0, tzinfo=UTC)
    response_observed_at = datetime(2026, 9, 19, 6, 0, tzinfo=UTC)

    def _explode() -> object:
        raise RuntimeError("market snapshot unavailable")

    async def _scanner_success(*_args: object, **_kwargs: object) -> object:
        page = market_scanner.ScannerEventPageDTO(
            items=[], next_cursor=None, as_of=database_as_of
        )
        return market_scanner._ScannerRead(page=page, snapshot_at=database_as_of)

    observations = iter([market_failure_at, response_observed_at])
    monkeypatch.setattr(active_scanner_host, "product_market_snapshot", _explode)
    monkeypatch.setattr(market_scanner, "_scanner_page", _scanner_success)
    monkeypatch.setattr(market_scanner, "_now", lambda: next(observations))

    client = TestClient(app_module.app)
    response = _request(
        client,
        _headers(client),
        "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z",
    )
    assert response.status_code == 200
    body = response.json()
    current_market = body["data"]["current_market"]
    scanner_events = body["data"]["scanner_events"]
    assert current_market["snapshot_at"] == market_failure_at.isoformat().replace("+00:00", "Z")
    assert current_market["source"]["snapshot_at"] == current_market["snapshot_at"]
    assert scanner_events["snapshot_at"] == database_as_of.isoformat().replace("+00:00", "Z")
    assert scanner_events["data"]["as_of"] == scanner_events["snapshot_at"]
    assert body["meta"]["snapshot_at"] == response_observed_at.isoformat().replace("+00:00", "Z")
    assert body["meta"]["observed_at"] == body["meta"]["snapshot_at"]
    assert body["operational_context"]["context_snapshot_at"] == body["meta"]["snapshot_at"]
    assert len(
        {
            current_market["snapshot_at"],
            scanner_events["snapshot_at"],
            body["meta"]["snapshot_at"],
        }
    ) == 3


def test_market_scanner_openapi_and_generated_contract_include_formal_failures() -> None:
    document = app_module.app.openapi()
    operation = document["paths"]["/api/v1/product/market-scanner"]["get"]
    assert {parameter["name"] for parameter in operation["parameters"]} >= {
        "range",
        "start",
        "end",
        "limit",
        "cursor",
    }
    assert {"503", "500"} <= set(operation["responses"])
    assert operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/HTTPValidationError"
    )
    assert operation["responses"]["503"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ProductUnavailableResponse"
    )
    assert operation["responses"]["500"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ProductInternalErrorResponse"
    )


@pytest.mark.parametrize(
    "query",
    [
        "cursor=not-a-product-cursor",
        "range=1h&cursor=" + _scanner_cursor(),
        "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z&cursor="
        + _alter_cursor(_scanner_cursor(), provenance="HISTORICAL_REPLAY"),
        "range=custom",
        "range=invalid",
        "range=custom&start=not-a-datetime&end=2026-09-18T11:00:00Z",
        "limit=0",
    ],
)
def test_market_scanner_manual_and_parameter_422s_share_openapi_validation_contract(
    active_scanner_host: RuntimeHost, query: str
) -> None:
    client = TestClient(app_module.app)
    _assert_validation_error(_request(client, _headers(client), query))


def test_market_scanner_postgresql_page_uses_database_as_of_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The durable page's ``as_of`` is read from PostgreSQL, never from Python DTO assembly."""
    with _postgres_database() as url:
        engine = create_async_engine(url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            asyncio.run(_seed(sessions))
            host = _host(sessions)
            monkeypatch.setattr(app_module.app.state, "host", host, raising=False)
            from marketpulse.api.product import market_scanner

            fabricated_python_now = datetime(2000, 1, 1, tzinfo=UTC)
            monkeypatch.setattr(market_scanner, "_now", lambda: fabricated_python_now)
            client = TestClient(app_module.app)
            response = _request(
                client,
                _headers(client),
                "range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z",
            )
            assert response.status_code == 200
            scanner = response.json()["data"]["scanner_events"]
            assert scanner["state"] == "FRESH"
            assert scanner["data"]["as_of"] == scanner["snapshot_at"]
            assert scanner["source"]["snapshot_at"] == scanner["snapshot_at"]
            assert datetime.fromisoformat(scanner["snapshot_at"]) != fabricated_python_now
        finally:
            app_module.app.state.host = None
            asyncio.run(engine.dispose())


def test_market_scanner_never_creates_a_second_engine(active_scanner_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_engine(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Product read must not create its own engine")

    monkeypatch.setattr(sqlalchemy_asyncio, "create_async_engine", _forbidden_engine)
    client = TestClient(app_module.app)
    assert _request(client, _headers(client)).status_code == 200
