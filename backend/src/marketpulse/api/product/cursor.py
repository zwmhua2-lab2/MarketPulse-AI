"""Small endpoint- and filter-bound opaque cursor codec for Product collections."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

CURSOR_VERSION = "ui-rd01-cursor-v1"


class ProductCursorError(ValueError):
    pass


@dataclass(frozen=True)
class IncidentCursor:
    opened_at: datetime
    incident_id: str


def incident_filter_fingerprint(*, incident_status: str | None, incident_type: str | None) -> str:
    material = json.dumps(
        {"incident_status": incident_status, "incident_type": incident_type},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def encode_incident_cursor(cursor: IncidentCursor, *, filter_fingerprint: str) -> str:
    payload = {
        "v": CURSOR_VERSION,
        "endpoint": "system.incidents",
        "filters": filter_fingerprint,
        "opened_at": cursor.opened_at.isoformat(),
        "incident_id": cursor.incident_id,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def decode_incident_cursor(value: str, *, filter_fingerprint: str) -> IncidentCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(payload, dict):
            raise ProductCursorError("cursor payload is not an object")
        if payload.get("v") != CURSOR_VERSION or payload.get("endpoint") != "system.incidents":
            raise ProductCursorError("cursor endpoint or version does not match")
        if payload.get("filters") != filter_fingerprint:
            raise ProductCursorError("cursor filters do not match")
        opened_at = datetime.fromisoformat(str(payload["opened_at"]))
        incident_id = payload["incident_id"]
        if opened_at.tzinfo is None or not isinstance(incident_id, str) or not incident_id:
            raise ProductCursorError("cursor sort tuple is invalid")
        return IncidentCursor(opened_at=opened_at, incident_id=incident_id)
    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductCursorError("invalid product cursor") from exc
