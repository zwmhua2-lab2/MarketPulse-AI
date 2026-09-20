"""Durable, provider-free Gate-A admission staging.

This module owns only the nested-SAVEPOINT contents.  The G2 transaction owner
performs the core flush and capacity acquisition before calling it, retains the
outer transaction, and publishes the returned ref only after its commit.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.db.models import (
    AdvisoryDecisionInvocationRecord,
    DecisionSnapshotRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.hashing import canonical_digest
from marketpulse.g2.models import AdvisoryWorkRef

from .contracts import AdvisoryAdmissionConfig
from .fence import AdvisoryDbFence
from .identity import (
    advisory_snapshot_id,
    baseline_arm_id,
    canonical_utc_timestamp,
    decision_invocation_id,
    experiment_definition_digest,
    experiment_id,
    input_binding_digest,
    pair_id,
    snapshot_payload_hash,
    treatment_arm_id,
)
from .vocabulary import (
    ADMISSION_FAILED_FINAL,
    ADMISSION_INVOCATION_CREATED,
    ADMISSION_UNSTAGED,
    ADVISORY_SEED_DIGEST_DOMAIN,
    ADVISORY_SEED_VERSION,
    INVOCATION_ADMITTED,
    PARTICIPATION_NO_LONG_UNBOUND,
    PARTICIPATION_PARTICIPATE_LONG,
    REASON_ADMISSION_STAGING_FAILED_UNBOUND,
)
from .worker import AdvisoryFinalizer


class AdvisoryAdmissionError(RuntimeError):
    """The caller must rollback only the current Advisory SAVEPOINT."""


class AdvisoryAdmissionWriter:
    """Build one complete immutable admission or nothing.

    The constructor deliberately accepts only frozen, non-provider configuration.
    There is no queue, worker, provider, `TradePlan`, or execution dependency in
    this call graph.
    """

    def __init__(self, config: AdvisoryAdmissionConfig) -> None:
        self._config = config

    async def admit(
        self,
        session: AsyncSession,
        *,
        evidence_id: str,
        state_version: int,
    ) -> AdvisoryWorkRef:
        """Stage Snapshot, Invocation and Evidence accounting in the current SAVEPOINT.

        The caller has already flushed core G2/Evidence facts and opened a nested
        transaction.  This function never starts a transaction or performs a
        capacity wait, so it cannot change the core transaction's ownership.
        """

        evidence = await session.scalar(
            select(EdgeOpportunityEvidenceRecord)
            .where(EdgeOpportunityEvidenceRecord.evidence_id == evidence_id)
            .with_for_update()
        )
        if evidence is None:
            raise AdvisoryAdmissionError("formal evidence is missing after core flush")
        if evidence.advisory_admission_state != ADMISSION_UNSTAGED:
            raise AdvisoryAdmissionError("formal evidence is not eligible for Gate-A admission")

        requested_at = await session.scalar(select(func.clock_timestamp()))
        if requested_at is None:
            raise AdvisoryAdmissionError("PostgreSQL admission clock is unavailable")
        deadline_at = requested_at + timedelta(milliseconds=self._config.deadline_duration_ms)

        snapshot_payload = self._snapshot_payload(evidence, state_version)
        payload_hash = snapshot_payload_hash(snapshot_payload)
        snapshot_id = advisory_snapshot_id(
            opportunity_id=evidence.opportunity_id,
            evidence_id=evidence.evidence_id,
            payload_hash=payload_hash,
        )
        binding = input_binding_digest(
            opportunity_id=evidence.opportunity_id,
            evidence_id=evidence.evidence_id,
            evidence_revision=evidence.evidence_revision,
            evidence_hash=evidence.evidence_hash,
            feature_snapshot_hash=evidence.feature_snapshot_hash,
            snapshot_id=snapshot_id,
            snapshot_payload_hash=payload_hash,
            state_version=state_version,
            config_version=self._config.config_version,
            family_id=evidence.family_id,
            family_version=evidence.family_version,
            instrument_id=evidence.instrument_id,
            market_type=evidence.market_type,
            advisory_config_epoch_id=self._config.epoch.epoch_id or "",
            decision_requested_at=requested_at,
            deadline_duration_ms=self._config.deadline_duration_ms,
            deadline_policy_version=self._config.deadline_policy_version,
            decision_deadline_at=deadline_at,
        )
        definition_digest = experiment_definition_digest(self._config.experiment_definition)
        exp_id = experiment_id(self._config.experiment_definition)
        pair = pair_id(experiment_id=exp_id, input_binding_digest=binding)
        baseline = baseline_arm_id(pair_id=pair)
        treatment = treatment_arm_id(pair_id=pair)
        invocation_id = decision_invocation_id(
            experiment_id=exp_id,
            pair_id=pair,
            treatment_arm_id=treatment,
            input_binding_digest=binding,
            prompt_version=self._config.prompt_version,
            schema_version=self._config.schema_version,
            treatment_version=self._config.treatment_version,
            configured_provider_id=self._config.configured_provider_id,
            configured_model_id=self._config.configured_model_id,
        )
        seed = self._seed(
            evidence=evidence,
            state_version=state_version,
            snapshot_id=snapshot_id,
            snapshot_payload_hash_value=payload_hash,
            input_binding_digest_value=binding,
            experiment_id_value=exp_id,
            experiment_definition_digest_value=definition_digest,
            pair_id_value=pair,
            baseline_arm_id_value=baseline,
            treatment_arm_id_value=treatment,
            decision_invocation_id_value=invocation_id,
            decision_requested_at=requested_at,
            decision_deadline_at=deadline_at,
        )
        seed_digest = canonical_digest(ADVISORY_SEED_DIGEST_DOMAIN, ADVISORY_SEED_VERSION, seed)

        session.add(
            DecisionSnapshotRecord(
                snapshot_id=snapshot_id,
                instrument_id=evidence.instrument_id,
                symbol=str(evidence.evidence_payload.get("symbol", evidence.instrument_id)),
                run_mode="LIVE_PAPER",
                state_version=state_version,
                config_version=self._config.config_version,
                snapshot_version=self._config.schema_version,
                created_at=requested_at,
                payload=snapshot_payload,
                decision_invocation_id=invocation_id,
                opportunity_id=evidence.opportunity_id,
                evidence_id=evidence.evidence_id,
                evidence_revision=evidence.evidence_revision,
                evidence_hash=evidence.evidence_hash,
                feature_snapshot_hash=evidence.feature_snapshot_hash,
                market_type=evidence.market_type,
                snapshot_payload_hash=payload_hash,
                input_binding_digest=binding,
                advisory_config_epoch_id=self._config.epoch.epoch_id,
                decision_requested_at=requested_at,
                deadline_duration_ms=self._config.deadline_duration_ms,
                deadline_policy_version=self._config.deadline_policy_version,
                decision_deadline_at=deadline_at,
            )
        )
        # This FK is not deferred. Flush the Snapshot first instead of relying on
        # incidental ORM insertion order between otherwise unrelated records.
        await session.flush()
        session.add(
            AdvisoryDecisionInvocationRecord(
                decision_invocation_id=invocation_id,
                snapshot_id=snapshot_id,
                opportunity_id=evidence.opportunity_id,
                evidence_id=evidence.evidence_id,
                evidence_revision=evidence.evidence_revision,
                evidence_hash=evidence.evidence_hash,
                feature_snapshot_hash=evidence.feature_snapshot_hash,
                experiment_id=exp_id,
                experiment_definition_digest=definition_digest,
                pair_id=pair,
                baseline_arm_id=baseline,
                treatment_arm_id=treatment,
                arm_id=treatment,
                baseline_policy_version=self._config.baseline_policy_version,
                baseline_participation=PARTICIPATION_PARTICIPATE_LONG,
                input_binding_digest=binding,
                prompt_version=self._config.prompt_version,
                schema_version=self._config.schema_version,
                treatment_version=self._config.treatment_version,
                configured_provider_id=self._config.configured_provider_id,
                configured_model_id=self._config.configured_model_id,
                decision_requested_at=requested_at,
                decision_deadline_at=deadline_at,
                state=INVOCATION_ADMITTED,
                final_status=None,
                final_reason_code=None,
                finalized_at=None,
                final_attempt_id=None,
                final_decision_id=None,
                created_at=requested_at,
                updated_at=requested_at,
            )
        )
        # The Invocation's Evidence/Snapshot references are now concrete. The
        # reverse Evidence -> Invocation FK is DEFERRABLE and is written below.
        await session.flush()
        evidence.advisory_admission_state = ADMISSION_INVOCATION_CREATED
        evidence.advisory_treatment_participation = PARTICIPATION_PARTICIPATE_LONG
        evidence.advisory_admission_seed_version = ADVISORY_SEED_VERSION
        evidence.advisory_admission_seed_digest = seed_digest
        evidence.advisory_admission_seed = seed
        evidence.advisory_decision_invocation_id = invocation_id
        await session.flush()
        return AdvisoryWorkRef(invocation_id, deadline_at)

    async def terminalize_unbound(self, session: AsyncSession, *, evidence_id: str) -> bool:
        """Write the only config-free fallback allowed after staging rollback."""

        result = await session.execute(
            update(EdgeOpportunityEvidenceRecord)
            .where(
                EdgeOpportunityEvidenceRecord.evidence_id == evidence_id,
                EdgeOpportunityEvidenceRecord.advisory_admission_state == ADMISSION_UNSTAGED,
            )
            .values(
                advisory_admission_state=ADMISSION_FAILED_FINAL,
                advisory_admission_reason_code=REASON_ADMISSION_STAGING_FAILED_UNBOUND,
                advisory_treatment_participation=PARTICIPATION_NO_LONG_UNBOUND,
            )
        )
        return result.rowcount == 1

    def _snapshot_payload(
        self, evidence: EdgeOpportunityEvidenceRecord, state_version: int
    ) -> dict[str, Any]:
        return {
            "contract_version": self._config.schema_version,
            "evidence": {
                "opportunity_id": evidence.opportunity_id,
                "evidence_id": evidence.evidence_id,
                "evidence_revision": evidence.evidence_revision,
                "evidence_hash": evidence.evidence_hash,
                "feature_snapshot_hash": evidence.feature_snapshot_hash,
                "evidence_payload": dict(evidence.evidence_payload),
                "feature_snapshot_payload": dict(evidence.feature_snapshot_payload),
            },
            "state_version": state_version,
            "config_version": self._config.config_version,
        }

    def _seed(self, **facts: Any) -> dict[str, Any]:
        evidence = facts.pop("evidence")
        # JSONB stores timestamp facts in the exact canonical representation used
        # by the identity contract; raw datetimes are neither JSON-safe nor an
        # acceptable alternate serialization authority.
        facts["decision_requested_at"] = canonical_utc_timestamp(
            facts["decision_requested_at"]
        )
        facts["decision_deadline_at"] = canonical_utc_timestamp(facts["decision_deadline_at"])
        return {
            "seed_version": ADVISORY_SEED_VERSION,
            "evidence": {
                "opportunity_id": evidence.opportunity_id,
                "evidence_id": evidence.evidence_id,
                "evidence_revision": evidence.evidence_revision,
                "evidence_hash": evidence.evidence_hash,
                "feature_snapshot_hash": evidence.feature_snapshot_hash,
            },
            "state_version": facts["state_version"],
            "config_version": self._config.config_version,
            "advisory_config_epoch_id": self._config.epoch.epoch_id,
            "experiment_definition": dict(self._config.experiment_definition),
            "configured_provider_id": self._config.configured_provider_id,
            "configured_model_id": self._config.configured_model_id,
            "deadline_duration_ms": self._config.deadline_duration_ms,
            "deadline_policy_version": self._config.deadline_policy_version,
            "prompt_version": self._config.prompt_version,
            "schema_version": self._config.schema_version,
            "treatment_version": self._config.treatment_version,
            "baseline_policy_version": self._config.baseline_policy_version,
            **facts,
        }


class AdvisoryIngress:
    """Host-owned, bounded post-commit handoff with no provider capability.

    Queue publication is deliberately separate from admission. When the queue is
    full, the just-committed Invocation is terminalized with the exact durable
    no-attempt pair instead of being dropped, coalesced, or held in a hidden
    process-local backlog.
    """

    def __init__(
        self, fence: AdvisoryDbFence, *, queue_capacity: int
    ) -> None:
        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")
        self._fence = fence
        self._queue: asyncio.Queue[AdvisoryWorkRef] = asyncio.Queue(maxsize=queue_capacity)

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def queue_capacity(self) -> int:
        return self._queue.maxsize

    def take_nowait(self) -> AdvisoryWorkRef:
        """Consumer seam; the queue contains only frozen post-commit references."""

        return self._queue.get_nowait()

    async def post_commit_offer(self, ref: AdvisoryWorkRef) -> bool:
        """Offer one committed ref without DB work, waiting, or capacity acquisition."""

        try:
            self._queue.put_nowait(ref)
        except asyncio.QueueFull:
            return False
        return True

    async def terminalize_queue_rejection(self, ref: AdvisoryWorkRef) -> bool:
        """Explicit bounded terminal step after a rejected queue offer."""

        return await AdvisoryFinalizer(self._fence).terminalize_queue_rejection(ref)

    async def consume_one(
        self, consume: Callable[[AdvisoryWorkRef], Awaitable[AdvisoryWorkRef | None]]
    ) -> bool:
        """Consume one bounded ref and re-offer only a durable retry continuation."""

        try:
            ref = self.take_nowait()
        except asyncio.QueueEmpty:
            return False
        try:
            retry_ref = await consume(ref)
            if retry_ref is not None and not await self.post_commit_offer(retry_ref):
                await self.terminalize_queue_rejection(retry_ref)
            return True
        finally:
            self._queue.task_done()

__all__ = ["AdvisoryAdmissionError", "AdvisoryAdmissionWriter", "AdvisoryIngress"]
