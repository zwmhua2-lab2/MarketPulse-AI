"""SE-02C Forward Outcome Calculator: pure, deterministic calculation core.

No database, no runtime and no persistence is exercised here -- this file pins
the frozen V1 calculator policy itself:

* the exact required formula vector (task §53);
* the terminal classification matrix (task §54);
* the causal rules (task §55) at the level where they are owned;
* digest / record-hash separation for Historical Replay vs Forward Paper (§52);
* the frozen endpoint tie-break (§22) and the four independent horizons (§49).
"""

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from marketpulse.edge import forward as forward_module
from marketpulse.edge.forward import (
    ALL_FORWARD_HORIZONS,
    CALCULATOR_VERSION,
    COST_MODEL_VERSION,
    COST_POLICY,
    END_FRESHNESS_TTL,
    FEE_RATE,
    SLIPPAGE_BPS,
    SLIPPAGE_FRACTION,
    ForwardOutcomeReason,
    ForwardReference,
    ForwardScopeFacts,
    calculate_forward_outcome,
    classify_forward_observations,
    cost_adjusted_forward_return,
    forward_due_at,
    is_forward_due,
)
from marketpulse.edge.models import (
    BboObservation,
    EvidenceSource,
    ForwardHorizon,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_bbo_observation,
)
from marketpulse.market_data.models import DataQuality, MarketType

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
INSTRUMENT = "BTC-USDT"
OTHER_INSTRUMENT = "ETH-USDT"
SESSION_EXPIRY = timedelta(minutes=20)


# --- fixtures ---------------------------------------------------------------------------


def _observation(
    *,
    bid: float,
    ask: float,
    available_at: datetime,
    instrument_id: str = INSTRUMENT,
    market_type: MarketType = MarketType.SPOT,
    data_quality: DataQuality = DataQuality.FRESH,
    tradable: bool = True,
    source: str = "fixture-bbo",
    source_sequence: int | None = None,
    source_event_time: datetime | None = None,
    source_offset_seconds: int = 1,
) -> BboObservation:
    return build_bbo_observation(
        instrument_id=instrument_id,
        market_type=market_type,
        bid=bid,
        ask=ask,
        available_at=available_at,
        source_event_time=(
            available_at - timedelta(seconds=source_offset_seconds)
            if source_event_time is None
            else source_event_time
        ),
        received_at=available_at,
        data_quality=data_quality,
        tradable=tradable,
        source=source,
        source_sequence=source_sequence,
        created_at=available_at,
    )


def _reference_observation(
    *, bid: float = 99.0, ask: float = 101.0, at: datetime = START
) -> BboObservation:
    return _observation(bid=bid, ask=ask, available_at=at, source_sequence=None)


def _ok_reference(reference: BboObservation | None = None) -> ForwardReference:
    observation = _reference_observation() if reference is None else reference
    return ForwardReference(
        status=ReferenceDataStatus.OK,
        bid=observation.bid,
        ask=observation.ask,
        observation_id=observation.observation_id,
        observation_instrument_id=observation.instrument_id,
        observation_market_type=observation.market_type,
    )


def _scope(
    *,
    horizon: ForwardHorizon = ForwardHorizon.M5,
    evidence_at: datetime = START,
    expires_at: datetime | None = None,
    source_type: EvidenceSource = EvidenceSource.FORWARD_PAPER,
    source_identity: str = "okx-ws-bbo",
    instrument_id: str = INSTRUMENT,
    market_type: MarketType = MarketType.SPOT,
) -> ForwardScopeFacts:
    return ForwardScopeFacts(
        opportunity_id="op-" + horizon.value,
        evidence_id="ev-" + horizon.value,
        horizon=horizon,
        evidence_at=evidence_at,
        expires_at=expires_at or (evidence_at + SESSION_EXPIRY),
        instrument_id=instrument_id,
        market_type=market_type,
        source_type=source_type,
        source_identity=source_identity,
    )


# --- §53 required formula vector ---------------------------------------------------------


def test_required_formula_vector_matches_the_frozen_specification():
    """The exact deterministic vector the task prescribes (task §53)."""

    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _reference_observation(bid=99.0, ask=101.0, at=START)
    path = (
        _observation(bid=101.0, ask=103.0, available_at=START + timedelta(seconds=1)),
        _observation(bid=97.0, ask=99.0, available_at=START + timedelta(seconds=2)),
        _observation(bid=103.0, ask=105.0, available_at=START + timedelta(seconds=295)),
    )

    outcome = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(reference), observations=path
    )

    assert outcome.calculation_status is OutcomeCalculationStatus.COMPLETE
    assert outcome.due_at == START + timedelta(minutes=5)
    assert outcome.reference_bbo_observation_id == reference.observation_id
    assert outcome.end_bbo_observation_id == path[-1].observation_id

    assert outcome.reference_price == pytest.approx(100.0, rel=1e-12)
    assert outcome.end_bid == pytest.approx(103.0, rel=1e-12)
    assert outcome.end_ask == pytest.approx(105.0, rel=1e-12)
    assert outcome.mfe == pytest.approx(0.04, rel=1e-12)
    assert outcome.mae == pytest.approx(-0.02, rel=1e-12)
    assert outcome.reference_return == pytest.approx(104 / 100 - 1, rel=1e-12)
    assert outcome.executable_long_return == pytest.approx(103 / 101 - 1, rel=1e-12)

    entry_exec = 101 * 1.0005
    exit_exec = 103 * 0.9995
    assert outcome.cost_adjusted_forward_return == pytest.approx(
        (exit_exec * 0.999) / (entry_exec * 1.001) - 1, rel=1e-12
    )

    assert outcome.calculator_version == CALCULATOR_VERSION
    assert outcome.cost_policy == COST_POLICY
    assert outcome.cost_model_version == COST_MODEL_VERSION
    assert outcome.outcome_revision == 1
    assert outcome.supersedes_outcome_id is None
    assert outcome.created_at == outcome.due_at


def test_cost_model_is_exact_multiplicative_not_an_approximation():
    """The frozen cost model is exact, so it cannot be replaced by fee subtraction (§36)."""

    assert FEE_RATE == 0.001
    assert SLIPPAGE_BPS == 5
    assert SLIPPAGE_FRACTION == 0.0005

    exact = cost_adjusted_forward_return(reference_ask=101.0, end_bid=103.0)
    approximate = (103.0 / 101.0 - 1) - 2 * FEE_RATE - 2 * SLIPPAGE_FRACTION
    assert abs(exact - approximate) > 1e-9

    expected = ((103 * 0.9995) * (1 - FEE_RATE)) / ((101 * 1.0005) * (1 + FEE_RATE)) - 1
    assert exact == pytest.approx(expected, rel=1e-12)


def test_mfe_and_mae_are_market_excursion_bounds_including_the_reference_point():
    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _reference_observation(bid=99.0, ask=101.0)
    # A path that never leaves the reference level must still yield 0 / 0.
    flat = (_observation(bid=99.0, ask=101.0, available_at=START + timedelta(seconds=299)),)
    flat_outcome = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(reference), observations=flat
    )
    assert flat_outcome.mfe == 0.0
    assert flat_outcome.mae == 0.0

    # An all-below-reference path keeps MAE negative and never takes abs().
    below = (
        _observation(bid=94.0, ask=96.0, available_at=START + timedelta(seconds=100)),
        _observation(bid=95.0, ask=97.0, available_at=START + timedelta(seconds=299)),
    )
    below_outcome = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(reference), observations=below
    )
    # MAE is a whole-path bound: the deepest point is the earliest mid (95 -> -0.05),
    # not the shallower terminal mid (96 -> -0.04).
    assert below_outcome.mfe == 0.0
    assert below_outcome.mae == pytest.approx(95 / 100 - 1, rel=1e-12)
    assert below_outcome.mae == min(0.0, 95 / 100 - 1, 96 / 100 - 1)
    assert below_outcome.mae < 0


# --- §21 / §22 endpoint selection --------------------------------------------------------


def test_endpoint_is_the_greatest_available_at_among_eligible_observations():
    scope = _scope(horizon=ForwardHorizon.M5)
    early = _observation(bid=101.0, ask=103.0, available_at=START + timedelta(seconds=10))
    middle = _observation(bid=102.0, ask=104.0, available_at=START + timedelta(seconds=20))
    latest = _observation(bid=103.0, ask=105.0, available_at=START + timedelta(seconds=299))

    outcome = calculate_forward_outcome(
        scope=scope,
        reference=_ok_reference(),
        observations=(middle, latest, early),
    )
    assert outcome.end_bbo_observation_id == latest.observation_id
    assert outcome.end_bid == latest.bid
    assert outcome.end_ask == latest.ask


def test_endpoint_tie_break_prefers_source_sequence_then_lexical_observation_id():
    """The frozen tie-break order must be directly tested (task §22)."""

    scope = _scope(horizon=ForwardHorizon.M5)
    at = START + timedelta(seconds=299)

    # 1. Same available_at, no comparable source_sequence on either side: the
    #    greater observation id wins, which is deterministic because the id is a
    #    content-addressed hash of the observation's own facts.
    a = _observation(bid=103.0, ask=105.0, available_at=at, source_sequence=None)
    b = _observation(bid=104.0, ask=106.0, available_at=at, source_sequence=None)
    expected = max(a.observation_id, b.observation_id)
    selected = classify_forward_observations(scope=scope, observations=[a, b]).endpoint
    assert selected is not None and selected.observation_id == expected

    # 2. One side carries a comparable source_sequence: that side wins over the
    #    side without one, regardless of the two observation ids.
    c = _observation(bid=107.0, ask=109.0, available_at=at, source_sequence=7)
    d = _observation(bid=110.0, ask=112.0, available_at=at, source_sequence=None)
    tie = classify_forward_observations(scope=scope, observations=[c, d]).endpoint
    assert tie is not None and tie.observation_id == c.observation_id
    reverse = classify_forward_observations(scope=scope, observations=[d, c]).endpoint
    assert reverse is not None and reverse.observation_id == c.observation_id

    # 3. Both sides carry a source_sequence: the greater sequence wins.
    e = _observation(bid=113.0, ask=115.0, available_at=at, source_sequence=7)
    f = _observation(bid=116.0, ask=118.0, available_at=at, source_sequence=9)
    greater = classify_forward_observations(scope=scope, observations=[e, f]).endpoint
    assert greater is not None and greater.observation_id == f.observation_id


# --- §23 endpoint freshness -------------------------------------------------------------


def test_endpoint_freshness_ttl_is_five_seconds_and_excludes_an_older_endpoint():
    assert END_FRESHNESS_TTL == timedelta(seconds=5)
    scope = _scope(horizon=ForwardHorizon.M5)

    exactly_five = _observation(
        bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=5)
    )
    fresh = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(exactly_five,)
    )
    assert fresh.calculation_status is OutcomeCalculationStatus.COMPLETE
    assert fresh.completeness_diagnostics["end_age_seconds"] == 5.0

    six_seconds = _observation(
        bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=6)
    )
    stale = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(six_seconds,)
    )
    assert stale.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA
    assert stale.completeness_diagnostics["reason"] == ForwardOutcomeReason.ENDPOINT_STALE.value
    assert stale.end_bbo_observation_id is None
    assert stale.end_bid is None and stale.end_ask is None
    assert stale.mfe is None and stale.mae is None


def test_endpoint_freshness_never_reads_a_mutable_runtime_setting():
    """The 5-second TTL is versioned calculator policy, not a runtime read."""

    assert forward_module.END_FRESHNESS_TTL == timedelta(seconds=5)
    source = Path(forward_module.__file__).read_text(encoding="utf-8")
    assert source.count("END_FRESHNESS_TTL = timedelta(seconds=5)") == 1
    assert "get_settings" not in source
    assert "Settings" not in source


# --- §19 / §20 / §48 eligibility and causality ------------------------------------------


def test_eligibility_requires_the_exact_market_identity_fresh_quality_and_tradability():
    scope = _scope(horizon=ForwardHorizon.M5)
    at = START + timedelta(seconds=299)
    selection = classify_forward_observations(
        scope=scope,
        observations=[
            _observation(bid=1.0, ask=2.0, available_at=at, instrument_id=OTHER_INSTRUMENT),
            _observation(bid=1.0, ask=2.0, available_at=at, market_type=MarketType.SWAP),
            _observation(bid=1.0, ask=2.0, available_at=at, data_quality=DataQuality.STALE),
            _observation(bid=1.0, ask=2.0, available_at=at, data_quality=DataQuality.UNAVAILABLE),
            _observation(bid=1.0, ask=2.0, available_at=at, tradable=False),
            _observation(bid=103.0, ask=105.0, available_at=at),
        ],
    )
    assert selection.total == 6
    assert selection.excluded_identity == 2
    assert selection.excluded_stale == 2
    assert selection.excluded_untradable == 1
    assert selection.excluded_causal == 0
    assert len(selection.eligible) == 1


def test_late_arrival_with_an_old_source_time_is_excluded_by_the_available_at_cutoff():
    """Task §48: the causal cutoff is ``available_at``, never ``source_event_time``."""

    scope = _scope(horizon=ForwardHorizon.M5)
    due_at = scope.due_at
    late = _observation(
        bid=1_000.0,
        ask=1_001.0,
        available_at=due_at + timedelta(seconds=2),
        source_event_time=due_at - timedelta(seconds=1),
    )
    assert late.source_event_time < due_at < late.available_at

    selection = classify_forward_observations(scope=scope, observations=[late])
    assert selection.eligible == ()
    assert selection.excluded_causal == 1

    outcome = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(late,)
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA
    assert outcome.end_bbo_observation_id is None
    assert outcome.end_bid is None


def test_future_observation_never_influences_a_complete_outcome():
    scope = _scope(horizon=ForwardHorizon.M5)
    honest = _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1))
    future = _observation(
        bid=9_999.0, ask=10_000.0, available_at=scope.due_at + timedelta(seconds=1)
    )

    without_future = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(honest,)
    )
    with_future = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(honest, future)
    )
    assert with_future.end_bbo_observation_id == without_future.end_bbo_observation_id
    assert with_future.executable_long_return == without_future.executable_long_return
    assert with_future.reference_return == without_future.reference_return
    assert (
        with_future.completeness_diagnostics["excluded_causal_count"]
        == without_future.completeness_diagnostics["excluded_causal_count"] + 1
    )


# --- §10 / §11 due and pending -----------------------------------------------------------


def test_due_at_is_a_pure_function_of_the_evidence_anchor_and_the_horizon():
    assert forward_due_at(START, ForwardHorizon.S30) == START + timedelta(seconds=30)
    assert forward_due_at(START, ForwardHorizon.M5) == START + timedelta(minutes=5)
    assert forward_due_at(START, ForwardHorizon.M15) == START + timedelta(minutes=15)
    assert forward_due_at(START, ForwardHorizon.H1) == START + timedelta(hours=1)


def test_pending_is_derived_state_and_never_a_terminal_status():
    assert {status.value for status in OutcomeCalculationStatus} == {
        "COMPLETE",
        "INSUFFICIENT_DATA",
        "INVALID",
    }
    scope = _scope(horizon=ForwardHorizon.M5)
    assert (
        is_forward_due(
            evidence_at=START, horizon=scope.horizon, now=scope.due_at - timedelta(seconds=1)
        )
        is False
    )
    assert is_forward_due(evidence_at=START, horizon=scope.horizon, now=scope.due_at) is True

    # Whenever the calculator does run, due_at stays the evidence-anchored instant;
    # a retry, a restart or a later run can never move the horizon.
    late = calculate_forward_outcome(
        scope=scope,
        reference=_ok_reference(),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
        ),
    )
    assert late.due_at == scope.due_at


# --- §24 / §13 / §40 / §41 classification -----------------------------------------------


def test_reference_price_is_the_frozen_midpoint_of_the_reference_bbo():
    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _reference_observation(bid=3_000.0, ask=3_002.0)
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=_ok_reference(reference),
        observations=(
            _observation(
                bid=3_010.0, ask=3_012.0, available_at=scope.due_at - timedelta(seconds=1)
            ),
        ),
    )
    assert outcome.reference_price == pytest.approx(3_001.0, rel=1e-12)
    assert outcome.reference_return == pytest.approx(3_011 / 3_001 - 1, rel=1e-12)


@pytest.mark.parametrize(
    "status,reason",
    [
        (ReferenceDataStatus.REFERENCE_MISSING, ForwardOutcomeReason.REFERENCE_MISSING),
        (ReferenceDataStatus.REFERENCE_STALE, ForwardOutcomeReason.REFERENCE_STALE),
    ],
)
def test_missing_or_stale_reference_is_insufficient_data_with_null_metrics(status, reason):
    scope = _scope(horizon=ForwardHorizon.M5)
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(status=status),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
        ),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA
    assert outcome.completeness_diagnostics["reason"] == reason.value
    assert outcome.reference_bbo_observation_id is None
    for value in (
        outcome.reference_price,
        outcome.end_bid,
        outcome.end_ask,
        outcome.mfe,
        outcome.mae,
        outcome.reference_return,
        outcome.executable_long_return,
        outcome.cost_adjusted_forward_return,
    ):
        assert value is None


def test_no_eligible_endpoint_is_insufficient_data_not_invalid():
    scope = _scope(horizon=ForwardHorizon.M5)
    outcome = calculate_forward_outcome(scope=scope, reference=_ok_reference(), observations=())
    assert outcome.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA
    assert outcome.completeness_diagnostics["reason"] == ForwardOutcomeReason.ENDPOINT_MISSING.value
    assert outcome.end_bbo_observation_id is None
    assert outcome.mfe is None and outcome.mae is None


def test_ordinary_missing_data_never_becomes_invalid():
    """Only a durable contradiction is INVALID (task §41)."""

    scope = _scope(horizon=ForwardHorizon.M5)
    cases = [
        calculate_forward_outcome(
            scope=scope,
            reference=ForwardReference(status=ReferenceDataStatus.REFERENCE_MISSING),
            observations=(),
        ),
        calculate_forward_outcome(scope=scope, reference=_ok_reference(), observations=()),
        calculate_forward_outcome(
            scope=scope,
            reference=_ok_reference(),
            observations=(
                _observation(bid=1.0, ask=2.0, available_at=scope.due_at - timedelta(minutes=3)),
            ),
        ),
        calculate_forward_outcome(
            scope=scope,
            reference=_ok_reference(),
            observations=(
                _observation(
                    bid=1.0, ask=2.0, available_at=scope.due_at - timedelta(seconds=2)
                , data_quality=DataQuality.STALE),
            ),
        ),
    ]
    for outcome in cases:
        assert outcome.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA


@pytest.mark.parametrize(
    "override,expected",
    [
        ({"observation_id": None}, ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_MISSING),
        (
            {"observation_instrument_id": OTHER_INSTRUMENT},
            ForwardOutcomeReason.INVALID_REFERENCE_INSTRUMENT_MISMATCH,
        ),
        (
            {"observation_market_type": MarketType.SWAP},
            ForwardOutcomeReason.INVALID_REFERENCE_MARKET_MISMATCH,
        ),
        ({"bid": 120.0, "ask": 100.0}, ForwardOutcomeReason.INVALID_REFERENCE_PRICES),
        ({"bid": 0.0}, ForwardOutcomeReason.INVALID_REFERENCE_PRICES),
    ],
)
def test_a_durable_structural_contradiction_is_invalid(override, expected):
    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _ok_reference()
    payload = {
        "status": reference.status,
        "bid": reference.bid,
        "ask": reference.ask,
        "observation_id": reference.observation_id,
        "observation_instrument_id": reference.observation_instrument_id,
        "observation_market_type": reference.observation_market_type,
        **override,
    }
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(**payload),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
        ),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert outcome.completeness_diagnostics["reason"] == expected.value
    assert outcome.reference_bbo_observation_id is None
    assert outcome.end_bbo_observation_id is None
    assert outcome.mfe is None


def test_a_reference_observation_missing_its_own_market_identity_is_invalid():
    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _ok_reference()
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(
            status=reference.status,
            bid=reference.bid,
            ask=reference.ask,
            observation_id=reference.observation_id,
        ),
        observations=(),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert (
        outcome.completeness_diagnostics["reason"]
        == ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_INCOMPLETE.value
    )


def test_a_reference_present_for_a_non_ok_status_is_invalid():
    scope = _scope(horizon=ForwardHorizon.M5)
    reference = _ok_reference()
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(
            status=ReferenceDataStatus.REFERENCE_STALE,
            bid=reference.bid,
            ask=reference.ask,
        ),
        observations=(),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert (
        outcome.completeness_diagnostics["reason"]
        == ForwardOutcomeReason.INVALID_REFERENCE_PRESENT_FOR_NON_OK_STATUS.value
    )


def test_impossible_chronology_is_invalid():
    scope = ForwardScopeFacts(
        opportunity_id="op",
        evidence_id="ev",
        horizon=ForwardHorizon.M5,
        evidence_at=START,
        expires_at=START - timedelta(seconds=1),
        instrument_id=INSTRUMENT,
        market_type=MarketType.SPOT,
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="okx-ws-bbo",
    )
    outcome = calculate_forward_outcome(scope=scope, reference=_ok_reference(), observations=())
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert outcome.completeness_diagnostics["reason"] == ForwardOutcomeReason.INVALID_CHRONOLOGY.value


def test_a_forward_paper_scope_without_its_anchor_is_invalid():
    """A missing FIX-01 authority is a provenance contradiction, not thin data."""

    scope = _scope(horizon=ForwardHorizon.M5)
    invalid = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(status=ReferenceDataStatus.OK),
        observations=(),
        structural_problem=ForwardOutcomeReason.INVALID_FORWARD_ANCHOR_MISSING,
    )
    assert invalid.calculation_status is OutcomeCalculationStatus.INVALID
    assert (
        invalid.completeness_diagnostics["reason"]
        == ForwardOutcomeReason.INVALID_FORWARD_ANCHOR_MISSING.value
    )
    assert invalid.reference_bbo_observation_id is None


def test_a_non_invalid_structural_problem_is_rejected_by_the_calculator():
    scope = _scope(horizon=ForwardHorizon.M5)
    with pytest.raises(ValueError):
        calculate_forward_outcome(
            scope=scope,
            reference=_ok_reference(),
            observations=(),
            structural_problem=ForwardOutcomeReason.ENDPOINT_MISSING,
        )


# --- §38 lifecycle ----------------------------------------------------------------------


def test_opportunity_lifecycle_at_horizon_is_only_active_or_expired():
    scope = _scope(horizon=ForwardHorizon.H1, expires_at=START + timedelta(minutes=20))
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=_ok_reference(),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
        ),
    )
    # due_at (1h) is after the SETUP expiry (20 min) => EXPIRED.
    assert outcome.opportunity_lifecycle_at_horizon is OpportunityLifecycleAtHorizon.EXPIRED

    short = _scope(horizon=ForwardHorizon.S30, expires_at=START + timedelta(minutes=20))
    short_outcome = calculate_forward_outcome(
        scope=short,
        reference=_ok_reference(),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=short.due_at - timedelta(seconds=1)),
        ),
    )
    assert short_outcome.opportunity_lifecycle_at_horizon is OpportunityLifecycleAtHorizon.ACTIVE
    assert {item.value for item in OpportunityLifecycleAtHorizon} == {"ACTIVE", "EXPIRED"}


# --- §42 diagnostics / §40 no placeholder -----------------------------------------------


def test_diagnostics_carry_every_required_field_without_placeholder_values():
    scope = _scope(horizon=ForwardHorizon.M5)
    path = (
        _observation(bid=101.0, ask=103.0, available_at=START + timedelta(seconds=60)),
        _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
    )
    outcome = calculate_forward_outcome(scope=scope, reference=_ok_reference(), observations=path)
    diagnostics = outcome.completeness_diagnostics
    assert set(diagnostics) >= {
        "reason",
        "observation_count",
        "eligible_observation_count",
        "first_available_at",
        "last_available_at",
        "max_observation_gap_seconds",
        "end_age_seconds",
        "reference_status",
    }
    assert diagnostics["observation_count"] == 2
    assert diagnostics["eligible_observation_count"] == 2
    assert diagnostics["first_available_at"] == (START + timedelta(seconds=60)).isoformat()
    assert diagnostics["last_available_at"] == (scope.due_at - timedelta(seconds=1)).isoformat()
    assert diagnostics["max_observation_gap_seconds"] == pytest.approx(
        (scope.due_at - timedelta(seconds=1) - (START + timedelta(seconds=60))).total_seconds()
    )
    assert diagnostics["reference_status"] == "OK"

    incomplete = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(status=ReferenceDataStatus.REFERENCE_MISSING),
        observations=path,
    )
    for value in incomplete.completeness_diagnostics.values():
        if isinstance(value, float):
            assert math.isfinite(value)


def test_a_wide_mid_path_gap_is_a_diagnostic_and_never_an_invalidity():
    scope = _scope(horizon=ForwardHorizon.H1)
    gap = (
        _observation(bid=101.0, ask=103.0, available_at=START + timedelta(seconds=1)),
        _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
    )
    outcome = calculate_forward_outcome(scope=scope, reference=_ok_reference(), observations=gap)
    assert outcome.calculation_status is OutcomeCalculationStatus.COMPLETE
    assert outcome.completeness_diagnostics["max_observation_gap_seconds"] > 3_000


# --- §49 four horizons / §47 no automatic revision 2 ------------------------------------


def test_the_four_horizons_are_independent_scopes():
    observations = tuple(
        _observation(bid=103.0, ask=105.0, available_at=START + timedelta(seconds=offset))
        for offset in (25, 295, 895, 3_595)
    )
    outcomes = [
        calculate_forward_outcome(
            scope=_scope(horizon=horizon),
            reference=_ok_reference(),
            observations=observations,
        )
        for horizon in ALL_FORWARD_HORIZONS
    ]
    assert [item.horizon for item in outcomes] == list(ALL_FORWARD_HORIZONS)
    assert len({item.due_at for item in outcomes}) == 4
    assert len({item.outcome_id for item in outcomes}) == 4
    assert len({item.calculation_digest for item in outcomes}) == 4
    assert all(item.calculation_status is OutcomeCalculationStatus.COMPLETE for item in outcomes)
    assert all(item.outcome_revision == 1 for item in outcomes)
    assert all(item.supersedes_outcome_id is None for item in outcomes)


def test_the_calculator_never_creates_a_revision_above_one():
    scope = _scope(horizon=ForwardHorizon.M5)
    observations = (
        _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
    )
    first = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=observations
    )
    # A retry, a later run and a later quote must all reproduce the very same
    # revision-1 record rather than proposing a correction.
    second = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=observations
    )
    assert second.outcome_revision == 1
    assert second.supersedes_outcome_id is None
    assert second.outcome_id == first.outcome_id
    assert second.calculation_digest == first.calculation_digest
    assert second.outcome_record_hash == first.outcome_record_hash


# --- §52 replay / forward digest separation ----------------------------------------------


def test_replay_and_forward_share_the_calculation_digest_but_not_the_record_hash():
    observations = (
        _observation(bid=101.0, ask=103.0, available_at=START + timedelta(seconds=1)),
        _observation(bid=103.0, ask=105.0, available_at=START + timedelta(seconds=295)),
    )
    forward = calculate_forward_outcome(
        scope=_scope(source_type=EvidenceSource.FORWARD_PAPER, source_identity="okx-ws-forward"),
        reference=_ok_reference(),
        observations=observations,
    )
    replay = calculate_forward_outcome(
        scope=_scope(
            source_type=EvidenceSource.HISTORICAL_REPLAY, source_identity="replay-manifest-7"
        ),
        reference=_ok_reference(),
        observations=observations,
    )

    assert forward.calculation_digest == replay.calculation_digest
    assert forward.calculation_content() == replay.calculation_content()
    assert forward.outcome_record_hash != replay.outcome_record_hash
    assert forward.outcome_id == replay.outcome_id
    assert forward.source_type is EvidenceSource.FORWARD_PAPER
    assert replay.source_type is EvidenceSource.HISTORICAL_REPLAY


def test_a_replay_scope_may_use_its_own_frozen_reference_metrics():
    """A Historical Replay revision has no Forward anchor, so its own metrics are the authority."""

    scope = _scope(horizon=ForwardHorizon.M5, source_type=EvidenceSource.HISTORICAL_REPLAY)
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(status=ReferenceDataStatus.OK, bid=99.0, ask=101.0),
        observations=(
            _observation(bid=103.0, ask=105.0, available_at=scope.due_at - timedelta(seconds=1)),
        ),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.COMPLETE
    assert outcome.reference_bbo_observation_id is None
    assert outcome.reference_price == pytest.approx(100.0, rel=1e-12)


def test_a_forward_paper_scope_may_not_use_frozen_metrics_without_its_anchor_bbo():
    scope = _scope(horizon=ForwardHorizon.M5, source_type=EvidenceSource.FORWARD_PAPER)
    outcome = calculate_forward_outcome(
        scope=scope,
        reference=ForwardReference(status=ReferenceDataStatus.OK, bid=99.0, ask=101.0),
        observations=(),
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert (
        outcome.completeness_diagnostics["reason"]
        == ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_MISSING.value
    )


# --- per-observation tradability is enforced on the durable row --------------------------


def test_a_single_untradable_observation_can_never_be_the_endpoint():
    scope = _scope(horizon=ForwardHorizon.M5)
    untradable = _observation(
        bid=1_000.0,
        ask=1_002.0,
        available_at=scope.due_at - timedelta(seconds=1),
        tradable=False,
    )
    outcome = calculate_forward_outcome(
        scope=scope, reference=_ok_reference(), observations=(untradable,)
    )
    assert outcome.calculation_status is OutcomeCalculationStatus.INSUFFICIENT_DATA
    assert outcome.completeness_diagnostics["excluded_untradable_count"] == 1


# --- immutable calculator policy ---------------------------------------------------------


def test_scope_facts_reject_a_naive_timestamp_or_a_foreign_horizon():
    with pytest.raises(ValueError):
        ForwardScopeFacts(
            opportunity_id="op",
            evidence_id="ev",
            horizon=ForwardHorizon.M5,
            evidence_at=datetime.fromisoformat("2026-01-02T09:30:00"),
            expires_at=START,
            instrument_id=INSTRUMENT,
            market_type=MarketType.SPOT,
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="okx-ws-bbo",
        )
    with pytest.raises(TypeError):
        ForwardScopeFacts(
            opportunity_id="op",
            evidence_id="ev",
            horizon="5m",
            evidence_at=START,
            expires_at=START,
            instrument_id=INSTRUMENT,
            market_type=MarketType.SPOT,
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="okx-ws-bbo",
        )
