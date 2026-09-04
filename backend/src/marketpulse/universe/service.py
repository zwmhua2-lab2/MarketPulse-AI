import httpx

from marketpulse.market_data.okx_live import OKXLiveProvider
from marketpulse.market_data.universe_provider import CoinGeckoMarketUniverseProvider

from .builder import build_universe
from .models import Universe


async def build_live_universe(provider: OKXLiveProvider, manual_watchlist: list[str]) -> Universe:
    instruments = await provider.instruments("SPOT")
    tradable = {item.instrument_id for item in instruments if item.tradable and item.quote_asset == "USDT"}
    tickers = await provider.spot_tickers()
    by_symbol = {str(item.get("instId")): item for item in tickers}
    liquid = {symbol: float(by_symbol.get(symbol, {}).get("volCcy24h", 0) or 0) >= 100_000 for symbol in tradable}
    hot = sorted(tradable, key=lambda symbol: float(by_symbol.get(symbol, {}).get("volCcy24h", 0) or 0), reverse=True)[:30]
    try:
        market_cap = await CoinGeckoMarketUniverseProvider().market_cap_top(100)
    except httpx.HTTPError:
        market_cap = []
    return build_universe(market_cap, hot, manual_watchlist, tradable, liquid)
