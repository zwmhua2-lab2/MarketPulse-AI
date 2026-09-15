"""SE-02D-I02: current-snapshot revision folding projection -- acceptance tests.

Two kinds of evidence:

* **Focused pure tests** (task section 28) exercise the folding / validation /
  projection logic directly with in-memory Accepted contracts (or in-memory ORM
  rows for rehydration-corruption cases). No database is required for these.
* **PostgreSQL MVCC tests** (task section 29, Snapshot A/B/C/D) run against a
  *disposable* database created and dropped by the test itself, reusing the
  already Accepted SE-02C harness shape. No accepted / shared database is ever
  touched.

All destructive durable writes go through the accepted SE-02A / SE-02B
repository writers into the disposable database only.
"""

import asyncio
import inspect
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.db.models import (
    EdgeForwardOutcomeRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.aggregation import NO_MEASUREMENT, build_ordered_input_manifest
from marketpulse.edge.aggregation_snapshot import (
    CurrentSnapshotRevisionReader,
    SnapshotIntegrityError,
    _check_cross_integrity,
    _evidence_from_record,
    _fold_evidence_chains,
    _fold_outcome_chains,
    _outcome_from_record,
    _project,
)
from marketpulse.edge.forward import forward_due_at
from marketpulse.edge.hashing import canonical_bytes
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.edge.repository import append_evidence_revision, append_forward_outcome
from marketpulse.market_data.models import MarketType
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
INSTRUMENT = "BTC-USDT"
PRIMARY_URL = Settings().database_url
BACKEND = Path(__file__).resolve().parents[1]


# --- disposable PostgreSQL harness (SE-02C shape) ----------------------------------------


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
async def _sessions(url: str):
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@contextmanager
def _se02d_database(label: str):
    name = f"marketpulse_se02d_{label}_{uuid4().hex[:12]}"
    asyncio.run(_execute(PRIMARY_URL, f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    command.upgrade(_alembic_config(url), "head")
    try:
        yield url
    finally:
        asyncio.run(
            _execute(
                PRIMARY_URL,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute(PRIMARY_URL, f'DROP DATABASE "{name}"'))


# --- contract builders (SE-02A shape) -----------------------------------------------------


def _opportunity(
    *,
    candidate_id="sc_breakout_1",
    instrument_id=INSTRUMENT,
    family_id=EdgeFamily.BREAKOUT_RETEST,
    family_version="f1",
    market_type=MarketType.SPOT,
):
    return build_opportunity_identity(
        family_id=family_id,
        family_version=family_version,
        instrument_id=instrument_id,
        market_type=market_type,
        candidate_id=candidate_id,
    )


def _evidence(
    opportunity,
    *,
    revision=1,
    supersedes=None,
    source_identity="okx-ws-bbo",
    source_type=EvidenceSource.HISTORICAL_REPLAY,
    reference_status=ReferenceDataStatus.OK,
    reference_bid=99.0,
    reference_ask=100.0,
    reference_received_at=START,
):
    return build_evidence_revision(
        opportunity=opportunity,
        evidence_revision=revision,
        detected_at=START,
        evidence_at=START + timedelta(seconds=1),
        expires_at=START + timedelta(minutes=5),
        source_type=source_type,
        source_identity=source_identity,
        source_manifest_id="manifest-1",
        reference_data_status=reference_status,
        reference_bid=reference_bid,
        reference_ask=reference_ask,
        reference_received_at=reference_received_at,
        evidence_payload={"setup": "breakout"},
        feature_snapshot_payload={"retest": True, "level": 99.5},
        supersedes_evidence_id=supersedes,
        created_at=START,
    )


def _outcome(
    opportunity,
    evidence,
    *,
    revision=1,
    supersedes=None,
    horizon=ForwardHorizon.M5,
    source_identity="okx-ws-bbo",
    source_type=EvidenceSource.HISTORICAL_REPLAY,
    calculator_version="calc-v1",
    calculation_status=OutcomeCalculationStatus.COMPLETE,
    lifecycle=None,
    due_at=None,
    completeness_diagnostics=None,
    cost_adjusted_forward_return=None,
    reference_return=None,
    executable_long_return=None,
    mfe=None,
    mae=None,
):
    if due_at is None:
        due_at = forward_due_at(evidence.evidence_at, horizon)
    return build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=evidence.evidence_id,
        horizon=horizon,
        outcome_revision=revision,
        due_at=due_at,
        source_type=source_type,
        source_identity=source_identity,
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version=calculator_version,
        calculation_status=calculation_status,
        opportunity_lifecycle_at_horizon=lifecycle,
        reference_price=99.5,
        end_bid=100.5,
        end_ask=100.6,
        mfe=mfe,
        mae=mae,
        reference_return=reference_return,
        executable_long_return=executable_long_return,
        cost_adjusted_forward_return=cost_adjusted_forward_return,
        created_at=START,
        supersedes_outcome_id=supersedes,
        completeness_diagnostics=completeness_diagnostics,
    )


def _evidence_row(**overrides) -> EdgeOpportunityEvidenceRecord:
    values = {
        "evidence_id": "e" * 64,
        "opportunity_id": "o" * 64,
        "candidate_id": "sc_raw",
        "family_id": "BREAKOUT_RETEST",
        "family_version": "f1",
        "instrument_id": INSTRUMENT,
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
        "calculation_status": "COMPLETE",
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


def _now() -> datetime:
    return datetime.now(UTC)


# === Focused pure tests (task section 28) =================================================


def test_evidence_rev1_only_canonical():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    folds = _fold_evidence_chains({opp.opportunity_id: [ev1]})
    fold = folds[opp.opportunity_id]
    assert fold.canonical.evidence_revision == 1
    assert fold.folded == ()


def test_evidence_rev1_to_rev3_canonical_rev3():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    ev3 = _evidence(opp, revision=3, supersedes=ev2.evidence_id)
    fold = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2, ev3]})[opp.opportunity_id]
    assert fold.canonical.evidence_revision == 3


def test_evidence_lower_revisions_folded():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    ev3 = _evidence(opp, revision=3, supersedes=ev2.evidence_id)
    fold = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2, ev3]})[opp.opportunity_id]
    assert [r.evidence_revision for r in fold.folded] == [1, 2]
    assert fold.folded[0].evidence_id == ev1.evidence_id
    assert fold.folded[1].evidence_id == ev2.evidence_id


def test_evidence_revision_gap_fails_closed():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev3 = _evidence(opp, revision=3, supersedes=ev1.evidence_id)
    with pytest.raises(SnapshotIntegrityError):
        _fold_evidence_chains({opp.opportunity_id: [ev1, ev3]})


def test_evidence_wrong_supersedes_fails_closed():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes="deadbeef" * 8)
    with pytest.raises(SnapshotIntegrityError):
        _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})


def test_evidence_rev1_supersedes_non_null_fails_closed():
    row = _evidence_row(evidence_revision=1, supersedes_evidence_id="x" * 64)
    with pytest.raises(SnapshotIntegrityError):
        _evidence_from_record(row)


def test_evidence_logical_fact_mutation_fails_closed():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    opp_mutated = _opportunity(family_version="f2")
    ev2 = _evidence(opp_mutated, revision=2, supersedes=ev1.evidence_id)
    with pytest.raises(SnapshotIntegrityError):
        _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})


def test_revision_mutable_source_head_only_determines_population_key():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1, source_identity="source-A")
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id, source_identity="source-B")
    folds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    proj = _project(folds, {}, ForwardHorizon.M5, _now())
    assert len(proj.facts) == 1
    assert proj.facts[0].evidence_revision == 2
    assert proj.facts[0].population_key.source_identity == "source-B"


def test_superseded_revision_cannot_remain_in_old_population_key():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1, source_identity="source-A")
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id, source_identity="source-B")
    folds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    proj = _project(folds, {}, ForwardHorizon.M5, _now())
    assert all(f.population_key.source_identity == "source-B" for f in proj.facts)
    assert len(proj.facts) == 1


def test_outcome_rev1_only_canonical():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    fold = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1]})[
        (opp.opportunity_id, ev.evidence_id)
    ]
    assert fold.canonical.outcome_revision == 1
    assert fold.folded == ()


def test_outcome_rev1_to_rev2_canonical_rev2():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id)
    fold = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})[
        (opp.opportunity_id, ev.evidence_id)
    ]
    assert fold.canonical.outcome_revision == 2


def test_outcome_revision_gap_fails_closed():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o3 = _outcome(opp, ev, revision=3, supersedes=o1.outcome_id)
    with pytest.raises(SnapshotIntegrityError):
        _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o3]})


def test_outcome_wrong_supersedes_fails_closed():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o2 = _outcome(opp, ev, revision=2, supersedes="deadbeef" * 8)
    with pytest.raises(SnapshotIntegrityError):
        _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})


def test_outcome_wrong_exact_scope_fails_closed():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    o1 = _outcome(opp, ev1, revision=1)
    o2 = _outcome(opp, ev2, revision=2, supersedes=o1.outcome_id)
    with pytest.raises(SnapshotIntegrityError):
        _fold_outcome_chains({(opp.opportunity_id, ev1.evidence_id): [o1, o2]})


def test_no_outcome_explicit_no_outcome():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    folds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    proj = _project(folds, {}, ForwardHorizon.M5, _now())
    fact = proj.facts[0]
    assert fact.outcome_id is None
    assert fact.outcome_revision is None
    assert fact.measurement_signature is None
    assert proj.manifest[0]["no_outcome"] is True


def test_folded_evidence_outcomes_excluded_not_in_economic_facts():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    o_folded = _outcome(opp, ev1, revision=1)
    o_canon = _outcome(opp, ev2, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    ofolds = _fold_outcome_chains(
        {
            (opp.opportunity_id, ev1.evidence_id): [o_folded],
            (opp.opportunity_id, ev2.evidence_id): [o_canon],
        }
    )
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    fact = proj.facts[0]
    assert fact.outcome_id == o_canon.outcome_id
    assert fact.outcomes_excluded_with_folded_evidence == 1
    assert all(e["outcome_id"] != o_folded.outcome_id for e in proj.manifest)
    assert all(
        o["outcome_id"] != o_folded.outcome_id
        for e in proj.manifest
        for o in e["outcome_revision_identities"]
    )


def test_outcomes_excluded_with_folded_evidence_count_correct():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    o_folded_1 = _outcome(opp, ev1, revision=1)
    o_folded_2 = _outcome(opp, ev1, revision=2, supersedes=o_folded_1.outcome_id)
    o_canon = _outcome(opp, ev2, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    ofolds = _fold_outcome_chains(
        {
            (opp.opportunity_id, ev1.evidence_id): [o_folded_1, o_folded_2],
            (opp.opportunity_id, ev2.evidence_id): [o_canon],
        }
    )
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    # folded evidence ev1 has 2 outcome revisions (1 canonical + 1 folded) -> 2 excluded
    assert proj.facts[0].outcomes_excluded_with_folded_evidence == 2


def test_folded_outcome_count_correct():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    assert proj.facts[0].folded_outcome_revision_count == 1


def test_evidence_hash_corruption_fails_closed():
    row = _evidence_row(evidence_hash="h" * 63 + "x")
    with pytest.raises(SnapshotIntegrityError):
        _evidence_from_record(row)


def test_outcome_hash_corruption_fails_closed():
    row = _outcome_row(outcome_record_hash="r" * 63 + "x")
    with pytest.raises(SnapshotIntegrityError):
        _outcome_from_record(row)


def test_evidence_outcome_source_mismatch_fails_closed():
    opp = _opportunity()
    ev = _evidence(opp, revision=1, source_identity="source-A")
    o = _outcome(opp, ev, revision=1, source_identity="source-B")
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o]})
    with pytest.raises(SnapshotIntegrityError):
        _project(efolds, ofolds, ForwardHorizon.M5, _now())


def test_outcome_due_at_mismatch_fails_closed():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o = _outcome(opp, ev, revision=1, due_at=ev.evidence_at + timedelta(days=1))
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o]})
    with pytest.raises(SnapshotIntegrityError):
        _project(efolds, ofolds, ForwardHorizon.M5, _now())


def test_measurement_signature_uses_canonical_outcome_only():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1, calculator_version="calc-v1")
    o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id, calculator_version="calc-v2")
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    assert proj.facts[0].measurement_signature is not None
    assert proj.facts[0].measurement_signature.calculator_version == "calc-v2"


def test_reason_comes_from_accepted_completeness_diagnostics():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o = _outcome(
        opp,
        ev,
        revision=1,
        calculation_status=OutcomeCalculationStatus.INSUFFICIENT_DATA,
        completeness_diagnostics={"reason": "REFERENCE_MISSING"},
    )
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    assert proj.facts[0].outcome_reason == "REFERENCE_MISSING"


def test_deterministic_manifest_ordering():
    opp_a = _opportunity(candidate_id="sc_a")
    opp_b = _opportunity(candidate_id="sc_b")
    opp_c = _opportunity(candidate_id="sc_c")
    ev_a = _evidence(opp_a, revision=1)
    ev_b = _evidence(opp_b, revision=1)
    ev_c = _evidence(opp_c, revision=1)
    efolds = _fold_evidence_chains(
        {
            opp_a.opportunity_id: [ev_a],
            opp_b.opportunity_id: [ev_b],
            opp_c.opportunity_id: [ev_c],
        }
    )
    proj = _project(efolds, {}, ForwardHorizon.M5, _now())
    keys = [(e["opportunity_id"], e["evidence_id"], e["horizon"]) for e in proj.manifest]
    assert keys == sorted(keys)


def test_manifest_includes_all_evidence_revision_identities():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    proj = _project(efolds, {}, ForwardHorizon.M5, _now())
    identities = proj.manifest[0]["evidence_revision_identities"]
    assert len(identities) == 2
    assert [i["evidence_revision"] for i in identities] == [1, 2]
    assert {i["role"] for i in identities} == {"CANONICAL", "FOLDED_EVIDENCE"}


def test_manifest_includes_all_exact_outcome_revision_identities():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())
    identities = proj.manifest[0]["outcome_revision_identities"]
    assert len(identities) == 2
    assert [i["outcome_revision"] for i in identities] == [1, 2]
    assert {i["role"] for i in identities} == {"CANONICAL", "FOLDED_OUTCOME"}


def test_manifest_population_key_and_horizon_present():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    proj = _project(efolds, {}, ForwardHorizon.M5, _now())
    entry = proj.manifest[0]
    assert "population_key" in entry
    assert entry["population_key"]["instrument_id"] == INSTRUMENT
    assert entry["horizon"] == "5m"


def test_input_permutation_cannot_change_projection():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    efolds_forward = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    efolds_shuffled = _fold_evidence_chains({opp.opportunity_id: [ev2, ev1]})
    proj_forward = _project(efolds_forward, {}, ForwardHorizon.M5, _now())
    proj_shuffled = _project(efolds_shuffled, {}, ForwardHorizon.M5, _now())
    assert canonical_bytes(proj_forward.manifest) == canonical_bytes(proj_shuffled.manifest)


def test_no_historical_as_of_interface():
    sig = inspect.signature(CurrentSnapshotRevisionReader.read)
    assert "as_of" not in sig.parameters
    assert sig.parameters["horizon"].annotation is not inspect.Parameter.empty


# === FIX-01 R1: complete Evidence <-> Outcome cross-integrity =============================


def test_evidence_outcome_source_type_mismatch_fails_closed():
    """A matching ``source_identity`` must not hide a ``source_type`` mismatch."""

    opp = _opportunity()
    ev = _evidence(
        opp,
        revision=1,
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="same-source",
    )
    o = _outcome(
        opp,
        ev,
        revision=1,
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="same-source",
    )
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o]})
    with pytest.raises(SnapshotIntegrityError):
        _project(efolds, ofolds, ForwardHorizon.M5, _now())


def test_cross_integrity_checks_every_link_field_fail_closed():
    """Each of the six cross-integrity links fails closed on its own mismatch."""

    opp = _opportunity()
    other_opp = _opportunity(candidate_id="sc_other")
    ev = _evidence(opp, revision=1)
    other_ev = _evidence(other_opp, revision=1)

    # matching link -> silent
    _check_cross_integrity(ev, _outcome(opp, ev, revision=1), horizon=ForwardHorizon.M5)

    mismatch = (
        ("opportunity_id", _outcome(other_opp, ev, revision=1)),
        ("evidence_id", _outcome(opp, other_ev, revision=1)),
        ("horizon", _outcome(opp, ev, revision=1, horizon=ForwardHorizon.M15)),
        ("source_type", _outcome(opp, ev, revision=1, source_type=EvidenceSource.FORWARD_PAPER)),
        ("source_identity", _outcome(opp, ev, revision=1, source_identity="other-source")),
        ("due_at", _outcome(opp, ev, revision=1, due_at=ev.evidence_at + timedelta(days=1))),
    )
    for _link, bad_outcome in mismatch:
        with pytest.raises(SnapshotIntegrityError):
            _check_cross_integrity(ev, bad_outcome, horizon=ForwardHorizon.M5)

    # NO_OUTCOME stays a no-op
    _check_cross_integrity(ev, None, horizon=ForwardHorizon.M5)


# === FIX-01 R2: I01 canonical manifest authority + revision identities ====================


def test_i02_manifest_preserves_every_i01_base_key_and_value():
    """I02 may ADD revision-aware fields; it may never drop or alter I01 fields."""

    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    o2 = _outcome(opp, ev2, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev2.evidence_id): [o2]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())

    base = build_ordered_input_manifest(proj.facts, as_of=proj.as_of)
    assert len(base) == len(proj.manifest)
    for base_entry, i02_entry in zip(base, proj.manifest, strict=True):
        for key, value in base_entry.items():
            assert i02_entry[key] == value

    # the I02-only extension is present on the same entry
    entry = proj.manifest[0]
    assert entry["no_outcome"] is False
    assert entry["evidence_revision_identities"]
    assert entry["outcome_revision_identities"]


def test_i02_manifest_evidence_revision_identities_carry_identity_fields():
    opp = _opportunity()
    ev1 = _evidence(opp, revision=1)
    ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev1, ev2]})
    proj = _project(efolds, {}, ForwardHorizon.M5, _now())

    identities = proj.manifest[0]["evidence_revision_identities"]
    assert [i["evidence_revision"] for i in identities] == [1, 2]
    assert [i["evidence_id"] for i in identities] == [ev1.evidence_id, ev2.evidence_id]
    assert [i["evidence_hash"] for i in identities] == [ev1.evidence_hash, ev2.evidence_hash]
    assert [i["role"] for i in identities] == ["FOLDED_EVIDENCE", "CANONICAL"]


def test_i02_manifest_outcome_revision_identities_carry_identity_fields():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o1 = _outcome(opp, ev, revision=1)
    o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o1, o2]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())

    identities = proj.manifest[0]["outcome_revision_identities"]
    assert [i["outcome_revision"] for i in identities] == [1, 2]
    assert [i["outcome_id"] for i in identities] == [o1.outcome_id, o2.outcome_id]
    assert [i["outcome_record_hash"] for i in identities] == [
        o1.outcome_record_hash,
        o2.outcome_record_hash,
    ]
    assert [i["role"] for i in identities] == ["FOLDED_OUTCOME", "CANONICAL"]


def test_i02_manifest_no_outcome_preserves_i01_no_measurement():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    proj = _project(efolds, {}, ForwardHorizon.M5, _now())

    entry = proj.manifest[0]
    assert entry["outcome_id"] is None
    assert entry["outcome_revision"] is None
    assert entry["outcome_record_hash"] is None
    assert entry["measurement_signature"] == NO_MEASUREMENT
    assert entry["maturity_marker"] in ("NOT_YET_DUE", "MISSING_OUTCOME")
    assert entry["outcome_revision_identities"] == []


def test_i02_manifest_complete_numeric_hex_bindings_match_i01():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    o = _outcome(
        opp,
        ev,
        revision=1,
        cost_adjusted_forward_return=0.0123,
        reference_return=0.01,
        executable_long_return=0.0099,
        mfe=0.02,
        mae=-0.005,
    )
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    ofolds = _fold_outcome_chains({(opp.opportunity_id, ev.evidence_id): [o]})
    proj = _project(efolds, ofolds, ForwardHorizon.M5, _now())

    base = build_ordered_input_manifest(proj.facts, as_of=proj.as_of)
    entry = proj.manifest[0]
    for key in (
        "cost_adjusted_forward_return_hex",
        "reference_return_hex",
        "executable_long_return_hex",
        "mfe_hex",
        "mae_hex",
    ):
        assert entry[key] is not None
        assert entry[key] == base[0][key]
    assert entry["cost_adjusted_forward_return_hex"] == 0.0123.hex()
    assert entry["integrity_conflicts"] == []


# === FIX-01 R3: explicit projection horizon ===============================================


def test_projection_carries_requested_horizon():
    opp = _opportunity()
    ev = _evidence(opp, revision=1)
    efolds = _fold_evidence_chains({opp.opportunity_id: [ev]})
    proj = _project(efolds, {}, ForwardHorizon.M15, _now())
    assert proj.horizon == ForwardHorizon.M15
    assert proj.facts[0].horizon == ForwardHorizon.M15


# === PostgreSQL MVCC tests (task section 29) ==============================================


def test_snapshot_a_transaction_ordering():
    with _se02d_database("snap_a") as url:
        captured = asyncio.run(_snapshot_a_run(url))
    set_idx = next(
        i
        for i, s in enumerate(captured)
        if "SET TRANSACTION" in s.upper()
        and "REPEATABLE READ" in s.upper()
        and "READ ONLY" in s.upper()
    )
    first_select_idx = next(
        i for i, s in enumerate(captured) if s.strip().upper().startswith("SELECT")
    )
    stmt_ts_idx = next(i for i, s in enumerate(captured) if "statement_timestamp()" in s)
    assert set_idx < first_select_idx
    assert stmt_ts_idx == first_select_idx


async def _snapshot_a_run(url: str) -> list[str]:
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    captured: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        captured.append(statement)

    event.listen(engine.sync_engine, "after_cursor_execute", _record)
    async with factory() as session:
        await append_evidence_revision(session, _evidence(_opportunity()))
        await session.commit()
    captured.clear()
    reader = CurrentSnapshotRevisionReader(factory)
    await reader.read(ForwardHorizon.M5)
    await engine.dispose()
    return captured


def test_snapshot_b_late_evidence_correction():
    with _se02d_database("snap_b") as url:
        established, fresh = asyncio.run(_snapshot_b_run(url))
    assert established == (1, 0)
    assert fresh == (2, 1)


async def _snapshot_b_run(url: str):
    async with _sessions(url) as factory:
        opp = _opportunity()
        ev1 = _evidence(opp, revision=1)
        ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id)
        async with factory() as session:
            await append_evidence_revision(session, ev1)
            await session.commit()
        reader = CurrentSnapshotRevisionReader(factory)
        session = factory()
        await session.begin()
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        as_of = (await session.scalar(text("SELECT statement_timestamp()"))).astimezone(UTC)
        async with factory() as writer:
            await append_evidence_revision(writer, ev2)
            await writer.commit()
        proj = await reader._read_in_session(session, ForwardHorizon.M5, as_of)
        established = (proj.facts[0].evidence_revision, proj.facts[0].folded_evidence_revision_count)
        await session.rollback()
        await session.close()
        fresh = await reader.read(ForwardHorizon.M5)
        fresh_rev = fresh.facts[0].evidence_revision
        fresh_folded = fresh.facts[0].folded_evidence_revision_count
        return established, (fresh_rev, fresh_folded)


def test_snapshot_c_late_outcome_correction():
    with _se02d_database("snap_c") as url:
        established, fresh = asyncio.run(_snapshot_c_run(url))
    # established snapshot (rev1 visible at snapshot, rev2 committed after) -> still sees rev1
    assert established[0] == 1
    # fresh reader -> sees rev2
    assert fresh[0] == 2
    assert fresh[1] is not None


async def _snapshot_c_run(url: str):
    async with _sessions(url) as factory:
        opp = _opportunity()
        ev = _evidence(opp, revision=1)
        o1 = _outcome(opp, ev, revision=1)
        o2 = _outcome(opp, ev, revision=2, supersedes=o1.outcome_id)
        async with factory() as session:
            await append_evidence_revision(session, ev)
            await append_forward_outcome(session, o1)
            await session.commit()
        reader = CurrentSnapshotRevisionReader(factory)
        session = factory()
        await session.begin()
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        as_of = (await session.scalar(text("SELECT statement_timestamp()"))).astimezone(UTC)
        async with factory() as writer:
            await append_forward_outcome(writer, o2)
            await writer.commit()
        proj = await reader._read_in_session(session, ForwardHorizon.M5, as_of)
        established = (proj.facts[0].outcome_revision, proj.facts[0].outcome_id)
        await session.rollback()
        await session.close()
        fresh = await reader.read(ForwardHorizon.M5)
        fresh_out = (fresh.facts[0].outcome_revision, fresh.facts[0].outcome_id)
        return established, fresh_out


def test_snapshot_d_as_of_is_database_statement_time():
    with _se02d_database("snap_d") as url:
        proj, fresh_ts = asyncio.run(_snapshot_d_run(url))
    assert proj.as_of.tzinfo is not None
    assert proj.as_of.utcoffset() == timedelta(0)
    assert abs((fresh_ts - proj.as_of).total_seconds()) < 2.0
    assert proj.manifest[0]["maturity_marker"] in ("NOT_YET_DUE", "MISSING_OUTCOME")


async def _snapshot_d_run(url: str):
    async with _sessions(url) as factory:
        opp = _opportunity()
        ev = _evidence(opp, revision=1)
        async with factory() as session:
            await append_evidence_revision(session, ev)
            await session.commit()
        reader = CurrentSnapshotRevisionReader(factory)
        proj = await reader.read(ForwardHorizon.M5)
        async with factory() as session:
            fresh_ts = (await session.scalar(text("SELECT statement_timestamp()"))).astimezone(UTC)
        return proj, fresh_ts


# === Regression: query-time revision filtering must not resurrect old populations =====


def test_no_query_time_revision_filtering_resurrects_old_population():
    with _se02d_database("snap_reg") as url:
        proj = asyncio.run(_regression_run(url))
    assert len(proj.facts) == 1
    assert proj.facts[0].population_key.source_identity == "source-B"
    assert proj.facts[0].evidence_revision == 2


async def _regression_run(url: str):
    async with _sessions(url) as factory:
        opp = _opportunity()
        ev1 = _evidence(opp, revision=1, source_identity="source-A")
        ev2 = _evidence(opp, revision=2, supersedes=ev1.evidence_id, source_identity="source-B")
        async with factory() as session:
            await append_evidence_revision(session, ev1)
            await append_evidence_revision(session, ev2)
            await session.commit()
        reader = CurrentSnapshotRevisionReader(factory)
        proj = await reader.read(ForwardHorizon.M5)
        return proj


# === FIX-01 R3: empty snapshot still carries the requested horizon =======================


def test_empty_snapshot_projection_carries_requested_horizon():
    """The horizon is a property of the request, not of the presence of facts."""

    with _se02d_database("empty_projection") as url:
        proj = asyncio.run(_empty_projection_run(url))
    assert proj.horizon == ForwardHorizon.M5
    assert proj.facts == ()
    assert proj.manifest == ()


async def _empty_projection_run(url: str):
    async with _sessions(url) as factory:
        reader = CurrentSnapshotRevisionReader(factory)
        return await reader.read(ForwardHorizon.M5)
