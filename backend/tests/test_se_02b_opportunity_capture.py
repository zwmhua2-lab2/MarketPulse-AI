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
import inspect
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import marketpulse.g2.repository as g2_repository_module
import pytest
from alembic import command
from alembic.config import Config
from marketpulse.advisory.attempts import AdvisoryAttemptStarter
from marketpulse.advisory.contracts import AdvisoryActivationEpoch, AdvisoryAdmissionConfig
from marketpulse.advisory.fence import AdvisoryDbFence
from marketpulse.advisory.ingress import AdvisoryAdmissionWriter, AdvisoryIngress
from marketpulse.advisory.worker import (
    AdvisoryFinalizer,
    AdvisoryRecovery,
    AdvisoryWorker,
    FakeProviderResult,
)
from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    AdvisoryDecisionAttemptRecord,
    AdvisoryDecisionInvocationRecord,
    DecisionSnapshotRecord,
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
    FORWARD_ADMISSION_PROOF_VERSION,
    EdgeCaptureContext,
    ForwardAdmissionAuthority,
    ForwardAdmissionProof,
    ForwardAdmissionVerifier,
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
    InMemoryG2Repository,
    PostgresG2Repository,
)
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.market_data.models import DataQuality, MarketType, NormalizedMarketEvent
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
    inherited_database_url = os.environ.pop("DATABASE_URL", None)
    try:
        command.upgrade(_alembic_config(url), "head")
    finally:
        if inherited_database_url is not None:
            os.environ["DATABASE_URL"] = inherited_database_url
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


def _live_authority(
    *,
    session_id: str = "fixture-live-forward-session",
    session_started_at: datetime = START,
) -> ForwardAdmissionAuthority:
    """A deterministic fixture-only live ingress capability for one process.

    ``session_started_at`` is taken from the authority's own runtime clock, exactly
    as the production live ingress does; a caller cannot pass a timestamp.
    """

    return ForwardAdmissionAuthority(
        clock=ReplayClock(session_started_at),
        session_id=session_id,
        secret=b"se-arch-fix-01-fixture-live-ingress-secret",
    )


def _live_input(event: MarketEvent, *, at: datetime | None = None) -> NormalizedMarketEvent:
    """The normalized live-ingress input this G2 event was generated from."""

    return NormalizedMarketEvent(
        exchange="OKX",
        base_asset="BTC",
        quote_asset="USDT",
        market_type=event.market_type,
        instrument_id=event.instrument_id,
        event_time=event.event_time if at is None else at,
        received_time=event.received_time,
        source="fixture-live-ingress",
    )


def _admitted(
    authority: ForwardAdmissionAuthority, event: MarketEvent
) -> ForwardAdmissionProof | None:
    """Mint a proof exactly as ``ScannerPipeline.issue_admission_proof`` does."""

    return authority.issue(source_event=_live_input(event), event=event)


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
    advisory_admission_state: str | None = None,
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
        forward_admission_verifier=authority.verifier(),
        advisory_admission_state=advisory_admission_state,
    )
    precondition = await repository.get_state(facts["event"].instrument_id)
    return (
        await repository.persist(
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
            forward_admission_proof=_admitted(authority, facts["event"]),
        )
    ).persisted


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
    assert observed["row"]["advisory_admission_state"] == "UNSTAGED"


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
                    "advisory_admission_state",
                )
            },
        }


def test_disabled_capture_preserves_evidence_facts_and_anchor_hash_validation():
    """SA-01: capture forwards the frozen literal without changing Edge construction."""

    with _capture_database("disabled_original_insert") as url:
        observed = asyncio.run(_disabled_capture_scenario(url))

    assert observed["status"] == INSERTED
    assert observed["admission_state"] == "GATE_A_DISABLED"
    assert observed["evidence_id"] == observed["expected_evidence_id"]
    assert observed["opportunity_id"] == observed["expected_opportunity_id"]
    assert observed["evidence_hash"] == observed["expected_evidence_hash"]
    assert observed["feature_snapshot_hash"] == observed["expected_feature_snapshot_hash"]
    assert observed["evidence_payload"] == observed["expected_evidence_payload"]
    assert observed["feature_snapshot_payload"] == observed["expected_feature_snapshot_payload"]
    assert observed["wrong_anchor_rejected"] is True
    assert observed["evidence_rows"] == 1


def test_g2_caller_forwards_frozen_disabled_classification_to_the_original_insert():
    with _capture_database("disabled_g2_caller") as url:
        observed = asyncio.run(_disabled_g2_caller_scenario(url))

    assert observed == {"persisted": True, "state": "GATE_A_DISABLED", "rows": 1}


def test_gate_a_admission_stages_complete_snapshot_and_invocation_after_core_flush():
    """The active-capable seam is injected; ordinary runtime stays disabled."""

    with _capture_database("gate_a_admission") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url))

    assert observed["persisted"] is True
    assert observed["has_work_ref"] is True
    assert observed["evidence_state"] == "INVOCATION_CREATED"
    assert observed["seed_complete"] is True
    assert observed["invocations"] == 1
    assert observed["snapshots"] == 1
    assert observed["fence_held_after_commit"] == 0
    assert observed["ref_matches_invocation"] is True
    assert observed["attempt_started"] is True
    assert observed["provider_calls"] == 1
    assert observed["provider_db_held"] == 0
    assert observed["invocation_final"] is True
    assert observed["final_attempt_matches"] is True


@pytest.mark.parametrize(
    ("retry_allowed", "expected_state", "expected_final"),
    [(True, "RETRY_PENDING", None), (False, "FINAL", "RETRY_EXHAUSTED")],
)
def test_process_lost_recovery_uses_the_durable_started_attempt_only(
    retry_allowed, expected_state, expected_final
):
    with _capture_database(f"process_lost_{retry_allowed}") as url:
        observed = asyncio.run(
            _gate_a_admission_scenario(url, process_lost_retry_allowed=retry_allowed)
        )

    assert observed["provider_calls"] == 0
    assert observed["attempt_state"] == "PROCESS_LOST"
    assert observed["invocation_state"] == expected_state
    assert observed["final_reason"] == expected_final
    assert observed["recovery_queue_size"] == (1 if retry_allowed else None)


def test_live_shutdown_abandons_only_the_current_durable_attempt():
    with _capture_database("abandoned_shutdown") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, abandon=True))

    assert observed["provider_calls"] == 0
    assert observed["attempt_state"] == "ABANDONED"
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT"
    assert observed["final_attempt_matches"] is True


def test_completion_shutdown_and_recovery_race_leave_one_authoritative_winner():
    with _capture_database("concurrent_terminal_contenders") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, terminal_race=True))

    assert observed["invocation_state"] == "FINAL"
    assert observed["final_attempt_matches"] is True
    assert observed["final_reason"] in {
        "VALID_PROVIDER_DECISION",
        "SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT",
        "RETRY_EXHAUSTED",
    }


def test_concurrent_duplicate_finalization_has_one_immutable_winner():
    with _capture_database("concurrent_winner") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, duplicate_finalize=True))

    assert observed["provider_calls"] == 0
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "VALID_PROVIDER_DECISION"
    assert observed["attempt_state"] == "COMPLETED"


def test_late_result_cannot_replace_the_retry_attempt_winner():
    with _capture_database("late_result") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, late_result=True))

    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "VALID_PROVIDER_DECISION"
    assert observed["attempt_count"] == 2
    assert observed["attempt_states"] == ["LATE_RESULT", "COMPLETED"]
    assert observed["final_attempt_matches_latest"] is True


def test_retry_reoffers_the_same_invocation_through_the_bounded_ingress():
    with _capture_database("retry_reoffer") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, retry_once=True))

    assert observed["provider_calls"] == 2
    assert observed["attempt_count"] == 2
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "VALID_PROVIDER_DECISION"


def test_provider_response_left_only_in_memory_recovers_as_process_lost():
    with _capture_database("provider_returned_uncommitted") as url:
        observed = asyncio.run(
            _gate_a_admission_scenario(url, provider_returned_uncommitted=True)
        )

    assert observed["provider_calls"] == 1
    assert observed["attempt_state"] == "PROCESS_LOST"
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "RETRY_EXHAUSTED"


def test_retry_gap_queue_rejection_does_not_link_the_historical_attempt():
    with _capture_database("retry_gap_queue_rejection") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, retry_gap_queue_reject=True))

    assert observed["provider_calls"] == 1
    assert observed["attempt_count"] == 1
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "ADVISORY_QUEUE_REJECTED"
    assert observed["final_attempt_is_null"] is True


def test_retry_gap_db_capacity_rejection_does_not_create_a_replacement_attempt():
    with _capture_database("retry_gap_db_capacity_rejection") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, retry_gap_db_capacity=True))

    assert observed["provider_calls"] == 0
    assert observed["attempt_count"] == 1
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "ADVISORY_DB_CAPACITY_UNAVAILABLE"
    assert observed["final_attempt_is_null"] is True


def test_supersede_before_finalizer_fences_the_old_attempt_as_stale():
    with _capture_database("supersede_before_finalizer") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, supersede_before_finalize=True))

    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "EVIDENCE_SUPERSEDED"
    assert observed["final_attempt_is_null"] is False


def test_finalizer_first_keeps_its_winner_immutable_when_a_new_evidence_revision_arrives():
    with _capture_database("finalizer_before_supersede") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, supersede_after_finalize=True))

    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "VALID_PROVIDER_DECISION"
    assert observed["evidence_revision_count"] == 2
    assert observed["invocation_evidence_superseded"] is True


def test_shutdown_cancellation_without_a_durable_cleanup_commit_recovers_as_process_lost():
    with _capture_database("shutdown_crash_before_abandon_commit") as url:
        observed = asyncio.run(_gate_a_admission_scenario(url, shutdown_crash_boundary=True))

    assert observed["provider_calls"] == 0
    assert observed["attempt_state"] == "PROCESS_LOST"
    assert observed["invocation_state"] == "FINAL"
    assert observed["final_reason"] == "RETRY_EXHAUSTED"


async def _gate_a_admission_scenario(
    url: str,
    *,
    process_lost_retry_allowed: bool | None = None,
    abandon: bool = False,
    terminal_race: bool = False,
    duplicate_finalize: bool = False,
    late_result: bool = False,
    retry_once: bool = False,
    provider_returned_uncommitted: bool = False,
    retry_gap_queue_reject: bool = False,
    retry_gap_db_capacity: bool = False,
    supersede_before_finalize: bool = False,
    supersede_after_finalize: bool = False,
    shutdown_crash_boundary: bool = False,
) -> dict[str, object]:
    config = AdvisoryAdmissionConfig(
        epoch=AdvisoryActivationEpoch("GATE_A_SHADOW", epoch_id="fixture-epoch-1"),
        config_version="fixture-config-1",
        configured_provider_id="fake-provider",
        configured_model_id="fake-model",
        deadline_duration_ms=30_000,
        experiment_definition={
            "placement": "C_TRADE_DECISION",
            "family": "BREAKOUT_RETEST",
            "version": "fixture-experiment-1",
        },
    )
    async with _sessions(url) as sessions:
        fence = AdvisoryDbFence(
            effective_db_capacity=4 if terminal_race else (3 if duplicate_finalize else 2),
            protection_reserve=1,
            session_factory=sessions,
        )
        # Test composition uses the same public PoolEvents authority as the
        # RuntimeHost-owned primary engine.  No checkout key is fabricated.
        fence.install_pool_listeners(sessions.kw["bind"].sync_engine)
        facts = _facts()
        authority = _live_authority()
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _: _quote(),
            forward_admission_verifier=authority.verifier(),
            advisory_admission_writer=AdvisoryAdmissionWriter(config),
            advisory_db_fence=fence,
        )
        result = await repository.persist(
            facts["event"],
            facts["timeline"],
            facts["state"],
            facts["transition"],
            facts["candidates"],
            facts["features"],
            precondition_state=SymbolStateRecord(
                instrument_id=facts["event"].instrument_id,
                symbol=facts["event"].symbol,
            ),
            forward_admission_proof=_admitted(authority, facts["event"]),
        )
        started_attempt = None
        provider_calls = 0
        provider_db_held = -1
        if result.advisory_work_ref is not None:
            class FakeProvider:
                async def decide(self, _ref, attempt_id):
                    nonlocal provider_calls, provider_db_held
                    provider_calls += 1
                    provider_db_held = fence.held
                    return FakeProviderResult(
                        retry=(retry_once or retry_gap_queue_reject) and provider_calls == 1,
                        payload={"attempt_id": attempt_id},
                    )

            starter = AdvisoryAttemptStarter(fence)
            finalizer = AdvisoryFinalizer(fence)
            if abandon:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                assert await finalizer.abandon(started_attempt, cancellation_observed=True)
            elif terminal_race:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                await asyncio.gather(
                    finalizer.finalize(started_attempt, FakeProviderResult()),
                    finalizer.abandon(started_attempt, cancellation_observed=True),
                    AdvisoryRecovery(fence, finalizer).recover_process_lost(retry_allowed=False),
                )
            elif provider_returned_uncommitted:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                await FakeProvider().decide(result.advisory_work_ref, started_attempt)
                assert await AdvisoryRecovery(fence, finalizer).recover_process_lost(
                    retry_allowed=False
                ) == 1
            elif shutdown_crash_boundary:
                # Cancellation acknowledgement existed only in the dead process's
                # memory. No ABANDONED transaction ran, so the new owner sees the
                # durable STARTED record and must classify PROCESS_LOST.
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                assert await AdvisoryRecovery(fence, finalizer).recover_process_lost(
                    retry_allowed=False
                ) == 1
            elif duplicate_finalize:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                await asyncio.gather(
                    finalizer.finalize(started_attempt, FakeProviderResult()),
                    finalizer.finalize(started_attempt, FakeProviderResult()),
                )
            elif late_result:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                retry_ref = await finalizer.finalize(
                    started_attempt, FakeProviderResult(retry=True)
                )
                assert retry_ref == result.advisory_work_ref
                winning_attempt = await starter.start(retry_ref)
                assert winning_attempt is not None
                await finalizer.finalize(winning_attempt, FakeProviderResult())
                await finalizer.finalize(started_attempt, FakeProviderResult())
            elif supersede_before_finalize:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                await _append_test_superseding_evidence(fence)
                await finalizer.finalize(started_attempt, FakeProviderResult())
            elif supersede_after_finalize:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                await finalizer.finalize(started_attempt, FakeProviderResult())
                await _append_test_superseding_evidence(fence)
            elif retry_gap_db_capacity:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                retry_ref = await finalizer.finalize(
                    started_attempt, FakeProviderResult(retry=True)
                )
                assert retry_ref == result.advisory_work_ref
                release_holder = asyncio.Event()
                holder_ready = asyncio.Event()

                async def hold_advisory_capacity() -> None:
                    async with fence.transaction():
                        holder_ready.set()
                        await release_holder.wait()

                holder = asyncio.create_task(hold_advisory_capacity())
                await holder_ready.wait()
                worker = AdvisoryWorker(starter, finalizer, FakeProvider())
                # The first terminal-write lease is unavailable too.  Worker must
                # fail closed: no replacement Attempt, no Provider, no synthetic
                # terminal record while the real holder remains authoritative.
                assert await worker.consume(retry_ref) is None
                release_holder.set()
                await holder
                assert await finalizer.terminalize_db_capacity_unavailable(retry_ref)
                # A concurrent/external terminal winner remains immutable.
                assert not await finalizer.terminalize_db_capacity_unavailable(retry_ref)
            elif process_lost_retry_allowed is None:
                worker = AdvisoryWorker(starter, finalizer, FakeProvider())
                ingress = AdvisoryIngress(fence, queue_capacity=1)
                assert await ingress.post_commit_offer(result.advisory_work_ref)
                assert await ingress.consume_one(worker.consume)
                if retry_gap_queue_reject:
                    assert ingress.queue_size == 1
                    assert not await ingress.post_commit_offer(result.advisory_work_ref)
                elif retry_once:
                    assert ingress.queue_size == 1
                    assert await ingress.consume_one(worker.consume)
                assert ingress.queue_size == (1 if retry_gap_queue_reject else 0)
            else:
                started_attempt = await starter.start(result.advisory_work_ref)
                assert started_attempt is not None
                ingress = AdvisoryIngress(fence, queue_capacity=1)
                assert await AdvisoryRecovery(fence, finalizer).recover_process_lost(
                    retry_allowed=process_lost_retry_allowed,
                    reoffer=ingress.post_commit_offer if process_lost_retry_allowed else None,
                ) == 1
            async with sessions() as session:
                started_attempt = await session.scalar(
                    select(AdvisoryDecisionAttemptRecord.attempt_id)
                )
        async with sessions() as session:
            evidence = (
                await session.scalars(
                    select(EdgeOpportunityEvidenceRecord).where(
                        EdgeOpportunityEvidenceRecord.evidence_revision == 1
                    )
                )
            ).one()
            invocation = (await session.scalars(select(AdvisoryDecisionInvocationRecord))).one()
            attempt_state = await session.scalar(select(AdvisoryDecisionAttemptRecord.attempt_state))
            attempt_states = list(
                await session.scalars(
                    select(AdvisoryDecisionAttemptRecord.attempt_state).order_by(
                        AdvisoryDecisionAttemptRecord.attempt_number
                    )
                )
            )
            attempt_count = await _count(session, AdvisoryDecisionAttemptRecord)
            invocations = await _count(session, AdvisoryDecisionInvocationRecord)
            snapshots = await _count(session, DecisionSnapshotRecord)
            evidence_revision_count = await _count(session, EdgeOpportunityEvidenceRecord)
            latest_attempt_id = await session.scalar(
                select(AdvisoryDecisionAttemptRecord.attempt_id)
                .order_by(AdvisoryDecisionAttemptRecord.attempt_number.desc())
                .limit(1)
            )
        return {
            "persisted": result.persisted,
            "has_work_ref": result.advisory_work_ref is not None,
            "evidence_state": evidence.advisory_admission_state,
            "seed_complete": all(
                value is not None
                for value in (
                    evidence.advisory_admission_seed_version,
                    evidence.advisory_admission_seed_digest,
                    evidence.advisory_admission_seed,
                )
            ),
            "invocations": invocations,
            "snapshots": snapshots,
            "fence_held_after_commit": fence.held,
            "ref_matches_invocation": result.advisory_work_ref is not None
            and result.advisory_work_ref.decision_invocation_id
            == invocation.decision_invocation_id,
            "attempt_started": started_attempt is not None,
            "provider_calls": provider_calls,
            "provider_db_held": provider_db_held,
            "invocation_final": invocation.state == "FINAL",
            "final_attempt_matches": invocation.final_attempt_id == started_attempt,
            "attempt_state": attempt_state,
            "invocation_state": invocation.state,
            "final_reason": invocation.final_reason_code,
            "attempt_count": attempt_count,
            "attempt_states": attempt_states,
            "final_attempt_is_null": invocation.final_attempt_id is None,
            "final_attempt_matches_latest": invocation.final_attempt_id == latest_attempt_id,
            "recovery_queue_size": ingress.queue_size
            if process_lost_retry_allowed is True
            else None,
            "evidence_revision_count": evidence_revision_count,
            "invocation_evidence_superseded": evidence_revision_count
            > invocation.evidence_revision,
        }


async def _append_test_superseding_evidence(fence: AdvisoryDbFence) -> None:
    """Fixture-only predecessor-chain write; it does not alter Edge production behavior."""

    async with fence.transaction() as session:
        old = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
        session.add(
            EdgeOpportunityEvidenceRecord(
                evidence_id=f"{old.evidence_id[:-1]}9",
                opportunity_id=old.opportunity_id,
                candidate_id=old.candidate_id,
                family_id=old.family_id,
                family_version=old.family_version,
                instrument_id=old.instrument_id,
                market_type=old.market_type,
                evidence_revision=2,
                evidence_contract_version=old.evidence_contract_version,
                evidence_hash="d" * 64,
                feature_snapshot_hash="e" * 64,
                feature_snapshot_hash_version=old.feature_snapshot_hash_version,
                supersedes_evidence_id=old.evidence_id,
                detected_at=old.detected_at,
                evidence_at=old.evidence_at,
                expires_at=old.expires_at,
                source_type=old.source_type,
                source_identity=old.source_identity,
                source_manifest_id=old.source_manifest_id,
                reference_bid=old.reference_bid,
                reference_ask=old.reference_ask,
                reference_received_at=old.reference_received_at,
                reference_data_status=old.reference_data_status,
                evidence_payload=old.evidence_payload,
                feature_snapshot_payload=old.feature_snapshot_payload,
                created_at=old.created_at,
            )
        )


async def _disabled_g2_caller_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        persisted = await _persist(
            sessions,
            facts,
            _context(),
            quote=_quote(),
            advisory_admission_state="GATE_A_DISABLED",
        )
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            return {
                "persisted": persisted,
                "state": row.advisory_admission_state,
                "rows": await _count(session, EdgeOpportunityEvidenceRecord),
            }


async def _disabled_capture_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as sessions:
        facts = _facts()
        context = _context()
        candidate = _breakout_candidate(facts["candidates"])
        expected = build_opportunity_evidence(
            event=facts["event"],
            timeline=facts["timeline"],
            state=facts["state"],
            transition=facts["transition"],
            candidate=candidate,
            observation=facts["features"],
            context=context,
            reference_quote=_quote(),
        )
        async with sessions() as session, session.begin():
            status = await capture_opportunity(
                session,
                event=facts["event"],
                timeline=facts["timeline"],
                state=facts["state"],
                transition=facts["transition"],
                candidates=facts["candidates"],
                observation=facts["features"],
                context=context,
                reference_quote=_quote(),
                expected_evidence_hash=expected.evidence_hash,
                advisory_admission_state="GATE_A_DISABLED",
            )
        wrong_anchor_rejected = False
        try:
            async with sessions() as session, session.begin():
                await capture_opportunity(
                    session,
                    event=facts["event"],
                    timeline=facts["timeline"],
                    state=facts["state"],
                    transition=facts["transition"],
                    candidates=facts["candidates"],
                    observation=facts["features"],
                    context=context,
                    reference_quote=_quote(),
                    expected_evidence_hash="0" * 64,
                    advisory_admission_state="GATE_A_DISABLED",
                )
        except ValueError:
            wrong_anchor_rejected = True
        async with sessions() as session:
            row = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
            return {
                "status": status,
                "admission_state": row.advisory_admission_state,
                "evidence_id": row.evidence_id,
                "expected_evidence_id": expected.evidence_id,
                "opportunity_id": row.opportunity_id,
                "expected_opportunity_id": expected.opportunity_id,
                "evidence_hash": row.evidence_hash,
                "expected_evidence_hash": expected.evidence_hash,
                "feature_snapshot_hash": row.feature_snapshot_hash,
                "expected_feature_snapshot_hash": expected.feature_snapshot_hash,
                "evidence_payload": row.evidence_payload,
                "expected_evidence_payload": expected.evidence_payload,
                "feature_snapshot_payload": row.feature_snapshot_payload,
                "expected_feature_snapshot_payload": expected.feature_snapshot_payload,
                "wrong_anchor_rejected": wrong_anchor_rejected,
                "evidence_rows": await _count(session, EdgeOpportunityEvidenceRecord),
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
            forward_admission_verifier=authority.verifier(),
        )
        runtime = EventRuntime(repository, worker_count=1)
        await runtime.start()
        try:
            features = _features()
            first_event = _event(event_id="evt-runtime-1", version=0)
            second_event = _event(event_id="evt-runtime-2", version=1)
            first = await runtime.publish(
                first_event, features, forward_admission_proof=_admitted(authority, first_event)
            )
            second = await runtime.publish(
                second_event, features, forward_admission_proof=_admitted(authority, second_event)
            )
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
            forward_admission_verifier=authority.verifier(),
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
                    forward_admission_proof=_admitted(authority, original_facts["event"]),
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
            forward_admission_verifier=authority.verifier(),
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
                    forward_admission_proof=_admitted(authority, facts["event"]),
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
            forward_admission_proof=_admitted(authority, facts["event"]), reference_quote=None,
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
            forward_admission_proof=_admitted(authority, facts["event"]), reference_quote=None,
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
            forward_admission_verifier=authority.verifier(),
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
                    forward_admission_proof=_admitted(authority, original_facts["event"]),
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
            forward_admission_proof=_admitted(authority, later_facts["event"]),
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
            forward_admission_verifier=authority.verifier(),
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
                    forward_admission_proof=_admitted(authority, facts["event"]),
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
    """RRF-01 §12 adversarial: a *later, working* session still refuses an old input.

    Process A opens a live session, freezes no durable anchor (its anchor write
    fails) and exits with nothing committed. Process B then opens a later live
    session with its own session id and its own secret and is handed that same old
    event -- with a real issuing capability, so the refusal has to come from the
    causal session-start fence rather than from a test that withholds a proof.
    Process A's old proof is replayed too, to prove cross-session reuse fails.
    """

    with _capture_database("redelivery_without_anchor") as url:
        observed = asyncio.run(_old_redelivery_scenario(url))

    assert observed == {
        "process_a_proof_issued": True,
        "process_a_anchor_write_failed": True,
        "process_a_anchors": 0,
        "process_a_evidence": 0,
        "process_b_session_started_at": START + timedelta(minutes=5),
        "process_b_issued_for_old_input": False,
        "process_b_issued_for_new_input": True,
        "redelivery_without_proof": "CaptureAdmissionRejected",
        "redelivery_with_replayed_proof": "CaptureAdmissionRejected",
        "anchors": 0,
        "evidence": 0,
    }


async def _old_redelivery_scenario(url: str) -> dict[str, object]:
    old_facts = _facts(event_id="evt-before-anchor-crash")
    fresh_facts = _facts(event_id="evt-after-session-start", at=START + timedelta(minutes=6))
    session_b_start = START + timedelta(minutes=5)
    precondition = SymbolStateRecord(instrument_id=INSTRUMENT, symbol=INSTRUMENT)
    async with _sessions(url) as sessions:
        # --- Process A: live session A issues a proof; its anchor write fails. ---
        process_a = _live_authority(session_id="session-a", session_started_at=START)
        process_a_proof = _admitted(process_a, old_facts["event"])
        repository_a = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(),
            forward_admission_verifier=process_a.verifier(),
        )
        original_record = g2_repository_module.record_bbo_observation

        async def fail_anchor_write(*_args, **_kwargs):
            raise RuntimeError("injected anchor write failure")

        g2_repository_module.record_bbo_observation = fail_anchor_write
        try:
            try:
                await repository_a.persist(
                    old_facts["event"],
                    old_facts["timeline"],
                    old_facts["state"],
                    old_facts["transition"],
                    old_facts["candidates"],
                    old_facts["features"],
                    precondition_state=precondition,
                    forward_admission_proof=process_a_proof,
                )
            except RuntimeError:
                process_a_anchor_write_failed = True
            else:
                process_a_anchor_write_failed = False
        finally:
            g2_repository_module.record_bbo_observation = original_record

        async with sessions() as session:
            process_a_anchors = await _count(session, EdgeOpportunityCaptureAnchorRecord)
            process_a_evidence = await _count(session, EdgeOpportunityEvidenceRecord)

        # --- Process B: a *later* session with a brand-new id and secret. ---
        process_b = _live_authority(
            session_id="session-b", session_started_at=session_b_start
        )
        repository_b = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(
                bid=101.5,
                ask=102.5,
                at=START + timedelta(seconds=10),
                source_event_time=START + timedelta(seconds=10),
                source_sequence=999,
            ),
            forward_admission_verifier=process_b.verifier(),
        )
        rejection = None
        replayed = None
        for proof, label in ((None, "fresh"), (process_a_proof, "replayed")):
            try:
                await repository_b.persist(
                    old_facts["event"],
                    old_facts["timeline"],
                    old_facts["state"],
                    old_facts["transition"],
                    old_facts["candidates"],
                    old_facts["features"],
                    precondition_state=precondition,
                    forward_admission_proof=proof,
                )
            except CaptureAdmissionRejected:
                if label == "fresh":
                    rejection = "CaptureAdmissionRejected"
                else:
                    replayed = "CaptureAdmissionRejected"
            else:
                raise AssertionError(f"old redelivery must be refused ({label} proof)")

        async with sessions() as session:
            return {
                "process_a_proof_issued": process_a_proof is not None,
                "process_a_anchor_write_failed": process_a_anchor_write_failed,
                "process_a_anchors": process_a_anchors,
                "process_a_evidence": process_a_evidence,
                "process_b_session_started_at": session_b_start,
                "process_b_issued_for_old_input": _admitted(process_b, old_facts["event"])
                is not None,
                "process_b_issued_for_new_input": _admitted(process_b, fresh_facts["event"])
                is not None,
                "redelivery_without_proof": rejection,
                "redelivery_with_replayed_proof": replayed,
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
            }


def test_live_session_admits_a_genuinely_new_input_and_binds_its_causal_facts():
    """RRF-01 positive: an input inside the session is admitted with exact bindings."""

    authority = _live_authority(session_id="session-positive")
    event = _facts(event_id="evt-live-positive")["event"]
    proof = _admitted(authority, event)

    assert proof is not None
    assert proof.proof_version == FORWARD_ADMISSION_PROOF_VERSION
    assert proof.session_id == "session-positive"
    assert proof.session_started_at == START
    assert proof.event_id == event.event_id
    assert proof.source_event_time == event.event_time
    assert proof.source_event_digest
    assert proof.source_event_digest != proof.event_digest
    assert authority.verifier().validates(proof, event) is True
    # A proof is bound to the exact event object, not to its identity alone.
    assert (
        authority.verifier().validates(proof, event.model_copy(update={"strength": 0.1}))
        is False
    )


def test_boundary_input_before_session_start_fails_closed():
    """RRF-01 §8: received-now is not enough -- the causal source time decides."""

    authority = _live_authority(
        session_id="session-boundary", session_started_at=START + timedelta(seconds=1)
    )
    event = _facts(event_id="evt-boundary")["event"]  # source time == START

    assert event.event_time < authority.session_started_at
    # Even handed the exact live ingress object, nothing can be minted.
    assert authority.issue(source_event=_live_input(event), event=event) is None
    # A source whose own event time is inside the session is admitted instead.
    later = _facts(event_id="evt-boundary-later", at=START + timedelta(seconds=2))["event"]
    assert authority.issue(source_event=_live_input(later), event=later) is not None


def test_forward_admission_proof_rejects_tampering_of_any_bound_causal_fact():
    """RRF-01 §13 tamper: changing any signed fact invalidates the proof."""

    authority = _live_authority(session_id="session-tamper")
    event = _facts(event_id="evt-proof-tamper")["event"]
    proof = _admitted(authority, event)
    assert proof is not None
    verifier = authority.verifier()
    assert verifier.validates(proof, event) is True

    for field, value in (
        ("proof_version", "se-arch-fix-01-forward-admission-v1"),
        ("session_id", "another-session"),
        ("session_started_at", START - timedelta(minutes=1)),
        ("event_id", "another-event"),
        ("event_digest", "0" * 64),
        ("source_event_digest", "1" * 64),
        ("source_event_time", START - timedelta(minutes=1)),
        ("signature", "f" * 64),
    ):
        tampered = proof.model_copy(update={field: value})
        assert verifier.validates(tampered, event) is False, field

    # A proof belongs to exactly one live session: another session id, another
    # secret, or another session start all fail closed.
    assert (
        _live_authority(session_id="another-session").verifier().validates(proof, event) is False
    )
    assert (
        ForwardAdmissionAuthority(
            clock=ReplayClock(START),
            session_id="session-tamper",
            secret=b"a-different-live-ingress-secret",
        )
        .verifier()
        .validates(proof, event)
        is False
    )


def test_repository_exposes_no_forward_admission_mint_path():
    """RRF-01 §13: the durable repository can verify a proof, never mint one."""

    parameters = inspect.signature(PostgresG2Repository.__init__).parameters
    assert "forward_admission_verifier" in parameters
    assert "forward_admission_proof_for" not in parameters
    assert "forward_admission_authority" not in parameters

    # The verifier the repository holds has no signing API at all.
    assert not hasattr(ForwardAdmissionVerifier, "issue")
    assert not hasattr(ForwardAdmissionVerifier, "admit_live_input")

    source = Path(g2_repository_module.__file__).read_text(encoding="utf-8")
    assert "admit_live_input" not in source
    assert ".issue(" not in source

    # And a proof is required per persist rather than produced by the repository.
    assert "forward_admission_proof" in inspect.signature(
        PostgresG2Repository.persist
    ).parameters


def test_historical_replay_neither_mints_nor_accepts_a_forward_admission_proof():
    """RRF-01 §11: replay is not live Forward ingress."""

    facts = _facts(event_id="evt-replay-separation")
    event = facts["event"]

    # 1. A replay pipeline holds no issuer, so it can mint nothing at all.
    replay_pipeline = ScannerPipeline(
        OpportunityScanner(), EventRuntime(InMemoryG2Repository()), clock=ReplayClock(START)
    )
    assert replay_pipeline.forward_admission_authority is None
    assert replay_pipeline.issue_admission_proof(_live_input(event), event) is None

    # 2. Even a genuine live proof cannot make a replay repository write a Forward
    #    anchor: HISTORICAL_REPLAY never enters the Forward admission path.
    with _capture_database("replay_separation") as url:
        observed = asyncio.run(_replay_separation_scenario(url, facts))

    assert observed == {"persisted": 1, "anchors": 0, "historical_evidence": 1}


async def _replay_separation_scenario(url: str, facts: dict[str, object]) -> dict[str, int]:
    authority = _live_authority(session_id="session-replay-check")
    proof = _admitted(authority, facts["event"])
    assert proof is not None
    async with _sessions(url) as sessions:
        repository = PostgresG2Repository(
            sessions,
            capture=EdgeCaptureContext(
                source_type=EvidenceSource.HISTORICAL_REPLAY,
                source_identity="replay-source",
                source_manifest_id="manifest-replay",
            ),
            reference_quote_for=lambda _instrument_id: _quote(),
            forward_admission_verifier=authority.verifier(),
        )
        persisted = await repository.persist(
            facts["event"],
            facts["timeline"],
            facts["state"],
            facts["transition"],
            facts["candidates"],
            facts["features"],
            precondition_state=SymbolStateRecord(
                instrument_id=INSTRUMENT, symbol=INSTRUMENT
            ),
            forward_admission_proof=proof,
        )
        async with sessions() as session:
            return {
                "persisted": int(persisted.persisted),
                "anchors": await _count(session, EdgeOpportunityCaptureAnchorRecord),
                "historical_evidence": int(
                    await session.scalar(
                        select(func.count())
                        .select_from(EdgeOpportunityEvidenceRecord)
                        .where(
                            EdgeOpportunityEvidenceRecord.source_type
                            == "HISTORICAL_REPLAY"
                        )
                    )
                ),
            }


def test_forward_paper_admission_is_rejected_when_no_proof_is_supplied():
    """RRF-01: with a verifier configured, a missing proof still fails closed."""

    with _capture_database("missing_proof") as url:
        observed = asyncio.run(_missing_proof_scenario(url))

    assert observed == {"rejected": "CaptureAdmissionRejected", "anchors": 0, "evidence": 0}


async def _missing_proof_scenario(url: str) -> dict[str, object]:
    facts = _facts(event_id="evt-missing-proof")
    authority = _live_authority()
    async with _sessions(url) as sessions:
        repository = PostgresG2Repository(
            sessions,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(),
            forward_admission_verifier=authority.verifier(),
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
            rejected = "CaptureAdmissionRejected"
        else:
            rejected = None
        async with sessions() as session:
            return {
                "rejected": rejected,
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
        forward_admission_proof=_admitted(authority, facts["event"]),
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
        forward_admission_proof=_admitted(authority, facts["event"]),
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
        forward_admission_proof=_admitted(authority, facts["event"]),
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
            forward_admission_verifier=authority.verifier(),
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
                    forward_admission_proof=_admitted(authority, first["event"]),
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
                forward_admission_proof=_admitted(authority, second["event"]),
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
