import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

logger = logging.getLogger(__name__)


class HostLifecycleState(StrEnum):
    """In-memory lifecycle facts of the single integrated Runtime Host.

    These are deliberately NOT aliases of the durable G4 ``SystemState``: a Host may be
    ``READY`` while the durable business state is ``SAFE_MODE`` is false, and the two are
    evaluated separately. Readiness derives from both.
    """

    CREATED = "CREATED"
    STARTING = "STARTING"
    ACQUIRING_SINGLETON = "ACQUIRING_SINGLETON"
    RECOVERY_INGRESS = "RECOVERY_INGRESS"
    RECOVERING = "RECOVERING"
    STARTING_RUNTIME = "STARTING_RUNTIME"
    WAITING_FOR_READINESS = "WAITING_FOR_READINESS"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAIL_CLOSED = "FAIL_CLOSED"
    FAILED = "FAILED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    STOP_FAILED = "STOP_FAILED"


class HostReadinessStatus(StrEnum):
    """Honest readiness surface. `READY` is a conjunction, never a default."""

    READY = "READY"
    NOT_READY = "NOT_READY"
    DEGRADED = "DEGRADED"
    FAIL_CLOSED = "FAIL_CLOSED"


#: Stable, non-secret reason codes. Health responses expose only these, never a DSN,
#: credential, query text or exception message.
READINESS_HOST_DISABLED = "HOST_DISABLED"
READINESS_HOST_NOT_READY = "HOST_NOT_READY"
READINESS_RISK_ADMISSION_CLOSED = "RISK_ADMISSION_CLOSED"
READINESS_SINGLETON_LOCK_NOT_HELD = "SINGLETON_LOCK_NOT_HELD"
READINESS_DB_UNAVAILABLE = "DB_UNAVAILABLE"
READINESS_RISK_GATE_UNHEALTHY = "RISK_GATE_HEALTH_BLOCKING"
READINESS_HEARTBEAT_STALE = "HEARTBEAT_STALE"
READINESS_RECOVERY_INCOMPLETE = "RECOVERY_INCOMPLETE"
READINESS_RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
READINESS_BLOCKING_INCIDENT = "BLOCKING_INCIDENT_OPEN"
READINESS_DURABLE_STATE_INVALID = "DURABLE_STATE_INVALID"
READINESS_MARKET_DATA_STALE = "MARKET_DATA_STALE"
READINESS_PROVIDER_STREAM_DOWN = "PROVIDER_STREAM_DOWN"
READINESS_WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"
READINESS_SAFETY_OVERFLOW = "SAFETY_QUEUE_OVERFLOW"
READINESS_HOST_INVARIANT = "HOST_INVARIANT_VIOLATION"


@dataclass(frozen=True)
class HostReadinessReport:
    """One readiness evaluation: a boolean, an honest status and stable reason codes."""

    ready: bool
    status: HostReadinessStatus
    reasons: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_payload(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class HealthRegistry:
    checks: dict[str, dict[str, object]] = field(default_factory=dict)

    def set(self, name: str, status: str, **details: object) -> None:
        self.checks[name] = {"status": status, **details, "updated_at": datetime.now(UTC).isoformat()}

    def snapshot(self) -> dict[str, dict[str, object]]:
        return dict(self.checks)

    def status(self, name: str, default: str = "HEALTHY") -> str:
        entry = self.checks.get(name)
        return str(entry["status"]) if entry else default

    def blocking(self, names: frozenset[str] | set[str] | tuple[str, ...]) -> list[str]:
        """Names whose status is not healthy. Used by the G4 risk gate for admission control."""
        return [name for name in names if self.status(name) != "HEALTHY"]

    def all_healthy(self, names: frozenset[str] | set[str] | tuple[str, ...]) -> bool:
        return not self.blocking(names)


@dataclass
class GlobalRuntimeState:
    run_mode: str
    health: HealthRegistry = field(default_factory=HealthRegistry)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


async def supervised_worker(name: str, worker: Callable[[], Awaitable[None]], health: HealthRegistry) -> None:
    """Isolate one worker exception and report it without cancelling the runtime."""
    try:
        await worker()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - exercised by integration harness
        logger.exception("worker_failed", extra={"worker": name})
        health.set(name, "FAILED", error=type(exc).__name__)

