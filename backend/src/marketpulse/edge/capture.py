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

Two causal rules are frozen here (SE-02B-FIX-01):

* the reference quote is a **per-capture** fact. The caller supplies it through a
  bounded accessor on every persist, so one long-lived quote can never be re-used
  as if it were still current for a later opportunity;
* the evidence horizon is anchored on the moment the opportunity became knowable
  (``qualifying_candidate.created_at``), and a reference quote is ``OK`` only when
  ``0 <= evidence_at - reference_received_at <= reference_max_age``. A quote that
  was received *after* the evidence anchor is lookahead, not freshness.

Deliberately absent (SE-02C / SE-02D): continuous quote-path capture, forward
outcome calculation, MFE, MAE, forward returns, expectancy, family aggregation,
KEEP / DOWNWEIGHT / KILL.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
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
from marketpulse.market_data.models import DataQuality, MarketType

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
# needs a new tag rather than a silent in-place edit. ``v2`` records the received
# reference quote's own identity / quality facts next to the frozen reference
# metrics (SE-02B-FIX-01 P0-1).
RUNTIME_CAPTURE_PAYLOAD_VERSION = "se02b-runtime-capture-v2"

# Default reference-quote age above which a supplied quote is not usable. It
# mirrors the accepted G3 execution freshness window so the Edge layer does not
# invent a second, incompatible market-data policy.
DEFAULT_REFERENCE_MAX_AGE = timedelta(seconds=5)


class ReferenceQuote(BaseModel):
    """Reference L1 quote facts supplied by the caller for exactly one capture.

    SE-02B does not capture a continuous quote path (that is SE-02C). The caller
    owns the live market state and passes the reference quote it already holds;
    G2 itself owns no bid/ask.

    The quote carries its own market identity and quality facts so an unusable
    quote can never be mistaken for this opportunity's reference: a quote for
    another instrument or another market type is not usable evidence here, and a
    quote received after the evidence anchor is future data, not freshness.

    Reference data can never decide whether an opportunity exists: an unusable
    quote is classified as ``REFERENCE_STALE`` and the sample is still
    persisted. Only a structurally malformed caller input (a naive timestamp)
    raises, and that is a caller contract violation rather than a market-data
    availability event.
    """

    model_config = ConfigDict(frozen=True)

    instrument_id: str = Field(min_length=1)
    market_type: MarketType
    bid: float
    ask: float
    received_at: datetime
    data_quality: DataQuality
    tradable: bool = True

    @field_validator("received_at")
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reference quote received_at must be timezone-aware")
        return value

    def _is_well_formed(self) -> bool:
        """Usable shape only: tradable, finite and positively ordered."""

        if not self.tradable:
            return False
        if not math.isfinite(self.bid) or not math.isfinite(self.ask):
            return False
        return self.bid > 0 and self.ask > 0 and self.bid <= self.ask

    def _is_causally_available(self, *, at: datetime, max_age: timedelta) -> bool:
        """``0 <= at - received_at <= max_age`` -- no future data, no stale data."""

        age = at - self.received_at
        return timedelta(0) <= age <= max_age

    def matches(self, *, instrument_id: str, market_type: MarketType) -> bool:
        """Does this quote belong to the opportunity's exact market identity?"""

        return self.instrument_id == instrument_id and self.market_type == market_type


class EdgeCaptureContext(BaseModel):
    """Everything the G2 persistence path needs that G2 itself does not own.

    This is the smallest existing-compatible injection boundary: provenance that
    only the caller can know, plus the reference-data freshness window.
    Provenance identifiers are caller supplied and stable -- they are never
    generated per call, so re-capturing the same facts is idempotent instead of
    producing a new sample.

    The reference quote is deliberately **not** part of this context: a context is
    constructed once per run, while a quote is only meaningful for the capture it
    was observed at. The caller supplies the current quote per persist through
    ``PostgresG2Repository(reference_quote_for=...)``.
    """

    model_config = ConfigDict(frozen=True)

    source_type: EvidenceSource
    source_identity: str
    source_manifest_id: str
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

    def classify_reference(
        self,
        *,
        quote: ReferenceQuote | None,
        instrument_id: str,
        market_type: MarketType,
        at: datetime,
    ) -> tuple[ReferenceDataStatus, ReferenceQuote | None]:
        """Return the frozen reference-data status plus the quote to persist.

        The returned quote is ``None`` whenever the status is not ``OK`` so a
        missing or unusable metric can only ever be written as ``NULL`` -- never
        as a zero placeholder and never as a fabricated quote. A quote for
        another instrument or market type is refused here, so one opportunity can
        never be evidenced by another symbol's BBO.
        """

        if quote is None:
            return ReferenceDataStatus.REFERENCE_MISSING, None
        if not quote.matches(instrument_id=instrument_id, market_type=market_type):
            return ReferenceDataStatus.REFERENCE_STALE, None
        if not quote._is_well_formed():
            return ReferenceDataStatus.REFERENCE_STALE, None
        if not quote._is_causally_available(at=at, max_age=self.reference_max_age):
            return ReferenceDataStatus.REFERENCE_STALE, None
        return ReferenceDataStatus.OK, quote


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
    if candidate.symbol != event.symbol:
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
    if state.symbol != event.symbol:
        return False
    if state.state_version != transition.state_version:
        return False
    # Timeline agreement. The timeline entry is the durable record of *this*
    # signal, so its symbol, signal type and config version must describe the same
    # facts as the event it was derived from.
    if timeline.event_id != event.event_id:
        return False
    if timeline.instrument_id != event.instrument_id:
        return False
    if timeline.symbol != event.symbol:
        return False
    if timeline.signal_type is not event.event_type:
        return False
    if timeline.config_version != event.config_version:
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
    reference_quote: ReferenceQuote | None = None,
) -> EvidenceRevision:
    """Build the immutable, self-sufficient evidence revision for one capture.

    The payload is intentionally redundant: it stores the complete triggering
    event, transition, timeline entry, resulting SETUP state, candidate and
    feature snapshot, so the question "what exactly did the system know at the
    instant this opportunity became a durable SETUP?" can be answered from the
    stored evidence alone, without reading mutable current runtime state.

    Causal anchors (frozen):

    * ``detected_at``  -- ``event.event_time``: when the triggering market fact
      happened;
    * ``evidence_at``  -- ``candidate.created_at``: when the qualifying candidate
      existed, i.e. the earliest moment the system could know this opportunity.
      Reference-quote freshness is measured against *this* anchor, and every
      forward horizon (SE-02C) starts from it;
    * ``created_at``   -- ``event.received_time``: the deterministic capture
      record timestamp of the accepted SE-02A contract (the recovery point of the
      triggering event), kept separate from ``evidence_at`` rather than folded
      into it.
    """

    opportunity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=candidate.strategy_version,
        instrument_id=candidate.instrument_id,
        market_type=event.market_type,
        candidate_id=candidate.candidate_id,
    )
    evidence_at = candidate.created_at
    reference_status, usable_quote = context.classify_reference(
        quote=reference_quote,
        instrument_id=candidate.instrument_id,
        market_type=event.market_type,
        at=evidence_at,
    )
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
        # ``reference_data`` keeps the frozen reference-metric contract: the quote
        # metrics are present only for ``OK`` and are NULL (never 0) otherwise.
        # The supplied quote's own identity / quality facts are recorded next to
        # them so a refused quote stays auditable ("a quote existed, and this is
        # what it was") without ever being promoted to ``OK`` evidence.
        "reference_data": {
            "status": reference_status.value,
            "bid": usable_quote.bid if usable_quote is not None else None,
            "ask": usable_quote.ask if usable_quote is not None else None,
            "received_at": (
                usable_quote.received_at.isoformat() if usable_quote is not None else None
            ),
            "instrument_id": (
                reference_quote.instrument_id if reference_quote is not None else None
            ),
            "market_type": (
                reference_quote.market_type.value if reference_quote is not None else None
            ),
            "data_quality": (
                reference_quote.data_quality.value if reference_quote is not None else None
            ),
            "tradable": reference_quote.tradable if reference_quote is not None else None,
        },
    }
    return build_evidence_revision(
        opportunity=opportunity,
        evidence_revision=RUNTIME_CAPTURE_REVISION,
        detected_at=event.event_time,
        evidence_at=evidence_at,
        expires_at=expires_at,
        source_type=context.source_type,
        source_identity=context.source_identity,
        source_manifest_id=context.source_manifest_id,
        reference_data_status=reference_status,
        reference_bid=usable_quote.bid if usable_quote is not None else None,
        reference_ask=usable_quote.ask if usable_quote is not None else None,
        reference_received_at=(
            usable_quote.received_at if usable_quote is not None else None
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
    reference_quote: ReferenceQuote | None = None,
) -> str | None:
    """Persist the qualifying opportunity through the accepted append-only writer.

    Returns ``None`` when the G2 facts do not qualify, otherwise the accepted
    writer's ``INSERTED`` / ``IDEMPOTENT`` result.

    ``reference_quote`` is the quote the caller holds *for this capture*: it is
    never cached inside the context, so a later opportunity can never be evidenced
    by an earlier market observation.

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
        reference_quote=reference_quote,
    )
    return await append_evidence_revision(session, revision)
