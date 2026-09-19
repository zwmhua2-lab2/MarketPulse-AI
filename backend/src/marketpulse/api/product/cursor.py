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


@dataclass(frozen=True)
class MarketScannerCursor:
    requested_range: str
    effective_start: datetime
    effective_end: datetime
    event_time: datetime
    event_id: str


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


def market_scanner_filter_fingerprint() -> str:
    """The Scanner currently has no user filters; keep the cursor binding explicit."""
    return hashlib.sha256(b"{}").hexdigest()


def encode_market_scanner_cursor(cursor: MarketScannerCursor) -> str:
    payload = {
        "v": CURSOR_VERSION,
        "endpoint": "market-scanner",
        "filters": market_scanner_filter_fingerprint(),
        "provenance": "FORWARD_PAPER",
        "range": cursor.requested_range,
        "effective_start": cursor.effective_start.isoformat(),
        "effective_end": cursor.effective_end.isoformat(),
        "event_time": cursor.event_time.isoformat(),
        "event_id": cursor.event_id,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def decode_market_scanner_cursor(value: str) -> MarketScannerCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(payload, dict):
            raise ProductCursorError("cursor payload is not an object")
        if payload.get("v") != CURSOR_VERSION or payload.get("endpoint") != "market-scanner":
            raise ProductCursorError("cursor endpoint or version does not match")
        if payload.get("filters") != market_scanner_filter_fingerprint():
            raise ProductCursorError("cursor filters do not match")
        if payload.get("provenance") != "FORWARD_PAPER":
            raise ProductCursorError("cursor provenance does not match")
        requested_range = payload["range"]
        effective_start = datetime.fromisoformat(str(payload["effective_start"]))
        effective_end = datetime.fromisoformat(str(payload["effective_end"]))
        event_time = datetime.fromisoformat(str(payload["event_time"]))
        event_id = payload["event_id"]
        if (
            effective_start.tzinfo is None
            or effective_end.tzinfo is None
            or event_time.tzinfo is None
            or effective_start >= effective_end
            or not effective_start <= event_time < effective_end
            or not isinstance(requested_range, str)
            or not requested_range
            or not isinstance(event_id, str)
            or not event_id
        ):
            raise ProductCursorError("cursor range or sort tuple is invalid")
        return MarketScannerCursor(
            requested_range=requested_range,
            effective_start=effective_start,
            effective_end=effective_end,
            event_time=event_time,
            event_id=event_id,
        )
    except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductCursorError("invalid market scanner cursor") from exc
