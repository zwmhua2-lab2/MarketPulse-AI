"""PRE-01B-I2 migration / schema verification against a real disposable PostgreSQL 16.

This script executes the *accepted* PRE-01B-D2 schema decision
(``docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`` §24)
against a throw-away database and reports the durable facts it observed. It is evidence
generation, not a unit test: every claim printed here was produced by PostgreSQL itself.

Isolation contract (task §29):

* the target database is always created and dropped by this script;
* the admin DSN comes from ``PRE_01B_I2_ADMIN_URL`` and must point at a **disposable**
  instance, never at the shared project database. The script refuses to run against the
  accepted project default (``127.0.0.1:5432``) so a mis-invocation cannot touch it;
* no existing project volume, container or database is modified.

What it proves:

1. migration head advances ``20260913_0009`` -> ``20260917_0010``, single head, no
   duplicate and no dangling revision;
2. historical truth is preserved: Evidence rows written before the upgrade are fixed to
   ``LEGACY_PRE_I2`` and rows written after it default to ``UNSTAGED``;
3. legacy ``decision_snapshots`` / ``ai_decisions`` rows stay valid after the additive
   extensions;
4. every frozen conditional CHECK rejects its negative shape with the exact named
   constraint, and accepts its positive shape;
5. the deferred composite foreign keys really are deferred: a single transaction may
   insert both halves of the Evidence <-> Invocation cycle in either order and commit;
6. the winner fences (partial unique Invocation linkage, invocations attempt numbering,
   experiment/pair/arm uniqueness, same-Invocation retry lineage) refuse duplicates;
7. ``downgrade`` back to ``20260913_0009`` then ``upgrade`` again both succeed.

Usage::

    PRE_01B_I2_ADMIN_URL=postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5450/marketpulse \
        py -3.14 scripts/verify_pre_01b_i2_advisory_schema.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

OLD_HEAD = "20260913_0009"
NEW_HEAD = "20260917_0010"
#: The accepted shared database. Reaching it would violate the task's isolation contract.
FORBIDDEN_HOSTS = ("127.0.0.1:5432", "localhost:5432")

DEFAULT_ADMIN_URL = "postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5450/marketpulse"

# ---------------------------------------------------------------------------- results

_FAILURES: list[str] = []
_CHECKS = 0


def ok(label: str, detail: str = "") -> None:
    global _CHECKS
    _CHECKS += 1
    print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))


def fail(label: str, detail: str = "") -> None:
    _FAILURES.append(label)
    print(f"  FAIL  {label}" + (f"  [{detail}]" if detail else ""))


def expect(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        ok(label, detail)
    else:
        fail(label, detail)


def expect_rejected(
    label: str, sql: str, needle: str | tuple[str, ...], params: dict | None = None
) -> None:
    """Run ``sql`` and require PostgreSQL to refuse it, naming one of ``needle``.

    A tuple of acceptable constraint names is used where more than one frozen CHECK
    legitimately forbids the same shape: PostgreSQL does not promise an evaluation order
    among CHECK constraints, so pinning a single winner would be testing the planner
    rather than the contract. The assertion that matters -- "this shape is refused" -- is
    unchanged.
    """

    accepted = (needle,) if isinstance(needle, str) else needle
    try:
        _run_sql(_CURRENT_URL, sql, params)
    except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
        message = " ".join(str(arg) for arg in exc.args) + repr(exc)
        hit = next((name for name in accepted if name in message), None)
        if hit is not None:
            ok(label, f"refused by {hit}")
        else:
            fail(label, f"refused by an unexpected constraint: {message[:220]}")
        return
    fail(label, "PostgreSQL accepted a shape the accepted contract forbids")


def expect_accepted(label: str, sql: str, params: dict | None = None) -> None:
    try:
        _run_sql(_CURRENT_URL, sql, params)
    except Exception as exc:  # noqa: BLE001 - acceptance is the assertion
        fail(label, f"refused: {' '.join(str(a) for a in exc.args)[:220]}")
        return
    ok(label)


# ---------------------------------------------------------------------------- plumbing

_ADMIN_URL = os.environ.get("PRE_01B_I2_ADMIN_URL", DEFAULT_ADMIN_URL)
#: The disposable database the probes are currently pointed at. ``_disposable_database``
#: sets it, so a probe can never silently run against the admin/primary database.
_CURRENT_URL = _ADMIN_URL


def _guard_isolation(url: str) -> None:
    if any(host in url for host in FORBIDDEN_HOSTS):
        raise SystemExit(
            "refusing to run: PRE_01B_I2_ADMIN_URL points at the shared project database. "
            "PRE-01B-I2 requires a NEW disposable PostgreSQL instance."
        )


def _url_for(database_name: str) -> str:
    return f"{_ADMIN_URL.rsplit('/', 1)[0]}/{database_name}"


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


async def _execute(url: str, statement: str, params: dict | None = None) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement), params or {})
    finally:
        await engine.dispose()


async def _scalar(url: str, statement: str, params: dict | None = None):
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return await connection.scalar(text(statement), params or {})
    finally:
        await engine.dispose()


async def _rows(url: str, statement: str, params: dict | None = None) -> list:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(statement), params or {})
            return list(result)
    finally:
        await engine.dispose()


def _run_sql(url: str, statement: str, params: dict | None = None) -> None:
    asyncio.run(_execute(url, statement, params))


def _as_scalar(url: str, statement: str, params: dict | None = None):
    return asyncio.run(_scalar(url, statement, params))


def _as_rows(url: str, statement: str, params: dict | None = None) -> list:
    return asyncio.run(_rows(url, statement, params))


async def _run_in_one_transaction(url: str, statements: list[tuple[str, dict]]) -> None:
    """Execute every statement inside ONE transaction, then commit.

    Deferred constraints are only exercised if the statements really share a transaction,
    so this deliberately does not autocommit between them.
    """

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for statement, params in statements:
                    await connection.execute(text(statement), params)
            except BaseException:
                await transaction.rollback()
                raise
            await transaction.commit()
    finally:
        await engine.dispose()


@contextmanager
def _disposable_database(label: str):
    global _CURRENT_URL
    name = f"mp_i2_{label}_{uuid4().hex[:12]}"
    _run_sql(_ADMIN_URL, f'CREATE DATABASE "{name}"')
    url = _url_for(name)
    _CURRENT_URL = url
    try:
        yield url
    finally:
        _CURRENT_URL = _ADMIN_URL
        _run_sql(
            _ADMIN_URL,
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
        )
        _run_sql(_ADMIN_URL, f'DROP DATABASE "{name}"')


# ---------------------------------------------------------------------------- fixtures

EVIDENCE_COLUMNS = (
    "evidence_id, opportunity_id, candidate_id, family_id, family_version, instrument_id, "
    "market_type, evidence_revision, evidence_contract_version, evidence_hash, "
    "feature_snapshot_hash, feature_snapshot_hash_version, detected_at, evidence_at, expires_at, "
    "source_type, source_identity, source_manifest_id, reference_data_status, "
    "reference_bid, reference_ask, reference_received_at, evidence_payload, "
    "feature_snapshot_payload, created_at"
)
EVIDENCE_VALUES = (
    ":evidence_id, :opportunity_id, 'sc_breakout_1', 'BREAKOUT_RETEST', 'f1', 'BTC-USDT', "
    "'SPOT', :revision, 'se02-evidence-v1', :evidence_hash, :feature_hash, 'v1', "
    "now(), now(), now() + interval '5 minutes', 'FORWARD_PAPER', 'okx-forward', 'm1', "
    "'OK', 100.0, 100.5, now(), '{}'::jsonb, '{}'::jsonb, now()"
)


def _evidence_insert(
    evidence_id: str, opportunity_id: str, revision: int = 1, hash_suffix: str = "a"
) -> tuple[str, dict]:
    return (
        f"INSERT INTO edge_opportunity_evidence ({EVIDENCE_COLUMNS}) VALUES ({EVIDENCE_VALUES})",
        {
            "evidence_id": evidence_id,
            "opportunity_id": opportunity_id,
            "revision": revision,
            "evidence_hash": (hash_suffix * 64)[:64],
            "feature_hash": (hash_suffix * 64)[:64],
        },
    )


def _snapshot_insert(snapshot_id: str) -> tuple[str, dict]:
    return (
        (
            "INSERT INTO decision_snapshots (snapshot_id, instrument_id, symbol, run_mode, "
            "state_version, config_version, snapshot_version, created_at, payload) "
            "VALUES (:sid, 'BTC-USDT', 'BTC-USDT', 'TEST', 1, 'c1', 'v1', now(), '{}'::jsonb)"
        ),
        {"sid": snapshot_id},
    )


def _invocation_insert(
    invocation_id: str,
    snapshot_id: str,
    evidence_id: str,
    opportunity_id: str,
    *,
    experiment_id: str = "exp-1",
    pair_id: str = "pair-1",
    arm_id: str = "arm-1",
    state: str = "ADMITTED",
) -> tuple[str, dict]:
    return (
        (
            "INSERT INTO advisory_decision_invocations (decision_invocation_id, snapshot_id, "
            "opportunity_id, evidence_id, evidence_revision, evidence_hash, feature_snapshot_hash, "
            "experiment_id, experiment_definition_digest, pair_id, baseline_arm_id, "
            "treatment_arm_id, arm_id, baseline_policy_version, baseline_participation, "
            "input_binding_digest, prompt_version, schema_version, treatment_version, "
            "configured_provider_id, configured_model_id, decision_requested_at, "
            "decision_deadline_at, state, created_at, updated_at) VALUES (:iid, :sid, :oid, :eid, "
            "1, :eh, :fh, :exp, 'defdigest', :pair, 'barm', 'tarm', :arm, "
            "'ALL_ELIGIBLE_LONG_SHADOW_V1', 'PARTICIPATE_LONG', 'bind', 'p1', 's1', 't1', "
            "'fake-provider', 'fake-model', now(), now() + interval '30 seconds', :state, "
            "now(), now())"
        ),
        {
            "iid": invocation_id,
            "sid": snapshot_id,
            "oid": opportunity_id,
            "eid": evidence_id,
            "eh": "b" * 64,
            "fh": "c" * 64,
            "exp": experiment_id,
            "pair": pair_id,
            "arm": arm_id,
            "state": state,
        },
    )


def _attempt_insert(
    attempt_id: str, invocation_id: str, number: int = 1, prior: str | None = None
) -> tuple[str, dict]:
    return (
        (
            "INSERT INTO advisory_decision_attempts (attempt_id, decision_invocation_id, "
            "attempt_number, attempt_state, prior_attempt_id, configured_provider_id, "
            "configured_model_id, input_binding_digest, started_at) "
            "VALUES (:aid, :iid, :num, 'STARTED', :prior, 'fake-provider', 'fake-model', "
            "'bind', now())"
        ),
        {"aid": attempt_id, "iid": invocation_id, "num": number, "prior": prior},
    )


def _finalize_statements(
    invocation_id: str, attempt_id: str, decision_id: str, snapshot_id: str
) -> list[tuple[str, dict]]:
    return [
        (
            (
                "INSERT INTO ai_decisions (decision_id, snapshot_id, run_mode, state_version, "
                "config_version, prompt_version, schema_version, model, status, raw_prompt, "
                "raw_response, created_at, decision_invocation_id, attempt_id) VALUES "
                "(:did, :sid, 'TEST', 1, 'c1', 'p1', 's1', 'fake-model', 'VALID', 'p', "
                "'{}'::jsonb, now(), :iid, :aid)"
            ),
            {"did": decision_id, "sid": snapshot_id, "iid": invocation_id, "aid": attempt_id},
        ),
        (
            (
                "UPDATE advisory_decision_invocations SET state='FINAL', final_status='VALID', "
                "final_reason_code='VALID_PROVIDER_DECISION', finalized_at=now(), "
                "final_attempt_id=:aid, final_decision_id=:did, updated_at=now() "
                "WHERE decision_invocation_id=:iid"
            ),
            {"aid": attempt_id, "did": decision_id, "iid": invocation_id},
        ),
    ]


# ---------------------------------------------------------------------------- phases


def phase_revision_graph() -> None:
    print("\n[1] Alembic revision graph")
    script = ScriptDirectory.from_config(_alembic_config(_ADMIN_URL))
    heads = script.get_heads()
    expect("single alembic head", len(heads) == 1, f"heads={sorted(heads)}")
    expect("new head is 20260917_0010", heads == [NEW_HEAD], f"head={heads[0] if heads else None}")
    revisions = [rev.revision for rev in script.walk_revisions()]
    expect("no duplicate revision id", len(revisions) == len(set(revisions)), f"n={len(revisions)}")
    dangling = [
        rev.revision
        for rev in script.walk_revisions()
        if rev.down_revision is not None and rev.down_revision not in revisions
    ]
    expect("no dangling down_revision", not dangling, f"dangling={dangling}")
    expect(
        "new revision descends from 20260913_0009",
        script.get_revision(NEW_HEAD).down_revision == OLD_HEAD,
        f"down_revision={script.get_revision(NEW_HEAD).down_revision}",
    )


def phase_upgrade_and_backfill() -> None:
    print("\n[2] upgrade 20260913_0009 -> 20260917_0010 with pre-existing historical rows")
    with _disposable_database("schema") as url:
        command.upgrade(_alembic_config(url), OLD_HEAD)
        at_old = _as_scalar(url, "SELECT version_num FROM alembic_version")
        expect("old head confirmed", at_old == OLD_HEAD, f"alembic_version={at_old}")

        # Historical rows written by the *accepted* pre-I2 schema, before the extension
        # existed. Their fate under the upgrade is the whole point of the backfill.
        legacy_evidence = "legacy-evidence-1"
        legacy_opportunity = "legacy-opportunity-1"
        legacy_snapshot = "legacy-snapshot-1"
        legacy_decision = "legacy-decision-1"
        _run_sql(url, *_evidence_insert(legacy_evidence, legacy_opportunity))
        _run_sql(url, *_snapshot_insert(legacy_snapshot))
        _run_sql(
            url,
            "INSERT INTO ai_decisions (decision_id, snapshot_id, run_mode, state_version, "
            "config_version, prompt_version, schema_version, model, status, raw_prompt, "
            "raw_response, created_at) VALUES (:did, :sid, 'TEST', 1, 'c1', 'p1', 's1', "
            "'legacy-model', 'VALID', 'p', '{}'::jsonb, now())",
            {"did": legacy_decision, "sid": legacy_snapshot},
        )

        command.upgrade(_alembic_config(url), NEW_HEAD)
        at_new = _as_scalar(url, "SELECT version_num FROM alembic_version")
        expect("new head reached", at_new == NEW_HEAD, f"alembic_version={at_new}")

        legacy_state = _as_scalar(
            url,
            "SELECT advisory_admission_state FROM edge_opportunity_evidence "
            "WHERE evidence_id = :eid",
            {"eid": legacy_evidence},
        )
        expect(
            "pre-existing Evidence backfilled to LEGACY_PRE_I2",
            legacy_state == "LEGACY_PRE_I2",
            f"state={legacy_state}",
        )
        legacy_binding = _as_scalar(
            url,
            "SELECT count(*) FROM edge_opportunity_evidence WHERE evidence_id = :eid AND "
            "(advisory_decision_invocation_id IS NOT NULL OR advisory_admission_seed IS NOT NULL "
            "OR advisory_treatment_participation IS NOT NULL)",
            {"eid": legacy_evidence},
        )
        expect(
            "legacy Evidence carries no fabricated experiment/pair/arm/seed/Invocation",
            legacy_binding == 0,
            f"bound_columns={legacy_binding}",
        )

        new_evidence = "new-evidence-1"
        _run_sql(url, *_evidence_insert(new_evidence, "new-opportunity-1"))
        new_state = _as_scalar(
            url,
            "SELECT advisory_admission_state FROM edge_opportunity_evidence WHERE evidence_id = :eid",
            {"eid": new_evidence},
        )
        expect(
            "post-upgrade Evidence takes the UNSTAGED server default",
            new_state == "UNSTAGED",
            f"state={new_state}",
        )
        default_expr = _as_scalar(
            url,
            "SELECT column_default FROM information_schema.columns WHERE "
            "table_name='edge_opportunity_evidence' AND column_name='advisory_admission_state'",
        )
        expect(
            "advisory_admission_state has a server default of 'UNSTAGED'",
            default_expr is not None and "UNSTAGED" in default_expr,
            f"default={default_expr}",
        )

        legacy_decision_ok = _as_scalar(
            url,
            "SELECT count(*) FROM ai_decisions WHERE decision_id = :did "
            "AND decision_invocation_id IS NULL AND attempt_id IS NULL",
            {"did": legacy_decision},
        )
        expect("legacy ai_decisions row survives unchanged", legacy_decision_ok == 1)
        legacy_snapshot_ok = _as_scalar(
            url,
            "SELECT count(*) FROM decision_snapshots WHERE snapshot_id = :sid "
            "AND decision_invocation_id IS NULL",
            {"sid": legacy_snapshot},
        )
        expect("legacy decision_snapshots row survives unchanged", legacy_snapshot_ok == 1)


def phase_constraint_inventory() -> None:
    print("\n[3] frozen constraint inventory materialised in PostgreSQL")
    with _disposable_database("inventory") as url:
        command.upgrade(_alembic_config(url), NEW_HEAD)
        expected_tables = {
            "advisory_decision_invocations",
            "advisory_decision_attempts",
            "edge_opportunity_evidence",
            "decision_snapshots",
            "ai_decisions",
        }
        rows = _as_rows(
            url,
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
            "AND table_name = ANY(:names)",
            {"names": sorted(expected_tables)},
        )
        present = {row[0] for row in rows}
        expect("all five contract tables exist", present == expected_tables, f"present={sorted(present)}")

        constraints = _as_rows(
            url,
            "SELECT conname, condeferrable, condeferred FROM pg_constraint WHERE conname = ANY(:names)",
            {
                "names": [
                    "fk_advisory_invocation_evidence",
                    "fk_advisory_evidence_invocation",
                    "fk_advisory_invocation_final_attempt",
                    "fk_advisory_invocation_final_decision",
                    "fk_ai_decisions_advisory_attempt",
                ]
            },
        )
        by_name = {row[0]: (row[1], row[2]) for row in constraints}
        expect("all five cycle/origin FKs exist", len(by_name) == 5, f"found={sorted(by_name)}")
        not_deferred = [name for name, (d, i) in by_name.items() if not (d and i)]
        expect(
            "every cycle/origin FK is DEFERRABLE INITIALLY DEFERRED",
            not not_deferred,
            f"not_deferred={sorted(not_deferred)}",
        )

        checks = _as_rows(
            url,
            "SELECT conname FROM pg_constraint WHERE contype='c' AND conrelid::regclass::text "
            "IN ('edge_opportunity_evidence','advisory_decision_invocations',"
            "'advisory_decision_attempts','decision_snapshots','ai_decisions')",
        )
        names = {row[0] for row in checks}
        required = {
            "ck_advisory_evidence_state",
            "ck_advisory_evidence_participation",
            "ck_advisory_evidence_unstaged_bare",
            "ck_advisory_evidence_classification_bare",
            "ck_advisory_evidence_seed_atomic",
            "ck_advisory_evidence_unbound_terminal",
            "ck_advisory_evidence_terminal_requires_seed",
            "ck_advisory_evidence_invocation_created",
            "ck_advisory_evidence_invocation_only_created",
            "ck_advisory_invocation_state",
            "ck_advisory_invocation_final_completeness",
            "ck_advisory_invocation_no_attempt_reason",
            "ck_advisory_invocation_final_decision_requires_attempt",
            "ck_advisory_attempt_state",
            "ck_advisory_attempt_usage_exclusive",
            "ck_advisory_attempt_cost_pair",
            "ck_ai_decisions_advisory_origin_pair",
            "ck_decision_snapshots_advisory_binding_atomic",
        }
        missing = sorted(required - names)
        expect("every frozen CHECK constraint exists", not missing, f"missing={missing}")

        partial = _as_scalar(
            url,
            "SELECT count(*) FROM pg_indexes WHERE indexname='uq_ai_decisions_advisory_invocation' "
            "AND indexdef LIKE '%WHERE%'",
        )
        expect(
            "ai_decisions Invocation uniqueness is a partial unique index (legacy rows exempt)",
            partial == 1,
        )


def phase_evidence_check_negatives() -> None:
    print("\n[4] conditional CHECK negatives on edge_opportunity_evidence")
    with _disposable_database("evidence_checks") as url:
        command.upgrade(_alembic_config(url), NEW_HEAD)
        # JSON payloads travel as bound parameters and are CAST server-side: an inline
        # `'{"k":1}'::jsonb` literal would be mis-parsed by the text() binder (the colon
        # inside the JSON reads as a bind marker), which would test the harness, not the
        # constraint.
        payload = '{"k": 1}'

        def probe() -> dict:
            return {"eid": _bootstrap_evidence(url), "seed": payload}

        expect_rejected(
            "UNSTAGED with a seed is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_seed_version='v1', "
            "advisory_admission_seed_digest='d', advisory_admission_seed=CAST(:seed AS jsonb) "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_unstaged_bare",
            probe(),
        )
        expect_rejected(
            "UNSTAGED with a reason code is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_reason_code='X' "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_unstaged_bare",
            probe(),
        )
        expect_rejected(
            "UNSTAGED with a treatment participation is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_treatment_participation='PARTICIPATE_LONG' WHERE evidence_id=:eid",
            "ck_advisory_evidence_unstaged_bare",
            probe(),
        )
        expect_rejected(
            "GATE_A_DISABLED with a treatment participation is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='GATE_A_DISABLED', "
            "advisory_treatment_participation='PARTICIPATE_LONG' WHERE evidence_id=:eid",
            "ck_advisory_evidence_classification_bare",
            probe(),
        )
        expect_rejected(
            "LEGACY_PRE_I2 with a seed is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='LEGACY_PRE_I2', "
            "advisory_admission_seed_version='v1', advisory_admission_seed_digest='d', "
            "advisory_admission_seed=CAST(:seed AS jsonb) WHERE evidence_id=:eid",
            "ck_advisory_evidence_classification_bare",
            probe(),
        )
        expect_rejected(
            "a digest without its seed payload is refused (half-written seed)",
            "UPDATE edge_opportunity_evidence SET advisory_admission_seed_digest='d' "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_seed_atomic",
            probe(),
        )
        expect_rejected(
            "a seed payload without its digest is refused (half-written seed)",
            "UPDATE edge_opportunity_evidence SET advisory_admission_seed=CAST(:seed AS jsonb) "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_seed_atomic",
            probe(),
        )
        expect_rejected(
            "INVOCATION_CREATED without a complete seed or Invocation is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='INVOCATION_CREATED', "
            "advisory_decision_invocation_id=NULL WHERE evidence_id=:eid",
            "ck_advisory_evidence_invocation_created",
            probe(),
        )
        expect_rejected(
            "a GATE_A_DISABLED classification carrying an Invocation is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='GATE_A_DISABLED', "
            "advisory_decision_invocation_id='inv-x' WHERE evidence_id=:eid",
            (
                "ck_advisory_evidence_invocation_only_created",
                "ck_advisory_evidence_classification_bare",
            ),
            probe(),
        )
        expect_rejected(
            "ADMISSION_FAILED_FINAL/UNBOUND with any seed is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='ADMISSION_STAGING_FAILED_UNBOUND', "
            "advisory_treatment_participation='NO_LONG_UNBOUND', "
            "advisory_admission_seed_version='v1', advisory_admission_seed_digest='d', "
            "advisory_admission_seed=CAST(:seed AS jsonb) WHERE evidence_id=:eid",
            "ck_advisory_evidence_unbound_terminal",
            probe(),
        )
        expect_rejected(
            "ADMISSION_FAILED_FINAL/UNBOUND with an Invocation is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='ADMISSION_STAGING_FAILED_UNBOUND', "
            "advisory_treatment_participation='NO_LONG_UNBOUND', "
            "advisory_decision_invocation_id='ghost' WHERE evidence_id=:eid",
            (
                "ck_advisory_evidence_invocation_only_created",
                "ck_advisory_evidence_unbound_terminal",
            ),
            probe(),
        )
        # Isolating probe for `ck_advisory_evidence_invocation_only_created`: a non-unbound
        # ADMISSION_FAILED_FINAL carries a complete seed (so `terminal_requires_seed` and
        # `unbound_terminal` are both satisfied), which leaves only "only
        # INVOCATION_CREATED may carry an Invocation" able to refuse it.
        expect_rejected(
            "only INVOCATION_CREATED may carry an Invocation (isolated)",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='DEADLINE_EXPIRED_BEFORE_PROVIDER', "
            "advisory_admission_seed_version='v1', advisory_admission_seed_digest='d', "
            "advisory_admission_seed=CAST(:seed AS jsonb), "
            "advisory_decision_invocation_id='inv-y' WHERE evidence_id=:eid",
            "ck_advisory_evidence_invocation_only_created",
            probe(),
        )
        expect_rejected(
            "ADMISSION_FAILED_FINAL/UNBOUND without the NO_LONG_UNBOUND participation is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='ADMISSION_STAGING_FAILED_UNBOUND', "
            "advisory_treatment_participation='NO_LONG' WHERE evidence_id=:eid",
            "ck_advisory_evidence_unbound_terminal",
            probe(),
        )
        expect_rejected(
            "a non-unbound ADMISSION_FAILED_FINAL without a complete seed is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='DEADLINE_EXPIRED_BEFORE_PROVIDER' "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_terminal_requires_seed",
            probe(),
        )
        expect_rejected(
            "an unknown admission state is refused",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='RECOVERY_REQUIRED' "
            "WHERE evidence_id=:eid",
            "ck_advisory_evidence_state",
            probe(),
        )
        expect_rejected(
            "an unknown treatment participation is refused",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_treatment_participation='MAYBE_LONG' WHERE evidence_id=:eid",
            "ck_advisory_evidence_participation",
            probe(),
        )

        expect_accepted(
            "the exact unbound staging-failure terminal is accepted",
            "UPDATE edge_opportunity_evidence SET "
            "advisory_admission_state='ADMISSION_FAILED_FINAL', "
            "advisory_admission_reason_code='ADMISSION_STAGING_FAILED_UNBOUND', "
            "advisory_treatment_participation='NO_LONG_UNBOUND' WHERE evidence_id=:eid",
            probe(),
        )
        expect_accepted(
            "a frozen-epoch GATE_A_DISABLED classification is accepted",
            "UPDATE edge_opportunity_evidence SET advisory_admission_state='GATE_A_DISABLED' "
            "WHERE evidence_id=:eid",
            probe(),
        )


def _bootstrap_evidence(url: str, evidence_id: str | None = None) -> str:
    """Insert one fresh Evidence row and return its id (schema-default UNSTAGED)."""

    identifier = evidence_id or f"ev-{uuid4().hex[:12]}"
    _run_sql(url, *_evidence_insert(identifier, f"op-{uuid4().hex[:12]}"))
    return identifier


def phase_evidence_positive_path() -> None:
    print("\n[5] negative/positive probes for the deferred cycles and winner fences")
    with _disposable_database("cycles") as url:
        command.upgrade(_alembic_config(url), NEW_HEAD)

        invocation = "inv-deferred"
        snapshot = "snap-deferred"
        evidence = "ev-deferred"
        opportunity = "op-deferred"
        attempt_1 = "att-1"
        attempt_2 = "att-2"

        # The strongest form of deferral: the Invocation half is written BEFORE the
        # Evidence half it references, and both are committed together.
        statements = [
            _snapshot_insert(snapshot),
            _invocation_insert(invocation, snapshot, evidence, opportunity),
            _evidence_insert(evidence, opportunity),
            (
                (
                    "UPDATE edge_opportunity_evidence SET "
                    "advisory_admission_state='INVOCATION_CREATED', "
                    "advisory_admission_seed_version='se02d-advisory-seed-v1', "
                    "advisory_admission_seed_digest='seeddigest', "
                    "advisory_admission_seed=CAST(:seed AS jsonb), "
                    "advisory_treatment_participation='PARTICIPATE_LONG', "
                    "advisory_decision_invocation_id=:iid WHERE evidence_id=:eid"
                ),
                {"iid": invocation, "eid": evidence, "seed": '{"seed": true}'},
            ),
        ]
        try:
            asyncio.run(_run_in_one_transaction(url, statements))
            ok(
                "Evidence <-> Invocation deferred FK: both halves commit atomically",
                "Invocation written before its Evidence row",
            )
        except Exception as exc:  # noqa: BLE001 - the deferral is the assertion
            fail(
                "Evidence <-> Invocation deferred FK: both halves commit atomically",
                " ".join(str(a) for a in exc.args)[:240],
            )

        linked = _as_scalar(
            url,
            "SELECT advisory_admission_state FROM edge_opportunity_evidence WHERE evidence_id=:eid",
            {"eid": evidence},
        )
        expect(
            "admission state reached INVOCATION_CREATED",
            linked == "INVOCATION_CREATED",
            f"state={linked}",
        )

        attempt_statements = [
            _attempt_insert(attempt_1, invocation, 1),
            _attempt_insert(attempt_2, invocation, 2, prior=attempt_1),
        ]
        asyncio.run(_run_in_one_transaction(url, attempt_statements))
        lineage = _as_scalar(
            url,
            "SELECT prior_attempt_id FROM advisory_decision_attempts WHERE attempt_id=:aid",
            {"aid": attempt_2},
        )
        expect(
            "retry lineage stays inside one Invocation",
            lineage == attempt_1,
            f"prior_attempt_id={lineage}",
        )
        expect_rejected(
            "a second Attempt with the same attempt_number is refused",
            "INSERT INTO advisory_decision_attempts (attempt_id, decision_invocation_id, "
            "attempt_number, attempt_state, configured_provider_id, configured_model_id, "
            "input_binding_digest, started_at) VALUES ('att-dup', :iid, 1, 'STARTED', "
            "'fake-provider', 'fake-model', 'bind', now())",
            "uq_advisory_attempt_invocation_number",
            {"iid": invocation},
        )
        expect_rejected(
            "a prior Attempt from another Invocation is refused",
            "INSERT INTO advisory_decision_attempts (attempt_id, decision_invocation_id, "
            "attempt_number, attempt_state, prior_attempt_id, configured_provider_id, "
            "configured_model_id, input_binding_digest, started_at) "
            "VALUES ('att-cross', :iid, 3, 'STARTED', 'att-1-other', 'fake-provider', "
            "'fake-model', 'bind', now())",
            "fk_advisory_attempt_prior",
            {"iid": invocation},
        )
        expect_rejected(
            "a second Invocation for the same (experiment, pair, arm) is refused",
            "INSERT INTO advisory_decision_invocations (decision_invocation_id, snapshot_id, "
            "opportunity_id, evidence_id, evidence_revision, evidence_hash, "
            "feature_snapshot_hash, experiment_id, experiment_definition_digest, pair_id, "
            "baseline_arm_id, treatment_arm_id, arm_id, baseline_policy_version, "
            "baseline_participation, input_binding_digest, prompt_version, schema_version, "
            "treatment_version, configured_provider_id, configured_model_id, "
            "decision_requested_at, decision_deadline_at, state, created_at, updated_at) "
            "SELECT 'inv-dup', snapshot_id, opportunity_id, evidence_id, evidence_revision, "
            "evidence_hash, feature_snapshot_hash, experiment_id, experiment_definition_digest, "
            "pair_id, baseline_arm_id, treatment_arm_id, arm_id, baseline_policy_version, "
            "baseline_participation, input_binding_digest, prompt_version, schema_version, "
            "treatment_version, configured_provider_id, configured_model_id, "
            "decision_requested_at, decision_deadline_at, 'ADMITTED', now(), now() "
            "FROM advisory_decision_invocations WHERE decision_invocation_id=:iid",
            "uq_advisory_invocation_experiment_pair_arm",
            {"iid": invocation},
        )

        expect_rejected(
            "state=FINAL without the three core final fields is refused",
            "UPDATE advisory_decision_invocations SET state='FINAL' WHERE "
            "decision_invocation_id=:iid",
            "ck_advisory_invocation_final_completeness",
            {"iid": invocation},
        )
        expect_rejected(
            "a non-FINAL state carrying final fields is refused",
            "UPDATE advisory_decision_invocations SET final_status='VALID' WHERE "
            "decision_invocation_id=:iid",
            "ck_advisory_invocation_final_completeness",
            {"iid": invocation},
        )
        expect_rejected(
            "a NULL final Attempt with a non-enumerated reason is refused",
            "UPDATE advisory_decision_invocations SET state='FINAL', final_status='VALID', "
            "final_reason_code='SOMETHING_ELSE', finalized_at=now() WHERE "
            "decision_invocation_id=:iid",
            "ck_advisory_invocation_no_attempt_reason",
            {"iid": invocation},
        )
        expect_accepted(
            "a NULL final Attempt with an enumerated no-provider reason is accepted",
            "UPDATE advisory_decision_invocations SET state='FINAL', "
            "final_status='CAPACITY_BLOCKED', final_reason_code='CAPACITY_BLOCKED', "
            "finalized_at=now(), updated_at=now() WHERE decision_invocation_id=:iid",
            {"iid": invocation},
        )
        expect_rejected(
            "a final decision without a final Attempt is refused",
            "UPDATE advisory_decision_invocations SET final_decision_id='dec-ghost' "
            "WHERE decision_invocation_id=:iid",
            "ck_advisory_invocation_final_decision_requires_attempt",
            {"iid": invocation},
        )
        expect_rejected(
            "an AIDecision carrying only decision_invocation_id is refused",
            "INSERT INTO ai_decisions (decision_id, snapshot_id, run_mode, state_version, "
            "config_version, prompt_version, schema_version, model, status, raw_prompt, "
            "raw_response, created_at, decision_invocation_id) VALUES ('dec-half', :sid, "
            "'TEST', 1, 'c1', 'p1', 's1', 'm', 'VALID', 'p', '{}'::jsonb, now(), :iid)",
            "ck_ai_decisions_advisory_origin_pair",
            {"sid": snapshot, "iid": invocation},
        )


def phase_finalizer_transaction() -> None:
    print("\n[6] the finalizer transaction commits as one atomic unit")
    with _disposable_database("finalizer") as url:
        command.upgrade(_alembic_config(url), NEW_HEAD)
        invocation, snapshot, evidence, opportunity = "inv-fin", "snap-fin", "ev-fin", "op-fin"
        attempt, decision = "att-fin", "dec-fin"
        asyncio.run(
            _run_in_one_transaction(
                url,
                [
                    _snapshot_insert(snapshot),
                    _evidence_insert(evidence, opportunity),
                    _invocation_insert(invocation, snapshot, evidence, opportunity),
                    _attempt_insert(attempt, invocation, 1),
                ],
            )
        )
        # The AIDecision insert and the Invocation terminal update share one transaction and
        # reference each other through deferred composite FKs in both directions.
        try:
            asyncio.run(
                _run_in_one_transaction(
                    url, _finalize_statements(invocation, attempt, decision, snapshot)
                )
            )
            ok("finalizer writes the five terminal fields + origin atomically")
        except Exception as exc:  # noqa: BLE001 - the atomicity is the assertion
            fail(
                "finalizer writes the five terminal fields + origin atomically",
                " ".join(str(a) for a in exc.args)[:240],
            )

        row = _as_rows(
            url,
            "SELECT state, final_status, final_reason_code, finalized_at IS NOT NULL, "
            "final_attempt_id, final_decision_id FROM advisory_decision_invocations "
            "WHERE decision_invocation_id=:iid",
            {"iid": invocation},
        )
        if row:
            state, status, reason, has_time, final_attempt, final_decision = row[0]
            expect("invocation is FINAL", state == "FINAL", f"state={state}")
            expect(
                "all five terminal fields are queryable",
                status == "VALID"
                and reason == "VALID_PROVIDER_DECISION"
                and has_time
                and final_attempt == attempt
                and final_decision == decision,
                f"status={status} reason={reason} attempt={final_attempt} decision={final_decision}",
            )
        else:
            fail("invocation row readable after finalization")

        expect_rejected(
            "a second AIDecision for the same Invocation is refused (winner fence)",
            "INSERT INTO ai_decisions (decision_id, snapshot_id, run_mode, state_version, "
            "config_version, prompt_version, schema_version, model, status, raw_prompt, "
            "raw_response, created_at, decision_invocation_id, attempt_id) VALUES "
            "('dec-loser', :sid, 'TEST', 1, 'c1', 'p1', 's1', 'm', 'VALID', 'p', "
            "'{}'::jsonb, now(), :iid, :aid)",
            "uq_ai_decisions_advisory_invocation",
            {"sid": snapshot, "iid": invocation, "aid": attempt},
        )
        expect_rejected(
            "a loser AIDecision naming a foreign Attempt is refused",
            "INSERT INTO ai_decisions (decision_id, snapshot_id, run_mode, state_version, "
            "config_version, prompt_version, schema_version, model, status, raw_prompt, "
            "raw_response, created_at, decision_invocation_id, attempt_id) VALUES "
            "('dec-cross', :sid, 'TEST', 1, 'c1', 'p1', 's1', 'm', 'VALID', 'p', "
            "'{}'::jsonb, now(), 'ghost-invocation', :aid)",
            "fk_ai_decisions_advisory_attempt",
            {"sid": snapshot, "aid": attempt},
        )
        expect_rejected(
            "an Attempt usage fact together with an unavailable reason is refused",
            "UPDATE advisory_decision_attempts SET total_tokens=10, "
            "usage_unavailable_reason='PROVIDER_OMITTED' WHERE attempt_id=:aid",
            "ck_advisory_attempt_usage_exclusive",
            {"aid": attempt},
        )
        expect_rejected(
            "a monetary cost without a pricing version is refused",
            "UPDATE advisory_decision_attempts SET monetary_cost=0.001 WHERE attempt_id=:aid",
            "ck_advisory_attempt_cost_pair",
            {"aid": attempt},
        )


def phase_downgrade_roundtrip() -> None:
    print("\n[7] downgrade to 20260913_0009 and upgrade again")
    with _disposable_database("roundtrip") as url:
        command.upgrade(_alembic_config(url), NEW_HEAD)
        command.downgrade(_alembic_config(url), OLD_HEAD)
        at_old = _as_scalar(url, "SELECT version_num FROM alembic_version")
        expect("downgrade returns to the old head", at_old == OLD_HEAD, f"alembic_version={at_old}")
        gone = _as_scalar(
            url,
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' "
            "AND table_name IN ('advisory_decision_invocations','advisory_decision_attempts')",
        )
        expect("downgrade removes both new tables", gone == 0, f"remaining={gone}")
        dropped_column = _as_scalar(
            url,
            "SELECT count(*) FROM information_schema.columns WHERE "
            "table_name='edge_opportunity_evidence' AND column_name="
            "'advisory_admission_state'",
        )
        expect("downgrade removes the Evidence accounting column", dropped_column == 0)

        legacy = _bootstrap_evidence_pre_i2(url)
        expect("old schema still accepts an Evidence insert", legacy is True)

        command.upgrade(_alembic_config(url), NEW_HEAD)
        at_new = _as_scalar(url, "SELECT version_num FROM alembic_version")
        expect("re-upgrade returns to the new head", at_new == NEW_HEAD, f"alembic_version={at_new}")


def _bootstrap_evidence_pre_i2(url: str) -> bool:
    _run_sql(url, *_evidence_insert(f"ev-roundtrip-{uuid4().hex[:8]}", f"op-{uuid4().hex[:8]}"))
    return True


def main() -> int:
    _guard_isolation(_ADMIN_URL)
    print("PRE-01B-I2 AdvisoryIngress Core - migration / schema verification")
    print(f"admin url : {_ADMIN_URL}")
    print(f"revisions : {OLD_HEAD} -> {NEW_HEAD}")
    probe = create_async_engine(_ADMIN_URL, poolclass=NullPool)

    async def _version() -> str:
        async with probe.connect() as connection:
            return str(await connection.scalar(text("SHOW server_version")))

    try:
        version = asyncio.run(_version())
    finally:
        asyncio.run(probe.dispose())
    print(f"postgres  : {version}")

    phase_revision_graph()
    phase_upgrade_and_backfill()
    phase_constraint_inventory()
    phase_evidence_check_negatives()
    phase_evidence_positive_path()
    phase_finalizer_transaction()
    phase_downgrade_roundtrip()

    print("\n=== summary ===")
    print(f"checks passed : {_CHECKS - len(_FAILURES)}/{_CHECKS}")
    if _FAILURES:
        print(f"FAILED        : {len(_FAILURES)}")
        for item in _FAILURES:
            print(f"  - {item}")
        return 1
    print("RESULT        : PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
