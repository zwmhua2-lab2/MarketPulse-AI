"""Deterministic Advisory identity derivation (D2 §12.1) and input binding (D2 §20).

Every identifier in this module is a pure function of explicit, immutable input facts.
There is no process-local state, no clock read, no provider response and no
``repr()``/process hash anywhere on these paths, so the same facts always produce the
same identifier and a *different* identifier can only come from different facts.

Two contract rules shape the code:

* **No ambiguous delimiter joining.** Every digest goes through the accepted
  ``marketpulse.edge.hashing.canonical_digest``, which hashes a versioned canonical JSON
  array ``[domain, *parts]``. The domain tag is an *element*, not a string prefix, so a
  caller cannot forge a cross-domain collision. No ``"|".join(...)`` appears here.
* **RFC 3339 ``Z`` with fixed 6 fractional digits.** D2 §17.1 freezes that serialization
  for the advisory deadline authority. The accepted canonicalizer would render a
  ``datetime`` as ``...+00:00``, so advisory timestamps are converted to the frozen string
  *before* hashing rather than passed as ``datetime`` objects. That keeps the DB
  ``TIMESTAMPTZ`` (microsecond) value and the hashed value provably the same fact.

Semantic equality is never decided by comparing digests — callers compare the structured
facts they were built from. A digest is an identity, not a comparison authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from marketpulse.advisory.vocabulary import (
    ADVISORY_ATTEMPT_ID_DOMAIN,
    ADVISORY_BINDING_VERSION,
    ADVISORY_EXPERIMENT_DEFINITION_DIGEST_DOMAIN,
    ADVISORY_EXPERIMENT_DEFINITION_VERSION,
    ADVISORY_EXPERIMENT_ID_DOMAIN,
    ADVISORY_FINAL_DECISION_ID_DOMAIN,
    ADVISORY_INVOCATION_ID_DOMAIN,
    ADVISORY_PAIR_ID_DOMAIN,
    ADVISORY_SNAPSHOT_CONTRACT_VERSION,
    ADVISORY_SNAPSHOT_ID_DOMAIN,
    ADVISORY_SNAPSHOT_PAYLOAD_HASH_DOMAIN,
    BASELINE_ARM_LABEL,
    TREATMENT_ARM_LABEL,
)
from marketpulse.edge.hashing import canonical_digest

#: Microseconds per second, used to express the frozen 6-digit fractional-second form.
_MICROSECONDS_PER_SECOND = 1_000_000


def canonical_utc_timestamp(value: datetime) -> str:
    """Render one instant in the frozen RFC 3339 form: ``...THH:MM:SS.ffffffZ``.

    A naive ``datetime`` is refused rather than assumed to be UTC: guessing the offset
    would silently change a deadline, and a deadline is an immutable identity fact
    (D2 §17.1). The instant is normalized to UTC first, so a value stored under any DB
    session timezone renders identically.
    """

    if value.tzinfo is None:
        raise AdvisoryIdentityError("advisory timestamps must be timezone-aware")
    utc = value.astimezone(UTC)
    micros = utc.microsecond
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}T"
        f"{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}."
        f"{micros:06d}Z"
    )


class AdvisoryIdentityError(ValueError):
    """Raised when an identity input is not the exact immutable fact the contract wants."""


def _non_empty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdvisoryIdentityError(f"{field} must be a non-empty string")
    return value


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AdvisoryIdentityError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: int, field: str) -> int:
    """A monotonic durable counter: negative is a caller bug, zero is legal.

    ``symbol_states.state_version`` is the accepted durable G2 authority for
    ``state_version`` and a symbol with no durable row yet is at version 0 (see the Host's
    ``F-01`` accessor). Rejecting 0 would therefore refuse a legal binding; accepting a
    negative version would put a nonsensical fact into an immutable identity.
    """

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdvisoryIdentityError(f"{field} must be a non-negative integer")
    return value


# ---------------------------------------------------------------------------------------
# Snapshot identity (D2 §12.1 steps 1-2)
# ---------------------------------------------------------------------------------------


def snapshot_payload_hash(payload: Mapping[str, Any]) -> str:
    """``H(snapshot_contract_version, canonical_snapshot_payload)``."""

    return canonical_digest(
        ADVISORY_SNAPSHOT_PAYLOAD_HASH_DOMAIN,
        ADVISORY_SNAPSHOT_CONTRACT_VERSION,
        dict(payload),
    )


def advisory_snapshot_id(
    *, opportunity_id: str, evidence_id: str, payload_hash: str
) -> str:
    """``H("advisory-snapshot-v1", opportunity_id, evidence_id, snapshot_payload_hash)``.

    The Evidence *identity* participates, not the canonical head: an already-created
    snapshot can never drift onto a later Evidence revision (D2 §9).
    """

    return canonical_digest(
        ADVISORY_SNAPSHOT_ID_DOMAIN,
        _non_empty(opportunity_id, "opportunity_id"),
        _non_empty(evidence_id, "evidence_id"),
        _non_empty(payload_hash, "snapshot_payload_hash"),
    )


# ---------------------------------------------------------------------------------------
# Input binding digest (D2 §12.1 step 3)
# ---------------------------------------------------------------------------------------


def input_binding_digest(
    *,
    opportunity_id: str,
    evidence_id: str,
    evidence_revision: int,
    evidence_hash: str,
    feature_snapshot_hash: str,
    snapshot_id: str,
    snapshot_payload_hash: str,
    state_version: int,
    config_version: str,
    family_id: str,
    family_version: str,
    instrument_id: str,
    market_type: str,
    advisory_config_epoch_id: str,
    decision_requested_at: datetime,
    deadline_duration_ms: int,
    deadline_policy_version: str,
    decision_deadline_at: datetime,
) -> str:
    """The exact immutable binding of one Advisory invocation to one Evidence revision.

    ``feature_snapshot_hash`` is included deliberately: D2 §9.1 froze the binding as
    ``opportunity_id + evidence_id + evidence_revision + evidence_hash +
    feature_snapshot_hash``, because the feature snapshot hash is part of the Evidence
    identity. Both timestamps are the *persisted* PostgreSQL admission clock values,
    never re-derived here.
    """

    return canonical_digest(
        ADVISORY_BINDING_VERSION,
        _non_empty(opportunity_id, "opportunity_id"),
        _non_empty(evidence_id, "evidence_id"),
        _positive_int(evidence_revision, "evidence_revision"),
        _non_empty(evidence_hash, "evidence_hash"),
        _non_empty(feature_snapshot_hash, "feature_snapshot_hash"),
        _non_empty(snapshot_id, "snapshot_id"),
        _non_empty(snapshot_payload_hash, "snapshot_payload_hash"),
        _non_negative_int(state_version, "state_version"),
        _non_empty(config_version, "config_version"),
        _non_empty(family_id, "family_id"),
        _non_empty(family_version, "family_version"),
        _non_empty(instrument_id, "instrument_id"),
        _non_empty(market_type, "market_type"),
        _non_empty(advisory_config_epoch_id, "advisory_config_epoch_id"),
        canonical_utc_timestamp(decision_requested_at),
        _positive_int(deadline_duration_ms, "deadline_duration_ms"),
        _non_empty(deadline_policy_version, "deadline_policy_version"),
        canonical_utc_timestamp(decision_deadline_at),
    )


# ---------------------------------------------------------------------------------------
# Experiment / pair / arm identity (D2 §12.1 steps 4-7)
# ---------------------------------------------------------------------------------------


def experiment_definition_digest(definition: Mapping[str, Any]) -> str:
    """Content digest of the complete canonical experiment definition (D2 §13.1)."""

    if not definition:
        raise AdvisoryIdentityError("experiment definition must not be empty")
    return canonical_digest(ADVISORY_EXPERIMENT_DEFINITION_DIGEST_DOMAIN, dict(definition))


def experiment_id(definition: Mapping[str, Any]) -> str:
    """``H(experiment_definition_version, canonical_experiment_definition)``.

    A changed definition therefore produces a *new* experiment lineage with no identity
    collision against the old one (PRE-01A AC-23), which is what makes
    "restart must not silently re-configure an old invocation" checkable.
    """

    if not definition:
        raise AdvisoryIdentityError("experiment definition must not be empty")
    return canonical_digest(
        ADVISORY_EXPERIMENT_ID_DOMAIN, ADVISORY_EXPERIMENT_DEFINITION_VERSION, dict(definition)
    )


def pair_id(*, experiment_id: str, input_binding_digest: str) -> str:
    """``H("pre01a-pair-v1", experiment_id, input_binding_digest)``."""

    return canonical_digest(
        ADVISORY_PAIR_ID_DOMAIN,
        _non_empty(experiment_id, "experiment_id"),
        _non_empty(input_binding_digest, "input_binding_digest"),
    )


def baseline_arm_id(*, pair_id: str) -> str:
    """``H(pair_id, "WITHOUT_AI_BASELINE")``."""

    return canonical_digest(
        ADVISORY_PAIR_ID_DOMAIN,
        _non_empty(pair_id, "pair_id"),
        BASELINE_ARM_LABEL,
    )


def treatment_arm_id(*, pair_id: str) -> str:
    """``H(pair_id, "REAL_AI_TREATMENT")``."""

    return canonical_digest(
        ADVISORY_PAIR_ID_DOMAIN,
        _non_empty(pair_id, "pair_id"),
        TREATMENT_ARM_LABEL,
    )


# ---------------------------------------------------------------------------------------
# Invocation / attempt / final identity (D2 §12.1 steps 8-10)
# ---------------------------------------------------------------------------------------


def decision_invocation_id(
    *,
    experiment_id: str,
    pair_id: str,
    treatment_arm_id: str,
    input_binding_digest: str,
    prompt_version: str,
    schema_version: str,
    treatment_version: str,
    configured_provider_id: str,
    configured_model_id: str,
) -> str:
    """The one collision-free identity of a logical Advisory invocation.

    It is deliberately *not* derived from any attempt, provider response or timestamp: a
    retry adds an Attempt and never a new invocation, and the provider is never a local
    identity authority (D2 §12.2).
    """

    return canonical_digest(
        ADVISORY_INVOCATION_ID_DOMAIN,
        _non_empty(experiment_id, "experiment_id"),
        _non_empty(pair_id, "pair_id"),
        _non_empty(treatment_arm_id, "treatment_arm_id"),
        _non_empty(input_binding_digest, "input_binding_digest"),
        _non_empty(prompt_version, "prompt_version"),
        _non_empty(schema_version, "schema_version"),
        _non_empty(treatment_version, "treatment_version"),
        _non_empty(configured_provider_id, "configured_provider_id"),
        _non_empty(configured_model_id, "configured_model_id"),
    )


def attempt_id(*, decision_invocation_id: str, attempt_number: int) -> str:
    """``H("advisory-attempt-v1", decision_invocation_id, attempt_number)``."""

    return canonical_digest(
        ADVISORY_ATTEMPT_ID_DOMAIN,
        _non_empty(decision_invocation_id, "decision_invocation_id"),
        _positive_int(attempt_number, "attempt_number"),
    )


def final_decision_id(*, decision_invocation_id: str) -> str:
    """``H("advisory-final-v1", decision_invocation_id)``.

    D2 §12.1 step 10: the logical final-result identity *is* ``decision_invocation_id``;
    this digest only names the optional normalized `AIDecision` artifact. Its Attempt
    origin is proved by the composite foreign key, never inferred from this digest.
    """

    return canonical_digest(
        ADVISORY_FINAL_DECISION_ID_DOMAIN,
        _non_empty(decision_invocation_id, "decision_invocation_id"),
    )


__all__ = [
    "AdvisoryIdentityError",
    "advisory_snapshot_id",
    "attempt_id",
    "baseline_arm_id",
    "canonical_utc_timestamp",
    "decision_invocation_id",
    "experiment_definition_digest",
    "experiment_id",
    "final_decision_id",
    "input_binding_digest",
    "pair_id",
    "snapshot_payload_hash",
    "treatment_arm_id",
]
