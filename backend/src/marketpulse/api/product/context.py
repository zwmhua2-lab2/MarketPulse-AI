"""Non-owning request facade over the current RuntimeHost."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketpulse.runtime_host import (
    ProductCurrentMarketSnapshot,
    ProductRuntimeSnapshot,
    RecoverySnapshot,
    RuntimeHost,
)


@dataclass(frozen=True)
class ProductReadContext:
    """Nullable, read-only borrower of Host-owned Product read capabilities."""

    host: RuntimeHost | None
    sessions: async_sessionmaker[AsyncSession] | None

    @classmethod
    def from_request(cls, request: Request) -> ProductReadContext:
        host = getattr(request.app.state, "host", None)
        if not isinstance(host, RuntimeHost):
            return cls(host=None, sessions=None)
        return cls(host=host, sessions=host.product_read_session_factory)

    def runtime_snapshot(self) -> ProductRuntimeSnapshot | None:
        return None if self.host is None else self.host.product_runtime_snapshot()

    def market_snapshot(self) -> ProductCurrentMarketSnapshot | None:
        return None if self.host is None else self.host.product_market_snapshot()

    def recovery_snapshot(self) -> RecoverySnapshot | None:
        return None if self.host is None else self.host.recovery_snapshot
