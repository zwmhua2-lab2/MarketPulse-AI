from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from marketpulse.market_data.models import MarketType

from .models import (
    EventType,
    LifecycleAction,
    MarketEvent,
    StateApplyResult,
    StateTransition,
    SymbolState,
    SymbolStateRecord,
    deterministic_id,
)


@dataclass(frozen=True)
class StateMachineConfig:
    version: str = "g2-v1"
    watch_ttl: timedelta = timedelta(minutes=15)
    setup_ttl: timedelta = timedelta(minutes=20)
    cooldown: timedelta = timedelta(minutes=5)
    setup_strength: float = 0.60
    cooldown_reentry_strength: float = 0.85


class SymbolStateManager:
    """The sole owner of lifecycle transition rules for Group 2 states."""

    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self.config = config or StateMachineConfig()
        self._records: dict[str, SymbolStateRecord] = {}

    def current(self, event: MarketEvent) -> SymbolStateRecord:
        return self.state_for(event.instrument_id, event.symbol)

    def state_for(self, instrument_id: str, symbol: str) -> SymbolStateRecord:
        return self._records.setdefault(instrument_id, SymbolStateRecord(instrument_id=instrument_id, symbol=symbol))

    def snapshot_for(self, instrument_id: str, symbol: str) -> SymbolStateRecord:
        current = self._records.get(instrument_id)
        if current is None:
            return SymbolStateRecord(instrument_id=instrument_id, symbol=symbol)
        return current.model_copy(deep=True)

    def hydrate(self, record: SymbolStateRecord) -> SymbolStateRecord:
        current = self._records.get(record.instrument_id)
        if current is None or record.state_version >= current.state_version:
            self._records[record.instrument_id] = record.model_copy(deep=True)
        return self._records[record.instrument_id]

    def apply(self, event: MarketEvent, action: LifecycleAction, expected_state_version: int | None = None) -> tuple[SymbolStateRecord, StateTransition]:
        state, transition = self.prepare_apply(event, action, expected_state_version)
        self.commit(state)
        return state, transition

    def prepare_apply(
        self,
        event: MarketEvent,
        action: LifecycleAction,
        expected_state_version: int | None = None,
    ) -> tuple[SymbolStateRecord, StateTransition]:
        """Build a transition without changing the committed in-memory state."""
        current = self.snapshot_for(event.instrument_id, event.symbol)
        expected = event.state_version if expected_state_version is None else expected_state_version
        if expected != current.state_version:
            return current, self._transition(current, current.state, event, StateApplyResult.REJECT_STALE_OPERATION, "expected_state_version_mismatch")
        if current.last_event_time and event.event_time < current.last_event_time:
            return current, self._transition(current, current.state, event, StateApplyResult.REJECT_LATE_EVENT, "event_time_precedes_applied_state")
        if current.cooldown_until and event.event_time < current.cooldown_until and event.strength < self.config.cooldown_reentry_strength:
            return current, self._transition(current, current.state, event, StateApplyResult.REJECT_COOLDOWN, "cooldown_requires_stronger_evidence")
        target, reason = self._target(current, event, action)
        if target == current.state:
            current.last_event_time = event.event_time
            return current, self._transition(current, target, event, StateApplyResult.NO_CHANGE, reason)
        before = current.state
        current.state = target
        current.state_version += 1
        current.last_event_time = event.event_time
        current.watch_expires_at = event.event_time + (self.config.setup_ttl if target is SymbolState.SETUP else self.config.watch_ttl) if target in {SymbolState.WATCHING, SymbolState.SETUP} else None
        if target is SymbolState.IDLE and before in {SymbolState.DETECTED, SymbolState.WATCHING, SymbolState.SETUP}:
            current.cooldown_until = event.event_time + self.config.cooldown
        return current, self._transition(current, target, event, StateApplyResult.APPLIED, reason, from_state=before)

    def commit(self, record: SymbolStateRecord) -> SymbolStateRecord:
        self._records[record.instrument_id] = record.model_copy(deep=True)
        return self._records[record.instrument_id]

    def expire(self, instrument_id: str, now: datetime) -> StateTransition | None:
        prepared = self.prepare_expire(instrument_id, now)
        if prepared is None:
            return None
        state, transition, _ = prepared
        self.commit(state)
        return transition

    def prepare_expire(
        self,
        instrument_id: str,
        now: datetime,
        market_type: MarketType = MarketType.SPOT,
    ) -> tuple[SymbolStateRecord, StateTransition, MarketEvent] | None:
        """Build a TTL transition without changing the committed in-memory state."""
        stored = self._records.get(instrument_id)
        current = stored.model_copy(deep=True) if stored else None
        if not current or current.state is SymbolState.IDLE or not current.watch_expires_at or now < current.watch_expires_at:
            return None
        before = current.state
        current.state = SymbolState.IDLE
        current.state_version += 1
        current.cooldown_until = now + self.config.cooldown
        synthetic = MarketEvent(event_id=deterministic_id("ttl", instrument_id, now.isoformat()), symbol=current.symbol, instrument_id=instrument_id, market_type=market_type, event_type=EventType.STRUCTURE_CHANGE, event_time=now, received_time=now, source="g2.state_ttl", strength=0, priority=0, state_version=current.state_version - 1, config_version=self.config.version)
        transition = self._transition(current, SymbolState.IDLE, synthetic, StateApplyResult.APPLIED, "watch_ttl_expired", from_state=before)
        return current, transition, synthetic

    def _target(self, current: SymbolStateRecord, event: MarketEvent, action: LifecycleAction) -> tuple[SymbolState, str]:
        if action is LifecycleAction.NORMALIZED or event.event_type is EventType.FAILED_BREAKOUT:
            if current.state is SymbolState.SETUP:
                return SymbolState.WATCHING, "normalization_or_failed_breakout"
            if current.state in {SymbolState.DETECTED, SymbolState.WATCHING}:
                return SymbolState.IDLE, "normalization_or_failed_breakout"
            return SymbolState.IDLE, "already_idle"
        setup_evidence = event.event_type in {EventType.BREAKOUT, EventType.STRUCTURE_CHANGE} and event.strength >= self.config.setup_strength
        if current.state is SymbolState.IDLE:
            return SymbolState.DETECTED, "significant_single_market_fact"
        if current.state is SymbolState.DETECTED:
            return (SymbolState.SETUP if setup_evidence else SymbolState.WATCHING), "upgrade_with_structure" if setup_evidence else "continue_observation"
        if current.state is SymbolState.WATCHING and setup_evidence:
            return SymbolState.SETUP, "evidence_upgrade"
        return current.state, "evidence_recorded"

    def _transition(self, current: SymbolStateRecord, target: SymbolState, event: MarketEvent, result: StateApplyResult, reason: str, from_state: SymbolState | None = None) -> StateTransition:
        return StateTransition(transition_id=deterministic_id("st", event.event_id, current.state_version, result), instrument_id=current.instrument_id, symbol=current.symbol, from_state=from_state or current.state, to_state=target, event_id=event.event_id, event_time=event.event_time, state_version=current.state_version, result=result, reason=reason)
