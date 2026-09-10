"""SE-02A additive persistence acceptance against real disposable PostgreSQL.

Covers the four approved Edge persistence boundaries, the frozen revision
semantics, and the minimal database-level backstops. No runtime capture, no
forward-outcome calculator and no G2/G3/G4/G5 integration is exercised here.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.db.models import (
    EdgeAttributionEventRecord,
    EdgeBboObservationRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.models import (
    AttributionSubjectType,
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ForwardHorizon,
    ForwardOutcomeContract,
    OpportunityIdentity,
    ReferenceDataReason,
    ReferenceDataStatus,
    build_attribution_event,
    build_bbo_observation,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.edge.repository import (
    IDEMPOTENT,
    INSERTED,
    EdgeEvidenceConflict,
    EdgeInvalidOutcomeSupersedes,
    EdgeInvalidSupersedes,
    append_attribution_event,
    append_evidence_revision,
    append_forward_outcome,
    record_bbo_observation,
)
from marketpulse.market_data.models import DataQuality, MarketType
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
PRIMARY_URL = Settings().database_url
BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260905_0004"
EDGE_TABLES = frozenset(
    {
        "edge_opportunity_evidence",
        "edge_bbo_observations",
        "edge_forward_outcomes",
        "edge_attribution_events",
    }
)


# --- disposable PostgreSQL harness ------------------------------------------------------


def _url_for(database_name: str) -> str:
    return f"{PRIMARY_URL.rsplit('/', 1)[0]}/{database_name}"


async def _execute(url: str, statement: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@asynccontextmanager
async def _session(url: str):
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _upgrade(url: str, revision: str) -> None:
    command.upgrade(_alembic_config(url), revision)


def _downgrade(url: str, revision: str) -> None:
    command.downgrade(_alembic_config(url), revision)


@contextmanager
def _edge_database(label: str):
    name = f"marketpulse_se02a_{label}_{uuid4().hex[:12]}"
    asyncio.run(_execute(PRIMARY_URL, f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    _upgrade(url, "head")
    try:
        yield name, url
    finally:
        asyncio.run(
            _execute(
                PRIMARY_URL,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute(PRIMARY_URL, f'DROP DATABASE "{name}"'))


async def _table_names(url: str) -> set[str]:
    async with _session(url) as session:
        rows = await session.scalars(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        return set(rows.all())


async def _count(url: str, model) -> int:
    async with _session(url) as session:
        return int(await session.scalar(select(func.count()).select_from(model)))


def _expect_integrity_error(url: str, row: object) -> None:
    """Prove a database-level backstop rejects a row that bypasses the service layer."""

    async def scenario() -> None:
        async with _session(url) as session:
            session.add(row)
            await session.flush()

    with pytest.raises(IntegrityError):
        asyncio.run(scenario())


# --- fixtures ---------------------------------------------------------------------------


def _opportunity(
    *, candidate_id: str = "sc_breakout_1", instrument_id: str = "BTC-USDT"
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version="f1",
        instrument_id=instrument_id,
        market_type=MarketType.SPOT,
        candidate_id=candidate_id,
    )


def _evidence(
    opportunity: OpportunityIdentity,
    *,
    revision: int = 1,
    supersedes: str | None = None,
    payload: dict | None = None,
) -> EvidenceRevision:
    return build_evidence_revision(
        opportunity=opportunity,
        evidence_revision=revision,
        detected_at=START,
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=5),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-1",
        reference_bid=99.0,
        reference_ask=100.0,
        reference_received_at=START,
        reference_data_status=ReferenceDataStatus.OK,
        reference_data_reason=ReferenceDataReason.NONE,
        evidence_payload={"setup": "breakout"} if payload is None else payload,
        feature_snapshot_payload={"retest": True, "level": 99.5},
        supersedes_evidence_id=supersedes,
        created_at=START,
    )


def _outcome(
    opportunity: OpportunityIdentity,
    evidence: EvidenceRevision,
    *,
    revision: int = 1,
    supersedes: str | None = None,
    horizon: ForwardHorizon = ForwardHorizon.M5,
    source_type: EvidenceSource = EvidenceSource.HISTORICAL_REPLAY,
    source_identity: str = "replay-a",
    calculator_version: str = "calc-v1",
) -> ForwardOutcomeContract:
    return build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=evidence.evidence_id,
        horizon=horizon,
        outcome_revision=revision,
        due_at=START + timedelta(seconds=horizon.duration_seconds),
        source_type=source_type,
        source_identity=source_identity,
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version=calculator_version,
        reference_price=99.5,
        end_bid=100.5,
        end_ask=100.6,
        created_at=START,
        supersedes_outcome_id=supersedes,
    )


def _evidence_row(**overrides) -> EdgeOpportunityEvidenceRecord:
    values = {
        "evidence_id": "e" * 64,
        "opportunity_id": "o" * 64,
        "candidate_id": "sc_raw",
        "family_id": "BREAKOUT_RETEST",
        "family_version": "f1",
        "instrument_id": "BTC-USDT",
        "market_type": "SPOT",
        "evidence_revision": 1,
        "evidence_contract_version": "se02-evidence-v1",
        "evidence_hash": "h" * 64,
        "feature_snapshot_hash": "s" * 64,
        "feature_snapshot_hash_version": "se02-feature-snapshot-hash-v1",
        "supersedes_evidence_id": None,
        "detected_at": START,
        "evidence_at": START,
        "expires_at": START,
        "source_type": "HISTORICAL_REPLAY",
        "source_identity": "raw",
        "source_manifest_id": "manifest-raw",
        "reference_bid": 99.0,
        "reference_ask": 100.0,
        "reference_received_at": START,
        "reference_data_status": "OK",
        "reference_data_reason": "NONE",
        "evidence_payload": {},
        "feature_snapshot_payload": {},
        "created_at": START,
    }
    values.update(overrides)
    return EdgeOpportunityEvidenceRecord(**values)


def _outcome_row(**overrides) -> EdgeForwardOutcomeRecord:
    values = {
        "outcome_id": "u" * 64,
        "opportunity_id": "o" * 64,
        "evidence_id": "e" * 64,
        "horizon": "5m",
        "outcome_revision": 1,
        "supersedes_outcome_id": None,
        "outcome_contract_version": "se02-outcome-v1",
        "calculation_status": "PENDING",
        "opportunity_lifecycle_at_horizon": None,
        "due_at": START,
        "source_type": "HISTORICAL_REPLAY",
        "source_identity": "raw",
        "reference_bbo_observation_id": None,
        "end_bbo_observation_id": None,
        "reference_price": None,
        "end_bid": None,
        "end_ask": None,
        "mfe": None,
        "mae": None,
        "reference_return": None,
        "executable_long_return": None,
        "cost_adjusted_forward_return": None,
        "completeness_diagnostics": {},
        "cost_policy": "taker-only",
        "cost_model_version": "cost-v1",
        "calculator_version": "calc-v1",
        "calculation_digest": None,
        "calculation_digest_version": "se02-outcome-calculation-digest-v1",
        "outcome_record_hash": "r" * 64,
        "outcome_record_hash_version": "se02-outcome-record-hash-v1",
        "created_at": START,
    }
    values.update(overrides)
    return EdgeForwardOutcomeRecord(**values)


# --- evidence persistence ---------------------------------------------------------------


def test_first_evidence_revision_is_persisted_with_its_full_provenance():
    with _edge_database("evidence_first") as (_, url):
        opportunity = _opportunity()
        record = _evidence(opportunity)

        async def scenario():
            async with _session(url) as session:
                outcome = await append_evidence_revision(session, record)
                await session.commit()
                row = await session.scalar(
                    select(EdgeOpportunityEvidenceRecord).where(
                        EdgeOpportunityEvidenceRecord.evidence_id == record.evidence_id
                    )
                )
                return outcome, row

        outcome, row = asyncio.run(scenario())

        assert outcome == INSERTED
        assert row is not None
        assert row.opportunity_id == opportunity.opportunity_id
        assert row.candidate_id == "sc_breakout_1"
        assert row.family_id == "BREAKOUT_RETEST"
        assert row.family_version == "f1"
        assert row.instrument_id == "BTC-USDT"
        assert row.market_type == "SPOT"
        assert row.evidence_revision == 1
        assert row.evidence_contract_version == "se02-evidence-v1"
        assert row.evidence_hash == record.evidence_hash
        assert row.feature_snapshot_hash == record.feature_snapshot_hash
        assert row.supersedes_evidence_id is None
        assert row.detected_at == START
        assert row.evidence_at == START + timedelta(seconds=1)
        assert row.expires_at == START + timedelta(minutes=5)
        assert row.source_type == "HISTORICAL_REPLAY"
        assert row.source_identity == "okx-ws-bbo"
        assert row.source_manifest_id == "manifest-1"
        assert row.reference_bid == 99.0
        assert row.reference_ask == 100.0
        assert row.reference_data_status == "OK"
        assert row.reference_data_reason == "NONE"
        assert row.evidence_payload == {"setup": "breakout"}
        assert row.feature_snapshot_payload == {"retest": True, "level": 99.5}


def test_exact_duplicate_revision_is_idempotent():
    with _edge_database("evidence_dup") as (_, url):
        record = _evidence(_opportunity())

        async def scenario():
            async with _session(url) as session:
                first = await append_evidence_revision(session, record)
                second = await append_evidence_revision(session, record)
                await session.commit()
                return first, second

        first, second = asyncio.run(scenario())

        assert (first, second) == (INSERTED, IDEMPOTENT)
        assert asyncio.run(_count(url, EdgeOpportunityEvidenceRecord)) == 1


def test_same_revision_with_a_different_hash_fails_closed():
    with _edge_database("evidence_conflict") as (_, url):
        opportunity = _opportunity()
        original = _evidence(opportunity)
        conflicting = _evidence(opportunity, payload={"setup": "tampered"})

        assert conflicting.evidence_id == original.evidence_id
        assert conflicting.evidence_hash != original.evidence_hash

        async def scenario():
            async with _session(url) as session:
                await append_evidence_revision(session, original)
                await session.commit()
            async with _session(url) as session:
                with pytest.raises(EdgeEvidenceConflict):
                    await append_evidence_revision(session, conflicting)

        asyncio.run(scenario())
        assert asyncio.run(_count(url, EdgeOpportunityEvidenceRecord)) == 1


def test_valid_superseding_revision_creates_an_immutable_correction():
    with _edge_database("evidence_supersede") as (_, url):
        opportunity = _opportunity()
        first = _evidence(opportunity)
        second = _evidence(opportunity, revision=2, supersedes=first.evidence_id)

        async def scenario():
            async with _session(url) as session:
                assert await append_evidence_revision(session, first) == INSERTED
                assert await append_evidence_revision(session, second) == INSERTED
                await session.commit()
                rows = (
                    await session.scalars(
                        select(EdgeOpportunityEvidenceRecord)
                        .where(
                            EdgeOpportunityEvidenceRecord.opportunity_id
                            == opportunity.opportunity_id
                        )
                        .order_by(EdgeOpportunityEvidenceRecord.evidence_revision)
                    )
                ).all()
                return rows

        rows = asyncio.run(scenario())

        assert [row.evidence_revision for row in rows] == [1, 2]
        assert rows[0].supersedes_evidence_id is None
        assert rows[1].supersedes_evidence_id == first.evidence_id
        # The superseded revision is still present: a correction appends, never rewrites.
        assert rows[1].evidence_hash != rows[0].evidence_hash
        assert asyncio.run(_count(url, EdgeOpportunityEvidenceRecord)) == 2


def test_invalid_evidence_supersedes_relations_are_rejected():
    with _edge_database("evidence_bad_supersede") as (_, url):
        alpha = _opportunity(candidate_id="sc_alpha")
        beta = _opportunity(candidate_id="sc_beta")
        alpha_first = _evidence(alpha)
        beta_first = _evidence(beta)

        async def scenario():
            async with _session(url) as session:
                await append_evidence_revision(session, alpha_first)
                await append_evidence_revision(session, beta_first)
                await session.commit()

            async with _session(url) as session:
                with pytest.raises(EdgeInvalidSupersedes):
                    await append_evidence_revision(
                        session, _evidence(beta, revision=2, supersedes=alpha_first.evidence_id)
                    )
            async with _session(url) as session:
                with pytest.raises(EdgeInvalidSupersedes):
                    await append_evidence_revision(
                        session, _evidence(beta, revision=2, supersedes="f" * 64)
                    )
            async with _session(url) as session:
                with pytest.raises(EdgeInvalidSupersedes):
                    await append_evidence_revision(
                        session, _evidence(beta, revision=3, supersedes=beta_first.evidence_id)
                    )

        asyncio.run(scenario())
        assert asyncio.run(_count(url, EdgeOpportunityEvidenceRecord)) == 2


def test_database_rejects_evidence_rows_that_bypass_the_service_rules():
    with _edge_database("evidence_db_backstop") as (_, url):
        # A composite supersedes foreign key needs the target to exist for the same
        # opportunity, so cross-opportunity and dangling links die in PostgreSQL too.
        _expect_integrity_error(
            url,
            _evidence_row(
                evidence_id="a" * 64,
                opportunity_id="o" * 64,
                evidence_revision=2,
                supersedes_evidence_id="b" * 64,
            ),
        )
        # Frozen family vocabulary.
        _expect_integrity_error(url, _evidence_row(family_id="TREND_PULLBACK"))
        # A revision above 1 may not exist without a supersedes link.
        _expect_integrity_error(url, _evidence_row(evidence_revision=2, supersedes_evidence_id=None))
        # Revision numbering starts at 1.
        _expect_integrity_error(url, _evidence_row(evidence_revision=0))
        assert asyncio.run(_count(url, EdgeOpportunityEvidenceRecord)) == 0


# --- BBO observation persistence --------------------------------------------------------


def test_bbo_observation_persists_the_horizon_reference_schema():
    with _edge_database("bbo") as (_, url):
        with_sequence = build_bbo_observation(
            instrument_id="BTC-USDT",
            market_type=MarketType.SPOT,
            bid=99.0,
            ask=100.0,
            available_at=START,
            source_event_time=START,
            received_at=START,
            data_quality=DataQuality.FRESH,
            tradable=True,
            source="okx-ws-bbo",
            source_sequence=42,
            created_at=START,
        )
        without_sequence = build_bbo_observation(
            instrument_id="BTC-USDT",
            market_type=MarketType.SWAP,
            bid=101.0,
            ask=102.0,
            available_at=START + timedelta(seconds=5),
            source_event_time=START + timedelta(seconds=4),
            received_at=START + timedelta(seconds=4),
            data_quality=DataQuality.STALE,
            tradable=False,
            source="okx-ws-bbo",
            created_at=START,
        )

        async def scenario():
            async with _session(url) as session:
                assert await record_bbo_observation(session, with_sequence) == INSERTED
                assert await record_bbo_observation(session, without_sequence) == INSERTED
                assert await record_bbo_observation(session, with_sequence) == IDEMPOTENT
                await session.commit()
                rows = (
                    await session.scalars(
                        select(EdgeBboObservationRecord).order_by(
                            EdgeBboObservationRecord.available_at
                        )
                    )
                ).all()
                return rows

        rows = asyncio.run(scenario())

        assert len(rows) == 2
        first, second = rows
        assert first.instrument_id == "BTC-USDT"
        assert first.market_type == "SPOT"
        assert (first.bid, first.ask) == (99.0, 100.0)
        assert first.available_at == START
        assert first.source_event_time == START
        assert first.received_at == START
        assert first.source_sequence == 42
        assert first.data_quality == "FRESH"
        assert first.tradable is True
        assert first.source == "okx-ws-bbo"
        assert second.market_type == "SWAP"
        assert second.source_sequence is None
        assert second.data_quality == "STALE"
        assert second.tradable is False

        _expect_integrity_error(
            url,
            EdgeBboObservationRecord(
                observation_id="z" * 64,
                instrument_id="BTC-USDT",
                market_type="SPOT",
                bid=101.0,
                ask=100.0,
                available_at=START,
                source_event_time=START,
                received_at=START,
                data_quality="FRESH",
                tradable=True,
                source="raw",
                source_sequence=None,
                created_at=START,
            ),
        )


# --- forward outcome persistence --------------------------------------------------------


def test_outcome_revision_persistence_and_digest_separation():
    with _edge_database("outcome") as (_, url):
        opportunity = _opportunity()
        evidence = _evidence(opportunity)
        first = _outcome(opportunity, evidence)
        second = _outcome(opportunity, evidence, revision=2, supersedes=first.outcome_id)

        assert first.calculation_digest is not None
        assert first.calculation_digest != first.outcome_record_hash

        async def scenario():
            async with _session(url) as session:
                await append_evidence_revision(session, evidence)
                assert await append_forward_outcome(session, first) == INSERTED
                assert await append_forward_outcome(session, first) == IDEMPOTENT
                assert await append_forward_outcome(session, second) == INSERTED
                await session.commit()
                rows = (
                    await session.scalars(
                        select(EdgeForwardOutcomeRecord).order_by(
                            EdgeForwardOutcomeRecord.outcome_revision
                        )
                    )
                ).all()
                return rows

        rows = asyncio.run(scenario())

        assert [row.outcome_revision for row in rows] == [1, 2]
        assert rows[0].horizon == "5m"
        assert rows[0].due_at == START + timedelta(minutes=5)
        assert rows[0].calculation_digest == first.calculation_digest
        assert rows[0].outcome_record_hash == first.outcome_record_hash
        assert rows[0].calculation_digest_version == "se02-outcome-calculation-digest-v1"
        assert rows[0].outcome_record_hash_version == "se02-outcome-record-hash-v1"
        assert rows[1].supersedes_outcome_id == first.outcome_id
        assert rows[1].outcome_record_hash != rows[0].outcome_record_hash
        assert asyncio.run(_count(url, EdgeForwardOutcomeRecord)) == 2


def test_replay_and_forward_provenance_share_one_calculation_digest():
    with _edge_database("outcome_provenance") as (_, url):
        opportunity = _opportunity()
        evidence = _evidence(opportunity)
        replay = _outcome(opportunity, evidence, source_type=EvidenceSource.HISTORICAL_REPLAY)
        paper = _outcome(
            opportunity,
            evidence,
            revision=2,
            supersedes=replay.outcome_id,
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="paper-b",
        )

        # Identical calculation facts, different provenance.
        assert replay.calculation_digest == paper.calculation_digest
        assert replay.outcome_revision != paper.outcome_revision

        async def scenario():
            async with _session(url) as session:
                await append_evidence_revision(session, evidence)
                await append_forward_outcome(session, replay)
                await append_forward_outcome(session, paper)
                await session.commit()
                return (
                    await session.scalars(
                        select(EdgeForwardOutcomeRecord).order_by(
                            EdgeForwardOutcomeRecord.outcome_revision
                        )
                    )
                ).all()

        rows = asyncio.run(scenario())

        assert {row.calculation_digest for row in rows} == {replay.calculation_digest}
        assert {row.outcome_record_hash for row in rows} == {
            replay.outcome_record_hash,
            paper.outcome_record_hash,
        }
        assert [row.source_type for row in rows] == ["HISTORICAL_REPLAY", "FORWARD_PAPER"]


def test_outcome_supersedes_and_reference_integrity_fail_closed():
    with _edge_database("outcome_integrity") as (_, url):
        alpha = _opportunity(candidate_id="sc_alpha")
        beta = _opportunity(candidate_id="sc_beta")
        alpha_evidence = _evidence(alpha)
        alpha_outcome = _outcome(alpha, alpha_evidence)

        async def scenario():
            async with _session(url) as session:
                await append_evidence_revision(session, alpha_evidence)
                await append_forward_outcome(session, alpha_outcome)
                await session.commit()
            async with _session(url) as session:
                with pytest.raises(EdgeInvalidOutcomeSupersedes):
                    await append_forward_outcome(
                        session,
                        _outcome(
                            alpha,
                            alpha_evidence,
                            revision=2,
                            supersedes="f" * 64,
                        ),
                    )

        asyncio.run(scenario())
        assert asyncio.run(_count(url, EdgeForwardOutcomeRecord)) == 1

        # An outcome that names evidence of another opportunity violates the composite
        # foreign key, so the database refuses it as well.
        _expect_integrity_error(
            url,
            _outcome_row(
                opportunity_id=beta.opportunity_id,
                evidence_id=alpha_evidence.evidence_id,
            ),
        )
        # A dangling evidence reference is refused.
        _expect_integrity_error(url, _outcome_row(evidence_id="d" * 64, opportunity_id="q" * 64))


def test_outcome_horizon_and_status_are_constrained_at_the_database_level():
    with _edge_database("outcome_checks") as (_, url):
        for overrides in (
            {"horizon": "1m"},
            {"horizon": "5s"},
            {"calculation_status": "MAYBE"},
            {"opportunity_lifecycle_at_horizon": "SOMETIMES"},
            {"outcome_revision": 2, "supersedes_outcome_id": None},
        ):
            _expect_integrity_error(url, _outcome_row(**overrides))
        assert asyncio.run(_count(url, EdgeForwardOutcomeRecord)) == 0


# --- attribution lineage ----------------------------------------------------------------


def test_attribution_events_are_append_only_and_idempotent():
    with _edge_database("attribution") as (_, url):
        opportunity = _opportunity()
        ai_event = build_attribution_event(
            subject_type=AttributionSubjectType.AI,
            event_type="ANALYSIS_RECORDED",
            occurred_at=START,
            recorded_at=START,
            payload={"direction": "LONG_BIAS"},
            opportunity_id=opportunity.opportunity_id,
        )
        plan_event = build_attribution_event(
            subject_type=AttributionSubjectType.PLAN,
            event_type="PLAN_CREATED",
            occurred_at=START + timedelta(seconds=1),
            recorded_at=START + timedelta(seconds=2),
            payload={"plan_id": "plan-1"},
            opportunity_id=opportunity.opportunity_id,
        )
        economic_event = build_attribution_event(
            subject_type=AttributionSubjectType.ECONOMIC_RESULT,
            event_type="TRADE_CLOSED",
            occurred_at=START + timedelta(minutes=10),
            recorded_at=START + timedelta(minutes=10),
            payload={"exit_reason": "STOP_LOSS"},
        )

        async def scenario():
            async with _session(url) as session:
                assert await append_attribution_event(session, ai_event) == INSERTED
                assert await append_attribution_event(session, plan_event) == INSERTED
                assert await append_attribution_event(session, economic_event) == INSERTED
                assert await append_attribution_event(session, ai_event) == IDEMPOTENT
                await session.commit()
                return (
                    await session.scalars(
                        select(EdgeAttributionEventRecord).order_by(
                            EdgeAttributionEventRecord.occurred_at
                        )
                    )
                ).all()

        rows = asyncio.run(scenario())

        assert len(rows) == 3
        assert [row.subject_type for row in rows] == ["AI", "PLAN", "ECONOMIC_RESULT"]
        assert rows[0].payload_hash == ai_event.payload_hash
        assert rows[0].contract_version == "se02-attribution-v1"
        assert rows[2].opportunity_id is None
        assert rows[2].payload == {"exit_reason": "STOP_LOSS"}

        _expect_integrity_error(
            url,
            EdgeAttributionEventRecord(
                attribution_event_id="a" * 64,
                contract_version="se02-attribution-v1",
                subject_type="STRATEGY",
                subject_id=None,
                event_type="X",
                opportunity_id=None,
                evidence_id=None,
                payload={},
                payload_hash="p" * 64,
                occurred_at=START,
                recorded_at=START,
            ),
        )


# --- migration boundary -----------------------------------------------------------------


def test_migration_cycle_only_adds_and_removes_edge_tables():
    with _edge_database("migration") as (_, url):
        head_tables = asyncio.run(_table_names(url))
        assert EDGE_TABLES <= head_tables
        assert {"positions", "paper_orders", "trade_plans", "market_events"} <= head_tables

        _downgrade(url, PREVIOUS_REVISION)
        downgraded_tables = asyncio.run(_table_names(url))
        assert not (EDGE_TABLES & downgraded_tables)
        assert {"positions", "paper_orders", "trade_plans", "market_events"} <= downgraded_tables

        _upgrade(url, "head")
        reupgraded_tables = asyncio.run(_table_names(url))
        assert EDGE_TABLES <= reupgraded_tables


def test_no_disposable_edge_database_is_left_behind():
    async def scenario() -> list[str]:
        engine = create_async_engine(PRIMARY_URL, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                rows = await connection.execute(
                    text("SELECT datname FROM pg_database WHERE datname LIKE 'marketpulse_se02a_%'")
                )
                return [name for (name,) in rows]
        finally:
            await engine.dispose()

    assert asyncio.run(scenario()) == []
