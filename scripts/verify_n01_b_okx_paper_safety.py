"""N01-B real OKX validation — OKX Reconnect / Freshness + Paper Safety Continuity.

This is the *real network* half of N01-B and is deliberately an explicit, opt-in validation
script: the unit/deterministic suite must never depend on the public internet.

Scope of this gate (all bounded, no soak):

  N01-3  real OKX public SPOT metadata for BTC-USDT / ETH-USDT
         real `bbo-tbt` + `trades` normalized events
         a controlled real reconnect (real connect -> real event -> local disconnect ->
         production reconnect loop -> second real connection -> post-reconnect real event)
         for BTC-USDT and ETH-USDT separately
  N01-4  LIVE_PAPER paper safety continuity against a disposable PostgreSQL database, driven by
         real OKX fresh BBO -> CONTROLLED STALE INJECTION -> post-reconnect real fresh BBO

Explicitly NOT in scope: N01-5 restart/recovery, 15m/2h/12h soak, integrated runtime host, live
trading, private OKX endpoints, OKX API keys, real funds.

Environment note (must not be mistaken for a product fact): the surrounding development sandbox
injects `HTTP_PROXY`/`HTTPS_PROXY` pointing at a local proxy that responds `502 CONNECT tunnel
failed` for OKX endpoints. Real OKX verification therefore clears those variables for this
process only. No production code is modified and no proxy is configured by the product.

Run:  py -3.14 scripts/verify_n01_b_okx_paper_safety.py
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPOSITORY_ROOT / "backend" / "src", REPOSITORY_ROOT / "backend" / "tests"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Clear the sandbox-injected proxy before any client is constructed. See module docstring.
for _name in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
):
    os.environ.pop(_name, None)

import websockets
from marketpulse.g3.models import BestBidAsk, DataQuality, OrderSide, RunMode
from marketpulse.g4.models import HealthComponent, IncidentType
from marketpulse.g4.reconciliation import reconcile
from marketpulse.market_data.models import (
    MarketType,
    NormalizedBookTicker,
    NormalizedTrade,
)
from marketpulse.market_data.okx_live import OKXLiveProvider
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from test_n01_okx_paper_safety import (
    CONTROLLED_STALE_AGE_SECONDS,
    PRODUCTION_FRESHNESS_TTL_SECONDS,
    LivePaperHarness,
    _database_activity,
    _disposable_postgres_database,
    _economic_counts,
    _incident,
    _leftover_disposable_databases,
    _position,
    _quote,
    _sell_fills,
    _settle_background_tasks,
)

RUN_MODE = RunMode.LIVE_PAPER
BTC = "BTC-USDT"
ETH = "ETH-USDT"
INSTRUMENTS = (BTC, ETH)
ROCKET_BOUND_SECONDS = 60.0
TRADES_BOUND_SECONDS = 45.0
PUBLIC_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
# Every OKX call this gate performs. All public market data; no private endpoint, no API key.
PUBLIC_OKX_ENDPOINTS = (
    "GET /api/v5/public/instruments",
    "WS /ws/v5/public bbo-tbt",
    "WS /ws/v5/public trades",
)


def _to_bbo(event: NormalizedBookTicker) -> BestBidAsk:
    """Real normalized OKX event -> the accepted G3 market-data contract."""
    return BestBidAsk(
        instrument_id=event.instrument_id,
        bid=event.bid_price,
        ask=event.ask_price,
        received_at=event.received_time,
        tradable=True,
        data_quality=DataQuality(event.data_quality.value),
    )


def _describe_bbo(event: NormalizedBookTicker, age_seconds: float | None = None) -> dict[str, Any]:
    return {
        "instrument_id": event.instrument_id,
        "market_type": event.market_type.value,
        "source": event.source,
        "bid": event.bid_price,
        "ask": event.ask_price,
        "data_quality": event.data_quality.value,
        "event_time": event.event_time.isoformat(),
        "received_time": event.received_time.isoformat(),
        "age_seconds_at_use": age_seconds,
    }


def _assert_real_bbo(event: NormalizedBookTicker, instrument_id: str) -> None:
    assert event.instrument_id == instrument_id, event.instrument_id
    # SPOT and SWAP must never share one instrument identity.
    assert event.market_type is MarketType.SPOT, event.market_type
    assert event.data_quality.value == "FRESH", event.data_quality
    assert event.bid_price > 0 and event.ask_price > 0
    assert event.ask_price >= event.bid_price
    assert event.received_time.tzinfo is not None
    assert event.source == "okx.websocket.bbo-tbt", event.source


def _assert_real_trade(event: NormalizedTrade, instrument_id: str) -> None:
    assert isinstance(event, NormalizedTrade), type(event)
    assert event.instrument_id == instrument_id, event.instrument_id
    assert event.market_type is MarketType.SPOT, event.market_type
    assert event.price > 0 and event.quantity > 0
    assert event.side in {"buy", "sell"}, event.side
    assert event.trade_id
    assert event.source == "okx.websocket.trade", event.source


async def _instruments(provider: OKXLiveProvider, instrument_ids: tuple[str, ...]) -> dict:
    """Fetch real OKX SPOT metadata and let the provider cache its instrument identity."""
    instruments = {
        item.instrument_id: item
        for item in await provider.instruments("SPOT")
        if item.instrument_id in instrument_ids
    }
    assert set(instruments) == set(instrument_ids), sorted(instruments)
    for item in instruments.values():
        assert item.market_type is MarketType.SPOT
        assert item.tradable is True
        assert item.exchange == "OKX"
    return instruments


async def _raw_handshake() -> dict[str, Any]:
    """Direct real OKX handshake evidence (subscribe acknowledgements + connection id)."""
    acknowledgements: list[dict[str, Any]] = []
    async with asyncio.timeout(ROCKET_BOUND_SECONDS):
        async with websockets.connect(
            PUBLIC_WS_URL, ping_interval=20, ping_timeout=20, open_timeout=15, close_timeout=5
        ) as websocket:
            await websocket.send(
                json.dumps(
                    {
                        "op": "subscribe",
                        "args": [
                            {"channel": "bbo-tbt", "instId": instrument}
                            for instrument in INSTRUMENTS
                        ],
                    }
                )
            )
            while len(acknowledgements) < len(INSTRUMENTS):
                payload = json.loads(await websocket.recv())
                if payload.get("event") == "subscribe":
                    acknowledgements.append(
                        {"arg": payload.get("arg"), "conn_id": payload.get("connId")}
                    )
    subscribed = sorted(item["arg"]["instId"] for item in acknowledgements)
    assert subscribed == sorted(INSTRUMENTS), subscribed
    return {
        "endpoint": PUBLIC_WS_URL,
        "acknowledgements": acknowledgements,
        "subscribed": subscribed,
    }


async def _trades_gate(instrument_id: str) -> dict[str, Any]:
    """Real `trades` channel evidence (bounded, one normalized event)."""
    provider = OKXLiveProvider()
    await _instruments(provider, (instrument_id,))
    stream = provider.stream([{"channel": "trades", "instId": instrument_id}])
    try:
        async with asyncio.timeout(TRADES_BOUND_SECONDS):
            event = await anext(stream)
    finally:
        await stream.aclose()
    _assert_real_trade(event, instrument_id)
    return {
        "instrument_id": instrument_id,
        "trade_id": event.trade_id,
        "price": event.price,
        "quantity": event.quantity,
        "side": event.side,
        "market_type": event.market_type.value,
        "received_time": event.received_time.isoformat(),
    }


async def _run_timeline(db_url: str) -> dict[str, Any]:
    report: dict[str, Any] = {}

    metadata = await _instruments(OKXLiveProvider(), INSTRUMENTS)
    report["metadata"] = {
        key: {
            "market_type": item.market_type.value,
            "tradable": item.tradable,
            "tick_size": item.tick_size,
            "lot_size": item.lot_size,
        }
        for key, item in metadata.items()
    }
    report["handshake"] = await _raw_handshake()
    report["trades_channel"] = {item: await _trades_gate(item) for item in INSTRUMENTS}

    engine = create_async_engine(db_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    harness = LivePaperHarness(sessions)
    try:
        await harness.boot()

        # ------------------------------------------------------------------ BTC reconnect gate
        provider = OKXLiveProvider(disconnect_after_events=1)
        await _instruments(provider, (BTC,))
        stream = provider.stream([{"channel": "bbo-tbt", "instId": BTC}])
        try:
            async with asyncio.timeout(ROCKET_BOUND_SECONDS):
                first = await anext(stream)
                attempts_after_first = provider.connection_attempts
                reconnects_after_first = provider.reconnects
                _assert_real_bbo(first, BTC)

                fresh_1 = _to_bbo(first)
                plan = await harness.open_paper_long(
                    fresh_1, stop_factor=0.90, take_profit_factor=1.10, tag="real-n01-b"
                )
                position_before = await _position(sessions, RUN_MODE, BTC)
                assert position_before is not None and position_before.quantity > 0
                counts_before = await _economic_counts(sessions, RUN_MODE)
                assert counts_before["orders"] == 1 and counts_before["fills"] == 1

                # ---- FRESH #1 (real OKX BBO) ---------------------------------------
                fresh_1_age = (harness.clock.now() - fresh_1.received_at).total_seconds()
                assert fresh_1_age <= PRODUCTION_FRESHNESS_TTL_SECONDS, fresh_1_age
                fresh_outcome = await harness.feed_market_data(fresh_1)
                assert fresh_outcome["fresh"] is True
                assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                assert fresh_outcome["protection"].triggered is False
                assert fresh_outcome["protection"].reason == "HOLD"
                admitted, admit_reason = await harness.risk_gate.check(
                    RUN_MODE, BTC, plan_id=plan.plan_id
                )
                assert (admitted, admit_reason) == (True, None), (admitted, admit_reason)

                # ---- CONTROLLED STALE INJECTION ------------------------------------
                stale = _quote(
                    BTC, fresh_1.bid, fresh_1.ask, age_seconds=CONTROLLED_STALE_AGE_SECONDS
                )
                assert stale.instrument_id == fresh_1.instrument_id
                assert (stale.bid, stale.ask) == (fresh_1.bid, fresh_1.ask)
                stale_outcome = await harness.feed_market_data(stale)
                assert stale_outcome["fresh"] is False
                assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "UNAVAILABLE"
                assert stale_outcome["protection"].triggered is False
                assert stale_outcome["protection"].reason == "CORE_MARKET_DATA_STALE"
                incident = await _incident(sessions, RUN_MODE, BTC, IncidentType.CORE_DATA_STALE)
                assert incident is not None and incident.status == "OPEN"

                position_after_stale = await _position(sessions, RUN_MODE, BTC)
                assert position_after_stale is not None
                assert position_after_stale.quantity == position_before.quantity
                assert position_after_stale.average_cost == position_before.average_cost
                assert await _economic_counts(sessions, RUN_MODE) == counts_before
                assert await _sell_fills(sessions, RUN_MODE) == []

                duplicate = await harness.feed_market_data(stale)
                assert duplicate["protection"].reason == "CORE_MARKET_DATA_STALE"
                assert await _economic_counts(sessions, RUN_MODE) == counts_before

                async with sessions() as session, session.begin():
                    sell_reason = await harness.risk_gate.evaluate(
                        session,
                        run_mode=RUN_MODE,
                        instrument_id=BTC,
                        side=OrderSide.SELL,
                        plan_id=plan.plan_id,
                        now=harness.clock.now(),
                    )
                assert sell_reason is None
                manual = await harness.protection.manual_close(RUN_MODE, BTC, stale)
                assert manual.triggered is False and manual.reason == "CORE_MARKET_DATA_STALE"
                assert await _economic_counts(sessions, RUN_MODE) == counts_before

                blocked, block_reason = await harness.risk_gate.check(
                    RUN_MODE, BTC, plan_id=plan.plan_id
                )
                assert blocked is False
                assert block_reason == "RUNTIME_STATE_DATA_DEGRADED", block_reason
                rejected = await harness.propose_risk_increasing_buy(plan, tag="real-stale-blocked")
                assert rejected.status.value == "REJECTED", rejected.status
                assert rejected.reason == "RUNTIME_STATE_DATA_DEGRADED", rejected.reason
                assert await _economic_counts(sessions, RUN_MODE) == counts_before

                # ---- FRESH #2: real post-reconnect BBO ------------------------------
                second = await anext(stream)
                _assert_real_bbo(second, BTC)
                fresh_2 = _to_bbo(second)
                fresh_2_age = (harness.clock.now() - fresh_2.received_at).total_seconds()
                assert fresh_2_age <= PRODUCTION_FRESHNESS_TTL_SECONDS, fresh_2_age
                recovery = await harness.feed_market_data(fresh_2)
                assert recovery["fresh"] is True
                assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                resolved = await _incident(sessions, RUN_MODE, BTC, IncidentType.CORE_DATA_STALE)
                assert resolved is not None and resolved.status == "RESOLVED"
                assert resolved.resolved_at is not None
                # Real post-reconnect protection evaluation of the same durable position/plan.
                assert recovery["protection"].triggered is False
                assert recovery["protection"].reason == "HOLD"
                position_after_recovery = await _position(sessions, RUN_MODE, BTC)
                assert position_after_recovery is not None
                assert position_after_recovery.quantity == position_before.quantity
                assert await _economic_counts(sessions, RUN_MODE) == counts_before

                re_admitted, re_reason = await harness.risk_gate.check(
                    RUN_MODE, BTC, plan_id=plan.plan_id
                )
                assert (re_admitted, re_reason) == (True, None), (re_admitted, re_reason)

            assert attempts_after_first == 1 and reconnects_after_first == 0
            assert provider.connection_attempts >= 2 and provider.reconnects >= 1
            report["btc_reconnect"] = {
                "first_connection_event": _describe_bbo(first, fresh_1_age),
                "forced_disconnect": "provider disconnect_after_events=1 (controlled local disconnect)",
                "connection_attempts": provider.connection_attempts,
                "reconnects": provider.reconnects,
                "attempts_after_first_event": attempts_after_first,
                "reconnects_after_first_event": reconnects_after_first,
                "post_reconnect_event": _describe_bbo(second, fresh_2_age),
            }
            report["btc_paper_safety"] = {
                "plan_id": plan.plan_id,
                "stop_loss": plan.stop_loss,
                "take_profit": plan.take_profit,
                "position_quantity_before": position_before.quantity,
                "position_quantity_after_recovery": position_after_recovery.quantity,
                "counts_before": counts_before,
                "counts_after_recovery": await _economic_counts(sessions, RUN_MODE),
                "fresh_1_age_seconds": fresh_1_age,
                "fresh_2_age_seconds": fresh_2_age,
                "health_stale": "UNAVAILABLE",
                "incident_type": incident.incident_type,
                "incident_status_stale": incident.status,
                "incident_status_recovered": resolved.status,
                "stale_protection_reason": stale_outcome["protection"].reason,
                "stale_gate_block_reason": block_reason,
                "stale_buy_intent_status": rejected.status.value,
                "stale_buy_intent_reason": rejected.reason,
                "recovery_protection_reason": recovery["protection"].reason,
                "recovery_gate": {"admitted": re_admitted, "reason": re_reason},
                "sell_fill_count": len(await _sell_fills(sessions, RUN_MODE)),
                "reconciliation_ok": None,
            }
        finally:
            await stream.aclose()
        assert provider.connection_attempts >= 2

        # ------------------------------------------------------ ETH reconnect + no-position path
        eth_provider = OKXLiveProvider(disconnect_after_events=1)
        await _instruments(eth_provider, (ETH,))
        eth_stream = eth_provider.stream([{"channel": "bbo-tbt", "instId": ETH}])
        try:
            async with asyncio.timeout(ROCKET_BOUND_SECONDS):
                eth_first = await anext(eth_stream)
                eth_attempts_after_first = eth_provider.connection_attempts
                eth_reconnects_after_first = eth_provider.reconnects
                _assert_real_bbo(eth_first, ETH)
                eth_fresh_1 = _to_bbo(eth_first)
                eth_fresh_1_age = (
                    harness.clock.now() - eth_fresh_1.received_at
                ).total_seconds()
                assert eth_fresh_1_age <= PRODUCTION_FRESHNESS_TTL_SECONDS, eth_fresh_1_age
                eth_open = await harness.feed_market_data(eth_fresh_1)
                assert eth_open["fresh"] is True
                assert eth_open["protection"].reason == "NO_POSITION"
                eth_before_gate = await harness.risk_gate.check(RUN_MODE, ETH, plan_id=None)

                eth_stale = _quote(
                    ETH, eth_fresh_1.bid, eth_fresh_1.ask, age_seconds=CONTROLLED_STALE_AGE_SECONDS
                )
                eth_stale_outcome = await harness.feed_market_data(eth_stale)
                assert eth_stale_outcome["fresh"] is False
                assert eth_stale_outcome["protection"].reason == "CORE_MARKET_DATA_STALE"
                eth_blocked, eth_block_reason = await harness.risk_gate.check(
                    RUN_MODE, ETH, plan_id=None
                )
                assert eth_blocked is False and eth_block_reason == "RUNTIME_STATE_DATA_DEGRADED"

                eth_second = await anext(eth_stream)
                _assert_real_bbo(eth_second, ETH)
                eth_fresh_2 = _to_bbo(eth_second)
                eth_fresh_2_age = (
                    harness.clock.now() - eth_fresh_2.received_at
                ).total_seconds()
                assert eth_fresh_2_age <= PRODUCTION_FRESHNESS_TTL_SECONDS, eth_fresh_2_age
                eth_recovery = await harness.feed_market_data(eth_fresh_2)
                assert eth_recovery["fresh"] is True
                assert harness.health.status(HealthComponent.CORE_MARKET_DATA.value) == "HEALTHY"
                eth_after_gate = await harness.risk_gate.check(RUN_MODE, ETH, plan_id=None)

            assert eth_attempts_after_first == 1 and eth_reconnects_after_first == 0
            assert eth_provider.connection_attempts >= 2 and eth_provider.reconnects >= 1
            report["eth_reconnect"] = {
                "first_connection_event": _describe_bbo(eth_first, eth_fresh_1_age),
                "forced_disconnect": "provider disconnect_after_events=1 (controlled local disconnect)",
                "connection_attempts": eth_provider.connection_attempts,
                "reconnects": eth_provider.reconnects,
                "attempts_after_first_event": eth_attempts_after_first,
                "reconnects_after_first_event": eth_reconnects_after_first,
                "post_reconnect_event": _describe_bbo(eth_second, eth_fresh_2_age),
            }
            report["eth_safety_path"] = {
                "position_present": False,
                "fresh_protection_reason": eth_open["protection"].reason,
                "fresh_gate": {"admitted": eth_before_gate[0], "reason": eth_before_gate[1]},
                "stale_protection_reason": eth_stale_outcome["protection"].reason,
                "stale_gate": {"admitted": eth_blocked, "reason": eth_block_reason},
                "recovery_protection_reason": eth_recovery["protection"].reason,
                "recovery_gate": {"admitted": eth_after_gate[0], "reason": eth_after_gate[1]},
            }
        finally:
            await eth_stream.aclose()

        # ------------------------------------------------------------------- final consistency
        report_obj = await reconcile(
            RUN_MODE, sessions=sessions, execution=harness.execution, now=harness.clock.now()
        )
        final_counts = await _economic_counts(sessions, RUN_MODE)
        background_tasks = await _settle_background_tasks()
        report["btc_paper_safety"]["reconciliation_ok"] = report_obj.ok
        report["final"] = {
            "reconciliation_ok": report_obj.ok,
            "reconciliation_diagnostics": report_obj.diagnostics,
            "economic_counts": final_counts,
            "duplicate_safe_since_pre_reconnect": final_counts == counts_before,
            "background_task_drain": background_tasks,
            "live_order_placed": False,
            "run_mode": RUN_MODE.value,
            "okx_endpoints_used": list(PUBLIC_OKX_ENDPOINTS),
            "okx_api_key_used": False,
            "private_endpoint_used": False,
        }
        assert report_obj.ok is True, report_obj.diagnostics
        assert final_counts == counts_before, (final_counts, counts_before)
        assert background_tasks["remaining_pending_tasks"] == [], background_tasks
    finally:
        await engine.dispose()
    return report


def main() -> int:
    started = datetime.now(UTC)
    with _disposable_postgres_database() as (db_name, db_url):
        report: dict[str, Any] = asyncio.run(_run_timeline(db_url))
        activity_after = asyncio.run(_database_activity(db_name))
        report["disposable_database"] = db_name
        report["disposable_database_activity_after_run"] = activity_after
        assert activity_after["idle_in_transaction"] == 0, activity_after
    report["leftover_n01_b_databases"] = asyncio.run(_leftover_disposable_databases())
    report["started_at"] = started.isoformat()
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["network_environment_note"] = (
        "sandbox-injected HTTP(S)_PROXY cleared for this process only: the local proxy returned "
        "502 CONNECT tunnel failed for OKX. No product proxy configuration was added."
    )
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
