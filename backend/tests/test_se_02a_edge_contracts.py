"""SE-02A identity, canonical hashing and frozen revision semantics (no database)."""

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
    ReferenceDataReason,
    ReferenceDataStatus,
    build_evidence_revision,
    build_forward_outcome_contract,
    build_opportunity_identity,
)
from marketpulse.market_data.models import MarketType
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
        feature_snapshot_payload={"retest": True, "level": 99.5} if snapshot is None else snapshot,
        supersedes_evidence_id=supersedes,
        created_at=created_at,
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
    baseline = build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=_evidence(opportunity).evidence_id,
        horizon=ForwardHorizon.H1,
        outcome_revision=1,
        due_at=START + timedelta(hours=1),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="paper",
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version="calc-v1",
        created_at=START,
    )
    recalibrated = build_forward_outcome_contract(
        opportunity_id=opportunity.opportunity_id,
        evidence_id=_evidence(opportunity).evidence_id,
        horizon=ForwardHorizon.H1,
        outcome_revision=1,
        due_at=START + timedelta(hours=1),
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="paper",
        cost_policy="taker-only",
        cost_model_version="cost-v1",
        calculator_version="calc-v9",
        created_at=START,
    )

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
            reference_bid=1.0,
            reference_ask=2.0,
            reference_received_at=START,
            reference_data_status=ReferenceDataStatus.OK,
            reference_data_reason=ReferenceDataReason.NONE,
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
