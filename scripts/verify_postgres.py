"""Verify a real PostgreSQL connection used by Alembic."""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    engine = create_async_engine("postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5432/marketpulse")
    async with engine.connect() as connection:
        version = (await connection.execute(text("select version()"))).scalar_one()
        tables = (await connection.execute(text("select count(*) from information_schema.tables where table_name = 'audit_events'"))).scalar_one()
    await engine.dispose()
    print({"postgres": "PASS", "audit_events_table": tables == 1, "version": version.split(",")[0]})


if __name__ == "__main__":
    asyncio.run(main())

