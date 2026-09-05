import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from marketpulse.clock import ReplayClock
from marketpulse.g2.scanner import ScannerConfig
from marketpulse.g5.replay import (
    ReplayEventSource,
    ReplayFrame,
    ReplayG2Runner,
    ReplayOrderingError,
)
from marketpulse.market_data.models import (
    MarketType,
    NormalizedBookTicker,
    NormalizedKline,
    NormalizedTrade,
)

HISTORICAL_START = datetime(2024, 1, 2, 9, 30, tzinfo=UTC)


def _frame(ordinal: int, *, received_offset: int, price: float = 100.0) -> ReplayFrame:
    event_time = HISTORICAL_START + timedelta(seconds=ordinal)
    return ReplayFrame(
        ordinal=ordinal,
        market_event=NormalizedTrade(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=event_time,
            received_time=HISTORICAL_START + timedelta(seconds=received_offset),
            source="g5-1-fixture",
            trade_id=f"trade-{ordinal}",
            price=price,
            quantity=10.0,
            side="buy",
        ),
    )


def _source(*frames: ReplayFrame) -> ReplayEventSource:
    return ReplayEventSource(frames)


def _runner() -> ReplayG2Runner:
    return ReplayG2Runner(ScannerConfig(flow_imbalance_threshold=0.1))


def test_replay_clock_advances_to_each_received_time():
    source = _source(_frame(0, received_offset=0), _frame(1, received_offset=3))
    result = asyncio.run(_runner().run(source))

    assert [frame.processing_time for frame in result.trace.frames] == [
        frame.market_event.received_time for frame in source.frames
    ]


def test_replay_clock_preserves_equal_received_time_input_order():
    source = _source(_frame(7, received_offset=0), _frame(8, received_offset=0))
    result = asyncio.run(_runner().run(source))

    assert [frame.input_ordinal for frame in result.trace.frames] == [7, 8]


def test_replay_source_rejects_backward_received_time():
    with pytest.raises(ReplayOrderingError, match="non-decreasing"):
        _source(_frame(0, received_offset=2), _frame(1, received_offset=1))


def test_replay_accepts_all_supported_normalized_event_types():
    trade = _frame(0, received_offset=0)
    book = ReplayFrame(
        ordinal=1,
        market_event=NormalizedBookTicker(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=HISTORICAL_START + timedelta(seconds=1),
            received_time=HISTORICAL_START + timedelta(seconds=1),
            source="g5-1-fixture",
            bid_price=99.0,
            bid_quantity=10.0,
            ask_price=100.0,
            ask_quantity=10.0,
        ),
    )
    kline = ReplayFrame(
        ordinal=2,
        market_event=NormalizedKline(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=HISTORICAL_START + timedelta(seconds=2),
            received_time=HISTORICAL_START + timedelta(seconds=2),
            source="g5-1-fixture",
            open_time=HISTORICAL_START,
            close_time=HISTORICAL_START + timedelta(seconds=2),
            open=99.0,
            high=101.0,
            low=98.0,
            close=100.0,
            volume=25.0,
            confirmed=True,
        ),
    )

    result = asyncio.run(_runner().run([trade, book, kline]))

    assert [frame.input_ordinal for frame in result.trace.frames] == [0, 1, 2]


def test_same_replay_twice_has_identical_canonical_trace():
    source = _source(
        _frame(0, received_offset=0, price=100.0),
        _frame(1, received_offset=1, price=101.0),
        _frame(2, received_offset=2, price=103.0),
    )

    first = asyncio.run(_runner().run(source))
    second = asyncio.run(_runner().run(source))

    assert first.trace.canonical() == second.trace.canonical()
    first_events = tuple(event for frame in first.trace.frames for event in frame.events)
    second_events = tuple(event for frame in second.trace.frames for event in frame.events)

    assert [event.event_id for event in first_events] == [event.event_id for event in second_events]
    assert [event.timeline_id for event in first_events] == [event.timeline_id for event in second_events]
    assert [
        (event.transition_id, event.transition_from, event.transition_to, event.state_version)
        for event in first_events
    ] == [
        (event.transition_id, event.transition_from, event.transition_to, event.state_version)
        for event in second_events
    ]
    assert [event.candidate_ids for event in first_events] == [
        event.candidate_ids for event in second_events
    ]
    assert [event.candidate_created_at for event in first_events] == [
        event.candidate_created_at for event in second_events
    ]
    assert [event.candidate_applicable for event in first_events] == [
        event.candidate_applicable for event in second_events
    ]
    assert [event.candidate_direction_bias for event in first_events] == [
        event.candidate_direction_bias for event in second_events
    ]


def test_replay_business_timestamps_are_historical_not_wall_clock():
    source = _source(_frame(0, received_offset=0), _frame(1, received_offset=1))
    result = asyncio.run(_runner().run(source))

    business_timestamps = [event.received_time for event in result.repository.events.values()]
    candidate_timestamps = [candidate.created_at for candidate in result.repository.candidates]
    business_timestamps.extend(candidate_timestamps)
    assert business_timestamps
    assert all(timestamp.date() == HISTORICAL_START.date() for timestamp in business_timestamps)
    assert candidate_timestamps
    assert set(candidate_timestamps) <= {
        frame.market_event.received_time for frame in source.frames
    }


def test_real_g2_chain_emits_events_transition_and_candidates():
    source = _source(_frame(0, received_offset=0), _frame(1, received_offset=1, price=102.0))
    result = asyncio.run(_runner().run(source))

    assert result.repository.events
    assert result.repository.transitions
    assert result.repository.candidates
    assert any(frame.events for frame in result.trace.frames)


def test_changing_processing_timestamp_changes_replay_timeline():
    original = _source(_frame(0, received_offset=0), _frame(1, received_offset=1))
    delayed = _source(_frame(0, received_offset=0), _frame(1, received_offset=5))

    assert asyncio.run(_runner().run(original)).trace.canonical() != asyncio.run(
        _runner().run(delayed)
    ).trace.canonical()


def test_replay_clock_is_explicitly_advanced_by_the_runner_fixture():
    clock = ReplayClock(HISTORICAL_START)
    next_time = HISTORICAL_START + timedelta(seconds=1)
    clock.advance_to(next_time)

    assert clock.now() == next_time
