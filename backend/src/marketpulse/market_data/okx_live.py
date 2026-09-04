import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import websockets

from .base import MarketDataProvider
from .models import AuxiliaryContext, DataQuality, Instrument, MarketType, NormalizedMarketEvent
from .normalizer import instrument_from_okx, normalize_book_ticker, normalize_kline, normalize_trade

logger = logging.getLogger(__name__)


class OKXLiveProvider(MarketDataProvider):
    def __init__(self, rest_url: str = "https://www.okx.com", ws_url: str = "wss://ws.okx.com:8443/ws/v5/public", business_ws_url: str = "wss://ws.okx.com:8443/ws/v5/business", reconnect_delay: float = 1.0, disconnect_after_events: int | None = None):
        self.rest_url = rest_url.rstrip("/")
        self.ws_url = ws_url
        self.business_ws_url = business_ws_url
        self.reconnect_delay = reconnect_delay
        self.disconnect_after_events = disconnect_after_events
        self.connection_attempts = 0
        self.reconnects = 0
        self._instruments: dict[str, Instrument] = {}

    async def instruments(self, market_type: str = "SPOT") -> list[Instrument]:
        async with httpx.AsyncClient(base_url=self.rest_url, timeout=15) as client:
            response = await client.get("/api/v5/public/instruments", params={"instType": market_type})
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "0":
            raise RuntimeError(f"OKX instruments error: {payload}")
        result = [instrument_from_okx(item) for item in payload.get("data", [])]
        self._instruments.update({item.instrument_id: item for item in result})
        return result

    async def spot_tickers(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(base_url=self.rest_url, timeout=15) as client:
            response = await client.get("/api/v5/market/tickers", params={"instType": "SPOT"})
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "0":
            raise RuntimeError(f"OKX tickers error: {payload}")
        return list(payload.get("data", []))

    async def auxiliary_context(self, instrument_id: str) -> AuxiliaryContext:
        inst = self._instruments.get(instrument_id)
        if not inst or inst.market_type is MarketType.SPOT:
            return AuxiliaryContext(instrument_id=instrument_id, market_type=MarketType.SPOT, availability_reason="spot_has_no_swap_context")
        async with httpx.AsyncClient(base_url=self.rest_url, timeout=15) as client:
            oi_response, funding_response = await asyncio.gather(
                client.get("/api/v5/public/open-interest", params={"instType": "SWAP", "instId": instrument_id}),
                client.get("/api/v5/public/funding-rate", params={"instId": instrument_id}),
                return_exceptions=True,
            )
        oi = None
        funding_rate = None
        if isinstance(oi_response, httpx.Response) and oi_response.is_success:
            payload = oi_response.json()
            if payload.get("code") == "0" and payload.get("data"):
                oi = float(payload["data"][0].get("oi", 0))
        if isinstance(funding_response, httpx.Response) and funding_response.is_success:
            payload = funding_response.json()
            if payload.get("code") == "0" and payload.get("data"):
                funding_rate = float(payload["data"][0].get("fundingRate", 0))
        quality = DataQuality.FRESH if oi is not None or funding_rate is not None else DataQuality.UNAVAILABLE
        reason = "okx_oi_funding_available" if quality is DataQuality.FRESH else "okx_oi_funding_unavailable"
        return AuxiliaryContext(instrument_id=instrument_id, market_type=inst.market_type, oi=oi, funding_rate=funding_rate, data_quality=quality, availability_reason=reason)

    async def context(self, instrument_id: str) -> AuxiliaryContext:
        """Liquidation provider boundary: preserve explicit availability when OKX has no payload."""
        return await self.auxiliary_context(instrument_id)

    async def _receive_once(self, channels: list[dict[str, str]]) -> AsyncIterator[NormalizedMarketEvent]:
        self.connection_attempts += 1
        emitted = 0
        endpoint = self.business_ws_url if any(item.get("channel", "").startswith("candle") for item in channels) else self.ws_url
        async with websockets.connect(endpoint, ping_interval=20, ping_timeout=20, close_timeout=5) as websocket:
            await websocket.send(json.dumps({"op": "subscribe", "args": channels}))
            async for message in websocket:
                payload: dict[str, Any] = json.loads(message)
                if payload.get("event") in {"subscribe", "unsubscribe"} or payload.get("arg", {}).get("channel") is None:
                    continue
                arg = payload.get("arg", {})
                inst = self._instruments.get(arg.get("instId"))
                if not inst:
                    logger.warning("unknown_instrument_event", extra={"instrument_id": arg.get("instId"), "arg": arg})
                    continue
                channel = arg.get("channel")
                for raw in payload.get("data", []):
                    if channel == "trades":
                        yield normalize_trade(raw, inst)
                    elif channel == "bbo-tbt":
                        yield normalize_book_ticker(raw, inst)
                    elif channel == "candle1m":
                        yield normalize_kline(raw, inst)
                    emitted += 1
                    if self.disconnect_after_events and emitted >= self.disconnect_after_events:
                        raise ConnectionError("verification_disconnect")

    async def stream(self, channels: list[dict[str, str]]) -> AsyncIterator[NormalizedMarketEvent]:
        """Reconnect indefinitely; callers own cancellation and can dedupe by event identity."""
        while True:
            try:
                async for event in self._receive_once(channels):
                    yield event
            except asyncio.CancelledError:
                raise
            except Exception:
                self.reconnects += 1
                logger.exception("okx_stream_disconnected")
                await asyncio.sleep(self.reconnect_delay)
