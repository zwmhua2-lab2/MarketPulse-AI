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
        binding_valid = bool(snapshot is not None and snapshot.decision_invocation_id == invocation.decision_invocation_id
                             and snapshot.evidence_id == invocation.evidence_id and snapshot.evidence_hash == invocation.evidence_hash
                             and snapshot.feature_snapshot_hash == invocation.feature_snapshot_hash
                             and snapshot.input_binding_digest == invocation.input_binding_digest)
        authority = self._authority
        activation_valid = authority.activation_level == ACTIVATION_GATE_A_SHADOW
        config_valid = bool(activation_valid and authority.config_version == (snapshot.config_version if snapshot else None)
                            and authority.configured_provider_id == invocation.configured_provider_id
                            and authority.configured_model_id == invocation.configured_model_id
                            and authority.prompt_version == invocation.prompt_version
                            and authority.schema_version == invocation.schema_version
                            and authority.treatment_version == invocation.treatment_version
                            and authority.baseline_policy_version == invocation.baseline_policy_version
                            and authority.deadline_policy_version is not None)
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
