"""SE-02C durable Forward-outcome service acceptance against real PostgreSQL.

Two halves of SE-02C are proven here, both on a disposable database that the test
creates and drops itself, so no accepted database is ever touched:

* **Forward BBO path capture** (task §15-§19) -- the recorder stores a normalized
  observation *only* while a ``FORWARD_PAPER`` evidence window covers it, reuses
  the accepted content-addressed BBO identity (two opportunities therefore share
  one durable row) and never opens a second archive or a second writer;
* **durable due discovery + bounded evaluation** (task §39-§47, §57, §58) -- due
  work is re-derived from immutable evidence facts alone, one pass appends exactly
  one terminal revision-1 outcome per ``(opportunity, evidence revision, horizon)``
  scope, and a restart, a retry, a later clock or a concurrent second evaluator
  never mints revision 2.

No new schema, no migration and no resident loop: every durable write goes through
the accepted SE-02A / SE-02B repository writers.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    EdgeBboObservationRecord,
    EdgeForwardOutcomeRecord,
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.capture import (
    DEFAULT_REFERENCE_MAX_AGE,
    EdgeCaptureContext,
    ForwardAdmissionAuthority,
    ReferenceQuote,
    capture_opportunity,
)
from marketpulse.edge.forward import (
    ALL_FORWARD_HORIZONS,
    CALCULATOR_VERSION,
    COST_MODEL_VERSION,
    COST_POLICY,
    FEE_RATE,
    RUNTIME_OUTCOME_REVISION,
    SLIPPAGE_FRACTION,
    forward_due_at,
)
from marketpulse.edge.forward_service import (
    ForwardOutcomeService,
    ForwardPathRecorder,
    discover_due_scopes,
    evaluate_due_outcomes,
)
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    build_opportunity_identity,
)
from marketpulse.edge.repository import EdgeOutcomeConflict
from marketpulse.g2.models import (
    EventType,
    FeatureSnapshot,
    LifecycleAction,
    MarketEvent,
    MarketStructure,
    SignalTimelineEvent,
    StateApplyResult,
    StateTransition,
    SymbolState,
    SymbolStateRecord,
    Zone,
    deterministic_id,
)
from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.market_data.models import (
    DataQuality,
    MarketType,
    NormalizedBookTicker,
    NormalizedMarketEvent,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
INSTRUMENT = "BTC-USDT"
SECOND_INSTRUMENT = "ETH-USDT"
#: The evaluation clock of every scenario: all four horizons are already due.
EVAL_NOW = START + timedelta(seconds=3700)
PRIMARY_URL = Settings().database_url
BACKEND = Path(__file__).resolve().parents[1]

#: The anchor reference quote: mid 100.0, ask 100.5.
REFERENCE_BID = 99.5
REFERENCE_ASK = 100.5

#: Forward path frames as ``(seconds after START, bid, ask, source_sequence)``.
#: Offsets 29 / 299 / 899 / 3599 sit inside the frozen 5-second endpoint TTL of
#: the 30s / 5m / 15m / 1h horizon, so every horizon has one COMPLETE endpoint and
#: every later frame is future data for the shorter horizons.
FRAMES = (
    (10, 100.0, 100.4, 1),
    (29, 101.0, 101.2, 2),
    (299, 103.0, 105.0, 3),
    (899, 101.0, 101.2, 4),
    (3599, 102.0, 102.4, 5),
)
PATH_SOURCE = "fixture-bbo-path"


# --- disposable PostgreSQL harness ------------------------------------------------------


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


@asynccontextmanager
async def _sessions(url: str):
    engine = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@contextmanager
def _se02c_database(label: str):
    name = f"marketpulse_se02c_{label}_{uuid4().hex[:12]}"
    asyncio.run(_execute(PRIMARY_URL, f'CREATE DATABASE "{name}"'))
    url = _url_for(name)
    command.upgrade(_alembic_config(url), "head")
    try:
        yield url
    finally:
        asyncio.run(
            _execute(
                PRIMARY_URL,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute(PRIMARY_URL, f'DROP DATABASE "{name}"'))


async def _count(session, model) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)))


async def _durable(factory) -> dict[str, object]:
    """Read back every SE-02C-relevant durable fact, keyed deterministically."""

    async with factory() as session:
        evidence = (
            await session.scalars(
                select(EdgeOpportunityEvidenceRecord).order_by(
                    EdgeOpportunityEvidenceRecord.opportunity_id.asc()
                )
            )
        ).all()
        anchors = (
            await session.scalars(
                select(EdgeOpportunityCaptureAnchorRecord).order_by(
                    EdgeOpportunityCaptureAnchorRecord.opportunity_id.asc()
                )
            )
        ).all()
        observations = (
            await session.scalars(
                select(EdgeBboObservationRecord).order_by(
                    EdgeBboObservationRecord.available_at.asc(),
                    EdgeBboObservationRecord.observation_id.asc(),
                )
            )
        ).all()
        outcomes = (
            await session.scalars(
                select(EdgeForwardOutcomeRecord).order_by(
                    EdgeForwardOutcomeRecord.opportunity_id.asc(),
                    EdgeForwardOutcomeRecord.horizon.asc(),
                )
            )
        ).all()
        return {
            "evidence": list(evidence),
            "anchors": list(anchors),
            "observations": list(observations),
            "outcomes": list(outcomes),
            "observation_count": await _count(session, EdgeBboObservationRecord),
            "outcome_count": await _count(session, EdgeForwardOutcomeRecord),
        }


async def _durable_of(url: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        return await _durable(factory)


def _by_horizon(outcomes, opportunity_id: str | None = None) -> dict[str, object]:
    return {
        row.horizon: row
        for row in outcomes
        if opportunity_id is None or row.opportunity_id == opportunity_id
    }


# --- fixture facts ----------------------------------------------------------------------


def _features(*, at: datetime = START, instrument_id: str = INSTRUMENT) -> FeatureSnapshot:
    return FeatureSnapshot(
        instrument_id=instrument_id,
        symbol=instrument_id,
        market_type=MarketType.SPOT,
        event_time=at,
        current_price=100.5,
        short_return=0.02,
        buy_sell_imbalance=0.7,
        spread=0.5,
        structure=MarketStructure(
            recent_swing_high=101.0,
            recent_swing_low=95.0,
            breakout_level=100.0,
            retest_area=Zone(lower=99.0, upper=100.0, kind="retest", observed_at=at),
        ),
    )


def _event(
    *, event_id: str = "evt-se02c-1", at: datetime = START, instrument_id: str = INSTRUMENT
) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        symbol=instrument_id,
        instrument_id=instrument_id,
        market_type=MarketType.SPOT,
        event_type=EventType.BREAKOUT,
        event_time=at,
        received_time=at,
        source="fixture",
        strength=0.9,
        priority=80,
        state_version=0,
        config_version="g2-v1",
        payload={"current_price": 100.5},
    )


def _state(*, at: datetime = START, instrument_id: str = INSTRUMENT) -> SymbolStateRecord:
    return SymbolStateRecord(
        instrument_id=instrument_id,
        symbol=instrument_id,
        state=SymbolState.SETUP,
        state_version=1,
        last_event_time=at,
        watch_expires_at=at + timedelta(minutes=20),
    )


def _transition(*, event: MarketEvent, state: SymbolStateRecord) -> StateTransition:
    return StateTransition(
        transition_id=deterministic_id("st", event.event_id, state.state_version, "APPLIED"),
        instrument_id=event.instrument_id,
        symbol=event.symbol,
        from_state=SymbolState.WATCHING,
        to_state=SymbolState.SETUP,
        event_id=event.event_id,
        event_time=event.event_time,
        state_version=state.state_version,
        result=StateApplyResult.APPLIED,
        reason="evidence_upgrade",
    )


def _timeline(*, event: MarketEvent, state: SymbolStateRecord) -> SignalTimelineEvent:
    return SignalTimelineEvent(
        timeline_id=deterministic_id("tl", event.event_id, LifecycleAction.START),
        event_id=event.event_id,
        symbol=event.symbol,
        instrument_id=event.instrument_id,
        signal_type=event.event_type,
        event_time=event.event_time,
        received_time=event.received_time,
        price=100.5,
        context=event.payload,
        strength=event.strength,
        lifecycle_action=LifecycleAction.START,
        symbol_state=state.state,
        state_version=state.state_version,
        config_version=event.config_version,
    )


def _facts(
    *, event_id: str = "evt-se02c-1", at: datetime = START, instrument_id: str = INSTRUMENT
) -> dict[str, object]:
    event = _event(event_id=event_id, at=at, instrument_id=instrument_id)
    features = _features(at=at, instrument_id=instrument_id)
    state = _state(at=at, instrument_id=instrument_id)
    return {
        "event": event,
        "features": features,
        "state": state,
        "transition": _transition(event=event, state=state),
        "timeline": _timeline(event=event, state=state),
        "candidates": StrategyEngine(clock=ReplayClock(at)).candidates(
            features, event, state.state_version
        ),
    }


def _opportunity_id(facts) -> str:
    """The accepted SE-02B identity the durable evidence row must carry."""

    candidate = next(
        item for item in facts["candidates"] if item.strategy_id == "BREAKOUT_RETEST"
    )
    return build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=candidate.strategy_version,
        instrument_id=candidate.instrument_id,
        market_type=MarketType.SPOT,
        candidate_id=candidate.candidate_id,
    ).opportunity_id


def _quote(*, at: datetime = START, instrument_id: str = INSTRUMENT) -> ReferenceQuote:
    return ReferenceQuote(
        instrument_id=instrument_id,
        market_type=MarketType.SPOT,
        bid=REFERENCE_BID,
        ask=REFERENCE_ASK,
        received_at=at,
        data_quality=DataQuality.FRESH,
        tradable=True,
        source_event_time=at,
        source="fixture-bbo",
        source_sequence=1,
    )


def _context(*, source_type: EvidenceSource = EvidenceSource.FORWARD_PAPER) -> EdgeCaptureContext:
    return EdgeCaptureContext(
        source_type=source_type,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-se02c",
        reference_max_age=DEFAULT_REFERENCE_MAX_AGE,
    )


def _live_authority(*, at: datetime = START) -> ForwardAdmissionAuthority:
    return ForwardAdmissionAuthority(
        clock=ReplayClock(at),
        session_id="fixture-se02c-live-forward-session",
        secret=b"se-02c-fixture-live-ingress-secret",
    )


def _admitted(authority: ForwardAdmissionAuthority, event: MarketEvent):
    base, quote = event.instrument_id.split("-", 1)
    return authority.issue(
        source_event=NormalizedMarketEvent(
            exchange="OKX",
            base_asset=base,
            quote_asset=quote,
            market_type=event.market_type,
            instrument_id=event.instrument_id,
            event_time=event.event_time,
            received_time=event.received_time,
            source="fixture-live-ingress",
        ),
        event=event,
    )


def _ticker(
    *,
    bid: float,
    ask: float,
    at: datetime,
    instrument_id: str = INSTRUMENT,
    source_sequence: int | None = None,
    quality: DataQuality = DataQuality.FRESH,
) -> NormalizedBookTicker:
    base, quote = instrument_id.split("-", 1)
    return NormalizedBookTicker(
        exchange="OKX",
        base_asset=base,
        quote_asset=quote,
        market_type=MarketType.SPOT,
        instrument_id=instrument_id,
        event_time=at,
        received_time=at,
        source=PATH_SOURCE,
        freshness=quality,
        data_quality=quality,
        bid_price=bid,
        bid_quantity=1.0,
        ask_price=ask,
        ask_quantity=1.0,
    )


# --- scenario building blocks -----------------------------------------------------------


async def _persist(sessions, facts, context: EdgeCaptureContext, *, quote: ReferenceQuote | None):
    """Persist one G2 event through the accepted repository, anchor and all."""

    authority = _live_authority()
    quotes = {} if quote is None else {quote.instrument_id: quote}
    repository = PostgresG2Repository(
        sessions,
        capture=context,
        reference_quote_for=(lambda instrument_id: quotes.get(instrument_id)) if quotes else None,
        forward_admission_verifier=authority.verifier(),
    )
    precondition = await repository.get_state(facts["event"].instrument_id)
    return await repository.persist(
        facts["event"],
        facts["timeline"],
        facts["state"],
        facts["transition"],
        facts["candidates"],
        facts["features"],
        precondition_state=precondition
        or SymbolStateRecord(
            instrument_id=facts["event"].instrument_id, symbol=facts["event"].symbol
        ),
        forward_admission_proof=_admitted(authority, facts["event"]),
    )


async def _capture_forward_opportunity(
    sessions, *, event_id: str = "evt-se02c-1", instrument_id: str = INSTRUMENT
):
    """One qualifying Forward Paper opportunity with its FIX-01 anchor and anchor BBO."""

    facts = _facts(event_id=event_id, instrument_id=instrument_id)
    persisted = await _persist(
        sessions, facts, _context(), quote=_quote(instrument_id=instrument_id)
    )
    assert persisted is True, f"capture did not qualify for {event_id}"
    return facts


async def _capture_unanchored_evidence(sessions, *, event_id: str = "evt-se02c-unanchored"):
    """Evidence written without the FIX-01 anchor -- a structurally INVALID scope.

    ``capture_opportunity`` is the accepted SE-02B evidence writer and never writes
    an anchor (the G2 repository owns that). This is therefore exactly the durable
    shape a Forward Paper scope has when its anchor is missing.
    """

    facts = _facts(event_id=event_id)
    async with sessions() as session, session.begin():
        result = await capture_opportunity(
            session,
            event=facts["event"],
            timeline=facts["timeline"],
            state=facts["state"],
            transition=facts["transition"],
            candidates=facts["candidates"],
            observation=facts["features"],
            context=_context(),
            reference_quote=_quote(),
        )
    assert result == "INSERTED"
    return facts


async def _record_frames(sessions, frames=FRAMES) -> list[str | None]:
    recorder = ForwardPathRecorder(sessions)
    results: list[str | None] = []
    for offset, bid, ask, sequence in frames:
        results.append(
            await recorder.record_event(
                _ticker(
                    bid=bid,
                    ask=ask,
                    at=START + timedelta(seconds=offset),
                    source_sequence=sequence,
                )
            )
        )
    return results


async def _scope_of(factory, *, horizon: ForwardHorizon):
    async with factory() as session:
        scopes = await discover_due_scopes(session, now=EVAL_NOW, horizons=(horizon,))
    assert len(scopes) == 1, f"expected exactly one due {horizon.value} scope"
    return scopes[0]


async def _due_scopes(factory, *, horizons=ALL_FORWARD_HORIZONS):
    """Discover the due work of one moment, before any of it is settled."""

    async with factory() as session:
        return await discover_due_scopes(session, now=EVAL_NOW, horizons=horizons)


# --- §56 Forward BBO path capture --------------------------------------------------------


def test_forward_path_recorder_captures_only_inside_an_open_forward_window():
    with _se02c_database("recorder") as url:
        observed = asyncio.run(_recorder_scenario(url))
    assert observed["before_evidence"] is None
    assert observed["before_rows"] == 0
    assert observed["first"] == "INSERTED"
    assert observed["replay"] == "IDEMPOTENT"
    assert observed["second_opportunity"] == "IDEMPOTENT"
    assert observed["rows_after_shared_capture"] == 2
    assert observed["outside_window"] is None
    assert observed["unrepresentable"] is None
    assert observed["final_rows"] == 2
    assert observed["stored"] == {
        "bid": 100.0,
        "ask": 100.4,
        "available_at": START + timedelta(seconds=10),
        "created_at": START + timedelta(seconds=10),
        "data_quality": "FRESH",
        "tradable": True,
        "source": PATH_SOURCE,
    }


async def _recorder_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        recorder = ForwardPathRecorder(sessions)
        frame = _ticker(
            bid=100.0, ask=100.4, at=START + timedelta(seconds=10), source_sequence=1
        )

        # 1. No Forward evidence exists: the market is not archived at all.
        before = await recorder.record_event(frame)
        async with sessions() as session:
            before_rows = await _count(session, EdgeBboObservationRecord)

        # 2. Open a Forward window at START and capture the very same frame.
        await _capture_forward_opportunity(sessions)
        first = await recorder.record_event(frame)
        replay = await recorder.record_event(frame)

        # 3. A second, independent opportunity inside the same window shares the
        #    content-addressed observation instead of storing a second copy.
        await _capture_forward_opportunity(sessions, event_id="evt-se02c-2")
        second_opportunity = await recorder.record_event(frame)
        async with sessions() as session:
            rows_after_shared_capture = await _count(session, EdgeBboObservationRecord)

        # 4. One second past the frozen one-hour capture window: not a path fact.
        outside_window = await recorder.record_event(
            _ticker(
                bid=100.0,
                ask=100.4,
                at=START + timedelta(seconds=3601),
                source_sequence=9,
            )
        )
        # 5. A crossed book is unrepresentable in the accepted contract: skipped,
        #    never raised, never stored.
        unrepresentable = await recorder.record_event(
            _ticker(
                bid=101.0,
                ask=100.0,
                at=START + timedelta(seconds=11),
                source_sequence=10,
            )
        )

        durable = await _durable(sessions)
        stored = next(row for row in durable["observations"] if row.source == PATH_SOURCE)
        return {
            "before_evidence": before,
            "before_rows": before_rows,
            "first": first,
            "replay": replay,
            "second_opportunity": second_opportunity,
            "rows_after_shared_capture": rows_after_shared_capture,
            "outside_window": outside_window,
            "unrepresentable": unrepresentable,
            "final_rows": durable["observation_count"],
            "stored": {
                "bid": stored.bid,
                "ask": stored.ask,
                "available_at": stored.available_at,
                "created_at": stored.created_at,
                "data_quality": stored.data_quality,
                "tradable": stored.tradable,
                "source": stored.source,
            },
        }


def test_forward_window_ignores_historical_replay_evidence():
    with _se02c_database("replay_window") as url:
        observed = asyncio.run(_replay_window_scenario(url))
    assert observed["evidence_source_type"] == "HISTORICAL_REPLAY"
    assert observed["anchor_present"] is False
    assert observed["recorded"] is None
    assert observed["rows"] == 0


async def _replay_window_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts(event_id="evt-se02c-replay")
        await _persist(
            sessions, facts, _context(source_type=EvidenceSource.HISTORICAL_REPLAY), quote=_quote()
        )
        recorded = await ForwardPathRecorder(sessions).record_event(
            _ticker(bid=100.0, ask=100.4, at=START + timedelta(seconds=10), source_sequence=1)
        )
        durable = await _durable(sessions)
        return {
            "evidence_source_type": durable["evidence"][0].source_type,
            "anchor_present": bool(durable["anchors"]),
            "recorded": recorded,
            "rows": durable["observation_count"],
        }


# --- §39-§40 durable due discovery -------------------------------------------------------


def test_due_discovery_is_derived_from_immutable_facts_and_the_clock():
    with _se02c_database("discovery") as url:
        observed = asyncio.run(_discovery_scenario(url))
    assert observed["before_due"] == []
    assert observed["at_30s_due"] == ["30s"]
    assert observed["planned_due_at"] == observed["expected_due_at"]
    assert observed["statuses"] == ["OK"] * 4
    assert observed["anchor_bound"] == [True] * 4
    assert observed["evidence_at"] == [START] * 4
    assert observed["planned_horizons"] == ["30s", "5m", "15m", "1h"]


async def _discovery_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        async with sessions() as session:
            before_due = await discover_due_scopes(session, now=START + timedelta(seconds=29))
            at_due = await discover_due_scopes(session, now=START + timedelta(seconds=30))
            planned = await discover_due_scopes(session, now=EVAL_NOW)
        return {
            "before_due": [scope.horizon.value for scope in before_due],
            "at_30s_due": [scope.horizon.value for scope in at_due],
            "planned_horizons": [scope.horizon.value for scope in planned],
            "planned_due_at": [scope.due_at for scope in planned],
            "expected_due_at": [forward_due_at(START, horizon) for horizon in ALL_FORWARD_HORIZONS],
            "statuses": [scope.reference_data_status.value for scope in planned],
            "anchor_bound": [
                scope.anchor_reference_bbo_observation_id is not None for scope in planned
            ],
            "evidence_at": [scope.evidence_at for scope in planned],
        }


# --- §43-§47 one terminal revision per scope, restart safe -------------------------------


def test_one_evaluation_pass_appends_one_terminal_outcome_per_scope_and_a_restart_changes_nothing():
    with _se02c_database("restart") as url:
        observed = asyncio.run(_restart_scenario(url))
    assert observed["first_pass_horizons"] == ["30s", "5m", "15m", "1h"]
    assert set(observed["statuses"].values()) == {"COMPLETE"}
    assert set(observed["revisions"].values()) == {1}
    assert all(observed["created_at_is_due_at"].values())
    assert observed["distinct_outcome_ids"] == 4
    assert observed["end_ids_are_bound_and_fresh"] == 4
    assert observed["loaded_counts"] == {"30s": 3, "5m": 4, "15m": 5, "1h": 6}
    assert observed["durable_observation_count"] == 6
    assert observed["rediscovered_by_fresh_process"] == []
    assert observed["rediscovered_with_a_later_clock"] == []
    assert observed["second_pass_outcomes"] == 0
    assert observed["retry_returned_the_durable_twin"] is True
    assert observed["outcome_count_at_the_end"] == 4
    assert observed["reference_binds_capture_anchor"] is True
    assert observed["reference_is_the_anchor_mid"] is True
    assert observed["provenance"] == {
        "calculator_version": CALCULATOR_VERSION,
        "cost_policy": COST_POLICY,
        "cost_model_version": COST_MODEL_VERSION,
        "revision": RUNTIME_OUTCOME_REVISION,
    }


async def _restart_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = await _capture_forward_opportunity(sessions)
        recorded = await _record_frames(sessions)
        opportunity_id = _opportunity_id(facts)
    assert recorded == ["INSERTED"] * len(FRAMES)

    # Process 1: one bounded pass over every due scope.
    engine1 = create_async_engine(url, poolclass=NullPool)
    try:
        factory1 = async_sessionmaker(engine1, expire_on_commit=False)
        # Due work is discovered *before* the pass: afterwards every scope is
        # settled, which is exactly what a restart must observe.
        m5_scope = next(
            scope for scope in await _due_scopes(factory1) if scope.horizon is ForwardHorizon.M5
        )
        first_pass = await evaluate_due_outcomes(factory1, now=EVAL_NOW)
        after_first_pass = await _durable(factory1)
    finally:
        await engine1.dispose()

    # Process 2: a brand-new engine (new pool, new connections) with no inherited
    # memory of the first pass, re-deriving everything from durable facts.
    engine2 = create_async_engine(url, poolclass=NullPool)
    try:
        factory2 = async_sessionmaker(engine2, expire_on_commit=False)
        async with factory2() as session:
            rediscovered = await discover_due_scopes(session, now=EVAL_NOW)
            with_later_clock = await discover_due_scopes(session, now=EVAL_NOW + timedelta(hours=4))
        second_pass = await evaluate_due_outcomes(factory2, now=EVAL_NOW)
        retried = await ForwardOutcomeService(factory2).evaluate_scope(m5_scope)
        at_the_end = await _durable(factory2)
    finally:
        await engine2.dispose()

    by_horizon = _by_horizon(after_first_pass["outcomes"])
    anchor = after_first_pass["anchors"][0]
    anchor_bbo = next(
        row
        for row in after_first_pass["observations"]
        if row.observation_id == anchor.reference_bbo_observation_id
    )
    return {
        "first_pass_horizons": [outcome.horizon.value for outcome in first_pass],
        "statuses": {row.horizon: row.calculation_status for row in by_horizon.values()},
        "revisions": {row.horizon: row.outcome_revision for row in by_horizon.values()},
        "created_at_is_due_at": {
            row.horizon: row.created_at == row.due_at for row in by_horizon.values()
        },
        "distinct_outcome_ids": len({row.outcome_id for row in by_horizon.values()}),
        "end_ids_are_bound_and_fresh": sum(
            1
            for row in by_horizon.values()
            if row.end_bbo_observation_id is not None
            and row.completeness_diagnostics["end_age_seconds"] <= 5.0
        ),
        "loaded_counts": {
            row.horizon: row.completeness_diagnostics["observation_count"]
            for row in by_horizon.values()
        },
        "durable_observation_count": after_first_pass["observation_count"],
        "rediscovered_by_fresh_process": [scope.horizon.value for scope in rediscovered],
        "rediscovered_with_a_later_clock": [scope.horizon.value for scope in with_later_clock],
        "second_pass_outcomes": len(second_pass),
        "retry_returned_the_durable_twin": (
            retried.outcome_id == by_horizon[ForwardHorizon.M5.value].outcome_id
        ),
        "outcome_count_at_the_end": at_the_end["outcome_count"],
        "reference_binds_capture_anchor": (
            by_horizon[ForwardHorizon.M5.value].reference_bbo_observation_id
            == anchor.reference_bbo_observation_id
        ),
        "reference_is_the_anchor_mid": (
            by_horizon[ForwardHorizon.M5.value].reference_price
            == (anchor_bbo.bid + anchor_bbo.ask) / 2
            == (REFERENCE_BID + REFERENCE_ASK) / 2
        ),
        "provenance": {
            "calculator_version": by_horizon[ForwardHorizon.M5.value].calculator_version,
            "cost_policy": by_horizon[ForwardHorizon.M5.value].cost_policy,
            "cost_model_version": by_horizon[ForwardHorizon.M5.value].cost_model_version,
            "revision": by_horizon[ForwardHorizon.M5.value].outcome_revision,
        },
        "opportunity_id": opportunity_id,
    }


# --- §53/§54 the frozen formula and the status matrix through the durable path ------------


def test_complete_outcome_persists_the_frozen_v1_formula_from_durable_facts_only():
    with _se02c_database("formula") as url:
        observed = asyncio.run(_formula_scenario(url))
    assert observed["status"] == "COMPLETE"
    assert observed["lifecycle"] == "ACTIVE"
    assert observed["endpoint"] == {
        "bid": 103.0,
        "ask": 105.0,
        "available_at": START + timedelta(seconds=299),
    }
    assert observed["reference_price"] == 100.0
    assert observed["mfe"] == pytest.approx(0.04, rel=1e-12)
    assert observed["mae"] == 0.0
    assert observed["reference_return"] == pytest.approx(observed["expected_reference_return"], rel=1e-12)
    assert observed["executable_long_return"] == pytest.approx(
        observed["expected_executable_long_return"], rel=1e-12
    )
    assert observed["cost_adjusted_forward_return"] == pytest.approx(
        observed["expected_cost_adjusted"], rel=1e-12
    )
    assert observed["cost_adjusted_differs_from_the_approximation"] is True
    assert observed["digests_are_present"] is True


async def _formula_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        outcomes = await evaluate_due_outcomes(factory, now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    outcome = next(item for item in outcomes if item.horizon is ForwardHorizon.M5)
    stored = next(item for item in durable["outcomes"] if item.horizon == "5m")
    endpoint = next(
        item
        for item in durable["observations"]
        if item.observation_id == stored.end_bbo_observation_id
    )
    expected_reference_return = 104.0 / 100.0 - 1
    expected_executable = 103.0 / REFERENCE_ASK - 1
    expected_cost_adjusted = (
        (103.0 * (1 - SLIPPAGE_FRACTION) * (1 - FEE_RATE))
        / (REFERENCE_ASK * (1 + SLIPPAGE_FRACTION) * (1 + FEE_RATE))
        - 1
    )
    approximation = expected_executable - 2 * FEE_RATE - 2 * SLIPPAGE_FRACTION
    return {
        "status": stored.calculation_status,
        "lifecycle": stored.opportunity_lifecycle_at_horizon,
        "endpoint": {
            "bid": endpoint.bid,
            "ask": endpoint.ask,
            "available_at": endpoint.available_at,
        },
        "reference_price": stored.reference_price,
        "mfe": stored.mfe,
        "mae": stored.mae,
        "reference_return": stored.reference_return,
        "executable_long_return": stored.executable_long_return,
        "cost_adjusted_forward_return": stored.cost_adjusted_forward_return,
        "expected_reference_return": expected_reference_return,
        "expected_executable_long_return": expected_executable,
        "expected_cost_adjusted": expected_cost_adjusted,
        "cost_adjusted_differs_from_the_approximation": (
            abs(stored.cost_adjusted_forward_return - approximation) > 1e-9
        ),
        "digests_are_present": bool(stored.calculation_digest and stored.outcome_record_hash),
        "service_status": outcome.calculation_status.value,
    }


def test_terminal_status_matrix_is_persisted_without_any_pending_row():
    with _se02c_database("status") as url:
        observed = asyncio.run(_status_scenario(url))
    assert observed["complete_status"] == "COMPLETE"
    assert observed["complete_reason"] == "COMPLETE"
    assert observed["complete_binds_both_observations"] is True
    assert observed["insufficient_status"] == "INSUFFICIENT_DATA"
    # The observed reason follows directly from the durable facts: see the
    # comment on the ETH scope in the scenario below.
    assert observed["insufficient_reason"] == observed["expected_insufficient_reason"]
    assert observed["insufficient_metrics_are_null"] is True
    assert observed["insufficient_end_is_not_bound"] is True
    assert observed["insufficient_reference_is_bound"] is True
    assert observed["invalid_status"] == "INVALID"
    assert observed["invalid_reason"] == "INVALID_FORWARD_ANCHOR_MISSING"
    assert observed["invalid_binds_nothing"] is True
    assert observed["statuses"] == ["COMPLETE", "INSUFFICIENT_DATA", "INVALID"]
    assert observed["pending_rows"] == 0
    assert observed["eth_durable_observations"] == 1
    assert observed["outcome_count"] == 12


async def _status_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        complete_facts = await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)
        # A Forward scope whose evidence exists but whose FIX-01 anchor never did.
        invalid_facts = await _capture_unanchored_evidence(sessions)
        # A second instrument with an anchor but no forward path observation.
        empty_facts = await _capture_forward_opportunity(
            sessions, event_id="evt-se02c-eth", instrument_id=SECOND_INSTRUMENT
        )
    complete_id = _opportunity_id(complete_facts)
    invalid_id = _opportunity_id(invalid_facts)
    empty_id = _opportunity_id(empty_facts)

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        outcomes = await evaluate_due_outcomes(factory, now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    complete = _by_horizon(durable["outcomes"], complete_id)["5m"]
    insufficient = _by_horizon(durable["outcomes"], empty_id)["5m"]
    invalid = _by_horizon(durable["outcomes"], invalid_id)["5m"]
    # The ETH scope has an anchor but no forward path observation of its own, so
    # the only in-window candidate is the anchor BBO itself. The frozen rule
    # therefore reports ENDPOINT_MISSING when that window is empty and
    # ENDPOINT_STALE when the anchor is the candidate -- both are
    # INSUFFICIENT_DATA with every metric NULL, which is what this test pins.
    eth_window = [
        row for row in durable["observations"] if row.instrument_id == SECOND_INSTRUMENT
    ]
    return {
        "eth_durable_observations": len(eth_window),
        "complete_status": complete.calculation_status,
        "complete_reason": complete.completeness_diagnostics["reason"],
        "complete_binds_both_observations": (
            complete.reference_bbo_observation_id is not None
            and complete.end_bbo_observation_id is not None
        ),
        "insufficient_status": insufficient.calculation_status,
        "insufficient_reason": insufficient.completeness_diagnostics["reason"],
        "expected_insufficient_reason": "ENDPOINT_MISSING" if not eth_window else "ENDPOINT_STALE",
        "insufficient_metrics_are_null": all(
            getattr(insufficient, field) is None
            for field in (
                "mfe",
                "mae",
                "reference_return",
                "executable_long_return",
                "end_bid",
                "end_ask",
            )
        ),
        # An INSUFFICIENT_DATA outcome still binds the reference it *did* accept;
        # only the horizon endpoint (and every metric derived from it) stays NULL.
        "insufficient_end_is_not_bound": (
            insufficient.end_bbo_observation_id is None and insufficient.end_bid is None
        ),
        "insufficient_reference_is_bound": insufficient.reference_bbo_observation_id is not None,
        "invalid_status": invalid.calculation_status,
        "invalid_reason": invalid.completeness_diagnostics["reason"],
        "invalid_binds_nothing": (
            invalid.reference_bbo_observation_id is None
            and invalid.end_bbo_observation_id is None
            and invalid.mfe is None
        ),
        "statuses": sorted({row.calculation_status for row in durable["outcomes"]}),
        "pending_rows": sum(1 for row in durable["outcomes"] if row.calculation_status == "PENDING"),
        "outcome_count": durable["outcome_count"],
        "service_outcomes": len(outcomes),
    }


# --- §22/§48 future data can never be the endpoint ---------------------------------------


def test_observations_after_due_at_are_durable_but_never_reach_the_calculation():
    with _se02c_database("causal") as url:
        observed = asyncio.run(_causal_scenario(url))
    assert observed["durable_observation_count"] == 6
    assert observed["loaded_counts"] == {"30s": 3, "5m": 4, "15m": 5, "1h": 6}
    assert observed["paths"] == {"30s": 2, "5m": 3, "15m": 4, "1h": 5}
    assert observed["endpoints"] == {
        "30s": START + timedelta(seconds=29),
        "5m": START + timedelta(seconds=299),
        "15m": START + timedelta(seconds=899),
        "1h": START + timedelta(seconds=3599),
    }
    assert observed["never_selects_a_later_frame"] is True


async def _causal_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        await evaluate_due_outcomes(factory, now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    by_horizon = _by_horizon(durable["outcomes"])
    endpoints = {
        row.horizon: next(
            observation.available_at
            for observation in durable["observations"]
            if observation.observation_id == row.end_bbo_observation_id
        )
        for row in by_horizon.values()
    }
    return {
        "durable_observation_count": durable["observation_count"],
        "loaded_counts": {
            row.horizon: row.completeness_diagnostics["observation_count"]
            for row in by_horizon.values()
        },
        "paths": {
            row.horizon: row.completeness_diagnostics["path_point_count"]
            for row in by_horizon.values()
        },
        "endpoints": endpoints,
        "never_selects_a_later_frame": all(
            endpoints[row.horizon] <= row.due_at for row in by_horizon.values()
        ),
    }


# --- §58 concurrency: exactly one durable outcome ----------------------------------------


def test_two_concurrent_evaluators_append_exactly_one_outcome_for_the_scope():
    with _se02c_database("concurrency") as url:
        observed = asyncio.run(_concurrency_scenario(url))
    assert observed["due_scopes"] == 1
    assert observed["outcome_count"] == 1
    assert observed["distinct_returned_outcome_ids"] == 1
    assert observed["distinct_returned_hashes"] == 1
    assert observed["both_callers_hold_the_durable_row"] is True
    assert observed["revision"] == 1
    assert observed["second_wave_outcome_count"] == 1


async def _concurrency_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)

    engines = [create_async_engine(url, poolclass=NullPool) for _ in range(2)]
    try:
        factories = [async_sessionmaker(engine, expire_on_commit=False) for engine in engines]
        scope = await _scope_of(factories[0], horizon=ForwardHorizon.S30)
        services = [
            ForwardOutcomeService(factory, horizons=(ForwardHorizon.S30,)) for factory in factories
        ]
        results = await asyncio.gather(*(service.evaluate_scope(scope) for service in services))
        durable = await _durable(factories[0])
        stored = durable["outcomes"][0]

        async with factories[1]() as session:
            unsettled = await discover_due_scopes(
                session, now=EVAL_NOW, horizons=(ForwardHorizon.S30,)
            )
        second_wave = await asyncio.gather(*(service.evaluate_scope(scope) for service in services))
        after = await _durable(factories[1])
    finally:
        for engine in engines:
            await engine.dispose()

    return {
        "due_scopes": 1,
        "unsettled_before_second_wave": len(unsettled),
        "outcome_count": durable["outcome_count"],
        "distinct_returned_outcome_ids": len({result.outcome_id for result in results}),
        "distinct_returned_hashes": len({result.outcome_record_hash for result in results}),
        "both_callers_hold_the_durable_row": all(
            result.outcome_id == stored.outcome_id
            and result.outcome_record_hash == stored.outcome_record_hash
            for result in results
        ),
        "revision": stored.outcome_revision,
        "second_wave_outcome_count": after["outcome_count"],
        "second_wave_ids": len({result.outcome_id for result in second_wave}),
    }


# --- §46 immutability: a settled scope never grows an automatic revision 2 ----------------


def test_a_settled_scope_never_grows_an_automatic_revision_two():
    with _se02c_database("immutable") as url:
        observed = asyncio.run(_immutable_scenario(url))
    assert observed["first_outcome_id"] == observed["retry_outcome_id"]
    assert observed["outcome_count"] == 4
    assert set(observed["revisions"].values()) == {1}
    assert observed["unsettled_after_a_late_frame"] == []
    assert observed["changed_facts_conflict"] is True
    assert observed["outcome_count_after_conflict"] == 4
    assert observed["hash_unchanged"] is True


async def _immutable_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        m5_scope = next(
            scope for scope in await _due_scopes(factory) if scope.horizon is ForwardHorizon.M5
        )
        first = await evaluate_due_outcomes(factory, now=EVAL_NOW)
        service = ForwardOutcomeService(factory)
        # A retry over identical durable facts is idempotent.
        retry = await service.evaluate_scope(m5_scope)
        before = await _durable(factory)
        hash_before = _by_horizon(before["outcomes"])["5m"].outcome_record_hash

        # A late frame inside the same window arrives after settlement. Discovery
        # still refuses to re-open the scope, and a forced re-evaluation surfaces
        # the accepted writer's conflict instead of minting revision 2.
        await ForwardPathRecorder(factory).record_event(
            _ticker(bid=104.0, ask=104.4, at=START + timedelta(seconds=298), source_sequence=7)
        )
        async with factory() as session:
            unsettled = await discover_due_scopes(session, now=EVAL_NOW)
        conflicted = False
        try:
            await service.evaluate_scope(m5_scope)
        except EdgeOutcomeConflict:
            conflicted = True
        after = await _durable(factory)
    finally:
        await engine.dispose()

    return {
        "first_outcome_id": next(
            item for item in first if item.horizon is ForwardHorizon.M5
        ).outcome_id,
        "retry_outcome_id": retry.outcome_id,
        "outcome_count": before["outcome_count"],
        "revisions": {
            row.horizon: row.outcome_revision for row in _by_horizon(after["outcomes"]).values()
        },
        "unsettled_after_a_late_frame": [item.horizon.value for item in unsettled],
        "changed_facts_conflict": conflicted,
        "outcome_count_after_conflict": after["outcome_count"],
        "hash_unchanged": _by_horizon(after["outcomes"])["5m"].outcome_record_hash == hash_before,
    }
