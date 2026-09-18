"""Bounded Advisory DB capacity with exact return-completion authority."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Self
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class AdvisoryFenceError(RuntimeError):
    """An invalid capacity-lease operation."""


@dataclass(frozen=True)
class AdvisoryCheckoutKey:
    """Application identity; never a DBAPI address, timestamp, or callback order."""

    runtime_epoch: str
    pool_entry_id: str
    checkout_generation: int


@dataclass
class _LeaseRecord:
    lease_id: str
    lease_kind: str = "ORDINARY"
    key: AdvisoryCheckoutKey | None = None
    cleanup_attempt_id: str | None = None
    checkin_observed: bool = False
    hard_invalidated: bool = False
    checkin_none: bool = False
    owner_completed: bool = False
    state: str = "ACQUIRED_UNBOUND"


@dataclass
class AdvisoryDbLease:
    _fence: AdvisoryDbFence
    lease_id: str

    def bind(self, key: AdvisoryCheckoutKey, cleanup_attempt_id: str) -> None:
        self._fence.bind(self, key, cleanup_attempt_id)

    def retire_uncertain(self) -> None:
        self._fence.retire_uncertain(self)


@dataclass
class AdvisoryDbLeaseOwner:
    """Reports owner success only after the enclosing Session context has closed."""

    lease: AdvisoryDbLease | None = None
    cleanup_attempt_id: str = ""

    async def __aenter__(self) -> Self:
        self.cleanup_attempt_id = uuid4().hex
        return self

    async def __aexit__(self, exc_type: object, *_: object) -> None:
        if self.lease is None:
            return
        if exc_type is None:
            self.lease._fence.owner_completed(self.lease, self.cleanup_attempt_id)
        else:
            self.lease.retire_uncertain()


class AdvisoryDbFence:
    """A bounded limiter where uncertain holders permanently consume Advisory capacity."""

    def __init__(
        self,
        *,
        effective_db_capacity: int,
        protection_reserve: int,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        runtime_epoch: str | None = None,
    ) -> None:
        if effective_db_capacity <= 0:
            raise ValueError("effective_db_capacity must be positive")
        if protection_reserve <= 0 or protection_reserve >= effective_db_capacity:
            raise ValueError("protection_reserve must be positive and below effective capacity")
        self._limit = effective_db_capacity - protection_reserve
        self._protection_limit = protection_reserve
        self._protection_held = 0
        self._session_factory = session_factory
        self.runtime_epoch = runtime_epoch or uuid4().hex
        self._records: dict[str, _LeaseRecord] = {}
        self._closed = False
        self._listener_installed = False

    @property
    def capacity(self) -> int:
        return self._limit

    @property
    def held(self) -> int:
        return len(self._records)

    @property
    def available(self) -> int:
        return self._limit - self.held

    @property
    def uncertain(self) -> int:
        return sum(item.state == "RETURN_UNCERTAIN_RETIRED" for item in self._records.values())

    @property
    def closed(self) -> bool:
        return self._closed

    def close_new_acquisition(self) -> None:
        self._closed = True

    def try_acquire(self) -> AdvisoryDbLease | None:
        """Immediate only: a full/closed fence performs no DB work or wait."""

        return self._try_acquire(lease_kind="ORDINARY")

    def try_acquire_terminal_write(self) -> AdvisoryDbLease | None:
        """Take one immediate terminal-write lease from Advisory capacity A.

        This is deliberately a distinct acquisition path, but not a second pool or
        a Protection-R borrow: its holder is counted in the same exact-return
        registry and against the same Advisory capacity bound as ordinary work.
        """

        return self._try_acquire(lease_kind="TERMINAL_WRITE")

    def _try_acquire(self, *, lease_kind: str) -> AdvisoryDbLease | None:
        if self._closed or self.held >= self._limit:
            return None
        lease_id = uuid4().hex
        self._records[lease_id] = _LeaseRecord(lease_id=lease_id, lease_kind=lease_kind)
        return AdvisoryDbLease(self, lease_id)

    def can_acquire(self) -> bool:
        """A non-mutating admission probe; it never creates/retires a lease."""

        return not self._closed and self.held < self._limit

    def bind(self, lease: AdvisoryDbLease, key: AdvisoryCheckoutKey, cleanup_attempt_id: str) -> None:
        record = self._record(lease)
        if record.key is not None or not cleanup_attempt_id:
            raise AdvisoryFenceError("lease binding is immutable and requires a cleanup attempt")
        if key.runtime_epoch != self.runtime_epoch or key.checkout_generation <= 0:
            raise AdvisoryFenceError("lease key is not authoritative for this runtime epoch")
        record.key = key
        record.cleanup_attempt_id = cleanup_attempt_id
        record.state = "HELD"

    def observe_pool_return(
        self, key: AdvisoryCheckoutKey, cleanup_attempt_id: str, *, checkin_none: bool = False
    ) -> None:
        record = self._matching_record(key, cleanup_attempt_id)
        if record is None or record.state == "RELEASE_CONFIRMED":
            return
        record.checkin_observed = True
        record.checkin_none = checkin_none
        record.state = "RETURN_PENDING"
        self._settle(record)

    def observe_hard_invalidation(self, key: AdvisoryCheckoutKey, cleanup_attempt_id: str) -> None:
        record = self._matching_record(key, cleanup_attempt_id)
        if record is None or record.state == "RELEASE_CONFIRMED":
            return
        record.hard_invalidated = True
        record.state = "INVALIDATE_PENDING"
        self._settle(record)

    def owner_completed(self, lease: AdvisoryDbLease, cleanup_attempt_id: str) -> None:
        record = self._record(lease)
        if record.cleanup_attempt_id != cleanup_attempt_id or record.state == "RELEASE_CONFIRMED":
            return
        record.owner_completed = True
        record.state = "OWNER_COMPLETED_PENDING_POOL_CONFIRMATION"
        self._settle(record)

    def retire_uncertain(self, lease: AdvisoryDbLease) -> None:
        record = self._record(lease)
        if record.state != "RELEASE_CONFIRMED":
            record.state = "RETURN_UNCERTAIN_RETIRED"

    def snapshot(self) -> dict[str, int | bool]:
        return {"capacity": self.capacity, "held": self.held, "available": self.available,
                "uncertain": self.uncertain, "closed": self.closed}

    def install_pool_listeners(self, sync_engine: object) -> None:
        """Install public PoolEvents once; this class never owns caller Sessions."""

        if self._listener_installed:
            return

        def checkout(_: object, record: Any, proxy: Any) -> None:
            record_info = record.record_info
            connection_info = proxy.info
            entry = record_info.setdefault("advisory_pool_entry_id", uuid4().hex)
            generation = int(record_info.get("advisory_checkout_generation", 0)) + 1
            record_info["advisory_checkout_generation"] = generation
            connection_info["advisory_checkout_key"] = AdvisoryCheckoutKey(self.runtime_epoch, entry, generation)

        def invalidate(_: object, record: Any, __: object) -> None:
            self._observe_record(record, checkin_none=True, invalidated=True)

        def checkin(dbapi_connection: object, record: Any) -> None:
            self._observe_record(record, checkin_none=dbapi_connection is None, invalidated=False)

        event.listen(sync_engine, "checkout", checkout)
        event.listen(sync_engine, "invalidate", invalidate)
        event.listen(sync_engine, "checkin", checkin)
        self._listener_installed = True

    def _observe_record(self, record: Any, *, checkin_none: bool, invalidated: bool) -> None:
        info = record.record_info
        entry, generation = info.get("advisory_pool_entry_id"), info.get("advisory_checkout_generation")
        if not isinstance(entry, str) or not isinstance(generation, int):
            return
        key = AdvisoryCheckoutKey(self.runtime_epoch, entry, generation)
        for item in list(self._records.values()):
            if item.key != key or item.cleanup_attempt_id is None:
                continue
            if invalidated:
                self.observe_hard_invalidation(key, item.cleanup_attempt_id)
            else:
                self.observe_pool_return(key, item.cleanup_attempt_id, checkin_none=checkin_none)

    def _settle(self, record: _LeaseRecord) -> None:
        normal = record.checkin_observed and not record.checkin_none
        invalidated = record.hard_invalidated and record.checkin_observed and record.checkin_none
        if record.owner_completed and (normal or invalidated):
            record.state = "RELEASE_CONFIRMED"
            del self._records[record.lease_id]

    def _record(self, lease: AdvisoryDbLease) -> _LeaseRecord:
        if lease._fence is not self or lease.lease_id not in self._records:
            raise AdvisoryFenceError("unknown or already released advisory DB lease")
        return self._records[lease.lease_id]

    def _matching_record(self, key: AdvisoryCheckoutKey, cleanup_attempt_id: str) -> _LeaseRecord | None:
        for record in self._records.values():
            if record.key == key and record.cleanup_attempt_id == cleanup_attempt_id:
                return record
        return None

    @asynccontextmanager
    async def transaction(self):
        """Fence-owned path; identity failure retires capacity rather than releasing it."""

        async with self._leased_transaction(terminal_write=False) as session:
            yield session

    @asynccontextmanager
    async def terminal_write_transaction(self):
        """Bounded, no-reserve terminal write path under the same Advisory fence."""

        async with self._leased_transaction(terminal_write=True) as session:
            yield session

    @asynccontextmanager
    async def _leased_transaction(self, *, terminal_write: bool):
        if self._session_factory is None:
            raise AdvisoryFenceError("ordinary advisory database access is not configured")
        lease = self.try_acquire_terminal_write() if terminal_write else self.try_acquire()
        if lease is None:
            raise AdvisoryFenceError("advisory DB capacity unavailable")
        owner = AdvisoryDbLeaseOwner(lease=lease)
        try:
            async with owner, self._session_factory() as session, session.begin():
                connection = await session.connection()
                key = connection.info.get("advisory_checkout_key")
                if not isinstance(key, AdvisoryCheckoutKey):
                    lease.retire_uncertain()
                    raise AdvisoryFenceError("advisory pool lease identity is unavailable")
                lease.bind(key, owner.cleanup_attempt_id)
                yield session
        except BaseException:
            if lease.lease_id in self._records:
                lease.retire_uncertain()
            raise

    @asynccontextmanager
    async def protection_transaction(self):
        if self._session_factory is None:
            raise AdvisoryFenceError("ordinary advisory database access is not configured")
        if self._protection_held >= self._protection_limit:
            raise AdvisoryFenceError("advisory protection capacity unavailable")
        self._protection_held += 1
        try:
            async with self._session_factory() as session, session.begin():
                yield session
        finally:
            self._protection_held -= 1


__all__ = ["AdvisoryCheckoutKey", "AdvisoryDbFence", "AdvisoryDbLease", "AdvisoryDbLeaseOwner", "AdvisoryFenceError"]
