"""SE-02D-I03 population grouping + aggregate orchestration -- focused tests.

Scope (task section 17): the orchestration seam between I02's
``CurrentSnapshotProjection`` and I01's ``aggregate()``. Nothing here re-tests
I01 statistics or I02 folding; this module proves only that

* the projection is validated as one unit before anything is aggregated;
* the complete structural ``PopulationKey`` is the only grouping identity;
* exactly one I01 ``aggregate()`` call happens per population;
* I02's revision-aware manifest -- not a re-derived one -- reaches I01;
* the ordering and the async wrapper are deterministic.

Projections are built through I02's own projection path (``_project``) with real
Accepted contracts, so the orchestrator is exercised against genuine I02 output
rather than a hand-rolled imitation of it. The fail-closed cases then tamper with
that output, because I02 by construction can never emit an inconsistent
projection.
"""

import ast
import asyncio
import dataclasses
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from marketpulse.edge import aggregation as aggregation_module
from marketpulse.edge import aggregation_orchestration as orchestration
from marketpulse.edge.aggregation import (
    AggregateStatus,
    AggregationError,
    CanonicalScopeFacts,
    MeasurementSignatureState,
    PopulationKey,
    build_ordered_input_manifest,
)
from marketpulse.edge.aggregation_orchestration import (
    AggregationOrchestrationError,
    aggregate_current_snapshot,
    aggregate_projection,
)
from marketpulse.edge.aggregation_snapshot import (
    CurrentSnapshotProjection,
    SnapshotIntegrityError,
    _fold_evidence_chains,
    _fold_outcome_chains,
    _project,
)
from marketpulse.edge.forward import forward_due_at
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ForwardHorizon,
    ForwardOutcomeContract,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.market_data.models import MarketType

T0 = datetime(2026, 9, 15, 0, 0, tzinfo=UTC)
AS_OF = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
HORIZON = ForwardHorizon.M5
INSTRUMENT = "BTC-USDT"
SOURCE_IDENTITY = "okx-ws-bbo"
MANIFEST_A = "manifest-a"
MANIFEST_B = "manifest-b"

ORCHESTRATION_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "marketpulse"
    / "edge"
    / "aggregation_orchestration.py"
)


# --- contract builders (SE-02A / SE-02C shape) ---------------------------------------------


def _opportunity(
    *,
    candidate_id: str,
    instrument_id: str = INSTRUMENT,
    market_type: MarketType = MarketType.SPOT,
    family_version: str = "f1",
):
    return build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=family_version,
        instrument_id=instrument_id,
        market_type=market_type,
        candidate_id=candidate_id,
    )


def _evidence(
    opportunity,
    *,
    revision: int = 1,
    supersedes: str | None = None,
    source_identity: str = SOURCE_IDENTITY,
    source_manifest_id: str = MANIFEST_A,
    evidence_offset_minutes: int = 0,
) -> EvidenceRevision:
    evidence_at = T0 + timedelta(minutes=evidence_offset_minutes)
    return build_evidence_revision(
        opportunity=opportunity,
        evidence_revision=revision,
        detected_at=evidence_at,
        evidence_at=evidence_at,
        expires_at=evidence_at + timedelta(minutes=5),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity=source_identity,
        source_manifest_id=source_manifest_id,
        reference_data_status=ReferenceDataStatus.OK,
        reference_bid=99.0,
        reference_ask=100.0,
        reference_received_at=evidence_at,
        evidence_payload={"setup": "breakout"},
        feature_snapshot_payload={"retest": True, "level": 99.5},
        supersedes_evidence_id=supersedes,
        created_at=evidence_at,
    )


def _outcome(
    opportunity,
    evidence: EvidenceRevision,
    *,
    revision: int = 1,
    supersedes: str | None = None,
    horizon: ForwardHorizon = HORIZON,
    source_identity: str = SOURCE_IDENTITY,
    calculator_version: str = "calc-v1",
    cost_model_version: str = "cost-v1",
    cost_adjusted_forward_return: float = 0.01,
) -> ForwardOutcomeContract:
    return build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=evidence.evidence_id,
        horizon=horizon,
        outcome_revision=revision,
        due_at=forward_due_at(evidence.evidence_at, horizon),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity=source_identity,
        cost_policy="SPOT_LONG_TAKER_ROUND_TRIP",
        cost_model_version=cost_model_version,
        calculator_version=calculator_version,
        calculation_status=OutcomeCalculationStatus.COMPLETE,
        opportunity_lifecycle_at_horizon=OpportunityLifecycleAtHorizon.ACTIVE,
        reference_price=99.5,
        end_bid=100.5,
        end_ask=100.6,
        mfe=0.02,
        mae=-0.005,
        reference_return=0.009,
        executable_long_return=0.008,
        cost_adjusted_forward_return=cost_adjusted_forward_return,
        completeness_diagnostics={"reason": "COMPLETE"},
        supersedes_outcome_id=supersedes,
        created_at=evidence.evidence_at,
    )


def _projection(
    *samples: dict[str, Any],
    horizon: ForwardHorizon = HORIZON,
    as_of: datetime = AS_OF,
) -> CurrentSnapshotProjection:
    """Build one genuine I02 projection from compact sample specifications."""

    evidence_chains: dict[str, list[EvidenceRevision]] = {}
    outcome_chains: dict[tuple[str, str], list[ForwardOutcomeContract]] = {}

    for position, sample in enumerate(samples):
        opportunity = _opportunity(
            candidate_id=sample.get("candidate_id", f"sc-{position}"),
            instrument_id=sample.get("instrument_id", INSTRUMENT),
            market_type=sample.get("market_type", MarketType.SPOT),
            family_version=sample.get("family_version", "f1"),
        )
        revisions: list[EvidenceRevision] = []
        previous_evidence: str | None = None
        for revision in range(1, sample.get("evidence_revision_count", 1) + 1):
            evidence = _evidence(
                opportunity,
                revision=revision,
                supersedes=previous_evidence,
                source_identity=sample.get("source_identity", SOURCE_IDENTITY),
                source_manifest_id=sample.get("source_manifest_id", MANIFEST_A),
                evidence_offset_minutes=sample.get("evidence_offset_minutes", position * 10),
            )
            revisions.append(evidence)
            previous_evidence = evidence.evidence_id
        evidence_chains[opportunity.opportunity_id] = revisions

        if sample.get("with_outcome", True):
            canonical_evidence = revisions[-1]
            contracts: list[ForwardOutcomeContract] = []
            previous_outcome: str | None = None
            for revision, overrides in enumerate(
                sample.get("outcome_revisions") or [{}], start=1
            ):
                contract = _outcome(
                    opportunity,
                    canonical_evidence,
                    revision=revision,
                    supersedes=previous_outcome,
                    horizon=horizon,
                    **overrides,
                )
                contracts.append(contract)
                previous_outcome = contract.outcome_id
            outcome_chains[
                (opportunity.opportunity_id, canonical_evidence.evidence_id)
            ] = contracts

    return _project(
        _fold_evidence_chains(evidence_chains),
        _fold_outcome_chains(outcome_chains),
        horizon,
        as_of,
    )


def _three_populations() -> CurrentSnapshotProjection:
    """One projection holding three structural populations of size 3 / 2 / 1."""

    return _projection(
        {"candidate_id": "btc-1", "instrument_id": "BTC-USDT"},
        {"candidate_id": "btc-2", "instrument_id": "BTC-USDT"},
        {"candidate_id": "btc-3", "instrument_id": "BTC-USDT"},
        {"candidate_id": "eth-1", "instrument_id": "ETH-USDT"},
        {"candidate_id": "eth-2", "instrument_id": "ETH-USDT"},
        {"candidate_id": "sol-1", "instrument_id": "SOL-USDT"},
    )


def _spy_on_aggregate(monkeypatch) -> list[dict[str, Any]]:
    """Record every I01 invocation while still delegating to the real I01."""

    calls: list[dict[str, Any]] = []
    real_aggregate = aggregation_module.aggregate

    def _record(**kwargs):
        calls.append(kwargs)
        return real_aggregate(**kwargs)

    monkeypatch.setattr(orchestration, "aggregate", _record)
    return calls


def _tampered(
    projection: CurrentSnapshotProjection, **overrides: Any
) -> CurrentSnapshotProjection:
    return dataclasses.replace(projection, **overrides)


# === A. empty projection ====================================================================


def test_empty_projection_returns_empty_tuple_and_never_calls_aggregate(monkeypatch):
    projection = CurrentSnapshotProjection(
        as_of=AS_OF, horizon=HORIZON, facts=(), manifest=()
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert results == ()
    assert calls == []
    # The empty projection is still authoritative about its own clock / horizon.
    assert projection.horizon is HORIZON
    assert projection.as_of == AS_OF


# === B. one population ======================================================================


def test_one_population_makes_exactly_one_i01_call(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "evidence_offset_minutes": 0},
        {"candidate_id": "b", "evidence_offset_minutes": 30},
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(results) == 1
    assert len(calls) == 1
    assert isinstance(results[0], aggregation_module.AggregationResult)
    assert isinstance(results, tuple)


def test_one_population_preserves_identity_horizon_and_as_of(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "evidence_offset_minutes": 0},
        {"candidate_id": "b", "evidence_offset_minutes": 30},
    )
    calls = _spy_on_aggregate(monkeypatch)

    result = aggregate_projection(projection)[0]
    expected_key = projection.facts[0].population_key

    assert result.population_key == expected_key
    assert result.identity.population_key == expected_key
    assert result.horizon is HORIZON
    assert result.as_of == projection.as_of
    assert calls[0]["population_key"] == expected_key
    assert calls[0]["horizon"] is HORIZON
    assert calls[0]["as_of"] == projection.as_of


def test_revision_aware_manifest_is_supplied_to_i01_not_rebuilt(monkeypatch):
    projection = _projection({"candidate_id": "a"})
    calls = _spy_on_aggregate(monkeypatch)

    result = aggregate_projection(projection)[0]

    # I03 must pass a manifest, never let I01 fall back to its own builder.
    assert len(calls) == 1
    supplied = calls[0]["ordered_input_manifest"]
    assert supplied is not None
    assert result.input_manifest == tuple(dict(entry) for entry in supplied)

    entry = result.input_manifest[0]
    assert entry["no_outcome"] is False
    assert entry["evidence_revision_identities"] == [
        {
            "evidence_id": projection.facts[0].evidence_id,
            "evidence_revision": 1,
            "evidence_hash": projection.facts[0].evidence_hash,
            "role": "CANONICAL",
        }
    ]
    assert entry["outcome_revision_identities"][0]["role"] == "CANONICAL"
    assert entry["outcome_revision_identities"][0]["outcome_id"] == (
        projection.facts[0].outcome_id
    )
    # The accepted I01 base fields survive alongside the I02 extension.
    assert entry["population_key"] == projection.facts[0].population_key.canonical_payload()
    assert entry["source_manifest_id"] == projection.facts[0].source_manifest_id
    assert entry["cost_adjusted_forward_return_hex"] is not None

    # Counter-proof: the revision-aware manifest is *not* the I01 base manifest.
    assert result.input_manifest != build_ordered_input_manifest(
        projection.facts, as_of=projection.as_of
    )


def test_manifest_subset_is_ordered_by_logical_identity(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "evidence_offset_minutes": 0},
        {"candidate_id": "b", "evidence_offset_minutes": 30},
        {"candidate_id": "c", "evidence_offset_minutes": 60},
    )
    calls = _spy_on_aggregate(monkeypatch)

    aggregate_projection(projection)

    ordered = calls[0]["ordered_input_manifest"]
    keys = [(e["opportunity_id"], e["evidence_id"], e["horizon"]) for e in ordered]
    assert keys == sorted(keys)
    assert {e["horizon"] for e in ordered} == {HORIZON.value}


# === C. multiple populations ================================================================


def test_exactly_one_i01_call_per_structural_population_key(monkeypatch):
    projection = _three_populations()
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(projection.facts) == 6
    assert len(calls) == 3
    assert len(results) == 3
    for call in calls:
        assert isinstance(call["population_key"], PopulationKey)
        assert {fact.population_key for fact in call["facts"]} == {call["population_key"]}
    sizes = sorted(len(call["facts"]) for call in calls)
    assert sizes == [1, 2, 3]


def test_multi_population_results_are_ordered_by_canonical_key(monkeypatch):
    projection = _three_populations()
    _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)
    keys = [result.population_key for result in results]

    assert len(set(keys)) == 3
    assert [key.canonical_key() for key in keys] == sorted(key.canonical_key() for key in keys)
    assert {key.instrument_id for key in keys} == {"BTC-USDT", "ETH-USDT", "SOL-USDT"}


# === D. source_manifest_id does not split a population ======================================


def test_source_manifest_id_does_not_split_population(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "source_manifest_id": MANIFEST_A, "evidence_offset_minutes": 0},
        {"candidate_id": "b", "source_manifest_id": MANIFEST_B, "evidence_offset_minutes": 30},
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len({fact.population_key for fact in projection.facts}) == 1
    assert {fact.source_manifest_id for fact in projection.facts} == {MANIFEST_A, MANIFEST_B}
    assert len(calls) == 1
    assert len(results) == 1
    assert {fact.source_manifest_id for fact in calls[0]["facts"]} == {MANIFEST_A, MANIFEST_B}
    assert results[0].manifest.manifest_count == 2
    assert results[0].manifest.ordered_manifest_ids == (MANIFEST_A, MANIFEST_B)


# === E. mixed Measurement Signature stays one invocation ====================================


def test_mixed_measurement_signature_does_not_split_population(monkeypatch):
    projection = _projection(
        {
            "candidate_id": "a",
            "evidence_offset_minutes": 0,
            "outcome_revisions": [{"calculator_version": "calc-v1"}],
        },
        {
            "candidate_id": "b",
            "evidence_offset_minutes": 30,
            "outcome_revisions": [{"calculator_version": "calc-v2"}],
        },
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(calls) == 1
    assert len(results) == 1
    assert (
        len({fact.measurement_signature for fact in projection.facts}) == 2
    )
    assert results[0].status is AggregateStatus.INCOMPATIBLE_MEASUREMENT_SIGNATURES
    assert results[0].measurement_signature_state is MeasurementSignatureState.MIXED


# === F. non-applicable market type is not filtered by I03 ===================================


def test_swap_population_is_not_filtered_and_reaches_i01(monkeypatch):
    projection = _projection(
        {
            "candidate_id": "a",
            "market_type": MarketType.SWAP,
            "evidence_offset_minutes": 0,
        },
        {
            "candidate_id": "b",
            "market_type": MarketType.SWAP,
            "evidence_offset_minutes": 30,
        },
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(calls) == 1
    assert len(calls[0]["facts"]) == 2
    assert len(results) == 1
    assert results[0].population_key.market_type is MarketType.SWAP
    assert results[0].status is AggregateStatus.NOT_APPLICABLE
    assert results[0].evidence_sufficient is False
    assert "MARKET_TYPE_NOT_APPLICABLE" in results[0].sufficiency_reasons


def test_spot_and_swap_populations_stay_separate(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "market_type": MarketType.SPOT, "evidence_offset_minutes": 0},
        {"candidate_id": "b", "market_type": MarketType.SWAP, "evidence_offset_minutes": 30},
    )
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(calls) == 2
    assert len(results) == 2
    assert {result.population_key.market_type for result in results} == {
        MarketType.SPOT,
        MarketType.SWAP,
    }


# === G / H. facts <-> manifest one-to-one correspondence ====================================


def test_fact_without_manifest_entry_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(AggregationOrchestrationError, match="fact_without_manifest_entry"):
        aggregate_projection(_tampered(projection, manifest=()))


def test_manifest_entry_without_fact_fails_closed():
    projection = _projection({"candidate_id": "a"})
    ghost = dict(projection.manifest[0])
    ghost["opportunity_id"] = "ghost-opportunity"

    with pytest.raises(AggregationOrchestrationError, match="manifest_entry_without_fact"):
        aggregate_projection(_tampered(projection, manifest=(*projection.manifest, ghost)))


def test_manifest_entry_without_any_fact_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(AggregationOrchestrationError, match="manifest_entry_without_fact"):
        aggregate_projection(
            _tampered(projection, facts=(), manifest=projection.manifest)
        )


# === I / J. duplicate logical identities ====================================================


def test_duplicate_fact_logical_identity_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(AggregationOrchestrationError, match="duplicate_fact_logical_identity"):
        aggregate_projection(
            _tampered(projection, facts=(*projection.facts, projection.facts[0]))
        )


def test_duplicate_manifest_logical_identity_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(
        AggregationOrchestrationError, match="duplicate_manifest_logical_identity"
    ):
        aggregate_projection(
            _tampered(
                projection, manifest=(*projection.manifest, dict(projection.manifest[0]))
            )
        )


def test_duplicate_identity_is_reported_deterministically():
    projection = _projection(
        {"candidate_id": "a", "evidence_offset_minutes": 0},
        {"candidate_id": "b", "evidence_offset_minutes": 30},
    )

    for duplicated in projection.facts:
        tampered = _tampered(projection, facts=(*projection.facts, duplicated))
        expected = (
            f"duplicate_fact_logical_identity:{duplicated.opportunity_id}:"
            f"{duplicated.evidence_id}:{HORIZON.value}"
        )
        with pytest.raises(AggregationOrchestrationError) as captured:
            aggregate_projection(tampered)
        assert str(captured.value) == expected


# === K / L. horizon mismatches ==============================================================


def test_fact_horizon_mismatch_fails_closed():
    projection = _projection({"candidate_id": "a"})
    fact = dataclasses.replace(projection.facts[0], horizon=ForwardHorizon.M15)

    with pytest.raises(AggregationOrchestrationError, match="fact_horizon_mismatch"):
        aggregate_projection(_tampered(projection, facts=(fact,)))


def test_manifest_horizon_mismatch_fails_closed():
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    entry["horizon"] = ForwardHorizon.M15.value

    with pytest.raises(AggregationOrchestrationError, match="manifest_horizon_mismatch"):
        aggregate_projection(_tampered(projection, manifest=(entry,)))


# === M. manifest Population Key mismatch ====================================================


def test_manifest_population_key_mismatch_fails_closed():
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    entry["population_key"] = {
        **entry["population_key"],
        "instrument_id": "ETH-USDT",
    }

    with pytest.raises(AggregationOrchestrationError, match="manifest_population_key_mismatch"):
        aggregate_projection(_tampered(projection, manifest=(entry,)))


def test_manifest_population_key_is_compared_structurally_not_by_digest():
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    # Same field values, same payload: this must NOT be treated as a mismatch.
    entry["population_key"] = dict(reversed(list(entry["population_key"].items())))

    results = aggregate_projection(_tampered(projection, manifest=(entry,)))

    assert len(results) == 1
    assert results[0].population_key == projection.facts[0].population_key


# === malformed identity fields (task section 9 rule 8) ======================================


@pytest.mark.parametrize("malformed", [None, "", 17, ["x"]])
def test_malformed_manifest_identity_field_fails_closed(malformed):
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    entry["opportunity_id"] = malformed

    with pytest.raises(AggregationOrchestrationError, match="malformed_manifest_logical_identity"):
        aggregate_projection(_tampered(projection, manifest=(entry,)))


def test_missing_manifest_identity_field_fails_closed():
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    del entry["evidence_id"]

    with pytest.raises(AggregationOrchestrationError, match="malformed_manifest_logical_identity"):
        aggregate_projection(_tampered(projection, manifest=(entry,)))


def test_non_mapping_manifest_entry_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(AggregationOrchestrationError, match="malformed_manifest_entry"):
        aggregate_projection(_tampered(projection, manifest=("not-a-mapping",)))


def test_malformed_manifest_population_key_fails_closed():
    projection = _projection({"candidate_id": "a"})
    entry = dict(projection.manifest[0])
    entry["population_key"] = "not-a-mapping"

    with pytest.raises(
        AggregationOrchestrationError, match="malformed_manifest_identity:population_key"
    ):
        aggregate_projection(_tampered(projection, manifest=(entry,)))


def test_non_canonical_scope_fact_fails_closed():
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(AggregationOrchestrationError, match="malformed_fact"):
        aggregate_projection(_tampered(projection, facts=("not-a-fact",)))


# === SE02D-I03-R1. malformed projection identity (FIX-01) ===================================


@pytest.mark.parametrize("malformed", ["5m", "M5", None, 5, []])
def test_malformed_projection_horizon_fails_closed(malformed):
    projection = _projection({"candidate_id": "a"})

    with pytest.raises(
        AggregationOrchestrationError, match="malformed_projection_identity:horizon"
    ):
        aggregate_projection(_tampered(projection, horizon=malformed))


def test_malformed_projection_horizon_fails_closed_without_any_fact():
    projection = CurrentSnapshotProjection(
        as_of=AS_OF, horizon="5m", facts=(), manifest=()
    )

    with pytest.raises(
        AggregationOrchestrationError, match="malformed_projection_identity:horizon"
    ):
        aggregate_projection(projection)


@pytest.mark.parametrize("malformed", ["5m", "M5", None, 5, []])
def test_malformed_fact_horizon_fails_closed(malformed):
    projection = _projection({"candidate_id": "a"})
    fact = dataclasses.replace(projection.facts[0], horizon=malformed)

    with pytest.raises(
        AggregationOrchestrationError, match="malformed_fact_logical_identity:horizon"
    ):
        aggregate_projection(_tampered(projection, facts=(fact,)))


@pytest.mark.parametrize("malformed", ["not-a-population-key", None, 17, ("t",)])
def test_malformed_fact_population_key_fails_closed(malformed):
    projection = _projection({"candidate_id": "a"})
    fact = dataclasses.replace(projection.facts[0], population_key=malformed)

    with pytest.raises(
        AggregationOrchestrationError, match="malformed_fact_population_key"
    ):
        aggregate_projection(_tampered(projection, facts=(fact,)))


def test_malformed_projection_identity_messages_are_exact_and_deterministic():
    projection = _projection({"candidate_id": "a"})
    fact = projection.facts[0]

    cases = (
        (
            _tampered(projection, horizon="5m"),
            "malformed_projection_identity:horizon:str",
        ),
        (
            _tampered(projection, facts=(dataclasses.replace(fact, horizon="5m"),)),
            "malformed_fact_logical_identity:horizon:str",
        ),
        (
            _tampered(
                projection,
                facts=(dataclasses.replace(fact, population_key="not-a-key"),),
            ),
            "malformed_fact_population_key:str",
        ),
    )

    for tampered, expected in cases:
        with pytest.raises(AggregationOrchestrationError) as captured:
            aggregate_projection(tampered)
        assert str(captured.value) == expected


def test_malformed_projection_identity_never_reaches_i01(monkeypatch):
    projection = _projection({"candidate_id": "a"})
    fact = projection.facts[0]
    calls = _spy_on_aggregate(monkeypatch)

    tampered_projections = (
        _tampered(projection, horizon="5m"),
        _tampered(projection, facts=(dataclasses.replace(fact, horizon="5m"),)),
        _tampered(
            projection,
            facts=(dataclasses.replace(fact, population_key="not-a-key"),),
        ),
    )

    for tampered in tampered_projections:
        with pytest.raises(AggregationOrchestrationError):
            aggregate_projection(tampered)

    assert calls == []


def test_valid_projection_behavior_is_unchanged_by_the_fix(monkeypatch):
    projection = _three_populations()
    calls = _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert len(results) == 3
    assert sorted(len(call["facts"]) for call in calls) == [1, 2, 3]
    assert [result.population_key.canonical_key() for result in results] == sorted(
        result.population_key.canonical_key() for result in results
    )
    assert all(result.horizon is HORIZON for result in results)
    # An empty projection still aggregates to nothing, without any failure.
    assert (
        aggregate_projection(
            CurrentSnapshotProjection(as_of=AS_OF, horizon=HORIZON, facts=(), manifest=())
        )
        == ()
    )


# === N. async wrapper =======================================================================


def test_async_wrapper_reads_exactly_once_and_delegates_the_exact_projection(monkeypatch):
    projection = _projection({"candidate_id": "a"})
    horizons: list[ForwardHorizon] = []

    class _RecordingReader:
        async def read(self, horizon: ForwardHorizon) -> CurrentSnapshotProjection:
            horizons.append(horizon)
            return projection

    captured: list[Any] = []
    sentinel = ("orchestration-sentinel",)

    def _record(proj):
        captured.append(proj)
        return sentinel

    monkeypatch.setattr(orchestration, "aggregate_projection", _record)

    outcome = asyncio.run(aggregate_current_snapshot(_RecordingReader(), HORIZON))

    assert outcome is sentinel
    assert horizons == [HORIZON]
    assert len(horizons) == 1
    assert len(captured) == 1
    assert captured[0] is projection


def test_async_wrapper_end_to_end_matches_the_pure_orchestrator():
    projection = _projection(
        {"candidate_id": "a", "instrument_id": "BTC-USDT"},
        {"candidate_id": "b", "instrument_id": "ETH-USDT"},
    )

    class _Reader:
        async def read(self, horizon: ForwardHorizon) -> CurrentSnapshotProjection:
            return projection

    results = asyncio.run(aggregate_current_snapshot(_Reader(), HORIZON))

    assert results == aggregate_projection(projection)
    assert [result.input_fingerprint for result in results] == [
        result.input_fingerprint for result in aggregate_projection(projection)
    ]


def test_async_wrapper_propagates_i02_snapshot_error():
    class _BrokenReader:
        async def read(self, horizon: ForwardHorizon) -> CurrentSnapshotProjection:
            raise SnapshotIntegrityError(("evidence_revision_gap:opp:1",))

    with pytest.raises(SnapshotIntegrityError):
        asyncio.run(aggregate_current_snapshot(_BrokenReader(), HORIZON))


# === O. permutation invariance ==============================================================


def test_permuted_facts_and_manifest_produce_identical_results():
    projection = _three_populations()
    permuted = _tampered(
        projection,
        facts=tuple(reversed(projection.facts)),
        manifest=tuple(reversed(projection.manifest)),
    )
    assert permuted.facts != projection.facts
    assert permuted.manifest != projection.manifest

    forward = aggregate_projection(projection)
    backward = aggregate_projection(permuted)

    assert len(forward) == len(backward) == 3
    assert [result.population_key for result in forward] == [
        result.population_key for result in backward
    ]
    assert [result.input_fingerprint for result in forward] == [
        result.input_fingerprint for result in backward
    ]
    assert [result.to_dict() for result in forward] == [
        result.to_dict() for result in backward
    ]


def test_permutation_keeps_populations_intact(monkeypatch):
    projection = _three_populations()
    permuted = _tampered(
        projection,
        facts=tuple(reversed(projection.facts)),
        manifest=tuple(reversed(projection.manifest)),
    )

    forward_calls = _spy_on_aggregate(monkeypatch)
    aggregate_projection(projection)
    forward_sizes = [len(call["facts"]) for call in forward_calls]

    monkeypatch.undo()
    backward_calls = _spy_on_aggregate(monkeypatch)
    aggregate_projection(permuted)
    backward_sizes = [len(call["facts"]) for call in backward_calls]

    assert sorted(forward_sizes) == sorted(backward_sizes) == [1, 2, 3]
    assert [call["population_key"] for call in forward_calls] == [
        call["population_key"] for call in backward_calls
    ]


# === public surface / boundaries ============================================================


def test_public_surface_shape():
    assert not inspect.iscoroutinefunction(aggregate_projection)
    assert inspect.iscoroutinefunction(aggregate_current_snapshot)
    assert list(inspect.signature(aggregate_projection).parameters) == ["projection"]
    assert list(inspect.signature(aggregate_current_snapshot).parameters) == [
        "reader",
        "horizon",
    ]
    assert set(orchestration.__all__) == {
        "AggregationOrchestrationError",
        "LogicalIdentity",
        "aggregate_current_snapshot",
        "aggregate_projection",
    }


def test_orchestration_error_is_a_sibling_not_subclass_of_aggregation_error():
    assert issubclass(AggregationOrchestrationError, ValueError)
    assert not issubclass(AggregationOrchestrationError, AggregationError)


def test_i01_aggregation_error_is_not_swallowed():
    projection = _projection({"candidate_id": "a"})
    # A naive ``as_of`` is I01's own fail-closed precondition; the point here is
    # that the failure surfaces as I01's type and is never swallowed or re-wrapped.
    naive = _tampered(projection, as_of=AS_OF.replace(tzinfo=None))

    with pytest.raises(AggregationError):
        aggregate_projection(naive)


def test_population_keys_come_from_the_facts_themselves(monkeypatch):
    projection = _projection(
        {"candidate_id": "a", "instrument_id": "BTC-USDT"},
        {"candidate_id": "b", "instrument_id": "ETH-USDT"},
    )
    _spy_on_aggregate(monkeypatch)

    results = aggregate_projection(projection)

    assert all(isinstance(fact, CanonicalScopeFacts) for fact in projection.facts)
    assert len(results) == 2
    for result in results:
        matching = [
            fact for fact in projection.facts if fact.population_key == result.population_key
        ]
        assert matching
        assert {fact.population_key for fact in matching} == {result.population_key}
    assert {result.population_key.instrument_id for result in results} == {
        "BTC-USDT",
        "ETH-USDT",
    }


def test_orchestration_module_owns_no_database_surface():
    tree = ast.parse(ORCHESTRATION_SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    assert not any(name.startswith("sqlalchemy") for name in imported)
    assert not any(name.startswith("marketpulse.db") for name in imported)
    assert not any("session" in name for name in imported)
