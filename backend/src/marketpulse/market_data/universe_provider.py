from collections.abc import Iterable

import httpx


class CoinGeckoMarketUniverseProvider:
    """Small public market-cap boundary; symbols are later filtered by OKX Spot."""

    def __init__(self, base_url: str = "https://api.coingecko.com/api/v3"):
        self.base_url = base_url.rstrip("/")

    async def market_cap_top(self, limit: int = 100) -> list[str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15) as client:
            response = await client.get("/coins/markets", params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": limit, "page": 1, "sparkline": "false"})
            response.raise_for_status()
            return [str(item["symbol"]).upper() + "-USDT" for item in response.json() if item.get("symbol")]


def normalize_watchlist(values: Iterable[str]) -> list[str]:
    return [value.strip().upper() for value in values if value.strip()]

