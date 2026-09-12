"""N01-7-F01 migration gate -- disposable PostgreSQL proof for `20260912_0006`.

Acceptance Batch: N01-7-F01-R1 (Protection Authority Closure + Validation Environment Recovery),
extended by N01-7-F01-R2 (Legacy Authority Proof Closure, finding N01-7-F01-R1-R01). The filename
keeps the R1 name for review lineage; the batch this file now proves is R2.
Scope: this script only *verifies*. It creates its own throwaway database, never writes the shared
primary `marketpulse` database, and never touches application code.

What it proves (task sections 8 and 11 of R1; sections 5-14 of R2):

1. `20260912_0006` is a single head whose `down_revision` is `20260911_0005`.
2. `0005 -> 0006` is additive: exactly five new `positions` columns and three new CHECK
   constraints, with every pre-existing row unchanged apart from those NULL columns.
3. The one-time legacy conversion (Candidate A compatibility matrix) produces exactly the approved
   answers on a real 0005 database:
     * CASE A  FLAT position (`quantity <= 0`)                      -> left NULL;
     * CASE B  OPEN position + one fully authoritative ACTIVE plan    -> SL/TP copied, TTL ignored;
     * CASE C  OPEN position whose authority is missing / ambiguous
               / corrupt / identity-mismatched                       -> left NULL, never guessed.
4. The expanded CASE C matrix of R2: eight row/payload identity mismatches plus an incomplete
   pseudo-plan that the R1 predicate accepted outright, each seeded as a real `0005` row.
5. Teeth proof (R2 section 9): the reviewed R1 predicate is loaded from the reviewed R1 commit and
   evaluated on the very same probe rows, so the report shows which probes it accepted -- i.e. the
   exact R1-R01 gap -- and that R2 refuses every one of them.
6. `0006 -> 0005` removes only the F01 delta: the three constraints and five columns disappear and
   every legacy column keeps its exact value.
7. `0005 -> 0006` again reproduces byte-identical conversion values, because the conversion copies
   `trade_plans.created_at` instead of reading a clock.
8. The shared primary database is left at `20260905_0004` and no disposable database survives.

usage:  py -3.14 scripts/verify_n01_7_f01_r1_migration_gate.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPOSITORY_ROOT / "backend"
sys.path.insert(0, str(BACKEND / "src"))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from marketpulse.config import Settings
from marketpulse.g3.models import OrderSide, PriceZone, RunMode, TradePlan
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_PREFIX = "marketpulse_n01_7_f01_r1_"
FOUNDATION_REVISION = "20260911_0005"
F01_REVISION = "20260912_0006"
SHARED_PRIMARY_BASELINE = "20260905_0004"  # task section 3/4: shared primary recovery target
MIGRATION_FILE = BACKEND / "alembic" / "versions" / "20260912_0006_position_protection_snapshot.py"
MIGRATION_REPO_PATH = "backend/alembic/versions/20260912_0006_position_protection_snapshot.py"
#: The reviewed R1 commit whose predicate is replayed as the teeth witness for this gate.
R1_REVIEWED_HEAD = "979e5d2ee6b2cc4f26ae382cd3e46020d868a088"

PROTECTION_COLUMNS = (
    "protection_plan_id",
    "protection_plan_version",
    "protection_stop_loss",
    "protection_take_profit",
    "protection_updated_at",
)
PROTECTION_CHECKS = (
    "ck_positions_protection_complete",
    "ck_positions_protection_version_positive",
    "ck_positions_protection_prices",
)

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
#: The 0005-era `positions` columns; used for a before/after value fingerprint.
LEGACY_POSITION_COLUMNS = (
    "position_id",
    "run_mode",
    "instrument_id",
    "quantity",
    "average_cost",
    "realized_pnl",
    "trade_id",
    "updated_at",
)

INSERT_LEGACY_POSITION_SQL = (
    "INSERT INTO positions (position_id, run_mode, instrument_id, quantity, average_cost, "
    "realized_pnl, trade_id, updated_at) VALUES "
    "(:position_id, 'REPLAY', :instrument_id, :quantity, 100.0, 0.0, :trade_id, :now)"
)

INSERT_LEGACY_PLAN_SQL = (
    "INSERT INTO trade_plans (plan_id, snapshot_id, decision_id, instrument_id, symbol, run_mode, "
    "state_version, plan_version, status, created_at, expires_at, payload) VALUES "
    "(:plan_id, :snapshot_id, :decision_id, :instrument_id, :symbol, 'REPLAY', "
    ":state_version, :plan_version, :status, :created_at, :expires_at, CAST(:payload AS json))"
)

#: A second ACTIVE plan for one symbol, used to find out whether `uq_trade_plans_one_active`
#: makes the ambiguity branch unreachable in a healthy schema.
INSERT_AMBIGUOUS_PLAN_SQL = (
    "INSERT INTO trade_plans (plan_id, snapshot_id, decision_id, instrument_id, symbol, run_mode, "
    "state_version, plan_version, status, created_at, expires_at, payload) VALUES "
    "('plan-r1-amb-2', 'snap-r1', 'decision-r1', 'DDD-USDT', 'DDD-USDT', 'REPLAY', 7, 1, 'ACTIVE', "
    ":now, :expires_at, CAST(:payload AS json))"
)

#: Every payload key the R1 predicate never looked at. Dropping all of them leaves exactly
#: `plan_id / run_mode / instrument_id / plan_version / status / stop_loss / take_profit`, which is
#: the incomplete pseudo-plan R1 accepted and R2 must refuse (R2 task section 9).
_PSEUDO_PLAN_DROP = (
    "snapshot_id",
    "decision_id",
    "symbol",
    "state_version",
    "created_at",
    "expires_at",
    "entry_zone",
    "intended_notional",
    "order_type",
    "side",
    "invalidation",
    "probe",
    "backup_scenarios",
)

#: The R2 authority-proof negative matrix. Every entry is one independent CASE C probe that
#: perturbs exactly one authoritative identity field between the `trade_plans` row and its
#: serialized payload (`payload`), or removes the fields R1 never checked (`drop`). No entry can be
#: blocked by the schema: `trade_plans` has no constraint on any of these columns, so every probe is
#: really seeded and really exercised.
_LEGACY_NEGATIVE_MATRIX: dict[str, dict[str, Any]] = {
    "SNAPSHOT_ID_MISMATCH": {"payload": {"snapshot_id": "snap-other"}},
    "DECISION_ID_MISMATCH": {"payload": {"decision_id": "decision-other"}},
    "SYMBOL_MISMATCH": {"payload": {"symbol": "OTHER-USDT"}},
    "STATE_VERSION_MISMATCH": {"payload": {"state_version": 8}},
    "CREATED_AT_MISMATCH": {"payload": {"created_at": (NOW - timedelta(days=2)).isoformat()}},
    "EXPIRES_AT_MISMATCH": {"payload": {"expires_at": (NOW + timedelta(days=1)).isoformat()}},
    "RUN_MODE_MISMATCH": {"payload": {"run_mode": "TEST"}},
    "INSTRUMENT_ID_MISMATCH": {"payload": {"instrument_id": "OTHER-USDT"}},
    "INCOMPLETE_PSEUDO_PLAN": {"drop": _PSEUDO_PLAN_DROP},
    # Identity-complete but not a TradePlan: `load_active_plan()` runs `TradePlan.model_validate`,
    # which fails closed on a missing required field, so this probe must fail closed here too. It is
    # the case that gives the *shape* proof teeth -- the pseudo-plan above is already refused by the
    # identity proof, because dropping its identity fields is itself a row/payload disagreement.
    "SCHEMA_INCOMPLETE_PAYLOAD": {"drop": ("entry_zone", "intended_notional")},
    # Identity-complete and shape-complete except for one badly typed optional field, which
    # `TradePlan.model_validate` also rejects.
    "INVALID_OPTIONAL_FIELD": {"payload": {"side": "LONG"}},
    # Robustness probes: an unhashable payload value must fail closed, never raise. Written after a
    # self-review found that `value not in frozenset(...)` raises `TypeError` for a dict/list, which
    # would abort the whole upgrade on one corrupt row instead of leaving that row NULL.
    "MALFORMED_ENUM_VALUE": {"payload": {"run_mode": {}}},
    "UNHASHABLE_OPTIONAL_FIELD": {"payload": {"side": ["BUY"]}},
}

#: The probes the reviewed R1 predicate accepted: the R1-R01 gap, which R2 must refuse in full.
#: (`CASE_C_MALFORMED_ENUM_VALUE` is deliberately absent: R1 already refused it, because an
#: unhashable value simply fails its `!=` comparison. It is kept as the no-raise probe.)
_R1_GAP_CASES = (
    "CASE_C_SNAPSHOT_ID_MISMATCH",
    "CASE_C_DECISION_ID_MISMATCH",
    "CASE_C_SYMBOL_MISMATCH",
    "CASE_C_STATE_VERSION_MISMATCH",
    "CASE_C_CREATED_AT_MISMATCH",
    "CASE_C_EXPIRES_AT_MISMATCH",
    "CASE_C_INCOMPLETE_PSEUDO_PLAN",
    "CASE_C_SCHEMA_INCOMPLETE_PAYLOAD",
    "CASE_C_INVALID_OPTIONAL_FIELD",
    "CASE_C_UNHASHABLE_OPTIONAL_FIELD",
)


def _plan_json(
    *,
    plan_id: str,
    instrument: str,
    status: str = "ACTIVE",
    plan_version: int = 1,
    stop_loss: float = 80.0,
    take_profit: float = 140.0,
    created_at: datetime = NOW,
) -> dict[str, Any]:
    """A real serialized TradePlan, so the conversion is proven against the production shape."""
    plan = TradePlan(
        plan_id=plan_id,
        snapshot_id="snap-r1",
        decision_id="decision-r1",
        instrument_id=instrument,
        symbol=instrument,
        run_mode=RunMode.REPLAY,
        state_version=7,
        plan_version=plan_version,
        status=status,
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
        side=OrderSide.BUY,
        entry_zone=PriceZone(lower=90, upper=120),
        stop_loss=stop_loss,
        take_profit=take_profit,
        intended_notional=50.0,
    )
    return plan.model_dump(mode="json")


def _legacy_plan(
    *,
    plan_id: str,
    instrument: str,
    plan_version: int = 1,
    status: str = "ACTIVE",
    created_at: datetime = NOW,
    row: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    raw_payload: dict[str, Any] | None = None,
    drop: tuple[str, ...] = (),
) -> dict[str, Any]:
    """One legacy `trade_plans` row plus the serialized payload stored next to it.

    Row and payload agree on every authoritative identity field by default, which is CASE B.
    `row` changes only the `trade_plans` columns, `payload` only the serialized `TradePlan`,
    `raw_payload` replaces the serialized plan outright (a payload that is not a TradePlan at all),
    and `drop` removes payload keys -- the ways a probe makes the two disagree.
    """
    identity: dict[str, Any] = {
        "snapshot_id": "snap-r1",
        "decision_id": "decision-r1",
        "symbol": instrument,
        "state_version": 7,
    }
    row_identity = {**identity, **(row or {})}
    if raw_payload is not None:
        serialized: dict[str, Any] = dict(raw_payload)
    else:
        serialized = _plan_json(
            plan_id=plan_id,
            instrument=instrument,
            status=status,
            plan_version=plan_version,
            created_at=created_at,
        )
        serialized.update(row_identity)
        serialized.update(payload or {})
    for key in drop:
        serialized.pop(key, None)
    return {
        "plan_id": plan_id,
        "instrument_id": instrument,
        "plan_version": plan_version,
        "status": status,
        "created_at": created_at,
        "expires_at": created_at + timedelta(minutes=5),
        **row_identity,
        "payload": serialized,
    }


def _candidate_from_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Reproduce, in Python, the candidate row `_LEGACY_CANDIDATES` returns for one fixture."""
    position_id, _instrument, _quantity = fixture["position"]
    plan = fixture["plans"][0]
    return {
        "position_id": position_id,
        "run_mode": "REPLAY",
        "instrument_id": plan["instrument_id"],
        "plan_id": plan["plan_id"],
        "snapshot_id": plan["snapshot_id"],
        "decision_id": plan["decision_id"],
        "symbol": plan["symbol"],
        "state_version": plan["state_version"],
        "plan_version": plan["plan_version"],
        "status": plan["status"],
        "created_at": plan["created_at"],
        "expires_at": plan["expires_at"],
        "payload": json.dumps(plan["payload"]),
    }


def _r1_candidate(row: dict[str, Any]) -> dict[str, Any]:
    """The same candidate under the column aliases the reviewed R1 migration selected."""
    renamed = dict(row)
    renamed["plan_status"] = renamed.pop("status")
    renamed["plan_created_at"] = renamed.pop("created_at")
    return renamed


@contextmanager
def _disposable_database() -> Iterator[tuple[str, str]]:
    """Create one throwaway database, migrate it to the F01 revision, drop it on exit."""
    primary_url = Settings().database_url
    name = f"{DATABASE_PREFIX}{uuid4().hex[:12]}"
    url = f"{primary_url.rsplit('/', 1)[0]}/{name}"

    async def execute(statement: str, target: str | None = None) -> None:
        engine = create_async_engine(target or primary_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
                await connection.execute(text(statement))
        finally:
            await engine.dispose()

    asyncio.run(execute(f'CREATE DATABASE "{name}"'))
    try:
        yield name, url
    finally:
        asyncio.run(
            execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
            )
        )
        asyncio.run(execute(f'DROP DATABASE "{name}"'))


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _migrate(url: str, *, upgrade_to: str | None = None, downgrade_to: str | None = None) -> None:
    """Run one Alembic step. `env.py` prefers `DATABASE_URL`, so anchor it explicitly."""
    config = _alembic_config(url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        if upgrade_to is not None:
            command.upgrade(config, upgrade_to)
        else:
            assert downgrade_to is not None
            command.downgrade(config, downgrade_to)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def _seed_fixtures(url: str) -> dict[str, dict[str, Any]]:
    """Seed the legacy states at 0005 and return the expectations the conversion must meet."""
    case_b_created_at = NOW - timedelta(days=1)
    expired_created_at = NOW - timedelta(days=30)
    fixtures: dict[str, dict[str, Any]] = {
        # CASE A: a flat position keeps a legal NULL authority.
        "CASE_A_FLAT": {
            "position": ("pos-r1-case-a", "AAA-USDT", 0.0),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-a",
                    instrument="AAA-USDT",
                    created_at=case_b_created_at,
                )
            ],
            "expect": None,
        },
        # CASE B: exactly one fully authoritative ACTIVE plan, deliberately long expired.
        "CASE_B_OPEN": {
            "position": ("pos-r1-case-b", "BBB-USDT", 0.25),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-b",
                    instrument="BBB-USDT",
                    created_at=expired_created_at,
                )
            ],
            "expect": ("plan-r1-case-b", 1, 80.0, 140.0, expired_created_at),
        },
        # CASE C: no plan row at all.
        "CASE_C_NO_PLAN": {
            "position": ("pos-r1-case-c1", "CCC1-USDT", 0.5),
            "plans": [],
            "expect": None,
        },
        # CASE C: payload is not a TradePlan.
        "CASE_C_CORRUPT_PAYLOAD": {
            "position": ("pos-r1-case-c2", "CCC2-USDT", 0.5),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-c2",
                    instrument="CCC2-USDT",
                    raw_payload={"corrupt": "not-a-trade-plan"},
                )
            ],
            "expect": None,
        },
        # CASE C: row and payload disagree on identity.
        "CASE_C_IDENTITY_MISMATCH": {
            "position": ("pos-r1-case-c3", "CCC3-USDT", 0.5),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-c3",
                    instrument="CCC3-USDT",
                    raw_payload=_plan_json(
                        plan_id="different-plan-id", instrument="CCC3-USDT"
                    ),
                )
            ],
            "expect": None,
        },
        # CASE C: inverted levels inside an otherwise consistent payload.
        "CASE_C_INVERTED_LEVELS": {
            "position": ("pos-r1-case-c4", "CCC4-USDT", 0.5),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-c4",
                    instrument="CCC4-USDT",
                    payload={"stop_loss": 140.0, "take_profit": 80.0},
                )
            ],
            "expect": None,
        },
        # CASE C: a plan whose version can never form an authority.
        "CASE_C_PLAN_VERSION_ZERO": {
            "position": ("pos-r1-case-c5", "CCC5-USDT", 0.5),
            "plans": [
                _legacy_plan(
                    plan_id="plan-r1-case-c5",
                    instrument="CCC5-USDT",
                    plan_version=0,
                    row={"state_version": 7},
                    payload={"plan_version": 0},
                )
            ],
            "expect": None,
        },
        # Ambiguity probe: this symbol starts with exactly one authoritative ACTIVE plan, and
        # `_ambiguity_in_schema` then tries to add a second one. Whether the schema rejects it
        # (`uq_trade_plans_one_active`) or accepts it, the position's expectation is derived from
        # what actually happened, so the "DO NOT GUESS a tie" rule is verified either way.
        "AMBIGUITY_PROBE": {
            "position": ("pos-r1-amb", "DDD-USDT", 0.5),
            "plans": [_legacy_plan(plan_id="plan-r1-amb-1", instrument="DDD-USDT")],
            "expect": "DYNAMIC",
        },
    }
    # R2 expanded CASE C matrix: each probe is a real OPEN position whose single ACTIVE plan is
    # authoritative in every respect except the one field it perturbs. `trade_plans` constrains none
    # of these columns, so nothing here is "NOT SEEDABLE BY SCHEMA" -- each probe is genuinely
    # inserted and genuinely exercised by the conversion.
    for index, (name, perturbation) in enumerate(_LEGACY_NEGATIVE_MATRIX.items(), start=6):
        slug = name.lower().replace("_", "-")
        instrument = f"CCC{index}-USDT"
        fixtures[f"CASE_C_{name}"] = {
            "position": (f"pos-r2-{slug}", instrument, 0.5),
            "plans": [
                _legacy_plan(
                    plan_id=f"plan-r2-{slug}",
                    instrument=instrument,
                    created_at=case_b_created_at,
                    payload=perturbation.get("payload"),
                    drop=perturbation.get("drop", ()),
                )
            ],
            "expect": None,
        }
    statements: list[tuple[str, dict[str, Any]]] = []
    for fixture in fixtures.values():
        position_id, instrument, quantity = fixture["position"]
        statements.append(
            (
                INSERT_LEGACY_POSITION_SQL,
                {
                    "position_id": position_id,
                    "instrument_id": instrument,
                    "quantity": quantity,
                    "trade_id": f"trade-{position_id}",
                    "now": NOW,
                },
            )
        )
        for plan in fixture["plans"]:
            statements.append(
                (
                    INSERT_LEGACY_PLAN_SQL,
                    {
                        "plan_id": plan["plan_id"],
                        "snapshot_id": plan["snapshot_id"],
                        "decision_id": plan["decision_id"],
                        "instrument_id": plan["instrument_id"],
                        "symbol": plan["symbol"],
                        "state_version": plan["state_version"],
                        "plan_version": plan["plan_version"],
                        "status": plan["status"],
                        "created_at": plan["created_at"],
                        "expires_at": plan["expires_at"],
                        "payload": json.dumps(plan["payload"]),
                    },
                )
            )
    _execute_many(url, statements)
    return fixtures


async def _rows(url: str, statement: str, params: dict[str, Any] | None = None) -> list[dict]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(statement), params or {})
            return [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()


async def _scalar(url: str, statement: str, params: dict[str, Any] | None = None):
    rows = await _rows(url, statement, params)
    return next(iter(rows[0].values())) if rows else None


def _execute_many(url: str, statements: list[tuple[str, dict[str, Any]]]) -> None:
    async def run() -> None:
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                for statement, params in statements:
                    await connection.execute(text(statement), params)
        finally:
            await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------------------
# Structural / value assertions
# ---------------------------------------------------------------------------------------


def _protection_columns(url: str) -> set[str]:
    rows = asyncio.run(
        _rows(
            url,
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'positions' "
            "AND column_name LIKE 'protection_%'",
        )
    )
    return {row["column_name"] for row in rows}


def _protection_checks(url: str) -> set[str]:
    rows = asyncio.run(
        _rows(
            url,
            "SELECT conname FROM pg_constraint WHERE conname LIKE 'ck_positions_protection_%'",
        )
    )
    return {row["conname"] for row in rows}


def _alembic_version(url: str) -> str | None:
    return asyncio.run(_scalar(url, "SELECT version_num FROM alembic_version"))


def _legacy_position_fingerprint(url: str) -> str:
    columns = ", ".join(LEGACY_POSITION_COLUMNS)
    rows = asyncio.run(
        _rows(
            url,
            f"SELECT md5(coalesce(string_agg(row_to_json(t)::text, '|' ORDER BY row_to_json(t)::text), '')) "
            f"AS fp FROM (SELECT {columns} FROM positions) t",
        )
    )
    return rows[0]["fp"]


def _table_counts(url: str) -> dict[str, int]:
    rows = asyncio.run(
        _rows(
            url,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
            "ORDER BY table_name",
        )
    )
    return {
        row["table_name"]: int(
            asyncio.run(
                _scalar(url, f'SELECT count(*) AS n FROM "{row["table_name"]}"')
            )
            or 0
        )
        for row in rows
    }


def _snapshot_authority(url: str) -> dict[str, Any]:
    rows = asyncio.run(
        _rows(
            url,
            "SELECT position_id, protection_plan_id, protection_plan_version, "
            "protection_stop_loss, protection_take_profit, protection_updated_at "
            "FROM positions ORDER BY position_id",
        )
    )
    return {row["position_id"]: row for row in rows}


async def _primary_state() -> dict[str, Any]:
    url = Settings().database_url
    version = await _scalar(url, "SELECT version_num FROM alembic_version")
    columns = await _scalar(
        url,
        "SELECT count(*) AS n FROM information_schema.columns WHERE table_name = 'positions' "
        "AND column_name LIKE 'protection_%'",
    )
    residue = await _scalar(
        url, f"SELECT count(*) AS n FROM pg_database WHERE datname LIKE '{DATABASE_PREFIX}%'"
    )
    return {
        "alembic_version": version,
        "protection_columns": int(columns or 0),
        "disposable_residue": int(residue or 0),
    }


# ---------------------------------------------------------------------------------------
# Migration-function guard: ambiguity can never be guessed
# ---------------------------------------------------------------------------------------


class _StubCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class _StubConnection:
    """Just enough of `sqlalchemy.Connection` for `backfill_legacy_position_protection`."""

    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self._candidates = candidates
        self.updates: list[dict[str, Any]] = []

    def execute(self, statement: Any, parameters: dict[str, Any] | None = None) -> _StubCursor:
        if parameters is None:
            return _StubCursor(self._candidates)
        self.updates.append(parameters)
        return _StubCursor([])


def _load_migration_module() -> Any:
    spec = importlib.util.spec_from_file_location("n01_7_f01_r1_migration_0006", MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate_row(plan_id: str, *, position_id: str = "pos-amb") -> dict[str, Any]:
    """One row exactly as `_LEGACY_CANDIDATES` returns it (row columns + serialized payload)."""
    return {
        "position_id": position_id,
        "run_mode": "REPLAY",
        "instrument_id": "AMB-USDT",
        "plan_id": plan_id,
        "snapshot_id": "snap-r1",
        "decision_id": "decision-r1",
        "symbol": "AMB-USDT",
        "state_version": 7,
        "plan_version": 1,
        "status": "ACTIVE",
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "payload": json.dumps(_plan_json(plan_id=plan_id, instrument="AMB-USDT")),
    }


def _ambiguity_guard() -> dict[str, Any]:
    """The conversion must convert exactly one unambiguous authority and never guess a tie."""
    module = _load_migration_module()
    single = _StubConnection([_candidate_row("plan-amb-1")])
    single_tally = module.backfill_legacy_position_protection(single)
    tied = _StubConnection([_candidate_row("plan-amb-1"), _candidate_row("plan-amb-2")])
    tied_tally = module.backfill_legacy_position_protection(tied)
    corrupt = _StubConnection([_candidate_row("plan-amb-1")])
    corrupt._candidates[0]["payload"] = "{not-json"
    corrupt_tally = module.backfill_legacy_position_protection(corrupt)
    return {
        "single_authoritative_converted": single_tally["converted"],
        "single_updates": len(single.updates),
        "two_candidates_not_authoritative": tied_tally["not_authoritative"],
        "two_candidates_converted": tied_tally["converted"],
        "two_candidates_updates": len(tied.updates),
        "unparsable_payload_not_authoritative": corrupt_tally["not_authoritative"],
        "unparsable_payload_updates": len(corrupt.updates),
    }


def _r1_authority_predicate() -> Any | None:
    """Load the *reviewed* R1 migration (`979e5d2`) and return its `_legacy_authority`.

    Used only as a historical witness: evaluating the same probe rows with the R1 predicate shows
    which of the new CASE C probes it accepted, i.e. the actual R1-R01 gap. Returns `None` when the
    reviewed blob is not reachable from this checkout, which the caller reports instead of hiding.
    """
    try:
        blob = subprocess.run(
            ["git", "show", f"{R1_REVIEWED_HEAD}:{MIGRATION_REPO_PATH}"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    staged = Path(tempfile.mkdtemp()) / "r1_migration_0006.py"
    staged.write_text(blob, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("n01_7_f01_r1_migration_0006", staged)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._legacy_authority


def _authority_proof_teeth(fixtures: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Evaluate every CASE C probe with both the R2 and the reviewed R1 predicate.

    `r2_authoritative` must be False everywhere (the fix). `r1_authoritative` is the historical
    witness: it is True for exactly the probes named in `_R1_GAP_CASES`, which is the R1-R01 gap.
    """
    module = _load_migration_module()
    r1_predicate = _r1_authority_predicate()
    witness: dict[str, Any] = {}
    for name, fixture in sorted(fixtures.items()):
        if not fixture["plans"] or not name.startswith("CASE_C_"):
            continue
        row = _candidate_from_fixture(fixture)
        witness[name] = {
            "r2_authoritative": module._legacy_authority(row) is not None,
            "r1_authoritative": (
                None if r1_predicate is None else r1_predicate(_r1_candidate(row)) is not None
            ),
            "in_r1_gap": name in _R1_GAP_CASES,
        }
    return witness


def _single_head() -> dict[str, Any]:
    config = _alembic_config("postgresql+asyncpg://unused/unused")
    script = ScriptDirectory.from_config(config)
    heads = [revision.revision for revision in script.get_revisions("heads")]
    revision = script.get_revision(F01_REVISION)
    return {
        "heads": heads,
        "single_head": heads == [F01_REVISION],
        "f01_down_revision": revision.down_revision,
    }


def _ambiguity_in_schema(url: str) -> dict[str, Any]:
    """Can two ACTIVE plans for one symbol even exist at 0005? Report what actually happens.

    `uq_trade_plans_one_active` is a partial unique index over `(run_mode, instrument_id)` where
    `status = 'ACTIVE'`, so the expected answer is "no, the schema refuses it" and the migration's
    ambiguity branch is then only reachable on a schema-damaged database. The caller asserts the
    conversion against whichever answer it actually gets, so this is evidence either way.
    """
    statements = [
        (
            INSERT_AMBIGUOUS_PLAN_SQL,
            {
                "now": NOW,
                "expires_at": NOW + timedelta(minutes=5),
                "payload": json.dumps(_plan_json(plan_id="plan-r1-amb-2", instrument="DDD-USDT")),
            },
        )
    ]
    try:
        _execute_many(url, statements)
    except IntegrityError as exc:  # the constraint name is the evidence
        return {"second_active_plan_rejected": True, "error": type(exc).__name__}
    return {"second_active_plan_rejected": False, "error": None}


# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------


def main() -> int:
    report: dict[str, Any] = {
        "batch": "N01-7-F01-R2",
        "gate": "disposable-migration-0006",
        "extends": "N01-7-F01-R1",
    }
    primary_before = asyncio.run(_primary_state())
    report["shared_primary_before"] = primary_before
    assert primary_before["alembic_version"] == SHARED_PRIMARY_BASELINE, primary_before
    assert primary_before["disposable_residue"] == 0, primary_before

    report["head"] = _single_head()
    assert report["head"]["single_head"] is True, report["head"]
    assert report["head"]["f01_down_revision"] == FOUNDATION_REVISION, report["head"]

    with _disposable_database() as (name, url):
        report["disposable_database"] = name
        _migrate(url, upgrade_to=FOUNDATION_REVISION)
        report["step_1_foundation"] = {
            "alembic_version": _alembic_version(url),
            "protection_columns": sorted(_protection_columns(url)),
        }
        assert report["step_1_foundation"]["alembic_version"] == FOUNDATION_REVISION
        assert report["step_1_foundation"]["protection_columns"] == []

        fixtures = _seed_fixtures(url)
        # The ambiguity probe runs *before* the retention baseline so any row it adds (only when
        # the schema unexpectedly accepts a second ACTIVE plan) is part of the "before" state.
        report["ambiguity_in_schema"] = _ambiguity_in_schema(url)
        counts_before = _table_counts(url)
        legacy_fp_before = _legacy_position_fingerprint(url)
        report["step_2_legacy_state"] = {
            "positions": counts_before.get("positions"),
            "trade_plans": counts_before.get("trade_plans"),
            "legacy_position_fingerprint": legacy_fp_before,
            "cases": sorted(fixtures),
        }

        _migrate(url, upgrade_to=F01_REVISION)
        columns_after = _protection_columns(url)
        checks_after = _protection_checks(url)
        counts_after = _table_counts(url)
        authority_first = _snapshot_authority(url)
        report["step_3_upgrade"] = {
            "alembic_version": _alembic_version(url),
            "protection_columns": sorted(columns_after),
            "protection_checks": sorted(checks_after),
            "row_counts_unchanged": counts_after == counts_before,
        }
        assert report["step_3_upgrade"]["alembic_version"] == F01_REVISION
        assert columns_after == set(PROTECTION_COLUMNS), columns_after
        assert checks_after == set(PROTECTION_CHECKS), checks_after
        assert counts_after == counts_before, (counts_before, counts_after)

        matrix: dict[str, Any] = {}
        for case, fixture in sorted(fixtures.items()):
            position_id = fixture["position"][0]
            row = authority_first[position_id]
            expect = fixture["expect"]
            if expect == "DYNAMIC":
                continue  # asserted below against the observed ambiguity-probe outcome
            if expect is None:
                assert row["protection_plan_id"] is None, (case, row)
                assert row["protection_plan_version"] is None, (case, row)
                assert row["protection_stop_loss"] is None, (case, row)
                assert row["protection_take_profit"] is None, (case, row)
                assert row["protection_updated_at"] is None, (case, row)
                matrix[case] = "NULL (DO NOT GUESS)"
            else:
                plan_id, plan_version, stop_loss, take_profit, updated_at = expect
                assert row["protection_plan_id"] == plan_id, (case, row)
                assert row["protection_plan_version"] == plan_version, (case, row)
                assert row["protection_stop_loss"] == stop_loss, (case, row)
                assert row["protection_take_profit"] == take_profit, (case, row)
                # Copied from `trade_plans.created_at`, never from a clock: the plan is long expired
                # and its TTL was deliberately ignored.
                assert row["protection_updated_at"] == updated_at, (case, row)
                matrix[case] = f"backfilled {plan_id} v{plan_version} [{stop_loss}, {take_profit}]"

        # The ambiguity rule, asserted against whatever the schema actually allowed above:
        # one candidate -> converted; a tie -> left NULL and never guessed.
        probe = authority_first[fixtures["AMBIGUITY_PROBE"]["position"][0]]
        if report["ambiguity_in_schema"]["second_active_plan_rejected"]:
            assert probe["protection_plan_id"] == "plan-r1-amb-1", probe
            assert probe["protection_stop_loss"] == 80.0 and probe["protection_take_profit"] == 140.0
            matrix["AMBIGUITY_PROBE"] = (
                "second ACTIVE plan rejected by uq_trade_plans_one_active; the single remaining "
                "authority was converted"
            )
        else:
            assert probe["protection_plan_id"] is None, probe
            assert probe["protection_stop_loss"] is None, probe
            matrix["AMBIGUITY_PROBE"] = "two ACTIVE plans -> NULL (DO NOT GUESS)"
        report["step_4_compatibility_matrix"] = matrix
        report["step_5_ambiguity_guard"] = _ambiguity_guard()
        assert report["step_5_ambiguity_guard"]["single_authoritative_converted"] == 1
        assert report["step_5_ambiguity_guard"]["single_updates"] == 1
        assert report["step_5_ambiguity_guard"]["two_candidates_not_authoritative"] == 1
        assert report["step_5_ambiguity_guard"]["two_candidates_converted"] == 0
        assert report["step_5_ambiguity_guard"]["two_candidates_updates"] == 0
        assert report["step_5_ambiguity_guard"]["unparsable_payload_not_authoritative"] == 1
        assert report["step_5_ambiguity_guard"]["unparsable_payload_updates"] == 0

        # R2 authority-proof teeth: the same probe rows, evaluated by both predicates. R2 must
        # refuse every CASE C probe, and the reviewed R1 predicate must have accepted exactly the
        # `_R1_GAP_CASES` -- which is the R1-R01 finding, now closed.
        teeth = _authority_proof_teeth(fixtures)
        report["step_5b_authority_proof_teeth"] = {
            "r1_predicate_loaded": any(
                entry["r1_authoritative"] is not None for entry in teeth.values()
            ),
            "probes": teeth,
        }
        for name, entry in teeth.items():
            assert entry["r2_authoritative"] is False, (name, entry)
        r1_accepted = {
            name
            for name, entry in teeth.items()
            if entry["r1_authoritative"] is True
        }
        assert r1_accepted == set(_R1_GAP_CASES), (sorted(r1_accepted), sorted(_R1_GAP_CASES))
        # The four R1 CASE C probes that do carry a plan, plus every R2 probe (CASE_C_NO_PLAN has
        # no plan row to reason about, so it is asserted through the database matrix only).
        assert len(teeth) == 4 + len(_LEGACY_NEGATIVE_MATRIX), sorted(teeth)

        _migrate(url, downgrade_to=FOUNDATION_REVISION)
        report["step_6_downgrade"] = {
            "alembic_version": _alembic_version(url),
            "protection_columns": sorted(_protection_columns(url)),
            "protection_checks": sorted(_protection_checks(url)),
            "legacy_position_fingerprint": _legacy_position_fingerprint(url),
            "row_counts": _table_counts(url) == counts_before,
        }
        assert report["step_6_downgrade"]["alembic_version"] == FOUNDATION_REVISION
        assert report["step_6_downgrade"]["protection_columns"] == []
        assert report["step_6_downgrade"]["protection_checks"] == []
        assert report["step_6_downgrade"]["legacy_position_fingerprint"] == legacy_fp_before
        assert report["step_6_downgrade"]["row_counts"] is True

        _migrate(url, upgrade_to=F01_REVISION)
        authority_second = _snapshot_authority(url)
        differing = sorted(
            position_id
            for position_id in authority_first
            if authority_first[position_id] != authority_second[position_id]
        )
        report["step_7_reupgrade"] = {
            "alembic_version": _alembic_version(url),
            "cycle_reproduced_identical_values": differing == [],
            "differing_positions": differing,
        }
        assert report["step_7_reupgrade"]["alembic_version"] == F01_REVISION
        assert report["step_7_reupgrade"]["cycle_reproduced_identical_values"] is True

    primary_after = asyncio.run(_primary_state())
    report["shared_primary_after"] = primary_after
    assert primary_after == primary_before, (primary_before, primary_after)

    report["result"] = "PASS"
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
