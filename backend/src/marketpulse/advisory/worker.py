"""Bounded, fake-provider-only Advisory worker and durable finalization primitives."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import exists, func, select
from sqlalchemy.exc import SQLAlchemyError

from marketpulse.db.models import (
    AdvisoryDecisionAttemptRecord,
    AdvisoryDecisionInvocationRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.g2.models import AdvisoryWorkRef

from .attempts import AdvisoryAttemptStarter
from .fence import AdvisoryDbFence, AdvisoryFenceError
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


class AdvisoryFinalizer:
    """Winner-fenced Attempt completion; it never touches economic authorities."""

    def __init__(self, fence: AdvisoryDbFence) -> None:
        self._fence = fence

    async def finalize(self, attempt_id: str, result: FakeProviderResult) -> AdvisoryWorkRef | None:
        async with self._fence.transaction() as session:
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
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == invocation_target.decision_invocation_id
                )
                .with_for_update()
            )
            attempt = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(AdvisoryDecisionAttemptRecord.attempt_id == attempt_id)
                .with_for_update()
            )
            if (
                evidence is None
                or invocation is None
                or attempt is None
                or invocation.evidence_id != evidence.evidence_id
                or invocation.evidence_hash != evidence.evidence_hash
                or attempt.decision_invocation_id != invocation.decision_invocation_id
            ):
                return None
            if invocation.state == INVOCATION_FINAL:
                if invocation.final_attempt_id != attempt.attempt_id:
                    attempt.attempt_state = ATTEMPT_LATE_RESULT
                return None
            now = await session.scalar(select(func.clock_timestamp()))
            if not isinstance(now, datetime):
                raise TypeError("PostgreSQL finalizer clock unavailable")
            attempt.attempt_state = ATTEMPT_COMPLETED
            attempt.response_received_at = now
            attempt.finished_at = now
            attempt.provider_outcome = "FAKE_VALID" if result.valid else "FAKE_INVALID"
            attempt.normalized_status = FINAL_STATUS_VALID if result.valid else FINAL_STATUS_INVALID_SCHEMA
            attempt.redacted_response_envelope = result.payload or {}
            superseded = evidence is None or bool(
                await session.scalar(
                    select(
                        exists().where(
                            EdgeOpportunityEvidenceRecord.opportunity_id == invocation.opportunity_id,
                            EdgeOpportunityEvidenceRecord.evidence_revision > invocation.evidence_revision,
                        )
                    )
                )
            )
            if result.retry and not superseded:
                invocation.state = INVOCATION_RETRY_PENDING
                invocation.updated_at = now
                return AdvisoryWorkRef(invocation.decision_invocation_id, invocation.decision_deadline_at)
            invocation.state = INVOCATION_FINAL
            invocation.finalized_at = now
            invocation.final_attempt_id = attempt.attempt_id
            invocation.final_decision_id = None
            invocation.updated_at = now
            if superseded:
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
                )
                invocation = await session.scalar(
                    select(AdvisoryDecisionInvocationRecord)
                    .where(
                        AdvisoryDecisionInvocationRecord.decision_invocation_id
                        == ref.decision_invocation_id
                    )
                    .with_for_update()
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
                )
                invocation = await session.scalar(
                    select(AdvisoryDecisionInvocationRecord)
                    .where(
                        AdvisoryDecisionInvocationRecord.decision_invocation_id
                        == ref.decision_invocation_id
                    )
                    .with_for_update()
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

    async def abandon(self, attempt_id: str, *, cancellation_observed: bool) -> bool:
        """Durably classify Host shutdown only after its cancellation was observed."""

        if not cancellation_observed:
            return False
        return await self._recover_or_shutdown(attempt_id, shutdown=True, retry_allowed=False)

    async def process_lost(self, attempt_id: str, *, retry_allowed: bool) -> bool:
        return await self._recover_or_shutdown(attempt_id, shutdown=False, retry_allowed=retry_allowed)

    async def _recover_or_shutdown(self, attempt_id: str, *, shutdown: bool, retry_allowed: bool) -> bool:
        async with self._fence.transaction() as session:
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
            )
            invocation = await session.scalar(
                select(AdvisoryDecisionInvocationRecord)
                .where(
                    AdvisoryDecisionInvocationRecord.decision_invocation_id
                    == invocation_target.decision_invocation_id
                )
                .with_for_update()
            )
            attempt = await session.scalar(
                select(AdvisoryDecisionAttemptRecord)
                .where(AdvisoryDecisionAttemptRecord.attempt_id == attempt_id)
                .with_for_update()
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
            now = await session.scalar(select(func.clock_timestamp()))
            if not isinstance(now, datetime):
                raise TypeError("PostgreSQL recovery clock unavailable")
            if not shutdown and retry_allowed:
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

    def __init__(self, fence: AdvisoryDbFence, finalizer: AdvisoryFinalizer) -> None:
        self._fence = fence
        self._finalizer = finalizer

    async def recover_process_lost(
        self,
        *,
        retry_allowed: bool,
        reoffer: Callable[[AdvisoryWorkRef], Awaitable[bool]] | None = None,
    ) -> int:
        async with self._fence.transaction() as session:
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
            if await self._finalizer.process_lost(attempt_id, retry_allowed=retry_allowed):
                recovered += 1
                if retry_allowed and reoffer is not None:
                    ref = AdvisoryWorkRef(invocation_id, deadline_at)
                    if not await reoffer(ref):
                        await self._finalizer.terminalize_queue_rejection(ref)
        return recovered


__all__ = [
    "AdvisoryFinalizer",
    "AdvisoryProvider",
    "AdvisoryRecovery",
    "AdvisoryWorker",
    "FakeProviderResult",
]
