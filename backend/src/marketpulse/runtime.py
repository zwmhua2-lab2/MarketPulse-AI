import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


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

