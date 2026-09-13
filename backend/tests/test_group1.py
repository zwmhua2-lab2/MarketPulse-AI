import asyncio
from datetime import UTC, datetime, timedelta

from marketpulse.clock import ReplayClock
from marketpulse.market_data.models import DataQuality, Instrument, MarketType, freshness_status
from marketpulse.market_data.normalizer import instrument_from_okx, normalize_book_ticker
from marketpulse.runtime import HealthRegistry, supervised_worker
from marketpulse.universe.builder import build_universe, hot_score


def test_replay_clock_is_replaceable():
    current = datetime(2026, 1, 1, tzinfo=UTC)
    clock = ReplayClock(current)
    assert clock.now() == current


def test_freshness_marks_old_data_stale():
    now = datetime.now(UTC)
    assert freshness_status(now - timedelta(seconds=2), now, 5) is DataQuality.FRESH
    assert freshness_status(now - timedelta(seconds=6), now, 5) is DataQuality.STALE


def test_universe_dedupes_and_filters():
    result = build_universe(["btc-usdt", "eth-usdt"], ["BTC-USDT", "sol-usdt"], ["doge-usdt"], {"BTC-USDT", "SOL-USDT"}, {"BTC-USDT": True, "SOL-USDT": False})
    assert result.symbols == ["BTC-USDT"]
    assert len(result.candidates) == 1


def test_hot_score_frozen_weights():
    assert hot_score(1, 1, 1, 1) == 100
    assert hot_score(0, 0, 0, 0) == 0


def test_okx_bbo_array_payload_is_normalized():
    instrument = Instrument(base_asset="BTC", quote_asset="USDT", market_type=MarketType.SPOT, instrument_id="BTC-USDT", trading_symbol="BTC-USDT")
    result = normalize_book_ticker({"ts": "1700000000000", "bids": [["100", "2"]], "asks": [["101", "3"]]}, instrument)
    assert (result.bid_price, result.bid_quantity, result.ask_price, result.ask_quantity) == (100, 2, 101, 3)


def test_okx_bbo_normalization_carries_the_instrument_tradability():
    """A normalized frame must state the instrument's real tradability, not imply it."""

    raw = {"ts": "1700000000000", "bids": [["100", "2"]], "asks": [["101", "3"]]}
    live = instrument_from_okx({"instId": "BTC-USDT", "instType": "SPOT", "state": "live"})
    suspended = instrument_from_okx({"instId": "BTC-USDT", "instType": "SPOT", "state": "suspend"})
    assert live.tradable is True
    assert suspended.tradable is False
    assert normalize_book_ticker(raw, live).tradable is True
    assert normalize_book_ticker(raw, suspended).tradable is False


def test_worker_failure_is_isolated():
    health = HealthRegistry()

    async def broken_worker():
        raise RuntimeError("expected")

    asyncio.run(supervised_worker("fixture", broken_worker, health))
    assert health.checks["fixture"]["status"] == "FAILED"
