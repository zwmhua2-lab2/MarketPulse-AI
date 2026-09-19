from __future__ import annotations

import asyncio
import base64
import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import marketpulse.api.app as app_module
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from marketpulse.api.product.cursor import OpportunityCursor, encode_opportunity_cursor
from marketpulse.config import Settings
from marketpulse.db.models import (
    AIDecisionRecord,
    EdgeAttributionEventRecord,
    MarketEventRecord,
    StrategyCandidateRecord,
)
from marketpulse.edge.attribution import AttributionEventType
from marketpulse.edge.models import (
    AttributionSubjectType,
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_attribution_event,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.edge.repository import (
    append_attribution_event,
    append_evidence_revision,
    append_forward_outcome,
)
from marketpulse.market_data.models import MarketType
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import RuntimeHost
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)
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


async def _sessions(url: str) -> tuple[async_sessionmaker[AsyncSession], Any]:
    engine = create_async_engine(url, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False), engine


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
    name = f"marketpulse_i02b_{uuid4().hex[:12]}"
    asyncio.run(_admin_execute(f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    command.upgrade(_alembic_config(url), "head")
    try:
        yield url
    finally:
        asyncio.run(_admin_execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity " f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"))
        asyncio.run(_admin_execute(f'DROP DATABASE "{name}"'))


async def _seed(sessions: async_sessionmaker[AsyncSession]) -> dict[str, str]:
    identity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="edge-v1",
        instrument_id="BTC-USDT",
        market_type=MarketType.SPOT,
        candidate_id="candidate-a",
    )
    replay_identity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="edge-v1",
        instrument_id="ETH-USDT",
        market_type=MarketType.SPOT,
        candidate_id="candidate-replay",
    )
    rev1 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=1,
        detected_at=START,
        evidence_at=START,
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-run-a",
        source_manifest_id="manifest-a",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={"secret_evidence": "must-not-leak"},
        feature_snapshot_payload={"secret_feature": "must-not-leak"},
        created_at=START,
    )
    rev2 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=2,
        supersedes_evidence_id=rev1.evidence_id,
        detected_at=START + timedelta(minutes=30),
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-run-a",
        source_manifest_id="manifest-a",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={"secret_evidence": "must-not-leak-rev2"},
        feature_snapshot_payload={"secret_feature": "must-not-leak-rev2"},
        created_at=START + timedelta(seconds=1),
    )
    replay = build_evidence_revision(
        opportunity=replay_identity,
        evidence_revision=1,
        detected_at=START + timedelta(minutes=1),
        evidence_at=START + timedelta(minutes=1),
        expires_at=START + timedelta(minutes=11),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="replay-run-a",
        source_manifest_id="manifest-replay",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={"secret_replay": "must-not-leak"},
        feature_snapshot_payload={},
        created_at=START,
    )
    outcome = build_forward_outcome_contract(
        opportunity_id=identity.opportunity_id,
        evidence_id=rev2.evidence_id,
        horizon=ForwardHorizon.M5,
        outcome_revision=1,
        due_at=rev2.evidence_at + timedelta(minutes=5),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-run-a",
        cost_policy="none",
        cost_model_version="v1",
        calculator_version="v1",
        calculation_status=OutcomeCalculationStatus.INSUFFICIENT_DATA,
        created_at=START + timedelta(minutes=5),
    )
    attribution = build_attribution_event(
        subject_type=AttributionSubjectType.AI,
        subject_id="decision-a",
        event_type=AttributionEventType.AI_ACCEPTED_LONG.value,
        opportunity_id=identity.opportunity_id,
        evidence_id=rev1.evidence_id,
        payload={"raw_prompt": "must-not-leak"},
        occurred_at=START,
        recorded_at=START,
    )
    async with sessions() as session, session.begin():
        session.add(
            MarketEventRecord(
                event_id="event-a", symbol="BTC-USDT", instrument_id="BTC-USDT", market_type="SPOT",
                event_type="BREAKOUT", event_time=START, received_time=START, source="G2",
                strength=0.8, priority=7, state_version=3, config_version="g2-v1", payload={"no": "leak"},
            )
        )
        session.add(
            StrategyCandidateRecord(
                candidate_id="candidate-a", strategy_id="strategy-a", strategy_version="v1",
                applicable=True, strength=0.8, setup_type="SETUP", direction_bias="LONG_BIAS",
                entry_context={}, supporting_evidence=[], contradicting_evidence=[], invalidation_hint="x",
                expected_behavior="y", instrument_id="BTC-USDT", symbol="BTC-USDT", event_id="event-a",
                state_version=3, config_version="g2-v1", created_at=START,
            )
        )
        session.add(
            AIDecisionRecord(
                decision_id="decision-a", snapshot_id="snapshot-a", run_mode="TEST", state_version=3,
                config_version="g3-v1", prompt_version="p1", schema_version="s1", model="fake",
                status="VALID", raw_prompt="must-not-leak", raw_response={"must": "not-leak"},
                error="must-not-leak", created_at=START,
            )
        )
        await append_evidence_revision(session, rev1)
        await append_evidence_revision(session, rev2)
        await append_evidence_revision(session, replay)
        await append_forward_outcome(session, outcome)
        await append_attribution_event(session, attribution)
    return {"opportunity": identity.opportunity_id, "replay": replay_identity.opportunity_id}


def _host(sessions: async_sessionmaker[AsyncSession]) -> RuntimeHost:
    host = RuntimeHost(_settings(), instance_id="opportunity-host")
    host._sessions = sessions
    host._state = HostLifecycleState.READY
    host._started_at = START
    host._started_monotonic = time.monotonic()
    return host


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "dev-only-change-this-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _request(client: TestClient, headers: dict[str, str], suffix: str = "") -> Any:
    return client.get(f"/api/v1/product/opportunities{suffix}", headers=headers)


@pytest.fixture
def opportunity_host(monkeypatch: pytest.MonkeyPatch):
    with _postgres_database() as url:
        sessions, engine = asyncio.run(_sessions(url))
        ids = asyncio.run(_seed(sessions))
        host = _host(sessions)
        monkeypatch.setattr(app_module.app.state, "host", host, raising=False)
        try:
            yield host, ids
        finally:
            app_module.app.state.host = None
            asyncio.run(engine.dispose())


def test_opportunity_requires_auth_and_host_absent_validates_before_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app_module.app)
    assert _request(client, {}).status_code == 401
    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    headers = _headers(client)
    absent = _request(client, headers)
    assert absent.status_code == 200
    assert absent.json()["meta"]["operational_availability"] == "NOT_ACTIVATED"
    assert absent.json()["meta"]["projection_state"] == "UNAVAILABLE"
    assert _request(client, headers, "?cursor=malformed").status_code == 422


def test_collection_folds_canonical_range_cursor_and_provenance(opportunity_host: tuple[RuntimeHost, dict[str, str]]) -> None:
    _, ids = opportunity_host
    client = TestClient(app_module.app)
    headers = _headers(client)
    query = "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z&limit=1"
    response = _request(client, headers, query)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["projection_state"] == "FRESH"
    assert [item["opportunity_id"] for item in body["data"]["items"]] == [ids["opportunity"]]
    item = body["data"]["items"][0]
    assert item["current_canonical_evidence"]["evidence_revision"] == 2
    assert item["detected_at"] == START.isoformat().replace("+00:00", "Z")
    assert item["source_type"] == "FORWARD_PAPER"
    assert "must-not-leak" not in response.text
    cursor = body["data"]["next_cursor"]
    assert cursor is None
    replay = _request(client, headers, query + "&source_type=HISTORICAL_REPLAY")
    assert replay.status_code == 200
    assert [row["opportunity_id"] for row in replay.json()["data"]["items"]] == [ids["replay"]]
    assert _request(client, headers, "?range=1h&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z").status_code == 422


def test_collection_cursor_binds_range_provenance_and_sort_tuple(opportunity_host: tuple[RuntimeHost, dict[str, str]]) -> None:
    _, ids = opportunity_host
    client = TestClient(app_module.app)
    headers = _headers(client)
    cursor = encode_opportunity_cursor(
        OpportunityCursor("custom", START, END, "FORWARD_PAPER", START, ids["opportunity"])
    )
    start = START.isoformat().replace("+00:00", "Z")
    end = END.isoformat().replace("+00:00", "Z")
    assert _request(client, headers, f"?range=custom&start={start}&end={end}&cursor={cursor}").status_code == 200
    assert _request(client, headers, f"?range=custom&start={start}&end={end}&source_type=HISTORICAL_REPLAY&cursor={cursor}").status_code == 422
    payload = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    payload["detected_at"] = END.isoformat()
    invalid = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert _request(client, headers, f"?range=custom&start={start}&end={end}&cursor={invalid}").status_code == 422


def test_detail_preserves_current_and_historical_evidence_and_typed_trace(opportunity_host: tuple[RuntimeHost, dict[str, str]]) -> None:
    _, ids = opportunity_host
    client = TestClient(app_module.app)
    headers = _headers(client)
    response = _request(client, headers, f"/{ids['opportunity']}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["market_event"]["state"] == "PRESENT"
    assert body["strategy_candidate"]["state"] == "PRESENT"
    assert body["current_canonical_evidence"]["evidence_revision"] == 2
    decision = body["trading_decision"]
    assert decision["state"] == "PRESENT"
    assert decision["data"]["decisions"][0]["decision_bound_evidence"]["data"]["evidence_revision"] == 1
    assert body["forward_outcomes"]["5m"]["state"] == "PRESENT"
    assert body["forward_outcomes"]["30s"]["state"] == "CAPABILITY_NOT_INTEGRATED"
    assert "must-not-leak" not in response.text
    assert _request(client, headers, "/missing").status_code == 404
    assert _request(client, headers, f"/{ids['opportunity']}?source_type=HISTORICAL_REPLAY").status_code == 404


def test_detail_ai_not_reached_is_not_guessed(opportunity_host: tuple[RuntimeHost, dict[str, str]]) -> None:
    host, ids = opportunity_host
    async def replace() -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))
            event = build_attribution_event(
                subject_type=AttributionSubjectType.AI, subject_id=None,
                event_type=AttributionEventType.AI_NOT_REACHED.value, opportunity_id=ids["opportunity"],
                evidence_id=None, payload={}, occurred_at=START, recorded_at=START,
            )
            await append_attribution_event(session, event)
    asyncio.run(replace())
    client = TestClient(app_module.app)
    body = _request(client, _headers(client), f"/{ids['opportunity']}").json()["data"]
    assert body["trading_decision"]["state"] == "NOT_REACHED"
