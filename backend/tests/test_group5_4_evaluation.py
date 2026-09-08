import asyncio
import math
import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
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
from marketpulse.g5.canonical import capture_workspace_snapshot
from marketpulse.g5.evaluation import (
    ReplayEvaluationError,
    ReplayEvaluationReport,
    evaluate_replay_workspace,
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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2024, 1, 2, 9, 30, tzinfo=UTC)
PRIMARY_URL = Settings().database_url
SCANNER = ScannerConfig(flow_imbalance_threshold=0.1)
BACKEND = Path(__file__).resolve().parents[1]
INITIAL_CASH = Settings().paper_initial_balance

#: Fields the G5-4 contract accepts as a real economic sensitivity signal between runs.
APPROVED_ECONOMIC_FIELDS = (
    "sell_filled_notional",
    "total_fees",
    "ledger_cash_delta",
    "account_realized_pnl",
    "final_cash_balance",
)


#: Test-only instrumentation for R3: verify the REAL PostgreSQL transaction characteristics that
#: ``evaluate_replay_workspace`` runs under. We monkeypatch ``AsyncSession.execute`` so the
#: production ``SET TRANSACTION ...`` is observed in the exact same session/transaction path the
#: production code uses, then read back the live ``transaction_isolation`` /
#: ``transaction_read_only`` settings from that same transaction. No production business API is
#: added for this; this is strictly test-only verification.
_CAPTURED_TXN: dict[str, str] = {}

_ORIGINAL_ASYNC_SESSION_EXECUTE = AsyncSession.execute


async def _instrumented_async_session_execute(self, statement, *args, **kwargs):
    result = await _ORIGINAL_ASYNC_SESSION_EXECUTE(self, statement, *args, **kwargs)
    if (
        "SET TRANSACTION ISOLATION LEVEL" in str(statement).upper()
        and "transaction_isolation" not in _CAPTURED_TXN
    ):
        iso = (
            await _ORIGINAL_ASYNC_SESSION_EXECUTE(self, text("SHOW transaction_isolation"))
        ).scalar_one()
        ro = (
            await _ORIGINAL_ASYNC_SESSION_EXECUTE(self, text("SHOW transaction_read_only"))
        ).scalar_one()
        _CAPTURED_TXN["transaction_isolation"] = iso
        _CAPTURED_TXN["transaction_read_only"] = ro
    return result


def _url_for(database_name: str) -> str:
    return f"{PRIMARY_URL.rsplit('/', 1)[0]}/{database_name}"


async def _execute(url: str, statement: str, **params: Any) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(statement), params)
    finally:
        await engine.dispose()


@contextmanager
def _replay_database(label: str):
    name = f"marketpulse_g54_{label}_{uuid4().hex[:12]}"
    asyncio.run(_execute(PRIMARY_URL, f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
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
            source="g5-4-fixture",
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
            source="g5-4-fixture",
            trade_id=f"g5-4-trade-{ordinal}",
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
            source="g5-4-fixture",
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


def _source(*, protective_stop_bid: float, last_ordinal: int = 7) -> ReplayEventSource:
    frames = (
        _book(0, 0, bid=99.0, ask=100.0),
        _trade(1, 1, 105.0),
        _kline(2, 2, high=101.0, low=99.0, close=100.0),
        _kline(3, 3, high=102.0, low=99.0, close=101.0),
        _kline(4, 4, high=103.0, low=99.0, close=102.0),
        _trade(5, 5, 105.0),
        _book(6, 6, bid=99.0, ask=100.0),
        _book(7, 7, bid=protective_stop_bid, ask=90.0),
    )
    return ReplayEventSource(frames[: last_ordinal + 1])


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
        frame
        for frame in trace.frames
        if any(event.transition_id == setup.transition_id for event in frame.events)
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


async def _evaluate(url: str) -> ReplayEvaluationReport:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        snapshot = await capture_workspace_snapshot(engine, _REPLAY_BUSINESS_TABLES)
        return await evaluate_replay_workspace(engine, workspace_digest=snapshot.digest())
    finally:
        await engine.dispose()


async def _durable_counts(url: str) -> dict[str, int]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            counts: dict[str, int] = {}
            for table in (
                "market_events",
                "ai_decisions",
                "trade_plans",
                "paper_orders",
                "fills",
            ):
                counts[table] = int(
                    (await connection.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
                )
        return counts
    finally:
        await engine.dispose()


async def _durable_fills(url: str) -> list[tuple[str, str, float, float, float]]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        "SELECT fill_id, order_id, price, quantity, fee FROM fills "
                        "ORDER BY fill_id"
                    )
                )
            ).all()
        return [(row[0], row[1], row[2], row[3], row[4]) for row in rows]
    finally:
        await engine.dispose()


async def _corrupt_first_fill_fee(url: str, *, delta: float) -> None:
    """Deliberate test-local corruption: desynchronize durable fill fees from ledger fees."""

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            fill_id = (
                await connection.execute(text("SELECT fill_id FROM fills ORDER BY fill_id LIMIT 1"))
            ).scalar_one()
            await connection.execute(
                text("UPDATE fills SET fee = fee + :delta WHERE fill_id = :fill_id"),
                {"delta": delta, "fill_id": fill_id},
            )
    finally:
        await engine.dispose()


async def _corrupt_fill_order_id(url: str, *, to_order_id: str) -> None:
    """Deliberate test-local corruption: point a fill at an order id absent from paper_orders.

    The production path must NOT guess a side or fall back for a fill whose order is missing; it
    must fail closed. ``fills.order_id`` has no FK at the model or migration layer, so this UPDATE
    is durable within the isolated workspace.
    """

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            fill_id = (
                await connection.execute(text("SELECT fill_id FROM fills ORDER BY fill_id LIMIT 1"))
            ).scalar_one()
            await connection.execute(
                text("UPDATE fills SET order_id = :oid WHERE fill_id = :fill_id"),
                {"oid": to_order_id, "fill_id": fill_id},
            )
    finally:
        await engine.dispose()


async def _corrupt_order_side(url: str, *, side: str) -> None:
    """Deliberate test-local corruption: set a paper order side to an unsupported value.

    The production path must NOT treat an unknown side as BUY/SELL; it must fail closed.
    ``paper_orders.side`` has no CHECK constraint at the model or migration layer, so this UPDATE
    is durable within the isolated workspace.
    """

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            order_id = (
                await connection.execute(
                    text("SELECT order_id FROM paper_orders ORDER BY order_id LIMIT 1")
                )
            ).scalar_one()
            await connection.execute(
                text("UPDATE paper_orders SET side = :side WHERE order_id = :order_id"),
                {"side": side, "order_id": order_id},
            )
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


def _runner(
    replay_url: str, *, g3_records: dict[str, AIAnalysis], g4_records: dict[str, PositionReevaluation]
) -> ReplayTradingRunner:
    return ReplayTradingRunner(
        Settings(run_mode="REPLAY", database_url=PRIMARY_URL, replay_database_url=replay_url),
        g3_records=g3_records,
        g4_records=g4_records,
        scanner_config=SCANNER,
    )


def _economic_field_deltas(
    left: ReplayEvaluationReport, right: ReplayEvaluationReport
) -> list[str]:
    return [
        field
        for field in APPROVED_ECONOMIC_FIELDS
        if getattr(left, field) != getattr(right, field)
    ]


def test_evaluation_reports_deterministic_metrics_from_durable_facts():
    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("metrics") as (_, url):
        result = asyncio.run(_runner(url, g3_records=g3_records, g4_records=g4_records).run(source))
        report = result.evaluation
        assert report is not None
        fills = asyncio.run(_durable_fills(url))
        assert len(fills) == 2
        counts = asyncio.run(_durable_counts(url))

        # Counts come from durable tables, not from ReplayTradingResult memory fields.
        # `market_events` only holds frames that produced a G2 timeline event, so it is compared
        # against the durable row count rather than the input frame count.
        assert report.market_event_count == counts["market_events"] > 0
        assert report.decision_count == counts["ai_decisions"] > 0
        assert report.plan_count == counts["trade_plans"] > 0
        assert report.order_count == counts["paper_orders"] == len(result.orders)
        assert report.fill_count == counts["fills"] == len(fills)
        assert report.buy_fill_count + report.sell_fill_count == report.fill_count
        assert report.buy_fill_count == 1
        assert report.sell_fill_count == 1

        # Notional and fee aggregates are exact fsum() results over ordered durable rows.
        sell_fill = next(fill for fill in fills if fill[0] != result.buy_fill_ids[0])
        buy_fill = next(fill for fill in fills if fill[0] == result.buy_fill_ids[0])
        assert report.buy_filled_notional == buy_fill[2] * buy_fill[3]
        assert report.sell_filled_notional == sell_fill[2] * sell_fill[3]
        assert report.total_fees == math.fsum(fill[4] for fill in fills)

        # The three accounting indicators stay separate and are never merged.
        assert report.account_realized_pnl != report.total_fees
        assert report.account_realized_pnl != report.ledger_cash_delta
        assert report.total_fees != report.ledger_cash_delta

        # Evaluation digest is reproducible from the report itself.
        assert report.evaluation_digest == report.digest()
        assert report.evaluation_digest != report.workspace_digest
        assert report.workspace_digest == result.workspace_digest


def test_evaluation_is_identical_for_two_independent_postgres_workspaces(monkeypatch):
    outbound_http_clients: list[object] = []

    def no_network(*args, **kwargs):
        outbound_http_clients.append((args, kwargs))
        raise AssertionError("Replay must not construct an outbound HTTP client")

    monkeypatch.setattr(httpx, "AsyncClient", no_network)
    source_a = _source(protective_stop_bid=89.0)
    source_b = _source(protective_stop_bid=89.0)
    g3_a, g4_a = asyncio.run(_recorded_inputs(source_a))
    g3_b, g4_b = asyncio.run(_recorded_inputs(source_b))

    with (
        _replay_database("run_a") as (name_a, url_a),
        _replay_database("run_b") as (name_b, url_b),
    ):
        result_a = asyncio.run(_runner(url_a, g3_records=g3_a, g4_records=g4_a).run(source_a))
        result_b = asyncio.run(_runner(url_b, g3_records=g3_b, g4_records=g4_b).run(source_b))
        report_a = result_a.evaluation
        report_b = result_b.evaluation
        assert report_a is not None and report_b is not None

    assert name_a != name_b
    assert report_a == report_b
    assert report_a.evaluation_digest == report_b.evaluation_digest
    assert report_a.workspace_digest == report_b.workspace_digest == result_a.workspace_digest
    assert result_b.workspace_digest == report_b.workspace_digest
    assert result_a.primary_counts_after == result_a.primary_counts_before
    assert result_b.primary_counts_after == result_b.primary_counts_before
    assert result_a.g3_provider_calls == result_b.g3_provider_calls == 1
    assert result_a.g4_provider_calls == result_b.g4_provider_calls == 1
    assert not outbound_http_clients


def test_evaluation_sensitivity_to_protective_stop_price(monkeypatch):
    outbound_http_clients: list[object] = []

    def no_network(*args, **kwargs):
        outbound_http_clients.append((args, kwargs))
        raise AssertionError("Replay must not construct an outbound HTTP client")

    monkeypatch.setattr(httpx, "AsyncClient", no_network)
    source_a = _source(protective_stop_bid=89.0)
    source_c = _source(protective_stop_bid=88.0)
    g3_a, g4_a = asyncio.run(_recorded_inputs(source_a))
    g3_c, g4_c = asyncio.run(_recorded_inputs(source_c))

    with (
        _replay_database("run_a") as (_, url_a),
        _replay_database("run_c") as (_, url_c),
    ):
        result_a = asyncio.run(_runner(url_a, g3_records=g3_a, g4_records=g4_a).run(source_a))
        result_c = asyncio.run(_runner(url_c, g3_records=g3_c, g4_records=g4_c).run(source_c))
        report_a = result_a.evaluation
        report_c = result_c.evaluation
        assert report_a is not None and report_c is not None

    assert report_a.evaluation_digest != report_c.evaluation_digest
    assert report_a.workspace_digest != report_c.workspace_digest

    changed = _economic_field_deltas(report_a, report_c)
    assert changed == list(APPROVED_ECONOMIC_FIELDS), (
        f"expected every approved economic field to change, changed={changed}"
    )

    # Lifecycle validity must survive the mutation used to create the sensitivity signal.
    for label, report in (("A", report_a), ("C", report_c)):
        assert report.closed_trade_count == 1, f"run {label} trade lifecycle broken"
        assert report.open_trade_count == 0, f"run {label} trade lifecycle broken"
        assert report.exit_reason_counts == (("STOP_LOSS", 1),), f"run {label} exit reason broken"
    assert report_a.sell_filled_notional > report_c.sell_filled_notional
    assert not outbound_http_clients


def test_flat_fixture_evaluation_state_and_cash_identity():
    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("flat") as (_, url):
        result = asyncio.run(_runner(url, g3_records=g3_records, g4_records=g4_records).run(source))
        report = result.evaluation
        assert report is not None

    assert report.closed_trade_count == 1
    assert report.open_trade_count == 0
    assert report.trade_count == 1
    assert report.open_position_count == 0
    assert report.open_quantity == 0
    assert report.final_reserved_cash == 0
    assert report.is_flat is True
    assert report.exit_reason_counts == (("STOP_LOSS", 1),)
    # Flat-fixture evidence: with no open position and no reservation, every cash movement of this
    # replay is a durable ledger cash delta. The two sides accumulate the SAME cash movements but
    # in DIFFERENT ORDERS (sequential account updates vs. ledger math.fsum over entry_id order),
    # so they can legitimately differ by a few ULPs of IEEE-754 binary floating point.
    #
    # This is a BINARY FLOATING-POINT RECONCILIATION BOUND, NOT an accounting-mismatch tolerance.
    # We therefore derive the tolerance from the machine precision (ulp) of the operands instead
    # of an arbitrary fixed value. abs_tol=1e-9 was far above the real ULP artifact and far below
    # any real accounting difference; the bound below is genuinely machine-precision-derived and
    # may be tightened further if real evidence supports it, but must never regress to a fixed
    # wide tolerance.
    cash_change = report.final_cash_balance - INITIAL_CASH
    abs_tol = 4 * max(
        math.ulp(report.final_cash_balance),
        math.ulp(INITIAL_CASH),
        math.ulp(report.ledger_cash_delta),
    )
    actual_diff = abs(cash_change - report.ledger_cash_delta)
    # Surface the real measured reconciliation bound so it can be recorded as evidence (R7).
    print(
        f"FLAT_CASH_RECON actual_diff={actual_diff!r} abs_tol={abs_tol!r} "
        f"cash_change={cash_change!r} ledger_cash_delta={report.ledger_cash_delta!r}"
    )
    assert actual_diff <= abs_tol, (
        f"binary float reconciliation bound exceeded: "
        f"actual_diff={actual_diff!r} > abs_tol={abs_tol!r}"
    )
    assert math.isclose(
        cash_change,
        report.ledger_cash_delta,
        rel_tol=0.0,
        abs_tol=abs_tol,
    )


def test_open_position_is_not_evaluated_as_flat():
    source = _source(protective_stop_bid=89.0, last_ordinal=6)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("open") as (_, url):
        result = asyncio.run(_runner(url, g3_records=g3_records, g4_records=g4_records).run(source))
        report = result.evaluation
        assert report is not None

    assert report.open_position_count == 1
    assert report.open_quantity > 0
    assert report.open_trade_count == 1
    assert report.closed_trade_count == 0
    assert report.trade_count == 1
    assert report.exit_reason_counts == ()
    assert report.is_flat is False
    assert report.sell_fill_count == 0
    assert report.buy_fill_count == 1


def test_fill_ledger_fee_mismatch_fails_closed():
    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("corrupt") as (_, url):
        result = asyncio.run(_runner(url, g3_records=g3_records, g4_records=g4_records).run(source))
        assert result.evaluation is not None
        # Deliberate test-local corruption only; production trading semantics are untouched.
        asyncio.run(_corrupt_first_fill_fee(url, delta=0.01))
        try:
            asyncio.run(_evaluate(url))
        except ReplayEvaluationError as exc:
            assert "fill fees do not match ledger fees" in str(exc)
        else:
            raise AssertionError("accounting fee mismatch must fail closed")


def test_evaluation_uses_repeatable_read_read_only_transaction(monkeypatch):
    """R3: prove the evaluation really runs inside REPEATABLE READ, READ ONLY on PostgreSQL.

    We monkeypatch ``AsyncSession.execute`` so the production ``SET TRANSACTION ...`` is observed
    in the exact same session/transaction path ``evaluate_replay_workspace`` uses, then read back
    the live settings from that same transaction. This is real evidence, not a SQL-string assert.
    """

    monkeypatch.setattr(AsyncSession, "execute", _instrumented_async_session_execute)
    _CAPTURED_TXN.clear()
    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("txn") as (_, url):
        result = asyncio.run(
            _runner(url, g3_records=g3_records, g4_records=g4_records).run(source)
        )
        assert result.evaluation is not None

    assert _CAPTURED_TXN.get("transaction_isolation") == "repeatable read", _CAPTURED_TXN
    assert _CAPTURED_TXN.get("transaction_read_only") == "on", _CAPTURED_TXN


def test_missing_durable_order_fails_closed():
    """R4: a fill whose order_id points at no durable order must fail closed."""

    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("missing_order") as (_, url):
        result = asyncio.run(
            _runner(url, g3_records=g3_records, g4_records=g4_records).run(source)
        )
        assert result.evaluation is not None
        # Deliberate test-local corruption only: point a fill at an order id absent from
        # paper_orders. Production must not guess a side or fall back; it must fail closed.
        asyncio.run(_corrupt_fill_order_id(url, to_order_id="g5-4-nonexistent-order-id"))
        try:
            asyncio.run(_evaluate(url))
        except ReplayEvaluationError as exc:
            assert "has no durable order" in str(exc), str(exc)
        else:
            raise AssertionError("missing durable order must fail closed")


def test_unknown_order_side_fails_closed():
    """R5: an unsupported paper order side must fail closed, never be coerced to BUY/SELL."""

    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("bad_side") as (_, url):
        result = asyncio.run(
            _runner(url, g3_records=g3_records, g4_records=g4_records).run(source)
        )
        assert result.evaluation is not None
        # Deliberate test-local corruption only: set a paper order side to an unsupported value.
        # Production must not treat an unknown side as BUY/SELL; it must fail closed.
        # NOTE: paper_orders.side is VARCHAR(8) with no CHECK constraint, so a non-BUY/SELL value
        # must fit in 8 chars. "UNKNOWN" (7 chars) is unsupported and exercises the same fail-closed
        # path the reviewer's INVALID_SIDE intends; no schema change is used.
        asyncio.run(_corrupt_order_side(url, side="UNKNOWN"))
        try:
            asyncio.run(_evaluate(url))
        except ReplayEvaluationError as exc:
            assert "unsupported order side" in str(exc), str(exc)
        else:
            raise AssertionError("unknown order side must fail closed")


def test_recorded_g4_hold_is_consumed_without_fallback():
    source = _source(protective_stop_bid=89.0)
    g3_records, g4_records = asyncio.run(_recorded_inputs(source))

    with _replay_database("g4") as (_, url):
        result = asyncio.run(_runner(url, g3_records=g3_records, g4_records=g4_records).run(source))
        g4_decisions = asyncio.run(_g4_decisions(url))

    assert result.g4_provider_calls == 1
    assert g4_decisions == [("replay-recorded-g4", None)]
    assert result.evaluation is not None
