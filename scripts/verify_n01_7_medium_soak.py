"""N01-7 — 2-hour Medium Runtime Soak (validation-only supervisor + two-phase runtime).

Why this file exists
--------------------
N01-6 (15-minute smoke) and the first N01-7 attempt both ran the accepted runtime as a *single*
OS process. The N01-7 acceptance contract additionally requires, inside the same >= 7200 s active
window:

* >= 5 controlled reconnects (CONNECTED -> controlled disconnect -> reconnect -> FRESH again),
* >= 2 controlled STALE -> FRESH cycles,
* exactly 1 fresh-process graceful restart (Process A exits, Process B recovers from PostgreSQL
  only, with no Python memory carried over),
* reconciliation checkpoints at start / ~30 min / ~60 min / ~90 min / before restart / after
  restart / final,
* socket / handle telemetry so the reconnect cost can be shown to be non-accumulating.

None of that is a second runtime. This module is a *thin layer*:

* `scripts/verify_n01_6_runtime_smoke.py` is **imported, never copied and never edited** — every
  runtime object (`OKXLiveProvider`, `ScannerPipeline`, `OpportunityScanner`, `EventRuntime`,
  `PostgresG2Repository`, `SmokeHarness` / `LivePaperHarness`, the market consumer `_consume`,
  the disposable-database factory and the PostgreSQL ownership split) comes from it unchanged.
* `scripts/verify_n01_7_runtime_soak.py` (the first N01-7 attempt, kept as historical evidence) is
  also imported for its already-reviewed observation helpers (`_db_state`, `_f01_witness`,
  `_shared_primary_snapshot`, `_alembic_version`, `_dsn_identity`, `_okx_rest_proxy`, the window /
  memory / dedupe analyses). It is not copied either.

The ONLY new behaviour is: the supervisor that owns the disposable database and the two child
processes, the controlled-feed wrapper (reconnect / stall injection), the checkpoint schedule, the
socket/handle telemetry and the aggregation of the two phase reports.

Explicitly NOT a mitigation for a product defect
------------------------------------------------
If the soak finds a product defect the run is reported and production code is NOT touched (task
section 8). Findings are evidence, never something to patch mid-run.

Claim boundary
--------------
Even on PASS this proves only: "the accepted production runtime components, inside an N01
validation harness, were stable for >= 2 hours including one fresh-process restart". It is NOT the
Integrated Runtime Host, NOT a FastAPI 7x24 runtime, NOT a deployment, NOT N01-8, NOT N01 overall
acceptance and NOT live trading.

Run (explicit opt-in; never part of the deterministic pytest suite)::

    py -3.14 scripts/verify_n01_7_medium_soak.py --mode acceptance \
        --raw-out E:/Temp/n01-7-medium/acceptance_raw.json
    py -3.14 scripts/verify_n01_7_medium_soak.py --mode acceptance --probe   # PROBE only
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
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

# Importing the accepted harness is the whole point: it clears the sandbox proxy for this process,
# puts `backend/src` + `backend/tests` on `sys.path`, and re-exports the accepted N01-B helpers.
import verify_n01_6_runtime_smoke as n6
import verify_n01_7_runtime_soak as soak  # the first N01-7 attempt; reuse only, never modified
from marketpulse.db.models import RuntimeControlRecord
from marketpulse.g4.models import HealthComponent
from marketpulse.g4.planning import load_active_plan, resolve_open_position_protection
from marketpulse.g4.reconciliation import reconcile
from marketpulse.g4.recovery import RecoveryManager
from sqlalchemy import select

RUN_MODE = n6.RUN_MODE
BTC = n6.BTC
ETH = n6.ETH
INSTRUMENTS = n6.INSTRUMENTS

DEFAULT_RAW_OUT = "E:/Temp/n01-7-medium/acceptance_raw.json"

# ---------------------------------------------------------------------------------------------
# Acceptance parameters (declared BEFORE the run so the verdict is not fitted afterwards)
# ---------------------------------------------------------------------------------------------
ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS = 7200.0
PROBE_PHASE_SECONDS = 150.0
DEFAULT_FIRST_PHASE_SECONDS = 3600.0
DEFAULT_SECOND_PHASE_SECONDS = 3720.0
DEFAULT_SAMPLE_INTERVAL_SECONDS = 10.0

TARGET_RECONNECTS = 5
TARGET_STALE_CYCLES = 2

# Controlled stall: withhold market-event delivery, then drive the production market-data entry
# point with the last real (by then genuinely stale) quote -- exactly what a late-delivered quote
# does. Far outside the production 5.0 s freshness TTL.
STALE_HOLD_SECONDS = 60.0
STALE_SETTLE_MAX_WAIT_SECONDS = 90.0
RECONNECT_REOPEN_MAX_WAIT_SECONDS = 30.0
RECONNECT_SETTLE_SECONDS = 25.0
RECONNECT_FRESH_MAX_WAIT_SECONDS = 60.0

# Section 23 gate: after the reconnects the process resource counts must be back in a stable band.
MAX_PERMANENT_SOCKET_DELTA = 2
MAX_PERMANENT_HANDLE_DELTA = 16

# Section 21, accepted N01 V1 memory condition: BOTH must hold (a spike alone is not a finding).
MEMORY_TOTAL_GROWTH_MIB = 64.0
MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR = 5.0

# Checks a short PROBE cannot satisfy: reported, but excluded from the PROBE failure list.
PROBE_SCOPE_KEYS = frozenset(
    {
        "active_total_ge_7200",
        "reconnects_ge_5",
        "stale_cycles_ge_2",
        "checkpoint_coverage_complete",
        "all_checkpoints_ok",
        "controlled_reconnects_recovered_fresh",
        "stale_cycles_health_unavailable",
        "stale_cycles_risk_increasing_fail_closed",
        "stale_cycles_no_economic_fact",
        "stale_cycles_protection_facts_preserved",
        "stale_cycles_fresh_recovered",
        "stale_cycles_fresh_protection_hold",
        "stale_cycles_reconciliation_ok",
        "f01_protection_authority_after_restart",
        "f01_authority_identity_matches_durable_plan",
        "f01_protection_service_resolves_snapshot_after_restart",
        "f01_plan_ttl_expired_while_position_open",
        "f01_durable_snapshot_present_after_ttl",
        "f01_snapshot_matches_originating_plan",
        "f01_witness_harness_ok",
        "memory_series_present",
        "worker_count_stable",
        "sockets_not_accumulating",
        "handles_not_accumulating",
    }
)

OKX_REST_PROXY_ENV = soak.OKX_REST_PROXY_ENV

# Accepted main at task base; used to prove production code was never touched.
TASK_BASE_SHA = "71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f"
PRODUCTION_PATHS = ("backend/src", "backend/alembic", "backend/tests", "frontend")


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(UTC)


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(REPOSITORY_ROOT),
        check=False,
    )
    return completed.stdout.strip()


def _code_freeze_evidence() -> dict[str, Any]:
    """Real git evidence that production code, migrations and accepted tests are untouched.

    Never hard-coded: the verdict is derived from `git diff` / `git status` against the
    accepted base SHA, so an accidental production edit fails the run instead of being hidden.
    """
    diff_stat = _git(["diff", "--stat", TASK_BASE_SHA, "--", *PRODUCTION_PATHS])
    status = _git(["status", "--porcelain", "--", *PRODUCTION_PATHS])
    return {
        "base_sha": TASK_BASE_SHA,
        "head_sha": _git(["rev-parse", "HEAD"]),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "production_diff_stat": diff_stat,
        "production_status_porcelain": status,
        "production_frozen": diff_stat == "" and status == "",
    }


def _proc_resources() -> dict[str, Any]:
    """Process-level resource telemetry (sections 13/23). Never fabricated: failures recorded."""
    out: dict[str, Any] = {}
    process = getattr(n6, "_PROCESS", None)
    if process is None:
        out["psutil_available"] = False
    else:
        out["psutil_available"] = True
        try:
            out["handles"] = process.num_handles()
        except Exception as exc:  # noqa: BLE001 - recorded, never invented
            out["handles"] = None
            out["handles_error"] = type(exc).__name__
        try:
            connections = process.net_connections(kind="inet")
            out["sockets"] = len(connections)
            out["socket_statuses"] = sorted({str(item.status) for item in connections})
        except Exception as exc:  # noqa: BLE001 - recorded, never invented
            out["sockets"] = None
            out["sockets_error"] = type(exc).__name__
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    owned = sorted(
        task.get_name()
        for task in tasks
        if task.get_name().startswith(("g2-event-worker-", "n01-7-"))
    )
    out["asyncio_tasks_total"] = len(tasks)
    out["n01_owned_task_count"] = len(owned)
    out["n01_owned_tasks"] = owned
    return out


def _delta(after: Any, before: Any) -> int | None:
    if isinstance(after, int) and isinstance(before, int):
        return after - before
    return None


async def _checkpoint(label: str, ctx: dict[str, Any], harness, sessions) -> dict[str, Any]:
    """Read-only reconciliation checkpoint. Detector only; never repairs anything."""
    elapsed = round(time.monotonic() - ctx["active_started_monotonic"], 3)
    report = await reconcile(
        RUN_MODE,
        sessions=sessions,
        execution=harness.execution,
        now=harness.clock.now(),
        clock=harness.clock,
    )
    entry = {
        "label": label,
        "phase": ctx["phase"],
        "at": _now().isoformat(),
        "phase_elapsed_seconds": elapsed,
        "absolute_elapsed_seconds": round(ctx.get("prior_active_seconds", 0.0) + elapsed, 3),
        "ok": report.ok,
        "diagnostics": list(report.diagnostics),
        "invariants": dict(report.invariants),
    }
    ctx["checkpoints"].append(entry)
    return entry


# ---------------------------------------------------------------------------------------------
# Controlled market-data stream: reconnect + stall injection (validation-only)
# ---------------------------------------------------------------------------------------------
class _ControlledStream:
    """Wrap the accepted provider stream so reconnect / stall can be driven deterministically.

    The transport itself is untouched: a controlled reconnect closes the current async generator
    (which exits `websockets.connect`, and therefore the real WebSocket) and opens a new one, so
    the provider performs a genuine connect. A controlled stall withholds *delivery* of received
    events, which is what a delivery-layer market-data stall looks like to the consumer.
    """

    def __init__(self, provider, channels) -> None:
        self._provider = provider
        self._channels = list(channels)
        self._reconnect_requests = 0
        self._stopping = False
        self.stale = False
        self.withheld_events = 0
        self.last_withheld: dict[str, Any] = {}
        self.reconnects_performed = 0
        self.generator_reopens = 0

    def request_reconnect(self) -> None:
        self._reconnect_requests += 1

    def set_stale(self, value: bool) -> None:
        self.stale = value

    def stop(self) -> None:
        self._stopping = True

    async def events(self):
        while True:
            generator = self._provider.stream(self._channels)
            self.generator_reopens += 1
            try:
                async for event in generator:
                    if self.stale:
                        self.withheld_events += 1
                        if isinstance(event, n6.NormalizedBookTicker):
                            self.last_withheld[event.instrument_id] = event
                        continue
                    yield event
                    if self._reconnect_requests > 0:
                        self._reconnect_requests -= 1
                        self.reconnects_performed += 1
                        break
            finally:
                # Closing the async generator must never mask the run outcome.
                with contextlib.suppress(Exception):
                    await generator.aclose()
            if self._stopping:
                return
            await asyncio.sleep(1.0)

    def snapshot(self) -> dict[str, Any]:
        return {
            "reconnects_performed": self.reconnects_performed,
            "reconnect_requests_pending": self._reconnect_requests,
            "generator_reopens": self.generator_reopens,
            "stale_active": self.stale,
            "withheld_events": self.withheld_events,
        }


# ---------------------------------------------------------------------------------------------
# Controlled reconnect (sections 14 / 23)
# ---------------------------------------------------------------------------------------------
async def _controlled_reconnect(
    index: int,
    controlled: _ControlledStream,
    harness,
    sessions,
    feed: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """CONNECTED -> controlled disconnect -> reconnect -> FRESH event again, then settle."""
    evidence: dict[str, Any] = {
        "index": index,
        "phase": ctx["phase"],
        "at": _now().isoformat(),
        "phase_elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
    }
    before_events = feed["total_normalized_events"]
    before_reopens = controlled.generator_reopens
    before_attempts = ctx["provider"].connection_attempts
    before_resources = _proc_resources()
    evidence["before"] = {
        "total_events": before_events,
        "provider_connection_attempts": before_attempts,
        "resources": before_resources,
    }

    controlled.request_reconnect()
    deadline = time.monotonic() + RECONNECT_REOPEN_MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        if controlled.generator_reopens > before_reopens:
            break
        await asyncio.sleep(0.5)
    evidence["disconnect_observed"] = controlled.generator_reopens > before_reopens
    evidence["reconnects_performed"] = controlled.reconnects_performed
    evidence["provider_connection_attempts_after"] = ctx["provider"].connection_attempts
    evidence["provider_reconnects_counter"] = ctx["provider"].reconnects

    # A reconnect alone is not enough: the re-established feed must deliver a new event.
    fresh_deadline = time.monotonic() + RECONNECT_FRESH_MAX_WAIT_SECONDS
    got_fresh = False
    while time.monotonic() < fresh_deadline:
        if feed["total_normalized_events"] > before_events and all(
            item in feed["latest_bbo"] for item in INSTRUMENTS
        ):
            got_fresh = True
            break
        await asyncio.sleep(0.5)
    evidence["fresh_event_after_reconnect"] = got_fresh
    evidence["events_delta"] = feed["total_normalized_events"] - before_events

    await asyncio.sleep(RECONNECT_SETTLE_SECONDS)
    settle_state = await soak._db_state(sessions)
    after_resources = _proc_resources()
    evidence["settle"] = {
        "at": _now().isoformat(),
        "queue_size": ctx["runtime"].queue.qsize(),
        "queue_capacity": ctx["runtime"].queue.maxsize,
        "inflight": len(ctx["runtime"]._inflight),
        "worker_count": len(ctx["runtime"]._workers),
        "worker_exceptions": len(ctx["runtime"].worker_exceptions),
        "dedupe_size": len(ctx["runtime"]._dedupe),
        "trade_dedupe_size": len(ctx["pipeline"]._trade_dedupe),
        "pg_owned_client_sessions": (ctx.get("last_activity") or {}).get("owned_client_sessions"),
        "system_state": settle_state["system_state"],
        "operator_state": settle_state["operator_state"],
        "resources": after_resources,
    }
    evidence["socket_delta_vs_before"] = _delta(
        after_resources.get("sockets"), before_resources.get("sockets")
    )
    evidence["handle_delta_vs_before"] = _delta(
        after_resources.get("handles"), before_resources.get("handles")
    )
    report = await reconcile(
        RUN_MODE,
        sessions=sessions,
        execution=harness.execution,
        now=harness.clock.now(),
        clock=harness.clock,
    )
    evidence["reconciliation_ok"] = report.ok is True
    evidence["reconciliation_diagnostics"] = list(report.diagnostics)
    return evidence


# ---------------------------------------------------------------------------------------------
# Controlled STALE -> FRESH (sections 15 / 19)
# ---------------------------------------------------------------------------------------------
def _protection_identity(state: dict[str, Any] | None) -> dict[str, Any]:
    protection = (state or {}).get("protection") or {}
    return {
        "present": protection.get("present"),
        "plan_id": protection.get("protection_plan_id"),
        "plan_version": protection.get("protection_plan_version"),
        "stop_loss": protection.get("protection_stop_loss"),
        "take_profit": protection.get("protection_take_profit"),
    }


async def _stale_fresh_cycle(
    index: int,
    controlled: _ControlledStream,
    harness,
    sessions,
    feed: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """Withhold delivery, drive the production market-data path with the (now stale) real quote,
    prove fail-closed behaviour, then let live delivery restore freshness naturally."""
    evidence: dict[str, Any] = {
        "index": index,
        "phase": ctx["phase"],
        "at": _now().isoformat(),
        "phase_elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
    }
    entry_plan_id = ctx.get("entry_plan_id")
    counts_before = await n6._economic_counts(sessions, RUN_MODE)
    state_before = await soak._db_state(sessions)
    evidence["health_before"] = harness.health.status(HealthComponent.CORE_MARKET_DATA.value)
    evidence["counts_before"] = counts_before

    # Pre-stall contrast: the same admission call, on fresh data, for the same plan.
    if entry_plan_id:
        admitted_before, reason_before = await harness.risk_gate.check(
            RUN_MODE, BTC, plan_id=entry_plan_id
        )
        evidence["risk_gate_before_stall"] = {
            "admitted": admitted_before,
            "reason": reason_before,
        }

    controlled.set_stale(True)
    stall_started = time.monotonic()
    await asyncio.sleep(STALE_HOLD_SECONDS)
    evidence["stall_seconds"] = round(time.monotonic() - stall_started, 3)
    evidence["withheld_events"] = controlled.withheld_events

    last_event = controlled.last_withheld.get(BTC)
    if last_event is None:
        evidence["harness_error"] = "no_withheld_btc_bbos_to_drive_staleness"
        controlled.set_stale(False)
        return evidence
    stale_bbo = n6._to_bbo(last_event)
    evidence["stale_quote"] = {
        "bid": stale_bbo.bid,
        "ask": stale_bbo.ask,
        "received_at": stale_bbo.received_at.isoformat(),
        "age_seconds": round((_now() - stale_bbo.received_at).total_seconds(), 3),
    }

    # Production market-data entry point (SafetyRuntime.on_market_data) with a genuinely late quote.
    outcome = await harness.feed_market_data(stale_bbo)
    protection = outcome.get("protection")
    evidence["stale"] = {
        "health_status": harness.health.status(HealthComponent.CORE_MARKET_DATA.value),
        "fresh_flag": outcome.get("fresh"),
        "protection_triggered": getattr(protection, "triggered", None),
        "protection_reason": getattr(protection, "reason", None),
        "protection_fill_id": getattr(protection, "fill_id", None),
    }
    evidence["state_during_stall"] = await soak._db_state(sessions)

    # Fail-closed: a risk-increasing action must be refused while market data is stale.
    if entry_plan_id:
        admitted_stale, reason_stale = await harness.risk_gate.check(
            RUN_MODE, BTC, plan_id=entry_plan_id
        )
        evidence["risk_gate_during_stall"] = {
            "admitted": admitted_stale,
            "reason": reason_stale,
        }
        async with sessions() as session:
            plan = await load_active_plan(session, RUN_MODE, BTC)
        if plan is not None and plan.plan_id == entry_plan_id:
            attempt = await harness.execute_intent(plan, tag=f"stale-probe-{ctx['phase']}-{index}")
            evidence["execute_intent_during_stall"] = {
                "status": str(attempt.status),
                "reason": attempt.reason,
            }
        else:
            evidence["execute_intent_during_stall"] = {
                "skipped": "durable_active_plan_unavailable",
                "loaded_plan_id": None if plan is None else plan.plan_id,
            }
    evidence["counts_after_stall"] = await n6._economic_counts(sessions, RUN_MODE)
    evidence["no_economic_fact_during_stall"] = evidence["counts_after_stall"] == counts_before
    evidence["protection_facts_preserved"] = _protection_identity(
        state_before
    ) == _protection_identity(evidence["state_during_stall"])

    # End the stall: live delivery resumes. Freshness must be restored by the production path.
    controlled.set_stale(False)
    recovered = await n6._wait_until(
        lambda: (
            harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
            and BTC in feed["latest_bbo"]
            and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
            <= n6.FRESH_QUOTE_MAX_AGE_SECONDS
        ),
        timeout=STALE_SETTLE_MAX_WAIT_SECONDS,
    )
    evidence["fresh_recovered"] = recovered
    fresh_outcome = None
    if recovered:
        fresh_bbo = feed["latest_bbo"][BTC]
        harness.publish_quote(fresh_bbo)
        fresh_outcome = await harness.protection.evaluate(
            RUN_MODE, BTC, fresh_bbo, now=harness.clock.now()
        )
    evidence["fresh"] = {
        "health_status": harness.health.status(HealthComponent.CORE_MARKET_DATA.value),
        "protection_triggered": getattr(fresh_outcome, "triggered", None),
        "protection_reason": getattr(fresh_outcome, "reason", None),
    }
    report = await reconcile(
        RUN_MODE,
        sessions=sessions,
        execution=harness.execution,
        now=harness.clock.now(),
        clock=harness.clock,
    )
    evidence["reconciliation_ok"] = report.ok is True
    evidence["reconciliation_diagnostics"] = list(report.diagnostics)
    return evidence


# ---------------------------------------------------------------------------------------------
# Phase schedule
# ---------------------------------------------------------------------------------------------
def _schedule(phase: str, active_seconds: float, probe: bool) -> list[dict[str, Any]]:
    if probe:
        return [
            {"kind": "reconnect", "at": max(10.0, active_seconds * 0.20), "index": 1},
            {"kind": "stale", "at": max(16.0, active_seconds * 0.35), "index": 1},
            {"kind": "reconnect", "at": max(24.0, active_seconds * 0.60), "index": 2},
            {
                "kind": "checkpoint",
                "at": max(30.0, active_seconds * 0.85),
                "label": f"{phase}_late",
            },
        ]
    if phase == "first":
        return [
            {"kind": "reconnect", "at": 300.0, "index": 1},
            {"kind": "stale", "at": 900.0, "index": 1},
            {"kind": "reconnect", "at": 1200.0, "index": 2},
            {"kind": "reconnect", "at": 2400.0, "index": 3},
            {"kind": "checkpoint", "at": 1800.0, "label": "abs_30m"},
            {"kind": "checkpoint", "at": 3540.0, "label": "before_restart"},
        ]
    return [
        {"kind": "reconnect", "at": 600.0, "index": 4},
        {"kind": "stale", "at": 1200.0, "index": 2},
        {"kind": "reconnect", "at": 2400.0, "index": 5},
        {"kind": "checkpoint", "at": 1740.0, "label": "abs_90m"},
    ]


# ---------------------------------------------------------------------------------------------
# Phase scenario (runs inside a child OS process)
# ---------------------------------------------------------------------------------------------
async def _phase_scenario(
    phase: str,
    database_name: str,
    database_url: str,
    active_seconds: float,
    sample_interval: float,
    prior_active_seconds: float,
    probe: bool,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure: dict[str, Any] | None = None
    feed = n6._new_feed()
    samples: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {
        "phase": phase,
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
    controlled: _ControlledStream | None = None
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

        controlled = _ControlledStream(provider, n6.CHANNELS)
        ctx["controlled"] = controlled
        stream = controlled.events()
        ctx["stream"] = stream

        if phase == "first":
            await harness.boot()
            await runtime.start()
            consumer = asyncio.create_task(
                n6._consume(stream, pipeline, harness, feed), name="n01-7ms-market-consumer"
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
            # A fresh process must NOT force RUNNING: PostgreSQL recovery owns that transition.
            await harness.state_service.ensure(RUN_MODE)

            # Warm-up: pull real events until both instruments have a live BBO, so recovery has a
            # genuine fresh quote. These events are counted and discarded -- never replayed.
            warmup_started = time.monotonic()
            warmup_events = 0
            while not all(item in harness.quotes for item in INSTRUMENTS):
                if time.monotonic() - warmup_started > n6.INITIAL_DATA_MAX_WAIT_SECONDS:
                    raise AssertionError("phase second warm-up never produced a live BBO")
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

            # --- fresh-process, PostgreSQL-only recovery (section 17)
            recovery_started = time.monotonic()

            async def _reconcile_for_recovery(run_mode):
                return await reconcile(
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

            # The runtime event-processing path only resumes *after* PostgreSQL recovery, with the
            # same live stream that the warm-up was reading from.
            await runtime.start()
            consumer = asyncio.create_task(
                n6._consume(stream, pipeline, harness, feed), name="n01-7ms-market-consumer"
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
                "phase": phase,
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
                **_proc_resources(),
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
                            "message": f"n01-7ms-sampler: {exc}",
                        }
                    )
                await asyncio.sleep(sample_interval)

        await sample_once()
        sampler = asyncio.create_task(sample_loop(), name="n01-7ms-sampler")
        ctx["sampler"] = sampler

        # --- boundary checkpoint
        await _checkpoint("after_restart" if phase == "second" else "start", ctx, harness, sessions)

        schedule = _schedule(phase, active_seconds, probe)
        entry_offset = min(60.0, max(10.0, active_seconds * 0.10))
        entry_done = phase == "second"
        pending = sorted(schedule, key=lambda item: item["at"])
        expiry_crossed = False
        witness_at: float | None = None

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
                ctx["entry_plan_version"] = ctx["entry"]["plan"]["plan_version"]
                entry_done = True

            while pending and elapsed >= pending[0]["at"]:
                item = pending.pop(0)
                if item["kind"] == "reconnect":
                    ctx["reconnects"].append(
                        await _controlled_reconnect(
                            item["index"], controlled, harness, sessions, feed, ctx
                        )
                    )
                elif item["kind"] == "stale":
                    ctx["stale_cycles"].append(
                        await _stale_fresh_cycle(
                            item["index"], controlled, harness, sessions, feed, ctx
                        )
                    )
                elif item["kind"] == "checkpoint":
                    await _checkpoint(item["label"], ctx, harness, sessions)

            if entry_done and not probe and phase == "first":
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

            if elapsed >= active_seconds:
                break
            await asyncio.sleep(0.5)

        ctx["active_duration_seconds"] = time.monotonic() - ctx["active_started_monotonic"]
        ctx["active_finished_at"] = _now()
        if phase == "first":
            checks["controlled_entry_performed"] = "entry" in ctx
            if not entry_done:
                raise AssertionError("controlled entry never executed during the active window")
            await _checkpoint("final_before_stop", ctx, harness, sessions)
        else:
            # --- section 19 witness C, after the restart: authority must still come from the
            # durable position snapshot, never re-derived from a plan, an AI or transient memory.
            ctx["f01_after_restart"] = await _protection_authority_after_restart(
                harness, sessions, ctx, checks
            )
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
            if task.get_name().startswith(("g2-event-worker-", "n01-7")) and not task.done()
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
        ctx["runtime_control_at_stop"] = await _runtime_control(sessions)

        if phase == "second":
            await _final_assertions(ctx, harness, sessions, checks)
        else:
            # Phase first deliberately leaves the position OPEN and the snapshot in place.
            checks["phase_first_position_left_open"] = bool(
                (ctx["durable_state_at_stop"].get("position_quantity") or 0.0) > 0.0
            )
            checks["phase_first_protection_snapshot_left_in_place"] = bool(
                (ctx["durable_state_at_stop"].get("protection") or {}).get("present")
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
        return _build_phase_report(phase, ctx, checks, failure, provider, feed)
    except Exception as exc:  # noqa: BLE001 - a report bug must never hide the verdict
        return {
            "phase": phase,
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


async def _protection_authority_after_restart(
    harness, sessions, ctx: dict[str, Any], checks: dict[str, bool]
) -> dict[str, Any]:
    """Section 19 witness C: after a fresh-process restart the protection authority is still the
    durable position snapshot -- not a plan, not an active plan, not transient memory."""
    evidence: dict[str, Any] = {"observed_at": _now().isoformat()}
    position = await n6._position(sessions, RUN_MODE, BTC)
    authority = resolve_open_position_protection(position) if position is not None else None
    async with sessions() as session:
        plan = await load_active_plan(session, RUN_MODE, BTC)
    evidence["position_quantity"] = position.quantity if position is not None else None
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
    evidence["durable_active_plan"] = (
        None
        if plan is None
        else {
            "plan_id": plan.plan_id,
            "plan_version": plan.plan_version,
            "expired": harness.clock.now() >= plan.expires_at,
        }
    )
    evidence["state"] = await soak._db_state(sessions)
    outcome = None
    if BTC in harness.quotes:
        outcome = await harness.protection.evaluate(
            RUN_MODE, BTC, harness.quotes[BTC], now=harness.clock.now()
        )
    evidence["evaluate"] = (
        None
        if outcome is None
        else {
            "triggered": outcome.triggered,
            "reason": outcome.reason,
            "trigger": str(outcome.trigger),
        }
    )
    durable_plan = evidence["durable_active_plan"]
    checks["f01_restart_authority_from_durable_snapshot"] = bool(
        authority is not None
        and authority.plan_id is not None
        and authority.plan_version is not None
        and authority.stop_loss is not None
        and authority.take_profit is not None
    )
    checks["f01_restart_authority_not_from_active_plan"] = bool(
        authority is not None
        and durable_plan is not None
        and authority.plan_id == durable_plan["plan_id"]
        and authority.plan_version == durable_plan["plan_version"]
    )
    checks["f01_restart_protection_service_resolves_snapshot"] = bool(
        outcome is not None and outcome.triggered is False and outcome.reason == "HOLD"
    )
    return evidence


async def _runtime_control(sessions) -> dict[str, Any]:

    async with sessions() as session:
        record = await session.scalar(
            select(RuntimeControlRecord).where(RuntimeControlRecord.run_mode == RUN_MODE)
        )
    if record is None:
        return {}
    return {
        "operator_state": record.operator_state,
        "system_state": record.system_state,
        "runtime_version": record.runtime_version,
        "reason": record.reason,
        "heartbeat_at": record.heartbeat_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


async def _final_assertions(ctx, harness, sessions, checks: dict[str, bool]) -> None:
    """Sections 18/25: flat position, economic invariants, no duplicate/fabricated facts."""
    counts_final = await n6._economic_counts(sessions, RUN_MODE)
    account_final = await n6._account(sessions)
    position_final = await n6._position(sessions, RUN_MODE, BTC)
    ctx["counts_final"] = counts_final
    ctx["account_final"] = account_final
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
    ctx["open_buys_final"] = await n6.count_open_buys(sessions, RUN_MODE)
    ctx["sell_fills"] = [fill.fill_id for fill in await n6._sell_fills(sessions, RUN_MODE)]
    ctx["trade_final"] = await n6._trade(sessions)
    ctx["fills_final"] = await n6._fill_facts(sessions)

    report = await reconcile(
        RUN_MODE,
        sessions=sessions,
        execution=harness.execution,
        now=harness.clock.now(),
        clock=harness.clock,
    )
    ctx["checkpoints"].append(
        {
            "label": "final",
            "phase": ctx["phase"],
            "at": _now().isoformat(),
            "phase_elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
            "absolute_elapsed_seconds": round(
                ctx.get("prior_active_seconds", 0.0)
                + (time.monotonic() - ctx["active_started_monotonic"]),
                3,
            ),
            "ok": report.ok,
            "diagnostics": list(report.diagnostics),
            "invariants": dict(report.invariants),
        }
    )
    ctx["reconciliation"] = report
    checks["reconciliation_ok"] = report.ok is True
    checks["final_position_flat"] = ctx["position_final"]["quantity"] == 0.0
    checks["final_no_open_buy"] = ctx["open_buys_final"] == 0
    checks["final_exactly_one_exit_fill"] = len(ctx["sell_fills"]) == 1
    checks["final_single_trade_lifecycle"] = bool(
        ctx["trade_final"] is not None and ctx["trade_final"]["status"] == "CLOSED"
    )
    checks["final_no_duplicate_facts"] = (
        counts_final["orders"] == 2
        and counts_final["fills"] == 2
        and counts_final["positions"] == 1
    )
    checks["final_reserved_cash_zero"] = bool(account_final and account_final["reserved_cash"] == 0)
    checks["final_cash_non_negative"] = bool(account_final and account_final["cash_balance"] >= 0)
    checks["final_protection_snapshot_cleared_when_flat"] = (
        ctx["position_final"]["protection_present"] is False
        and ctx["position_final"]["protection_plan_id"] is None
    )


# ---------------------------------------------------------------------------------------------
# Per-phase report
# ---------------------------------------------------------------------------------------------
def _build_phase_report(phase, ctx, checks, failure, provider, feed) -> dict[str, Any]:
    return {
        "phase": phase,
        "pid": ctx.get("pid"),
        "result": "FAIL" if failure is not None else "OK",
        "active_duration_seconds": ctx.get("active_duration_seconds"),
        "active_started_at": (
            ctx["active_started_at"].isoformat() if ctx.get("active_started_at") else None
        ),
        "active_finished_at": (
            ctx["active_finished_at"].isoformat() if ctx.get("active_finished_at") else None
        ),
        "process_started_at": ctx.get("process_started_at"),
        "process_exited_at": ctx.get("process_exited_at"),
        "prior_active_seconds": ctx.get("prior_active_seconds"),
        "dsn": ctx.get("dsn"),
        "metadata": ctx.get("metadata"),
        "okx_rest_transport": ctx.get("okx_rest_transport"),
        "warmup": ctx.get("warmup"),
        "recovery": ctx.get("recovery"),
        "recovered_position": ctx.get("recovered_position"),
        "recovered_account": ctx.get("recovered_account"),
        "recovered_counts": ctx.get("recovered_counts"),
        "recovered_plan": ctx.get("recovered_plan"),
        "entry": ctx.get("entry"),
        "entry_plan_id": ctx.get("entry_plan_id"),
        "entry_plan_version": ctx.get("entry_plan_version"),
        "expiry_crossed_at": ctx.get("expiry_crossed_at"),
        "expiry_crossed_elapsed_seconds": ctx.get("expiry_crossed_elapsed_seconds"),
        "f01": ctx.get("f01"),
        "f01_elapsed_seconds": ctx.get("f01_elapsed_seconds"),
        "f01_after_restart": ctx.get("f01_after_restart"),
        "exit": ctx.get("exit"),
        "checkpoints": ctx.get("checkpoints"),
        "reconnects": ctx.get("reconnects"),
        "stale_cycles": ctx.get("stale_cycles"),
        "controlled": None if ctx.get("controlled") is None else ctx["controlled"].snapshot(),
        "durable_state_at_stop": ctx.get("durable_state_at_stop"),
        "runtime_control_at_stop": ctx.get("runtime_control_at_stop"),
        "counts_at_stop": ctx.get("counts_at_stop"),
        "account_at_stop": ctx.get("account_at_stop"),
        "counts_final": ctx.get("counts_final"),
        "account_final": ctx.get("account_final"),
        "position_final": ctx.get("position_final"),
        "open_buys_final": ctx.get("open_buys_final"),
        "sell_fills": ctx.get("sell_fills"),
        "trade_final": ctx.get("trade_final"),
        "fills_final": ctx.get("fills_final"),
        "reconciliation": (
            None
            if ctx.get("reconciliation") is None
            else {
                "ok": ctx["reconciliation"].ok,
                "diagnostics": list(ctx["reconciliation"].diagnostics),
                "invariants": dict(ctx["reconciliation"].invariants),
            }
        ),
        "okx": {
            "connection_attempts": provider.connection_attempts,
            "provider_reconnects": provider.reconnects,
            "trades": dict(feed["trades"]),
            "bbos": dict(feed["bbos"]),
            "total_normalized_events": feed["total_normalized_events"],
            "first_received": feed["first_received"],
            "last_received": feed["last_received"],
            "max_inter_arrival_gap_seconds": feed["max_inter_arrival_gap_seconds"],
            "health_transitions": feed["health_transitions"],
            "stale_periods": feed["stale_periods"],
        },
        "rss": {"start": ctx.get("rss_start"), "end": ctx.get("rss_end")},
        "shutdown": {
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_tasks_final": ctx.get("worker_tasks_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
            "background_tasks": ctx.get("background_tasks"),
            "cleanup": (
                None
                if ctx.get("cleanup") is None
                else {
                    "released": ctx["cleanup"].released,
                    "elapsed_seconds": ctx["cleanup"].elapsed_seconds,
                    "polls": ctx["cleanup"].polls,
                    "first_client_sessions": ctx["cleanup"].first_snapshot.client_sessions,
                    "final_client_sessions": ctx["cleanup"].final_snapshot.client_sessions,
                    "final_server_sessions": ctx["cleanup"].final_snapshot.server_sessions,
                    "final_idle_in_transaction": (
                        ctx["cleanup"].final_snapshot.idle_in_transaction
                    ),
                    "foreign_rows": list(ctx["cleanup"].foreign_rows),
                    "transients": len(ctx["cleanup"].transients),
                }
            ),
            "errors": ctx.get("shutdown_errors", []),
        },
        "harness_errors": feed["errors"][:100],
        "checks": checks,
        "failure": failure,
        "samples": ctx.get("samples", []),
    }


# ---------------------------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------------------------
def _child_command(
    phase: str,
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
        phase,
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


def _run_child(command: list[str], timeout: float, log_path: Path) -> dict[str, Any]:
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy(),
            cwd=str(REPOSITORY_ROOT),
        )
        returncode = process.wait(timeout=timeout)
    return {"returncode": returncode, "pid": process.pid, "log": str(log_path)}


def _supervisor(args) -> int:
    raw_out = Path(args.raw_out or DEFAULT_RAW_OUT)
    log_dir = raw_out.parent / "n01-7-medium-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.seconds:
        first_seconds = second_seconds = args.seconds
    elif args.probe:
        first_seconds = second_seconds = PROBE_PHASE_SECONDS
    else:
        first_seconds = DEFAULT_FIRST_PHASE_SECONDS
        second_seconds = DEFAULT_SECOND_PHASE_SECONDS
    mode = "PROBE" if args.probe else "ACCEPTANCE"

    started = _now()
    shared_before = asyncio.run(soak._shared_primary_snapshot(soak.SHARED_PRIMARY_URL))
    phase_process_errors: list[dict[str, Any]] = []

    with n6._disposable_postgres_database() as (database_name, database_url):
        revision = asyncio.run(soak._alembic_version(database_url))
        first_raw = log_dir / "phase_first_raw.json"
        second_raw = log_dir / "phase_second_raw.json"
        first_run = _run_child(
            _child_command(
                "first",
                database_url,
                database_name,
                first_seconds,
                args.sample_interval,
                0.0,
                args.probe,
                first_raw,
            ),
            timeout=first_seconds + 1200.0,
            log_path=log_dir / "phase_first.stdout.txt",
        )
        first = json.loads(first_raw.read_text(encoding="utf-8")) if first_raw.exists() else None
        prior_active = 0.0
        if first is not None and first.get("active_duration_seconds"):
            prior_active = float(first["active_duration_seconds"])
        if first_run["returncode"] != 0:
            phase_process_errors.append(
                {
                    "step": "phase_first_process",
                    "returncode": first_run["returncode"],
                    "log": first_run["log"],
                }
            )
        second_run = _run_child(
            _child_command(
                "second",
                database_url,
                database_name,
                second_seconds,
                args.sample_interval,
                prior_active,
                args.probe,
                second_raw,
            ),
            timeout=second_seconds + 1200.0,
            log_path=log_dir / "phase_second.stdout.txt",
        )
        second = json.loads(second_raw.read_text(encoding="utf-8")) if second_raw.exists() else None
        if second_run["returncode"] != 0:
            phase_process_errors.append(
                {
                    "step": "phase_second_process",
                    "returncode": second_run["returncode"],
                    "log": second_run["log"],
                }
            )

    shared_after = asyncio.run(soak._shared_primary_snapshot(soak.SHARED_PRIMARY_URL))
    leftover = asyncio.run(n6._n01_6_leftover_databases())
    finished = _now()

    if first is None or second is None:
        report = {
            "task": "N01-7",
            "mode": mode,
            "result": "FAIL",
            "reason": "a child phase produced no report",
            "phase_process_errors": phase_process_errors,
            "database_name": database_name,
        }
        return _emit(report, raw_out)

    report = _aggregate(
        mode=mode,
        database_name=database_name,
        database_url=database_url,
        revision=revision,
        first=first,
        second=second,
        shared_before=shared_before,
        shared_after=shared_after,
        leftover=leftover,
        started=started,
        finished=finished,
        probe=args.probe,
        phase_process_errors=phase_process_errors,
        code_evidence=_code_freeze_evidence(),
    )
    return _emit(report, raw_out)


def _aggregate(
    *,
    mode: str,
    database_name: str,
    database_url: str,
    revision: str | None,
    first: dict[str, Any],
    second: dict[str, Any],
    shared_before: dict[str, Any],
    shared_after: dict[str, Any],
    leftover: int,
    started: datetime,
    finished: datetime,
    probe: bool,
    phase_process_errors: list[dict[str, Any]],
    code_evidence: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    first_checks = dict(first.get("checks") or {})
    second_checks = dict(second.get("checks") or {})

    active_first = float(first.get("active_duration_seconds") or 0.0)
    active_second = float(second.get("active_duration_seconds") or 0.0)
    total_active = active_first + active_second

    reconnects = (first.get("reconnects") or []) + (second.get("reconnects") or [])
    stale_cycles = (first.get("stale_cycles") or []) + (second.get("stale_cycles") or [])
    checkpoints = (first.get("checkpoints") or []) + (second.get("checkpoints") or [])
    samples = (first.get("samples") or []) + (second.get("samples") or [])

    checks["active_total_ge_7200"] = total_active >= ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS
    checks["reconnects_ge_5"] = len(reconnects) >= TARGET_RECONNECTS
    checks["stale_cycles_ge_2"] = len(stale_cycles) >= TARGET_STALE_CYCLES
    checks["fresh_process_restart_performed"] = bool(
        first.get("pid") and second.get("pid") and first.get("pid") != second.get("pid")
    )
    checks["no_python_memory_carried_over"] = checks["fresh_process_restart_performed"]
    labels = {item["label"] for item in checkpoints}
    required_labels = {"start", "abs_30m", "before_restart", "after_restart", "abs_90m", "final"}
    checks["checkpoint_coverage_complete"] = required_labels.issubset(labels)
    checks["all_checkpoints_ok"] = bool(checkpoints) and all(
        item.get("ok") is True for item in checkpoints
    )

    checks["controlled_reconnects_recovered_fresh"] = bool(reconnects) and all(
        item.get("disconnect_observed") and item.get("fresh_event_after_reconnect")
        for item in reconnects
    )
    checks["reconnect_reconciliation_ok"] = bool(reconnects) and all(
        item.get("reconciliation_ok") is True for item in reconnects
    )

    checks["recovery_ok"] = second_checks.get("recovery_ok") is True
    checks["recovery_final_state_running"] = (
        second_checks.get("recovery_final_state_running") is True
    )
    checks["recovery_position_recovered"] = second_checks.get("recovery_position_present") is True
    checks["recovery_protection_snapshot_recovered"] = (
        second_checks.get("recovery_protection_snapshot_present") is True
    )
    checks["no_fabricated_fill_across_restart"] = first.get("counts_at_stop") == second.get(
        "recovered_counts"
    )

    # ---- stale / fresh
    checks["stale_cycles_health_unavailable"] = bool(stale_cycles) and all(
        (item.get("stale") or {}).get("health_status") == "UNAVAILABLE" for item in stale_cycles
    )
    checks["stale_cycles_risk_increasing_fail_closed"] = bool(stale_cycles) and all(
        "risk_gate_during_stall" in item
        and (item.get("risk_gate_during_stall") or {}).get("admitted") is False
        for item in stale_cycles
    )
    checks["stale_cycles_no_economic_fact"] = bool(stale_cycles) and all(
        item.get("no_economic_fact_during_stall") is True for item in stale_cycles
    )
    checks["stale_cycles_protection_facts_preserved"] = bool(stale_cycles) and all(
        item.get("protection_facts_preserved") is True for item in stale_cycles
    )
    checks["stale_cycles_fresh_recovered"] = bool(stale_cycles) and all(
        item.get("fresh_recovered") is True for item in stale_cycles
    )
    checks["stale_cycles_fresh_protection_hold"] = bool(stale_cycles) and all(
        (item.get("fresh") or {}).get("protection_reason") == "HOLD" for item in stale_cycles
    )
    checks["stale_cycles_reconciliation_ok"] = bool(stale_cycles) and all(
        item.get("reconciliation_ok") is True for item in stale_cycles
    )

    # ---- N01-7-F01 protection authority (sections 5 / 19)
    checks["f01_plan_ttl_expired_while_position_open"] = (
        first_checks.get("f01_position_still_open_after_expiry") is True
    )
    checks["f01_durable_snapshot_present_after_ttl"] = (
        first_checks.get("f01_protection_snapshot_complete_after_expiry") is True
    )
    checks["f01_snapshot_matches_originating_plan"] = (
        first_checks.get("f01_snapshot_matches_originating_plan") is True
    )
    checks["f01_witness_harness_ok"] = first_checks.get("f01_witness_harness_ok") is True
    checks["f01_protection_authority_after_restart"] = (
        second_checks.get("f01_restart_authority_from_durable_snapshot") is True
    )
    checks["f01_authority_identity_matches_durable_plan"] = (
        second_checks.get("f01_restart_authority_not_from_active_plan") is True
    )
    checks["f01_protection_service_resolves_snapshot_after_restart"] = (
        second_checks.get("f01_restart_protection_service_resolves_snapshot") is True
    )
    f01_restart_state = (second.get("f01_after_restart") or {}).get("state") or {}
    checks["f01_no_unprotected_incident"] = (
        f01_restart_state.get("open_position_unprotected_incidents") == 0
    )

    # ---- runtime health / bounded structures
    checks["worker_count_stable"] = bool(samples) and all(
        item.get("worker_count") == 4 and item.get("workers_alive") == 4 for item in samples
    )
    checks["worker_exceptions_zero"] = bool(samples) and all(
        item.get("worker_exceptions") == 0 for item in samples
    )
    checks["queue_within_capacity"] = bool(samples) and all(
        item["queue_size"] <= item["queue_capacity"] for item in samples
    )
    checks["dedupe_within_capacity"] = bool(samples) and all(
        item["dedupe_size"] <= item["dedupe_capacity"]
        and item["trade_dedupe_size"] <= item["trade_dedupe_capacity"]
        for item in samples
    )
    checks["final_queue_empty"] = (second.get("shutdown") or {}).get("queue_final") == 0
    checks["final_inflight_empty"] = (second.get("shutdown") or {}).get("inflight_final") == 0
    checks["final_no_owned_tasks"] = bool(
        (second.get("shutdown") or {}).get("workers_final") == 0
        and (second.get("shutdown") or {}).get("worker_tasks_final") == []
    )
    checks["no_harness_event_errors"] = bool(
        first_checks.get("no_harness_event_errors") and second_checks.get("no_harness_event_errors")
    )
    checks["no_detached_runtime_tasks"] = bool(
        first_checks.get("no_detached_runtime_tasks")
        and second_checks.get("no_detached_runtime_tasks")
    )
    checks["shutdown_no_errors"] = bool(
        first_checks.get("shutdown_no_errors") and second_checks.get("shutdown_no_errors")
    )

    # ---- memory (section 21)
    memory = _memory_condition(samples)
    checks["memory_within_approved_condition"] = not memory["finding"]
    checks["memory_series_present"] = memory.get("points", 0) >= 4

    # ---- sockets / handles (section 23)
    socket_deltas = [
        item.get("socket_delta_vs_before")
        for item in reconnects
        if item.get("socket_delta_vs_before") is not None
    ]
    handle_deltas = [
        item.get("handle_delta_vs_before")
        for item in reconnects
        if item.get("handle_delta_vs_before") is not None
    ]
    checks["sockets_not_accumulating"] = bool(socket_deltas) and (
        socket_deltas[-1] <= MAX_PERMANENT_SOCKET_DELTA
    )
    checks["handles_not_accumulating"] = bool(handle_deltas) and (
        handle_deltas[-1] <= MAX_PERMANENT_HANDLE_DELTA
    )

    # ---- postgresql (section 24)
    checks["pg_no_foreign_client_sessions"] = bool(
        first_checks.get("pg_no_foreign_client_sessions")
        and second_checks.get("pg_no_foreign_client_sessions")
    )
    checks["pg_other_sessions_zero_all_samples"] = bool(samples) and all(
        item.get("pg_other_client_sessions") == 0 for item in samples
    )
    checks["pg_owned_clients_zero"] = bool(
        first_checks.get("pg_owned_clients_zero") and second_checks.get("pg_owned_clients_zero")
    )
    checks["pg_idle_in_transaction_zero"] = bool(
        first_checks.get("pg_idle_in_transaction_zero")
        and second_checks.get("pg_idle_in_transaction_zero")
    )

    # ---- economics (section 25)
    for key in (
        "final_position_flat",
        "final_no_open_buy",
        "final_exactly_one_exit_fill",
        "final_single_trade_lifecycle",
        "final_no_duplicate_facts",
        "final_reserved_cash_zero",
        "final_cash_non_negative",
        "final_protection_snapshot_cleared_when_flat",
        "reconciliation_ok",
        "queue_drained",
        "inflight_empty",
        "runtime_workers_stopped",
    ):
        checks[key] = second_checks.get(key) is True

    # ---- environment / isolation
    checks["runtime_dsn_points_at_task_owned_instance"] = bool(
        first_checks.get("runtime_dsn_points_at_task_owned_instance")
        and second_checks.get("runtime_dsn_points_at_task_owned_instance")
    )
    checks["disposable_database_residue_zero"] = leftover == 0
    checks["shared_primary_unchanged"] = shared_before.get("revision") == shared_after.get(
        "revision"
    ) and shared_before.get("protection_columns") == shared_after.get("protection_columns")
    checks["shared_primary_no_owned_sessions"] = (
        shared_after.get("n01_7_owned_sessions_visible") == 0
    )
    checks["single_migration_head"] = revision == soak.EXPECTED_MIGRATION_HEAD
    checks["production_code_unchanged"] = code_evidence["production_frozen"] is True

    failures = sorted(
        key
        for key, value in checks.items()
        if value is not True and not (probe and key in PROBE_SCOPE_KEYS)
    )
    harness_errors = (first.get("harness_errors") or []) + (second.get("harness_errors") or [])
    shutdown_errors = [
        dict(item, phase="first") for item in ((first.get("shutdown") or {}).get("errors") or [])
    ] + [
        dict(item, phase="second") for item in ((second.get("shutdown") or {}).get("errors") or [])
    ]
    phase_failures = [item for item in (first.get("failure"), second.get("failure")) if item]

    if probe:
        result = (
            "PROBE_OK"
            if not (failures or harness_errors or shutdown_errors or phase_failures)
            else "FAIL"
        )
    else:
        result = (
            "PASS"
            if not (failures or harness_errors or shutdown_errors or phase_failures)
            else "FAIL"
        )

    return {
        "task": "N01-7",
        "mode": mode,
        "result": result,
        "run_identity": {
            "database_name": database_name,
            "database_identity": soak._dsn_identity(database_url),
            "migration_head_observed": revision,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "wall_clock_seconds": round((finished - started).total_seconds(), 3),
            "phase_first_active_seconds": round(active_first, 3),
            "phase_second_active_seconds": round(active_second, 3),
            "total_active_seconds": round(total_active, 3),
            "phase_first_pid": first.get("pid"),
            "phase_second_pid": second.get("pid"),
            "restart_gap_seconds": _gap(
                first.get("active_finished_at"), second.get("active_started_at")
            ),
        },
        "phases": {"first": first, "second": second},
        "reconnects": reconnects,
        "stale_cycles": stale_cycles,
        "checkpoints": checkpoints,
        "memory": memory,
        "environment": {
            "shared_primary_before": shared_before,
            "shared_primary_after": shared_after,
            "leftover_databases": leftover,
            "okx_rest_transport": first.get("okx_rest_transport"),
            "proxy_note": (
                "sandbox proxy cleared for this process only; the single OKX REST metadata call per "
                "phase is routed through the machine's existing user proxy; the public WebSocket is "
                "direct. No machine or system proxy configuration was written."
            ),
        },
        "code_evidence": code_evidence,
        "checks": checks,
        "failures": failures,
        "phase_process_errors": phase_process_errors,
        "phase_failures": phase_failures,
        "harness_errors": harness_errors,
        "shutdown_errors": shutdown_errors,
        "samples": samples,
    }


def _gap(first_finished: str | None, second_started: str | None) -> float | None:
    if not first_finished or not second_started:
        return None
    return round(
        (
            datetime.fromisoformat(second_started) - datetime.fromisoformat(first_finished)
        ).total_seconds(),
        3,
    )


def _memory_condition(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Accepted N01 V1 memory condition: warm-up-trimmed peak growth > 64 MiB AND second-half
    trend > 5 MiB/hour. Both must hold for a finding; a spike alone is never a finding."""
    rss = [
        (item["absolute_elapsed_seconds"], item["rss_mb"])
        for item in samples
        if isinstance(item.get("rss_mb"), (int, float))
        and isinstance(item.get("absolute_elapsed_seconds"), (int, float))
    ]
    if len(rss) < 4:
        return {"finding": False, "reason": "insufficient_samples", "points": len(rss)}
    warmup_index = max(1, int(len(rss) * 0.1))
    trimmed = rss[warmup_index:]
    baseline = trimmed[0][1]
    peak = max(value for _, value in trimmed)
    final = trimmed[-1][1]
    total_growth_mib = round(peak - baseline, 3)
    half = max(1, len(trimmed) // 2)
    trend = soak._slope_per_hour(trimmed[half:])
    finding = bool(
        total_growth_mib > MEMORY_TOTAL_GROWTH_MIB
        and trend is not None
        and trend > MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR
    )
    return {
        "points": len(trimmed),
        "warmup_baseline_mb": round(baseline, 3),
        "peak_mb": round(peak, 3),
        "final_mb": round(final, 3),
        "total_growth_mib": total_growth_mib,
        "second_half_trend_mib_per_hour": trend,
        "overall_trend_mib_per_hour": soak._slope_per_hour(trimmed),
        "threshold_total_growth_mib": MEMORY_TOTAL_GROWTH_MIB,
        "threshold_second_half_trend_mib_per_hour": MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR,
        "finding": finding,
    }


def _emit(report: dict[str, Any], raw_out: Path) -> int:
    payload = json.dumps(report, indent=2, default=str)
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    raw_out.write_text(payload, encoding="utf-8")
    compact = {
        key: report.get(key)
        for key in ("task", "mode", "result", "run_identity", "failures", "memory")
    }
    print(json.dumps(compact, indent=2, default=str))
    return 0 if report.get("result") in {"PASS", "PROBE_OK"} else 1


# ---------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------
def _main_phase(args) -> int:
    report = asyncio.run(
        _phase_scenario(
            args.phase,
            args.database_name,
            args.database_url,
            args.seconds,
            args.sample_interval,
            args.prior_active_seconds,
            args.probe,
        )
    )
    if args.raw_out:
        Path(args.raw_out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    summary = {
        "phase": report["phase"],
        "result": report["result"],
        "active_duration_seconds": report["active_duration_seconds"],
        "failures": sorted(key for key, value in report["checks"].items() if value is not True),
        "failure": report["failure"],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if report["result"] == "OK" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="N01-7 2-hour medium runtime soak")
    parser.add_argument("--mode", choices=("acceptance", "phase"), default="acceptance")
    parser.add_argument("--phase", choices=("first", "second"), default="first")
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
