"""SE-02D-I01: deterministic Family Aggregation / Forward-Outcome Expectancy core.

Pure domain module. It performs **no** database work: no session, no SQL, no
loader, no schema, no scheduler and no runtime host. It consumes
already-canonicalized *aggregation scope facts* and produces an immutable,
reproducible aggregate result.

Explicit boundary (task SE-02D-I01 section 7): this module does **not** fold
revision chains. Producing these facts -- reading the full visible Evidence
revision chain in one stable snapshot, validating and folding it to a canonical
Evidence head, then doing the same for the exact-horizon Outcome chain -- is the
responsibility of a later, separately authorized layer. I01 only proves that
*given* those facts the aggregate is a deterministic function of them.

Owned behaviour (Accepted ``SE-02D-D01`` V1 contract):

* Population Key / Population Aggregate Identity / Measurement Signature;
* maturity, population coverage and every coverage denominator;
* COMPLETE Measurement Signature compatibility (fail closed when mixed);
* deterministic Expectancy and descriptive statistics over ``math.fsum``;
* overlap clustering of ``[evidence_at, due_at]`` intervals (overlap **or** touch,
  transitively collapsed);
* deterministic overlap-cluster percentile bootstrap
  (``SHA256_COUNTER_REJECTION_V1``) with exact percentile indices;
* evidence sufficiency including leave-one-cluster-out stability;
* tail evidence; manifest diagnostics; deterministic fingerprint primitive.

Explicitly **not** owned here: KEEP / DOWNWEIGHT / KILL, any threshold, any
strategy / risk / execution / Gate C / Live action. This module emits evidence
only (task section 31).

Frozen version literals (Accepted Design pointers):

============================  ==================================================
``AGGREGATION_CONTRACT_VERSION``  D01 section 16, frozen literal
``RNG_ALGORITHM_VERSION``         D01 section 10.1 item 7, frozen literal
``VISIBILITY_MODE``               D01 section 5.1 / 9.1, frozen literal
``UNCERTAINTY_METHOD_VERSION``    Human Design Clarification 2026-09-15
                                  (the Accepted D01 named the seed input but
                                  never froze its literal; the value below is
                                  the explicitly authorized clarification and
                                  changes no accepted statistical semantics)
============================  ==================================================

Determinism notes:

* every derived sequence is sorted before use, so the input order of ``facts``
  cannot change any output value (permutation invariance). Sorting keys are always
  built from the frozen fields; the arithmetic accumulation order is a separate,
  explicitly named concept (see the next two notes);
* identity encoding is **structural** (SE02D-I01-R1). Semantic compatibility --
  population identity, sample identity, Measurement Signature distinctness -- is
  decided on the frozen field tuples themselves. Derived strings exist only for
  ordering, diagnostics and set keys, and are produced through the accepted G5
  boundary as ``canonical_bytes(payload).hex()`` so they are injective. A
  delimiter-joined ``field=value|...`` rendering is never used, because field
  values may themselves contain ``|`` or ``=`` and could then collapse two
  structurally different identities into one bucket;
* two arithmetic orders are kept explicitly apart (SE02D-I01-R2, D01 section 7.1).
  ``sample_id`` lexical ascending is the **accumulation** order for the headline
  mean, the variance/standard-deviation accumulation and the sign counts, and is
  passed to :func:`economic_statistics` unchanged. A value-sorted copy is used only
  for the order statistics that are defined on value order -- ``median``,
  ``worst_observation`` and ``worst_decile_mean``. ``math.fsum`` is exactly rounded
  and therefore order-independent, which is precisely why the order must be frozen
  by contract rather than left to an implicit sort: swapping to a non-exact
  accumulator would otherwise change the published number;
* ``ceil(0.10 * n)`` is implemented as the exact integer ceiling ``-(-n // 10)``.
  ``math.ceil(0.10 * n)`` is a floating-point expression whose result can drift
  from its own mathematical definition; the exact form is provably identical on
  the sample sizes reachable here and is asserted against the float form in the
  focused tests;
* the rejection-sampling counters ``j`` and ``k`` are both 0-based counters, in
  keeping with ``j = replicate_index * n_clusters + draw_index`` which is 0-based
  by construction;
* the leave-one-cluster-out recomputation reuses the *unchanged* frozen seed
  derivation and only varies the cluster count, so no second seed scheme is
  invented.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from marketpulse.market_data.models import MarketType

from .forward import ForwardOutcomeReason
from .hashing import canonical_bytes
from .models import (
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
)

# --- Frozen version / policy constants ---------------------------------------------------

#: D01 section 16, frozen literal.
AGGREGATION_CONTRACT_VERSION = "se02d-family-aggregation-v1"

#: Human Design Clarification, 2026-09-15. The Accepted D01 listed
#: ``uncertainty_method_version`` as a seed component (section 10.1 item 6) and
#: required I01 to expose it as a constant, but never froze its literal. The
#: clarification supplies exactly that missing identifier and changes no
#: accepted statistical semantics.
UNCERTAINTY_METHOD_VERSION = "se02d-overlap-cluster-percentile-bootstrap-v1"

#: D01 section 10.1 item 7, frozen literal.
RNG_ALGORITHM_VERSION = "SHA256_COUNTER_REJECTION_V1"

#: D01 section 5.1 / 9.1, frozen literal.
VISIBILITY_MODE = "CURRENT_STABLE_SNAPSHOT"

#: D01 section 10.1 item 5 / task section 22: frozen resample count and the exact
#: percentile indices ``[ceil(0.025 * 10000) - 1, ceil(0.975 * 10000) - 1]``.
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_LOWER_INDEX = 249
BOOTSTRAP_UPPER_INDEX = 9749
BOOTSTRAP_LOWER_QUANTILE = 0.025
BOOTSTRAP_UPPER_QUANTILE = 0.975
CONFIDENCE_LEVEL = "TWO_SIDED_95"

#: D01 section 10.1 item 8 / task section 24.
MIN_CLUSTERS_FOR_INTERVAL = 2

#: D01 section 12.1: after removing one whole cluster at least two clusters must
#: remain for the uncertainty interval to stay computable.
MIN_CLUSTERS_FOR_SUFFICIENCY = 3

#: D01 section 12.1: no Missing-At-Random model exists in V1, so a statistically
#: resolved claim needs complete coverage.
REQUIRED_COVERAGE_RATE = 1.0

#: D01 section 12.2: ``k = max(1, ceil(0.10 * n))``, exact integer form.
WORST_DECILE_DENOMINATOR = 10

#: D01 section 10.3, frozen literals.
DEPENDENCE_LIMITATIONS = (
    "BEYOND_HORIZON_SERIAL_DEPENDENCE_UNMODELED",
    "REGIME_IDENTITY_UNAVAILABLE",
)

#: D01 section 13, frozen literals.
REGIME_GATE = "NONE_IN_SE02D_V1"
REGIME_SUFFICIENCY = "NOT_EVALUABLE"

#: D01 section 8.4, frozen literal: every artifact must display this statement.
INTEGRITY_STATEMENT = "Positive Expectancy != Evidence Completeness Proven."

#: D01 section 8.4: opportunities lost before Capture Anchor durability and
#: opportunities rejected by the session-start fence are not countable from the
#: current tables. I01 cannot count them and must not pretend they are covered.
UNOBSERVABLE_COVERAGE_LIMITATIONS = (
    (
        "opportunities lost before Capture Anchor durability, and opportunities "
        "rejected by the session-start fence, are not countable from the current "
        "tables and are absent from every denominator reported here"
    ),
)

#: D01 section 9.2: the manifest records the canonical Measurement Signature, or
#: this marker when no canonical Outcome exists.
NO_MEASUREMENT = "NO_MEASUREMENT"

_TWO_POW_256 = 1 << 256

#: D01 section 8.3: reason tokens that must be preserved verbatim.
KNOWN_OUTCOME_REASONS = frozenset(reason.value for reason in ForwardOutcomeReason)


class AggregationError(ValueError):
    """Base class for every fail-closed pure-layer aggregation error."""


class DuplicateSampleIdentityError(AggregationError):
    """Two facts collapsed onto one ``(population_key, horizon, opportunity_id)``.

    D01 section 4.1 allows at most one canonical sample per logical opportunity
    and horizon. A duplicate is never resolved by keeping the first, keeping the
    last or silently de-duplicating.
    """


class ForeignScopeFactError(AggregationError):
    """A supplied fact does not belong to the requested aggregate identity."""


# --- Enumerations ------------------------------------------------------------------------


class AggregateStatus(StrEnum):
    """Headline aggregate status.

    Fail-closed precedence (task section 28): ``INTEGRITY_CONFLICT`` >
    ``INCOMPATIBLE_MEASUREMENT_SIGNATURES`` > ``NOT_APPLICABLE`` >
    ``NOT_CALCULABLE`` > ``VALID``.
    """

    VALID = "VALID"
    NOT_CALCULABLE = "NOT_CALCULABLE"
    INCOMPATIBLE_MEASUREMENT_SIGNATURES = "INCOMPATIBLE_MEASUREMENT_SIGNATURES"
    INTEGRITY_CONFLICT = "INTEGRITY_CONFLICT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MaturityClass(StrEnum):
    """Per-scope maturity / coverage classification (task sections 12-13)."""

    NOT_YET_DUE = "NOT_YET_DUE"
    COMPLETE = "COMPLETE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID = "INVALID"
    MISSING_OUTCOME = "MISSING_OUTCOME"


class MeasurementSignatureState(StrEnum):
    """D01 section 16 ``measurement_signature`` state machine."""

    EXACT = "EXACT"
    NO_MEASUREMENT = "NO_MEASUREMENT"
    MIXED = "MIXED"


class Calculability(StrEnum):
    """D01 section 12.1 calculability ladder."""

    NOT_CALCULABLE = "NOT_CALCULABLE"
    CALCULABLE_DESCRIPTIVE_ONLY = "CALCULABLE_DESCRIPTIVE_ONLY"
    CALCULABLE_WITH_UNCERTAINTY = "CALCULABLE_WITH_UNCERTAINTY"


class IntervalSide(StrEnum):
    """Side of zero an interval resolves to. ``None`` means "not resolved"."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class UncertaintyUnavailableReason(StrEnum):
    """D01 section 10.1 item 8."""

    TOO_FEW_CLUSTERS = "TOO_FEW_CLUSTERS"
    DEGENERATE_SAMPLE = "DEGENERATE_SAMPLE"


class SufficiencyReason(StrEnum):
    """Why ``evidence_sufficient`` is false. Never a K/D/K verdict."""

    INTEGRITY_CONFLICT_PRESENT = "INTEGRITY_CONFLICT_PRESENT"
    INCOMPATIBLE_MEASUREMENT_SIGNATURES = "INCOMPATIBLE_MEASUREMENT_SIGNATURES"
    MARKET_TYPE_NOT_APPLICABLE = "MARKET_TYPE_NOT_APPLICABLE"
    NO_ECONOMIC_SAMPLES = "NO_ECONOMIC_SAMPLES"
    COVERAGE_BELOW_ONE = "COVERAGE_BELOW_ONE"
    TOO_FEW_CLUSTERS = "TOO_FEW_CLUSTERS"
    NO_BOOTSTRAP_INTERVAL = "NO_BOOTSTRAP_INTERVAL"
    DEGENERATE_INTERVAL = "DEGENERATE_INTERVAL"
    INTERVAL_CONTAINS_ZERO = "INTERVAL_CONTAINS_ZERO"
    LEAVE_ONE_CLUSTER_OUT_UNSTABLE = "LEAVE_ONE_CLUSTER_OUT_UNSTABLE"


# --- Identity contracts ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PopulationKey:
    """D01 section 6.1 Population Key.

    Only canonical-Evidence-head facts may populate this key, so coverage
    membership exists even when no Outcome exists. ``source_manifest_id`` is
    deliberately **not** a member: D01 section 6.3 classifies it as provenance /
    stratification.
    """

    family_id: EdgeFamily
    family_version: str
    instrument_id: str
    market_type: MarketType
    source_type: EvidenceSource
    source_identity: str
    evidence_contract_version: str

    def canonical_payload(self) -> dict[str, str]:
        return {
            "family_id": self.family_id.value,
            "family_version": self.family_version,
            "instrument_id": self.instrument_id,
            "market_type": self.market_type.value,
            "source_type": self.source_type.value,
            "source_identity": self.source_identity,
            "evidence_contract_version": self.evidence_contract_version,
        }

    def canonical_key(self) -> str:
        """Collision-safe derived representation of this key.

        Derived through the accepted G5 canonicalization boundary:
        ``canonical_bytes(canonical_payload()).hex()``. A delimiter-joined
        ``field=value|...`` rendering is **not** injective, because values may
        themselves contain ``|`` or ``=``, so two structurally different keys could
        share one derived string (SE02D-I01-R1). This representation cannot.

        Structural equality of this dataclass -- not this string -- remains the
        semantic authority for population identity.
        """

        return canonical_bytes(self.canonical_payload()).hex()


@dataclass(frozen=True, slots=True)
class MeasurementSignature:
    """D01 section 6.1 Measurement Signature.

    Controls economic compatibility **only**. It never controls population
    membership, maturity, missing outcome or any coverage denominator.
    """

    outcome_contract_version: str
    calculator_version: str
    cost_policy: str
    cost_model_version: str
    outcome_source_type: EvidenceSource
    outcome_source_identity: str

    def canonical_payload(self) -> dict[str, str]:
        return {
            "outcome_contract_version": self.outcome_contract_version,
            "calculator_version": self.calculator_version,
            "cost_policy": self.cost_policy,
            "cost_model_version": self.cost_model_version,
            "outcome_source_type": self.outcome_source_type.value,
            "outcome_source_identity": self.outcome_source_identity,
        }

    def canonical_key(self) -> str:
        """Collision-safe **diagnostic** identity of this signature.

        Diagnostic / ordering output only. It is derived through the accepted G5
        boundary as ``canonical_bytes(canonical_payload()).hex()``, so different
        canonical payloads always give different keys and the same six-field
        payload always gives the same key (SE02D-I01-R1).

        Semantic compatibility is decided by this dataclass's structural
        equality/hash -- the six frozen fields themselves. It is never decided by
        this string, and never by a digest standing in for the fields.
        """

        return canonical_bytes(self.canonical_payload()).hex()


@dataclass(frozen=True, slots=True)
class AggregateIdentity:
    """D01 section 6.1 Population Aggregate Identity = ``(population_key, horizon)``."""

    population_key: PopulationKey
    horizon: ForwardHorizon


# --- Canonical scope input ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CanonicalScopeFacts:
    """One logical opportunity's already-canonicalized aggregation facts.

    This is **not** a durable entity and deliberately does not reproduce the ORM
    schema. It is the pure-layer projection of:

    ``full visible Evidence revision chain -> validated canonical Evidence head ->
    full visible exact-horizon Outcome revision chain -> canonical Outcome head or
    an explicit ``NO_OUTCOME`` marker``

    produced by a later, separately authorized layer. ``outcome_id is None`` is
    the explicit ``NO_OUTCOME`` marker; in that state no Outcome contract,
    calculator or cost version may be supplied or guessed, which is what lets
    ``MISSING_OUTCOME`` land in the right coverage denominator (D01 section 8.2).
    """

    opportunity_id: str
    population_key: PopulationKey
    horizon: ForwardHorizon

    # canonical Evidence head
    evidence_id: str
    evidence_revision: int
    evidence_hash: str
    evidence_at: datetime
    due_at: datetime

    # provenance / stratification
    source_manifest_id: str
    reference_data_status: ReferenceDataStatus

    # canonical Outcome head, or the explicit NO_OUTCOME marker
    outcome_id: str | None = None
    outcome_revision: int | None = None
    outcome_record_hash: str | None = None
    outcome_status: OutcomeCalculationStatus | None = None
    outcome_reason: str | None = None
    measurement_signature: MeasurementSignature | None = None

    # economic facts (only meaningful for a COMPLETE canonical Outcome)
    cost_adjusted_forward_return: float | None = None
    reference_return: float | None = None
    executable_long_return: float | None = None
    mfe: float | None = None
    mae: float | None = None

    lifecycle: OpportunityLifecycleAtHorizon | None = None

    # upstream folding diagnostics (counts only: I01 does not fold chains)
    folded_evidence_revision_count: int = 0
    folded_outcome_revision_count: int = 0
    outcomes_excluded_with_folded_evidence: int = 0

    def __post_init__(self) -> None:
        for label, value in (
            ("opportunity_id", self.opportunity_id),
            ("evidence_id", self.evidence_id),
            ("evidence_hash", self.evidence_hash),
            ("source_manifest_id", self.source_manifest_id),
        ):
            if not isinstance(value, str) or not value:
                raise AggregationError(f"{label} must be a non-empty string")

        if self.evidence_revision < 1:
            raise AggregationError("evidence_revision must be at least 1")
        for label, count in (
            ("folded_evidence_revision_count", self.folded_evidence_revision_count),
            ("folded_outcome_revision_count", self.folded_outcome_revision_count),
            ("outcomes_excluded_with_folded_evidence", self.outcomes_excluded_with_folded_evidence),
        ):
            if count < 0:
                raise AggregationError(f"{label} must not be negative")

        if self.due_at <= self.evidence_at:
            raise AggregationError("due_at must be strictly after evidence_at")

        if self.outcome_id is None:
            if any(
                value is not None
                for value in (
                    self.outcome_revision,
                    self.outcome_record_hash,
                    self.outcome_status,
                    self.outcome_reason,
                    self.measurement_signature,
                )
            ):
                raise AggregationError(
                    "the NO_OUTCOME marker must not carry Outcome fields; a canonical "
                    "Outcome contract/calculator/cost version must never be guessed"
                )
            return

        if self.outcome_revision is None or self.outcome_revision < 1:
            raise AggregationError("a canonical Outcome requires outcome_revision >= 1")
        if self.outcome_status is None:
            raise AggregationError("a canonical Outcome requires an outcome_status")
        if (
            self.outcome_status is OutcomeCalculationStatus.COMPLETE
            and self.measurement_signature is None
        ):
            raise AggregationError(
                "a COMPLETE canonical Outcome must carry its Measurement Signature"
            )

    @property
    def sample_id(self) -> str:
        """Frozen sample identity rendered as one collision-safe string.

        The frozen *identity* is ``(population_key, horizon, opportunity_id)``;
        inside a single aggregate the first two components are constant. The
        population component is rendered through the collision-safe
        :meth:`PopulationKey.canonical_key`, so an ambiguous ``field=value|...``
        rendering can never make two structurally different identities share one
        ``sample_id`` (SE02D-I01-R1). Within one aggregate this therefore renders a
        total order on ``opportunity_id``, which is the order D01 section 7.1
        freezes for the headline ``math.fsum`` accumulation.
        """

        return f"{self.population_key.canonical_key()}|{self.horizon.value}|{self.opportunity_id}"


def sample_identity(facts: CanonicalScopeFacts) -> tuple[PopulationKey, ForwardHorizon, str]:
    """Freeze the D01 section 4.1 sample identity as a comparable tuple.

    This structured tuple -- not the derived :attr:`CanonicalScopeFacts.sample_id`
    string -- is the semantic authority for duplicate detection. The derived string
    is only ever an ordering / diagnostic / set-key rendering, and it is
    collision-safe so it can be used for those purposes without ever merging two
    structurally different identities (SE02D-I01-R1).
    """

    return (facts.population_key, facts.horizon, facts.opportunity_id)


# --- Maturity / integrity ------------------------------------------------------------------


def classify_maturity(facts: CanonicalScopeFacts, *, as_of: datetime) -> MaturityClass:
    """D01 section 4.2 / task sections 12-13 maturity classification.

    ``NOT_YET_DUE`` is decided first and never enters the mature denominator. A
    canonical Outcome that is absent after the exact-scope lookup is
    ``MISSING_OUTCOME`` and is never back-filled from a superseded revision.
    """

    if facts.due_at > as_of:
        return MaturityClass.NOT_YET_DUE
    if facts.outcome_id is None:
        return MaturityClass.MISSING_OUTCOME
    if facts.outcome_status is OutcomeCalculationStatus.COMPLETE:
        return MaturityClass.COMPLETE
    if facts.outcome_status is OutcomeCalculationStatus.INSUFFICIENT_DATA:
        return MaturityClass.INSUFFICIENT_DATA
    if facts.outcome_status is OutcomeCalculationStatus.INVALID:
        return MaturityClass.INVALID
    raise AggregationError(f"unsupported canonical outcome status: {facts.outcome_status!r}")


def integrity_conflicts(facts: CanonicalScopeFacts, maturity: MaturityClass) -> tuple[str, ...]:
    """Pure-layer integrity conflicts for one mature scope (task section 15).

    A canonical COMPLETE sample that requires an economic return which is
    ``None``, ``NaN`` or ``+/-Infinity`` is a conflict, not a removable row. The
    conflict is recorded and the aggregate fails closed; the raw ``COMPLETE``
    status count stays visible in coverage.
    """

    if maturity is not MaturityClass.COMPLETE:
        return ()

    value = facts.cost_adjusted_forward_return
    if value is None:
        return ("COMPLETE_RETURN_MISSING",)
    if not math.isfinite(value):
        return ("COMPLETE_RETURN_NON_FINITE",)
    return ()


# --- Canonical manifest / fingerprint -------------------------------------------------------


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _hex(value: float | None) -> str | None:
    return None if value is None else value.hex()


def _reason_token(reason: str | None, maturity: MaturityClass) -> str:
    """Preserve every durable reason; flag unknown ones without rewriting them.

    D01 section 8.3: ``REFERENCE_MISSING`` / ``REFERENCE_STALE`` /
    ``ENDPOINT_MISSING`` / ``ENDPOINT_STALE`` and every durable ``INVALID_*``
    value must survive, and an unknown reason is ``UNKNOWN_REASON`` plus its
    exact raw value.
    """

    if reason is None:
        return maturity.value
    if reason in KNOWN_OUTCOME_REASONS:
        return reason
    return f"UNKNOWN_REASON:{reason}"


def build_ordered_input_manifest(
    facts: Sequence[CanonicalScopeFacts], *, as_of: datetime
) -> tuple[dict[str, Any], ...]:
    """Deterministic canonical input manifest (D01 section 9.2).

    Ordered by ``(opportunity_id, evidence_id, horizon)``. Every entry records the
    Population Key and the horizon, as D01 section 9.2 requires (SE02D-I01-R3), and
    numeric returns are recorded as their exact ``float.hex()`` bit representation,
    so the manifest binds the precise bits that produced the aggregate.

    Boundary note: I01 does not fold revision chains, so it can record the folded
    revision *counts* but not the identity of every folded revision. A later
    folding layer that owns the chains must extend the manifest accordingly.
    """

    ordered = sorted(facts, key=lambda item: (item.opportunity_id, item.evidence_id, item.horizon.value))
    entries: list[dict[str, Any]] = []
    for item in ordered:
        maturity = classify_maturity(item, as_of=as_of)
        signature = item.measurement_signature
        entries.append(
            {
                "opportunity_id": item.opportunity_id,
                # D01 section 9.2 requires every logical opportunity's entry to
                # record the Population Key as well as the horizon (SE02D-I01-R3).
                # The value is the frozen ``canonical_payload()`` projection, never
                # a locally reconstructed key.
                "population_key": item.population_key.canonical_payload(),
                "horizon": item.horizon.value,
                "evidence_id": item.evidence_id,
                "evidence_revision": item.evidence_revision,
                "evidence_hash": item.evidence_hash,
                "evidence_role": "CANONICAL",
                "evidence_at": _iso(item.evidence_at),
                "due_at": _iso(item.due_at),
                "reference_data_status": item.reference_data_status.value,
                "source_manifest_id": item.source_manifest_id,
                "lifecycle": None if item.lifecycle is None else item.lifecycle.value,
                "folded_evidence_revision_count": item.folded_evidence_revision_count,
                "folded_outcome_revision_count": item.folded_outcome_revision_count,
                "outcomes_excluded_with_folded_evidence": (
                    item.outcomes_excluded_with_folded_evidence
                ),
                "maturity_marker": maturity.value,
                "outcome_id": item.outcome_id,
                "outcome_revision": item.outcome_revision,
                "outcome_record_hash": item.outcome_record_hash,
                "outcome_status": None if item.outcome_status is None else item.outcome_status.value,
                "outcome_reason": item.outcome_reason,
                "measurement_signature": (
                    NO_MEASUREMENT if signature is None else signature.canonical_payload()
                ),
                "cost_adjusted_forward_return_hex": _hex(item.cost_adjusted_forward_return),
                "reference_return_hex": _hex(item.reference_return),
                "executable_long_return_hex": _hex(item.executable_long_return),
                "mfe_hex": _hex(item.mfe),
                "mae_hex": _hex(item.mae),
                "integrity_conflicts": list(integrity_conflicts(item, maturity)),
            }
        )
    return tuple(entries)


def compute_input_fingerprint(
    *,
    as_of: datetime,
    population_key: PopulationKey,
    horizon: ForwardHorizon,
    ordered_input_manifest: Sequence[Mapping[str, Any]],
) -> str:
    """D01 section 9.3 fingerprint primitive.

    Reuses the accepted :func:`marketpulse.edge.hashing.canonical_bytes` G5
    canonicalization boundary -- no second serializer exists. Non-finite canonical
    data fails closed inside that boundary. The caller may supply the manifest
    (I01 never queries a database to construct it); the same input must always
    produce the same fingerprint and a changed manifest must change it.
    """

    payload = {
        "aggregation_contract_version": AGGREGATION_CONTRACT_VERSION,
        "visibility_mode": VISIBILITY_MODE,
        "as_of": as_of,
        "population_key": population_key.canonical_payload(),
        "horizon": horizon.value,
        "ordered_input_manifest": [dict(entry) for entry in ordered_input_manifest],
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def bootstrap_seed(
    *,
    population_key: PopulationKey,
    horizon: ForwardHorizon,
    as_of: datetime,
    input_fingerprint: str,
) -> bytes:
    """D01 section 10.1 item 6: the frozen 32-byte RNG seed digest."""

    payload = {
        "aggregation_contract_version": AGGREGATION_CONTRACT_VERSION,
        "population_key": population_key.canonical_payload(),
        "horizon": horizon.value,
        "as_of": as_of,
        "input_fingerprint": input_fingerprint,
        "uncertainty_method_version": UNCERTAINTY_METHOD_VERSION,
    }
    return hashlib.sha256(canonical_bytes(payload)).digest()


# --- Deterministic RNG ---------------------------------------------------------------------


def uint256_be_draw(seed: bytes, draw_ordinal: int, attempt: int) -> int:
    """One ``SHA256_COUNTER_REJECTION_V1`` rejection attempt (D01 section 10.1 item 7).

    ``u = uint256_be(SHA256(seed || uint64_be(j) || uint32_be(k)))`` with the
    rejected-attempt counter ``k`` starting at ``0`` -- the same 0-based counter
    convention as ``j = replicate_index * n_clusters + draw_index``.
    """

    if draw_ordinal < 0:
        raise AggregationError("draw ordinal must not be negative")
    if attempt < 0:
        raise AggregationError("rejection attempt counter must not be negative")
    digest = hashlib.sha256(
        seed + draw_ordinal.to_bytes(8, "big") + attempt.to_bytes(4, "big")
    ).digest()
    return int.from_bytes(digest, "big")


def draw_cluster_index(seed: bytes, n_clusters: int, draw_ordinal: int) -> int:
    """Rejection-sample one cluster index in ``range(n_clusters)``.

    ``limit = 2**256 - (2**256 mod n_clusters)``; the first ``u < limit`` wins and
    yields ``u mod n_clusters``. Rejection (rather than a plain modulo) is what
    keeps the draw exactly uniform.
    """

    if n_clusters < 1:
        raise AggregationError("n_clusters must be at least 1")
    limit = _TWO_POW_256 - (_TWO_POW_256 % n_clusters)
    attempt = 0
    while True:
        value = uint256_be_draw(seed, draw_ordinal, attempt)
        if value < limit:
            return value % n_clusters
        attempt += 1


# --- Overlap clustering --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OverlapCluster:
    """One connected component of overlapping-or-touching sample intervals."""

    cluster_id: int
    sample_ids: tuple[str, ...]
    opportunity_ids: tuple[str, ...]
    returns: tuple[float, ...]
    interval_start: datetime
    interval_end: datetime


def cluster_samples(samples: Sequence[CanonicalScopeFacts]) -> tuple[OverlapCluster, ...]:
    """Cluster ``[evidence_at, due_at]`` intervals (task section 20).

    Sweep order is ``(evidence_at, opportunity_id)``. Two closed intervals that
    overlap **or merely touch** belong to the same component, and overlap is
    transitive: ``A~B`` and ``B~C`` collapse to a single cluster even when ``A``
    and ``C`` do not intersect directly. No time bucket and no regime inference is
    used, and cluster ids follow the deterministic sweep order.
    """

    ordered = sorted(samples, key=lambda item: (item.evidence_at, item.opportunity_id))
    clusters: list[OverlapCluster] = []
    for item in ordered:
        if item.cost_adjusted_forward_return is None:
            raise AggregationError("overlap clustering requires a finite economic return")
        value = item.cost_adjusted_forward_return
        if clusters:
            current = clusters[-1]
            if item.evidence_at <= current.interval_end:
                clusters[-1] = OverlapCluster(
                    cluster_id=current.cluster_id,
                    sample_ids=(*current.sample_ids, item.sample_id),
                    opportunity_ids=(*current.opportunity_ids, item.opportunity_id),
                    returns=(*current.returns, value),
                    interval_start=current.interval_start,
                    interval_end=max(current.interval_end, item.due_at),
                )
                continue
        clusters.append(
            OverlapCluster(
                cluster_id=len(clusters),
                sample_ids=(item.sample_id,),
                opportunity_ids=(item.opportunity_id,),
                returns=(value,),
                interval_start=item.evidence_at,
                interval_end=item.due_at,
            )
        )
    return tuple(clusters)


# --- Bootstrap interval ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    """Deterministic overlap-cluster percentile bootstrap outcome."""

    n_clusters: int
    n_resamples: int
    confidence_level: str
    lower_index: int
    upper_index: int
    lower: float | None
    upper: float | None
    unavailable_reason: UncertaintyUnavailableReason | None
    is_degenerate: bool | None
    excludes_zero: bool | None
    side: IntervalSide | None
    seed_hex: str
    rng_algorithm_version: str


def replicate_means(
    *,
    clusters: Sequence[OverlapCluster],
    seed: bytes,
    n_resamples: int,
) -> tuple[float, ...]:
    """Every replicate's mean over the observations its drawn clusters carry.

    One replicate draws ``n_clusters`` clusters **with replacement**; each draw is
    a whole cluster, so selecting a cluster contributes all of its observations.
    The replicate mean is therefore the arithmetic mean of the carried
    observations (sample-weighted), never an equal-weight mean of cluster means.
    Observations are accumulated in deterministic draw-then-member order so the
    ordered ``fsum`` can never depend on an arbitrary container order.
    """

    n_clusters = len(clusters)
    if n_clusters < 1:
        raise AggregationError("bootstrap requires at least one overlap cluster")

    means: list[float] = []
    for replicate_index in range(n_resamples):
        carried: list[float] = []
        for draw_index in range(n_clusters):
            ordinal = replicate_index * n_clusters + draw_index
            carried.extend(clusters[draw_cluster_index(seed, n_clusters, ordinal)].returns)
        means.append(math.fsum(carried) / len(carried))
    return tuple(means)


def percentile_interval(
    *,
    clusters: Sequence[OverlapCluster],
    seed: bytes,
    n_resamples: int = BOOTSTRAP_REPLICATES,
) -> BootstrapInterval:
    """D01 section 10.1: deterministic overlap-cluster percentile bootstrap.

    The interval is ``[b[249], b[9749]]`` over the ascending replicate means --
    exact indices, no interpolation and no external statistics library. When the
    sample cannot support an interval the result is ``NULL`` with an explicit
    reason and **no** zero-width "high certainty" interval is ever emitted.
    """

    n_clusters = len(clusters)
    seed_hex = seed.hex()

    def unavailable(reason: UncertaintyUnavailableReason) -> BootstrapInterval:
        return BootstrapInterval(
            n_clusters=n_clusters,
            n_resamples=n_resamples,
            confidence_level=CONFIDENCE_LEVEL,
            lower_index=BOOTSTRAP_LOWER_INDEX,
            upper_index=BOOTSTRAP_UPPER_INDEX,
            lower=None,
            upper=None,
            unavailable_reason=reason,
            is_degenerate=None,
            excludes_zero=None,
            side=None,
            seed_hex=seed_hex,
            rng_algorithm_version=RNG_ALGORITHM_VERSION,
        )

    if n_clusters < MIN_CLUSTERS_FOR_INTERVAL:
        return unavailable(UncertaintyUnavailableReason.TOO_FEW_CLUSTERS)

    observations = [value for cluster in clusters for value in cluster.returns]
    if len(set(observations)) <= 1:
        return unavailable(UncertaintyUnavailableReason.DEGENERATE_SAMPLE)

    ordered_means = sorted(replicate_means(clusters=clusters, seed=seed, n_resamples=n_resamples))
    lower = ordered_means[BOOTSTRAP_LOWER_INDEX]
    upper = ordered_means[BOOTSTRAP_UPPER_INDEX]
    degenerate = lower == upper
    if lower > 0.0:
        side = IntervalSide.POSITIVE
    elif upper < 0.0:
        side = IntervalSide.NEGATIVE
    else:
        side = None
    return BootstrapInterval(
        n_clusters=n_clusters,
        n_resamples=n_resamples,
        confidence_level=CONFIDENCE_LEVEL,
        lower_index=BOOTSTRAP_LOWER_INDEX,
        upper_index=BOOTSTRAP_UPPER_INDEX,
        lower=lower,
        upper=upper,
        unavailable_reason=None,
        is_degenerate=degenerate,
        excludes_zero=side is not None,
        side=side,
        seed_hex=seed_hex,
        rng_algorithm_version=RNG_ALGORITHM_VERSION,
    )


# --- Descriptive statistics / tail ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EconomicStatistics:
    """D01 section 7.2 minimum secondary evidence set."""

    n_economic_samples: int
    mean: float
    median: float
    positive_count: int
    flat_count: int
    negative_count: int
    positive_rate: float
    sample_standard_deviation: float | None
    worst_observation: float
    worst_decile_mean: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_economic_samples": self.n_economic_samples,
            "mean": self.mean,
            "median": self.median,
            "positive_count": self.positive_count,
            "flat_count": self.flat_count,
            "negative_count": self.negative_count,
            "positive_rate": self.positive_rate,
            "sample_standard_deviation": self.sample_standard_deviation,
            "worst_observation": self.worst_observation,
            "worst_decile_mean": self.worst_decile_mean,
        }


@dataclass(frozen=True, slots=True)
class TailEvidence:
    """D01 section 12.2 tail statistic. No pass/fail threshold exists in V1."""

    k: int
    worst_observation: float
    worst_decile_mean: float
    threshold: None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "worst_observation": self.worst_observation,
            "worst_decile_mean": self.worst_decile_mean,
            "acceptable_tail_risk_threshold": None,
        }


def worst_decile_k(n_economic_samples: int) -> int:
    """``k = max(1, ceil(0.10 * n))`` in exact integer arithmetic."""

    if n_economic_samples < 1:
        raise AggregationError("worst-decile k requires at least one economic sample")
    return max(1, -(-n_economic_samples // WORST_DECILE_DENOMINATOR))


def economic_statistics(returns: Sequence[float]) -> EconomicStatistics:
    """Expectancy and the frozen descriptive set.

    Two distinct orderings are used deliberately (SE02D-I01-R2, D01 section 7.1):

    * ``returns`` arrives in the caller's **sample order** -- ``sample_id`` lexical
      ascending -- and every arithmetic accumulation that the Accepted contract
      ties to that order uses exactly this sequence: the headline mean, the
      variance / standard-deviation accumulation and the sign counts. The sequence
      is never value-sorted before accumulation.
    * a private ``value_sorted`` copy is used **only** for the order statistics
      that mathematically require value order: ``median``,
      ``worst_observation`` and ``worst_decile_mean``.

    ``math.fsum`` is the required deterministic summation. ``sample_standard_
    deviation`` uses the ``n - 1`` denominator and is ``NULL`` below two samples.
    Units stay dimensionless decimal returns where ``0.01 == +1%`` and the sign
    split uses no epsilon.
    """

    if not returns:
        raise AggregationError("economic statistics require at least one sample")

    sample_ordered = tuple(returns)
    n = len(sample_ordered)

    # Arithmetic tied to the Accepted sample order: accumulate in that order only.
    mean = math.fsum(sample_ordered) / n
    positive = sum(1 for value in sample_ordered if value > 0.0)
    negative = sum(1 for value in sample_ordered if value < 0.0)
    flat = n - positive - negative
    if n < 2:
        deviation: float | None = None
    else:
        deviation = math.sqrt(
            math.fsum((value - mean) ** 2 for value in sample_ordered) / (n - 1)
        )

    # Order statistics only: these are defined on value order by the contract.
    value_sorted = sorted(sample_ordered)
    if n % 2 == 1:
        median = value_sorted[n // 2]
    else:
        median = math.fsum((value_sorted[n // 2 - 1], value_sorted[n // 2])) / 2.0
    k = worst_decile_k(n)

    return EconomicStatistics(
        n_economic_samples=n,
        mean=mean,
        median=median,
        positive_count=positive,
        flat_count=flat,
        negative_count=negative,
        positive_rate=positive / n,
        sample_standard_deviation=deviation,
        worst_observation=value_sorted[0],
        worst_decile_mean=math.fsum(value_sorted[:k]) / k,
    )


# --- Leave-one-cluster-out ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LocoResult:
    """One leave-one-cluster-out recomputation (D01 section 12.1 / task section 26)."""

    removed_cluster_id: int
    removed_opportunity_ids: tuple[str, ...]
    remaining_cluster_count: int
    interval: BootstrapInterval
    preserves_full_side: bool


def leave_one_cluster_out(
    *,
    clusters: Sequence[OverlapCluster],
    full_interval: BootstrapInterval,
    seed: bytes,
    n_resamples: int = BOOTSTRAP_REPLICATES,
) -> tuple[LocoResult, ...]:
    """Remove one whole cluster, recompute the classification, compare the side.

    The frozen seed derivation is reused unchanged -- only the cluster count and
    the observation set vary -- so no second seed scheme is invented. A
    recomputation that cannot produce an interval (including when fewer than two
    clusters would remain) does not preserve the full-result side.
    """

    results: list[LocoResult] = []
    for cluster in clusters:
        remaining = tuple(item for item in clusters if item.cluster_id != cluster.cluster_id)
        interval = percentile_interval(clusters=remaining, seed=seed, n_resamples=n_resamples)
        preserves = (
            full_interval.side is not None
            and interval.side is not None
            and interval.side is full_interval.side
        )
        results.append(
            LocoResult(
                removed_cluster_id=cluster.cluster_id,
                removed_opportunity_ids=cluster.opportunity_ids,
                remaining_cluster_count=len(remaining),
                interval=interval,
                preserves_full_side=preserves,
            )
        )
    return tuple(results)


# --- Coverage / diagnostics ------------------------------------------------------------------


def _histogram(keys: Iterable[str], *, universe: Sequence[str] | None = None) -> dict[str, int]:
    """Deterministic histogram; ``universe`` zero-fills a frozen closed vocabulary.

    D01 section 8.1 freezes ``reference_status_counts`` as exactly
    ``{OK, REFERENCE_MISSING, REFERENCE_STALE}`` and ``lifecycle_counts`` as exactly
    ``{ACTIVE, EXPIRED, NULL}``, so a state that simply did not occur is reported as
    an explicit zero rather than being omitted from the report.
    """

    counts: dict[str, int] = {}
    for key in keys:
        counts[key] = counts.get(key, 0) + 1
    names = set(counts) if universe is None else set(counts) | set(universe)
    return {name: counts.get(name, 0) for name in sorted(names)}


#: D01 section 8.1 frozen closed vocabularies.
REFERENCE_STATUS_KEYS: tuple[str, ...] = tuple(
    status.value for status in ReferenceDataStatus
)
LIFECYCLE_KEYS: tuple[str, ...] = (
    *(lifecycle.value for lifecycle in OpportunityLifecycleAtHorizon),
    "NULL",
)


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """D01 section 8.1 coverage block. Every mature scope lands in exactly one class."""

    eligible_opportunities: int
    not_yet_due: int
    mature_denominator: int
    complete: int
    insufficient_data: int
    invalid: int
    missing_outcome: int
    coverage_rate: float | None
    settlement_rate: float | None
    folded_evidence_revisions: int
    folded_outcome_revisions: int
    outcomes_excluded_with_folded_evidence: int
    integrity_conflict_count: int
    reference_status_counts: dict[str, int]
    lifecycle_counts: dict[str, int]
    status_reason_counts: dict[str, int]
    measurement_signature_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible_opportunities": self.eligible_opportunities,
            "not_yet_due": self.not_yet_due,
            "mature_denominator": self.mature_denominator,
            "complete": self.complete,
            "insufficient_data": self.insufficient_data,
            "invalid": self.invalid,
            "missing_outcome": self.missing_outcome,
            "coverage_rate": self.coverage_rate,
            "settlement_rate": self.settlement_rate,
            "folded_evidence_revisions": self.folded_evidence_revisions,
            "folded_outcome_revisions": self.folded_outcome_revisions,
            "outcomes_excluded_with_folded_evidence": (
                self.outcomes_excluded_with_folded_evidence
            ),
            "integrity_conflict_count": self.integrity_conflict_count,
            "reference_status_counts": dict(self.reference_status_counts),
            "lifecycle_counts": dict(self.lifecycle_counts),
            "status_reason_counts": dict(self.status_reason_counts),
            "measurement_signature_counts": dict(self.measurement_signature_counts),
        }


@dataclass(frozen=True, slots=True)
class ManifestDiagnostics:
    """D01 section 6.3: ``source_manifest_id`` is provenance, never a population key."""

    manifest_counts: dict[str, int]
    manifest_count: int
    ordered_manifest_ids: tuple[str, ...]
    max_manifest_concentration: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_counts": dict(self.manifest_counts),
            "manifest_count": self.manifest_count,
            "ordered_manifest_ids": list(self.ordered_manifest_ids),
            "max_manifest_concentration": self.max_manifest_concentration,
        }


# --- Result object ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AggregationResult:
    """Serializable immutable aggregate artifact (D01 section 15.1 / 16)."""

    aggregation_contract_version: str
    uncertainty_method_version: str
    rng_algorithm_version: str
    status: AggregateStatus
    visibility_mode: str
    as_of: datetime
    identity: AggregateIdentity
    measurement_signature_state: MeasurementSignatureState
    measurement_signature: MeasurementSignature | None
    input_manifest: tuple[dict[str, Any], ...]
    input_fingerprint: str
    coverage: CoverageReport
    manifest: ManifestDiagnostics
    statistics: EconomicStatistics | None
    tail_risk: TailEvidence | None
    uncertainty: BootstrapInterval | None
    clusters: tuple[OverlapCluster, ...]
    leave_one_cluster_out: tuple[LocoResult, ...]
    calculability: Calculability | None
    evidence_sufficient: bool
    sufficiency_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    unobservable_coverage_limitations: tuple[str, ...]
    integrity_statement: str
    regime_gate: str
    regime_sufficiency: str
    integrity_conflicts: tuple[str, ...] = field(default=())

    @property
    def population_key(self) -> PopulationKey:
        return self.identity.population_key

    @property
    def horizon(self) -> ForwardHorizon:
        return self.identity.horizon

    def to_dict(self) -> dict[str, Any]:
        """Canonical-JSON-safe projection for Gate C style evidence retention."""

        return {
            "aggregation_contract_version": self.aggregation_contract_version,
            "uncertainty_method_version": self.uncertainty_method_version,
            "rng_algorithm_version": self.rng_algorithm_version,
            "status": self.status.value,
            "visibility_mode": self.visibility_mode,
            "as_of": _iso(self.as_of),
            "population_key": self.population_key.canonical_payload(),
            "horizon": self.horizon.value,
            "measurement_signature_state": self.measurement_signature_state.value,
            "measurement_signature": (
                None if self.measurement_signature is None else self.measurement_signature.canonical_payload()
            ),
            "input_manifest": [dict(entry) for entry in self.input_manifest],
            "input_fingerprint": self.input_fingerprint,
            "coverage": self.coverage.to_dict(),
            "manifest": self.manifest.to_dict(),
            "statistics": None if self.statistics is None else self.statistics.to_dict(),
            "tail_risk": None if self.tail_risk is None else self.tail_risk.to_dict(),
            "uncertainty": (
                None
                if self.uncertainty is None
                else {
                    "n_clusters": self.uncertainty.n_clusters,
                    "n_resamples": self.uncertainty.n_resamples,
                    "confidence_level": self.uncertainty.confidence_level,
                    "lower_index": self.uncertainty.lower_index,
                    "upper_index": self.uncertainty.upper_index,
                    "lower": self.uncertainty.lower,
                    "upper": self.uncertainty.upper,
                    "unavailable_reason": (
                        None
                        if self.uncertainty.unavailable_reason is None
                        else self.uncertainty.unavailable_reason.value
                    ),
                    "is_degenerate": self.uncertainty.is_degenerate,
                    "excludes_zero": self.uncertainty.excludes_zero,
                    "side": None if self.uncertainty.side is None else self.uncertainty.side.value,
                    "seed_hex": self.uncertainty.seed_hex,
                    "rng_algorithm_version": self.uncertainty.rng_algorithm_version,
                }
            ),
            "overlap_clusters": [
                {
                    "cluster_id": cluster.cluster_id,
                    "opportunity_ids": list(cluster.opportunity_ids),
                    "interval_start": _iso(cluster.interval_start),
                    "interval_end": _iso(cluster.interval_end),
                }
                for cluster in self.clusters
            ],
            "leave_one_cluster_out": [
                {
                    "removed_cluster_id": result.removed_cluster_id,
                    "removed_opportunity_ids": list(result.removed_opportunity_ids),
                    "remaining_cluster_count": result.remaining_cluster_count,
                    "lower": result.interval.lower,
                    "upper": result.interval.upper,
                    "unavailable_reason": (
                        None
                        if result.interval.unavailable_reason is None
                        else result.interval.unavailable_reason.value
                    ),
                    "side": None if result.interval.side is None else result.interval.side.value,
                    "preserves_full_side": result.preserves_full_side,
                }
                for result in self.leave_one_cluster_out
            ],
            "calculability": None if self.calculability is None else self.calculability.value,
            "evidence_sufficient": self.evidence_sufficient,
            "sufficiency_reasons": list(self.sufficiency_reasons),
            "limitations": list(self.limitations),
            "unobservable_coverage_limitations": list(self.unobservable_coverage_limitations),
            "integrity_statement": self.integrity_statement,
            "regime_gate": self.regime_gate,
            "regime_sufficiency": self.regime_sufficiency,
            "integrity_conflicts": list(self.integrity_conflicts),
        }


# --- Aggregation entry point ------------------------------------------------------------------


def _validate_and_order(
    *,
    population_key: PopulationKey,
    horizon: ForwardHorizon,
    facts: Iterable[CanonicalScopeFacts],
) -> tuple[CanonicalScopeFacts, ...]:
    ordered = sorted(
        facts, key=lambda item: (item.opportunity_id, item.evidence_id, item.horizon.value)
    )
    seen: set[tuple[PopulationKey, ForwardHorizon, str]] = set()
    for item in ordered:
        if item.population_key != population_key or item.horizon is not horizon:
            raise ForeignScopeFactError(
                f"fact {item.opportunity_id!r} does not belong to the requested aggregate identity"
            )
        identity = sample_identity(item)
        if identity in seen:
            raise DuplicateSampleIdentityError(
                "duplicate sample identity (population_key, horizon, opportunity_id): "
                f"{item.opportunity_id!r}"
            )
        seen.add(identity)
    return ordered


def aggregate(
    *,
    population_key: PopulationKey,
    horizon: ForwardHorizon,
    as_of: datetime,
    facts: Iterable[CanonicalScopeFacts],
    ordered_input_manifest: Sequence[Mapping[str, Any]] | None = None,
) -> AggregationResult:
    """Compute one deterministic aggregate for ``(population_key, horizon)``.

    The function is a pure function of ``(population_key, horizon, as_of, facts)``:
    reordering ``facts`` cannot change any output value, and a repeated call on the
    same facts produces a byte-identical fingerprint.

    The result never contains KEEP / DOWNWEIGHT / KILL, any threshold, or any
    strategy / risk / execution / Gate C action.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise AggregationError("as_of must be timezone-aware")

    ordered = _validate_and_order(population_key=population_key, horizon=horizon, facts=facts)

    manifest = (
        build_ordered_input_manifest(ordered, as_of=as_of)
        if ordered_input_manifest is None
        else tuple(dict(entry) for entry in ordered_input_manifest)
    )
    fingerprint = compute_input_fingerprint(
        as_of=as_of,
        population_key=population_key,
        horizon=horizon,
        ordered_input_manifest=manifest,
    )

    maturity = tuple(classify_maturity(item, as_of=as_of) for item in ordered)
    conflicts = tuple(
        conflict
        for item, item_maturity in zip(ordered, maturity, strict=True)
        for conflict in integrity_conflicts(item, item_maturity)
    )

    complete = [
        item
        for item, item_maturity in zip(ordered, maturity, strict=True)
        if item_maturity is MaturityClass.COMPLETE
    ]
    insufficient = sum(1 for value in maturity if value is MaturityClass.INSUFFICIENT_DATA)
    invalid = sum(1 for value in maturity if value is MaturityClass.INVALID)
    missing = sum(1 for value in maturity if value is MaturityClass.MISSING_OUTCOME)
    not_yet_due = sum(1 for value in maturity if value is MaturityClass.NOT_YET_DUE)
    mature_denominator = len(complete) + insufficient + invalid + missing
    if len(ordered) != mature_denominator + not_yet_due:
        raise AggregationError("coverage invariant violated: no mature status may disappear")

    # A COMPLETE scope whose required economic return is contradictory is not a
    # usable economic sample; it stays visible in the raw COMPLETE count and in
    # ``integrity_conflict_count`` and forces the whole aggregate to fail closed.
    usable_complete = [
        item
        for item in complete
        if not integrity_conflicts(item, MaturityClass.COMPLETE)
    ]
    signatures = [item.measurement_signature for item in usable_complete]
    if any(signature is None for signature in signatures):
        raise AggregationError("a usable COMPLETE sample must carry a Measurement Signature")
    # Structural authority (SE02D-I01-R1): distinctness is decided on the actual
    # six frozen fields of ``MeasurementSignature``, never on a derived string or
    # digest. ``canonical_key()`` is used here only to give the distinct set a
    # deterministic order for reporting.
    distinct_signatures = sorted(
        {signature for signature in signatures if signature is not None},
        key=MeasurementSignature.canonical_key,
    )

    coverage = CoverageReport(
        eligible_opportunities=len(ordered),
        not_yet_due=not_yet_due,
        mature_denominator=mature_denominator,
        complete=len(complete),
        insufficient_data=insufficient,
        invalid=invalid,
        missing_outcome=missing,
        coverage_rate=(None if mature_denominator == 0 else len(complete) / mature_denominator),
        settlement_rate=(
            None
            if mature_denominator == 0
            else (len(complete) + insufficient + invalid) / mature_denominator
        ),
        folded_evidence_revisions=sum(item.folded_evidence_revision_count for item in ordered),
        folded_outcome_revisions=sum(item.folded_outcome_revision_count for item in ordered),
        outcomes_excluded_with_folded_evidence=sum(
            item.outcomes_excluded_with_folded_evidence for item in ordered
        ),
        integrity_conflict_count=len(
            {
                item.sample_id
                for item in complete
                if integrity_conflicts(item, MaturityClass.COMPLETE)
            }
        ),
        reference_status_counts=_histogram(
            (item.reference_data_status.value for item in ordered),
            universe=REFERENCE_STATUS_KEYS,
        ),
        lifecycle_counts=_histogram(
            ("NULL" if item.lifecycle is None else item.lifecycle.value for item in ordered),
            universe=LIFECYCLE_KEYS,
        ),
        status_reason_counts=_histogram(
            _reason_token(item.outcome_reason, item_maturity)
            for item, item_maturity in zip(ordered, maturity, strict=True)
            if item_maturity is not MaturityClass.NOT_YET_DUE
        ),
        measurement_signature_counts=_histogram(
            signature.canonical_key()
            for item in complete
            if (signature := item.measurement_signature) is not None
        ),
    )

    manifest_counts = _histogram(item.source_manifest_id for item in ordered)
    manifest_diagnostics = ManifestDiagnostics(
        manifest_counts=manifest_counts,
        manifest_count=len(manifest_counts),
        ordered_manifest_ids=tuple(sorted(manifest_counts)),
        max_manifest_concentration=(
            None
            if not ordered
            else max(manifest_counts.values()) / len(ordered)
        ),
    )

    applicable = population_key.market_type is MarketType.SPOT

    # --- fail-closed headline status (task section 28 precedence) ---
    if coverage.integrity_conflict_count > 0:
        status = AggregateStatus.INTEGRITY_CONFLICT
    elif len(distinct_signatures) > 1:
        status = AggregateStatus.INCOMPATIBLE_MEASUREMENT_SIGNATURES
    elif not applicable:
        status = AggregateStatus.NOT_APPLICABLE
    elif not usable_complete:
        status = AggregateStatus.NOT_CALCULABLE
    else:
        status = AggregateStatus.VALID

    if not usable_complete:
        signature_state = MeasurementSignatureState.NO_MEASUREMENT
        exact_signature: MeasurementSignature | None = None
    elif len(distinct_signatures) == 1:
        signature_state = MeasurementSignatureState.EXACT
        exact_signature = distinct_signatures[0]
    else:
        signature_state = MeasurementSignatureState.MIXED
        exact_signature = None

    reasons: set[SufficiencyReason] = set()
    statistics: EconomicStatistics | None = None
    tail: TailEvidence | None = None
    uncertainty: BootstrapInterval | None = None
    clusters: tuple[OverlapCluster, ...] = ()
    loco: tuple[LocoResult, ...] = ()
    calculability: Calculability | None = None

    if status is AggregateStatus.VALID:
        # Deterministic economic sample order: sample_id lexical ascending.
        samples = sorted(usable_complete, key=lambda item: item.sample_id)
        returns = tuple(
            item.cost_adjusted_forward_return for item in samples
        )
        if any(value is None for value in returns):
            raise AggregationError("VALID aggregation requires a finite economic return per sample")
        numeric_returns = tuple(float(value) for value in returns)  # type: ignore[arg-type]

        statistics = economic_statistics(numeric_returns)
        k = worst_decile_k(len(numeric_returns))
        tail = TailEvidence(
            k=k,
            worst_observation=statistics.worst_observation,
            worst_decile_mean=statistics.worst_decile_mean,
        )
        clusters = cluster_samples(samples)
        seed = bootstrap_seed(
            population_key=population_key,
            horizon=horizon,
            as_of=as_of,
            input_fingerprint=fingerprint,
        )
        uncertainty = percentile_interval(clusters=clusters, seed=seed)
        loco = leave_one_cluster_out(clusters=clusters, full_interval=uncertainty, seed=seed)
        calculability = (
            Calculability.CALCULABLE_WITH_UNCERTAINTY
            if len(clusters) >= MIN_CLUSTERS_FOR_INTERVAL
            else Calculability.CALCULABLE_DESCRIPTIVE_ONLY
        )

        if coverage.integrity_conflict_count != 0:
            reasons.add(SufficiencyReason.INTEGRITY_CONFLICT_PRESENT)
        if coverage.coverage_rate != REQUIRED_COVERAGE_RATE:
            reasons.add(SufficiencyReason.COVERAGE_BELOW_ONE)
        if len(clusters) < MIN_CLUSTERS_FOR_SUFFICIENCY:
            reasons.add(SufficiencyReason.TOO_FEW_CLUSTERS)
        if uncertainty.lower is None or uncertainty.upper is None:
            reasons.add(SufficiencyReason.NO_BOOTSTRAP_INTERVAL)
            if uncertainty.unavailable_reason is UncertaintyUnavailableReason.DEGENERATE_SAMPLE:
                reasons.add(SufficiencyReason.DEGENERATE_INTERVAL)
        else:
            if uncertainty.is_degenerate:
                reasons.add(SufficiencyReason.DEGENERATE_INTERVAL)
            if uncertainty.side is None:
                reasons.add(SufficiencyReason.INTERVAL_CONTAINS_ZERO)
        if not all(result.preserves_full_side for result in loco):
            reasons.add(SufficiencyReason.LEAVE_ONE_CLUSTER_OUT_UNSTABLE)
    else:
        if coverage.integrity_conflict_count != 0:
            reasons.add(SufficiencyReason.INTEGRITY_CONFLICT_PRESENT)
        if status is AggregateStatus.INCOMPATIBLE_MEASUREMENT_SIGNATURES:
            reasons.add(SufficiencyReason.INCOMPATIBLE_MEASUREMENT_SIGNATURES)
        if not applicable:
            reasons.add(SufficiencyReason.MARKET_TYPE_NOT_APPLICABLE)
        if not complete:
            reasons.add(SufficiencyReason.NO_ECONOMIC_SAMPLES)

    return AggregationResult(
        aggregation_contract_version=AGGREGATION_CONTRACT_VERSION,
        uncertainty_method_version=UNCERTAINTY_METHOD_VERSION,
        rng_algorithm_version=RNG_ALGORITHM_VERSION,
        status=status,
        visibility_mode=VISIBILITY_MODE,
        as_of=as_of,
        identity=AggregateIdentity(population_key=population_key, horizon=horizon),
        measurement_signature_state=signature_state,
        measurement_signature=exact_signature,
        input_manifest=manifest,
        input_fingerprint=fingerprint,
        coverage=coverage,
        manifest=manifest_diagnostics,
        statistics=statistics,
        tail_risk=tail,
        uncertainty=uncertainty,
        clusters=clusters,
        leave_one_cluster_out=loco,
        calculability=calculability,
        evidence_sufficient=not reasons,
        sufficiency_reasons=tuple(sorted(reason.value for reason in reasons)),
        limitations=DEPENDENCE_LIMITATIONS,
        unobservable_coverage_limitations=UNOBSERVABLE_COVERAGE_LIMITATIONS,
        integrity_statement=INTEGRITY_STATEMENT,
        regime_gate=REGIME_GATE,
        regime_sufficiency=REGIME_SUFFICIENCY,
        integrity_conflicts=conflicts,
    )


__all__ = [
    "AGGREGATION_CONTRACT_VERSION",
    "BOOTSTRAP_LOWER_INDEX",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_UPPER_INDEX",
    "CONFIDENCE_LEVEL",
    "DEPENDENCE_LIMITATIONS",
    "INTEGRITY_STATEMENT",
    "KNOWN_OUTCOME_REASONS",
    "MIN_CLUSTERS_FOR_INTERVAL",
    "MIN_CLUSTERS_FOR_SUFFICIENCY",
    "NO_MEASUREMENT",
    "REGIME_GATE",
    "REGIME_SUFFICIENCY",
    "REQUIRED_COVERAGE_RATE",
    "RNG_ALGORITHM_VERSION",
    "UNCERTAINTY_METHOD_VERSION",
    "UNOBSERVABLE_COVERAGE_LIMITATIONS",
    "VISIBILITY_MODE",
    "WORST_DECILE_DENOMINATOR",
    "AggregateIdentity",
    "AggregateStatus",
    "AggregationError",
    "AggregationResult",
    "BootstrapInterval",
    "Calculability",
    "CanonicalScopeFacts",
    "CoverageReport",
    "DuplicateSampleIdentityError",
    "EconomicStatistics",
    "ForeignScopeFactError",
    "IntervalSide",
    "LocoResult",
    "ManifestDiagnostics",
    "MaturityClass",
    "MeasurementSignature",
    "MeasurementSignatureState",
    "OverlapCluster",
    "PopulationKey",
    "SufficiencyReason",
    "TailEvidence",
    "UncertaintyUnavailableReason",
    "aggregate",
    "bootstrap_seed",
    "build_ordered_input_manifest",
    "classify_maturity",
    "cluster_samples",
    "compute_input_fingerprint",
    "draw_cluster_index",
    "economic_statistics",
    "integrity_conflicts",
    "leave_one_cluster_out",
    "percentile_interval",
    "replicate_means",
    "sample_identity",
    "uint256_be_draw",
    "worst_decile_k",
]
