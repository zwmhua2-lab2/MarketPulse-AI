"""PRE-01B Integrated Runtime Host — Host Core V1.

One app-scoped composition root. This module is the only production owner of the
long-lived runtime resources (engine, session factory, singleton advisory-lock
connection, provider stream, bounded market-state store, G2 scanner runtime, G4 safety
graph, background loops). It is deliberately *not* a process supervisor: it never
restarts a critical child and it never restarts the process.

Design authority: ``docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md``
(ACCEPTED / COMPLETE, 2026-09-15). The file reads in the contract's own order:
ownership → FSM → startup → readiness → lanes → children → shutdown → telemetry.

Two accepted carry-ins are implemented here explicitly:

* **F-01** — ``state_version_for`` is bound to the *durable* G2 symbol-state authority
  (``symbol_states.state_version`` in PostgreSQL, read through the Host-owned
  ``PostgresG2Repository``). The Host never mints, increments or derives a parallel
  ``state_version`` authority from ``LiveMarketState`` or any other process-local quote
  state. ``LiveMarketState`` is ephemeral observation and is never a recovery authority.
* **F-02** — ``runtime_safety_queue_capacity`` is an *initial configurable default*, not a
  correctness constant. The Host exposes capacity, current size, high-water mark and
  overflow/rejection counters so Implementation Acceptance can size it from observed
  evidence. A capacity that turns out to be too small becomes a recorded finding for
  review/design adjudication; it is never silently re-tuned from here and the
  architecture contract is never rewritten from this module.

Deferred by the accepted contract and deliberately absent here: G2→G3 live handoff,
``BoundedAITaskQueue`` consumer, ``DecisionService``, any Real AI provider, SE-02D,
Forward-Outcome scheduling, WinSW/service packaging and live trading. In particular the
Host constructs **no AI provider at all** (see :class:`_AIDisabledSentinel`), so
"provider constructor call count = 0" is mechanical rather than a matter of trust.

PRE-01B-I1-FIX-01 lifecycle closure notes, so the *why* of each shape survives a re-read:

* the dedicated singleton-lock connection ends its SQLAlchemy transaction after every lock
  and liveness statement. A *session* advisory lock is not transaction-scoped, so committing
  here keeps the fence held while removing the ``idle in transaction`` state the accepted D1
  contract forbids;
* a critical child failure publishes a :class:`HostTerminalResult` that the FastAPI lifespan
  owns and awaits, instead of a detached cleanup task nobody observes. The result is only
  published *after* bounded cleanup finished, so whoever observes it observes a settled Host;
* every cleanup step is attempted independently and its failure is recorded rather than
  swallowed, and the terminal state is ``STOPPED`` only when mandatory cleanup really
  succeeded. A cancelled shutdown still runs the shielded final disposal before the
  cancellation is propagated.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar, Self
from uuid import uuid4

import anyio
import anyio.lowlevel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.clock import Clock, SystemClock
from marketpulse.config import Settings
from marketpulse.db.models import PaperOrderRecord, PositionRecord, TradePlanRecord
from marketpulse.db.session import DatabaseResources, create_database_resources
from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner
from marketpulse.g3.models import BestBidAsk, DataQuality, OrderStatus, PlanStatus, RunMode
from marketpulse.g3.service import PaperExecutionService
from marketpulse.g4.control import SystemControlService
from marketpulse.g4.incidents import IncidentManager
from marketpulse.g4.models import (
    RISK_BLOCKING_COMPONENTS,
    HealthComponent,
    HealthStatus,
    IncidentType,
    OperatorState,
    ReconciliationReport,
    SystemState,
)
from marketpulse.g4.orchestrator import SafetyRuntime
from marketpulse.g4.planning import PlanManager
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.reconciliation import reconcile as reconcile_run_mode
from marketpulse.g4.recovery import RecoveryManager
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.models import (
    Instrument,
    MarketType,
    NormalizedBookTicker,
    NormalizedMarketEvent,
    NormalizedTrade,
)
from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.runtime import (
    READINESS_BLOCKING_INCIDENT,
    READINESS_DB_UNAVAILABLE,
    READINESS_DURABLE_STATE_INVALID,
    READINESS_HEARTBEAT_STALE,
    READINESS_HOST_DISABLED,
    READINESS_HOST_INVARIANT,
    READINESS_HOST_NOT_READY,
    READINESS_MARKET_DATA_STALE,
    READINESS_PROVIDER_STREAM_DOWN,
    READINESS_RECONCILIATION_FAILED,
    READINESS_RECOVERY_INCOMPLETE,
    READINESS_RISK_ADMISSION_CLOSED,
    READINESS_RISK_GATE_UNHEALTHY,
    READINESS_SAFETY_OVERFLOW,
    READINESS_SINGLETON_LOCK_NOT_HELD,
    READINESS_WORKER_UNAVAILABLE,
    GlobalRuntimeState,
    HealthRegistry,
    HostLifecycleState,
    HostReadinessReport,
    HostReadinessStatus,
)

try:  # psutil is a declared direct production dependency. The guard exists only so a
    # missing probe reports UNAVAILABLE instead of a fabricated zero.
    import psutil
except ImportError:  # pragma: no cover - only on a host without psutil installed
    psutil = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "BoundedLane",
    "DuplicateRuntimeHostError",
    "HostConfigurationError",
    "HostDependencies",
    "HostFatalError",
    "HostInvariantError",
    "HostStartupError",
    "HostTerminalResult",
    "LiveMarketState",
    "ProductCurrentMarketSnapshot",
    "ProductHealthCheckSnapshot",
    "ProductLaneSnapshot",
    "ProductMarketQuoteSnapshot",
    "ProductMarketSnapshot",
    "ProductRuntimeSnapshot",
    "RecoverySnapshot",
    "RuntimeHost",
    "SafetyQueueOverflowError",
]

#: Poll granularity for lane drains and child liveness checks. Every wait in this module
#: is bounded by either this value or an explicit contract deadline, so no shutdown path
#: can wait forever.
POLL_INTERVAL_SECONDS = 0.2
#: EventRuntime worker liveness is checked more often than the lane poll: an unexpected
#: worker exit must fail the Host promptly rather than a full telemetry interval later.
MONITOR_INTERVAL_SECONDS = 0.25
#: Prefix for every Host-owned child task name, so a task can be attributed to this Host.
HOST_TASK_PREFIX = "marketpulse-host"

#: Bounded retention for the two Host collections that otherwise grow with uptime. The bound
#: lives on the storage itself (`deque(maxlen=...)`), not on the read path: slicing a list at
#: telemetry time would still retain every historical entry in memory.
STATE_HISTORY_MAXLEN = 64
SCANNER_ERROR_SAMPLE_MAXLEN = 16

#: The V1 activation contract: an enabled Host must subscribe at least BTC-USDT and ETH-USDT.
#: Additional symbols are allowed; a missing one of these two is not.
V1_REQUIRED_INSTRUMENTS = ("BTC-USDT", "ETH-USDT")

_NO_ITEM: Any = object()

#: Non-blocking impairments. They never gate READY on their own; they downgrade the Host
#: to DEGRADED, which still reports honest 503 readiness.
DEGRADED_SCANNER_LANE = "SCANNER_LANE_DEGRADED"
DEGRADED_TELEMETRY = "TELEMETRY_DEGRADED"

#: Lifecycle phases in which the Host is still coming up (never ready).
_PRE_READY_STATES = frozenset(
    {
        HostLifecycleState.CREATED,
        HostLifecycleState.STARTING,
        HostLifecycleState.ACQUIRING_SINGLETON,
        HostLifecycleState.RECOVERY_INGRESS,
        HostLifecycleState.RECOVERING,
        HostLifecycleState.STARTING_RUNTIME,
        HostLifecycleState.WAITING_FOR_READINESS,
    }
)

#: States the Host is never promoted out of again. A stopped or failed Host stays stopped or
#: failed; only a new process may build a new Host.
_TERMINAL_STATES = frozenset(
    {
        HostLifecycleState.FAILED,
        HostLifecycleState.STOPPING,
        HostLifecycleState.STOPPED,
        HostLifecycleState.STOP_FAILED,
    }
)

#: Health components whose non-healthy status closes risk admission in the accepted G4 risk
#: gate. `CORE_MARKET_DATA` is kept honest by the Host itself (see `_sync_market_health`).
_DB_HEALTH_COMPONENTS = frozenset({HealthComponent.DATABASE.value, HealthComponent.EXECUTION.value})


class HostConfigurationError(RuntimeError):
    """The Host was asked to start with a configuration it must refuse."""


class DuplicateRuntimeHostError(HostConfigurationError):
    """Another Runtime already owns the cross-process advisory lock.

    Fail closed with no wait: a second Runtime must never start, and the Host must never
    queue behind the incumbent.
    """

    reason_code = "DUPLICATE_RUNTIME_HOST"


class SafetyQueueOverflowError(RuntimeError):
    """The bounded safety lane was full.

    A protective BBO may never be dropped or coalesced: losing an intermediate quote can
    erase a real protective threshold crossing. Fullness is therefore fatal, not lossy.
    """

    reason_code = "SAFETY_QUEUE_OVERFLOW"


class HostFatalError(RuntimeError):
    """A condition that must fail the Host and require external restart/recovery."""


class HostInvariantError(RuntimeError):
    """A caller contract violation, such as a silent double start."""


class HostStartupError(RuntimeError):
    """Startup could not reach readiness within the accepted absolute deadline."""


@dataclass(frozen=True)
class HostTerminalResult:
    """The lifespan-owned outcome of a Host that died on its own.

    Published only for a Host that terminated *because of a fatal condition*, and only after
    its bounded cleanup finished, so a lifespan that awaits it observes a settled Host rather
    than a mid-flight one. An orderly lifespan/operator stop never produces it, which is what
    keeps "the runtime died" distinguishable from "we were asked to shut down".
    """

    reason: str
    state: HostLifecycleState
    shutdown_failures: tuple[str, ...]


@dataclass(frozen=True)
class RecoverySnapshot:
    """Sanitized terminal recovery fact for one Host process lifetime."""

    status: str
    ok: bool
    started_at: datetime
    finished_at: datetime | None
    ready_at: datetime | None
    reason: str | None
    final_system_state: SystemState
    operator_state: OperatorState
    reconciliation_ok: bool | None


@dataclass(frozen=True)
class ProductMarketSnapshot:
    instrument_id: str
    present: bool
    fresh: bool
    quality: str


@dataclass(frozen=True)
class ProductMarketQuoteSnapshot:
    """An immutable Product projection of one Host-owned latest quote."""

    instrument_id: str
    bid: float | None
    ask: float | None
    received_at: datetime | None
    tradable: bool
    data_quality: str
    age_seconds: float | None


@dataclass(frozen=True)
class ProductCurrentMarketSnapshot:
    """A narrow, non-owning snapshot of the Host's current market authority."""

    snapshot_at: datetime
    instance_id: str
    quotes: tuple[ProductMarketQuoteSnapshot, ...]


@dataclass(frozen=True)
class ProductLaneSnapshot:
    name: str
    size: int
    capacity: int
    high_water: int
    processed: int
    rejected: int
    overflow: int


@dataclass(frozen=True)
class ProductHealthCheckSnapshot:
    name: str
    status: str
    updated_at: datetime | None
    reason: str | None


@dataclass(frozen=True)
class ProductRuntimeSnapshot:
    """Narrow, sanitized Host-owned read snapshot for the Product API.

    ``snapshot_at`` is the authoritative instant of this acquisition, captured exactly once
    together with the facts below. ``health_checks`` and ``readiness`` are read in the same
    synchronous pass, so a Product health section can never combine checks from one instant
    with an overall status derived from a later, independent readiness evaluation.
    """

    snapshot_at: datetime
    instance_id: str
    run_mode: str
    local_only: bool
    lifecycle_state: HostLifecycleState
    uptime_seconds: float | None
    instruments: tuple[str, ...]
    active_risk_instruments: tuple[str, ...]
    children_live: tuple[str, ...]
    risk_admission: bool
    ingress: bool
    safety: bool
    scanner: bool
    created_at: datetime
    started_at: datetime | None
    recovery_ready_at: datetime | None
    last_heartbeat_at: datetime | None
    last_reconciliation_at: datetime | None
    health_checks: tuple[ProductHealthCheckSnapshot, ...]
    readiness: HostReadinessReport
    provider_status: str
    provider_connection_attempts: int | None
    provider_reconnects: int | None
    provider_constructed_by_host: bool
    subscriptions: tuple[tuple[str, str], ...]
    market: tuple[ProductMarketSnapshot, ...]
    scanner_lane: ProductLaneSnapshot
    safety_lanes: tuple[ProductLaneSnapshot, ...]
    database_application_name: str
    database_engine_disposed: bool | None
    database_owns_engine: bool
    singleton_lock_held: bool
    singleton_connection_present: bool
    singleton_lock_lost: bool
    recovery: RecoverySnapshot | None
    reconciliation_startup_ok: bool
    reconciliation_last_ok: bool
    reconciliation_last_result: str | None
    reconciliation_diagnostics: tuple[str, ...]
    safe_mode_latched_by_host: bool
    operator_state: OperatorState | None
    system_state: SystemState | None
    blocking_incident_count: int


@dataclass
class _AIDisabledSentinel:
    """A deliberately inert placeholder for the disabled AI re-evaluation service.

    ``SafetyRuntime`` structurally requires a ``PositionReevaluationService`` instance,
    but Host Core V1 runs with ``reevaluation_enabled=False``, so that dependency is never
    read. Constructing a real service would mean constructing a review *provider*, which
    the accepted contract forbids ("Real AI = NOT CONSTRUCTED / NOT ACTIVATED" plus a
    required proof of zero provider-constructor calls).

    This object therefore fails closed rather than failing silently: every attribute
    access raises, so a future change that flips ``reevaluation_enabled`` True on a
    Host-owned ``SafetyRuntime`` explodes loudly instead of quietly doing nothing or
    reaching for a model.
    """

    def __getattr__(self, name: str) -> Any:
        raise HostInvariantError(f"ai_reevaluation_disabled_in_host_core_v1:{name}")


@dataclass
class HostDependencies:
    """Explicit injection seams.

    Production composition leaves every field ``None`` and the Host constructs its own
    resources. ``RunMode.TEST`` **requires** injection, because a test must never be able
    to reach real OKX or Real AI by accident.
    """

    provider: Any | None = None
    database: DatabaseResources | None = None
    lock_database: DatabaseResources | None = None
    clock: Clock | None = None
    health: HealthRegistry | None = None


@dataclass
class BoundedLane:
    """One bounded FIFO ingress lane with honest pressure counters.

    ``capacity``, ``high_water``, ``overflow_count`` and ``rejected_count`` are the
    evidence surface the accepted contract requires for sizing (`F-02`); none of them is a
    correctness constant.
    """

    name: str
    capacity: int
    processed_count: int = 0
    rejected_count: int = 0
    overflow_count: int = 0
    high_water: int = 0
    _queue: asyncio.Queue[Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise HostConfigurationError(f"lane_capacity_must_be_positive:{self.name}")
        self._queue = asyncio.Queue(maxsize=self.capacity)

    @property
    def size(self) -> int:
        return self._queue.qsize()

    def is_empty(self) -> bool:
        return self._queue.empty()

    def try_send(self, item: Any) -> bool:
        """Non-blocking send. Returns ``False`` when the lane is full.

        The caller decides what fullness means: fatal for the safety lane, a recorded
        rejection for the scanner lane. The lane itself never blocks a producer and never
        drops an item it accepted.
        """
        if self._queue.full():
            return False
        self._queue.put_nowait(item)
        self.high_water = max(self.high_water, self._queue.qsize())
        return True

    async def receive(self, timeout: float) -> Any:
        """Bounded receive; returns ``_NO_ITEM`` when nothing arrived in time."""
        try:
            async with asyncio.timeout(timeout):
                return await self._queue.get()
        except TimeoutError:
            return _NO_ITEM

    def task_done(self) -> None:
        with contextlib.suppress(ValueError):
            self._queue.task_done()

    def telemetry(self) -> dict[str, int]:
        return {
            "size": self.size,
            "capacity": self.capacity,
            "high_water": self.high_water,
            "processed": self.processed_count,
            "rejected": self.rejected_count,
            "overflow": self.overflow_count,
        }


@dataclass
class LiveMarketState:
    """Process-local latest-BBO boundary. Ephemeral observation, never authority.

    Nothing here survives a restart and nothing here may be used as recovered economic
    state: durable PostgreSQL facts stay the only recovery authority. Quotes are stored
    with their arrival instant and their tradability fact, and the accessor downgrades
    quality by age, so no consumer can ever be handed a FRESH label for an aged quote.
    """

    freshness_seconds: float = 5.0
    _latest: dict[str, BestBidAsk] = field(default_factory=dict, repr=False)
    _received_monotonic: dict[str, float] = field(default_factory=dict, repr=False)
    _frames: dict[str, int] = field(default_factory=dict, repr=False)

    def update(self, bbo: BestBidAsk, *, now_monotonic: float | None = None) -> None:
        self._latest[bbo.instrument_id] = bbo
        self._received_monotonic[bbo.instrument_id] = (
            time.monotonic() if now_monotonic is None else now_monotonic
        )
        self._frames[bbo.instrument_id] = self._frames.get(bbo.instrument_id, 0) + 1

    def latest(self, instrument_id: str) -> BestBidAsk | None:
        return self._latest.get(instrument_id)

    def instruments(self) -> tuple[str, ...]:
        return tuple(sorted(self._latest))

    def age_seconds(self, instrument_id: str) -> float | None:
        received = self._received_monotonic.get(instrument_id)
        return None if received is None else max(0.0, time.monotonic() - received)

    def frames(self, instrument_id: str) -> int:
        return self._frames.get(instrument_id, 0)

    def quality(self, instrument_id: str) -> DataQuality:
        bbo = self._latest.get(instrument_id)
        if bbo is None:
            return DataQuality.UNAVAILABLE
        if bbo.data_quality is DataQuality.UNAVAILABLE:
            return DataQuality.UNAVAILABLE
        age = self.age_seconds(instrument_id)
        if age is None or age > self.freshness_seconds:
            return DataQuality.STALE
        return DataQuality.FRESH

    def fresh_tradable(self, instrument_id: str) -> bool:
        bbo = self._latest.get(instrument_id)
        if bbo is None or not bbo.tradable:
            return False
        return self.quality(instrument_id) is DataQuality.FRESH

    async def bbo_for(self, instrument_id: str) -> BestBidAsk:
        """The accessor handed to G3/G4. Fails closed when no observation exists."""
        bbo = self._latest.get(instrument_id)
        if bbo is None:
            raise RuntimeError(f"no_live_quote_for:{instrument_id}")
        return bbo.model_copy(update={"data_quality": self.quality(instrument_id)})

    def clear(self) -> None:
        self._latest.clear()
        self._received_monotonic.clear()
        self._frames.clear()

    def telemetry(self, instruments: tuple[str, ...]) -> dict[str, Any]:
        return {
            "instruments": list(self.instruments()),
            "present": {item: item in self._latest for item in instruments},
            "fresh": {item: self.fresh_tradable(item) for item in instruments},
            "quality": {item: self.quality(item).value for item in instruments},
            "age_seconds": {item: _round_or_none(self.age_seconds(item)) for item in instruments},
            "frames": {item: self.frames(item) for item in instruments},
        }


class RuntimeHost:
    """The single production composition owner of the Integrated Runtime Host V1."""

    #: Every legal lifecycle edge. Anything else is an invariant violation, never a
    #: silently tolerated jump.
    _LEGAL_TRANSITIONS: ClassVar[dict[HostLifecycleState, frozenset[HostLifecycleState]]] = {
        HostLifecycleState.CREATED: frozenset(
            {HostLifecycleState.STARTING, HostLifecycleState.STOPPING}
        ),
        HostLifecycleState.STARTING: frozenset(
            {
                HostLifecycleState.ACQUIRING_SINGLETON,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.ACQUIRING_SINGLETON: frozenset(
            {
                HostLifecycleState.RECOVERY_INGRESS,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.RECOVERY_INGRESS: frozenset(
            {
                HostLifecycleState.RECOVERING,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.RECOVERING: frozenset(
            {
                HostLifecycleState.STARTING_RUNTIME,
                HostLifecycleState.FAILED,
                HostLifecycleState.FAIL_CLOSED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.STARTING_RUNTIME: frozenset(
            {
                HostLifecycleState.WAITING_FOR_READINESS,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.WAITING_FOR_READINESS: frozenset(
            {
                HostLifecycleState.READY,
                HostLifecycleState.DEGRADED,
                HostLifecycleState.FAIL_CLOSED,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.READY: frozenset(
            {
                HostLifecycleState.DEGRADED,
                HostLifecycleState.FAIL_CLOSED,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.DEGRADED: frozenset(
            {
                HostLifecycleState.READY,
                HostLifecycleState.FAIL_CLOSED,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.FAIL_CLOSED: frozenset(
            {
                HostLifecycleState.READY,
                HostLifecycleState.DEGRADED,
                HostLifecycleState.FAILED,
                HostLifecycleState.STOPPING,
            }
        ),
        HostLifecycleState.FAILED: frozenset({HostLifecycleState.STOPPING}),
        HostLifecycleState.STOPPING: frozenset(
            {HostLifecycleState.STOPPED, HostLifecycleState.STOP_FAILED}
        ),
        HostLifecycleState.STOPPED: frozenset(),
        HostLifecycleState.STOP_FAILED: frozenset(),
    }

    def __init__(
        self,
        settings: Settings,
        *,
        clock: Clock | None = None,
        dependencies: HostDependencies | None = None,
        instance_id: str | None = None,
    ) -> None:
        self.settings = settings
        self.dependencies = dependencies
        self.clock: Clock = (
            clock or (dependencies.clock if dependencies is not None else None) or SystemClock()
        )
        self.instance_id = instance_id or uuid4().hex[:12]
        self.run_mode = RunMode(settings.run_mode)
        self.instruments: tuple[str, ...] = tuple(settings.runtime_host_instrument_list)

        self._health: HealthRegistry = (
            dependencies.health
            if dependencies is not None and dependencies.health is not None
            else HealthRegistry()
        )
        self._global_state = GlobalRuntimeState(run_mode=settings.run_mode, health=self._health)

        # --- lifecycle -------------------------------------------------------------
        self._state = HostLifecycleState.CREATED
        self._state_history: deque[tuple[str, str]] = deque(
            [(self.clock.now().isoformat(), HostLifecycleState.CREATED.value)],
            maxlen=STATE_HISTORY_MAXLEN,
        )
        self._start_invoked = False
        self._stop_completed = False
        self._shutting_down = False
        self._host_failed = False
        self._failure_reason: str | None = None
        self._child_failure: BaseException | None = None
        self._stop_lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None
        self._terminal_result: HostTerminalResult | None = None
        self._terminal_event = anyio.Event()

        # --- resources -------------------------------------------------------------
        self._db: DatabaseResources | None = None
        self._lock_db: DatabaseResources | None = None
        self._lock_connection: Any | None = None
        self._lock_held = False
        self._lock_lost = False
        self._owns_database = True
        self._provider: Any | None = None
        self._provider_constructed = False
        self._task_group: Any | None = None
        self._supervisor_task: asyncio.Task[None] | None = None
        self._ingress_cancel_scope: anyio.CancelScope | None = None
        self._stream: Any | None = None

        # --- composition -----------------------------------------------------------
        self._sessions: async_sessionmaker[AsyncSession] | None = None
        self._g2_repository: PostgresG2Repository | None = None
        self._event_runtime: EventRuntime | None = None
        self._pipeline: ScannerPipeline | None = None
        self._execution: PaperExecutionService | None = None
        self._state_service: SystemStateService | None = None
        self._incidents: IncidentManager | None = None
        self._risk_gate: SystemRiskGate | None = None
        self._protection: PositionProtectionService | None = None
        self._plans: PlanManager | None = None
        self._safety: SafetyRuntime | None = None
        self._recovery: RecoveryManager | None = None
        self._control: SystemControlService | None = None

        # --- market state / lanes --------------------------------------------------
        self._market = LiveMarketState(freshness_seconds=settings.runtime_market_freshness_seconds)
        self._safety_lanes: dict[str, BoundedLane] = {}
        self._scanner_lane = BoundedLane(
            name="scanner", capacity=settings.runtime_scanner_queue_capacity
        )

        # --- gates -----------------------------------------------------------------
        self._risk_admission_open = False
        self._ingress_open = False
        self._safety_admission_open = False
        self._scanner_admission_open = False

        # --- signals ---------------------------------------------------------------
        self._ingress_scope_ready = anyio.Event()
        self._runtime_children_requested = anyio.Event()
        self._supervisor_stop_requested = anyio.Event()
        self._loops_stop = anyio.Event()
        self._provider_stopped = anyio.Event()
        self._child_started: dict[str, anyio.Event] = {}
        self._child_finished: dict[str, anyio.Event] = {}
        self._children_live: set[str] = set()

        # --- observations ----------------------------------------------------------
        self._instrument_metadata: dict[str, Instrument] = {}
        self._active_risk_instruments: tuple[str, ...] = ()
        self._recovery_ok = False
        self._recovery_snapshot: RecoverySnapshot | None = None
        self._startup_reconciliation_ok = False
        self._durable_system_state: SystemState | None = None
        self._durable_operator_state: OperatorState | None = None
        self._blocking_incident_count = 0
        self._reconciliation_ok = True
        self._safe_mode_latch_applied = False
        self._market_frames = 0
        self._trade_frames = 0
        self._ingress_forwarded = 0

        # --- counters (monotonic only; no unbounded time series) -------------------
        self._safety_overflow_count = 0
        self._safety_processed = 0
        self._scanner_rejections = 0
        self._scanner_processed = 0
        self._scanner_errors = 0
        self._scanner_error_samples: deque[str] = deque(maxlen=SCANNER_ERROR_SAMPLE_MAXLEN)
        self._eventruntime_worker_exits = 0
        self._invariant_violations = 0
        self._telemetry_errors = 0
        self._shutdown_escalated = False
        self._shutdown_failures: list[str] = []

        # --- timestamps ------------------------------------------------------------
        self._created_at = self.clock.now()
        self._started_at: datetime | None = None
        self._recovery_ready_at: datetime | None = None
        self._degraded_at: datetime | None = None
        self._stop_requested_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._started_monotonic: float | None = None
        self._last_heartbeat_at: datetime | None = None
        self._last_heartbeat_monotonic: float | None = None
        self._last_reconciliation_at: datetime | None = None
        self._last_reconciliation_result: str | None = None
        self._last_reconciliation_diagnostics: list[str] = []
        self._last_frame_at: datetime | None = None
        self._last_bbo_at: datetime | None = None
        self._telemetry: dict[str, Any] = {}

    # ------------------------------------------------------------------ introspection

    @property
    def state(self) -> HostLifecycleState:
        return self._state

    @property
    def failed(self) -> bool:
        return self._host_failed

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    @property
    def terminal_result(self) -> HostTerminalResult | None:
        """The published fatal outcome, or ``None`` while the Host has not died on its own."""
        return self._terminal_result

    async def wait_for_terminal_result(self) -> HostTerminalResult:
        """Lifespan-owned awaitable for a fatal Host completion.

        Resolves only after a fatal child failure has been followed by bounded cleanup and a
        truthful terminal state, so an observer never races the cleanup it is meant to outlive.
        An orderly ``stop()`` never resolves it, which keeps "the runtime died" distinct from
        "we were asked to shut down".
        """
        await self._terminal_event.wait()
        result = self._terminal_result
        if result is None:  # pragma: no cover - the event is only set together with a result
            raise HostInvariantError("terminal_event_set_without_result")
        return result

    def _publish_terminal_result(self) -> None:
        """Publish the fatal outcome exactly once, after cleanup has settled the Host."""
        if self._terminal_event.is_set():
            return
        self._terminal_result = HostTerminalResult(
            reason=self._failure_reason or "host_failed",
            state=self._state,
            shutdown_failures=tuple(self._shutdown_failures),
        )
        self._terminal_event.set()

    @property
    def health(self) -> HealthRegistry:
        return self._health

    @property
    def global_state(self) -> GlobalRuntimeState:
        return self._global_state

    @property
    def market_state(self) -> LiveMarketState:
        return self._market

    @property
    def event_runtime(self) -> EventRuntime | None:
        return self._event_runtime

    @property
    def scanner_lane(self) -> BoundedLane:
        return self._scanner_lane

    @property
    def safety_lanes(self) -> dict[str, BoundedLane]:
        return self._safety_lanes

    @property
    def safety_overflow_count(self) -> int:
        return self._safety_overflow_count

    @property
    def children_live(self) -> tuple[str, ...]:
        return tuple(sorted(self._children_live))

    @property
    def provider_constructed_by_host(self) -> bool:
        return self._provider_constructed

    @property
    def product_read_session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        """Borrow the exact Host-owned session factory without transferring ownership."""
        return self._sessions

    @property
    def recovery_snapshot(self) -> RecoverySnapshot | None:
        """The immutable, sanitized recovery completion fact, if recovery returned."""
        return self._recovery_snapshot

    def product_runtime_snapshot(self) -> ProductRuntimeSnapshot:
        """Return the Product allowlist as a section-consistent Host-memory snapshot.

        This is intentionally separate from ``runtime_payload()``.  The latter remains the
        existing authenticated telemetry surface; it includes broad operational diagnostics
        that are not a Product API contract.

        ``snapshot_at`` is captured exactly once, here, as the authoritative instant of this
        acquisition; every Product section derived from this Host snapshot publishes that
        instant instead of minting a later per-section timestamp. The health registry and the
        readiness evaluation are read in this same synchronous pass so the Product health
        section is internally snapshot-consistent.
        """
        snapshot_at = datetime.now(UTC)
        health_checks = tuple(
            ProductHealthCheckSnapshot(
                name=name,
                status=str(entry.get("status", "UNAVAILABLE")),
                updated_at=_as_utc_datetime(entry.get("updated_at")),
                reason=(entry.get("reason") if isinstance(entry.get("reason"), str) else None),
            )
            for name, entry in sorted(self._health.snapshot().items())
        )
        readiness = self.readiness()
        provider = self._provider
        provider_status = "NOT_STARTED"
        connection_attempts: int | None = None
        reconnects: int | None = None
        if provider is not None:
            provider_status = (
                "LIVE"
                if self._provider_stream_live()
                else ("STOPPED" if self._provider_stopped.is_set() else "NOT_STARTED")
            )
            connection_attempts = _as_int_or_none(_safe_getattr(provider, "connection_attempts"))
            reconnects = _as_int_or_none(_safe_getattr(provider, "reconnects"))
        market = tuple(
            ProductMarketSnapshot(
                instrument_id=instrument_id,
                present=self._market.latest(instrument_id) is not None,
                fresh=self._market.fresh_tradable(instrument_id),
                quality=self._market.quality(instrument_id).value,
            )
            for instrument_id in self.required_instruments()
        )

        def lane_snapshot(lane: BoundedLane) -> ProductLaneSnapshot:
            return ProductLaneSnapshot(name=lane.name, **lane.telemetry())

        return ProductRuntimeSnapshot(
            snapshot_at=snapshot_at,
            instance_id=self.instance_id,
            run_mode=self.run_mode.value,
            local_only=self.settings.local_only,
            lifecycle_state=self._state,
            uptime_seconds=(
                None
                if self._started_monotonic is None
                else round(time.monotonic() - self._started_monotonic, 3)
            ),
            instruments=self.instruments,
            active_risk_instruments=self._active_risk_instruments,
            children_live=tuple(sorted(self._children_live)),
            risk_admission=self._risk_admission_open,
            ingress=self._ingress_open,
            safety=self._safety_admission_open,
            scanner=self._scanner_admission_open,
            created_at=self._created_at,
            started_at=self._started_at,
            recovery_ready_at=self._recovery_ready_at,
            last_heartbeat_at=self._last_heartbeat_at,
            last_reconciliation_at=self._last_reconciliation_at,
            health_checks=health_checks,
            readiness=readiness,
            provider_status=provider_status,
            provider_connection_attempts=connection_attempts,
            provider_reconnects=reconnects,
            provider_constructed_by_host=self._provider_constructed,
            subscriptions=tuple(
                (channel["channel"], channel["instId"]) for channel in self.subscriptions
            ),
            market=market,
            scanner_lane=lane_snapshot(self._scanner_lane),
            safety_lanes=tuple(
                lane_snapshot(lane) for _, lane in sorted(self._safety_lanes.items())
            ),
            database_application_name=self.database_application_name,
            database_engine_disposed=None if self._db is None else self._db.disposed,
            database_owns_engine=self._owns_database,
            singleton_lock_held=self._lock_held,
            singleton_connection_present=self._lock_connection is not None,
            singleton_lock_lost=self._lock_lost,
            recovery=self._recovery_snapshot,
            reconciliation_startup_ok=self._startup_reconciliation_ok,
            reconciliation_last_ok=self._reconciliation_ok,
            reconciliation_last_result=self._last_reconciliation_result,
            reconciliation_diagnostics=tuple(self._last_reconciliation_diagnostics),
            safe_mode_latched_by_host=self._safe_mode_latch_applied,
            operator_state=self._durable_operator_state,
            system_state=self._durable_system_state,
            blocking_incident_count=self._blocking_incident_count,
        )

    def product_market_snapshot(self) -> ProductCurrentMarketSnapshot:
        """Copy the current Host-owned quote authority into an immutable Product snapshot.

        The Product boundary receives scalar facts only.  It never receives a mutable
        ``LiveMarketState`` or ``BestBidAsk`` object, and it delegates freshness and age to
        the existing Host-owned monotonic-clock authority.
        """
        snapshot_at = datetime.now(UTC)
        quotes: list[ProductMarketQuoteSnapshot] = []
        for instrument_id in self.required_instruments():
            bbo = self._market.latest(instrument_id)
            quality = self._market.quality(instrument_id)
            if bbo is None:
                quotes.append(
                    ProductMarketQuoteSnapshot(
                        instrument_id=instrument_id,
                        bid=None,
                        ask=None,
                        received_at=None,
                        tradable=False,
                        data_quality=quality.value,
                        age_seconds=None,
                    )
                )
                continue
            quotes.append(
                ProductMarketQuoteSnapshot(
                    instrument_id=instrument_id,
                    bid=bbo.bid,
                    ask=bbo.ask,
                    received_at=bbo.received_at,
                    tradable=bbo.tradable,
                    data_quality=quality.value,
                    age_seconds=self._market.age_seconds(instrument_id),
                )
            )
        return ProductCurrentMarketSnapshot(
            snapshot_at=snapshot_at,
            instance_id=self.instance_id,
            quotes=tuple(quotes),
        )

    def ownership_snapshot(self) -> dict[str, Any]:
        """Read-only facts about what this Host owns right now (used by tests/review)."""
        return {
            "instance_id": self.instance_id,
            "run_mode": self.run_mode.value,
            "state": self._state.value,
            "state_history": list(self._state_history),
            "instruments": list(self.instruments),
            "active_risk_instruments": list(self._active_risk_instruments),
            "owns_database": self._owns_database,
            "engine_disposed": None if self._db is None else self._db.disposed,
            "lock_engine_disposed": None if self._lock_db is None else self._lock_db.disposed,
            "singleton_lock_held": self._lock_held,
            "singleton_connection_present": self._lock_connection is not None,
            "provider_constructed_by_host": self._provider_constructed,
            "provider_injected": (
                self.dependencies is not None and self.dependencies.provider is not None
            ),
            "children_live": sorted(self._children_live),
            "eventruntime_workers_live": (
                None if self._event_runtime is None else self._event_runtime.live_worker_count
            ),
            "gates": {
                "risk_admission": self._risk_admission_open,
                "ingress": self._ingress_open,
                "safety": self._safety_admission_open,
                "scanner": self._scanner_admission_open,
            },
            "shutdown_failures": list(self._shutdown_failures),
        }

    # ------------------------------------------------------------------ host FSM

    def _legal(self, current: HostLifecycleState, target: HostLifecycleState) -> bool:
        return target in self._LEGAL_TRANSITIONS[current]

    def _transition(self, target: HostLifecycleState) -> None:
        current = self._state
        if target is current:
            return
        if not self._legal(current, target):
            self._invariant_violations += 1
            raise HostInvariantError(f"illegal_host_transition:{current.value}->{target.value}")
        self._state = target
        self._state_history.append((self.clock.now().isoformat(), target.value))
        logger.info(
            "runtime_host_state",
            extra={"instance_id": self.instance_id, "from": current.value, "to": target.value},
        )
        if target is HostLifecycleState.DEGRADED and self._degraded_at is None:
            self._degraded_at = self.clock.now()

    # ------------------------------------------------------------------ lifecycle API

    def lifecycle(self) -> Any:
        """Async context manager entering and exiting the Host exactly once."""
        return self._lifecycle_cm()

    @contextlib.asynccontextmanager
    async def _lifecycle_cm(self) -> AsyncIterator[RuntimeHost]:
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.stop()

    async def start(self) -> None:
        """Run the accepted deterministic startup sequence, once.

        A second call is a caller contract violation, not a restart: the accepted model is
        one Host per process lifetime, and a new Host may only start after the previous
        Host reached ``STOPPED`` and released everything it owned. Any failure runs the
        bounded cleanup path before the exception is re-raised, so a failed start never
        leaks the resources it already opened.
        """
        if self._start_invoked:
            self._invariant_violations += 1
            raise HostInvariantError("double_start_is_an_invariant_violation")
        self._start_invoked = True
        if self._state is not HostLifecycleState.CREATED:
            self._invariant_violations += 1
            raise HostInvariantError(f"start_from_illegal_state:{self._state.value}")

        # 1 — explicit enable gate and operational contract, checked before any resource is
        #     touched. A refused configuration is a caller contract violation rather than a
        #     runtime failure: nothing has been opened yet, so the Host stays CREATED and
        #     there is nothing to clean up. Failures *after* this point own resources and go
        #     through the bounded cleanup path below.
        self._validate_configuration()

        try:
            with anyio.fail_after(self.settings.runtime_startup_timeout_seconds):
                await self._startup()
        except TimeoutError as exc:
            await self._safe_fail("startup_deadline_exceeded")
            raise HostStartupError("startup_deadline_exceeded") from exc
        except BaseException as exc:
            await self._safe_fail(f"{type(exc).__name__}")
            raise

    async def _safe_fail(self, reason: str) -> None:
        """Fail closed and clean up without ever masking the original exception."""
        with anyio.CancelScope(shield=True):
            try:
                await self._fail(reason)
            except BaseException:  # cleanup must not hide the real cause
                logger.exception("runtime_host_failure_cleanup_failed")

    async def _fail(self, reason: str) -> None:
        self._host_failed = True
        self._failure_reason = reason
        self._risk_admission_open = False
        self._ingress_open = False
        self._safety_admission_open = False
        self._scanner_admission_open = False
        # Release the supervisor even if the failure happened before the runtime children
        # were requested; otherwise its task group would never be able to unwind.
        self._supervisor_stop_requested.set()
        self._loops_stop.set()
        if self._legal(self._state, HostLifecycleState.FAILED):
            self._transition(HostLifecycleState.FAILED)
        await self.stop()

    async def _startup(self) -> None:
        # 1 — already validated by `start()` before the shared deadline was armed.
        self._transition(HostLifecycleState.STARTING)
        self._started_at = self.clock.now()
        self._started_monotonic = time.monotonic()

        # 2 — owned engine/session factory plus a bounded connectivity probe.
        self._open_database()
        await self._probe_database()
        self._transition(HostLifecycleState.ACQUIRING_SINGLETON)

        # 3 — dedicated singleton advisory-lock connection.
        await self._acquire_singleton_lock()
        self._transition(HostLifecycleState.RECOVERY_INGRESS)

        # 4 — dependency graph. Long-lived resources stay closed and nothing is started.
        self._compose_services()
        # The accepted recovery and risk paths read the shared EXECUTION component, and the
        # accepted `RecoveryManager._final_state` lands the durable state in ERROR when it is
        # not healthy. By now the Host has built the complete execution graph and proven DB
        # connectivity, which is exactly what that component asserts; recovery itself is what
        # decides next whether new risk may be admitted.
        self._health.set(
            HealthComponent.EXECUTION.value, HealthStatus.HEALTHY.value, reason="constructed"
        )

        # 5 — real public metadata first, then one provider stream task in
        #     RECOVERY_INGRESS mode. The stream may consume frames from here on, but the
        #     routing switch that turns a frame into scanner/risk work is the
        #     safety/scanner admission pair, which stays closed until step 9.
        await self._verify_instruments()
        self._ingress_open = True
        self._supervise_in_background()
        await self._ingress_scope_ready.wait()

        # 6 — durable active-risk symbols must have a usable fresh BBO first.
        await self._load_active_risk_instruments()
        await self._await_active_risk_warmup()

        # 7 — recovery, exactly once, through Host-owned market state.
        self._transition(HostLifecycleState.RECOVERING)
        await self._run_recovery()
        self._transition(HostLifecycleState.STARTING_RUNTIME)

        # 8 — bounded runtime: finite workers, loops and monitors.
        await self._start_event_runtime()
        self._runtime_children_requested.set()
        await self._await_children_started(
            [f"safety:{item}" for item in self.instruments]
            + ["scanner", "eventruntime_monitor", "heartbeat", "reconciliation"]
        )

        # 9 — switch routing from recovery-only to normal ingress. No buffered warm-up
        #     frame is replayed: this only changes where *future* frames are routed.
        self._safety_admission_open = True
        self._scanner_admission_open = True
        self._risk_admission_open = True
        self._transition(HostLifecycleState.WAITING_FOR_READINESS)

        # 10 / 11 — honest readiness, then the lifespan startup block is allowed to end.
        self._refresh_host_state()
        self._telemetry = self._build_telemetry()

    # ------------------------------------------------------------------ startup steps

    def _validate_configuration(self) -> None:
        settings = self.settings
        if not settings.runtime_host_enabled:
            raise HostConfigurationError("HOST_DISABLED")
        if self.run_mode is RunMode.REPLAY:
            raise HostConfigurationError("REPLAY_IS_NOT_A_RUNTIME_HOST_MODE")
        if self.run_mode is RunMode.TEST and self.dependencies is None:
            raise HostConfigurationError("HOST_TEST_REQUIRES_INJECTED_DEPENDENCIES")
        if not self.instruments:
            raise HostConfigurationError("NO_INSTRUMENTS_CONFIGURED")
        missing_v1 = sorted(set(V1_REQUIRED_INSTRUMENTS) - set(self.instruments))
        if missing_v1:
            # V1 activation contract: an enabled Host always covers both accepted instruments.
            # Additional symbols stay allowed; a missing BTC-USDT / ETH-USDT does not.
            raise HostConfigurationError("V1_REQUIRED_INSTRUMENTS_MISSING:" + ",".join(missing_v1))
        if self.run_mode is RunMode.LIVE_PAPER:
            if not settings.local_only or settings.host != "127.0.0.1":
                raise HostConfigurationError("LIVE_PAPER_REQUIRES_LOCAL_ONLY")
            if settings.runtime_workers != 1 or settings.runtime_reload:
                raise HostConfigurationError("LIVE_PAPER_REQUIRES_ONE_WORKER_AND_RELOAD_OFF")
        for name, value in (
            ("runtime_startup_timeout_seconds", settings.runtime_startup_timeout_seconds),
            ("runtime_shutdown_grace_seconds", settings.runtime_shutdown_grace_seconds),
            ("runtime_shutdown_dispose_seconds", settings.runtime_shutdown_dispose_seconds),
            ("runtime_market_freshness_seconds", settings.runtime_market_freshness_seconds),
            ("runtime_heartbeat_interval_seconds", settings.runtime_heartbeat_interval_seconds),
            (
                "runtime_reconciliation_interval_seconds",
                settings.runtime_reconciliation_interval_seconds,
            ),
            ("runtime_telemetry_interval_seconds", settings.runtime_telemetry_interval_seconds),
        ):
            if not _positive_finite(value):
                raise HostConfigurationError(f"invalid_host_setting:{name}")
        for name, capacity in (
            ("runtime_safety_queue_capacity", settings.runtime_safety_queue_capacity),
            ("runtime_scanner_queue_capacity", settings.runtime_scanner_queue_capacity),
        ):
            if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
                raise HostConfigurationError(f"invalid_host_setting:{name}")
        self._health.set(
            HealthComponent.DATABASE.value, HealthStatus.UNAVAILABLE.value, reason="not_probed"
        )
        self._health.set(
            HealthComponent.CORE_MARKET_DATA.value,
            HealthStatus.UNAVAILABLE.value,
            reason="no_live_observation",
        )
        self._health.set(
            HealthComponent.EXECUTION.value, HealthStatus.UNAVAILABLE.value, reason="not_recovered"
        )
        self._health.set(
            HealthComponent.AI_AUXILIARY.value,
            HealthStatus.DEGRADED.value,
            reason="ai_reevaluation_disabled",
        )

    def _open_database(self) -> None:
        injected = self.dependencies.database if self.dependencies is not None else None
        if injected is not None:
            self._db = injected
            self._owns_database = False
        else:
            self._db = create_database_resources(
                self.settings, application_name=self.database_application_name
            )
            self._owns_database = True
        self._sessions = self._db.session_factory

    @property
    def database_application_name(self) -> str:
        """Unique, redacted, self-identifying PostgreSQL application_name."""
        return f"{self.settings.runtime_database_application_name}-{self.instance_id}"

    async def _probe_database(self) -> None:
        assert self._db is not None
        async with self._db.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        self._health.set(HealthComponent.DATABASE.value, HealthStatus.HEALTHY.value)

    def _advisory_lock_key(self) -> int:
        return int(self.run_mode is RunMode.LIVE_PAPER)

    async def _acquire_singleton_lock(self) -> None:
        injected = self.dependencies.lock_database if self.dependencies is not None else None
        self._lock_db = (
            injected
            if injected is not None
            else create_database_resources(
                self.settings, application_name=f"{self.database_application_name}-singleton"
            )
        )
        # A dedicated connection whose lifetime *is* the lock lifetime. It is never
        # returned to a pool: a session advisory lock ends when the session ends, so the
        # connection must stay checked out for as long as the Host runs.
        self._lock_connection = await self._lock_db.engine.connect()
        try:
            acquired = await self._lock_connection.scalar(
                text("SELECT pg_try_advisory_lock(:namespace, :key)"),
                {
                    "namespace": self.settings.runtime_advisory_lock_namespace,
                    "key": self._advisory_lock_key(),
                },
            )
            # The statement above autobegan a transaction. It is committed immediately so the
            # dedicated connection never sits `idle in transaction` for the whole Host
            # lifetime. A *session* advisory lock is not transaction-scoped, so committing
            # here leaves the fence held — only an explicit unlock or a disconnect ends it.
            await self._lock_connection.commit()
        except BaseException:
            await self._release_singleton_lock()
            raise
        if acquired is not True:
            await self._release_singleton_lock()
            raise DuplicateRuntimeHostError(DuplicateRuntimeHostError.reason_code)
        self._lock_held = True
        self._health.set("SINGLETON_LOCK", HealthStatus.HEALTHY.value)

    async def _release_singleton_lock(self) -> None:
        """Release the singleton fence. Every step is attempted and reported separately.

        Nothing here is swallowed: a failed unlock, an unreturned dedicated connection or a
        failed lock-engine disposal is recorded in `shutdown_failures`. A fence that is still
        held or a connection that never came back is exactly what a "clean stop" must not
        paper over.
        """
        connection, self._lock_connection = self._lock_connection, None
        if connection is not None:
            if self._lock_held:
                try:
                    await connection.scalar(
                        text("SELECT pg_advisory_unlock(:namespace, :key)"),
                        {
                            "namespace": self.settings.runtime_advisory_lock_namespace,
                            "key": self._advisory_lock_key(),
                        },
                    )
                    await connection.commit()
                except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                    self._record_cleanup_failure("singleton_unlock_failed", exc)
            try:
                await connection.close()
            except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                self._record_cleanup_failure("singleton_connection_close_failed", exc)
        self._lock_held = False
        injected = self.dependencies.lock_database if self.dependencies is not None else None
        lock_db, self._lock_db = self._lock_db, None
        if lock_db is not None and lock_db is not injected:
            try:
                await lock_db.dispose()
            except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                self._record_cleanup_failure("lock_engine_dispose_failed", exc)

    def _compose_services(self) -> None:
        assert self._sessions is not None
        sessions = self._sessions
        self._g2_repository = PostgresG2Repository(sessions)
        self._event_runtime = EventRuntime(self._g2_repository)
        self._pipeline = ScannerPipeline(OpportunityScanner(), self._event_runtime)
        self._state_service = SystemStateService(sessions, clock=self.clock)
        self._incidents = IncidentManager(sessions, clock=self.clock)
        self._execution = PaperExecutionService(
            sessions,
            self._market.bbo_for,
            self._durable_state_version_for,
            initial_balance=self.settings.paper_initial_balance,
            clock=self.clock,
        )
        self._risk_gate = SystemRiskGate(
            sessions, self._state_service, self._incidents, self._health, clock=self.clock
        )
        self._execution.risk_gate = self._risk_gate
        self._protection = PositionProtectionService(
            sessions, self._execution, self._incidents, self._health, clock=self.clock
        )
        self._plans = PlanManager(sessions, self._execution, clock=self.clock)
        # Real AI re-evaluation is NOT constructed and NOT activated. The inert sentinel
        # only satisfies a structural dependency that `reevaluation_enabled=False` never
        # reads, so no provider constructor is ever called by the Host.
        self._safety = SafetyRuntime(
            execution=self._execution,
            protection=self._protection,
            reevaluation=_AIDisabledSentinel(),  # type: ignore[arg-type]
            health=self._health,
            clock=self.clock,
            reevaluation_enabled=False,
        )
        self._recovery = RecoveryManager(
            sessions,
            self._state_service,
            self._incidents,
            self._health,
            self._protection,
            self._execution,
            self._reconcile,
            clock=self.clock,
        )
        self._control = SystemControlService(
            sessions,
            self._state_service,
            self._incidents,
            self._health,
            self._risk_gate,
            self._protection,
            self._execution,
            self._reconcile,
            clock=self.clock,
        )
        self._safety_lanes = {
            instrument: BoundedLane(
                name=f"safety:{instrument}",
                capacity=self.settings.runtime_safety_queue_capacity,
            )
            for instrument in self.instruments
        }

    async def _durable_state_version_for(self, instrument_id: str) -> int:
        """F-01: the durable G2 symbol-state authority, and nothing else.

        ``symbol_states.state_version`` is written by the accepted
        ``PostgresG2Repository.persist`` inside the same PostgreSQL transaction as the
        state transition, and the accepted ``RecoveryManager`` re-validates plans against
        that very same durable row. Binding this accessor to it means the Host introduces
        no second version system: no counter, no quote-derived estimate, no in-memory
        increment. A symbol with no durable row yet is at durable version 0, exactly the
        accepted ``SymbolStateRecord`` default.
        """
        assert self._g2_repository is not None
        record = await self._g2_repository.get_state(instrument_id)
        return 0 if record is None else int(record.state_version)

    async def _verify_instruments(self) -> None:
        self._provider = self._build_provider()
        metadata = await self._provider.instruments("SPOT")
        by_id: dict[str, Instrument] = {item.instrument_id: item for item in metadata}
        for symbol in self.instruments:
            item = by_id.get(symbol)
            if item is None:
                raise HostConfigurationError(f"instrument_metadata_missing:{symbol}")
            if item.market_type is not MarketType.SPOT:
                raise HostConfigurationError(f"instrument_not_spot:{symbol}")
            if not item.tradable:
                raise HostConfigurationError(f"instrument_not_tradable:{symbol}")
        self._instrument_metadata = {symbol: by_id[symbol] for symbol in self.instruments}

    def _build_provider(self) -> Any:
        injected = self.dependencies.provider if self.dependencies is not None else None
        if injected is not None:
            return injected
        self._provider_constructed = True
        return OKXLiveProvider(self.settings.okx_rest_url, self.settings.okx_ws_url)

    @property
    def subscriptions(self) -> list[dict[str, str]]:
        channels: list[dict[str, str]] = []
        for instrument in self.instruments:
            channels.append({"channel": "trades", "instId": instrument})
            channels.append({"channel": "bbo-tbt", "instId": instrument})
        return channels

    async def _load_active_risk_instruments(self) -> None:
        assert self._sessions is not None
        # Shielded so a sibling cancellation cannot land inside the session's exit: a
        # cancelled `AsyncSession.close()` aborts the connection return and the pool silently
        # loses that checkout. This covers one bounded set of queries, not an unbounded wait.
        with anyio.CancelScope(shield=True):
            async with self._sessions() as session:
                orders = set(
                    (
                        await session.scalars(
                            select(PaperOrderRecord.instrument_id).where(
                                PaperOrderRecord.run_mode == self.run_mode,
                                PaperOrderRecord.status == OrderStatus.OPEN,
                            )
                        )
                    ).all()
                )
                positions = set(
                    (
                        await session.scalars(
                            select(PositionRecord.instrument_id).where(
                                PositionRecord.run_mode == self.run_mode,
                                PositionRecord.quantity > 0,
                            )
                        )
                    ).all()
                )
                plans = set(
                    (
                        await session.scalars(
                            select(TradePlanRecord.instrument_id).where(
                                TradePlanRecord.run_mode == self.run_mode,
                                TradePlanRecord.status == PlanStatus.ACTIVE,
                            )
                        )
                    ).all()
                )
        self._active_risk_instruments = tuple(sorted(orders | positions | plans))

    def required_instruments(self) -> tuple[str, ...]:
        """Configured subscriptions plus every durable active-risk symbol."""
        return tuple(sorted(set(self.instruments) | set(self._active_risk_instruments)))

    async def _await_active_risk_warmup(self) -> None:
        required = self.required_instruments()
        if not required:
            return
        while True:
            if all(self._market.fresh_tradable(item) for item in required):
                return
            if self._provider_stopped.is_set():
                raise HostStartupError("provider_stream_ended_during_warmup")
            # The enclosing `anyio.fail_after` in start() is the single absolute deadline.
            await anyio.sleep(POLL_INTERVAL_SECONDS)

    async def _run_recovery(self) -> None:
        assert self._recovery is not None and self._incidents is not None
        if self._recovery_snapshot is not None:
            raise HostInvariantError("recovery_snapshot_already_published")
        report = await self._recovery.recover(
            self.run_mode, bbo_for=self._market.bbo_for, now=self.clock.now()
        )
        self._recovery_ok = bool(report.ok)
        self._startup_reconciliation_ok = bool(
            report.reconciliation.ok if report.reconciliation is not None else False
        )
        self._durable_system_state = SystemState(report.final_system_state)
        self._durable_operator_state = OperatorState(report.operator_state)
        self._last_reconciliation_at = self.clock.now()
        self._last_reconciliation_result = "OK" if self._startup_reconciliation_ok else "MISMATCH"
        if report.reconciliation is not None:
            self._last_reconciliation_diagnostics = list(report.reconciliation.diagnostics)[:8]
        if self._recovery_ok:
            self._recovery_ready_at = self.clock.now()
        # ``report`` is mutable and contains arbitrary revalidation/evidence payloads.  Publish
        # one complete, immutable Product-safe fact only after ``recover()`` has returned.
        # Assignment is atomic at the object-reference level and this process-lifetime field is
        # never subsequently mutated or reconstructed from timestamps.
        self._recovery_snapshot = RecoverySnapshot(
            status="COMPLETED",
            ok=bool(report.ok),
            started_at=report.started_at,
            finished_at=report.finished_at,
            ready_at=self._recovery_ready_at,
            reason=report.reason,
            final_system_state=SystemState(report.final_system_state),
            operator_state=OperatorState(report.operator_state),
            reconciliation_ok=(
                None if report.reconciliation is None else bool(report.reconciliation.ok)
            ),
        )
        self._health.set(
            HealthComponent.DATABASE.value, HealthStatus.HEALTHY.value, recovery="completed"
        )
        self._health.set(
            HealthComponent.EXECUTION.value,
            HealthStatus.HEALTHY.value if self._recovery_ok else HealthStatus.UNAVAILABLE.value,
        )
        with contextlib.suppress(Exception):
            self._blocking_incident_count = len(await self._incidents.blocking(self.run_mode))
        # Recovery leaves the durable state settled. The Host commits its own heartbeat here so
        # that the readiness conjunct "latest heartbeat committed" is decidable when step 10
        # evaluates readiness, instead of only becoming true on the heartbeat loop's first
        # interval. This is a real durable write, not a synthetic timestamp, and a failure is
        # fatal exactly like any other DB failure during startup.
        await self._state_service.heartbeat(self.run_mode)
        self._last_heartbeat_at = self.clock.now()
        self._last_heartbeat_monotonic = time.monotonic()

    async def _start_event_runtime(self) -> None:
        assert self._event_runtime is not None
        await self._event_runtime.start()

    async def _reconcile(self, run_mode: RunMode) -> ReconciliationReport:
        assert self._sessions is not None and self._execution is not None
        return await reconcile_run_mode(
            run_mode,
            sessions=self._sessions,
            execution=self._execution,
            now=self.clock.now(),
            clock=self.clock,
        )

    # ------------------------------------------------------------------ supervisor

    def _supervise_in_background(self) -> None:
        self._supervisor_task = asyncio.create_task(
            self._supervise(), name=f"{HOST_TASK_PREFIX}-supervisor"
        )

    async def _supervise(self) -> None:
        """Own every Host child inside exactly one structured-concurrency scope.

        The task group is a lifetime owner, never a restart supervisor: a child that exits
        unexpectedly cancels its siblings and fails the Host, and nothing in this process
        ever re-creates it.
        """
        try:
            async with anyio.create_task_group() as task_group:
                self._task_group = task_group
                task_group.start_soon(
                    self._provider_stream_driver, name=f"{HOST_TASK_PREFIX}-provider-stream"
                )
                while (
                    not self._runtime_children_requested.is_set()
                    and not self._supervisor_stop_requested.is_set()
                ):
                    await anyio.sleep(POLL_INTERVAL_SECONDS)
                if not self._runtime_children_requested.is_set():
                    return
                for instrument in self.instruments:
                    task_group.start_soon(
                        self._safety_worker,
                        instrument,
                        name=f"{HOST_TASK_PREFIX}-safety-{instrument}",
                    )
                task_group.start_soon(self._scanner_worker, name=f"{HOST_TASK_PREFIX}-scanner")
                task_group.start_soon(
                    self._eventruntime_monitor, name=f"{HOST_TASK_PREFIX}-eventruntime-monitor"
                )
                task_group.start_soon(self._heartbeat_loop, name=f"{HOST_TASK_PREFIX}-heartbeat")
                task_group.start_soon(
                    self._reconciliation_loop, name=f"{HOST_TASK_PREFIX}-reconciliation"
                )
                task_group.start_soon(self._telemetry_loop, name=f"{HOST_TASK_PREFIX}-telemetry")
                # Children leave on their own once the ordered shutdown closes their
                # admissions; this event only releases the supervisor to wait for them.
                await self._supervisor_stop_requested.wait()
        except BaseException as exc:  # one place owns child-failure policy
            self._child_failure = exc
            if isinstance(exc, anyio.get_cancelled_exc_class()):
                return
            if self._shutting_down:
                return
            self._host_failed = True
            self._failure_reason = f"critical_child_failure:{type(exc).__name__}"
            self._risk_admission_open = False
            self._ingress_open = False
            self._safety_admission_open = False
            self._scanner_admission_open = False
            self._health.set(
                HealthComponent.CORE_MARKET_DATA.value,
                HealthStatus.UNAVAILABLE.value,
                reason="host_failed",
            )
            self._health.set(
                HealthComponent.EXECUTION.value,
                HealthStatus.UNAVAILABLE.value,
                reason="host_failed",
            )
            logger.error(
                "runtime_host_child_failure",
                extra={"instance_id": self.instance_id, "reason": self._failure_reason},
                exc_info=exc,
            )
            # Bounded cleanup, then publish the terminal result. The supervisor task itself has
            # already unwound, so `stop()` awaiting it cannot self-deadlock. Publishing only
            # after `stop()` returned is what makes the result a settled lifecycle fact a
            # lifespan can own, instead of a detached fire-and-forget notification.
            self._cleanup_task = asyncio.create_task(
                self._failure_cleanup(), name=f"{HOST_TASK_PREFIX}-failure-cleanup"
            )

    async def _failure_cleanup(self) -> None:
        """Own a fatal failure's cleanup and publish its terminal result.

        The Host half of the lifespan-observable failure signal: the result is published only
        once cleanup finished and the terminal state is truthful, so an observer never sees a
        result that outruns the disposal standing behind it. A cleanup failure is recorded
        rather than left as an unretrieved task exception.
        """
        try:
            await self.stop()
        except Exception as exc:  # noqa: BLE001 - recorded, never left unretrieved
            self._record_cleanup_failure("failure_cleanup_failed", exc)
        finally:
            self._publish_terminal_result()

    def _mark_started(self, name: str) -> None:
        self._children_live.add(name)
        self._child_started.setdefault(name, anyio.Event()).set()

    def _mark_finished(self, name: str) -> None:
        self._children_live.discard(name)
        self._child_finished.setdefault(name, anyio.Event()).set()

    def _child_ever_started(self, name: str) -> bool:
        event = self._child_started.get(name)
        return event is not None and event.is_set()

    async def _await_children_started(self, names: list[str]) -> None:
        for name in names:
            await self._child_started.setdefault(name, anyio.Event()).wait()

    # ------------------------------------------------------------------ children

    async def _provider_stream_driver(self) -> None:
        """Own the provider stream lifetime and route every normalized frame."""
        with anyio.CancelScope() as scope:
            self._ingress_cancel_scope = scope
            self._mark_started("provider_stream")
            stream = self._provider.stream(self.subscriptions)
            self._stream = stream
            self._ingress_scope_ready.set()
            try:
                async for event in stream:
                    if not self._ingress_open:
                        break
                    await self._handle_market_event(event)
            finally:
                self._ingress_cancel_scope = None
                with anyio.CancelScope(shield=True):
                    await self._close_stream(stream)
                self._provider_stopped.set()
                self._mark_finished("provider_stream")

    async def _close_stream(self, stream: Any) -> None:
        """Deterministic provider disposal, bounded to this shutdown window.

        ``aclose()`` throws ``GeneratorExit`` into the suspended generator so its
        ``async with websockets.connect(...)`` runs its own ``__aexit__`` here and now. The
        accepted ``OKXLiveProvider.stream()`` reconnects by iterating an inner async generator
        (``_receive_once``) that owns the websocket; closing the outer generator makes that
        inner one unreachable, and asyncio only turns that into a real ``aclose()`` on a
        following loop turn. The bounded yields below let those turns happen so "provider
        socket closed" holds by the time ``stop()`` returns, instead of being deferred to loop
        teardown. No forced collection is used: the abandoned generator becomes unreachable as
        soon as the closed generator's frame is released, and forcing a collection while Host
        workers could still hold SQLAlchemy connections would risk finalising a live
        connection wrapper.

        A close that fails is recorded in ``shutdown_failures`` rather than swallowed: an
        unreported provider disposal is a resource claim the Host cannot honestly make.
        """
        try:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()
        except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
            self._record_cleanup_failure("provider_close_failed", exc)
        self._stream = None
        for _ in range(8):
            with anyio.CancelScope(shield=True):
                await anyio.lowlevel.checkpoint()

    async def _handle_market_event(self, event: NormalizedMarketEvent) -> None:
        self._last_frame_at = self.clock.now()
        if isinstance(event, NormalizedBookTicker):
            self._market_frames += 1
            self._last_bbo_at = self.clock.now()
            self._market.update(self._to_bbo(event))
            if not self._safety_admission_open:
                # Recovery-only ingress: updated latest market state and freshness
                # telemetry only. No scanner call, no economic fact, no fabricated fill.
                return
            lane = self._safety_lanes.get(event.instrument_id)
            if lane is None:
                return
            if not lane.try_send(self._market.latest(event.instrument_id)):
                self._safety_overflow_count += 1
                lane.overflow_count += 1
                self._risk_admission_open = False
                self._health.set(
                    HealthComponent.CORE_MARKET_DATA.value,
                    HealthStatus.UNAVAILABLE.value,
                    reason="safety_lane_overflow",
                )
                raise SafetyQueueOverflowError(
                    f"safety_lane_overflow:{event.instrument_id}:{lane.size}/{lane.capacity}"
                )
            self._ingress_forwarded += 1
        elif isinstance(event, NormalizedTrade):
            self._trade_frames += 1
        else:  # candle1m and any other frame is outside Host Core V1 ingress
            return
        if not self._scanner_admission_open:
            return
        if not self._scanner_lane.try_send(event):
            self._scanner_rejections += 1
            self._scanner_lane.rejected_count += 1

    def _to_bbo(self, event: NormalizedBookTicker) -> BestBidAsk:
        return BestBidAsk(
            instrument_id=event.instrument_id,
            bid=event.bid_price,
            ask=event.ask_price,
            received_at=event.received_time,
            # Tradability is the frame's fact, never an assumption: an unspecified
            # `None` from a non-OKX boundary fails closed.
            tradable=bool(event.tradable),
            data_quality=DataQuality(event.data_quality.value),
        )

    async def _safety_worker(self, instrument_id: str) -> None:
        """One FIFO worker per instrument: protection never queues behind the scanner."""
        name = f"safety:{instrument_id}"
        lane = self._safety_lanes[instrument_id]
        self._mark_started(name)
        try:
            while True:
                # A closed admission gate is a *routing* fact, not a shutdown fact: at startup
                # the workers are started before normal ingress is switched on, so only an
                # actual shutdown may end this loop.
                if self._shutting_down and lane.is_empty():
                    return
                item = await lane.receive(POLL_INTERVAL_SECONDS)
                if item is _NO_ITEM:
                    continue
                if item is None:  # pragma: no cover - defensive; latest() is set first
                    lane.task_done()
                    continue
                # Quality is re-derived at consumption time: a BBO that aged while the
                # worker drained its backlog must not be handed on under a FRESH label.
                item = item.model_copy(update={"data_quality": self._market.quality(instrument_id)})
                assert self._safety is not None
                try:
                    await self._safety.on_market_data(self.run_mode, item, now=self.clock.now())
                    lane.processed_count += 1
                    self._safety_processed += 1
                except Exception as exc:  # protection failure is safety-critical
                    self._health.set(
                        HealthComponent.EXECUTION.value,
                        HealthStatus.UNAVAILABLE.value,
                        reason="safety_lane_failure",
                    )
                    raise HostFatalError(f"safety_lane_failure:{type(exc).__name__}") from exc
                finally:
                    lane.task_done()
        finally:
            self._mark_finished(name)

    async def _scanner_worker(self) -> None:
        """The isolated scanner lane. Overload degrades this lane, never the safety lane."""
        name = "scanner"
        lane = self._scanner_lane
        self._mark_started(name)
        try:
            while True:
                # Same rule as the safety workers: only a real shutdown ends this loop.
                if self._shutting_down and lane.is_empty():
                    break
                item = await lane.receive(POLL_INTERVAL_SECONDS)
                if item is _NO_ITEM:
                    continue
                assert self._pipeline is not None
                try:
                    await self._pipeline.ingest(item)
                    lane.processed_count += 1
                    self._scanner_processed += 1
                except Exception as exc:  # noqa: BLE001 - per-event isolation is the contract
                    self._scanner_errors += 1
                    sample = type(exc).__name__
                    if sample not in self._scanner_error_samples:
                        self._scanner_error_samples.append(sample)
                    lane.rejected_count += 1
                finally:
                    lane.task_done()
        finally:
            try:
                await self._stop_event_runtime()
            finally:
                self._mark_finished(name)

    async def _stop_event_runtime(self) -> None:
        if self._event_runtime is None:
            return
        try:
            with anyio.move_on_after(self.settings.runtime_shutdown_grace_seconds) as scope:
                await self._event_runtime.stop()
            if scope.cancel_called:
                self._shutdown_escalated = True
                self._shutdown_failures.append("eventruntime_stop_deadline_exceeded")
        except Exception as exc:  # noqa: BLE001 - aggregated, never reported as clean
            self._shutdown_failures.append(f"eventruntime_stop_failed:{type(exc).__name__}")

    async def _eventruntime_monitor(self) -> None:
        name = "eventruntime_monitor"
        self._mark_started(name)
        try:
            while not self._loops_stop.is_set():
                if not self._shutting_down:
                    if self._provider_stopped.is_set():
                        raise HostFatalError("provider_stream_exited_unexpectedly")
                    runtime = self._event_runtime
                    if runtime is not None and runtime.done_worker_count > 0:
                        self._eventruntime_worker_exits += 1
                        raise HostFatalError("eventruntime_worker_exited")
                    if runtime is not None and runtime.live_worker_count != runtime.worker_count:
                        raise HostFatalError("eventruntime_worker_unavailable")
                await self._sleep_or_stop(MONITOR_INTERVAL_SECONDS)
        finally:
            self._mark_finished(name)

    async def _heartbeat_loop(self) -> None:
        name = "heartbeat"
        self._mark_started(name)
        try:
            while not self._loops_stop.is_set():
                # One shielded unit of Host-owned DB work. `shield=True` is not a claim that the
                # loop cannot be stopped — it still ends at this iteration's boundary. It exists
                # because a sibling cancellation delivered inside `AsyncSession.close()` aborts
                # the connection return, and the pool then silently loses that checkout (P2-01).
                # The covered work is one bounded `load` + `heartbeat` + liveness round trip.
                with anyio.CancelScope(shield=True):
                    assert self._state_service is not None
                    try:
                        control = await self._state_service.load(self.run_mode)
                        self._durable_system_state = SystemState(control.system_state)
                        self._durable_operator_state = OperatorState(control.operator_state)
                        await self._state_service.heartbeat(self.run_mode)
                    except Exception as exc:  # DB loss is fatal by contract
                        self._set_database_health(False)
                        raise HostFatalError(f"database_unavailable:{type(exc).__name__}") from exc
                    self._last_heartbeat_at = self.clock.now()
                    self._last_heartbeat_monotonic = time.monotonic()
                    if not await self._singleton_connection_alive():
                        raise HostFatalError("singleton_lock_connection_lost")
                await self._sleep_or_stop(self.settings.runtime_heartbeat_interval_seconds)
        finally:
            self._mark_finished(name)

    async def _reconciliation_loop(self) -> None:
        name = "reconciliation"
        self._mark_started(name)
        try:
            while not self._loops_stop.is_set():
                await self._sleep_or_stop(self.settings.runtime_reconciliation_interval_seconds)
                if self._loops_stop.is_set():
                    return
                # Shielded for the same reason as the heartbeat loop: the detector and the
                # observation refresh both open Host-owned sessions, and a cancellation landing
                # inside a session's exit loses the pooled checkout (P2-01). One bounded pass.
                with anyio.CancelScope(shield=True):
                    try:
                        report = await self._reconcile(self.run_mode)
                    except Exception as exc:  # a detector cannot run without a DB
                        self._set_database_health(False)
                        raise HostFatalError(
                            f"reconciliation_unavailable:{type(exc).__name__}"
                        ) from exc
                    self._reconciliation_ok = bool(report.ok)
                    self._last_reconciliation_at = self.clock.now()
                    self._last_reconciliation_result = "OK" if report.ok else "MISMATCH"
                    self._last_reconciliation_diagnostics = list(report.diagnostics)[:8]
                    if not report.ok and not self._safe_mode_latch_applied:
                        # Detector semantics only: latch the accepted fail-closed state once.
                        # Never repair an economic fact, never auto-resume.
                        self._safe_mode_latch_applied = True
                        assert self._control is not None
                        try:
                            await self._control.enter_safe_mode(
                                self.run_mode,
                                "periodic_reconciliation_mismatch",
                                incident_type=IncidentType.ACCOUNT_INTEGRITY_ERROR,
                            )
                        except Exception as exc:  # incident recording must not mask the cause
                            self._set_database_health(False)
                            raise HostFatalError(
                                f"safe_mode_transition_failed:{type(exc).__name__}"
                            ) from exc
                        self._durable_system_state = SystemState.SAFE_MODE
                    await self._refresh_observation_state()
        finally:
            self._mark_finished(name)

    async def _refresh_observation_state(self) -> None:
        with contextlib.suppress(Exception):
            await self._load_active_risk_instruments()
        with contextlib.suppress(Exception):
            assert self._incidents is not None
            self._blocking_incident_count = len(await self._incidents.blocking(self.run_mode))

    async def _telemetry_loop(self) -> None:
        """Observation only. A sampler failure is recorded and degrades; never fatal."""
        name = "telemetry"
        self._mark_started(name)
        try:
            while not self._loops_stop.is_set():
                try:
                    self._telemetry = self._build_telemetry()
                    self._refresh_host_state()
                except Exception:  # noqa: BLE001 - telemetry must never fail the Host
                    self._telemetry_errors += 1
                await self._sleep_or_stop(self.settings.runtime_telemetry_interval_seconds)
        finally:
            self._mark_finished(name)

    async def _sleep_or_stop(self, seconds: float) -> None:
        with anyio.move_on_after(seconds):
            await self._loops_stop.wait()

    async def _singleton_connection_alive(self) -> bool:
        connection = self._lock_connection
        if connection is None or self._lock_lost:
            return False
        try:
            await connection.execute(text("SELECT 1"))
            # End the autobegun transaction: the liveness probe must not leave the dedicated
            # connection `idle in transaction` for the rest of the Host lifetime.
            await connection.commit()
        except Exception:  # noqa: BLE001 - losing the fence is a fatal Host invariant
            self._lock_lost = True
            self._health.set("SINGLETON_LOCK", HealthStatus.UNAVAILABLE.value)
            return False
        return True

    # ------------------------------------------------------------------ readiness

    def readiness(self) -> HostReadinessReport:
        """Honest, live readiness. `READY` is a conjunction of real conditions.

        Two different reasons can make a Host non-ready, and they are reported separately: the
        Host has not reached the promotable phase at all (`HOST_NOT_READY`, a lifecycle fact),
        or one or more live conjuncts are currently false (a runtime fact). The lifecycle state
        is never itself a conjunct used to *derive* the lifecycle state — that would be
        self-referential and could never promote out of `WAITING_FOR_READINESS`.
        """
        if not self.settings.runtime_host_enabled:
            return HostReadinessReport(
                ready=False,
                status=HostReadinessStatus.FAIL_CLOSED,
                reasons=[READINESS_HOST_DISABLED],
            )
        blockers = self._blocking_reasons()
        if self._state in _PRE_READY_STATES or self._state in _TERMINAL_STATES:
            if READINESS_HOST_NOT_READY not in blockers:
                blockers.insert(0, READINESS_HOST_NOT_READY)
            return HostReadinessReport(
                ready=False, status=HostReadinessStatus.FAIL_CLOSED, reasons=blockers
            )
        if blockers:
            return HostReadinessReport(
                ready=False, status=HostReadinessStatus.FAIL_CLOSED, reasons=blockers
            )
        degradations = self._degradation_reasons()
        if degradations:
            return HostReadinessReport(
                ready=False, status=HostReadinessStatus.DEGRADED, reasons=degradations
            )
        return HostReadinessReport(ready=True, status=HostReadinessStatus.READY, reasons=[])

    def _blocking_reasons(self) -> list[str]:
        """The live readiness conjuncts that are currently false.

        Deliberately excludes the lifecycle state, which is an *output* of this evaluation.
        """
        reasons: list[str] = []
        if self._host_failed:
            reasons.append(READINESS_HOST_INVARIANT)
        if not self._risk_admission_open or self._shutting_down:
            reasons.append(READINESS_RISK_ADMISSION_CLOSED)
        if self._lock_connection is None or not self._lock_held or self._lock_lost:
            reasons.append(READINESS_SINGLETON_LOCK_NOT_HELD)
        # The accepted risk gate blocks every BUY while any RISK_BLOCKING_COMPONENT is not
        # healthy. Readiness must not be claimable while that admission boundary would refuse
        # new work. `CORE_MARKET_DATA` is judged from the Host-owned observation boundary
        # instead of the last per-frame writer, because the accepted `SafetyRuntime` also
        # writes that component per instrument and one fresh symbol could mask a stale one.
        blocking_health = set(self._health.blocking(RISK_BLOCKING_COMPONENTS))
        if blocking_health:
            reasons.append(
                READINESS_DB_UNAVAILABLE
                if blocking_health & _DB_HEALTH_COMPONENTS
                else READINESS_RISK_GATE_UNHEALTHY
            )
        if not self._heartbeat_fresh():
            reasons.append(READINESS_HEARTBEAT_STALE)
        if not self._recovery_ok:
            reasons.append(READINESS_RECOVERY_INCOMPLETE)
        if not self._startup_reconciliation_ok:
            reasons.append(READINESS_RECONCILIATION_FAILED)
        if self._blocking_incident_count > 0:
            reasons.append(READINESS_BLOCKING_INCIDENT)
        if (
            self._durable_system_state is not SystemState.RUNNING
            or self._durable_operator_state is not OperatorState.NORMAL
        ):
            reasons.append(READINESS_DURABLE_STATE_INVALID)
        if not self._provider_stream_live():
            reasons.append(READINESS_PROVIDER_STREAM_DOWN)
        if not self._market_all_fresh():
            reasons.append(READINESS_MARKET_DATA_STALE)
        if not self._required_workers_live():
            reasons.append(READINESS_WORKER_UNAVAILABLE)
        if self._safety_overflow_count > 0 or self._eventruntime_worker_exits > 0:
            reasons.append(READINESS_SAFETY_OVERFLOW)
        return reasons

    def _degradation_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self._scanner_rejections > 0 or self._scanner_errors > 0:
            reasons.append(DEGRADED_SCANNER_LANE)
        if self._telemetry_errors > 0:
            reasons.append(DEGRADED_TELEMETRY)
        return reasons

    def _heartbeat_fresh(self) -> bool:
        if self._last_heartbeat_monotonic is None:
            return False
        # A heartbeat that has not been recommitted for several intervals means DB health
        # is unknown, so readiness fails closed rather than trusting a stale claim. The
        # heartbeat child itself fails the Host on any DB exception; this guard covers the
        # case where that child is already gone.
        allowed = max(
            self.settings.runtime_heartbeat_interval_seconds * 3.0,
            self.settings.runtime_heartbeat_interval_seconds + 5.0,
        )
        return (time.monotonic() - self._last_heartbeat_monotonic) <= allowed

    def _provider_stream_live(self) -> bool:
        return "provider_stream" in self._children_live and not self._provider_stopped.is_set()

    def _market_all_fresh(self) -> bool:
        required = self.required_instruments()
        return bool(required) and all(self._market.fresh_tradable(item) for item in required)

    def _required_workers_live(self) -> bool:
        required = [f"safety:{item}" for item in self.instruments] + [
            "provider_stream",
            "scanner",
            "eventruntime_monitor",
            "heartbeat",
            "reconciliation",
        ]
        if not all(name in self._children_live for name in required):
            return False
        runtime = self._event_runtime
        if runtime is None:
            return False
        return runtime.live_worker_count == runtime.worker_count and runtime.done_worker_count == 0

    def _sync_market_health(self) -> None:
        """Keep the shared `CORE_MARKET_DATA` component equal to the Host's own conjunction.

        The accepted G4 risk gate refuses every BUY while this component is not healthy, so the
        Host — which owns the ingress that decides it — must never leave the component claiming
        health for a stale symbol. With more than one instrument, a per-frame writer would let a
        fresh symbol mask a stale one; this conjunct is deliberately stricter and can only ever
        close admission earlier, never open it for a symbol the Host cannot see.
        """
        required = self.required_instruments()
        healthy = bool(required) and all(self._market.fresh_tradable(item) for item in required)
        self._health.set(
            HealthComponent.CORE_MARKET_DATA.value,
            HealthStatus.HEALTHY.value if healthy else HealthStatus.UNAVAILABLE.value,
            reason="host_market_conjunction",
        )

    def _refresh_host_state(self) -> None:
        """Derive the lifecycle state from the readiness conjuncts.

        The lifecycle state is an *output* of readiness and never an input to it, otherwise the
        `WAITING_FOR_READINESS` phase could never promote. Terminal states are never resurrected.
        """
        self._sync_market_health()
        if self._host_failed:
            if self._legal(self._state, HostLifecycleState.FAIL_CLOSED):
                self._transition(HostLifecycleState.FAIL_CLOSED)
            return
        if self._state in _TERMINAL_STATES:
            return
        if self._blocking_reasons():
            target = HostLifecycleState.FAIL_CLOSED
        elif self._degradation_reasons():
            target = HostLifecycleState.DEGRADED
        else:
            target = HostLifecycleState.READY
        if self._legal(self._state, target):
            self._transition(target)

    def _set_database_health(self, healthy: bool) -> None:
        status = HealthStatus.HEALTHY.value if healthy else HealthStatus.UNAVAILABLE.value
        self._health.set(HealthComponent.DATABASE.value, status)
        self._health.set(HealthComponent.EXECUTION.value, status)

    # ------------------------------------------------------------------ payloads

    def live_payload(self) -> dict[str, object]:
        """Minimal liveness facts: the process and Host control path are alive."""
        return {
            "status": "alive",
            "run_mode": self.run_mode.value,
            "host_state": self._state.value,
        }

    def ready_payload(self) -> dict[str, object]:
        report = self.readiness()
        return {
            "run_mode": self.run_mode.value,
            "host_state": self._state.value,
            **report.as_payload(),
        }

    def health_payload(self) -> dict[str, object]:
        report = self.readiness()
        if report.ready:
            status = "ok"
        elif report.status is HostReadinessStatus.DEGRADED:
            status = "DEGRADED"
        else:
            status = "FAIL_CLOSED"
        return {
            "status": status,
            "run_mode": self.run_mode.value,
            "local_only": self.settings.local_only,
            "host_state": self._state.value,
            "ready": report.ready,
            "reasons": list(report.reasons),
            "checks": self._health.snapshot(),
        }

    def runtime_payload(self) -> dict[str, object]:
        """Detailed telemetry. Only ever reachable behind the authenticated boundary."""
        return {
            "run_mode": self.run_mode.value,
            "local_only": self.settings.local_only,
            "version": "v1",
            "host": self.telemetry(),
        }

    # ------------------------------------------------------------------ telemetry (P2)

    def telemetry(self) -> dict[str, object]:
        if not self._telemetry:
            self._telemetry = self._build_telemetry()
        return self._telemetry

    def _build_telemetry(self) -> dict[str, object]:
        runtime = self._event_runtime
        return {
            "instance_id": self.instance_id,
            "state": self._state.value,
            "uptime_seconds": (
                None
                if self._started_monotonic is None
                else round(time.monotonic() - self._started_monotonic, 3)
            ),
            "timestamps": {
                "created_at": self._created_at.isoformat(),
                "started_at": _iso(self._started_at),
                "recovery_ready_at": _iso(self._recovery_ready_at),
                "degraded_at": _iso(self._degraded_at),
                "stop_requested_at": _iso(self._stop_requested_at),
                "stopped_at": _iso(self._stopped_at),
                "last_heartbeat_at": _iso(self._last_heartbeat_at),
                "last_reconciliation_at": _iso(self._last_reconciliation_at),
                "last_frame_at": _iso(self._last_frame_at),
                "last_bbo_at": _iso(self._last_bbo_at),
            },
            "process": self._process_probe(),
            "tasks": {
                "event_loop_task_count": _event_loop_task_count(),
                "host_children_live": sorted(self._children_live),
                "host_children_live_count": len(self._children_live),
            },
            "eventruntime": (None if runtime is None else runtime.telemetry_snapshot()),
            "scanner_pipeline": (
                None if self._pipeline is None else self._pipeline.telemetry_snapshot()
            ),
            "lanes": {
                "safety": {name: lane.telemetry() for name, lane in self._safety_lanes.items()},
                "scanner": self._scanner_lane.telemetry(),
            },
            "counters": {
                "market_frames": self._market_frames,
                "trade_frames": self._trade_frames,
                "ingress_forwarded_to_safety": self._ingress_forwarded,
                "safety_processed": self._safety_processed,
                "safety_overflow": self._safety_overflow_count,
                "scanner_processed": self._scanner_processed,
                "scanner_rejected": self._scanner_rejections,
                "scanner_event_errors": self._scanner_errors,
                "scanner_event_error_samples": list(self._scanner_error_samples)[:8],
                "eventruntime_worker_exits": self._eventruntime_worker_exits,
                "host_invariant_violations": self._invariant_violations,
                "telemetry_errors": self._telemetry_errors,
                "shutdown_escalated": self._shutdown_escalated,
                "shutdown_failures": list(self._shutdown_failures),
            },
            "market_state": self._market.telemetry(self.required_instruments()),
            "provider": self._provider_telemetry(),
            "database": self._database_telemetry(),
            "reconciliation": {
                "startup_ok": self._startup_reconciliation_ok,
                "last_ok": self._reconciliation_ok,
                "last_result": self._last_reconciliation_result,
                "diagnostics": list(self._last_reconciliation_diagnostics),
                "safe_mode_latched_by_host": self._safe_mode_latch_applied,
            },
            "durable_state": {
                "system_state": (
                    None if self._durable_system_state is None else self._durable_system_state.value
                ),
                "operator_state": (
                    None
                    if self._durable_operator_state is None
                    else self._durable_operator_state.value
                ),
                "blocking_incidents": self._blocking_incident_count,
            },
            "safety_reevaluation": {
                "enabled": False,
                "inflight": 0,
                "note": "ai_reevaluation_disabled_in_host_core_v1",
            },
            "readiness": self.readiness().as_payload(),
        }

    def _provider_telemetry(self) -> dict[str, object]:
        if self._provider is None:
            return {"status": "NOT_STARTED"}
        return {
            "status": (
                "LIVE"
                if self._provider_stream_live()
                else ("STOPPED" if self._provider_stopped.is_set() else "NOT_STARTED")
            ),
            "connection_attempts": _safe_getattr(self._provider, "connection_attempts"),
            "reconnects": _safe_getattr(self._provider, "reconnects"),
            "constructed_by_host": self._provider_constructed,
            "subscriptions": self.subscriptions,
        }

    def _database_telemetry(self) -> dict[str, object]:
        pool_state: dict[str, object] = {
            "checked_in": "UNAVAILABLE",
            "checked_out": "UNAVAILABLE",
            "overflow": "UNAVAILABLE",
            "size": "UNAVAILABLE",
        }
        db = self._db
        if db is not None:
            pool = getattr(db.engine, "pool", None)
            if pool is not None:
                for key, method in (
                    ("checked_in", "checkedin"),
                    ("checked_out", "checkedout"),
                    ("overflow", "overflow"),
                    ("size", "size"),
                ):
                    pool_state[key] = _safe_call(pool, method)
        return {
            # Counts and a redacted identity only: never a DSN, user, password or query.
            "application_name": self.database_application_name,
            "engine_disposed": None if db is None else db.disposed,
            "owns_engine": self._owns_database,
            "pool": pool_state,
            "singleton_lock": {
                "held": self._lock_held,
                "connection_present": self._lock_connection is not None,
                "lost": self._lock_lost,
            },
        }

    def _process_probe(self) -> dict[str, object]:
        unavailable = {
            "rss_mb": "UNAVAILABLE",
            "rss_bytes": "UNAVAILABLE",
            "tcp_socket_count": "UNAVAILABLE",
            "handle_count": "UNAVAILABLE",
        }
        if psutil is None:
            return unavailable
        try:
            process = psutil.Process()
            rss = int(process.memory_info().rss)
            return {
                "rss_bytes": rss,
                "rss_mb": round(rss / (1024 * 1024), 3),
                "tcp_socket_count": _safe_call(process, "net_connections", kind="tcp", length=True),
                "handle_count": _handle_count(process),
            }
        except Exception:  # noqa: BLE001 - a failed probe is UNAVAILABLE, never zero
            return unavailable

    # ------------------------------------------------------------------ shutdown

    def _record_cleanup_failure(self, label: str, exc: BaseException) -> None:
        """Record one sanitized cleanup failure. Never swallowed, never re-raised."""
        self._shutdown_failures.append(f"{label}:{type(exc).__name__}")

    async def _attempt_cleanup(self, label: str, action: Callable[[], Awaitable[None]]) -> None:
        """Run one mandatory cleanup step; a failure is recorded and the next step still runs.

        Cleanup steps are deliberately independent: one broken step must never prevent the
        others from returning a lock, a connection or an engine. A failure is *recorded*, which
        is what later turns the terminal state into `STOP_FAILED` instead of a false `STOPPED`.
        """
        try:
            await action()
        except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
            self._record_cleanup_failure(label, exc)

    async def stop(self) -> None:
        """Accepted dependency-reverse shutdown. Bounded, ordered and idempotent.

        A second call is cleanup, not a second shutdown: it never double-disposes a
        resource and never reports the first stop's failures as a clean stop. A cancellation
        that arrives mid-shutdown does not escape early — it is recorded, the shielded final
        disposal still runs, and only then is it propagated.
        """
        if self._stop_completed:
            return
        async with self._stop_lock:
            if self._stop_completed:
                return
            await self._shutdown()

    async def _shutdown(self) -> None:
        self._shutting_down = True
        self._stop_requested_at = self.clock.now()
        self._risk_admission_open = False
        self._health.set(
            HealthComponent.EXECUTION.value, HealthStatus.UNAVAILABLE.value, reason="shutting_down"
        )
        if self._legal(self._state, HostLifecycleState.STOPPING):
            self._transition(HostLifecycleState.STOPPING)

        deadline = time.monotonic() + self.settings.runtime_shutdown_grace_seconds
        # A cancellation arriving in the graceful phase is *recorded*, never propagated yet:
        # the mandatory final disposal below must still run. Re-raising here is exactly how a
        # cancelled shutdown used to abandon the singleton lock, its connection and the engine;
        # the cancellation leaves only after a truthful terminal state exists.
        cancelled: BaseException | None = None

        try:
            # 1 — risk-increasing admission is already closed above.
            # 2 — there is no advisory work in Host Core V1 (G2→G3 handoff is deferred).
            # 3 — stop new market ingress, then cancel and close the provider stream.
            self._ingress_open = False
            scope = self._ingress_cancel_scope
            if scope is not None:
                scope.cancel()
            if scope is not None:
                await self._drain(
                    "provider_stream",
                    lambda: (
                        self._provider_stopped.is_set()
                        or not self._child_ever_started("provider_stream")
                    ),
                    deadline,
                )

            # 4 — close the safety send ends, then drain accepted per-instrument BBOs.
            self._safety_admission_open = False
            safety_names = [f"safety:{item}" for item in self.instruments]
            await self._drain(
                "safety_lanes",
                lambda: all(
                    (not self._child_ever_started(name)) or name not in self._children_live
                    for name in safety_names
                ),
                deadline,
            )

            # 5 — close the scanner send end last; its own child drains and then stops the
            #     EventRuntime so the accepted queue/futures reach a terminal state.
            self._scanner_admission_open = False
            await self._drain(
                "scanner_lane",
                lambda: (
                    "scanner" not in self._children_live or not self._child_ever_started("scanner")
                ),
                deadline,
            )

            # 6 — stop the loops and monitors, releasing the supervisor to collect them.
            self._loops_stop.set()
            self._supervisor_stop_requested.set()
            loop_names = ["heartbeat", "reconciliation", "telemetry", "eventruntime_monitor"]
            await self._drain(
                "host_loops",
                lambda: all(
                    (not self._child_ever_started(name)) or name not in self._children_live
                    for name in loop_names
                ),
                deadline,
            )

            # 7 — verify no Host-owned child remains; cancel stragglers at grace expiry.
            #     Cancellation is escalation and is reported, never called a clean stop.
            supervisor = self._supervisor_task
            if supervisor is not None and supervisor is not asyncio.current_task():
                with anyio.move_on_after(self._remaining(deadline)) as grace_scope:
                    with contextlib.suppress(BaseException):
                        await supervisor
                if grace_scope.cancel_called:
                    self._shutdown_escalated = True
                    self._shutdown_failures.append("host_children_shutdown_deadline_exceeded")
                    supervisor.cancel()
                    with contextlib.suppress(BaseException):
                        await supervisor
            if self._children_live:
                self._shutdown_escalated = True
                self._shutdown_failures.append(
                    "host_children_remained:" + ",".join(sorted(self._children_live))
                )

            # 8 — final detector-only reconciliation while DB access is still permitted.
            #     A mismatch is reported and latched; no economic fact is ever repaired.
            if self._recovery is not None and self._remaining(deadline) > 0.0:
                with anyio.move_on_after(self._remaining(deadline)) as final_scope:
                    try:
                        report = await self._reconcile(self.run_mode)
                        self._last_reconciliation_at = self.clock.now()
                        self._last_reconciliation_result = "OK" if report.ok else "MISMATCH"
                        self._last_reconciliation_diagnostics = list(report.diagnostics)[:8]
                        if not report.ok:
                            self._reconciliation_ok = False
                    except Exception as exc:  # noqa: BLE001 - reported, never repaired
                        self._shutdown_failures.append(
                            f"final_reconciliation_failed:{type(exc).__name__}"
                        )
                if final_scope.cancel_called:
                    self._shutdown_failures.append("final_reconciliation_deadline_exceeded")

            # 9 — close remaining provider resources, then clear market-state references.
            await self._close_remaining_stream()
            self._market.clear()
        except BaseException as exc:  # noqa: BLE001 - recorded here, propagated at the end
            if isinstance(exc, anyio.get_cancelled_exc_class()):
                cancelled = exc
                self._shutdown_escalated = True
                self._shutdown_failures.append("shutdown_cancelled")
            else:
                self._shutdown_failures.append(f"shutdown_sequence:{type(exc).__name__}")

        # 10 — shielded final region. This is the one region a cancellation may not skip: the
        #      graceful phase above may have been interrupted or have exhausted its deadline,
        #      and what still has to happen is exactly what a "clean stop" claims — every child
        #      collected, every owned resource returned, and a terminal state that tells the
        #      truth. Establishing that state *inside* the shield is what keeps a cancellation
        #      that arrives here from leaving a Host stuck in `STOPPING` while presenting
        #      itself as stopped.
        with anyio.CancelScope(shield=True):
            # 10a — collect whatever child the graceful phase did not manage to stop, so a
            #       cancelled or interrupted shutdown can never return while a supervisor task
            #       group is still running behind it.
            await self._force_children_down(self.settings.runtime_shutdown_dispose_seconds)
            # 10b — mandatory disposal (close, unlock, close, dispose), itself bounded by
            #       `runtime_shutdown_dispose_seconds` so a wedged socket or pool can never
            #       make `stop()` return never.
            with anyio.move_on_after(self.settings.runtime_shutdown_dispose_seconds) as reserve:
                await self._dispose_resources()
            if reserve.cancel_called:
                self._shutdown_failures.append("dispose_reserve_deadline_exceeded")

            # 11 — a truthful terminal state, established before any recorded cancellation is
            #      allowed to leave. An escalated or failure-recording stop reports
            #      `STOP_FAILED`; it is never dressed up as a clean `STOPPED`.
            self._stopped_at = self.clock.now()
            self._stop_completed = True
            escalated = self._shutdown_escalated or bool(self._shutdown_failures)
            target = HostLifecycleState.STOP_FAILED if escalated else HostLifecycleState.STOPPED
            if self._legal(self._state, target):
                self._transition(target)
            else:
                self._state = target
            self._telemetry = self._build_telemetry()

        if cancelled is not None:
            # Every mandatory disposal has been attempted and the terminal state is truthful;
            # only now does the cancellation leave. It stays recorded in `shutdown_failures`,
            # so a cancelled shutdown can never present itself as a clean `STOPPED`.
            raise cancelled

    async def _force_children_down(self, budget: float) -> None:
        """Escalation reserve: no Host-owned child may outlive `stop()`.

        The graceful phase normally collects every child through the ordered admissions, and
        this method is then a no-op. It exists for the two paths that cannot rely on that: a
        cancellation delivered mid-shutdown, and a graceful phase that exhausted its deadline.
        Both would otherwise let `stop()` return while the supervisor task group — with its
        loops and workers — is still running, which is exactly the orphan the accepted
        forced-shutdown property forbids. Escalation is always *recorded*, never silent, and
        bounded by `budget` so this reserve cannot become an unbounded join.
        """
        self._loops_stop.set()
        self._supervisor_stop_requested.set()
        supervisor = self._supervisor_task
        if supervisor is None or supervisor is asyncio.current_task():
            return
        if not supervisor.done():
            # Prefer graceful collection: setting the stop events already ends every loop at
            # its next boundary. Only a group that outlives the budget is cancelled, which is
            # escalation and is reported as such.
            with anyio.move_on_after(budget):
                with contextlib.suppress(BaseException):
                    await supervisor
            if not supervisor.done():
                self._shutdown_escalated = True
                if "host_children_shutdown_deadline_exceeded" not in self._shutdown_failures:
                    self._shutdown_failures.append("host_children_shutdown_deadline_exceeded")
                supervisor.cancel()
                with anyio.move_on_after(budget) as join_scope:
                    with contextlib.suppress(BaseException):
                        await supervisor
                if join_scope.cancel_called:
                    entry = "supervisor_join_deadline_exceeded"
                    if entry not in self._shutdown_failures:
                        self._shutdown_failures.append(entry)
        if self._children_live:
            self._shutdown_escalated = True
            entry = "host_children_remained:" + ",".join(sorted(self._children_live))
            if entry not in self._shutdown_failures:
                self._shutdown_failures.append(entry)

    def _remaining(self, deadline: float) -> float:
        return max(0.0, deadline - time.monotonic())

    async def _drain(self, label: str, predicate: Callable[[], bool], deadline: float) -> bool:
        """Bounded wait for one shutdown stage. Never an unbounded join."""
        ok = await self._await_until(predicate, self._remaining(deadline))
        if not ok:
            self._shutdown_escalated = True
            self._shutdown_failures.append(f"drain_deadline_exceeded:{label}")
        return ok

    async def _await_until(self, predicate: Callable[[], bool], timeout: float) -> bool:
        limit = time.monotonic() + max(0.0, timeout)
        while True:
            if predicate():
                return True
            remaining = limit - time.monotonic()
            if remaining <= 0.0:
                return predicate()
            await anyio.sleep(min(POLL_INTERVAL_SECONDS, max(0.01, remaining)))

    async def _close_remaining_stream(self) -> None:
        """Close whatever provider stream reference is still held, exactly once."""
        remaining_stream, self._stream = self._stream, None
        if remaining_stream is not None:
            await self._close_stream(remaining_stream)

    async def _dispose_resources(self) -> None:
        """Final disposal of everything the Host owns. Every step is attempted and reported.

        Order is dependency-reverse: provider, then the singleton lock (before the engine it
        was opened against), then the owned engine. A failure in any step is recorded and never
        prevents the remaining steps, because a Host that returns *some* resources while
        claiming it returned all of them is the dishonesty this contract exists to prevent.
        """
        await self._attempt_cleanup("provider_close_failed", self._close_remaining_stream)
        await self._attempt_cleanup("singleton_release_failed", self._release_singleton_lock)
        self._task_group = None
        db, self._db = self._db, None
        self._sessions = None
        if db is not None and self._owns_database:
            if db.disposed:
                self._shutdown_failures.append("engine_disposed_twice")
            else:
                dispose_failure: str | None = None
                try:
                    await db.dispose()
                except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                    dispose_failure = f"engine_dispose_failed:{type(exc).__name__}"
                if dispose_failure is not None:
                    self._shutdown_failures.append(dispose_failure)
                elif not db.disposed:
                    # `dispose()` returned without raising yet still reports an undisposed
                    # engine: the truthful flag is the authority, not the call's success.
                    self._shutdown_failures.append("engine_dispose_incomplete")
        self._event_runtime = None
        self._pipeline = None
        self._event_runtime = None
        self._pipeline = None


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat()


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def _as_utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _as_int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _positive_finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return number > 0.0 and math.isfinite(number)


def _event_loop_task_count() -> int | str:
    try:
        return len(asyncio.all_tasks())
    except RuntimeError:  # pragma: no cover - only reachable without a running loop
        return "UNAVAILABLE"


def _safe_getattr(target: object, name: str) -> object:
    try:
        return getattr(target, name)
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE"


def _safe_call(target: object, method: str, **kwargs: object) -> object:
    function = getattr(target, method, None)
    if not callable(function):
        return "UNAVAILABLE"
    try:
        result = function(**kwargs)
    except Exception:  # noqa: BLE001
        return "UNAVAILABLE"
    if kwargs.get("length") and result is not None:
        try:
            return len(result)
        except TypeError:  # pragma: no cover - defensive
            return "UNAVAILABLE"
    return result


def _handle_count(process: object) -> object:
    for name in ("num_handles", "num_fds"):
        value = _safe_call(process, name)
        if value != "UNAVAILABLE":
            return value
    return "UNAVAILABLE"
