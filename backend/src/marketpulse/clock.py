from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class ReplayClock:
    def __init__(self, current: datetime):
        self._current = current.astimezone(UTC)

    def now(self) -> datetime:
        return self._current

    def advance_to(self, current: datetime) -> None:
        self._current = current.astimezone(UTC)

