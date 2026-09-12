"""SE-02B attribution linkage acceptance against real disposable PostgreSQL.

Proves part B of SE-02B: the append-only attribution lineage that runs from a
captured opportunity into the already-accepted G3/Risk/Execution economic chain.

Every scenario drives the *real* accepted services (``DecisionService``,
``G3Workflow``, ``persist_trade_plan``, ``PaperExecutionService``) against a real
disposable PostgreSQL database, and then reads the lineage back out of
``edge_attribution_events``. Attribution is asserted to be:

* complete -- the accepted chain records AI -> Plan -> Risk -> Execution -> Economic;
* linked -- every row carries the exact captured ``opportunity_id`` / ``evidence_id``;
* honest -- a refusal keeps its exact authority and reason, an execution validation
  outcome is never mislabelled as a risk refusal, and an OPEN order is never a fill;
* non-authoritative -- no business or economic fact is written by the lineage.

No forward-outcome calculator, no MFE/MAE, no expectancy and no family aggregation
is exercised here: those belong to SE-02C / SE-02D.
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
    AccountRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    EdgeAttributionEventRecord,
    EdgeOpportunityEvidenceRecord,
    ExecutionIntentRecord,
    FillRecord,
    PaperOrderRecord,
    PositionRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.edge.attribution import (
    RISK_AUTHORITY_CAPACITY_POLICY,
    RISK_AUTHORITY_SYSTEM_RISK_GATE,
    AttributionEventType,
    EdgeAttributionRecorder,
    ai_attribution_event_type,
    family_is_selected,
    link_for_opportunity,
)
from marketpulse.edge.capture import EdgeCaptureContext, ReferenceQuote
from marketpulse.edge.models import (
    EdgeFamily,
    EvidenceSource,
    build_opportunity_identity,
)
from marketpulse.g2.models import (
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
from marketpulse.g2.repository import PostgresG2Repository
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.g3.models import (
    AIAnalysis,
    BestBidAsk,
    DecisionStatus,
    Direction,
    ExecutionIntent,
    IntentStatus,
    OrderStatus,
    OrderType,
    PriceZone,
    RunMode,
)
from marketpulse.g3.provider import DeterministicFakeAIProvider
from marketpulse.g3.service import (
    DecisionService,
    DecisionSnapshotBuilder,
    G3Workflow,
    PaperExecutionService,
    TradePlanManager,
    persist_trade_plan,
    stable_id,
)
from marketpulse.market_data.models import MarketType
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

NOW = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
T0 = NOW
T1 = NOW + timedelta(seconds=1)
T2 = NOW + timedelta(seconds=2)
T3 = NOW + timedelta(seconds=3)
INSTRUMENT = "SOL-USDT"
FAMILY = "BREAKOUT_RETEST"
STATE_VERSION = 1
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
def _attribution_database(label: str):
    name = f"marketpulse_se02b_attr_{label}_{uuid4().hex[:12]}"
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


async def _attribution_rows(factory) -> list[EdgeAttributionEventRecord]:
    async with factory() as session:
        return list(
            (
                await session.scalars(
                    select(EdgeAttributionEventRecord).order_by(
                        EdgeAttributionEventRecord.occurred_at,
                        EdgeAttributionEventRecord.event_type,
                        EdgeAttributionEventRecord.attribution_event_id,
                    )
                )
            ).all()
        )


async def _event_summary(factory) -> list[dict[str, object]]:
    return [
        {
            "event_type": row.event_type,
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "opportunity_id": row.opportunity_id,
            "evidence_id": row.evidence_id,
            "occurred_at": row.occurred_at,
            "payload": dict(row.payload),
        }
        for row in await _attribution_rows(factory)
    ]


async def _business_counts(session) -> dict[str, int]:
    """Durable G3 business facts that attribution must never rewrite."""

    return {
        "accounts": await _count(session, AccountRecord),
        "decisions": await _count(session, AIDecisionRecord),
        "snapshots": await _count(session, DecisionSnapshotRecord),
        "plans": await _count(session, TradePlanRecord),
        "intents": await _count(session, ExecutionIntentRecord),
        "orders": await _count(session, PaperOrderRecord),
        "fills": await _count(session, FillRecord),
        "positions": await _count(session, PositionRecord),
        "trades": await _count(session, TradeRecord),
    }


# --- captured opportunity ---------------------------------------------------------------


def _features(*, at: datetime = NOW) -> FeatureSnapshot:
    structure = MarketStructure(
        recent_swing_high=101.0,
        recent_swing_low=95.0,
        breakout_level=100.0,
        retest_area=Zone(lower=99.0, upper=100.0, kind="retest", observed_at=at),
    )
    return FeatureSnapshot(
        instrument_id=INSTRUMENT,
        symbol=INSTRUMENT,
        market_type=MarketType.SPOT,
        event_time=at,
        current_price=100.5,
        short_return=0.02,
        buy_sell_imbalance=0.7,
        spread=0.5,
        structure=structure,
    )


def _event(*, event_id: str = "evt-attr-1", at: datetime = NOW, version: int = 0) -> MarketEvent:
    return MarketEvent(
        event_id=event_id,
        symbol=INSTRUMENT,
        instrument_id=INSTRUMENT,
        market_type=MarketType.SPOT,
        event_type=EventType.BREAKOUT,
        event_time=at,
        received_time=at,
        source="fixture",
        strength=0.9,
        priority=80,
        state_version=version,
        config_version="g2-v1",
        payload={"current_price": 100.5},
    )


def _state(*, at: datetime = NOW, version: int = STATE_VERSION) -> SymbolStateRecord:
    return SymbolStateRecord(
        instrument_id=INSTRUMENT,
        symbol=INSTRUMENT,
        state=SymbolState.SETUP,
        state_version=version,
        last_event_time=at,
        watch_expires_at=at + timedelta(minutes=20),
    )


def _transition(*, event: MarketEvent, state: SymbolStateRecord) -> StateTransition:
    return StateTransition(
        transition_id=deterministic_id("st", event.event_id, state.state_version, "applied"),
        instrument_id=INSTRUMENT,
        symbol=INSTRUMENT,
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
        symbol=INSTRUMENT,
        instrument_id=INSTRUMENT,
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
    features: FeatureSnapshot, event: MarketEvent, state_version: int
) -> list[StrategyCandidate]:
    return StrategyEngine(clock=ReplayClock(event.received_time)).candidates(
        features, event, state_version
    )


def _breakout(candidates: list[StrategyCandidate]) -> StrategyCandidate:
    return next(item for item in candidates if item.strategy_id == FAMILY)


async def _captured_opportunity(factory):
    """Persist one real qualifying G2 SETUP and return the captured Edge facts."""

    event = _event()
    features = _features()
    state = _state()
    transition = _transition(event=event, state=state)
    timeline = _timeline(event=event, state=state)
    candidates = _candidates(features, event, state.state_version)
    context = EdgeCaptureContext(
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-se02b",
        reference_quote=ReferenceQuote(bid=99.5, ask=100.5, received_at=NOW),
    )
    repository = PostgresG2Repository(factory, capture=context)
    await repository.persist(event, timeline, state, transition, candidates, features)
    candidate = _breakout(candidates)
    async with factory() as session:
        evidence = (await session.scalars(select(EdgeOpportunityEvidenceRecord))).one()
    opportunity = build_opportunity_identity(
        family_id=EdgeFamily.BREAKOUT_RETEST,
        family_version=candidate.strategy_version,
        instrument_id=INSTRUMENT,
        market_type=MarketType.SPOT,
        candidate_id=candidate.candidate_id,
    )
    return opportunity, candidate, evidence


# --- G3 helpers -------------------------------------------------------------------------


def _analysis(
    direction: Direction = Direction.LONG_BIAS,
    *,
    zone: PriceZone | None = None,
    stop: float = 90.0,
    take_profit: float = 120.0,
    selected: tuple[str, ...] = (FAMILY,),
) -> AIAnalysis:
    zone = zone or PriceZone(lower=99.0, upper=101.0)
    if direction is Direction.LONG_BIAS:
        return AIAnalysis(
            direction=direction,
            trends={"5m": "UP", "15m": "UP", "1H": "UP", "4H": "UP", "1D": "UP"},
            entry_zone=zone,
            stop_loss=stop,
            take_profit=take_profit,
            invalidation="breaks the stop",
            main_plan="buy the confirmed retest",
            confidence=0.8,
            suggested_position_pct=0.15,
            reason="fixture",
            selected_strategy_ids=list(selected),
        )
    return AIAnalysis(
        direction=direction,
        trends={"5m": "UP", "15m": "UP", "1H": "UP", "4H": "UP", "1D": "UP"},
        confidence=0.8,
        suggested_position_pct=0.0,
        reason="fixture",
        selected_strategy_ids=list(selected),
    )


def _snapshot(*, candidates: list[StrategyCandidate], state_version: int = STATE_VERSION):
    state = _state(version=state_version)
    features = _features()
    bbo = BestBidAsk(instrument_id=INSTRUMENT, bid=99.5, ask=100.5, received_at=NOW)
    return DecisionSnapshotBuilder().build(
        run_mode=RunMode.REPLAY,
        state=state,
        features=features,
        bbo=bbo,
        candidates=candidates,
        timeline=[{"event_id": "evt-attr-1"}],
        config_version="g2-v1",
        trading_context={"current_position": None, "open_orders": []},
        now=NOW,
    )


class _FailingProvider:
    """Test-only provider whose every call fails; no AI result is ever produced."""

    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, snapshot, prompt):  # protocol shape
        self.calls += 1
        raise RuntimeError("provider_unavailable")


class _RefusingRiskGate:
    """Test-only G4-shaped gate that refuses every risk-increasing action."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.calls = 0

    async def evaluate(
        self, session, *, run_mode, instrument_id, side, plan_id, now
    ):
        self.calls += 1
        return self.reason


def _execution_service(
    factory,
    *,
    bbo_at: datetime = T2,
    risk_gate=None,
    initial_balance: float = 1000.0,
) -> PaperExecutionService:
    bbo = BestBidAsk(instrument_id=INSTRUMENT, bid=99.5, ask=100.5, received_at=bbo_at)
    return PaperExecutionService(
        factory,
        lambda _: asyncio.sleep(0, result=bbo),
        lambda _: asyncio.sleep(0, result=STATE_VERSION),
        initial_balance=initial_balance,
        risk_gate=risk_gate,
        clock=ReplayClock(bbo_at),
    )


async def _accepted_plan(
    factory,
    *,
    recorder: EdgeAttributionRecorder,
    candidate: StrategyCandidate,
    order_type: OrderType = OrderType.MARKET,
    zone: PriceZone | None = None,
    stop: float = 90.0,
    take_profit: float = 120.0,
    notional: float = 100.0,
    decision_at: datetime = T0,
    plan_at: datetime = T1,
):
    """Run the real accepted decision + plan persistence for one LONG plan.

    The decision and the plan use distinct clocks so the AI fact and the plan fact
    are genuinely staged in time rather than sharing one timestamp.
    """

    zone = zone or PriceZone(lower=99.0, upper=101.0)
    snapshot = _snapshot(candidates=[candidate])
    service = DecisionService(
        factory,
        DeterministicFakeAIProvider(
            _analysis(Direction.LONG_BIAS, zone=zone, stop=stop, take_profit=take_profit)
        ),
        model="fake-model",
        clock=ReplayClock(decision_at),
    )
    decision_id, status, analysis = await service.decide(
        snapshot, lambda _: asyncio.sleep(0, result=STATE_VERSION), attribution=recorder
    )
    assert status is DecisionStatus.VALID and analysis is not None
    plan = TradePlanManager(clock=ReplayClock(plan_at)).from_analysis(
        decision_id=decision_id,
        snapshot=snapshot,
        analysis=analysis,
        current_equity=1000.0,
    )
    assert plan is not None
    plan = plan.model_copy(
        update={
            "order_type": order_type,
            "entry_zone": zone,
            "stop_loss": stop,
            "take_profit": take_profit,
            "intended_notional": notional,
        }
    )
    await persist_trade_plan(factory, plan, attribution=recorder)
    return snapshot, decision_id, plan


def _intent(plan, *, intent_id: str, created_at: datetime = T2) -> ExecutionIntent:
    return ExecutionIntent(
        intent_id=intent_id,
        plan_id=plan.plan_id,
        instrument_id=INSTRUMENT,
        run_mode=RunMode.REPLAY,
        state_version=STATE_VERSION,
        created_at=created_at,
    )


def _by_type(events: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["event_type"]): item for item in events}


# --- A. accepted lineage ----------------------------------------------------------------


def test_accepted_ai_through_fill_links_the_whole_lineage_to_one_opportunity():
    with _attribution_database("lineage") as url:
        observed = asyncio.run(_lineage_scenario(url))

    assert observed["status"] == "VALID"
    assert observed["result_status"] == IntentStatus.EXECUTED.value
    assert sorted(observed["event_types"]) == sorted(
        [
            AttributionEventType.AI_ACCEPTED_LONG.value,
            AttributionEventType.PLAN_CREATED.value,
            AttributionEventType.RISK_ACCEPTED.value,
            AttributionEventType.BUY_FILLED.value,
            AttributionEventType.TRADE_OPEN.value,
        ]
    )
    assert observed["subject_types"] == {
        AttributionEventType.AI_ACCEPTED_LONG.value: "AI",
        AttributionEventType.PLAN_CREATED.value: "PLAN",
        AttributionEventType.RISK_ACCEPTED.value: "RISK",
        AttributionEventType.BUY_FILLED.value: "EXECUTION",
        AttributionEventType.TRADE_OPEN.value: "ECONOMIC_RESULT",
    }
    # Every lineage row points at the one captured opportunity and its stored revision.
    assert observed["link_matches_stored_evidence"] is True
    assert observed["all_linked"] is True
    assert observed["candidate_is_the_captured_one"] is True
    # AI -> Plan -> Execution are causally staged. Within one execution stage every
    # fact shares the one occurrence timestamp the settlement used, and the database
    # defines no order among equal timestamps, so the stage is what is asserted -- a
    # tie-break on the event name would be an accident, not evidence.
    assert observed["occurred_at"] == {
        AttributionEventType.AI_ACCEPTED_LONG.value: T0,
        AttributionEventType.PLAN_CREATED.value: T1,
        AttributionEventType.RISK_ACCEPTED.value: T2,
        AttributionEventType.BUY_FILLED.value: T2,
        AttributionEventType.TRADE_OPEN.value: T2,
    }
    # The sample (opportunity evidence) survives the whole economic chain.
    assert observed["evidence_rows"] == 1
    # Each lineage row names the exact business subject it descends from.
    assert observed["subject_ids"] == {
        "AI": observed["decision_id"],
        "PLAN": observed["plan_id"],
        "RISK": observed["intent_id"],
        "EXECUTION": observed["fill_id"],
        "ECONOMIC_RESULT": observed["trade_id"],
    }
    # No refusal or no-plan fact exists on the accepted path.
    assert not observed["rejection_events"]


async def _lineage_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, evidence = await _captured_opportunity(factory)
        link = link_for_opportunity(opportunity)
        recorder = EdgeAttributionRecorder(link, clock=ReplayClock(T0))
        snapshot = _snapshot(candidates=[candidate])
        workflow = G3Workflow(
            DecisionService(
                factory,
                DeterministicFakeAIProvider(_analysis(Direction.LONG_BIAS)),
                model="fake-model",
                clock=ReplayClock(T0),
            ),
            TradePlanManager(clock=ReplayClock(T1)),
            factory,
        )
        status, plan = await workflow.process_setup(
            snapshot,
            lambda _: asyncio.sleep(0, result=STATE_VERSION),
            1000.0,
            attribution=recorder,
        )
        assert plan is not None
        service = _execution_service(factory)
        await service.bootstrap_account(RunMode.REPLAY)
        intent = _intent(plan, intent_id="intent-lineage")
        result = await service.execute(intent, plan, T2, attribution=recorder)
        events = await _event_summary(factory)
        async with factory() as session:
            evidence_rows = await _count(session, EdgeOpportunityEvidenceRecord)
            trade = (
                await session.scalars(
                    select(TradeRecord).where(TradeRecord.run_mode == RunMode.REPLAY)
                )
            ).one()
        return {
            "status": status.value,
            "result_status": result.status.value,
            "event_types": [str(item["event_type"]) for item in events],
            "subject_types": {
                str(item["event_type"]): str(item["subject_type"]) for item in events
            },
            "subject_ids": {
                str(item["subject_type"]): item["subject_id"] for item in events
            },
            "link_matches_stored_evidence": link.evidence_id == evidence.evidence_id,
            "all_linked": all(
                item["opportunity_id"] == opportunity.opportunity_id
                and item["evidence_id"] == link.evidence_id
                for item in events
            ),
            "candidate_is_the_captured_one": any(
                item.candidate_id == candidate.candidate_id for item in snapshot.strategies
            ),
            "occurred_at": {
                str(item["event_type"]): item["occurred_at"] for item in events
            },
            "evidence_rows": evidence_rows,
            "decision_id": plan.decision_id,
            "plan_id": plan.plan_id,
            "fill_id": result.fill_id,
            "trade_id": trade.trade_id,
            "intent_id": intent.intent_id,
            "rejection_events": [
                str(item["event_type"])
                for item in events
                if str(item["event_type"])
                in {
                    AttributionEventType.RISK_REJECTED.value,
                    AttributionEventType.EXECUTION_REJECTED.value,
                    AttributionEventType.PLAN_NOT_CREATED.value,
                }
            ],
        }


# --- B. rejections keep the sample ------------------------------------------------------


def test_wait_direction_records_the_ai_reject_and_no_plan_but_keeps_the_sample():
    with _attribution_database("wait") as url:
        observed = asyncio.run(_rejected_scenario(url, direction=Direction.WAIT))

    assert observed["status"] == "VALID"
    assert observed["plan"] is None
    assert sorted(observed["event_types"]) == sorted(
        [
            AttributionEventType.AI_REJECTED_WAIT.value,
            AttributionEventType.PLAN_NOT_CREATED.value,
        ]
    )
    assert set(observed["occurred_at"].values()) == {T0}
    assert observed["no_plan_reason"] == "no_long_plan"
    assert observed["all_linked"] is True
    assert observed["evidence_rows"] == 1  # the sample is never deleted
    assert observed["plans"] == 0
    assert observed["fills"] == 0


def test_provider_failure_records_the_provider_error_and_no_plan_but_keeps_the_sample():
    with _attribution_database("provider") as url:
        observed = asyncio.run(_rejected_scenario(url, provider=_FailingProvider()))

    assert observed["status"] == "INVALID_SCHEMA"
    assert observed["plan"] is None
    assert sorted(observed["event_types"]) == sorted(
        [
            AttributionEventType.AI_PROVIDER_ERROR.value,
            AttributionEventType.PLAN_NOT_CREATED.value,
        ]
    )
    assert set(observed["occurred_at"].values()) == {T0}
    assert observed["no_plan_reason"] == "INVALID_SCHEMA"
    assert observed["all_linked"] is True
    assert observed["evidence_rows"] == 1
    assert observed["plans"] == 0
    assert observed["fills"] == 0


async def _rejected_scenario(url: str, *, direction=None, provider=None) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        link = link_for_opportunity(opportunity)
        recorder = EdgeAttributionRecorder(link, clock=ReplayClock(T0))
        snapshot = _snapshot(candidates=[candidate])
        if provider is None:
            provider = DeterministicFakeAIProvider(_analysis(direction))
        workflow = G3Workflow(
            DecisionService(factory, provider, model="fake-model", clock=ReplayClock(T0)),
            TradePlanManager(clock=ReplayClock(T1)),
            factory,
        )
        status, plan = await workflow.process_setup(
            snapshot,
            lambda _: asyncio.sleep(0, result=STATE_VERSION),
            1000.0,
            attribution=recorder,
        )
        events = await _event_summary(factory)
        async with factory() as session:
            counts = {
                "evidence": await _count(session, EdgeOpportunityEvidenceRecord),
                "plans": await _count(session, TradePlanRecord),
                "fills": await _count(session, FillRecord),
            }
        by_type = _by_type(events)
        return {
            "status": status.value,
            "plan": plan,
            "event_types": [str(item["event_type"]) for item in events],
            "occurred_at": {str(item["event_type"]): item["occurred_at"] for item in events},
            "no_plan_reason": (
                by_type[AttributionEventType.PLAN_NOT_CREATED.value]["payload"].get("reason")
                if AttributionEventType.PLAN_NOT_CREATED.value in by_type
                else None
            ),
            "all_linked": all(
                item["opportunity_id"] == opportunity.opportunity_id
                and item["evidence_id"] == link.evidence_id
                for item in events
            ),
            "evidence_rows": counts["evidence"],
            "plans": counts["plans"],
            "fills": counts["fills"],
        }


# --- C. risk refusals keep their exact authority ----------------------------------------


def test_authoritative_gate_refusal_keeps_its_exact_authority_and_reason():
    with _attribution_database("gate") as url:
        observed = asyncio.run(_risk_refusal_scenario(url, authority="gate"))

    assert observed["result_status"] == IntentStatus.REJECTED.value
    assert observed["result_reason"] == "SYSTEM_RISK_GATE_TEST_REFUSAL"
    assert observed["event_types"] == [
        AttributionEventType.AI_ACCEPTED_LONG.value,
        AttributionEventType.PLAN_CREATED.value,
        AttributionEventType.RISK_REJECTED.value,
    ]
    assert observed["risk"]["subject_type"] == "RISK"
    assert observed["risk"]["payload"]["authority"] == RISK_AUTHORITY_SYSTEM_RISK_GATE
    assert observed["risk"]["payload"]["reason"] == "SYSTEM_RISK_GATE_TEST_REFUSAL"
    assert observed["risk"]["payload"]["plan_id"] == observed["plan_id"]
    # A risk refusal must never be recorded as an execution rejection.
    assert AttributionEventType.EXECUTION_REJECTED.value not in observed["event_types"]
    assert observed["orders"] == 0 and observed["fills"] == 0


def test_capacity_policy_refusal_keeps_its_own_distinct_authority():
    with _attribution_database("capacity") as url:
        observed = asyncio.run(_risk_refusal_scenario(url, authority="capacity"))

    assert observed["result_status"] == IntentStatus.REJECTED.value
    assert observed["result_reason"] == "CAPACITY_BLOCKED"
    assert observed["event_types"] == [
        AttributionEventType.AI_ACCEPTED_LONG.value,
        AttributionEventType.PLAN_CREATED.value,
        AttributionEventType.RISK_REJECTED.value,
    ]
    assert observed["risk"]["payload"]["authority"] == RISK_AUTHORITY_CAPACITY_POLICY
    assert observed["risk"]["payload"]["reason"] == "CAPACITY_BLOCKED"
    # The two risk authorities are never collapsed into one generic rejection.
    assert observed["risk"]["payload"]["authority"] != RISK_AUTHORITY_SYSTEM_RISK_GATE
    assert AttributionEventType.EXECUTION_REJECTED.value not in observed["event_types"]
    assert observed["orders"] == 0 and observed["fills"] == 0


async def _risk_refusal_scenario(url: str, *, authority: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        recorder = EdgeAttributionRecorder(link_for_opportunity(opportunity), clock=ReplayClock(T0))
        _, _, plan = await _accepted_plan(factory, recorder=recorder, candidate=candidate)
        if authority == "gate":
            gate = _RefusingRiskGate("SYSTEM_RISK_GATE_TEST_REFUSAL")
            service = _execution_service(factory, risk_gate=gate)
        else:
            service = _execution_service(factory, initial_balance=10.0)
        await service.bootstrap_account(RunMode.REPLAY)
        intent = _intent(plan, intent_id=f"intent-{authority}")
        result = await service.execute(intent, plan, T2, attribution=recorder)
        events = await _event_summary(factory)
        by_type = _by_type(events)
        async with factory() as session:
            orders = await _count(session, PaperOrderRecord)
            fills = await _count(session, FillRecord)
        return {
            "result_status": result.status.value,
            "result_reason": result.reason,
            "event_types": [str(item["event_type"]) for item in events],
            "risk": by_type.get(AttributionEventType.RISK_REJECTED.value),
            "plan_id": plan.plan_id,
            "orders": orders,
            "fills": fills,
        }


# --- D. execution validation is never a risk refusal ------------------------------------


def test_expired_plan_is_recorded_as_an_execution_rejection_not_a_risk_refusal():
    with _attribution_database("expired") as url:
        observed = asyncio.run(
            _execution_refusal_scenario(url, now=T2 + timedelta(minutes=10))
        )

    assert observed["result_reason"] == "plan_not_active_or_expired"
    assert observed["event_types"] == [
        AttributionEventType.AI_ACCEPTED_LONG.value,
        AttributionEventType.PLAN_CREATED.value,
        AttributionEventType.EXECUTION_REJECTED.value,
    ]
    assert observed["execution"]["subject_type"] == "EXECUTION"
    assert observed["execution"]["payload"]["reason"] == "plan_not_active_or_expired"
    # An execution validation outcome is never mislabelled as a risk refusal.
    assert AttributionEventType.RISK_REJECTED.value not in observed["event_types"]
    assert observed["orders"] == 0 and observed["fills"] == 0


def test_price_outside_the_entry_zone_is_recorded_as_an_execution_rejection():
    with _attribution_database("zone") as url:
        observed = asyncio.run(
            _execution_refusal_scenario(
                url, now=T2, zone=PriceZone(lower=90.0, upper=95.0)
            )
        )

    assert observed["result_reason"] == "price_outside_entry_zone"
    assert observed["event_types"] == [
        AttributionEventType.AI_ACCEPTED_LONG.value,
        AttributionEventType.PLAN_CREATED.value,
        AttributionEventType.EXECUTION_REJECTED.value,
    ]
    assert observed["execution"]["payload"]["reason"] == "price_outside_entry_zone"
    assert AttributionEventType.RISK_REJECTED.value not in observed["event_types"]
    assert observed["orders"] == 0 and observed["fills"] == 0


async def _execution_refusal_scenario(
    url: str, *, now: datetime, zone: PriceZone | None = None
) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        recorder = EdgeAttributionRecorder(link_for_opportunity(opportunity), clock=ReplayClock(T0))
        _, _, plan = await _accepted_plan(
            factory,
            recorder=recorder,
            candidate=candidate,
            zone=zone,
            # A LONG plan must satisfy stop < zone.lower <= zone.upper < take_profit.
            stop=85.0 if zone is not None else 90.0,
        )
        service = _execution_service(factory)
        await service.bootstrap_account(RunMode.REPLAY)
        intent = _intent(plan, intent_id="intent-execution-rejection")
        result = await service.execute(intent, plan, now, attribution=recorder)
        events = await _event_summary(factory)
        by_type = _by_type(events)
        async with factory() as session:
            orders = await _count(session, PaperOrderRecord)
            fills = await _count(session, FillRecord)
        return {
            "result_reason": result.reason,
            "event_types": [str(item["event_type"]) for item in events],
            "execution": by_type.get(AttributionEventType.EXECUTION_REJECTED.value),
            "orders": orders,
            "fills": fills,
        }


# --- E. an OPEN order is never a fill ---------------------------------------------------


def test_limit_buy_records_an_open_order_and_never_claims_a_fill():
    with _attribution_database("openorder") as url:
        observed = asyncio.run(_limit_order_scenario(url))

    assert observed["result_status"] == IntentStatus.EXECUTED.value
    assert sorted(observed["event_types"]) == sorted(
        [
            AttributionEventType.AI_ACCEPTED_LONG.value,
            AttributionEventType.PLAN_CREATED.value,
            AttributionEventType.RISK_ACCEPTED.value,
            AttributionEventType.ORDER_OPEN.value,
        ]
    )
    assert observed["occurred_at"] == {
        AttributionEventType.AI_ACCEPTED_LONG.value: T0,
        AttributionEventType.PLAN_CREATED.value: T1,
        AttributionEventType.RISK_ACCEPTED.value: T2,
        AttributionEventType.ORDER_OPEN.value: T2,
    }
    assert observed["order_status"] == OrderStatus.OPEN.value
    # Admission plus an OPEN order is not evidence that trading happened.
    assert AttributionEventType.BUY_FILLED.value not in observed["event_types"]
    assert AttributionEventType.TRADE_OPEN.value not in observed["event_types"]
    assert observed["fills"] == 0
    assert observed["trades"] == 0
    assert observed["order_open"]["payload"]["order_id"] == observed["order_id"]


async def _limit_order_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        recorder = EdgeAttributionRecorder(link_for_opportunity(opportunity), clock=ReplayClock(T0))
        _, _, plan = await _accepted_plan(
            factory, recorder=recorder, candidate=candidate, order_type=OrderType.LIMIT
        )
        service = _execution_service(factory)
        await service.bootstrap_account(RunMode.REPLAY)
        intent = _intent(plan, intent_id="intent-limit-open")
        result = await service.execute(intent, plan, T2, attribution=recorder)
        events = await _event_summary(factory)
        by_type = _by_type(events)
        async with factory() as session:
            order = await session.get(PaperOrderRecord, result.order_id)
            fills = await _count(session, FillRecord)
            trades = await _count(session, TradeRecord)
        return {
            "result_status": result.status.value,
            "event_types": [str(item["event_type"]) for item in events],
            "occurred_at": {str(item["event_type"]): item["occurred_at"] for item in events},
            "order_status": order.status,
            "order_id": result.order_id,
            "order_open": by_type.get(AttributionEventType.ORDER_OPEN.value),
            "fills": fills,
            "trades": trades,
        }


# --- F. economic result linkage ---------------------------------------------------------


def test_closed_trade_records_the_actual_economic_result_linkage():
    with _attribution_database("economic") as url:
        observed = asyncio.run(_economic_scenario(url))

    assert observed["buy_status"] == IntentStatus.EXECUTED.value
    assert observed["exit_status"] == IntentStatus.EXECUTED.value
    assert sorted(observed["event_types"]) == sorted(
        [
            AttributionEventType.AI_ACCEPTED_LONG.value,
            AttributionEventType.PLAN_CREATED.value,
            AttributionEventType.RISK_ACCEPTED.value,
            AttributionEventType.BUY_FILLED.value,
            AttributionEventType.TRADE_OPEN.value,
            AttributionEventType.TRADE_CLOSED.value,
            AttributionEventType.ACTUAL_ECONOMIC_RESULT_AVAILABLE.value,
        ]
    )
    # The closing fill happens at T3, strictly after the opening fill at T2.
    assert observed["occurred_at"] == {
        AttributionEventType.AI_ACCEPTED_LONG.value: T0,
        AttributionEventType.PLAN_CREATED.value: T1,
        AttributionEventType.RISK_ACCEPTED.value: T2,
        AttributionEventType.BUY_FILLED.value: T2,
        AttributionEventType.TRADE_OPEN.value: T2,
        AttributionEventType.TRADE_CLOSED.value: T3,
        AttributionEventType.ACTUAL_ECONOMIC_RESULT_AVAILABLE.value: T3,
    }
    assert observed["trade_is_closed"] is True
    # The economic result is observed from the settlement that produced it.
    assert observed["economic"]["subject_type"] == "ECONOMIC_RESULT"
    assert observed["economic"]["payload"]["ledger_entry_id"] == observed["ledger_entry_id"]
    assert observed["economic"]["payload"]["exit_reason"] == "MANUAL_CLOSE"
    assert observed["economic"]["payload"]["realized_pnl"] == pytest.approx(
        observed["position_realized_pnl"]
    )
    assert observed["position_quantity"] == 0
    assert observed["all_linked"] is True
    assert observed["evidence_rows"] == 1


async def _economic_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        link = link_for_opportunity(opportunity)
        recorder = EdgeAttributionRecorder(link, clock=ReplayClock(T0))
        _, _, plan = await _accepted_plan(factory, recorder=recorder, candidate=candidate)
        service = _execution_service(factory)
        await service.bootstrap_account(RunMode.REPLAY)
        intent = _intent(plan, intent_id="intent-economic-buy")
        buy = await service.execute(intent, plan, T2, attribution=recorder)
        async with factory() as session:
            position = await session.scalar(
                select(PositionRecord).where(PositionRecord.instrument_id == INSTRUMENT)
            )
        assert position is not None and position.quantity > 0
        exit_result = await service.execute_risk_reducing_exit(
            intent_id="intent-economic-exit",
            plan_id=plan.plan_id,
            instrument_id=INSTRUMENT,
            run_mode=RunMode.REPLAY,
            quantity=position.quantity,
            exit_reason="MANUAL_CLOSE",
            now=T3,
            attribution=recorder,
        )
        events = await _event_summary(factory)
        by_type = _by_type(events)
        async with factory() as session:
            position_after = await session.scalar(
                select(PositionRecord).where(PositionRecord.instrument_id == INSTRUMENT)
            )
            trade = (
                await session.scalars(select(TradeRecord).where(TradeRecord.status == "CLOSED"))
            ).one()
            evidence_rows = await _count(session, EdgeOpportunityEvidenceRecord)
            exit_fill_id = await session.scalar(
                select(FillRecord.fill_id).where(FillRecord.intent_id == "intent-economic-exit")
            )
        # The accounting path addresses its ledger row as stable_id("ledger", fill_id).
        ledger_entry_id = stable_id("ledger", exit_fill_id)
        return {
            "buy_status": buy.status.value,
            "exit_status": exit_result.status.value,
            "event_types": [str(item["event_type"]) for item in events],
            "occurred_at": {str(item["event_type"]): item["occurred_at"] for item in events},
            "trade_is_closed": trade.closed_at is not None,
            "economic": by_type.get(
                AttributionEventType.ACTUAL_ECONOMIC_RESULT_AVAILABLE.value
            ),
            "ledger_entry_id": ledger_entry_id,
            "position_realized_pnl": position_after.realized_pnl,
            "position_quantity": position_after.quantity,
            "all_linked": all(
                item["opportunity_id"] == opportunity.opportunity_id
                and item["evidence_id"] == link.evidence_id
                for item in events
            ),
            "evidence_rows": evidence_rows,
        }


# --- G. append-only idempotency and non-authority ---------------------------------------


def test_re_emitting_lineage_is_idempotent_and_never_rewrites_business_state():
    with _attribution_database("idempotent") as url:
        observed = asyncio.run(_idempotency_scenario(url))

    # Re-observing an already-recorded lineage fact must not duplicate it.
    assert observed["replayed_status"] == "IDEMPOTENT"
    # A brand new fact is inserted once and then stays idempotent.
    assert observed["fresh_statuses"] == ["INSERTED", "IDEMPOTENT"]
    assert observed["plan_created_rows"] == 1
    assert observed["total_row_count"] == 3  # AI, PLAN_CREATED, ORDER_OPEN
    # The business chain really exists, and re-emitting lineage rewrote none of it.
    assert observed["business_before"]["plans"] == 1
    assert observed["business_before"]["decisions"] == 1
    assert observed["business_after"] == observed["business_before"]


async def _idempotency_scenario(url: str) -> dict[str, object]:
    async with _sessions(url) as factory:
        opportunity, candidate, _ = await _captured_opportunity(factory)
        recorder = EdgeAttributionRecorder(
            link_for_opportunity(opportunity), clock=ReplayClock(T0)
        )
        snapshot, decision_id, plan = await _accepted_plan(
            factory, recorder=recorder, candidate=candidate
        )
        async with factory() as session:
            before = await _business_counts(session)
        # The exact same plan-created fact, observed a second time.
        async with factory() as session, session.begin():
            replayed = await recorder.record_plan_created(
                session,
                plan_id=plan.plan_id,
                decision_id=decision_id,
                snapshot_id=snapshot.snapshot_id,
                occurred_at=plan.created_at,
            )
        fresh = []
        for _ in range(2):
            async with factory() as session, session.begin():
                fresh.append(
                    await recorder.record_order_open(
                        session,
                        order_id="order-idempotent",
                        intent_id="intent-idempotent",
                        plan_id=plan.plan_id,
                        quantity=1.0,
                        limit_price=99.0,
                        occurred_at=T2,
                    )
                )
        async with factory() as session:
            after = await _business_counts(session)
        events = await _event_summary(factory)
        return {
            "replayed_status": replayed,
            "fresh_statuses": fresh,
            "plan_created_rows": sum(
                1
                for item in events
                if item["event_type"] == AttributionEventType.PLAN_CREATED.value
            ),
            "total_row_count": len(events),
            "business_before": before,
            "business_after": after,
        }


# --- H. frozen AI vocabulary (no database needed) ---------------------------------------


@pytest.mark.parametrize(
    ("status", "direction", "provider_error", "applies_to_family", "expected"),
    [
        (None, None, False, True, AttributionEventType.AI_NOT_REACHED),
        (
            DecisionStatus.STALE_DECISION,
            Direction.LONG_BIAS,
            False,
            True,
            AttributionEventType.AI_STALE,
        ),
        (
            DecisionStatus.INVALID_SCHEMA,
            None,
            True,
            True,
            AttributionEventType.AI_PROVIDER_ERROR,
        ),
        (
            DecisionStatus.INVALID_SCHEMA,
            None,
            False,
            True,
            AttributionEventType.AI_INVALID,
        ),
        (
            DecisionStatus.INVALID_BUSINESS,
            Direction.LONG_BIAS,
            False,
            True,
            AttributionEventType.AI_INVALID,
        ),
        (
            DecisionStatus.VALID,
            Direction.SHORT_BIAS,
            False,
            True,
            AttributionEventType.AI_REJECTED_SHORT_ANALYSIS_ONLY,
        ),
        (
            DecisionStatus.VALID,
            Direction.LONG_BIAS,
            False,
            False,
            AttributionEventType.AI_NOT_SELECTED_THIS_FAMILY,
        ),
        (
            DecisionStatus.VALID,
            Direction.LONG_BIAS,
            False,
            True,
            AttributionEventType.AI_ACCEPTED_LONG,
        ),
        (
            DecisionStatus.VALID,
            Direction.WAIT,
            False,
            True,
            AttributionEventType.AI_REJECTED_WAIT,
        ),
        (DecisionStatus.RECEIVED, None, False, True, AttributionEventType.AI_INVALID),
        (
            DecisionStatus.CAPACITY_BLOCKED,
            Direction.LONG_BIAS,
            False,
            True,
            AttributionEventType.AI_INVALID,
        ),
    ],
)
def test_ai_attribution_vocabulary_matrix(
    status, direction, provider_error, applies_to_family, expected
):
    assert (
        ai_attribution_event_type(
            status=status,
            direction=direction,
            provider_error=provider_error,
            applies_to_family=applies_to_family,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("selected", "snapshot", "expected"),
    [
        ([FAMILY], [], True),
        ([], [FAMILY], True),
        (["TREND_PULLBACK"], [FAMILY], False),
        ([], ["TREND_PULLBACK"], False),
        ([], [], False),
    ],
)
def test_family_selection_never_follows_a_later_plan(selected, snapshot, expected):
    assert (
        family_is_selected(selected_strategy_ids=selected, snapshot_strategy_ids=snapshot)
        is expected
    )
