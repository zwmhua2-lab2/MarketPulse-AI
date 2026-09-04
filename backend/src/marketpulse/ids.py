from datetime import UTC, datetime
from uuid import UUID, uuid4


def new_id() -> UUID:
    """Use UUIDv4 as the portable V1 identifier convention."""
    return uuid4()


def utc_now_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


VERSION = "v1"

