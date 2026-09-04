from datetime import UTC, datetime

from .models import Instrument, MarketType, NormalizedBookTicker, NormalizedKline, NormalizedTrade


def instrument_from_okx(raw: dict[str, object]) -> Instrument:
    inst_id = str(raw["instId"])
    market_type = MarketType.SWAP if str(raw.get("instType")) == "SWAP" else MarketType.SPOT
    parts = inst_id.split("-")
    base = parts[0]
    quote = parts[1] if len(parts) > 1 else ""
    return Instrument(
        base_asset=base,
        quote_asset=quote,
        market_type=market_type,
        instrument_id=inst_id,
        trading_symbol=f"{base}-{quote}" if market_type is MarketType.SWAP and quote else inst_id,
        tradable=str(raw.get("state", "live")) == "live",
        tick_size=float(raw["tickSz"]) if raw.get("tickSz") else None,
        lot_size=float(raw["lotSz"]) if raw.get("lotSz") else None,
    )


def _base(inst: Instrument, event_ms: int, source: str) -> dict[str, object]:
    return {
        "base_asset": inst.base_asset,
        "quote_asset": inst.quote_asset,
        "market_type": inst.market_type,
        "instrument_id": inst.instrument_id,
        "event_time": datetime.fromtimestamp(event_ms / 1000, tz=UTC),
        "received_time": datetime.now(UTC),
        "source": source,
    }


def normalize_trade(raw: dict[str, object], inst: Instrument) -> NormalizedTrade:
    return NormalizedTrade(
        **_base(inst, int(raw["ts"]), "okx.websocket.trade"),
        trade_id=str(raw["tradeId"]), price=float(raw["px"]), quantity=float(raw["sz"]), side=str(raw["side"]),
    )


def normalize_book_ticker(raw: dict[str, object], inst: Instrument) -> NormalizedBookTicker:
    bids = raw.get("bids") or []
    asks = raw.get("asks") or []
    bid = raw.get("bidPx")
    bid_size = raw.get("bidSz")
    ask = raw.get("askPx")
    ask_size = raw.get("askSz")
    if bid is None:
        bid, bid_size = bids[0][0], bids[0][1]  # type: ignore[index]
    if ask is None:
        ask, ask_size = asks[0][0], asks[0][1]  # type: ignore[index]
    return NormalizedBookTicker(
        **_base(inst, int(raw["ts"]), "okx.websocket.bbo-tbt"),
        bid_price=float(bid), bid_quantity=float(bid_size),
        ask_price=float(ask), ask_quantity=float(ask_size),
    )


def normalize_kline(raw: list[object], inst: Instrument) -> NormalizedKline:
    open_ms = int(raw[0])
    close_ms = open_ms + 60_000
    return NormalizedKline(
        **_base(inst, open_ms, "okx.websocket.candle1m"),
        open_time=datetime.fromtimestamp(open_ms / 1000, tz=UTC),
        close_time=datetime.fromtimestamp(close_ms / 1000, tz=UTC),
        open=float(raw[1]), high=float(raw[2]), low=float(raw[3]), close=float(raw[4]), volume=float(raw[5]),
        confirmed=str(raw[8]) == "1",
    )
