"""Bounded, fake-provider-only Advisory worker and durable finalization primitives."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    AdvisoryDecisionAttemptRecord,
    AdvisoryDecisionInvocationRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.g2.models import AdvisoryWorkRef

from .attempts import AdvisoryAttemptStarter
from .contracts import LiveAttemptCapability, RecoveryInput
from .fence import AdvisoryDbFence, AdvisoryFenceError
from .predicates import AdvisoryPredicateEvaluator, AdvisoryPredicateFacts
from .vocabulary import (
    ATTEMPT_ABANDONED,
    ATTEMPT_COMPLETED,
    ATTEMPT_LATE_RESULT,
    ATTEMPT_PROCESS_LOST,
    ATTEMPT_STARTED,
    FINAL_STATUS_CAPACITY_BLOCKED,
    FINAL_STATUS_INVALID_SCHEMA,
    FINAL_STATUS_STALE_DECISION,
    FINAL_STATUS_VALID,
    INVOCATION_ACTIVE,
    INVOCATION_ADMITTED,
    INVOCATION_FINAL,
    INVOCATION_RETRY_PENDING,
    REASON_ADVISORY_DB_CAPACITY_UNAVAILABLE,
    REASON_ADVISORY_QUEUE_REJECTED,
    REASON_DEADLINE_EXPIRED_BEFORE_PROVIDER,
    REASON_EVIDENCE_SUPERSEDED,
    REASON_EVIDENCE_SUPERSEDED_BEFORE_PROVIDER,
    REASON_RETRY_EXHAUSTED,
    REASON_SCHEMA_FAILURE,
    REASON_SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT,
    REASON_VALID_PROVIDER_DECISION,
)


@dataclass(frozen=True)
class FakeProviderResult:
    """Test-only normalized output; no real provider adapter is part of I2."""

    valid: bool = True
    retry: bool = False
    payload: dict[str, object] | None = None


class AdvisoryProvider(Protocol):
    async def decide(self, ref: AdvisoryWorkRef, attempt_id: str) -> FakeProviderResult: ...


def _current_attempt_external_terminal(
    facts: AdvisoryPredicateFacts | None,
) -> tuple[str, str] | None:
    """Map an already-durable Attempt to the frozen current-attempt terminal."""

    if facts is None:
        return None
    if not facts.deadline_valid:
        return FINAL_STATUS_STALE_DECISION, "DEADLINE_EXPIRED"
    if not facts.evidence_current:
        return FINAL_STATUS_STALE_DECISION, REASON_EVIDENCE_SUPERSEDED
    if not all(
        (
            facts.opportunity_eligible,
            facts.market_fresh,
            facts.binding_valid,
            facts.activation_valid,
            facts.config_valid,
            facts.shutdown_valid,
        )
    ):
        return FINAL_STATUS_STALE_DECISION, "STALE_BINDING"
    return None


def _recovery_external_terminal(
    facts: AdvisoryPredicateFacts,
) -> tuple[str, str] | None:
    """Map recovery predicates before retry policy; retry-gap provenance is NULL."""

    if not facts.deadline_valid:
        return FINAL_STATUS_STALE_DECISION, REASON_DEADLINE_EXPIRED_BEFORE_PROVIDER
    if not facts.evidence_current:
        return FINAL_STATUS_STALE_DECISION, REASON_EVIDENCE_SUPERSEDED_BEFORE_PROVIDER
    if not facts.opportunity_eligible or not facts.market_fresh:
        return FINAL_STATUS_STALE_DECISION, "OPPORTUNITY_STALE_BEFORE_PROVIDER"
    if not facts.binding_valid:
        return FINAL_STATUS_STALE_DECISION, "BINDING_INVALID_BEFORE_PROVIDER"
    if not facts.activation_valid:
        return FINAL_STATUS_STALE_DECISION, "ACTIVATION_DISABLED_BEFORE_PROVIDER"
    if not facts.config_valid:
        return FINAL_STATUS_STALE_DECISION, "EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER"
    if not facts.shutdown_valid:
        return FINAL_STATUS_INVALID_SCHEMA, "SHUTDOWN_BEFORE_PROVIDER"
    return None


class AdvisoryFinalizer:
    """Winner-fenced Attempt completion; it never touches economic authorities."""

    def __init__(
        self,
        fence: AdvisoryDbFence | None,
        evaluator: AdvisoryPredicateEvaluator | None = None,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._fence = fence
        self._evaluator = evaluator
        self._session_factory = session_factory

    @asynccontextmanager
    async def _recovery_transaction(self):
        if self._fence is not None:
            async with self._fence.transaction() as session:
                yield session
            return
        if self._session_factory is None:
            raise AdvisoryFenceError("advisory recovery transaction is not configured")
        async with self._session_factory() as session, session.begin():
            yield session

    async def finalize(self, attempt_id: str, result: FakeProviderResult) -> AdvisoryWorkRef | None:
        # Completion is a normal lifecycle transition, so it cannot proceed
        # without the current predicate authority required by P1-04.  The
        # separate pre-provider terminal methods intentionally remain usable by
        # provider-free ingress/recovery composition.
        if self._evaluator is None:
            return None
        async with self._recovery_transaction() as session:
            attempt_target = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(AdvisoryDecisionAttemptRecord.attempt_id == attempt_id)
            )
            if attempt_target is None:
                return None
            invocation_target = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == attempt_target.decision_invocation_id
                )
            )
            if invocation_target is None:
                return None
            evidence = await session.scalar(
                select(EdgeOpportunityEvidenceRecord)
                .where(EdgeOpportunityEvidenceRecord.evidence_id == invocation_target.evidence_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == invocation_target.decision_invocation_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            current_attempt = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(
                    AdvisoryDecisionAttemptRecord.decision_invocation_id
                    == invocation_target.decision_invocation_id
                )
                .order_by(AdvisoryDecisionAttemptRecord.attempt_number.desc())
                .limit(1)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                evidence is None
                or invocation is None
                or current_attempt is None
                or invocation.evidence_id != evidence.evidence_id
                or invocation.evidence_hash != evidence.evidence_hash
            ):
                return None
            if invocation.state == INVOCATION_FINAL:
                submitted = await session.scalar(
                    select(AdvisoryDecisionAttemptRecord)
                    .where(AdvisoryDecisionAttemptRecord.attempt_id == attempt_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if (
                    submitted is not None
                    and invocation.final_attempt_id != submitted.attempt_id
                    and submitted.attempt_state not in (ATTEMPT_PROCESS_LOST, ATTEMPT_ABANDONED)
                ):
                    submitted.attempt_state = ATTEMPT_LATE_RESULT
                return None
            if (
                invocation.state != INVOCATION_ACTIVE
                or current_attempt.attempt_id != attempt_id
                or current_attempt.attempt_state != ATTEMPT_STARTED
            ):
                return None
            attempt = current_attempt
            facts = await self._evaluator.evaluate(
                session, invocation=invocation, evidence=evidence
            )
            now = await session.scalar(select(func.clock_timestamp()))
            if not isinstance(now, datetime):
                raise TypeError("PostgreSQL finalizer clock unavailable")
            attempt.attempt_state = ATTEMPT_COMPLETED
            attempt.response_received_at = now
            attempt.finished_at = now
            attempt.provider_outcome = "FAKE_VALID" if result.valid else "FAKE_INVALID"
            attempt.normalized_status = FINAL_STATUS_VALID if result.valid else FINAL_STATUS_INVALID_SCHEMA
            attempt.redacted_response_envelope = result.payload or {}
            superseded = (facts is not None and not facts.evidence_current) or evidence is None or bool(
                await session.scalar(
                    select(
                        exists().where(
                            EdgeOpportunityEvidenceRecord.opportunity_id == invocation.opportunity_id,
                            EdgeOpportunityEvidenceRecord.evidence_revision > invocation.evidence_revision,
                        )
                    )
                )
            )
            external_terminal = _current_attempt_external_terminal(facts)
            # R3 precedence: current deadline/external/config predicates always
            # outrank a retryable provider response.
            if result.retry and not superseded and external_terminal is None:
                invocation.state = INVOCATION_RETRY_PENDING
                invocation.updated_at = now
                return AdvisoryWorkRef(invocation.decision_invocation_id, invocation.decision_deadline_at)
            invocation.state = INVOCATION_FINAL
            invocation.finalized_at = now
            invocation.final_attempt_id = attempt.attempt_id
            invocation.final_decision_id = None
            invocation.updated_at = now
            if external_terminal is not None:
                invocation.final_status, invocation.final_reason_code = external_terminal
            elif superseded:
                invocation.final_status = FINAL_STATUS_STALE_DECISION
                invocation.final_reason_code = REASON_EVIDENCE_SUPERSEDED
            elif result.valid:
                invocation.final_status = FINAL_STATUS_VALID
                invocation.final_reason_code = REASON_VALID_PROVIDER_DECISION
            else:
                invocation.final_status = FINAL_STATUS_INVALID_SCHEMA
                invocation.final_reason_code = REASON_SCHEMA_FAILURE
            return None

    async def terminalize_db_capacity_unavailable(self, ref: AdvisoryWorkRef) -> bool:
        """Fail closed before a provider Attempt when a bounded terminal lease wins.

        A terminal-write lease is deliberately separate from the failed ordinary
        Attempt acquisition, while still consuming only Advisory capacity A.  If
        that lease is unavailable, this method leaves the existing durable state
        untouched for a later owner/restart to inspect.
        """

        try:
            async with self._fence.terminal_write_transaction() as session:
                invocation_target = await session.scalar(
                    select(AdvisoryDecisionInvocationRecord)
                    .where(
                        AdvisoryDecisionInvocationRecord.decision_invocation_id
                        == ref.decision_invocation_id
                    )
                )
                if invocation_target is None:
                    return False
                evidence = await session.scalar(
                    select(EdgeOpportunityEvidenceRecord)
                    .where(EdgeOpportunityEvidenceRecord.evidence_id == invocation_target.evidence_id)
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
                    or invocation.evidence_hash != evidence.evidence_hash
                    or invocation.state == INVOCATION_FINAL
                ):
                    return False
                now = await session.scalar(select(func.clock_timestamp()))
                if not isinstance(now, datetime):
                    raise TypeError("PostgreSQL finalizer clock unavailable")
                superseded = evidence is None or bool(
                    await session.scalar(
                        select(
                            exists().where(
                                EdgeOpportunityEvidenceRecord.opportunity_id
                                == invocation.opportunity_id,
                                EdgeOpportunityEvidenceRecord.evidence_revision
                                > invocation.evidence_revision,
                            )
                        )
                    )
                )
                invocation.state = INVOCATION_FINAL
                invocation.finalized_at = now
                invocation.final_attempt_id = None
                invocation.final_decision_id = None
                invocation.updated_at = now
                if superseded:
                    invocation.final_status = FINAL_STATUS_STALE_DECISION
                    invocation.final_reason_code = REASON_EVIDENCE_SUPERSEDED_BEFORE_PROVIDER
                elif now >= invocation.decision_deadline_at:
                    invocation.final_status = FINAL_STATUS_STALE_DECISION
                    invocation.final_reason_code = REASON_DEADLINE_EXPIRED_BEFORE_PROVIDER
                else:
                    invocation.final_status = FINAL_STATUS_CAPACITY_BLOCKED
                    invocation.final_reason_code = REASON_ADVISORY_DB_CAPACITY_UNAVAILABLE
                return True
        except (AdvisoryFenceError, SQLAlchemyError):
            return False

    async def terminalize_queue_rejection(self, ref: AdvisoryWorkRef) -> bool:
        """Persist a queue-full terminal only through bounded Advisory capacity A."""

        try:
            async with self._fence.terminal_write_transaction() as session:
                invocation_target = await session.scalar(
                    select(AdvisoryDecisionInvocationRecord).where(
                        AdvisoryDecisionInvocationRecord.decision_invocation_id
                        == ref.decision_invocation_id
                    )
                )
                if invocation_target is None:
                    return False
                evidence = await session.scalar(
                    select(EdgeOpportunityEvidenceRecord)
                    .where(EdgeOpportunityEvidenceRecord.evidence_id == invocation_target.evidence_id)
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
                    or invocation.evidence_hash != evidence.evidence_hash
                    or invocation.state == INVOCATION_FINAL
                ):
                    return False
                finalized_at = await session.scalar(select(func.clock_timestamp()))
                if not isinstance(finalized_at, datetime):
                    raise TypeError("PostgreSQL finalizer clock unavailable")
                superseded = bool(
                    await session.scalar(
                        select(
                            exists().where(
                                EdgeOpportunityEvidenceRecord.opportunity_id
                                == invocation.opportunity_id,
                                EdgeOpportunityEvidenceRecord.evidence_revision
                                > invocation.evidence_revision,
                            )
                        )
                    )
                )
                invocation.state = INVOCATION_FINAL
                invocation.finalized_at = finalized_at
                invocation.final_attempt_id = None
                invocation.final_decision_id = None
                invocation.updated_at = finalized_at
                if superseded:
                    invocation.final_status = FINAL_STATUS_STALE_DECISION
                    invocation.final_reason_code = REASON_EVIDENCE_SUPERSEDED_BEFORE_PROVIDER
                else:
                    invocation.final_status = FINAL_STATUS_CAPACITY_BLOCKED
                    invocation.final_reason_code = REASON_ADVISORY_QUEUE_REJECTED
                return True
        except (AdvisoryFenceError, SQLAlchemyError):
            return False

    async def abandon(
        self, attempt_id: str, *, capability: LiveAttemptCapability, host_lifetime: str
    ) -> bool:
        """ABANDONED requires an exact current Host cancellation capability."""

        return await self._recover_or_shutdown(
            attempt_id, shutdown=True, retry_permitted=False, live_capability=capability,
            host_lifetime=host_lifetime,
        )

    async def process_lost(self, attempt_id: str, *, recovery: RecoveryInput) -> bool:
        recovery.require_valid()
        return await self._recover_or_shutdown(
            attempt_id, shutdown=False, retry_permitted=None, recovery=recovery
        )

    async def recover_without_started_attempt(
        self, decision_invocation_id: str, *, recovery: RecoveryInput
    ) -> bool:
        """Provider-free recovery of ADMITTED/RETRY_PENDING with no current Attempt.

        Absent an independently provable external terminal this leaves durable
        state untouched.  DISABLED recovery therefore never fabricates a retry
        or an Attempt from historical process memory.
        """

        recovery.require_valid()
        async with self._recovery_transaction() as session:
            target = await session.scalar(
                select(AdvisoryDecisionInvocationRecord).where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id == decision_invocation_id
                )
            )
            if target is None:
                return False
            evidence = await session.scalar(
                select(EdgeOpportunityEvidenceRecord)
                .where(EdgeOpportunityEvidenceRecord.evidence_id == target.evidence_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id == decision_invocation_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                evidence is None
                or invocation is None
                or invocation.state not in (INVOCATION_ADMITTED, INVOCATION_RETRY_PENDING)
                or invocation.evidence_id != evidence.evidence_id
                or invocation.evidence_hash != evidence.evidence_hash
            ):
                return False
            facts = await AdvisoryPredicateEvaluator(recovery.authority).evaluate(
                session, invocation=invocation, evidence=evidence
            )
            external_terminal = _recovery_external_terminal(facts)
            if external_terminal is None:
                return False
            now = await session.scalar(select(func.clock_timestamp()))
            if not isinstance(now, datetime) or not await recovery.capability.admit_owner_session():
                return False
            invocation.state = INVOCATION_FINAL
            invocation.final_status, invocation.final_reason_code = external_terminal
            invocation.finalized_at = now
            invocation.final_attempt_id = None
            invocation.final_decision_id = None
            invocation.updated_at = now
            return True

    async def _recover_or_shutdown(
        self, attempt_id: str, *, shutdown: bool, retry_permitted: bool | None,
        recovery: RecoveryInput | None = None, live_capability: LiveAttemptCapability | None = None,
        host_lifetime: str | None = None,
    ) -> bool:
        async with self._recovery_transaction() as session:
            attempt_target = await session.scalar(
                select(AdvisoryDecisionAttemptRecord).where(
                    AdvisoryDecisionAttemptRecord.attempt_id == attempt_id
                )
            )
            if attempt_target is None:
                return False
            invocation_target = await session.scalar(
                select(AdvisoryDecisionInvocationRecord).where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == attempt_target.decision_invocation_id
                )
            )
            if invocation_target is None:
                return False
            evidence = await session.scalar(
                select(EdgeOpportunityEvidenceRecord)
                .where(EdgeOpportunityEvidenceRecord.evidence_id == invocation_target.evidence_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == invocation_target.decision_invocation_id
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            attempt = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(AdvisoryDecisionAttemptRecord.attempt_id == attempt_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                evidence is None
                or invocation is None
                or attempt is None
                or invocation.evidence_id != evidence.evidence_id
                or invocation.evidence_hash != evidence.evidence_hash
                or attempt.decision_invocation_id != invocation.decision_invocation_id
                or attempt.attempt_state != ATTEMPT_STARTED
                or invocation.state == INVOCATION_FINAL
            ):
                return False
            if shutdown and (
                live_capability is None or host_lifetime is None or not live_capability.matches(
                    host_lifetime=host_lifetime,
                    decision_invocation_id=invocation.decision_invocation_id,
                    attempt_id=attempt.attempt_id,
                )
            ):
                return False
            if recovery is not None:
                facts = await AdvisoryPredicateEvaluator(recovery.authority).evaluate(
                    session, invocation=invocation, evidence=evidence
                )
                external_terminal = _recovery_external_terminal(facts)
                if external_terminal is None:
                    retry_permitted = recovery.retry_policy.allows_retry(
                        attempt_number=attempt.attempt_number
                    )
            else:
                external_terminal = None
            now = await session.scalar(select(func.clock_timestamp()))
            if not isinstance(now, datetime):
                raise TypeError("PostgreSQL recovery clock unavailable")
            # The primary transaction still owns Evidence -> Invocation -> Attempt.
            # No lifecycle field has changed yet.  The Host's dedicated singleton
            # session now provides the sole admission linearization point.
            admitted = (
                await live_capability.admit_owner_session()
                if shutdown and live_capability is not None
                else await recovery.capability.admit_owner_session()
                if recovery is not None
                else False
            )
            if not admitted:
                return False
            if external_terminal is not None:
                attempt.attempt_state = ATTEMPT_PROCESS_LOST
                invocation.state = INVOCATION_FINAL
                invocation.final_status, invocation.final_reason_code = external_terminal
                invocation.finalized_at = now
                invocation.final_attempt_id = None
                invocation.final_decision_id = None
                invocation.updated_at = now
                return True
            if not shutdown and retry_permitted is True:
                attempt.attempt_state = ATTEMPT_PROCESS_LOST
                invocation.state = INVOCATION_RETRY_PENDING
                invocation.updated_at = now
                return True
            attempt.attempt_state = ATTEMPT_ABANDONED if shutdown else ATTEMPT_PROCESS_LOST
            invocation.state = INVOCATION_FINAL
            invocation.final_status = FINAL_STATUS_INVALID_SCHEMA
            invocation.final_reason_code = REASON_SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT if shutdown else REASON_RETRY_EXHAUSTED
            invocation.finalized_at = now
            invocation.final_attempt_id = attempt.attempt_id
            invocation.final_decision_id = None
            invocation.updated_at = now
            return True


class AdvisoryWorker:
    """One bounded dequeue; DB resources are absent while awaiting its fake provider."""

    def __init__(self, starter: AdvisoryAttemptStarter, finalizer: AdvisoryFinalizer, provider: AdvisoryProvider) -> None:
        self._starter = starter
        self._finalizer = finalizer
        self._provider = provider

    async def consume(self, ref: AdvisoryWorkRef) -> AdvisoryWorkRef | None:
        try:
            attempt_id = await self._starter.start(ref)
        except AdvisoryFenceError:
            # One cooperative turn is bounded (it is not a DB wait) and lets an
            # already-completing checkout publish its authoritative checkin before
            # the separate terminal-write lease is attempted.
            await asyncio.sleep(0)
            await self._finalizer.terminalize_db_capacity_unavailable(ref)
            return None
        if attempt_id is None:
            return None
        result = await self._provider.decide(ref, attempt_id)
        return await self._finalizer.finalize(attempt_id, result)


class AdvisoryRecovery:
    """New-owner recovery reads durable STARTED facts only, never process memory."""

    def __init__(
        self,
        fence: AdvisoryDbFence | None,
        finalizer: AdvisoryFinalizer,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._fence = fence
        self._finalizer = finalizer
        self._session_factory = session_factory

    @asynccontextmanager
    async def _scan_transaction(self):
        if self._fence is not None:
            async with self._fence.transaction() as session:
                yield session
            return
        if self._session_factory is None:
            raise AdvisoryFenceError("advisory recovery scan is not configured")
        async with self._session_factory() as session, session.begin():
            yield session

    async def recover_process_lost(
        self,
        *,
        recovery: RecoveryInput,
        reoffer: Callable[[AdvisoryWorkRef], Awaitable[bool]] | None = None,
    ) -> int:
        async with self._scan_transaction() as session:
            rows = list(
                await session.execute(
                    select(
                        AdvisoryDecisionAttemptRecord.attempt_id,
                        AdvisoryDecisionInvocationRecord.decision_invocation_id,
                        AdvisoryDecisionInvocationRecord.decision_deadline_at,
                    )
                    .join(
                        AdvisoryDecisionInvocationRecord,
                        AdvisoryDecisionInvocationRecord.decision_invocation_id
                        == AdvisoryDecisionAttemptRecord.decision_invocation_id,
                    )
                    .where(
                        AdvisoryDecisionAttemptRecord.attempt_state == ATTEMPT_STARTED,
                        AdvisoryDecisionInvocationRecord.state != INVOCATION_FINAL,
                    )
                )
            )
        recovered = 0
        for attempt_id, invocation_id, deadline_at in rows:
            if await self._finalizer.process_lost(attempt_id, recovery=recovery):
                recovered += 1
                if reoffer is not None:
                    ref = AdvisoryWorkRef(invocation_id, deadline_at)
                    if not await reoffer(ref):
                        await self._finalizer.terminalize_queue_rejection(ref)
        return recovered

    async def recover_pending(self, *, recovery: RecoveryInput) -> int:
        """Classify only independently terminal ADMITTED/RETRY_PENDING rows."""

        async with self._scan_transaction() as session:
            invocation_ids = list(
                await session.scalars(
                    select(AdvisoryDecisionInvocationRecord.decision_invocation_id).where(
                        AdvisoryDecisionInvocationRecord.state.in_(
                            (INVOCATION_ADMITTED, INVOCATION_RETRY_PENDING)
                        )
                    )
                )
            )
        return sum(
            [
                await self._finalizer.recover_without_started_attempt(
                    invocation_id, recovery=recovery
                )
                for invocation_id in invocation_ids
            ]
        )


__all__ = [
    "AdvisoryFinalizer",
    "AdvisoryProvider",
    "AdvisoryRecovery",
    "AdvisoryWorker",
    "FakeProviderResult",
]
