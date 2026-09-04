"""Bounded real OKX Group 2 smoke: normalized trade to persisted market facts."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner, ScannerConfig
from marketpulse.market_data.okx_live import OKXLiveProvider
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    provider = OKXLiveProvider()
    instrument = next(item for item in await provider.instruments("SPOT") if item.instrument_id == "SOL-USDT")
    engine = create_async_engine("postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5432/marketpulse")
    runtime = EventRuntime(PostgresG2Repository(async_sessionmaker(engine, expire_on_commit=False)))
    pipeline = ScannerPipeline(OpportunityScanner(ScannerConfig(flow_imbalance_threshold=0.1)), runtime)
    await runtime.start()
    stream = provider.stream([{"channel": "trades", "instId": instrument.instrument_id}])
    try:
        async with asyncio.timeout(20):
            market_data = await anext(stream)
            outcomes = await pipeline.ingest(market_data)
    finally:
        await stream.aclose()
        await runtime.stop()
        await engine.dispose()
    print({"normalized_source": market_data.source, "feature_to_event_outcomes": len(outcomes), "persisted": [outcome.persisted for outcome in outcomes], "worker_exceptions": len(runtime.worker_exceptions)})


if __name__ == "__main__":
    asyncio.run(main())
