"""SE-02C: deterministic Forward Outcome Calculator (pure core).

This module owns the *calculation*: the frozen V1 calculator policy, the causal
eligibility rules, endpoint selection, the market-excursion (MFE / MAE)
computation and the terminal classification. It performs no I/O, opens no
session and writes nothing -- the durable orchestration lives in
:mod:`marketpulse.edge.forward_service`, and the single persistence path stays
the accepted :func:`marketpulse.edge.repository.append_forward_outcome`.

Frozen V1 calculator policy (approved SE-02C requirement, not derived from any
other setting in the repository):

===========================  ==========================================
``calculator_version``       ``se02c-forward-outcome-v1``
``cost_policy``              ``SPOT_LONG_TAKER_ROUND_TRIP``
``cost_model_version``       ``se02c-paper-cost-v1``
``fee_rate``                 ``0.001``
``slippage_bps``             ``5``
reference price              ``(reference_bid + reference_ask) / 2``
endpoint freshness TTL       ``5 seconds``
forward path window          the largest licensed horizon (``1h``)
===========================  ==========================================

The five freshness / excursion values above are *versioned calculator policy*.
They are module constants on purpose: the calculator must never read a mutable
G3/G4 runtime setting at evaluation time, otherwise a later configuration change
would silently rewrite what an outcome means.

Determinism / causality rules frozen here:

* ``due_at = evidence_at + horizon.duration`` -- never ``now + horizon``, so a
  retry, a restart, a later run or a later quote can never move the horizon;
* the causal cutoff is ``available_at <= due_at``. A quote whose
  ``source_event_time`` is inside the horizon but whose ``available_at`` is after
  ``due_at`` is **future** data and is excluded: it was not observable at the
  horizon, so using it would be lookahead;
* the reference price authority is the durable FIX-01 capture-anchor BBO
  (``reference_bbo_observation_id``) -- never "the latest quote at evaluation
  time";
* the endpoint is the greatest **forward path** observation (strictly after the
  evidence anchor) under the total order
  ``(available_at, has_source_sequence, source_sequence, observation_id)``. The
  capture anchor itself is the reference authority only and is never an endpoint;
* the durable loader has no observation ceiling: the whole Forward Path always
  takes part in endpoint selection, MFE and MAE (task §8-§11).

Reuse / provenance separation (task §52): the calculation content excludes
provenance, so a ``HISTORICAL_REPLAY`` outcome and a ``FORWARD_PAPER`` outcome
computed from identical facts share one ``calculation_digest`` while their
``outcome_record_hash`` still differs. Because the digest feeds the record hash,
the digest is computed for **every** terminal status -- that is what makes the
record hash stable across retries and restarts.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from itertools import pairwise

from marketpulse.market_data.models import DataQuality, MarketType

from .models import (
    BboObservation,
    EvidenceSource,
    ForwardHorizon,
    ForwardOutcomeContract,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
    build_forward_outcome_contract,
)

# --- Frozen V1 calculator policy ---------------------------------------------------------

CALCULATOR_VERSION = "se02c-forward-outcome-v1"
COST_POLICY = "SPOT_LONG_TAKER_ROUND_TRIP"
COST_MODEL_VERSION = "se02c-paper-cost-v1"
FEE_RATE = 0.001
SLIPPAGE_BPS = 5
SLIPPAGE_FRACTION = SLIPPAGE_BPS / 10_000
END_FRESHNESS_TTL = timedelta(seconds=5)

# The widest forward path window: one hour, i.e. the largest licensed horizon.
FORWARD_PATH_WINDOW = timedelta(seconds=3600)

# The normal evaluator only ever writes the first revision of a scope.
RUNTIME_OUTCOME_REVISION = 1

ALL_FORWARD_HORIZONS: tuple[ForwardHorizon, ...] = (
    ForwardHorizon.S30,
    ForwardHorizon.M5,
    ForwardHorizon.M15,
    ForwardHorizon.H1,
)


class ForwardOutcomeReason(StrEnum):
    """Frozen terminal reason vocabulary.

    The first group is *data insufficiency*; the second group is *durable-fact
    contradiction*. A plain missing quote is never a contradiction.
    """

    COMPLETE = "COMPLETE"
    REFERENCE_MISSING = "REFERENCE_MISSING"
    REFERENCE_STALE = "REFERENCE_STALE"
    ENDPOINT_MISSING = "ENDPOINT_MISSING"
    ENDPOINT_STALE = "ENDPOINT_STALE"

    INVALID_REFERENCE_OBSERVATION_MISSING = "INVALID_REFERENCE_OBSERVATION_MISSING"
    INVALID_REFERENCE_OBSERVATION_INCOMPLETE = "INVALID_REFERENCE_OBSERVATION_INCOMPLETE"
    INVALID_REFERENCE_INSTRUMENT_MISMATCH = "INVALID_REFERENCE_INSTRUMENT_MISMATCH"
    INVALID_REFERENCE_MARKET_MISMATCH = "INVALID_REFERENCE_MARKET_MISMATCH"
    INVALID_REFERENCE_PRICES = "INVALID_REFERENCE_PRICES"
    INVALID_REFERENCE_PRESENT_FOR_NON_OK_STATUS = "INVALID_REFERENCE_PRESENT_FOR_NON_OK_STATUS"
    INVALID_FORWARD_ANCHOR_MISSING = "INVALID_FORWARD_ANCHOR_MISSING"
    INVALID_CHRONOLOGY = "INVALID_CHRONOLOGY"

    @property
    def is_invalid(self) -> bool:
        return self.value.startswith("INVALID_")


# --- Calculation inputs ------------------------------------------------------------------


def forward_due_at(evidence_at: datetime, horizon: ForwardHorizon) -> datetime:
    """``due_at`` is a pure function of the durable evidence anchor and the horizon."""

    return evidence_at + timedelta(seconds=horizon.duration_seconds)


def is_forward_due(*, evidence_at: datetime, horizon: ForwardHorizon, now: datetime) -> bool:
    """Is this scope due? PENDING is *derived*, never persisted (task §11)."""

    return forward_due_at(evidence_at, horizon) <= now


@dataclass(frozen=True)
class ForwardScopeFacts:
    """The durable identity and causal facts of one ``(opportunity, evidence, horizon)``."""

    opportunity_id: str
    evidence_id: str
    horizon: ForwardHorizon
    evidence_at: datetime
    expires_at: datetime
    instrument_id: str
    market_type: MarketType
    source_type: EvidenceSource
    source_identity: str

    def __post_init__(self) -> None:
        for name in ("evidence_at", "expires_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if not self.opportunity_id or not self.evidence_id:
            raise ValueError("evidence scope identifiers must be non-empty")
        if not self.instrument_id:
            raise ValueError("instrument_id must be non-empty")
        if not self.source_identity:
            raise ValueError("source_identity must be non-empty")
        if not isinstance(self.horizon, ForwardHorizon):
            raise TypeError("horizon must be one of the licensed forward horizons")

    @property
    def due_at(self) -> datetime:
        return forward_due_at(self.evidence_at, self.horizon)


@dataclass(frozen=True)
class ForwardReference:
    """Frozen reference authority of one forward scope.

    ``observation_id`` is the FIX-01 durable capture-anchor BBO. When it is
    present the observation's own market identity must be supplied too, so a
    reference observed on another instrument or another market can never be used
    silently. ``observation_id is None`` is only legal for ``HISTORICAL_REPLAY``,
    whose accepted SE-02A evidence row already froze the reference metrics
    itself; a ``FORWARD_PAPER`` scope without its durable anchor BBO is a
    provenance contradiction.
    """

    status: ReferenceDataStatus
    bid: float | None = None
    ask: float | None = None
    observation_id: str | None = None
    observation_instrument_id: str | None = None
    observation_market_type: MarketType | None = None


# --- Observation classification ----------------------------------------------------------


@dataclass(frozen=True)
class ForwardObservationSelection:
    """Deterministic partition of the durable observations of one scope."""

    evidence_at: datetime
    total: int
    eligible: tuple[BboObservation, ...]
    excluded_identity: int
    excluded_stale: int
    excluded_untradable: int
    excluded_causal: int

    @property
    def endpoint(self) -> BboObservation | None:
        """Greatest *forward path* observation under the frozen V1 total order.

        The horizon endpoint may only be a **forward path** observation, i.e. one
        with ``evidence_at < available_at <= due_at`` (task §20). The FIX-01
        capture anchor sits exactly at ``available_at == evidence_at`` and is the
        *reference authority only*: it is never a horizon endpoint. Restricting
        the selection to the strictly later path is what makes a scope whose only
        durable observation is its own anchor report ``ENDPOINT_MISSING`` instead
        of mistaking the anchor for a horizon endpoint.
        """

        path = self.path_points
        if not path:
            return None
        return max(path, key=_endpoint_sort_key)

    @property
    def path_points(self) -> tuple[BboObservation, ...]:
        """Eligible observations strictly after the evidence anchor (task §28)."""

        return tuple(item for item in self.eligible if item.available_at > self.evidence_at)


def _endpoint_sort_key(observation: BboObservation) -> tuple[datetime, int, int, str]:
    """Frozen endpoint tie-break (task §21-§22).

    Greatest ``available_at`` first; on a tie an observation that carries a
    comparable ``source_sequence`` wins over one that does not; then the greater
    ``source_sequence``; then the greater ``observation_id`` in lexical order.
    Every component increases in the same direction, so the endpoint is the
    maximum of one total order rather than a mix of sort directions.
    """

    has_sequence = observation.source_sequence is not None
    return (
        observation.available_at,
        1 if has_sequence else 0,
        observation.source_sequence if has_sequence else 0,
        observation.observation_id,
    )


def classify_forward_observations(
    *, scope: ForwardScopeFacts, observations: Sequence[BboObservation]
) -> ForwardObservationSelection:
    """Apply the frozen BBO eligibility rules (task §19-§20).

    An observation is eligible when and only when it belongs to the scope's exact
    market identity, the feed marked it ``FRESH``, it is ``tradable`` and it was
    already observable at ``due_at`` (``available_at <= due_at``).

    Each observation is counted in at most one exclusion bucket, decided in the
    order identity -> stale -> untradable -> causal, so the four counters plus
    the eligible set always add up to ``total``.

    The frozen Forward Path range is ``evidence_at < available_at <= due_at``
    (task §20). This partition keeps the eligibility rule itself unchanged and
    additionally carries ``evidence_at``, so :attr:`endpoint` and
    :attr:`path_points` can restrict themselves to the strictly later Forward
    Path: the FIX-01 capture anchor (``available_at == evidence_at``) is a
    reference authority only and can never become a horizon endpoint.
    """

    due_at = scope.due_at
    eligible: list[BboObservation] = []
    excluded_identity = excluded_stale = excluded_untradable = excluded_causal = 0
    for observation in observations:
        if (
            observation.instrument_id != scope.instrument_id
            or observation.market_type != scope.market_type
        ):
            excluded_identity += 1
            continue
        if observation.data_quality is not DataQuality.FRESH:
            excluded_stale += 1
            continue
        if not observation.tradable:
            excluded_untradable += 1
            continue
        if observation.available_at > due_at:
            excluded_causal += 1
            continue
        eligible.append(observation)
    return ForwardObservationSelection(
        evidence_at=scope.evidence_at,
        total=len(observations),
        eligible=tuple(eligible),
        excluded_identity=excluded_identity,
        excluded_stale=excluded_stale,
        excluded_untradable=excluded_untradable,
        excluded_causal=excluded_causal,
    )


# --- Structural validation ---------------------------------------------------------------


def _structural_invalid_reason(
    *, scope: ForwardScopeFacts, reference: ForwardReference
) -> ForwardOutcomeReason | None:
    """Detect a contradiction in the durable facts themselves (task §41).

    Only self-contradictory or structurally impossible facts reach this branch.
    A missing or stale quote is a *data insufficiency*, never an invalidity.
    """

    if scope.expires_at < scope.evidence_at:
        return ForwardOutcomeReason.INVALID_CHRONOLOGY

    if reference.status is not ReferenceDataStatus.OK:
        if (
            reference.bid is not None
            or reference.ask is not None
            or reference.observation_id is not None
        ):
            return ForwardOutcomeReason.INVALID_REFERENCE_PRESENT_FOR_NON_OK_STATUS
        return None

    if reference.bid is None or reference.ask is None:
        return ForwardOutcomeReason.INVALID_REFERENCE_PRICES
    if not (math.isfinite(reference.bid) and math.isfinite(reference.ask)):
        return ForwardOutcomeReason.INVALID_REFERENCE_PRICES
    if reference.bid <= 0 or reference.ask <= 0 or reference.bid > reference.ask:
        return ForwardOutcomeReason.INVALID_REFERENCE_PRICES

    if reference.observation_id is None:
        # Replay revisions carry their frozen reference metrics on the accepted
        # evidence row itself; a Forward Paper revision must name the durable
        # FIX-01 capture-anchor BBO.
        if scope.source_type is not EvidenceSource.HISTORICAL_REPLAY:
            return ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_MISSING
        return None

    if reference.observation_instrument_id is None or reference.observation_market_type is None:
        return ForwardOutcomeReason.INVALID_REFERENCE_OBSERVATION_INCOMPLETE
    if reference.observation_instrument_id != scope.instrument_id:
        return ForwardOutcomeReason.INVALID_REFERENCE_INSTRUMENT_MISMATCH
    if reference.observation_market_type != scope.market_type:
        return ForwardOutcomeReason.INVALID_REFERENCE_MARKET_MISMATCH
    return None


# --- Cost model --------------------------------------------------------------------------


def forward_cost_prices(*, reference_ask: float, end_bid: float) -> tuple[float, float]:
    """Executable entry / exit prices of one V1 SPOT LONG round trip (task §32-§33)."""

    entry_exec = reference_ask * (1 + SLIPPAGE_FRACTION)
    exit_exec = end_bid * (1 - SLIPPAGE_FRACTION)
    return entry_exec, exit_exec


def cost_adjusted_forward_return(*, reference_ask: float, end_bid: float) -> float:
    """Exact multiplicative cost model -- never an approximate fee subtraction (§36)."""

    entry_exec, exit_exec = forward_cost_prices(reference_ask=reference_ask, end_bid=end_bid)
    entry_cash_cost = entry_exec * (1 + FEE_RATE)
    exit_cash_value = exit_exec * (1 - FEE_RATE)
    return exit_cash_value / entry_cash_cost - 1


# --- Terminal contract -------------------------------------------------------------------


@dataclass(frozen=True)
class _Metrics:
    reference_price: float | None = None
    end_bid: float | None = None
    end_ask: float | None = None
    mfe: float | None = None
    mae: float | None = None
    reference_return: float | None = None
    executable_long_return: float | None = None
    cost_adjusted_forward_return: float | None = None


_NO_METRICS = _Metrics()


def _isoformat(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat()


def _diagnostics(
    *,
    reason: ForwardOutcomeReason,
    selection: ForwardObservationSelection,
    scope: ForwardScopeFacts,
    reference: ForwardReference,
    endpoint: BboObservation | None,
    path_points: tuple[BboObservation, ...],
) -> dict[str, object]:
    """Bounded completeness diagnostics (task §42).

    A wide gap between two path observations is a diagnostic, never an
    invalidity: the calculator reports what it saw and still classifies only on
    the frozen rules.

    There is deliberately no "truncated" flag: the durable layer loads the whole
    Forward Path, so an incomplete path is not a representable input at all
    (task §10 / §11).
    """

    available = [item.available_at for item in selection.eligible]
    path_times = [scope.evidence_at, *[item.available_at for item in path_points]]
    path_times.sort()
    gap = (
        max((later - earlier).total_seconds() for earlier, later in pairwise(path_times))
        if len(path_times) > 1
        else 0.0
    )
    return {
        "reason": reason.value,
        "observation_count": selection.total,
        "eligible_observation_count": len(selection.eligible),
        "path_point_count": len(path_points),
        "first_available_at": _isoformat(min(available)) if available else None,
        "last_available_at": _isoformat(max(available)) if available else None,
        "max_observation_gap_seconds": gap,
        "end_age_seconds": (
            None
            if endpoint is None
            else (scope.due_at - endpoint.available_at).total_seconds()
        ),
        "end_observation_id": None if endpoint is None else endpoint.observation_id,
        "reference_status": reference.status.value,
        "excluded_stale_count": selection.excluded_stale,
        "excluded_untradable_count": selection.excluded_untradable,
        "excluded_causal_count": selection.excluded_causal,
        "excluded_identity_count": selection.excluded_identity,
    }


def calculate_forward_outcome(
    *,
    scope: ForwardScopeFacts,
    reference: ForwardReference,
    observations: Sequence[BboObservation],
    structural_problem: ForwardOutcomeReason | None = None,
) -> ForwardOutcomeContract:
    """Compute one terminal, deterministic forward-outcome revision.

    Terminal classification (frozen order):

    1. ``INVALID`` -- the durable facts contradict each other or are structurally
       impossible. An ``INVALID`` outcome binds no observation at all.
    2. ``INSUFFICIENT_DATA`` -- the reference is ``REFERENCE_MISSING`` /
       ``REFERENCE_STALE``, no eligible forward path endpoint exists, or the
       endpoint is more than the frozen 5-second TTL away from ``due_at``.
    3. ``COMPLETE`` -- every frozen condition holds and every metric is produced.

    Every uncomputable metric stays ``NULL``; no ``0`` / ``NaN`` / ``Infinity``
    placeholder is ever substituted.

    ``observations`` must be the **complete** eligible durable path of the scope
    (``evidence_at < available_at <= due_at``). There is no truncation parameter
    and no internal observation ceiling: the durable layer loads the whole path,
    so "an incomplete path still classified COMPLETE" is not a representable
    state (task §8-§11). A missing observation is simply not supplied, which
    only ever *weakens* the result towards ``INSUFFICIENT_DATA``.

    ``structural_problem`` lets a durable orchestrator report a contradiction it
    detected on facts the pure core cannot see (for example: a ``FORWARD_PAPER``
    scope with no FIX-01 capture anchor at all). It must be an ``INVALID_*``
    reason; a data insufficiency is never reported this way.

    ``created_at`` is frozen to ``due_at`` so that retrying or restarting the
    evaluator over the same durable facts reproduces the same record hash.
    """

    if structural_problem is not None and not structural_problem.is_invalid:
        raise ValueError("structural_problem must be an INVALID_* reason")

    due_at = scope.due_at
    lifecycle = (
        OpportunityLifecycleAtHorizon.ACTIVE
        if due_at < scope.expires_at
        else OpportunityLifecycleAtHorizon.EXPIRED
    )
    selection = classify_forward_observations(scope=scope, observations=observations)
    endpoint = selection.endpoint
    path_points = selection.path_points

    structural_reason = (
        structural_problem
        if structural_problem is not None
        else _structural_invalid_reason(scope=scope, reference=reference)
    )
    # An outcome binds a durable observation id only when the calculator actually
    # accepted that observation: the reference authority whenever the reference
    # itself is `OK`, and the endpoint only for a COMPLETE outcome. A rejected
    # candidate is recorded in the diagnostics instead of being bound here.
    reference_observation_id: str | None = None
    end_observation_id: str | None = None
    metrics = _NO_METRICS

    if structural_reason is not None:
        reason = structural_reason
        status = OutcomeCalculationStatus.INVALID
        end_bid = end_ask = None
    elif reference.status is not ReferenceDataStatus.OK:
        reason = ForwardOutcomeReason(reference.status.value)
        status = OutcomeCalculationStatus.INSUFFICIENT_DATA
        end_bid = end_ask = None
    else:
        reference_observation_id = reference.observation_id
        end_bid = None if endpoint is None else endpoint.bid
        end_ask = None if endpoint is None else endpoint.ask
        if endpoint is None:
            reason = ForwardOutcomeReason.ENDPOINT_MISSING
            status = OutcomeCalculationStatus.INSUFFICIENT_DATA
        elif scope.due_at - endpoint.available_at > END_FRESHNESS_TTL:
            reason = ForwardOutcomeReason.ENDPOINT_STALE
            status = OutcomeCalculationStatus.INSUFFICIENT_DATA
        else:
            reason = ForwardOutcomeReason.COMPLETE
            status = OutcomeCalculationStatus.COMPLETE

    if status is OutcomeCalculationStatus.COMPLETE:
        assert reference.bid is not None and reference.ask is not None
        assert endpoint is not None and end_bid is not None and end_ask is not None
        end_observation_id = endpoint.observation_id
        reference_price = (reference.bid + reference.ask) / 2
        end_mid = (end_bid + end_ask) / 2
        path_returns = [0.0]
        for item in path_points:
            path_returns.append(((item.bid + item.ask) / 2) / reference_price - 1)
        metrics = _Metrics(
            reference_price=reference_price,
            end_bid=end_bid,
            end_ask=end_ask,
            mfe=max(path_returns),
            mae=min(path_returns),
            reference_return=end_mid / reference_price - 1,
            executable_long_return=end_bid / reference.ask - 1,
            cost_adjusted_forward_return=cost_adjusted_forward_return(
                reference_ask=reference.ask, end_bid=end_bid
            ),
        )

    return build_forward_outcome_contract(
        opportunity_id=scope.opportunity_id,
        evidence_id=scope.evidence_id,
        horizon=scope.horizon,
        outcome_revision=RUNTIME_OUTCOME_REVISION,
        due_at=due_at,
        source_type=scope.source_type,
        source_identity=scope.source_identity,
        cost_policy=COST_POLICY,
        cost_model_version=COST_MODEL_VERSION,
        calculator_version=CALCULATOR_VERSION,
        calculation_status=status,
        opportunity_lifecycle_at_horizon=lifecycle,
        reference_bbo_observation_id=reference_observation_id,
        end_bbo_observation_id=end_observation_id,
        reference_price=metrics.reference_price,
        end_bid=metrics.end_bid,
        end_ask=metrics.end_ask,
        mfe=metrics.mfe,
        mae=metrics.mae,
        reference_return=metrics.reference_return,
        executable_long_return=metrics.executable_long_return,
        cost_adjusted_forward_return=metrics.cost_adjusted_forward_return,
        completeness_diagnostics=_diagnostics(
            reason=reason,
            selection=selection,
            scope=scope,
            reference=reference,
            endpoint=endpoint,
            path_points=path_points,
        ),
        created_at=due_at,
    )
