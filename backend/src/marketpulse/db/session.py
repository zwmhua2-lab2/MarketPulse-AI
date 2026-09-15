from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from marketpulse.config import Settings


@dataclass
class DatabaseResources:
    """One owned engine plus the session factory derived from it.

    The engine handle and its factory travel together so the composing owner (the
    Integrated Runtime Host, or a validation harness) can dispose the exact engine it
    created. Before this bundle existed the factory outlived its engine reference and no
    production component could dispose it, which is the ownership gap the accepted
    PRE-01B-D1 contract closes under "DB ownership". Nothing here is request-scoped: one
    owner constructs it once and disposes it once.
    """

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession] = field(init=False)
    disposed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        """Dispose the owned engine, and stay truthful about whether that happened.

        Idempotent: a second call is a no-op, not a re-dispose. ``disposed`` is set only
        *after* ``engine.dispose()`` returned, so a disposal that raises leaves the flag
        ``False`` and no caller can mistake an undisposed engine for a released one.
        """
        if self.disposed:
            return
        await self.engine.dispose()
        self.disposed = True


def create_database_resources(
    settings: Settings, *, application_name: str | None = None
) -> DatabaseResources:
    """Construct an owned engine/factory bundle.

    This is the only way production code opens an engine. It deliberately has no
    "return the factory only" sibling: a factory whose owning engine handle was dropped
    cannot be disposed by anyone, which is exactly the hidden-engine ownership gap the
    accepted PRE-01B-D1 contract closed. `application_name` is set per connection so
    PostgreSQL can attribute every session to its owning lifecycle; it never carries a
    DSN, a credential or a query.
    """
    connect_args: dict[str, object] = {}
    if application_name:
        connect_args["server_settings"] = {"application_name": application_name}
    engine = create_async_engine(
        settings.database_url, pool_pre_ping=True, connect_args=connect_args
    )
    return DatabaseResources(engine=engine)
