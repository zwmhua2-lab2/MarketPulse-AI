"""SE-02B: runtime capture of a G2 opportunity into immutable Edge evidence.

SE-02B has two responsibilities and nothing else:

* **A. G2 opportunity capture** -- when a G2 ``SETUP`` transition qualifies, one
  immutable opportunity evidence revision is persisted *inside the very
  transaction* that made the G2 facts durable (see
  ``marketpulse.g2.repository.PostgresG2Repository``);
* **B. attribution linkage** -- see ``marketpulse.edge.attribution``.

This module owns part A only. It contains no second Edge writer: it builds an
accepted ``EvidenceRevision`` contract object and hands it to
``marketpulse.edge.repository.append_evidence_revision``, so every accepted
SE-02A identity / hash / revision / idempotency rule is reused unchanged.

Deliberately absent (SE-02C / SE-02D): continuous quote-path capture, forward
outcome calculation, MFE, MAE, forward returns, expectancy, family aggregation,
KEEP / DOWNWEIGHT / KILL.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.g2.models import (
    DirectionBias,
    EventType,
    FeatureSnapshot,
    MarketEvent,
    SignalTimelineEvent,
    StateApplyResult,
    StateTransition,
    StrategyCandidate,
    SymbolState,
    SymbolStateRecord,
)

from .models import (
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ReferenceDataStatus,
    build_evidence_revision,
    build_opportunity_identity,
)
from .repository import append_evidence_revision

# The single strategy / family identity licensed by the accepted SE-02 design.
OPPORTUNITY_FAMILY_STRATEGY_ID = "BREAKOUT_RETEST"

# Runtime capture always writes the initial revision of the logical opportunity.
RUNTIME_CAPTURE_REVISION = 1

# Contracts version of the captured payload. It is frozen: changing the payload
# shape of a runtime capture changes the stored evidence hash, so a new shape
# needs a new tag rather than a silent in-place edit.
RUNTIME_CAPTURE_PAYLOAD_VERSION = "se02b-runtime-capture-v1"

# Default reference-quote age above which a supplied quote is not usable. It
# mirrors the accepted G3 execution freshness window so the Edge layer does not
# invent a second, incompatible market-data policy.
DEFAULT_REFERENCE_MAX_AGE = timedelta(seconds=5)


class ReferenceQuote(BaseModel):
    """Reference L1 quote facts supplied by the caller.

    SE-02B does not capture a continuous quote path (that is SE-02C). The caller
    owns the live market state and passes the reference quote it already holds;
    G2 itself owns no bid/ask.

    Reference data can never decide whether an opportunity exists: an unusable
    quote is classified as ``REFERENCE_STALE`` and the sample is still
    persisted. Only a structurally malformed caller input (a naive timestamp)
    raises, and that is a caller contract violation rather than a market-data
    availability event.
    """

    model_config = ConfigDict(frozen=True)

    bid: float
    ask: float
    received_at: datetime
    tradable: bool = True

    @field_validator("received_at")
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reference quote received_at must be timezone-aware")
        return value

    def _is_usable(self, *, at: datetime, max_age: timedelta) -> bool:
        """A quote is usable only when it is tradable, well-formed and fresh."""

        if not self.tradable:
            return False
        if not math.isfinite(self.bid) or not math.isfinite(self.ask):
            return False
        if self.bid <= 0 or self.ask <= 0 or self.bid > self.ask:
            return False
        return at - self.received_at <= max_age


class EdgeCaptureContext(BaseModel):
    """Everything the G2 persistence path needs that G2 itself does not own.

    This is the smallest existing-compatible injection boundary: provenance that
    only the caller can know, plus the optional reference quote. Provenance
    identifiers are caller supplied and stable -- they are never generated per
    call, so re-capturing the same facts is idempotent instead of producing a new
    sample.
    """

    model_config = ConfigDict(frozen=True)

    source_type: EvidenceSource
    source_identity: str
    source_manifest_id: str
    reference_quote: ReferenceQuote | None = None
    reference_max_age: timedelta = DEFAULT_REFERENCE_MAX_AGE

    @field_validator("source_identity", "source_manifest_id")
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("capture provenance identifiers must be non-empty")
        return value

    @field_validator("reference_max_age")
    def _positive_window(cls, value: timedelta) -> timedelta:
        if value <= timedelta(0):
            raise ValueError("reference_max_age must be positive")
        return value

    def classify_reference(self, *, at: datetime) -> tuple[ReferenceDataStatus, ReferenceQuote | None]:
        """Return the frozen reference-data status plus the quote to persist.

        The returned quote is ``None`` whenever the status is not ``OK`` so a
        missing or unusable metric can only ever be written as ``NULL`` -- never
        as a zero placeholder and never as a fabricated quote.
        """

        if self.reference_quote is None:
            return ReferenceDataStatus.REFERENCE_MISSING, None
        if not self.reference_quote._is_usable(at=at, max_age=self.reference_max_age):
            return ReferenceDataStatus.REFERENCE_STALE, None
        return ReferenceDataStatus.OK, self.reference_quote


def qualifies(
    *,
    event: MarketEvent,
    timeline: SignalTimelineEvent,
    state: SymbolStateRecord,
    transition: StateTransition,
    candidates: list[StrategyCandidate],
    observation: FeatureSnapshot,
) -> StrategyCandidate | None:
    """Return the qualifying ``BREAKOUT_RETEST`` candidate, or ``None``.

    A candidate becomes a formal opportunity only when *every* required G2 fact
    agrees (task §4). The check is total and side-effect free, so a reviewer can
    enumerate the negative matrix directly.

    Reference-data availability, AI, Risk, Trade and BBO are deliberately not
    admission conditions: they can never make an opportunity disappear.
    """

    if transition.result is not StateApplyResult.APPLIED:
        return None
    if transition.to_state is not SymbolState.SETUP:
        return None
    if event.event_type is not EventType.BREAKOUT:
        return None
    if state.state is not SymbolState.SETUP:
        return None
    if state.watch_expires_at is None:
        # The SETUP expiry is part of the immutable evidence; a SETUP without a
        # durable expiry is not a well-formed G2 fact.
        return None
    for candidate in candidates:
        if _candidate_agrees(
            candidate=candidate,
            event=event,
            timeline=timeline,
            state=state,
            transition=transition,
            observation=observation,
        ):
            return candidate
    return None


def _candidate_agrees(
    *,
    candidate: StrategyCandidate,
    event: MarketEvent,
    timeline: SignalTimelineEvent,
    state: SymbolStateRecord,
    transition: StateTransition,
    observation: FeatureSnapshot,
) -> bool:
    """Applicability, direction, family and every shared identity / version must agree."""

    if candidate.strategy_id != OPPORTUNITY_FAMILY_STRATEGY_ID:
        return False
    if not candidate.strategy_version:
        return False
    if not candidate.applicable:
        return False
    if candidate.direction_bias is not DirectionBias.BULLISH:
        return False
    # Candidate / Event / Transition agreement.
    if candidate.event_id != event.event_id:
        return False
    if candidate.instrument_id != event.instrument_id:
        return False
    if candidate.state_version != transition.state_version:
        return False
    if candidate.config_version != event.config_version:
        return False
    if transition.event_id != event.event_id:
        return False
    if transition.instrument_id != event.instrument_id:
        return False
    if transition.symbol != event.symbol:
        return False
    if state.instrument_id != event.instrument_id:
        return False
    if state.state_version != transition.state_version:
        return False
    # Timeline agreement.
    if timeline.event_id != event.event_id:
        return False
    if timeline.instrument_id != event.instrument_id:
        return False
    if timeline.state_version != state.state_version:
        return False
    # Feature snapshot agreement.
    if observation.instrument_id != event.instrument_id:
        return False
    if observation.symbol != event.symbol:
        return False
    return observation.market_type == event.market_type


def build_opportunity_evidence(
    *,
    event: MarketEvent,
    timeline: SignalTimelineEvent,
    state: SymbolStateRecord,
    transition: StateTransition,
    candidate: StrategyCandidate,
    observation: FeatureSnapshot,
    context: EdgeCaptureContext,
) -> EvidenceRevision:
    """Build the immutable, self-sufficient evidence revision for one capture.

    The payload is intentionally redundant: it stores the complete triggering
    event, transition, timeline entry, resulting SETUP state, candidate and
    feature snapshot, so the question "what exactly did the system know at the
    instant this opportunity became a durable SETUP?" can be answered from the
    stored evidence alone, without reading mutable current runtime state.
    """

    opportunity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=candidate.strategy_version,
        instrument_id=candidate.instrument_id,
        market_type=event.market_type,
        candidate_id=candidate.candidate_id,
    )
    at = event.received_time
    reference_status, reference_quote = context.classify_reference(at=at)
    expires_at = state.watch_expires_at
    assert expires_at is not None  # guaranteed by ``qualifies``

    evidence_payload: dict[str, Any] = {
        "capture": {
            "payload_version": RUNTIME_CAPTURE_PAYLOAD_VERSION,
            "evidence_revision": RUNTIME_CAPTURE_REVISION,
            "strategy_id": candidate.strategy_id,
        },
        "opportunity": {
            "opportunity_id": opportunity.opportunity_id,
            "family_id": opportunity.family_id.value,
            "family_version": opportunity.family_version,
            "instrument_id": opportunity.instrument_id,
            "market_type": opportunity.market_type.value,
            "candidate_id": opportunity.candidate_id,
        },
        "candidate": candidate.model_dump(mode="json"),
        "triggering_event": event.model_dump(mode="json"),
        "transition": transition.model_dump(mode="json"),
        "timeline": timeline.model_dump(mode="json"),
        "resulting_state": state.model_dump(mode="json"),
        "setup_expires_at": expires_at.isoformat(),
        "entry_context": candidate.entry_context,
        "supporting_evidence": list(candidate.supporting_evidence),
        "contradicting_evidence": list(candidate.contradicting_evidence),
        "invalidation_hint": candidate.invalidation_hint,
        "expected_behavior": candidate.expected_behavior,
        "versions": {
            "strategy_version": candidate.strategy_version,
            "state_version": state.state_version,
            "config_version": event.config_version,
            "transition_state_version": transition.state_version,
            "timeline_state_version": timeline.state_version,
        },
        "provenance": {
            "source_type": context.source_type.value,
            "source_identity": context.source_identity,
            "source_manifest_id": context.source_manifest_id,
        },
        "reference_data": {
            "status": reference_status.value,
            "bid": reference_quote.bid if reference_quote is not None else None,
            "ask": reference_quote.ask if reference_quote is not None else None,
            "received_at": (
                reference_quote.received_at.isoformat() if reference_quote is not None else None
            ),
        },
    }
    return build_evidence_revision(
        opportunity=opportunity,
        evidence_revision=RUNTIME_CAPTURE_REVISION,
        detected_at=event.event_time,
        evidence_at=event.received_time,
        expires_at=expires_at,
        source_type=context.source_type,
        source_identity=context.source_identity,
        source_manifest_id=context.source_manifest_id,
        reference_data_status=reference_status,
        reference_bid=reference_quote.bid if reference_quote is not None else None,
        reference_ask=reference_quote.ask if reference_quote is not None else None,
        reference_received_at=(
            reference_quote.received_at if reference_quote is not None else None
        ),
        evidence_payload=evidence_payload,
        feature_snapshot_payload=observation.model_dump(mode="json"),
        created_at=event.received_time,
    )


async def capture_opportunity(
    session: AsyncSession,
    *,
    event: MarketEvent,
    timeline: SignalTimelineEvent,
    state: SymbolStateRecord,
    transition: StateTransition,
    candidates: list[StrategyCandidate],
    observation: FeatureSnapshot,
    context: EdgeCaptureContext,
) -> str | None:
    """Persist the qualifying opportunity through the accepted append-only writer.

    Returns ``None`` when the G2 facts do not qualify, otherwise the accepted
    writer's ``INSERTED`` / ``IDEMPOTENT`` result.

    The caller owns the transaction. Any Edge integrity failure propagates
    unchanged so the surrounding G2 transaction fails closed: evidence is never
    silently skipped, and G2 truth never commits without its evidence.
    """

    candidate = qualifies(
        event=event,
        timeline=timeline,
        state=state,
        transition=transition,
        candidates=candidates,
        observation=observation,
    )
    if candidate is None:
        return None
    revision = build_opportunity_evidence(
        event=event,
        timeline=timeline,
        state=state,
        transition=transition,
        candidate=candidate,
        observation=observation,
        context=context,
    )
    return await append_evidence_revision(session, revision)
