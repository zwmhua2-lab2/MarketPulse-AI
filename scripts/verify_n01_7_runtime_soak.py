"""N01-7 — 2-hour Medium Runtime Soak (validation-only thin layer over the accepted N01-6 harness).

Why this file exists
--------------------
N01-7 needs the *same* accepted runtime components as N01-6 to run for >= 7200 s, plus evidence
N01-6 did not have to produce: 8 x 15-minute progress windows, dedupe turnover across a long run,
a durable-protection-snapshot witness that outlives the originating TradePlan TTL (N01-7-F01), and
a per-window reconciliation read. None of that is a second runtime.

Reuse contract (N01-7 task spec section 6)
------------------------------------------
The accepted `scripts/verify_n01_6_runtime_smoke.py` is **imported, never copied and never edited**.
Every runtime object below is constructed by that module: `OKXLiveProvider`, `ScannerPipeline`,
`OpportunityScanner`, `EventRuntime`, `PostgresG2Repository`, `SmokeHarness` (which itself extends
the accepted N01-B `LivePaperHarness`: `SafetyRuntime`, `PositionProtectionService`,
`SystemRiskGate`, `PaperExecutionService`), the market consumer, the disposable-database factory and
the PostgreSQL ownership split all come from it unchanged. This module only adds:

* the 7200 s duration and the 8 x 900 s window collection,
* the N01-7-specific analyses (dedupe turnover, RSS trend, PostgreSQL session trend),
* the N01-7-F01 long-lived protection observation,
* the final acceptance report.

Two explicitly authorised deviations from the accepted harness invocation (environment/topology,
not product behaviour). Both were reported to, and approved by, the human operator in this window:

1. **PostgreSQL topology** — the accepted harness creates its disposable database on the server
   reached by `Settings().database_url`. N01-7 points that setting at a *task-owned disposable
   PostgreSQL container* (`127.0.0.1:5434`) via a gitignored `.env`, so the runtime process never
   has a shared-primary DSN at all. `checks["runtime_dsn_points_at_task_owned_instance"]` fails
   closed if that ever stops being true.
2. **OKX REST transport** — the surrounding sandbox injects `HTTP(S)_PROXY` pointing at a local
   proxy that returns 502 for OKX, and direct `www.okx.com` / `aws.okx.com` resolution fails from
   Python. The single OKX REST metadata lookup is therefore routed through the machine's existing
   user proxy for the duration of that one call; the public WebSocket stays direct. NOTHING else
   uses a proxy, and no machine or system proxy setting is written.

Claim boundary (must not be overstated)
---------------------------------------
Even on PASS this proves only "accepted production runtime components, inside a validation harness,
stable for >= 2 hours". It is NOT the Integrated Runtime Host, NOT a FastAPI 7x24 runtime, NOT a
daemon/service, NOT a deployment, NOT N01 overall acceptance, NOT N01-8, NOT live trading.
`Integrated Runtime Host` remains `NOT STARTED` and `N01 overall` remains `NOT ACCEPTED`.

Run (explicit opt-in; never part of the deterministic pytest suite)::

    py -3.14 scripts/verify_n01_7_runtime_soak.py --seconds 180            # PROBE only
    py -3.14 scripts/verify_n01_7_runtime_soak.py --seconds 7200 \
        --raw-out E:/Temp/n01-7-soak/acceptance_raw.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = str(REPOSITORY_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Importing the accepted harness is the whole point: it clears the sandbox proxy for this process
# and puts `backend/src` + `backend/tests` on `sys.path`. It is never modified by this module.
import verify_n01_6_runtime_smoke as n6
from marketpulse.config import Settings
from marketpulse.db.models import (
    IncidentRecord,
    PositionRecord,
    RuntimeControlRecord,
    TradePlanRecord,
)
from marketpulse.g4.models import (
    HealthComponent,
    IncidentStatus,
    IncidentType,
    OperatorState,
    SystemState,
)
from marketpulse.g4.planning import (
    load_active_plan,
    load_valid_long_active_plan,
    resolve_open_position_protection,
)
from marketpulse.g4.reconciliation import count_open_buys, reconcile
from marketpulse.market_data.okx_live import OKXLiveProvider
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

RUN_MODE = n6.RUN_MODE
BTC = n6.BTC
ETH = n6.ETH
INSTRUMENTS = n6.INSTRUMENTS

# ---- N01-7 identity / acceptance parameters -------------------------------------------------
DEFAULT_ACTIVE_SECONDS = 7200.0
ACCEPTANCE_MIN_ACTIVE_SECONDS = 7200.0
PROBE_MAX_ACTIVE_SECONDS = 300.0
DEFAULT_WINDOW_SECONDS = 900.0
DEFAULT_WINDOW_COUNT = 8
DEFAULT_SAMPLE_INTERVAL_SECONDS = 10.0

F01_PROTECTION_REVISION = "20260912_0006"


def _current_migration_head() -> str:
    """Return the repository's single current Alembic head without connecting to a database.

    `20260912_0006` remains the immutable F01 protection migration, but it is no longer the
    repository head after accepted Edge migrations.  A latest-main validation must therefore
    derive the current head from the checked-out lineage rather than treating the historical
    F01 revision as a perpetual head pin.
    """
    config = Config()
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "backend" / "alembic"))
    heads = list(ScriptDirectory.from_config(config).get_heads())
    if len(heads) != 1:
        raise RuntimeError(f"expected one Alembic head, found {heads!r}")
    return heads[0]


EXPECTED_MIGRATION_HEAD = _current_migration_head()

# The immutable F01 Position-protection contract: the revision that introduced these columns, and
# the columns themselves. A latest-main validation must prove both survived the newer accepted Edge
# migrations, without re-pinning the head to the historical revision.
F01_PROTECTION_COLUMNS = frozenset(
    {
        "protection_plan_id",
        "protection_plan_version",
        "protection_stop_loss",
        "protection_take_profit",
        "protection_updated_at",
    }
)


def _migration_lineage() -> dict[str, Any]:
    """Static, database-free proof of the checked-out migration lineage.

    Two facts have to hold together: the lineage has exactly one head (so `upgrade head` is
    unambiguous), and `20260912_0006` is still an *ancestor* of that head (so the F01 protection
    contract is being validated against a lineage that actually contains the protection migration,
    rather than one where it was dropped, re-based or bypassed by an accepted Edge migration).
    """
    config = Config()
    config.set_main_option("script_location", str(REPOSITORY_ROOT / "backend" / "alembic"))
    script = ScriptDirectory.from_config(config)
    heads = sorted(script.get_heads())
    revisions = sorted({revision.revision for revision in script.walk_revisions()})
    return {
        "heads": heads,
        "single_head": len(heads) == 1,
        "head": heads[0] if len(heads) == 1 else None,
        "f01_protection_revision": F01_PROTECTION_REVISION,
        "f01_protection_is_ancestor_of_head": F01_PROTECTION_REVISION in revisions,
        "revision_count": len(revisions),
        "lineage": revisions,
    }


async def _protection_schema(database_url: str) -> dict[str, Any]:
    """Read back the migration-written Position protection schema from the disposable database.

    Read-only, and only ever against the task-owned disposable instance. It is the database-side
    half of the lineage proof: the columns F01 introduced must still exist after the newer accepted
    migrations have been applied on top.
    """
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_name = 'positions' "
                        "AND column_name LIKE 'protection_%' "
                        "ORDER BY column_name"
                    )
                )
            ).mappings()
            columns = [dict(row) for row in rows]
        return {
            "protection_columns": columns,
            "protection_column_names": sorted(item["column_name"] for item in columns),
            "expected_columns_present": F01_PROTECTION_COLUMNS
            <= {item["column_name"] for item in columns},
        }
    finally:
        await engine.dispose()


TASK_OWNED_DATABASE_PORT = "5434"
# The repository's own default DSN. Recorded read-only before/after the run ONLY; never used by
# the runtime, which is pointed at the task-owned disposable instance by `.env`.
SHARED_PRIMARY_URL = "postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5432/marketpulse"

# N01-7 ownership domains (the reused module reads these module globals at call time).
N01_7_DATABASE_PREFIX = "marketpulse_n01_7_r01_"
N01_7_OWNED_APPLICATION = "marketpulse-n01-7-r01-runtime"
N01_7_OBSERVER_APPLICATION = "marketpulse-n01-7-r01-observer"

# The machine's existing user proxy. Used ONLY for the single OKX REST metadata lookup.
OKX_REST_PROXY_ENV = "http://127.0.0.1:10808"
_PROXY_ENV_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)

# N01-7-F01 observation parameters.
POST_EXPIRY_WITNESS_DELAY_SECONDS = 60.0
FRESH_QUOTE_MAX_AGE_SECONDS = n6.FRESH_QUOTE_MAX_AGE_SECONDS

# Long-run stability thresholds (declared up front so the verdict is not fitted after the fact).
STALE_PERIOD_ALERT_SECONDS = 300.0
RSS_GROWTH_ALERT_FRACTION = 0.25

# ---------------------------------------------------------------------------------------------
# Rebind the reused harness to the N01-7 ownership domains (validation-side identity only).
# ---------------------------------------------------------------------------------------------
n6.DATABASE_PREFIX = N01_7_DATABASE_PREFIX
n6.OWNED_APPLICATION = N01_7_OWNED_APPLICATION
n6.OBSERVER_APPLICATION = N01_7_OBSERVER_APPLICATION

# Checks that can only be satisfied by a real >= 7200 s run: they are reported but excluded from
# the failure list of a short PROBE, exactly like the duration check itself.
ACCEPTANCE_SCOPE_KEYS = frozenset(
    {
        "active_duration_ge_acceptance",
        "windows_observed_with_samples",
        "market_data_continuity_all_windows",
        "dedupe_long_run_turnover",
        "reconciliation_ok_all_windows",
    }
)

MARKET_PATH_F01_KEYS = frozenset(
    {
        "f01_plan_expired_observed",
        "f01_plan_no_longer_risk_increasing_valid",
        "f01_position_still_open_after_expiry",
        "f01_protection_snapshot_complete_after_expiry",
        "f01_snapshot_matches_originating_plan",
        "f01_protection_service_uses_snapshot_after_expiry",
        "f01_no_position_unprotected_incident",
        "f01_runtime_not_safe_mode",
        "f01_expired_plan_blocks_risk_increasing",
        "f01_no_economic_fact_from_probe",
    }
)

# Plan attributes the production execution path reads for an intent: `plan.side` in
# `PaperExecutionService._execute_once` / `SystemRiskGate`, plus `plan.instrument_id` /
# `plan.plan_id` in `SmokeHarness.execute_intent` and `plan.entry_zone` / `plan.order_type`
# further down the same path. The witness asserts these exist before calling production so a
# missing attribute surfaces as a named harness error instead of an AttributeError mid-run.
PLAN_FIELDS_READ_BY_EXECUTION = ("plan_id", "instrument_id", "side", "entry_zone", "order_type")


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(UTC)


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 6) if values else None


def _slope_per_hour(points: list[tuple[float, float]]) -> float | None:
    """Least-squares slope of `value` against `elapsed_seconds`, expressed per hour."""
    if len(points) < 2:
        return None
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope_per_second = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / (
        denominator
    )
    return round(slope_per_second * 3600.0, 6)


@contextmanager
def _okx_rest_proxy():
    """Route ONLY the single OKX REST metadata lookup through the machine's existing user proxy.

    Process-local environment edit; no product configuration, no machine or system proxy change.
    The proxy is removed again before the public WebSocket is opened.
    """
    saved = {name: os.environ.get(name) for name in _PROXY_ENV_NAMES}
    for name in _PROXY_ENV_NAMES:
        os.environ[name] = OKX_REST_PROXY_ENV
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _dsn_identity(url: str) -> dict[str, Any]:
    """Credentials-free identity of a DSN, so the report can prove which server was used."""
    tail = url.rsplit("@", 1)[-1]
    host_port, _, database = tail.partition("/")
    host, _, port = host_port.partition(":")
    return {"host": host, "port": port, "database": database, "scheme": url.split("://", 1)[0]}


async def _alembic_version(database_url: str) -> str | None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        return str(value) if value is not None else None
    finally:
        await engine.dispose()


async def _shared_primary_snapshot(primary_url: str) -> dict[str, Any]:
    """READ-ONLY observation of the shared primary (revision + protection columns + sessions).

    Deliberately NEVER called by the soak: the runtime opens no shared-primary connection at all.
    It exists so a wrapper can take the specification section 9 before/after record with an
    explicit, attributable application name, without smuggling that connection into the run.
    """
    engine = create_async_engine(
        primary_url,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"application_name": "marketpulse-shared-primary-observer"}
        },
    )
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            columns = (
                await connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'positions' AND column_name LIKE 'protection_%' "
                        "ORDER BY column_name"
                    )
                )
            ).scalars()
            sessions = (
                await connection.execute(
                    text(
                        "SELECT application_name, count(*) AS n FROM pg_stat_activity "
                        "WHERE backend_type = 'client backend' "
                        "AND datname = current_database() GROUP BY application_name "
                        "ORDER BY application_name"
                    )
                )
            ).mappings()
            n01_7_sessions = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE backend_type = 'client backend' "
                        "AND application_name LIKE 'marketpulse-n01-7-%'"
                    )
                )
            ).scalar()
        return {
            "revision": revision,
            "protection_columns": list(columns),
            "client_sessions_by_application": [dict(row) for row in sessions],
            "n01_7_owned_sessions_visible": int(n01_7_sessions or 0),
        }
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------------------------
# Per-sample database state (position + durable protection snapshot + plan + runtime control)
# ---------------------------------------------------------------------------------------------
async def _db_state(sessions) -> dict[str, Any]:
    async with sessions() as session:
        position = await session.scalar(
            select(PositionRecord).where(
                PositionRecord.run_mode == RUN_MODE, PositionRecord.instrument_id == BTC
            )
        )
        plans = list(
            (
                await session.scalars(
                    select(TradePlanRecord).where(
                        TradePlanRecord.run_mode == RUN_MODE,
                        TradePlanRecord.instrument_id == BTC,
                        TradePlanRecord.status == "ACTIVE",
                    )
                )
            ).all()
        )
        control = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RUN_MODE)
        )
        open_incidents = int(
            await session.scalar(
                select(func.count())
                .select_from(IncidentRecord)
                .where(
                    IncidentRecord.run_mode == RUN_MODE,
                    IncidentRecord.status == IncidentStatus.OPEN.value,
                )
            )
            or 0
        )
        unprotected = int(
            await session.scalar(
                select(func.count())
                .select_from(IncidentRecord)
                .where(
                    IncidentRecord.run_mode == RUN_MODE,
                    IncidentRecord.instrument_id == BTC,
                    IncidentRecord.incident_type == IncidentType.POSITION_UNPROTECTED.value,
                    IncidentRecord.status == IncidentStatus.OPEN.value,
                )
            )
            or 0
        )
        stale = int(
            await session.scalar(
                select(func.count())
                .select_from(IncidentRecord)
                .where(
                    IncidentRecord.run_mode == RUN_MODE,
                    IncidentRecord.instrument_id == BTC,
                    IncidentRecord.incident_type == IncidentType.CORE_DATA_STALE.value,
                    IncidentRecord.status == IncidentStatus.OPEN.value,
                )
            )
            or 0
        )

    now = _now()
    protection = (
        {
            "protection_plan_id": position.protection_plan_id,
            "protection_plan_version": position.protection_plan_version,
            "protection_stop_loss": position.protection_stop_loss,
            "protection_take_profit": position.protection_take_profit,
            "protection_updated_at": position.protection_updated_at.isoformat()
            if position.protection_updated_at
            else None,
            "present": resolve_open_position_protection(position) is not None,
        }
        if position is not None
        else {"present": False}
    )
    active_plan = plans[0] if len(plans) == 1 else None
    return {
        "position_quantity": position.quantity if position is not None else None,
        "position_average_cost": position.average_cost if position is not None else None,
        "position_trade_id": position.trade_id if position is not None else None,
        "protection": protection,
        "active_plan_count": len(plans),
        "plan_status": active_plan.status if active_plan is not None else None,
        "plan_plan_id": active_plan.plan_id if active_plan is not None else None,
        "plan_plan_version": active_plan.plan_version if active_plan is not None else None,
        "plan_expires_at": active_plan.expires_at.isoformat() if active_plan is not None else None,
        "plan_expired": bool(active_plan is not None and now >= active_plan.expires_at),
        "operator_state": control.operator_state if control is not None else None,
        "system_state": control.system_state if control is not None else None,
        "open_incidents": open_incidents,
        "open_position_unprotected_incidents": unprotected,
        "open_core_data_stale_incidents": stale,
    }


# ---------------------------------------------------------------------------------------------
# N01-7-F01 witness
# ---------------------------------------------------------------------------------------------
async def _f01_witness(
    harness: n6.SmokeHarness,
    sessions,
    feed: dict[str, Any],
    entry_plan_id: str | None,
    checks: dict[str, bool],
) -> dict[str, Any]:
    """Prove the durable position snapshot is the protection-lifetime authority after plan TTL.

    Performed strictly as observation on the real, unmodified production path:

    * the TradePlan is genuinely expired and no longer a risk-increasing authority,
    * the OPEN position still carries a complete durable snapshot whose identity is the
      originating plan,
    * `PositionProtectionService.evaluate` still resolves that snapshot (HOLD, not
      POSITION_UNPROTECTED) on a real fresh BBO,
    * a new risk-increasing BUY through the expired plan is refused and creates no economic fact.

    The expired plan object is taken from the production durable loader `load_active_plan` -- the
    canonical ACTIVE-plan reader, which carries no TTL gate -- instead of a hand-built stand-in.
    The production path reads several plan attributes (`side`, `entry_zone`, `order_type`, ...), so
    a synthetic view risks silently missing one; a real `TradePlan` cannot.

    Nothing here fabricates market data, widens a protection level, or triggers a close.
    """
    evidence: dict[str, Any] = {"observed_at": _now().isoformat()}
    now = harness.clock.now()

    position = await n6._position(sessions, RUN_MODE, BTC)
    authority = resolve_open_position_protection(position) if position is not None else None
    async with sessions() as session:
        plan = await load_active_plan(session, RUN_MODE, BTC)
        valid_plan = await load_valid_long_active_plan(session, RUN_MODE, BTC, now=now)

    evidence["position_quantity"] = position.quantity if position is not None else None
    if plan is None or (entry_plan_id is not None and plan.plan_id != entry_plan_id):
        # Harness-side failure: the durable ACTIVE plan could not be obtained, or it is not the
        # plan that opened this position. Recorded explicitly and classified as a harness error so
        # that a 7200 s run is not thrown away -- and never reported as a product result.
        evidence["harness_error"] = {
            "reason": "durable_active_plan_unavailable_for_witness",
            "entry_plan_id": entry_plan_id,
            "loaded_plan_id": None if plan is None else plan.plan_id,
        }
        checks["f01_witness_harness_ok"] = False
        return evidence
    missing = [name for name in PLAN_FIELDS_READ_BY_EXECUTION if not hasattr(plan, name)]
    if missing:
        # Explicit, named harness failure instead of an AttributeError raised deep inside the
        # production execute path (which is what a hand-built stand-in caused before).
        evidence["harness_error"] = {
            "reason": "plan_object_missing_fields_read_by_production_execution",
            "missing": missing,
            "plan_id": plan.plan_id,
        }
        checks["f01_witness_harness_ok"] = False
        return evidence
    checks["f01_witness_harness_ok"] = True

    evidence["plan"] = {
        "plan_id": plan.plan_id,
        "plan_version": plan.plan_version,
        "side": str(plan.side),
        "expires_at": plan.expires_at.isoformat(),
        "expired_at_observation": now >= plan.expires_at,
        "load_valid_long_active_plan": None if valid_plan is None else valid_plan.plan_id,
    }
    checks["f01_plan_expired_observed"] = now >= plan.expires_at
    checks["f01_plan_no_longer_risk_increasing_valid"] = valid_plan is None

    checks["f01_position_still_open_after_expiry"] = bool(
        position is not None and position.quantity > 0.0
    )
    evidence["protection"] = await _db_state(sessions)
    protection = evidence["protection"]["protection"]
    complete = bool(
        protection.get("present")
        and protection.get("protection_plan_id")
        and protection.get("protection_plan_version")
        and protection.get("protection_stop_loss") is not None
        and protection.get("protection_take_profit") is not None
        and protection.get("protection_updated_at")
    )
    checks["f01_protection_snapshot_complete_after_expiry"] = complete
    checks["f01_snapshot_matches_originating_plan"] = bool(
        authority is not None
        and authority.plan_id == plan.plan_id
        and authority.plan_version == plan.plan_version
        and authority.stop_loss == plan.stop_loss
        and authority.take_profit == plan.take_profit
    )
    evidence["authority"] = (
        None
        if authority is None
        else {
            "plan_id": authority.plan_id,
            "plan_version": authority.plan_version,
            "stop_loss": authority.stop_loss,
            "take_profit": authority.take_profit,
        }
    )

    # The protection service must still resolve the snapshot on a real fresh BBO.
    fresh_ready = await n6._wait_until(
        lambda: (
            BTC in feed["latest_bbo"]
            and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
            <= FRESH_QUOTE_MAX_AGE_SECONDS
        ),
        timeout=30.0,
    )
    outcome = None
    if fresh_ready:
        bbo = feed["latest_bbo"][BTC]
        harness.publish_quote(bbo)
        outcome = await harness.protection.evaluate(RUN_MODE, BTC, bbo, now=harness.clock.now())
    evidence["evaluate"] = (
        None
        if outcome is None
        else {
            "triggered": outcome.triggered,
            "reason": outcome.reason,
            "trigger": str(outcome.trigger),
        }
    )
    checks["f01_protection_service_uses_snapshot_after_expiry"] = bool(
        fresh_ready
        and outcome is not None
        and outcome.triggered is False
        and outcome.reason == "HOLD"
    )

    state = evidence["protection"]
    checks["f01_no_position_unprotected_incident"] = (
        state["open_position_unprotected_incidents"] == 0
    )
    checks["f01_runtime_not_safe_mode"] = (
        state["system_state"] != SystemState.SAFE_MODE.value
        and state["operator_state"] == OperatorState.NORMAL.value
    )

    # The plan TTL must keep blocking the expired plan as a risk-increasing authority.
    counts_before = await n6._economic_counts(sessions, RUN_MODE)
    admitted, gate_reason = await harness.risk_gate.check(RUN_MODE, BTC, plan_id=plan.plan_id)
    probe = await harness.execute_intent(plan, tag="post-ttl-risk-increasing-probe")
    counts_after = await n6._economic_counts(sessions, RUN_MODE)
    evidence["risk_gate_after_expiry"] = {"admitted": admitted, "reason": gate_reason}
    evidence["probe"] = {"status": str(probe.status), "reason": probe.reason}
    checks["f01_expired_plan_blocks_risk_increasing"] = bool(
        admitted is False and gate_reason == "PLAN_EXPIRED" and probe.reason == "PLAN_EXPIRED"
    )
    checks["f01_no_economic_fact_from_probe"] = counts_after == counts_before
    evidence["economic_counts"] = {"before": counts_before, "after": counts_after}
    return evidence


# ---------------------------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------------------------
async def _scenario(
    database_name: str,
    database_url: str,
    active_seconds: float,
    sample_interval: float,
    window_seconds: float,
    window_count: int,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure: dict[str, Any] | None = None
    samples: list[dict[str, Any]] = []
    window_reconciliations: list[dict[str, Any]] = []
    feed = n6._new_feed()
    ctx: dict[str, Any] = {
        "feed": feed,
        "samples": samples,
        "window_reconciliations": window_reconciliations,
        "active_seconds_requested": active_seconds,
        "window_seconds": window_seconds,
        "window_count": window_count,
    }
    engine = None
    observer = None
    runtime = None
    consumer: asyncio.Task | None = None
    sampler: asyncio.Task | None = None
    stream = None
    provider = OKXLiveProvider()

    try:
        engine = n6._smoke_engine(database_url)
        observer = n6._observer_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ctx["sessions"] = sessions

        ctx["dsn"] = _dsn_identity(database_url)
        checks["runtime_dsn_points_at_task_owned_instance"] = (
            ctx["dsn"]["port"] == TASK_OWNED_DATABASE_PORT
        )
        ctx["baseline"] = await n6._ownership_activity(observer, database_name)

        # --- OKX REST metadata: the single proxied call of this run -----------------------------
        rest_started = time.monotonic()
        with _okx_rest_proxy():
            ctx["metadata"] = await n6._okx_metadata(provider)
        ctx["okx_rest_transport"] = {
            "proxy_used_for_rest_only": True,
            "proxy": OKX_REST_PROXY_ENV,
            "elapsed_seconds": round(time.monotonic() - rest_started, 3),
            "ws_direct": True,
        }

        harness = n6.SmokeHarness(sessions)
        await harness.boot()
        ctx["harness"] = harness
        runtime = n6.EventRuntime(n6.PostgresG2Repository(sessions))
        pipeline = n6.ScannerPipeline(n6.OpportunityScanner(), runtime)
        await runtime.start()
        ctx["runtime"] = runtime
        ctx["pipeline"] = pipeline

        stream = provider.stream(list(n6.CHANNELS))
        ctx["stream"] = stream
        consumer = asyncio.create_task(
            n6._consume(stream, pipeline, harness, feed), name="n01-7-market-consumer"
        )
        ctx["consumer"] = consumer
        ctx["rss_start"] = n6._rss_mb()

        def initial_data_ready() -> bool:
            return all(feed["trades"][item] > 0 and feed["bbos"][item] > 0 for item in INSTRUMENTS)

        ready = await n6._wait_until(initial_data_ready, n6.INITIAL_DATA_MAX_WAIT_SECONDS, 0.2)
        checks["initial_real_data_both_symbols"] = ready
        if not ready:
            raise AssertionError("real BTC/ETH trade+BBO data did not arrive in time")

        active_started_at = _now()
        ctx["active_started_monotonic"] = time.monotonic()
        ctx["active_started_at"] = active_started_at
        entry_offset = min(60.0, max(10.0, active_seconds * 0.10))
        entry_plan_id: str | None = None
        expiry_crossed = False
        witness_at: float | None = None

        async def sample_once() -> dict[str, Any]:
            activity = await n6._ownership_activity(observer, database_name)
            state = await _db_state(sessions)
            now = _now()
            snapshot = {
                "at": now.isoformat(),
                "elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
                "btc_trades": feed["trades"][BTC],
                "btc_bbos": feed["bbos"][BTC],
                "eth_trades": feed["trades"][ETH],
                "eth_bbos": feed["bbos"][ETH],
                "total_events": feed["total_normalized_events"],
                "btc_last_trade_age_seconds": _age(feed["last_trade_received"].get(BTC)),
                "btc_last_bbo_age_seconds": _age(feed["last_bbo_received"].get(BTC)),
                "eth_last_trade_age_seconds": _age(feed["last_trade_received"].get(ETH)),
                "eth_last_bbo_age_seconds": _age(feed["last_bbo_received"].get(ETH)),
                "btc_fresh": feed["last_freshness"].get(BTC, {}).get("fresh"),
                "eth_fresh": feed["last_freshness"].get(ETH, {}).get("fresh"),
                "btc_data_quality": feed["bbo_data_quality"].get(BTC),
                "eth_data_quality": feed["bbo_data_quality"].get(ETH),
                "health_status": harness.health.status(HealthComponent.CORE_MARKET_DATA.value),
                "connection_attempts": provider.connection_attempts,
                "reconnects": provider.reconnects,
                "queue_size": runtime.queue.qsize(),
                "queue_capacity": runtime.queue.maxsize,
                "inflight": len(runtime._inflight),
                "worker_count": len(runtime._workers),
                "workers_alive": sum(1 for task in runtime._workers if not task.done()),
                "worker_exceptions": len(runtime.worker_exceptions),
                "worker_exception_capacity": runtime._worker_exception_capacity,
                "dedupe_size": len(runtime._dedupe),
                "dedupe_capacity": runtime._dedupe_capacity,
                "dedupe_oldest": runtime._dedupe_fifo[0] if runtime._dedupe_fifo else None,
                "trade_dedupe_size": len(pipeline._trade_dedupe),
                "trade_dedupe_capacity": pipeline._trade_dedupe_capacity,
                "trade_dedupe_oldest": pipeline._trade_dedupe_fifo[0]
                if pipeline._trade_dedupe_fifo
                else None,
                "rss_mb": n6._rss_mb(),
                "pg_owned_client_sessions": activity["owned_client_sessions"],
                "pg_other_client_sessions": activity["other_client_sessions"],
                "pg_idle_in_transaction": activity["idle_in_transaction"],
                "runtime_errors": len(feed["errors"]),
                **state,
            }
            samples.append(snapshot)
            return snapshot

        async def sample_loop() -> None:
            while True:
                try:
                    await sample_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 - recorded, never fabricated
                    feed["errors"].append(
                        {
                            "at": _now().isoformat(),
                            "instrument_id": None,
                            "type": type(exc).__name__,
                            "message": f"n01-7-sampler: {exc}",
                        }
                    )
                await asyncio.sleep(sample_interval)

        await sample_once()
        sampler = asyncio.create_task(sample_loop(), name="n01-7-sampler")
        ctx["sampler"] = sampler

        entry_done = False
        next_window = 1
        while True:
            elapsed = time.monotonic() - ctx["active_started_monotonic"]

            if not entry_done and elapsed >= entry_offset:

                def entry_ready() -> bool:
                    return (
                        harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                        and BTC in feed["latest_bbo"]
                        and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                        <= FRESH_QUOTE_MAX_AGE_SECONDS
                        and feed["last_freshness"].get(BTC, {}).get("fresh") is True
                    )

                await n6._wait_until(entry_ready, timeout=n6.ENTRY_GATE_MAX_WAIT_SECONDS)
                ctx["entry"] = await n6._controlled_entry(harness, sessions, feed, checks)
                entry_plan_id = ctx["entry"]["plan"]["plan_id"]
                entry_done = True

            # --- reconcile at every window boundary (detector only, never a repair) -------------
            if elapsed >= next_window * window_seconds and next_window < window_count:
                report_obj = await reconcile(
                    RUN_MODE,
                    sessions=sessions,
                    execution=harness.execution,
                    now=harness.clock.now(),
                )
                window_reconciliations.append(
                    {
                        "window_index": next_window,
                        "at": _now().isoformat(),
                        "elapsed_seconds": round(elapsed, 3),
                        "ok": report_obj.ok,
                        "diagnostics": list(report_obj.diagnostics),
                        "invariants": dict(report_obj.invariants),
                    }
                )
                next_window += 1

            # --- N01-7-F01: detect genuine plan expiry, then observe well after it --------------
            if entry_done:
                state = samples[-1]
                if not expiry_crossed and state.get("plan_expired"):
                    expiry_crossed = True
                    ctx["expiry_crossed_at"] = state["at"]
                    ctx["expiry_crossed_elapsed_seconds"] = state["elapsed_seconds"]
                    witness_at = state["elapsed_seconds"] + POST_EXPIRY_WITNESS_DELAY_SECONDS
                if (
                    expiry_crossed
                    and witness_at is not None
                    and "f01" not in ctx
                    and elapsed >= witness_at
                ):
                    ctx["f01"] = await _f01_witness(harness, sessions, feed, entry_plan_id, checks)
                    ctx["f01_elapsed_seconds"] = round(elapsed, 3)

            if elapsed >= active_seconds:
                break
            await asyncio.sleep(0.5)

        ctx["active_duration_seconds"] = time.monotonic() - ctx["active_started_monotonic"]
        ctx["active_finished_at"] = _now()
        checks["active_duration_ge_acceptance"] = (
            ctx["active_duration_seconds"] >= ACCEPTANCE_MIN_ACTIVE_SECONDS
        )
        checks["controlled_entry_performed"] = "entry" in ctx
        if not entry_done:
            raise AssertionError("controlled entry never executed during the active window")

        await n6._wait_until(
            lambda: (
                BTC in feed["latest_bbo"]
                and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                <= FRESH_QUOTE_MAX_AGE_SECONDS
            ),
            timeout=30.0,
        )
        ctx["exit"] = await n6._controlled_close(harness, sessions, feed, checks)

        # ---------------------------------------------------------------- shutdown (spec section 24)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        consumer = None
        ctx["consumer"] = None
        await stream.aclose()
        stream = None
        ctx["stream"] = None
        await runtime.stop()
        sampler.cancel()
        await asyncio.gather(sampler, return_exceptions=True)
        sampler = None
        ctx["sampler"] = None

        ctx["queue_final"] = runtime.queue.qsize()
        ctx["inflight_final"] = len(runtime._inflight)
        ctx["workers_final"] = len(runtime._workers)
        ctx["worker_exceptions_final"] = len(runtime.worker_exceptions)
        ctx["worker_tasks_final"] = [
            task.get_name()
            for task in asyncio.all_tasks()
            if task.get_name().startswith("g2-event-worker-") and not task.done()
        ]
        checks["queue_drained"] = ctx["queue_final"] == 0
        checks["inflight_empty"] = ctx["inflight_final"] == 0
        checks["runtime_workers_stopped"] = (
            ctx["workers_final"] == 0 and not ctx["worker_tasks_final"]
        )
        checks["worker_exceptions_zero"] = ctx["worker_exceptions_final"] == 0

        ctx["counts_final"] = await n6._economic_counts(sessions, RUN_MODE)
        ctx["account_final"] = await n6._account(sessions)
        position_final = await n6._position(sessions, RUN_MODE, BTC)
        ctx["position_final"] = {
            "quantity": position_final.quantity if position_final else 0.0,
            "average_cost": position_final.average_cost if position_final else None,
            "protection_present": (
                resolve_open_position_protection(position_final) is not None
                if position_final is not None
                else False
            ),
            "protection_plan_id": (
                position_final.protection_plan_id if position_final is not None else None
            ),
        }
        ctx["open_buys_final"] = await count_open_buys(sessions, RUN_MODE)
        ctx["sell_fills"] = [fill.fill_id for fill in await n6._sell_fills(sessions, RUN_MODE)]
        ctx["trade_final"] = await n6._trade(sessions)
        ctx["fills_final"] = await n6._fill_facts(sessions)

        report_obj = await reconcile(
            RUN_MODE, sessions=sessions, execution=harness.execution, now=harness.clock.now()
        )
        ctx["reconciliation"] = report_obj
        checks["reconciliation_ok"] = report_obj.ok is True
        checks["final_position_flat"] = ctx["position_final"]["quantity"] == 0.0
        checks["final_no_open_buy"] = ctx["open_buys_final"] == 0
        checks["final_exactly_one_exit_fill"] = len(ctx["sell_fills"]) == 1
        checks["final_single_trade_lifecycle"] = (
            ctx["trade_final"] is not None and ctx["trade_final"]["status"] == "CLOSED"
        )
        checks["final_no_duplicate_facts"] = (
            ctx["counts_final"]["orders"] == 2
            and ctx["counts_final"]["fills"] == 2
            and ctx["counts_final"]["positions"] == 1
        )
        checks["final_reserved_cash_zero"] = bool(
            ctx["account_final"] and ctx["account_final"]["reserved_cash"] == 0
        )
        checks["final_cash_non_negative"] = bool(
            ctx["account_final"] and ctx["account_final"]["cash_balance"] >= 0
        )
        # Section 17: a flat position must not retain a durable protection snapshot.
        checks["final_protection_snapshot_cleared_when_flat"] = (
            ctx["position_final"]["protection_present"] is False
            and ctx["position_final"]["protection_plan_id"] is None
        )

        ctx["background_tasks"] = await n6._settle_background_tasks()
        checks["no_detached_runtime_tasks"] = (
            ctx["background_tasks"]["remaining_pending_tasks"] == []
        )
        checks["shutdown_no_errors"] = True

        ctx["rss_end"] = n6._rss_mb()
        await engine.dispose()
        engine = None
        await observer.dispose()
        observer = None

        cleanup = await n6._wait_for_owned_client_cleanup(database_name, N01_7_OWNED_APPLICATION)
        ctx["cleanup"] = cleanup
        checks["pg_owned_clients_zero"] = cleanup.final_snapshot.client_sessions == 0
        checks["pg_idle_in_transaction_zero"] = cleanup.final_snapshot.idle_in_transaction == 0
        checks["pg_no_foreign_client_sessions"] = not cleanup.foreign_rows

        for instrument, period in list(feed["open_stale"].items()):
            period.pop("start_monotonic", None)
            period["end"] = ctx["active_finished_at"].isoformat()
            period["duration_seconds"] = round(ctx["active_duration_seconds"], 6)
            feed["stale_periods"].append(period)
        feed["open_stale"].clear()

        checks["no_harness_event_errors"] = feed["errors"] == []
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - always report, then shut down in `finally`
        failure = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        shutdown_errors: list[dict[str, Any]] = []
        if sampler is not None:
            sampler.cancel()
            await asyncio.gather(sampler, return_exceptions=True)
        if consumer is not None:
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)
        if stream is not None:
            try:
                await stream.aclose()
            except Exception as exc:  # noqa: BLE001 - shutdown continues to the next step
                shutdown_errors.append(
                    {"step": "stream_aclose", "type": type(exc).__name__, "message": str(exc)}
                )
        if runtime is not None:
            try:
                await runtime.stop()
            except Exception as exc:  # noqa: BLE001 - shutdown continues to the next step
                shutdown_errors.append(
                    {"step": "runtime_stop", "type": type(exc).__name__, "message": str(exc)}
                )
            ctx.setdefault("queue_final", runtime.queue.qsize())
            ctx.setdefault("inflight_final", len(runtime._inflight))
            ctx.setdefault("workers_final", len(runtime._workers))
            ctx.setdefault("worker_exceptions_final", len(runtime.worker_exceptions))
        if engine is not None:
            await engine.dispose()
        if observer is not None:
            await observer.dispose()
        try:
            cleanup = await n6._wait_for_owned_client_cleanup(
                database_name, N01_7_OWNED_APPLICATION
            )
            ctx["cleanup"] = cleanup
            checks.setdefault("pg_owned_clients_zero", cleanup.final_snapshot.client_sessions == 0)
            checks.setdefault(
                "pg_idle_in_transaction_zero", cleanup.final_snapshot.idle_in_transaction == 0
            )
            checks.setdefault("pg_no_foreign_client_sessions", not cleanup.foreign_rows)
        except Exception as exc:  # noqa: BLE001 - record the evidence gap instead of hiding it
            shutdown_errors.append(
                {
                    "step": "owned_client_cleanup_probe",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            checks.setdefault("pg_owned_clients_zero", False)
            checks.setdefault("pg_idle_in_transaction_zero", False)
        ctx.setdefault("rss_end", n6._rss_mb())
        checks.setdefault("no_harness_event_errors", feed["errors"] == [])
        checks.setdefault("shutdown_no_errors", not shutdown_errors)
        ctx["shutdown_errors"] = shutdown_errors

    return _build_report(
        database_name, ctx, checks, failure, provider, samples, window_count, window_seconds
    )


def _age(iso_value: str | None) -> float | None:
    if not iso_value:
        return None
    return round((_now() - datetime.fromisoformat(iso_value)).total_seconds(), 3)


# ---------------------------------------------------------------------------------------------
# Windows / analysis
# ---------------------------------------------------------------------------------------------
def _bucket(
    samples: list[dict[str, Any]], lo: float, hi: float, last: bool
) -> list[dict[str, Any]]:
    if last:
        return [item for item in samples if lo <= item["elapsed_seconds"] <= hi]
    return [item for item in samples if lo <= item["elapsed_seconds"] < hi]


def _series(bucket: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Summary of one sampled field. Numeric statistics only apply to numeric fields.

    Several sampled fields are categorical (`btc_data_quality`, `health_status`,
    `operator_state`, `system_state`); they are summarised by first/last only, and their
    min/max/median stay `None` rather than being coerced into a fake number.
    """
    values = [item[key] for item in bucket if item.get(key) is not None]
    if not values:
        return {"count": 0, "first": None, "last": None, "min": None, "max": None, "median": None}
    numeric = all(
        isinstance(value, int | float) and not isinstance(value, bool) for value in values
    )
    return {
        "count": len(values),
        "first": values[0],
        "last": values[-1],
        "min": min(values) if numeric else None,
        "max": max(values) if numeric else None,
        "median": _median([float(value) for value in values]) if numeric else None,
    }


def _counter_series(bucket: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [item[key] for item in bucket if item.get(key) is not None]
    if not values:
        return {"first": None, "last": None, "delta": None}
    return {"first": values[0], "last": values[-1], "delta": values[-1] - values[0]}


def _aggregate_windows(
    samples: list[dict[str, Any]],
    window_seconds: float,
    window_count: int,
    reconciliations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for index in range(window_count):
        lo = index * window_seconds
        hi = lo + window_seconds
        bucket = _bucket(samples, lo, hi, index == window_count - 1)
        reconciliation = next(
            (item for item in reconciliations if item["window_index"] == index + 1), None
        )
        windows.append(
            {
                "index": index + 1,
                "start_elapsed_seconds": lo,
                "end_elapsed_seconds": hi,
                "samples": len(bucket),
                "elapsed_first": bucket[0]["elapsed_seconds"] if bucket else None,
                "elapsed_last": bucket[-1]["elapsed_seconds"] if bucket else None,
                "btc_trades": _counter_series(bucket, "btc_trades"),
                "btc_bbos": _counter_series(bucket, "btc_bbos"),
                "eth_trades": _counter_series(bucket, "eth_trades"),
                "eth_bbos": _counter_series(bucket, "eth_bbos"),
                "total_events": _counter_series(bucket, "total_events"),
                "btc_max_event_age_seconds": _series(bucket, "btc_last_bbo_age_seconds")["max"],
                "eth_max_event_age_seconds": _series(bucket, "eth_last_bbo_age_seconds")["max"],
                "btc_fresh_all": all(item.get("btc_fresh") is True for item in bucket)
                if bucket
                else None,
                "eth_fresh_all": all(item.get("eth_fresh") is True for item in bucket)
                if bucket
                else None,
                "btc_data_quality": _series(bucket, "btc_data_quality")["last"],
                "eth_data_quality": _series(bucket, "eth_data_quality")["last"],
                "health_status": _series(bucket, "health_status")["last"],
                "connection_attempts": _series(bucket, "connection_attempts")["last"],
                "reconnects": _series(bucket, "reconnects")["last"],
                "queue": _series(bucket, "queue_size"),
                "inflight": _series(bucket, "inflight"),
                "worker_count": _series(bucket, "worker_count")["last"],
                "workers_alive_min": _series(bucket, "workers_alive")["min"],
                "worker_exceptions": _series(bucket, "worker_exceptions")["last"],
                "dedupe_size": _series(bucket, "dedupe_size"),
                "dedupe_capacity": _series(bucket, "dedupe_capacity")["last"],
                "dedupe_oldest_first": bucket[0]["dedupe_oldest"] if bucket else None,
                "dedupe_oldest_last": bucket[-1]["dedupe_oldest"] if bucket else None,
                "trade_dedupe_size": _series(bucket, "trade_dedupe_size"),
                "trade_dedupe_capacity": _series(bucket, "trade_dedupe_capacity")["last"],
                "rss_mb": _series(bucket, "rss_mb"),
                "pg_owned_client_sessions": _series(bucket, "pg_owned_client_sessions"),
                "pg_other_client_sessions": _series(bucket, "pg_other_client_sessions"),
                "pg_idle_in_transaction": _series(bucket, "pg_idle_in_transaction"),
                "runtime_errors": _series(bucket, "runtime_errors")["last"],
                "position_quantity": _series(bucket, "position_quantity"),
                "protection_present_last": bucket[-1]["protection"]["present"] if bucket else None,
                "plan_expired_first": bucket[0].get("plan_expired") if bucket else None,
                "plan_expired_last": bucket[-1].get("plan_expired") if bucket else None,
                "operator_state": _series(bucket, "operator_state")["last"],
                "system_state": _series(bucket, "system_state")["last"],
                "open_incidents": _series(bucket, "open_incidents")["last"],
                "open_position_unprotected_incidents": _series(
                    bucket, "open_position_unprotected_incidents"
                )["last"],
                "reconciliation": reconciliation,
            }
        )
    return windows


def _fifo_head_changes(saturated: list[dict[str, Any]], key: str) -> int:
    """How many times `key` (a FIFO head) changed across consecutive saturated samples."""
    changes = 0
    previous = None
    for item in saturated:
        current = item.get(key)
        if previous is not None and current != previous:
            changes += 1
        previous = current
    return changes


def _trade_events(item: dict[str, Any]) -> int:
    """Accepted trade-stream arrivals observed so far, across both symbols."""
    return int(item.get("btc_trades") or 0) + int(item.get("eth_trades") or 0)


def _dedupe_analysis(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Two dedupe structures, two different questions (N01-7-INV-01 section 5).

    `EventRuntime._dedupe` keys on *published* event ids. Under the accepted workload it does not
    reach its capacity, so requiring turnover from it is structurally unobservable -- it may only
    be checked for boundedness (`size <= capacity`).

    `ScannerPipeline._trade_dedupe` is the structure the accepted section 20 trade-stream
    semantics actually describe: it keys on `(exchange, instrument_id, market_type, trade_id)`
    and *must* saturate under a long trade stream. Once saturated, `_remember_trade` evicts the
    FIFO head before admitting a new key, so a moving FIFO head is the turnover witness.

    The turnover witness therefore requires all three of:
      * `_trade_dedupe` reached its capacity,
      * its FIFO head changed while saturated,
      * trade events were still observed arriving after the first saturation sample.

    The last item is a corroborating count, not a substitute: a FIFO head can only move through
    `_remember_trade`, which is reached only for a key that is not already remembered.
    """
    runtime_capacity = next(
        (item["dedupe_capacity"] for item in samples if item.get("dedupe_capacity")), None
    )
    trade_capacity = next(
        (item["trade_dedupe_capacity"] for item in samples if item.get("trade_dedupe_capacity")),
        None,
    )
    runtime_sizes = [item["dedupe_size"] for item in samples if item.get("dedupe_size") is not None]
    trade_sizes = [
        item["trade_dedupe_size"] for item in samples if item.get("trade_dedupe_size") is not None
    ]

    runtime_saturated = [
        item for item in samples if runtime_capacity and item.get("dedupe_size") == runtime_capacity
    ]
    trade_saturated = [
        item
        for item in samples
        if trade_capacity and item.get("trade_dedupe_size") == trade_capacity
    ]
    runtime_head_changes = _fifo_head_changes(runtime_saturated, "dedupe_oldest")
    trade_head_changes = _fifo_head_changes(trade_saturated, "trade_dedupe_oldest")

    first_trade_saturated = trade_saturated[0] if trade_saturated else None
    trades_after_first_saturation = None
    if first_trade_saturated is not None and samples:
        trades_after_first_saturation = _trade_events(samples[-1]) - _trade_events(
            first_trade_saturated
        )

    runtime_within_capacity = all(
        (item.get("dedupe_size") or 0) <= (item.get("dedupe_capacity") or 0) for item in samples
    )
    trade_within_capacity = all(
        (item.get("trade_dedupe_size") or 0) <= (item.get("trade_dedupe_capacity") or 0)
        for item in samples
    )

    trade_reached_capacity = bool(trade_saturated)
    trade_head_moved = trade_head_changes > 0
    trades_kept_arriving = bool(
        trades_after_first_saturation is not None and trades_after_first_saturation > 0
    )

    return {
        "turnover_basis": "scanner_pipeline_trade_dedupe",
        "runtime_dedupe_saturation_required": False,
        "runtime_dedupe": {
            "capacity": runtime_capacity,
            "size_first": runtime_sizes[0] if runtime_sizes else None,
            "size_last": runtime_sizes[-1] if runtime_sizes else None,
            "size_max": max(runtime_sizes) if runtime_sizes else None,
            "size_min": min(runtime_sizes) if runtime_sizes else None,
            "reached_capacity": bool(runtime_saturated),
            "saturated_sample_count": len(runtime_saturated),
            "oldest_key_at_first_saturation": runtime_saturated[0].get("dedupe_oldest")
            if runtime_saturated
            else None,
            "oldest_key_changes_while_saturated": runtime_head_changes,
            "size_within_capacity_all_samples": runtime_within_capacity,
        },
        "trade_dedupe": {
            "capacity": trade_capacity,
            "size_first": trade_sizes[0] if trade_sizes else None,
            "size_last": trade_sizes[-1] if trade_sizes else None,
            "size_max": max(trade_sizes) if trade_sizes else None,
            "size_min": min(trade_sizes) if trade_sizes else None,
            "reached_capacity": trade_reached_capacity,
            "saturated_sample_count": len(trade_saturated),
            "saturation_elapsed_seconds": first_trade_saturated.get("elapsed_seconds")
            if first_trade_saturated
            else None,
            "saturation_at": first_trade_saturated.get("at") if first_trade_saturated else None,
            "oldest_key_at_first_saturation": first_trade_saturated.get("trade_dedupe_oldest")
            if first_trade_saturated
            else None,
            "oldest_key_last": trade_saturated[-1].get("trade_dedupe_oldest")
            if trade_saturated
            else None,
            "oldest_key_changes_while_saturated": trade_head_changes,
            "trade_events_at_first_saturation": _trade_events(first_trade_saturated)
            if first_trade_saturated
            else None,
            "trade_events_after_first_saturation": trades_after_first_saturation,
            "size_within_capacity_all_samples": trade_within_capacity,
        },
        "trade_dedupe_reached_capacity": trade_reached_capacity,
        "trade_dedupe_fifo_head_changed_while_saturated": trade_head_moved,
        "trade_dedupe_kept_accepting_after_saturation": trades_kept_arriving,
        "turnover_observed": bool(
            trade_reached_capacity and trade_head_moved and trades_kept_arriving
        ),
    }


# ---------------------------------------------------------------------------------------------
# Deterministic self-check for the corrected turnover analyser (N01-7-INV-01 section 5)
# ---------------------------------------------------------------------------------------------
_SELF_CHECK_CAPACITY = 4


def _synthetic_sample(
    *,
    index: int,
    runtime_size: int,
    runtime_head: str,
    trade_size: int,
    trade_head: str,
    trade_events: int,
    capacity: int,
) -> dict[str, Any]:
    """One synthetic sample carrying only the fields `_dedupe_analysis` reads."""
    return {
        "at": f"synthetic-{index}",
        "elapsed_seconds": float(index * 10),
        "dedupe_size": runtime_size,
        "dedupe_capacity": capacity,
        "dedupe_oldest": runtime_head,
        "trade_dedupe_size": trade_size,
        "trade_dedupe_capacity": capacity,
        "trade_dedupe_oldest": trade_head,
        "btc_trades": trade_events,
        "eth_trades": 0,
        "total_events": trade_events,
    }


def _self_check() -> dict[str, Any]:
    """Prove the corrected turnover analyser still has teeth, without any runtime or network.

    Synthetic sample data only. Four sequences are required to be classified exactly as stated;
    the check fails closed if any one of them is mis-classified. Two of them are deliberately
    chosen so that the *old* (defective) model -- keyed on `EventRuntime._dedupe` -- would have
    answered them the other way round, which is what makes this a regression guard for F-2.
    """
    capacity = _SELF_CHECK_CAPACITY

    def sequence(
        *,
        trade_sizes: list[int],
        trade_heads: list[str],
        runtime_sizes: list[int],
        runtime_heads: list[str],
        trade_events: list[int],
    ) -> list[dict[str, Any]]:
        return [
            _synthetic_sample(
                index=index,
                runtime_size=runtime_sizes[index],
                runtime_head=runtime_heads[index],
                trade_size=trade_sizes[index],
                trade_head=trade_heads[index],
                trade_events=trade_events[index],
                capacity=capacity,
            )
            for index in range(len(trade_sizes))
        ]

    sequences = {
        # Saturated AND the FIFO head keeps moving AND trades keep arriving -> the section 20
        # witness. The runtime dedupe is saturated and rotating too here, so a passing verdict
        # must NOT be attributable to the runtime structure.
        "saturated_and_rotating": sequence(
            trade_sizes=[2, 3, capacity, capacity, capacity, capacity],
            trade_heads=["t0", "t1", "t2", "t3", "t4", "t5"],
            runtime_sizes=[1, 2, 3, 4, 4, 4],
            runtime_heads=["r0", "r1", "r2", "r3", "r4", "r5"],
            trade_events=[0, 10, 20, 30, 40, 50],
        ),
        # Saturated but the trade FIFO head never moves -> NOT turnover, even though the runtime
        # dedupe IS saturated and rotating. The defective model returned True for this shape.
        "saturated_not_rotating": sequence(
            trade_sizes=[2, 3, capacity, capacity, capacity, capacity],
            trade_heads=["t0", "t1", "t2", "t2", "t2", "t2"],
            runtime_sizes=[1, 2, 3, 4, 4, 4],
            runtime_heads=["r0", "r1", "r2", "r3", "r4", "r5"],
            trade_events=[0, 10, 20, 30, 40, 50],
        ),
        # Trade dedupe never saturates -> structurally unobservable, must not be reported as
        # turnover even when the runtime dedupe is saturated and rotating. The defective model
        # returned True for this shape as well.
        "never_saturated": sequence(
            trade_sizes=[1, 2, 3, 3, 3, 3],
            trade_heads=["t0", "t1", "t2", "t3", "t4", "t5"],
            runtime_sizes=[1, 2, 3, 4, 4, 4],
            runtime_heads=["r0", "r1", "r2", "r3", "r4", "r5"],
            trade_events=[0, 10, 20, 30, 40, 50],
        ),
        # Saturated, head moved, but no further trade event ever arrived afterwards -> the third
        # arm of the witness is required, so this must NOT be accepted.
        "saturated_no_further_trades": sequence(
            trade_sizes=[2, 3, capacity, capacity],
            trade_heads=["t0", "t1", "t2", "t3"],
            runtime_sizes=[1, 2, 3, 4],
            runtime_heads=["r0", "r1", "r2", "r3"],
            trade_events=[0, 10, 20, 20],
        ),
    }
    expected = {
        "saturated_and_rotating": True,
        "saturated_not_rotating": False,
        "never_saturated": False,
        "saturated_no_further_trades": False,
    }

    observed: dict[str, bool] = {}
    detail: dict[str, Any] = {}
    for name, samples in sequences.items():
        analysis = _dedupe_analysis(samples)
        observed[name] = bool(analysis["turnover_observed"])
        detail[name] = {
            "turnover_observed": analysis["turnover_observed"],
            "turnover_basis": analysis["turnover_basis"],
            "trade_dedupe_reached_capacity": analysis["trade_dedupe_reached_capacity"],
            "trade_dedupe_fifo_head_changed_while_saturated": analysis[
                "trade_dedupe_fifo_head_changed_while_saturated"
            ],
            "trade_dedupe_kept_accepting_after_saturation": analysis[
                "trade_dedupe_kept_accepting_after_saturation"
            ],
            "runtime_dedupe_reached_capacity": analysis["runtime_dedupe"]["reached_capacity"],
            "runtime_dedupe_oldest_key_changes_while_saturated": analysis["runtime_dedupe"][
                "oldest_key_changes_while_saturated"
            ],
            "trade_dedupe_oldest_key_changes_while_saturated": analysis["trade_dedupe"][
                "oldest_key_changes_while_saturated"
            ],
        }

    return {
        "passed": observed == expected,
        "expected": expected,
        "observed": observed,
        "runtime_dedupe_saturation_required": False,
        "capacity_used": capacity,
        "detail": detail,
    }


def _memory_analysis(samples: list[dict[str, Any]], window_seconds: float) -> dict[str, Any]:
    values = [item["rss_mb"] for item in samples if item.get("rss_mb") is not None]
    if not values:
        return {"samples": 0}
    points = [
        (item["elapsed_seconds"], item["rss_mb"])
        for item in samples
        if item.get("rss_mb") is not None
    ]
    window_means: list[float] = []
    for index in range(int(points[-1][0] // window_seconds) + 1):
        bucket = [
            value
            for elapsed, value in points
            if index * window_seconds <= elapsed < (index + 1) * window_seconds
        ]
        if bucket:
            window_means.append(round(statistics.fmean(bucket), 3))
    monotonic = all(later > earlier for earlier, later in pairwise(window_means))
    growth = window_means[-1] - window_means[0] if len(window_means) >= 2 else 0.0
    growth_fraction = growth / window_means[0] if window_means and window_means[0] else 0.0
    return {
        "samples": len(values),
        "rss_start_mb": values[0],
        "rss_peak_mb": max(values),
        "rss_final_mb": values[-1],
        "rss_min_mb": min(values),
        "rss_median_mb": _median(values),
        "rss_slope_mb_per_hour": _slope_per_hour(points),
        "window_mean_mb": window_means,
        "window_means_strictly_increasing": monotonic,
        "window_mean_growth_mb": round(growth, 3),
        "window_mean_growth_fraction": round(growth_fraction, 4),
        "unbounded_growth_detected": bool(
            monotonic and growth_fraction >= RSS_GROWTH_ALERT_FRACTION
        ),
    }


def _build_report(
    database_name: str,
    ctx: dict[str, Any],
    checks: dict[str, bool],
    failure: dict[str, Any] | None,
    provider: OKXLiveProvider,
    samples: list[dict[str, Any]],
    window_count: int,
    window_seconds: float,
) -> dict[str, Any]:
    feed = ctx["feed"]
    runtime = ctx.get("runtime")
    windows = _aggregate_windows(
        samples, window_seconds, window_count, ctx.get("window_reconciliations", [])
    )
    dedupe = _dedupe_analysis(samples)
    memory = _memory_analysis(samples, window_seconds)

    # --- N01-7-specific acceptance implications of the window table ---------------------------
    checks["windows_observed_with_samples"] = all(item["samples"] > 0 for item in windows)
    checks["market_data_continuity_all_windows"] = all(
        bool(item["btc_trades"]["delta"] or item["btc_bbos"]["delta"])
        and bool(item["eth_trades"]["delta"] or item["eth_bbos"]["delta"])
        for item in windows
    )
    max_stale = max(
        (period.get("duration_seconds") or 0.0 for period in feed["stale_periods"]), default=0.0
    )
    checks["no_long_market_stale_period"] = max_stale < STALE_PERIOD_ALERT_SECONDS
    checks["workers_alive_all_samples"] = all(
        item["workers_alive"] == item["worker_count"] for item in samples if item["worker_count"]
    )
    checks["worker_exceptions_zero_all_samples"] = all(
        (item.get("worker_exceptions") or 0) == 0 for item in samples
    )
    checks["queue_within_capacity_all_samples"] = all(
        (item.get("queue_size") or 0) <= (item.get("queue_capacity") or 0) for item in samples
    )
    checks["runtime_dedupe_within_capacity_all_samples"] = dedupe["runtime_dedupe"][
        "size_within_capacity_all_samples"
    ]
    checks["trade_dedupe_within_capacity_all_samples"] = dedupe["trade_dedupe"][
        "size_within_capacity_all_samples"
    ]
    # Kept as the aggregate of both structures so an existing reader of this key still sees the
    # full boundedness claim; the two named checks above are the precise ones.
    checks["dedupe_within_capacity_all_samples"] = (
        checks["runtime_dedupe_within_capacity_all_samples"]
        and checks["trade_dedupe_within_capacity_all_samples"]
    )
    checks["dedupe_long_run_turnover"] = bool(dedupe["turnover_observed"])
    checks["rss_no_unbounded_growth"] = not memory["unbounded_growth_detected"]
    checks["pg_no_idle_in_transaction_accumulation"] = all(
        (item.get("pg_idle_in_transaction") or 0) <= 8 for item in samples
    )
    checks["reconciliation_ok_all_windows"] = all(
        item["reconciliation"] is None or item["reconciliation"]["ok"] is True for item in windows
    )

    f01 = ctx.get("f01")
    # A market-path early exit is the only admissible reason for an incomplete F01 witness: it is
    # characterised by the position no longer being OPEN at the observation point (SL/TP closed it
    # before the plan TTL was crossed). When the position IS still open, every F01 claim must hold
    # -- a missing snapshot or a protection service that ignores the snapshot is a product finding,
    # never "market path".
    f01_market_path_early_exit = checks.get("f01_position_still_open_after_expiry") is not True
    if f01 is None:
        if ctx.get("expiry_crossed_at") is None:
            f01_classification = "PLAN_TTL_NOT_REACHED"
        else:
            f01_classification = "WITNESS_NOT_OBSERVED"
    elif f01.get("harness_error"):
        f01_classification = "WITNESS_HARNESS_ERROR"
    elif f01_market_path_early_exit:
        f01_classification = "VALIDATION INCOMPLETE DUE TO MARKET PATH"
    elif all(checks.get(key) is True for key in MARKET_PATH_F01_KEYS):
        f01_classification = "LONG_LIVED_PROTECTION_WITNESSED"
    else:
        f01_classification = "F01_CLAIMS_NOT_SATISFIED"

    cleanup = ctx.get("cleanup")
    background = ctx.get("background_tasks")
    report_obj = ctx.get("reconciliation")
    account_final = ctx.get("account_final")

    return {
        "result": None,  # decided by main()
        "database_name": database_name,
        "run_mode": RUN_MODE.value,
        "requested_active_seconds": ctx.get("active_seconds_requested"),
        "active_started_at": ctx.get("active_started_at").isoformat()
        if ctx.get("active_started_at")
        else None,
        "active_finished_at": ctx.get("active_finished_at").isoformat()
        if ctx.get("active_finished_at")
        else None,
        "active_duration_seconds": round(ctx.get("active_duration_seconds", 0.0), 3),
        "database": {
            "disposable_database": database_name,
            "dsn": ctx.get("dsn"),
            "alembic_version": ctx.get("disposable_alembic_version"),
            "expected_migration_head": EXPECTED_MIGRATION_HEAD,
            "owned_application_name": N01_7_OWNED_APPLICATION,
            "observer_application_name": N01_7_OBSERVER_APPLICATION,
        },
        "okx": {
            "endpoints": list(n6.PUBLIC_OKX_ENDPOINTS),
            "ws_url": n6.PUBLIC_WS_URL,
            "channels": n6.CHANNELS,
            "metadata": ctx.get("metadata"),
            "connection_attempts": provider.connection_attempts,
            "reconnects": provider.reconnects,
            "api_key_used": False,
            "private_endpoint_used": False,
            "rest_transport": ctx.get("okx_rest_transport"),
        },
        "market_data": {
            "total_normalized_events": feed["total_normalized_events"],
            "per_symbol": {
                item: {
                    "trades": feed["trades"][item],
                    "bbos": feed["bbos"][item],
                    "first_received_at": feed["first_received"].get(item),
                    "last_received_at": feed["last_received"].get(item),
                    "max_inter_arrival_gap_seconds": round(
                        feed["max_inter_arrival_gap_seconds"].get(item, 0.0), 6
                    ),
                }
                for item in INSTRUMENTS
            },
            "stale_periods": feed["stale_periods"],
            "max_stale_period_seconds": round(max_stale, 3),
            "health_transitions": feed["health_transitions"],
            "production_ttl_seconds": n6.ACCEPTED_FRESHNESS_TTL_SECONDS,
        },
        "runtime": {
            "worker_count": 4,
            "queue_capacity": runtime.queue.maxsize if runtime else None,
            "dedupe_capacity": runtime._dedupe_capacity if runtime else None,
            "worker_exception_capacity": runtime._worker_exception_capacity if runtime else None,
            "queue_high_water": max((item.get("queue_size") or 0) for item in samples)
            if samples
            else None,
            "inflight_high_water": max((item.get("inflight") or 0) for item in samples)
            if samples
            else None,
            "worker_exception_max": max((item.get("worker_exceptions") or 0) for item in samples)
            if samples
            else None,
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_tasks_final": ctx.get("worker_tasks_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
        },
        "dedupe": dedupe,
        "memory": memory,
        "postgres": {
            "baseline": ctx.get("baseline"),
            "max_owned_client_sessions": max(
                (item.get("pg_owned_client_sessions") or 0) for item in samples
            )
            if samples
            else None,
            "max_other_client_sessions": max(
                (item.get("pg_other_client_sessions") or 0) for item in samples
            )
            if samples
            else None,
            "max_idle_in_transaction": max(
                (item.get("pg_idle_in_transaction") or 0) for item in samples
            )
            if samples
            else None,
            "cleanup": None
            if cleanup is None
            else {
                "owned_application": N01_7_OWNED_APPLICATION,
                "released": cleanup.released,
                "released_seconds": round(cleanup.elapsed_seconds, 6),
                "polls": cleanup.polls,
                "client_sessions_final": cleanup.final_snapshot.client_sessions,
                "idle_in_transaction_final": cleanup.final_snapshot.idle_in_transaction,
                "foreign_rows": list(cleanup.foreign_rows),
            },
        },
        "paper_lifecycle": {
            "entry": ctx.get("entry"),
            "exit": ctx.get("exit"),
            "position_present_samples": sum(
                1
                for item in samples
                if item.get("position_quantity") is not None and item["position_quantity"] > 0
            ),
            "sample_count": len(samples),
            "sample_interval_seconds": DEFAULT_SAMPLE_INTERVAL_SECONDS,
        },
        "f01_witness": {
            "classification": f01_classification,
            "market_path_early_exit": f01_market_path_early_exit,
            "plan_expires_at": (ctx["entry"]["plan"]["expires_at"] if ctx.get("entry") else None),
            "expiry_crossed_at": ctx.get("expiry_crossed_at"),
            "expiry_crossed_elapsed_seconds": ctx.get("expiry_crossed_elapsed_seconds"),
            "observed_at_elapsed_seconds": ctx.get("f01_elapsed_seconds"),
            "evidence": f01,
            "post_expiry_position_samples": sum(
                1
                for item in samples
                if item.get("plan_expired") and (item.get("position_quantity") or 0) > 0
            ),
            "post_expiry_samples_with_protection": sum(
                1 for item in samples if item.get("plan_expired") and item["protection"]["present"]
            ),
        },
        "economic_invariants": {
            "counts_final": ctx.get("counts_final"),
            "account_final": account_final,
            "position_final": ctx.get("position_final"),
            "open_buys_final": ctx.get("open_buys_final"),
            "sell_fill_ids": ctx.get("sell_fills"),
            "trade_final": ctx.get("trade_final"),
            "fills_final": ctx.get("fills_final"),
        },
        "reconciliation": None
        if report_obj is None
        else {
            "ok": report_obj.ok,
            "diagnostics": list(report_obj.diagnostics),
            "invariants": dict(report_obj.invariants),
            "details": {key: value for key, value in report_obj.details.items() if key != "g3"},
        },
        "shutdown": {
            "background_tasks": background,
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_tasks_final": ctx.get("worker_tasks_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
            "errors": ctx.get("shutdown_errors", []),
        },
        "windows": windows,
        "harness_errors": feed["errors"][:200],
        "checks": checks,
        "failure": failure,
        "samples": samples,
    }


# ---------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="N01-7 2-hour medium runtime soak")
    parser.add_argument("--seconds", type=float, default=DEFAULT_ACTIVE_SECONDS)
    parser.add_argument("--sample-interval", type=float, default=DEFAULT_SAMPLE_INTERVAL_SECONDS)
    parser.add_argument("--window-seconds", type=float, default=DEFAULT_WINDOW_SECONDS)
    parser.add_argument("--window-count", type=int, default=DEFAULT_WINDOW_COUNT)
    parser.add_argument("--raw-out", type=str, default=None)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help=(
            "run only the deterministic dedupe-turnover analyser self-check and exit; "
            "no network, no database and no runtime are touched"
        ),
    )
    args = parser.parse_args()

    if args.self_check:
        result = _self_check()
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    strict = args.seconds >= ACCEPTANCE_MIN_ACTIVE_SECONDS
    if not strict and args.seconds > PROBE_MAX_ACTIVE_SECONDS:
        raise SystemExit("PROBE runs must be <= 300 s; only >= 7200 s counts as ACCEPTANCE")

    started = _now()
    settings = Settings()
    runtime_dsn = _dsn_identity(settings.database_url)
    # Section 9 before-record: two labelled READ-ONLY observations of the shared primary, taken
    # outside the active window. The soak itself never opens a shared-primary connection.
    shared_primary_before = asyncio.run(_shared_primary_snapshot(SHARED_PRIMARY_URL))
    with n6._disposable_postgres_database() as (database_name, database_url):
        disposable_version = asyncio.run(_alembic_version(database_url))
        report = asyncio.run(
            _scenario(
                database_name,
                database_url,
                args.seconds,
                args.sample_interval,
                args.window_seconds,
                args.window_count,
            )
        )
    leftover = asyncio.run(n6._n01_6_leftover_databases())
    shared_primary_after = asyncio.run(_shared_primary_snapshot(SHARED_PRIMARY_URL))

    checks: dict[str, bool] = dict(report.get("checks", {}))
    checks["disposable_migration_head_is_accepted"] = disposable_version == EXPECTED_MIGRATION_HEAD
    checks["disposable_database_residue_zero"] = leftover == 0
    checks["shared_primary_not_migrated"] = shared_primary_before.get(
        "revision"
    ) == shared_primary_after.get("revision")
    checks["shared_primary_protection_columns_unchanged"] = shared_primary_before.get(
        "protection_columns"
    ) == shared_primary_after.get("protection_columns")
    checks["shared_primary_no_n01_7_runtime_session"] = (
        shared_primary_before.get("n01_7_owned_sessions_visible") == 0
        and shared_primary_after.get("n01_7_owned_sessions_visible") == 0
    )
    report["checks"] = checks
    report["shared_primary_isolation"] = {
        "dsn": _dsn_identity(SHARED_PRIMARY_URL),
        "observer_application_name": "marketpulse-shared-primary-observer",
        "observed_before": shared_primary_before,
        "observed_after": shared_primary_after,
        "runtime_connected_to_shared_primary": False,
    }
    report["database"]["alembic_version"] = disposable_version
    f01_classification = report["f01_witness"]["classification"]
    f01_market_path_early_exit = bool(report["f01_witness"].get("market_path_early_exit"))

    # F01 checks are excused ONLY when a market-path early exit made the observation impossible.
    # With the position still OPEN, a failed F01 check is a product finding and must appear in
    # `failures`.
    f01_excused = set(MARKET_PATH_F01_KEYS) if f01_market_path_early_exit else set()
    market_path_only = {
        key for key, value in checks.items() if value is not True and key in f01_excused
    }
    probe_excluded = set() if strict else set(ACCEPTANCE_SCOPE_KEYS)
    failures = sorted(
        key
        for key, value in checks.items()
        if value is not True and key not in f01_excused and key not in probe_excluded
    )
    report["failures"] = failures
    report["probe_excluded_acceptance_checks"] = sorted(probe_excluded)
    report["f01_only_failures"] = sorted(market_path_only)
    report["mode"] = "ACCEPTANCE" if strict else "PROBE"
    report["leftover_n01_7_databases"] = leftover
    report["runtime_dsn"] = runtime_dsn
    report["started_at"] = started.isoformat()
    report["finished_at"] = _now().isoformat()
    report["wall_clock_seconds"] = round((_now() - started).total_seconds(), 3)
    report["environment_notes"] = [
        "Sandbox-injected HTTP(S)_PROXY is cleared for this process by the reused harness.",
        (
            "The single OKX REST metadata lookup runs through the machine's existing user proxy "
            f"{OKX_REST_PROXY_ENV}; the public WebSocket is direct. No system proxy setting written."
        ),
        (
            "The runtime is pointed at a task-owned disposable PostgreSQL container via .env; the "
            "shared primary (127.0.0.1:5432/marketpulse) is never migrated or written by this run."
        ),
    ]

    if report.get("failure") is not None or failures:
        report["result"] = "FAIL"
    elif f01_classification == "VALIDATION INCOMPLETE DUE TO MARKET PATH":
        report["result"] = "INCOMPLETE_MARKET_PATH"
    else:
        report["result"] = "PASS" if strict else "PROBE_OK"

    if args.raw_out:
        raw_path = Path(args.raw_out)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    summary = {
        "result": report["result"],
        "mode": report["mode"],
        "active_duration_seconds": report["active_duration_seconds"],
        "f01_classification": f01_classification,
        "f01_market_path_early_exit": f01_market_path_early_exit,
        "failures": failures,
        "f01_only_failures": sorted(market_path_only),
        "total_normalized_events": report["market_data"]["total_normalized_events"],
        "reconnects": report["okx"]["reconnects"],
        "dedupe": report["dedupe"],
        "memory": report["memory"],
        "windows": [
            {
                "index": item["index"],
                "elapsed": [item["elapsed_first"], item["elapsed_last"]],
                "btc_trades": item["btc_trades"]["delta"],
                "btc_bbos": item["btc_bbos"]["delta"],
                "eth_trades": item["eth_trades"]["delta"],
                "eth_bbos": item["eth_bbos"]["delta"],
                "queue_max": item["queue"]["max"],
                "inflight_max": item["inflight"]["max"],
                "dedupe_last": item["dedupe_size"]["last"],
                "rss_last": item["rss_mb"]["last"],
                "pg_owned_max": item["pg_owned_client_sessions"]["max"],
                "position_last": item["position_quantity"]["last"],
                "plan_expired_last": item["plan_expired_last"],
                "protection_present_last": item["protection_present_last"],
                "system_state": item["system_state"],
                "open_incidents": item["open_incidents"],
                "reconciliation_ok": None
                if item["reconciliation"] is None
                else item["reconciliation"]["ok"],
            }
            for item in report["windows"]
        ],
        "economic_invariants": report["economic_invariants"],
        "reconciliation": report["reconciliation"],
        "postgres": report["postgres"],
        "shutdown": report["shutdown"],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if report["result"] in {"PASS", "PROBE_OK"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
