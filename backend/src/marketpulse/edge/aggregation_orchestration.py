"""SE-02D-I03: population grouping and aggregate orchestration.

This module is the thin orchestration seam *between* two already-accepted
SE-02D layers. It owns no contract of its own and redefines neither authority:

* :mod:`marketpulse.edge.aggregation_snapshot` (I02) produces exactly one
  :class:`~marketpulse.edge.aggregation_snapshot.CurrentSnapshotProjection` per
  requested horizon: one PostgreSQL ``REPEATABLE READ READ ONLY`` snapshot, the
  database ``statement_timestamp()`` as ``as_of``, the fully folded visible
  Evidence chain and exact-horizon Outcome chain, and the revision-aware
  manifest;
* :mod:`marketpulse.edge.aggregation` (I01) turns one population's canonical
  scope facts into one deterministic :class:`~marketpulse.edge.aggregation.AggregationResult`.

I03 adds only the deterministic *many-populations* step in between::

    CurrentSnapshotProjection
        -> facts <-> manifest integrity gate
        -> group by the complete structural PopulationKey
        -> exactly one I01 aggregate() call per population
        -> tuple[AggregationResult, ...] ordered by PopulationKey.canonical_key()

Boundaries that are deliberately **not** crossed here:

* population identity is the structural :class:`PopulationKey` dataclass, and the
  grouping key is that dataclass itself -- not ``source_manifest_id``, not the
  Measurement Signature, not a delimiter-joined identity string;
* ``source_manifest_id`` stays provenance / stratification and never splits an
  aggregate; a mixed Measurement Signature stays one invocation and keeps I01's
  accepted ``INCOMPATIBLE_MEASUREMENT_SIGNATURES`` fail-closed status;
* a non-applicable ``market_type`` is never filtered here -- I01 owns
  applicability, including the ``NOT_APPLICABLE`` semantics;
* the revision-aware manifest I02 built is the manifest supplied to I01.
  ``build_ordered_input_manifest()`` is never used as a fallback, rows are never
  discarded, de-duplicated, fabricated or re-derived;
* every projection identity this module dereferences -- ``projection.horizon``,
  each ``fact.horizon`` and each ``fact.population_key`` -- is proven to be the
  Accepted runtime type first, so malformed or tampered input fails closed as
  :class:`AggregationOrchestrationError` rather than leaking an incidental
  ``AttributeError`` (SE02D-I03-R1);
* no statistic, threshold, maturity / coverage rule, fingerprint algorithm or
  KEEP / DOWNWEIGHT / KILL decision is recomputed here;
* no API, persistence, migration, scheduler or runtime host is involved.

``aggregate_projection`` is pure: given one projection it is a deterministic
function of that projection alone, and permuting ``facts`` / ``manifest`` cannot
change the returned tuple or any result inside it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .aggregation import (
    AggregationResult,
    CanonicalScopeFacts,
    PopulationKey,
    aggregate,
)
from .aggregation_snapshot import (
    CurrentSnapshotProjection,
    CurrentSnapshotRevisionReader,
)
from .models import ForwardHorizon

#: The logical scope identity on which facts and manifest entries must agree.
#: ``(opportunity_id, evidence_id, horizon)`` -- D01 section 9.2's manifest key.
LogicalIdentity = tuple[str, str, str]


class AggregationOrchestrationError(ValueError):
    """Fail-closed projection-level orchestration failure.

    Raised only for a facts <-> manifest / population-grouping integrity breach of
    one :class:`CurrentSnapshotProjection` (task sections 9 and 14). It is
    deliberately a *sibling* of
    :class:`~marketpulse.edge.aggregation.AggregationError` rather than a
    subclass: I03 never catches, re-wraps or swallows an I01 aggregation failure
    or an I02 snapshot-integrity failure, so those keep travelling as their own
    types.

    The message always names the violated invariant first, then the offending
    logical identity, so a test or a reviewer can identify the breach without
    parsing prose. Set-valued offenders (missing / extra / duplicate) are always
    reported through their smallest member, so the message never depends on the
    input iteration order.
    """


# --- facts / manifest integrity gate -------------------------------------------------------


def _require_text(value: Any, *, field: str, origin: str) -> str:
    """Fail closed unless ``value`` is a usable logical-identity string."""

    if not isinstance(value, str) or not value:
        raise AggregationOrchestrationError(
            f"malformed_{origin}_logical_identity:{field}:{type(value).__name__}"
        )
    return value


def _require_forward_horizon(value: Any, *, marker: str) -> None:
    """Fail closed unless ``value`` really is a :class:`ForwardHorizon` member.

    Neither :class:`~marketpulse.edge.aggregation_snapshot.CurrentSnapshotProjection`
    nor :class:`~marketpulse.edge.aggregation.CanonicalScopeFacts` runtime-validates
    the type of ``horizon``, so dereferencing ``.value`` on a malformed or tampered
    projection would otherwise escape this module's fail-closed boundary as an
    incidental ``AttributeError`` (SE02D-I03-R1).
    """

    if not isinstance(value, ForwardHorizon):
        raise AggregationOrchestrationError(f"{marker}:{type(value).__name__}")


def _require_population_key(value: Any) -> None:
    """Fail closed unless ``value`` really is a structural :class:`PopulationKey`.

    ``CanonicalScopeFacts.population_key`` is likewise unvalidated at runtime, so
    grouping on it or calling ``canonical_payload()`` on a tampered fact would
    otherwise raise an incidental error instead of this module's fail-closed type
    (SE02D-I03-R1).
    """

    if not isinstance(value, PopulationKey):
        raise AggregationOrchestrationError(
            f"malformed_fact_population_key:{type(value).__name__}"
        )


def _index_facts(
    projection: CurrentSnapshotProjection,
) -> dict[LogicalIdentity, CanonicalScopeFacts]:
    """Index every projected fact by its logical identity.

    Fails closed on a malformed projection horizon, on a malformed fact, on a fact
    whose horizon is not the projection's requested horizon (task section 9 rule 5)
    and on two facts that share one logical identity (rule 3). Nothing is silently
    dropped or merged.
    """

    _require_forward_horizon(
        projection.horizon, marker="malformed_projection_identity:horizon"
    )
    horizon_value = projection.horizon.value
    index: dict[LogicalIdentity, CanonicalScopeFacts] = {}
    duplicates: set[LogicalIdentity] = set()
    for fact in projection.facts:
        if not isinstance(fact, CanonicalScopeFacts):
            raise AggregationOrchestrationError(
                f"malformed_fact:not_canonical_scope_facts:{type(fact).__name__}"
            )
        _require_forward_horizon(
            fact.horizon, marker="malformed_fact_logical_identity:horizon"
        )
        _require_population_key(fact.population_key)
        opportunity_id = _require_text(
            fact.opportunity_id, field="opportunity_id", origin="fact"
        )
        evidence_id = _require_text(fact.evidence_id, field="evidence_id", origin="fact")
        if fact.horizon.value != horizon_value:
            raise AggregationOrchestrationError(
                f"fact_horizon_mismatch:{opportunity_id}:{evidence_id}:"
                f"expected={horizon_value}:got={fact.horizon.value}"
            )
        identity: LogicalIdentity = (opportunity_id, evidence_id, horizon_value)
        if identity in index:
            duplicates.add(identity)
        else:
            index[identity] = fact
    if duplicates:
        opportunity_id, evidence_id, horizon = min(duplicates)
        raise AggregationOrchestrationError(
            f"duplicate_fact_logical_identity:{opportunity_id}:{evidence_id}:{horizon}"
        )
    return index


def _index_manifest(
    projection: CurrentSnapshotProjection,
) -> dict[LogicalIdentity, Mapping[str, Any]]:
    """Index every revision-aware manifest entry by its logical identity.

    Fails closed on a non-mapping entry, on a missing / malformed identity field
    (task section 9 rule 8), on an entry whose horizon is not the projection's
    requested horizon (rule 6) and on two entries that share one logical identity
    (rule 4).
    """

    horizon_value = projection.horizon.value
    index: dict[LogicalIdentity, Mapping[str, Any]] = {}
    duplicates: set[LogicalIdentity] = set()
    for entry in projection.manifest:
        if not isinstance(entry, Mapping):
            raise AggregationOrchestrationError(
                f"malformed_manifest_entry:not_a_mapping:{type(entry).__name__}"
            )
        opportunity_id = _require_text(
            entry.get("opportunity_id"), field="opportunity_id", origin="manifest"
        )
        evidence_id = _require_text(entry.get("evidence_id"), field="evidence_id", origin="manifest")
        entry_horizon = _require_text(entry.get("horizon"), field="horizon", origin="manifest")
        if entry_horizon != horizon_value:
            raise AggregationOrchestrationError(
                f"manifest_horizon_mismatch:{opportunity_id}:{evidence_id}:"
                f"expected={horizon_value}:got={entry_horizon}"
            )
        identity: LogicalIdentity = (opportunity_id, evidence_id, horizon_value)
        if identity in index:
            duplicates.add(identity)
        else:
            index[identity] = entry
    if duplicates:
        opportunity_id, evidence_id, horizon = min(duplicates)
        raise AggregationOrchestrationError(
            f"duplicate_manifest_logical_identity:{opportunity_id}:{evidence_id}:{horizon}"
        )
    return index


def _require_one_to_one_mapping(
    fact_index: Mapping[LogicalIdentity, CanonicalScopeFacts],
    manifest_index: Mapping[LogicalIdentity, Mapping[str, Any]],
) -> None:
    """Prove a strict one-to-one facts <-> manifest correspondence.

    A fact with no manifest entry (task section 9 rule 1) and a manifest entry
    with no fact (rule 2) both fail closed. Neither side is ever padded,
    truncated or inferred to restore the correspondence (rule 9).
    """

    missing = sorted(set(fact_index) - set(manifest_index))
    if missing:
        opportunity_id, evidence_id, horizon = missing[0]
        raise AggregationOrchestrationError(
            f"fact_without_manifest_entry:{opportunity_id}:{evidence_id}:{horizon}"
        )
    extra = sorted(set(manifest_index) - set(fact_index))
    if extra:
        opportunity_id, evidence_id, horizon = extra[0]
        raise AggregationOrchestrationError(
            f"manifest_entry_without_fact:{opportunity_id}:{evidence_id}:{horizon}"
        )


def _require_declared_population_key(
    fact_index: Mapping[LogicalIdentity, CanonicalScopeFacts],
    manifest_index: Mapping[LogicalIdentity, Mapping[str, Any]],
) -> None:
    """Prove every manifest entry declares its fact's Population Key.

    Task section 9 rule 7. The comparison is structural, against the frozen
    ``PopulationKey.canonical_payload()`` projection -- never against a locally
    reconstructed key and never against a derived digest. Identities are visited
    in sorted order so the reported offender is deterministic.
    """

    for identity in sorted(fact_index):
        opportunity_id, evidence_id, horizon = identity
        declared = manifest_index[identity].get("population_key")
        if not isinstance(declared, Mapping):
            raise AggregationOrchestrationError(
                f"malformed_manifest_identity:population_key:{opportunity_id}:"
                f"{evidence_id}:{horizon}"
            )
        expected = fact_index[identity].population_key.canonical_payload()
        if dict(declared) != expected:
            raise AggregationOrchestrationError(
                f"manifest_population_key_mismatch:{opportunity_id}:{evidence_id}:{horizon}"
            )


# --- population grouping / manifest subset -------------------------------------------------


def _ordered_population_groups(
    fact_index: Mapping[LogicalIdentity, CanonicalScopeFacts],
) -> list[tuple[PopulationKey, list[CanonicalScopeFacts]]]:
    """Group facts by the complete structural PopulationKey, deterministically.

    Grouping authority is :class:`PopulationKey` equality/hash -- the seven frozen
    fields themselves (task section 6). ``source_manifest_id``, the Measurement
    Signature, outcome / calculator / cost versions, lifecycle and status are not
    grouping inputs. Ordering is by :meth:`PopulationKey.canonical_key`, a
    collision-safe ordering derived through the accepted G5 boundary; ordering is
    *not* identity authority (task section 7).
    """

    grouped: dict[PopulationKey, list[CanonicalScopeFacts]] = {}
    for fact in fact_index.values():
        grouped.setdefault(fact.population_key, []).append(fact)
    return sorted(grouped.items(), key=lambda item: item[0].canonical_key())


def _manifest_subset(
    facts: Sequence[CanonicalScopeFacts],
    manifest_index: Mapping[LogicalIdentity, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    """Select and order one population's revision-aware manifest entries.

    Entries are carried through verbatim -- ``no_outcome``,
    ``evidence_revision_identities``, ``outcome_revision_identities`` and every
    Accepted I01 base field survive unchanged (task section 10) -- and ordered
    deterministically by ``(opportunity_id, evidence_id, horizon)``.
    """

    horizon_value = facts[0].horizon.value
    selected = [
        manifest_index[(fact.opportunity_id, fact.evidence_id, horizon_value)] for fact in facts
    ]
    return tuple(
        sorted(
            selected,
            key=lambda entry: (
                entry["opportunity_id"],
                entry["evidence_id"],
                entry["horizon"],
            ),
        )
    )


# --- public surface ------------------------------------------------------------------------


def aggregate_projection(
    projection: CurrentSnapshotProjection,
) -> tuple[AggregationResult, ...]:
    """Aggregate one I02 projection into one result per structural population.

    The projection is validated as one complete unit first, then each distinct
    :class:`PopulationKey` receives exactly one I01 :func:`aggregate` call. An
    empty projection is authoritative -- it carries its own ``horizon`` and
    ``as_of`` -- but yields zero populations and therefore the empty tuple, with
    no :func:`aggregate` invocation at all.

    Returns the results ordered by :meth:`PopulationKey.canonical_key`. I01 and
    I02 failures propagate unchanged; this function only ever raises
    :class:`AggregationOrchestrationError` for a projection-level integrity
    breach.
    """

    fact_index = _index_facts(projection)
    manifest_index = _index_manifest(projection)
    _require_one_to_one_mapping(fact_index, manifest_index)
    _require_declared_population_key(fact_index, manifest_index)

    results: list[AggregationResult] = []
    for population_key, facts in _ordered_population_groups(fact_index):
        results.append(
            aggregate(
                population_key=population_key,
                horizon=projection.horizon,
                as_of=projection.as_of,
                facts=facts,
                ordered_input_manifest=_manifest_subset(facts, manifest_index),
            )
        )
    return tuple(results)


async def aggregate_current_snapshot(
    reader: CurrentSnapshotRevisionReader,
    horizon: ForwardHorizon,
) -> tuple[AggregationResult, ...]:
    """Read one current snapshot and aggregate it.

    Exactly one ``reader.read(horizon)`` call is made, and the projection it
    returns is passed unchanged to :func:`aggregate_projection`. There is no
    second read, no second session, no second snapshot, no retry loop, no
    database query of its own and no Python-generated ``as_of`` (task section 16).
    """

    projection = await reader.read(horizon)
    return aggregate_projection(projection)


__all__ = [
    "AggregationOrchestrationError",
    "LogicalIdentity",
    "aggregate_current_snapshot",
    "aggregate_projection",
]
