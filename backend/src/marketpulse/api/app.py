import logging

from fastapi import Depends, FastAPI

from marketpulse.api.auth import router as auth_router
from marketpulse.api.auth import verify_session
from marketpulse.api.market import router as market_router
from marketpulse.config import get_settings
from marketpulse.logging_config import configure_logging
from marketpulse.runtime import GlobalRuntimeState

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
runtime_state = GlobalRuntimeState(run_mode=settings.run_mode)
runtime_state.health.set("backend", "HEALTHY", local_only=settings.local_only)

app = FastAPI(title="MarketPulse AI API", version="v1-group1")
app.include_router(auth_router)
app.include_router(market_router)


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict[str, object]:
    return {"status": "ok", "run_mode": runtime_state.run_mode, "local_only": settings.local_only, "checks": runtime_state.health.snapshot()}


@app.get("/api/v1/runtime", tags=["system"])
async def runtime(_: str = Depends(verify_session)) -> dict[str, object]:
    return {"run_mode": runtime_state.run_mode, "local_only": settings.local_only, "version": "v1"}


@app.get("/api/v1/protected/ping", tags=["system"])
async def protected_ping(_: str = Depends(verify_session)) -> dict[str, str]:
    return {"status": "authenticated"}
