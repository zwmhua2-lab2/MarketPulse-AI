"""Deterministic identity derivation for the SE-02 Edge contracts.

Every identifier in this module is a pure function of explicit input facts. In
particular:

* ``opportunity_id`` never depends on an evidence revision, an evidence hash or a
  calculator version, so a legitimate evidence correction cannot re-identify the
  logical opportunity;
* ``evidence_id`` depends on the revision and the evidence contract version, so a
  new revision always yields a new evidence identity for the same opportunity.
"""

from __future__ import annotations

from datetime import datetime

from marketpulse.edge.hashing import (
    ATTRIBUTION_EVENT_ID_DOMAIN,
    BBO_OBSERVATION_ID_DOMAIN,
    EVIDENCE_ID_DOMAIN,
    OPPORTUNITY_ID_DOMAIN,
    OUTCOME_ID_DOMAIN,
    canonical_digest,
)


def opportunity_id(
    *,
    family_id: str,
    family_version: str,
    instrument_id: str,
    candidate_id: str,
) -> str:
    """``SHA256("se02-opportunity-id-v1", family_id, family_version, instrument_id, candidate_id)``."""

    return canonical_digest(
        OPPORTUNITY_ID_DOMAIN,
        family_id,
        family_version,
        instrument_id,
        candidate_id,
    )


def evidence_id(
    *,
    opportunity_id: str,
    evidence_revision: int,
    evidence_contract_version: str,
) -> str:
    """``SHA256("se02-evidence-id-v1", opportunity_id, evidence_revision, evidence_contract_version)``."""

    return canonical_digest(
        EVIDENCE_ID_DOMAIN,
        opportunity_id,
        evidence_revision,
        evidence_contract_version,
    )


def bbo_observation_id(
    *,
    instrument_id: str,
    market_type: str,
    source: str,
    source_sequence: int | None,
    source_event_time: datetime,
    available_at: datetime,
    received_at: datetime,
    bid: float,
    ask: float,
) -> str:
    """Content-addressed identity of one normalized L1 BBO observation.

    Every fact that determines the causal market observation and its future
    eligibility is part of the identity: instrument, market, source and source
    sequence, the event/availability/receive timestamps and the quote itself.
    Identical observations collapse onto the same identity, which makes
    re-ingesting the same replay frame idempotent instead of duplicating a
    horizon reference point. ``data_quality`` and ``tradable`` are deliberately
    outside the identity; the repository compares them as immutable eligibility
    facts when an identity is re-used, so a conflicting re-use fails closed
    instead of being silently treated as a duplicate.
    """

    return canonical_digest(
        BBO_OBSERVATION_ID_DOMAIN,
        instrument_id,
        market_type,
        source,
        source_sequence,
        source_event_time,
        available_at,
        received_at,
        bid,
        ask,
    )


def forward_outcome_id(
    *,
    opportunity_id: str,
    evidence_id: str,
    horizon: str,
    outcome_contract_version: str,
    outcome_revision: int,
) -> str:
    """Identity of one immutable forward-outcome revision."""

    return canonical_digest(
        OUTCOME_ID_DOMAIN,
        opportunity_id,
        evidence_id,
        horizon,
        outcome_contract_version,
        outcome_revision,
    )


def attribution_event_id(
    *,
    contract_version: str,
    subject_type: str,
    subject_id: str | None,
    event_type: str,
    opportunity_id: str | None,
    evidence_id: str | None,
    payload_hash: str,
    occurred_at: datetime,
) -> str:
    """Content-addressed identity of one append-only attribution event."""

    return canonical_digest(
        ATTRIBUTION_EVENT_ID_DOMAIN,
        contract_version,
        subject_type,
        subject_id,
        event_type,
        opportunity_id,
        evidence_id,
        payload_hash,
        occurred_at,
    )
