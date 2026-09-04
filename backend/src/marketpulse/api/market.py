from fastapi import APIRouter, Depends, Query

from marketpulse.api.auth import verify_session
from marketpulse.config import get_settings
from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.universe.service import build_live_universe

router = APIRouter(prefix="/api/v1", tags=["market-data"])


@router.get("/market/instruments")
async def instruments(market_type: str = Query("SPOT", pattern="^(SPOT|SWAP)$"), _: str = Depends(verify_session)):
    settings = get_settings()
    provider = OKXLiveProvider(settings.okx_rest_url, settings.okx_ws_url)
    return {"items": [item.model_dump(mode="json") for item in await provider.instruments(market_type)]}


@router.get("/universe")
async def universe(manual_watchlist: list[str] | None = Query(default=None), _: str = Depends(verify_session)):  # noqa: B008
    settings = get_settings()
    value = await build_live_universe(OKXLiveProvider(settings.okx_rest_url, settings.okx_ws_url), manual_watchlist or [])
    return value.model_dump(mode="json")
