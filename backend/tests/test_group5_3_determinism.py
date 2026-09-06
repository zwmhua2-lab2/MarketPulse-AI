import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from marketpulse.config import Settings
from marketpulse.db.models import AIDecisionRecord
from marketpulse.g2.scanner import ScannerConfig
from marketpulse.g3.models import AIAnalysis, Direction, PriceZone, RunMode
from marketpulse.g3.service import stable_id
from marketpulse.g4.models import PositionReevaluation, ReevaluationAction
from marketpulse.g5.canonical import (
    CanonicalRow,
    CanonicalTable,
    CanonicalWorkspaceSnapshot,
    canonicalize_value,
    capture_workspace_snapshot,
    first_snapshot_difference,
)
from marketpulse.g5.replay import (
    _REPLAY_BUSINESS_TABLES,
    ReplayEventSource,
    ReplayFrame,
    ReplayG2Runner,
    ReplayTradingRunner,
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
_ECONOMIC_TABLES = ("fills", "positions", "trades", "accounts", "ledger_entries")


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
def _replay_database(label: str):
    name = f"marketpulse_g53_{label}_{uuid4().hex[:12]}"
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
            source="g5-3-fixture",
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
            source="g5-3-fixture",
            trade_id=f"g5-3-trade-{ordinal}",
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
            source="g5-3-fixture",
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


def _source(*, protective_stop_bid: float) -> ReplayEventSource:
    return ReplayEventSource(
        (
            _book(0, 0, bid=99.0, ask=100.0),
            _trade(1, 1, 105.0),
            _kline(2, 2, high=101.0, low=99.0, close=100.0),
            _kline(3, 3, high=102.0, low=99.0, close=101.0),
            _kline(4, 4, high=103.0, low=99.0, close=102.0),
            _trade(5, 5, 105.0),
            _book(6, 6, bid=99.0, ask=100.0),
            _book(7, 7, bid=protective_stop_bid, ask=90.0),
        )
    )


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


async def _recorded_inputs(
    source: ReplayEventSource,
) -> tuple[dict[str, AIAnalysis], dict[str, PositionReevaluation]]:
    trace = (await ReplayG2Runner(SCANNER).run(source)).trace
    setup = next(
        event
        for frame in trace.frames
        for event in frame.events
        if event.transition_to == "SETUP"
    )
    setup_frame = next(
        frame for frame in trace.frames if any(event.transition_id == setup.transition_id for event in frame.events)
    )
    review_state_version = max(
        event.state_version
        for frame in trace.frames
        if frame.input_ordinal <= 6
        for event in frame.events
    )
    g3_snapshot_id = stable_id(
        "snap",
        RunMode.REPLAY,
        "ETH-USDT",
        setup.state_version,
        SCANNER.version,
        setup_frame.processing_time.isoformat(),
    )
    g4_snapshot_id = ReplayTradingRunner._review_snapshot_id(
        RunMode.REPLAY,
        "ETH-USDT",
        review_state_version,
        "state_version_changed",
        START + timedelta(seconds=6),
    )
    return (
        {g3_snapshot_id: _g3_analysis()},
        {
            g4_snapshot_id: PositionReevaluation(
                action=ReevaluationAction.HOLD,
                reason="recorded hold",
                confidence=1.0,
            )
        },
    )


async def _snapshot(url: str) -> CanonicalWorkspaceSnapshot:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        return await capture_workspace_snapshot(engine, _REPLAY_BUSINESS_TABLES)
    finally:
        await engine.dispose()


async def _g4_decisions(url: str) -> list[tuple[str, str | None]]:
    engine = create_async_engine(url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            return [
                (record.model, record.error)
                for record in (
                    await session.scalars(
                        select(AIDecisionRecord).where(
                            AIDecisionRecord.model == "replay-recorded-g4"
                        )
                    )
                ).all()
            ]
    finally:
        await engine.dispose()


async def _business_timestamps(url: str) -> list[tuple[str, str, datetime]]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            table_list = ", ".join(f"'{table}'" for table in _REPLAY_BUSINESS_TABLES)
            columns = (
                await connection.execute(
                    text(
                        "SELECT table_name, column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' "
                        f"AND table_name IN ({table_list}) "
                        "AND data_type = 'timestamp with time zone' "
                        "ORDER BY table_name, ordinal_position"
                    )
                )
            ).all()
            timestamps: list[tuple[str, str, datetime]] = []
            for table_name, column_name in columns:
                result = await connection.execute(
                    text(f'SELECT "{column_name}" FROM "{table_name}"')
                )
                timestamps.extend(
                    (table_name, column_name, value) for value in result.scalars() if value is not None
                )
            return timestamps
    finally:
        await engine.dispose()


def _runner(
    replay_url: str, *, g3_records: dict[str, AIAnalysis], g4_records: dict[str, PositionReevaluation]
) -> ReplayTradingRunner:
    return ReplayTradingRunner(
        Settings(run_mode="REPLAY", database_url=PRIMARY_URL, replay_database_url=replay_url),
        g3_records=g3_records,
        g4_records=g4_records,
        scanner_config=SCANNER,
    )


class _ExampleEnum(Enum):
    REPLAY = "REPLAY"


def test_canonicalization_is_lossless_and_deterministic_for_required_types():
    local_time = datetime(2024, 1, 2, 9, 30, tzinfo=timezone(timedelta(hours=8)))
    value = {
        "z": [None, True, 7, "text", Decimal("1.2300"), 0.1, _ExampleEnum.REPLAY],
        "a": local_time,
    }

    normalized = canonicalize_value(value)

    assert normalized == [
        "object",
        [
            ["a", ["datetime", "2024-01-02T01:30:00.000000+00:00"]],
            [
                "z",
                [
                    "array",
                    [
                        ["null"],
                        ["bool", True],
                        ["int", 7],
                        ["str", "text"],
                        ["decimal", "1.2300"],
                        ["float", (0.1).hex()],
                        ["enum", ["str", "REPLAY"]],
                    ],
                ],
            ],
        ],
    ]


def test_canonicalization_is_injective_across_source_types():
    local_time = datetime(2024, 1, 2, 9, 30, tzinfo=UTC)

    assert canonicalize_value(1.0) != canonicalize_value("0x1.0000000000000p+0")
    assert canonicalize_value(Decimal("1.2300")) != canonicalize_value("1.2300")
    assert canonicalize_value(local_time) != canonicalize_value("2024-01-02T09:30:00.000000+00:00")
    assert canonicalize_value(["float", "0x1.0000000000000p+0"]) != canonicalize_value(1.0)
    # A source JSON object shaped like a type marker must remain distinct from a real value.
    assert canonicalize_value({"type": "bool", "value": True}) != canonicalize_value(True)
    # A source string that looks like a tagged marker must not collide with a real tagged value.
    assert canonicalize_value("float") != canonicalize_value(1.0)


def test_canonicalization_preserves_ordering_precision_and_utc():
    local_time = datetime(2024, 1, 2, 9, 30, tzinfo=timezone(timedelta(hours=8)))
    value = {
        "z_keys": {"b": 1, "a": 2, "c": 3},
        "array": [Decimal("1.2300"), 0.1, local_time],
    }

    normalized = canonicalize_value(value)

    # Top-level dict keys are sorted deterministically ("array" < "z_keys").
    assert normalized[0] == "object"
    pairs = dict(normalized[1])
    assert list(pairs) == ["array", "z_keys"]
    # Array ordering preserved, Decimal exact, float hex exact, UTC normalization.
    assert pairs["array"] == [
        "array",
        [
            ["decimal", "1.2300"],
            ["float", (0.1).hex()],
            ["datetime", "2024-01-02T01:30:00.000000+00:00"],
        ],
    ]
    # Nested dict keys sorted deterministically.
    assert pairs["z_keys"] == [
        "object",
        [
            ["a", ["int", 2]],
            ["b", ["int", 1]],
            ["c", ["int", 3]],
        ],
    ]


def test_canonical_diff_reports_table_primary_key_and_nested_json_path():
    payload_a = canonicalize_value({"economics": {"realized_pnl": 0.1}})
    payload_b = canonicalize_value({"economics": {"realized_pnl": 1.5}})
    run_a = CanonicalWorkspaceSnapshot(
        tables=(
            CanonicalTable(
                name="positions",
                primary_key_columns=("position_id",),
                rows=(
                    CanonicalRow(
                        primary_key=(("position_id", "position-1"),),
                        values=(("payload", payload_a),),
                    ),
                ),
            ),
        )
    )
    run_b = CanonicalWorkspaceSnapshot(
        tables=(
            CanonicalTable(
                name="positions",
                primary_key_columns=("position_id",),
                rows=(
                    CanonicalRow(
                        primary_key=(("position_id", "position-1"),),
                        values=(("payload", payload_b),),
                    ),
                ),
            ),
        )
    )

    difference = first_snapshot_difference(run_a, run_b)

    assert difference is not None
    assert difference.table == "positions"
    assert difference.primary_key == (("position_id", "position-1"),)
    assert difference.path == "$values.payload.economics.realized_pnl"
    assert difference.run_a_value == ["float", (0.1).hex()]
    assert difference.run_b_value == ["float", (1.5).hex()]


def test_end_to_end_replay_determinism_uses_three_independent_postgres_workspaces(monkeypatch):
    outbound_http_clients: list[object] = []

    def no_network(*args, **kwargs):
        outbound_http_clients.append((args, kwargs))
        raise AssertionError("Replay must not construct an outbound HTTP client")

    monkeypatch.setattr(httpx, "AsyncClient", no_network)
    source_a = _source(protective_stop_bid=89.0)
    source_b = _source(protective_stop_bid=89.0)
    source_c = _source(protective_stop_bid=88.0)
    g3_a, g4_a = asyncio.run(_recorded_inputs(source_a))
    g3_b, g4_b = asyncio.run(_recorded_inputs(source_b))
    g3_c, g4_c = asyncio.run(_recorded_inputs(source_c))

    with (
        _replay_database("run_a") as (name_a, url_a),
        _replay_database("run_b") as (name_b, url_b),
        _replay_database("run_c") as (name_c, url_c),
    ):
        result_a = asyncio.run(_runner(url_a, g3_records=g3_a, g4_records=g4_a).run(source_a))
        result_b = asyncio.run(_runner(url_b, g3_records=g3_b, g4_records=g4_b).run(source_b))
        result_c = asyncio.run(_runner(url_c, g3_records=g3_c, g4_records=g4_c).run(source_c))
        snapshot_a = asyncio.run(_snapshot(url_a))
        snapshot_b = asyncio.run(_snapshot(url_b))
        snapshot_c = asyncio.run(_snapshot(url_c))
        timestamps_a = asyncio.run(_business_timestamps(url_a))
        timestamps_b = asyncio.run(_business_timestamps(url_b))
        timestamps_c = asyncio.run(_business_timestamps(url_c))
        g4_decisions_a = asyncio.run(_g4_decisions(url_a))
        g4_decisions_b = asyncio.run(_g4_decisions(url_b))
        g4_decisions_c = asyncio.run(_g4_decisions(url_c))

    # Every run must consume the recorded G4 HOLD. A silent ReplayPositionReviewRecordMissing
    # fallback would still increment the provider call counter and would still end in HOLD.
    for label, g4_decisions in (
        ("A", g4_decisions_a),
        ("B", g4_decisions_b),
        ("C", g4_decisions_c),
    ):
        assert g4_decisions == [("replay-recorded-g4", None)], (
            f"run {label} did not consume the recorded G4 HOLD"
        )

    assert len({name_a, name_b, name_c}) == 3
    assert tuple(table.name for table in snapshot_a.tables) == _REPLAY_BUSINESS_TABLES
    assert all(table.primary_key_columns for table in snapshot_a.tables)
    assert all(
        [row.primary_key for row in table.rows] == sorted(row.primary_key for row in table.rows)
        for table in snapshot_a.tables
    )
    assert snapshot_a == snapshot_b
    assert snapshot_a.digest() == snapshot_b.digest() == result_a.workspace_digest == result_b.workspace_digest
    assert result_a.primary_counts_after == result_a.primary_counts_before
    assert result_b.primary_counts_after == result_b.primary_counts_before
    assert result_c.primary_counts_after == result_c.primary_counts_before
    assert result_a.g3_provider_calls == result_b.g3_provider_calls == result_c.g3_provider_calls == 1
    assert result_a.g4_provider_calls == result_b.g4_provider_calls == result_c.g4_provider_calls == 1
    assert result_a.trades[0][1:] == result_b.trades[0][1:] == result_c.trades[0][1:] == (
        "CLOSED",
        "STOP_LOSS",
    )
    assert snapshot_a.digest() != snapshot_c.digest()
    assert snapshot_c.digest() == result_c.workspace_digest
    assert first_snapshot_difference(snapshot_a, snapshot_b) is None
    assert first_snapshot_difference(snapshot_a, snapshot_c) is not None
    economic_difference = first_snapshot_difference(
        snapshot_a, snapshot_c, table_names=_ECONOMIC_TABLES
    )
    assert economic_difference is not None
    assert economic_difference.table == "fills"
    assert economic_difference.path == "$values.fee"
    assert economic_difference.run_a_value != economic_difference.run_b_value
    fills_a = next(table for table in snapshot_a.tables if table.name == "fills")
    fills_c = next(table for table in snapshot_c.tables if table.name == "fills")
    assert dict(fills_a.rows[-1].values)["price"] != dict(fills_c.rows[-1].values)["price"]
    assert not outbound_http_clients
    for timestamps in (timestamps_a, timestamps_b, timestamps_c):
        assert timestamps
        assert all(
            START <= value <= START + timedelta(minutes=15, seconds=7)
            for _, _, value in timestamps
        )
        assert all(
            value <= START + timedelta(seconds=7)
            for _, column_name, value in timestamps
            if column_name not in {"expires_at", "watch_expires_at"}
        )
