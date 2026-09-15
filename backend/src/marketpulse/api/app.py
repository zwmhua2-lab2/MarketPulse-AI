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

While the Host is running, its fatal outcome is a ``lifespan``-owned lifecycle result: the
lifespan awaits it, requests the OS process stop the accepted D1 contract leaves to the
external supervisor, and ends the run phase. A dead runtime can therefore never masquerade as
a healthy process that merely happens to be waiting for a shutdown.
"""

from __future__ import annotations

import logging
import signal
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
from fastapi import Depends, FastAPI, Request, Response

from marketpulse.api.auth import router as auth_router
from marketpulse.api.auth import verify_session
from marketpulse.api.market import router as market_router
from marketpulse.config import get_settings
from marketpulse.logging_config import configure_logging
from marketpulse.runtime import HostLifecycleState
from marketpulse.runtime_host import HostTerminalResult, RuntimeHost

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


def request_process_stop(reason: str) -> None:
    """Ask the OS to stop this process, so an external supervisor sees a nonzero exit.

    The accepted PRE-01B-D1 contract keeps process supervision *outside* the Host: the Host
    owns the in-process lifecycle and a deterministic exit signal, and the external OS/service
    layer watches the process exit code. Uvicorn maps ``SIGTERM`` into ASGI lifespan shutdown,
    so the request still runs the accepted shutdown path — it never bypasses cleanup, never
    restarts a child and never restarts the process.

    Refused when no server owns ``SIGTERM``: an unmapped ``SIGTERM`` terminates the interpreter
    immediately and would skip the cleanup this signal exists to precede.
    """
    if signal.getsignal(signal.SIGTERM) in (signal.SIG_DFL,):
        logger.error("runtime_host_process_stop_unmapped", extra={"reason": reason})
        return
    signal.raise_signal(signal.SIGTERM)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Enter and exit the single Runtime Host.

    Startup failure is fatal and fail-closed: the exception leaves this context, so the
    server never begins serving requests while the runtime is not actually owned.

    While running, the lifespan *owns* the Host's fatal outcome instead of leaving it to a
    detached background task. A critical child failure is therefore observed here, during the
    run phase, and not merely discovered when an external shutdown happens to arrive. The
    observation requests the OS process stop and also ends the run phase directly, so the
    failure reaches even an ASGI caller that never sends a shutdown of its own. A terminal
    ``STOP_FAILED`` is surfaced as a shutdown error rather than being reported as a clean stop.
    """
    host: RuntimeHost | None = None
    if not settings.runtime_host_enabled:
        app.state.host = None
        app.state.runtime_failure = None
        logger.warning(
            "runtime_host_disabled",
            extra={"run_mode": settings.run_mode, "local_only": settings.local_only},
        )
        yield
        return

    host = RuntimeHost(settings)
    app.state.host = host
    app.state.runtime_failure = None
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
    failure: HostTerminalResult | None = None
    try:
        async with anyio.create_task_group() as task_group:

            async def own_runtime_failure() -> None:
                """Lifespan-owned observation of a fatal Host completion."""
                nonlocal failure
                failure = await host.wait_for_terminal_result()
                app.state.runtime_failure = failure
                logger.critical(
                    "runtime_host_fatal",
                    extra={
                        "instance_id": host.instance_id,
                        "reason": failure.reason,
                        "state": failure.state.value,
                        "shutdown_failures": list(failure.shutdown_failures),
                    },
                )
                request_process_stop(failure.reason)
                task_group.cancel_scope.cancel()

            task_group.start_soon(own_runtime_failure)
            yield
            task_group.cancel_scope.cancel()
    finally:
        # The Host already ran its own bounded cleanup before publishing the result, but the
        # lifespan's own shutdown is shielded too: nothing may interrupt the disposal of what
        # this boundary owns. Only afterwards does the failure surface to the caller.
        with anyio.CancelScope(shield=True):
            await host.stop()
        if failure is not None:
            raise RuntimeError(f"runtime_host_fatal:{failure.reason}")
        if host.state is HostLifecycleState.STOP_FAILED:
            logger.critical(
                "runtime_host_stop_failed",
                extra={
                    "instance_id": host.instance_id,
                    "failures": host.ownership_snapshot()["shutdown_failures"],
                },
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
