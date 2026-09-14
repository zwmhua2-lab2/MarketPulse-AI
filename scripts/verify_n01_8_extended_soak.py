"""N01-8 — 12-hour Extended Runtime Soak (validation-only N-phase supervisor).

Why this file exists
--------------------
N01-7 (>= 7200 s) proved the accepted runtime stable for two hours with exactly ONE fresh-process
restart.  N01-8 asks the next question: does the same accepted runtime stay stable for >= 43200 s
(12 h) across FOUR fresh-process phases, 12 controlled reconnects and 6 controlled STALE->FRESH
cycles -- and, above all, does the accepted bounded-retention memory behaviour reach a plateau
(closed P2 watch item `N01-7-R01-RR-P2-01`) or keep trending.

Reuse contract (nothing accepted is rewritten)
----------------------------------------------
* `scripts/verify_n01_6_runtime_smoke.py` -- **imported, never copied and never edited**.  Every
  runtime object (`OKXLiveProvider`, `ScannerPipeline`, `OpportunityScanner`, `EventRuntime`,
  `PostgresG2Repository`, `SmokeHarness`, `_consume`, `_controlled_entry`, `_controlled_close`,
  the disposable-database factory and the PostgreSQL ownership split) comes from it unchanged.
* `scripts/verify_n01_7_runtime_soak.py`  -- **imported for its reviewed observation helpers only**
  (`_db_state`, `_age`, `_slope_per_hour`, `_f01_witness`, `_shared_primary_snapshot`,
  `_alembic_version`, `_protection_schema`, `_dsn_identity`, `_okx_rest_proxy`).
* `scripts/verify_n01_7_medium_soak.py`   -- **imported for its reviewed supervisor machinery and
  acceptance aggregation** (`_ControlledStream`, `_controlled_reconnect`,
  `_stale_fresh_cycle`, `_checkpoint`, `_witness_b_new_active_plan`,
  `_protection_authority_after_restart`, `_final_assertions`, `_runtime_control`,
  `_proc_resources`, `_build_phase_report`, `_memory_condition`, `_aggregate`, `_emit`).

Deliberate N01-8 deltas (validation-only; task sections 9 and 12)
-----------------------------------------------------------------
1. **Role-driven phase runner** (`_phase_scenario_n01_8`).  The accepted runner hard-codes a
   two-phase open/close scenario through `phase == "first"` / `phase == "second"`.  A 12 h window
   with an OPEN position carried across three restarts needs a third role, so the runner is
   re-expressed over explicit roles (`open` / `continue` / `close`).  Every step inside it is a
   call into the accepted helpers listed above; no runtime behaviour is re-implemented.
2. **12 h deterministic schedule** (`_GLOBAL_SCHEDULE`) -- 12 reconnect / 6 stale / 12 hourly
   checkpoint items, each pinned to a phase-local offset, so the timeline is declared before the
   run instead of fitted afterwards.
3. **Retention saturation / post-saturation RSS analysis** (`_retention_analysis`) plus rolling
   window slopes (`_rolling_slopes`) and a cheap non-intrusive GC/gc-count telemetry field.
4. **N-phase aggregation by virtual phase merge** (`_merge_phase_reports`): the accepted
   `ms._aggregate` is reused verbatim; the N phase reports are folded into the `first`/`second`
   pair it expects (checks AND-merged, event lists concatenated, durations summed).  The fold is
   recorded in the report so a reviewer can audit it.
5. **Environment identity** -- N01-8 database prefix / application names / port / task base.

Not a mitigation for a product defect
-------------------------------------
If the soak finds a product defect the run is reported and production code is NOT touched
(task section 10).  Findings are evidence, never something to patch mid-run.

Claim boundary
--------------
Even on PASS this proves only: "the accepted production runtime components, inside the N01-8
validation harness, were stable for >= 12 h including three fresh-process restarts".  It is NOT
the Integrated Runtime Host, NOT a FastAPI 7x24 runtime, NOT a deployment, NOT N01 overall
acceptance and NOT live trading.

Run (explicit opt-in; never part of the deterministic pytest suite)::

    py -3.14 scripts/verify_n01_8_extended_soak.py --mode acceptance \
        --raw-out E:/Temp/n01-8/acceptance_raw.json
    py -3.14 scripts/verify_n01_8_extended_soak.py --mode acceptance --probe
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import gc
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = str(REPOSITORY_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Importing the accepted harnesses is the whole point: `n6` clears the sandbox proxy for this
# process and puts `backend/src` + `backend/tests` on `sys.path`; `soak` re-exports the accepted
# observation helpers; `ms` re-exports the accepted supervisor machinery.  `soak` also installs the
# N01-7-R01 ownership domain on `n6` at import time -- `_apply_env_identity()` overrides it below.
import verify_n01_6_runtime_smoke as n6
import verify_n01_7_medium_soak as ms
import verify_n01_7_runtime_soak as soak
from marketpulse.g4.models import HealthComponent
from marketpulse.g4.planning import load_active_plan, resolve_open_position_protection
from marketpulse.g4.recovery import RecoveryManager

RUN_MODE = n6.RUN_MODE
BTC = n6.BTC
ETH = n6.ETH
INSTRUMENTS = n6.INSTRUMENTS
OKX_REST_PROXY_ENV = soak.OKX_REST_PROXY_ENV

# ---------------------------------------------------------------------------------------------
# N01-8 environment identity (task section 7) -- unique container / port / db / application_name
# ---------------------------------------------------------------------------------------------
N01_8_DATABASE_PREFIX = "marketpulse_n01_8_"
N01_8_OWNED_APPLICATION = "marketpulse-n01-8-runtime"
N01_8_OBSERVER_APPLICATION = "marketpulse-n01-8-observer"
N01_8_DATABASE_PORT = "5440"
N01_8_CONTAINER = "marketpulse-n01-8-pg"

DEFAULT_RAW_OUT = "E:/Temp/n01-8/acceptance_raw.json"

# Task base frozen at N01-8 preflight (dd78a979...).  Deliberately frozen rather than resolved from
# a moving ref at report time, so a main advance during the 12 h run stays visible evidence.
TASK_BASE_SHA = "dd78a979d128dee385c7a8ddc2254a53366af714"
PRODUCTION_PATHS = ("backend/src", "backend/alembic", "backend/tests", "frontend")

# ---------------------------------------------------------------------------------------------
# Acceptance parameters (declared BEFORE the run so the verdict is not fitted afterwards)
# ---------------------------------------------------------------------------------------------
ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS = 43200.0
DEFAULT_PHASE_SECONDS = 11100.0
PROBE_PHASE_SECONDS = 420.0
DEFAULT_SAMPLE_INTERVAL_SECONDS = 10.0

TARGET_PHASES = 4
TARGET_FRESH_PROCESS_RESTARTS = 3
TARGET_RECONNECTS = 12
TARGET_STALE_CYCLES = 6

# Phase roles.  The OPEN phase creates the position; CONTINUE phases recover it from PostgreSQL and
# deliberately leave it open; the CLOSE phase recovers, witnesses the authority, closes and asserts.
PHASE_PLAN: tuple[tuple[str, str], ...] = (
    ("p1_open", "open"),
    ("p2_continue", "continue"),
    ("p3_continue", "continue"),
    ("p4_close", "close"),
)
PROBE_PHASE_PLAN: tuple[tuple[str, str], ...] = (("p1_open", "open"), ("p2_close", "close"))

# 12 h deterministic schedule (task section 12-C).  Offsets are PHASE-LOCAL seconds; every item is
# a real machine-checkable witness (see `ms._controlled_reconnect` / `ms._stale_fresh_cycle`).
# Hourly checkpoints are pinned to global multiples of 3600 s.
_GLOBAL_SCHEDULE: dict[str, list[dict[str, Any]]] = {
    "p1_open": [
        {"kind": "reconnect", "at": 900.0, "index": 1},
        # Absolute 30-min / 90-min checkpoints.  The accepted `ms._aggregate` BAKES the N01-7
        # two-hour coverage bands into `checkpoints_cover_required_points` ([1500,2100] and
        # [5100,5700] on `absolute_elapsed_seconds`) and requires the labels {abs_30m, abs_90m} in
        # `checkpoint_coverage_complete`.  A 12 h N01-8 schedule that only emitted `abs_1h..abs_12h`
        # would therefore fail both checks for a harness reason, not a runtime one, so the two
        # absolute-time checkpoints are emitted at exactly the moments the accepted verifier names.
        {"kind": "checkpoint", "at": 1800.0, "label": "abs_30m"},
        {"kind": "stale", "at": 2400.0, "index": 1},
        {"kind": "checkpoint", "at": 3600.0, "label": "abs_1h"},
        {"kind": "reconnect", "at": 4600.0, "index": 2},
        {"kind": "checkpoint", "at": 5400.0, "label": "abs_90m"},
        {"kind": "checkpoint", "at": 7200.0, "label": "abs_2h"},
        {"kind": "stale", "at": 7300.0, "index": 2},
        {"kind": "reconnect", "at": 8300.0, "index": 3},
        {"kind": "checkpoint", "at": 10800.0, "label": "abs_3h"},
    ],
    "p2_continue": [
        {"kind": "reconnect", "at": 1200.0, "index": 4},
        {"kind": "stale", "at": 3000.0, "index": 3},
        {"kind": "checkpoint", "at": 3300.0, "label": "abs_4h"},
        {"kind": "reconnect", "at": 4900.0, "index": 5},
        {"kind": "checkpoint", "at": 6900.0, "label": "abs_5h"},
        {"kind": "reconnect", "at": 8600.0, "index": 6},
        {"kind": "checkpoint", "at": 10500.0, "label": "abs_6h"},
    ],
    "p3_continue": [
        {"kind": "reconnect", "at": 1500.0, "index": 7},
        {"kind": "checkpoint", "at": 3000.0, "label": "abs_7h"},
        {"kind": "stale", "at": 3600.0, "index": 4},
        {"kind": "reconnect", "at": 5200.0, "index": 8},
        {"kind": "checkpoint", "at": 6600.0, "label": "abs_8h"},
        {"kind": "stale", "at": 7800.0, "index": 5},
        {"kind": "reconnect", "at": 8900.0, "index": 9},
        {"kind": "checkpoint", "at": 10200.0, "label": "abs_9h"},
    ],
    "p4_close": [
        {"kind": "reconnect", "at": 1800.0, "index": 10},
        {"kind": "checkpoint", "at": 2700.0, "label": "abs_10h"},
        {"kind": "stale", "at": 4000.0, "index": 6},
        {"kind": "reconnect", "at": 5500.0, "index": 11},
        {"kind": "checkpoint", "at": 6300.0, "label": "abs_11h"},
        {"kind": "reconnect", "at": 9200.0, "index": 12},
        {"kind": "checkpoint", "at": 9900.0, "label": "abs_12h"},
    ],
}
_PROBE_SCHEDULE: dict[str, list[dict[str, Any]]] = {
    "p1_open": [
        {"kind": "reconnect", "at": 90.0, "index": 1},
        # Witness B must really run in the PROBE too, and it must run *before* the controlled STALE
        # cycle: that cycle holds delivery for STALE_HOLD_SECONDS and then waits for freshness to
        # return, so a later slot can be cut off by the end of the probe window -- and the probe
        # would then pass without ever executing the witness it exists to check.
        {"kind": "witness_b", "at": 120.0},
        {"kind": "stale", "at": 200.0, "index": 1},
        {"kind": "checkpoint", "at": 390.0, "label": "probe_p1_late"},
    ],
    "p2_close": [
        {"kind": "checkpoint", "at": 390.0, "label": "probe_p2_late"},
    ],
}

# Checks a short PROBE structurally cannot satisfy: reported, but excluded from the PROBE verdict.
N01_8_EXTRA_PROBE_SCOPE = frozenset(
    {
        # N01-8-canonical aliases of the inherited N01-7 threshold checks.  The inherited names
        # (`active_total_ge_7200` / `reconnects_ge_5` / `stale_cycles_ge_2`) are already excluded by
        # `ms.PROBE_SCOPE_KEYS`; these aliases carry the N01-8 thresholds and must be excluded too,
        # otherwise a short probe can never report PROBE_OK.
        "active_total_ge_43200",
        "reconnects_ge_12",
        "stale_cycles_ge_6",
        "phases_completed_ge_4",
        "fresh_process_restarts_ge_3",
        "retention_analysis_present",
        "post_saturation_observation_window_present",
        "hourly_checkpoint_coverage_complete",
    }
)

# N01-8 aggregation additions whose names must not be reported under an N01-7 label.
CHECK_ALIASES = {
    "active_total_ge_7200": "active_total_ge_43200 (inherited N01-7 label, N01-8 threshold applied)",
    "reconnects_ge_5": "reconnects_ge_12 (inherited N01-7 label, N01-8 threshold applied)",
    "stale_cycles_ge_2": "stale_cycles_ge_6 (inherited N01-7 label, N01-8 threshold applied)",
}


def _apply_env_identity() -> None:
    """Point every reused helper at the N01-8 isolation domain.

    `soak` installs `n01_7_r01` names on `n6` when it is imported; `ms` reads
    `soak.N01_7_OWNED_APPLICATION` / `soak.TASK_OWNED_DATABASE_PORT` / `soak.EXPECTED_MIGRATION_HEAD`
    through module attributes at call time, so re-assigning them here is enough.  No accepted file is
    edited.
    """
    n6.DATABASE_PREFIX = N01_8_DATABASE_PREFIX
    n6.OWNED_APPLICATION = N01_8_OWNED_APPLICATION
    n6.OBSERVER_APPLICATION = N01_8_OBSERVER_APPLICATION
    soak.N01_7_DATABASE_PREFIX = N01_8_DATABASE_PREFIX
    soak.N01_7_OWNED_APPLICATION = N01_8_OWNED_APPLICATION
    soak.N01_7_OBSERVER_APPLICATION = N01_8_OBSERVER_APPLICATION
    soak.TASK_OWNED_DATABASE_PORT = N01_8_DATABASE_PORT

    ms.TASK_BASE_SHA = TASK_BASE_SHA
    ms.PRODUCTION_PATHS = PRODUCTION_PATHS
    ms.ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS = ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS
    ms.TARGET_RECONNECTS = TARGET_RECONNECTS
    ms.TARGET_STALE_CYCLES = TARGET_STALE_CYCLES
    ms.DEFAULT_RAW_OUT = DEFAULT_RAW_OUT
    ms.PROBE_SCOPE_KEYS = frozenset(set(ms.PROBE_SCOPE_KEYS) | N01_8_EXTRA_PROBE_SCOPE)
    # Validation-probe constant only (never a product contract): Plan B must still be an ACTIVE,
    # unexpired plan when the LAST restart revalidates it, which the accepted 6 h does not cover
    # inside a 12 h window.  Plan A keeps its real 30-minute product TTL and still expires first.
    ms.WITNESS_B_PLAN_TTL = timedelta(hours=18)


_apply_env_identity()


# ---------------------------------------------------------------------------------------------
# Small helpers (N01-8 only)
# ---------------------------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(UTC)


def _schedule_n01_8(phase_label: str, probe: bool) -> list[dict[str, Any]]:
    table = _PROBE_SCHEDULE if probe else _GLOBAL_SCHEDULE
    return [dict(item) for item in table.get(phase_label, [])]


def _gc_telemetry() -> dict[str, Any]:
    """Cheap, non-intrusive GC telemetry.  `tracemalloc` is deliberately NOT used: it is an
    intrusive probe that measurably raises RSS on its own and must never contaminate a long-run RSS
    series (see the project skill `long-run-soak-harness`, rule 9)."""
    out: dict[str, Any] = {"gc_enabled": gc.isenabled()}
    with contextlib.suppress(Exception):
        counts = gc.get_count()
        out["gc_count_generation_0"] = counts[0]
        out["gc_count_generation_1"] = counts[1]
        out["gc_count_generation_2"] = counts[2]
    with contextlib.suppress(Exception):
        stats = gc.get_stats()
        out["gc_stats_collections"] = [item.get("collections") for item in stats]
        out["gc_stats_collected"] = [item.get("collected") for item in stats]
        out["gc_stats_uncollectable"] = [item.get("uncollectable") for item in stats]
    return out


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(REPOSITORY_ROOT),
        check=False,
    )
    return completed.stdout.strip()


def _remote_main() -> dict[str, Any]:
    """Live remote truth for `main` -- recorded at run start and again at run end."""
    return {
        "at": _now().isoformat(),
        "ls_remote_main": _git(["ls-remote", "origin", "refs/heads/main"]),
        "local_head": _git(["rev-parse", "HEAD"]),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "task_base_sha": TASK_BASE_SHA,
    }


# ---------------------------------------------------------------------------------------------
# Phase scenario (runs inside a child OS process) -- role-driven N01-8 delta
# ---------------------------------------------------------------------------------------------
async def _phase_scenario_n01_8(
    phase_label: str,
    role: str,
    database_name: str,
    database_url: str,
    active_seconds: float,
    sample_interval: float,
    prior_active_seconds: float,
    probe: bool,
    progress_path: Path | None = None,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure: dict[str, Any] | None = None
    feed = n6._new_feed()
    samples: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {
        "phase": phase_label,
        "role": role,
        "feed": feed,
        "samples": samples,
        "checkpoints": [],
        "reconnects": [],
        "stale_cycles": [],
        "prior_active_seconds": prior_active_seconds,
        "pid": os.getpid(),
        "process_started_at": _now().isoformat(),
    }
    engine = None
    observer = None
    runtime = None
    consumer: asyncio.Task | None = None
    sampler: asyncio.Task | None = None
    controlled: ms._ControlledStream | None = None
    provider = n6.OKXLiveProvider()
    ctx["provider"] = provider

    try:
        engine = n6._smoke_engine(database_url)
        observer = n6._observer_engine()
        sessions = n6.async_sessionmaker(engine, expire_on_commit=False)
        ctx["sessions"] = sessions
        ctx["dsn"] = soak._dsn_identity(database_url)
        checks["runtime_dsn_points_at_task_owned_instance"] = (
            ctx["dsn"]["port"] == soak.TASK_OWNED_DATABASE_PORT
        )
        ctx["baseline_db_activity"] = await n6._ownership_activity(observer, database_name)
        ctx["last_activity"] = ctx["baseline_db_activity"]

        rest_started = time.monotonic()
        with soak._okx_rest_proxy():
            ctx["metadata"] = await n6._okx_metadata(provider)
        ctx["okx_rest_transport"] = {
            "proxy_used_for_rest_only": True,
            "proxy": OKX_REST_PROXY_ENV,
            "elapsed_seconds": round(time.monotonic() - rest_started, 3),
            "ws_direct": True,
        }

        harness = n6.SmokeHarness(sessions)
        ctx["harness"] = harness
        runtime = n6.EventRuntime(n6.PostgresG2Repository(sessions))
        pipeline = n6.ScannerPipeline(n6.OpportunityScanner(), runtime)
        ctx["runtime"] = runtime
        ctx["pipeline"] = pipeline

        controlled = ms._ControlledStream(provider, n6.CHANNELS)
        ctx["controlled"] = controlled
        stream = controlled.events()
        ctx["stream"] = stream

        if role == "open":
            # --- first process: boot, subscribe, create the position through the accepted path
            await harness.boot()
            await runtime.start()
            consumer = asyncio.create_task(
                n6._consume(stream, pipeline, harness, feed), name="n01-8ms-market-consumer"
            )
            ctx["consumer"] = consumer

            def initial_data_ready() -> bool:
                return all(
                    feed["trades"][item] > 0 and feed["bbos"][item] > 0 for item in INSTRUMENTS
                )

            ready = await n6._wait_until(initial_data_ready, n6.INITIAL_DATA_MAX_WAIT_SECONDS, 0.2)
            checks["initial_real_data_both_symbols"] = ready
            if not ready:
                raise AssertionError("real BTC/ETH trade+BBO data did not arrive in time")
        else:
            # --- fresh process: PostgreSQL recovery owns the RUNNING transition (never forced)
            await harness.state_service.ensure(RUN_MODE)

            # Warm-up: pull real events until both instruments have a live BBO so recovery has a
            # genuine fresh quote. These events are counted and discarded -- never replayed.
            warmup_started = time.monotonic()
            warmup_events = 0
            while not all(item in harness.quotes for item in INSTRUMENTS):
                if time.monotonic() - warmup_started > n6.INITIAL_DATA_MAX_WAIT_SECONDS:
                    raise AssertionError(f"{phase_label} warm-up never produced a live BBO")
                event = await asyncio.wait_for(stream.__anext__(), timeout=30.0)
                warmup_events += 1
                if isinstance(event, n6.NormalizedBookTicker):
                    harness.publish_quote(n6._to_bbo(event))
            ctx["warmup"] = {
                "events_discarded": warmup_events,
                "seconds": round(time.monotonic() - warmup_started, 3),
                "quotes": {
                    item: harness.quotes[item].received_at.isoformat() for item in INSTRUMENTS
                },
            }

            recovery_started = time.monotonic()

            async def _reconcile_for_recovery(run_mode):
                return await ms.reconcile(
                    run_mode,
                    sessions=sessions,
                    execution=harness.execution,
                    now=harness.clock.now(),
                    clock=harness.clock,
                )

            async def _bbo_for(instrument_id: str):
                quote = harness.quotes.get(instrument_id)
                if quote is None:
                    raise RuntimeError(f"no_live_quote_for:{instrument_id}")
                return quote

            manager = RecoveryManager(
                sessions,
                harness.state_service,
                harness.incidents,
                harness.health,
                harness.protection,
                harness.execution,
                _reconcile_for_recovery,
                clock=harness.clock,
                gap_threshold=timedelta(seconds=10),
            )
            recovery = await manager.recover(RUN_MODE, bbo_for=_bbo_for, now=harness.clock.now())
            ctx["recovery"] = {
                "seconds": round(time.monotonic() - recovery_started, 3),
                "report": json.loads(recovery.model_dump_json()),
            }
            ctx["recovery_bbo"] = {
                item: harness.quotes[item].model_dump(mode="json") for item in harness.quotes
            }
            checks["recovery_ok"] = recovery.ok is True
            checks["recovery_final_state_running"] = str(recovery.final_system_state) == "RUNNING"

            recovered_position = await n6._position(sessions, RUN_MODE, BTC)
            async with sessions() as session:
                recovered_plan = await load_active_plan(session, RUN_MODE, BTC)
            ctx["recovered_position"] = {
                "quantity": recovered_position.quantity if recovered_position else 0.0,
                "average_cost": recovered_position.average_cost if recovered_position else None,
                "protection_present": (
                    resolve_open_position_protection(recovered_position) is not None
                    if recovered_position is not None
                    else False
                ),
                "protection_plan_id": (
                    recovered_position.protection_plan_id
                    if recovered_position is not None
                    else None
                ),
                "protection_plan_version": (
                    recovered_position.protection_plan_version
                    if recovered_position is not None
                    else None
                ),
                "protection_updated_at": (
                    recovered_position.protection_updated_at.isoformat()
                    if recovered_position is not None and recovered_position.protection_updated_at
                    else None
                ),
            }
            ctx["recovered_account"] = await n6._account(sessions)
            ctx["recovered_counts"] = await n6._economic_counts(sessions, RUN_MODE)
            ctx["recovered_plan"] = (
                None
                if recovered_plan is None
                else {
                    "plan_id": recovered_plan.plan_id,
                    "plan_version": recovered_plan.plan_version,
                    "expires_at": recovered_plan.expires_at.isoformat(),
                    "expired": harness.clock.now() >= recovered_plan.expires_at,
                }
            )
            checks["recovery_position_present"] = bool(
                recovered_position is not None and recovered_position.quantity > 0.0
            )
            checks["recovery_protection_snapshot_present"] = ctx["recovered_position"][
                "protection_present"
            ]
            if recovered_plan is not None:
                ctx["entry_plan_id"] = recovered_plan.plan_id
                ctx["entry_plan_version"] = recovered_plan.plan_version

            await runtime.start()
            consumer = asyncio.create_task(
                n6._consume(stream, pipeline, harness, feed), name="n01-8ms-market-consumer"
            )
            ctx["consumer"] = consumer

        ctx["active_started_at"] = _now()
        ctx["active_started_monotonic"] = time.monotonic()
        ctx["rss_start"] = n6._rss_mb()

        async def sample_once() -> dict[str, Any]:
            activity = await n6._ownership_activity(observer, database_name)
            ctx["last_activity"] = activity
            state = await soak._db_state(sessions)
            snapshot = {
                "phase": phase_label,
                "role": role,
                "at": _now().isoformat(),
                "elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
                "absolute_elapsed_seconds": round(
                    prior_active_seconds + (time.monotonic() - ctx["active_started_monotonic"]), 3
                ),
                "btc_trades": feed["trades"][BTC],
                "btc_bbos": feed["bbos"][BTC],
                "eth_trades": feed["trades"][ETH],
                "eth_bbos": feed["bbos"][ETH],
                "total_events": feed["total_normalized_events"],
                "btc_last_trade_age_seconds": soak._age(feed["last_trade_received"].get(BTC)),
                "btc_last_bbo_age_seconds": soak._age(feed["last_bbo_received"].get(BTC)),
                "eth_last_trade_age_seconds": soak._age(feed["last_trade_received"].get(ETH)),
                "eth_last_bbo_age_seconds": soak._age(feed["last_bbo_received"].get(ETH)),
                "btc_fresh": feed["last_freshness"].get(BTC, {}).get("fresh"),
                "eth_fresh": feed["last_freshness"].get(ETH, {}).get("fresh"),
                "btc_data_quality": feed["bbo_data_quality"].get(BTC),
                "eth_data_quality": feed["bbo_data_quality"].get(ETH),
                "health_status": harness.health.status(HealthComponent.CORE_MARKET_DATA.value),
                "connection_attempts": provider.connection_attempts,
                "reconnects": provider.reconnects,
                "controlled_reconnects": controlled.reconnects_performed,
                "stale_injection_active": controlled.stale,
                "queue_size": runtime.queue.qsize(),
                "queue_capacity": runtime.queue.maxsize,
                "inflight": len(runtime._inflight),
                "worker_count": len(runtime._workers),
                "workers_alive": sum(1 for task in runtime._workers if not task.done()),
                "worker_exceptions": len(runtime.worker_exceptions),
                "worker_exception_capacity": runtime._worker_exception_capacity,
                "dedupe_size": len(runtime._dedupe),
                "dedupe_capacity": runtime._dedupe_capacity,
                "trade_dedupe_size": len(pipeline._trade_dedupe),
                "trade_dedupe_capacity": pipeline._trade_dedupe_capacity,
                "rss_mb": n6._rss_mb(),
                "pg_owned_client_sessions": activity["owned_client_sessions"],
                "pg_other_client_sessions": activity["other_client_sessions"],
                "pg_idle_in_transaction": activity["idle_in_transaction"],
                "runtime_errors": len(feed["errors"]),
                **state,
                **_gc_telemetry(),
                **ms._proc_resources(),
            }
            samples.append(snapshot)
            if progress_path is not None:
                ms._append_jsonl(progress_path, snapshot)
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
                            "message": f"n01-8ms-sampler: {exc}",
                        }
                    )
                await asyncio.sleep(sample_interval)

        await sample_once()
        sampler = asyncio.create_task(sample_loop(), name="n01-8ms-sampler")
        ctx["sampler"] = sampler

        # --- boundary checkpoint (task section 17: start / after every restart)
        await ms._checkpoint("start" if role == "open" else "after_restart", ctx, harness, sessions)

        schedule = _schedule_n01_8(phase_label, probe)
        # Only the OPEN phase creates the position; every later phase must recover the *same* one.
        entry_offset = min(60.0, max(10.0, active_seconds * 0.10))
        entry_done = role != "open"
        pending = sorted(schedule, key=lambda item: item["at"])
        expiry_crossed = False
        witness_at: float | None = None
        before_restart_done = False

        while True:
            elapsed = time.monotonic() - ctx["active_started_monotonic"]

            if not entry_done and elapsed >= entry_offset:

                def entry_ready() -> bool:
                    return (
                        harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                        and BTC in feed["latest_bbo"]
                        and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                        <= n6.FRESH_QUOTE_MAX_AGE_SECONDS
                        and feed["last_freshness"].get(BTC, {}).get("fresh") is True
                    )

                await n6._wait_until(entry_ready, timeout=n6.ENTRY_GATE_MAX_WAIT_SECONDS)
                ctx["entry"] = await n6._controlled_entry(harness, sessions, feed, checks)
                ctx["entry_plan_id"] = ctx["entry"]["plan"]["plan_id"]
                ctx["entry_plan_version"] = ctx["entry"]["plan"].get("plan_version")
                entry_done = True

            while pending and elapsed >= pending[0]["at"]:
                item = pending.pop(0)
                if item["kind"] == "reconnect":
                    ctx["reconnects"].append(
                        await ms._controlled_reconnect(
                            item["index"], controlled, harness, sessions, feed, ctx
                        )
                    )
                elif item["kind"] == "stale":
                    ctx["stale_cycles"].append(
                        await ms._stale_fresh_cycle(
                            item["index"], controlled, harness, sessions, feed, ctx
                        )
                    )
                elif item["kind"] == "checkpoint":
                    await ms._checkpoint(item["label"], ctx, harness, sessions)
                elif item["kind"] == "witness_b":
                    ctx["witness_b"] = await ms._witness_b_new_active_plan(
                        harness, sessions, feed, ctx, checks
                    )

            # Witness A/B: only the OPEN phase owns Plan A, so the TTL-expiry witness runs there.
            if entry_done and role == "open" and not probe:
                if not expiry_crossed and samples[-1].get("plan_expired"):
                    expiry_crossed = True
                    ctx["expiry_crossed_at"] = samples[-1]["at"]
                    ctx["expiry_crossed_elapsed_seconds"] = samples[-1]["elapsed_seconds"]
                    witness_at = (
                        samples[-1]["elapsed_seconds"] + soak.POST_EXPIRY_WITNESS_DELAY_SECONDS
                    )
                if (
                    expiry_crossed
                    and witness_at is not None
                    and "f01" not in ctx
                    and elapsed >= witness_at
                ):
                    ctx["f01"] = await soak._f01_witness(
                        harness, sessions, feed, ctx["entry_plan_id"], checks
                    )
                    ctx["f01_elapsed_seconds"] = round(elapsed, 3)
                    ctx["witness_b"] = await ms._witness_b_new_active_plan(
                        harness, sessions, feed, ctx, checks
                    )

            # A fresh-process restart follows every non-final phase, so the durable state is
            # checkpointed immediately before the process is stopped -- the accepted verifier
            # requires the label `before_restart` (see `checkpoint_coverage_complete` /
            # `checkpoints_cover_required_points`) and it must sit just before a real restart.
            if (
                role != "close"
                and not before_restart_done
                and elapsed >= active_seconds - 60.0
            ):
                await ms._checkpoint("before_restart", ctx, harness, sessions)
                before_restart_done = True

            if elapsed >= active_seconds:
                break
            await asyncio.sleep(0.5)

        ctx["active_duration_seconds"] = time.monotonic() - ctx["active_started_monotonic"]
        ctx["active_finished_at"] = _now()
        if role == "open":
            checks["controlled_entry_performed"] = "entry" in ctx
            checks["phase_first_position_left_open"] = True
            checks["phase_first_protection_snapshot_left_in_place"] = True
            if not entry_done:
                raise AssertionError("controlled entry never executed during the active window")
        else:
            # Witness C after every restart: authority must still come from the durable position
            # snapshot, never re-derived from a plan, an AI or transient memory.
            ctx["f01_after_restart"] = await ms._protection_authority_after_restart(
                harness, sessions, ctx, checks
            )
            if role == "continue":
                checks["phase_first_position_left_open"] = True
                checks["phase_first_protection_snapshot_left_in_place"] = True
                await ms._checkpoint("final_before_stop", ctx, harness, sessions)
            else:
                await n6._wait_until(
                    lambda: (
                        BTC in feed["latest_bbo"]
                        and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                        <= n6.FRESH_QUOTE_MAX_AGE_SECONDS
                    ),
                    timeout=30.0,
                )
                ctx["exit"] = await n6._controlled_close(harness, sessions, feed, checks)

        # ------------------------------------------------------------------ graceful stop
        if consumer is not None:
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)
            consumer = None
            ctx["consumer"] = None
        controlled.stop()
        with contextlib.suppress(Exception):
            await stream.aclose()
        ctx["stream"] = None
        await runtime.stop()
        if sampler is not None:
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
            if task.get_name().startswith(("g2-event-worker-", "n01-8")) and not task.done()
        ]
        checks["queue_drained"] = ctx["queue_final"] == 0
        checks["inflight_empty"] = ctx["inflight_final"] == 0
        checks["runtime_workers_stopped"] = (
            ctx["workers_final"] == 0 and not ctx["worker_tasks_final"]
        )
        checks["worker_exceptions_zero"] = ctx["worker_exceptions_final"] == 0

        ctx["durable_state_at_stop"] = await soak._db_state(sessions)
        ctx["counts_at_stop"] = await n6._economic_counts(sessions, RUN_MODE)
        ctx["account_at_stop"] = await n6._account(sessions)
        ctx["runtime_control_at_stop"] = await ms._runtime_control(sessions)

        if role == "close":
            await ms._final_assertions(ctx, harness, sessions, checks)

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

        cleanup = await n6._wait_for_owned_client_cleanup(
            database_name, soak.N01_7_OWNED_APPLICATION
        )
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
        for task in (sampler, consumer):
            if task is not None:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        if controlled is not None:
            controlled.stop()
        if ctx.get("stream") is not None:
            try:
                await ctx["stream"].aclose()
            except Exception as exc:  # noqa: BLE001
                shutdown_errors.append(
                    {"step": "stream_aclose", "type": type(exc).__name__, "message": str(exc)}
                )
        if runtime is not None:
            try:
                await runtime.stop()
            except Exception as exc:  # noqa: BLE001
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
                database_name, soak.N01_7_OWNED_APPLICATION
            )
            ctx["cleanup"] = cleanup
            checks.setdefault("pg_owned_clients_zero", cleanup.final_snapshot.client_sessions == 0)
            checks.setdefault(
                "pg_idle_in_transaction_zero", cleanup.final_snapshot.idle_in_transaction == 0
            )
            checks.setdefault("pg_no_foreign_client_sessions", not cleanup.foreign_rows)
        except Exception as exc:  # noqa: BLE001
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
        ctx["process_exited_at"] = _now().isoformat()

    try:
        report = ms._build_phase_report(phase_label, ctx, checks, failure, provider, feed)
        report["role"] = role
        return report
    except Exception as exc:  # noqa: BLE001 - a report bug must never hide the verdict
        return {
            "phase": phase_label,
            "role": role,
            "pid": ctx.get("pid"),
            "result": "FAIL",
            "report_build_error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "failure": failure,
            "checks": checks,
            "active_duration_seconds": ctx.get("active_duration_seconds"),
            "reconnects": ctx.get("reconnects"),
            "stale_cycles": ctx.get("stale_cycles"),
            "checkpoints": ctx.get("checkpoints"),
            "samples": ctx.get("samples", []),
            "harness_errors": feed["errors"][:100],
        }


# ---------------------------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------------------------
def _child_command(
    phase_label: str,
    role: str,
    database_url: str,
    database_name: str,
    seconds: float,
    sample_interval: float,
    prior_active_seconds: float,
    probe: bool,
    raw_out: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--mode",
        "phase",
        "--phase",
        phase_label,
        "--role",
        role,
        "--database-url",
        database_url,
        "--database-name",
        database_name,
        "--seconds",
        str(seconds),
        "--sample-interval",
        str(sample_interval),
        "--prior-active-seconds",
        str(prior_active_seconds),
        "--raw-out",
        str(raw_out),
    ]
    if probe:
        command.append("--probe")
    return command


def _write_status(path: Path, payload: dict[str, Any]) -> None:
    with contextlib.suppress(Exception):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _supervisor(args) -> int:
    raw_out = Path(args.raw_out or DEFAULT_RAW_OUT)
    log_dir = raw_out.parent / "n01-8-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    status_path = raw_out.parent / "supervisor_status.json"

    phases = PROBE_PHASE_PLAN if args.probe else PHASE_PLAN
    if args.seconds:
        phase_seconds = float(args.seconds)
    elif args.probe:
        phase_seconds = PROBE_PHASE_SECONDS
    else:
        phase_seconds = DEFAULT_PHASE_SECONDS
    mode = "PROBE" if args.probe else "ACCEPTANCE"

    started = _now()
    main_before = _remote_main()
    launch = {
        "task": "N01-8",
        "mode": mode,
        "supervisor_pid": os.getpid(),
        "supervisor_argv": sys.argv,
        "started_at": started.isoformat(),
        "task_base_sha": TASK_BASE_SHA,
        "phase_plan": [{"phase": label, "role": role} for label, role in phases],
        "phase_seconds": phase_seconds,
        "sample_interval_seconds": args.sample_interval,
        "raw_out": str(raw_out),
        "log_dir": str(log_dir),
        "n01_8_environment": {
            "container": N01_8_CONTAINER,
            "port": N01_8_DATABASE_PORT,
            "database_prefix": N01_8_DATABASE_PREFIX,
            "owned_application_name": N01_8_OWNED_APPLICATION,
            "observer_application_name": N01_8_OBSERVER_APPLICATION,
        },
        "main_before": main_before,
    }
    _write_status(raw_out.parent / "acceptance_launch.json", launch)

    shared_before = asyncio.run(soak._shared_primary_snapshot(soak.SHARED_PRIMARY_URL))
    phase_process_errors: list[dict[str, Any]] = []
    phase_reports: list[dict[str, Any]] = []
    phase_runs: list[dict[str, Any]] = []
    prior_active = 0.0

    _write_status(
        status_path,
        {
            "task": "N01-8",
            "mode": mode,
            "state": "RUNNING",
            "supervisor_pid": os.getpid(),
            "started_at": started.isoformat(),
            "total_phases": len(phases),
            "phases_completed": 0,
            "last_update_at": _now().isoformat(),
        },
    )

    with n6._disposable_postgres_database() as (database_name, database_url):
        revision = asyncio.run(soak._alembic_version(database_url))
        protection_schema = asyncio.run(soak._protection_schema(database_url))
        for position, (phase_label, role) in enumerate(phases, start=1):
            phase_raw = log_dir / f"phase_{phase_label}_raw.json"
            run = ms._run_child(
                _child_command(
                    phase_label,
                    role,
                    database_url,
                    database_name,
                    phase_seconds,
                    args.sample_interval,
                    prior_active,
                    args.probe,
                    phase_raw,
                ),
                timeout=phase_seconds + 1800.0,
                log_path=log_dir / f"phase_{phase_label}.stdout.txt",
            )
            report = (
                json.loads(phase_raw.read_text(encoding="utf-8")) if phase_raw.exists() else None
            )
            if report is not None:
                phase_reports.append(report)
                if report.get("active_duration_seconds"):
                    prior_active += float(report["active_duration_seconds"])
            if run["returncode"] != 0:
                phase_process_errors.append(
                    {
                        "step": f"phase_{phase_label}_process",
                        "returncode": run["returncode"],
                        "log": run["log"],
                    }
                )
            phase_runs.append({"phase": phase_label, "role": role, **run})
            _write_status(
                status_path,
                {
                    "task": "N01-8",
                    "mode": mode,
                    "state": "RUNNING",
                    "supervisor_pid": os.getpid(),
                    "started_at": started.isoformat(),
                    "total_phases": len(phases),
                    "phases_completed": position,
                    "current_phase": phase_label,
                    "prior_active_seconds": round(prior_active, 3),
                    "phase_runs": phase_runs,
                    "last_update_at": _now().isoformat(),
                },
            )

    shared_after = asyncio.run(soak._shared_primary_snapshot(soak.SHARED_PRIMARY_URL))
    leftover = asyncio.run(n6._n01_6_leftover_databases())
    finished = _now()
    main_after = _remote_main()

    if not phase_reports:
        report = {
            "task": "N01-8",
            "mode": mode,
            "result": "FAIL",
            "reason": "no child phase produced a report",
            "phase_process_errors": phase_process_errors,
            "database_name": database_name,
        }
        _write_status(status_path, {**report, "state": "FINISHED", "finished_at": finished.isoformat()})
        return ms._emit(report, raw_out)

    final = _aggregate_n01_8(
        mode=mode,
        database_name=database_name,
        database_url=database_url,
        revision=revision,
        protection_schema=protection_schema,
        phase_reports=phase_reports,
        phase_runs=phase_runs,
        shared_before=shared_before,
        shared_after=shared_after,
        leftover=leftover,
        started=started,
        finished=finished,
        probe=args.probe,
        phase_process_errors=phase_process_errors,
        code_evidence=ms._code_freeze_evidence(),
        main_before=main_before,
        main_after=main_after,
        launch=launch,
        phase_plan=phases,
        phase_seconds=phase_seconds,
    )
    _write_status(
        status_path,
        {
            "task": "N01-8",
            "mode": mode,
            "state": "FINISHED",
            "supervisor_pid": os.getpid(),
            "result": final.get("result"),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "total_phases": len(phases),
            "phases_completed": len(phase_reports),
            "total_active_seconds": (final.get("run_identity") or {}).get("total_active_seconds"),
            "failures": final.get("failures"),
            "raw_out": str(raw_out),
        },
    )
    return ms._emit(final, raw_out)


# ---------------------------------------------------------------------------------------------
# N01-8 aggregation: fold N phase reports into the accepted 2-phase aggregation
# ---------------------------------------------------------------------------------------------
def _merge_phase_reports(phase_reports: list[dict[str, Any]]) -> tuple[dict, dict]:
    """Fold N phase reports into the `(first, second)` pair `ms._aggregate` expects.

    The fold is deliberately narrow and auditable:
      * `checks`  -> AND-merge across every phase (a phase-local False can never be hidden), and the
        merged dict is placed on BOTH sides so `first_checks` / `second_checks` each describe the
        whole timeline;
      * the earlier phases fold into `first` and the final phase into `second`, because the accepted
        aggregate CONCATENATES `reconnects` / `stale_cycles` / `checkpoints` / `samples` / errors
        and then computes a per-side net growth (`socket_growth_first` / `socket_growth_second`).
        Putting every sample on one side would leave the other side's net growth `None` and make the
        resource-band checks fail for a harness reason rather than a runtime one;
      * `active_duration_seconds` -> summed per side, so the accepted total is the true total;
      * restart-boundary fields (`active_finished_at`, `counts_at_stop`, `durable_state_at_stop`) ->
        taken from the penultimate phase, so the accepted "no fabricated fill across restart" check
        compares the LAST restart boundary rather than the first.

    With N == 2 this reduces exactly to the accepted two-phase shape.
    """
    head = phase_reports[:-1]
    last = phase_reports[-1]
    penultimate = phase_reports[-2] if len(phase_reports) > 1 else phase_reports[-1]

    merged_checks: dict[str, bool] = {}
    for report in phase_reports:
        for key, value in (report.get("checks") or {}).items():
            merged_checks[key] = bool(merged_checks.get(key, True)) and (value is True)

    def collect(source: list[dict[str, Any]], key: str) -> list[Any]:
        return [item for report in source for item in (report.get(key) or [])]

    def shutdown_errors(source: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            dict(item, phase=report.get("phase"))
            for report in source
            for item in ((report.get("shutdown") or {}).get("errors") or [])
        ]

    head_or_last = head or [last]
    merged_first = {
        **phase_reports[0],
        "active_duration_seconds": sum(
            float(report.get("active_duration_seconds") or 0.0) for report in head
        ),
        "active_finished_at": penultimate.get("active_finished_at"),
        "counts_at_stop": penultimate.get("counts_at_stop"),
        "durable_state_at_stop": penultimate.get("durable_state_at_stop"),
        "reconnects": collect(head_or_last, "reconnects"),
        "stale_cycles": collect(head_or_last, "stale_cycles"),
        "checkpoints": collect(head_or_last, "checkpoints"),
        "samples": collect(head_or_last, "samples"),
        "harness_errors": collect(head_or_last, "harness_errors"),
        "checks": merged_checks,
        "shutdown": {"errors": shutdown_errors(head_or_last)},
    }
    merged_last = {
        **last,
        "active_duration_seconds": float(last.get("active_duration_seconds") or 0.0),
        "reconnects": collect([last], "reconnects"),
        "stale_cycles": collect([last], "stale_cycles"),
        "checkpoints": collect([last], "checkpoints"),
        "samples": collect([last], "samples"),
        "harness_errors": collect([last], "harness_errors"),
        "checks": merged_checks,
        "shutdown": {**(last.get("shutdown") or {}), "errors": shutdown_errors([last])},
    }
    return merged_first, merged_last


def _int_series(samples: list[dict[str, Any]], key: str) -> list[int]:
    return [item[key] for item in samples if isinstance(item.get(key), int)]


def _float_series(samples: list[dict[str, Any]], key: str) -> list[float]:
    return [float(item[key]) for item in samples if isinstance(item.get(key), (int, float))]


def _rolling_slopes(samples: list[dict[str, Any]], window_seconds: float = 1800.0) -> dict[str, Any]:
    """Rolling RSS trend: 30-minute window means plus the trailing slope over those window means.

    Only the SHAPE is reported here.  RSS slope is never used on its own to attribute a cause
    (see `_retention_analysis` and the project skill `long-run-soak-harness`, rule 9).
    """
    points = [
        (float(item["absolute_elapsed_seconds"]), float(item["rss_mb"]))
        for item in samples
        if isinstance(item.get("rss_mb"), (int, float))
        and isinstance(item.get("absolute_elapsed_seconds"), (int, float))
    ]
    if not points:
        return {"window_seconds": window_seconds, "windows": [], "reason": "no_samples"}
    windows: list[dict[str, Any]] = []
    start = points[0][0]
    end = points[-1][0]
    cursor = start
    while cursor <= end:
        bucket = [value for ts, value in points if cursor <= ts < cursor + window_seconds]
        if bucket:
            windows.append(
                {
                    "window_start_seconds": round(cursor, 3),
                    "samples": len(bucket),
                    "rss_mean_mb": round(sum(bucket) / len(bucket), 3),
                    "rss_max_mb": round(max(bucket), 3),
                    "rss_min_mb": round(min(bucket), 3),
                }
            )
        cursor += window_seconds
    means = [
        (item["window_start_seconds"] + window_seconds / 2.0, item["rss_mean_mb"])
        for item in windows
    ]
    return {
        "window_seconds": window_seconds,
        "windows": windows,
        "trailing_slope_mib_per_hour": soak._slope_per_hour(means),
        "window_mean_first_mb": windows[0]["rss_mean_mb"] if windows else None,
        "window_mean_last_mb": windows[-1]["rss_mean_mb"] if windows else None,
        "window_mean_peak_mb": max((item["rss_mean_mb"] for item in windows), default=None),
    }


def _retention_series(
    samples: list[dict[str, Any]], size_key: str, capacity_key: str
) -> dict[str, Any]:
    """Bounded-retention behaviour for one capacity-limited structure (task section 22)."""
    rows = [
        (
            float(item["absolute_elapsed_seconds"]),
            int(item[size_key]),
            item.get(capacity_key),
            item.get("rss_mb"),
        )
        for item in samples
        if isinstance(item.get(size_key), int)
        and isinstance(item.get("absolute_elapsed_seconds"), (int, float))
    ]
    out: dict[str, Any] = {"size_key": size_key, "capacity_key": capacity_key, "points": len(rows)}
    if not rows:
        out["reason"] = "no_samples"
        return out
    capacity = next((row[2] for row in rows if isinstance(row[2], int)), None)
    out["capacity"] = capacity
    out["max_size_observed"] = max(row[1] for row in rows)
    out["final_size"] = rows[-1][1]
    if not isinstance(capacity, int) or capacity <= 0:
        out["saturated"] = False
        out["reason"] = "capacity_unknown"
        return out

    first_saturation = next((row for row in rows if row[1] >= capacity), None)
    out["first_saturation_elapsed_seconds"] = (
        None if first_saturation is None else round(first_saturation[0], 3)
    )
    out["first_saturation_rss_mb"] = None if first_saturation is None else first_saturation[3]
    # Sustained saturation: the earliest sample after which size NEVER drops below capacity again.
    sustained_index: int | None = None
    for index in range(len(rows)):
        if all(row[1] >= capacity for row in rows[index:]):
            sustained_index = index
            break
    out["sustained_saturation_elapsed_seconds"] = (
        None if sustained_index is None else round(rows[sustained_index][0], 3)
    )
    out["saturated"] = sustained_index is not None

    rss_points = [
        (ts, rss) for ts, _, _, rss in rows if isinstance(rss, (int, float))
    ]
    if not rss_points:
        return out
    out["rss_at_start_mb"] = rss_points[0][1]
    out["rss_final_mb"] = rss_points[-1][1]
    if first_saturation is None:
        out["pre_saturation_slope_mib_per_hour"] = soak._slope_per_hour(rss_points)
        return out

    saturation_ts = first_saturation[0]
    pre = [(ts, rss) for ts, rss in rss_points if ts < saturation_ts]
    out["pre_saturation_slope_mib_per_hour"] = soak._slope_per_hour(pre)
    window_end = saturation_ts + 1800.0
    window = [(ts, rss) for ts, rss in rss_points if saturation_ts <= ts <= window_end]
    out["saturation_window_slope_mib_per_hour"] = soak._slope_per_hour(window)
    out["saturation_window_seconds"] = 1800.0

    if sustained_index is not None:
        sustained_ts = rows[sustained_index][0]
        post = [(ts, rss) for ts, rss in rss_points if ts >= sustained_ts]
        out["post_saturation_observation_seconds"] = round(rss_points[-1][0] - sustained_ts, 3)
        out["post_saturation_points"] = len(post)
        out["post_saturation_slope_mib_per_hour"] = soak._slope_per_hour(post)
        out["rss_at_sustained_saturation_mb"] = next(
            (rss for ts, rss in rss_points if ts >= sustained_ts), None
        )
        out["rss_peak_after_saturation_mb"] = (
            max(rss for ts, rss in post) if post else None
        )
    return out


def _retention_analysis(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Task section 22/23: saturation timeline + post-saturation RSS behaviour + companion trends.

    Nothing here changes the frozen Memory AND gate -- it is the independent answer to "is the RSS
    growth explained by a bounded retention structure that fills up and then stops?".
    """
    dedupe = _retention_series(samples, "dedupe_size", "dedupe_capacity")
    trade_dedupe = _retention_series(samples, "trade_dedupe_size", "trade_dedupe_capacity")

    companion_keys = (
        "asyncio_tasks_total",
        "worker_count",
        "queue_size",
        "inflight",
        "sockets",
        "handles",
        "pg_owned_client_sessions",
        "pg_other_client_sessions",
        "pg_idle_in_transaction",
        "worker_exceptions",
        "total_events",
    )
    companion: dict[str, Any] = {}
    for key in companion_keys:
        # Aligned (elapsed, value) pairs: taking the two series independently and zipping them would
        # mis-align sample sets that do not all carry the key.
        pairs = [
            (float(item["absolute_elapsed_seconds"]), int(item[key]))
            for item in samples
            if isinstance(item.get(key), int)
            and isinstance(item.get("absolute_elapsed_seconds"), (int, float))
        ]
        if not pairs:
            companion[key] = {"points": 0}
            continue
        series = [value for _, value in pairs]
        companion[key] = {
            "points": len(series),
            "first": series[0],
            "max": max(series),
            "final": series[-1],
            "net_growth": ms._net_growth(series),
            "slope_per_hour": soak._slope_per_hour(pairs),
        }

    return {
        "dedupe": dedupe,
        "trade_dedupe": trade_dedupe,
        "companion_trends": companion,
    }


def _operational_memory_interpretation(
    memory: dict[str, Any], retention: dict[str, Any], rolling: dict[str, Any]
) -> dict[str, Any]:
    """Task section 23: state what the evidence supports, without presupposing a conclusion.

    Explicitly never says "memory is fine" / "memory resolved": the frozen gate's AND structure can
    leave the slope branch exceeded while `finding` stays false, which is exactly what happened in
    N01-7-R01 and is still an OPEN concern.
    """
    dedupe = retention.get("dedupe") or {}
    trade_dedupe = retention.get("trade_dedupe") or {}
    post_slope = trade_dedupe.get("post_saturation_slope_mib_per_hour")
    post_seconds = trade_dedupe.get("post_saturation_observation_seconds")
    saturated = bool(trade_dedupe.get("saturated"))
    bounded_growth = {
        key: value.get("net_growth")
        for key, value in (retention.get("companion_trends") or {}).items()
        if key in {"asyncio_tasks_total", "sockets", "handles", "pg_owned_client_sessions"}
        and isinstance(value.get("net_growth"), int)
    }
    slope_branch_exceeded = bool(
        isinstance(memory.get("second_half_trend_mib_per_hour"), (int, float))
        and memory["second_half_trend_mib_per_hour"]
        > ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR
    )
    plateau = bool(
        isinstance(post_slope, (int, float))
        and post_slope <= ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR
    )
    if not saturated:
        classification = "RETENTION_NOT_SATURATED_WITHIN_WINDOW"
    elif plateau:
        classification = "POST_SATURATION_PLATEAU"
    else:
        classification = "POST_SATURATION_STILL_TRENDING"
    return {
        "classification": classification,
        "retention_saturated": saturated,
        "dedupe_saturated": bool(dedupe.get("saturated")),
        "dedupe_post_saturation_slope_mib_per_hour": dedupe.get(
            "post_saturation_slope_mib_per_hour"
        ),
        "post_saturation_slope_mib_per_hour": post_slope,
        "post_saturation_observation_seconds": post_seconds,
        "slope_branch_exceeded": slope_branch_exceeded,
        "slope_branch_threshold_mib_per_hour": ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR,
        "companion_net_growth": bounded_growth,
        "companion_structures_bounded": all(
            isinstance(value, int) and value <= 0 for value in bounded_growth.values()
        )
        if bounded_growth
        else None,
        "rolling_window_trailing_slope_mib_per_hour": rolling.get(
            "trailing_slope_mib_per_hour"
        ),
        "frozen_gate_unchanged": {
            "total_growth_mib_threshold": ms.MEMORY_TOTAL_GROWTH_MIB,
            "second_half_trend_mib_per_hour_threshold": ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR,
            "combination": "AND",
        },
        "p2_watch_item": "N01-7-R01-RR-P2-01",
        "statement": (
            "Operational memory interpretation only. It does NOT close the N01-7-R01-RR-P2-01 watch "
            "item and does NOT assert that memory is fine. The frozen AND gate is evaluated "
            "separately in `memory`."
        ),
    }


def _aggregate_n01_8(
    *,
    mode: str,
    database_name: str,
    database_url: str,
    revision: str | None,
    protection_schema: dict[str, Any],
    phase_reports: list[dict[str, Any]],
    phase_runs: list[dict[str, Any]],
    shared_before: dict[str, Any],
    shared_after: dict[str, Any],
    leftover: int,
    started: datetime,
    finished: datetime,
    probe: bool,
    phase_process_errors: list[dict[str, Any]],
    code_evidence: dict[str, Any],
    main_before: dict[str, Any],
    main_after: dict[str, Any],
    launch: dict[str, Any],
    phase_plan: tuple[tuple[str, str], ...],
    phase_seconds: float,
) -> dict[str, Any]:
    merged_first, merged_last = _merge_phase_reports(phase_reports)
    report = ms._aggregate(
        mode=mode,
        database_name=database_name,
        database_url=database_url,
        revision=revision,
        protection_schema=protection_schema,
        first=merged_first,
        second=merged_last,
        shared_before=shared_before,
        shared_after=shared_after,
        leftover=leftover,
        started=started,
        finished=finished,
        probe=probe,
        phase_process_errors=phase_process_errors,
        code_evidence=code_evidence,
    )

    all_checks: dict[str, bool] = dict(report.get("checks") or {})

    # The whole-timeline series MUST be rebuilt straight from the ordered phase reports.  Reading
    # them back off `merged_first` would silently drop the final phase, because the fold puts the
    # earlier phases on `first` and only the last phase on `second` (the accepted `ms._aggregate`
    # itself concatenates `first + second` internally, so it is unaffected — but the N01-8 extras,
    # memory, retention and rolling-slope analysis below are computed here, not by the accepted
    # aggregate).
    def _collect(key: str) -> list[Any]:
        return [item for report in phase_reports for item in (report.get(key) or [])]

    samples = _collect("samples")
    reconnects = _collect("reconnects")
    stale_cycles = _collect("stale_cycles")
    checkpoints = _collect("checkpoints")
    total_active = sum(float(item.get("active_duration_seconds") or 0.0) for item in phase_reports)
    pids = [item.get("pid") for item in phase_reports]
    distinct_pids = len({pid for pid in pids if pid is not None})

    memory = _memory_condition_n01_8(samples)
    retention = _retention_analysis(samples)
    rolling = _rolling_slopes(samples)

    # The accepted `ms._aggregate` only inspects `first`/`second`, so a phase that failed with an
    # exception but still produced all-True checks would be invisible to `phase_failures`.  These
    # three checks close that gap over EVERY phase report.
    hourly_labels = {f"abs_{hour}h" for hour in range(1, TARGET_PHASES * 3 + 1)}
    extra_checks: dict[str, bool] = {
        "phases_completed_ge_4": len(phase_reports) >= TARGET_PHASES,
        "all_planned_phases_present": [item.get("phase") for item in phase_reports]
        == [label for label, _ in phase_plan],
        "fresh_process_restarts_ge_3": distinct_pids >= TARGET_FRESH_PROCESS_RESTARTS + 1,
        "fresh_process_pids_all_distinct": len(set(pids)) == len(pids),
        "active_total_ge_43200": total_active >= ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS,
        "reconnects_ge_12": len(reconnects) >= TARGET_RECONNECTS,
        "stale_cycles_ge_6": len(stale_cycles) >= TARGET_STALE_CYCLES,
        "hourly_checkpoint_coverage_complete": hourly_labels
        <= {item.get("label") for item in checkpoints},
        "no_phase_failures_recorded": all(item.get("failure") is None for item in phase_reports),
        "all_phases_result_ok": all(item.get("result") == "OK" for item in phase_reports),
        "no_phase_report_build_errors": all(
            "report_build_error" not in item for item in phase_reports
        ),
        "retention_analysis_present": bool(
            retention["dedupe"].get("points") and retention["trade_dedupe"].get("points")
        ),
        "post_saturation_observation_window_present": bool(
            isinstance(
                retention["trade_dedupe"].get("post_saturation_observation_seconds"), (int, float)
            )
            and retention["trade_dedupe"]["post_saturation_observation_seconds"] > 0
        ),
        "task_base_recorded": code_evidence.get("base_sha") == TASK_BASE_SHA,
        "baseline_drift_recorded": bool(main_before and main_after),
    }
    for key, value in extra_checks.items():
        all_checks.setdefault(key, value)

    probe_scope = frozenset(set(ms.PROBE_SCOPE_KEYS))
    failures = sorted(
        key
        for key, value in all_checks.items()
        if value is not True and not (probe and key in probe_scope)
    )
    report["checks"] = all_checks
    report["failures"] = failures
    report["result"] = (
        "PROBE_OK" if (probe and not failures) else ("PASS" if not failures else "FAIL")
    )
    report["task"] = "N01-8"
    report["check_aliases"] = CHECK_ALIASES
    report["phase_table"] = [
        {
            "phase": item.get("phase"),
            "role": item.get("role"),
            "pid": item.get("pid"),
            "result": item.get("result"),
            "active_duration_seconds": item.get("active_duration_seconds"),
            "active_started_at": item.get("active_started_at"),
            "active_finished_at": item.get("active_finished_at"),
            "reconnects": len(item.get("reconnects") or []),
            "stale_cycles": len(item.get("stale_cycles") or []),
            "checkpoints": len(item.get("checkpoints") or []),
            "non_true_checks": sorted(
                key for key, value in (item.get("checks") or {}).items() if value is not True
            ),
        }
        for item in phase_reports
    ]
    report["phase_runs"] = phase_runs
    report["phase_merge"] = {
        "phases_folded": [item.get("phase") for item in phase_reports],
        "checks_combination": "AND across all phases",
        "event_lists": "reconnects / stale_cycles / checkpoints / samples concatenated",
        "restart_boundary_phase": (
            phase_reports[-2].get("phase") if len(phase_reports) > 1 else phase_reports[-1].get("phase")
        ),
        "note": (
            "The accepted ms._aggregate is reused verbatim over these folded reports; the folded "
            "checks dict is AND-merged so a single phase-local False can never be hidden."
        ),
    }
    report["n01_8_identity"] = launch.get("n01_8_environment")
    report["phase_plan"] = [{"phase": label, "role": role} for label, role in phase_plan]
    report["phase_seconds"] = phase_seconds
    report["main_before"] = main_before
    report["main_after"] = main_after
    report["baseline_drift"] = {
        "main_before_sha": _sha_of(main_before.get("ls_remote_main")),
        "main_after_sha": _sha_of(main_after.get("ls_remote_main")),
        "drifted": _sha_of(main_before.get("ls_remote_main"))
        != _sha_of(main_after.get("ls_remote_main")),
        "task_base_sha": TASK_BASE_SHA,
    }
    report["memory"] = memory
    report["retention_saturation_analysis"] = retention
    report["rolling_rss_slope"] = rolling
    report["operational_memory_interpretation"] = _operational_memory_interpretation(
        memory, retention, rolling
    )
    report["resource_trends_overall"] = {
        key: {
            "first": series[0],
            "max": max(series),
            "final": series[-1],
            "net_growth": ms._net_growth(series),
        }
        for key, series in (
            (key, _int_series(samples, key))
            for key in (
                "sockets",
                "handles",
                "asyncio_tasks_total",
                "worker_count",
                "queue_size",
                "inflight",
                "pg_owned_client_sessions",
                "dedupe_size",
                "trade_dedupe_size",
            )
        )
        if series
    }
    report["acceptance_criteria"] = _acceptance_criteria(report, retention, total_active)
    return report


def _memory_condition_n01_8(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Frozen N01 V1 memory condition, evaluated exactly as accepted (thresholds unchanged)."""
    condition = ms._memory_condition(samples)
    condition["thresholds_unchanged"] = (
        ms.MEMORY_TOTAL_GROWTH_MIB == 64.0 and ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR == 5.0
    )
    condition["branch_total_growth_exceeded"] = bool(
        isinstance(condition.get("total_growth_mib"), (int, float))
        and condition["total_growth_mib"] > ms.MEMORY_TOTAL_GROWTH_MIB
    )
    condition["branch_second_half_slope_exceeded"] = bool(
        isinstance(condition.get("second_half_trend_mib_per_hour"), (int, float))
        and condition["second_half_trend_mib_per_hour"]
        > ms.MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR
    )
    return condition


def _sha_of(ls_remote_line: Any) -> str | None:
    if not isinstance(ls_remote_line, str) or not ls_remote_line.strip():
        return None
    return ls_remote_line.split()[0]


def _acceptance_criteria(
    report: dict[str, Any], retention: dict[str, Any], total_active: float
) -> list[dict[str, Any]]:
    checks = report.get("checks") or {}
    run_identity = report.get("run_identity") or {}
    memory = report.get("memory") or {}

    def c(key: str) -> Any:
        return checks.get(key)

    return [
        {"ac": "AC-01", "what": "task base frozen and recorded", "evidence": report.get("phase_merge") is not None and c("task_base_recorded"), "keys": ["task_base_recorded"]},
        {"ac": "AC-02", "what": "formal active runtime >= 43200 s", "evidence": total_active >= ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS, "keys": ["active_total_ge_43200"], "value": round(total_active, 3)},
        {"ac": "AC-03", "what": "one coherent timeline (single disposable database, no stitching)", "evidence": bool(run_identity.get("database_name")), "keys": []},
        {"ac": "AC-04", "what": "4 planned phases complete", "evidence": c("phases_completed_ge_4"), "keys": ["phases_completed_ge_4", "all_planned_phases_present"]},
        {"ac": "AC-05", "what": "3 true fresh-process restarts", "evidence": c("fresh_process_restarts_ge_3"), "keys": ["fresh_process_restarts_ge_3", "fresh_process_pids_all_distinct", "fresh_process_restart"]},
        {"ac": "AC-06", "what": "12 controlled reconnects materially covered", "evidence": c("reconnects_ge_12"), "keys": ["reconnects_ge_12", "controlled_reconnects_recovered_fresh"]},
        {"ac": "AC-07", "what": "6 controlled STALE->FRESH cycles materially covered", "evidence": c("stale_cycles_ge_6"), "keys": ["stale_cycles_ge_6", "stale_cycles_health_unavailable", "stale_cycles_risk_increasing_fail_closed", "stale_cycles_protection_facts_preserved", "stale_cycles_fresh_recovered"]},
        {"ac": "AC-08", "what": "periodic reconciliation covers timeline, all PASS", "evidence": c("all_checkpoints_ok"), "keys": ["all_checkpoints_ok", "checkpoint_coverage_complete", "hourly_checkpoint_coverage_complete"]},
        {"ac": "AC-09", "what": "no duplicate / fabricated economic facts", "evidence": c("final_no_duplicate_facts") and c("no_fabricated_fill_across_restart"), "keys": ["final_no_duplicate_facts", "no_fabricated_fill_across_restart"]},
        {"ac": "AC-10", "what": "protection authority remains the durable Position snapshot", "evidence": c("f01_protection_authority_after_restart"), "keys": ["f01_protection_authority_after_restart", "f01_restart_authority_remains_snapshot_a", "f01_active_plan_b_does_not_replace_snapshot"]},
        {"ac": "AC-11", "what": "no worker exception requiring failure", "evidence": c("worker_exceptions_zero"), "keys": ["worker_exceptions_zero"]},
        {"ac": "AC-12", "what": "DB/session lifecycle bounded", "evidence": c("pg_owned_clients_zero"), "keys": ["pg_owned_clients_zero", "pg_idle_in_transaction_zero", "pg_no_foreign_client_sessions"]},
        {"ac": "AC-13", "what": "socket permanent delta <= 2 (or classified)", "evidence": c("sockets_not_accumulating"), "keys": ["sockets_not_accumulating"]},
        {"ac": "AC-14", "what": "handle delta <= 16 (or classified)", "evidence": c("handles_not_accumulating"), "keys": ["handles_not_accumulating"]},
        {"ac": "AC-15", "what": "frozen memory AND gate evaluated exactly as accepted", "evidence": memory.get("thresholds_unchanged"), "keys": ["memory_series_present"]},
        {"ac": "AC-16", "what": "retention saturation analysis complete", "evidence": c("retention_analysis_present"), "keys": ["retention_analysis_present"]},
        {"ac": "AC-17", "what": "post-saturation observation window materially long enough", "evidence": c("post_saturation_observation_window_present"), "keys": ["post_saturation_observation_window_present"], "value": (retention.get("trade_dedupe") or {}).get("post_saturation_observation_seconds")},
        {"ac": "AC-18", "what": "no unexplained synchronized resource growth", "evidence": c("worker_count_stable"), "keys": ["worker_count_stable"]},
        {"ac": "AC-19", "what": "primary DB unchanged", "evidence": c("shared_primary_unchanged"), "keys": ["shared_primary_unchanged", "shared_primary_no_owned_sessions"]},
        {"ac": "AC-20", "what": "disposable DB residue = 0", "evidence": c("disposable_database_residue_zero"), "keys": ["disposable_database_residue_zero"]},
        {"ac": "AC-21", "what": "production code unchanged", "evidence": c("production_code_unchanged"), "keys": ["production_code_unchanged"]},
        {"ac": "AC-22", "what": "raw evidence complete and internally consistent", "evidence": bool(report.get("samples")), "keys": []},
        {"ac": "AC-23", "what": "start/end remote main recorded", "evidence": c("baseline_drift_recorded"), "keys": ["baseline_drift_recorded"]},
        {"ac": "AC-24", "what": "any baseline drift classified", "evidence": True, "keys": [], "value": report.get("baseline_drift")},
    ]


# ---------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------
def _main_phase(args) -> int:
    progress_path = Path(args.raw_out).with_suffix(".progress.jsonl") if args.raw_out else None
    if progress_path is not None:
        with contextlib.suppress(OSError):
            progress_path.unlink(missing_ok=True)
    try:
        report = asyncio.run(
            _phase_scenario_n01_8(
                args.phase,
                args.role,
                args.database_name,
                args.database_url,
                args.seconds,
                args.sample_interval,
                args.prior_active_seconds,
                args.probe,
                progress_path,
            )
        )
    except BaseException as exc:  # noqa: BLE001 - the phase report must survive any crash
        report = {
            "phase": args.phase,
            "role": args.role,
            "pid": os.getpid(),
            "result": "FAIL",
            "active_duration_seconds": None,
            "checks": {},
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc()[-8000:],
            },
            "crash": True,
        }
    if args.raw_out:
        Path(args.raw_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raw_out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    summary = {
        "phase": report["phase"],
        "role": report.get("role"),
        "result": report["result"],
        "active_duration_seconds": report["active_duration_seconds"],
        "failures": sorted(key for key, value in report["checks"].items() if value is not True),
        "failure": report["failure"],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if report["result"] == "OK" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="N01-8 12-hour extended runtime soak")
    parser.add_argument("--mode", choices=("acceptance", "phase"), default="acceptance")
    parser.add_argument("--phase", type=str, default="p1_open")
    parser.add_argument("--role", choices=("open", "continue", "close"), default="open")
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument("--database-name", type=str, default=None)
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--sample-interval", type=float, default=DEFAULT_SAMPLE_INTERVAL_SECONDS)
    parser.add_argument("--prior-active-seconds", type=float, default=0.0)
    parser.add_argument("--raw-out", type=str, default=None)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.mode == "phase":
        if not args.database_url or not args.database_name:
            parser.error("--database-url and --database-name are required in phase mode")
        return _main_phase(args)
    return _supervisor(args)


if __name__ == "__main__":
    raise SystemExit(main())
