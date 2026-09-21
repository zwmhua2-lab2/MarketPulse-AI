"""Provider-free durable Attempt start boundary for Advisory consumers."""

from __future__ import annotations

from sqlalchemy import func, select

from marketpulse.db.models import (
    AdvisoryDecisionAttemptRecord,
    AdvisoryDecisionInvocationRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.g2.models import AdvisoryWorkRef

from .fence import AdvisoryDbFence
from .identity import attempt_id
from .predicates import AdvisoryPredicateEvaluator
from .vocabulary import (
    ATTEMPT_STARTED,
    INVOCATION_ACTIVE,
    INVOCATION_ADMITTED,
    INVOCATION_RETRY_PENDING,
)


class AdvisoryAttemptStarter:
    """Commit `ACTIVE + STARTED` before any future provider call is allowed."""

    def __init__(self, fence: AdvisoryDbFence, evaluator: AdvisoryPredicateEvaluator | None = None) -> None:
        self._fence = fence
        self._evaluator = evaluator

    async def start(self, ref: AdvisoryWorkRef) -> str | None:
        # A caller without current predicate authority has no right to create a
        # STARTED Attempt.  This check is deliberately before any lifecycle DB
        # work so a future composition cannot bypass P1-03 by omission.
        if self._evaluator is None:
            return None
        async with self._fence.transaction() as session:
            target = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == ref.decision_invocation_id
                )
            )
            if target is None:
                return None
            evidence = await session.scalar(
                select(EdgeOpportunityEvidenceRecord)
                .where(EdgeOpportunityEvidenceRecord.evidence_id == target.evidence_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == ref.decision_invocation_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                evidence is None
                or invocation is None
                or invocation.evidence_id != evidence.evidence_id
                or invocation.state not in (INVOCATION_ADMITTED, INVOCATION_RETRY_PENDING)
                or evidence.evidence_hash != invocation.evidence_hash
            ):
                return None
            facts = await self._evaluator.evaluate(session, invocation=invocation, evidence=evidence)
            if not facts.dispatch_legal:
                return None
            now = await session.scalar(select(func.clock_timestamp()))
            if now is None or now >= invocation.decision_deadline_at:
                return None
            prior_attempt = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(
                    AdvisoryDecisionAttemptRecord.decision_invocation_id
                    == invocation.decision_invocation_id
                )
                .order_by(AdvisoryDecisionAttemptRecord.attempt_number.desc())
                .limit(1)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            number = (prior_attempt.attempt_number if prior_attempt is not None else 0) + 1
            identifier = attempt_id(
                decision_invocation_id=invocation.decision_invocation_id, attempt_number=number
            )
            session.add(
                AdvisoryDecisionAttemptRecord(
                    attempt_id=identifier,
                    decision_invocation_id=invocation.decision_invocation_id,
                    attempt_number=number,
                    attempt_state=ATTEMPT_STARTED,
                    retry_class=None,
                    retry_reason=None,
                    prior_attempt_id=prior_attempt.attempt_id if prior_attempt is not None else None,
                    provider_request_id=None,
                    provider_response_id=None,
                    configured_provider_id=invocation.configured_provider_id,
                    configured_model_id=invocation.configured_model_id,
                    provider_reported_model_id=None,
                    input_binding_digest=invocation.input_binding_digest,
                    started_at=now,
                    response_received_at=None,
                    finished_at=None,
                    latency_ms=None,
                    provider_outcome=None,
                    normalized_status=None,
                    error_category=None,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    usage_unavailable_reason="NOT_CALLED_YET",
                    monetary_cost=None,
                    pricing_version=None,
                    output_digest=None,
                    validation_result=None,
                    validation_errors=None,
                    redacted_request_envelope=None,
                    redacted_response_envelope=None,
                )
            )
            invocation.state = INVOCATION_ACTIVE
            invocation.updated_at = now
            return identifier


__all__ = ["AdvisoryAttemptStarter"]
