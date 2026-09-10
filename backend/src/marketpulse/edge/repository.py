"""Append-only persistence for the SE-02 Edge contracts.

Only insert operations are exposed. There is no update or delete API anywhere in this
module, so a business caller cannot silently rewrite an immutable evidence revision or
outcome revision. Immutability is additionally backstopped by database constraints
(unique ``opportunity_id + evidence_revision``, composite supersedes foreign keys and
the frozen-family / frozen-horizon check constraints) rather than by a trigger
framework.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.db.models import (
    EdgeAttributionEventRecord,
    EdgeBboObservationRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.models import (
    AttributionEvent,
    BboObservation,
    EvidenceRevision,
    ForwardOutcomeContract,
)

INSERTED = "INSERTED"
IDEMPOTENT = "IDEMPOTENT"


class EdgePersistenceError(RuntimeError):
    """Base class for fail-closed Edge persistence errors."""


class EdgeEvidenceConflict(EdgePersistenceError):
    """Same opportunity + same revision + different hash."""


class EdgeInvalidSupersedes(EdgePersistenceError):
    """A supersedes link that is not a valid immutable correction."""


class EdgeOutcomeConflict(EdgePersistenceError):
    """Same outcome revision + different record content."""


class EdgeInvalidOutcomeSupersedes(EdgePersistenceError):
    """An outcome supersedes link that is not a valid immutable correction."""


class EdgeEvidenceReferenceMissing(EdgePersistenceError):
    """An outcome references evidence that does not exist for that opportunity."""


async def append_evidence_revision(session: AsyncSession, record: EvidenceRevision) -> str:
    """Append one evidence revision. Returns ``INSERTED`` or ``IDEMPOTENT``.

    Raises ``EdgeEvidenceConflict`` for the frozen integrity-conflict case and
    ``EdgeInvalidSupersedes`` for an invalid correction link.
    """

    existing = await session.scalar(
        select(EdgeOpportunityEvidenceRecord).where(
            EdgeOpportunityEvidenceRecord.opportunity_id == record.opportunity_id,
            EdgeOpportunityEvidenceRecord.evidence_revision == record.evidence_revision,
        )
    )
    if existing is not None:
        if existing.evidence_hash == record.evidence_hash:
            return IDEMPOTENT
        raise EdgeEvidenceConflict(
            "same opportunity and revision with a different evidence hash "
            f"(opportunity_id={record.opportunity_id}, revision={record.evidence_revision})"
        )

    if record.evidence_revision > 1:
        predecessor = await session.scalar(
            select(EdgeOpportunityEvidenceRecord).where(
                EdgeOpportunityEvidenceRecord.evidence_id == record.supersedes_evidence_id
            )
        )
        if predecessor is None:
            raise EdgeInvalidSupersedes("superseded evidence revision does not exist")
        if predecessor.opportunity_id != record.opportunity_id:
            raise EdgeInvalidSupersedes("supersedes must stay inside one opportunity")
        if predecessor.evidence_revision != record.evidence_revision - 1:
            raise EdgeInvalidSupersedes(
                "supersedes must name the immediately preceding evidence revision"
            )

    session.add(
        EdgeOpportunityEvidenceRecord(
            evidence_id=record.evidence_id,
            opportunity_id=record.opportunity_id,
            candidate_id=record.candidate_id,
            family_id=record.family_id.value,
            family_version=record.family_version,
            instrument_id=record.instrument_id,
            market_type=record.market_type.value,
            evidence_revision=record.evidence_revision,
            evidence_contract_version=record.evidence_contract_version,
            evidence_hash=record.evidence_hash,
            feature_snapshot_hash=record.feature_snapshot_hash,
            feature_snapshot_hash_version=record.feature_snapshot_hash_version,
            supersedes_evidence_id=record.supersedes_evidence_id,
            detected_at=record.detected_at,
            evidence_at=record.evidence_at,
            expires_at=record.expires_at,
            source_type=record.source_type.value,
            source_identity=record.source_identity,
            source_manifest_id=record.source_manifest_id,
            reference_bid=record.reference_bid,
            reference_ask=record.reference_ask,
            reference_received_at=record.reference_received_at,
            reference_data_status=record.reference_data_status.value,
            reference_data_reason=record.reference_data_reason.value,
            evidence_payload=dict(record.evidence_payload),
            feature_snapshot_payload=dict(record.feature_snapshot_payload),
            created_at=record.created_at,
        )
    )
    await session.flush()
    return INSERTED


async def record_bbo_observation(session: AsyncSession, observation: BboObservation) -> str:
    """Append one normalized L1 BBO observation (content-addressed, append-only)."""

    existing = await session.scalar(
        select(EdgeBboObservationRecord).where(
            EdgeBboObservationRecord.observation_id == observation.observation_id
        )
    )
    if existing is not None:
        return IDEMPOTENT

    session.add(
        EdgeBboObservationRecord(
            observation_id=observation.observation_id,
            instrument_id=observation.instrument_id,
            market_type=observation.market_type.value,
            bid=observation.bid,
            ask=observation.ask,
            available_at=observation.available_at,
            source_event_time=observation.source_event_time,
            received_at=observation.received_at,
            data_quality=observation.data_quality.value,
            tradable=observation.tradable,
            source=observation.source,
            source_sequence=observation.source_sequence,
            created_at=observation.created_at,
        )
    )
    await session.flush()
    return INSERTED


async def append_forward_outcome(
    session: AsyncSession, record: ForwardOutcomeContract
) -> str:
    """Append one immutable forward-outcome revision. Returns ``INSERTED``/``IDEMPOTENT``."""

    evidence = await session.scalar(
        select(EdgeOpportunityEvidenceRecord).where(
            EdgeOpportunityEvidenceRecord.evidence_id == record.evidence_id,
            EdgeOpportunityEvidenceRecord.opportunity_id == record.opportunity_id,
        )
    )
    if evidence is None:
        raise EdgeEvidenceReferenceMissing(
            "forward outcome must reference evidence of the same opportunity"
        )

    existing = await session.scalar(
        select(EdgeForwardOutcomeRecord).where(
            EdgeForwardOutcomeRecord.opportunity_id == record.opportunity_id,
            EdgeForwardOutcomeRecord.evidence_id == record.evidence_id,
            EdgeForwardOutcomeRecord.horizon == record.horizon.value,
            EdgeForwardOutcomeRecord.outcome_revision == record.outcome_revision,
        )
    )
    if existing is not None:
        if existing.outcome_record_hash == record.outcome_record_hash:
            return IDEMPOTENT
        raise EdgeOutcomeConflict(
            "same outcome revision with different record content "
            f"(opportunity_id={record.opportunity_id}, revision={record.outcome_revision})"
        )

    if record.outcome_revision > 1:
        predecessor = await session.scalar(
            select(EdgeForwardOutcomeRecord).where(
                EdgeForwardOutcomeRecord.outcome_id == record.supersedes_outcome_id
            )
        )
        if predecessor is None:
            raise EdgeInvalidOutcomeSupersedes("superseded outcome revision does not exist")
        if predecessor.opportunity_id != record.opportunity_id:
            raise EdgeInvalidOutcomeSupersedes("supersedes must stay inside one opportunity")
        if predecessor.outcome_revision != record.outcome_revision - 1:
            raise EdgeInvalidOutcomeSupersedes(
                "supersedes must name the immediately preceding outcome revision"
            )

    session.add(
        EdgeForwardOutcomeRecord(
            outcome_id=record.outcome_id,
            opportunity_id=record.opportunity_id,
            evidence_id=record.evidence_id,
            horizon=record.horizon.value,
            outcome_revision=record.outcome_revision,
            supersedes_outcome_id=record.supersedes_outcome_id,
            outcome_contract_version=record.outcome_contract_version,
            calculation_status=record.calculation_status.value,
            opportunity_lifecycle_at_horizon=(
                None
                if record.opportunity_lifecycle_at_horizon is None
                else record.opportunity_lifecycle_at_horizon.value
            ),
            due_at=record.due_at,
            source_type=record.source_type.value,
            source_identity=record.source_identity,
            reference_bbo_observation_id=record.reference_bbo_observation_id,
            end_bbo_observation_id=record.end_bbo_observation_id,
            reference_price=record.reference_price,
            end_bid=record.end_bid,
            end_ask=record.end_ask,
            mfe=record.mfe,
            mae=record.mae,
            reference_return=record.reference_return,
            executable_long_return=record.executable_long_return,
            cost_adjusted_forward_return=record.cost_adjusted_forward_return,
            completeness_diagnostics=dict(record.completeness_diagnostics),
            cost_policy=record.cost_policy,
            cost_model_version=record.cost_model_version,
            calculator_version=record.calculator_version,
            calculation_digest=record.calculation_digest,
            calculation_digest_version=record.calculation_digest_version,
            outcome_record_hash=record.outcome_record_hash,
            outcome_record_hash_version=record.outcome_record_hash_version,
            created_at=record.created_at,
        )
    )
    await session.flush()
    return INSERTED


async def append_attribution_event(session: AsyncSession, event: AttributionEvent) -> str:
    """Append one attribution lineage event (content-addressed, append-only)."""

    existing = await session.scalar(
        select(EdgeAttributionEventRecord).where(
            EdgeAttributionEventRecord.attribution_event_id == event.attribution_event_id
        )
    )
    if existing is not None:
        return IDEMPOTENT

    session.add(
        EdgeAttributionEventRecord(
            attribution_event_id=event.attribution_event_id,
            contract_version=event.contract_version,
            subject_type=event.subject_type.value,
            subject_id=event.subject_id,
            event_type=event.event_type,
            opportunity_id=event.opportunity_id,
            evidence_id=event.evidence_id,
            payload=dict(event.payload),
            payload_hash=event.payload_hash,
            occurred_at=event.occurred_at,
            recorded_at=event.recorded_at,
        )
    )
    await session.flush()
    return INSERTED
