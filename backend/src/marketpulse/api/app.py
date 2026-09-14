"""FastAPI application boundary.

The application owns no long-lived runtime resource of its own. Exactly one
:class:`~marketpulse.runtime_host.RuntimeHost` is constructed and entered by the ``lifespan``
context below, and that context is the only activation boundary the accepted PRE-01B-D1
contract permits. The Host is deliberately *not* a process supervisor: it never restarts
its own critical child and it never restarts the process.

Three response surfaces are kept strictly distinct:

* ``/api/v1/live``    — liveness only. The ASGI process and Host control path are alive.
                        Says nothing about trading readiness, so it stays ``200``.
* ``/api/v1/ready``   — readiness. ``200`` only when every risk-increasing prerequisite
                        currently holds, otherwise ``503``.
* ``/api/v1/health``  — the accepted health payload, honest about DEGRADED / FAIL_CLOSED.

Detailed telemetry stays behind the pre-existing authenticated ``/api/v1/runtime``
boundary, and Host-owned objects stay in ``app.state`` — they are never serialized.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response

from marketpulse.api.auth import router as auth_router
from marketpulse.api.auth import verify_session
from marketpulse.api.market import router as market_router
from marketpulse.config import get_settings
from marketpulse.logging_config import configure_logging
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import RuntimeHost

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

#: The single ``app.state`` slot the Host lives in. Read-only for every request handler.
HOST_STATE_KEY = "host"

DISABLED_STATUS = "disabled"
READY_STATUS_CODE = 200
NOT_READY_STATUS_CODE = 503


def host_of(request: Request) -> RuntimeHost | None:
    """The Host for this process, or ``None`` when the Host is not enabled."""
    return getattr(request.app.state, HOST_STATE_KEY, None)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Enter and exit the single Runtime Host.

    Startup failure is fatal and fail-closed: the exception leaves this context, so the
    server never begins serving requests while the runtime is not actually owned. A
    terminal ``STOP_FAILED`` is surfaced as a shutdown error rather than being reported as
    a clean stop.
    """
    host: RuntimeHost | None = None
    if not settings.runtime_host_enabled:
        app.state.host = None
        logger.warning(
            "runtime_host_disabled",
            extra={"run_mode": settings.run_mode, "local_only": settings.local_only},
        )
    else:
        host = RuntimeHost(settings)
        app.state.host = host
        await host.start()
        logger.info(
            "runtime_host_started",
            extra={
                "instance_id": host.instance_id,
                "run_mode": host.run_mode.value,
                "state": host.state.value,
                "instruments": list(host.instruments),
            },
        )
    try:
        yield
    finally:
        if host is not None:
            await host.stop()
            if host.state is HostLifecycleState.STOP_FAILED:
                logger.critical(
                    "runtime_host_stop_failed",
                    extra={"instance_id": host.instance_id, "failures": host.ownership_snapshot()["shutdown_failures"]},
                )
                raise RuntimeError("runtime_host_stop_failed")


def create_app() -> FastAPI:
    application = FastAPI(title="MarketPulse AI API", version="v1-group1", lifespan=lifespan)
    application.include_router(auth_router)
    application.include_router(market_router)

    @application.get("/api/v1/live", tags=["system"])
    async def live(request: Request) -> dict[str, object]:
        """Liveness. Alive iff the process and Host control path are up."""
        host = host_of(request)
        if host is None:
            return {
                "status": DISABLED_STATUS,
                "run_mode": settings.run_mode,
                "local_only": settings.local_only,
            }
        return host.live_payload()

    @application.get("/api/v1/ready", tags=["system"])
    async def ready(request: Request, response: Response) -> dict[str, object]:
        """Readiness. ``200`` only when every risk-increasing prerequisite holds."""
        host = host_of(request)
        if host is None:
            response.status_code = NOT_READY_STATUS_CODE
            return {
                "ready": False,
                "run_mode": settings.run_mode,
                "local_only": settings.local_only,
                "reasons": ["HOST_DISABLED"],
            }
        payload = host.ready_payload()
        if not payload.get("ready"):
            response.status_code = NOT_READY_STATUS_CODE
        return payload

    @application.get("/api/v1/health", tags=["system"])
    async def health(request: Request) -> dict[str, object]:
        """Honest health: ``ok`` only when the Host is fully ready."""
        host = host_of(request)
        if host is None:
            return {
                "status": DISABLED_STATUS,
                "run_mode": settings.run_mode,
                "local_only": settings.local_only,
                "checks": {},
            }
        return host.health_payload()

    @application.get("/api/v1/runtime", tags=["system"])
    async def runtime(request: Request, _: str = Depends(verify_session)) -> dict[str, object]:
        """Detailed telemetry. Only ever reachable behind the authenticated boundary."""
        host = host_of(request)
        if host is None:
            return {
                "run_mode": settings.run_mode,
                "local_only": settings.local_only,
                "version": "v1",
                "host": {"status": DISABLED_STATUS},
            }
        return host.runtime_payload()

    @application.get("/api/v1/protected/ping", tags=["system"])
    async def protected_ping(_: str = Depends(verify_session)) -> dict[str, str]:
        return {"status": "authenticated"}

    return application


app = create_app()
