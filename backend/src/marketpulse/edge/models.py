"""SE-02 Edge domain contracts.

Contracts only. This module captures no opportunity, runs no forward-outcome
calculator and integrates with no G2/G3/G4/G5 runtime path.

Frozen revision semantics implemented here:

    same opportunity + same revision + same hash       -> IDEMPOTENT
    same opportunity + same revision + different hash  -> INTEGRITY_CONFLICT (fail closed)
    higher revision + valid supersedes                 -> legitimate immutable correction
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from marketpulse.edge import identity
from marketpulse.edge.hashing import (
    ATTRIBUTION_EVENT_ID_DOMAIN,  # noqa: F401  (re-exported contract surface)
    CALCULATION_DIGEST_DOMAIN,
    EVIDENCE_HASH_DOMAIN,  # noqa: F401
    FEATURE_SNAPSHOT_HASH_DOMAIN,
    OUTCOME_RECORD_HASH_DOMAIN,
    attribution_payload_hash,
    calculation_digest,
    evidence_hash,
    feature_snapshot_hash,
    outcome_record_hash,
)
from marketpulse.market_data.models import DataQuality, MarketType

# --- Contract / hashing scheme versions -------------------------------------------------
# The hash *versions* are the domain tags themselves so a stored version string can never
# drift away from the scheme that produced the stored value.
EVIDENCE_CONTRACT_VERSION = "se02-evidence-v1"
OUTCOME_CONTRACT_VERSION = "se02-outcome-v1"
ATTRIBUTION_CONTRACT_VERSION = "se02-attribution-v1"

FEATURE_SNAPSHOT_HASH_VERSION = FEATURE_SNAPSHOT_HASH_DOMAIN
CALCULATION_DIGEST_VERSION = CALCULATION_DIGEST_DOMAIN
OUTCOME_RECORD_HASH_VERSION = OUTCOME_RECORD_HASH_DOMAIN

# --- Frozen enumerations ----------------------------------------------------------------


class EdgeFamily(StrEnum):
    """The only family licensed by the accepted SE-02 design for this batch."""

    BREAKOUT_RETEST = "BREAKOUT_RETEST"


class ForwardHorizon(StrEnum):
    """The only forward horizons licensed by the accepted SE-02 design."""

    S30 = "30s"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"

    @property
    def duration_seconds(self) -> int:
        return {"30s": 30, "5m": 300, "15m": 900, "1h": 3600}[self.value]


class EvidenceSource(StrEnum):
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    FORWARD_PAPER = "FORWARD_PAPER"


class ReferenceDataStatus(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ReferenceDataReason(StrEnum):
    NONE = "NONE"
    MISSING_BBO = "MISSING_BBO"
    STALE_BBO = "STALE_BBO"
    NON_TRADABLE = "NON_TRADABLE"
    CROSSED_BOOK = "CROSSED_BOOK"
    SOURCE_GAP = "SOURCE_GAP"
    UNKNOWN = "UNKNOWN"


class OpportunityLifecycleAtHorizon(StrEnum):
    """Edge-local lifecycle assessment at the horizon.

    The derivation belongs to SE-02C; SE-02A only fixes the contract vocabulary.
    """

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class OutcomeCalculationStatus(StrEnum):
    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FAILED = "FAILED"


class AttributionSubjectType(StrEnum):
    AI = "AI"
    PLAN = "PLAN"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    ECONOMIC_RESULT = "ECONOMIC_RESULT"


# --- Shared validators ------------------------------------------------------------------


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must be timezone-aware")
    return value.astimezone(UTC)


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


def _optional_finite(value: float | None) -> float | None:
    return None if value is None else _finite(value)


# --- Opportunity identity ---------------------------------------------------------------


class OpportunityIdentity(BaseModel):
    """Deterministic logical opportunity identity.

    Deliberately excludes evidence revision, evidence hash and calculator version:
    a legitimate evidence correction must not re-identify the opportunity.
    """

    model_config = ConfigDict(frozen=True)

    opportunity_id: str
    family_id: EdgeFamily
    family_version: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    market_type: MarketType
    candidate_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _derivation_is_consistent(self) -> OpportunityIdentity:
        expected = identity.opportunity_id(
            family_id=self.family_id.value,
            family_version=self.family_version,
            instrument_id=self.instrument_id,
            candidate_id=self.candidate_id,
        )
        if self.opportunity_id != expected:
            raise ValueError("opportunity_id does not match its deterministic derivation")
        return self


def build_opportunity_identity(
    *,
    family_id: EdgeFamily,
    family_version: str,
    instrument_id: str,
    market_type: MarketType,
    candidate_id: str,
) -> OpportunityIdentity:
    return OpportunityIdentity(
        opportunity_id=identity.opportunity_id(
            family_id=family_id.value,
            family_version=family_version,
            instrument_id=instrument_id,
            candidate_id=candidate_id,
        ),
        family_id=family_id,
        family_version=family_version,
        instrument_id=instrument_id,
        market_type=market_type,
        candidate_id=candidate_id,
    )


# --- Evidence revision ------------------------------------------------------------------


def _evidence_immutable_content(
    *,
    opportunity_id: str,
    candidate_id: str,
    family_id: str,
    family_version: str,
    instrument_id: str,
    market_type: str,
    evidence_revision: int,
    evidence_contract_version: str,
    supersedes_evidence_id: str | None,
    detected_at: datetime,
    evidence_at: datetime,
    expires_at: datetime,
    source_type: str,
    source_identity: str,
    source_manifest_id: str,
    reference_bid: float,
    reference_ask: float,
    reference_received_at: datetime,
    reference_data_status: str,
    reference_data_reason: str,
    feature_snapshot_hash_value: str,
    feature_snapshot_hash_version: str,
    evidence_payload: dict[str, Any],
    feature_snapshot_payload: dict[str, Any],
) -> dict[str, Any]:
    """Everything that makes a revision immutable. Excludes derived ids and hashes."""

    return {
        "opportunity_id": opportunity_id,
        "candidate_id": candidate_id,
        "family_id": family_id,
        "family_version": family_version,
        "instrument_id": instrument_id,
        "market_type": market_type,
        "evidence_revision": evidence_revision,
        "evidence_contract_version": evidence_contract_version,
        "supersedes_evidence_id": supersedes_evidence_id,
        "detected_at": detected_at,
        "evidence_at": evidence_at,
        "expires_at": expires_at,
        "source_type": source_type,
        "source_identity": source_identity,
        "source_manifest_id": source_manifest_id,
        "reference_bid": reference_bid,
        "reference_ask": reference_ask,
        "reference_received_at": reference_received_at,
        "reference_data_status": reference_data_status,
        "reference_data_reason": reference_data_reason,
        "feature_snapshot_hash": feature_snapshot_hash_value,
        "feature_snapshot_hash_version": feature_snapshot_hash_version,
        "evidence_payload": evidence_payload,
        "feature_snapshot_payload": feature_snapshot_payload,
    }


class EvidenceRevision(BaseModel):
    """One immutable evidence revision for one logical opportunity."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    opportunity_id: str
    candidate_id: str
    family_id: EdgeFamily
    family_version: str
    instrument_id: str
    market_type: MarketType
    evidence_revision: int = Field(ge=1)
    evidence_contract_version: str
    evidence_hash: str
    feature_snapshot_hash: str
    feature_snapshot_hash_version: str
    supersedes_evidence_id: str | None = None
    detected_at: datetime
    evidence_at: datetime
    expires_at: datetime
    source_type: EvidenceSource
    source_identity: str
    source_manifest_id: str
    reference_bid: float
    reference_ask: float
    reference_received_at: datetime
    reference_data_status: ReferenceDataStatus
    reference_data_reason: ReferenceDataReason
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    feature_snapshot_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    _aware_times = field_validator(
        "detected_at", "evidence_at", "expires_at", "reference_received_at", "created_at"
    )(_aware)
    _finite_prices = field_validator("reference_bid", "reference_ask")(_finite)

    def immutable_content(self) -> dict[str, Any]:
        return _evidence_immutable_content(
            opportunity_id=self.opportunity_id,
            candidate_id=self.candidate_id,
            family_id=self.family_id.value,
            family_version=self.family_version,
            instrument_id=self.instrument_id,
            market_type=self.market_type.value,
            evidence_revision=self.evidence_revision,
            evidence_contract_version=self.evidence_contract_version,
            supersedes_evidence_id=self.supersedes_evidence_id,
            detected_at=self.detected_at,
            evidence_at=self.evidence_at,
            expires_at=self.expires_at,
            source_type=self.source_type.value,
            source_identity=self.source_identity,
            source_manifest_id=self.source_manifest_id,
            reference_bid=self.reference_bid,
            reference_ask=self.reference_ask,
            reference_received_at=self.reference_received_at,
            reference_data_status=self.reference_data_status.value,
            reference_data_reason=self.reference_data_reason.value,
            feature_snapshot_hash_value=self.feature_snapshot_hash,
            feature_snapshot_hash_version=self.feature_snapshot_hash_version,
            evidence_payload=self.evidence_payload,
            feature_snapshot_payload=self.feature_snapshot_payload,
        )

    @model_validator(mode="after")
    def _hashes_and_identity_are_consistent(self) -> EvidenceRevision:
        if self.feature_snapshot_hash != feature_snapshot_hash(self.feature_snapshot_payload):
            raise ValueError("feature_snapshot_hash does not match the feature snapshot payload")
        expected_hash = evidence_hash(self.immutable_content())
        if self.evidence_hash != expected_hash:
            raise ValueError("evidence_hash does not match the immutable evidence content")
        expected_id = identity.evidence_id(
            opportunity_id=self.opportunity_id,
            evidence_revision=self.evidence_revision,
            evidence_contract_version=self.evidence_contract_version,
        )
        if self.evidence_id != expected_id:
            raise ValueError("evidence_id does not match its deterministic derivation")
        if self.evidence_revision == 1 and self.supersedes_evidence_id is not None:
            raise ValueError("revision 1 must not supersede another evidence revision")
        if self.evidence_revision > 1 and self.supersedes_evidence_id is None:
            raise ValueError("a revision above 1 must name the revision it supersedes")
        return self


def build_evidence_revision(
    *,
    opportunity: OpportunityIdentity,
    evidence_revision: int,
    detected_at: datetime,
    evidence_at: datetime,
    expires_at: datetime,
    source_type: EvidenceSource,
    source_identity: str,
    source_manifest_id: str,
    reference_bid: float,
    reference_ask: float,
    reference_received_at: datetime,
    reference_data_status: ReferenceDataStatus,
    reference_data_reason: ReferenceDataReason,
    evidence_payload: dict[str, Any],
    feature_snapshot_payload: dict[str, Any],
    supersedes_evidence_id: str | None = None,
    created_at: datetime,
    evidence_contract_version: str = EVIDENCE_CONTRACT_VERSION,
) -> EvidenceRevision:
    snapshot_hash = feature_snapshot_hash(feature_snapshot_payload)
    content = _evidence_immutable_content(
        opportunity_id=opportunity.opportunity_id,
        candidate_id=opportunity.candidate_id,
        family_id=opportunity.family_id.value,
        family_version=opportunity.family_version,
        instrument_id=opportunity.instrument_id,
        market_type=opportunity.market_type.value,
        evidence_revision=evidence_revision,
        evidence_contract_version=evidence_contract_version,
        supersedes_evidence_id=supersedes_evidence_id,
        detected_at=detected_at,
        evidence_at=evidence_at,
        expires_at=expires_at,
        source_type=source_type.value,
        source_identity=source_identity,
        source_manifest_id=source_manifest_id,
        reference_bid=reference_bid,
        reference_ask=reference_ask,
        reference_received_at=reference_received_at,
        reference_data_status=reference_data_status.value,
        reference_data_reason=reference_data_reason.value,
        feature_snapshot_hash_value=snapshot_hash,
        feature_snapshot_hash_version=FEATURE_SNAPSHOT_HASH_VERSION,
        evidence_payload=evidence_payload,
        feature_snapshot_payload=feature_snapshot_payload,
    )
    return EvidenceRevision(
        evidence_id=identity.evidence_id(
            opportunity_id=opportunity.opportunity_id,
            evidence_revision=evidence_revision,
            evidence_contract_version=evidence_contract_version,
        ),
        opportunity_id=opportunity.opportunity_id,
        candidate_id=opportunity.candidate_id,
        family_id=opportunity.family_id,
        family_version=opportunity.family_version,
        instrument_id=opportunity.instrument_id,
        market_type=opportunity.market_type,
        evidence_revision=evidence_revision,
        evidence_contract_version=evidence_contract_version,
        evidence_hash=evidence_hash(content),
        feature_snapshot_hash=snapshot_hash,
        feature_snapshot_hash_version=FEATURE_SNAPSHOT_HASH_VERSION,
        supersedes_evidence_id=supersedes_evidence_id,
        detected_at=detected_at,
        evidence_at=evidence_at,
        expires_at=expires_at,
        source_type=source_type,
        source_identity=source_identity,
        source_manifest_id=source_manifest_id,
        reference_bid=reference_bid,
        reference_ask=reference_ask,
        reference_received_at=reference_received_at,
        reference_data_status=reference_data_status,
        reference_data_reason=reference_data_reason,
        evidence_payload=evidence_payload,
        feature_snapshot_payload=feature_snapshot_payload,
        created_at=created_at,
    )


# --- Normalized L1 BBO observation ------------------------------------------------------


class BboObservation(BaseModel):
    """Normalized L1 BBO persisted only as an Edge horizon reference point."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    instrument_id: str = Field(min_length=1)
    market_type: MarketType
    bid: float
    ask: float
    available_at: datetime
    source_event_time: datetime
    received_at: datetime
    data_quality: DataQuality
    tradable: bool
    source: str = Field(min_length=1)
    source_sequence: int | None = None
    created_at: datetime

    _aware_times = field_validator(
        "available_at", "source_event_time", "received_at", "created_at"
    )(_aware)
    _finite_prices = field_validator("bid", "ask")(_finite)

    @model_validator(mode="after")
    def _identity_is_consistent(self) -> BboObservation:
        expected = identity.bbo_observation_id(
            instrument_id=self.instrument_id,
            market_type=self.market_type.value,
            source=self.source,
            source_sequence=self.source_sequence,
            source_event_time=self.source_event_time,
            received_at=self.received_at,
            bid=self.bid,
            ask=self.ask,
        )
        if self.observation_id != expected:
            raise ValueError("observation_id does not match its deterministic derivation")
        return self


def build_bbo_observation(
    *,
    instrument_id: str,
    market_type: MarketType,
    bid: float,
    ask: float,
    available_at: datetime,
    source_event_time: datetime,
    received_at: datetime,
    data_quality: DataQuality,
    tradable: bool,
    source: str,
    created_at: datetime,
    source_sequence: int | None = None,
) -> BboObservation:
    return BboObservation(
        observation_id=identity.bbo_observation_id(
            instrument_id=instrument_id,
            market_type=market_type.value,
            source=source,
            source_sequence=source_sequence,
            source_event_time=source_event_time,
            received_at=received_at,
            bid=bid,
            ask=ask,
        ),
        instrument_id=instrument_id,
        market_type=market_type,
        bid=bid,
        ask=ask,
        available_at=available_at,
        source_event_time=source_event_time,
        received_at=received_at,
        data_quality=data_quality,
        tradable=tradable,
        source=source,
        source_sequence=source_sequence,
        created_at=created_at,
    )


# --- Forward outcome contract (persistence only; calculation belongs to SE-02C) ----------


def _outcome_calculation_content(
    *,
    opportunity_id: str,
    evidence_id: str,
    horizon: str,
    outcome_contract_version: str,
    calculation_status: str,
    opportunity_lifecycle_at_horizon: str | None,
    due_at: datetime,
    reference_bbo_observation_id: str | None,
    end_bbo_observation_id: str | None,
    reference_price: float | None,
    end_bid: float | None,
    end_ask: float | None,
    mfe: float | None,
    mae: float | None,
    reference_return: float | None,
    executable_long_return: float | None,
    cost_adjusted_forward_return: float | None,
    completeness_diagnostics: dict[str, Any],
    cost_policy: str,
    cost_model_version: str,
    calculator_version: str,
    calculation_digest_version: str,
) -> dict[str, Any]:
    """Calculation facts only.

    Deliberately excludes provenance (``source_type`` / ``source_identity`` and the
    record timestamps), the immutable revision lineage and the record hash, so a
    Historical Replay outcome and a Forward Paper outcome computed from the same
    market facts share one calculation digest.
    """

    return {
        "opportunity_id": opportunity_id,
        "evidence_id": evidence_id,
        "horizon": horizon,
        "outcome_contract_version": outcome_contract_version,
        "calculation_status": calculation_status,
        "opportunity_lifecycle_at_horizon": opportunity_lifecycle_at_horizon,
        "due_at": due_at,
        "reference_bbo_observation_id": reference_bbo_observation_id,
        "end_bbo_observation_id": end_bbo_observation_id,
        "reference_price": reference_price,
        "end_bid": end_bid,
        "end_ask": end_ask,
        "mfe": mfe,
        "mae": mae,
        "reference_return": reference_return,
        "executable_long_return": executable_long_return,
        "cost_adjusted_forward_return": cost_adjusted_forward_return,
        "completeness_diagnostics": completeness_diagnostics,
        "cost_policy": cost_policy,
        "cost_model_version": cost_model_version,
        "calculator_version": calculator_version,
        "calculation_digest_version": calculation_digest_version,
    }


class ForwardOutcomeContract(BaseModel):
    """Immutable forward-outcome revision.

    SE-02A fixes the persistence contract only; no forward return, MFE, MAE or
    expectancy value is produced in this batch.
    """

    model_config = ConfigDict(frozen=True)

    outcome_id: str
    opportunity_id: str
    evidence_id: str
    horizon: ForwardHorizon
    outcome_revision: int = Field(ge=1)
    supersedes_outcome_id: str | None = None
    outcome_contract_version: str
    calculation_status: OutcomeCalculationStatus
    opportunity_lifecycle_at_horizon: OpportunityLifecycleAtHorizon | None = None
    due_at: datetime
    source_type: EvidenceSource
    source_identity: str
    reference_bbo_observation_id: str | None = None
    end_bbo_observation_id: str | None = None
    reference_price: float | None = None
    end_bid: float | None = None
    end_ask: float | None = None
    mfe: float | None = None
    mae: float | None = None
    reference_return: float | None = None
    executable_long_return: float | None = None
    cost_adjusted_forward_return: float | None = None
    completeness_diagnostics: dict[str, Any] = Field(default_factory=dict)
    cost_policy: str
    cost_model_version: str
    calculator_version: str
    calculation_digest: str | None = None
    calculation_digest_version: str
    outcome_record_hash: str
    outcome_record_hash_version: str
    created_at: datetime

    _aware_times = field_validator("due_at", "created_at")(_aware)
    _finite_values = field_validator(
        "reference_price",
        "end_bid",
        "end_ask",
        "mfe",
        "mae",
        "reference_return",
        "executable_long_return",
        "cost_adjusted_forward_return",
    )(_optional_finite)

    def calculation_content(self) -> dict[str, Any]:
        return _outcome_calculation_content(
            opportunity_id=self.opportunity_id,
            evidence_id=self.evidence_id,
            horizon=self.horizon.value,
            outcome_contract_version=self.outcome_contract_version,
            calculation_status=self.calculation_status.value,
            opportunity_lifecycle_at_horizon=(
                None
                if self.opportunity_lifecycle_at_horizon is None
                else self.opportunity_lifecycle_at_horizon.value
            ),
            due_at=self.due_at,
            reference_bbo_observation_id=self.reference_bbo_observation_id,
            end_bbo_observation_id=self.end_bbo_observation_id,
            reference_price=self.reference_price,
            end_bid=self.end_bid,
            end_ask=self.end_ask,
            mfe=self.mfe,
            mae=self.mae,
            reference_return=self.reference_return,
            executable_long_return=self.executable_long_return,
            cost_adjusted_forward_return=self.cost_adjusted_forward_return,
            completeness_diagnostics=self.completeness_diagnostics,
            cost_policy=self.cost_policy,
            cost_model_version=self.cost_model_version,
            calculator_version=self.calculator_version,
            calculation_digest_version=self.calculation_digest_version,
        )

    def record_content(self) -> dict[str, Any]:
        """Full immutable record content, including provenance and revision lineage."""

        return {
            "outcome_id": self.outcome_id,
            "outcome_revision": self.outcome_revision,
            "supersedes_outcome_id": self.supersedes_outcome_id,
            "source_type": self.source_type.value,
            "source_identity": self.source_identity,
            "created_at": self.created_at,
            "calculation_digest": self.calculation_digest,
            **self.calculation_content(),
        }

    @model_validator(mode="after")
    def _hashes_and_identity_are_consistent(self) -> ForwardOutcomeContract:
        if self.calculation_digest is not None and self.calculation_digest != calculation_digest(
            self.calculation_content()
        ):
            raise ValueError("calculation_digest does not match the calculation content")
        if self.outcome_record_hash != outcome_record_hash(self.record_content()):
            raise ValueError("outcome_record_hash does not match the immutable outcome record")
        expected_id = identity.forward_outcome_id(
            opportunity_id=self.opportunity_id,
            evidence_id=self.evidence_id,
            horizon=self.horizon.value,
            outcome_contract_version=self.outcome_contract_version,
            outcome_revision=self.outcome_revision,
        )
        if self.outcome_id != expected_id:
            raise ValueError("outcome_id does not match its deterministic derivation")
        if self.outcome_revision == 1 and self.supersedes_outcome_id is not None:
            raise ValueError("outcome revision 1 must not supersede another outcome revision")
        if self.outcome_revision > 1 and self.supersedes_outcome_id is None:
            raise ValueError("an outcome revision above 1 must name the revision it supersedes")
        return self


def build_forward_outcome_contract(
    *,
    opportunity_id: str,
    evidence_id: str,
    horizon: ForwardHorizon,
    outcome_revision: int,
    due_at: datetime,
    source_type: EvidenceSource,
    source_identity: str,
    cost_policy: str,
    cost_model_version: str,
    calculator_version: str,
    calculation_status: OutcomeCalculationStatus = OutcomeCalculationStatus.PENDING,
    opportunity_lifecycle_at_horizon: OpportunityLifecycleAtHorizon | None = None,
    reference_bbo_observation_id: str | None = None,
    end_bbo_observation_id: str | None = None,
    reference_price: float | None = None,
    end_bid: float | None = None,
    end_ask: float | None = None,
    mfe: float | None = None,
    mae: float | None = None,
    reference_return: float | None = None,
    executable_long_return: float | None = None,
    cost_adjusted_forward_return: float | None = None,
    completeness_diagnostics: dict[str, Any] | None = None,
    supersedes_outcome_id: str | None = None,
    created_at: datetime,
    outcome_contract_version: str = OUTCOME_CONTRACT_VERSION,
) -> ForwardOutcomeContract:
    diagnostics = dict(completeness_diagnostics or {})
    content = _outcome_calculation_content(
        opportunity_id=opportunity_id,
        evidence_id=evidence_id,
        horizon=horizon.value,
        outcome_contract_version=outcome_contract_version,
        calculation_status=calculation_status.value,
        opportunity_lifecycle_at_horizon=(
            None if opportunity_lifecycle_at_horizon is None else opportunity_lifecycle_at_horizon.value
        ),
        due_at=due_at,
        reference_bbo_observation_id=reference_bbo_observation_id,
        end_bbo_observation_id=end_bbo_observation_id,
        reference_price=reference_price,
        end_bid=end_bid,
        end_ask=end_ask,
        mfe=mfe,
        mae=mae,
        reference_return=reference_return,
        executable_long_return=executable_long_return,
        cost_adjusted_forward_return=cost_adjusted_forward_return,
        completeness_diagnostics=diagnostics,
        cost_policy=cost_policy,
        cost_model_version=cost_model_version,
        calculator_version=calculator_version,
        calculation_digest_version=CALCULATION_DIGEST_VERSION,
    )
    digest = calculation_digest(content)
    outcome_identity = identity.forward_outcome_id(
        opportunity_id=opportunity_id,
        evidence_id=evidence_id,
        horizon=horizon.value,
        outcome_contract_version=outcome_contract_version,
        outcome_revision=outcome_revision,
    )
    record_content = {
        "outcome_id": outcome_identity,
        "outcome_revision": outcome_revision,
        "supersedes_outcome_id": supersedes_outcome_id,
        "source_type": source_type.value,
        "source_identity": source_identity,
        "created_at": created_at,
        "calculation_digest": digest,
        **content,
    }
    return ForwardOutcomeContract(
        outcome_id=outcome_identity,
        opportunity_id=opportunity_id,
        evidence_id=evidence_id,
        horizon=horizon,
        outcome_revision=outcome_revision,
        supersedes_outcome_id=supersedes_outcome_id,
        outcome_contract_version=outcome_contract_version,
        calculation_status=calculation_status,
        opportunity_lifecycle_at_horizon=opportunity_lifecycle_at_horizon,
        due_at=due_at,
        source_type=source_type,
        source_identity=source_identity,
        reference_bbo_observation_id=reference_bbo_observation_id,
        end_bbo_observation_id=end_bbo_observation_id,
        reference_price=reference_price,
        end_bid=end_bid,
        end_ask=end_ask,
        mfe=mfe,
        mae=mae,
        reference_return=reference_return,
        executable_long_return=executable_long_return,
        cost_adjusted_forward_return=cost_adjusted_forward_return,
        completeness_diagnostics=diagnostics,
        cost_policy=cost_policy,
        cost_model_version=cost_model_version,
        calculator_version=calculator_version,
        calculation_digest=digest,
        calculation_digest_version=CALCULATION_DIGEST_VERSION,
        outcome_record_hash=outcome_record_hash(record_content),
        outcome_record_hash_version=OUTCOME_RECORD_HASH_VERSION,
        created_at=created_at,
    )


# --- Append-only attribution lineage -----------------------------------------------------


class AttributionEvent(BaseModel):
    """Generic, versioned, append-only attribution event.

    Carries lineage for AI / Plan / Risk / Execution / Economic result without
    redefining any existing G3/G4 economic semantics.
    """

    model_config = ConfigDict(frozen=True)

    attribution_event_id: str
    contract_version: str
    subject_type: AttributionSubjectType
    subject_id: str | None = None
    event_type: str = Field(min_length=1)
    opportunity_id: str | None = None
    evidence_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str
    occurred_at: datetime
    recorded_at: datetime

    _aware_times = field_validator("occurred_at", "recorded_at")(_aware)

    @model_validator(mode="after")
    def _identities_are_consistent(self) -> AttributionEvent:
        if self.payload_hash != attribution_payload_hash(self.payload):
            raise ValueError("payload_hash does not match the attribution payload")
        expected = identity.attribution_event_id(
            contract_version=self.contract_version,
            subject_type=self.subject_type.value,
            subject_id=self.subject_id,
            event_type=self.event_type,
            opportunity_id=self.opportunity_id,
            evidence_id=self.evidence_id,
            payload_hash=self.payload_hash,
            occurred_at=self.occurred_at,
        )
        if self.attribution_event_id != expected:
            raise ValueError("attribution_event_id does not match its deterministic derivation")
        return self


def build_attribution_event(
    *,
    subject_type: AttributionSubjectType,
    event_type: str,
    occurred_at: datetime,
    recorded_at: datetime,
    payload: dict[str, Any],
    subject_id: str | None = None,
    opportunity_id: str | None = None,
    evidence_id: str | None = None,
    contract_version: str = ATTRIBUTION_CONTRACT_VERSION,
) -> AttributionEvent:
    payload_digest = attribution_payload_hash(payload)
    return AttributionEvent(
        attribution_event_id=identity.attribution_event_id(
            contract_version=contract_version,
            subject_type=subject_type.value,
            subject_id=subject_id,
            event_type=event_type,
            opportunity_id=opportunity_id,
            evidence_id=evidence_id,
            payload_hash=payload_digest,
            occurred_at=occurred_at,
        ),
        contract_version=contract_version,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        opportunity_id=opportunity_id,
        evidence_id=evidence_id,
        payload=payload,
        payload_hash=payload_digest,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
    )
