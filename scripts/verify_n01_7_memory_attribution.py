"""N01-7-INV-01 — memory-attribution diagnostic layer (validation-only, diagnostic only).

Why this file exists
--------------------
The first formal N01-7 2-hour run observed a sustained monotonic RSS increase
(+19.785 MB, +9.066 MB/h) that could not be attributed to any accepted production structure.
It left the finding open (N01-7-MEM-01: OBSERVED, ROOT CAUSE UNRESOLVED) and blocked N01-7.

This module answers exactly one question: *what owns the observed growth?* It is a thin
observation layer over the already-accepted N01-6 harness -- `verify_n01_6_runtime_smoke` is
**imported, never copied and never edited** -- and it changes no production behaviour.

Claim boundary (must not be overstated)
---------------------------------------
This is **NOT** an N01-7 acceptance run. It does **not** count toward the 7200 s acceptance
window, it produces no PASS/FAIL verdict for N01-7, and it must never be described as a fix.
It is one bounded diagnostic observation. `N01-7` stays `BLOCKED / INVESTIGATION REQUIRED`
until a reviewer acts on the evidence this produces.

What it measures (per checkpoint: baseline, then the four window quarters)
-------------------------------------------------------------------------
* tracemalloc: traced current / peak bytes, plus top positive allocation deltas grouped by
  traceback, filename and line, and a per-owner-group attribution of live bytes;
* RSS / USS / private bytes / working set / handles / threads (USS and private are reported
  only when `psutil` exposes them -- on this platform PSS is not available and is recorded as
  UNSUPPORTED rather than invented);
* `gc` counters and a targeted live-object census over `gc.get_objects()`;
* every bounded runtime structure (rolling state, both dedupe structures, inflight, locks,
  worker exceptions, queue) and the validation-side retained evidence;
* asyncio task census and PostgreSQL pool / session counts.

Discipline
----------
During the measurement nothing is trimmed: no `gc.collect()`, no cache clearing, no allocator
trim, no dedupe reset and no sample clearing, because any of those would destroy the phenomenon
being investigated. Exactly one diagnostic `gc.collect()` probe runs *after* the final
checkpoint is fully captured; it is a probe, never a fix, and it is labelled as such.

Environment (same arrangement as the reviewed N01-7 run)
--------------------------------------------------------
Task-owned disposable PostgreSQL on `127.0.0.1:5435` reached through a gitignored `.env`; the
shared primary `127.0.0.1:5432` is never contacted by the runtime. The single OKX REST metadata
lookup goes through the machine's existing user proxy `http://127.0.0.1:10808`; the public
WebSocket stays direct. No machine or system proxy setting is written.

Run (explicit opt-in; never part of the deterministic pytest suite)::

    py -3.14 scripts/verify_n01_7_memory_attribution.py --seconds 180   # harness dry run
    py -3.14 scripts/verify_n01_7_memory_attribution.py \
        --raw-out E:/Temp/n01-7-inv-01/attribution_raw.json             # the 60 minute run
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
import statistics
import sys
import time
import traceback
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = str(REPOSITORY_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Importing the accepted harness is the whole point: it clears the sandbox proxy for this
# process and puts `backend/src` + `backend/tests` on `sys.path`. It is never modified here.
import tracemalloc

import verify_n01_6_runtime_smoke as n6
from marketpulse.market_data.okx_live import OKXLiveProvider
from sqlalchemy.ext.asyncio import async_sessionmaker

RUN_MODE = n6.RUN_MODE
BTC = n6.BTC
ETH = n6.ETH
INSTRUMENTS = n6.INSTRUMENTS

# ---- diagnostic identity / bounds ----------------------------------------------------------
DEFAULT_ACTIVE_SECONDS = 3600.0
MAX_DIAGNOSTIC_ACTIVE_SECONDS = 3600.0
DRY_RUN_MAX_ACTIVE_SECONDS = 300.0
CHECKPOINT_COUNT = 5
DEFAULT_SAMPLE_INTERVAL_SECONDS = 10.0
TRACEMALLOC_FRAMES = 25
TOP_ALLOCATION_DELTAS = 30
TOP_FILENAMES = 25
DEEP_SIZE_DEPTH = 2

TASK_OWNED_DATABASE_PORT = "5435"

# N01-7-INV-01 ownership domains (the reused module reads these module globals at call time).
N01_7_INV_01_DATABASE_PREFIX = "marketpulse_n01_7_inv01_"
N01_7_INV_01_OWNED_APPLICATION = "marketpulse-n01-7-inv01-runtime"
N01_7_INV_01_OBSERVER_APPLICATION = "marketpulse-n01-7-inv01-observer"

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

# ---------------------------------------------------------------------------------------------
# Rebind the reused harness to the INV-01 ownership domains (validation-side identity only).
# ---------------------------------------------------------------------------------------------
n6.DATABASE_PREFIX = N01_7_INV_01_DATABASE_PREFIX
n6.OWNED_APPLICATION = N01_7_INV_01_OWNED_APPLICATION
n6.OBSERVER_APPLICATION = N01_7_INV_01_OBSERVER_APPLICATION

# ---- live-object census targets ------------------------------------------------------------
# Only names that can plausibly grow in *this* runtime are censused, so the walk over
# `gc.get_objects()` stays cheap enough to run inside the measurement.
_CENSUS_TYPES = frozenset(
    {
        # market data / domain facts
        "NormalizedTrade",
        "NormalizedBookTicker",
        "NormalizedKline",
        "AuxiliaryContext",
        "Instrument",
        "BestBidAsk",
        "FeatureSnapshot",
        "MarketEvent",
        "SignalTimelineEvent",
        "StateTransition",
        "StrategyCandidate",
        "SymbolStateRecord",
        "TradePlan",
        "ExecutionIntent",
        "ExecutionResult",
        "ApplyOutcome",
        "_QueuedEvent",
        "_SymbolRollingState",
        "_SignalMemory",
        # ORM records
        "PositionRecord",
        "TradePlanRecord",
        "PaperOrderRecord",
        "FillRecord",
        "TradeRecord",
        "AccountRecord",
        "LedgerEntryRecord",
        "RuntimeControlRecord",
        "IncidentRecord",
        "MarketEventRecord",
        "SignalTimelineRecord",
        "DerivedObservationRecord",
        "StateTransitionRecord",
        "StrategyCandidateRecord",
        # asyncio / IO
        "Task",
        "Future",
        "TimerHandle",
        "Handle",
        "Lock",
        "Event",
        "Condition",
        "Semaphore",
        "coroutine",
        "generator",
        "async_generator",
        "ClientConnection",
        "Connection",
        "Reader",
        "Writer",
        # SQLAlchemy / asyncpg
        "AsyncAdapt_asyncpg_connection",
        "AsyncAdapt_asyncpg_cursor",
        "AsyncAdapt_asyncpg_dbapi",
        "PreparedStatement",
        "AsyncConnection",
        "AsyncSession",
        "AsyncEngine",
        "_ConnectionRecord",
        "_ConnectionFairy",
        # containers (only GC-tracked ones appear here)
        "dict",
        "list",
        "set",
        "tuple",
        "deque",
    }
)

_STDLIB_ROOT = ""
try:  # pragma: no cover - platform probe
    import sysconfig

    _STDLIB_ROOT = str(Path(sysconfig.get_paths()["stdlib"]).resolve()).replace("\\", "/").lower()
except Exception:  # noqa: BLE001, S110 - classification still works without it
    pass


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(UTC)


def _round_mb(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024 * 1024), 4)


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


def _window_means(points: list[tuple[float, float]], windows: int = 4) -> list[float]:
    """Mean of each equal window of `points`; used for the monotonicity check."""
    if not points:
        return []
    span = points[-1][0]
    if span <= 0:
        return []
    width = span / windows
    means: list[float] = []
    for index in range(windows):
        lo = index * width
        hi = span if index == windows - 1 else lo + width
        bucket = [value for elapsed, value in points if lo <= elapsed <= hi]
        if bucket:
            means.append(round(statistics.fmean(bucket), 4))
    return means


def _deep_size(obj: Any, depth: int = DEEP_SIZE_DEPTH) -> int:
    """Best-effort shallow-ish size of a validation-side structure (bounded recursion)."""
    total = sys.getsizeof(obj, 0)
    if depth <= 0:
        return total
    if isinstance(obj, dict):
        for key, value in obj.items():
            total += _deep_size(key, depth - 1) + _deep_size(value, depth - 1)
    elif isinstance(obj, list | tuple | set | frozenset):
        for item in obj:
            total += _deep_size(item, depth - 1)
    return total


@contextmanager
def _okx_rest_proxy():
    """Route ONLY the single OKX REST metadata lookup through the machine's existing proxy.

    Process-local environment edit; no product configuration, no machine or system proxy change.
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
    tail = url.rsplit("@", 1)[-1]
    host_port, _, database = tail.partition("/")
    host, _, port = host_port.partition(":")
    return {"host": host, "port": port, "database": database, "scheme": url.split("://", 1)[0]}


# ---------------------------------------------------------------------------------------------
# Memory probes
# ---------------------------------------------------------------------------------------------
def _process_memory() -> dict[str, Any]:
    """RSS / USS / private / working set / handles / threads, or UNSUPPORTED per field."""
    process = getattr(n6, "_PROCESS", None)
    if process is None:
        return {"available": False, "reason": "psutil_unavailable"}
    info = process.memory_info()
    full = process.memory_full_info()
    fields = set(full._fields)
    result: dict[str, Any] = {
        "available": True,
        "rss_mb": _round_mb(info.rss),
        "vms_mb": _round_mb(info.vms),
        "uss_mb": _round_mb(full.uss) if "uss" in fields else "UNSUPPORTED",
        "private_mb": _round_mb(full.private) if "private" in fields else "UNSUPPORTED",
        "pss_mb": _round_mb(full.pss) if "pss" in fields else "UNSUPPORTED",
        "wset_mb": _round_mb(full.wset) if "wset" in fields else "UNSUPPORTED",
        "peak_wset_mb": _round_mb(full.peak_wset) if "peak_wset" in fields else "UNSUPPORTED",
        "pagefile_mb": _round_mb(full.pagefile) if "pagefile" in fields else "UNSUPPORTED",
        "peak_pagefile_mb": _round_mb(full.peak_pagefile)
        if "peak_pagefile" in fields
        else "UNSUPPORTED",
        "num_page_faults": full.num_page_faults if "num_page_faults" in fields else "UNSUPPORTED",
        "num_handles": process.num_handles(),
        "num_threads": process.num_threads(),
    }
    return result


def _rss_mb() -> float | None:
    return n6._rss_mb()


def _gc_state() -> dict[str, Any]:
    return {
        "enabled": gc.isenabled(),
        "count": list(gc.get_count()),
        "stats": [dict(item) for item in gc.get_stats()],
        "threshold": list(gc.get_threshold()),
    }


def _object_census() -> dict[str, Any]:
    """Targeted live-object census. Never calls `gc.collect()`; drops the list immediately."""
    counts = dict.fromkeys(_CENSUS_TYPES, 0)
    total = 0
    for obj in gc.get_objects():
        total += 1
        name = type(obj).__name__
        if name in counts:
            counts[name] += 1
    return {
        "total_tracked_objects": total,
        "counts": {name: value for name, value in sorted(counts.items()) if value},
    }


# ---------------------------------------------------------------------------------------------
# tracemalloc owner classification
# ---------------------------------------------------------------------------------------------
def _owner_group(filename: str) -> str:
    """Classify one tracemalloc owner filename into the report's attribution groups.

    Order matters: on this platform `site-packages` lives *under* the stdlib root
    (`.../Python314/Lib/site-packages`), so third-party tokens are tested before the stdlib
    prefix test, otherwise every third-party package would be mislabelled as stdlib.
    """
    lowered = filename.replace("\\", "/").lower()
    if "/backend/src/marketpulse/" in lowered:
        return "production_backend_src"
    if "/backend/tests/" in lowered:
        return "accepted_test_modules"
    if lowered.startswith("scripts/") or "/scripts/" in lowered:
        return "validation_scripts"
    if any(token in lowered for token in ("sqlalchemy", "asyncpg", "greenlet")):
        return "sqlalchemy_asyncpg"
    if any(
        token in lowered
        for token in (
            "websockets",
            "httpx",
            "httpcore",
            "h11",
            "anyio",
            "certifi",
            "idna",
            "sniffio",
        )
    ):
        return "websocket_http_stack"
    if "/site-packages/" in lowered:
        return "other_third_party"
    if _STDLIB_ROOT and lowered.startswith(_STDLIB_ROOT):
        return "stdlib"
    if "/lib/python3" in lowered:
        return "stdlib"
    if lowered.startswith(("<frozen", "<string")):
        return "interpreter_frozen"
    return "unclassified"


def _live_bytes_by_group(snapshot: tracemalloc.Snapshot) -> dict[str, int]:
    totals: dict[str, int] = {}
    for stat in snapshot.statistics("filename"):
        group = _owner_group(stat.traceback[0].filename)
        totals[group] = totals.get(group, 0) + stat.size
    return totals


def _live_bytes_by_filename(snapshot: tracemalloc.Snapshot) -> dict[str, int]:
    totals: dict[str, int] = {}
    for stat in snapshot.statistics("filename"):
        name = stat.traceback[0].filename.replace("\\", "/")
        totals[name] = totals.get(name, 0) + stat.size
    return totals


def _format_traceback(traceback_obj: tracemalloc.Traceback) -> list[str]:
    return [f"{frame.filename}:{frame.lineno}" for frame in traceback_obj]


def _top_positive_deltas(
    snapshot: tracemalloc.Snapshot,
    previous: tracemalloc.Snapshot,
    key_type: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for diff in snapshot.compare_to(previous, key_type):
        if diff.size_diff <= 0:
            continue
        rows.append(
            {
                "location": _format_traceback(diff.traceback),
                "owner_group": _owner_group(diff.traceback[0].filename),
                "size_diff_bytes": diff.size_diff,
                "size_diff_mb": _round_mb(diff.size_diff),
                "size_bytes": diff.size,
                "count_diff": diff.count_diff,
                "count": diff.count,
            }
        )
    rows.sort(key=lambda item: item["size_diff_bytes"], reverse=True)
    return rows[:TOP_ALLOCATION_DELTAS]


def _tracemalloc_block(
    snapshot: tracemalloc.Snapshot,
    previous: tracemalloc.Snapshot | None,
) -> dict[str, Any]:
    current, peak = tracemalloc.get_traced_memory()
    # tracemalloc's own bookkeeping lives in a C-level allocation and is deliberately NOT part
    # of `get_traced_memory()`. It is reported explicitly so that the probe's own RSS cost can
    # never be mistaken for runtime growth.
    tracer_self_bytes = tracemalloc.get_tracemalloc_memory() if tracemalloc.is_tracing() else None
    by_filename = _live_bytes_by_filename(snapshot)
    watched = {
        name: value
        for name, value in by_filename.items()
        if "/backend/src/marketpulse/g" in name or "/scripts/verify_n01_7" in name
    }
    block: dict[str, Any] = {
        "traced_current_bytes": current,
        "traced_peak_bytes": peak,
        "traced_current_mb": _round_mb(current),
        "traced_peak_mb": _round_mb(peak),
        "tracemalloc_self_bytes": tracer_self_bytes,
        "tracemalloc_self_mb": _round_mb(tracer_self_bytes),
        "python_allocated_blocks": sys.getallocatedblocks(),
        "live_bytes_by_owner_group": _live_bytes_by_group(snapshot),
        "top_filenames_by_live_bytes": [
            {"filename": name, "bytes": value, "mb": _round_mb(value)}
            for name, value in sorted(by_filename.items(), key=lambda item: item[1], reverse=True)[
                :TOP_FILENAMES
            ]
        ],
        "watched_production_and_validation_filenames": {
            name: {"bytes": value, "mb": _round_mb(value)}
            for name, value in sorted(watched.items(), key=lambda item: item[1], reverse=True)
        },
    }
    if previous is None:
        block["top_positive_deltas"] = {
            "traceback": [],
            "filename": [],
            "lineno": [],
            "note": "first snapshot: no previous to diff against",
        }
    else:
        block["top_positive_deltas"] = {
            "traceback": _top_positive_deltas(snapshot, previous, "traceback"),
            "filename": _top_positive_deltas(snapshot, previous, "filename"),
            "lineno": _top_positive_deltas(snapshot, previous, "lineno"),
        }
    return block


# ---------------------------------------------------------------------------------------------
# Bounded runtime structures / harness retention / async / DB
# ---------------------------------------------------------------------------------------------
def _deque_info(name: str, item: Any) -> dict[str, Any]:
    return {"name": name, "length": len(item), "maxlen": item.maxlen}


def _runtime_structures(pipeline, runtime, harness) -> dict[str, Any]:
    rolling_states = {
        instrument: {
            "trades": _deque_info("trades", state.trades),
            "books": _deque_info("books", state.books),
            "klines": _deque_info("klines", state.klines),
            "has_auxiliary": state.auxiliary is not None,
            "estimated_bytes": _deep_size(state.__dict__, 2),
        }
        for instrument, state in pipeline.rolling._states.items()
    }
    trade_dedupe_fifo = pipeline._trade_dedupe_fifo
    runtime_dedupe_fifo = runtime._dedupe_fifo
    return {
        "rolling_state_cardinality": len(pipeline.rolling._states),
        "rolling_states": rolling_states,
        "rolling_states_estimated_bytes": _deep_size(pipeline.rolling._states, 2),
        "pipeline_lifecycle_active_keys": len(pipeline.lifecycle._active),
        "pipeline_btc_returns_keys": len(pipeline._btc_returns),
        "pipeline_last_detected_events_len": len(pipeline.last_detected_events),
        "trade_dedupe": {
            "size": len(pipeline._trade_dedupe),
            "capacity": pipeline._trade_dedupe_capacity,
            "saturated": len(pipeline._trade_dedupe) == pipeline._trade_dedupe_capacity,
            "fifo_length": len(trade_dedupe_fifo),
            "fifo_head": list(trade_dedupe_fifo[0]) if trade_dedupe_fifo else None,
            "estimated_bytes": sys.getsizeof(pipeline._trade_dedupe)
            + sys.getsizeof(trade_dedupe_fifo),
        },
        "runtime_dedupe": {
            "size": len(runtime._dedupe),
            "capacity": runtime._dedupe_capacity,
            "saturated": len(runtime._dedupe) == runtime._dedupe_capacity,
            "fifo_length": len(runtime_dedupe_fifo),
            "fifo_head": runtime_dedupe_fifo[0] if runtime_dedupe_fifo else None,
            "estimated_bytes": sys.getsizeof(runtime._dedupe) + sys.getsizeof(runtime_dedupe_fifo),
        },
        "runtime_inflight": len(runtime._inflight),
        "runtime_locks": len(runtime._locks),
        "runtime_workers": len(runtime._workers),
        "runtime_queue_size": runtime.queue.qsize(),
        "runtime_queue_capacity": runtime.queue.maxsize,
        "worker_exceptions": _deque_info("worker_exceptions", runtime.worker_exceptions),
        "state_manager_records": len(runtime.state_manager._records),
        "harness_quotes": len(harness.quotes),
        "harness_health_checks": len(harness.health.checks),
        "harness_safety_locks": len(harness.safety._locks),
        "harness_reevaluation_inflight": len(harness.safety._reevaluation_inflight),
        "harness_meaningful_gate_last_keys": len(harness.reevaluation.meaningful._last),
        # `harness.plans` is the accepted `g4.planning.PlanManager`, which owns only
        # clock/execution/sessions -- no accumulator (verified against the real object; the
        # g3 `TradePlanManager._active` is not constructed on this path).
        "provider_cached_instruments": len(_PROVIDER_CACHE["provider"]._instruments)
        if _PROVIDER_CACHE.get("provider") is not None
        else None,
    }


_PROVIDER_CACHE: dict[str, Any] = {"provider": None}


def _harness_retention(
    samples: list[dict[str, Any]],
    rss_series: list[dict[str, Any]],
    feed: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "samples_len": len(samples),
        "samples_estimated_bytes": _deep_size(samples),
        "samples_json_bytes": len(json.dumps(samples, default=str)),
        "rss_series_len": len(rss_series),
        "rss_series_estimated_bytes": _deep_size(rss_series),
        "checkpoints_len": len(checkpoints),
        "checkpoints_estimated_bytes": _deep_size(checkpoints),
        "feed_errors_len": len(feed["errors"]),
        "feed_stale_periods_len": len(feed["stale_periods"]),
        "feed_open_stale_len": len(feed["open_stale"]),
        "feed_health_transitions_len": len(feed["health_transitions"]),
        "feed_first_received_len": len(feed["first_received"]),
        "feed_last_received_len": len(feed["last_received"]),
        "feed_latest_bbo_len": len(feed["latest_bbo"]),
        "feed_last_freshness_len": len(feed["last_freshness"]),
        "feed_last_freshness_rows": len(feed["last_freshness"]),
        "feed_bbo_data_quality_len": len(feed["bbo_data_quality"]),
    }


def _async_state() -> dict[str, Any]:
    tasks = asyncio.all_tasks()
    names = Counter(task.get_name() for task in tasks)
    return {
        "task_count": len(tasks),
        "task_names": dict(sorted(names.items())),
        "done_task_count": sum(1 for task in tasks if task.done()),
    }


def _db_state(engine, observer, database_name: str) -> dict[str, Any]:
    pool = engine.pool
    pool_block: dict[str, Any] = {"type": type(pool).__name__}
    for method in ("size", "checkedin", "checkedout", "overflow"):
        getter = getattr(pool, method, None)
        if getter is None:
            pool_block[method] = "UNSUPPORTED"
            continue
        try:
            pool_block[method] = getter()
        except Exception as exc:  # noqa: BLE001 - recorded, never invented
            pool_block[method] = f"ERROR:{type(exc).__name__}"
    try:
        pool_block["status"] = pool.status()
    except Exception as exc:  # noqa: BLE001
        pool_block["status"] = f"ERROR:{type(exc).__name__}"
    return {"runtime_engine_pool": pool_block}


async def _db_activity(observer, database_name: str) -> dict[str, Any]:
    activity = await n6._ownership_activity(observer, database_name)
    return {
        "client_sessions": activity["client_sessions"],
        "owned_client_sessions": activity["owned_client_sessions"],
        "other_client_sessions": activity["other_client_sessions"],
        "server_sessions": activity["server_sessions"],
        "idle_in_transaction": activity["idle_in_transaction"],
    }


# ---------------------------------------------------------------------------------------------
# Checkpoint capture
# ---------------------------------------------------------------------------------------------
async def _capture_checkpoint(
    *,
    label: str,
    ctx: dict[str, Any],
    engine,
    observer,
    database_name: str,
    previous_snapshot: tracemalloc.Snapshot | None,
) -> tracemalloc.Snapshot:
    """Capture one checkpoint. Light probes first, heavy probes last (see module docstring)."""
    # The baseline checkpoint is taken before the active clock starts, so it reports 0.0.
    active_started = ctx.get("active_started_monotonic")
    elapsed = 0.0 if active_started is None else round(time.monotonic() - active_started, 3)
    record: dict[str, Any] = {
        "label": label,
        "at": _now().isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed_minutes": round(elapsed / 60.0, 3),
        "events_total": ctx["feed"]["total_normalized_events"],
    }

    # (1) light: process memory -- this is the clean RSS series, taken before any heavy probe.
    record["memory"] = _process_memory()
    record["gc"] = _gc_state()
    record["structures"] = _runtime_structures(ctx["pipeline"], ctx["runtime"], ctx["harness"])
    record["harness_retention"] = _harness_retention(
        ctx["samples"], ctx["rss_series"], ctx["feed"], ctx["checkpoints"]
    )
    record["async_state"] = _async_state()
    record["db"] = _db_state(engine, observer, database_name) | {
        "activity": await _db_activity(observer, database_name)
    }

    # (2) heavy: tracemalloc snapshot + diff.
    snapshot = tracemalloc.take_snapshot()
    record["tracemalloc"] = _tracemalloc_block(snapshot, previous_snapshot)

    # (3) heavy: live-object census. Its own RSS cost is measured and reported, not hidden.
    rss_before = _rss_mb()
    census_started = time.monotonic()
    census = _object_census()
    census["rss_mb_before"] = rss_before
    census["rss_mb_after"] = _rss_mb()
    census["rss_delta_mb"] = (
        None
        if census["rss_mb_before"] is None or census["rss_mb_after"] is None
        else round(census["rss_mb_after"] - census["rss_mb_before"], 4)
    )
    census["duration_seconds"] = round(time.monotonic() - census_started, 3)
    census["note"] = (
        "gc.get_objects() materialises a large temporary list; the before/after RSS delta is "
        "reported so its own cost is never mistaken for runtime growth"
    )
    record["object_census"] = census

    ctx["checkpoints"].append(record)
    return snapshot


# ---------------------------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------------------------
async def _scenario(
    database_name: str,
    database_url: str,
    active_seconds: float,
    sample_interval: float,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure: dict[str, Any] | None = None
    samples: list[dict[str, Any]] = []
    rss_series: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    feed = n6._new_feed()
    ctx: dict[str, Any] = {
        "feed": feed,
        "samples": samples,
        "rss_series": rss_series,
        "checkpoints": checkpoints,
        "active_seconds_requested": active_seconds,
        "sample_interval_seconds": sample_interval,
    }
    engine = None
    observer = None
    runtime = None
    consumer: asyncio.Task | None = None
    sampler: asyncio.Task | None = None
    sampler_errors: list[dict[str, Any]] = []
    stream = None
    provider = OKXLiveProvider()
    _PROVIDER_CACHE["provider"] = provider
    checkpoint_interval = active_seconds / (CHECKPOINT_COUNT - 1)
    ctx["checkpoint_interval_seconds"] = round(checkpoint_interval, 3)

    # tracemalloc is enabled before any runtime activity begins (module docstring).
    tracemalloc.start(TRACEMALLOC_FRAMES)
    ctx["tracemalloc_started_with_frames"] = TRACEMALLOC_FRAMES

    try:
        engine = n6._smoke_engine(database_url)
        observer = n6._observer_engine()
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ctx["sessions"] = sessions

        ctx["dsn"] = _dsn_identity(database_url)
        checks["runtime_dsn_points_at_task_owned_instance"] = (
            ctx["dsn"]["port"] == TASK_OWNED_DATABASE_PORT
        )
        ctx["baseline_db_activity"] = await n6._ownership_activity(observer, database_name)

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

        # --- baseline checkpoint: after setup, before any runtime activity -------------------
        ctx["latest_snapshot"] = await _capture_checkpoint(
            label="baseline",
            ctx=ctx,
            engine=engine,
            observer=observer,
            database_name=database_name,
            previous_snapshot=None,
        )
        checks["baseline_captured_before_activity"] = ctx["feed"]["total_normalized_events"] == 0

        stream = provider.stream(list(n6.CHANNELS))
        ctx["stream"] = stream
        consumer = asyncio.create_task(
            n6._consume(stream, pipeline, harness, feed), name="n01-7-inv-01-market-consumer"
        )
        ctx["consumer"] = consumer

        def initial_data_ready() -> bool:
            return all(feed["trades"][item] > 0 and feed["bbos"][item] > 0 for item in INSTRUMENTS)

        ready = await n6._wait_until(initial_data_ready, n6.INITIAL_DATA_MAX_WAIT_SECONDS, 0.2)
        checks["initial_real_data_both_symbols"] = ready
        if not ready:
            raise AssertionError("real BTC/ETH trade+BBO data did not arrive in time")

        ctx["active_started_at"] = _now()
        ctx["active_started_monotonic"] = time.monotonic()
        ctx["rss_start"] = _rss_mb()

        async def sample_once() -> None:
            samples.append(
                {
                    "at": _now().isoformat(),
                    "elapsed_seconds": round(time.monotonic() - ctx["active_started_monotonic"], 3),
                    "rss_mb": _rss_mb(),
                    "btc_trades": feed["trades"][BTC],
                    "btc_bbos": feed["bbos"][BTC],
                    "eth_trades": feed["trades"][ETH],
                    "eth_bbos": feed["bbos"][ETH],
                    "total_events": feed["total_normalized_events"],
                    "queue_size": runtime.queue.qsize(),
                    "inflight": len(runtime._inflight),
                    "worker_exceptions": len(runtime.worker_exceptions),
                    "runtime_dedupe_size": len(runtime._dedupe),
                    "trade_dedupe_size": len(pipeline._trade_dedupe),
                    "trade_dedupe_oldest": list(pipeline._trade_dedupe_fifo[0])
                    if pipeline._trade_dedupe_fifo
                    else None,
                }
            )

        async def sample_loop() -> None:
            while True:
                try:
                    traced_current, _ = tracemalloc.get_traced_memory()
                    rss_series.append(
                        {
                            "elapsed_seconds": round(
                                time.monotonic() - ctx["active_started_monotonic"], 3
                            ),
                            "rss_mb": _rss_mb(),
                            "traced_current_mb": _round_mb(traced_current),
                            "total_events": feed["total_normalized_events"],
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - recorded, never fabricated
                    # Bounded: the sampler must not itself become a growing structure.
                    sampler_errors.append(
                        {"at": _now().isoformat(), "type": type(exc).__name__, "message": str(exc)}
                    )
                    if len(sampler_errors) > 20:
                        sampler_errors.pop(0)
                await asyncio.sleep(sample_interval)

        sampler = asyncio.create_task(sample_loop(), name="n01-7-inv-01-memory-sampler")
        ctx["sampler"] = sampler
        await sample_once()

        # --- controlled entry (fidelity to the reviewed run's workload) ----------------------
        entry_offset = min(60.0, max(10.0, active_seconds * 0.10))

        def entry_ready() -> bool:
            return (
                harness.health.status(n6.HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                and BTC in feed["latest_bbo"]
                and (_now() - feed["latest_bbo"][BTC].received_at).total_seconds()
                <= n6.FRESH_QUOTE_MAX_AGE_SECONDS
                and feed["last_freshness"].get(BTC, {}).get("fresh") is True
            )

        entry_done = False
        next_checkpoint = 1
        while True:
            elapsed = time.monotonic() - ctx["active_started_monotonic"]

            if not entry_done and elapsed >= entry_offset:
                await n6._wait_until(entry_ready, timeout=n6.ENTRY_GATE_MAX_WAIT_SECONDS)
                try:
                    ctx["entry"] = await n6._controlled_entry(harness, sessions, feed, checks)
                    entry_done = True
                except Exception as exc:  # noqa: BLE001 - recorded; the measurement is the point
                    checks["controlled_entry_performed"] = False
                    ctx["entry_harness_error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "note": (
                            "the open position is workload fidelity only; losing it does not "
                            "invalidate the memory measurement, and it is never reported as a "
                            "product result"
                        ),
                    }
                    entry_done = True

            if (
                next_checkpoint < CHECKPOINT_COUNT
                and elapsed >= next_checkpoint * checkpoint_interval
            ):
                ctx["latest_snapshot"] = await _capture_checkpoint(
                    label=f"window_quarter_{next_checkpoint}",
                    ctx=ctx,
                    engine=engine,
                    observer=observer,
                    database_name=database_name,
                    previous_snapshot=ctx.get("latest_snapshot"),
                )
                next_checkpoint += 1

            if elapsed >= active_seconds:
                break
            await asyncio.sleep(0.5)

        ctx["active_duration_seconds"] = time.monotonic() - ctx["active_started_monotonic"]
        ctx["active_finished_at"] = _now()
        ctx["rss_end_before_gc_probe"] = _rss_mb()
        ctx["sampler_errors"] = sampler_errors
        checks["active_duration_observed"] = ctx["active_duration_seconds"] >= active_seconds

        # --- post-measurement diagnostic probe: exactly one gc.collect(), never a fix --------
        # Taken strictly AFTER the final checkpoint was fully captured.
        tracer_current_before, tracer_peak_before = tracemalloc.get_traced_memory()
        probe: dict[str, Any] = {
            "note": (
                "diagnostic probe only, run after the measurement window closed; it is NOT a fix "
                "and it must not be described as one"
            ),
            "at": _now().isoformat(),
            "elapsed_seconds": round(ctx["active_duration_seconds"], 3),
            "rss_mb_before": _rss_mb(),
            "traced_current_bytes_before": tracer_current_before,
            "traced_peak_bytes_before": tracer_peak_before,
            "tracked_objects_before": len(gc.get_objects()),
        }
        probe["gc_collected"] = gc.collect()
        probe["rss_mb_after"] = _rss_mb()
        probe["traced_current_bytes_after"] = tracemalloc.get_traced_memory()[0]
        probe["tracked_objects_after"] = len(gc.get_objects())
        probe["rss_delta_mb"] = (
            None
            if probe["rss_mb_before"] is None or probe["rss_mb_after"] is None
            else round(probe["rss_mb_after"] - probe["rss_mb_before"], 4)
        )
        probe["traced_current_delta_bytes"] = (
            probe["traced_current_bytes_after"] - probe["traced_current_bytes_before"]
        )
        probe["tracked_objects_delta"] = (
            probe["tracked_objects_after"] - probe["tracked_objects_before"]
        )
        ctx["post_measurement_gc_probe"] = probe

        # --- cleanup (after every measurement has been taken) -------------------------------
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
        checks["queue_drained"] = ctx["queue_final"] == 0
        checks["inflight_empty"] = ctx["inflight_final"] == 0
        checks["runtime_workers_stopped"] = ctx["workers_final"] == 0
        checks["worker_exceptions_zero"] = ctx["worker_exceptions_final"] == 0

        ctx["rss_after_shutdown"] = _rss_mb()
        ctx["object_census_after_shutdown"] = _object_census()
        await engine.dispose()
        engine = None
        await observer.dispose()
        observer = None
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
        for name, task in (("sampler", sampler), ("consumer", consumer)):
            if task is not None:
                task.cancel()
                try:
                    await asyncio.gather(task, return_exceptions=True)
                except Exception as exc:  # noqa: BLE001
                    shutdown_errors.append(
                        {"step": f"{name}_cancel", "type": type(exc).__name__, "message": str(exc)}
                    )
        if stream is not None:
            try:
                await stream.aclose()
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
        ctx.setdefault("rss_after_shutdown", _rss_mb())
        ctx.setdefault("sampler_errors", sampler_errors)
        ctx["shutdown_errors"] = shutdown_errors

    return _build_report(database_name, ctx, checks, failure, provider)


# ---------------------------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------------------------
def _trend(points: list[tuple[float, float]]) -> dict[str, Any]:
    if not points:
        return {"samples": 0}
    values = [value for _, value in points]
    means = _window_means(points, windows=4)
    return {
        "samples": len(values),
        "first": round(values[0], 4),
        "final": round(values[-1], 4),
        "peak": round(max(values), 4),
        "min": round(min(values), 4),
        "median": round(statistics.median(values), 4),
        "delta": round(values[-1] - values[0], 4),
        "slope_per_hour": _slope_per_hour(points),
        "quarter_means": means,
        "quarter_means_strictly_increasing": bool(
            len(means) >= 2 and all(later > earlier for earlier, later in pairwise(means))
        ),
    }


def _memory_analysis(ctx: dict[str, Any]) -> dict[str, Any]:
    checkpoints = ctx["checkpoints"]
    rss_points = [
        (item["elapsed_seconds"], item["rss_mb"])
        for item in ctx["rss_series"]
        if item.get("rss_mb") is not None
    ]
    traced_points = [
        (item["elapsed_seconds"], item["traced_current_mb"])
        for item in ctx["rss_series"]
        if item.get("traced_current_mb") is not None
    ]
    checkpoint_rss = [
        (item["elapsed_seconds"], item["memory"]["rss_mb"])
        for item in checkpoints
        if item["memory"].get("rss_mb") is not None
    ]
    checkpoint_traced_current = [
        (item["elapsed_seconds"], item["tracemalloc"]["traced_current_mb"]) for item in checkpoints
    ]
    checkpoint_traced_peak = [
        (item["elapsed_seconds"], item["tracemalloc"]["traced_peak_mb"]) for item in checkpoints
    ]
    checkpoint_tracked = [
        (item["elapsed_seconds"], item["object_census"]["total_tracked_objects"])
        for item in checkpoints
    ]
    uss_field = checkpoints[0]["memory"].get("uss_mb") if checkpoints else None
    private_field = checkpoints[0]["memory"].get("private_mb") if checkpoints else None
    return {
        "checkpoint_count": len(checkpoints),
        "rss_sampled_series": _trend(rss_points),
        "rss_checkpoint_series": _trend(checkpoint_rss),
        "traced_current_checkpoint_series": _trend(checkpoint_traced_current),
        "traced_peak_checkpoint_series": _trend(checkpoint_traced_peak),
        "traced_current_sampled_series": _trend(traced_points),
        "tracked_objects_checkpoint_series": _trend([(x, float(y)) for x, y in checkpoint_tracked]),
        "uss_available": isinstance(uss_field, int | float),
        "private_available": isinstance(private_field, int | float),
        "checkpoint_table": [
            {
                "label": item["label"],
                "elapsed_seconds": item["elapsed_seconds"],
                "rss_mb": item["memory"].get("rss_mb"),
                "uss_mb": item["memory"].get("uss_mb"),
                "private_mb": item["memory"].get("private_mb"),
                "wset_mb": item["memory"].get("wset_mb"),
                "num_handles": item["memory"].get("num_handles"),
                "num_threads": item["memory"].get("num_threads"),
                "traced_current_mb": item["tracemalloc"]["traced_current_mb"],
                "traced_peak_mb": item["tracemalloc"]["traced_peak_mb"],
                "tracemalloc_self_mb": item["tracemalloc"].get("tracemalloc_self_mb"),
                "python_allocated_blocks": item["tracemalloc"].get("python_allocated_blocks"),
                "tracked_objects": item["object_census"]["total_tracked_objects"],
                "object_census_rss_delta_mb": item["object_census"].get("rss_delta_mb"),
                "object_census_seconds": item["object_census"].get("duration_seconds"),
                "task_count": item["async_state"]["task_count"],
                "trade_dedupe_size": item["structures"]["trade_dedupe"]["size"],
                "runtime_dedupe_size": item["structures"]["runtime_dedupe"]["size"],
            }
            for item in checkpoints
        ],
    }


def _owner_group_trend(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    groups: set[str] = set()
    for item in checkpoints:
        groups.update(item["tracemalloc"]["live_bytes_by_owner_group"])
    series: dict[str, Any] = {}
    for group in sorted(groups):
        points = [
            (
                item["elapsed_seconds"],
                item["tracemalloc"]["live_bytes_by_owner_group"].get(group, 0) / (1024 * 1024),
            )
            for item in checkpoints
        ]
        series[group] = _trend(points)
    return series


def _allocation_deltas(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "per_checkpoint": [
            {
                "label": item["label"],
                "elapsed_seconds": item["elapsed_seconds"],
                "top_positive_deltas": item["tracemalloc"]["top_positive_deltas"],
            }
            for item in checkpoints
        ],
        "top_n": TOP_ALLOCATION_DELTAS,
    }


def _structure_series(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    def series(selector) -> list[Any]:
        return [
            {"elapsed_seconds": item["elapsed_seconds"], "value": selector(item)}
            for item in checkpoints
        ]

    return {
        "rolling_state_cardinality": series(
            lambda item: item["structures"]["rolling_state_cardinality"]
        ),
        "rolling_states_estimated_bytes": series(
            lambda item: item["structures"]["rolling_states_estimated_bytes"]
        ),
        "rolling_deque_lengths": series(
            lambda item: {
                instrument: {
                    "trades": state["trades"]["length"],
                    "books": state["books"]["length"],
                    "klines": state["klines"]["length"],
                }
                for instrument, state in item["structures"]["rolling_states"].items()
            }
        ),
        "trade_dedupe_size": series(lambda item: item["structures"]["trade_dedupe"]["size"]),
        "trade_dedupe_saturated": series(
            lambda item: item["structures"]["trade_dedupe"]["saturated"]
        ),
        "trade_dedupe_fifo_length": series(
            lambda item: item["structures"]["trade_dedupe"]["fifo_length"]
        ),
        "runtime_dedupe_size": series(lambda item: item["structures"]["runtime_dedupe"]["size"]),
        "runtime_inflight": series(lambda item: item["structures"]["runtime_inflight"]),
        "runtime_locks": series(lambda item: item["structures"]["runtime_locks"]),
        "runtime_queue_size": series(lambda item: item["structures"]["runtime_queue_size"]),
        "worker_exceptions": series(lambda item: item["structures"]["worker_exceptions"]["length"]),
        "pipeline_lifecycle_active_keys": series(
            lambda item: item["structures"]["pipeline_lifecycle_active_keys"]
        ),
        "state_manager_records": series(lambda item: item["structures"]["state_manager_records"]),
        "harness_meaningful_gate_last_keys": series(
            lambda item: item["structures"]["harness_meaningful_gate_last_keys"]
        ),
        "task_count": series(lambda item: item["async_state"]["task_count"]),
        "task_names": series(lambda item: item["async_state"]["task_names"]),
        "pg_owned_client_sessions": series(
            lambda item: item["db"]["activity"]["owned_client_sessions"]
        ),
        "pg_idle_in_transaction": series(
            lambda item: item["db"]["activity"]["idle_in_transaction"]
        ),
        "runtime_pool_checkedout": series(
            lambda item: item["db"]["runtime_engine_pool"].get("checkedout")
        ),
        "num_handles": series(lambda item: item["memory"].get("num_handles")),
        "num_threads": series(lambda item: item["memory"].get("num_threads")),
    }


def _object_census_series(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    names: set[str] = set()
    for item in checkpoints:
        names.update(item["object_census"]["counts"])
    tracked_names = (
        "NormalizedTrade",
        "NormalizedBookTicker",
        "FeatureSnapshot",
        "MarketEvent",
        "SymbolStateRecord",
        "TradePlan",
        "PositionRecord",
        "Task",
        "Future",
        "TimerHandle",
        "Handle",
        "Lock",
        "dict",
        "list",
        "set",
        "tuple",
        "deque",
        "coroutine",
        "generator",
        "async_generator",
    )
    return {
        "total_tracked_objects": [
            {
                "elapsed_seconds": item["elapsed_seconds"],
                "value": item["object_census"]["total_tracked_objects"],
            }
            for item in checkpoints
        ],
        "all_censused_names_present": sorted(names),
        "per_checkpoint": [
            {
                "label": item["label"],
                "elapsed_seconds": item["elapsed_seconds"],
                "counts": item["object_census"]["counts"],
            }
            for item in checkpoints
        ],
        "tracked_high_signal_names": tracked_names,
    }


def _harness_retention_series(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "label": item["label"],
            "elapsed_seconds": item["elapsed_seconds"],
            **item["harness_retention"],
        }
        for item in checkpoints
    ]


def _suggest_classification(memory: dict[str, Any], owner_groups: dict[str, Any]) -> dict[str, Any]:
    """Evidence-driven *suggestion* only; the report states the final classification."""
    rss = memory["rss_checkpoint_series"]
    traced = memory["traced_current_checkpoint_series"]
    tracked = memory["tracked_objects_checkpoint_series"]
    rss_slope = rss.get("slope_per_hour")
    traced_slope = traced.get("slope_per_hour")
    tracked_slope = tracked.get("slope_per_hour")

    validation_slope = None
    if "validation_scripts" in owner_groups:
        validation_slope = owner_groups["validation_scripts"]["slope_per_hour"]
    production_slope = None
    if "production_backend_src" in owner_groups:
        production_slope = owner_groups["production_backend_src"]["slope_per_hour"]

    rss_growing = bool(rss_slope is not None and rss_slope > 1.0)
    traced_growing = bool(traced_slope is not None and abs(traced_slope) > 1.0)
    tracked_growing = bool(tracked_slope is not None and tracked_slope > 1000.0)

    suggestion = "E_INCONCLUSIVE"
    rationale = []
    if rss_slope is not None and rss_slope > 1.0 and traced_slope is not None:
        if abs(traced_slope) <= 1.0 and not tracked_growing:
            suggestion = "C_ALLOCATOR_OR_NATIVE_RETENTION_LIKELY"
            rationale.append(
                "RSS grows materially while traced live heap and live object counts stay bounded"
            )
        elif traced_growing:
            if validation_slope is not None and production_slope is not None:
                if validation_slope > production_slope and validation_slope > 1.0:
                    suggestion = "B_HARNESS_RETENTION_CONFIRMED"
                    rationale.append("validation-side owner grows faster than production owner")
                elif production_slope > 1.0:
                    suggestion = "A_PYTHON_LIVE_HEAP_GROWTH_CONFIRMED"
                    rationale.append("production owner grows materially with RSS")
                else:
                    suggestion = "E_INCONCLUSIVE"
            else:
                suggestion = "E_INCONCLUSIVE"
    elif not rss_growing:
        suggestion = "E_INCONCLUSIVE"
        rationale.append("no material RSS growth was observed in this diagnostic window")
    return {
        "suggestion": suggestion,
        "rationale": rationale,
        "inputs": {
            "rss_slope_mb_per_hour": rss_slope,
            "traced_current_slope_mb_per_hour": traced_slope,
            "tracked_objects_slope_per_hour": tracked_slope,
            "production_owner_group_slope_mb_per_hour": production_slope,
            "validation_owner_group_slope_mb_per_hour": validation_slope,
            "rss_growing_threshold_mb_per_hour": 1.0,
            "traced_bounded_threshold_mb_per_hour": 1.0,
            "tracked_objects_growing_threshold_per_hour": 1000.0,
        },
        "note": (
            "automated suggestion only, and deliberately conservative: a human reviewer must "
            "confirm the classification against the per-checkpoint evidence before it is used"
        ),
    }


def _build_report(
    database_name: str,
    ctx: dict[str, Any],
    checks: dict[str, bool],
    failure: dict[str, Any] | None,
    provider: OKXLiveProvider,
) -> dict[str, Any]:
    feed = ctx["feed"]
    checkpoints = ctx["checkpoints"]
    memory = _memory_analysis(ctx)
    owner_groups = _owner_group_trend(checkpoints)

    # One baseline checkpoint plus one per window quarter => exactly CHECKPOINT_COUNT records.
    checks["checkpoints_captured"] = len(checkpoints) == CHECKPOINT_COUNT
    checks["rss_available_all_checkpoints"] = all(
        item["memory"].get("rss_mb") is not None for item in checkpoints
    )

    return {
        "result": None,
        "diagnostic": "N01-7-INV-01 memory attribution",
        "is_n01_7_acceptance": False,
        "counts_toward_7200s": False,
        "counts_toward_n01_7": False,
        "requested_active_seconds": ctx.get("active_seconds_requested"),
        "active_duration_seconds": round(ctx.get("active_duration_seconds", 0.0), 3),
        "active_started_at": ctx["active_started_at"].isoformat()
        if ctx.get("active_started_at")
        else None,
        "active_finished_at": ctx["active_finished_at"].isoformat()
        if ctx.get("active_finished_at")
        else None,
        "checkpoint_interval_seconds": ctx.get("checkpoint_interval_seconds"),
        "sample_interval_seconds": ctx.get("sample_interval_seconds"),
        "tracemalloc_started_with_frames": ctx.get("tracemalloc_started_with_frames"),
        "database": {
            "disposable_database": database_name,
            "dsn": ctx.get("dsn"),
            "owned_application_name": N01_7_INV_01_OWNED_APPLICATION,
            "observer_application_name": N01_7_INV_01_OBSERVER_APPLICATION,
            "baseline_activity": ctx.get("baseline_db_activity"),
            "task_owned_port": TASK_OWNED_DATABASE_PORT,
        },
        "okx": {
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
            "health_transitions": feed["health_transitions"],
            "production_ttl_seconds": n6.ACCEPTED_FRESHNESS_TTL_SECONDS,
        },
        "controlled_entry": ctx.get("entry"),
        "controlled_entry_harness_error": ctx.get("entry_harness_error"),
        "memory": memory,
        "live_bytes_by_owner_group": owner_groups,
        "allocation_deltas": _allocation_deltas(checkpoints),
        "object_census": _object_census_series(checkpoints),
        "bounded_structures": _structure_series(checkpoints),
        "harness_retention": _harness_retention_series(checkpoints),
        "sampler_errors": ctx.get("sampler_errors", []),
        "checkpoints": checkpoints,
        "post_measurement_gc_probe": ctx.get("post_measurement_gc_probe"),
        "rss_start_mb": ctx.get("rss_start"),
        "rss_end_before_gc_probe_mb": ctx.get("rss_end_before_gc_probe"),
        "rss_after_shutdown_mb": ctx.get("rss_after_shutdown"),
        "object_census_after_shutdown": ctx.get("object_census_after_shutdown"),
        "shutdown": {
            "queue_final": ctx.get("queue_final"),
            "inflight_final": ctx.get("inflight_final"),
            "workers_final": ctx.get("workers_final"),
            "worker_exceptions_final": ctx.get("worker_exceptions_final"),
            "errors": ctx.get("shutdown_errors", []),
        },
        "harness_errors": feed["errors"][:200],
        "checks": checks,
        "failure": failure,
        "classification_suggestion": _suggest_classification(memory, owner_groups),
    }


# ---------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="N01-7-INV-01 memory attribution diagnostic")
    parser.add_argument("--seconds", type=float, default=DEFAULT_ACTIVE_SECONDS)
    parser.add_argument("--sample-interval", type=float, default=DEFAULT_SAMPLE_INTERVAL_SECONDS)
    parser.add_argument("--raw-out", type=str, default=None)
    args = parser.parse_args()

    if args.seconds > MAX_DIAGNOSTIC_ACTIVE_SECONDS:
        raise SystemExit(
            "this diagnostic is capped at 3600 s and never extends itself; the N01-7 acceptance "
            "window is a separate, explicitly invoked run"
        )
    label = "HARNESS_DRY_RUN" if args.seconds <= DRY_RUN_MAX_ACTIVE_SECONDS else "DIAGNOSTIC"

    started = _now()
    with n6._disposable_postgres_database() as (database_name, database_url):
        report = asyncio.run(
            _scenario(database_name, database_url, args.seconds, args.sample_interval)
        )
    leftover = asyncio.run(n6._n01_6_leftover_databases())

    report["mode"] = label
    report["leftover_n01_7_inv01_databases"] = leftover
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
            "The runtime is pointed at a task-owned disposable PostgreSQL container (.env); the "
            "shared primary (127.0.0.1:5432/marketpulse) is never migrated or written by this run."
        ),
        (
            "This is a diagnostic. It is NOT an N01-7 acceptance run and does not count toward "
            "the 7200 s acceptance window."
        ),
    ]

    failures = sorted(key for key, value in report["checks"].items() if value is not True)
    report["failures"] = failures
    if report.get("failure") is not None:
        report["result"] = "FAIL"
    elif failures:
        # Distinct from FAIL: the diagnostic produced its evidence, but one integrity check did
        # not hold. The raw report still carries every measurement.
        report["result"] = "DIAGNOSTIC_WITH_CHECK_FAILURES"
    else:
        report["result"] = "DIAGNOSTIC_OK"
    report["classification"] = report["classification_suggestion"]["suggestion"]

    if args.raw_out:
        raw_path = Path(args.raw_out)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    summary = {
        "result": report["result"],
        "mode": report["mode"],
        "classification": report["classification"],
        "classification_suggestion": report["classification_suggestion"],
        "active_duration_seconds": report["active_duration_seconds"],
        "total_normalized_events": report["market_data"]["total_normalized_events"],
        "checkpoints": report["memory"]["checkpoint_table"],
        "rss_checkpoint_series": report["memory"]["rss_checkpoint_series"],
        "traced_current_checkpoint_series": report["memory"]["traced_current_checkpoint_series"],
        "traced_peak_checkpoint_series": report["memory"]["traced_peak_checkpoint_series"],
        "tracked_objects_checkpoint_series": report["memory"]["tracked_objects_checkpoint_series"],
        "live_bytes_by_owner_group": report["live_bytes_by_owner_group"],
        "post_measurement_gc_probe": report["post_measurement_gc_probe"],
        "bounded_structures": report["bounded_structures"],
        "harness_retention": report["harness_retention"],
        "failures": failures,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if report["result"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
