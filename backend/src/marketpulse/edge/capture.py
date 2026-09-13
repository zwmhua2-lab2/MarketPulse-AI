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

One reference-data rule is frozen here (SE-02B-FIX-02):

* ``OK`` is the conjunction of every usability condition -- identity, **feed
  quality**, tradability, finite and positively ordered prices, and causal
  freshness (see :meth:`EdgeCaptureContext.classify_reference`). Anything else is
  ``REFERENCE_STALE`` and the opportunity is still captured, with the accepted
  reference metrics left NULL;
* a refused quote is still evidence *of what was supplied*: the immutable payload
  keeps the caller's raw ``supplied_quote`` next to ``accepted_reference``, so a
  refusal stays auditable without ever being promoted to ``OK``.

Deliberately absent (SE-02C / SE-02D): continuous quote-path capture, forward
outcome calculation, MFE, MAE, forward returns, expectancy, family aggregation,
KEEP / DOWNWEIGHT / KILL.

One live-ingress admission rule is frozen here (SE-ARCH-FIX-01 R2):

* a Forward admission proof is minted **only** by the live-ingress boundary
  (:class:`ForwardAdmissionAuthority`, held by ``ScannerPipeline``) for the exact
  ``MarketEvent`` that the current ``ingest(NormalizedMarketEvent)`` produced, and
  only when that input's causal source time
  (``NormalizedMarketEvent.event_time``) is at or after the live session start;
* the durable repository holds :class:`ForwardAdmissionVerifier` instead, so it
  can *verify* a proof but has no API to mint one for an arbitrary historical
  event. A fresh process that redelivers an older input therefore fails closed:
  coverage is lost instead of a stale input being republished as a new Forward
  sample under a new clock or a newer BBO.
"""

from __future__ import annotations

import hmac
import math
import secrets
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.clock import Clock
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
from marketpulse.market_data.models import DataQuality, MarketType, NormalizedMarketEvent

from .hashing import (
    CAPTURE_ANCHOR_HASH_DOMAIN,
    canonical_bytes,
    capture_anchor_hash,
    capture_anchor_orphan_hash,
    forward_admission_event_hash,
    forward_admission_proof_hash,
    forward_admission_source_hash,
)
from .models import (
    BboObservation,
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ReferenceDataStatus,
    build_bbo_observation,
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
#
# * ``v1`` -- original shape;
# * ``v2`` -- the received reference quote's own identity / quality facts were
#   recorded next to the frozen reference metrics (SE-02B-FIX-01 P0-1), but a
#   *refused* quote kept only its identity / quality fields: its raw ``bid`` /
#   ``ask`` / ``received_at`` were dropped;
# * ``v3`` -- ``reference_data`` separates ``supplied_quote`` (the caller's raw
#   input, kept verbatim even when refused) from ``accepted_reference`` (the
#   metrics actually accepted as this opportunity's reference)
#   (SE-02B-FIX-02 P0-1). ``v2`` is therefore not a valid tag for this shape.
RUNTIME_CAPTURE_PAYLOAD_VERSION = "se02b-runtime-capture-v3"

CAPTURE_ANCHOR_PAYLOAD_VERSION = "se-arch-fix-01-anchor-v1"
CAPTURE_ANCHOR_HASH_VERSION = CAPTURE_ANCHOR_HASH_DOMAIN
FORWARD_ADMISSION_PROOF_VERSION = "se-arch-fix-01-forward-admission-v2"
CAPTURE_ANCHOR_ORPHAN_VERSION = "se-arch-fix-01-orphan-v1"
CAPTURE_ANCHOR_ORPHAN_HASH_VERSION = "se02-capture-anchor-orphan-hash-v1"

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
    another instrument or another market type is not usable evidence here, a quote
    the feed itself flagged ``STALE`` / ``UNAVAILABLE`` is not fresh evidence even
    when its prices look well-formed, and a quote received after the evidence
    anchor is future data, not freshness.

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
    # These are intentionally optional at the SE-02B boundary: old callers can
    # still supply an auditable, refused quote. A usable quote becomes a durable
    # BBO observation only when the caller can prove these observation facts.
    source_event_time: datetime | None = None
    source: str | None = None
    source_sequence: int | None = None

    @field_validator("received_at")
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reference quote received_at must be timezone-aware")
        return value

    def _is_usable(self) -> bool:
        """The frozen usability rule: fresh, tradable, finite, positively ordered.

        ``data_quality`` is part of usability, not decoration: a quote the upstream
        feed itself marked ``STALE`` or ``UNAVAILABLE`` is not a reference this
        opportunity may be evidenced by, even when its prices happen to look
        well-formed. Quality can only *refuse* a quote -- it never creates one.
        """

        if self.data_quality is not DataQuality.FRESH:
            return False
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

    def bbo_observation(self, *, recorded_at: datetime) -> BboObservation | None:
        """Return the exact normalized BBO fact, never a synthesized one."""

        if self.source_event_time is None or not self.source:
            return None
        return build_bbo_observation(
            instrument_id=self.instrument_id,
            market_type=self.market_type,
            bid=self.bid,
            ask=self.ask,
            available_at=self.received_at,
            source_event_time=self.source_event_time,
            received_at=self.received_at,
            data_quality=self.data_quality,
            tradable=self.tradable,
            source=self.source,
            source_sequence=self.source_sequence,
            created_at=recorded_at,
        )


def _json_safe_price(value: float) -> float | str:
    """Render a supplied price so it survives canonical hashing and JSON storage.

    Neither the canonical hashing contract (which fails closed on non-finite
    numbers) nor a ``JSON`` column can carry ``NaN`` / ``Infinity``. Such a price
    is recorded as its canonical name instead of being dropped or nulled, so the
    caller's real input -- however malformed -- stays auditable.
    """

    if math.isfinite(value):
        return value
    if math.isnan(value):
        return "NaN"
    return "Infinity" if value > 0 else "-Infinity"


def _supplied_quote_payload(quote: ReferenceQuote | None) -> dict[str, Any] | None:
    """Record the quote the caller actually supplied for one capture, verbatim.

    A quote that was *refused* -- future, time-stale, ``STALE`` / ``UNAVAILABLE``
    quality, another instrument or market type, untradable, crossed, non-positive,
    non-finite -- is still the fact the caller supplied, so it is kept rather than
    discarded. The immutable evidence must be able to answer "what did we actually
    receive, and why was it not accepted?" long after the runtime state is gone.

    Nothing here is synthesized: every field is the quote's own fact. ``None``
    means no quote was supplied at all.
    """

    if quote is None:
        return None
    return {
        "instrument_id": quote.instrument_id,
        "market_type": quote.market_type.value,
        "bid": _json_safe_price(quote.bid),
        "ask": _json_safe_price(quote.ask),
        "received_at": quote.received_at.isoformat(),
        "data_quality": quote.data_quality.value,
        "tradable": quote.tradable,
        "source_event_time": (
            None if quote.source_event_time is None else quote.source_event_time.isoformat()
        ),
        "source": quote.source,
        "source_sequence": quote.source_sequence,
    }


def _anchor_reference_quote_payload(quote: ReferenceQuote | None) -> dict[str, Any] | None:
    """The complete supplied quote needed to rebuild an anchor after restart."""

    if quote is None:
        return None
    payload = _supplied_quote_payload(quote)
    assert payload is not None
    return payload


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

        ``OK`` requires *every* frozen condition to hold at once:

        1. a quote exists;
        2. ``quote.instrument_id == instrument_id``;
        3. ``quote.market_type == market_type``;
        4. ``quote.data_quality is FRESH``;
        5. ``quote.tradable``;
        6. ``bid`` / ``ask`` finite;
        7. ``bid > 0``; 8. ``ask > 0``; 9. ``bid <= ask``;
        10. ``0 <= at - quote.received_at <= reference_max_age``.

        Any failure yields ``REFERENCE_STALE`` (``REFERENCE_MISSING`` when no quote
        exists at all) and the opportunity sample is still persisted.

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
        # A reference may be diagnostically supplied without feed provenance, but
        # it is never an accepted BBO until every observation fact is real. This
        # prevents the illegal ``OK + observation_id NULL`` shape without guessing
        # source or source-event time.
        if quote.source_event_time is None or not quote.source:
            return ReferenceDataStatus.REFERENCE_STALE, None
        if not quote._is_usable():
            return ReferenceDataStatus.REFERENCE_STALE, None
        if not quote._is_causally_available(at=at, max_age=self.reference_max_age):
            return ReferenceDataStatus.REFERENCE_STALE, None
        return ReferenceDataStatus.OK, quote


def _admission_signature(
    secret: bytes,
    *,
    session_id: str,
    session_started_at: datetime,
    event_id: str,
    event_digest: str,
    source_event_digest: str,
    source_event_time: datetime,
) -> str:
    """HMAC over every causal fact a proof binds, in canonical form."""

    return hmac.new(
        secret,
        canonical_bytes(
            {
                "proof_version": FORWARD_ADMISSION_PROOF_VERSION,
                "session_id": session_id,
                "session_started_at": session_started_at.isoformat(),
                "event_id": event_id,
                "event_digest": event_digest,
                "source_event_digest": source_event_digest,
                "source_event_time": source_event_time.isoformat(),
            }
        ),
        "sha256",
    ).hexdigest()


class ForwardAdmissionProof(BaseModel):
    """Opaque, causal-fact-bound proof minted only by the live-ingress session.

    It binds the live session (``session_id`` plus the ``session_started_at`` the
    session was created with), the exact event this ingest produced, and the
    exact normalized input it came from -- including that input's own causal time,
    which is the fact the session-start fence is decided on.
    """

    model_config = ConfigDict(frozen=True)

    proof_version: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_started_at: datetime
    event_id: str = Field(min_length=1)
    event_digest: str = Field(min_length=1)
    source_event_digest: str = Field(min_length=1)
    source_event_time: datetime
    signature: str = Field(min_length=1)

    @field_validator("session_started_at", "source_event_time")
    def _aware_admission_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("forward admission proof timestamps must be timezone-aware")
        return value

    def signed_payload(self) -> dict[str, str]:
        """Every signed fact, without the signature itself."""

        return {
            "proof_version": self.proof_version,
            "session_id": self.session_id,
            "session_started_at": self.session_started_at.isoformat(),
            "event_id": self.event_id,
            "event_digest": self.event_digest,
            "source_event_digest": self.source_event_digest,
            "source_event_time": self.source_event_time.isoformat(),
        }

    def payload(self) -> dict[str, str]:
        return {**self.signed_payload(), "signature": self.signature}

    @property
    def proof_hash(self) -> str:
        return forward_admission_proof_hash(self.payload())


class ForwardAdmissionAuthority:
    """Live-ingress-only capability that mints Forward admission proofs.

    It is created by the actual live ingress (``ScannerPipeline``) from the same
    trusted runtime clock that stamps the session, so:

    * ``session_started_at`` can never be supplied -- and therefore rewound -- by
      a repository caller;
    * the random secret is never persisted, so a previous process cannot mint a
      proof that a new process would accept.

    ``issue`` is deliberately the only mint API and it *requires* the triggering
    ``NormalizedMarketEvent``: there is no way to sign an arbitrary historical
    ``MarketEvent`` from this boundary alone.
    """

    def __init__(
        self, *, clock: Clock, session_id: str | None = None, secret: bytes | None = None
    ) -> None:
        self.session_id = session_id or secrets.token_urlsafe(24)
        self.session_started_at = clock.now()
        if self.session_started_at.tzinfo is None or self.session_started_at.utcoffset() is None:
            raise ValueError("live-ingress session start must be timezone-aware")
        self._secret = secret or secrets.token_bytes(32)

    def issue(
        self, *, source_event: NormalizedMarketEvent, event: MarketEvent
    ) -> ForwardAdmissionProof | None:
        """Mint a proof, or ``None`` when the input predates this live session.

        The decision uses the input's own causal source time, never a receipt,
        retry or restart time: an input that the exchange stamped before this
        session began is a redelivery, and admitting it would forge a new Forward
        sample out of an old market fact. Refusing it is the approved V1
        trade-off (capture-coverage loss after restart/reconnect).
        """

        if source_event.event_time < self.session_started_at:
            return None
        event_digest = forward_admission_event_hash(event.model_dump(mode="json"))
        source_event_digest = forward_admission_source_hash(source_event.model_dump(mode="json"))
        return ForwardAdmissionProof(
            proof_version=FORWARD_ADMISSION_PROOF_VERSION,
            session_id=self.session_id,
            session_started_at=self.session_started_at,
            event_id=event.event_id,
            event_digest=event_digest,
            source_event_digest=source_event_digest,
            source_event_time=source_event.event_time,
            signature=_admission_signature(
                self._secret,
                session_id=self.session_id,
                session_started_at=self.session_started_at,
                event_id=event.event_id,
                event_digest=event_digest,
                source_event_digest=source_event_digest,
                source_event_time=source_event.event_time,
            ),
        )

    def verifier(self) -> ForwardAdmissionVerifier:
        """The verification-only capability the durable repository may hold."""

        return ForwardAdmissionVerifier(
            session_id=self.session_id,
            session_started_at=self.session_started_at,
            secret=self._secret,
        )


class ForwardAdmissionVerifier:
    """Verification-only view of one live-ingress session.

    It intentionally exposes no signing API, so a repository composed with it has
    no public mint path: it can only accept or reject a proof the live ingress
    already issued for this session and this exact event.
    """

    def __init__(
        self, *, session_id: str, session_started_at: datetime, secret: bytes
    ) -> None:
        self.session_id = session_id
        self.session_started_at = session_started_at
        self._secret = secret

    def validates(self, proof: ForwardAdmissionProof, event: MarketEvent) -> bool:
        """Verify session ownership, the session-start fence and the exact event binding."""

        if proof.proof_version != FORWARD_ADMISSION_PROOF_VERSION:
            return False
        if proof.session_id != self.session_id or proof.event_id != event.event_id:
            return False
        if proof.session_started_at != self.session_started_at:
            return False
        # Defence in depth: even a correctly signed proof is refused when its own
        # causal source time sits before the live session it claims to belong to.
        if proof.source_event_time < self.session_started_at:
            return False
        event_digest = forward_admission_event_hash(event.model_dump(mode="json"))
        if not hmac.compare_digest(proof.event_digest, event_digest):
            return False
        return hmac.compare_digest(
            proof.signature,
            _admission_signature(
                self._secret,
                session_id=proof.session_id,
                session_started_at=proof.session_started_at,
                event_id=proof.event_id,
                event_digest=proof.event_digest,
                source_event_digest=proof.source_event_digest,
                source_event_time=proof.source_event_time,
            ),
        )


class CaptureAnchorInputs(BaseModel):
    """Frozen facts used for the later Formal G2 + Edge transaction."""

    model_config = ConfigDict(frozen=True)

    precondition_state: SymbolStateRecord | None
    opportunity_id: str
    evidence_revision: int
    anchor_recorded_at: datetime
    formal_evidence_hash: str
    event: MarketEvent
    timeline: SignalTimelineEvent
    state: SymbolStateRecord
    transition: StateTransition
    candidate: StrategyCandidate
    candidates: list[StrategyCandidate]
    observation: FeatureSnapshot
    context: EdgeCaptureContext
    forward_admission_proof: ForwardAdmissionProof
    reference_quote: ReferenceQuote | None
    reference_bbo_observation: BboObservation | None


class CaptureAnchor(BaseModel):
    """Append-only durable admission record for one Forward Paper opportunity."""

    model_config = ConfigDict(frozen=True)

    opportunity_id: str = Field(min_length=1)
    evidence_revision: int = Field(ge=1)
    event_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    evidence_at: datetime
    reference_data_status: ReferenceDataStatus
    reference_bbo_observation_id: str | None = None
    source_type: EvidenceSource
    source_identity: str = Field(min_length=1)
    source_manifest_id: str = Field(min_length=1)
    forward_admission_session_id: str = Field(min_length=1)
    forward_admission_event_digest: str = Field(min_length=1)
    forward_admission_proof_hash: str = Field(min_length=1)
    anchor_payload_version: str = Field(min_length=1)
    anchor_payload: dict[str, Any]
    anchor_hash: str = Field(min_length=1)
    anchor_hash_version: str = Field(min_length=1)
    recorded_at: datetime

    @field_validator("evidence_at", "recorded_at")
    def _aware_anchor_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capture anchor timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _canonical_content_is_consistent(self) -> CaptureAnchor:
        """Never trust a caller-provided hash or duplicated causal field."""

        if self.anchor_hash_version != CAPTURE_ANCHOR_HASH_VERSION:
            raise ValueError("capture anchor hash version is not supported")
        if self.anchor_hash != capture_anchor_hash(self.anchor_payload):
            raise ValueError("capture anchor hash does not match its canonical payload")
        inputs = self.formal_inputs()
        proof = inputs.forward_admission_proof
        if proof.proof_hash != self.forward_admission_proof_hash:
            raise ValueError("capture anchor admission proof hash is inconsistent")
        if proof.session_id != self.forward_admission_session_id:
            raise ValueError("capture anchor admission session is inconsistent")
        if proof.event_digest != self.forward_admission_event_digest:
            raise ValueError("capture anchor admission event digest is inconsistent")
        evidence = build_opportunity_evidence(
            event=inputs.event,
            timeline=inputs.timeline,
            state=inputs.state,
            transition=inputs.transition,
            candidate=inputs.candidate,
            observation=inputs.observation,
            context=inputs.context,
            reference_quote=inputs.reference_quote,
        )
        if self.anchor_payload.get("formal_evidence_hash") != evidence.evidence_hash:
            raise ValueError("capture anchor formal evidence hash is inconsistent")
        if (
            self.opportunity_id != evidence.opportunity_id
            or self.evidence_revision != evidence.evidence_revision
            or self.event_id != inputs.event.event_id
            or self.candidate_id != inputs.candidate.candidate_id
            or self.evidence_at != evidence.evidence_at
            or self.reference_data_status is not evidence.reference_data_status
            or self.source_type is not inputs.context.source_type
            or self.source_identity != inputs.context.source_identity
            or self.source_manifest_id != inputs.context.source_manifest_id
        ):
            raise ValueError("capture anchor top-level causal fields are inconsistent")
        _, usable_quote = inputs.context.classify_reference(
            quote=inputs.reference_quote,
            instrument_id=inputs.candidate.instrument_id,
            market_type=inputs.event.market_type,
            at=inputs.candidate.created_at,
        )
        expected_bbo = (
            None
            if usable_quote is None
            else usable_quote.bbo_observation(recorded_at=inputs.event.received_time)
        )
        if self.reference_data_status is ReferenceDataStatus.OK:
            if expected_bbo is None or self.reference_bbo_observation_id != expected_bbo.observation_id:
                raise ValueError("OK capture anchor must bind its complete reference BBO")
        elif self.reference_bbo_observation_id is not None or expected_bbo is not None:
            raise ValueError("missing/stale capture anchor may not bind a reference BBO")
        payload_bbo = self.anchor_payload.get("reference_bbo_observation")
        if (expected_bbo is None) != (payload_bbo is None):
            raise ValueError("capture anchor BBO payload is inconsistent")
        if expected_bbo is not None and BboObservation.model_validate(payload_bbo) != expected_bbo:
            raise ValueError("capture anchor BBO payload differs from its frozen observation")
        return self

    def formal_inputs(self) -> CaptureAnchorInputs:
        """Reconstruct all formal inputs solely from immutable anchor facts."""

        payload = self.anchor_payload
        observation = (
            None
            if payload["reference_bbo_observation"] is None
            else BboObservation.model_validate(payload["reference_bbo_observation"])
        )
        return CaptureAnchorInputs(
            precondition_state=(
                None
                if payload["precondition_state"] is None
                else SymbolStateRecord.model_validate(payload["precondition_state"])
            ),
            opportunity_id=self.opportunity_id,
            evidence_revision=self.evidence_revision,
            anchor_recorded_at=self.recorded_at,
            formal_evidence_hash=payload["formal_evidence_hash"],
            event=MarketEvent.model_validate(payload["event"]),
            timeline=SignalTimelineEvent.model_validate(payload["timeline"]),
            state=SymbolStateRecord.model_validate(payload["state"]),
            transition=StateTransition.model_validate(payload["transition"]),
            candidate=StrategyCandidate.model_validate(payload["candidate"]),
            candidates=[StrategyCandidate.model_validate(item) for item in payload["candidates"]],
            observation=FeatureSnapshot.model_validate(payload["observation"]),
            context=EdgeCaptureContext.model_validate(payload["context"]),
            forward_admission_proof=ForwardAdmissionProof.model_validate(
                payload["forward_admission_proof"]
            ),
            reference_quote=(
                None
                if payload["reference_quote"] is None
                else ReferenceQuote.model_validate(payload["reference_quote"])
            ),
            reference_bbo_observation=observation,
        )


class CaptureAnchorOrphanClassification(BaseModel):
    """One immutable, restart-visible reason an anchor can never be formalized."""

    model_config = ConfigDict(frozen=True)

    opportunity_id: str = Field(min_length=1)
    evidence_revision: int = Field(ge=1)
    classification: str = "UNVERIFIABLE_ORPHAN"
    reason: str = Field(min_length=1)
    expected_precondition: dict[str, Any]
    actual_precondition: dict[str, Any]
    orphan_version: str = CAPTURE_ANCHOR_ORPHAN_VERSION
    classification_hash: str = Field(min_length=1)
    classification_hash_version: str = CAPTURE_ANCHOR_ORPHAN_HASH_VERSION
    detected_at: datetime
    recorded_at: datetime

    @field_validator("detected_at", "recorded_at")
    def _aware_orphan_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capture anchor orphan timestamps must be timezone-aware")
        return value

    def payload(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "evidence_revision": self.evidence_revision,
            "classification": self.classification,
            "reason": self.reason,
            "expected_precondition": self.expected_precondition,
            "actual_precondition": self.actual_precondition,
            "orphan_version": self.orphan_version,
            "detected_at": self.detected_at,
            "recorded_at": self.recorded_at,
        }

    @model_validator(mode="after")
    def _canonical_orphan_is_consistent(self) -> CaptureAnchorOrphanClassification:
        if self.classification != "UNVERIFIABLE_ORPHAN":
            raise ValueError("capture anchor orphan classification is not supported")
        if self.classification_hash_version != CAPTURE_ANCHOR_ORPHAN_HASH_VERSION:
            raise ValueError("capture anchor orphan hash version is not supported")
        if self.classification_hash != capture_anchor_orphan_hash(self.payload()):
            raise ValueError("capture anchor orphan hash does not match its canonical payload")
        return self


def build_capture_anchor_orphan(
    *,
    opportunity_id: str,
    evidence_revision: int,
    recorded_at: datetime,
    expected_precondition: SymbolStateRecord,
    actual_precondition: SymbolStateRecord,
) -> CaptureAnchorOrphanClassification:
    """Freeze the first durable precondition mismatch without changing its anchor."""

    payload = {
        "opportunity_id": opportunity_id,
        "evidence_revision": evidence_revision,
        "classification": "UNVERIFIABLE_ORPHAN",
        "reason": "durable_g2_precondition_incompatible",
        "expected_precondition": expected_precondition.model_dump(mode="json"),
        "actual_precondition": actual_precondition.model_dump(mode="json"),
        "orphan_version": CAPTURE_ANCHOR_ORPHAN_VERSION,
        # The frozen event receipt time is used so repeated recovery attempts
        # derive the same immutable classification rather than inventing retry time.
        "detected_at": recorded_at,
        "recorded_at": recorded_at,
    }
    return CaptureAnchorOrphanClassification(
        **payload,
        classification_hash=capture_anchor_orphan_hash(payload),
        classification_hash_version=CAPTURE_ANCHOR_ORPHAN_HASH_VERSION,
    )


def build_capture_anchor(
    *,
    precondition_state: SymbolStateRecord | None,
    event: MarketEvent,
    timeline: SignalTimelineEvent,
    state: SymbolStateRecord,
    transition: StateTransition,
    candidates: list[StrategyCandidate],
    observation: FeatureSnapshot,
    context: EdgeCaptureContext,
    forward_admission_proof: ForwardAdmissionProof,
    reference_quote: ReferenceQuote | None,
) -> CaptureAnchor | None:
    """Freeze one qualifying Forward Paper admission before Formal persistence."""

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
    evidence = build_opportunity_evidence(
        event=event,
        timeline=timeline,
        state=state,
        transition=transition,
        candidate=candidate,
        observation=observation,
        context=context,
        reference_quote=reference_quote,
    )
    _, usable_quote = context.classify_reference(
        quote=reference_quote,
        instrument_id=candidate.instrument_id,
        market_type=event.market_type,
        at=candidate.created_at,
    )
    bbo = None if usable_quote is None else usable_quote.bbo_observation(recorded_at=event.received_time)
    payload = {
        "payload_version": CAPTURE_ANCHOR_PAYLOAD_VERSION,
        "precondition_state": (
            None if precondition_state is None else precondition_state.model_dump(mode="json")
        ),
        "event": event.model_dump(mode="json"),
        "timeline": timeline.model_dump(mode="json"),
        "state": state.model_dump(mode="json"),
        "transition": transition.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "observation": observation.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
        "forward_admission_proof": forward_admission_proof.model_dump(mode="json"),
        "reference_quote": _anchor_reference_quote_payload(reference_quote),
        "reference_bbo_observation": None if bbo is None else bbo.model_dump(mode="json"),
        "formal_evidence_hash": evidence.evidence_hash,
    }
    return CaptureAnchor(
        opportunity_id=evidence.opportunity_id,
        evidence_revision=evidence.evidence_revision,
        event_id=event.event_id,
        candidate_id=candidate.candidate_id,
        evidence_at=evidence.evidence_at,
        reference_data_status=evidence.reference_data_status,
        reference_bbo_observation_id=None if bbo is None else bbo.observation_id,
        source_type=context.source_type,
        source_identity=context.source_identity,
        source_manifest_id=context.source_manifest_id,
        forward_admission_session_id=forward_admission_proof.session_id,
        forward_admission_event_digest=forward_admission_proof.event_digest,
        forward_admission_proof_hash=forward_admission_proof.proof_hash,
        anchor_payload_version=CAPTURE_ANCHOR_PAYLOAD_VERSION,
        anchor_payload=payload,
        anchor_hash=capture_anchor_hash(payload),
        anchor_hash_version=CAPTURE_ANCHOR_HASH_VERSION,
        recorded_at=event.received_time,
    )


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
        # ``reference_data`` separates what was *supplied* from what was
        # *accepted*, so the immutable evidence answers both "which metrics did
        # this opportunity get?" and "what quote did the caller actually hand us,
        # and why was it refused?" -- without promoting a refused quote to
        # evidence. The accepted half keeps the frozen reference-metric contract:
        # metrics are present only for ``OK`` and are NULL (never 0) otherwise.
        # SE-02A's top-level reference contract is unchanged: the rejected metrics
        # stay NULL on ``EdgeOpportunityEvidence`` itself.
        "reference_data": {
            "status": reference_status.value,
            "supplied_quote": _supplied_quote_payload(reference_quote),
            "accepted_reference": {
                "bid": usable_quote.bid if usable_quote is not None else None,
                "ask": usable_quote.ask if usable_quote is not None else None,
                "received_at": (
                    usable_quote.received_at.isoformat() if usable_quote is not None else None
                ),
            },
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
    expected_evidence_hash: str | None = None,
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
    if expected_evidence_hash is not None and revision.evidence_hash != expected_evidence_hash:
        raise ValueError("formal evidence hash differs from the durable capture anchor")
    return await append_evidence_revision(session, revision)
