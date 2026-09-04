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
        key = (event.instrument_id, event.event_type)
        previous = self._active.get(key)
        if previous is None:
            self._active[key] = _SignalMemory(event.strength, event.event_id)
            return LifecycleAction.START
        delta = event.strength - previous.strength
        if delta >= self.strength_delta:
            self._active[key] = _SignalMemory(event.strength, event.event_id)
            return LifecycleAction.STRENGTHENED
        if delta <= -self.strength_delta:
            self._active[key] = _SignalMemory(event.strength, event.event_id)
            return LifecycleAction.WEAKENED
        return None

    def normalize(self, instrument_id: str, event_type: str) -> str | None:
        item = self._active.pop((instrument_id, event_type), None)
        return item.event_id if item else None

    def active_types(self, instrument_id: str) -> set[str]:
        return {event_type for active_instrument, event_type in self._active if active_instrument == instrument_id}
