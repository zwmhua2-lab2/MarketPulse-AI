"""SE-02A identity, canonical hashing and frozen contract semantics (no database).

Covers the three contract boundaries that the Acceptance Fix #1 corrected:

* P0-1 -- an opportunity evidence revision survives a missing / stale reference
  BBO, and the reference-data status vocabulary is unambiguous;
* P0-2 -- only approved terminal forward-outcome statuses exist and `PENDING`
  is never a persisted state;
* P0-3 -- BBO observations obey the causal `available_at == received_at` rule and
  carry a stable, causal deterministic identity.
"""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from marketpulse.edge import identity
from marketpulse.edge.hashing import (
    CanonicalHashError,
    canonical_digest,
    feature_snapshot_hash,
    outcome_record_hash,
)
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ForwardHorizon,
    OpportunityIdentity,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_bbo_observation,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.market_data.models import DataQuality, MarketType
from pydantic import ValidationError

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)


def _opportunity(
    *,
    candidate_id: str = "sc_breakout_1",
    instrument_id: str = "BTC-USDT",
    family_version: str = "f1",
    market_type: MarketType = MarketType.SPOT,
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=family_version,
        instrument_id=instrument_id,
        market_type=market_type,
        candidate_id=candidate_id,
    )


def _evidence(
    opportunity: OpportunityIdentity,
    *,
    revision: int = 1,
    supersedes: str | None = None,
    payload: dict | None = None,
    snapshot: dict | None = None,
    created_at: datetime = START,
    reference_status: ReferenceDataStatus = ReferenceDataStatus.OK,
    reference_bid: float | None = 99.0,
    reference_ask: float | None = 100.0,
    reference_received_at: datetime | None = START,
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
        reference_data_status=reference_status,
        reference_bid=reference_bid,
        reference_ask=reference_ask,
        reference_received_at=reference_received_at,
        evidence_payload={"setup": "breakout"} if payload is None else payload,
        feature_snapshot_payload={"retest": True, "level": 99.5} if snapshot is None else snapshot,
        supersedes_evidence_id=supersedes,
        created_at=created_at,
    )


def _unavailable_evidence(
    opportunity: OpportunityIdentity,
    status: ReferenceDataStatus,
    *,
    revision: int = 1,
    supersedes: str | None = None,
) -> EvidenceRevision:
    """An evidence revision whose reference quote is missing or stale."""

    return _evidence(
        opportunity,
        revision=revision,
        supersedes=supersedes,
        reference_status=status,
        reference_bid=None,
        reference_ask=None,
        reference_received_at=None,
    )


def _bbo(
    *,
    instrument_id: str = "BTC-USDT",
    market_type: MarketType = MarketType.SPOT,
    bid: float = 99.0,
    ask: float = 100.0,
    source_event_time: datetime | None = None,
    received_at: datetime | None = None,
    available_at: datetime | None = None,
    data_quality: DataQuality = DataQuality.FRESH,
    tradable: bool = True,
    source: str = "okx-ws-bbo",
    source_sequence: int | None = 42,
):
    return build_bbo_observation(
        instrument_id=instrument_id,
        market_type=market_type,
        bid=bid,
        ask=ask,
        available_at=START if available_at is None else available_at,
        source_event_time=START if source_event_time is None else source_event_time,
        received_at=START if received_at is None else received_at,
        data_quality=data_quality,
        tradable=tradable,
        source=source,
        source_sequence=source_sequence,
        created_at=START,
    )


# --- Identity ---------------------------------------------------------------------------


def test_opportunity_id_is_deterministic_and_matches_the_approved_formula():
    first = _opportunity()
    second = _opportunity()

    assert first.opportunity_id == second.opportunity_id
    assert first.opportunity_id == identity.opportunity_id(
        family_id="BREAKOUT_RETEST",
        family_version="f1",
        instrument_id="BTC-USDT",
        candidate_id="sc_breakout_1",
    )
    assert len(first.opportunity_id) == 64


@pytest.mark.parametrize(
    "changed",
    [
        {"candidate_id": "sc_breakout_2"},
        {"instrument_id": "ETH-USDT"},
        {"family_version": "f2"},
    ],
)
def test_opportunity_id_is_sensitive_to_every_identity_fact(changed):
    baseline = _opportunity()
    mutated = _opportunity(**changed)

    assert mutated.opportunity_id != baseline.opportunity_id


def test_opportunity_id_formula_distinguishes_market_type_through_instrument_id():
    """The approved formula takes instrument_id, not market_type.

    SPOT and SWAP are separate instruments, so distinct instruments keep distinct
    opportunity identities without widening the frozen formula.
    """

    spot = _opportunity(instrument_id="BTC-USDT", market_type=MarketType.SPOT)
    swap = _opportunity(instrument_id="BTC-USDT-SWAP", market_type=MarketType.SWAP)

    assert spot.opportunity_id != swap.opportunity_id


def test_opportunity_id_rejects_a_tampered_derivation():
    with pytest.raises(ValidationError):
        OpportunityIdentity(
            opportunity_id="0" * 64,
            family_id=EdgeFamily.BREAKOUT_RETEST,
            family_version="f1",
            instrument_id="BTC-USDT",
            market_type=MarketType.SPOT,
            candidate_id="sc_breakout_1",
        )


def test_evidence_id_is_deterministic_and_sensitive_to_revision():
    opportunity = _opportunity()
    first = _evidence(opportunity, revision=1)
    repeat = _evidence(opportunity, revision=1)
    second = _evidence(opportunity, revision=2, supersedes=first.evidence_id)

    assert first.evidence_id == repeat.evidence_id
    assert first.evidence_id == identity.evidence_id(
        opportunity_id=opportunity.opportunity_id,
        evidence_revision=1,
        evidence_contract_version="se02-evidence-v1",
    )
    assert second.evidence_id != first.evidence_id


def test_evidence_correction_keeps_logical_opportunity_identity():
    opportunity = _opportunity()
    first = _evidence(opportunity, revision=1)
    corrected = _evidence(
        opportunity, revision=2, supersedes=first.evidence_id, payload={"setup": "breakout-v2"}
    )

    # A correction changes the immutable revision and its hash, never the opportunity.
    assert corrected.opportunity_id == first.opportunity_id
    assert corrected.evidence_id != first.evidence_id
    assert corrected.evidence_hash != first.evidence_hash


def test_calculator_version_does_not_affect_opportunity_identity():
    opportunity = _opportunity()
    evidence_id = _evidence(opportunity).evidence_id

    def _outcome(calculator_version: str):
        return build_forward_outcome_contract(
            opportunity_id=opportunity.opportunity_id,
            evidence_id=evidence_id,
            horizon=ForwardHorizon.H1,
            outcome_revision=1,
            due_at=START + timedelta(hours=1),
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="paper",
            cost_policy="taker-only",
            cost_model_version="cost-v1",
            calculator_version=calculator_version,
            calculation_status=OutcomeCalculationStatus.COMPLETE,
            created_at=START,
        )

    baseline = _outcome("calc-v1")
    recalibrated = _outcome("calc-v9")

    assert recalibrated.opportunity_id == baseline.opportunity_id == opportunity.opportunity_id
    assert recalibrated.outcome_id == baseline.outcome_id
    assert recalibrated.calculation_digest != baseline.calculation_digest


# --- Frozen vocabulary ------------------------------------------------------------------


def test_only_breakout_retest_family_is_licensed():
    assert [family.value for family in EdgeFamily] == ["BREAKOUT_RETEST"]
    with pytest.raises(ValueError):
        EdgeFamily("TREND_PULLBACK")


def test_only_approved_forward_horizons_are_licensed():
    assert [horizon.value for horizon in ForwardHorizon] == ["30s", "5m", "15m", "1h"]
    assert [horizon.duration_seconds for horizon in ForwardHorizon] == [30, 300, 900, 3600]
    for unsupported in ("5s", "1m", "2h", "1d"):
        with pytest.raises(ValueError):
            ForwardHorizon(unsupported)


# --- P0-2: forward outcome terminal semantics -------------------------------------------


def test_only_approved_terminal_outcome_statuses_are_licensed():
    assert [status.value for status in OutcomeCalculationStatus] == [
        "COMPLETE",
        "INSUFFICIENT_DATA",
        "INVALID",
    ]
    for unapproved in (
        "PENDING",
        "CALCULATED",
        "INCOMPLETE_DATA",
        "NOT_APPLICABLE",
        "FAILED",
    ):
        with pytest.raises(ValueError):
            OutcomeCalculationStatus(unapproved)


def test_only_approved_lifecycle_vocabulary_is_licensed():
    assert [state.value for state in OpportunityLifecycleAtHorizon] == ["ACTIVE", "EXPIRED"]
    for unapproved in ("INVALIDATED", "UNKNOWN"):
        with pytest.raises(ValueError):
            OpportunityLifecycleAtHorizon(unapproved)


def test_calculation_status_is_required_so_no_pending_row_can_be_built():
    """`PENDING` is not a persisted status, so the builder has no default status.

    While `clock < due_at` there is no row at all; a row is only written once a
    terminal status is known.
    """

    with pytest.raises(TypeError):
        build_forward_outcome_contract(  # type: ignore[call-arg]
            opportunity_id="o" * 64,
            evidence_id="e" * 64,
            horizon=ForwardHorizon.M5,
            outcome_revision=1,
            due_at=START + timedelta(minutes=5),
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="paper",
            cost_policy="taker-only",
            cost_model_version="cost-v1",
            calculator_version="calc-v1",
            created_at=START,
        )


@pytest.mark.parametrize(
    "status",
    [
        OutcomeCalculationStatus.COMPLETE,
        OutcomeCalculationStatus.INSUFFICIENT_DATA,
        OutcomeCalculationStatus.INVALID,
    ],
)
def test_terminal_statuses_build_with_optional_metrics(status):
    opportunity = _opportunity()
    outcome = build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=_evidence(opportunity).evidence_id,
        horizon=ForwardHorizon.M5,
        outcome_revision=1,
        due_at=START + timedelta(minutes=5),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="paper",
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version="calc-v1",
        calculation_status=status,
        created_at=START,
    )

    assert outcome.calculation_status is status
    # No calculator runs in this batch, so every metric stays absent.
    assert outcome.reference_return is None
    assert outcome.mfe is None
    assert outcome.mae is None


def test_lifecycle_is_independent_of_calculation_status():
    opportunity = _opportunity()
    outcome = build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=_evidence(opportunity).evidence_id,
        horizon=ForwardHorizon.M5,
        outcome_revision=1,
        due_at=START + timedelta(minutes=5),
        source_type=EvidenceSource.HISTORICAL_REPLAY,
        source_identity="replay-a",
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version="calc-v1",
        calculation_status=OutcomeCalculationStatus.INVALID,
        opportunity_lifecycle_at_horizon=OpportunityLifecycleAtHorizon.EXPIRED,
        created_at=START,
    )

    # Invalid *data* is a calculation status; it is never folded into lifecycle.
    assert outcome.calculation_status is OutcomeCalculationStatus.INVALID
    assert outcome.opportunity_lifecycle_at_horizon is OpportunityLifecycleAtHorizon.EXPIRED


# --- P0-1: reference data may be missing / stale ----------------------------------------


@pytest.mark.parametrize(
    "status",
    [ReferenceDataStatus.REFERENCE_MISSING, ReferenceDataStatus.REFERENCE_STALE],
)
def test_evidence_persists_without_a_usable_reference_quote(status):
    record = _unavailable_evidence(_opportunity(), status)

    assert record.reference_data_status is status
    assert record.reference_bid is None
    assert record.reference_ask is None
    assert record.reference_received_at is None


@pytest.mark.parametrize(
    "status",
    [ReferenceDataStatus.REFERENCE_MISSING, ReferenceDataStatus.REFERENCE_STALE],
)
def test_unavailable_reference_evidence_is_deterministic(status):
    opportunity = _opportunity()

    first = _unavailable_evidence(opportunity, status)
    second = _unavailable_evidence(opportunity, status)

    assert first.evidence_hash == second.evidence_hash
    assert first.evidence_id == second.evidence_id


def test_missing_and_stale_reference_data_do_not_share_an_evidence_hash():
    opportunity = _opportunity()

    missing = _unavailable_evidence(opportunity, ReferenceDataStatus.REFERENCE_MISSING)
    stale = _unavailable_evidence(opportunity, ReferenceDataStatus.REFERENCE_STALE)
    present = _evidence(opportunity)

    assert len({missing.evidence_hash, stale.evidence_hash, present.evidence_hash}) == 3


@pytest.mark.parametrize(
    "reference_bid,reference_ask,reference_received_at",
    [
        (None, 100.0, START),
        (99.0, None, START),
        (99.0, 100.0, None),
        (None, None, None),
    ],
)
def test_ok_reference_status_requires_a_complete_quote(
    reference_bid, reference_ask, reference_received_at
):
    with pytest.raises(ValidationError):
        _evidence(
            _opportunity(),
            reference_bid=reference_bid,
            reference_ask=reference_ask,
            reference_received_at=reference_received_at,
        )


@pytest.mark.parametrize("reference_bid,reference_ask", [(0.0, 100.0), (-1.0, 100.0), (101.0, 100.0)])
def test_ok_reference_status_rejects_non_positive_or_crossed_prices(reference_bid, reference_ask):
    with pytest.raises(ValidationError):
        _evidence(_opportunity(), reference_bid=reference_bid, reference_ask=reference_ask)


@pytest.mark.parametrize(
    "status",
    [ReferenceDataStatus.REFERENCE_MISSING, ReferenceDataStatus.REFERENCE_STALE],
)
def test_unavailable_reference_data_must_not_carry_a_placeholder_quote(status):
    """A missing metric is NULL, never 0, and never a partially filled quote."""

    with pytest.raises(ValidationError):
        _evidence(
            _opportunity(),
            reference_status=status,
            reference_bid=0.0,
            reference_ask=0.0,
            reference_received_at=START,
        )


def test_reference_status_vocabulary_is_the_frozen_three_state_set():
    assert [status.value for status in ReferenceDataStatus] == [
        "OK",
        "REFERENCE_MISSING",
        "REFERENCE_STALE",
    ]
    for unapproved in ("DEGRADED", "UNAVAILABLE", "MISSING", "STALE"):
        with pytest.raises(ValueError):
            ReferenceDataStatus(unapproved)


# --- P0-3: BBO causal identity ----------------------------------------------------------


def test_bbo_observation_identity_is_stable_and_deterministic():
    first = _bbo()
    second = _bbo()

    assert first.observation_id == second.observation_id
    assert len(first.observation_id) == 64
    assert first.observation_id == identity.bbo_observation_id(
        instrument_id="BTC-USDT",
        market_type="SPOT",
        source="okx-ws-bbo",
        source_sequence=42,
        source_event_time=START,
        available_at=START,
        received_at=START,
        bid=99.0,
        ask=100.0,
    )


@pytest.mark.parametrize(
    "changed",
    [
        {"instrument_id": "ETH-USDT"},
        {"market_type": MarketType.SWAP},
        {"bid": 98.5},
        {"ask": 100.5},
        {"source": "other-feed"},
        {"source_sequence": 43},
        {"source_sequence": None},
        {"source_event_time": START + timedelta(seconds=1)},
        {"received_at": START + timedelta(seconds=1), "available_at": START + timedelta(seconds=1)},
    ],
)
def test_bbo_observation_identity_covers_every_causal_fact(changed):
    baseline = _bbo()
    mutated = _bbo(**changed)

    assert mutated.observation_id != baseline.observation_id


def test_bbo_observation_requires_available_at_to_equal_received_at():
    """Frozen V1 causal rule: available_at is the normalized receive time."""

    with pytest.raises(ValidationError):
        _bbo(available_at=START + timedelta(seconds=1), received_at=START)


@pytest.mark.parametrize("bid,ask", [(0.0, 100.0), (-1.0, 100.0), (101.0, 100.0)])
def test_bbo_observation_rejects_non_positive_or_crossed_quotes(bid, ask):
    with pytest.raises(ValidationError):
        _bbo(bid=bid, ask=ask)


def test_bbo_observation_accepts_an_absent_source_sequence():
    observation = _bbo(source_sequence=None)

    assert observation.source_sequence is None
    assert observation.observation_id == identity.bbo_observation_id(
        instrument_id="BTC-USDT",
        market_type="SPOT",
        source="okx-ws-bbo",
        source_sequence=None,
        source_event_time=START,
        available_at=START,
        received_at=START,
        bid=99.0,
        ask=100.0,
    )


# --- Canonical hashing ------------------------------------------------------------------


def test_identical_semantic_objects_hash_identically_regardless_of_key_order():
    left = {"level": 99.5, "nested": {"b": [1, 2], "a": "x"}, "flag": True}
    right = {"flag": True, "nested": {"a": "x", "b": [1, 2]}, "level": 99.5}

    assert feature_snapshot_hash(left) == feature_snapshot_hash(right)
    assert feature_snapshot_hash(left) == feature_snapshot_hash(dict(left))


def test_canonical_hashing_is_type_sensitive():
    assert canonical_digest("d", 1) != canonical_digest("d", "1")
    assert canonical_digest("d", 1) != canonical_digest("d", 1.0)
    assert canonical_digest("d", 0.1) != canonical_digest("d", Decimal("0.1"))
    assert canonical_digest("d", 0.1) != canonical_digest("d", (0.1).hex())
    assert canonical_digest("d", {"a": 1}) != canonical_digest("d", {"a": "1"})


def test_canonical_hashing_is_domain_separated():
    assert canonical_digest("domain-a", "payload") != canonical_digest("domain-b", "payload")
    assert canonical_digest("domain-a", "payload") != canonical_digest("domain-a", "domain-b", "payload")
    assert feature_snapshot_hash({"a": 1}) != outcome_record_hash({"a": 1})


def test_datetime_normalization_is_utc_and_rejects_naive_values():
    local = datetime(2026, 1, 2, 17, 30, tzinfo=timezone(timedelta(hours=8)))
    same_instant = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)

    assert canonical_digest("d", local) == canonical_digest("d", same_instant)
    assert canonical_digest("d", local) != canonical_digest("d", same_instant + timedelta(seconds=1))

    with pytest.raises(CanonicalHashError):
        canonical_digest("d", datetime(2026, 1, 2, 9, 30))  # noqa: DTZ001  (naive on purpose)
    # The canonical layer fails closed before the contract layer, so a naive business
    # timestamp can never reach persistence with a silently local-time hash.
    with pytest.raises(CanonicalHashError):
        build_evidence_revision(
            opportunity=_opportunity(),
            evidence_revision=1,
            detected_at=datetime(2026, 1, 2, 9, 30),  # noqa: DTZ001  (naive on purpose)
            evidence_at=START,
            expires_at=START,
            source_type=EvidenceSource.HISTORICAL_REPLAY,
            source_identity="s",
            source_manifest_id="m",
            reference_data_status=ReferenceDataStatus.OK,
            reference_bid=1.0,
            reference_ask=2.0,
            reference_received_at=START,
            evidence_payload={},
            feature_snapshot_payload={},
            created_at=START,
        )


def test_float_canonicalization_distinguishes_precision_loss():
    assert canonical_digest("d", 0.1) == canonical_digest("d", 0.1)
    assert canonical_digest("d", 0.1) != canonical_digest("d", Decimal("0.1"))
    assert canonical_digest("d", 1e-9) != canonical_digest("d", 0.0)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_values_fail_closed(bad):
    with pytest.raises(CanonicalHashError):
        canonical_digest("d", {"value": bad})
    with pytest.raises(CanonicalHashError):
        canonical_digest("d", [bad])


# --- Frozen revision semantics ----------------------------------------------------------


def test_revision_one_must_not_supersede():
    opportunity = _opportunity()
    first = _evidence(opportunity, revision=1)
    with pytest.raises(ValidationError):
        _evidence(opportunity, revision=1, supersedes=first.evidence_id)


def test_revision_above_one_must_supersede():
    opportunity = _opportunity()
    with pytest.raises(ValidationError):
        _evidence(opportunity, revision=2)


def test_evidence_hash_must_match_its_immutable_content():
    opportunity = _opportunity()
    valid = _evidence(opportunity)
    dumped = valid.model_dump()

    # `model_copy` bypasses validation by design, so tampering is attempted through
    # a real re-validation path (the same path a persisted row would take).
    for field, value in (
        ("evidence_hash", "f" * 64),
        ("feature_snapshot_hash", "f" * 64),
        ("evidence_id", "f" * 64),
        ("evidence_payload", {"setup": "tampered"}),
    ):
        with pytest.raises(ValidationError):
            EvidenceRevision.model_validate({**dumped, field: value})


def test_missing_reference_evidence_also_hashes_its_immutable_content():
    opportunity = _opportunity()
    valid = _unavailable_evidence(opportunity, ReferenceDataStatus.REFERENCE_STALE)
    dumped = valid.model_dump()

    # A NULL reference quote is part of the immutable content, so claiming `OK`
    # while the metrics stay absent must fail closed.
    with pytest.raises(ValidationError):
        EvidenceRevision.model_validate(
            {**dumped, "reference_data_status": ReferenceDataStatus.OK.value}
        )
    with pytest.raises(ValidationError):
        EvidenceRevision.model_validate(
            {
                **dumped,
                "reference_data_status": ReferenceDataStatus.OK.value,
                "reference_bid": 99.0,
                "reference_ask": 100.0,
                "reference_received_at": START,
            }
        )
