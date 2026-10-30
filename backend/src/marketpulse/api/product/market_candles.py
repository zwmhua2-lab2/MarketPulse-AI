"""Standalone authenticated read of recent, closed OKX spot candles."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from marketpulse.api.auth import verify_session
from marketpulse.config import Settings, get_settings

PATH = "/api/v1/product/market-candles"
router = APIRouter(tags=["product-read"])
_STEP = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000}
_OKX_BAR = {"5m": "5m", "15m": "15m", "1h": "1H"}
_NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def _now() -> datetime:
    return datetime.now(UTC)


def _unavailable() -> HTTPException:
    return HTTPException(503, "market data unavailable")


def _decimal(value: object, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not _NUMBER.fullmatch(value):
        raise ValueError("invalid decimal")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise ValueError("invalid decimal")
    return number


def _candles(data: object, *, step: int, now_ms: int) -> list[dict[str, object]]:
    if not isinstance(data, list) or len(data) not in (60, 61):
        raise ValueError("invalid candle count")
    parsed = []
    for row in data:
        if not isinstance(row, list) or len(row) != 9 or any(not isinstance(x, str) for x in row):
            raise ValueError("invalid candle row")
        ts = row[0]
        if not ts.isascii() or not ts.isdigit() or str(int(ts)) != ts:
            raise ValueError("invalid timestamp")
        stamp = int(ts)
        if stamp % step:
            raise ValueError("unaligned timestamp")
        o, h, low, c, _volume = (_decimal(v, positive=i < 4) for i, v in enumerate(row[1:6]))
        if h < max(o, low, c) or low > min(o, c) or row[8] not in ("0", "1"):
            raise ValueError("invalid OHLC or confirmation")
        parsed.append((stamp, row, h, low))
    parsed.sort(key=lambda item: item[0])
    if len({item[0] for item in parsed}) != len(parsed):
        raise ValueError("duplicate timestamp")
    edge = now_ms // step * step
    closed = [item for item in parsed if item[1][8] == "1"]
    forming = [item for item in parsed if item[1][8] == "0"]
    if len(closed) != 60 or len(forming) > 1 or (forming and forming[0][0] != edge):
        raise ValueError("invalid confirmation window")
    expected = [edge - step * i for i in range(60, 0, -1)]
    if [item[0] for item in closed] != expected:
        raise ValueError("incomplete candle window")
    if now_ms - (closed[-1][0] + step) > step + 30_000:
        raise ValueError("stale candles")
    return [
        {
            "open_time_ms": ts,
            "close_time_ms": ts + step,
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
            "confirmed": True,
        }
        for ts, row, _, _ in closed
    ]


@router.get(PATH)
async def market_candles(
    request: Request,
    instrument_id: Literal["BTC-USDT", "ETH-USDT"] = Query(...),
    bar: Literal["5m", "15m", "1h"] = Query("5m"),
    _: str = Depends(verify_session),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, object]:
    if set(request.query_params) - {"instrument_id", "bar"}:
        raise HTTPException(422, "unsupported query parameter")
    observed = _now()
    try:
        async with httpx.AsyncClient(base_url=settings.okx_rest_url, timeout=10) as client:
            response = await client.get(
                "/api/v5/market/candles",
                params={"instId": instrument_id, "bar": _OKX_BAR[bar], "limit": "61"},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") != "0":
            raise ValueError("invalid OKX response")
        observed_ms = int(observed.timestamp()) * 1000 + observed.microsecond // 1000
        items = _candles(payload.get("data"), step=_STEP[bar], now_ms=observed_ms)
    except Exception as exc:  # provider errors are intentionally non-disclosing
        raise _unavailable() from exc
    return {
        "source": "OKX_PUBLIC_REST",
        "instrument_id": instrument_id,
        "bar": bar,
        "observed_at": observed.isoformat(),
        "data_quality": "FRESH",
        "items": items,
    }
