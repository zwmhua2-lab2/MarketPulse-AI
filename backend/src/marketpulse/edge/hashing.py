"""Canonical, domain-separated hashing infrastructure for the SE-02 Edge layer.

SE-02 does not introduce a second canonical serializer: every hash in this module
is computed over ``marketpulse.g5.canonical.canonicalize_value``, the accepted G5
canonicalization contract. On top of that accepted contract this module adds only:

* a lossless byte encoding of the canonical form (``canonical_bytes``);
* domain separation (``canonical_digest``) so two different contract concepts can
  never collide even when their payloads are byte-identical;
* an explicit rejection of non-finite numeric values, which the G5 serializer
  alone would otherwise accept.

This module performs no business calculation; it only proves deterministic
canonical hashing.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from marketpulse.g5.canonical import CanonicalizationError, canonicalize_value

# Hash / identity domain tags. They are part of the frozen id contract: changing a
# tag changes every derived identifier, so they are never renamed in place.
OPPORTUNITY_ID_DOMAIN = "se02-opportunity-id-v1"
EVIDENCE_ID_DOMAIN = "se02-evidence-id-v1"
BBO_OBSERVATION_ID_DOMAIN = "se02-bbo-observation-id-v1"
OUTCOME_ID_DOMAIN = "se02-outcome-id-v1"
ATTRIBUTION_EVENT_ID_DOMAIN = "se02-attribution-event-id-v1"

FEATURE_SNAPSHOT_HASH_DOMAIN = "se02-feature-snapshot-hash-v1"
EVIDENCE_HASH_DOMAIN = "se02-evidence-hash-v1"
CALCULATION_DIGEST_DOMAIN = "se02-outcome-calculation-digest-v1"
OUTCOME_RECORD_HASH_DOMAIN = "se02-outcome-record-hash-v1"
ATTRIBUTION_PAYLOAD_HASH_DOMAIN = "se02-attribution-payload-hash-v1"


class CanonicalHashError(ValueError):
    """Raised when a value cannot be hashed losslessly and unambiguously."""


def _reject_non_finite(value: Any) -> None:
    """Fail closed on NaN / Infinity so hashes never depend on non-canonical numbers."""

    if isinstance(value, bool | str | bytes | int) or value is None:
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalHashError("non-finite float values are not canonicalizable")
        return
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalHashError("non-finite decimal values are not canonicalizable")
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_non_finite(item)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _reject_non_finite(item)


def canonical_bytes(value: Any) -> bytes:
    """Encode any supported value into its unambiguous canonical byte string."""

    _reject_non_finite(value)
    try:
        normalized = canonicalize_value(value)
    except CanonicalizationError as error:
        raise CanonicalHashError(str(error)) from error
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(domain: str, *parts: object) -> str:
    """SHA-256 over ``[domain, *parts]`` in canonical form.

    The domain tag is hashed as the first element rather than concatenated as a
    prefix, so a caller cannot construct a cross-domain collision by choosing a
    payload that starts with another domain's tag.
    """

    if not isinstance(domain, str) or not domain:
        raise CanonicalHashError("hash domain must be a non-empty string")
    return hashlib.sha256(canonical_bytes([domain, *parts])).hexdigest()


def feature_snapshot_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic hash of a normalized feature snapshot payload."""

    return canonical_digest(FEATURE_SNAPSHOT_HASH_DOMAIN, dict(payload))


def evidence_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic hash of the immutable evidence revision content."""

    return canonical_digest(EVIDENCE_HASH_DOMAIN, dict(payload))


def calculation_digest(payload: Mapping[str, Any]) -> str:
    """Deterministic digest of forward-outcome calculation facts.

    SE-02A only defines the boundary; the actual forward return / MFE / MAE
    calculation belongs to SE-02C and runs outside this batch.
    """

    return canonical_digest(CALCULATION_DIGEST_DOMAIN, dict(payload))


def outcome_record_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic hash of a complete immutable forward-outcome record."""

    return canonical_digest(OUTCOME_RECORD_HASH_DOMAIN, dict(payload))


def attribution_payload_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic hash of an append-only attribution event payload."""

    return canonical_digest(ATTRIBUTION_PAYLOAD_HASH_DOMAIN, dict(payload))
