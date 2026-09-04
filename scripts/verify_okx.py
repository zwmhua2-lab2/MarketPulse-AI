"""Bounded real OKX Group 1 verification; no credentials and no trading endpoints."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from marketpulse.market_data.okx_live import OKXLiveProvider


async def collect(provider: OKXLiveProvider, channels: list[dict[str, str]], minimum: int) -> list[object]:
    result = []
    event_stream = provider.stream(channels)
    try:
        try:
            async with asyncio.timeout(20):
                async for event in event_stream:
                    result.append(event)
                    if len(result) >= minimum:
                        break
        except TimeoutError:
            pass
    finally:
        await event_stream.aclose()
    return result


async def main() -> None:
    provider = OKXLiveProvider()
    spot = await provider.instruments("SPOT")
    swaps = await provider.instruments("SWAP")
    btc = next(item for item in spot if item.instrument_id == "BTC-USDT" and item.tradable)
    swap = next(item for item in swaps if item.instrument_id == "BTC-USDT-SWAP" and item.tradable)
    auxiliary = await provider.auxiliary_context(swap.instrument_id)
    print(json.dumps({"rest": "PASS", "spot_count": len(spot), "swap_count": len(swaps), "spot": btc.model_dump(mode="json"), "swap": swap.model_dump(mode="json"), "auxiliary": auxiliary.model_dump(mode="json")}, ensure_ascii=False))

    trade_events = await collect(provider, [{"channel": "trades", "instId": btc.instrument_id}], 1)
    book_events = await collect(provider, [{"channel": "bbo-tbt", "instId": btc.instrument_id}], 1)
    kline_events = await collect(provider, [{"channel": "candle1m", "instId": btc.instrument_id}], 1)
    reconnect_provider = OKXLiveProvider(disconnect_after_events=1, reconnect_delay=0.1)
    await reconnect_provider.instruments("SPOT")
    reconnect_events = await collect(reconnect_provider, [{"channel": "trades", "instId": btc.instrument_id}], 2)
    events = trade_events + book_events + kline_events
    print(json.dumps({"websocket": "PASS" if len(events) == 3 else "NOT VERIFIED", "event_count": len(events), "event_types": sorted({type(event).__name__ for event in events}), "freshness": [event.freshness for event in events], "reconnect_events": len(reconnect_events), "connection_attempts": reconnect_provider.connection_attempts, "reconnects": reconnect_provider.reconnects, "reconnect_verification": "PASS" if reconnect_provider.reconnects and reconnect_provider.connection_attempts > 1 else "NOT VERIFIED"}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
