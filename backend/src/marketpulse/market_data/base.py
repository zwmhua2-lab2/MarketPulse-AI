from collections.abc import AsyncIterator
from typing import Protocol

from .models import AuxiliaryContext, Instrument, NormalizedMarketEvent


class MarketDataProvider(Protocol):
    async def instruments(self, market_type: str = "SPOT") -> list[Instrument]: ...

    def stream(self, channels: list[dict[str, str]]) -> AsyncIterator[NormalizedMarketEvent]: ...


class MarketUniverseProvider(Protocol):
    async def market_cap_top(self, limit: int = 100) -> list[str]: ...


class LiquidationDataProvider(Protocol):
    async def context(self, instrument_id: str) -> AuxiliaryContext: ...

