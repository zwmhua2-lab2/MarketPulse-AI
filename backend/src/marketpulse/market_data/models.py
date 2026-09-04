from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class MarketType(StrEnum):
    SPOT = "SPOT"
    SWAP = "SWAP"


class DataQuality(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class Instrument(BaseModel):
    exchange: str = "OKX"
    base_asset: str
    quote_asset: str
    market_type: MarketType
    instrument_id: str
    trading_symbol: str
    tradable: bool = True
    tick_size: float | None = None
    lot_size: float | None = None


class NormalizedMarketEvent(BaseModel):
    exchange: str = "OKX"
    base_asset: str
    quote_asset: str
    market_type: MarketType
    instrument_id: str
    event_time: datetime
    received_time: datetime
    source: str
    freshness: DataQuality = DataQuality.FRESH
    data_quality: DataQuality = DataQuality.FRESH


class NormalizedTrade(NormalizedMarketEvent):
    trade_id: str
    price: float
    quantity: float
    side: str


class NormalizedBookTicker(NormalizedMarketEvent):
    bid_price: float
    bid_quantity: float
    ask_price: float
    ask_quantity: float


class NormalizedKline(NormalizedMarketEvent):
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    confirmed: bool


class AuxiliaryContext(BaseModel):
    instrument_id: str
    market_type: MarketType
    oi: float | None = None
    funding_rate: float | None = None
    liquidation: dict[str, Any] | None = None
    data_quality: DataQuality = DataQuality.UNAVAILABLE
    availability_reason: str = "provider_not_available"


def freshness_status(received_time: datetime, now: datetime, max_age_seconds: float) -> DataQuality:
    age = (now - received_time).total_seconds()
    return DataQuality.FRESH if age <= max_age_seconds else DataQuality.STALE

