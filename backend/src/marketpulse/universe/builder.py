from collections.abc import Iterable

from .models import Universe, UniverseCandidate


def hot_score(turnover_activity: float, volume_acceleration: float, volatility_activity: float, trade_activity: float) -> float:
    """Frozen V1 weighted score; it is a priority score, never a trading signal."""
    values = [max(0.0, min(1.0, value)) for value in (turnover_activity, volume_acceleration, volatility_activity, trade_activity)]
    return round(100 * (0.35 * values[0] + 0.30 * values[1] + 0.20 * values[2] + 0.15 * values[3]), 6)


def build_universe(
    market_cap_top100: Iterable[str],
    hot_top30: Iterable[str],
    manual_watchlist: Iterable[str],
    tradable_spot: set[str],
    liquidity: dict[str, bool],
) -> Universe:
    ordered: list[tuple[str, str, float]] = []
    seen: set[str] = set()
    for source, symbols, score in (("MARKET_CAP_TOP100", market_cap_top100, 50.0), ("HOT_TOP30", hot_top30, 75.0), ("MANUAL_WATCHLIST", manual_watchlist, 100.0)):
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in seen:
                continue
            seen.add(symbol)
            ordered.append((symbol, source, score))
    candidates = [
        UniverseCandidate(symbol=symbol, source=source, priority_score=score, tradable=symbol in tradable_spot, liquidity_ok=liquidity.get(symbol, False))
        for symbol, source, score in ordered
        if symbol in tradable_spot and liquidity.get(symbol, False)
    ]
    return Universe(symbols=[candidate.symbol for candidate in candidates], candidates=candidates)

