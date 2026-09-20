from __future__ import annotations

import asyncio
import base64
import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import asyncpg
import marketpulse.api.app as app_module
import marketpulse.api.product.opportunities as opportunities_module
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from marketpulse.api.product.cursor import OpportunityCursor, encode_opportunity_cursor
from marketpulse.config import Settings
from marketpulse.db.models import (
    AIDecisionRecord,
    EdgeAttributionEventRecord,
    EdgeOpportunityEvidenceRecord,
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
from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
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
        asyncio.run(
            _admin_execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
            )
        )
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
                event_id="event-a",
                symbol="BTC-USDT",
                instrument_id="BTC-USDT",
                market_type="SPOT",
                event_type="BREAKOUT",
                event_time=START,
                received_time=START,
                source="G2",
                strength=0.8,
                priority=7,
                state_version=3,
                config_version="g2-v1",
                payload={"no": "leak"},
            )
        )
        session.add(
            StrategyCandidateRecord(
                candidate_id="candidate-a",
                strategy_id="strategy-a",
                strategy_version="v1",
                applicable=True,
                strength=0.8,
                setup_type="SETUP",
                direction_bias="LONG_BIAS",
                entry_context={},
                supporting_evidence=[],
                contradicting_evidence=[],
                invalidation_hint="x",
                expected_behavior="y",
                instrument_id="BTC-USDT",
                symbol="BTC-USDT",
                event_id="event-a",
                state_version=3,
                config_version="g2-v1",
                created_at=START,
            )
        )
        session.add(
            AIDecisionRecord(
                decision_id="decision-a",
                snapshot_id="snapshot-a",
                run_mode="TEST",
                state_version=3,
                config_version="g3-v1",
                prompt_version="p1",
                schema_version="s1",
                model="fake",
                status="VALID",
                raw_prompt="must-not-leak",
                raw_response={"must": "not-leak"},
                error="must-not-leak",
                created_at=START,
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
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "dev-only-change-this-password"},
    )
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


def test_opportunity_requires_auth_and_host_absent_validates_before_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app_module.app)
    assert _request(client, {}).status_code == 401
    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    headers = _headers(client)
    absent = _request(client, headers)
    assert absent.status_code == 200
    assert absent.json()["meta"]["operational_availability"] == "NOT_ACTIVATED"
    assert absent.json()["meta"]["projection_state"] == "UNAVAILABLE"
    assert _request(client, headers, "?cursor=malformed").status_code == 422


def test_collection_folds_canonical_range_cursor_and_provenance(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
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
    assert (
        _request(
            client, headers, "?range=1h&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z"
        ).status_code
        == 422
    )


def test_collection_cursor_binds_range_provenance_and_sort_tuple(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    _, ids = opportunity_host
    client = TestClient(app_module.app)
    headers = _headers(client)
    cursor = encode_opportunity_cursor(
        OpportunityCursor("custom", START, END, "FORWARD_PAPER", START, ids["opportunity"])
    )
    start = START.isoformat().replace("+00:00", "Z")
    end = END.isoformat().replace("+00:00", "Z")
    assert (
        _request(
            client, headers, f"?range=custom&start={start}&end={end}&cursor={cursor}"
        ).status_code
        == 200
    )
    assert (
        _request(
            client,
            headers,
            f"?range=custom&start={start}&end={end}&source_type=HISTORICAL_REPLAY&cursor={cursor}",
        ).status_code
        == 422
    )
    payload = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    payload["detected_at"] = END.isoformat()
    invalid = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert (
        _request(
            client, headers, f"?range=custom&start={start}&end={end}&cursor={invalid}"
        ).status_code
        == 422
    )


def test_detail_preserves_current_and_historical_evidence_and_typed_trace(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
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
    assert (
        decision["data"]["decisions"][0]["decision_bound_evidence"]["data"]["evidence_revision"]
        == 1
    )
    assert body["forward_outcomes"]["5m"]["state"] == "PRESENT"
    assert body["forward_outcomes"]["30s"]["state"] == "CAPABILITY_NOT_INTEGRATED"
    assert "must-not-leak" not in response.text
    assert _request(client, headers, "/missing").status_code == 404
    assert (
        _request(
            client, headers, f"/{ids['opportunity']}?source_type=HISTORICAL_REPLAY"
        ).status_code
        == 404
    )


def test_detail_ai_not_reached_is_not_guessed(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, ids = opportunity_host

    async def replace() -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))
            event = build_attribution_event(
                subject_type=AttributionSubjectType.AI,
                subject_id=None,
                event_type=AttributionEventType.AI_NOT_REACHED.value,
                opportunity_id=ids["opportunity"],
                evidence_id=None,
                payload={},
                occurred_at=START,
                recorded_at=START,
            )
            await append_attribution_event(session, event)

    asyncio.run(replace())
    client = TestClient(app_module.app)
    body = _request(client, _headers(client), f"/{ids['opportunity']}").json()["data"]
    assert body["trading_decision"]["state"] == "NOT_REACHED"


def test_cross_provenance_chain_folds_before_projection_and_keeps_historical_binding(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, _ = opportunity_host
    identity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="edge-v1",
        instrument_id="SOL-USDT",
        market_type=MarketType.SPOT,
        candidate_id="candidate-cross-provenance",
    )
    rev1 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=1,
        detected_at=START + timedelta(minutes=2),
        evidence_at=START,
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-cross",
        source_manifest_id="manifest-cross-forward",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START,
    )
    rev2 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=2,
        supersedes_evidence_id=rev1.evidence_id,
        detected_at=START + timedelta(minutes=3),
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="replay-cross",
        source_manifest_id="manifest-cross-replay",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START + timedelta(seconds=1),
    )
    attribution = build_attribution_event(
        subject_type=AttributionSubjectType.AI,
        subject_id="decision-cross",
        event_type=AttributionEventType.AI_ACCEPTED_LONG.value,
        opportunity_id=identity.opportunity_id,
        evidence_id=rev1.evidence_id,
        payload={},
        occurred_at=START,
        recorded_at=START,
    )

    async def append_cross_chain() -> None:
        async with host._sessions() as session, session.begin():
            session.add(
                AIDecisionRecord(
                    decision_id="decision-cross",
                    snapshot_id="snapshot-cross",
                    run_mode="TEST",
                    state_version=3,
                    config_version="g3-v1",
                    prompt_version="p1",
                    schema_version="s1",
                    model="fake",
                    status="VALID",
                    raw_prompt="",
                    raw_response={},
                    error=None,
                    created_at=START,
                )
            )
            await append_evidence_revision(session, rev1)
            await append_evidence_revision(session, rev2)
            await append_attribution_event(session, attribution)

    asyncio.run(append_cross_chain())
    client = TestClient(app_module.app)
    headers = _headers(client)
    query = "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z"
    forward = _request(client, headers, query)
    assert forward.status_code == 200
    assert identity.opportunity_id not in {
        item["opportunity_id"] for item in forward.json()["data"]["items"]
    }
    replay = _request(client, headers, query + "&source_type=HISTORICAL_REPLAY")
    assert replay.status_code == 200
    replay_item = next(
        item
        for item in replay.json()["data"]["items"]
        if item["opportunity_id"] == identity.opportunity_id
    )
    assert replay_item["current_canonical_evidence"]["evidence_revision"] == 2
    detail = _request(client, headers, f"/{identity.opportunity_id}?source_type=HISTORICAL_REPLAY")
    assert detail.status_code == 200
    trace = detail.json()["data"]
    assert trace["current_canonical_evidence"]["evidence_revision"] == 2
    assert (
        trace["trading_decision"]["data"]["decisions"][0]["decision_bound_evidence"]["data"][
            "evidence_revision"
        ]
        == 1
    )
    assert _request(client, headers, f"/{identity.opportunity_id}").status_code == 404


def test_cross_provenance_chain_corruption_is_not_hidden(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, _ = opportunity_host
    identity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="edge-v1",
        instrument_id="XRP-USDT",
        market_type=MarketType.SPOT,
        candidate_id="candidate-corrupt-cross-provenance",
    )
    rev1 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=1,
        detected_at=START,
        evidence_at=START,
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-corrupt",
        source_manifest_id="manifest-corrupt-forward",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START,
    )
    rev2 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=2,
        supersedes_evidence_id=rev1.evidence_id,
        detected_at=START,
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="replay-corrupt",
        source_manifest_id="manifest-corrupt-replay",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START + timedelta(seconds=1),
    )
    rev3 = build_evidence_revision(
        opportunity=identity,
        evidence_revision=3,
        supersedes_evidence_id=rev1.evidence_id,
        detected_at=START,
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="replay-corrupt",
        source_manifest_id="manifest-corrupt-replay",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START + timedelta(seconds=1),
    )

    async def append_corruption() -> None:
        async with host._sessions() as session, session.begin():
            await append_evidence_revision(session, rev1)
            await append_evidence_revision(session, rev2)
            persisted = await session.get(EdgeOpportunityEvidenceRecord, rev2.evidence_id)
            assert persisted is not None
            persisted.evidence_id = rev3.evidence_id
            persisted.evidence_revision = rev3.evidence_revision
            persisted.evidence_hash = rev3.evidence_hash

    asyncio.run(append_corruption())
    client = TestClient(app_module.app)
    response = _request(
        client,
        _headers(client),
        "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z",
    )
    assert response.status_code == 503
    assert response.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_collection_validation_is_query_scoped_and_pagination_is_provenance_complete(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, ids = opportunity_host

    def revision(
        *, candidate_id: str, instrument_id: str, detected_at: datetime, source_type: EvidenceSource
    ) -> tuple[object, object]:
        identity = build_opportunity_identity(
            family_id=EdgeFamily.BREAKOUT_RETEST,
            family_version="edge-v1",
            instrument_id=instrument_id,
            market_type=MarketType.SPOT,
            candidate_id=candidate_id,
        )
        return identity, build_evidence_revision(
            opportunity=identity,
            evidence_revision=1,
            detected_at=detected_at,
            evidence_at=detected_at,
            expires_at=detected_at + timedelta(minutes=10),
            source_type=source_type,
            source_identity=f"{source_type.value}-{candidate_id}",
            source_manifest_id=f"manifest-{candidate_id}",
            reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
            evidence_payload={},
            feature_snapshot_payload={},
            created_at=detected_at,
        )

    outside_identity, outside = revision(
        candidate_id="outside-corrupt",
        instrument_id="XRP-USDT",
        detected_at=START - timedelta(hours=2),
        source_type=EvidenceSource.FORWARD_PAPER,
    )
    replay_only_identity, replay_only = revision(
        candidate_id="replay-only-corrupt",
        instrument_id="SOL-USDT",
        detected_at=START + timedelta(minutes=25),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
    )
    _, replay_early = revision(
        candidate_id="replay-early",
        instrument_id="ADA-USDT",
        detected_at=START + timedelta(minutes=20),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
    )
    _, forward_later = revision(
        candidate_id="forward-later",
        instrument_id="DOGE-USDT",
        detected_at=START + timedelta(minutes=10),
        source_type=EvidenceSource.FORWARD_PAPER,
    )

    async def append_records() -> None:
        async with host._sessions() as session, session.begin():
            for record in (outside, replay_only, replay_early, forward_later):
                await append_evidence_revision(session, record)
            for identity, corrupt, revised_detected_at in (
                (outside_identity, outside, START + timedelta(minutes=10)),
                (replay_only_identity, replay_only, replay_only.detected_at),
            ):
                revision_two = build_evidence_revision(
                    opportunity=identity,
                    evidence_revision=2,
                    supersedes_evidence_id=corrupt.evidence_id,
                    detected_at=revised_detected_at,
                    evidence_at=corrupt.evidence_at + timedelta(seconds=1),
                    expires_at=corrupt.expires_at,
                    source_type=corrupt.source_type,
                    source_identity=corrupt.source_identity,
                    source_manifest_id=corrupt.source_manifest_id,
                    reference_data_status=corrupt.reference_data_status,
                    evidence_payload={},
                    feature_snapshot_payload={},
                    created_at=corrupt.created_at + timedelta(seconds=1),
                )
                await append_evidence_revision(session, revision_two)
                persisted = await session.get(
                    EdgeOpportunityEvidenceRecord, revision_two.evidence_id
                )
                assert persisted is not None
                persisted.evidence_revision = 3

    asyncio.run(append_records())
    client = TestClient(app_module.app)
    headers = _headers(client)
    query = "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z&limit=1"
    forward = _request(client, headers, query)
    assert forward.status_code == 200
    assert forward.json()["data"]["items"][0]["opportunity_id"] == forward_later.opportunity_id

    cursor_identity, cursor_root = revision(
        candidate_id="cursor-root-outside",
        instrument_id="AVAX-USDT",
        detected_at=START + timedelta(minutes=40),
        source_type=EvidenceSource.FORWARD_PAPER,
    )

    async def append_cursor_corruption() -> None:
        async with host._sessions() as session, session.begin():
            await append_evidence_revision(session, cursor_root)
            revision_two = build_evidence_revision(
                opportunity=cursor_identity,
                evidence_revision=2,
                supersedes_evidence_id=cursor_root.evidence_id,
                detected_at=START + timedelta(minutes=10),
                evidence_at=cursor_root.evidence_at + timedelta(seconds=1),
                expires_at=cursor_root.expires_at,
                source_type=cursor_root.source_type,
                source_identity=cursor_root.source_identity,
                source_manifest_id=cursor_root.source_manifest_id,
                reference_data_status=cursor_root.reference_data_status,
                evidence_payload={},
                feature_snapshot_payload={},
                created_at=cursor_root.created_at + timedelta(seconds=1),
            )
            await append_evidence_revision(session, revision_two)
            persisted = await session.get(EdgeOpportunityEvidenceRecord, revision_two.evidence_id)
            assert persisted is not None
            persisted.evidence_revision = 3

    asyncio.run(append_cursor_corruption())
    cursor = encode_opportunity_cursor(
        OpportunityCursor(
            requested_range="custom",
            effective_start=START,
            effective_end=END,
            source_type=EvidenceSource.FORWARD_PAPER.value,
            detected_at=START + timedelta(minutes=30),
            opportunity_id="zzzz",
        )
    )
    cursor_page = _request(client, headers, query + f"&cursor={cursor}")
    assert cursor_page.status_code == 200
    assert cursor_identity.opportunity_id not in {
        item["opportunity_id"] for item in cursor_page.json()["data"]["items"]
    }

    async def corrupt_in_scope() -> None:
        async with host._sessions() as session, session.begin():
            record = await session.scalar(
                select(EdgeOpportunityEvidenceRecord).where(
                    EdgeOpportunityEvidenceRecord.opportunity_id == ids["opportunity"],
                    EdgeOpportunityEvidenceRecord.evidence_revision == 2,
                )
            )
            assert record is not None
            record.detected_at = END + timedelta(minutes=1)
            record.evidence_revision = 3

    asyncio.run(corrupt_in_scope())
    in_scope = _request(client, headers, query)
    assert in_scope.status_code == 503
    assert in_scope.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_collection_rootless_malformed_chain_fails_closed(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, _ = opportunity_host
    identity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="edge-v1",
        instrument_id="LINK-USDT",
        market_type=MarketType.SPOT,
        candidate_id="rootless-malformed",
    )
    root = build_evidence_revision(
        opportunity=identity,
        evidence_revision=1,
        detected_at=START + timedelta(minutes=20),
        evidence_at=START,
        expires_at=START + timedelta(minutes=30),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-rootless",
        source_manifest_id="manifest-rootless",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START,
    )
    revision_two = build_evidence_revision(
        opportunity=identity,
        evidence_revision=2,
        supersedes_evidence_id=root.evidence_id,
        detected_at=START + timedelta(minutes=21),
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=30),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="forward-rootless",
        source_manifest_id="manifest-rootless",
        reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
        evidence_payload={},
        feature_snapshot_payload={},
        created_at=START + timedelta(seconds=1),
    )

    async def append_rootless_malformed_chain() -> None:
        async with host._sessions() as session, session.begin():
            await append_evidence_revision(session, root)
            await append_evidence_revision(session, revision_two)
            persisted_root = await session.get(EdgeOpportunityEvidenceRecord, root.evidence_id)
            assert persisted_root is not None
            persisted_root.evidence_revision = 3
            persisted_root.supersedes_evidence_id = revision_two.evidence_id

    asyncio.run(append_rootless_malformed_chain())
    client = TestClient(app_module.app)
    response = _request(
        client,
        _headers(client),
        "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z",
    )
    assert response.status_code == 503
    assert response.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_unprovable_decision_binding_uses_frozen_absence_semantics(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, ids = opportunity_host

    async def replace_attribution(subject_id: str | None, evidence_id: str | None) -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))
            event = build_attribution_event(
                subject_type=AttributionSubjectType.AI,
                subject_id=subject_id,
                event_type=AttributionEventType.AI_ACCEPTED_LONG.value,
                opportunity_id=ids["opportunity"],
                evidence_id=evidence_id,
                payload={},
                occurred_at=START,
                recorded_at=START,
            )
            await append_attribution_event(session, event)

    client = TestClient(app_module.app)
    headers = _headers(client)
    asyncio.run(replace_attribution("decision-a", None))
    null_binding = _request(client, headers, f"/{ids['opportunity']}")
    assert null_binding.status_code == 200
    decision = null_binding.json()["data"]["trading_decision"]
    assert decision["state"] == "PRESENT"
    assert (
        decision["data"]["decisions"][0]["decision_bound_evidence"]["state"] == "NO_PROVABLE_RECORD"
    )
    asyncio.run(replace_attribution("missing-decision", None))
    unprovable_decision = _request(client, headers, f"/{ids['opportunity']}")
    assert unprovable_decision.status_code == 200
    assert unprovable_decision.json()["data"]["trading_decision"]["state"] == "NO_PROVABLE_RECORD"

    async def clear_attributions() -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))

    asyncio.run(clear_attributions())
    no_attribution = _request(client, headers, f"/{ids['opportunity']}")
    assert no_attribution.status_code == 200
    assert no_attribution.json()["data"]["trading_decision"]["state"] == "NO_PROVABLE_RECORD"


def test_corrupt_exact_decision_bindings_remain_snapshot_failures(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, ids = opportunity_host

    async def evidence_ids() -> tuple[str, str, str]:
        async with host._sessions() as session:
            records = list(
                (
                    await session.scalars(
                        select(EdgeOpportunityEvidenceRecord).where(
                            EdgeOpportunityEvidenceRecord.opportunity_id == ids["opportunity"]
                        )
                    )
                ).all()
            )
            replay = await session.scalar(
                select(EdgeOpportunityEvidenceRecord).where(
                    EdgeOpportunityEvidenceRecord.opportunity_id == ids["replay"]
                )
            )
            assert replay is not None
            ordered = sorted(records, key=lambda record: record.evidence_revision)
            return ordered[0].evidence_id, ordered[1].evidence_id, replay.evidence_id

    first, second, cross_opportunity = asyncio.run(evidence_ids())

    async def replace_attributions(*, evidence_id: str, competing: bool = False) -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))
            first_event = build_attribution_event(
                subject_type=AttributionSubjectType.AI,
                subject_id="decision-a",
                event_type=AttributionEventType.AI_ACCEPTED_LONG.value,
                opportunity_id=ids["opportunity"],
                evidence_id=evidence_id,
                payload={},
                occurred_at=START,
                recorded_at=START,
            )
            await append_attribution_event(session, first_event)
            if competing:
                second_event = build_attribution_event(
                    subject_type=AttributionSubjectType.AI,
                    subject_id="decision-a",
                    event_type=AttributionEventType.AI_ACCEPTED_LONG.value,
                    opportunity_id=ids["opportunity"],
                    evidence_id=second,
                    payload={},
                    occurred_at=START + timedelta(seconds=1),
                    recorded_at=START + timedelta(seconds=1),
                )
                await append_attribution_event(session, second_event)

    client = TestClient(app_module.app)
    headers = _headers(client)
    asyncio.run(replace_attributions(evidence_id="missing-evidence"))
    missing = _request(client, headers, f"/{ids['opportunity']}")
    assert missing.status_code == 503
    assert missing.json()["read_failure_reason"] == "SNAPSHOT_FAILED"
    asyncio.run(replace_attributions(evidence_id=cross_opportunity))
    cross = _request(client, headers, f"/{ids['opportunity']}")
    assert cross.status_code == 503
    assert cross.json()["read_failure_reason"] == "SNAPSHOT_FAILED"
    asyncio.run(replace_attributions(evidence_id=first, competing=True))
    conflicting = _request(client, headers, f"/{ids['opportunity']}")
    assert conflicting.status_code == 503
    assert conflicting.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_attribution_authority_validates_conflicts_before_decision_existence(
    opportunity_host: tuple[RuntimeHost, dict[str, str]],
) -> None:
    host, ids = opportunity_host

    async def evidence_ids() -> tuple[str, str]:
        async with host._sessions() as session:
            rows = list(
                (
                    await session.scalars(
                        select(EdgeOpportunityEvidenceRecord).where(
                            EdgeOpportunityEvidenceRecord.opportunity_id == ids["opportunity"]
                        )
                    )
                ).all()
            )
            ordered = sorted(rows, key=lambda row: row.evidence_revision)
            return ordered[0].evidence_id, ordered[1].evidence_id

    first, second = asyncio.run(evidence_ids())

    async def replace(
        *, decision_id: str, event_types: list[str], evidence_ids: list[str | None]
    ) -> None:
        async with host._sessions() as session, session.begin():
            await session.execute(delete(EdgeAttributionEventRecord))
            for index, (event_type, evidence_id) in enumerate(
                zip(event_types, evidence_ids, strict=True)
            ):
                await append_attribution_event(
                    session,
                    build_attribution_event(
                        subject_type=AttributionSubjectType.AI,
                        subject_id=decision_id,
                        event_type=event_type,
                        opportunity_id=ids["opportunity"],
                        evidence_id=evidence_id,
                        payload={},
                        occurred_at=START + timedelta(seconds=index),
                        recorded_at=START + timedelta(seconds=index),
                    ),
                )

    client = TestClient(app_module.app)
    headers = _headers(client)
    suffix = f"/{ids['opportunity']}"
    accepted = AttributionEventType.AI_ACCEPTED_LONG.value
    rejected = AttributionEventType.AI_REJECTED_WAIT.value

    asyncio.run(
        replace(
            decision_id="decision-a", event_types=[accepted, accepted], evidence_ids=[first, None]
        )
    )
    exact_plus_null = _request(client, headers, suffix)
    assert exact_plus_null.status_code == 200
    decision = exact_plus_null.json()["data"]["trading_decision"]["data"]["decisions"][0]
    assert decision["attribution_event_type"] == accepted
    assert decision["decision_bound_evidence"]["data"]["evidence_id"] == first

    asyncio.run(
        replace(
            decision_id="decision-a", event_types=[accepted, rejected], evidence_ids=[first, first]
        )
    )
    existing_event_conflict = _request(client, headers, suffix)
    assert existing_event_conflict.status_code == 503
    assert existing_event_conflict.json()["read_failure_reason"] == "SNAPSHOT_FAILED"

    asyncio.run(
        replace(
            decision_id="decision-a", event_types=[accepted, accepted], evidence_ids=[first, second]
        )
    )
    existing_binding_conflict = _request(client, headers, suffix)
    assert existing_binding_conflict.status_code == 503
    assert existing_binding_conflict.json()["read_failure_reason"] == "SNAPSHOT_FAILED"

    asyncio.run(
        replace(decision_id="missing-decision", event_types=[accepted], evidence_ids=[first])
    )
    missing_consistent = _request(client, headers, suffix)
    assert missing_consistent.status_code == 200
    assert missing_consistent.json()["data"]["trading_decision"]["state"] == "NO_PROVABLE_RECORD"

    asyncio.run(
        replace(
            decision_id="missing-decision",
            event_types=[accepted, rejected],
            evidence_ids=[first, first],
        )
    )
    missing_event_conflict = _request(client, headers, suffix)
    assert missing_event_conflict.status_code == 503
    assert missing_event_conflict.json()["read_failure_reason"] == "SNAPSHOT_FAILED"

    asyncio.run(
        replace(
            decision_id="missing-decision",
            event_types=[accepted, accepted],
            evidence_ids=[first, second],
        )
    )
    missing_binding_conflict = _request(client, headers, suffix)
    assert missing_binding_conflict.status_code == 503
    assert missing_binding_conflict.json()["read_failure_reason"] == "SNAPSHOT_FAILED"


def test_product_error_boundaries_are_typed_and_sanitized(
    opportunity_host: tuple[RuntimeHost, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, ids = opportunity_host
    client = TestClient(app_module.app)
    headers = _headers(client)
    original_begin_snapshot = opportunities_module._begin_snapshot
    original_fold_evidence_records = opportunities_module.fold_evidence_records
    original_opportunity_dto = opportunities_module._opportunity_dto

    async def source_failure(_: object) -> datetime:
        raise OperationalError("SELECT source", {}, RuntimeError("source-secret"))

    monkeypatch.setattr(opportunities_module, "_begin_snapshot", source_failure)
    collection_suffix = "?range=custom&start=2026-09-18T10:00:00Z&end=2026-09-18T11:00:00Z"
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 503
        assert response.json()["read_failure_reason"] == "SOURCE_UNAVAILABLE"
        assert "source-secret" not in response.text

    async def timeout_failure(_: object) -> datetime:
        raise TimeoutError("timeout-secret")

    monkeypatch.setattr(opportunities_module, "_begin_snapshot", timeout_failure)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 503
        assert response.json()["read_failure_reason"] == "SOURCE_UNAVAILABLE"
        assert "timeout-secret" not in response.text

    async def auth_failure(_: object) -> datetime:
        raise asyncpg.exceptions.InvalidPasswordError("auth-secret")

    monkeypatch.setattr(opportunities_module, "_begin_snapshot", auth_failure)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 503
        assert response.json()["read_failure_reason"] == "SOURCE_UNAVAILABLE"
        assert "auth-secret" not in response.text

    async def refused_failure(_: object) -> datetime:
        raise ConnectionRefusedError("refused-secret")

    monkeypatch.setattr(opportunities_module, "_begin_snapshot", refused_failure)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 503
        assert response.json()["read_failure_reason"] == "SOURCE_UNAVAILABLE"
        assert "refused-secret" not in response.text

    monkeypatch.setattr(opportunities_module, "_begin_snapshot", original_begin_snapshot)

    def integrity_failure(_: object) -> object:
        raise opportunities_module.SnapshotIntegrityError(("injected-integrity-secret",))

    monkeypatch.setattr(opportunities_module, "fold_evidence_records", integrity_failure)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 503
        assert response.json()["read_failure_reason"] == "SNAPSHOT_FAILED"
        assert "injected-integrity-secret" not in response.text

    monkeypatch.setattr(
        opportunities_module, "fold_evidence_records", original_fold_evidence_records
    )

    def internal_failure(*_: object, **__: object) -> object:
        raise RuntimeError("internal-mapper-secret")

    monkeypatch.setattr(opportunities_module, "_opportunity_dto", internal_failure)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 500
        assert "correlation_id" in response.json()
        assert "internal-mapper-secret" not in response.text

    def product_timeout(*_: object, **__: object) -> object:
        raise TimeoutError("product-timeout-secret")

    monkeypatch.setattr(opportunities_module, "_opportunity_dto", product_timeout)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 500
        assert "correlation_id" in response.json()
        assert "product-timeout-secret" not in response.text

    def product_os_error(*_: object, **__: object) -> object:
        raise OSError("product-oserror-secret")

    monkeypatch.setattr(opportunities_module, "_opportunity_dto", product_os_error)
    for suffix in (collection_suffix, f"/{ids['opportunity']}"):
        response = _request(client, headers, suffix)
        assert response.status_code == 500
        assert "correlation_id" in response.json()
        assert "product-oserror-secret" not in response.text
    monkeypatch.setattr(opportunities_module, "_opportunity_dto", original_opportunity_dto)


def test_forward_due_authority_is_reused_for_all_horizons_and_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = SimpleNamespace(
        opportunity_id="opportunity", evidence_id="evidence", evidence_at=START
    )
    original_forward_due_at = opportunities_module.forward_due_at
    calls: list[ForwardHorizon] = []

    def controlled_due_at(evidence_at: datetime, horizon: ForwardHorizon) -> datetime:
        calls.append(horizon)
        return evidence_at + timedelta(days=1)

    monkeypatch.setattr(opportunities_module, "forward_due_at", controlled_due_at)
    controlled = opportunities_module._forward_nodes(
        evidence=evidence,
        outcome_records=[],
        as_of=START,
    )
    assert set(calls) == set(ForwardHorizon)
    assert {node.state for node in controlled.values()} == {
        opportunities_module.TraceNodeState.NOT_YET_DUE
    }

    monkeypatch.setattr(opportunities_module, "forward_due_at", original_forward_due_at)
    due_at = original_forward_due_at(START, ForwardHorizon.M5)
    before = opportunities_module._forward_nodes(
        evidence=evidence,
        outcome_records=[],
        as_of=due_at - timedelta(microseconds=1),
    )
    exactly_due = opportunities_module._forward_nodes(
        evidence=evidence, outcome_records=[], as_of=due_at
    )
    after = opportunities_module._forward_nodes(
        evidence=evidence,
        outcome_records=[],
        as_of=due_at + timedelta(microseconds=1),
    )
    assert before["5m"].state == opportunities_module.TraceNodeState.NOT_YET_DUE
    assert exactly_due["5m"].state != opportunities_module.TraceNodeState.NOT_YET_DUE
    assert after["5m"].state != opportunities_module.TraceNodeState.NOT_YET_DUE
