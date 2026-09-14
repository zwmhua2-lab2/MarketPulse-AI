#!/usr/bin/env python
"""PRE-01B-I1 — real public-OKX runtime validation for the Integrated Runtime Host V1.

This is the *online* half of PRE-01B-I1. The deterministic half is
``backend/tests/test_runtime_host.py`` and never touches the internet; this script never
substitutes a fake for a real OKX fact and never fabricates a PASS.

What it does, against a task-owned **disposable** PostgreSQL database (the shared primary
database is never used or mutated):

1. creates the database and upgrades Alembic to the current accepted head, then proves
   ``current == head`` before the runtime starts;
2. starts exactly one production-composed ``RuntimeHost`` (owned engine, owned advisory-lock
   connection, owned ``OKXLiveProvider``) in ``LIVE_PAPER``/local-only/one-worker/no-reload;
3. proves the duplicate-Host fence by asking a *second*, independent Host for the same
   session advisory lock and requiring a fail-closed ``DuplicateRuntimeHostError``;
4. runs for a configurable window (default: 5 continuous minutes after ``READY``) while an
   observer connection attributes every PostgreSQL session by ``application_name`` and the
   Host's bounded P2 telemetry is sampled;
5. stops the Host normally and proves the accepted shutdown conditions.

Authorised inputs only: public OKX market data (no credentials, no private endpoint, no
trading API, no Real AI key). No economic Position is opened or intended.

Usage:
    py -3.14 scripts/verify_pre_01b_runtime_host.py --minutes 5 --output <path.json>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from marketpulse.clock import SystemClock
from marketpulse.config import Settings
from marketpulse.db.session import create_database_resources
from marketpulse.g3.models import RunMode
from marketpulse.g3.service import PaperExecutionService
from marketpulse.g4.models import OperatorState, SystemState
from marketpulse.g4.state import SystemStateService
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import (
    DuplicateRuntimeHostError,
    RuntimeHost,
    _AIDisabledSentinel,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_PREFIX = "marketpulse_pre_01b_i1_verify_"
OBSERVER_APPLICATION_NAME = "pre-01b-i1-observer"
PROVISION_APPLICATION_NAME = "pre-01b-i1-provision"
HOST_APPLICATION_PREFIX = "marketpulse-runtime-host-"
DEFAULT_PROXY: str | None = None
# Economic / decision facts that Host Core V1 must never create: no G2->G3 handoff, no Real
# AI, no Live Trading, so every one of these tables stays empty on a disposable database.
ECONOMIC_TABLES = (
    "paper_orders",
    "fills",
    "positions",
    "trades",
    "ledger_entries",
    "trade_plans",
    "execution_intents",
    "ai_decisions",
    "decision_snapshots",
)


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------


def _redact(url: str) -> str:
    """Never emit a credential, even into local evidence."""
    return re.sub(r"//([^:/@]+):([^@]+)@", r"//\1:***@", url)


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(ROOT), capture_output=True, text=True, timeout=20, check=False
        )
        return out.stdout.strip()
    except Exception as exc:  # noqa: BLE001 - an evidence helper degrades to UNAVAILABLE
        return f"UNAVAILABLE:{type(exc).__name__}"


def _alembic_config(database_url: str) -> Config:
    backend = ROOT / "backend"
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _execute(
    connect_url: str,
    statement: str,
    *,
    application_name: str | None = None,
    **params: Any,
) -> list[tuple[Any, ...]]:
    connect_args: dict[str, Any] = {}
    if application_name:
        connect_args["server_settings"] = {"application_name": application_name}
    engine = create_async_engine(connect_url, poolclass=NullPool, connect_args=connect_args)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            result = await connection.execute(text(statement), params)
            return list(result.all()) if result.returns_rows else []
    finally:
        await engine.dispose()


@contextmanager
def disposable_database(primary_url: str) -> Iterator[tuple[str, str]]:
    """Create a task-owned database, migrate it to head, and always drop it again."""
    name = f"{DATABASE_PREFIX}{uuid4().hex[:12]}"
    server_url = primary_url.rsplit("/", 1)[0]
    url = f"{server_url}/{name}"
    asyncio.run(_execute(primary_url, f'CREATE DATABASE "{name}"'))
    try:
        yield name, url
    finally:
        try:
            asyncio.run(
                _execute(
                    primary_url,
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()",
                    name=name,
                )
            )
            asyncio.run(_execute(primary_url, f'DROP DATABASE IF EXISTS "{name}"'))
        except Exception:  # noqa: BLE001, S110 - dropping a disposable DB is best effort
            pass


def upgrade_to_head(url: str) -> dict[str, Any]:
    config = _alembic_config(url)
    command.upgrade(config, "head")
    head = ScriptDirectory.from_config(config).get_current_head()
    rows = asyncio.run(_execute(url, "SELECT version_num FROM alembic_version"))
    current = rows[0][0] if rows else None
    return {"head": head, "current": current, "current_equals_head": current == head}


def apply_proxy(proxy: str | None) -> dict[str, str]:
    """Process-local egress policy.

    Environment note (environment, not a product fact): this development sandbox injects
    ``HTTP_PROXY``/``HTTPS_PROXY`` pointing at a local proxy that fails OKX. The accepted
    precedent (``scripts/verify_n01_6_runtime_smoke.py``) is to clear those variables for
    this process only; no machine or system proxy setting is touched. ``--proxy`` is an
    explicit opt-in for an environment that needs a local egress proxy.
    """
    cleared = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    )
    for key in cleared:
        os.environ.pop(key, None)
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        return {"mode": "explicit_proxy", "HTTP_PROXY": proxy, "HTTPS_PROXY": proxy}
    return {"mode": "cleared_environment", "values": "none"}


def _socket_probe(proxy_port: int) -> dict[str, Any]:
    try:
        import psutil
    except Exception:  # noqa: BLE001 - a missing probe is UNAVAILABLE, never a crash
        return {"status": "UNAVAILABLE"}
    try:
        process = psutil.Process()
        connections = process.net_connections(kind="tcp")
    except Exception as exc:  # noqa: BLE001 - a failed probe is UNAVAILABLE, never zero
        return {"status": f"UNAVAILABLE:{type(exc).__name__}"}
    established = [c for c in connections if c.status == "ESTABLISHED"]
    tls = [c for c in established if c.raddr and c.raddr.port in (443, 8443)]
    to_proxy = [c for c in established if proxy_port and c.raddr and c.raddr.port == proxy_port]
    return {
        "status": "OK",
        "established_total": len(established),
        "established_tls_to_exchange": len(tls),
        "established_to_proxy_port": len(to_proxy),
        "proxy_port": proxy_port,
        "provider_socket_connections": len(tls) + len(to_proxy),
    }


def _proxy_port(proxy: str | None) -> int:
    if not proxy:
        return 0
    match = re.search(r":(\d+)\s*$", proxy)
    return int(match.group(1)) if match else 0


async def _session_attribution(url: str) -> dict[str, Any]:
    """Observer: attribute every PostgreSQL session, and prove none is idle-in-transaction."""
    rows = await _execute(
        url,
        "SELECT application_name, state, count(*) FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid <> pg_backend_pid() "
        "GROUP BY application_name, state ORDER BY application_name, state",
        application_name=OBSERVER_APPLICATION_NAME,
    )
    by_app: dict[str, dict[str, int]] = {}
    for application_name, state, count in rows:
        by_app.setdefault(application_name or "",{})[state or "UNKNOWN"] = count
    host_owned = {
        app: states
        for app, states in by_app.items()
        if app.startswith(HOST_APPLICATION_PREFIX)
    }
    singleton = {app: s for app, s in host_owned.items() if app.endswith("-singleton")}
    non_singleton = {app: s for app, s in host_owned.items() if not app.endswith("-singleton")}
    return {
        "by_application_name": by_app,
        "host_owned_sessions": sum(sum(s.values()) for s in host_owned.values()),
        "host_owned_singleton_sessions": sum(sum(s.values()) for s in singleton.values()),
        "host_owned_non_singleton_sessions": sum(
            sum(s.values()) for s in non_singleton.values()
        ),
        "host_owned_detail": host_owned,
        "idle_in_transaction_total": sum(
            states.get("idle in transaction", 0) for states in by_app.values()
        ),
        "idle_in_transaction_host_owned": sum(
            states.get("idle in transaction", 0) for states in host_owned.values()
        ),
        # The accepted contract gives the advisory-lock connection a lifetime equal to the
        # Host's, so its own session is expected to sit in an open transaction. What must
        # not happen is an *accumulating* non-singleton idle-in-transaction set.
        "idle_in_transaction_host_owned_non_singleton": sum(
            states.get("idle in transaction", 0) for states in non_singleton.values()
        ),
        "observer_sessions": sum(
            sum(s.values()) for app, s in by_app.items() if app == OBSERVER_APPLICATION_NAME
        ),
    }


async def _economic_counts(url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in ECONOMIC_TABLES:
        rows = await _execute(url, f"SELECT count(*) FROM {table}")
        counts[table] = int(rows[0][0]) if rows else -1
    return counts


async def provision_durable_state(url: str, run_mode: RunMode) -> dict[str, Any]:
    """Give the disposable database the durable state a legitimately started deployment has.

    A clean database has no `runtime_controls` row and no account, so the accepted
    readiness conjunction ("Recovery completed ... durable system_state=RUNNING with
    operator_state=NORMAL", "startup reconciliation ok=true") is unreachable by design.
    This mirrors the accepted initialization path used by the N01 harnesses
    (`SystemStateService.ensure` -> `transition` -> `PaperExecutionService.bootstrap_account`)
    and nothing else: no economic fact, no order, no fill, no AI decision.
    """
    settings = Settings(run_mode=run_mode.value, database_url=url)
    resources = create_database_resources(
        settings, application_name=PROVISION_APPLICATION_NAME
    )
    clock = SystemClock()

    async def no_quote(instrument_id: str) -> Any:
        raise RuntimeError(f"provisioning_has_no_quote:{instrument_id}")

    async def version_zero(instrument_id: str) -> int:
        return 0

    try:
        states = SystemStateService(resources.session_factory, clock=clock)
        execution = PaperExecutionService(
            resources.session_factory, no_quote, version_zero, clock=clock
        )
        await states.ensure(run_mode)
        await states.transition(
            run_mode,
            operator_state=OperatorState.NORMAL,
            system_state=SystemState.RUNNING,
            reason="pre_01b_i1_verify_provision",
        )
        await execution.bootstrap_account(run_mode)
        control = await states.load(run_mode)
        return {
            "system_state": control.system_state,
            "operator_state": control.operator_state,
            "engine_disposed": resources.disposed,
        }
    finally:
        await resources.dispose()


# ---------------------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------------------


async def wait_for(predicate, timeout: float = 60.0, interval: float = 0.1) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return bool(predicate())


def _counter_block(telemetry: dict[str, Any]) -> dict[str, Any]:
    return {
        "counters": telemetry["counters"],
        "lanes": telemetry["lanes"],
        "provider": telemetry["provider"],
        "database": telemetry["database"],
        "eventruntime": telemetry["eventruntime"],
        "market_state": telemetry["market_state"],
        "reconciliation": telemetry["reconciliation"],
        "readiness": telemetry["readiness"],
        "tasks": telemetry["tasks"],
        "process": telemetry["process"],
    }


async def run(args: argparse.Namespace, url: str, evidence: dict[str, Any]) -> None:
    settings = Settings(
        run_mode="LIVE_PAPER",
        local_only=True,
        host="127.0.0.1",
        database_url=url,
        runtime_host_enabled=True,
        runtime_host_instruments="BTC-USDT,ETH-USDT",
        runtime_workers=1,
        runtime_reload=False,
        # Accepted contract defaults; only the observation window is task-configurable.
        runtime_startup_timeout_seconds=90.0,
        runtime_shutdown_grace_seconds=30.0,
        runtime_shutdown_dispose_seconds=5.0,
        runtime_heartbeat_interval_seconds=5.0,
        runtime_telemetry_interval_seconds=5.0,
        runtime_reconciliation_interval_seconds=30.0,
        runtime_market_freshness_seconds=5.0,
    )
    evidence["settings"] = {
        "run_mode": settings.run_mode,
        "local_only": settings.local_only,
        "host": settings.host,
        "database_url": _redact(settings.database_url),
        "runtime_host_enabled": settings.runtime_host_enabled,
        "runtime_host_instruments": settings.runtime_host_instruments,
        "runtime_workers": settings.runtime_workers,
        "runtime_reload": settings.runtime_reload,
        "runtime_safety_queue_capacity": settings.runtime_safety_queue_capacity,
        "runtime_scanner_queue_capacity": settings.runtime_scanner_queue_capacity,
        "runtime_heartbeat_interval_seconds": settings.runtime_heartbeat_interval_seconds,
        "runtime_reconciliation_interval_seconds": (
            settings.runtime_reconciliation_interval_seconds
        ),
        "runtime_market_freshness_seconds": settings.runtime_market_freshness_seconds,
        "runtime_advisory_lock_namespace": settings.runtime_advisory_lock_namespace,
    }

    evidence["provisioning"] = await provision_durable_state(url, RunMode(settings.run_mode))
    before = await _economic_counts(url)
    evidence["economic_counts_before"] = before

    host = RuntimeHost(settings)
    evidence["composition"] = {
        "provider_constructed_by_host": host.provider_constructed_by_host,
        "owns_database": host.ownership_snapshot()["owns_database"],
        "dependencies_injected": host.dependencies is not None,
    }

    # --- startup ---------------------------------------------------------------------
    started = time.monotonic()
    await host.start()
    evidence["startup"] = {
        "seconds": round(time.monotonic() - started, 3),
        "state": host.state.value,
        "state_history": host.ownership_snapshot()["state_history"],
    }
    owned_db = host._db  # evidence handle: the Host's own DatabaseResources
    lock_db = host._lock_db

    ready = await wait_for(lambda: host.state is HostLifecycleState.READY, timeout=90.0)
    evidence["ready"] = {
        "reached": ready,
        "seconds_after_start": round(time.monotonic() - started, 3),
        "state": host.state.value,
        "readiness": host.readiness().as_payload(),
        "children_live": list(host.children_live),
    }
    if not ready:
        raise RuntimeError(f"host_never_became_ready:state={host.state.value}")

    # --- duplicate-Host fence --------------------------------------------------------
    second = RuntimeHost(Settings(**{**settings.model_dump(), "runtime_host_enabled": True}))
    fence: dict[str, Any] = {}
    try:
        await second.start()
        fence["duplicate_refused"] = False
    except DuplicateRuntimeHostError as exc:
        fence["duplicate_refused"] = True
        fence["error"] = type(exc).__name__
    except BaseException as exc:  # noqa: BLE001 - reported, not swallowed
        fence["duplicate_refused"] = False
        fence["error"] = f"{type(exc).__name__}:{exc}"
    fence["second_host_state"] = second.state.value
    fence["second_host_engine_disposed"] = second.ownership_snapshot()["engine_disposed"]
    fence["second_host_singleton_connection_present"] = second.ownership_snapshot()[
        "singleton_connection_present"
    ]
    if second.state not in (HostLifecycleState.STOPPED, HostLifecycleState.STOP_FAILED):
        await second.stop()
    evidence["duplicate_host_fence"] = fence

    # --- observation window ----------------------------------------------------------
    runtime_before_stop = host.event_runtime
    samples: list[dict[str, Any]] = []
    window_started = time.monotonic()
    window_deadline = window_started + args.minutes * 60.0
    while time.monotonic() < window_deadline:
        telemetry = host.telemetry()
        samples.append(
            {
                "t_seconds": round(time.monotonic() - window_started, 3),
                "state": telemetry["state"],
                "readiness_status": telemetry["readiness"]["status"],
                "ready": telemetry["readiness"]["ready"],
                **_counter_block(telemetry),
                "postgres": await _session_attribution(url),
                "sockets": _socket_probe(_proxy_port(args.proxy)),
            }
        )
        await asyncio.sleep(max(1.0, args.sample_seconds))

    evidence["window"] = {
        "configured_minutes": args.minutes,
        "elapsed_seconds": round(time.monotonic() - window_started, 3),
        "sample_count": len(samples),
        "sample_seconds": args.sample_seconds,
        "samples": samples,
    }
    final_window = samples[-1]
    safety_lanes = final_window["lanes"]["safety"]
    evidence["window_summary"] = {
        "states_seen": sorted({s["state"] for s in samples}),
        "readiness_statuses_seen": sorted({s["readiness_status"] for s in samples}),
        "ready_fraction": round(sum(1 for s in samples if s["ready"]) / max(1, len(samples)), 4),
        "market_frames_final": final_window["counters"]["market_frames"],
        "trade_frames_final": final_window["counters"]["trade_frames"],
        "ingress_forwarded_final": final_window["counters"]["ingress_forwarded_to_safety"],
        "safety_processed_final": final_window["counters"]["safety_processed"],
        "scanner_processed_final": final_window["counters"]["scanner_processed"],
        "safety_overflow_final": final_window["counters"]["safety_overflow"],
        "scanner_rejected_final": final_window["counters"]["scanner_rejected"],
        "safety_queue_high_water": {k: v["high_water"] for k, v in safety_lanes.items()},
        "safety_queue_capacity": {k: v["capacity"] for k, v in safety_lanes.items()},
        "scanner_queue_high_water": final_window["lanes"]["scanner"]["high_water"],
        "scanner_queue_capacity": final_window["lanes"]["scanner"]["capacity"],
        "eventruntime_queue_size_max": max(
            (s["eventruntime"] or {}).get("queue_size", 0) for s in samples
        ),
        "eventruntime_queue_capacity": (final_window["eventruntime"] or {}).get(
            "queue_capacity"
        ),
        "eventruntime_inflight_max": max(
            (s["eventruntime"] or {}).get("inflight", 0) for s in samples
        ),
        "provider_status_seen": sorted({s["provider"]["status"] for s in samples}),
        "provider_connection_attempts_final": final_window["provider"]["connection_attempts"],
        "provider_reconnects_final": final_window["provider"]["reconnects"],
        "reconciliation_results_seen": sorted(
            {str(s["reconciliation"]["last_result"]) for s in samples}
        ),
        "periodic_reconciliation_timestamps": sorted(
            {str(s["reconciliation"]["last_result"]) for s in samples}
        ),
        "max_host_owned_sessions": max(
            s["postgres"]["host_owned_sessions"] for s in samples
        ),
        "max_host_owned_singleton_sessions": max(
            s["postgres"]["host_owned_singleton_sessions"] for s in samples
        ),
        "max_host_owned_non_singleton_sessions": max(
            s["postgres"]["host_owned_non_singleton_sessions"] for s in samples
        ),
        "max_idle_in_transaction": max(
            s["postgres"]["idle_in_transaction_total"] for s in samples
        ),
        "max_host_owned_idle_in_transaction": max(
            s["postgres"]["idle_in_transaction_host_owned"] for s in samples
        ),
        "max_host_owned_non_singleton_idle_in_transaction": max(
            s["postgres"]["idle_in_transaction_host_owned_non_singleton"] for s in samples
        ),
        "max_sockets_to_proxy": max(
            s["sockets"].get("established_to_proxy_port", -1) for s in samples
        ),
        "rss_mb_first": samples[0]["process"].get("rss_mb"),
        "rss_mb_last": final_window["process"].get("rss_mb"),
    }

    # --- shutdown --------------------------------------------------------------------
    stopped = time.monotonic()
    await host.stop()
    evidence["shutdown"] = {
        "seconds": round(time.monotonic() - stopped, 3),
        "state": host.state.value,
        "ownership": host.ownership_snapshot(),
        "state_history": host.ownership_snapshot()["state_history"],
        "final_counters": host.telemetry()["counters"],
    }

    # Let the loop settle so "no Host-owned task remains" is a proof, not a race.
    for _ in range(25):
        await asyncio.sleep(0.02)
    current = asyncio.current_task()
    orphan_tasks = sorted(
        t.get_name() for t in asyncio.all_tasks() if t is not current and not t.done()
    )
    postgres = await _session_attribution(url)
    economic_after = await _economic_counts(url)
    sockets = _socket_probe(_proxy_port(args.proxy))
    eventruntime = runtime_before_stop
    readiness = host.readiness().as_payload()

    evidence["post_stop"] = {
        "orphan_tasks": orphan_tasks,
        "postgres": postgres,
        "sockets": sockets,
        "economic_counts_after": economic_after,
        "eventruntime_live_workers": (
            None if eventruntime is None else eventruntime.live_worker_count
        ),
        "eventruntime_inflight": None if eventruntime is None else eventruntime.inflight_size,
        "eventruntime_queue_size": None if eventruntime is None else eventruntime.queue_size,
        "eventruntime_telemetry": (
            None if eventruntime is None else eventruntime.telemetry_snapshot()
        ),
        "owned_engine_checkedout": None if owned_db is None else owned_db.engine.pool.checkedout(),
        "owned_engine_disposed": None if owned_db is None else owned_db.disposed,
        "lock_engine_checkedout": None if lock_db is None else lock_db.engine.pool.checkedout(),
        "lock_engine_disposed": None if lock_db is None else lock_db.disposed,
        "readiness_at_stop": readiness,
        "provider_status": host.telemetry()["provider"]["status"],
        "provider_telemetry": host.telemetry()["provider"],
        "ai_sentinel": isinstance(host._safety.reevaluation, _AIDisabledSentinel),
        "safety_reevaluation": host.telemetry()["safety_reevaluation"],
    }

    # --- accepted pass conditions (§22) ----------------------------------------------
    ownership = evidence["shutdown"]["ownership"]
    counters = host.telemetry()["counters"]
    ai_raises = False
    try:
        host._safety.reevaluation.reevaluate  # noqa: B018 - deliberately exploded on
        ai_raises = False
    except Exception:  # noqa: BLE001 - any use of the disabled sentinel must raise
        ai_raises = True
    conditions = {
        "host_owned_tasks_zero": orphan_tasks == [],
        "eventruntime_live_workers_zero": evidence["post_stop"]["eventruntime_live_workers"] == 0,
        "eventruntime_inflight_zero": evidence["post_stop"]["eventruntime_inflight"] == 0,
        "provider_socket_closed": (
            sockets.get("status") == "OK"
            and sockets.get("provider_socket_connections") == 0
            and evidence["post_stop"]["provider_status"] == "STOPPED"
        ),
        "db_checked_out_zero": evidence["post_stop"]["owned_engine_checkedout"] == 0,
        "singleton_connection_released": (
            ownership["singleton_connection_present"] is False
            and ownership["singleton_lock_held"] is False
        ),
        "host_owned_db_sessions_zero": postgres["host_owned_sessions"] == 0,
        "engine_disposed": evidence["post_stop"]["owned_engine_disposed"] is True,
        "lock_engine_disposed": evidence["post_stop"]["lock_engine_disposed"] is True,
        "no_idle_in_transaction_after_stop": postgres["idle_in_transaction_total"] == 0,
        "real_ai_never_constructed": (
            evidence["post_stop"]["ai_sentinel"]
            and ai_raises
            and host.telemetry()["safety_reevaluation"]["enabled"] is False
        ),
        "g2_to_g3_live_handoff_absent": host.telemetry()["safety_reevaluation"]["inflight"] == 0,
        "no_economic_fact_created": all(value == 0 for value in economic_after.values()),
        "shutdown_without_escalation": host.telemetry()["counters"]["shutdown_escalated"] is False,
        "shutdown_failures_empty": host.telemetry()["counters"]["shutdown_failures"] == [],
        "no_host_invariant_violation": counters["host_invariant_violations"] == 0,
        # `ingress_forwarded_to_safety` counts only BBO frames admitted to a safety lane;
        # the scanner lane receives every normalized event admitted after step 9. The live
        # invariant is therefore that the scanner was fed only by frames that took the
        # post-admission route: the recovery-only warm-up BBOs are structurally excluded
        # (nothing is forwarded before `_safety_admission_open`), and the exact proof is
        # `test_warmup_frames_are_never_replayed_into_the_scanner` in the focused suite.
        "scanner_fed_only_by_admitted_frames": (
            counters["scanner_processed"]
            <= counters["ingress_forwarded_to_safety"] + counters["trade_frames"]
        ),
    }
    evidence["pass_conditions"] = conditions
    evidence["result"] = "PASS" if all(conditions.values()) else "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=float, default=5.0)
    parser.add_argument("--sample-seconds", type=float, default=5.0)
    parser.add_argument(
        "--proxy",
        default=os.environ.get("PRE_01B_I1_PROXY") or DEFAULT_PROXY,
        help="explicit egress proxy for REST+WS; default clears the sandbox proxy variables",
    )
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    primary_url = Settings().database_url
    output = Path(
        args.output
        or os.environ.get("TEMP", ".") / f"pre_01b_i1_runtime_host_{uuid4().hex[:8]}.json"
    )

    evidence: dict[str, Any] = {
        "task": "PRE-01B-I1",
        "script": "scripts/verify_pre_01b_runtime_host.py",
        "started_at": datetime.now(UTC).isoformat(),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "status_porcelain": _git("status", "--porcelain").splitlines(),
        },
        "primary_database_url": _redact(primary_url),
        "proxy": apply_proxy(args.proxy),
        "observer_application_name": OBSERVER_APPLICATION_NAME,
    }

    try:
        with disposable_database(primary_url) as (name, url):
            evidence["disposable_database"] = {"name": name, "url": _redact(url)}
            evidence["alembic"] = upgrade_to_head(url)
            if not evidence["alembic"]["current_equals_head"]:
                evidence["result"] = "FAIL"
                evidence["error"] = "alembic_current_is_not_head"
            else:
                asyncio.run(run(args, url, evidence))
    except BaseException as exc:  # noqa: BLE001 - always emit evidence
        evidence.setdefault("result", "FAIL")
        evidence["error"] = f"{type(exc).__name__}:{exc}"
    evidence["finished_at"] = datetime.now(UTC).isoformat()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"result": evidence.get("result"), "output": str(output)}, indent=2))
    return 0 if evidence.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
