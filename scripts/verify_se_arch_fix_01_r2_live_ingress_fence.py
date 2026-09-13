"""SE-ARCH-FIX-01 R2 cross-process live-ingress fence harness (Reviewer RRF-01 §12).

Reproduces the exact reviewer attack across real process boundaries, sharing only
PostgreSQL:

* **Process A** opens a live ingress session, issues a proof for one input, fails
  its Capture Anchor write and exits with *nothing* durable -- no anchor, no
  evidence.
* **Process B** is a **new interpreter** with a new session id and a new secret,
  started *later*, and is handed that same old event with a newer BBO available.
  It must refuse it, and the refusal must come from the causal session-start
  fence rather than from a test that withholds a proof: B is given a real issuer,
  is offered the old proof replayed, and is also shown to admit a genuinely new
  input afterwards.

Each phase is its own interpreter so no in-process state (pending anchors, the
signing secret, the session clock) can carry across the boundary.

Usage (from the repository root, cwd = worktree):

    py -3.14 scripts/verify_se_arch_fix_01_r2_live_ingress_fence.py

Exit code 0 only when every check passes. ``DATABASE_URL`` selects the disposable
PostgreSQL instance; the harness creates and drops its own database on it.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
SRC = BACKEND / "src"
sys.path.insert(0, str(SRC))

from alembic import command
from alembic.config import Config
from marketpulse.clock import ReplayClock
from marketpulse.config import Settings
from marketpulse.db.models import (
    EdgeOpportunityCaptureAnchorRecord,
    EdgeOpportunityEvidenceRecord,
)
from marketpulse.edge.capture import (
    EdgeCaptureContext,
    ForwardAdmissionAuthority,
    ForwardAdmissionProof,
    ReferenceQuote,
)
from marketpulse.edge.models import EvidenceSource
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
from marketpulse.g2.repository import (
    CaptureAdmissionRejected,
    PostgresG2Repository,
)
from marketpulse.g2.strategy import StrategyEngine
from marketpulse.market_data.models import (
    DataQuality,
    MarketType,
    NormalizedMarketEvent,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# The event's own causal time. Process A's session starts at exactly this instant;
# Process B's session starts five minutes later, which is what makes the
# redelivered input older than the live session it is being offered to.
EVENT_TIME = datetime(2026, 1, 2, 9, 30, tzinfo=UTC)
SESSION_A_START = EVENT_TIME
SESSION_B_START = EVENT_TIME + timedelta(minutes=5)
SECRET_A = b"process-a-live-ingress-secret"
SECRET_B = b"process-b-live-ingress-secret"
INSTRUMENT = "BTC-USDT"
EVENT_ID = "evt-fence-redelivery"
FRESH_EVENT_ID = "evt-fence-fresh"
RESULT_MARKER = "R2_FENCE_RESULT "


# --- fixtures ---------------------------------------------------------------------------


def _features(at: datetime) -> FeatureSnapshot:
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


def _event(*, event_id: str, at: datetime) -> MarketEvent:
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
        state_version=1,
        config_version="g2-v1",
        payload={"current_price": 100.5},
    )


def _facts(*, event_id: str, at: datetime) -> dict[str, object]:
    event = _event(event_id=event_id, at=at)
    features = _features(at)
    state = SymbolStateRecord(
        instrument_id=INSTRUMENT,
        symbol=INSTRUMENT,
        state=SymbolState.SETUP,
        state_version=1,
        last_event_time=at,
        watch_expires_at=at + timedelta(minutes=20),
    )
    transition = StateTransition(
        transition_id=deterministic_id("st", event.event_id, 1, StateApplyResult.APPLIED),
        instrument_id=INSTRUMENT,
        symbol=INSTRUMENT,
        from_state=SymbolState.WATCHING,
        to_state=SymbolState.SETUP,
        event_id=event.event_id,
        event_time=at,
        state_version=1,
        result=StateApplyResult.APPLIED,
        reason="evidence_upgrade",
    )
    timeline = SignalTimelineEvent(
        timeline_id=deterministic_id("tl", event.event_id, LifecycleAction.START),
        event_id=event.event_id,
        symbol=INSTRUMENT,
        instrument_id=INSTRUMENT,
        signal_type=event.event_type,
        event_time=at,
        received_time=at,
        price=100.5,
        context=event.payload,
        strength=event.strength,
        lifecycle_action=LifecycleAction.START,
        symbol_state=state.state,
        state_version=state.state_version,
        config_version=event.config_version,
    )
    candidates: list[StrategyCandidate] = StrategyEngine(clock=ReplayClock(at)).candidates(
        features, event, state.state_version
    )
    return {
        "event": event,
        "features": features,
        "state": state,
        "transition": transition,
        "timeline": timeline,
        "candidates": candidates,
    }


def _live_input(event: MarketEvent) -> NormalizedMarketEvent:
    return NormalizedMarketEvent(
        exchange="OKX",
        base_asset="BTC",
        quote_asset="USDT",
        market_type=event.market_type,
        instrument_id=event.instrument_id,
        event_time=event.event_time,
        received_time=event.received_time,
        source="fixture-live-ingress",
    )


def _quote(*, at: datetime, bid: float = 99.5, ask: float = 100.5) -> ReferenceQuote:
    return ReferenceQuote(
        instrument_id=INSTRUMENT,
        market_type=MarketType.SPOT,
        bid=bid,
        ask=ask,
        received_at=at,
        data_quality=DataQuality.FRESH,
        tradable=True,
        source_event_time=at,
        source="okx-bbo-tbt",
        source_sequence=1,
    )


def _context() -> EdgeCaptureContext:
    return EdgeCaptureContext(
        source_type=EvidenceSource.FORWARD_PAPER,
        source_identity="okx-ws-bbo",
        source_manifest_id="manifest-r2-fence",
    )


# --- database helpers -------------------------------------------------------------------


def _database_url() -> str:
    return os.environ.get("DATABASE_URL") or Settings().database_url


def _url_for(base: str, name: str) -> str:
    return f"{base.rsplit('/', 1)[0]}/{name}"


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


async def _counts(factory) -> dict[str, int]:
    async with factory() as session:
        return {
            "anchors": int(
                await session.scalar(select(func.count()).select_from(EdgeOpportunityCaptureAnchorRecord))
            ),
            "evidence": int(
                await session.scalar(
                    select(func.count()).select_from(EdgeOpportunityEvidenceRecord)
                )
            ),
        }


# --- phases -----------------------------------------------------------------------------


async def _phase_a(url: str, handoff: str) -> dict[str, object]:
    """Session A issues a proof, fails its anchor write, exits with nothing durable."""

    import marketpulse.g2.repository as g2_repository

    facts = _facts(event_id=EVENT_ID, at=EVENT_TIME)
    authority = ForwardAdmissionAuthority(
        clock=ReplayClock(SESSION_A_START), session_id="process-a-session", secret=SECRET_A
    )
    proof = authority.issue(source_event=_live_input(facts["event"]), event=facts["event"])
    if proof is None:
        raise AssertionError("session A must be able to issue a proof for its own input")

    async with _sessions(url) as factory:
        repository = PostgresG2Repository(
            factory,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(at=EVENT_TIME),
            forward_admission_verifier=authority.verifier(),
        )
        original = g2_repository.record_bbo_observation

        async def fail_anchor_write(*_args, **_kwargs):
            raise RuntimeError("injected anchor write failure")

        g2_repository.record_bbo_observation = fail_anchor_write
        try:
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
                    forward_admission_proof=proof,
                )
            except RuntimeError:
                anchor_write_failed = True
            else:
                anchor_write_failed = False
        finally:
            g2_repository.record_bbo_observation = original
        counts = await _counts(factory)

    Path(handoff).write_text(json.dumps(proof.payload()), encoding="utf-8")
    return {
        "proof_issued": True,
        "anchor_write_failed": anchor_write_failed,
        "session_id": proof.session_id,
        "session_started_at": proof.session_started_at.isoformat(),
        "source_event_time": proof.source_event_time.isoformat(),
        **counts,
    }


async def _phase_b(url: str, handoff: str) -> dict[str, object]:
    """A later, fully working session must still refuse the redelivered old input."""

    old_facts = _facts(event_id=EVENT_ID, at=EVENT_TIME)
    fresh_facts = _facts(event_id=FRESH_EVENT_ID, at=SESSION_B_START + timedelta(minutes=1))
    authority = ForwardAdmissionAuthority(
        clock=ReplayClock(SESSION_B_START), session_id="process-b-session", secret=SECRET_B
    )
    replayed = ForwardAdmissionProof.model_validate(
        json.loads(Path(handoff).read_text(encoding="utf-8"))
    )

    issued_for_old = authority.issue(
        source_event=_live_input(old_facts["event"]), event=old_facts["event"]
    )
    fresh_proof = authority.issue(
        source_event=_live_input(fresh_facts["event"]), event=fresh_facts["event"]
    )

    async with _sessions(url) as factory:
        repository = PostgresG2Repository(
            factory,
            capture=_context(),
            reference_quote_for=lambda _instrument_id: _quote(
                at=EVENT_TIME + timedelta(seconds=10), bid=101.5, ask=102.5
            ),
            forward_admission_verifier=authority.verifier(),
        )

        async def attempt(proof: ForwardAdmissionProof | None) -> str:
            try:
                await repository.persist(
                    old_facts["event"],
                    old_facts["timeline"],
                    old_facts["state"],
                    old_facts["transition"],
                    old_facts["candidates"],
                    old_facts["features"],
                    precondition_state=SymbolStateRecord(
                        instrument_id=INSTRUMENT, symbol=INSTRUMENT
                    ),
                    forward_admission_proof=proof,
                )
            except CaptureAdmissionRejected:
                return "CaptureAdmissionRejected"
            return "ADMITTED"

        without_proof = await attempt(None)
        with_replayed_proof = await attempt(replayed)
        after_redelivery = await _counts(factory)

        fresh_admitted = await repository.persist(
            fresh_facts["event"],
            fresh_facts["timeline"],
            fresh_facts["state"],
            fresh_facts["transition"],
            fresh_facts["candidates"],
            fresh_facts["features"],
            precondition_state=SymbolStateRecord(
                instrument_id=INSTRUMENT, symbol=INSTRUMENT
            ),
            forward_admission_proof=fresh_proof,
        )
        after_fresh = await _counts(factory)

    return {
        "session_id": authority.session_id,
        "session_started_at": authority.session_started_at.isoformat(),
        "issued_for_old_input": issued_for_old is not None,
        "redelivery_without_proof": without_proof,
        "redelivery_with_replayed_proof": with_replayed_proof,
        "anchors_after_redelivery": after_redelivery["anchors"],
        "evidence_after_redelivery": after_redelivery["evidence"],
        "fresh_input_admitted": bool(fresh_admitted),
        "anchors_after_fresh_input": after_fresh["anchors"],
        "evidence_after_fresh_input": after_fresh["evidence"],
    }


# --- orchestrator -----------------------------------------------------------------------


@contextmanager
def _disposable_database(base: str, label: str):
    name = f"marketpulse_fix01r2_{label}_{uuid4().hex[:12]}"
    asyncio.run(_execute(base, f'CREATE DATABASE "{name}"'))
    url = _url_for(base, name)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    # `alembic/env.py` prefers the `DATABASE_URL` environment variable over the
    # config URL, so the upgrade has to be pointed at this disposable database
    # explicitly -- otherwise it would silently migrate whatever the caller's
    # environment already names.
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    try:
        yield url
    finally:
        asyncio.run(
            _execute(
                base,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{name}' AND pid <> pg_backend_pid()",
            )
        )
        asyncio.run(_execute(base, f'DROP DATABASE "{name}"'))


def _run_phase(phase: str, url: str, handoff: str) -> dict[str, object]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env["DATABASE_URL"] = url
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--phase", phase, url, handoff],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"phase {phase} failed (exit {completed.returncode})\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    for line in completed.stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            return json.loads(line[len(RESULT_MARKER) :])
    raise RuntimeError(f"phase {phase} produced no result line:\n{completed.stdout}")


def main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[1] == "--phase":
        phase, url, handoff = argv[2], argv[3], argv[4]
        outcome = asyncio.run(_phase_a(url, handoff) if phase == "a" else _phase_b(url, handoff))
        print(RESULT_MARKER + json.dumps(outcome, sort_keys=True, default=str))
        return 0

    base = _database_url()
    handoff = str(REPO_ROOT / "r2-fence-proof.json")
    with _disposable_database(base, "fence") as url:
        process_a = _run_phase("a", url, handoff)
        process_b = _run_phase("b", url, handoff)
    Path(handoff).unlink(missing_ok=True)

    checks = {
        "process A issued a proof for its own input": process_a["proof_issued"] is True,
        "process A anchor write failed": process_a["anchor_write_failed"] is True,
        "process A left zero anchors": process_a["anchors"] == 0,
        "process A left zero evidence": process_a["evidence"] == 0,
        "process B runs a genuinely later session": (
            process_b["session_started_at"] == SESSION_B_START.isoformat()
        ),
        "process B cannot issue for the old input": process_b["issued_for_old_input"] is False,
        "old redelivery without a proof is refused": (
            process_b["redelivery_without_proof"] == "CaptureAdmissionRejected"
        ),
        "old redelivery with A's replayed proof is refused": (
            process_b["redelivery_with_replayed_proof"] == "CaptureAdmissionRejected"
        ),
        "redelivery wrote no anchors": process_b["anchors_after_redelivery"] == 0,
        "redelivery wrote no evidence": process_b["evidence_after_redelivery"] == 0,
        "process B still admits a genuinely new input": process_b["fresh_input_admitted"] is True,
        "the new input produced exactly one anchor": process_b["anchors_after_fresh_input"] == 1,
        "the new input produced exactly one evidence row": (
            process_b["evidence_after_fresh_input"] == 1
        ),
    }

    print(json.dumps({"process_a": process_a, "process_b": process_b}, indent=2, default=str))
    print()
    for label, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    failed = [label for label, passed in checks.items() if not passed]
    print()
    print(
        f"result={'PASS' if not failed else 'FAIL'} "
        f"checks={len(checks) - len(failed)}/{len(checks)}"
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
