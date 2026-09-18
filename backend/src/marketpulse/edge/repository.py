"""Append-only persistence for the SE-02 Edge contracts.

Only insert operations are exposed. There is no update or delete API anywhere in this
module, so a business caller cannot silently rewrite an immutable evidence revision or
outcome revision. Immutability is additionally backstopped by database constraints
(unique ``opportunity_id + evidence_revision``, composite supersedes foreign keys and
the frozen-family / frozen-horizon check constraints) rather than by a trigger
framework.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.db.models import (
    EdgeAttributionEventRecord,
    EdgeBboObservationRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityCaptureAnchorOrphanRecord,
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.models import (
    AttributionEvent,
    BboObservation,
    EvidenceRevision,
    ForwardOutcomeContract,
)

if TYPE_CHECKING:
    from marketpulse.edge.capture import CaptureAnchor, CaptureAnchorOrphanClassification

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


class EdgeBboObservationConflict(EdgePersistenceError):
    """Same observation id but conflicting immutable observation content."""


class EdgeCaptureAnchorConflict(EdgePersistenceError):
    """Same opportunity + revision but different durable admission facts."""


class EdgeCaptureAnchorOrphanConflict(EdgePersistenceError):
    """Same anchor has a different immutable orphan classification."""


# Every immutable fact of a BBO observation, in a fixed order. The first eight are
# already folded into ``observation_id``; ``data_quality`` and ``tradable`` are not,
# so re-using an identity with a different eligibility fact must fail closed.
_BBO_IMMUTABLE_FIELDS = (
    "instrument_id",
    "market_type",
    "bid",
    "ask",
    "available_at",
    "source_event_time",
    "received_at",
    "source",
    "source_sequence",
    "data_quality",
    "tradable",
)


def _normalized(value: object) -> object:
    """Collapse str-valued enums onto their persisted string form."""

    return value.value if isinstance(value, StrEnum) else value


def _bbo_immutable_content(row: EdgeBboObservationRecord | BboObservation) -> tuple[object, ...]:
    """The immutable observation content as a comparable tuple."""

    return tuple(_normalized(getattr(row, field)) for field in _BBO_IMMUTABLE_FIELDS)


async def append_evidence_revision(
    session: AsyncSession,
    record: EvidenceRevision,
    *,
    advisory_admission_state: str | None = None,
) -> str:
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
            ).with_for_update()
        )
        if predecessor is None:
            raise EdgeInvalidSupersedes("superseded evidence revision does not exist")
        if predecessor.opportunity_id != record.opportunity_id:
            raise EdgeInvalidSupersedes("supersedes must stay inside one opportunity")
        if predecessor.evidence_revision != record.evidence_revision - 1:
            raise EdgeInvalidSupersedes(
                "supersedes must name the immediately preceding evidence revision"
            )
        head = await session.scalar(
            select(EdgeOpportunityEvidenceRecord)
            .where(EdgeOpportunityEvidenceRecord.opportunity_id == record.opportunity_id)
            .order_by(EdgeOpportunityEvidenceRecord.evidence_revision.desc())
            .limit(1)
            .with_for_update()
        )
        if head is None or head.evidence_id != predecessor.evidence_id:
            raise EdgeInvalidSupersedes("supersedes must name the current evidence head")

    if advisory_admission_state is not None and advisory_admission_state != "GATE_A_DISABLED":
        raise ValueError("only GATE_A_DISABLED may override the Evidence admission state")

    values = {
        "evidence_id": record.evidence_id,
        "opportunity_id": record.opportunity_id,
        "candidate_id": record.candidate_id,
        "family_id": record.family_id.value,
        "family_version": record.family_version,
        "instrument_id": record.instrument_id,
        "market_type": record.market_type.value,
        "evidence_revision": record.evidence_revision,
        "evidence_contract_version": record.evidence_contract_version,
        "evidence_hash": record.evidence_hash,
        "feature_snapshot_hash": record.feature_snapshot_hash,
        "feature_snapshot_hash_version": record.feature_snapshot_hash_version,
        "supersedes_evidence_id": record.supersedes_evidence_id,
        "detected_at": record.detected_at,
        "evidence_at": record.evidence_at,
        "expires_at": record.expires_at,
        "source_type": record.source_type.value,
        "source_identity": record.source_identity,
        "source_manifest_id": record.source_manifest_id,
        "reference_bid": record.reference_bid,
        "reference_ask": record.reference_ask,
        "reference_received_at": record.reference_received_at,
        "reference_data_status": record.reference_data_status.value,
        "evidence_payload": dict(record.evidence_payload),
        "feature_snapshot_payload": dict(record.feature_snapshot_payload),
        "created_at": record.created_at,
    }
    if advisory_admission_state is not None:
        values["advisory_admission_state"] = advisory_admission_state

    session.add(
        EdgeOpportunityEvidenceRecord(
            **values,
        )
    )
    await session.flush()
    return INSERTED


async def record_bbo_observation(session: AsyncSession, observation: BboObservation) -> str:
    """Append one normalized L1 BBO observation (content-addressed, append-only).

    Same ``observation_id`` + same immutable content -> ``IDEMPOTENT``.
    Same ``observation_id`` + conflicting immutable content -> ``EdgeBboObservationConflict``.

    ``data_quality`` and ``tradable`` sit outside the deterministic identity, so a
    re-used identity is compared against them explicitly: the first stored copy is
    never silently kept when a conflicting eligibility fact arrives.
    """

    values = {
        "observation_id": observation.observation_id,
        "instrument_id": observation.instrument_id,
        "market_type": observation.market_type.value,
        "bid": observation.bid,
        "ask": observation.ask,
        "available_at": observation.available_at,
        "source_event_time": observation.source_event_time,
        "received_at": observation.received_at,
        "data_quality": observation.data_quality.value,
        "tradable": observation.tradable,
        "source": observation.source,
        "source_sequence": observation.source_sequence,
        "created_at": observation.created_at,
    }
    inserted = await session.scalar(
        insert(EdgeBboObservationRecord)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[EdgeBboObservationRecord.observation_id])
        .returning(EdgeBboObservationRecord.observation_id)
    )
    if inserted is not None:
        return INSERTED
    existing = await session.get(EdgeBboObservationRecord, observation.observation_id)
    if existing is not None and _bbo_immutable_content(existing) == _bbo_immutable_content(observation):
        return IDEMPOTENT
    raise EdgeBboObservationConflict(
        "same observation_id with conflicting immutable observation content "
        f"(observation_id={observation.observation_id})"
    )


async def append_capture_anchor(session: AsyncSession, anchor: CaptureAnchor) -> str:
    """Append one Forward Paper admission anchor, or verify its idempotent twin."""

    from marketpulse.edge.capture import CaptureAnchor

    # ``model_copy`` can bypass Pydantic validators, so canonicalize every caller
    # object again at the persistence boundary before trusting any supplied hash.
    anchor = CaptureAnchor.model_validate(anchor.model_dump(mode="python"))
    values = {
        "opportunity_id": anchor.opportunity_id,
        "evidence_revision": anchor.evidence_revision,
        "event_id": anchor.event_id,
        "candidate_id": anchor.candidate_id,
        "evidence_at": anchor.evidence_at,
        "reference_data_status": anchor.reference_data_status.value,
        "reference_bbo_observation_id": anchor.reference_bbo_observation_id,
        "source_type": anchor.source_type.value,
        "source_identity": anchor.source_identity,
        "source_manifest_id": anchor.source_manifest_id,
        "forward_admission_session_id": anchor.forward_admission_session_id,
        "forward_admission_event_digest": anchor.forward_admission_event_digest,
        "forward_admission_proof_hash": anchor.forward_admission_proof_hash,
        "anchor_payload_version": anchor.anchor_payload_version,
        "anchor_payload": dict(anchor.anchor_payload),
        "anchor_hash": anchor.anchor_hash,
        "anchor_hash_version": anchor.anchor_hash_version,
        "recorded_at": anchor.recorded_at,
    }
    inserted = await session.scalar(
        insert(EdgeOpportunityCaptureAnchorRecord)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=[
                EdgeOpportunityCaptureAnchorRecord.opportunity_id,
                EdgeOpportunityCaptureAnchorRecord.evidence_revision,
            ]
        )
        .returning(EdgeOpportunityCaptureAnchorRecord.opportunity_id)
    )
    if inserted is not None:
        return INSERTED
    existing = await session.get(
        EdgeOpportunityCaptureAnchorRecord,
        (anchor.opportunity_id, anchor.evidence_revision),
    )
    if existing is not None and capture_anchor_from_record(existing) == anchor:
        return IDEMPOTENT
    raise EdgeCaptureAnchorConflict(
        "same opportunity and revision with different capture anchor content "
        f"(opportunity_id={anchor.opportunity_id}, revision={anchor.evidence_revision})"
    )


def capture_anchor_from_record(record: EdgeOpportunityCaptureAnchorRecord) -> CaptureAnchor:
    """Rehydrate one immutable anchor without consulting mutable runtime state."""

    from marketpulse.edge.capture import CaptureAnchor

    return CaptureAnchor(
        opportunity_id=record.opportunity_id,
        evidence_revision=record.evidence_revision,
        event_id=record.event_id,
        candidate_id=record.candidate_id,
        evidence_at=record.evidence_at,
        reference_data_status=record.reference_data_status,
        reference_bbo_observation_id=record.reference_bbo_observation_id,
        source_type=record.source_type,
        source_identity=record.source_identity,
        source_manifest_id=record.source_manifest_id,
        forward_admission_session_id=record.forward_admission_session_id,
        forward_admission_event_digest=record.forward_admission_event_digest,
        forward_admission_proof_hash=record.forward_admission_proof_hash,
        anchor_payload_version=record.anchor_payload_version,
        anchor_payload=dict(record.anchor_payload),
        anchor_hash=record.anchor_hash,
        anchor_hash_version=record.anchor_hash_version,
        recorded_at=record.recorded_at,
    )


async def load_capture_anchor_for_event(
    session: AsyncSession, event_id: str
) -> CaptureAnchor | None:
    """Load the single Forward Paper anchor admitted for a triggering G2 event."""

    record = await session.scalar(
        select(EdgeOpportunityCaptureAnchorRecord).where(
            EdgeOpportunityCaptureAnchorRecord.event_id == event_id
        )
    )
    return None if record is None else capture_anchor_from_record(record)


async def append_capture_anchor_orphan(
    session: AsyncSession, orphan: CaptureAnchorOrphanClassification
) -> str:
    """Append or verify the one immutable orphan classification for an anchor."""

    from marketpulse.edge.capture import CaptureAnchorOrphanClassification

    orphan = CaptureAnchorOrphanClassification.model_validate(orphan.model_dump(mode="python"))
    values = {
        "opportunity_id": orphan.opportunity_id,
        "evidence_revision": orphan.evidence_revision,
        "classification": orphan.classification,
        "reason": orphan.reason,
        "expected_precondition": dict(orphan.expected_precondition),
        "actual_precondition": dict(orphan.actual_precondition),
        "orphan_version": orphan.orphan_version,
        "classification_hash": orphan.classification_hash,
        "classification_hash_version": orphan.classification_hash_version,
        "detected_at": orphan.detected_at,
        "recorded_at": orphan.recorded_at,
    }
    inserted = await session.scalar(
        insert(EdgeOpportunityCaptureAnchorOrphanRecord)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=[
                EdgeOpportunityCaptureAnchorOrphanRecord.opportunity_id,
                EdgeOpportunityCaptureAnchorOrphanRecord.evidence_revision,
            ]
        )
        .returning(EdgeOpportunityCaptureAnchorOrphanRecord.opportunity_id)
    )
    if inserted is not None:
        return INSERTED
    existing = await session.get(
        EdgeOpportunityCaptureAnchorOrphanRecord,
        (orphan.opportunity_id, orphan.evidence_revision),
    )
    if existing is not None and existing.classification_hash == orphan.classification_hash:
        return IDEMPOTENT
    raise EdgeCaptureAnchorOrphanConflict(
        "same capture anchor has a different orphan classification "
        f"(opportunity_id={orphan.opportunity_id}, revision={orphan.evidence_revision})"
    )


async def load_capture_anchor_orphan(
    session: AsyncSession, opportunity_id: str, evidence_revision: int
) -> EdgeOpportunityCaptureAnchorOrphanRecord | None:
    """Return a restart-visible orphan record, if this anchor was classified."""

    return await session.get(
        EdgeOpportunityCaptureAnchorOrphanRecord, (opportunity_id, evidence_revision)
    )


async def append_forward_outcome(
    session: AsyncSession, record: ForwardOutcomeContract
) -> str:
    """Append one immutable forward-outcome revision. Returns ``INSERTED``/``IDEMPOTENT``.

    A revision chain is scoped to ``(opportunity_id, evidence_id, horizon)``: each such
    triple owns its own revision numbering. A revision above 1 may therefore only
    supersede the immediately preceding revision *of the same scope*; naming a
    predecessor from another evidence revision, another horizon or another opportunity
    is an invalid correction lineage and fails closed.
    """

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
        if predecessor.evidence_id != record.evidence_id:
            raise EdgeInvalidOutcomeSupersedes(
                "supersedes must stay inside one evidence revision"
            )
        if predecessor.horizon != record.horizon.value:
            raise EdgeInvalidOutcomeSupersedes("supersedes must stay inside one horizon")
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
