from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Self, cast

import marketpulse.api.app as app_module
import pytest
import sqlalchemy.ext.asyncio as sqlalchemy_asyncio
from fastapi.testclient import TestClient
from marketpulse.api.product.context import ProductReadContext
from marketpulse.api.product.models import TraceNodeDTO, TraceNodeState
from marketpulse.config import Settings
from marketpulse.db.models import IncidentRecord
from marketpulse.g3.models import RunMode
from marketpulse.g4.models import (
    IncidentStatus,
    IncidentType,
    OperatorState,
    ReconciliationReport,
    RecoveryReport,
    SystemState,
)
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import HostInvariantError, RecoverySnapshot, RuntimeHost
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

#: Every Product System section whose facts come from the one Host-memory snapshot. The
#: Incident DB page is deliberately excluded: it owns its own query-acquisition instant.
HOST_DERIVED_SECTIONS = (
    "live",
    "ready",
    "health",
    "runtime",
    "market_provider",
    "lanes",
    "database_singleton",
    "recovery",
    "reconciliation",
    "operator_system_state",
    "ai_activation",
)

#: An incident type that no seeded ``TEST`` incident uses, so a valid filter can prove EMPTY.
UNSEEDED_INCIDENT_TYPE = IncidentType.EXECUTION_GAP.value

INJECTED_SECRET = "postgresql://product:injected-secret@10.0.0.9/marketpulse"


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "run_mode": "TEST",
        "runtime_host_enabled": True,
        "runtime_host_instruments": "BTC-USDT,ETH-USDT",
    }
    values.update(overrides)
    return Settings(**values)


def _headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "dev-only-change-this-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _instant(value: str) -> datetime:
    """Parse an RFC 3339 Product timestamp back into an aware UTC instant."""
    return datetime.fromisoformat(value)


async def _make_sessions() -> tuple[async_sessionmaker[AsyncSession], Any]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(IncidentRecord.__table__.create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _seed_incidents(sessions: async_sessionmaker[AsyncSession]) -> None:
    opened = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    rows = [
        IncidentRecord(
            incident_id=incident_id,
            incident_type=IncidentType.RECOVERY_FAILED.value,
            run_mode="TEST",
            instrument_id="BTC-USDT",
            status=IncidentStatus.OPEN.value,
            reason=f"reason-{incident_id}",
            payload={"must_not": "leak"},
            opened_at=opened,
            resolved_at=None,
        )
        for incident_id in ("incident-c", "incident-b", "incident-a")
    ]
    rows.append(
        IncidentRecord(
            incident_id="incident-other-mode",
            incident_type=IncidentType.RECOVERY_FAILED.value,
            run_mode="REPLAY",
            instrument_id=None,
            status=IncidentStatus.OPEN.value,
            reason="other-mode",
            payload={"must_not": "leak"},
            opened_at=opened + timedelta(seconds=1),
            resolved_at=None,
        )
    )
    async with sessions() as session, session.begin():
        session.add_all(rows)


def _active_host(sessions: async_sessionmaker[AsyncSession]) -> RuntimeHost:
    host = RuntimeHost(_settings(), instance_id="product-read-host")
    host._sessions = sessions  # test-only injection of the Host-owned factory
    host._state = HostLifecycleState.READY
    host._started_at = datetime(2026, 9, 18, 11, 0, tzinfo=UTC)
    host._started_monotonic = 1.0
    host._risk_admission_open = True
    host._ingress_open = True
    host._safety_admission_open = True
    host._scanner_admission_open = True
    host._recovery_ok = True
    host._startup_reconciliation_ok = True
    host._durable_system_state = SystemState.RUNNING
    host._durable_operator_state = OperatorState.NORMAL
    host._recovery_snapshot = RecoverySnapshot(
        status="COMPLETED",
        ok=True,
        started_at=datetime(2026, 9, 18, 11, 0, tzinfo=UTC),
        finished_at=datetime(2026, 9, 18, 11, 1, tzinfo=UTC),
        ready_at=datetime(2026, 9, 18, 11, 1, tzinfo=UTC),
        reason=None,
        final_system_state=SystemState.RUNNING,
        operator_state=OperatorState.NORMAL,
        reconciliation_ok=True,
    )
    return host


@pytest.fixture
def active_product_host(monkeypatch: pytest.MonkeyPatch):
    sessions, engine = asyncio.run(_make_sessions())
    asyncio.run(_seed_incidents(sessions))
    host = _active_host(sessions)
    monkeypatch.setattr(app_module.app.state, "host", host, raising=False)
    try:
        yield host
    finally:
        app_module.app.state.host = None
        asyncio.run(engine.dispose())


@dataclass
class _SecretBearingLane:
    """A lane whose read fails with a message that must never reach a response body."""

    def __getattribute__(self, name: str) -> object:
        raise RuntimeError(INJECTED_SECRET)


def _product_system(client: TestClient, headers: dict[str, str], query: str = "") -> Any:
    suffix = f"?{query}" if query else ""
    return client.get(f"/api/v1/product/system{suffix}", headers=headers)


def test_product_system_requires_session() -> None:
    client = TestClient(app_module.app)
    assert client.get("/api/v1/product/system").status_code == 401


def test_trace_node_state_contract_includes_not_yet_due_and_serializes() -> None:
    assert {state.value for state in TraceNodeState} == {
        "PRESENT",
        "NOT_OCCURRED",
        "NOT_REACHED",
        "NOT_YET_DUE",
        "NO_PROVABLE_RECORD",
        "CAPABILITY_NOT_INTEGRATED",
    }
    assert TraceNodeState.NOT_REACHED != TraceNodeState.NOT_YET_DUE

    node = TraceNodeDTO[dict[str, str]](
        state=TraceNodeState.NOT_YET_DUE,
        data={"reason": "future_due_at"},
    )
    assert node.model_dump_json() == (
        '{"state":"NOT_YET_DUE","data":{"reason":"future_due_at"},'
        '"evidence_basis":null}'
    )


def test_product_system_host_absent_is_not_activated_without_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    client = TestClient(app_module.app)
    response = client.get("/api/v1/product/system", headers=_headers(client))
    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "projection": "SystemIncidentRead",
        "contract_version": "ui-rd01-product-read-v1",
        "read_surface_class": "A",
        "operational_availability": "NOT_ACTIVATED",
        "projection_state": "UNAVAILABLE",
        "read_failure_reason": None,
        "snapshot_at": body["meta"]["snapshot_at"],
        "observed_at": None,
        "is_partial": False,
        "next_cursor": None,
    }
    assert body["data"] is None


def test_product_context_is_nullable_frozen_and_borrows_the_host_factory(
    active_product_host: RuntimeHost,
) -> None:
    context = ProductReadContext(
        host=active_product_host, sessions=active_product_host.product_read_session_factory
    )
    assert context.sessions is active_product_host.product_read_session_factory
    assert context.host is active_product_host
    # Nullable: a request without a Host is representable rather than an error.
    assert ProductReadContext(host=None, sessions=None).runtime_snapshot() is None
    # Non-owning and immutable: the facade cannot be re-pointed after construction.
    with pytest.raises(FrozenInstanceError):
        context.host = None  # type: ignore[misc]


def test_product_system_active_is_typed_sanitized_and_keyset_paginated(
    active_product_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    first = _product_system(client, headers, "limit=2")
    assert first.status_code == 200
    body = first.json()
    assert body["meta"]["operational_availability"] == "ACTIVE"
    assert body["meta"]["projection_state"] == "FRESH"
    assert body["meta"]["is_partial"] is False
    assert set(body["data"]) == {
        "live",
        "ready",
        "health",
        "runtime",
        "market_provider",
        "lanes",
        "database_singleton",
        "recovery",
        "reconciliation",
        "operator_system_state",
        "incidents",
        "ai_activation",
    }
    items = body["data"]["incidents"]["data"]["items"]
    assert [item["incident_id"] for item in items] == ["incident-c", "incident-b"]
    assert "payload" not in items[0]
    assert "database_url" not in str(body)
    cursor = body["meta"]["next_cursor"]
    assert cursor
    second = _product_system(client, headers, f"limit=2&cursor={cursor}")
    assert second.status_code == 200
    assert [
        item["incident_id"] for item in second.json()["data"]["incidents"]["data"]["items"]
    ] == ["incident-a"]


def test_product_system_valid_enum_filters_select_authoritative_rows(
    active_product_host: RuntimeHost,
) -> None:
    """AC-F01-03: the authoritative enum values are accepted and filter as documented."""
    client = TestClient(app_module.app)
    headers = _headers(client)

    open_filtered = _product_system(client, headers, f"incident_status={IncidentStatus.OPEN.value}")
    assert open_filtered.status_code == 200
    assert [
        item["incident_id"] for item in open_filtered.json()["data"]["incidents"]["data"]["items"]
    ] == ["incident-c", "incident-b", "incident-a"]

    resolved_filtered = _product_system(
        client, headers, f"incident_status={IncidentStatus.RESOLVED.value}"
    )
    assert resolved_filtered.status_code == 200
    assert resolved_filtered.json()["data"]["incidents"]["state"] == "EMPTY"
    assert resolved_filtered.json()["data"]["incidents"]["data"]["items"] == []

    type_filtered = _product_system(
        client, headers, f"incident_type={IncidentType.RECOVERY_FAILED.value}"
    )
    assert type_filtered.status_code == 200
    assert [
        item["incident_type"] for item in type_filtered.json()["data"]["incidents"]["data"]["items"]
    ] == [IncidentType.RECOVERY_FAILED.value] * 3

    unseeded = _product_system(client, headers, f"incident_type={UNSEEDED_INCIDENT_TYPE}")
    assert unseeded.status_code == 200
    assert unseeded.json()["data"]["incidents"]["state"] == "EMPTY"


@pytest.mark.parametrize(
    "query",
    [
        "incident_status=INVALID",
        "incident_type=INVALID",
        f"incident_status={IncidentStatus.OPEN.value.lower()}",
        f"incident_type={IncidentType.RECOVERY_FAILED.value.lower()}",
    ],
)
def test_product_system_invalid_enum_filters_are_422(
    active_product_host: RuntimeHost, query: str
) -> None:
    """AC-F01-01 / AC-F01-02: an invalid filter value is rejected before any read."""
    client = TestClient(app_module.app)
    response = _product_system(client, _headers(client), query)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_product_system_cursor_filter_mismatch_is_422(active_product_host: RuntimeHost) -> None:
    """AC-F01-17: keyset cursors stay bound to the filter set that produced them."""
    client = TestClient(app_module.app)
    headers = _headers(client)
    first = _product_system(client, headers, "limit=2")
    cursor = first.json()["meta"]["next_cursor"]
    assert cursor
    # A *valid* enum value that differs from the cursor's filter set is still a mismatch, so the
    # cursor cannot be replayed against a different query.
    mismatched = _product_system(
        client, headers, f"limit=2&incident_type={UNSEEDED_INCIDENT_TYPE}&cursor={cursor}"
    )
    assert mismatched.status_code == 422
    # The same cursor replayed against its own filter set still pages.
    replayed = _product_system(client, headers, f"limit=2&cursor={cursor}")
    assert replayed.status_code == 200
    assert [
        item["incident_id"] for item in replayed.json()["data"]["incidents"]["data"]["items"]
    ] == ["incident-a"]


def test_product_system_prevalidates_cursor_before_unavailable_incident_source(
    active_product_host: RuntimeHost,
) -> None:
    """Cursor validity is a request contract, not contingent on the borrowed DB source."""
    client = TestClient(app_module.app)
    headers = _headers(client)
    first = _product_system(client, headers, "limit=2")
    cursor = first.json()["meta"]["next_cursor"]
    assert cursor

    active_product_host._sessions = None
    malformed = _product_system(client, headers, "cursor=not-a-product-cursor")
    assert malformed.status_code == 422
    mismatched = _product_system(
        client, headers, f"incident_type={UNSEEDED_INCIDENT_TYPE}&cursor={cursor}"
    )
    assert mismatched.status_code == 422

    for query in ("", f"cursor={cursor}"):
        partial = _product_system(client, headers, query)
        assert partial.status_code == 200
        assert partial.json()["meta"]["is_partial"] is True
        assert partial.json()["data"]["incidents"]["read_failure_reason"] == "SOURCE_UNAVAILABLE"


def test_product_system_empty_incidents_and_section_local_database_failure(
    active_product_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    empty = _product_system(client, headers, f"incident_type={UNSEEDED_INCIDENT_TYPE}")
    assert empty.status_code == 200
    assert empty.json()["data"]["incidents"]["state"] == "EMPTY"
    assert empty.json()["data"]["incidents"]["data"] == {"items": [], "next_cursor": None}

    class BrokenSession:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def scalars(self, _statement: object) -> object:
            raise RuntimeError("database unavailable")

    class BrokenFactory:
        def __call__(self) -> BrokenSession:
            return BrokenSession()

    active_product_host._sessions = cast(async_sessionmaker[AsyncSession], BrokenFactory())
    partial = client.get("/api/v1/product/system", headers=headers)
    assert partial.status_code == 200
    assert partial.json()["meta"]["is_partial"] is True
    assert partial.json()["data"]["incidents"] == {
        "state": "UNAVAILABLE",
        "snapshot_at": partial.json()["data"]["incidents"]["snapshot_at"],
        "source": partial.json()["data"]["incidents"]["source"],
        "read_failure_reason": "SOURCE_UNAVAILABLE",
        "data": None,
    }
    # AC-F01-07: the section-local failure keeps every other section available.
    assert partial.json()["data"]["runtime"]["state"] == "FRESH"


def test_product_system_snapshot_acquisition_failure_is_formal_503_snapshot_failed(
    active_product_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """AC-F01-05: endpoint-wide snapshot failure keeps the frozen SNAPSHOT_FAILED contract."""
    client = TestClient(app_module.app)
    headers = _headers(client)

    def _explode() -> object:
        raise RuntimeError(INJECTED_SECRET)

    monkeypatch.setattr(active_product_host, "product_runtime_snapshot", _explode)
    with caplog.at_level("ERROR", logger="marketpulse.api.product.system"):
        failed = client.get("/api/v1/product/system", headers=headers)
    assert failed.status_code == 503
    body = failed.json()
    assert set(body) == {
        "projection",
        "contract_version",
        "read_surface_class",
        "read_failure_reason",
        "correlation_id",
    }
    assert body["read_failure_reason"] == "SNAPSHOT_FAILED"
    assert body["projection"] == "SystemIncidentRead"
    assert body["read_surface_class"] == "A"
    assert body["contract_version"] == "ui-rd01-product-read-v1"
    # AC-F01-13: the acquisition failure never leaks the underlying exception text.
    assert INJECTED_SECRET not in failed.text
    assert "RuntimeError" not in failed.text
    # The correlation id is what makes the failure diagnosable server-side.
    assert body["correlation_id"]
    assert body["correlation_id"] in caplog.text

    # A Host facade that answers "no snapshot" is the same endpoint-wide failure.
    monkeypatch.setattr(active_product_host, "product_runtime_snapshot", lambda: None)
    absent = client.get("/api/v1/product/system", headers=headers)
    assert absent.status_code == 503
    assert absent.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_product_system_host_sections_use_the_authoritative_snapshot_instant(
    active_product_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-F01-08 / AC-F01-09: one captured instant, never a per-section construction time."""
    frozen = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    captured = replace(active_product_host.product_runtime_snapshot(), snapshot_at=frozen)
    monkeypatch.setattr(active_product_host, "product_runtime_snapshot", lambda: captured)

    client = TestClient(app_module.app)
    body = _product_system(client, _headers(client)).json()

    for name in HOST_DERIVED_SECTIONS:
        section = body["data"][name]
        assert _instant(section["snapshot_at"]) == frozen, name
        # A section's own provenance must agree with the section it describes.
        assert _instant(section["source"]["snapshot_at"]) == frozen, name
    assert _instant(body["meta"]["snapshot_at"]) == frozen
    assert _instant(body["meta"]["observed_at"]) == frozen
    assert _instant(body["operational_context"]["context_snapshot_at"]) == frozen
    assert _instant(body["data"]["reconciliation"]["data"]["snapshot_at"]) == frozen
    # Exactly one instant is published for the whole Host snapshot: no fabricated per-section
    # timestamps (a DTO-construction `_now()` would make these differ).
    assert len({body["data"][name]["snapshot_at"] for name in HOST_DERIVED_SECTIONS}) == 1

    # The Incident DB page is not Host-derived: it owns the instant its query was read, which is
    # a real acquisition instant rather than a reuse of the Host snapshot instant.
    incidents = body["data"]["incidents"]
    query_instant = _instant(incidents["snapshot_at"])
    assert query_instant == _instant(incidents["source"]["snapshot_at"])
    assert query_instant > frozen
    assert abs((datetime.now(UTC) - query_instant).total_seconds()) < 300


def test_product_system_health_section_is_snapshot_consistent(
    active_product_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-F01-10 / AC-F01-11: checks and overall status share one readiness evaluation."""
    original = RuntimeHost.readiness
    calls: list[int] = []

    def _counting_readiness(self: RuntimeHost) -> Any:
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("health section used a second, later readiness evaluation")
        return original(self)

    monkeypatch.setattr(RuntimeHost, "readiness", _counting_readiness)

    client = TestClient(app_module.app)
    response = _product_system(client, _headers(client))
    assert response.status_code == 200
    assert len(calls) == 1

    body = response.json()
    ready_section = body["data"]["ready"]["data"]
    health_section = body["data"]["health"]["data"]
    expected_overall = (
        "ok"
        if ready_section["ready"]
        else ("DEGRADED" if ready_section["status"] == "DEGRADED" else "FAIL_CLOSED")
    )
    assert health_section["overall_status"] == expected_overall

    # Live != Ready != Health stay distinct Product concepts.
    assert set(body["data"]["live"]["data"]) == {
        "alive",
        "run_mode",
        "local_only",
        "instance_id",
        "host_state",
    }
    assert set(ready_section) == {"ready", "status", "reasons", "evaluated_at"}
    assert set(health_section) == {"overall_status", "checks"}
    assert "ready" not in health_section
    assert "overall_status" not in ready_section


def test_product_system_unclassified_failure_is_a_sanitized_500(
    active_product_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """AC-F01-12 / AC-F01-13: only a correlation id leaves the process."""
    broken = replace(active_product_host.product_runtime_snapshot(), scanner_lane=_SecretBearingLane())
    monkeypatch.setattr(active_product_host, "product_runtime_snapshot", lambda: broken)

    client = TestClient(app_module.app)
    with caplog.at_level("ERROR", logger="marketpulse.api.product.system"):
        response = _product_system(client, _headers(client))

    assert response.status_code == 500
    body = response.json()
    assert set(body) == {"correlation_id"}
    correlation_id = body["correlation_id"]
    assert correlation_id and correlation_id.isalnum() and len(correlation_id) >= 16
    assert correlation_id in caplog.text

    # No traceback, exception message, SQL, DSN, provider or secret detail escapes.
    for forbidden in (
        INJECTED_SECRET,
        "injected-secret",
        "postgresql",
        "Traceback",
        "RuntimeError",
        "_SecretBearingLane",
        "marketpulse",
    ):
        assert forbidden not in response.text


def test_product_system_never_creates_a_second_engine_authority(
    active_product_host: RuntimeHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-F01-15: the Product read borrows Host resources and opens no engine of its own."""
    client = TestClient(app_module.app)
    headers = _headers(client)

    def _forbidden_engine(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("product read must not create its own engine")

    monkeypatch.setattr(sqlalchemy_asyncio, "create_async_engine", _forbidden_engine)
    assert _product_system(client, headers).status_code == 200


def test_product_system_recovery_section_projects_the_immutable_process_snapshot(
    active_product_host: RuntimeHost,
) -> None:
    """AC-F01-16: recovery keeps its immutable, process-lifetime snapshot semantics."""
    published = active_product_host.recovery_snapshot
    assert published is not None
    client = TestClient(app_module.app)
    body = _product_system(client, _headers(client)).json()
    recovery = body["data"]["recovery"]["data"]
    assert recovery["status"] == published.status
    assert recovery["ok"] is published.ok
    assert _instant(recovery["ready_at"]) == published.ready_at
    assert recovery["final_system_state"] == published.final_system_state.value
    assert recovery["operator_state"] == published.operator_state.value
    # The projected facts are read from the published snapshot, never re-derived per request.
    assert active_product_host.recovery_snapshot is published


def _enum_values(schema: dict[str, Any], components: dict[str, Any]) -> set[str] | None:
    """Resolve a (possibly nullable/anyOf-wrapped) parameter schema down to its enum values."""
    if "$ref" in schema:
        return _enum_values(components[schema["$ref"].rsplit("/", 1)[-1]], components)
    if "enum" in schema:
        return set(schema["enum"])
    for branch in schema.get("anyOf", []):
        values = _enum_values(branch, components)
        if values:
            return values
    return None


def test_product_system_openapi_declares_enum_filters_and_formal_failures() -> None:
    """AC-F01-04 / AC-F01-06: the frozen contract is visible in OpenAPI."""
    document = app_module.app.openapi()
    operation = document["paths"]["/api/v1/product/system"]["get"]
    schemas = document["components"]["schemas"]

    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) >= {"incident_status", "incident_type"}
    for name, authority in (
        ("incident_status", IncidentStatus),
        ("incident_type", IncidentType),
    ):
        # The filter is a constrained enum reference, never an unconstrained arbitrary string.
        assert _enum_values(parameters[name]["schema"], schemas) == {
            member.value for member in authority
        }
    # Both authorities are single shared components, so the frontend gets one generated enum
    # rather than a duplicate per-parameter definition.
    assert set(schemas["IncidentStatus"]["enum"]) == {member.value for member in IncidentStatus}
    assert set(schemas["IncidentType"]["enum"]) == {member.value for member in IncidentType}

    responses = operation["responses"]
    assert "503" in responses
    assert "500" in responses
    unavailable_content = responses["503"]["content"]["application/json"]["schema"]
    assert unavailable_content["$ref"] == "#/components/schemas/ProductUnavailableResponse"
    unavailable = schemas["ProductUnavailableResponse"]
    assert set(unavailable["required"]) == {
        "projection",
        "contract_version",
        "read_surface_class",
        "read_failure_reason",
        "correlation_id",
    }
    assert unavailable["properties"]["read_failure_reason"] == {
        "$ref": "#/components/schemas/ReadFailureReason"
    }
    internal_content = responses["500"]["content"]["application/json"]["schema"]
    assert internal_content["$ref"] == "#/components/schemas/ProductInternalErrorResponse"
    assert schemas["ProductInternalErrorResponse"] == {
        "type": "object",
        "title": "ProductInternalErrorResponse",
        "description": "Frozen ``500`` body: no product or diagnostic detail leaves the process.",
        "properties": {"correlation_id": {"type": "string", "title": "Correlation Id"}},
        "required": ["correlation_id"],
    }
    assert set(schemas["ReadFailureReason"]["enum"]) == {
        "SOURCE_UNAVAILABLE",
        "SNAPSHOT_FAILED",
    }


def test_product_system_generated_types_keep_503_required_and_500_minimal() -> None:
    generated = (Path(__file__).parents[2] / "frontend" / "src" / "api" / "generated.ts").read_text(
        encoding="utf-8"
    )
    assert 'ProductUnavailableResponse: {' in generated
    assert 'read_failure_reason: components["schemas"]["ReadFailureReason"];' in generated
    assert 'ProductInternalErrorResponse: {' in generated
    assert '"application/json": components["schemas"]["ProductUnavailableResponse"];' in generated
    assert '"application/json": components["schemas"]["ProductInternalErrorResponse"];' in generated


def test_recovery_snapshot_is_published_after_report_and_is_immutable() -> None:
    host = RuntimeHost(_settings())

    class Recovery:
        async def recover(self, *_args: object, **_kwargs: object) -> RecoveryReport:
            assert host.recovery_snapshot is None
            return RecoveryReport(
                run_mode=RunMode.TEST,
                ok=True,
                started_at=datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
                finished_at=datetime(2026, 9, 18, 10, 1, tzinfo=UTC),
                final_system_state=SystemState.RUNNING,
                operator_state=OperatorState.NORMAL,
                reconciliation=ReconciliationReport(ok=True),
                reason=None,
                plan_revalidation=[{"raw": "must_not_escape"}],
            )

    class Incidents:
        async def blocking(self, _run_mode: RunMode) -> list[object]:
            return []

    class StateService:
        async def heartbeat(self, _run_mode: RunMode) -> None:
            return None

    host._recovery = cast(Any, Recovery())
    host._incidents = cast(Any, Incidents())
    host._state_service = cast(Any, StateService())
    asyncio.run(host._run_recovery())
    snapshot = host.recovery_snapshot
    assert snapshot is not None
    assert snapshot.status == "COMPLETED"
    assert snapshot.reconciliation_ok is True
    assert not hasattr(snapshot, "plan_revalidation")
    with pytest.raises(FrozenInstanceError):
        snapshot.reason = "mutate"  # type: ignore[misc]
    with pytest.raises(HostInvariantError, match="recovery_snapshot_already_published"):
        asyncio.run(host._run_recovery())
