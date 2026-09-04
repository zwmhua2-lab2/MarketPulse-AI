"""Bounded Group 2 persistence verification against local PostgreSQL only."""
import asyncio
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from marketpulse.db.models import MarketEventRecord, SignalTimelineRecord
from marketpulse.g2.models import EventType, FeatureSnapshot, MarketEvent
from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.runtime import EventRuntime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    engine = create_async_engine("postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5432/marketpulse")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    event = MarketEvent(event_id=f"g2-local-verification-{int(now.timestamp())}", symbol="BTC-USDT", instrument_id="BTC-USDT", market_type="SPOT", event_type=EventType.VOLUME_ANOMALY, event_time=now, received_time=now, source="verification.fixture", strength=0.8, priority=80, state_version=0, config_version="g2-v1", payload={"verification": True})
    features = FeatureSnapshot(instrument_id="BTC-USDT", symbol="BTC-USDT", market_type="SPOT", event_time=now, current_price=100_000, short_return=0.01, buy_sell_imbalance=0.8)
    runtime = EventRuntime(PostgresG2Repository(factory))
    await runtime.start()
    first = await runtime.publish(event, features)
    duplicate = await runtime.publish(event, features)
    await runtime.stop()
    async with factory() as session:
        event_count = await session.scalar(select(func.count()).select_from(MarketEventRecord).where(MarketEventRecord.event_id == event.event_id))
        timeline_count = await session.scalar(select(func.count()).select_from(SignalTimelineRecord).where(SignalTimelineRecord.event_id == event.event_id))
    await engine.dispose()
    print({"first_persisted": first.persisted, "duplicate_persisted": duplicate.persisted, "market_event_rows": event_count, "timeline_rows": timeline_count, "worker_exceptions": len(runtime.worker_exceptions)})


if __name__ == "__main__":
    asyncio.run(main())
