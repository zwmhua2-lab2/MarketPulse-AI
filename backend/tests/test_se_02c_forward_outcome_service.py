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
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import marketpulse.edge.forward_service as forward_service_module
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
    FORWARD_PATH_READ_PAGE_SIZE,
    ForwardOutcomeService,
    ForwardPathRecorder,
    ForwardPathTradabilityUnknown,
    _scope_advisory_lock_key,
    build_forward_path_observation,
    discover_due_scopes,
    evaluate_due_outcomes,
)
from marketpulse.edge.models import (
    BboObservation,
    EdgeFamily,
    EvidenceSource,
    ForwardHorizon,
    ReferenceDataStatus,
    build_bbo_observation,
    build_evidence_revision,
    build_opportunity_identity,
)
from marketpulse.edge.repository import append_evidence_revision, record_bbo_observation
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
    Instrument,
    MarketType,
    NormalizedBookTicker,
    NormalizedMarketEvent,
)
from marketpulse.market_data.normalizer import normalize_book_ticker
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
    try:
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = url
        try:
            command.upgrade(_alembic_config(url), "head")
        finally:
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url
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
    tradable: bool | None = True,
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
        # SE-02C-FIX-01: tradability is an authoritative fact carried through the
        # normalized frame, never inferred from "a quote arrived". Existing
        # scenarios pass it explicitly; ``None`` exercises the fail-closed path.
        tradable=tradable,
    )


def _instrument(*, instrument_id: str = INSTRUMENT, tradable: bool = True) -> Instrument:
    """The real G1 instrument boundary: ``tradable`` comes from OKX ``state``."""

    base, quote = instrument_id.split("-", 1)
    return Instrument(
        base_asset=base,
        quote_asset=quote,
        market_type=MarketType.SPOT,
        instrument_id=instrument_id,
        trading_symbol=instrument_id,
        tradable=tradable,
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


async def _record_frames(
    sessions, frames=FRAMES, *, instrument_id: str = INSTRUMENT
) -> list[str | None]:
    recorder = ForwardPathRecorder(sessions)
    results: list[str | None] = []
    for offset, bid, ask, sequence in frames:
        results.append(
            await recorder.record_event(
                _ticker(
                    bid=bid,
                    ask=ask,
                    at=START + timedelta(seconds=offset),
                    instrument_id=instrument_id,
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


class _PageOnePausedForwardOutcomeService(ForwardOutcomeService):
    """Test witness that pauses only after the real first path SELECT has returned."""

    def __init__(self, *args, page_one_loaded: asyncio.Event, resume: asyncio.Event, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_one_loaded = page_one_loaded
        self.resume = resume
        self.snapshot_isolation: str | None = None
        self.snapshot_read_only: str | None = None
        self.reference_session_id: int | None = None
        self.path_session_id: int | None = None
        self.calculation_count = 0

    async def calculate_scope(self, scope):
        self.calculation_count += 1
        return await super().calculate_scope(scope)

    async def _resolve_reference(self, session, scope):
        result = await super()._resolve_reference(session, scope)
        self.reference_session_id = id(session)
        self.snapshot_isolation = await session.scalar(text("SHOW transaction_isolation"))
        self.snapshot_read_only = await session.scalar(text("SHOW transaction_read_only"))
        return result

    async def _load_observations(self, session, scope):
        self.path_session_id = id(session)
        original_scalars = session.scalars
        page_count = 0

        async def paused_scalars(*args, **kwargs):
            nonlocal page_count
            result = await original_scalars(*args, **kwargs)
            page_count += 1
            if page_count == 1:
                self.page_one_loaded.set()
                await self.resume.wait()
            return result

        session.scalars = paused_scalars
        try:
            return await super()._load_observations(session, scope)
        finally:
            session.scalars = original_scalars


class _CountingForwardOutcomeService(ForwardOutcomeService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculation_count = 0

    async def calculate_scope(self, scope):
        self.calculation_count += 1
        return await super().calculate_scope(scope)


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
        "source_type": "FORWARD_PAPER",
        "source_identity": "okx-ws-bbo",
        "evidence_source_type": "FORWARD_PAPER",
        "evidence_source_identity": "okx-ws-bbo",
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
            # C-24: the outcome inherits its provenance from the evidence revision
            # it was computed from, never from the evaluating process.
            "source_type": by_horizon[ForwardHorizon.M5.value].source_type,
            "source_identity": by_horizon[ForwardHorizon.M5.value].source_identity,
            "evidence_source_type": after_first_pass["evidence"][0].source_type,
            "evidence_source_identity": after_first_pass["evidence"][0].source_identity,
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
    # R4: the anchor-only scope reports ENDPOINT_MISSING -- the capture anchor is
    # the reference authority only and can never be a horizon endpoint.
    assert observed["insufficient_reason"] == observed["expected_insufficient_reason"]
    assert observed["insufficient_reason"] == "ENDPOINT_MISSING"
    assert observed["eth_durable_observations"] == 1
    assert observed["eth_window_available_at_equals_evidence_at"] is True
    assert observed["eth_window_path_point_count"] == 0
    assert observed["insufficient_metrics_are_null"] is True
    assert observed["insufficient_end_is_not_bound"] is True
    assert observed["insufficient_reference_is_bound"] is True
    assert observed["invalid_status"] == "INVALID"
    assert observed["invalid_reason"] == "INVALID_FORWARD_ANCHOR_MISSING"
    assert observed["invalid_binds_nothing"] is True
    assert observed["statuses"] == ["COMPLETE", "INSUFFICIENT_DATA", "INVALID"]
    assert observed["pending_rows"] == 0
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
    # the only in-window durable row is the anchor BBO itself (available_at ==
    # evidence_at). SE-02C-FIX-01 (R4): the FIX-01 capture anchor is the
    # *reference authority only* and is never a horizon endpoint, so this now
    # reports ENDPOINT_MISSING rather than mistaking the anchor for a stale
    # endpoint -- still INSUFFICIENT_DATA with every metric NULL, which is what
    # this test pins.
    eth_window = [
        row for row in durable["observations"] if row.instrument_id == SECOND_INSTRUMENT
    ]
    return {
        "eth_durable_observations": len(eth_window),
        "eth_window_available_at_equals_evidence_at": (
            bool(eth_window) and all(row.available_at == START for row in eth_window)
        ),
        "eth_window_path_point_count": insufficient.completeness_diagnostics[
            "path_point_count"
        ],
        "complete_status": complete.calculation_status,
        "complete_reason": complete.completeness_diagnostics["reason"],
        "complete_binds_both_observations": (
            complete.reference_bbo_observation_id is not None
            and complete.end_bbo_observation_id is not None
        ),
        "insufficient_status": insufficient.calculation_status,
        "insufficient_reason": insufficient.completeness_diagnostics["reason"],
        "expected_insufficient_reason": "ENDPOINT_MISSING",
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


def test_scope_advisory_lock_key_uses_the_frozen_canonical_sha256_contract():
    assert (
        _scope_advisory_lock_key("opp-fixed", "ev-fixed", ForwardHorizon.M5)
        == 750_685_418_615_989_498
    )
    assert _scope_advisory_lock_key(
        "opp-fixed", "ev-fixed", ForwardHorizon.S30
    ) != _scope_advisory_lock_key("opp-fixed", "ev-fixed", ForwardHorizon.M5)


@pytest.mark.parametrize(
    ("cursor_position", "late_offset"),
    (("after", 300), ("before", 100)),
    ids=("cursor-after", "cursor-before"),
)
def test_late_commit_is_excluded_by_the_stable_snapshot_and_visible_to_a_fresh_scope(
    monkeypatch, cursor_position: str, late_offset: int
):
    monkeypatch.setattr(forward_service_module, "FORWARD_PATH_READ_PAGE_SIZE", 2)
    with _se02c_database(f"snapshot_{cursor_position}") as url:
        observed = asyncio.run(_snapshot_boundary_scenario(url, late_offset=late_offset))

    assert observed["initial_rows_span_multiple_pages"] is True
    assert observed["snapshot_isolation"] == "repeatable read"
    assert observed["snapshot_read_only"] == "on"
    assert observed["reference_and_path_session_match"] is True
    assert observed["late_key_relation_matches_case"] is True
    assert observed["late_row_is_market_time_eligible"] is True
    assert observed["late_rows_durable"] is True
    assert observed["current_loaded_count"] == observed["baseline_loaded_count"]
    assert observed["current_endpoint"] == observed["baseline_endpoint"]
    assert observed["current_mfe"] == observed["baseline_mfe"]
    assert observed["current_mae"] == observed["baseline_mae"]
    assert observed["current_calculation_digest"] == observed["baseline_calculation_digest"]
    assert observed["current_outcome_hash"] == observed["baseline_outcome_hash"]
    assert observed["fresh_loaded_count"] == observed["fresh_baseline_loaded_count"] + 1
    assert observed["fresh_mfe"] > observed["fresh_baseline_mfe"]
    assert observed["fresh_calculation_digest"] != observed["fresh_baseline_calculation_digest"]
    assert observed["fresh_outcome_hash"] != observed["fresh_baseline_outcome_hash"]
    if cursor_position == "after":
        assert observed["fresh_endpoint"] == observed["fresh_late_observation_id"]
        assert observed["fresh_endpoint"] != observed["fresh_baseline_endpoint"]
    else:
        assert observed["fresh_endpoint"] == observed["fresh_baseline_endpoint"]


async def _snapshot_boundary_scenario(url: str, *, late_offset: int) -> dict[str, object]:
    initial_frames = (
        (298, 100.9, 101.1, 10),
        (299, 101.9, 102.1, 20),
    )
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        await _capture_forward_opportunity(
            sessions, event_id="evt-se02c-snapshot-control", instrument_id=SECOND_INSTRUMENT
        )
        await _record_frames(sessions, initial_frames)
        await _record_frames(sessions, initial_frames, instrument_id=SECOND_INSTRUMENT)

        scopes = await _due_scopes(sessions, horizons=(ForwardHorizon.M5,))
        primary_scope = next(scope for scope in scopes if scope.instrument_id == INSTRUMENT)
        control_scope = next(
            scope for scope in scopes if scope.instrument_id == SECOND_INSTRUMENT
        )
        baseline_service = ForwardOutcomeService(sessions, horizons=(ForwardHorizon.M5,))
        baseline = await baseline_service.calculate_scope(primary_scope)
        fresh_baseline = await baseline_service.calculate_scope(control_scope)

        page_one_loaded = asyncio.Event()
        resume = asyncio.Event()
        paused_service = _PageOnePausedForwardOutcomeService(
            sessions,
            horizons=(ForwardHorizon.M5,),
            page_one_loaded=page_one_loaded,
            resume=resume,
        )
        calculation = asyncio.create_task(paused_service.calculate_scope(primary_scope))
        await asyncio.wait_for(page_one_loaded.wait(), timeout=5)

        late_at = START + timedelta(seconds=late_offset)
        late_observations = tuple(
            build_bbo_observation(
                instrument_id=instrument_id,
                market_type=MarketType.SPOT,
                bid=109.0,
                ask=111.0,
                available_at=late_at,
                source_event_time=late_at,
                received_at=late_at,
                data_quality=DataQuality.FRESH,
                tradable=True,
                source="fixture-snapshot-late",
                source_sequence=99,
                created_at=late_at,
            )
            for instrument_id in (INSTRUMENT, SECOND_INSTRUMENT)
        )
        async with sessions() as writer, writer.begin():
            for observation in late_observations:
                assert await record_bbo_observation(writer, observation) == "INSERTED"

        async with sessions() as verifier:
            late_rows_durable = True
            for observation in late_observations:
                if (
                    await verifier.get(
                        EdgeBboObservationRecord, observation.observation_id
                    )
                    is None
                ):
                    late_rows_durable = False
        resume.set()
        current = await asyncio.wait_for(calculation, timeout=5)
        fresh = await baseline_service.calculate_scope(control_scope)

    return {
        "initial_rows_span_multiple_pages": (
            baseline.completeness_diagnostics["observation_count"] > 2
        ),
        "snapshot_isolation": paused_service.snapshot_isolation,
        "snapshot_read_only": paused_service.snapshot_read_only,
        "reference_and_path_session_match": (
            paused_service.reference_session_id == paused_service.path_session_id
        ),
        "late_key_relation_matches_case": (
            late_at > START + timedelta(seconds=298)
            if late_offset == 300
            else late_at < START + timedelta(seconds=298)
        ),
        "late_row_is_market_time_eligible": late_at <= primary_scope.due_at,
        "late_rows_durable": late_rows_durable,
        "baseline_loaded_count": baseline.completeness_diagnostics["observation_count"],
        "current_loaded_count": current.completeness_diagnostics["observation_count"],
        "baseline_endpoint": baseline.end_bbo_observation_id,
        "current_endpoint": current.end_bbo_observation_id,
        "baseline_mfe": baseline.mfe,
        "current_mfe": current.mfe,
        "baseline_mae": baseline.mae,
        "current_mae": current.mae,
        "baseline_calculation_digest": baseline.calculation_digest,
        "current_calculation_digest": current.calculation_digest,
        "baseline_outcome_hash": baseline.outcome_record_hash,
        "current_outcome_hash": current.outcome_record_hash,
        "fresh_baseline_loaded_count": fresh_baseline.completeness_diagnostics[
            "observation_count"
        ],
        "fresh_loaded_count": fresh.completeness_diagnostics["observation_count"],
        "fresh_baseline_endpoint": fresh_baseline.end_bbo_observation_id,
        "fresh_endpoint": fresh.end_bbo_observation_id,
        "fresh_late_observation_id": late_observations[1].observation_id,
        "fresh_baseline_mfe": fresh_baseline.mfe,
        "fresh_mfe": fresh.mfe,
        "fresh_baseline_calculation_digest": fresh_baseline.calculation_digest,
        "fresh_calculation_digest": fresh.calculation_digest,
        "fresh_baseline_outcome_hash": fresh_baseline.outcome_record_hash,
        "fresh_outcome_hash": fresh.outcome_record_hash,
    }


def test_two_evaluators_share_the_scope_lock_and_late_ingress_cannot_change_the_winner(
    monkeypatch,
):
    monkeypatch.setattr(forward_service_module, "FORWARD_PATH_READ_PAGE_SIZE", 2)
    with _se02c_database("stable_concurrency") as url:
        observed = asyncio.run(_stable_concurrency_scenario(url))

    assert observed["second_evaluator_waited_on_advisory_lock"] is True
    assert observed["late_ingress_result"] == "INSERTED"
    assert observed["late_row_durable"] is True
    assert observed["winner_excluded_late_row"] is True
    assert observed["both_callers_succeeded"] is True
    assert observed["outcome_count"] == 1
    assert observed["distinct_returned_outcome_ids"] == 1
    assert observed["distinct_returned_digests"] == 1
    assert observed["distinct_returned_hashes"] == 1
    assert observed["both_callers_match_durable"] is True
    assert observed["first_calculation_count"] == 1
    assert observed["second_calculation_count"] == 0
    assert observed["revision"] == 1


async def _stable_concurrency_scenario(url: str) -> dict[str, object]:
    initial_frames = (
        (298, 100.9, 101.1, 10),
        (299, 101.9, 102.1, 20),
    )
    async with _sessions(url) as setup_sessions:
        await _capture_forward_opportunity(setup_sessions)
        await _record_frames(setup_sessions, initial_frames)
        scope = await _scope_of(setup_sessions, horizon=ForwardHorizon.M5)
        baseline = await ForwardOutcomeService(setup_sessions).calculate_scope(scope)

    engines = [
        create_async_engine(
            url,
            poolclass=NullPool,
            connect_args={"server_settings": {"application_name": application_name}},
        )
        for application_name in ("se02c-fix02-evaluator-a", "se02c-fix02-evaluator-b")
    ]
    writer_engine = create_async_engine(url, poolclass=NullPool)
    observer_engine = create_async_engine(url, poolclass=NullPool)
    try:
        factories = [async_sessionmaker(engine, expire_on_commit=False) for engine in engines]
        writer_factory = async_sessionmaker(writer_engine, expire_on_commit=False)
        observer_factory = async_sessionmaker(observer_engine, expire_on_commit=False)
        page_one_loaded = asyncio.Event()
        resume = asyncio.Event()
        first_service = _PageOnePausedForwardOutcomeService(
            factories[0],
            horizons=(ForwardHorizon.M5,),
            page_one_loaded=page_one_loaded,
            resume=resume,
        )
        second_service = _CountingForwardOutcomeService(
            factories[1], horizons=(ForwardHorizon.M5,)
        )

        first_task = asyncio.create_task(first_service.evaluate_scope(scope))
        await asyncio.wait_for(page_one_loaded.wait(), timeout=5)
        second_task = asyncio.create_task(second_service.evaluate_scope(scope))
        second_waited = await _wait_for_advisory_wait(
            observer_factory, "se02c-fix02-evaluator-b"
        )

        late_at = scope.due_at
        late_event = _ticker(
            bid=109.0,
            ask=111.0,
            at=late_at,
            source_sequence=99,
        )
        late_observation = build_forward_path_observation(late_event)
        late_ingress_result = await ForwardPathRecorder(writer_factory).record_event(late_event)
        async with writer_factory() as verifier:
            late_row_durable = (
                await verifier.get(EdgeBboObservationRecord, late_observation.observation_id)
                is not None
            )

        resume.set()
        returned = await asyncio.wait_for(
            asyncio.gather(first_task, second_task), timeout=10
        )
        async with factories[0]() as session:
            durable_rows = (
                await session.scalars(
                    select(EdgeForwardOutcomeRecord).where(
                        EdgeForwardOutcomeRecord.opportunity_id == scope.opportunity_id,
                        EdgeForwardOutcomeRecord.evidence_id == scope.evidence_id,
                        EdgeForwardOutcomeRecord.horizon == scope.horizon.value,
                    )
                )
            ).all()
    finally:
        for engine in (*engines, writer_engine, observer_engine):
            await engine.dispose()

    durable = durable_rows[0]
    return {
        "second_evaluator_waited_on_advisory_lock": second_waited,
        "late_ingress_result": late_ingress_result,
        "late_row_durable": late_row_durable,
        "winner_excluded_late_row": (
            returned[0].end_bbo_observation_id == baseline.end_bbo_observation_id
            and returned[0].calculation_digest == baseline.calculation_digest
            and returned[0].outcome_record_hash == baseline.outcome_record_hash
        ),
        "both_callers_succeeded": len(returned) == 2,
        "outcome_count": len(durable_rows),
        "distinct_returned_outcome_ids": len({item.outcome_id for item in returned}),
        "distinct_returned_digests": len({item.calculation_digest for item in returned}),
        "distinct_returned_hashes": len({item.outcome_record_hash for item in returned}),
        "both_callers_match_durable": all(
            item.outcome_id == durable.outcome_id
            and item.calculation_digest == durable.calculation_digest
            and item.outcome_record_hash == durable.outcome_record_hash
            for item in returned
        ),
        "first_calculation_count": first_service.calculation_count,
        "second_calculation_count": second_service.calculation_count,
        "revision": durable.outcome_revision,
    }


async def _wait_for_advisory_wait(factory, application_name: str) -> bool:
    for _ in range(100):
        async with factory() as session:
            waiting = await session.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_stat_activity "
                    "WHERE application_name = :application_name "
                    "AND wait_event_type = 'Lock' AND wait_event = 'advisory'"
                    ")"
                ),
                {"application_name": application_name},
            )
        if waiting:
            return True
        await asyncio.sleep(0.01)
    return False


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
    assert observed["settled_retry_returned_existing"] is True
    assert observed["outcome_count_after_retry"] == 4
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
        # still refuses to re-open the scope, and a forced normal re-evaluation
        # returns the revision-1 row found after the scope lock. It never opens a
        # fresh calculation snapshot and therefore cannot conflict or mint revision 2.
        await ForwardPathRecorder(factory).record_event(
            _ticker(bid=104.0, ask=104.4, at=START + timedelta(seconds=298), source_sequence=7)
        )
        async with factory() as session:
            unsettled = await discover_due_scopes(session, now=EVAL_NOW)
        settled_retry = await service.evaluate_scope(m5_scope)
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
        "settled_retry_returned_existing": (
            settled_retry.outcome_id == retry.outcome_id
            and settled_retry.outcome_record_hash == hash_before
        ),
        "outcome_count_after_retry": after["outcome_count"],
        "hash_unchanged": _by_horizon(after["outcomes"])["5m"].outcome_record_hash == hash_before,
    }


# --- C-16 cross-evidence independence ----------------------------------------------------


def test_two_evidence_revisions_of_one_opportunity_own_disjoint_outcome_scopes():
    with _se02c_database("cross_evidence") as url:
        observed = asyncio.run(_cross_evidence_scenario(url))
    assert observed["appended"] == "INSERTED"
    assert observed["evidence_revisions"] == [1, 2]
    assert observed["revision_two_supersedes_revision_one"] is True
    assert observed["outcome_count"] == 8
    assert observed["distinct_outcome_ids"] == 8
    assert observed["scopes_per_evidence"] == {1: 4, 2: 4}
    assert observed["revision_one_statuses"] == ["COMPLETE"] * 4
    assert set(observed["revision_two_statuses"]) == {"INVALID"}
    assert observed["revision_one_unchanged"] is True
    assert observed["revision_two_due_at"] == observed["expected_revision_two_due_at"]


async def _cross_evidence_scenario(url: str) -> dict[str, object]:
    """Two evidence revisions of one opportunity must never share an outcome scope.

    The accepted SE-02B runtime capture path pins ``evidence_revision = 1``, so a
    revision 2 can only exist through the accepted append-only evidence writer.
    That is exactly what this scenario uses -- no new persistence path, no repo
    change: ``append_evidence_revision`` is the accepted SE-02A writer.
    """

    async with _sessions(url) as sessions:
        facts = await _capture_forward_opportunity(sessions)
        await _record_frames(sessions)
        candidate = next(
            item for item in facts["candidates"] if item.strategy_id == "BREAKOUT_RETEST"
        )
        opportunity = build_opportunity_identity(
            family_id=EdgeFamily.BREAKOUT_RETEST,
            family_version=candidate.strategy_version,
            instrument_id=INSTRUMENT,
            market_type=MarketType.SPOT,
            candidate_id=candidate.candidate_id,
        )
        async with sessions() as session:
            first_revision = await session.scalar(
                select(EdgeOpportunityEvidenceRecord).where(
                    EdgeOpportunityEvidenceRecord.opportunity_id == opportunity.opportunity_id,
                    EdgeOpportunityEvidenceRecord.evidence_revision == 1,
                )
            )
        second = build_evidence_revision(
            opportunity=opportunity,
            evidence_revision=2,
            detected_at=START,
            evidence_at=START + timedelta(seconds=60),
            expires_at=START + timedelta(minutes=20),
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="okx-ws-bbo",
            source_manifest_id="manifest-se02c",
            reference_data_status=ReferenceDataStatus.OK,
            reference_bid=REFERENCE_BID,
            reference_ask=REFERENCE_ASK,
            reference_received_at=START,
            supersedes_evidence_id=first_revision.evidence_id,
            evidence_payload={"capture": {"payload_version": "se02c-cross-evidence-fixture"}},
            feature_snapshot_payload=facts["features"].model_dump(mode="json"),
            created_at=START + timedelta(seconds=60),
        )
        async with sessions() as session, session.begin():
            appended = await append_evidence_revision(session, second)

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        await evaluate_due_outcomes(factory, now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    mine = [
        row
        for row in durable["outcomes"]
        if row.opportunity_id == opportunity.opportunity_id
    ]
    evidence_ids = {
        row.evidence_revision: row.evidence_id
        for row in durable["evidence"]
        if row.opportunity_id == opportunity.opportunity_id
    }
    by_evidence = {
        revision: {
            row.horizon: row for row in mine if row.evidence_id == evidence_id
        }
        for revision, evidence_id in evidence_ids.items()
    }
    return {
        "appended": appended,
        "evidence_revisions": sorted(evidence_ids),
        "revision_two_supersedes_revision_one": (
            second.supersedes_evidence_id == evidence_ids[1]
        ),
        "outcome_count": len(durable["outcomes"]),
        "distinct_outcome_ids": len({row.outcome_id for row in durable["outcomes"]}),
        "scopes_per_evidence": {revision: len(rows) for revision, rows in by_evidence.items()},
        "revision_one_statuses": [row.calculation_status for row in by_evidence[1].values()],
        "revision_two_statuses": [row.calculation_status for row in by_evidence[2].values()],
        "revision_one_unchanged": all(
            row.outcome_revision == 1
            and row.due_at == forward_due_at(START, ForwardHorizon(row.horizon))
            for row in by_evidence[1].values()
        ),
        "revision_two_due_at": sorted(row.due_at for row in by_evidence[2].values()),
        "expected_revision_two_due_at": sorted(
            forward_due_at(START + timedelta(seconds=60), horizon)
            for horizon in ALL_FORWARD_HORIZONS
        ),
    }


# --- SE-02C-FIX-01 · R1: the complete forward path, never a capped prefix -----------------


LONG_PATH_COUNT = 50_001
LONG_PATH_BASE = START + timedelta(seconds=295)


def _long_path_observation(index: int) -> BboObservation:
    """One legal Forward path observation; the extremes live in the last two rows.

    The deepest and the highest excursion are deliberately placed in forward path
    observations ``50_000`` and ``50_001`` -- exactly the rows a 50,000-row read
    ceiling would have dropped -- so a capped loader cannot reproduce this
    outcome: its endpoint would be an earlier row and both excursions would
    collapse to ``0``.
    """

    if index == LONG_PATH_COUNT:
        bid, ask = 109.99, 110.01
    elif index == LONG_PATH_COUNT - 1:
        bid, ask = 89.99, 90.01
    else:
        bid, ask = 99.99, 100.01
    at = LONG_PATH_BASE + timedelta(microseconds=index)
    return build_bbo_observation(
        instrument_id=INSTRUMENT,
        market_type=MarketType.SPOT,
        bid=bid,
        ask=ask,
        available_at=at,
        source_event_time=at,
        received_at=at,
        data_quality=DataQuality.FRESH,
        tradable=True,
        source=PATH_SOURCE,
        created_at=at,
    )


def test_more_than_fifty_thousand_forward_observations_are_used_in_full():
    """R1: a >50,000 observation Forward Path must reach the endpoint and both excursions."""

    with _se02c_database("long_path") as url:
        observed = asyncio.run(_long_path_scenario(url))

    assert observed["forward_path_observation_count"] == LONG_PATH_COUNT
    # 1 durable FIX-01 capture anchor + LONG_PATH_COUNT forward path observations.
    assert observed["durable_bbo_rows"] == LONG_PATH_COUNT + 1
    assert observed["page_size_is_smaller_than_the_path"] is True
    assert observed["status"] == "COMPLETE"
    assert observed["service_status"] == "COMPLETE"
    assert observed["observation_count"] == LONG_PATH_COUNT + 1
    assert observed["eligible_observation_count"] == LONG_PATH_COUNT + 1
    assert observed["path_point_count"] == LONG_PATH_COUNT
    assert observed["no_truncation_flag"] is True
    assert observed["endpoint_is_the_true_latest"] is True
    assert observed["endpoint_available_at"] == observed["expected_endpoint_available_at"]
    assert observed["end_age_seconds"] <= 5.0
    assert observed["mfe"] == pytest.approx(0.10, rel=1e-12)
    assert observed["mae"] == pytest.approx(-0.10, rel=1e-12)
    assert observed["reference_return"] == pytest.approx(0.10, rel=1e-12)
    assert observed["executable_long_return"] == pytest.approx(
        109.99 / REFERENCE_ASK - 1, rel=1e-12
    )
    assert observed["end_bid"] == 109.99
    assert observed["end_ask"] == 110.01
    assert observed["first_extreme_was_outside_the_old_ceiling"] is True


async def _long_path_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        await _capture_forward_opportunity(sessions)
        # The accepted SE-02A/SE-02B writer, used verbatim: these are legal durable
        # forward path observations of the open FORWARD_PAPER window.
        async with sessions() as session, session.begin():
            for index in range(1, LONG_PATH_COUNT + 1):
                await record_bbo_observation(session, _long_path_observation(index))

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        service = ForwardOutcomeService(factory, horizons=(ForwardHorizon.M5,))
        outcomes = await service.evaluate_due_outcomes(now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    stored = next(row for row in durable["outcomes"] if row.horizon == "5m")
    endpoint_row = next(
        row
        for row in durable["observations"]
        if row.observation_id == stored.end_bbo_observation_id
    )
    diagnostics = dict(stored.completeness_diagnostics)
    latest_available_at = LONG_PATH_BASE + timedelta(microseconds=LONG_PATH_COUNT)
    return {
        "forward_path_observation_count": sum(
            1 for row in durable["observations"] if row.available_at > START
        ),
        "durable_bbo_rows": durable["observation_count"],
        "page_size_is_smaller_than_the_path": (
            FORWARD_PATH_READ_PAGE_SIZE < durable["observation_count"]
        ),
        "status": stored.calculation_status,
        "service_status": next(
            item.calculation_status.value
            for item in outcomes
            if item.horizon is ForwardHorizon.M5
        ),
        "observation_count": diagnostics["observation_count"],
        "eligible_observation_count": diagnostics["eligible_observation_count"],
        "path_point_count": diagnostics["path_point_count"],
        "end_age_seconds": diagnostics["end_age_seconds"],
        "no_truncation_flag": (
            "path_truncated" not in diagnostics and "truncated" not in diagnostics
        ),
        "endpoint_is_the_true_latest": endpoint_row.available_at == latest_available_at,
        "endpoint_available_at": endpoint_row.available_at,
        "expected_endpoint_available_at": latest_available_at,
        "mfe": stored.mfe,
        "mae": stored.mae,
        "reference_return": stored.reference_return,
        "executable_long_return": stored.executable_long_return,
        "end_bid": stored.end_bid,
        "end_ask": stored.end_ask,
        # The MAE-driving row sits at index 50_000 of the path: inside the path,
        # outside the 50_000-row prefix the old loader kept.
        "first_extreme_was_outside_the_old_ceiling": (
            LONG_PATH_BASE + timedelta(microseconds=LONG_PATH_COUNT - 1) > START
            and stored.mae is not None
        ),
    }


# --- SE-02C-FIX-01 · R2: authoritative tradability ----------------------------------------


#: Case A / Case B live inside the frozen 5-second endpoint TTL of the 5m horizon.
CASE_A_AT = START + timedelta(seconds=295)
CASE_B_AT = START + timedelta(seconds=296)
CASE_C_AT = START + timedelta(seconds=12)
SUSPENDED_AT = START + timedelta(seconds=295)
CASE_C_BID = 777.0


def test_tradability_is_carried_from_the_instrument_and_unknown_tradability_fails_closed():
    with _se02c_database("tradability") as url:
        observed = asyncio.run(_tradability_scenario(url))

    # Case A -- instrument tradable -> frame tradable -> durable tradable -> eligible.
    assert observed["case_a_normalized_tradable"] is True
    assert observed["case_a_recorded"] == "INSERTED"
    assert observed["case_a_durable_tradable"] is True
    assert observed["case_a_is_the_endpoint"] is True

    # Case B -- instrument non-tradable -> frame False -> durable False -> excluded,
    # even though it is the *later* quote and would otherwise win the endpoint.
    assert observed["case_b_normalized_tradable"] is False
    assert observed["case_b_recorded"] == "INSERTED"
    assert observed["case_b_durable_tradable"] is False
    assert observed["case_b_is_the_endpoint"] is False
    assert observed["excluded_untradable_count"] == 1
    assert observed["complete_end_bid"] == 101.0
    assert observed["complete_mfe"] == pytest.approx(0.012, rel=1e-12)
    assert observed["complete_status"] == "COMPLETE"

    # Case C -- no authoritative tradability fact: nothing is archived, nothing raises.
    assert observed["case_c_recorded"] is None
    assert observed["case_c_builder_raises"] is True
    assert observed["case_c_rows"] == 0

    # A suspended instrument's only forward path quote can never produce COMPLETE,
    # executable return or cost-adjusted return.
    assert observed["suspended_recorded"] == "INSERTED"
    assert observed["suspended_durable_tradable"] is False
    assert observed["suspended_status"] == "INSUFFICIENT_DATA"
    assert observed["suspended_reason"] == "ENDPOINT_MISSING"
    assert observed["suspended_metrics_are_null"] is True
    assert observed["suspended_end_is_not_bound"] is True
    assert observed["suspended_complete_rows"] == 0
    assert observed["suspended_excluded_untradable_count"] == 1


async def _tradability_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        live_facts = await _capture_forward_opportunity(sessions)
        suspended_facts = await _capture_forward_opportunity(
            sessions, event_id="evt-se02c-eth", instrument_id=SECOND_INSTRUMENT
        )
        recorder = ForwardPathRecorder(sessions)

        # The real G1 authority: ``Instrument.tradable`` is the value the
        # normalizer resolved from OKX ``state``, and it is what the frame carries.
        live_instrument = _instrument(tradable=True)
        suspended_instrument = _instrument(instrument_id=SECOND_INSTRUMENT, tradable=False)

        case_a_normalized = _normalize(tradable=live_instrument.tradable)
        case_b_normalized = _normalize(tradable=suspended_instrument.tradable)

        case_a_recorded = await recorder.record_event(
            _ticker(
                bid=101.0,
                ask=101.4,
                at=CASE_A_AT,
                tradable=case_a_normalized.tradable,
            )
        )
        case_b_recorded = await recorder.record_event(
            _ticker(
                bid=500.0,
                ask=500.4,
                at=CASE_B_AT,
                tradable=case_b_normalized.tradable,
            )
        )
        case_c_frame = _ticker(
            bid=CASE_C_BID, ask=CASE_C_BID + 0.4, at=CASE_C_AT, tradable=None
        )
        case_c_recorded = await recorder.record_event(case_c_frame)
        try:
            build_forward_path_observation(case_c_frame)
            case_c_builder_raises = False
        except ForwardPathTradabilityUnknown:
            case_c_builder_raises = True

        suspended_recorded = await recorder.record_event(
            _ticker(
                bid=200.0,
                ask=200.4,
                at=SUSPENDED_AT,
                instrument_id=SECOND_INSTRUMENT,
                tradable=suspended_instrument.tradable,
            )
        )

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        service = ForwardOutcomeService(factory, horizons=(ForwardHorizon.M5,))
        await service.evaluate_due_outcomes(now=EVAL_NOW)
        durable = await _durable(factory)
    finally:
        await engine.dispose()

    complete = _by_horizon(durable["outcomes"], _opportunity_id(live_facts))["5m"]
    suspended = _by_horizon(durable["outcomes"], _opportunity_id(suspended_facts))["5m"]
    rows = durable["observations"]

    def _row(at: datetime, instrument_id: str = INSTRUMENT):
        """The one durable row of an exact (instrument, available_at) pair.

        ``CASE_A_AT`` and ``SUSPENDED_AT`` intentionally share an instant, so the
        instrument must be part of the lookup rather than assumed.
        """

        return next(
            row
            for row in rows
            if row.available_at == at and row.instrument_id == instrument_id
        )

    case_b_rows = [row for row in rows if row.available_at == CASE_B_AT]
    suspended_rows = [
        row for row in rows if row.instrument_id == SECOND_INSTRUMENT and row.bid == 200.0
    ]
    return {
        "case_a_normalized_tradable": case_a_normalized.tradable,
        "case_a_recorded": case_a_recorded,
        "case_a_durable_tradable": _row(CASE_A_AT).tradable,
        "case_a_is_the_endpoint": (
            complete.end_bbo_observation_id == _row(CASE_A_AT).observation_id
        ),
        "case_b_normalized_tradable": case_b_normalized.tradable,
        "case_b_recorded": case_b_recorded,
        "case_b_durable_tradable": next(
            row.tradable for row in case_b_rows
        ) if case_b_rows else None,
        "case_b_is_the_endpoint": (
            complete.end_bbo_observation_id == _row(CASE_B_AT).observation_id
        ),
        "excluded_untradable_count": complete.completeness_diagnostics[
            "excluded_untradable_count"
        ],
        "complete_status": complete.calculation_status,
        "complete_end_bid": complete.end_bid,
        "complete_mfe": complete.mfe,
        "case_c_recorded": case_c_recorded,
        "case_c_builder_raises": case_c_builder_raises,
        "case_c_rows": sum(1 for row in rows if row.bid == CASE_C_BID),
        "suspended_recorded": suspended_recorded,
        "suspended_durable_tradable": next(
            (row.tradable for row in suspended_rows), None
        ),
        "suspended_status": suspended.calculation_status,
        "suspended_reason": suspended.completeness_diagnostics["reason"],
        "suspended_metrics_are_null": all(
            getattr(suspended, field) is None
            for field in (
                "reference_return",
                "executable_long_return",
                "cost_adjusted_forward_return",
                "mfe",
                "mae",
                "end_bid",
                "end_ask",
            )
        ),
        "suspended_end_is_not_bound": suspended.end_bbo_observation_id is None,
        "suspended_complete_rows": sum(
            1
            for row in durable["outcomes"]
            if row.opportunity_id == suspended.opportunity_id
            and row.calculation_status == "COMPLETE"
        ),
        "suspended_excluded_untradable_count": suspended.completeness_diagnostics[
            "excluded_untradable_count"
        ],
    }


def _normalize(*, tradable: bool) -> NormalizedBookTicker:
    """One normalized OKX frame through the real market-data normalizer."""

    return normalize_book_ticker(
        {
            "ts": str(int(START.timestamp() * 1000)),
            "bids": [["100.0", "1"]],
            "asks": [["101.0", "1"]],
        },
        _instrument(tradable=tradable),
    )
