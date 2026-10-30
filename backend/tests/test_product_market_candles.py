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
            [str(ts), "10.00", "12.00", "9.00", "11.00", "2.50", "3.75", "41.25", "0" if i == 0 else "1"]
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
            if state.get("response_now") is not None:
                monkeypatch.setattr(candles, "_now", lambda: state["response_now"])
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


def test_gwt_b04_accepts_exactly_sixty_closed_candles(harness):
    client, state, _, settings = harness
    state["payload"] = {"code": "0", "data": rows()[1:]}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert response.status_code == 200 and len(response.json()["items"]) == 60


@pytest.mark.parametrize("field,value", [(i, v) for i in (6, 7) for v in ("", "NaN", "Infinity", "1e2", "-1")])
def test_gwt_b03_rejects_invalid_quote_volumes(harness, field, value):
    client, state, _, settings = harness
    state["payload"] = {"code": "0", "data": rows(bad=lambda r: r[2].__setitem__(field, value))}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert response.status_code == 503 and "items" not in response.json()


def test_gwt_b03_allows_zero_quote_volumes_without_exposing_them(harness):
    client, state, _, settings = harness
    state["payload"] = {"code": "0", "data": rows(bad=lambda r: (r[2].__setitem__(6, "0"), r[2].__setitem__(7, "0")))}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert response.status_code == 200
    assert "volCcy" not in response.text and "volCcyQuote" not in response.text


def test_gwt_b04_rejects_old_complete_window(harness):
    client, state, _, settings = harness
    data = rows()[1:]
    for row in data:
        row[0] = str(int(row[0]) - PERIOD["5m"])
    state["payload"] = {"code": "0", "data": data}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert response.status_code == 503


def test_gwt_b04_rejects_aligned_future_candle(harness):
    client, state, _, settings = harness
    data = rows()[1:-1]
    future = rows()[0].copy()
    future[0], future[8] = str(int(future[0]) + PERIOD["5m"]), "1"
    data.append(future)
    state["payload"] = {"code": "0", "data": data}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
    assert response.status_code == 503


@pytest.mark.parametrize("bar,minute", [("5m", 5), ("15m", 15), ("1h", 0)])
def test_gwt_b04_uses_post_response_observation_time(harness, bar, minute):
    client, state, _, settings = harness
    response_now = NOW.replace(hour=13, minute=minute, second=1) if bar == "1h" else NOW.replace(minute=minute, second=1)
    step = PERIOD[bar]
    data = rows(bar)[1:]
    for row in data:
        row[0] = str(int(row[0]) + step)
    state["response_now"] = response_now
    state["payload"] = {"code": "0", "data": data}
    response = client.get(candles.PATH, params={"instrument_id": "BTC-USDT", "bar": bar}, headers=auth(settings))
    observed_at = datetime.fromisoformat(response.json()["observed_at"])
    assert response.status_code == 200 and observed_at == response_now


@pytest.mark.parametrize(
    "query",
    [
        [("instrument_id", "BTC-USDT"), ("instrument_id", "ETH-USDT")],
        [("instrument_id", "BTC-USDT"), ("bar", "5m"), ("bar", "15m")],
    ],
)
def test_gwt_b05_rejects_duplicate_query_keys_without_upstream(harness, query):
    client, _, calls, settings = harness
    response = client.get(candles.PATH, params=query, headers=auth(settings))
    assert response.status_code == 422 and not calls


def test_gwt_b01_b02_registers_precisely_typed_authenticated_route(harness, monkeypatch):
    import marketpulse.api.app as app_module

    _, state, calls, settings = harness
    monkeypatch.setattr(app_module, "settings", settings)
    monkeypatch.setattr(app_module, "RuntimeHost", lambda *_: pytest.fail("RuntimeHost started"))
    application = app_module.create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    expected_paths = {
        "/api/v1/auth/login", "/api/v1/health", "/api/v1/live", "/api/v1/market/instruments",
        "/api/v1/product/market-scanner", "/api/v1/product/opportunities",
        "/api/v1/product/opportunities/{opportunity_id}", "/api/v1/product/system",
        "/api/v1/product/trading-audit", "/api/v1/protected/ping", "/api/v1/ready",
        "/api/v1/runtime", "/api/v1/universe", candles.PATH,
    }
    with TestClient(application) as client:
        assert application.state.host is None
        spec = client.get("/openapi.json").json()
        operation = spec["paths"][candles.PATH]["get"]
        assert set(spec["paths"]) == expected_paths and set(spec["paths"][candles.PATH]) == {"get"}
        responses = operation["responses"]
        success_name = responses["200"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
        error_name = responses["503"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
        success = spec["components"]["schemas"][success_name]
        error = spec["components"]["schemas"][error_name]
        assert set(success["properties"]) == {"source", "instrument_id", "bar", "observed_at", "data_quality", "items"}
        item_ref = success["properties"]["items"]["items"]["$ref"].split("/")[-1]
        item = spec["components"]["schemas"][item_ref]
        assert set(item["properties"]) == {"open_time_ms", "close_time_ms", "open", "high", "low", "close", "volume", "confirmed"}
        assert success.get("additionalProperties") is not True
        assert set(error["properties"]) == {"detail"}
        assert client.get("/api/v1/live").json()["status"] == "disabled"
        assert client.get("/api/v1/ready").status_code == 503
        assert client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}).status_code == 401
        assert not calls
        assert client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings)).status_code == 200
        state["status"] = 503
        unavailable = client.get(candles.PATH, params={"instrument_id": "BTC-USDT"}, headers=auth(settings))
        assert unavailable.status_code == 503 and unavailable.json() == {"detail": "market data unavailable"}

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
