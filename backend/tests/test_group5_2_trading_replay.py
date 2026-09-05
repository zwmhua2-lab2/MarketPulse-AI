import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    FillRecord,
    LedgerEntryRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g2.scanner import ScannerConfig
from marketpulse.g3.models import AIAnalysis, Direction, PriceZone, RunMode
from marketpulse.g3.service import stable_id
from marketpulse.g4.models import PositionReevaluation, ReevaluationAction
from marketpulse.g5.replay import (
    ReplayAIRecordMissing,
    ReplayBBOUnavailable,
    ReplayEventSource,
    ReplayFrame,
    ReplayG2Runner,
    ReplayMarketState,
    ReplayTradingRunner,
    ReplayWorkspaceIsolationError,
)
from marketpulse.market_data.models import (
    MarketType,
    NormalizedBookTicker,
    NormalizedKline,
    NormalizedTrade,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2024, 1, 2, 9, 30, tzinfo=UTC)
PRIMARY_URL = Settings().database_url
SCANNER = ScannerConfig(flow_imbalance_threshold=0.1)
BACKEND = Path(__file__).resolve().parents[1]


def _url_for(database_name: str) -> str:
    return f"{PRIMARY_URL.rsplit('/', 1)[0]}/{database_name}"


async def _execute(url: str, statement: str) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@contextmanager
def _replay_database():
    name = f"marketpulse_g52_{uuid4().hex[:12]}"
    asyncio.run(_execute(PRIMARY_URL, f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    try:
        yield name, url
    finally:
        asyncio.run(
            _execute(
                PRIMARY_URL,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute(PRIMARY_URL, f'DROP DATABASE "{name}"'))


def _book(ordinal: int, offset: int, *, bid: float, ask: float) -> ReplayFrame:
    moment = START + timedelta(seconds=offset)
    return ReplayFrame(
        ordinal=ordinal,
        market_event=NormalizedBookTicker(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=moment,
            received_time=moment,
            source="g5-2-fixture",
            bid_price=bid,
            ask_price=ask,
            bid_quantity=10.0,
            ask_quantity=10.0,
        ),
    )


def _trade(ordinal: int, offset: int, price: float) -> ReplayFrame:
    moment = START + timedelta(seconds=offset)
    return ReplayFrame(
        ordinal=ordinal,
        market_event=NormalizedTrade(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=moment,
            received_time=moment,
            source="g5-2-fixture",
            trade_id=f"replay-trade-{ordinal}",
            price=price,
            quantity=10.0,
            side="buy",
        ),
    )


def _kline(ordinal: int, offset: int, *, high: float, low: float, close: float) -> ReplayFrame:
    moment = START + timedelta(seconds=offset)
    return ReplayFrame(
        ordinal=ordinal,
        market_event=NormalizedKline(
            base_asset="ETH",
            quote_asset="USDT",
            market_type=MarketType.SPOT,
            instrument_id="ETH-USDT",
            event_time=moment,
            received_time=moment,
            source="g5-2-fixture",
            open_time=moment - timedelta(minutes=1),
            close_time=moment,
            open=close - 1,
            high=high,
            low=low,
            close=close,
            volume=10.0,
            confirmed=True,
        ),
    )


def _source(*, include_stop: bool = True) -> ReplayEventSource:
    frames = [
        _book(0, 0, bid=99.0, ask=100.0),
        _trade(1, 1, 100.0),
        _kline(2, 2, high=101.0, low=99.0, close=100.0),
        _kline(3, 3, high=102.0, low=99.0, close=101.0),
        _kline(4, 4, high=103.0, low=99.0, close=102.0),
        _trade(5, 5, 105.0),
        _book(6, 6, bid=99.0, ask=100.0),
    ]
    if include_stop:
        frames.append(_book(7, 7, bid=89.0, ask=90.0))
    return ReplayEventSource(frames)


def _g3_analysis() -> AIAnalysis:
    return AIAnalysis(
        direction=Direction.LONG_BIAS,
        trends={"trend": "bullish"},
        entry_zone=PriceZone(lower=99.0, upper=101.0),
        stop_loss=95.0,
        take_profit=120.0,
        invalidation="stop_loss only",
        confidence=0.9,
        suggested_position_pct=0.1,
        reason="recorded deterministic fixture",
        main_plan="long replay fixture",
    )


async def _expected_ids(source: ReplayEventSource) -> tuple[str, str]:
    result = await ReplayG2Runner(SCANNER).run(source)
    setup = next(
        event
        for frame in result.trace.frames
        for event in frame.events
        if event.transition_to == "SETUP"
    )
    setup_frame = next(
        frame
        for frame in result.trace.frames
        if any(event.transition_id == setup.transition_id for event in frame.events)
    )
    review_state_version = setup_frame.events[-1].state_version
    snapshot_id = stable_id(
        "snap",
        RunMode.REPLAY,
        "ETH-USDT",
        setup.state_version,
        SCANNER.version,
        setup_frame.processing_time.isoformat(),
    )
    review_id = ReplayTradingRunner._review_snapshot_id(
        RunMode.REPLAY,
        "ETH-USDT",
        review_state_version,
        "no_previous_evaluation",
        START + timedelta(seconds=6),
    )
    return snapshot_id, review_id


def _runner(
    url: str, *, g3: dict[str, AIAnalysis], g4: dict[str, PositionReevaluation]
) -> ReplayTradingRunner:
    return ReplayTradingRunner(
        Settings(run_mode="REPLAY", database_url=PRIMARY_URL, replay_database_url=url),
        g3_records=g3,
        g4_records=g4,
        scanner_config=SCANNER,
    )


async def _rows(url: str):
    engine = create_async_engine(url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            return {
                "plans": list((await session.scalars(select(TradePlanRecord))).all()),
                "orders": list((await session.scalars(select(PaperOrderRecord))).all()),
                "fills": list((await session.scalars(select(FillRecord))).all()),
                "positions": list((await session.scalars(select(PositionRecord))).all()),
                "trades": list((await session.scalars(select(TradeRecord))).all()),
                "ledgers": list((await session.scalars(select(LedgerEntryRecord))).all()),
                "events": list((await session.scalars(select(PositionEventRecord))).all()),
                "decisions": list((await session.scalars(select(AIDecisionRecord))).all()),
                "accounts": list((await session.scalars(select(AccountRecord))).all()),
            }
    finally:
        await engine.dispose()


def test_workspace_guard_rejects_primary_and_dirty_replay_database():
    source = ReplayEventSource([_book(0, 0, bid=99.0, ask=100.0)])
    with pytest.raises(ReplayWorkspaceIsolationError, match="identity equals"):
        asyncio.run(_runner(PRIMARY_URL, g3={}, g4={}).run(source))

    with _replay_database() as (_, replay_url):
        asyncio.run(
            _execute(replay_url, "INSERT INTO accounts VALUES ('dirty', 'REPLAY', 1, 0, 0, now())")
        )
        with pytest.raises(ReplayWorkspaceIsolationError, match="not clean"):
            asyncio.run(_runner(replay_url, g3={}, g4={}).run(source))


def test_replay_market_state_never_observes_a_future_bbo():
    state = ReplayMarketState()
    with pytest.raises(ReplayBBOUnavailable, match="no observed replay BBO"):
        asyncio.run(state.bbo_for("ETH-USDT"))
    state.ingest(_book(1, 2, bid=101.0, ask=102.0).market_event)
    assert asyncio.run(state.bbo_for("ETH-USDT")).received_at == START + timedelta(seconds=2)


def test_g3_record_miss_fails_closed_without_plan_or_position_mutation():
    source = _source(include_stop=False)
    with _replay_database() as (_, replay_url):
        with pytest.raises(ReplayAIRecordMissing, match="recorded G3 AI result missing"):
            asyncio.run(_runner(replay_url, g3={}, g4={}).run(source))
        rows = asyncio.run(_rows(replay_url))
        assert not rows["plans"]
        assert not rows["orders"]
        assert not rows["positions"]


def test_real_postgres_replay_g2_to_g4_stop_exit_is_isolated_and_historical(monkeypatch):
    source = _source()
    g3_id, g4_id = asyncio.run(_expected_ids(source))
    hold = PositionReevaluation(
        action=ReevaluationAction.HOLD,
        reason="recorded hold",
        confidence=1.0,
    )

    def no_network(*args, **kwargs):
        raise AssertionError("replay must not create an outbound HTTP client")

    monkeypatch.setattr(httpx, "AsyncClient", no_network)
    with _replay_database() as (replay_name, replay_url):
        result = asyncio.run(
            _runner(replay_url, g3={g3_id: _g3_analysis()}, g4={g4_id: hold}).run(source)
        )
        rows = asyncio.run(_rows(replay_url))

    assert result.primary_database == "marketpulse"
    assert result.replay_database == replay_name
    assert result.primary_counts_after == result.primary_counts_before
    assert result.setup_snapshot_ids == (g3_id,)
    assert result.g3_provider_calls == 1
    assert result.g4_provider_calls == 1
    assert len(result.plan_ids) == len(result.buy_order_ids) == len(result.buy_fill_ids) == 1
    assert len(rows["plans"]) == 1
    assert len(rows["orders"]) == len(rows["fills"]) == len(rows["ledgers"]) == 2
    assert rows["positions"][0].quantity == 0
    assert rows["trades"][0].status == "CLOSED"
    assert rows["trades"][0].exit_reason == "STOP_LOSS"
    assert any(decision.model == "replay-recorded-g4" for decision in rows["decisions"])
    assert any(event.event_type == "SL_TRIGGERED" for event in rows["events"])
    business_times = [
        *(record.created_at for record in rows["plans"]),
        *(record.created_at for record in rows["orders"]),
        *(record.created_at for record in rows["fills"]),
        *(record.created_at for record in rows["ledgers"]),
        *(record.created_at for record in rows["events"]),
        *(record.opened_at for record in rows["trades"]),
        *(record.closed_at for record in rows["trades"] if record.closed_at is not None),
        *(record.updated_at for record in rows["accounts"]),
        *(record.updated_at for record in rows["positions"]),
    ]
    assert business_times
    assert all(START <= value <= START + timedelta(seconds=7) for value in business_times)


def test_missing_recorded_g4_review_is_hold_safe_and_never_calls_real_ai():
    source = _source(include_stop=False)
    g3_id, _ = asyncio.run(_expected_ids(source))
    with _replay_database() as (_, replay_url):
        result = asyncio.run(_runner(replay_url, g3={g3_id: _g3_analysis()}, g4={}).run(source))
        rows = asyncio.run(_rows(replay_url))
    assert result.g3_provider_calls == 1
    assert result.g4_provider_calls == 1
    assert rows["positions"][0].quantity > 0
    assert any(
        decision.error == "AI_ERROR:ReplayPositionReviewRecordMissing"
        for decision in rows["decisions"]
    )
