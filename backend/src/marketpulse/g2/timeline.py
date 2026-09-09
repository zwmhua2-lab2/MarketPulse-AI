from __future__ import annotations

from dataclasses import dataclass

from .models import LifecycleAction, MarketEvent


@dataclass
class _SignalMemory:
    strength: float
    event_id: str


class SignalLifecycle:
    """Suppress repeated equal observations and create append-only lifecycle actions."""

    def __init__(self, strength_delta: float = 0.1) -> None:
        self.strength_delta = strength_delta
        self._active: dict[tuple[str, str], _SignalMemory] = {}

    def action_for(self, event: MarketEvent) -> LifecycleAction | None:
        action = self.preview_action(event)
        if action is not None:
            self.commit_action(event, action)
        return action

    def preview_action(self, event: MarketEvent) -> LifecycleAction | None:
        """Determine an action without changing lifecycle memory."""
        key = (event.instrument_id, event.event_type)
        previous = self._active.get(key)
        if previous is None:
            return LifecycleAction.START
        delta = event.strength - previous.strength
        if delta >= self.strength_delta:
            return LifecycleAction.STRENGTHENED
        if delta <= -self.strength_delta:
            return LifecycleAction.WEAKENED
        return None

    def commit_action(self, event: MarketEvent, action: LifecycleAction) -> None:
        if action not in {
            LifecycleAction.START,
            LifecycleAction.STRENGTHENED,
            LifecycleAction.WEAKENED,
        }:
            raise ValueError(f"cannot commit lifecycle action {action}")
        self._active[(event.instrument_id, event.event_type)] = _SignalMemory(
            event.strength, event.event_id
        )

    def normalize(self, instrument_id: str, event_type: str) -> str | None:
        item = self._active.pop((instrument_id, event_type), None)
        return item.event_id if item else None

    def preview_normalize(self, instrument_id: str, event_type: str) -> str | None:
        item = self._active.get((instrument_id, event_type))
        return item.event_id if item else None

    def commit_normalize(self, instrument_id: str, event_type: str) -> None:
        self.normalize(instrument_id, event_type)

    def active_types(self, instrument_id: str) -> set[str]:
        return {event_type for active_instrument, event_type in self._active if active_instrument == instrument_id}
