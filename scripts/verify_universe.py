"""Build a bounded V1 Universe from real public market-cap and OKX Spot data."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.universe.service import build_live_universe


async def main() -> None:
    result = await build_live_universe(OKXLiveProvider(), ["BTC-USDT", "ETH-USDT", "NOT-A-LIVE-SYMBOL"])
    print(json.dumps({"universe": "PASS" if len(result.symbols) > 0 else "FAIL", "count": len(result.symbols), "unique": len(result.symbols) == len(set(result.symbols)), "sample": result.symbols[:10], "manual_invalid_filtered": "NOT-A-LIVE-SYMBOL" not in result.symbols}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

