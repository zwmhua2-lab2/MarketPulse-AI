from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    DecisionSnapshotRecord,
    ExecutionIntentRecord,
    FillRecord,
    PaperOrderRecord,
    PositionEventRecord,
    PositionRecord,
    SignalTimelineRecord,
    StrategyCandidateRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g2.models import (
    DirectionBias,
    LifecycleAction,
    StateTransition,
    StrategyCandidate,
)
from marketpulse.g2.repository import InMemoryG2Repository, PostgresG2Repository
from marketpulse.g2.runtime import EventRuntime, ScannerPipeline
from marketpulse.g2.scanner import OpportunityScanner, ScannerConfig
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.g3.models import (
    AIAnalysis,
    BestBidAsk,
    DecisionSnapshot,
    ExecutionIntent,
    RunMode,
)
from marketpulse.g3.service import (
    DecisionService,
    DecisionSnapshotBuilder,
    G3Workflow,
    PaperExecutionService,
    TradePlanManager,
    stable_id,
)
from marketpulse.g4.incidents import IncidentManager
from marketpulse.g4.models import (
    HealthComponent,
    HealthStatus,
    PositionReevaluation,
    SystemState,
)
from marketpulse.g4.orchestrator import SafetyRuntime
from marketpulse.g4.planning import PlanManager
from marketpulse.g4.protection import PositionProtectionService
from marketpulse.g4.reevaluation import PositionReevaluationService
from marketpulse.g4.risk_gate import SystemRiskGate
from marketpulse.g4.state import SystemStateService
from marketpulse.market_data.models import (
    AuxiliaryContext,
    NormalizedBookTicker,
    NormalizedMarketEvent,
)
from marketpulse.runtime import HealthRegistry

from .canonical import capture_workspace_snapshot
from .evaluation import ReplayEvaluationReport, evaluate_replay_workspace


class ReplayOrderingError(ValueError):
    """Raised when replay input cannot preserve observed processing order."""


class ReplayWorkspaceIsolationError(RuntimeError):
    """Raised when replay cannot prove it has an isolated, current, empty workspace."""


class ReplayBBOUnavailable(RuntimeError):
    """Raised when a replay trading decision would need an unobserved quote."""


class ReplayAIRecordMissing(RuntimeError):
    """Recorded G3 input is intentionally total only for approved replay snapshots."""

    replay_record_missing = True


class ReplayPositionReviewRecordMissing(RuntimeError):
    """Recorded G4 review input is intentionally total only for approved replay snapshots."""

    replay_record_missing = True


@dataclass(frozen=True)
class ReplayFrame:
    ordinal: int
    market_event: NormalizedMarketEvent
    auxiliary: AuxiliaryContext | None = None

    @property
    def processing_time(self) -> datetime:
        received_time = self.market_event.received_time
        if received_time.tzinfo is None:
            raise ReplayOrderingError("ReplayFrame.received_time must be timezone-aware")
        return received_time.astimezone(UTC)


class ReplayEventSource:
    """An ordered, stable view of already-normalized replay input."""

    def __init__(self, frames: Iterable[ReplayFrame]) -> None:
        self.frames = tuple(frames)
        previous_time: datetime | None = None
        for frame in self.frames:
            processing_time = frame.processing_time
            if previous_time is not None and processing_time < previous_time:
                raise ReplayOrderingError(
                    "received_time must be non-decreasing in replay input "
                    f"(ordinal={frame.ordinal})"
                )
            previous_time = processing_time


@dataclass(frozen=True)
class ReplayEventTrace:
    event_id: str
    timeline_id: str
    lifecycle_action: LifecycleAction
    transition_id: str
    transition_from: str
    transition_to: str
    state_version: int
    candidate_ids: tuple[str, ...]
    candidate_created_at: tuple[datetime, ...]
    candidate_applicable: tuple[bool, ...]
    candidate_direction_bias: tuple[DirectionBias, ...]

    def canonical(self) -> tuple[object, ...]:
        return (
            self.event_id,
            self.timeline_id,
            self.lifecycle_action.value,
            self.transition_id,
            self.transition_from,
            self.transition_to,
            self.state_version,
            self.candidate_ids,
            tuple(item.isoformat() for item in self.candidate_created_at),
            self.candidate_applicable,
            tuple(item.value for item in self.candidate_direction_bias),
        )


@dataclass(frozen=True)
class ReplayFrameTrace:
    input_ordinal: int
    processing_time: datetime
    instrument_id: str
    detected_event_ids: tuple[str, ...]
    events: tuple[ReplayEventTrace, ...]

    def canonical(self) -> tuple[object, ...]:
        return (
            self.input_ordinal,
            self.processing_time.isoformat(),
            self.instrument_id,
            self.detected_event_ids,
            tuple(event.canonical() for event in self.events),
        )


@dataclass(frozen=True)
class ReplayTrace:
    frames: tuple[ReplayFrameTrace, ...]

    def canonical(self) -> tuple[object, ...]:
        return tuple(frame.canonical() for frame in self.frames)


@dataclass(frozen=True)
class ReplayResult:
    trace: ReplayTrace
    repository: InMemoryG2Repository


class ReplayG2Runner:
    """Feed normalized history through the existing G2 runtime using ReplayClock."""

    def __init__(self, scanner_config: ScannerConfig | None = None) -> None:
        self.scanner_config = scanner_config or ScannerConfig()

    async def run(self, source: ReplayEventSource | Iterable[ReplayFrame]) -> ReplayResult:
        if not isinstance(source, ReplayEventSource):
            source = ReplayEventSource(source)
        if not source.frames:
            raise ValueError("replay source must contain at least one frame")

        clock = ReplayClock(source.frames[0].processing_time)
        repository = InMemoryG2Repository()
        runtime = EventRuntime(
            repository,
            strategy_engine=StrategyEngine(clock),
            worker_count=1,
        )
        pipeline = ScannerPipeline(
            OpportunityScanner(self.scanner_config, clock),
            runtime,
            clock=clock,
        )
        traces: list[ReplayFrameTrace] = []
        await runtime.start()
        try:
            for frame in source.frames:
                clock.advance_to(frame.processing_time)
                if clock.now() != frame.processing_time:
                    raise RuntimeError("ReplayClock did not advance to the frame received_time")
                timeline_offset = len(repository.timeline)
                candidate_offset = len(repository.candidates)
                await pipeline.ingest(frame.market_event, auxiliary=frame.auxiliary)
                timelines = repository.timeline[timeline_offset:]
                candidates = repository.candidates[candidate_offset:]
                traces.append(
                    ReplayFrameTrace(
                        input_ordinal=frame.ordinal,
                        processing_time=clock.now(),
                        instrument_id=frame.market_event.instrument_id,
                        detected_event_ids=tuple(
                            event.event_id for event in pipeline.last_detected_events
                        ),
                        events=tuple(
                            self._event_trace(
                                timeline.lifecycle_action,
                                transition,
                                timeline.timeline_id,
                                candidates,
                            )
                            for timeline, transition in zip(
                                timelines, repository.transitions[timeline_offset:], strict=True
                            )
                        ),
                    )
                )
        finally:
            await runtime.stop()
        if runtime.worker_exceptions:
            raise runtime.worker_exceptions[0]
        return ReplayResult(trace=ReplayTrace(tuple(traces)), repository=repository)

    @staticmethod
    def _event_trace(
        lifecycle_action: LifecycleAction,
        transition: StateTransition,
        timeline_id: str,
        candidates: list[StrategyCandidate],
    ) -> ReplayEventTrace:
        event_candidates = [item for item in candidates if item.event_id == transition.event_id]
        return ReplayEventTrace(
            event_id=transition.event_id,
            timeline_id=timeline_id,
            lifecycle_action=lifecycle_action,
            transition_id=transition.transition_id,
            transition_from=transition.from_state.value,
            transition_to=transition.to_state.value,
            state_version=transition.state_version,
            candidate_ids=tuple(item.candidate_id for item in event_candidates),
            candidate_created_at=tuple(item.created_at for item in event_candidates),
            candidate_applicable=tuple(item.applicable for item in event_candidates),
            candidate_direction_bias=tuple(item.direction_bias for item in event_candidates),
        )


class ReplayMarketState:
    """Only exposes BBO facts observed by the replay processing cursor."""

    def __init__(self) -> None:
        self.latest_bbo_by_instrument: dict[str, BestBidAsk] = {}

    def ingest(self, event: NormalizedMarketEvent) -> None:
        if isinstance(event, NormalizedBookTicker):
            self.latest_bbo_by_instrument[event.instrument_id] = BestBidAsk(
                instrument_id=event.instrument_id,
                bid=event.bid_price,
                ask=event.ask_price,
                received_at=event.received_time,
                tradable=True,
                data_quality="FRESH",
            )

    async def bbo_for(self, instrument_id: str) -> BestBidAsk:
        try:
            return self.latest_bbo_by_instrument[instrument_id]
        except KeyError as exc:
            raise ReplayBBOUnavailable(f"no observed replay BBO for {instrument_id}") from exc


class RecordedAIProvider:
    """Replay-only G3 provider: no record means no decision and no fallback."""

    model = "replay-recorded-g3"

    def __init__(self, records: Mapping[str, AIAnalysis]) -> None:
        self.records = dict(records)
        self.calls = 0

    async def analyze(self, snapshot: DecisionSnapshot, prompt: str) -> AIAnalysis:
        self.calls += 1
        try:
            return self.records[snapshot.snapshot_id]
        except KeyError as exc:
            raise ReplayAIRecordMissing(
                f"recorded G3 AI result missing for snapshot {snapshot.snapshot_id}"
            ) from exc


class RecordedPositionReviewProvider:
    """Replay-only G4 provider: a missing review remains a HOLD-safe failure."""

    model = "replay-recorded-g4"

    def __init__(self, records: Mapping[str, PositionReevaluation]) -> None:
        self.records = dict(records)
        self.calls = 0

    async def review(self, snapshot: DecisionSnapshot, prompt: str) -> PositionReevaluation:
        self.calls += 1
        try:
            return self.records[snapshot.snapshot_id]
        except KeyError as exc:
            raise ReplayPositionReviewRecordMissing(
                f"recorded G4 review missing for snapshot {snapshot.snapshot_id}"
            ) from exc


_REPLAY_BUSINESS_TABLES = (
    "market_events",
    "signal_timeline_events",
    "symbol_states",
    "state_transitions",
    "strategy_candidates",
    "derived_observations",
    "decision_snapshots",
    "ai_decisions",
    "trade_plans",
    "trade_plan_scenarios",
    "execution_intents",
    "paper_orders",
    "fills",
    "positions",
    "trades",
    "accounts",
    "ledger_entries",
    "outbox_records",
    "runtime_controls",
    "symbol_controls",
    "incidents",
    "position_events",
)


class ReplayWorkspaceGuard:
    """Proves the replay database is separate, migrated and empty before a run."""

    def __init__(self, primary: AsyncEngine, replay: AsyncEngine, *, schema_head: str) -> None:
        self.primary = primary
        self.replay = replay
        self.schema_head = schema_head

    async def validate(self) -> tuple[str, str, dict[str, int]]:
        primary_name = await self._database_name(self.primary)
        replay_name = await self._database_name(self.replay)
        if primary_name == replay_name:
            raise ReplayWorkspaceIsolationError("replay database identity equals primary database")
        async with self.replay.connect() as connection:
            revision = (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar()
        if revision != self.schema_head:
            raise ReplayWorkspaceIsolationError(
                f"replay schema is {revision!r}, expected Alembic head {self.schema_head!r}"
            )
        counts = await self.counts(self.replay)
        dirty = {table: count for table, count in counts.items() if count}
        if dirty:
            raise ReplayWorkspaceIsolationError(f"replay workspace is not clean: {dirty}")
        return primary_name, replay_name, counts

    @staticmethod
    async def _database_name(engine: AsyncEngine) -> str:
        async with engine.connect() as connection:
            value = (await connection.execute(text("SELECT current_database()"))).scalar_one()
        return str(value)

    @staticmethod
    async def counts(engine: AsyncEngine) -> dict[str, int]:
        async with engine.connect() as connection:
            return {
                table: int(
                    (await connection.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
                )
                for table in _REPLAY_BUSINESS_TABLES
            }


@dataclass(frozen=True)
class ReplayTradingResult:
    primary_database: str
    replay_database: str
    primary_counts_before: dict[str, int]
    primary_counts_after: dict[str, int]
    processed_frames: int
    snapshot_ids: tuple[str, ...]
    decisions: tuple[tuple[str, str], ...]
    plans: tuple[tuple[str, str], ...]
    intents: tuple[tuple[str, str], ...]
    orders: tuple[tuple[str, str, str], ...]
    fills: tuple[tuple[str, str, float, float, float], ...]
    final_account: tuple[float, float, float] | None
    final_positions: tuple[tuple[str, float, float, float], ...]
    trades: tuple[tuple[str, str, str | None], ...]
    position_events: tuple[tuple[str, str, dict], ...]
    setup_snapshot_ids: tuple[str, ...]
    plan_ids: tuple[str, ...]
    buy_order_ids: tuple[str, ...]
    buy_fill_ids: tuple[str, ...]
    safety_results: tuple[dict[str, object], ...]
    g3_provider_calls: int
    g4_provider_calls: int
    workspace_digest: str
    evaluation: ReplayEvaluationReport | None = None


class ReplayTradingRunner:
    """Orchestrates historical frames through accepted G2/G3/G4 components only."""

    # The replay guard verifies the replay workspace is migrated to the *current*
    # Alembic head and is empty. The linear chain is SE-02A Edge evidence
    # (20260911_0005), N01-7 position protection (20260912_0006), the
    # pre-acceptance FIX-01 capture-anchor and review-fix revisions
    # (20260913_0007 -> 20260913_0008), FIX-02 outcome revision scope
    # (20260913_0009), then PRE-01B-I2 Advisory ingress core (20260917_0010,
    # additive: two new Advisory tables plus three extension column-sets on
    # already-accepted tables). Its separate + migrated + clean workspace
    # behaviour is unchanged.
    schema_head = "20260917_0010"

    def __init__(
        self,
        settings: Settings,
        *,
        g3_records: Mapping[str, AIAnalysis],
        g4_records: Mapping[str, PositionReevaluation],
        scanner_config: ScannerConfig | None = None,
        schema_head: str | None = None,
    ) -> None:
        if settings.run_mode != "REPLAY":
            raise ReplayWorkspaceIsolationError("ReplayTradingRunner requires RUN_MODE=REPLAY")
        if not settings.replay_database_url:
            raise ReplayWorkspaceIsolationError("RUN_MODE=REPLAY requires replay_database_url")
        self.settings = settings
        self.g3_provider = RecordedAIProvider(g3_records)
        self.g4_provider = RecordedPositionReviewProvider(g4_records)
        self.scanner_config = scanner_config or ScannerConfig()
        self.expected_schema_head = schema_head or self.schema_head

    async def run(self, source: ReplayEventSource | Iterable[ReplayFrame]) -> ReplayTradingResult:
        if not isinstance(source, ReplayEventSource):
            source = ReplayEventSource(source)
        if not source.frames:
            raise ValueError("replay source must contain at least one frame")

        primary = create_async_engine(self.settings.database_url, poolclass=NullPool)
        replay = create_async_engine(self.settings.replay_database_url, poolclass=NullPool)
        try:
            guard = ReplayWorkspaceGuard(primary, replay, schema_head=self.expected_schema_head)
            primary_name, replay_name, _ = await guard.validate()
            primary_before = await guard.counts(primary)
            result = await self._run_in_workspace(
                source, replay, primary_name, replay_name, primary_before
            )
            snapshot = await capture_workspace_snapshot(replay, _REPLAY_BUSINESS_TABLES)
            evaluation = await evaluate_replay_workspace(
                replay, workspace_digest=snapshot.digest()
            )
            primary_after = await guard.counts(primary)
            if primary_after != primary_before:
                raise ReplayWorkspaceIsolationError("primary database changed during replay")
            return ReplayTradingResult(
                primary_database=result.primary_database,
                replay_database=result.replay_database,
                primary_counts_before=result.primary_counts_before,
                primary_counts_after=primary_after,
                processed_frames=result.processed_frames,
                snapshot_ids=result.snapshot_ids,
                decisions=result.decisions,
                plans=result.plans,
                intents=result.intents,
                orders=result.orders,
                fills=result.fills,
                final_account=result.final_account,
                final_positions=result.final_positions,
                trades=result.trades,
                position_events=result.position_events,
                setup_snapshot_ids=result.setup_snapshot_ids,
                plan_ids=result.plan_ids,
                buy_order_ids=result.buy_order_ids,
                buy_fill_ids=result.buy_fill_ids,
                safety_results=result.safety_results,
                g3_provider_calls=result.g3_provider_calls,
                g4_provider_calls=result.g4_provider_calls,
                workspace_digest=snapshot.digest(),
                evaluation=evaluation,
            )
        finally:
            await primary.dispose()
            await replay.dispose()

    async def _run_in_workspace(
        self,
        source: ReplayEventSource,
        engine: AsyncEngine,
        primary_name: str,
        replay_name: str,
        primary_counts: dict[str, int],
    ) -> ReplayTradingResult:
        clock = ReplayClock(source.frames[0].processing_time)
        sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, expire_on_commit=False
        )
        market = ReplayMarketState()
        health = HealthRegistry()
        state_service = SystemStateService(sessions, clock=clock)
        incidents = IncidentManager(sessions, clock=clock)
        risk_gate = SystemRiskGate(sessions, state_service, incidents, health, clock=clock)
        runtime = EventRuntime(
            PostgresG2Repository(sessions), strategy_engine=StrategyEngine(clock), worker_count=1
        )
        pipeline = ScannerPipeline(
            OpportunityScanner(self.scanner_config, clock), runtime, clock=clock
        )
        execution = PaperExecutionService(
            sessions,
            market.bbo_for,
            lambda instrument_id: self._state_version(runtime, instrument_id),
            initial_balance=self.settings.paper_initial_balance,
            risk_gate=risk_gate,
            clock=clock,
        )
        protection = PositionProtectionService(sessions, execution, incidents, health, clock=clock)
        plans = PlanManager(sessions, execution, clock=clock)
        reevaluation = PositionReevaluationService(
            sessions,
            self.g4_provider,
            plans,
            risk_gate,
            protection,
            incidents,
            execution,
            health,
            model=RecordedPositionReviewProvider.model,
            clock=clock,
            snapshot_id_factory=self._review_snapshot_id,
        )
        safety = SafetyRuntime(
            execution=execution,
            protection=protection,
            reevaluation=reevaluation,
            health=health,
            clock=clock,
        )
        decision_service = DecisionService(
            sessions, self.g3_provider, model=RecordedAIProvider.model, clock=clock
        )
        workflow = G3Workflow(decision_service, TradePlanManager(clock=clock), sessions)
        builder = DecisionSnapshotBuilder(clock=clock)
        setup_snapshot_ids: list[str] = []
        plan_ids: list[str] = []
        buy_order_ids: list[str] = []
        buy_fill_ids: list[str] = []
        safety_results: list[dict[str, object]] = []

        await execution.bootstrap_account(RunMode.REPLAY)
        await state_service.ensure(RunMode.REPLAY)
        health.set(HealthComponent.DATABASE.value, HealthStatus.HEALTHY.value)
        health.set(HealthComponent.EXECUTION.value, HealthStatus.HEALTHY.value)
        health.set(HealthComponent.AI_AUXILIARY.value, HealthStatus.HEALTHY.value)
        await runtime.start()
        try:
            for frame in source.frames:
                clock.advance_to(frame.processing_time)
                market.ingest(frame.market_event)
                if isinstance(frame.market_event, NormalizedBookTicker):
                    quote = await market.bbo_for(frame.market_event.instrument_id)
                    health.set(
                        HealthComponent.CORE_MARKET_DATA.value,
                        HealthStatus.HEALTHY.value,
                        instrument_id=quote.instrument_id,
                    )
                    await self._ensure_running(state_service)

                outcomes = await pipeline.ingest(frame.market_event, auxiliary=frame.auxiliary)
                if isinstance(frame.market_event, NormalizedBookTicker):
                    outcome = await safety.on_market_data(
                        RunMode.REPLAY,
                        await market.bbo_for(frame.market_event.instrument_id),
                        now=clock.now(),
                    )
                    safety_results.append(outcome)
                features = pipeline.last_features
                if features is None:
                    raise RuntimeError("ScannerPipeline did not retain frame features")
                for applied in outcomes:
                    transition = applied.transition
                    if (
                        transition is None
                        or transition.to_state != "SETUP"
                        or transition.result != "APPLIED"
                    ):
                        continue
                    event = next(
                        candidate
                        for candidate in pipeline.last_detected_events
                        if candidate.event_id == applied.event_id
                    )
                    snapshot, plan = await self._process_setup(
                        sessions,
                        runtime,
                        market,
                        builder,
                        workflow,
                        execution,
                        event,
                        features,
                        applied.state,
                        transition,
                    )
                    setup_snapshot_ids.append(snapshot.snapshot_id)
                    if plan is None:
                        continue
                    plan_ids.append(plan.plan_id)
                    intent = ExecutionIntent(
                        intent_id=stable_id(
                            "replay-intent", plan.plan_id, plan.state_version, clock.now().isoformat()
                        ),
                        plan_id=plan.plan_id,
                        instrument_id=plan.instrument_id,
                        run_mode=RunMode.REPLAY,
                        state_version=plan.state_version,
                        created_at=clock.now(),
                    )
                    execution_result = await execution.execute(intent, plan, now=clock.now())
                    if execution_result.order_id:
                        buy_order_ids.append(execution_result.order_id)
                    if execution_result.fill_id:
                        buy_fill_ids.append(execution_result.fill_id)
        finally:
            await runtime.stop()
        if runtime.worker_exceptions:
            raise runtime.worker_exceptions[0]
        facts = await self._trading_facts(sessions)
        return ReplayTradingResult(
            primary_database=primary_name,
            replay_database=replay_name,
            primary_counts_before=primary_counts,
            primary_counts_after=primary_counts,
            processed_frames=len(source.frames),
            **facts,
            setup_snapshot_ids=tuple(setup_snapshot_ids),
            plan_ids=tuple(plan_ids),
            buy_order_ids=tuple(buy_order_ids),
            buy_fill_ids=tuple(buy_fill_ids),
            safety_results=tuple(safety_results),
            g3_provider_calls=self.g3_provider.calls,
            g4_provider_calls=self.g4_provider.calls,
            workspace_digest="",
        )

    @staticmethod
    async def _trading_facts(
        sessions: async_sessionmaker[AsyncSession],
    ) -> dict[str, object]:
        """Extract the durable trading facts produced by this replay workspace."""
        async with sessions() as session:
            snapshots = list(
                (await session.scalars(select(DecisionSnapshotRecord).order_by(DecisionSnapshotRecord.snapshot_id))).all()
            )
            decisions = list(
                (await session.scalars(select(AIDecisionRecord).order_by(AIDecisionRecord.decision_id))).all()
            )
            plans = list(
                (await session.scalars(select(TradePlanRecord).order_by(TradePlanRecord.plan_id))).all()
            )
            intents = list(
                (await session.scalars(select(ExecutionIntentRecord).order_by(ExecutionIntentRecord.intent_id))).all()
            )
            orders = list(
                (await session.scalars(select(PaperOrderRecord).order_by(PaperOrderRecord.order_id))).all()
            )
            fills = list(
                (await session.scalars(select(FillRecord).order_by(FillRecord.fill_id))).all()
            )
            account = await session.scalar(select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY))
            positions = list(
                (await session.scalars(select(PositionRecord).order_by(PositionRecord.instrument_id))).all()
            )
            trades = list(
                (await session.scalars(select(TradeRecord).order_by(TradeRecord.trade_id))).all()
            )
            position_events = list(
                (await session.scalars(select(PositionEventRecord).order_by(PositionEventRecord.event_id))).all()
            )
        return {
            "snapshot_ids": tuple(record.snapshot_id for record in snapshots),
            "decisions": tuple((record.decision_id, record.status) for record in decisions),
            "plans": tuple((record.plan_id, record.status) for record in plans),
            "intents": tuple((record.intent_id, record.status) for record in intents),
            "orders": tuple((record.order_id, record.side, record.status) for record in orders),
            "fills": tuple(
                (record.fill_id, record.order_id, record.price, record.quantity, record.fee)
                for record in fills
            ),
            "final_account": (
                (account.cash_balance, account.reserved_cash, account.realized_pnl)
                if account is not None
                else None
            ),
            "final_positions": tuple(
                (record.instrument_id, record.quantity, record.average_cost, record.realized_pnl)
                for record in positions
            ),
            "trades": tuple((record.trade_id, record.status, record.exit_reason) for record in trades),
            "position_events": tuple(
                (record.event_id, record.event_type, record.payload) for record in position_events
            ),
        }

    @staticmethod
    async def _latest_timeline(
        session: AsyncSession, instrument_id: str
    ) -> list[SignalTimelineRecord]:
        """Return the latest persisted G2 timeline window in chronological order."""
        records = list(
            (
                await session.scalars(
                    select(SignalTimelineRecord)
                    .where(SignalTimelineRecord.instrument_id == instrument_id)
                    .order_by(
                        SignalTimelineRecord.event_time.desc(),
                        SignalTimelineRecord.timeline_id.desc(),
                    )
                    .limit(20)
                )
            ).all()
        )
        records.reverse()
        return records

    @staticmethod
    async def _state_version(runtime: EventRuntime, instrument_id: str) -> int:
        state = await runtime.current_state(instrument_id, instrument_id)
        return state.state_version

    @staticmethod
    async def _ensure_running(state_service: SystemStateService) -> None:
        record = await state_service.load(RunMode.REPLAY)
        if record.system_state != SystemState.RUNNING:
            await state_service.transition(
                RunMode.REPLAY, system_state=SystemState.RUNNING, reason="replay_bootstrap"
            )

    @staticmethod
    def _review_snapshot_id(
        run_mode: RunMode,
        instrument_id: str,
        state_version: int,
        triggering_event: str,
        now: datetime,
    ) -> str:
        return stable_id(
            "replay-review",
            run_mode,
            instrument_id,
            state_version,
            triggering_event,
            now.isoformat(),
        )

    async def _process_setup(
        self,
        sessions: async_sessionmaker[AsyncSession],
        runtime: EventRuntime,
        market: ReplayMarketState,
        builder: DecisionSnapshotBuilder,
        workflow: G3Workflow,
        execution: PaperExecutionService,
        event,
        features,
        state,
        transition,
    ) -> tuple[DecisionSnapshot, object | None]:
        bbo = await market.bbo_for(transition.instrument_id)
        async with sessions() as session:
            candidate_records = list(
                (
                    await session.scalars(
                        select(StrategyCandidateRecord)
                        .where(StrategyCandidateRecord.event_id == event.event_id)
                        .order_by(StrategyCandidateRecord.candidate_id)
                    )
                ).all()
            )
            timeline_records = await self._latest_timeline(session, transition.instrument_id)
            account = await session.scalar(
                select(AccountRecord).where(AccountRecord.run_mode == RunMode.REPLAY)
            )
            positions = list(
                (
                    await session.scalars(
                        select(PositionRecord).where(PositionRecord.run_mode == RunMode.REPLAY)
                    )
                ).all()
            )
            open_orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.run_mode == RunMode.REPLAY,
                            PaperOrderRecord.status == "OPEN",
                        )
                    )
                ).all()
            )
        if account is None:
            raise RuntimeError("replay account was not bootstrapped")
        equity_and_marks = await execution._execution_equity(
            account, positions, bbo, builder.clock.now()
        )
        if equity_and_marks is None:
            raise ReplayBBOUnavailable("replay current equity has no fresh observed mark")
        current_equity, _ = equity_and_marks
        candidates = [
            StrategyCandidate.model_validate(
                {
                    "candidate_id": record.candidate_id,
                    "strategy_id": record.strategy_id,
                    "strategy_version": record.strategy_version,
                    "applicable": record.applicable,
                    "strength": record.strength,
                    "setup_type": record.setup_type,
                    "direction_bias": record.direction_bias,
                    "entry_context": record.entry_context,
                    "supporting_evidence": record.supporting_evidence,
                    "contradicting_evidence": record.contradicting_evidence,
                    "invalidation_hint": record.invalidation_hint,
                    "expected_behavior": record.expected_behavior,
                    "instrument_id": record.instrument_id,
                    "symbol": record.symbol,
                    "event_id": record.event_id,
                    "state_version": record.state_version,
                    "config_version": record.config_version,
                    "created_at": record.created_at,
                }
            )
            for record in candidate_records
        ]
        timeline = [
            {
                "timeline_id": record.timeline_id,
                "event_id": record.event_id,
                "signal_type": record.signal_type,
                "event_time": record.event_time.isoformat(),
                "received_time": record.received_time.isoformat(),
                "symbol_state": record.symbol_state,
                "state_version": record.state_version,
            }
            for record in timeline_records
        ]
        trading_context = {
            "account": {
                "cash_balance": account.cash_balance,
                "reserved_cash": account.reserved_cash,
                "realized_pnl": account.realized_pnl,
            },
            "positions": [
                {
                    "instrument_id": position.instrument_id,
                    "quantity": position.quantity,
                    "average_cost": position.average_cost,
                }
                for position in positions
            ],
            "open_orders": [
                {
                    "order_id": order.order_id,
                    "instrument_id": order.instrument_id,
                    "side": order.side,
                    "quantity": order.quantity,
                    "limit_price": order.limit_price,
                }
                for order in open_orders
            ],
        }
        snapshot = builder.build(
            run_mode=RunMode.REPLAY,
            state=state,
            features=features,
            bbo=bbo,
            candidates=candidates,
            timeline=timeline,
            config_version=self.scanner_config.version,
            trading_context=trading_context,
            now=builder.clock.now(),
        )
        _, plan = await workflow.process_setup(
            snapshot,
            lambda instrument_id: self._state_version(runtime, instrument_id),
            current_equity,
        )
        return snapshot, plan
