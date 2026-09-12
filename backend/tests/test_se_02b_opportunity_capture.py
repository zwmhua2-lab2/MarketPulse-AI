"""SE-02B opportunity capture acceptance against real disposable PostgreSQL.

Proves the two SE-02B capture guarantees:

* a qualifying ``BREAKOUT -> BREAKOUT_RETEST BULLISH -> APPLIED -> SETUP``
  transition produces exactly one immutable Edge evidence revision, with a
  deterministic opportunity id and evidence id/hash, persisted together with the
  durable G2 facts in one PostgreSQL transaction;
* every other G2 outcome stays evidence-free, and an Edge integrity failure
  cannot commit G2 truth on its own.

No forward-outcome calculator, no MFE/MAE, no expectancy and no family
aggregation is exercised here: those belong to SE-02C / SE-02D.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import marketpulse.g2.repository as g2_repository_module
from alembic import command
from alembic.config import Config
from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    DerivedObservationRecord,
    EdgeBboObservationRecord,
    EdgeOpportunityCaptureAnchorOrphanRecord,
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
    MarketEventRecord,
    SignalTimelineRecord,
    StateTransitionRecord,
    StrategyCandidateRecord,
    SymbolStateStore,
)
from marketpulse.edge.capture import (
    DEFAULT_REFERENCE_MAX_AGE,
    EdgeCaptureContext,
    ForwardAdmissionAuthority,
    ReferenceQuote,
    build_capture_anchor,
    build_opportunity_evidence,
    capture_opportunity,
    qualifies,
)
from marketpulse.edge.identity import evidence_id as derive_evidence_id
from marketpulse.edge.models import (
    EVIDENCE_CONTRACT_VERSION,
    EdgeFamily,
    EvidenceSource,
    build_opportunity_identity,
)
from marketpulse.edge.repository import (
    IDEMPOTENT,
    INSERTED,
    EdgeCaptureAnchorConflict,
    EdgeEvidenceConflict,
    append_capture_anchor,
)
from marketpulse.g2.models import (
    DirectionBias,
    EventType,
    FeatureSnapshot,
    LifecycleAction,
    MarketEvent,
    MarketStructure,
    SignalTimelineEvent,
    StateApplyResult,
    StateTransition,
    StrategyCandidate,
    SymbolState,
    SymbolStateRecord,
    Zone,
    deterministic_id,
)
from marketpulse.g2.repository import (
    CaptureAdmissionOverloaded,
    CaptureAdmissionRejected,
    CaptureAnchorOrphan,
    PostgresG2Repository,
)
from marketpulse.g2.runtime import EventRuntime
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.market_data.models import DataQuality, MarketType
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

START = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
INSTRUMENT = "BTC-USDT"
STRATEGY_VERSION = StrategyEngine.version
PRIMARY_URL = Settings().database_url
BACKEND = Path(__file__).resolve().parents[1]


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
def _capture_database(label: str):
    name = f"marketpulse_se02b_{label}_{uuid4().hex[:12]}"
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


async def _g2_counts(session) -> dict[str, int]:
    return {
        "events": await _count(session, MarketEventRecord),
        "timeline": await _count(session, SignalTimelineRecord),
        "transitions": await _count(session, StateTransitionRecord),
        "candidates": await _count(session, StrategyCandidateRecord),
        "observations": await _count(session, DerivedObservationRecord),
        "states": await _count(session, SymbolStateStore),
    }


# --- fixture facts ----------------------------------------------------------------------


def _features(
    *,
    at: datetime = START,
    instrument_id: str = INSTRUMENT,
    price: float = 100.5,
    retest: bool = True,
) -> FeatureSnapshot:
    structure = MarketStructure(
        recent_swing_high=101.0,
        recent_swing_low=95.0,
        breakout_level=100.0,
        retest_area=(
            Zone(lower=99.0, upper=100.0, kind="retest", observed_at=at) if retest else None
        ),
    )
    return FeatureSnapshot(
        instrument_id=instrument_id,
        symbol=instrument_id,
        market_type=MarketType.SPOT,
        event_time=at,
        current_price=price,
        short_return=0.02,
        buy_sell_imbalance=0.7,
        spread=0.5,
        structure=structure,
    )


def _event(
    *,
    event_id: str = "evt-breakout-1",
    at: datetime = START,
    version: int = 0,
    kind: EventType = EventType.BREAKOUT,
    strength: float = 0.9,
    instrument_id: str = INSTRUMENT,
    received_at: datetime | None = None,
) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        symbol=instrument_id,
        instrument_id=instrument_id,
        market_type=MarketType.SPOT,
        event_type=kind,
        event_time=at,
        received_time=received_at or at,
        source="fixture",
        strength=strength,
        priority=80,
        state_version=version,
        config_version="g2-v1",
        payload={"current_price": 100.5},
    )


def _state(
    *,
    at: datetime = START,
    version: int = 1,
    state: SymbolState = SymbolState.SETUP,
    expires: bool = True,
    instrument_id: str = INSTRUMENT,
) -> SymbolStateRecord:
    return SymbolStateRecord(
        instrument_id=instrument_id,
        symbol=instrument_id,
        state=state,
        state_version=version,
        last_event_time=at,
        watch_expires_at=(at + timedelta(minutes=20)) if expires else None,
    )


def _transition(
    *,
    event: MarketEvent,
    state: SymbolStateRecord,
    result: StateApplyResult = StateApplyResult.APPLIED,
    to_state: SymbolState = SymbolState.SETUP,
) -> StateTransition:
    return StateTransition(
        transition_id=deterministic_id("st", event.event_id, state.state_version, result),
        instrument_id=event.instrument_id,
        symbol=event.symbol,
        from_state=SymbolState.WATCHING,
        to_state=to_state,
        event_id=event.event_id,
        event_time=event.event_time,
        state_version=state.state_version,
        result=result,
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


def _candidates(
    features: FeatureSnapshot,
    event: MarketEvent,
    state_version: int,
    *,
    created_at: datetime | None = None,
) -> list[StrategyCandidate]:
    """Candidates from the real accepted G2 strategy engine, never hand-rolled.

    ``created_at`` defaults to the event receipt time, which is what the accepted
    runtime does. A test may stage a strictly later candidate time to separate the
    event's own receipt from the moment the candidate became knowable.
    """

    return StrategyEngine(clock=ReplayClock(created_at or event.received_time)).candidates(
        features, event, state_version
    )


def _breakout_candidate(candidates: list[StrategyCandidate]) -> StrategyCandidate:
    return next(item for item in candidates if item.strategy_id == "BREAKOUT_RETEST")


def _quote(
    *,
    bid: float = 99.5,
    ask: float = 100.5,
    at: datetime = START,
    tradable: bool = True,
    instrument_id: str = INSTRUMENT,
    market_type: MarketType = MarketType.SPOT,
    data_quality: DataQuality = DataQuality.FRESH,
    source_event_time: datetime | None = START,
    source: str | None = "fixture-bbo",
    source_sequence: int | None = 1,
) -> ReferenceQuote:
    return ReferenceQuote(
        instrument_id=instrument_id,
        market_type=market_type,
        bid=bid,
        ask=ask,
        received_at=at,
        data_quality=data_quality,
        tradable=tradable,
        source_event_time=source_event_time,
        source=source,
        source_sequence=source_sequence,
    )


def _context(
    *,
    source_type: EvidenceSource = EvidenceSource.FORWARD_PAPER,
    max_age: timedelta = DEFAULT_REFERENCE_MAX_AGE,
) -> EdgeCaptureContext:
    """The reference quote is deliberately *not* part of the capture context.

    A context lives for a whole run while a quote is only valid for the capture it
    was observed at, so each persist supplies its own quote (P0-1).
    """

    return EdgeCaptureContext(
        source_type=source_type,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-se02b",
        reference_max_age=max_age,
    )


def _live_authority(*, session_id: str = "fixture-live-forward-session") -> ForwardAdmissionAuthority:
    """A deterministic fixture-only live ingress capability for one process."""

    return ForwardAdmissionAuthority(
        session_id=session_id,
        secret=b"se-arch-fix-01-fixture-live-ingress-secret",
    )


def _facts(
    *,
    event_id: str = "evt-breakout-1",
    at: datetime = START,
    state_version: int = 1,
    kind: EventType = EventType.BREAKOUT,
    strength: float = 0.9,
    instrument_id: str = INSTRUMENT,
    received_at: datetime | None = None,
    created_at: datetime | None = None,
) -> dict[str, object]:
    event = _event(
        event_id=event_id,
        at=at,
        kind=kind,
        strength=strength,
        instrument_id=instrument_id,
        received_at=received_at,
    )
    features = _features(at=at, instrument_id=instrument_id)
    state = _state(at=at, version=state_version, instrument_id=instrument_id)
    transition = _transition(event=event, state=state)
    timeline = _timeline(event=event, state=state)
    candidates = _candidates(
        features, event, state.state_version, created_at=created_at
    )
    return {
        "event": event,
        "features": features,
        "state": state,
        "transition": transition,
        "timeline": timeline,
        "candidates": candidates,
    }


def _opportunity_for(candidate: StrategyCandidate):
    return build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=candidate.strategy_version,
        instrument_id=candidate.instrument_id,
        market_type=MarketType.SPOT,
        candidate_id=candidate.candidate_id,
    )


async def _persist(
    sessions,
    facts,
    context: EdgeCaptureContext | None,
    *,
    quote: ReferenceQuote | None = None,
    quotes_by_instrument: dict[str, ReferenceQuote] | None = None,
):
    """Persist one G2 event through the real repository, with a per-capture quote.

    The quote reaches the capture through the repository's bounded accessor, which
    is how production supplies it: one repository instance serves many events, so
    the quote can never be a constructor constant (P0-1).

    A single ``quote`` is handed to *this* event's instrument, which is what lets a
    test stage a quote that does not actually belong to the instrument being
    captured. ``quotes_by_instrument`` states the mapping explicitly instead.
    """

    if quotes_by_instrument is None and quote is not None:
        quotes_by_instrument = {facts["event"].instrument_id: quote}
    authority = _live_authority()
    repository = PostgresG2Repository(
        sessions,
        capture=context,
        reference_quote_for=(
            None
            if quotes_by_instrument is None
            else lambda instrument_id: quotes_by_instrument.get(instrument_id)
        ),
        forward_admission_authority=authority,
        forward_admission_proof_for=authority.admit_live_input,
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
            instrument_id=facts["event"].instrument_id,
            symbol=facts["event"].symbol,
        ),
    )


# --- A. capture positive ----------------------------------------------------------------


def test_qualifying_setup_captures_exactly_one_deterministic_evidence_revision():
    with _capture_database("capture") as url:
        observed = asyncio.run(_qualifying_capture_scenario(url))

    assert observed["persisted"] is True
    assert observed["qualifying_candidate"] is not None
    assert observed["g2"] == {
        "events": 1,
        "timeline": 1,
        "transitions": 1,
        "candidates": 4,
        "observations": 1,
        "states": 1,
    }
    assert observed["evidence_rows"] == 1
    assert observed["row"]["opportunity_id"] == observed["expected_opportunity_id"]
    assert observed["row"]["evidence_id"] == observed["expected_evidence_id"]
    assert observed["row"]["evidence_hash"] == observed["rebuilt_hash"]
    assert observed["row"]["evidence_revision"] == 1
    assert observed["row"]["supersedes_evidence_id"] is None
    assert observed["row"]["family_id"] == "BREAKOUT_RETEST"
    assert observed["row"]["family_version"] == STRATEGY_VERSION
    assert observed["row"]["reference_data_status"] == "OK"
    assert observed["row"]["reference_bid"] == 99.5
    assert observed["row"]["reference_ask"] == 100.5
    assert observed["row"]["reference_received_at"] == START
    assert observed["row"]["source_type"] == "FORWARD_PAPER"
    assert observed["row"]["source_identity"] == "okx-ws-bbo"
    assert observed["row"]["source_manifest_id"] == "manifest-se02b"


async def _qualifying_capture_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        context = _context()
        persisted = await _persist(sessions, facts, context, quote=_quote())
        candidate = _breakout_candidate(facts["candidates"])
        opportunity = _opportunity_for(candidate)
        revisions = [
            build_opportunity_evidence(
                event=facts["event"],
                timeline=facts["timeline"],
                state=facts["state"],
                transition=facts["transition"],
                candidate=candidate,
                observation=facts["features"],
                context=context,
                reference_quote=_quote(),
            )
            for _ in range(2)
        ]
        async with sessions() as session:
            row = (
                await session.scalars(select(EdgeOpportunityEvidenceRecord))
            ).one()
            g2 = await _g2_counts(session)
            rows = await _count(session, EdgeOpportunityEvidenceRecord)
        return {
            "persisted": persisted,
            "qualifying_candidate": qualifies(
                event=facts["event"],
                timeline=facts["timeline"],
                state=facts["state"],
                transition=facts["transition"],
                candidates=facts["candidates"],
                observation=facts["features"],
            ),
            "g2": g2,
            "evidence_rows": rows,
            "expected_opportunity_id": opportunity.opportunity_id,
            "expected_evidence_id": derive_evidence_id(
                opportunity_id=opportunity.opportunity_id,
                evidence_revision=1,
                evidence_contract_version=EVIDENCE_CONTRACT_VERSION,
            ),
            "rebuilt_hash": revisions[0].evidence_hash,
            "deterministic": revisions[0].evidence_id == revisions[1].evidence_id
            and revisions[0].evidence_hash == revisions[1].evidence_hash,
            "row": {
                column: getattr(row, column)
                for column in (
                    "evidence_id",
                    "opportunity_id",
                    "family_id",
                    "family_version",
                    "instrument_id",
                    "market_type",
                    "evidence_revision",
                    "evidence_contract_version",
                    "evidence_hash",
                    "supersedes_evidence_id",
                    "reference_data_status",
                    "reference_bid",
                    "reference_ask",
                    "reference_received_at",
                    "source_type",
                    "source_identity",
                    "source_manifest_id",
                )
            },
        }


def test_rebuilding_the_same_facts_twice_is_deterministic():
    with _capture_database("determinism") as url:
        deterministic = asyncio.run(_determinism_scenario(url))
    assert deterministic is True


async def _determinism_scenario(url: str) -> bool:
    async with _sessions(url) as sessions:
        facts = _facts()
        context = _context()
        await _persist(sessions, facts, context, quote=_quote())
        candidate = _breakout_candidate(facts["candidates"])
        first = build_opportunity_evidence(
            event=facts["event"],
            timeline=facts["timeline"],
            state=facts["state"],
            transition=facts["transition"],
            candidate=candidate,
            observation=facts["features"],
            context=context,
            reference_quote=_quote(),
        )
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
        return (
            row.opportunity_id == first.opportunity_id
            and row.evidence_id == first.evidence_id
            and row.evidence_hash == first.evidence_hash
            and row.feature_snapshot_hash == first.feature_snapshot_hash
        )


def test_legacy_g2_persistence_is_unchanged_when_capture_is_not_configured():
    with _capture_database("legacy") as url:
        result = asyncio.run(_legacy_scenario(url))
    assert result["persisted"] is True
    assert result["evidence_rows"] == 0
    assert result["g2"]["events"] == 1


async def _legacy_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        persisted = await _persist(sessions, facts, None)
        async with sessions() as session:
            return {
                "persisted": persisted,
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
                "g2": await _g2_counts(session),
            }


# --- B. negative admission matrix -------------------------------------------------------


def _mutations(event_id: str = "evt-breakout-1") -> dict[str, dict[str, object]]:
    base = _facts(event_id=event_id)
    candidate = _breakout_candidate(base["candidates"])

    def replace_candidate(**updates):
        others = [item for item in base["candidates"] if item.candidate_id != candidate.candidate_id]
        return [*others, candidate.model_copy(update=updates)]

    return {
        "non_applicable_candidate": {"candidates": replace_candidate(applicable=False)},
        "wrong_family": {
            "candidates": [
                item
                for item in base["candidates"]
                if item.strategy_id != "BREAKOUT_RETEST" and item.strategy_id == "TREND_PULLBACK"
            ]
        },
        "wrong_direction": {
            "candidates": replace_candidate(direction_bias=DirectionBias.BEARISH)
        },
        "neutral_direction": {
            "candidates": replace_candidate(direction_bias=DirectionBias.NEUTRAL)
        },
        "wrong_event_type": {
            "event": base["event"].model_copy(update={"event_type": EventType.VOLUME_ANOMALY})
        },
        "detected_only": {
            "state": base["state"].model_copy(update={"state": SymbolState.DETECTED}),
            "transition": base["transition"].model_copy(
                update={"to_state": SymbolState.DETECTED}
            ),
        },
        "watching_only": {
            "state": base["state"].model_copy(update={"state": SymbolState.WATCHING}),
            "transition": base["transition"].model_copy(
                update={"to_state": SymbolState.WATCHING}
            ),
        },
        "no_change_transition": {
            "transition": base["transition"].model_copy(
                update={"result": StateApplyResult.NO_CHANGE}
            )
        },
        "rejected_transition": {
            "transition": base["transition"].model_copy(
                update={"result": StateApplyResult.REJECT_STALE_OPERATION}
            )
        },
        "late_event_rejection": {
            "transition": base["transition"].model_copy(
                update={"result": StateApplyResult.REJECT_LATE_EVENT}
            )
        },
        "setup_without_expiry": {
            "state": base["state"].model_copy(update={"watch_expires_at": None})
        },
        "disagreeing_candidate_event": {"candidates": replace_candidate(event_id="other-event")},
        "disagreeing_candidate_version": {"candidates": replace_candidate(state_version=99)},
        # P1 cross-fact consistency: the durable facts must describe the *same*
        # symbol / signal / config as the event they were derived from. G2 still
        # persists each of these, but none may be admitted as this opportunity's
        # evidence.
        "candidate_symbol_mismatch": {
            "candidates": replace_candidate(symbol="OTHER-SYMBOL")
        },
        "timeline_symbol_mismatch": {
            "timeline": base["timeline"].model_copy(update={"symbol": "OTHER-SYMBOL"})
        },
        "timeline_config_version_mismatch": {
            "timeline": base["timeline"].model_copy(update={"config_version": "g2-v9"})
        },
        "timeline_signal_type_mismatch": {
            "timeline": base["timeline"].model_copy(
                update={"signal_type": EventType.VOLUME_ANOMALY}
            )
        },
        "state_symbol_mismatch": {
            "state": base["state"].model_copy(update={"symbol": "OTHER-SYMBOL"})
        },
    }


def _mutation_names() -> list[str]:
    return sorted(_mutations())


def test_negative_admission_matrix_writes_no_evidence_at_all():
    mutations = _mutation_names()
    with _capture_database("matrix") as url:
        observed = asyncio.run(_negative_scenario(url, mutations))

    # Every non-qualifying outcome persisted its G2 fact but produced no sample.
    assert observed["persisted"] == {name: True for name in mutations}
    assert observed["evidence_rows"] == {name: 0 for name in mutations}
    assert observed["g2"]["events"] == len(mutations)
    assert observed["g2"]["timeline"] == len(mutations)
    assert observed["g2"]["transitions"] == len(mutations)
    assert observed["g2"]["observations"] == len(mutations)
    # Candidate admission is not the subject of this test, so compare against the
    # candidate count the mutations actually supplied rather than a hard-coded 4.
    assert observed["g2"]["candidates"] == observed["expected_candidates"]
    # Every non-qualifying outcome left the durable G2 facts in place (it is only
    # *evidence* that must not appear). One instrument therefore means one
    # symbol-state row, rewritten by each mutation.
    assert observed["g2"]["states"] == 1
    assert observed["total_evidence_rows"] == 0


async def _negative_scenario(url: str, mutations: list[str]) -> dict[str, object]:
    async with _sessions(url) as sessions:
        persisted: dict[str, object] = {}
        evidence_rows: dict[str, int] = {}
        expected_candidates = 0
        for name in mutations:
            facts = dict(_facts(event_id=f"evt-{name}"))
            facts.update(_mutations(event_id=f"evt-{name}")[name])
            expected_candidates += len(facts["candidates"])
            persisted[name] = await _persist(
                sessions, facts, _context(), quote=_quote()
            )
            async with sessions() as session:
                evidence_rows[name] = await _count(session, EdgeOpportunityEvidenceRecord)
        async with sessions() as session:
            return {
                "persisted": persisted,
                "evidence_rows": evidence_rows,
                "expected_candidates": expected_candidates,
                "g2": await _g2_counts(session),
                "total_evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
            }


# --- C. duplicate / idempotency ---------------------------------------------------------


def test_duplicate_market_event_replay_does_not_inflate_the_sample_count():
    with _capture_database("duplicate") as url:
        observed = asyncio.run(_duplicate_scenario(url))
    assert observed["first"] is True
    assert observed["second"] is False
    assert observed["evidence_rows"] == 1
    assert observed["g2"]["events"] == 1


async def _duplicate_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        context = _context()
        first = await _persist(sessions, facts, context, quote=_quote())
        second = await _persist(sessions, facts, context, quote=_quote())
        async with sessions() as session:
            return {
                "first": first,
                "second": second,
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
                "g2": await _g2_counts(session),
            }


def test_same_revision_same_hash_is_idempotent_and_a_changed_hash_fails_closed():
    with _capture_database("idempotent") as url:
        observed = asyncio.run(_idempotency_scenario(url))
    assert observed["statuses"] == [INSERTED, IDEMPOTENT]
    assert observed["conflict"] == "EdgeEvidenceConflict"
    assert observed["evidence_rows"] == 1
    assert observed["row_reference_status"] == "OK"


async def _idempotency_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        statuses = []
        for _ in range(2):
            async with sessions() as session, session.begin():
                statuses.append(
                    await capture_opportunity(
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
                )
        conflict = None
        try:
            async with sessions() as session, session.begin():
                # Same logical opportunity and revision, different immutable content
                # (the reference quote is now missing, so the evidence hash differs).
                await capture_opportunity(
                    session,
                    event=facts["event"],
                    timeline=facts["timeline"],
                    state=facts["state"],
                    transition=facts["transition"],
                    candidates=facts["candidates"],
                    observation=facts["features"],
                    context=_context(),
                    reference_quote=None,
                )
        except EdgeEvidenceConflict:
            conflict = "EdgeEvidenceConflict"
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            return {
                "statuses": statuses,
                "conflict": conflict,
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
                "row_reference_status": row.reference_data_status,
            }


# --- D. reference data cannot decide whether an opportunity exists ----------------------


def _reference_cases() -> dict[str, tuple[object, str]]:
    """Every adverse reference state the caller can supply, plus the usable one.

    ``evidence_at`` is the qualifying candidate's ``created_at`` (``START`` here),
    so a quote received at ``START + 1s`` is *future* data relative to this
    opportunity and must be refused rather than treated as fresh.
    """

    return {
        "usable": (_quote(), "OK"),
        "missing": (None, "REFERENCE_MISSING"),
        "future": (_quote(at=START + timedelta(seconds=1)), "REFERENCE_STALE"),
        "stale": (_quote(at=START - timedelta(minutes=2)), "REFERENCE_STALE"),
        "data_quality_stale": (
            _quote(data_quality=DataQuality.STALE),
            "REFERENCE_STALE",
        ),
        "data_quality_unavailable": (
            _quote(data_quality=DataQuality.UNAVAILABLE),
            "REFERENCE_STALE",
        ),
        "wrong_instrument": (_quote(instrument_id="ETH-USDT"), "REFERENCE_STALE"),
        "wrong_market_type": (_quote(market_type=MarketType.SWAP), "REFERENCE_STALE"),
        "untradable": (_quote(tradable=False), "REFERENCE_STALE"),
        "crossed": (_quote(bid=101.0, ask=100.0), "REFERENCE_STALE"),
        "non_positive": (_quote(bid=0.0, ask=100.0), "REFERENCE_STALE"),
        "non_finite": (_quote(bid=float("nan"), ask=100.0), "REFERENCE_STALE"),
    }


def test_reference_availability_never_blocks_capture():
    labels = sorted(_reference_cases())
    with _capture_database("bbo") as url:
        observed = asyncio.run(_reference_scenario(url, labels))

    assert observed["row_count"] == len(labels)
    assert observed["cases"] == {
        label: {
            "present": True,
            "status": _reference_cases()[label][1],
            "bid": None if _reference_cases()[label][1] != "OK" else 99.5,
            "ask": None if _reference_cases()[label][1] != "OK" else 100.5,
            "received_at": None if _reference_cases()[label][1] != "OK" else START,
        }
        for label in labels
    }


async def _reference_scenario(url: str, labels: list[str]) -> dict[str, object]:
    cases = _reference_cases()
    candidate_by_label: dict[str, str] = {}
    async with _sessions(url) as sessions:
        for label in labels:
            quote, _ = cases[label]
            facts = _facts(event_id=f"evt-{label}")
            candidate_by_label[label] = _breakout_candidate(facts["candidates"]).candidate_id
            await _persist(sessions, facts, _context(), quote=quote)
        async with sessions() as session:
            rows = list((await session.scalars(select(EdgeOpportunityEvidenceRecord))).all())
    rows_by_candidate = {row.candidate_id: row for row in rows}
    return {
        "row_count": len(rows),
        "cases": {
            label: {
                "present": candidate_id in rows_by_candidate,
                "status": (
                    None
                    if candidate_id not in rows_by_candidate
                    else rows_by_candidate[candidate_id].reference_data_status
                ),
                "bid": (
                    None
                    if candidate_id not in rows_by_candidate
                    else rows_by_candidate[candidate_id].reference_bid
                ),
                "ask": (
                    None
                    if candidate_id not in rows_by_candidate
                    else rows_by_candidate[candidate_id].reference_ask
                ),
                "received_at": (
                    None
                    if candidate_id not in rows_by_candidate
                    else rows_by_candidate[candidate_id].reference_received_at
                ),
            }
            for label, candidate_id in candidate_by_label.items()
        },
    }


# --- E. atomic rollback -----------------------------------------------------------------


def test_edge_integrity_conflict_rolls_back_every_g2_fact():
    with _capture_database("rollback1") as url:
        observed = asyncio.run(_conflict_rollback_scenario(url))
    assert observed["raised"] == "EdgeEvidenceConflict"
    assert observed["g2"] == {
        "events": 0,
        "timeline": 0,
        "transitions": 0,
        "candidates": 0,
        "observations": 0,
        "states": 0,
    }
    assert observed["evidence_rows"] == 1  # only the deliberately pre-staged row
    assert observed["staged_opportunity_id"] == observed["expected_opportunity_id"]


async def _conflict_rollback_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        candidate = _breakout_candidate(facts["candidates"])
        opportunity = _opportunity_for(candidate)
        async with sessions() as session, session.begin():
            session.add(
                EdgeOpportunityEvidenceRecord(
                    evidence_id="f" * 64,
                    opportunity_id=opportunity.opportunity_id,
                    candidate_id=candidate.candidate_id,
                    family_id="BREAKOUT_RETEST",
                    family_version=STRATEGY_VERSION,
                    instrument_id=INSTRUMENT,
                    market_type="SPOT",
                    evidence_revision=1,
                    evidence_contract_version=EVIDENCE_CONTRACT_VERSION,
                    evidence_hash="0" * 64,
                    feature_snapshot_hash="1" * 64,
                    feature_snapshot_hash_version="se02-feature-snapshot-hash-v1",
                    supersedes_evidence_id=None,
                    detected_at=START,
                    evidence_at=START,
                    expires_at=START,
                    source_type="FORWARD_PAPER",
                    source_identity="pre-staged",
                    source_manifest_id="pre-staged",
                    reference_bid=None,
                    reference_ask=None,
                    reference_received_at=None,
                    reference_data_status="REFERENCE_MISSING",
                    evidence_payload={},
                    feature_snapshot_payload={},
                    created_at=START,
                )
            )
        raised = None
        try:
            await _persist(sessions, facts, _context(), quote=_quote())
        except EdgeEvidenceConflict:
            raised = "EdgeEvidenceConflict"
        async with sessions() as session:
            return {
                "raised": raised,
                "g2": await _g2_counts(session),
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
                "staged_opportunity_id": opportunity.opportunity_id,
                "expected_opportunity_id": _opportunity_for(candidate).opportunity_id,
            }


class _InjectedEdgeFailure(RuntimeError):
    """Test-only fault raised strictly after the evidence row has been staged."""


def test_failure_after_evidence_is_staged_leaves_no_evidence_behind(monkeypatch):
    with _capture_database("rollback2") as url:
        observed = asyncio.run(_staged_failure_scenario(url, monkeypatch))
    assert observed["raised"] == "_InjectedEdgeFailure"
    assert observed["capture_status"] == INSERTED
    assert observed["g2"] == {
        "events": 0,
        "timeline": 0,
        "transitions": 0,
        "candidates": 0,
        "observations": 0,
        "states": 0,
    }
    assert observed["evidence_rows"] == 0


async def _staged_failure_scenario(url: str, monkeypatch) -> dict[str, object]:
    from marketpulse.g2 import repository as g2_repository

    real_capture = g2_repository.capture_opportunity
    captured: list[object] = []

    async def capture_then_fail(session, **kwargs):
        result = await real_capture(session, **kwargs)
        captured.append(result)
        raise _InjectedEdgeFailure("injected failure after evidence staged")

    monkeypatch.setattr(g2_repository, "capture_opportunity", capture_then_fail)
    async with _sessions(url) as sessions:
        facts = _facts()
        raised = None
        try:
            await _persist(sessions, facts, _context(), quote=_quote())
        except _InjectedEdgeFailure:
            raised = "_InjectedEdgeFailure"
        async with sessions() as session:
            return {
                "raised": raised,
                "capture_status": captured[0] if captured else None,
                "g2": await _g2_counts(session),
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
            }


# --- F. immutable reconstruction --------------------------------------------------------


def test_stored_evidence_reconstructs_the_frozen_setup_without_runtime_state():
    with _capture_database("reconstruct") as url:
        observed = asyncio.run(_reconstruction_scenario(url))
    assert observed["event"] is True
    assert observed["transition"] is True
    assert observed["timeline"] is True
    assert observed["state"] is True
    assert observed["candidate"] is True
    assert observed["feature_snapshot"] is True
    assert observed["setup_expires_at"] == (START + timedelta(minutes=20)).isoformat()
    assert observed["versions"] == {
        "strategy_version": STRATEGY_VERSION,
        "state_version": 1,
        "config_version": "g2-v1",
        "transition_state_version": 1,
        "timeline_state_version": 1,
    }
    assert observed["provenance"]["source_identity"] == "okx-ws-bbo"
    assert observed["reference_status"] == "OK"
    assert observed["supplied_quote"] == {
        "instrument_id": INSTRUMENT,
        "market_type": "SPOT",
        "bid": 99.5,
        "ask": 100.5,
        "received_at": START.isoformat(),
        "data_quality": "FRESH",
        "tradable": True,
        "source_event_time": START.isoformat(),
        "source": "fixture-bbo",
        "source_sequence": 1,
    }
    assert observed["accepted_reference"] == {
        "bid": 99.5,
        "ask": 100.5,
        "received_at": START.isoformat(),
    }
    assert observed["row_reference"] == {
        "status": "OK",
        "bid": 99.5,
        "ask": 100.5,
        "received_at": START,
    }
    assert observed["hash_rebuild"] is True
    assert observed["id_rebuild"] is True
    assert observed["feature_hash_rebuild"] is True


async def _reconstruction_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        await _persist(sessions, facts, _context(), quote=_quote())
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
        payload = dict(row.evidence_payload)
        candidate = StrategyCandidate.model_validate(payload["candidate"])
        event = MarketEvent.model_validate(payload["triggering_event"])
        opportunity = build_opportunity_identity(
            family_id=EdgeFamily.BREAKOUT_RETEST,
            family_version=candidate.strategy_version,
            instrument_id=candidate.instrument_id,
            market_type=event.market_type,
            candidate_id=candidate.candidate_id,
        )
        reference = payload["reference_data"]
        supplied = reference["supplied_quote"]
        rebuilt = build_opportunity_evidence(
            event=event,
            timeline=SignalTimelineEvent.model_validate(payload["timeline"]),
            state=SymbolStateRecord.model_validate(payload["resulting_state"]),
            transition=StateTransition.model_validate(payload["transition"]),
            candidate=candidate,
            observation=FeatureSnapshot.model_validate(row.feature_snapshot_payload),
            context=EdgeCaptureContext(
                source_type=EvidenceSource(payload["provenance"]["source_type"]),
                source_identity=payload["provenance"]["source_identity"],
                source_manifest_id=payload["provenance"]["source_manifest_id"],
            ),
            # Rebuilt from the *supplied* quote rather than the accepted metrics:
            # the stored payload alone must reproduce the same status and the same
            # evidence hash -- including for a quote that ends up refused.
            reference_quote=(
                None
                if supplied is None
                else ReferenceQuote(
                    instrument_id=supplied["instrument_id"],
                    market_type=MarketType(supplied["market_type"]),
                    bid=supplied["bid"],
                    ask=supplied["ask"],
                    received_at=datetime.fromisoformat(supplied["received_at"]),
                    data_quality=DataQuality(supplied["data_quality"]),
                    tradable=supplied["tradable"],
                    source_event_time=(
                        None
                        if supplied["source_event_time"] is None
                        else datetime.fromisoformat(supplied["source_event_time"])
                    ),
                    source=supplied["source"],
                    source_sequence=supplied["source_sequence"],
                )
            ),
        )
        return {
            "event": event == facts["event"],
            "transition": StateTransition.model_validate(payload["transition"])
            == facts["transition"],
            "timeline": SignalTimelineEvent.model_validate(payload["timeline"])
            == facts["timeline"],
            "state": SymbolStateRecord.model_validate(payload["resulting_state"])
            == facts["state"],
            "candidate": candidate == _breakout_candidate(facts["candidates"]),
            "feature_snapshot": FeatureSnapshot.model_validate(row.feature_snapshot_payload)
            == facts["features"],
            "setup_expires_at": payload["setup_expires_at"],
            "versions": payload["versions"],
            "provenance": payload["provenance"],
            "reference_status": reference["status"],
            "supplied_quote": supplied,
            "accepted_reference": reference["accepted_reference"],
            "row_reference": {
                "status": row.reference_data_status,
                "bid": row.reference_bid,
                "ask": row.reference_ask,
                "received_at": row.reference_received_at,
            },
            "hash_rebuild": rebuilt.evidence_hash == row.evidence_hash,
            "id_rebuild": rebuilt.evidence_id == row.evidence_id,
            "feature_hash_rebuild": rebuilt.feature_snapshot_hash == row.feature_snapshot_hash,
            "opportunity_id_rebuild": opportunity.opportunity_id == row.opportunity_id,
        }


# --- G. real G2 runtime path ------------------------------------------------------------


def test_event_runtime_persists_the_setup_and_its_evidence_in_one_transaction():
    with _capture_database("runtime") as url:
        observed = asyncio.run(_runtime_scenario(url))
    assert observed["first_result"] == "APPLIED"
    assert observed["first_state"] == "DETECTED"
    assert observed["second_result"] == "APPLIED"
    assert observed["second_state"] == "SETUP"
    assert observed["evidence_rows"] == 1
    assert observed["row_revision"] == 1
    assert observed["g2"]["events"] == 2
    assert observed["g2"]["transitions"] == 2
    assert observed["worker_exceptions"] == 0


async def _runtime_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        authority = _live_authority()
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(),
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
        )
        runtime = EventRuntime(repository, worker_count=1)
        await runtime.start()
        try:
            features = _features()
            first = await runtime.publish(_event(event_id="evt-runtime-1", version=0), features)
            second = await runtime.publish(_event(event_id="evt-runtime-2", version=1), features)
        finally:
            await runtime.stop()
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            return {
                "first_result": first.result.value,
                "first_state": first.state.state.value,
                "second_result": second.result.value,
                "second_state": second.state.state.value,
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
                "row_revision": row.evidence_revision,
                "g2": await _g2_counts(session),
                "worker_exceptions": len(runtime.worker_exceptions),
            }


# --- H. reference quote quality and provenance (P0-1) -----------------------------------


def _supplied(**overrides: object) -> dict[str, object]:
    """The payload's ``supplied_quote`` half for the default ``_quote()``.

    Each case states only the field it actually changes, so the expectation stays
    readable while the comparison remains a full dict equality against the stored
    payload.
    """

    return {
        "instrument_id": INSTRUMENT,
        "market_type": "SPOT",
        "bid": 99.5,
        "ask": 100.5,
        "received_at": START.isoformat(),
        "data_quality": "FRESH",
        "tradable": True,
        "source_event_time": START.isoformat(),
        "source": "fixture-bbo",
        "source_sequence": 1,
        **overrides,
    }


_ACCEPTED_REFERENCE = {"bid": 99.5, "ask": 100.5, "received_at": START.isoformat()}
_NO_ACCEPTED_REFERENCE = {"bid": None, "ask": None, "received_at": None}


def _provenance_cases() -> dict[str, tuple[object, str, object, object]]:
    """Every adverse reference state, plus the usable one, with its exact payload.

    ``evidence_at`` is the qualifying candidate's ``created_at`` (``START`` here),
    so a quote received later than ``START`` is *future* data for this opportunity
    and must be refused rather than treated as fresh.
    """

    refused = _NO_ACCEPTED_REFERENCE
    return {
        "usable": (_quote(), "OK", _supplied(), _ACCEPTED_REFERENCE),
        "future": (
            _quote(at=START + timedelta(seconds=1)),
            "REFERENCE_STALE",
            _supplied(received_at=(START + timedelta(seconds=1)).isoformat()),
            refused,
        ),
        "time_stale": (
            _quote(at=START - timedelta(minutes=2)),
            "REFERENCE_STALE",
            _supplied(received_at=(START - timedelta(minutes=2)).isoformat()),
            refused,
        ),
        "data_quality_stale": (
            _quote(data_quality=DataQuality.STALE),
            "REFERENCE_STALE",
            _supplied(data_quality="STALE"),
            refused,
        ),
        "data_quality_unavailable": (
            _quote(data_quality=DataQuality.UNAVAILABLE),
            "REFERENCE_STALE",
            _supplied(data_quality="UNAVAILABLE"),
            refused,
        ),
        "wrong_instrument": (
            _quote(instrument_id="ETH-USDT"),
            "REFERENCE_STALE",
            _supplied(instrument_id="ETH-USDT"),
            refused,
        ),
        "wrong_market_type": (
            _quote(market_type=MarketType.SWAP),
            "REFERENCE_STALE",
            _supplied(market_type="SWAP"),
            refused,
        ),
        "untradable": (
            _quote(tradable=False),
            "REFERENCE_STALE",
            _supplied(tradable=False),
            refused,
        ),
        "crossed": (
            _quote(bid=101.0, ask=100.0),
            "REFERENCE_STALE",
            _supplied(bid=101.0, ask=100.0),
            refused,
        ),
        "non_positive": (
            _quote(bid=0.0, ask=100.0),
            "REFERENCE_STALE",
            _supplied(bid=0.0, ask=100.0),
            refused,
        ),
        # ``NaN`` cannot be stored as a JSON number and the canonical hashing
        # contract fails closed on it, so the raw input is kept by name.
        "non_finite": (
            _quote(bid=float("nan")),
            "REFERENCE_STALE",
            _supplied(bid="NaN"),
            refused,
        ),
        # No quote was supplied at all, so there is nothing to keep.
        "missing": (None, "REFERENCE_MISSING", None, refused),
    }


def test_every_supplied_quote_is_kept_verbatim_while_only_ok_is_accepted():
    labels = sorted(_provenance_cases())
    with _capture_database("provenance") as url:
        observed = asyncio.run(_provenance_scenario(url, labels))

    cases = _provenance_cases()
    for label in labels:
        _, status, supplied, accepted = cases[label]
        item = observed[label]
        # An unusable reference never removes the opportunity sample.
        assert item["persisted"] is True, label
        assert item["capture_version"] == "se02b-runtime-capture-v3", label
        assert item["reference_data"] == {
            "status": status,
            "supplied_quote": supplied,
            "accepted_reference": accepted,
        }, label
        # SE-02A's top-level reference contract is unchanged: the refused metrics
        # stay NULL there, never a zero placeholder.
        assert item["row"] == {
            "status": status,
            "bid": None if status != "OK" else 99.5,
            "ask": None if status != "OK" else 100.5,
            "received_at": None if status != "OK" else START,
        }, label


def test_stale_and_unavailable_feed_quality_is_never_accepted_as_reference():
    """A well-formed quote is refused purely because the feed flagged its quality."""

    assert DataQuality.STALE is not DataQuality.FRESH
    assert DataQuality.UNAVAILABLE is not DataQuality.FRESH

    labels = ["data_quality_stale", "data_quality_unavailable"]
    with _capture_database("quality") as url:
        observed = asyncio.run(_provenance_scenario(url, labels))

    # The same quote is accepted verbatim when FRESH (see the ``usable`` case), so
    # the only difference under test here is the quality flag itself.
    for label, quality in (
        ("data_quality_stale", "STALE"),
        ("data_quality_unavailable", "UNAVAILABLE"),
    ):
        item = observed[label]
        assert item["persisted"] is True, label
        assert item["reference_data"]["status"] != "OK", label
        assert item["reference_data"]["status"] == "REFERENCE_STALE", label
        assert item["reference_data"]["supplied_quote"] == _supplied(
            data_quality=quality
        ), label
        assert item["reference_data"]["accepted_reference"] == {
            "bid": None,
            "ask": None,
            "received_at": None,
        }, label
        assert item["row"] == {
            "status": "REFERENCE_STALE",
            "bid": None,
            "ask": None,
            "received_at": None,
        }, label


async def _provenance_scenario(url: str, labels: list[str]) -> dict[str, object]:
    cases = _provenance_cases()
    candidate_by_label: dict[str, str] = {}
    async with _sessions(url) as sessions:
        for label in labels:
            quote, _, _, _ = cases[label]
            facts = _facts(event_id=f"evt-provenance-{label}")
            candidate_by_label[label] = _breakout_candidate(
                facts["candidates"]
            ).candidate_id
            await _persist(sessions, facts, _context(), quote=quote)
        async with sessions() as session:
            rows = list(
                (await session.scalars(select(EdgeOpportunityEvidenceRecord))).all()
            )
    by_candidate = {row.candidate_id: row for row in rows}
    observed: dict[str, object] = {}
    for label, candidate_id in candidate_by_label.items():
        row = by_candidate.get(candidate_id)
        if row is None:
            observed[label] = {"persisted": False}
            continue
        payload = dict(row.evidence_payload)
        observed[label] = {
            "persisted": True,
            "capture_version": payload["capture"]["payload_version"],
            "reference_data": payload["reference_data"],
            "row": {
                "status": row.reference_data_status,
                "bid": row.reference_bid,
                "ask": row.reference_ask,
                "received_at": row.reference_received_at,
            },
        }
    return observed


# --- I. per-opportunity reference quote (P0-1) ------------------------------------------


def test_each_opportunity_is_evidenced_only_by_its_own_reference_quote():
    with _capture_database("perquote") as url:
        observed = asyncio.run(_per_quote_scenario(url))

    assert observed["btc"]["status"] == "OK"
    assert observed["btc"]["bid"] == 99.5
    assert observed["btc"]["ask"] == 100.5
    assert observed["eth"]["status"] == "OK"
    assert observed["eth"]["bid"] == 2500.0
    assert observed["eth"]["ask"] == 2501.0
    # A symbol with no quote of its own must never inherit another symbol's BBO.
    assert observed["sol"]["status"] == "REFERENCE_MISSING"
    assert observed["sol"]["bid"] is None
    assert observed["sol"]["ask"] is None


async def _per_quote_scenario(url: str) -> dict[str, object]:
    quotes = {
        "BTC-USDT": _quote(bid=99.5, ask=100.5, instrument_id="BTC-USDT"),
        "ETH-USDT": _quote(bid=2500.0, ask=2501.0, instrument_id="ETH-USDT"),
    }
    observed: dict[str, object] = {}
    async with _sessions(url) as sessions:
        candidate_by_label: dict[str, str] = {}
        for label, instrument_id in (
            ("btc", "BTC-USDT"),
            ("eth", "ETH-USDT"),
            ("sol", "SOL-USDT"),
        ):
            facts = _facts(event_id=f"evt-{label}", instrument_id=instrument_id)
            candidate_by_label[label] = _breakout_candidate(
                facts["candidates"]
            ).candidate_id
            await _persist(
                sessions, facts, _context(), quotes_by_instrument=quotes
            )
        async with sessions() as session:
            rows = list(
                (await session.scalars(select(EdgeOpportunityEvidenceRecord))).all()
            )
        by_candidate = {row.candidate_id: row for row in rows}
        for label, candidate_id in candidate_by_label.items():
            row = by_candidate[candidate_id]
            observed[label] = {
                "status": row.reference_data_status,
                "bid": row.reference_bid,
                "ask": row.reference_ask,
            }
    return observed


# --- J. causal anchor of the evidence horizon (P0-2) ------------------------------------


def test_evidence_horizon_is_anchored_on_the_candidate_not_the_event_receipt():
    with _capture_database("anchor") as url:
        observed = asyncio.run(_anchor_scenario(url))

    # Strictly ordered: event happened, then was received, then the candidate existed.
    for item in observed.values():
        assert item["detected_at"] == START
        assert item["created_at"] == START + timedelta(seconds=1)
        assert item["evidence_at"] == START + timedelta(seconds=10)
    # A quote received at the candidate's own moment is fresh: 0 <= 0 <= max_age.
    assert observed["at_evidence_anchor"]["status"] == "OK"
    # A quote received at the *event receipt* is 9s older than the evidence anchor,
    # so it is stale against the real horizon. Had freshness been measured from the
    # event receipt the age would have been 0 and it would have been accepted.
    assert observed["at_event_receipt"]["status"] == "REFERENCE_STALE"


async def _anchor_scenario(url: str) -> dict[str, object]:
    received_at = START + timedelta(seconds=1)
    candidate_at = START + timedelta(seconds=10)
    observed: dict[str, object] = {}
    async with _sessions(url) as sessions:
        for label, quote_at in (
            ("at_evidence_anchor", candidate_at),
            ("at_event_receipt", received_at),
        ):
            facts = _facts(
                event_id=f"evt-{label}",
                at=START,
                received_at=received_at,
                created_at=candidate_at,
            )
            candidate = _breakout_candidate(facts["candidates"])
            assert candidate.created_at == candidate_at
            await _persist(sessions, facts, _context(), quote=_quote(at=quote_at))
            async with sessions() as session:
                row = (
                    await session.scalars(
                        select(EdgeOpportunityEvidenceRecord).where(
                            EdgeOpportunityEvidenceRecord.candidate_id
                            == candidate.candidate_id
                        )
                    )
                ).one()
            observed[label] = {
                "status": row.reference_data_status,
                "detected_at": row.detected_at,
                "evidence_at": row.evidence_at,
                "created_at": row.created_at,
            }
    return observed


# --- K. SE-ARCH-FIX-01 durable capture admission ---------------------------------------


def test_stable_anchor_reuses_original_t0_bbo_and_payload_after_formal_failure():
    with _capture_database("stable_anchor_retry") as url:
        observed = asyncio.run(_stable_anchor_retry_scenario(url))

    assert observed["anchor_count"] == 1
    assert observed["evidence_count"] == 1
    assert observed["bbo_count"] == 1
    assert observed["evidence_at"] == START
    assert observed["reference_bbo_id"] == observed["anchor_bbo_id"]
    assert observed["bid"] == 99.5
    assert observed["ask"] == 100.5
    assert observed["evidence_hash"] == observed["frozen_evidence_hash"]


async def _stable_anchor_retry_scenario(url: str) -> dict[str, object]:
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    original_facts = _facts(created_at=START)
    later_facts = _facts(created_at=START + timedelta(seconds=10))
    original_quote = _quote(
        bid=99.5,
        ask=100.5,
        source="okx-bbo-tbt",
        source_event_time=START,
        source_sequence=101,
    )
    later_quote = _quote(
        bid=101.5,
        ask=102.5,
        at=START + timedelta(seconds=10),
        source="okx-bbo-tbt",
        source_event_time=START + timedelta(seconds=10),
        source_sequence=102,
    )
    quotes = [original_quote]
    async with _sessions(url) as sessions:
        authority = _live_authority()
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: quotes[0],
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
        )
        original_capture = g2_repository_module.capture_opportunity

        async def fail_formal(*_args, **_kwargs):
            raise RuntimeError("injected formal transaction failure")

        g2_repository_module.capture_opportunity = fail_formal
        try:
            try:
                await repository.persist(
                    original_facts["event"],
                    original_facts["timeline"],
                    original_facts["state"],
                    original_facts["transition"],
                    original_facts["candidates"],
                    original_facts["features"],
                    precondition_state=precondition,
                )
            except RuntimeError as error:
                assert str(error) == "injected formal transaction failure"
            else:
                raise AssertionError("formal failure must propagate")
        finally:
            g2_repository_module.capture_opportunity = original_capture

        # A fresh process has different current clock/BBO/provenance facts. The
        # durable anchor, not source-B live state, must drive Formal evidence.
        quotes[0] = later_quote
        process_b = PostgresG2Repository(
            sessions,
            capture=EdgeCaptureContext(
                source_type=EvidenceSource.FORWARD_PAPER,
                source_identity="source-b-new-session",
                source_manifest_id="manifest-source-b",
            ),
            reference_quote_for=lambda _instrument_id: quotes[0],
        )
        assert await process_b.persist(
            later_facts["event"],
            later_facts["timeline"],
            later_facts["state"],
            later_facts["transition"],
            later_facts["candidates"],
            later_facts["features"],
            precondition_state=precondition,
        )
        async with sessions() as session:
            anchor = (await session.scalars(select(EdgeOpportunityCaptureAnchorRecord))).one()
            evidence = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            bbo = (await session.scalars(select(EdgeBboObservationRecord))).one()
            return {
                "anchor_count": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence_count": await _count(session, EdgeOpportunityEvidenceRecord),
                "bbo_count": await _count(session, EdgeBboObservationRecord),
                "evidence_at": evidence.evidence_at,
                "reference_bbo_id": anchor.reference_bbo_observation_id,
                "anchor_bbo_id": bbo.observation_id,
                "bid": evidence.reference_bid,
                "ask": evidence.reference_ask,
                "evidence_hash": evidence.evidence_hash,
                "frozen_evidence_hash": anchor.anchor_payload["formal_evidence_hash"],
            }


def test_fresh_repository_resumes_durable_anchor_without_current_quote():
    with _capture_database("stable_anchor_restart") as url:
        observed = asyncio.run(_fresh_repository_resume_scenario(url))

    assert observed == {"resumed": 1, "anchors": 1, "evidence": 1}


async def _fresh_repository_resume_scenario(url: str) -> dict[str, int]:
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    facts = _facts(created_at=START)
    async with _sessions(url) as sessions:
        authority = _live_authority(session_id="process-a")
        process_a = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(
                source="okx-bbo-tbt", source_event_time=START, source_sequence=101
            ),
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
        )
        original_capture = g2_repository_module.capture_opportunity

        async def fail_formal(*_args, **_kwargs):
            raise RuntimeError("injected formal transaction failure")

        g2_repository_module.capture_opportunity = fail_formal
        try:
            try:
                await process_a.persist(
                    facts["event"], facts["timeline"], facts["state"], facts["transition"],
                    facts["candidates"], facts["features"], precondition_state=precondition,
                )
            except RuntimeError:
                pass
        finally:
            g2_repository_module.capture_opportunity = original_capture

        # A newly constructed repository has no process-A pending-memory object
        # and no reference quote accessor. Recovery reads the anchor only.
        process_b = PostgresG2Repository(sessions, capture=_context())
        resumed = await process_b.resume_pending_capture_anchors()
        async with sessions() as session:
            return {
                "resumed": resumed,
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
            }


def test_forward_anchor_requires_explicit_live_session_proof_and_anchor_conflicts_fail_closed():
    with _capture_database("stable_anchor_admission") as url:
        observed = asyncio.run(_anchor_admission_scenario(url))

    assert observed == {"rejected": True, "idempotent": True, "conflict": True}


async def _anchor_admission_scenario(url: str) -> dict[str, bool]:
    facts = _facts(created_at=START)
    context = EdgeCaptureContext(
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-se02b",
    )
    async with _sessions(url) as sessions:
        repository = PostgresG2Repository(sessions, capture=context)
        try:
            await repository.persist(
                facts["event"], facts["timeline"], facts["state"], facts["transition"],
                facts["candidates"], facts["features"], precondition_state=SymbolStateRecord(
                    instrument_id=INSTRUMENT, symbol=INSTRUMENT
                ),
            )
        except CaptureAdmissionRejected:
            rejected = True
        else:
            rejected = False

        admitted_context = _context()
        authority = _live_authority()
        anchor = build_capture_anchor(
            precondition_state=None,
            event=facts["event"], timeline=facts["timeline"], state=facts["state"],
            transition=facts["transition"], candidates=facts["candidates"],
            observation=facts["features"], context=admitted_context,
            forward_admission_proof=authority.admit_live_input(facts["event"]), reference_quote=None,
        )
        assert anchor is not None
        async with sessions() as session, session.begin():
            idempotent = await append_capture_anchor(session, anchor) == INSERTED
        async with sessions() as session, session.begin():
            idempotent = (await append_capture_anchor(session, anchor) == IDEMPOTENT) and idempotent
        changed = build_capture_anchor(
            precondition_state=None,
            event=facts["event"], timeline=facts["timeline"], state=facts["state"],
            transition=facts["transition"],
            candidates=_candidates(facts["features"], facts["event"], facts["state"].state_version,
                                   created_at=START + timedelta(seconds=1)),
            observation=facts["features"], context=admitted_context,
            forward_admission_proof=authority.admit_live_input(facts["event"]), reference_quote=None,
        )
        assert changed is not None
        async with sessions() as session, session.begin():
            try:
                await append_capture_anchor(session, changed)
            except EdgeCaptureAnchorConflict:
                conflict = True
            else:
                conflict = False
        return {"rejected": rejected, "idempotent": idempotent, "conflict": conflict}


def test_same_process_anchor_write_failure_retries_the_frozen_payload_only():
    with _capture_database("stable_anchor_same_process") as url:
        observed = asyncio.run(_same_process_anchor_failure_scenario(url))

    assert observed == {"anchors": 1, "evidence_at": START, "bid": 99.5, "ask": 100.5}


async def _same_process_anchor_failure_scenario(url: str) -> dict[str, object]:
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    original_facts = _facts(created_at=START)
    later_facts = _facts(created_at=START + timedelta(seconds=10))
    original_quote = _quote(
        source="okx-bbo-tbt", source_event_time=START, source_sequence=101
    )
    quotes = [original_quote]
    async with _sessions(url) as sessions:
        authority = _live_authority()
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: quotes[0],
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
        )
        original_record = g2_repository_module.record_bbo_observation

        async def fail_anchor_write(*_args, **_kwargs):
            raise RuntimeError("injected anchor write failure")

        g2_repository_module.record_bbo_observation = fail_anchor_write
        try:
            try:
                await repository.persist(
                    original_facts["event"], original_facts["timeline"], original_facts["state"],
                    original_facts["transition"], original_facts["candidates"], original_facts["features"],
                    precondition_state=precondition,
                )
            except RuntimeError as error:
                assert str(error) == "injected anchor write failure"
            else:
                raise AssertionError("anchor write failure must propagate")
        finally:
            g2_repository_module.record_bbo_observation = original_record

        quotes[0] = _quote(
            bid=101.5,
            ask=102.5,
            at=START + timedelta(seconds=10),
            source="okx-bbo-tbt",
            source_event_time=START + timedelta(seconds=10),
            source_sequence=102,
        )
        assert await repository.persist(
            later_facts["event"], later_facts["timeline"], later_facts["state"],
            later_facts["transition"], later_facts["candidates"], later_facts["features"],
            precondition_state=precondition,
        )
        async with sessions() as session:
            evidence = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            return {
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence_at": evidence.evidence_at,
                "bid": evidence.reference_bid,
                "ask": evidence.reference_ask,
            }


def test_incompatible_durable_g2_precondition_leaves_an_auditable_orphan():
    with _capture_database("stable_anchor_orphan") as url:
        observed = asyncio.run(_orphan_anchor_scenario(url))

    assert observed == {
        "orphaned": True,
        "retry_resumed": 0,
        "anchors": 1,
        "evidence": 0,
        "orphans": 1,
    }


async def _orphan_anchor_scenario(url: str) -> dict[str, object]:
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    facts = _facts(created_at=START)
    async with _sessions(url) as sessions:
        authority = _live_authority(session_id="process-a")
        process_a = PostgresG2Repository(
            sessions,
            capture=_context(),
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
        )
        original_capture = g2_repository_module.capture_opportunity

        async def fail_formal(*_args, **_kwargs):
            raise RuntimeError("injected formal transaction failure")

        g2_repository_module.capture_opportunity = fail_formal
        try:
            try:
                await process_a.persist(
                    facts["event"], facts["timeline"], facts["state"], facts["transition"],
                    facts["candidates"], facts["features"], precondition_state=precondition,
                )
            except RuntimeError:
                pass
        finally:
            g2_repository_module.capture_opportunity = original_capture

        # Another durable G2 writer makes the original anchor precondition stale.
        async with sessions() as session, session.begin():
            session.add(SymbolStateStore(**facts["state"].model_dump(mode="python")))
        process_b = PostgresG2Repository(sessions, capture=_context())
        try:
            await process_b.resume_pending_capture_anchors()
        except CaptureAnchorOrphan:
            orphaned = True
        else:
            orphaned = False
        retry_resumed = await process_b.resume_pending_capture_anchors()
        async with sessions() as session:
            return {
                "orphaned": orphaned,
                "retry_resumed": retry_resumed,
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
                "orphans": await _count(session, EdgeOpportunityCaptureAnchorOrphanRecord),
            }


def test_old_redelivery_after_pre_anchor_crash_is_not_admitted_by_a_new_session():
    """A new process must not turn an arbitrary old event into live Forward input."""

    with _capture_database("redelivery_without_anchor") as url:
        observed = asyncio.run(_old_redelivery_scenario(url))

    assert observed == {"redelivery_admitted": False, "anchors": 0, "evidence": 0}


async def _old_redelivery_scenario(url: str) -> dict[str, object]:
    facts = _facts(event_id="evt-before-anchor-crash")
    authority = _live_authority(session_id="new-process-live-session")
    async with _sessions(url) as sessions:
        # The event is a redelivery after a process died *before* it durable-wrote
        # an anchor. The new BBO/session may observe it, but only the live-ingress
        # boundary can issue proof and it refuses this old delivery.
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(
                bid=101.5,
                ask=102.5,
                at=START + timedelta(seconds=10),
                source_event_time=START + timedelta(seconds=10),
                source_sequence=999,
            ),
            forward_admission_authority=authority,
            forward_admission_proof_for=lambda _event: None,
        )
        try:
            await repository.persist(
                facts["event"],
                facts["timeline"],
                facts["state"],
                facts["transition"],
                facts["candidates"],
                facts["features"],
                precondition_state=SymbolStateRecord(
                    instrument_id=INSTRUMENT, symbol=INSTRUMENT
                ),
            )
        except CaptureAdmissionRejected:
            redelivery_admitted = False
        else:
            redelivery_admitted = True
        async with sessions() as session:
            return {
                "redelivery_admitted": redelivery_admitted,
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
            }


def test_incomplete_bbo_provenance_is_stale_and_never_binds_an_observation():
    with _capture_database("incomplete_bbo_provenance") as url:
        observed = asyncio.run(_incomplete_bbo_provenance_scenario(url))

    assert observed == {"status": "REFERENCE_STALE", "bbo_id": None, "bbo_rows": 0}


async def _incomplete_bbo_provenance_scenario(url: str) -> dict[str, object]:
    facts = _facts(event_id="evt-incomplete-bbo")
    async with _sessions(url) as sessions:
        await _persist(
            sessions,
            facts,
            _context(),
            quote=_quote(source_event_time=None, source=None, source_sequence=None),
        )
        async with sessions() as session:
            evidence = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            anchor = (await session.scalars(select(EdgeOpportunityCaptureAnchorRecord))).one()
            return {
                "status": evidence.reference_data_status,
                "bbo_id": anchor.reference_bbo_observation_id,
                "bbo_rows": await _count(session, EdgeBboObservationRecord),
            }


def test_anchor_tampering_of_any_duplicated_causal_fact_fails_closed():
    with _capture_database("anchor_tamper") as url:
        observed = asyncio.run(_anchor_tamper_scenario(url))

    assert observed == {
        "candidate": True,
        "t0": True,
        "bbo": True,
        "source": True,
        "session": True,
    }


async def _anchor_tamper_scenario(url: str) -> dict[str, bool]:
    facts = _facts(event_id="evt-anchor-tamper")
    authority = _live_authority()
    anchor = build_capture_anchor(
        precondition_state=SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT),
        event=facts["event"],
        timeline=facts["timeline"],
        state=facts["state"],
        transition=facts["transition"],
        candidates=facts["candidates"],
        observation=facts["features"],
        context=_context(),
        forward_admission_proof=authority.admit_live_input(facts["event"]),
        reference_quote=None,
    )
    assert anchor is not None
    altered = {
        "candidate": anchor.model_copy(update={"candidate_id": "tampered-candidate"}),
        "t0": anchor.model_copy(update={"evidence_at": START + timedelta(seconds=1)}),
        "bbo": anchor.model_copy(update={"reference_bbo_observation_id": "tampered-bbo"}),
        "source": anchor.model_copy(update={"source_identity": "tampered-source"}),
        "session": anchor.model_copy(
            update={"forward_admission_session_id": "tampered-session"}
        ),
    }
    outcomes: dict[str, bool] = {}
    async with _sessions(url) as sessions:
        for label, tampered in altered.items():
            async with sessions() as session, session.begin():
                try:
                    await append_capture_anchor(session, tampered)
                except ValueError:
                    outcomes[label] = True
                else:
                    outcomes[label] = False
    return outcomes


def test_concurrent_capture_anchor_append_is_atomic_for_idempotency_and_conflict():
    with _capture_database("anchor_concurrency") as url:
        observed = asyncio.run(_anchor_concurrency_scenario(url))

    assert observed == {"same_hash": [IDEMPOTENT, INSERTED], "conflict": True, "rows": 1}


async def _anchor_concurrency_scenario(url: str) -> dict[str, object]:
    facts = _facts(event_id="evt-anchor-concurrency")
    authority = _live_authority()
    anchor = build_capture_anchor(
        precondition_state=SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT),
        event=facts["event"],
        timeline=facts["timeline"],
        state=facts["state"],
        transition=facts["transition"],
        candidates=facts["candidates"],
        observation=facts["features"],
        context=_context(),
        forward_admission_proof=authority.admit_live_input(facts["event"]),
        reference_quote=None,
    )
    assert anchor is not None
    conflicting = build_capture_anchor(
        precondition_state=SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT),
        event=facts["event"],
        timeline=facts["timeline"],
        state=facts["state"],
        transition=facts["transition"],
        candidates=facts["candidates"],
        observation=facts["features"],
        context=EdgeCaptureContext(
            source_type=EvidenceSource.FORWARD_PAPER,
            source_identity="another-valid-source",
            source_manifest_id="manifest-se02b",
        ),
        forward_admission_proof=authority.admit_live_input(facts["event"]),
        reference_quote=None,
    )
    assert conflicting is not None

    async with _sessions(url) as sessions:
        async def append_once() -> str:
            async with sessions() as session, session.begin():
                return await append_capture_anchor(session, anchor)

        same_hash = sorted(await asyncio.gather(append_once(), append_once()))
        async with sessions() as session, session.begin():
            try:
                await append_capture_anchor(session, conflicting)
            except EdgeCaptureAnchorConflict:
                conflict = True
            else:
                conflict = False
        async with sessions() as session:
            rows = await _count(session, EdgeOpportunityCaptureAnchorRecord)
    return {"same_hash": same_hash, "conflict": conflict, "rows": rows}


def test_pending_anchor_capacity_fails_closed_without_silent_eviction():
    with _capture_database("anchor_capacity") as url:
        observed = asyncio.run(_anchor_capacity_scenario(url))

    assert observed == {"first_failed": True, "overloaded": True, "anchors": 0, "evidence": 0}


async def _anchor_capacity_scenario(url: str) -> dict[str, object]:
    first = _facts(event_id="evt-anchor-capacity-first")
    second = _facts(event_id="evt-anchor-capacity-second")
    authority = _live_authority()
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    async with _sessions(url) as sessions:
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(),
            forward_admission_authority=authority,
            forward_admission_proof_for=authority.admit_live_input,
            pending_capture_anchor_capacity=1,
        )
        original_record = g2_repository_module.record_bbo_observation

        async def fail_anchor_write(*_args, **_kwargs):
            raise RuntimeError("injected first admission write failure")

        g2_repository_module.record_bbo_observation = fail_anchor_write
        try:
            try:
                await repository.persist(
                    first["event"], first["timeline"], first["state"], first["transition"],
                    first["candidates"], first["features"], precondition_state=precondition,
                )
            except RuntimeError:
                first_failed = True
            else:
                first_failed = False
        finally:
            g2_repository_module.record_bbo_observation = original_record
        try:
            await repository.persist(
                second["event"], second["timeline"], second["state"], second["transition"],
                second["candidates"], second["features"], precondition_state=precondition,
            )
        except CaptureAdmissionOverloaded:
            overloaded = True
        else:
            overloaded = False
        async with sessions() as session:
            return {
                "first_failed": first_failed,
                "overloaded": overloaded,
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
            }
