"""SE-02D-I01 deterministic Family Aggregation / Expectancy core: focused contract tests.

This module is pure. No database, no session, no migration, no runtime host and
no persistence is exercised here; every test binds one frozen clause of the
Accepted ``SE-02D-D01`` V1 contract (task SE-02D-I01 section 32).

Golden-vector policy: the RNG tests do not merely re-invoke the implementation.
``test_rng_matches_independent_hand_rolled_rejection_sampling`` re-implements
``SHA256_COUNTER_REJECTION_V1`` straight from the contract text using only
``hashlib`` / ``int.from_bytes``, and the frozen literals below pin the seed and
fingerprint derivations so later drift is a test failure rather than a silent
re-interpretation.
"""

import ast
import dataclasses
import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from marketpulse.edge import aggregation as aggregation_module
from marketpulse.edge.aggregation import (
    AGGREGATION_CONTRACT_VERSION,
    BOOTSTRAP_LOWER_INDEX,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_UPPER_INDEX,
    CONFIDENCE_LEVEL,
    DEPENDENCE_LIMITATIONS,
    INTEGRITY_STATEMENT,
    MIN_CLUSTERS_FOR_INTERVAL,
    MIN_CLUSTERS_FOR_SUFFICIENCY,
    REGIME_GATE,
    REGIME_SUFFICIENCY,
    REQUIRED_COVERAGE_RATE,
    RNG_ALGORITHM_VERSION,
    UNCERTAINTY_METHOD_VERSION,
    VISIBILITY_MODE,
    AggregateStatus,
    AggregationError,
    Calculability,
    CanonicalScopeFacts,
    DuplicateSampleIdentityError,
    ForeignScopeFactError,
    IntervalSide,
    MaturityClass,
    MeasurementSignature,
    MeasurementSignatureState,
    OverlapCluster,
    PopulationKey,
    SufficiencyReason,
    UncertaintyUnavailableReason,
    aggregate,
    bootstrap_seed,
    build_ordered_input_manifest,
    classify_maturity,
    cluster_samples,
    compute_input_fingerprint,
    draw_cluster_index,
    economic_statistics,
    percentile_interval,
    replicate_means,
    sample_identity,
    worst_decile_k,
)
from marketpulse.edge.hashing import canonical_bytes
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
)
from marketpulse.market_data.models import MarketType

T0 = datetime(2026, 9, 15, 0, 0, tzinfo=UTC)
AS_OF = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
HORIZON = ForwardHorizon.M5
FAMILY_VERSION = "g2-v1"
INSTRUMENT = "BTC-USDT"
SOURCE_IDENTITY = "okx"
MANIFEST_A = "manifest-a"

AGGREGATION_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "marketpulse" / "edge" / "aggregation.py"
)


# --- fixtures / builders -----------------------------------------------------------------


def _key(
    *,
    instrument_id: str = INSTRUMENT,
    market_type: MarketType = MarketType.SPOT,
    source_type: EvidenceSource = EvidenceSource.FORWARD_PAPER,
    source_identity: str = SOURCE_IDENTITY,
    family_version: str = FAMILY_VERSION,
) -> PopulationKey:
    return PopulationKey(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=family_version,
        instrument_id=instrument_id,
        market_type=market_type,
        source_type=source_type,
        source_identity=source_identity,
        evidence_contract_version="se02-evidence-v1",
    )


KEY = _key()


def _signature(
    *,
    calculator_version: str = "se02c-forward-outcome-v1",
    cost_model_version: str = "se02c-paper-cost-v1",
    outcome_source_identity: str = SOURCE_IDENTITY,
) -> MeasurementSignature:
    return MeasurementSignature(
        outcome_contract_version="se02-outcome-v1",
        calculator_version=calculator_version,
        cost_policy="SPOT_LONG_TAKER_ROUND_TRIP",
        cost_model_version=cost_model_version,
        outcome_source_type=EvidenceSource.FORWARD_PAPER,
        outcome_source_identity=outcome_source_identity,
    )


SIGNATURE = _signature()


def _fact(
    opportunity_id: str,
    *,
    start_offset_hours: float = 0.0,
    start_offset_minutes: float | None = None,
    return_value: float | None = 0.01,
    key: PopulationKey | None = None,
    horizon: ForwardHorizon = HORIZON,
    status: OutcomeCalculationStatus | None = OutcomeCalculationStatus.COMPLETE,
    signature: MeasurementSignature | None = None,
    outcome_reason: str | None = None,
    source_manifest_id: str = MANIFEST_A,
    reference_data_status: ReferenceDataStatus = ReferenceDataStatus.OK,
    lifecycle: OpportunityLifecycleAtHorizon | None = OpportunityLifecycleAtHorizon.ACTIVE,
    folded_evidence_revision_count: int = 0,
    folded_outcome_revision_count: int = 0,
    outcomes_excluded_with_folded_evidence: int = 0,
) -> CanonicalScopeFacts:
    resolved_key = key if key is not None else KEY
    offset = (
        timedelta(minutes=start_offset_minutes)
        if start_offset_minutes is not None
        else timedelta(hours=start_offset_hours)
    )
    start = T0 + offset
    common = {
        "opportunity_id": opportunity_id,
        "population_key": resolved_key,
        "horizon": horizon,
        "evidence_id": f"ev-{opportunity_id}",
        "evidence_revision": 1,
        "evidence_hash": f"hash-{opportunity_id}",
        "evidence_at": start,
        "due_at": start + timedelta(seconds=horizon.duration_seconds),
        "source_manifest_id": source_manifest_id,
        "reference_data_status": reference_data_status,
        "lifecycle": lifecycle,
        "folded_evidence_revision_count": folded_evidence_revision_count,
        "folded_outcome_revision_count": folded_outcome_revision_count,
        "outcomes_excluded_with_folded_evidence": outcomes_excluded_with_folded_evidence,
    }
    if status is None:
        return CanonicalScopeFacts(**common)
    resolved_signature = signature if signature is not None else SIGNATURE
    return CanonicalScopeFacts(
        **common,
        outcome_id=f"out-{opportunity_id}",
        outcome_revision=1,
        outcome_record_hash=f"rechash-{opportunity_id}",
        outcome_status=status,
        outcome_reason=(
            outcome_reason
            if outcome_reason is not None
            else (
                "COMPLETE"
                if status is OutcomeCalculationStatus.COMPLETE
                else "ENDPOINT_MISSING"
                if status is OutcomeCalculationStatus.INSUFFICIENT_DATA
                else "INVALID_CHRONOLOGY"
            )
        ),
        measurement_signature=(
            resolved_signature if status is OutcomeCalculationStatus.COMPLETE else None
        ),
        cost_adjusted_forward_return=(
            return_value if status is OutcomeCalculationStatus.COMPLETE else None
        ),
        reference_return=0.005 if status is OutcomeCalculationStatus.COMPLETE else None,
        executable_long_return=0.004 if status is OutcomeCalculationStatus.COMPLETE else None,
        mfe=0.02 if status is OutcomeCalculationStatus.COMPLETE else None,
        mae=-0.01 if status is OutcomeCalculationStatus.COMPLETE else None,
    )


def _resolved_positive_facts() -> list[CanonicalScopeFacts]:
    """Three disjoint clusters, clearly positive expectancy."""
    return [
        _fact("opp-01", start_offset_hours=1, return_value=0.05),
        _fact("opp-02", start_offset_hours=4, return_value=0.06),
        _fact("opp-03", start_offset_hours=7, return_value=0.07),
    ]


def _aggregate(facts, *, key: PopulationKey | None = None, horizon: ForwardHorizon = HORIZON, **kwargs):
    return aggregate(
        population_key=key if key is not None else KEY,
        horizon=horizon,
        as_of=AS_OF,
        facts=facts,
        **kwargs,
    )


def _cluster(cluster_id: int, returns: tuple[float, ...]) -> OverlapCluster:
    start = T0 + timedelta(hours=cluster_id * 3)
    return OverlapCluster(
        cluster_id=cluster_id,
        sample_ids=tuple(f"sample-{cluster_id}-{i}" for i in range(len(returns))),
        opportunity_ids=tuple(f"opp-{cluster_id}-{i}" for i in range(len(returns))),
        returns=returns,
        interval_start=start,
        interval_end=start + timedelta(minutes=5),
    )


# --- Population Key / aggregate identity ---------------------------------------------------


def test_population_key_field_set_and_order_match_accepted_contract():
    assert tuple(field.name for field in dataclasses.fields(PopulationKey)) == (
        "family_id",
        "family_version",
        "instrument_id",
        "market_type",
        "source_type",
        "source_identity",
        "evidence_contract_version",
    )
    payload = KEY.canonical_payload()
    assert "source_manifest_id" not in payload


def test_measurement_signature_field_set_and_order_match_accepted_contract():
    assert tuple(field.name for field in dataclasses.fields(MeasurementSignature)) == (
        "outcome_contract_version",
        "calculator_version",
        "cost_policy",
        "cost_model_version",
        "outcome_source_type",
        "outcome_source_identity",
    )


def test_population_key_equality_and_separation():
    assert _key() == KEY
    assert _key(instrument_id="ETH-USDT") != KEY
    assert _key(market_type=MarketType.SWAP) != KEY
    assert _key(source_type=EvidenceSource.HISTORICAL_REPLAY) != KEY
    assert _key(source_identity="binance") != KEY
    assert _key(family_version="g2-v2") != KEY


def test_manifest_is_not_a_population_key_field():
    """D01 section 6.3: a different manifest must not create a different population."""
    first = _aggregate([_fact("opp-01", start_offset_hours=1, source_manifest_id="m-1")])
    second = _aggregate([_fact("opp-01", start_offset_hours=1, source_manifest_id="m-2")])
    assert first.population_key == second.population_key
    assert first.coverage.eligible_opportunities == 1
    assert first.manifest.manifest_count == 1
    assert second.manifest.ordered_manifest_ids == ("m-2",)


def test_horizon_separation():
    """Four horizons are separate repeated-measure views, never one pooled sample."""
    m5 = _aggregate([_fact("opp-01", start_offset_hours=1, return_value=0.05)])
    m15 = _aggregate(
        [_fact("opp-01", start_offset_hours=1, return_value=0.05, horizon=ForwardHorizon.M15)],
        horizon=ForwardHorizon.M15,
    )
    assert m5.horizon is ForwardHorizon.M5
    assert m15.horizon is ForwardHorizon.M15
    assert m5.input_fingerprint != m15.input_fingerprint
    assert m5.statistics.n_economic_samples == 1
    assert m15.statistics.n_economic_samples == 1
    # the same logical opportunity contributes exactly one sample per horizon
    assert m5.coverage.eligible_opportunities == 1
    assert m15.coverage.eligible_opportunities == 1


def test_facts_from_another_horizon_are_not_pooled_into_one_aggregate():
    with pytest.raises(ForeignScopeFactError):
        _aggregate(
            [_fact("opp-01", start_offset_hours=1, horizon=ForwardHorizon.M15)],
            horizon=ForwardHorizon.M5,
        )


# --- Sample identity / fail-closed input ----------------------------------------------------


def test_duplicate_sample_identity_fails_closed():
    duplicates = [
        _fact("opp-01", start_offset_hours=1, return_value=0.05),
        _fact("opp-01", start_offset_hours=4, return_value=0.09),
    ]
    with pytest.raises(DuplicateSampleIdentityError):
        _aggregate(duplicates)


def test_duplicate_sample_identity_is_not_silently_deduplicated():
    """Neither "keep first" nor "keep last" is an allowed resolution."""
    with pytest.raises(DuplicateSampleIdentityError):
        _aggregate(
            [
                _fact("opp-01", start_offset_hours=1, return_value=0.05),
                _fact("opp-02", start_offset_hours=4, return_value=0.06),
                _fact("opp-01", start_offset_hours=7, return_value=0.07),
            ]
        )


def test_foreign_scope_fact_fails_closed():
    with pytest.raises(ForeignScopeFactError):
        _aggregate([_fact("opp-01", start_offset_hours=1, key=_key(instrument_id="ETH-USDT"))])


def test_no_outcome_marker_must_not_carry_outcome_fields():
    base = {
        "opportunity_id": "opp-01",
        "population_key": KEY,
        "horizon": HORIZON,
        "evidence_id": "ev-opp-01",
        "evidence_revision": 1,
        "evidence_hash": "hash-opp-01",
        "evidence_at": T0 + timedelta(hours=1),
        "due_at": T0 + timedelta(hours=1, minutes=5),
        "source_manifest_id": MANIFEST_A,
        "reference_data_status": ReferenceDataStatus.OK,
    }
    with pytest.raises(AggregationError):
        CanonicalScopeFacts(**base, outcome_status=OutcomeCalculationStatus.COMPLETE)
    with pytest.raises(AggregationError):
        CanonicalScopeFacts(**base, measurement_signature=SIGNATURE)


def test_complete_outcome_requires_a_measurement_signature():
    base = {
        "opportunity_id": "opp-01",
        "population_key": KEY,
        "horizon": HORIZON,
        "evidence_id": "ev-opp-01",
        "evidence_revision": 1,
        "evidence_hash": "hash-opp-01",
        "evidence_at": T0 + timedelta(hours=1),
        "due_at": T0 + timedelta(hours=1, minutes=5),
        "source_manifest_id": MANIFEST_A,
        "reference_data_status": ReferenceDataStatus.OK,
        "outcome_id": "out-opp-01",
        "outcome_revision": 1,
        "outcome_record_hash": "rechash-opp-01",
        "outcome_status": OutcomeCalculationStatus.COMPLETE,
        "cost_adjusted_forward_return": 0.01,
    }
    with pytest.raises(AggregationError):
        CanonicalScopeFacts(**base)


def test_measurement_signature_does_not_create_a_second_sample():
    """D01 section 4.1: an Outcome correction cannot re-identify the sample."""
    single = _aggregate([_fact("opp-01", start_offset_hours=1, return_value=0.05)])
    assert single.statistics.n_economic_samples == 1
    assert single.coverage.eligible_opportunities == 1


# --- Maturity / coverage --------------------------------------------------------------------


def test_maturity_classification_matrix():
    facts = {
        MaturityClass.NOT_YET_DUE: _fact("opp-a", start_offset_hours=20),
        MaturityClass.COMPLETE: _fact("opp-b", start_offset_hours=1),
        MaturityClass.INSUFFICIENT_DATA: _fact(
            "opp-c", start_offset_hours=1, status=OutcomeCalculationStatus.INSUFFICIENT_DATA
        ),
        MaturityClass.INVALID: _fact(
            "opp-d", start_offset_hours=1, status=OutcomeCalculationStatus.INVALID
        ),
        MaturityClass.MISSING_OUTCOME: _fact("opp-e", start_offset_hours=1, status=None),
    }
    for expected, fact in facts.items():
        assert classify_maturity(fact, as_of=AS_OF) is expected


def test_not_yet_due_is_excluded_from_mature_denominator():
    result = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=0.05),
            _fact("opp-02", start_offset_hours=20, return_value=0.05),
        ]
    )
    assert result.coverage.eligible_opportunities == 2
    assert result.coverage.not_yet_due == 1
    assert result.coverage.mature_denominator == 1
    assert result.coverage.coverage_rate == 1.0


def test_missing_outcome_lands_in_its_own_coverage_class():
    result = _aggregate([_fact("opp-01", start_offset_hours=1, status=None)])
    coverage = result.coverage
    assert coverage.eligible_opportunities == 1
    assert coverage.not_yet_due == 0
    assert coverage.mature_denominator == 1
    assert coverage.missing_outcome == 1
    assert coverage.complete == 0
    assert coverage.coverage_rate == 0.0
    assert coverage.settlement_rate == 0.0
    assert coverage.status_reason_counts == {"MISSING_OUTCOME": 1}


def test_every_mature_status_is_counted_exactly_once():
    result = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=0.05),
            _fact("opp-02", start_offset_hours=4, status=OutcomeCalculationStatus.INSUFFICIENT_DATA),
            _fact("opp-03", start_offset_hours=7, status=OutcomeCalculationStatus.INVALID),
            _fact("opp-04", start_offset_hours=10, status=None),
            _fact("opp-05", start_offset_hours=20, return_value=0.05),
        ]
    )
    coverage = result.coverage
    assert coverage.eligible_opportunities == 5
    assert coverage.not_yet_due == 1
    assert coverage.mature_denominator == 4
    assert (
        coverage.complete
        + coverage.insufficient_data
        + coverage.invalid
        + coverage.missing_outcome
        == coverage.mature_denominator
    )
    assert coverage.coverage_rate == pytest.approx(0.25)
    assert coverage.settlement_rate == pytest.approx(0.75)
    assert sum(coverage.status_reason_counts.values()) == coverage.mature_denominator


def test_zero_mature_denominator_gives_null_coverage_rate():
    result = _aggregate([_fact("opp-01", start_offset_hours=20, return_value=0.05)])
    assert result.coverage.mature_denominator == 0
    assert result.coverage.coverage_rate is None
    assert result.coverage.settlement_rate is None
    assert result.coverage.not_yet_due == 1
    assert result.status is AggregateStatus.NOT_CALCULABLE


def test_coverage_diagnostics_are_reported_in_full():
    result = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=0.05),
            _fact(
                "opp-02",
                start_offset_hours=4,
                return_value=0.06,
                reference_data_status=ReferenceDataStatus.REFERENCE_MISSING,
                lifecycle=OpportunityLifecycleAtHorizon.EXPIRED,
                source_manifest_id="m-2",
                folded_evidence_revision_count=2,
                folded_outcome_revision_count=1,
                outcomes_excluded_with_folded_evidence=1,
            ),
        ]
    )
    coverage = result.coverage
    assert coverage.reference_status_counts == {
        "OK": 1,
        "REFERENCE_MISSING": 1,
        "REFERENCE_STALE": 0,
    }
    assert coverage.lifecycle_counts == {"ACTIVE": 1, "EXPIRED": 1, "NULL": 0}
    assert coverage.folded_evidence_revisions == 2
    assert coverage.folded_outcome_revisions == 1
    assert coverage.outcomes_excluded_with_folded_evidence == 1
    assert result.manifest.manifest_counts == {"m-2": 1, "manifest-a": 1}
    assert result.manifest.manifest_count == 2
    assert result.manifest.ordered_manifest_ids == ("m-2", "manifest-a")
    assert result.manifest.max_manifest_concentration == pytest.approx(0.5)


def test_unknown_outcome_reason_is_preserved_not_rewritten():
    result = _aggregate(
        [
            _fact(
                "opp-01",
                start_offset_hours=1,
                status=OutcomeCalculationStatus.INVALID,
                outcome_reason="INVALID_SOMETHING_NEW",
            )
        ]
    )
    assert result.coverage.status_reason_counts == {"UNKNOWN_REASON:INVALID_SOMETHING_NEW": 1}


# --- Measurement compatibility -------------------------------------------------------------


def test_single_compatible_signature_allows_economic_calculation():
    result = _aggregate(_resolved_positive_facts())
    assert result.status is AggregateStatus.VALID
    assert result.measurement_signature_state is MeasurementSignatureState.EXACT
    assert result.measurement_signature == SIGNATURE
    assert result.statistics is not None


def test_mixed_measurement_signatures_fail_closed_without_losing_coverage():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.05),
        _fact(
            "opp-02",
            start_offset_hours=4,
            return_value=0.06,
            signature=_signature(calculator_version="se02c-forward-outcome-v2"),
        ),
    ]
    result = _aggregate(facts)
    assert result.status is AggregateStatus.INCOMPATIBLE_MEASUREMENT_SIGNATURES
    assert result.measurement_signature_state is MeasurementSignatureState.MIXED
    assert result.measurement_signature is None
    # population coverage survives untouched
    assert result.coverage.complete == 2
    assert result.coverage.coverage_rate == 1.0
    assert result.coverage.mature_denominator == 2
    # headline economic statistics are withheld
    assert result.statistics is None
    assert result.tail_risk is None
    assert result.uncertainty is None
    assert result.calculability is None
    assert SufficiencyReason.INCOMPATIBLE_MEASUREMENT_SIGNATURES.value in result.sufficiency_reasons


def test_zero_complete_signatures_is_not_calculable():
    result = _aggregate([_fact("opp-01", start_offset_hours=1, status=None)])
    assert result.status is AggregateStatus.NOT_CALCULABLE
    assert result.measurement_signature_state is MeasurementSignatureState.NO_MEASUREMENT


# --- Integrity fail-closed ------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [None, float("nan"), float("inf"), float("-inf")],
    ids=["none", "nan", "pos-inf", "neg-inf"],
)
def test_complete_return_integrity_conflict_fails_closed(value):
    result = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=value),
            _fact("opp-02", start_offset_hours=4, return_value=0.06),
        ]
    )
    assert result.status is AggregateStatus.INTEGRITY_CONFLICT
    assert result.coverage.integrity_conflict_count == 1
    # the raw COMPLETE status count stays visible; the row is not silently removed
    assert result.coverage.complete == 2
    assert result.coverage.coverage_rate == 1.0
    # no economic statistics are emitted for the whole aggregate
    assert result.statistics is None
    assert result.uncertainty is None
    assert result.integrity_conflicts != ()
    assert SufficiencyReason.INTEGRITY_CONFLICT_PRESENT.value in result.sufficiency_reasons


def test_integrity_conflict_outranks_incompatible_signatures():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=float("nan")),
        _fact(
            "opp-02",
            start_offset_hours=4,
            return_value=0.06,
            signature=_signature(calculator_version="se02c-forward-outcome-v2"),
        ),
    ]
    result = _aggregate(facts)
    assert result.status is AggregateStatus.INTEGRITY_CONFLICT


def test_integrity_conflict_outranks_not_applicable():
    swap_key = _key(market_type=MarketType.SWAP)
    result = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=None, key=swap_key),
            _fact("opp-02", start_offset_hours=4, return_value=0.06, key=swap_key),
        ],
        key=swap_key,
    )
    assert result.status is AggregateStatus.INTEGRITY_CONFLICT


# --- Market-type boundary --------------------------------------------------------------------


def test_swap_is_not_applicable_but_keeps_coverage():
    swap_key = _key(market_type=MarketType.SWAP)
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.05, key=swap_key),
        _fact("opp-02", start_offset_hours=4, status=None, key=swap_key),
    ]
    result = _aggregate(facts, key=swap_key)
    assert result.status is AggregateStatus.NOT_APPLICABLE
    assert result.coverage.coverage_rate == pytest.approx(0.5)
    assert result.coverage.mature_denominator == 2
    assert result.statistics is None
    assert result.uncertainty is None
    assert result.calculability is None
    assert SufficiencyReason.MARKET_TYPE_NOT_APPLICABLE.value in result.sufficiency_reasons


# --- Expectancy / descriptive statistics -----------------------------------------------------


def test_expectancy_is_deterministic_fsum_over_cost_adjusted_returns():
    returns = [0.05, 0.06, 0.07]
    result = _aggregate(
        [_fact(f"opp-0{i + 1}", start_offset_hours=1 + i * 3, return_value=value)
         for i, value in enumerate(returns)]
    )
    assert result.statistics.n_economic_samples == 3
    assert result.statistics.mean == math.fsum(returns) / len(returns)


def test_descriptive_statistics_values():
    returns = [-0.04, 0.0, 0.02, 0.06]
    stats = economic_statistics(returns)
    ordered = sorted(returns)
    assert stats.n_economic_samples == 4
    assert stats.mean == math.fsum(ordered) / 4
    assert stats.median == math.fsum((ordered[1], ordered[2])) / 2.0
    assert stats.positive_count == 2
    assert stats.negative_count == 1
    assert stats.flat_count == 1
    assert stats.positive_rate == pytest.approx(0.5)
    assert stats.worst_observation == -0.04


def test_median_of_odd_count_is_the_middle_sample():
    stats = economic_statistics([0.03, 0.01, 0.02])
    assert stats.median == 0.02


def test_sample_standard_deviation_uses_n_minus_one_denominator():
    returns = [0.02, 0.04, 0.06]
    stats = economic_statistics(returns)
    mean = math.fsum(returns) / 3
    assert stats.sample_standard_deviation == pytest.approx(
        math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / 2)
    )
    # sample (n-1) deviates from the population (n) deviates on purpose
    assert stats.sample_standard_deviation != pytest.approx(
        math.sqrt(math.fsum((value - mean) ** 2 for value in returns) / 3)
    )


def test_sample_standard_deviation_is_null_below_two_samples():
    result = _aggregate([_fact("opp-01", start_offset_hours=1, return_value=0.05)])
    assert result.status is AggregateStatus.VALID
    assert result.statistics.n_economic_samples == 1
    assert result.statistics.sample_standard_deviation is None
    assert result.statistics.worst_observation == 0.05
    assert result.statistics.worst_decile_mean == 0.05


def test_no_trend_or_portfolio_statistics_are_produced():
    stats = economic_statistics([0.01, 0.02, 0.03])
    names = {field.name for field in dataclasses.fields(stats)}
    for forbidden in ("sharpe", "sortino", "kelly", "profit_factor", "drawdown", "equity_curve"):
        assert forbidden not in names


# --- Tail evidence -------------------------------------------------------------------------


def test_worst_decile_k_matches_the_float_formula():
    for n in range(1, 2001):
        assert worst_decile_k(n) == math.ceil(0.10 * n)


@pytest.mark.parametrize(
    ("n", "expected"),
    [(1, 1), (2, 1), (9, 1), (10, 1), (11, 2), (20, 2), (21, 3), (30, 3), (100, 10)],
)
def test_worst_decile_k_known_values(n, expected):
    assert worst_decile_k(n) == expected


def test_worst_observation_and_worst_decile_mean():
    returns = [0.10, -0.05, 0.03, 0.07, -0.02, 0.04, 0.01, 0.06, 0.02, 0.05]
    stats = economic_statistics(returns)
    ordered = sorted(returns)
    assert stats.worst_observation == ordered[0]
    assert stats.worst_decile_mean == math.fsum(ordered[:1]) / 1


def test_worst_decile_mean_averages_the_k_smallest():
    returns = [-0.10, -0.08, -0.06, -0.04, -0.02, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    stats = economic_statistics(returns)
    assert worst_decile_k(11) == 2
    ordered = sorted(returns)
    assert stats.worst_decile_mean == math.fsum(ordered[:2]) / 2


def test_tail_evidence_has_no_threshold():
    result = _aggregate(_resolved_positive_facts())
    assert result.tail_risk.threshold is None
    assert result.tail_risk.to_dict()["acceptable_tail_risk_threshold"] is None


# --- Overlap clustering -------------------------------------------------------------------


def test_non_overlapping_intervals_form_separate_clusters():
    clusters = cluster_samples(_resolved_positive_facts())
    assert len(clusters) == 3
    assert [cluster.cluster_id for cluster in clusters] == [0, 1, 2]
    assert [cluster.opportunity_ids for cluster in clusters] == [
        ("opp-01",),
        ("opp-02",),
        ("opp-03",),
    ]


def test_touching_intervals_form_one_cluster():
    """Touch counts as overlap: ``[a, b]`` and ``[b, c]`` are one component."""
    first = _fact("opp-01", start_offset_minutes=60)
    second = _fact("opp-02", start_offset_minutes=65)
    clusters = cluster_samples([first, second])
    assert second.evidence_at == first.due_at
    assert len(clusters) == 1
    assert clusters[0].opportunity_ids == ("opp-01", "opp-02")


def test_adjacent_but_disjoint_intervals_stay_separate():
    first = _fact("opp-01", start_offset_minutes=60)
    second = _fact("opp-02", start_offset_minutes=66)
    clusters = cluster_samples([first, second])
    assert len(clusters) == 2


def test_transitive_overlap_collapses_into_one_cluster():
    """A~B and B~C must collapse to one cluster even when A and C are disjoint."""
    a = _fact("opp-01", start_offset_minutes=60, return_value=0.01)
    b = _fact("opp-02", start_offset_minutes=64, return_value=0.02)
    c = _fact("opp-03", start_offset_minutes=68, return_value=0.03)
    # A ends at 65 and C starts at 68, so A and C never intersect directly
    assert c.evidence_at > a.due_at
    assert b.evidence_at <= a.due_at <= b.due_at
    assert c.evidence_at <= b.due_at
    clusters = cluster_samples([a, b, c])
    assert len(clusters) == 1
    assert clusters[0].opportunity_ids == ("opp-01", "opp-02", "opp-03")
    assert clusters[0].returns == (0.01, 0.02, 0.03)


def test_cluster_ordering_is_deterministic_and_input_order_independent():
    forward = _resolved_positive_facts()
    backward = list(reversed(forward))
    assert cluster_samples(forward) == cluster_samples(backward)


def test_cluster_sweep_uses_evidence_at_then_opportunity_id():
    overlapping = [
        _fact("opp-b", start_offset_hours=2, return_value=0.01),
        _fact("opp-a", start_offset_hours=2, return_value=0.02),
    ]
    clusters = cluster_samples(overlapping)
    assert len(clusters) == 1
    # same evidence_at -> tie-broken by opportunity_id
    assert clusters[0].opportunity_ids == ("opp-a", "opp-b")


def test_cluster_interval_end_is_the_maximum_due_at():
    a = _fact("opp-01", start_offset_hours=1)
    b = _fact("opp-02", start_offset_hours=1, horizon=ForwardHorizon.M15)
    clusters = cluster_samples([a, b])
    assert len(clusters) == 1
    assert clusters[0].interval_end == max(a.due_at, b.due_at)


# --- Deterministic RNG --------------------------------------------------------------------


ZERO_SEED = bytes(32)

FROZEN_DRAWS_N3 = [2, 2, 0, 1, 2, 0, 2, 1, 1, 2, 0, 1]
FROZEN_DRAWS_N7 = [5, 1, 4, 4, 6, 5, 1, 0, 5, 0, 4, 1]
FROZEN_FINGERPRINT = "3cb82ce861888317446412d116b0d7d17573eb30f8dce6a277c63ee76b76c203"
FROZEN_SEED_HEX = "919df6df3b440173a5be56415d4ee7a38b6de6ddfba2b4407eaf2796c5088fcd"
FROZEN_DRAWS_FROM_REAL_SEED = [0, 1, 4, 4, 4, 2, 3, 0, 3, 2]
FROZEN_GOLDEN_MANIFEST = [
    {
        "opportunity_id": "opp-01",
        "horizon": "5m",
        "evidence_id": "ev-01",
        "evidence_revision": 1,
        "evidence_hash": "hash-01",
        "cost_adjusted_forward_return_hex": "0x1.999999999999ap-5",
    }
]


def test_rng_golden_vector():
    assert [draw_cluster_index(ZERO_SEED, 3, ordinal) for ordinal in range(12)] == FROZEN_DRAWS_N3
    assert [draw_cluster_index(ZERO_SEED, 7, ordinal) for ordinal in range(12)] == FROZEN_DRAWS_N7


def test_rng_matches_independent_hand_rolled_rejection_sampling():
    """Re-implement SHA256_COUNTER_REJECTION_V1 from the contract text independently."""

    def hand_rolled(n_clusters: int, draw_ordinal: int) -> tuple[int, int]:
        limit = (1 << 256) - ((1 << 256) % n_clusters)
        attempt = 0
        while True:
            digest = hashlib.sha256(
                ZERO_SEED + draw_ordinal.to_bytes(8, "big") + attempt.to_bytes(4, "big")
            ).digest()
            value = int.from_bytes(digest, "big")
            if value < limit:
                return value % n_clusters, attempt
            attempt += 1

    for n_clusters in (1, 2, 3, 5, 7, 11, 64, 255):
        for draw_ordinal in range(40):
            expected, _ = hand_rolled(n_clusters, draw_ordinal)
            assert draw_cluster_index(ZERO_SEED, n_clusters, draw_ordinal) == expected


def test_rng_first_attempt_digest_is_pinned():
    digest = hashlib.sha256(ZERO_SEED + (0).to_bytes(8, "big") + (0).to_bytes(4, "big")).hexdigest()
    assert digest == "85759b3811ff7dc47b03792ac85317be51431a3f9e01dcafce317ed736a391b0"
    assert int(digest, 16) % 3 == FROZEN_DRAWS_N3[0]


def test_draw_counter_is_zero_based_and_sequential():
    """``j = replicate_index * n_clusters + draw_index`` with both counters 0-based."""
    n_clusters = 4
    for replicate_index in range(3):
        for draw_index in range(n_clusters):
            ordinal = replicate_index * n_clusters + draw_index
            assert draw_cluster_index(ZERO_SEED, n_clusters, ordinal) == draw_cluster_index(
                ZERO_SEED, n_clusters, ordinal
            )
    assert draw_cluster_index(ZERO_SEED, 1, 0) == 0


def test_seed_derivation_golden():
    fingerprint = compute_input_fingerprint(
        as_of=AS_OF,
        population_key=KEY,
        horizon=HORIZON,
        ordered_input_manifest=FROZEN_GOLDEN_MANIFEST,
    )
    assert fingerprint == FROZEN_FINGERPRINT
    seed = bootstrap_seed(
        population_key=KEY, horizon=HORIZON, as_of=AS_OF, input_fingerprint=fingerprint
    )
    assert seed.hex() == FROZEN_SEED_HEX
    assert len(seed) == 32
    assert [draw_cluster_index(seed, 5, ordinal) for ordinal in range(10)] == (
        FROZEN_DRAWS_FROM_REAL_SEED
    )


def test_seed_changes_when_the_fingerprint_changes():
    first = bootstrap_seed(
        population_key=KEY, horizon=HORIZON, as_of=AS_OF, input_fingerprint="a" * 64
    )
    second = bootstrap_seed(
        population_key=KEY, horizon=HORIZON, as_of=AS_OF, input_fingerprint="b" * 64
    )
    assert first != second


# --- Bootstrap ----------------------------------------------------------------------------


def test_replicate_mean_is_sample_weighted_not_cluster_weighted():
    """A drawn cluster contributes all of its observations, with no re-weighting."""
    clusters = (_cluster(0, (0.0,)), _cluster(1, (1.0, 1.0, 1.0)))
    means = replicate_means(clusters=clusters, seed=ZERO_SEED, n_resamples=400)
    assert set(means) <= {0.0, 0.75, 1.0}
    # equal-weighting the two clusters would produce 0.5; sample weighting must not
    assert 0.5 not in means


def test_bootstrap_reproducibility():
    facts = _resolved_positive_facts()
    first = _aggregate(facts)
    second = _aggregate(list(reversed(facts)))
    assert first.uncertainty.lower == second.uncertainty.lower
    assert first.uncertainty.upper == second.uncertainty.upper
    assert first.uncertainty.seed_hex == second.uncertainty.seed_hex
    assert first.uncertainty.rng_algorithm_version == RNG_ALGORITHM_VERSION


def test_percentile_indices_match_the_frozen_quantile_rule():
    assert BOOTSTRAP_LOWER_INDEX == math.ceil(0.025 * BOOTSTRAP_REPLICATES) - 1
    assert BOOTSTRAP_UPPER_INDEX == math.ceil(0.975 * BOOTSTRAP_REPLICATES) - 1
    assert (BOOTSTRAP_LOWER_INDEX, BOOTSTRAP_UPPER_INDEX) == (249, 9749)
    assert BOOTSTRAP_REPLICATES == 10_000
    assert CONFIDENCE_LEVEL == "TWO_SIDED_95"


def test_exact_percentile_indices_select_ordered_replicate_means():
    clusters = (
        _cluster(0, (-0.10,)),
        _cluster(1, (0.01,)),
        _cluster(2, (0.10,)),
    )
    seed = bytes(range(32))
    interval = percentile_interval(clusters=clusters, seed=seed, n_resamples=10_000)
    ordered = sorted(replicate_means(clusters=clusters, seed=seed, n_resamples=10_000))
    assert interval.lower == ordered[249]
    assert interval.upper == ordered[9749]
    assert interval.lower_index == 249
    assert interval.upper_index == 9749
    assert interval.n_resamples == 10_000


def test_too_few_clusters_gives_null_interval():
    result = _aggregate([_fact("opp-01", start_offset_hours=1, return_value=0.05)])
    assert len(result.clusters) == 1
    assert MIN_CLUSTERS_FOR_INTERVAL == 2
    assert result.uncertainty.lower is None
    assert result.uncertainty.upper is None
    assert result.uncertainty.unavailable_reason is UncertaintyUnavailableReason.TOO_FEW_CLUSTERS
    assert result.uncertainty.side is None
    assert result.calculability is Calculability.CALCULABLE_DESCRIPTIVE_ONLY
    assert result.evidence_sufficient is False
    assert SufficiencyReason.NO_BOOTSTRAP_INTERVAL.value in result.sufficiency_reasons
    assert SufficiencyReason.TOO_FEW_CLUSTERS.value in result.sufficiency_reasons


def test_identical_returns_are_degenerate_not_high_certainty():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.03),
        _fact("opp-02", start_offset_hours=4, return_value=0.03),
        _fact("opp-03", start_offset_hours=7, return_value=0.03),
    ]
    result = _aggregate(facts)
    assert len(result.clusters) == 3
    assert result.uncertainty.lower is None
    assert result.uncertainty.upper is None
    assert result.uncertainty.unavailable_reason is UncertaintyUnavailableReason.DEGENERATE_SAMPLE
    assert result.evidence_sufficient is False
    assert SufficiencyReason.DEGENERATE_INTERVAL.value in result.sufficiency_reasons


def test_bootstrap_interval_for_two_clusters_is_available_but_not_sufficient():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.05),
        _fact("opp-02", start_offset_hours=4, return_value=0.07),
    ]
    result = _aggregate(facts)
    assert len(result.clusters) == 2
    assert result.uncertainty.lower is not None
    assert result.calculability is Calculability.CALCULABLE_WITH_UNCERTAINTY
    assert result.evidence_sufficient is False
    assert SufficiencyReason.TOO_FEW_CLUSTERS.value in result.sufficiency_reasons


# --- Evidence sufficiency / LOCO -------------------------------------------------------------


def test_resolved_positive_case_is_sufficient():
    result = _aggregate(_resolved_positive_facts())
    assert result.status is AggregateStatus.VALID
    assert result.uncertainty.side is IntervalSide.POSITIVE
    assert result.uncertainty.excludes_zero is True
    assert all(item.preserves_full_side for item in result.leave_one_cluster_out)
    assert result.evidence_sufficient is True
    assert result.sufficiency_reasons == ()
    assert result.coverage.coverage_rate == REQUIRED_COVERAGE_RATE
    assert len(result.clusters) >= MIN_CLUSTERS_FOR_SUFFICIENCY


def test_resolved_negative_case_is_sufficient():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=-0.05),
        _fact("opp-02", start_offset_hours=4, return_value=-0.06),
        _fact("opp-03", start_offset_hours=7, return_value=-0.07),
    ]
    result = _aggregate(facts)
    assert result.uncertainty.side is IntervalSide.NEGATIVE
    assert result.evidence_sufficient is True
    assert result.sufficiency_reasons == ()


def test_coverage_below_one_is_insufficient():
    facts = [
        *_resolved_positive_facts(),
        _fact("opp-04", start_offset_hours=10, status=None),
    ]
    result = _aggregate(facts)
    assert result.status is AggregateStatus.VALID
    assert result.coverage.coverage_rate == pytest.approx(0.75)
    assert result.evidence_sufficient is False
    assert result.sufficiency_reasons == (SufficiencyReason.COVERAGE_BELOW_ONE.value,)


def test_interval_crossing_zero_is_insufficient():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=-0.10),
        _fact("opp-02", start_offset_hours=4, return_value=0.01),
        _fact("opp-03", start_offset_hours=7, return_value=0.10),
    ]
    result = _aggregate(facts)
    assert result.uncertainty.lower < 0.0 < result.uncertainty.upper
    assert result.uncertainty.side is None
    assert result.uncertainty.excludes_zero is False
    assert result.evidence_sufficient is False
    assert SufficiencyReason.INTERVAL_CONTAINS_ZERO.value in result.sufficiency_reasons


def test_loco_instability_is_insufficient():
    """The full interval is positive, but removing one cluster is degenerate."""
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.02),
        _fact("opp-02", start_offset_hours=4, return_value=0.02),
        _fact("opp-03", start_offset_hours=7, return_value=0.20),
    ]
    result = _aggregate(facts)
    assert result.uncertainty.side is IntervalSide.POSITIVE
    unstable = [item for item in result.leave_one_cluster_out if not item.preserves_full_side]
    assert len(unstable) == 1
    assert unstable[0].interval.side is None
    assert result.evidence_sufficient is False
    assert SufficiencyReason.LEAVE_ONE_CLUSTER_OUT_UNSTABLE.value in result.sufficiency_reasons


def test_loco_recomputes_uncertainty_for_every_cluster():
    result = _aggregate(_resolved_positive_facts())
    assert len(result.leave_one_cluster_out) == len(result.clusters)
    assert [item.removed_cluster_id for item in result.leave_one_cluster_out] == [0, 1, 2]
    for item in result.leave_one_cluster_out:
        assert item.remaining_cluster_count == len(result.clusters) - 1
        assert item.interval.lower is not None


def test_loco_is_deterministic():
    facts = _resolved_positive_facts()
    first = _aggregate(facts)
    second = _aggregate(facts)
    assert first.leave_one_cluster_out == second.leave_one_cluster_out


# --- Determinism / permutation invariance ------------------------------------------------------


def test_input_permutation_invariance():
    facts = _resolved_positive_facts()
    forward = _aggregate(facts).to_dict()
    backward = _aggregate(list(reversed(facts))).to_dict()
    assert forward == backward


def test_input_permutation_invariance_with_integrity_conflict():
    facts = [
        _fact("opp-01", start_offset_hours=1, return_value=0.05),
        _fact("opp-02", start_offset_hours=4, return_value=None),
    ]
    forward = _aggregate(facts).to_dict()
    backward = _aggregate(list(reversed(facts))).to_dict()
    assert forward == backward


def test_repeated_call_is_byte_identical():
    facts = _resolved_positive_facts()
    assert json.dumps(_aggregate(facts).to_dict(), sort_keys=True) == json.dumps(
        _aggregate(facts).to_dict(), sort_keys=True
    )


def test_sample_ordering_is_lexical_ascending():
    facts = [
        _fact("opp-c", start_offset_hours=1, return_value=0.05),
        _fact("opp-a", start_offset_hours=4, return_value=0.06),
        _fact("opp-b", start_offset_hours=7, return_value=0.07),
    ]
    result = _aggregate(facts)
    identifiers = [entry["opportunity_id"] for entry in result.input_manifest]
    assert identifiers == sorted(identifiers)


# --- Manifest / fingerprint ------------------------------------------------------------------


def test_fingerprint_reproducibility():
    facts = _resolved_positive_facts()
    first = _aggregate(facts)
    second = _aggregate(facts)
    assert first.input_fingerprint == second.input_fingerprint
    assert len(first.input_fingerprint) == 64
    assert first.input_fingerprint == compute_input_fingerprint(
        as_of=AS_OF,
        population_key=KEY,
        horizon=HORIZON,
        ordered_input_manifest=first.input_manifest,
    )


def test_fingerprint_manifest_sensitivity():
    baseline = _aggregate(_resolved_positive_facts())
    mutated = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=0.05, source_manifest_id="m-9"),
            _fact("opp-02", start_offset_hours=4, return_value=0.06),
            _fact("opp-03", start_offset_hours=7, return_value=0.07),
        ]
    )
    assert baseline.input_fingerprint != mutated.input_fingerprint


def test_fingerprint_binds_the_return_bits():
    baseline = _aggregate(_resolved_positive_facts())
    mutated = _aggregate(
        [
            _fact("opp-01", start_offset_hours=1, return_value=0.05000000000000001),
            _fact("opp-02", start_offset_hours=4, return_value=0.06),
            _fact("opp-03", start_offset_hours=7, return_value=0.07),
        ]
    )
    assert baseline.input_fingerprint != mutated.input_fingerprint


def test_fingerprint_rejects_non_finite_canonical_data():
    with pytest.raises(ValueError):
        compute_input_fingerprint(
            as_of=AS_OF,
            population_key=KEY,
            horizon=HORIZON,
            ordered_input_manifest=[{"cost_adjusted_forward_return": float("nan")}],
        )


def test_caller_supplied_manifest_is_used_verbatim():
    supplied = ({"opportunity_id": "supplied"},)
    baseline = _aggregate(_resolved_positive_facts())
    with_supplied = _aggregate(_resolved_positive_facts(), ordered_input_manifest=supplied)
    assert with_supplied.input_manifest == supplied
    assert with_supplied.input_fingerprint != baseline.input_fingerprint
    assert with_supplied.input_fingerprint == compute_input_fingerprint(
        as_of=AS_OF,
        population_key=KEY,
        horizon=HORIZON,
        ordered_input_manifest=supplied,
    )


def test_manifest_records_hex_return_representation():
    result = _aggregate([_fact("opp-01", start_offset_hours=1, return_value=0.05)])
    entry = result.input_manifest[0]
    assert entry["cost_adjusted_forward_return_hex"] == (0.05).hex()
    assert entry["maturity_marker"] == MaturityClass.COMPLETE.value
    assert entry["evidence_role"] == "CANONICAL"
    assert entry["measurement_signature"] != "NO_MEASUREMENT"


def test_manifest_records_no_measurement_marker():
    manifest = build_ordered_input_manifest(
        [_fact("opp-01", start_offset_hours=1, status=None)], as_of=AS_OF
    )
    entry = manifest[0]
    assert entry["measurement_signature"] == "NO_MEASUREMENT"
    assert entry["maturity_marker"] == MaturityClass.MISSING_OUTCOME.value
    assert entry["cost_adjusted_forward_return_hex"] is None


# --- Version constants / boundaries -----------------------------------------------------------


def test_version_constants_match_the_accepted_literals():
    assert AGGREGATION_CONTRACT_VERSION == "se02d-family-aggregation-v1"
    assert RNG_ALGORITHM_VERSION == "SHA256_COUNTER_REJECTION_V1"
    assert UNCERTAINTY_METHOD_VERSION == "se02d-overlap-cluster-percentile-bootstrap-v1"
    assert VISIBILITY_MODE == "CURRENT_STABLE_SNAPSHOT"


def test_result_declares_limitations_an_integrity_statement_and_no_regime_gate():
    result = _aggregate(_resolved_positive_facts())
    assert result.limitations == DEPENDENCE_LIMITATIONS
    assert result.integrity_statement == INTEGRITY_STATEMENT
    assert result.regime_gate == REGIME_GATE == "NONE_IN_SE02D_V1"
    assert result.regime_sufficiency == REGIME_SUFFICIENCY == "NOT_EVALUABLE"
    assert result.unobservable_coverage_limitations != ()
    assert result.visibility_mode == VISIBILITY_MODE


def test_result_reports_the_frozen_version_constants():
    result = _aggregate(_resolved_positive_facts())
    assert result.aggregation_contract_version == AGGREGATION_CONTRACT_VERSION
    assert result.uncertainty_method_version == UNCERTAINTY_METHOD_VERSION
    assert result.rng_algorithm_version == RNG_ALGORITHM_VERSION


def test_no_keep_downweight_kill_output():
    result = _aggregate(_resolved_positive_facts())
    serialized = json.dumps(result.to_dict(), sort_keys=True).upper()
    for token in ("KEEP", "DOWNWEIGHT", "KILL"):
        assert token not in serialized
    names = {field.name for field in dataclasses.fields(result)}
    for token in ("keep", "downweight", "kill", "decision", "action", "threshold"):
        assert token not in names


def test_module_has_no_direct_database_or_runtime_imports():
    tree = ast.parse(AGGREGATION_SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for name in imported:
        assert not name.startswith(
            ("sqlalchemy", "asyncpg", "fastapi", "marketpulse.db", "marketpulse.g5")
        ), f"forbidden direct import: {name}"
    assert "async_sessionmaker" not in imported
    source = AGGREGATION_SOURCE.read_text(encoding="utf-8")
    for forbidden in ("AsyncSession", "create_async_engine", "async_sessionmaker", "FastAPI"):
        assert forbidden not in source


def test_result_object_is_serializable_and_immutable():
    result = _aggregate(_resolved_positive_facts())
    payload = json.dumps(result.to_dict(), sort_keys=True, allow_nan=False)
    assert "aggregation_contract_version" in payload
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = AggregateStatus.NOT_CALCULABLE


def test_result_exposes_the_population_aggregate_identity():
    result = _aggregate(_resolved_positive_facts())
    assert result.population_key == KEY
    assert result.horizon is HORIZON
    assert result.identity == result.identity
    assert result.identity.population_key == KEY
    assert result.identity.horizon is HORIZON


def test_aggregation_module_is_reachable_through_the_package():
    assert aggregation_module.AGGREGATION_CONTRACT_VERSION == AGGREGATION_CONTRACT_VERSION


# --- SE-02D-I01-FIX-01 regression coverage ---------------------------------------------------
#
# Independent Review returned ``FAIL — FIX REQUIRED`` with three P1 findings:
#
#   SE02D-I01-R1  Measurement Signature identity encoding is non-injective
#   SE02D-I01-R2  headline arithmetic order violated the accepted sample_id order
#   SE02D-I01-R3  generated canonical input manifest omitted the Population Key
#
# Every test in this section fails against the reviewed pre-FIX implementation.

# Adversarial delimiter-injection pair: all six fields identical except for how one
# ``|`` / ``=`` sequence is split across ``cost_policy`` / ``cost_model_version``.
_COLLIDING_A = MeasurementSignature(
    outcome_contract_version="se02-outcome-v1",
    calculator_version="se02c-forward-outcome-v1",
    cost_policy="P|cost_model_version=Q",
    cost_model_version="R",
    outcome_source_type=EvidenceSource.FORWARD_PAPER,
    outcome_source_identity=SOURCE_IDENTITY,
)
_COLLIDING_B = MeasurementSignature(
    outcome_contract_version="se02-outcome-v1",
    calculator_version="se02c-forward-outcome-v1",
    cost_policy="P",
    cost_model_version="Q|cost_model_version=R",
    outcome_source_type=EvidenceSource.FORWARD_PAPER,
    outcome_source_identity=SOURCE_IDENTITY,
)

# Adversarial Population Key pair: all seven fields identical except for how the same
# delimiter sequence is split across ``family_version`` / ``instrument_id``.
_KEY_COLLIDING_A = _key(family_version="g2-v1|instrument_id=X", instrument_id="Y")
_KEY_COLLIDING_B = _key(family_version="g2-v1", instrument_id="X|instrument_id=Y")

# Post-FIX-01 frozen chain for the *generated* manifest over
# ``_resolved_positive_facts()`` with ``AS_OF`` / ``HORIZON``. Recording the R3
# Population Key in every generated entry changes the fingerprint, therefore the
# bootstrap seed and every draw taken from that seed.
FROZEN_GENERATED_FINGERPRINT = "4d6f2b40b46fa912f14de87f3d2a79d3f2382171d344e17a9a3bb289f6b73855"
FROZEN_GENERATED_SEED_HEX = "fc206f667e0a1b571ab5b36a588946aaaaf909c666fd4280a4ca1b5109e894b8"
FROZEN_GENERATED_DRAWS_N3 = [0, 1, 2, 1, 0, 2, 1, 1, 2, 0]
# Same fixtures with the R3 field stripped again, i.e. the reviewed pre-FIX shape.
FROZEN_PRE_FIX_SHAPE_FINGERPRINT = (
    "6b1808df759d45275a9ec9b6c2a6b94d887aa2881174d3c7e95ef810216511eb"
)
FROZEN_PRE_FIX_SHAPE_SEED_HEX = (
    "e670ea2e47ad7d53c1f51162331ea5614652a4efe55afecc6ae2234a95013e4a"
)


def _capture_fsum_operand_orders(call, *, limit):
    """Run ``call`` with ``math.fsum`` spied on; return the first ``limit`` operand orders."""

    observed: list[list[float]] = []
    real_fsum = math.fsum

    def spy(sequence):
        materialised = [float(value) for value in sequence]
        if len(observed) < limit:
            observed.append(materialised)
        return real_fsum(materialised)

    math.fsum = spy
    try:
        call()
    finally:
        math.fsum = real_fsum
    return observed


# --- R1: structural identity + collision-safe diagnostics ------------------------------------


def test_r1_structural_fields_are_the_signature_equality_authority():
    assert _COLLIDING_A != _COLLIDING_B
    assert hash(_COLLIDING_A) != hash(_COLLIDING_B)
    assert _signature() == SIGNATURE
    assert hash(_signature()) == hash(SIGNATURE)


def test_r1_diagnostic_key_is_collision_safe_and_lossless():
    left = _COLLIDING_A.canonical_key()
    right = _COLLIDING_B.canonical_key()
    assert left != right
    assert left == canonical_bytes(_COLLIDING_A.canonical_payload()).hex()
    assert right == canonical_bytes(_COLLIDING_B.canonical_payload()).hex()
    # Same six-field payload -> same diagnostic key.
    assert _signature().canonical_key() == SIGNATURE.canonical_key()
    # The representation carries no unescaped delimiter of its own.
    for rendered in (left, right):
        assert "|" not in rendered
        assert "=" not in rendered


def test_r1_adversarial_delimiter_collision_fails_closed():
    facts = [
        _fact("opp-1", start_offset_hours=1, return_value=0.10, signature=_COLLIDING_A),
        _fact("opp-2", start_offset_hours=4, return_value=-0.05, signature=_COLLIDING_B),
    ]
    result = _aggregate(facts)

    assert result.status is AggregateStatus.INCOMPATIBLE_MEASUREMENT_SIGNATURES
    assert result.measurement_signature_state is MeasurementSignatureState.MIXED
    assert result.measurement_signature is None
    assert result.statistics is None
    assert result.tail_risk is None
    assert result.uncertainty is None
    assert result.evidence_sufficient is False
    assert (
        SufficiencyReason.INCOMPATIBLE_MEASUREMENT_SIGNATURES.value
        in result.sufficiency_reasons
    )

    # Coverage is still reported in full, with both signatures visible as separate buckets.
    assert result.coverage.complete == 2
    assert result.coverage.mature_denominator == 2
    counts = result.coverage.measurement_signature_counts
    assert len(counts) == 2
    assert sorted(counts.values()) == [1, 1]
    assert set(counts) == {
        _COLLIDING_A.canonical_key(),
        _COLLIDING_B.canonical_key(),
    }


def test_r1_population_key_derived_key_is_collision_safe():
    assert _KEY_COLLIDING_A != _KEY_COLLIDING_B
    assert _KEY_COLLIDING_A.canonical_key() != _KEY_COLLIDING_B.canonical_key()
    assert _KEY_COLLIDING_A.canonical_key() == canonical_bytes(
        _KEY_COLLIDING_A.canonical_payload()
    ).hex()
    assert _KEY_COLLIDING_B.canonical_key() == canonical_bytes(
        _KEY_COLLIDING_B.canonical_payload()
    ).hex()
    # Structurally equal keys still share one derived rendering.
    assert _key().canonical_key() == KEY.canonical_key()
    # The frozen field set is unchanged.
    assert tuple(_KEY_COLLIDING_A.canonical_payload()) == (
        "family_id",
        "family_version",
        "instrument_id",
        "market_type",
        "source_type",
        "source_identity",
        "evidence_contract_version",
    )


def test_r1_sample_id_is_collision_safe():
    shared_opportunity = "opp-shared"
    first = _fact(shared_opportunity, start_offset_hours=1, key=_KEY_COLLIDING_A)
    second = _fact(shared_opportunity, start_offset_hours=1, key=_KEY_COLLIDING_B)

    assert sample_identity(first) != sample_identity(second)
    assert first.sample_id != second.sample_id
    assert "\n" not in first.sample_id


# --- R2: accepted arithmetic order -----------------------------------------------------------


def test_r2_economic_statistics_accumulates_in_caller_order():
    orders = _capture_fsum_operand_orders(
        lambda: economic_statistics((0.5, 0.001, 0.2)), limit=3
    )
    # 1) the headline mean accumulates the returns in the caller (sample) order.
    assert orders[0] == [0.5, 0.001, 0.2]
    # 2) the variance accumulation also walks the caller order; its operands are the
    #    squared deviations, so the sequence must follow 0.5, 0.001, 0.2 and must not
    #    be the value-sorted alternative.
    mean = math.fsum((0.5, 0.001, 0.2)) / 3
    deviations = [(0.5 - mean) ** 2, (0.001 - mean) ** 2, (0.2 - mean) ** 2]
    assert orders[1] == deviations
    assert orders[1] != sorted(deviations)
    # 3) the worst-decile mean is an order statistic: value order is used only here.
    assert orders[2] == [0.001]


def test_r2_value_sorting_is_limited_to_order_statistics():
    returns = (0.5, 0.001, 0.2)
    stats = economic_statistics(returns)

    assert stats.n_economic_samples == 3
    # Arithmetic tied to the accepted sample order.
    assert stats.mean == math.fsum(returns) / 3
    assert stats.positive_count == 3
    assert stats.flat_count == 0
    assert stats.negative_count == 0
    assert stats.positive_rate == 1.0
    # Order statistics follow value order, which differs from the sample order above.
    assert stats.median == 0.2
    assert stats.worst_observation == 0.001
    assert stats.worst_decile_mean == 0.001


def test_r2_headline_fsum_uses_sample_id_lexical_order():
    facts = [
        _fact("opp-a", start_offset_hours=1, return_value=0.5),
        _fact("opp-b", start_offset_hours=4, return_value=0.001),
        _fact("opp-c", start_offset_hours=7, return_value=0.2),
    ]
    orders = _capture_fsum_operand_orders(lambda: _aggregate(facts), limit=1)
    assert orders[0] == [0.5, 0.001, 0.2]


def test_r2_accumulation_order_is_independent_of_caller_order():
    facts = [
        _fact("opp-a", start_offset_hours=1, return_value=0.5),
        _fact("opp-b", start_offset_hours=4, return_value=0.001),
        _fact("opp-c", start_offset_hours=7, return_value=0.2),
    ]
    forward = _capture_fsum_operand_orders(lambda: _aggregate(list(facts)), limit=1)
    backward = _capture_fsum_operand_orders(
        lambda: _aggregate(list(reversed(facts))), limit=1
    )
    assert forward == backward
    assert forward[0] == [0.5, 0.001, 0.2]


# --- R3: manifest Population Key + regenerated golden chain ----------------------------------


def test_r3_generated_manifest_records_population_key_and_horizon():
    result = _aggregate(_resolved_positive_facts())
    assert result.input_manifest
    for entry in result.input_manifest:
        assert entry["population_key"] == KEY.canonical_payload()
        assert entry["horizon"] == HORIZON.value


def test_r3_manifest_population_key_reuses_canonical_payload():
    manifest = build_ordered_input_manifest(_resolved_positive_facts(), as_of=AS_OF)
    entry = manifest[0]
    assert entry["population_key"] == KEY.canonical_payload()
    assert set(entry["population_key"]) == {
        "family_id",
        "family_version",
        "instrument_id",
        "market_type",
        "source_type",
        "source_identity",
        "evidence_contract_version",
    }
    assert "source_manifest_id" not in entry["population_key"]


def test_r3_top_level_fingerprint_payload_still_carries_population_key():
    facts = _resolved_positive_facts()
    result = _aggregate(facts)
    stripped = tuple(
        {key: value for key, value in entry.items() if key != "population_key"}
        for entry in result.input_manifest
    )
    # Dropping only the *entry-level* key does not drop the top-level one.
    assert compute_input_fingerprint(
        as_of=AS_OF,
        population_key=KEY,
        horizon=HORIZON,
        ordered_input_manifest=stripped,
    ) == FROZEN_PRE_FIX_SHAPE_FINGERPRINT


def test_r3_population_key_changes_fingerprint_and_seed():
    result = _aggregate(_resolved_positive_facts())
    stripped = tuple(
        {key: value for key, value in entry.items() if key != "population_key"}
        for entry in result.input_manifest
    )
    pre_fix_fingerprint = compute_input_fingerprint(
        as_of=AS_OF,
        population_key=KEY,
        horizon=HORIZON,
        ordered_input_manifest=stripped,
    )
    assert pre_fix_fingerprint != result.input_fingerprint
    assert pre_fix_fingerprint == FROZEN_PRE_FIX_SHAPE_FINGERPRINT
    assert FROZEN_PRE_FIX_SHAPE_FINGERPRINT != FROZEN_GENERATED_FINGERPRINT

    pre_fix_seed = bootstrap_seed(
        population_key=KEY,
        horizon=HORIZON,
        as_of=AS_OF,
        input_fingerprint=pre_fix_fingerprint,
    )
    assert pre_fix_seed.hex() == FROZEN_PRE_FIX_SHAPE_SEED_HEX
    assert pre_fix_seed.hex() != FROZEN_GENERATED_SEED_HEX


def test_r3_golden_vectors_are_pinned():
    result = _aggregate(_resolved_positive_facts())
    assert result.input_fingerprint == FROZEN_GENERATED_FINGERPRINT

    seed = bootstrap_seed(
        population_key=KEY,
        horizon=HORIZON,
        as_of=AS_OF,
        input_fingerprint=result.input_fingerprint,
    )
    assert seed.hex() == FROZEN_GENERATED_SEED_HEX
    assert len(result.clusters) == 3
    assert [
        draw_cluster_index(seed, 3, ordinal) for ordinal in range(len(FROZEN_GENERATED_DRAWS_N3))
    ] == FROZEN_GENERATED_DRAWS_N3
    # The RNG algorithm itself is unchanged (D01 section 10.1 item 7).
    assert RNG_ALGORITHM_VERSION == "SHA256_COUNTER_REJECTION_V1"
    assert [draw_cluster_index(ZERO_SEED, 3, ordinal) for ordinal in range(12)] == FROZEN_DRAWS_N3
