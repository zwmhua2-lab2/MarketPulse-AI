from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any, Self, cast

import marketpulse.api.app as app_module
import pytest
from fastapi.testclient import TestClient
from marketpulse.api.product.context import ProductReadContext
from marketpulse.config import Settings
from marketpulse.db.models import IncidentRecord
from marketpulse.g3.models import RunMode
from marketpulse.g4.models import OperatorState, ReconciliationReport, RecoveryReport, SystemState
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import HostInvariantError, RecoverySnapshot, RuntimeHost
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


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
            incident_type="RECOVERY_FAILED",
            run_mode="TEST",
            instrument_id="BTC-USDT",
            status="OPEN",
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
            incident_type="RECOVERY_FAILED",
            run_mode="REPLAY",
            instrument_id=None,
            status="OPEN",
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


def test_product_system_requires_session() -> None:
    client = TestClient(app_module.app)
    assert client.get("/api/v1/product/system").status_code == 401


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


def test_product_context_borrows_exact_host_session_factory(
    active_product_host: RuntimeHost,
) -> None:
    context = ProductReadContext(
        host=active_product_host, sessions=active_product_host.product_read_session_factory
    )
    assert context.sessions is active_product_host.product_read_session_factory
    assert context.host is active_product_host


def test_product_system_active_is_typed_sanitized_and_keyset_paginated(
    active_product_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    first = client.get("/api/v1/product/system?limit=2", headers=headers)
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
    second = client.get(f"/api/v1/product/system?limit=2&cursor={cursor}", headers=headers)
    assert second.status_code == 200
    assert [
        item["incident_id"] for item in second.json()["data"]["incidents"]["data"]["items"]
    ] == ["incident-a"]
    mismatched = client.get(
        f"/api/v1/product/system?limit=2&incident_type=OTHER&cursor={cursor}", headers=headers
    )
    assert mismatched.status_code == 422


def test_product_system_empty_incidents_and_section_local_database_failure(
    active_product_host: RuntimeHost,
) -> None:
    client = TestClient(app_module.app)
    headers = _headers(client)
    empty = client.get("/api/v1/product/system?incident_type=NO_MATCH", headers=headers)
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
