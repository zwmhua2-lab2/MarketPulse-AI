"""Provider-free durable Advisory predicate facts; callers retain terminal mapping."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.db.models import (
    AdvisoryDecisionInvocationRecord,
    DecisionSnapshotRecord,
    EdgeOpportunityEvidenceRecord,
    SymbolStateStore,
)

from .contracts import CurrentAdvisoryAuthority
from .identity import (
    AdvisoryIdentityError,
    advisory_snapshot_id,
    input_binding_digest,
    snapshot_payload_hash,
)
from .vocabulary import ACTIVATION_GATE_A_SHADOW


@dataclass(frozen=True)
class AdvisoryPredicateFacts:
    deadline_valid: bool
    evidence_current: bool
    opportunity_eligible: bool
    market_fresh: bool
    binding_valid: bool
    activation_valid: bool
    config_valid: bool
    shutdown_valid: bool

    @property
    def dispatch_legal(self) -> bool:
        return all((self.deadline_valid, self.evidence_current, self.opportunity_eligible,
                    self.market_fresh, self.binding_valid, self.activation_valid,
                    self.config_valid, self.shutdown_valid))


class AdvisoryPredicateEvaluator:
    """Read accepted facts from locked durable rows and current Host authority."""

    def __init__(self, authority: CurrentAdvisoryAuthority, *, host_accepting: bool = True) -> None:
        self._authority = authority
        self._host_accepting = host_accepting

    async def evaluate(self, session: AsyncSession, *, invocation: AdvisoryDecisionInvocationRecord,
                       evidence: EdgeOpportunityEvidenceRecord | None) -> AdvisoryPredicateFacts:
        now = await session.scalar(select(func.clock_timestamp()))
        if now is None:
            raise RuntimeError("PostgreSQL advisory predicate clock unavailable")
        # The lifecycle caller already owns Evidence -> Invocation -> Attempt.
        # Snapshot and current G2 state are predicate facts only; neither is a
        # lifecycle winner row and neither may supply a second authority.
        snapshot = await session.scalar(select(DecisionSnapshotRecord).where(
            DecisionSnapshotRecord.snapshot_id == invocation.snapshot_id))
        current_state = await session.scalar(select(SymbolStateStore).where(
            SymbolStateStore.instrument_id == (snapshot.instrument_id if snapshot else "")))
        higher_revision = False
        if evidence is not None:
            higher_revision = bool(await session.scalar(select(EdgeOpportunityEvidenceRecord.evidence_id).where(
                EdgeOpportunityEvidenceRecord.opportunity_id == invocation.opportunity_id,
                EdgeOpportunityEvidenceRecord.evidence_revision > invocation.evidence_revision).limit(1)))
        evidence_current = bool(evidence is not None and evidence.evidence_id == invocation.evidence_id
                                and evidence.evidence_hash == invocation.evidence_hash and not higher_revision)
        authority = self._authority
        activation_valid = authority.activation_level == ACTIVATION_GATE_A_SHADOW
        binding_valid = False
        if snapshot is not None and evidence is not None:
            try:
                payload_hash = snapshot_payload_hash(snapshot.payload)
                expected_snapshot_id = advisory_snapshot_id(
                    opportunity_id=evidence.opportunity_id,
                    evidence_id=evidence.evidence_id,
                    payload_hash=payload_hash,
                )
                expected_binding = input_binding_digest(
                    opportunity_id=evidence.opportunity_id,
                    evidence_id=evidence.evidence_id,
                    evidence_revision=evidence.evidence_revision,
                    evidence_hash=evidence.evidence_hash,
                    feature_snapshot_hash=evidence.feature_snapshot_hash,
                    snapshot_id=expected_snapshot_id,
                    snapshot_payload_hash=payload_hash,
                    state_version=snapshot.state_version,
                    config_version=snapshot.config_version,
                    family_id=evidence.family_id,
                    family_version=evidence.family_version,
                    instrument_id=evidence.instrument_id,
                    market_type=evidence.market_type,
                    advisory_config_epoch_id=snapshot.advisory_config_epoch_id or "",
                    decision_requested_at=snapshot.decision_requested_at,
                    deadline_duration_ms=snapshot.deadline_duration_ms,
                    deadline_policy_version=snapshot.deadline_policy_version or "",
                    decision_deadline_at=snapshot.decision_deadline_at,
                )
            except (AdvisoryIdentityError, AttributeError, TypeError):
                expected_binding = None
                expected_snapshot_id = None
                payload_hash = None
            binding_valid = bool(
                expected_binding is not None
                and expected_snapshot_id is not None
                and payload_hash is not None
                and snapshot.snapshot_id == expected_snapshot_id
                and snapshot.snapshot_payload_hash == payload_hash
                and snapshot.decision_invocation_id == invocation.decision_invocation_id
                and snapshot.opportunity_id == invocation.opportunity_id
                and snapshot.evidence_id == invocation.evidence_id
                and snapshot.evidence_revision == invocation.evidence_revision
                and snapshot.evidence_hash == invocation.evidence_hash
                and snapshot.feature_snapshot_hash == invocation.feature_snapshot_hash
                and snapshot.market_type == evidence.market_type
                and snapshot.snapshot_version == invocation.schema_version
                and snapshot.input_binding_digest == expected_binding
                and invocation.input_binding_digest == expected_binding
                and snapshot.decision_requested_at == invocation.decision_requested_at
                and snapshot.decision_deadline_at == invocation.decision_deadline_at
            )
        config_valid = bool(
            activation_valid
            and snapshot is not None
            and authority.config_version == snapshot.config_version
            and authority.epoch_id == snapshot.advisory_config_epoch_id
            and authority.experiment_definition_digest == invocation.experiment_definition_digest
            and authority.configured_provider_id == invocation.configured_provider_id
            and authority.configured_model_id == invocation.configured_model_id
            and authority.prompt_version == invocation.prompt_version
            and authority.schema_version == invocation.schema_version
            and authority.treatment_version == invocation.treatment_version
            and authority.baseline_policy_version == invocation.baseline_policy_version
            and authority.deadline_policy_version == snapshot.deadline_policy_version
        )
        # A missing optional reference BBO is a durable coverage fact, not proof
        # of a stale current market.  Only the accepted explicit stale state
        # negates this predicate; unknown/query failure still raises and fails closed.
        market_fresh = bool(
            evidence is not None and evidence.reference_data_status != "REFERENCE_STALE"
        )
        opportunity_eligible = bool(
            evidence is not None
            and now < evidence.expires_at
            and snapshot is not None
            and current_state is not None
            and current_state.state == "SETUP"
            and current_state.state_version == snapshot.state_version
        )
        return AdvisoryPredicateFacts(now < invocation.decision_deadline_at, evidence_current,
            opportunity_eligible, market_fresh, binding_valid, activation_valid,
            config_valid, self._host_accepting)


__all__ = ["AdvisoryPredicateEvaluator", "AdvisoryPredicateFacts"]
