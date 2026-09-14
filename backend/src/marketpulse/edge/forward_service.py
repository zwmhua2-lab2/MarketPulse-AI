"""SE-02C: durable Forward Outcome service.

Three responsibilities, all bounded:

* **A. Forward path capture** -- :class:`ForwardPathRecorder` stores a normalized
  L1 BBO observation *only* while at least one ``FORWARD_PAPER`` evidence window
  covers it, and only through the accepted
  :func:`marketpulse.edge.repository.record_bbo_observation` writer, so there is
  no second BBO archive, no second BBO identity and no whole-market dump;
* **B. durable due discovery** -- :func:`discover_due_scopes` finds
  ``(opportunity_id, evidence_id, horizon)`` scopes that are already due and still
  have no revision-1 outcome, using PostgreSQL facts only, so a fresh process
  with no inherited memory rediscovers exactly the same work;
* **C. bounded evaluation** -- :func:`evaluate_due_outcomes` builds the
  deterministic calculation input, calls the pure calculator and appends the
  terminal outcome through the accepted
  :func:`marketpulse.edge.repository.append_forward_outcome`. "Bounded" refers to
  the number of *scopes* one call processes, never to the per-scope path: the
  durable forward path of a scope is read in full (keyset pages, no ceiling), so
  an incomplete path can never be classified as COMPLETE.

Deliberately absent: any resident loop, ``sleep``, scheduler, daemon, runtime host,
second market-data pipeline, second OKX websocket or new persistence path. The
service is a *capability*: an owner that already runs decides when to call it.

The evaluator never writes a revision above 1. An existing revision-1 outcome is
read back, verified compatible and returned as ``existing / idempotent``; a later
run, a later wall clock, a later BBO or a retry can never create revision 2.
Automatic correction stays the explicit immutable-correction path.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, select, text, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.db.models import (
    EdgeBboObservationRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.forward import (
    ALL_FORWARD_HORIZONS,
    FORWARD_PATH_WINDOW,
    RUNTIME_OUTCOME_REVISION,
    ForwardOutcomeReason,
    ForwardReference,
    ForwardScopeFacts,
    calculate_forward_outcome,
    forward_due_at,
)
from marketpulse.edge.models import (
    BboObservation,
    EvidenceSource,
    ForwardHorizon,
    ForwardOutcomeContract,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_bbo_observation,
)
from marketpulse.edge.repository import (
    INSERTED,
    EdgeOutcomeConflict,
    append_forward_outcome,
    record_bbo_observation,
)
from marketpulse.market_data.models import MarketType, NormalizedBookTicker

logger = logging.getLogger(__name__)

# Upper bound on the scopes one evaluation call processes per horizon. The call is
# a capability, not a loop: an owner that wants to drain more simply calls again.
DEFAULT_MAX_SCOPES_PER_EVALUATION = 500

# Forward path reads are **paged**, never capped. This constant is a per-statement
# page size that bounds each query's working set -- it is deliberately *not* a
# correctness ceiling: the loader keeps reading keyset pages until the durable
# window is exhausted, so the complete Forward Path always reaches the calculator
# (task §8-§11). Because no ceiling exists, no partially loaded path can ever be
# classified as COMPLETE.
FORWARD_PATH_READ_PAGE_SIZE = 10_000


def _scope_advisory_lock_key(
    opportunity_id: str, evidence_id: str, horizon: ForwardHorizon
) -> int:
    """Return the deterministic PostgreSQL bigint lock key for one outcome scope."""

    canonical = f"se02c|{opportunity_id}|{evidence_id}|{horizon.value}".encode()
    return int.from_bytes(hashlib.sha256(canonical).digest()[:8], "big", signed=True)


class ForwardPathTradabilityUnknown(ValueError):
    """The normalized ingress frame carries no authoritative tradability fact.

    A ``NormalizedBookTicker`` whose ``tradable`` is ``None`` states only that
    this frame does not know whether the instrument is currently tradable. That
    is *not* a tradable fact, so the ingress fails closed and archives nothing
    (task §17). It is a subclass of :class:`ValueError` so a caller that already
    guards the "unrepresentable frame" case keeps working unchanged.
    """


# --- A. Forward BBO path capture ---------------------------------------------------------


def build_forward_path_observation(event: NormalizedBookTicker) -> BboObservation:
    """Normalize one live book-ticker frame into the accepted BBO observation contract.

    ``available_at`` is the normalized receive time (the frozen V1 causal rule),
    and ``created_at`` is that same ingress instant rather than a wall clock, so
    re-ingesting the identical frame reproduces the identical observation and the
    identical identity instead of duplicating a horizon path point.

    Tradability is **carried through from the instrument**, never assumed. The
    normalized frame's ``tradable`` is the authority: ``True`` / ``False`` are
    persisted verbatim so the calculator can exclude a non-tradable observation,
    while ``None`` -- the frame carries no authoritative tradability fact --
    raises :class:`ForwardPathTradabilityUnknown` so the ingress fails closed
    instead of archiving a guess (task §12-§17). Quote presence, subscription
    presence and "the market event arrived" are never evidence of tradability.
    """

    if event.tradable is None:
        raise ForwardPathTradabilityUnknown(
            "normalized frame carries no authoritative tradability fact "
            f"(instrument_id={event.instrument_id})"
        )
    return build_bbo_observation(
        instrument_id=event.instrument_id,
        market_type=event.market_type,
        bid=event.bid_price,
        ask=event.ask_price,
        available_at=event.received_time,
        source_event_time=event.event_time,
        received_at=event.received_time,
        data_quality=event.data_quality,
        tradable=event.tradable,
        source=event.source,
        source_sequence=None,
        created_at=event.received_time,
    )


class ForwardPathRecorder:
    """Capture Forward BBO path observations for instruments with an open evidence window.

    Capture is minimised on purpose (task §15-§17): an observation is stored
    **only** when some ``FORWARD_PAPER`` evidence revision of the same
    ``instrument_id`` + ``market_type`` satisfies
    ``evidence_at <= observation.available_at <= evidence_at + 1h``. With no such
    window the market is not archived at all.

    Both the capture test and the storage are idempotent: the identity is
    content addressed, so two opportunities sharing one BBO still persist exactly
    one durable observation, and re-ingesting the same frame returns
    ``IDEMPOTENT``.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def has_relevant_forward_window(
        self,
        session: AsyncSession,
        *,
        instrument_id: str,
        market_type: MarketType,
        at: datetime,
    ) -> bool:
        """Is this exact instrument/market inside any Forward evidence window at ``at``?"""

        matched = await session.scalar(
            select(EdgeOpportunityEvidenceRecord.evidence_id)
            .where(
                EdgeOpportunityEvidenceRecord.instrument_id == instrument_id,
                EdgeOpportunityEvidenceRecord.market_type == market_type.value,
                EdgeOpportunityEvidenceRecord.source_type == EvidenceSource.FORWARD_PAPER.value,
                EdgeOpportunityEvidenceRecord.evidence_at <= at,
                EdgeOpportunityEvidenceRecord.evidence_at >= at - FORWARD_PATH_WINDOW,
            )
            .limit(1)
        )
        return matched is not None

    async def record(self, observation: BboObservation) -> str | None:
        """Store one Forward path observation, or ``None`` when it is not relevant.

        Returns the accepted writer's ``INSERTED`` / ``IDEMPOTENT``.
        """

        async with self._session_factory() as session:
            relevant = await self.has_relevant_forward_window(
                session,
                instrument_id=observation.instrument_id,
                market_type=observation.market_type,
                at=observation.available_at,
            )
            if not relevant:
                return None
            result = await record_bbo_observation(session, observation)
            await session.commit()
            return result

    async def record_event(self, event: NormalizedBookTicker) -> str | None:
        """Live-ingress entry point: build the observation and store it if relevant.

        Two frames are deliberately *not* Forward path facts, and neither one
        aborts the ingest loop:

        * a frame that cannot be represented as an accepted observation (a
          crossed, non-positive or non-finite quote) is unrepresentable in the
          accepted contract;
        * a frame whose ``tradable`` is ``None`` carries no authoritative
          tradability fact, so archiving it would silently invent one (task §17).

        Both are skipped and logged, bounded to one line per frame.
        """

        try:
            observation = build_forward_path_observation(event)
        except ForwardPathTradabilityUnknown:
            logger.warning(
                "forward_path_observation_skipped_unknown_tradability "
                "instrument_id=%s event_time=%s",
                event.instrument_id,
                event.event_time.isoformat(),
            )
            return None
        except ValueError:
            logger.warning(
                "forward_path_observation_rejected instrument_id=%s event_time=%s",
                event.instrument_id,
                event.event_time.isoformat(),
            )
            return None
        return await self.record(observation)


# --- B. Durable due discovery ------------------------------------------------------------


@dataclass(frozen=True)
class DueForwardScope:
    """One durable ``(opportunity, evidence revision, horizon)`` scope that is due."""

    opportunity_id: str
    evidence_id: str
    evidence_revision: int
    horizon: ForwardHorizon
    evidence_at: datetime
    expires_at: datetime
    instrument_id: str
    market_type: MarketType
    source_type: EvidenceSource
    source_identity: str
    reference_data_status: ReferenceDataStatus
    reference_bid: float | None
    reference_ask: float | None
    anchor_present: bool
    anchor_reference_bbo_observation_id: str | None

    @property
    def due_at(self) -> datetime:
        return forward_due_at(self.evidence_at, self.horizon)

    def scope_facts(self) -> ForwardScopeFacts:
        return ForwardScopeFacts(
            opportunity_id=self.opportunity_id,
            evidence_id=self.evidence_id,
            horizon=self.horizon,
            evidence_at=self.evidence_at,
            expires_at=self.expires_at,
            instrument_id=self.instrument_id,
            market_type=self.market_type,
            source_type=self.source_type,
            source_identity=self.source_identity,
        )


def _scope_from_rows(evidence, anchor, horizon: ForwardHorizon) -> DueForwardScope:
    return DueForwardScope(
        opportunity_id=evidence.opportunity_id,
        evidence_id=evidence.evidence_id,
        evidence_revision=evidence.evidence_revision,
        horizon=horizon,
        evidence_at=evidence.evidence_at,
        expires_at=evidence.expires_at,
        instrument_id=evidence.instrument_id,
        market_type=MarketType(evidence.market_type),
        source_type=EvidenceSource(evidence.source_type),
        source_identity=evidence.source_identity,
        reference_data_status=ReferenceDataStatus(evidence.reference_data_status),
        reference_bid=evidence.reference_bid,
        reference_ask=evidence.reference_ask,
        anchor_present=anchor is not None,
        anchor_reference_bbo_observation_id=(
            None if anchor is None else anchor.reference_bbo_observation_id
        ),
    )


async def discover_due_scopes(
    session: AsyncSession,
    *,
    now: datetime,
    horizons: Sequence[ForwardHorizon] = ALL_FORWARD_HORIZONS,
    limit: int = DEFAULT_MAX_SCOPES_PER_EVALUATION,
) -> list[DueForwardScope]:
    """Find due scopes from durable PostgreSQL facts only.

    ``due_at = evidence_at + horizon.duration``, so ``due_at <= now`` is exactly
    ``evidence_at <= now - duration``: the discovery predicate is a pure function
    of immutable evidence facts and the evaluation clock. A scope that already
    owns a revision-1 outcome is excluded, which makes re-running the evaluator
    over the same facts a no-op instead of a second outcome.
    """

    if limit <= 0:
        raise ValueError("limit must be positive")
    scopes: list[DueForwardScope] = []
    for horizon in horizons:
        cutoff = now - timedelta(seconds=horizon.duration_seconds)
        settled = (
            select(EdgeForwardOutcomeRecord.outcome_id)
            .where(
                EdgeForwardOutcomeRecord.opportunity_id
                == EdgeOpportunityEvidenceRecord.opportunity_id,
                EdgeForwardOutcomeRecord.evidence_id
                == EdgeOpportunityEvidenceRecord.evidence_id,
                EdgeForwardOutcomeRecord.horizon == horizon.value,
                EdgeForwardOutcomeRecord.outcome_revision == RUNTIME_OUTCOME_REVISION,
            )
            .exists()
        )
        rows = (
            await session.execute(
                select(EdgeOpportunityEvidenceRecord, EdgeOpportunityCaptureAnchorRecord)
                .outerjoin(
                    EdgeOpportunityCaptureAnchorRecord,
                    and_(
                        EdgeOpportunityCaptureAnchorRecord.opportunity_id
                        == EdgeOpportunityEvidenceRecord.opportunity_id,
                        EdgeOpportunityCaptureAnchorRecord.evidence_revision
                        == EdgeOpportunityEvidenceRecord.evidence_revision,
                    ),
                )
                .where(EdgeOpportunityEvidenceRecord.evidence_at <= cutoff, ~settled)
                .order_by(
                    EdgeOpportunityEvidenceRecord.evidence_at.asc(),
                    EdgeOpportunityEvidenceRecord.evidence_id.asc(),
                )
                .limit(limit)
            )
        ).all()
        for evidence, anchor in rows:
            scopes.append(_scope_from_rows(evidence, anchor, horizon))
    return scopes


async def load_forward_outcome_contract(
    session: AsyncSession,
    *,
    opportunity_id: str,
    evidence_id: str,
    horizon: ForwardHorizon,
    outcome_revision: int,
) -> ForwardOutcomeContract | None:
    """Rehydrate one durable outcome revision and re-verify its immutable hashes."""

    record = await session.scalar(
        select(EdgeForwardOutcomeRecord).where(
            EdgeForwardOutcomeRecord.opportunity_id == opportunity_id,
            EdgeForwardOutcomeRecord.evidence_id == evidence_id,
            EdgeForwardOutcomeRecord.horizon == horizon.value,
            EdgeForwardOutcomeRecord.outcome_revision == outcome_revision,
        )
    )
    return None if record is None else _contract_from_record(record)


def _contract_from_record(record: EdgeForwardOutcomeRecord) -> ForwardOutcomeContract:
    """Rebuild the accepted contract from its durable row.

    Rebuilding goes through the accepted contract validators, so a stored row
    whose ``calculation_digest`` / ``outcome_record_hash`` no longer match its own
    content is rejected here rather than silently trusted.
    """

    return ForwardOutcomeContract(
        outcome_id=record.outcome_id,
        opportunity_id=record.opportunity_id,
        evidence_id=record.evidence_id,
        horizon=ForwardHorizon(record.horizon),
        outcome_revision=record.outcome_revision,
        supersedes_outcome_id=record.supersedes_outcome_id,
        outcome_contract_version=record.outcome_contract_version,
        calculation_status=OutcomeCalculationStatus(record.calculation_status),
        opportunity_lifecycle_at_horizon=(
            None
            if record.opportunity_lifecycle_at_horizon is None
            else OpportunityLifecycleAtHorizon(record.opportunity_lifecycle_at_horizon)
        ),
        due_at=record.due_at,
        source_type=EvidenceSource(record.source_type),
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


# --- C. Bounded evaluation ---------------------------------------------------------------


class ForwardOutcomeService:
    """Evaluate due scopes and append their first, terminal forward outcome.

    The service owns no loop, no timer and no cache: every call re-derives
    everything from durable facts, which is exactly what makes a restart safe.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        clock: Clock | None = None,
        horizons: Sequence[ForwardHorizon] = ALL_FORWARD_HORIZONS,
        max_scopes: int = DEFAULT_MAX_SCOPES_PER_EVALUATION,
    ) -> None:
        if max_scopes <= 0:
            raise ValueError("max_scopes must be positive")
        self._session_factory = session_factory
        self.clock = clock or SystemClock()
        self.horizons = tuple(horizons)
        self.max_scopes = max_scopes

    async def evaluate_due_outcomes(
        self, now: datetime | None = None
    ) -> list[ForwardOutcomeContract]:
        """Evaluate every due scope without a revision-1 outcome. Bounded, no sleeping."""

        moment = now if now is not None else self.clock.now()
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("evaluation clock must be timezone-aware")
        async with self._session_factory() as session:
            scopes = await discover_due_scopes(
                session, now=moment, horizons=self.horizons, limit=self.max_scopes
            )
        outcomes: list[ForwardOutcomeContract] = []
        for scope in scopes:
            outcomes.append(await self.evaluate_scope(scope))
        return outcomes

    async def evaluate_scope(self, scope: DueForwardScope) -> ForwardOutcomeContract:
        """Serialize, calculate and append exactly one terminal revision-1 outcome.

        The coordinator transaction holds a PostgreSQL advisory transaction lock for
        the complete scope identity until the outcome commit. The existing-outcome
        check deliberately happens *after* lock acquisition: a waiter therefore sees
        the winner's committed revision under READ COMMITTED and returns it without
        opening a second calculation snapshot.
        """

        async with self._session_factory() as coordinator, coordinator.begin():
            await coordinator.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {
                    "lock_key": _scope_advisory_lock_key(
                        scope.opportunity_id, scope.evidence_id, scope.horizon
                    )
                },
            )
            existing = await load_forward_outcome_contract(
                coordinator,
                opportunity_id=scope.opportunity_id,
                evidence_id=scope.evidence_id,
                horizon=scope.horizon,
                outcome_revision=RUNTIME_OUTCOME_REVISION,
            )
            if existing is not None:
                return existing

            outcome = await self.calculate_scope(scope)
            result = await append_forward_outcome(coordinator, outcome)
            if result == INSERTED:
                return outcome

            durable = await load_forward_outcome_contract(
                coordinator,
                opportunity_id=scope.opportunity_id,
                evidence_id=scope.evidence_id,
                horizon=scope.horizon,
                outcome_revision=RUNTIME_OUTCOME_REVISION,
            )
            if durable is None:
                raise RuntimeError("idempotent forward outcome is not durable")
            return durable

    async def calculate_scope(self, scope: DueForwardScope) -> ForwardOutcomeContract:
        """Build the calculation input from one stable, read-only PostgreSQL snapshot."""

        async with self._session_factory() as session, session.begin():
            # This is intentionally the first SQL statement in the transaction. The
            # reference and every keyset page below must share the snapshot that this
            # statement establishes; late commits remain durable but cannot alter the
            # already-started calculation attempt.
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            reference, structural_problem = await self._resolve_reference(session, scope)
            observations = await self._load_observations(session, scope)
        return calculate_forward_outcome(
            scope=scope.scope_facts(),
            reference=reference,
            observations=observations,
            structural_problem=structural_problem,
        )

    async def _resolve_reference(
        self, session: AsyncSession, scope: DueForwardScope
    ) -> tuple[ForwardReference, ForwardOutcomeReason | None]:
        """Resolve the reference authority of one scope from durable facts.

        A ``FORWARD_PAPER`` scope takes its reference from the FIX-01 durable
        capture anchor (``reference_bbo_observation_id``) and never from "the
        latest quote" -- the whole point of the frozen anchor is that a later
        quote can never become the reference of an earlier opportunity. A
        ``HISTORICAL_REPLAY`` scope has no Forward anchor by design, so it uses
        the reference metrics its accepted evidence row already froze.
        """

        if scope.source_type is EvidenceSource.FORWARD_PAPER:
            if not scope.anchor_present:
                return (
                    ForwardReference(status=scope.reference_data_status),
                    ForwardOutcomeReason.INVALID_FORWARD_ANCHOR_MISSING,
                )
            observation_id = scope.anchor_reference_bbo_observation_id
            if observation_id is None:
                return ForwardReference(status=scope.reference_data_status), None
            record = await session.get(EdgeBboObservationRecord, observation_id)
            if record is None:
                return (
                    ForwardReference(status=scope.reference_data_status),
                    ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_MISSING,
                )
            return (
                ForwardReference(
                    status=scope.reference_data_status,
                    bid=record.bid,
                    ask=record.ask,
                    observation_id=record.observation_id,
                    observation_instrument_id=record.instrument_id,
                    observation_market_type=MarketType(record.market_type),
                ),
                None,
            )
        return (
            ForwardReference(
                status=scope.reference_data_status,
                bid=scope.reference_bid,
                ask=scope.reference_ask,
            ),
            None,
        )

    async def _load_observations(
        self, session: AsyncSession, scope: DueForwardScope
    ) -> tuple[BboObservation, ...]:
        """Load the **complete** forward path of one scope, page by page.

        The durable market-time window is
        ``evidence_at <= available_at <= due_at``. Snapshot visibility is a second,
        independent eligibility boundary: reference resolution and every page are
        read in the caller's single REPEATABLE READ transaction, so a row committed
        after that snapshot began cannot alter this calculation attempt. The causal
        cutoff is also enforced inside the pure calculator, so a caller that hands
        it a later observation still gets it rejected as future data.

        Reading is keyset-paged on ``(available_at, observation_id)`` solely as a
        complete traversal order. Endpoint selection remains the pure calculator's
        independent total order
        ``(available_at, has_source_sequence, source_sequence, observation_id)``.
        The loop ends only when the durable snapshot window is exhausted.
        ``FORWARD_PATH_READ_PAGE_SIZE`` therefore bounds one statement, **not** the
        path: every snapshot-visible durable observation in the window reaches the
        calculator, so endpoint selection, MFE and MAE cover the whole frozen path.
        """

        observations: list[BboObservation] = []
        last_key: tuple[datetime, str] | None = None
        while True:
            statement = (
                select(EdgeBboObservationRecord)
                .where(
                    EdgeBboObservationRecord.instrument_id == scope.instrument_id,
                    EdgeBboObservationRecord.market_type == scope.market_type.value,
                    EdgeBboObservationRecord.available_at >= scope.evidence_at,
                    EdgeBboObservationRecord.available_at <= scope.due_at,
                )
                .order_by(
                    EdgeBboObservationRecord.available_at.asc(),
                    EdgeBboObservationRecord.observation_id.asc(),
                )
                .limit(FORWARD_PATH_READ_PAGE_SIZE)
            )
            if last_key is not None:
                statement = statement.where(
                    tuple_(
                        EdgeBboObservationRecord.available_at,
                        EdgeBboObservationRecord.observation_id,
                    )
                    > last_key
                )
            page = (await session.scalars(statement)).all()
            if not page:
                break
            observations.extend(_observation_from_record(row) for row in page)
            if len(page) < FORWARD_PATH_READ_PAGE_SIZE:
                break
            last_key = (page[-1].available_at, page[-1].observation_id)
        return tuple(observations)

    async def append_outcome(self, outcome: ForwardOutcomeContract) -> ForwardOutcomeContract:
        """Append the first revision, or return the compatible durable twin.

        Two independent evaluators may race on the same scope. The accepted
        writer already collapses ``same scope + same revision + same hash`` onto
        ``IDEMPOTENT``; the remaining race is two ``INSERT``s, where PostgreSQL
        keeps exactly one row and rejects the loser. That loser is reconciled
        here against the winning row instead of surfacing a bare
        ``IntegrityError``, so both callers receive an equivalent durable outcome
        and the scope still owns exactly one revision-1 row.
        """

        try:
            async with self._session_factory() as session, session.begin():
                result = await append_forward_outcome(session, outcome)
        except IntegrityError as error:
            existing = await self._reconcile(outcome, error)
            return existing
        if result != "INSERTED":
            durable = await self._load_durable(outcome)
            if durable is not None:
                return durable
        return outcome

    async def _load_durable(
        self, outcome: ForwardOutcomeContract
    ) -> ForwardOutcomeContract | None:
        async with self._session_factory() as session:
            return await load_forward_outcome_contract(
                session,
                opportunity_id=outcome.opportunity_id,
                evidence_id=outcome.evidence_id,
                horizon=outcome.horizon,
                outcome_revision=outcome.outcome_revision,
            )

    async def _reconcile(
        self, outcome: ForwardOutcomeContract, error: IntegrityError
    ) -> ForwardOutcomeContract:
        durable = await self._load_durable(outcome)
        if durable is None:
            # Not the revision race: the constraint that fired was something else.
            raise error
        if durable.outcome_record_hash != outcome.outcome_record_hash:
            raise EdgeOutcomeConflict(
                "same outcome scope and revision with different record content "
                f"(opportunity_id={outcome.opportunity_id}, horizon={outcome.horizon.value})"
            )
        return durable


def _observation_from_record(record: EdgeBboObservationRecord) -> BboObservation:
    return BboObservation(
        observation_id=record.observation_id,
        instrument_id=record.instrument_id,
        market_type=MarketType(record.market_type),
        bid=record.bid,
        ask=record.ask,
        available_at=record.available_at,
        source_event_time=record.source_event_time,
        received_at=record.received_at,
        data_quality=record.data_quality,
        tradable=record.tradable,
        source=record.source,
        source_sequence=record.source_sequence,
        created_at=record.created_at,
    )


async def evaluate_due_outcomes(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    now: datetime | None = None,
    horizons: Sequence[ForwardHorizon] = ALL_FORWARD_HORIZONS,
    max_scopes: int = DEFAULT_MAX_SCOPES_PER_EVALUATION,
    clock: Clock | None = None,
) -> list[ForwardOutcomeContract]:
    """Bounded service API: evaluate all due Forward scopes once and return their outcomes."""

    service = ForwardOutcomeService(
        session_factory, clock=clock, horizons=horizons, max_scopes=max_scopes
    )
    return await service.evaluate_due_outcomes(now)
