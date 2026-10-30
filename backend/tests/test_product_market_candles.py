"""Offline contract tests for the standalone OKX candle router (GWT-DATA-01..07)."""

from datetime import UTC, datetime
from itertools import pairwise

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from marketpulse.api.auth import _token
from marketpulse.api.product import market_candles as candles
from marketpulse.config import Settings, get_settings

NOW = datetime(2026, 10, 30, 12, 2, tzinfo=UTC)
MS = int(NOW.timestamp() * 1000)
PERIOD = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000}


def rows(bar="5m", *, n=61, bad=None):
    step = PERIOD[bar]
    edge = MS // step * step
    result = []
    for i in range(n):
        ts = edge - i * step
        result.append(
            [str(ts), "10.00", "12.00", "9.00", "11.00", "2.50", "", "", "0" if i == 0 else "1"]
        )
    if bad:
        bad(result)
    return result

@pytest.fixture
def harness(monkeypatch):
    calls, state = [], {"payload": None, "status": 200, "error": None}

    class Response:
        @property
        def status_code(self):
            return state["status"]

        def raise_for_status(self):
            if state["status"] >= 400:
                raise RuntimeError("private upstream body")

        def json(self):
            return state["payload"]

    class Client:
        def __init__(self, **kw):
            assert kw["timeout"] == 10

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            pass

        async def get(self, path, *, params):
            calls.append((path, params))
            if state["error"]:
                raise state["error"]
            if state["payload"] is None:
                state["payload"] = {"code": "0", "data": rows(params["bar"].replace("H", "h"))}
            return Response()

    monkeypatch.setattr(candles.httpx, "AsyncClient", Client)
    monkeypatch.setattr(candles, "_now", lambda: NOW)
    settings = Settings(
        session_secret="test-secret", admin_username="admin", okx_rest_url="https://mock.okx"
    )
    app = FastAPI()
    app.include_router(candles.router)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), state, calls, settings


def auth(settings):
    return {"Authorization": f"Bearer {_token(settings, 'admin')}"}

@pytest.mark.parametrize(
    "instrument,bar,okx",
    [
        (s, b, o)
        for s in ("BTC-USDT", "ETH-USDT")
        for b, o in (("5m", "5m"), ("15m", "15m"), ("1h", "1H"))
    ],
)
def test_gwt_data_01_allowed_symbols_periods_and_mapping(harness, instrument, bar, okx):
    assert candles.PATH == "/api/v1/product/market-candles"
    assert candles.router.routes[0].path == candles.PATH
    client, _, calls, settings = harness
    response = client.get(
        candles.PATH, params={"instrument_id": instrument, "bar": bar}, headers=auth(settings)
    )
    assert response.status_code == 200 and calls[0][1] == {
        "instId": instrument,
        "bar": okx,
        "limit": "61",
    }
    for params in ({"bar": "1D"}, {"instrument_id": "BTC-USDT-SWAP"}, {"extra": "x"}, {}):
        before = len(calls)
        assert client.get(candles.PATH, params=params, headers=auth(settings)).status_code == 422
        assert len(calls) == before

def test_gwt_data_02_returns_sixty_exact_sorted_confirmed_values(harness):
    client, _, calls, settings = harness
    r = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    data = r.json()
    items = data["items"]
    assert r.status_code == 200 and len(items) == 60
    assert data["source"] == "OKX_PUBLIC_REST" and data["data_quality"] == "FRESH"
    assert [x["open_time_ms"] for x in items] == sorted(x["open_time_ms"] for x in items)
    assert all(b["open_time_ms"] - a["open_time_ms"] == PERIOD["5m"] for a, b in pairwise(items))
    assert (
        items[-1]["open"] == "10.00"
        and items[-1]["volume"] == "2.50"
        and items[-1]["confirmed"] is True
    )
    assert items[-1]["close_time_ms"] == items[-1]["open_time_ms"] + PERIOD["5m"]
    assert calls[0][0] == "/api/v5/market/candles"

@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop(2),
        lambda r: r[2].__setitem__(0, r[1][0]),
        lambda r: r[2].__setitem__(8, "0"),
        lambda r: r[2].__setitem__(0, str(int(r[2][0]) + 1)),
        lambda r: r[1].__setitem__(0, str(MS + PERIOD["5m"])),
    ],
)
def test_gwt_data_03_bad_window_fails_closed(harness, mutate):
    client, state, _, settings = harness
    state["payload"] = {"code": "0", "data": rows()}; mutate(state["payload"]["data"])
    r = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert r.status_code == 503 and "private" not in r.text and "10.00" not in r.text

@pytest.mark.parametrize(
    "payload",
    [
        {"code": "500", "data": []},
        {"code": "0", "data": [["1"]]},
        {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(1, "NaN"))},
        {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(1, "Infinity"))},
        {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(1, "1e2"))},
        {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(5, "-1"))},
        {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(2, "8"))},
    ],
)
def test_gwt_data_04_malformed_provider_data_is_sanitized(harness, payload):
    client, state, _, settings = harness
    state["payload"] = payload
    r = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert r.status_code == 503 and "NaN" not in r.text and "Infinity" not in r.text
    assert "private" not in r.text

@pytest.mark.parametrize(
    "failure", [429, 500, 504, TimeoutError("secret timeout"), ConnectionError("secret connection")]
)
def test_gwt_data_05_failures_are_503_without_retry(harness, failure):
    client, state, calls, settings = harness
    state["status" if isinstance(failure, int) else "error"] = failure
    r = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert (
        r.status_code == 503
        and len(calls) == 1
        and "secret" not in r.text
        and "private" not in r.text
    )

def test_gwt_data_06_authentication_precedes_upstream(harness):
    client, _, calls, settings = harness
    assert client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}).status_code == 401
    assert not calls
    assert (
        client.get(
            candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings)
        ).status_code
        == 200
    )
    assert len(calls) == 1
