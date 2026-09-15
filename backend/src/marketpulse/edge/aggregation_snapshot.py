"""SE-02D-I02: current-snapshot revision folding projection.

Ownership boundary (task card, section 17-18)
--------------------------------------------
This layer owns, for *one* ``REPEATABLE READ READ ONLY`` PostgreSQL snapshot:

* read ``statement_timestamp()`` as the snapshot ``as_of`` (never the Python clock);
* validate and fold the *full visible* Evidence revision chain per logical
  opportunity into a canonical Evidence head;
* validate and fold the *full visible* exact-horizon Outcome revision chain per
  ``(opportunity_id, evidence_id)`` into a canonical Outcome head (or an explicit
  ``NO_OUTCOME`` marker);
* project one ``CanonicalScopeFacts`` per canonical Evidence head, carrying the
  revision-aware manifest.

It deliberately does **not** aggregate statistics, does **not** expose a
historical ``as_of`` interface, and does **not** call or reuse ``aggregate()``
from :mod:`marketpulse.edge.aggregation`. Aggregation (I01) is a separate,
already-accepted layer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    EdgeForwardOutcomeRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.aggregation import (
    CanonicalScopeFacts,
    MeasurementSignature,
    PopulationKey,
    build_ordered_input_manifest,
)
from marketpulse.edge.forward import forward_due_at
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceRevision,
    EvidenceSource,
    ForwardHorizon,
    ForwardOutcomeContract,
    OpportunityLifecycleAtHorizon,
    OutcomeCalculationStatus,
    ReferenceDataStatus,
)
from marketpulse.market_data.models import MarketType


class SnapshotIntegrityError(Exception):
    """Raised when the full visible revision state fails a folding invariant.

    Carries a tuple of stable, collision-safe conflict identifiers. The
    identifiers are the semantic authority for *what* failed; they are never
    derived from a digest and are always wrapped in a single-element tuple so
    ``tuple(conflicts)`` yields exactly one string per conflict (SE02D-I01-R1).
    """

    def __init__(self, conflicts: Sequence[str]) -> None:
        self.conflicts = tuple(conflicts)
        super().__init__("; ".join(self.conflicts))


@dataclass(frozen=True, slots=True)
class _EvidenceFold:
    """One validated Evidence revision chain: canonical head + folded tail."""

    opportunity_id: str
    canonical: EvidenceRevision
    folded: tuple[EvidenceRevision, ...]


@dataclass(frozen=True, slots=True)
class _OutcomeFold:
    """One validated exact-scope Outcome revision chain: canonical head + tail."""

    opportunity_id: str
    evidence_id: str
    canonical: ForwardOutcomeContract
    folded: tuple[ForwardOutcomeContract, ...]


@dataclass(frozen=True, slots=True)
class CurrentSnapshotProjection:
    """The revision-aware projection of one database snapshot.

    ``horizon`` is carried explicitly rather than being inferred from the
    projected facts: an empty snapshot has no facts at all, yet it still has a
    well-defined requested horizon (task section 16-17).
    """

    as_of: datetime
    horizon: ForwardHorizon
    facts: tuple[CanonicalScopeFacts, ...]
    manifest: tuple[dict[str, Any], ...]

    def filter_by_population_key(
        self, key: PopulationKey
    ) -> tuple[CanonicalScopeFacts, ...]:
        return tuple(fact for fact in self.facts if fact.population_key == key)


# --- Rehydration (record -> Accepted contract, with corruption fails-closed) ----------


def _evidence_from_record(record: EdgeOpportunityEvidenceRecord) -> EvidenceRevision:
    """Rebuild one Accepted ``EvidenceRevision`` from its durable row.

    The stored ``evidence_hash`` / ``feature_snapshot_hash`` are carried through
    verbatim so the frozen :class:`EvidenceRevision` validators re-derive and
    compare them; any tampering with the on-disk hash fails closed.
    """
    try:
        return EvidenceRevision(
            evidence_id=record.evidence_id,
            opportunity_id=record.opportunity_id,
            candidate_id=record.candidate_id,
            family_id=EdgeFamily(record.family_id),
            family_version=record.family_version,
            instrument_id=record.instrument_id,
            market_type=MarketType(record.market_type),
            evidence_revision=record.evidence_revision,
            evidence_contract_version=record.evidence_contract_version,
            evidence_hash=record.evidence_hash,
            feature_snapshot_hash=record.feature_snapshot_hash,
            feature_snapshot_hash_version=record.feature_snapshot_hash_version,
            supersedes_evidence_id=record.supersedes_evidence_id,
            detected_at=record.detected_at,
            evidence_at=record.evidence_at,
            expires_at=record.expires_at,
            source_type=EvidenceSource(record.source_type),
            source_identity=record.source_identity,
            source_manifest_id=record.source_manifest_id,
            reference_bid=record.reference_bid,
            reference_ask=record.reference_ask,
            reference_received_at=record.reference_received_at,
            reference_data_status=ReferenceDataStatus(record.reference_data_status),
            evidence_payload=record.evidence_payload,
            feature_snapshot_payload=record.feature_snapshot_payload,
            created_at=record.created_at,
        )
    except (ValueError, TypeError) as error:
        raise SnapshotIntegrityError(
            (
                (f"evidence_rehydration_failed:{record.opportunity_id}:"
                f"{record.evidence_revision}:{type(error).__name__}"),
            )
        ) from error


def _outcome_from_record(record: EdgeForwardOutcomeRecord) -> ForwardOutcomeContract:
    """Rebuild one Accepted ``ForwardOutcomeContract`` from its durable row."""
    try:
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
            completeness_diagnostics=record.completeness_diagnostics,
            cost_policy=record.cost_policy,
            cost_model_version=record.cost_model_version,
            calculator_version=record.calculator_version,
            calculation_digest=record.calculation_digest,
            calculation_digest_version=record.calculation_digest_version,
            outcome_record_hash=record.outcome_record_hash,
            outcome_record_hash_version=record.outcome_record_hash_version,
            created_at=record.created_at,
        )
    except (ValueError, TypeError) as error:
        raise SnapshotIntegrityError(
            (
                (f"outcome_rehydration_failed:{record.opportunity_id}:"
                f"{record.evidence_id}:{record.outcome_revision}:{type(error).__name__}"),
            )
        ) from error


# --- Evidence chain folding --------------------------------------------------------------


def _fold_evidence_chains(
    evidence_by_opportunity: Mapping[str, Sequence[EvidenceRevision]],
) -> dict[str, _EvidenceFold]:
    """Validate every opportunity's full visible Evidence chain and fold it.

    Rules (D01 section 6 / task section 18): revisions begin at 1, are contiguous,
    contain no duplicate, N>1 supersedes exactly N-1, revision 1 supersedes
    nothing, and every row keeps the same frozen logical facts. Any violation
    fails closed.
    """
    folds: dict[str, _EvidenceFold] = {}
    for opportunity_id, revisions in evidence_by_opportunity.items():
        ordered = sorted(revisions, key=lambda item: item.evidence_revision)
        seen: set[int] = set()
        expected = 1
        for rev in ordered:
            if rev.evidence_revision in seen:
                raise SnapshotIntegrityError(
                    (f"evidence_duplicate_revision:{opportunity_id}:{rev.evidence_revision}",)
                )
            seen.add(rev.evidence_revision)
            if rev.evidence_revision != expected:
                raise SnapshotIntegrityError(
                    (
                        (f"evidence_revision_gap:{opportunity_id}:"
                        f"expected={expected}:got={rev.evidence_revision}"),
                    )
                )
            expected += 1

        anchor = ordered[0]
        frozen = (
            anchor.family_id,
            anchor.family_version,
            anchor.instrument_id,
            anchor.candidate_id,
            anchor.market_type,
        )
        previous: EvidenceRevision | None = None
        for rev in ordered:
            if (
                rev.family_id != frozen[0]
                or rev.family_version != frozen[1]
                or rev.instrument_id != frozen[2]
                or rev.candidate_id != frozen[3]
                or rev.market_type != frozen[4]
            ):
                raise SnapshotIntegrityError(
                    (f"evidence_logical_fact_mutation:{opportunity_id}:{rev.evidence_revision}",)
                )
            if rev.evidence_revision == 1:
                if rev.supersedes_evidence_id is not None:
                    raise SnapshotIntegrityError(
                        (f"evidence_rev1_supersedes:{opportunity_id}:{rev.evidence_revision}",)
                    )
            else:
                if rev.supersedes_evidence_id is None:
                    raise SnapshotIntegrityError(
                        (f"evidence_missing_supersedes:{opportunity_id}:{rev.evidence_revision}",)
                    )
                if previous is None or rev.supersedes_evidence_id != previous.evidence_id:
                    raise SnapshotIntegrityError(
                        (
                            (f"evidence_wrong_supersedes:{opportunity_id}:"
                            f"{rev.evidence_revision}:expected="
                            f"{previous.evidence_id if previous is not None else None}"),
                        )
                    )
            previous = rev

        folds[opportunity_id] = _EvidenceFold(
            opportunity_id=opportunity_id,
            canonical=ordered[-1],
            folded=tuple(ordered[:-1]),
        )
    return folds


# --- Outcome chain folding ---------------------------------------------------------------


def _fold_outcome_chains(
    outcomes_by_scope: Mapping[tuple[str, str], Sequence[ForwardOutcomeContract]],
) -> dict[tuple[str, str], _OutcomeFold]:
    """Validate every exact-scope Outcome chain and fold to a canonical head.

    Scope is ``(opportunity_id, evidence_id)`` within the requested horizon. Rules
    (D01 section 6 / task section 18): revisions begin at 1, are contiguous,
    contain no duplicate, N>1 supersedes exactly N-1, revision 1 supersedes
    nothing, and every row keeps the same opportunity_id / evidence_id / horizon.
    Any violation fails closed.
    """
    folds: dict[tuple[str, str], _OutcomeFold] = {}
    for (opportunity_id, evidence_id), revisions in outcomes_by_scope.items():
        ordered = sorted(revisions, key=lambda item: item.outcome_revision)
        seen: set[int] = set()
        expected = 1
        for rev in ordered:
            if rev.outcome_revision in seen:
                raise SnapshotIntegrityError(
                    (
                        (f"outcome_duplicate_revision:{opportunity_id}:"
                        f"{evidence_id}:{rev.outcome_revision}"),
                    )
                )
            seen.add(rev.outcome_revision)
            if rev.outcome_revision != expected:
                raise SnapshotIntegrityError(
                    (
                        (f"outcome_revision_gap:{opportunity_id}:{evidence_id}:"
                        f"expected={expected}:got={rev.outcome_revision}"),
                    )
                )
            expected += 1

        previous: ForwardOutcomeContract | None = None
        for rev in ordered:
            if rev.opportunity_id != opportunity_id or rev.evidence_id != evidence_id:
                raise SnapshotIntegrityError(
                    (
                        (f"outcome_scope_drift:{opportunity_id}:{evidence_id}:"
                        f"{rev.outcome_revision}"),
                    )
                )
            if rev.outcome_revision == 1:
                if rev.supersedes_outcome_id is not None:
                    raise SnapshotIntegrityError(
                        (f"outcome_rev1_supersedes:{opportunity_id}:{evidence_id}",)
                    )
            else:
                if rev.supersedes_outcome_id is None:
                    raise SnapshotIntegrityError(
                        (
                            (f"outcome_missing_supersedes:{opportunity_id}:"
                            f"{evidence_id}:{rev.outcome_revision}"),
                        )
                    )
                if previous is None or rev.supersedes_outcome_id != previous.outcome_id:
                    raise SnapshotIntegrityError(
                        (
                            (f"outcome_wrong_supersedes:{opportunity_id}:"
                            f"{evidence_id}:{rev.outcome_revision}"),
                        )
                    )
            previous = rev

        folds[(opportunity_id, evidence_id)] = _OutcomeFold(
            opportunity_id=opportunity_id,
            evidence_id=evidence_id,
            canonical=ordered[-1],
            folded=tuple(ordered[:-1]),
        )
    return folds


# --- Cross-integrity (canonical Evidence <-> canonical Outcome) -------------------------


def _check_cross_integrity(
    evidence: EvidenceRevision,
    outcome: ForwardOutcomeContract | None,
    *,
    horizon: ForwardHorizon,
) -> None:
    """Fail closed if the canonical Outcome is inconsistent with its Evidence.

    The canonical Outcome must agree with the canonical Evidence on the *whole*
    linking contract -- ``opportunity_id``, ``evidence_id``, ``horizon``,
    ``source_type``, ``source_identity`` and the horizon-derived ``due_at``
    (task section 7). Neither side is ever normalized onto the other, and a
    matching ``source_identity`` can never hide a ``source_type`` mismatch.
    """
    if outcome is None:
        return
    if outcome.opportunity_id != evidence.opportunity_id:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_opportunity_mismatch:{evidence.opportunity_id}:"
                f"{evidence.evidence_id}:outcome={outcome.opportunity_id}"),
            )
        )
    if outcome.evidence_id != evidence.evidence_id:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_evidence_id_mismatch:{evidence.opportunity_id}:"
                f"expected={evidence.evidence_id}:outcome={outcome.evidence_id}"),
            )
        )
    if outcome.horizon != horizon:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_horizon_mismatch:{evidence.opportunity_id}:"
                f"{evidence.evidence_id}:expected={horizon.value}:"
                f"got={outcome.horizon.value}"),
            )
        )
    if outcome.source_type != evidence.source_type:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_source_type_mismatch:{evidence.opportunity_id}:"
                f"{evidence.evidence_id}:evidence={evidence.source_type.value}:"
                f"outcome={outcome.source_type.value}"),
            )
        )
    if evidence.source_identity != outcome.source_identity:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_source_mismatch:{evidence.opportunity_id}:"
                f"{evidence.evidence_id}:evidence={evidence.source_identity}:"
                f"outcome={outcome.source_identity}"),
            )
        )
    expected_due_at = forward_due_at(evidence.evidence_at, horizon)
    if outcome.due_at != expected_due_at:
        raise SnapshotIntegrityError(
            (
                (f"evidence_outcome_due_at_mismatch:{evidence.opportunity_id}:"
                f"{evidence.evidence_id}:expected={expected_due_at.isoformat()}:"
                f"got={outcome.due_at.isoformat()}"),
            )
        )


# --- Projection ---------------------------------------------------------------------------


def _project(
    evidence_folds: Mapping[str, _EvidenceFold],
    outcome_folds: Mapping[tuple[str, str], _OutcomeFold],
    horizon: ForwardHorizon,
    as_of: datetime,
) -> CurrentSnapshotProjection:
    """Project one ``CanonicalScopeFacts`` per canonical Evidence head.

    For each canonical Evidence head, the exact-scope Outcome chain (same
    ``(opportunity_id, evidence_id)``) is paired if present; otherwise the
    explicit ``NO_OUTCOME`` marker is emitted. Outcomes attached to *folded*
    Evidence revisions are counted as excluded and never enter the economic
    facts or the canonical scope's outcome identities.
    """
    folded_evidence_ids: dict[str, set[str]] = {}
    for opportunity_id, efold in evidence_folds.items():
        folded_evidence_ids.setdefault(opportunity_id, set())
        for rev in efold.folded:
            folded_evidence_ids[opportunity_id].add(rev.evidence_id)

    facts: list[CanonicalScopeFacts] = []
    # I02 owns only the revision-chain identities. Every *base* manifest field
    # stays I01's authority (``build_ordered_input_manifest``); the extension is
    # collected here and merged onto the I01 base entries at the end of this
    # function, so no canonical manifest field is ever re-derived in I02.
    revision_identities: dict[
        tuple[str, str, str], tuple[bool, list[dict[str, Any]], list[dict[str, Any]]]
    ] = {}

    for opportunity_id, efold in evidence_folds.items():
        canonical_evidence = efold.canonical
        scope = (opportunity_id, canonical_evidence.evidence_id)
        outcome_fold = outcome_folds.get(scope)
        canonical_outcome = outcome_fold.canonical if outcome_fold is not None else None

        _check_cross_integrity(canonical_evidence, canonical_outcome, horizon=horizon)

        population_key = PopulationKey(
            family_id=canonical_evidence.family_id,
            family_version=canonical_evidence.family_version,
            instrument_id=canonical_evidence.instrument_id,
            market_type=canonical_evidence.market_type,
            source_type=canonical_evidence.source_type,
            source_identity=canonical_evidence.source_identity,
            evidence_contract_version=canonical_evidence.evidence_contract_version,
        )
        due_at = forward_due_at(canonical_evidence.evidence_at, horizon)

        excluded = 0
        for oid, ofold in outcome_folds.items():
            if oid[0] != opportunity_id:
                continue
            if oid[1] in folded_evidence_ids.get(opportunity_id, set()):
                excluded += len(ofold.folded) + 1

        if canonical_outcome is None:
            fact = CanonicalScopeFacts(
                opportunity_id=opportunity_id,
                population_key=population_key,
                horizon=horizon,
                evidence_id=canonical_evidence.evidence_id,
                evidence_revision=canonical_evidence.evidence_revision,
                evidence_hash=canonical_evidence.evidence_hash,
                evidence_at=canonical_evidence.evidence_at,
                due_at=due_at,
                source_manifest_id=canonical_evidence.source_manifest_id,
                reference_data_status=canonical_evidence.reference_data_status,
                outcome_id=None,
                folded_evidence_revision_count=len(efold.folded),
                outcomes_excluded_with_folded_evidence=excluded,
            )
            outcome_identities: list[dict[str, Any]] = []
        else:
            measurement_signature = MeasurementSignature(
                outcome_contract_version=canonical_outcome.outcome_contract_version,
                calculator_version=canonical_outcome.calculator_version,
                cost_policy=canonical_outcome.cost_policy,
                cost_model_version=canonical_outcome.cost_model_version,
                outcome_source_type=canonical_outcome.source_type,
                outcome_source_identity=canonical_outcome.source_identity,
            )
            fact = CanonicalScopeFacts(
                opportunity_id=opportunity_id,
                population_key=population_key,
                horizon=horizon,
                evidence_id=canonical_evidence.evidence_id,
                evidence_revision=canonical_evidence.evidence_revision,
                evidence_hash=canonical_evidence.evidence_hash,
                evidence_at=canonical_evidence.evidence_at,
                due_at=canonical_outcome.due_at,
                source_manifest_id=canonical_evidence.source_manifest_id,
                reference_data_status=canonical_evidence.reference_data_status,
                outcome_id=canonical_outcome.outcome_id,
                outcome_revision=canonical_outcome.outcome_revision,
                outcome_record_hash=canonical_outcome.outcome_record_hash,
                outcome_status=canonical_outcome.calculation_status,
                outcome_reason=canonical_outcome.completeness_diagnostics.get("reason"),
                measurement_signature=measurement_signature,
                cost_adjusted_forward_return=canonical_outcome.cost_adjusted_forward_return,
                reference_return=canonical_outcome.reference_return,
                executable_long_return=canonical_outcome.executable_long_return,
                mfe=canonical_outcome.mfe,
                mae=canonical_outcome.mae,
                lifecycle=canonical_outcome.opportunity_lifecycle_at_horizon,
                folded_evidence_revision_count=len(efold.folded),
                folded_outcome_revision_count=len(outcome_fold.folded),
                outcomes_excluded_with_folded_evidence=excluded,
            )
            ordered_outcomes = sorted(
                [canonical_outcome, *outcome_fold.folded],
                key=lambda item: item.outcome_revision,
            )
            outcome_identities = [
                {
                    "outcome_id": rev.outcome_id,
                    "outcome_revision": rev.outcome_revision,
                    "outcome_record_hash": rev.outcome_record_hash,
                    "role": "CANONICAL" if rev is canonical_outcome else "FOLDED_OUTCOME",
                }
                for rev in ordered_outcomes
            ]

        ordered_evidence = sorted(
            [canonical_evidence, *efold.folded],
            key=lambda item: item.evidence_revision,
        )
        evidence_identities = [
            {
                "evidence_id": rev.evidence_id,
                "evidence_revision": rev.evidence_revision,
                "evidence_hash": rev.evidence_hash,
                "role": "CANONICAL" if rev is canonical_evidence else "FOLDED_EVIDENCE",
            }
            for rev in ordered_evidence
        ]

        facts.append(fact)
        revision_identities[(opportunity_id, canonical_evidence.evidence_id, horizon.value)] = (
            canonical_outcome is None,
            evidence_identities,
            outcome_identities,
        )

    base_manifest = build_ordered_input_manifest(facts, as_of=as_of)
    facts_by_key = {
        (fact.opportunity_id, fact.evidence_id, fact.horizon.value): fact for fact in facts
    }

    ordered_facts: list[CanonicalScopeFacts] = []
    manifest: list[dict[str, Any]] = []
    for base_entry in base_manifest:
        key = (base_entry["opportunity_id"], base_entry["evidence_id"], base_entry["horizon"])
        no_outcome, ev_identities, out_identities = revision_identities[key]
        ordered_facts.append(facts_by_key[key])
        manifest.append(
            {
                **base_entry,
                "no_outcome": no_outcome,
                "evidence_revision_identities": ev_identities,
                "outcome_revision_identities": out_identities,
            }
        )

    return CurrentSnapshotProjection(
        as_of=as_of,
        horizon=horizon,
        facts=tuple(ordered_facts),
        manifest=tuple(manifest),
    )


# --- Reader (one REPEATABLE READ READ ONLY snapshot) ------------------------------------


class CurrentSnapshotRevisionReader:
    """Read the current snapshot and fold it into a revision-aware projection.

    Exactly one transaction is opened per :meth:`read`: ``SET TRANSACTION
    ISOLATION LEVEL REPEATABLE READ READ ONLY`` followed by
    ``SELECT statement_timestamp()`` as the ``as_of`` clock, after which the
    visible Evidence / Outcome revisions are folded and projected. There is no
    historical ``as_of`` parameter (task section 13): the snapshot is always the
    database's current statement timestamp.
    """

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def read(self, horizon: ForwardHorizon) -> CurrentSnapshotProjection:
        async with self._factory() as session:
            await session.begin()
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            as_of = (
                await session.scalar(text("SELECT statement_timestamp()"))
            ).astimezone(UTC)
            projection = await self._read_in_session(session, horizon, as_of)
            await session.rollback()
            return projection

    async def _read_in_session(
        self,
        session: AsyncSession,
        horizon: ForwardHorizon,
        as_of: datetime,
    ) -> CurrentSnapshotProjection:
        evidence_result = await session.execute(select(EdgeOpportunityEvidenceRecord))
        evidence_records = evidence_result.scalars().all()

        outcome_result = await session.execute(
            select(EdgeForwardOutcomeRecord).where(
                EdgeForwardOutcomeRecord.horizon == horizon.value
            )
        )
        outcome_records = outcome_result.scalars().all()

        evidence_by_opportunity: dict[str, list[EvidenceRevision]] = {}
        for record in evidence_records:
            rev = _evidence_from_record(record)
            evidence_by_opportunity.setdefault(rev.opportunity_id, []).append(rev)

        outcomes_by_scope: dict[tuple[str, str], list[ForwardOutcomeContract]] = {}
        for record in outcome_records:
            contract = _outcome_from_record(record)
            outcomes_by_scope.setdefault(
                (contract.opportunity_id, contract.evidence_id), []
            ).append(contract)

        evidence_folds = _fold_evidence_chains(evidence_by_opportunity)
        outcome_folds = _fold_outcome_chains(outcomes_by_scope)
        return _project(evidence_folds, outcome_folds, horizon, as_of)
