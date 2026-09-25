"""Focused contract smoke tests for the I03 Product Read boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import marketpulse.api.app as app_module
import pytest
from fastapi.testclient import TestClient
from marketpulse.api.product.cursor import (
    ProductCursorError,
    TradingAuditCursor,
    decode_trading_audit_cursor,
    encode_trading_audit_cursor,
)
from marketpulse.api.product.models import (
    ReadFailureReason,
    TraceNodeState,
    TradingPositionProtectionDTO,
    TradingProtectionState,
    TradingTraceabilityStatus,
    TradingTraceMissingLink,
)
from marketpulse.api.product.trading_audit import (
    SnapshotError,
    _build_timeline,
    _event_traceability,
    _historical_binding,
    _ownership,
    _project_active_plans,
    _project_decision_nodes,
    _resolve_decision_binding,
    _timeline_page,
    _trace_for,
    _unavailable,
    _validate,
)
from marketpulse.g3.models import OrderSide, OrderType, PlanStatus, PriceZone, RunMode, TradePlan


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "dev-only-change-this-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_trading_audit_requires_authentication() -> None:
    assert TestClient(app_module.app).get("/api/v1/product/trading-audit").status_code == 401


def test_trading_audit_host_absent_is_not_activated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.app.state, "host", None, raising=False)
    client = TestClient(app_module.app)
    response = client.get("/api/v1/product/trading-audit", headers=_headers(client))
    assert response.status_code == 200
    assert response.json()["meta"]["operational_availability"] == "NOT_ACTIVATED"
    assert response.json()["meta"]["projection_state"] == "UNAVAILABLE"
    assert response.json()["data"] is None


def test_snapshot_failure_response_is_a_real_503_json_response() -> None:
    response = _unavailable(ReadFailureReason.SNAPSHOT_FAILED, "correlation")
    assert response.status_code == 503
    assert b'"read_failure_reason":"SNAPSHOT_FAILED"' in response.body


def test_trading_cursor_is_endpoint_and_scope_bound() -> None:
    from datetime import UTC, datetime

    cursor = TradingAuditCursor(
        "TEST",
        "BTC-USDT",
        datetime(2026, 9, 22, tzinfo=UTC),
        datetime(2026, 9, 21, tzinfo=UTC),
        "ORDER",
        "order:create:o1",
    )
    assert decode_trading_audit_cursor(encode_trading_audit_cursor(cursor)) == cursor


def test_unprotected_dto_has_no_fabricated_authority() -> None:
    assert TradingPositionProtectionDTO(state=TradingProtectionState.UNPROTECTED).authority is None


def test_historical_decision_binding_requires_exact_durable_evidence() -> None:
    snapshot = SimpleNamespace(
        opportunity_id="opp",
        evidence_id="e1",
        evidence_revision=2,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    evidence = SimpleNamespace(
        opportunity_id="opp",
        evidence_id="e1",
        evidence_revision=2,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    node = _historical_binding(snapshot, {"e1": evidence})
    assert node.state.value == "PRESENT" and node.data.evidence_id == "e1"
    with pytest.raises(SnapshotError):
        _historical_binding(
            snapshot, {"e1": SimpleNamespace(**{**evidence.__dict__, "evidence_hash": "other"})}
        )


def test_historical_binding_absence_is_not_canonical_substitution() -> None:
    assert (
        _historical_binding(
            SimpleNamespace(
                opportunity_id=None,
                evidence_id=None,
                evidence_revision=None,
                evidence_hash=None,
                feature_snapshot_hash=None,
            ),
            {},
        ).state.value
        == "NO_PROVABLE_RECORD"
    )


def test_traceability_core_distinguishes_complete_partial_not_provable() -> None:
    links = {TradingTraceMissingLink.PLAN, TradingTraceMissingLink.DECISION}
    assert _trace_for(applicable=links, proven=links).status is TradingTraceabilityStatus.COMPLETE
    assert (
        _trace_for(applicable=links, proven={TradingTraceMissingLink.PLAN}).status
        is TradingTraceabilityStatus.PARTIAL
    )


@pytest.mark.parametrize(
    ("row", "kwargs"),
    [
        ("PLAN_CREATED", {}),
        ("INTENT_REJECTED", {}),
        ("INTENT_EXECUTED", {"side": "BUY"}),
        ("INTENT_EXECUTED", {"side": "SELL", "has_plan": True}),
        ("INTENT_EXECUTED", {"side": "SELL", "has_plan": False}),
        ("ORDER_CREATED", {"side": "BUY"}),
        ("ORDER_CREATED", {"side": "SELL", "has_plan": True}),
        ("ORDER_CREATED", {"side": "SELL", "has_plan": False}),
        ("ORDER_CANCELLED", {"side": "BUY"}),
        ("RISK", {"initial": True}),
        ("RISK", {"initial": False}),
        ("EXECUTION", {"initial": True}),
        ("EXECUTION", {"initial": False}),
        ("FILL", {"side": "BUY"}),
        ("FILL", {"side": "SELL", "has_plan": True}),
        ("FILL", {"side": "SELL", "has_plan": False}),
        ("LEDGER", {"side": "BUY"}),
        ("TRADE_OPEN", {"side": "BUY"}),
        ("TRADE_CLOSE", {"side": "SELL", "has_plan": True}),
        ("TRADE_CLOSE", {"side": "SELL", "has_plan": False}),
        ("POSITION_EVENT", {"explicit": {"PLAN", "ORDER", "FILL"}}),
    ],
)
def test_a54_a73_matrix_rows_are_reached_through_event_projection(
    row: str, kwargs: dict[str, object]
) -> None:
    traceability = _event_traceability(row, **kwargs)
    assert traceability.status in {
        TradingTraceabilityStatus.COMPLETE,
        TradingTraceabilityStatus.NOT_PROVABLE,
    }


def test_no_plan_sell_and_unproven_trade_fill_have_exact_applicability() -> None:
    traceability = _event_traceability("FILL", side="SELL", has_plan=False)
    assert TradingTraceMissingLink.PLAN not in traceability.missing_links
    assert TradingTraceMissingLink.RISK_ATTRIBUTION not in traceability.missing_links
    assert _event_traceability("TRADE_CLOSE", fill_proven=False).missing_links == [
        TradingTraceMissingLink.FILL
    ]


def test_direct_binding_rejects_cross_opportunity_and_partial_explicit_facts() -> None:
    binding = SimpleNamespace(
        opportunity_id="a",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="h",
        feature_snapshot_hash="f",
    )
    with pytest.raises(SnapshotError):
        _historical_binding(
            binding, {"e": SimpleNamespace(**{**binding.__dict__, "opportunity_id": "b"})}
        )
    with pytest.raises(SnapshotError):
        _historical_binding(SimpleNamespace(**{**binding.__dict__, "evidence_hash": None}), {})


def _plan_row(
    plan_id: str, instrument_id: str, expires_at: datetime, *, status: str = "ACTIVE"
) -> SimpleNamespace:
    created = expires_at - timedelta(hours=1)
    plan = TradePlan(
        plan_id=plan_id,
        snapshot_id=f"s-{plan_id}",
        decision_id=f"d-{plan_id}",
        instrument_id=instrument_id,
        symbol=instrument_id,
        run_mode=RunMode.TEST,
        state_version=1,
        plan_version=1,
        status=PlanStatus.ACTIVE,
        created_at=created,
        expires_at=expires_at,
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        entry_zone=PriceZone(lower=1, upper=2),
        stop_loss=0.5,
        take_profit=3,
        intended_notional=10,
    )
    return SimpleNamespace(
        plan_id=plan_id,
        snapshot_id=plan.snapshot_id,
        decision_id=plan.decision_id,
        instrument_id=instrument_id,
        symbol=instrument_id,
        run_mode="TEST",
        state_version=1,
        plan_version=1,
        status=status,
        created_at=created,
        expires_at=expires_at,
        payload=plan.model_dump(mode="json"),
    )


def test_active_plan_projection_retains_expired_orders_and_sorts_allowlist() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    plans = _project_active_plans(
        [
            _plan_row("b", "ETH", now + timedelta(hours=1)),
            _plan_row("a", "BTC", now - timedelta(seconds=1)),
            _plan_row("skip", "AAA", now, status="CANCELLED"),
        ],
        now,
    )
    assert [(row.instrument_id, row.plan_id) for row in plans] == [("BTC", "a"), ("ETH", "b")]
    assert plans[0].ttl_expired is True and "payload" not in plans[0].model_dump()


@pytest.mark.parametrize("mutate", ["payload", "plan_id", "state_version"])
def test_active_plan_corruption_or_identity_mismatch_fails_closed(mutate: str) -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    row = _plan_row("p", "BTC", now + timedelta(hours=1))
    if mutate == "payload":
        row.payload = {"invalid": True}
    elif mutate == "plan_id":
        row.payload["plan_id"] = "other"
    else:
        row.payload["state_version"] = 2
    with pytest.raises(SnapshotError):
        _project_active_plans([row], now)


def test_direct_advisory_chain_and_conflicting_attribution_are_fail_closed() -> None:
    direct = SimpleNamespace(
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id="i",
        input_binding_digest="d",
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="h",
        feature_snapshot_hash="f",
    )
    decision = SimpleNamespace(
        decision_id="d1",
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id="i",
    )
    invocation = SimpleNamespace(**direct.__dict__)
    evidence = SimpleNamespace(
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="h",
        feature_snapshot_hash="f",
    )
    assert (
        _resolve_decision_binding(
            decision, {"s": direct}, {"i": invocation}, {"e": evidence}, []
        ).data.opportunity_id
        == "o"
    )
    assert (
        _resolve_decision_binding(
            decision,
            {"s": direct},
            {"i": invocation},
            {"e": evidence},
            [
                SimpleNamespace(
                    subject_type="AI", subject_id="d1", opportunity_id="o", evidence_id="e"
                )
            ],
        ).data.evidence_hash
        == "h"
    )
    with pytest.raises(SnapshotError):
        _resolve_decision_binding(
            decision,
            {"s": direct},
            {"i": invocation},
            {"e": evidence},
            [SimpleNamespace(subject_id="d1", opportunity_id="other", evidence_id="e")],
        )
    with pytest.raises(SnapshotError):
        _resolve_decision_binding(
            decision,
            {"s": direct},
            {"i": invocation},
            {"e": evidence},
            [
                SimpleNamespace(
                    subject_type="AI", subject_id="d1", opportunity_id=None, evidence_id="e"
                )
            ],
        )


@pytest.mark.parametrize(
    "failure",
    [
        "missing_snapshot",
        "partial_snapshot_binding",
        "missing_invocation",
        "invocation_snapshot_mismatch",
        "missing_evidence",
        "evidence_hash_mismatch",
        "evidence_cross_opportunity",
        "decision_snapshot_invocation_mismatch",
    ],
)
def test_direct_binding_explicit_reference_failures_are_snapshot_errors(failure: str) -> None:
    snapshot = SimpleNamespace(
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id="i",
        input_binding_digest="digest",
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    decision = SimpleNamespace(
        decision_id="d",
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id="i",
        input_binding_digest="digest",
    )
    invocation = SimpleNamespace(**snapshot.__dict__)
    evidence = SimpleNamespace(
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    invocations = {"i": invocation}
    evidence_by_id = {"e": evidence}
    snapshots = {"s": snapshot}
    if failure == "missing_snapshot":
        snapshots = {}
    elif failure == "partial_snapshot_binding":
        snapshot.evidence_hash = None
    elif failure == "missing_invocation":
        invocations = {}
    elif failure == "invocation_snapshot_mismatch":
        invocation.snapshot_id = "other"
    elif failure == "missing_evidence":
        evidence_by_id = {}
    elif failure == "evidence_hash_mismatch":
        evidence.evidence_hash = "other"
    elif failure == "evidence_cross_opportunity":
        evidence.opportunity_id = "other"
    else:
        decision.decision_invocation_id = "other"
    with pytest.raises(SnapshotError):
        _resolve_decision_binding(decision, snapshots, invocations, evidence_by_id, [])


def test_legacy_decision_binding_returns_no_provable_record_without_current_evidence() -> None:
    snapshot = SimpleNamespace(
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id=None,
        input_binding_digest=None,
        opportunity_id=None,
        evidence_id=None,
        evidence_revision=None,
        evidence_hash=None,
        feature_snapshot_hash=None,
    )
    decision = SimpleNamespace(
        decision_id="d",
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id=None,
        input_binding_digest=None,
    )
    binding = _resolve_decision_binding(decision, {"s": snapshot}, {}, {"current": object()}, [])
    assert binding.state.value == "NO_PROVABLE_RECORD" and binding.data is None


def test_decision_projection_is_sanitized_and_uses_durable_binding() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    snapshot = SimpleNamespace(
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id=None,
        input_binding_digest=None,
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    decision = SimpleNamespace(
        decision_id="d",
        snapshot_id="s",
        run_mode="TEST",
        state_version=1,
        decision_invocation_id=None,
        input_binding_digest=None,
        status="ACCEPTED",
        model="model",
        created_at=now,
        raw_prompt="secret",
        raw_response={"secret": True},
        error="secret",
    )
    evidence = SimpleNamespace(
        opportunity_id="o",
        evidence_id="e",
        evidence_revision=1,
        evidence_hash="hash",
        feature_snapshot_hash="features",
    )
    projected = _project_decision_nodes([decision], {"s": snapshot}, {}, {"e": evidence}, [])
    assert {"raw_prompt", "raw_response", "error"}.isdisjoint(projected["d"].model_dump())
    assert projected["d"].data.opportunity_binding.data.evidence_id == "e"


def test_event_builder_applies_trade_role_integrity_before_traceability() -> None:
    with pytest.raises(SnapshotError):
        _event_traceability("TRADE_OPEN", side="SELL")
    with pytest.raises(SnapshotError):
        _event_traceability("TRADE_CLOSE", side="BUY")
    assert _event_traceability("TRADE_OPEN", fill_proven=False).missing_links == [
        TradingTraceMissingLink.FILL
    ]


def test_event_projection_strong_integrity_dominates_traceability_gaps() -> None:
    with pytest.raises(SnapshotError):
        _event_traceability(
            "INTENT_EXECUTED", side="BUY", intent_id="intent-a", order_intent_id="intent-b"
        )
    with pytest.raises(SnapshotError):
        _event_traceability("FILL", side="SELL", has_plan=False, no_plan_bundle_valid=False)
    with pytest.raises(SnapshotError):
        _event_traceability("ORDER_CANCELLED", side="SELL", has_plan=False)
    with pytest.raises(SnapshotError):
        _event_traceability("INTENT_REJECTED", has_plan=False)


def test_position_event_all_null_links_is_complete() -> None:
    traceability = _event_traceability("POSITION_EVENT", explicit=set())
    assert traceability.status is TradingTraceabilityStatus.COMPLETE
    assert traceability.missing_links == []


@pytest.mark.parametrize(
    ("anchors", "expected"),
    [
        (["TEST", "TEST"], "PROVEN_CURRENT"),
        (["OTHER", "OTHER"], "PROVEN_OTHER"),
        (["TEST", "OTHER"], "CONFLICTING_SCOPE"),
        (["TEST", None], "UNSCOPED"),
        ([None, None], "UNSCOPED"),
    ],
)
def test_economic_row_ownership_uses_both_durable_anchors(
    anchors: list[str | None], expected: str
) -> None:
    assert _ownership(anchors=anchors, current_run_mode="TEST") == expected


def _timeline_sources(now: datetime) -> dict[str, list[SimpleNamespace]]:
    plan = SimpleNamespace(
        plan_id="p",
        snapshot_id="s",
        decision_id="d",
        instrument_id="BTC",
        symbol="BTC",
        plan_version=1,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    executed = SimpleNamespace(
        intent_id="i",
        plan_id="p",
        instrument_id="BTC",
        status="EXECUTED",
        reason=None,
        created_at=now,
    )
    rejected = SimpleNamespace(
        intent_id="r",
        plan_id="p",
        instrument_id="ETH",
        status="REJECTED",
        reason="risk",
        created_at=now,
    )
    rejected_execution = SimpleNamespace(
        intent_id="x",
        plan_id="p",
        instrument_id="SOL",
        status="REJECTED",
        reason="execution",
        created_at=now,
    )
    order = SimpleNamespace(
        order_id="o",
        intent_id="i",
        plan_id="p",
        instrument_id="BTC",
        side="BUY",
        order_type="MARKET",
        status="CANCELLED",
        quantity=1.0,
        limit_price=None,
        created_at=now,
    )
    fill = SimpleNamespace(
        fill_id="f", order_id="o", intent_id="i", price=10.0, quantity=1.0, fee=0.1, created_at=now
    )
    ledger = SimpleNamespace(
        entry_id="l",
        fill_id="f",
        entry_type="SETTLEMENT",
        cash_delta=-10.1,
        fee=0.1,
        payload={"settlement_realized_pnl": 1.0},
        created_at=now,
    )
    risk_initial = SimpleNamespace(
        attribution_event_id="a-risk",
        subject_id="r",
        event_type="RISK_REJECTED",
        payload={"intent_id": "r", "plan_id": "p", "reason": "risk", "authority": "Gate"},
        occurred_at=now,
        opportunity_id=None,
        evidence_id=None,
    )
    risk_deferred = SimpleNamespace(
        attribution_event_id="a-risk-deferred",
        subject_id="i",
        event_type="RISK_REJECTED",
        payload={
            "intent_id": "i",
            "plan_id": "p",
            "order_id": "o",
            "reason": "later-risk",
            "authority": "Gate",
        },
        occurred_at=now + timedelta(seconds=1),
        opportunity_id=None,
        evidence_id=None,
    )
    risk_accepted = SimpleNamespace(
        attribution_event_id="a-accept",
        subject_id="i",
        event_type="RISK_ACCEPTED",
        payload={"intent_id": "i", "plan_id": "p", "order_id": "o"},
        occurred_at=now + timedelta(seconds=1, milliseconds=500),
        opportunity_id=None,
        evidence_id=None,
    )
    execution_deferred = SimpleNamespace(
        attribution_event_id="a-exec",
        subject_id="i",
        event_type="EXECUTION_REJECTED",
        payload={"intent_id": "i", "plan_id": "p", "reason": "later"},
        occurred_at=now + timedelta(seconds=2),
        opportunity_id=None,
        evidence_id=None,
    )
    execution_initial = SimpleNamespace(
        attribution_event_id="a-exec-initial",
        subject_id="x",
        event_type="EXECUTION_REJECTED",
        payload={"intent_id": "x", "plan_id": "p", "reason": "execution"},
        occurred_at=now,
        opportunity_id=None,
        evidence_id=None,
    )
    return {
        "plans": [plan],
        "intents": [executed, rejected, rejected_execution],
        "orders": [order],
        "fills": [fill],
        "ledgers": [ledger],
        "outbox": [
            SimpleNamespace(
                outbox_id="c",
                aggregate_id="o",
                event_type="ORDER_CANCELLED",
                payload={"raw": True},
                created_at=now,
            )
        ],
        "trades": [
            SimpleNamespace(
                trade_id="t",
                instrument_id="BTC",
                opened_at=now,
                closed_at=now + timedelta(seconds=3),
                exit_reason="MANUAL_CLOSE",
            )
        ],
        "position_events": [
            SimpleNamespace(
                event_id="pe",
                event_type="CLOSE",
                instrument_id="BTC",
                position_id=None,
                plan_id=None,
                order_id=None,
                fill_id=None,
                payload={"raw": True},
                created_at=now,
            ),
            SimpleNamespace(
                event_id="drop",
                event_type="RECOVERY",
                instrument_id="BTC",
                position_id=None,
                plan_id=None,
                order_id=None,
                fill_id=None,
                payload={"raw": True},
                created_at=now,
            ),
        ],
        "attribution": [
            risk_initial,
            risk_deferred,
            risk_accepted,
            execution_deferred,
            execution_initial,
        ],
    }


def test_timeline_assembly_projects_typed_families_and_sanitizes_payloads() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    items = _build_timeline(**_timeline_sources(now))
    kinds = {(item.entity_kind, item.event_type) for item in items}
    assert {
        "PLAN",
        "INTENT",
        "ORDER",
        "FILL",
        "LEDGER",
        "RISK",
        "EXECUTION",
        "TRADE_OPEN",
        "TRADE_CLOSE",
        "POSITION_EVENT",
    } <= {kind for kind, _ in kinds}
    assert {
        "PLAN_CREATED",
        "RISK_ACCEPTED",
        "RISK_REJECTED",
        "EXECUTION_REJECTED",
        "INTENT_EXECUTED",
        "INTENT_REJECTED",
        "ORDER_CREATED",
        "ORDER_CANCELLED",
        "FILL_OCCURRED",
        "SETTLEMENT_RECORDED",
        "TRADE_OPEN",
        "TRADE_CLOSE",
        "CLOSE",
    } <= {event_type for _, event_type in kinds}
    assert all("payload" not in item.model_dump() for item in items)
    rejected = next(item for item in items if item.entity_id == "r")
    assert rejected.initial_rejection.state.value == "PRESENT"
    assert (
        next(item for item in items if item.entity_id == "x").initial_rejection.data.kind
        == "EXECUTION"
    )
    assert {
        item.attribution_event_id for item in items if item.entity_kind in {"RISK", "EXECUTION"}
    } == {
        "a-risk",
        "a-risk-deferred",
        "a-accept",
        "a-exec",
        "a-exec-initial",
    }


def test_timeline_global_keyset_uses_identity_and_reuses_upper_bound() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    items = [
        item for item in _build_timeline(**_timeline_sources(now)) if item.entity_kind == "ORDER"
    ]
    page_one, cursor = _timeline_page(
        items,
        upper=now,
        limit=1,
        cursor=None,
        run_mode="TEST",
        instrument_id=None,
    )
    decoded = decode_trading_audit_cursor(cursor)
    page_two, _ = _timeline_page(
        items,
        upper=decoded.timeline_upper_bound,
        limit=1,
        cursor=decoded,
        run_mode="TEST",
        instrument_id=None,
    )
    assert decoded.timeline_upper_bound == now
    assert [item.timeline_event_id for item in [*page_one, *page_two]] == [
        "outbox:c",
        "order:create:o",
    ]


def test_timeline_global_merge_is_not_source_by_source_truncated() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    items = _build_timeline(**_timeline_sources(now))
    page, _ = _timeline_page(
        items,
        upper=now + timedelta(seconds=5),
        limit=4,
        cursor=None,
        run_mode="TEST",
        instrument_id=None,
    )
    assert [item.timeline_event_id for item in page] == [
        "trade:close:t",
        "attribution:a-exec",
        "attribution:a-accept",
        "attribution:a-risk-deferred",
    ]


def test_same_time_attribution_events_for_one_intent_remain_distinct() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    sources = _timeline_sources(now)
    sources["attribution"][1].occurred_at = now
    sources["attribution"][2].occurred_at = now
    items = _build_timeline(**sources)
    page, _ = _timeline_page(
        [item for item in items if item.entity_kind == "RISK" and item.entity_id == "i"],
        upper=now,
        limit=2,
        cursor=None,
        run_mode="TEST",
        instrument_id=None,
    )
    assert {item.timeline_event_id for item in page} == {
        "attribution:a-risk-deferred",
        "attribution:a-accept",
    }


def test_rejected_intent_does_not_infer_initial_classification_from_reason_text() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    sources = _timeline_sources(now)
    sources["attribution"] = [
        row for row in sources["attribution"] if row.attribution_event_id != "a-risk"
    ]
    items = _build_timeline(**sources)
    rejected = next(item for item in items if item.entity_id == "r")
    assert rejected.initial_rejection.state.value == "NO_PROVABLE_RECORD"


def test_trading_cursor_rejects_invalid_sort_tuple() -> None:
    bad = encode_trading_audit_cursor(
        TradingAuditCursor(
            "TEST",
            None,
            datetime(2026, 9, 22, tzinfo=UTC),
            datetime(2026, 9, 23, tzinfo=UTC),
            "NOPE",
            "x",
        )
    )
    with pytest.raises(ProductCursorError):
        decode_trading_audit_cursor(bad)


def test_real_postgres_disposable_snapshot_is_repeatable_read_only() -> None:
    async def scenario() -> tuple[str, str, bool]:
        database_name = f"i03_snapshot_{uuid4().hex[:12]}"
        admin = await asyncpg.connect(
            user="marketpulse",
            password="marketpulse",
            host="127.0.0.1",
            port=5432,
            database="postgres",
        )
        try:
            await admin.execute(f'CREATE DATABASE "{database_name}"')
            connection = await asyncpg.connect(
                user="marketpulse",
                password="marketpulse",
                host="127.0.0.1",
                port=5432,
                database=database_name,
            )
            try:
                await connection.execute("BEGIN")
                await connection.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                isolation = await connection.fetchval("SHOW transaction_isolation")
                read_only = await connection.fetchval("SHOW transaction_read_only")
                await connection.execute("COMMIT")
            finally:
                await connection.close()
        finally:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
            dropped = await admin.fetchval(
                "SELECT NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = $1)", database_name
            )
            await admin.close()
        return isolation, read_only, dropped

    isolation, read_only, dropped = asyncio.run(scenario())
    assert (isolation, read_only, dropped) == ("repeatable read", "on", True)


def test_cancelled_order_without_outbox_is_a_trace_gap_not_fabricated_event() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    sources = _timeline_sources(now)
    sources["outbox"] = []
    items = _build_timeline(**sources)
    order = next(item for item in items if item.timeline_event_id == "order:create:o")
    assert TradingTraceMissingLink.ORDER_CANCELLATION_EVENT in order.traceability.missing_links
    assert all(item.event_type != "ORDER_CANCELLED" for item in items)


def _account_row() -> SimpleNamespace:
    return SimpleNamespace(
        account_id="acc", run_mode="TEST", cash_balance=100.0, reserved_cash=0.0, realized_pnl=0.0
    )


def _no_plan_workspace(
    *,
    side: str = "SELL",
    order_type: str = "MARKET",
    status: str = "FILLED",
    intent_status: str = "EXECUTED",
) -> tuple[
    list[SimpleNamespace], list[SimpleNamespace], list[SimpleNamespace], list[SimpleNamespace]
]:
    """One empty-plan order plus the closure the A74 validator already requires of it."""
    now = datetime(2026, 9, 22, tzinfo=UTC)
    opening_intent = SimpleNamespace(
        intent_id="i-buy",
        plan_id="p",
        instrument_id="BTC",
        status="EXECUTED",
        reason=None,
        created_at=now,
    )
    intent = SimpleNamespace(
        intent_id="i",
        plan_id="",
        instrument_id="BTC",
        status=intent_status,
        reason=None,
        created_at=now,
    )
    opening_order = SimpleNamespace(
        order_id="o-buy",
        intent_id="i-buy",
        plan_id="p",
        instrument_id="BTC",
        side="BUY",
        order_type="MARKET",
        status="FILLED",
        quantity=1.0,
        limit_price=None,
        reserved_cash=0.0,
        reserved_quantity=0.0,
        created_at=now,
    )
    order = SimpleNamespace(
        order_id="o",
        intent_id="i",
        plan_id="",
        instrument_id="BTC",
        side=side,
        order_type=order_type,
        status=status,
        quantity=1.0,
        limit_price=None,
        reserved_cash=0.0,
        reserved_quantity=0.0,
        created_at=now,
    )
    settled = status == "FILLED"
    opening_fill = SimpleNamespace(
        fill_id="f-buy",
        order_id="o-buy",
        intent_id="i-buy",
        price=1.0,
        quantity=1.0,
        fee=0.0,
        created_at=now,
    )
    fills = (
        [
            opening_fill,
            SimpleNamespace(
                fill_id="f",
                order_id="o",
                intent_id="i",
                price=1.0,
                quantity=1.0,
                fee=0.0,
                created_at=now,
            ),
        ]
        if settled
        else [opening_fill]
    )
    opening_ledger = SimpleNamespace(
        entry_id="l-buy",
        account_id="acc",
        fill_id="f-buy",
        entry_type="SETTLEMENT",
        cash_delta=-1.0,
        fee=0.0,
        payload={},
        created_at=now,
    )
    ledgers = (
        [
            opening_ledger,
            SimpleNamespace(
                entry_id="l",
                account_id="acc",
                fill_id="f",
                entry_type="SETTLEMENT",
                cash_delta=1.0,
                fee=0.0,
                payload={},
                created_at=now,
            ),
        ]
        if settled
        else [opening_ledger]
    )
    return [opening_intent, intent], [opening_order, order], fills, ledgers


def _positions_for_fills(
    orders: list[SimpleNamespace], fills: list[SimpleNamespace]
) -> list[SimpleNamespace]:
    net: dict[str, float] = {}
    by_order = {order.order_id: order for order in orders}
    for fill in fills:
        order = by_order[fill.order_id]
        net[order.instrument_id] = net.get(order.instrument_id, 0.0) + (
            fill.quantity if order.side == "BUY" else -fill.quantity
        )
    return [
        SimpleNamespace(instrument_id=instrument_id, quantity=quantity)
        for instrument_id, quantity in net.items()
        if quantity != 0.0
    ]


def test_reconciliation_uses_accepted_g3_tolerance_boundaries() -> None:
    account = _account_row()
    account.reserved_cash = 1e-8
    _validate(account, [], [], [], [], [], [])
    account.reserved_cash = 1.0000001e-8
    with pytest.raises(SnapshotError, match="account reservation"):
        _validate(account, [], [], [], [], [], [])


def test_reconciliation_is_bidirectional_for_positions_and_fill_instruments() -> None:
    intents, orders, fills, ledgers = _no_plan_workspace()
    with pytest.raises(SnapshotError, match="position/fill mismatch"):
        _validate(
            _account_row(),
            [SimpleNamespace(instrument_id="BTC", quantity=1.0)],
            intents,
            orders,
            fills,
            ledgers,
            [],
        )

    buy_intent = SimpleNamespace(
        intent_id="i", plan_id="p", instrument_id="ETH", status="EXECUTED", reason=None
    )
    buy_order = SimpleNamespace(
        order_id="o",
        intent_id="i",
        plan_id="p",
        instrument_id="ETH",
        side="BUY",
        order_type="MARKET",
        status="FILLED",
        quantity=1.0,
        reserved_cash=0.0,
        reserved_quantity=0.0,
    )
    buy_fill = SimpleNamespace(fill_id="f", order_id="o", intent_id="i", quantity=1.0)
    buy_ledger = SimpleNamespace(entry_id="l", fill_id="f")
    with pytest.raises(SnapshotError, match="position/fill mismatch"):
        _validate(_account_row(), [], [buy_intent], [buy_order], [buy_fill], [buy_ledger], [])

    second_intent = SimpleNamespace(
        intent_id="i-sol", plan_id="p-sol", instrument_id="SOL", status="EXECUTED", reason=None
    )
    second_order = SimpleNamespace(
        order_id="o-sol",
        intent_id="i-sol",
        plan_id="p-sol",
        instrument_id="SOL",
        side="BUY",
        order_type="MARKET",
        status="FILLED",
        quantity=2.0,
        reserved_cash=0.0,
        reserved_quantity=0.0,
    )
    second_fill = SimpleNamespace(
        fill_id="f-sol", order_id="o-sol", intent_id="i-sol", quantity=2.0
    )
    second_ledger = SimpleNamespace(entry_id="l-sol", fill_id="f-sol")
    with pytest.raises(SnapshotError, match="position/fill mismatch"):
        _validate(
            _account_row(),
            [SimpleNamespace(instrument_id="SOL", quantity=1.0)],
            [buy_intent, second_intent],
            [buy_order, second_order],
            [buy_fill, second_fill],
            [buy_ledger, second_ledger],
            [],
        )

    _validate(
        _account_row(),
        [
            SimpleNamespace(instrument_id="ETH", quantity=1.0),
            SimpleNamespace(instrument_id="SOL", quantity=2.0),
        ],
        [buy_intent, second_intent],
        [buy_order, second_order],
        [buy_fill, second_fill],
        [buy_ledger, second_ledger],
        [],
    )
    _validate(_account_row(), [], intents, orders, fills, ledgers, [])


def test_missing_account_with_trade_is_snapshot_failure() -> None:
    with pytest.raises(SnapshotError, match="economic facts without account"):
        _validate(None, [], [], [], [], [], [SimpleNamespace(trade_id="t")])


def test_no_plan_sell_requires_intent_order_instrument_coherence() -> None:
    intents, orders, fills, ledgers = _no_plan_workspace()
    intents[1].instrument_id = "ETH"
    with pytest.raises(SnapshotError, match="empty-plan order"):
        _validate(
            _account_row(), _positions_for_fills(orders, fills), intents, orders, fills, ledgers, []
        )


def test_initial_risk_accepted_keeps_initial_semantics_after_intent_executes() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    sources = _timeline_sources(now)
    risk_accepted = next(row for row in sources["attribution"] if row.event_type == "RISK_ACCEPTED")
    risk_accepted.occurred_at = now
    items = _build_timeline(**sources, decision_nodes=_complete_decision_nodes())
    initial = next(item for item in items if item.timeline_event_id == "attribution:a-accept")
    deferred = next(
        item for item in items if item.timeline_event_id == "attribution:a-risk-deferred"
    )
    assert TradingTraceMissingLink.ORDER not in initial.traceability.missing_links
    assert TradingTraceMissingLink.ORDER not in deferred.traceability.missing_links


def _complete_decision_nodes() -> dict[str, SimpleNamespace]:
    return {
        "d": SimpleNamespace(
            state=TraceNodeState.PRESENT,
            data=SimpleNamespace(opportunity_binding=SimpleNamespace(state=TraceNodeState.PRESENT)),
        )
    }


def test_projection_derives_a53_complete_partial_not_provable_from_durable_facts() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    complete = _build_timeline(**_timeline_sources(now), decision_nodes=_complete_decision_nodes())
    complete_plan = next(item for item in complete if item.timeline_event_id == "plan:create:p")
    assert complete_plan.traceability.status is TradingTraceabilityStatus.COMPLETE
    assert complete_plan.traceability.missing_links == []

    partial_sources = _timeline_sources(now)
    partial_sources["attribution"] = [
        row for row in partial_sources["attribution"] if row.event_type != "RISK_ACCEPTED"
    ]
    partial = _build_timeline(**partial_sources, decision_nodes=_complete_decision_nodes())
    partial_fill = next(item for item in partial if item.timeline_event_id == "fill:f")
    assert partial_fill.traceability.status is TradingTraceabilityStatus.PARTIAL
    assert partial_fill.traceability.missing_links == [TradingTraceMissingLink.RISK_ATTRIBUTION]

    not_provable_sources = _timeline_sources(now)
    not_provable_sources["attribution"] = []
    not_provable = _build_timeline(
        **not_provable_sources, decision_nodes=_complete_decision_nodes()
    )
    trade_open = next(item for item in not_provable if item.timeline_event_id == "trade:open:t")
    assert trade_open.traceability.status is TradingTraceabilityStatus.NOT_PROVABLE
    assert trade_open.traceability.missing_links == [TradingTraceMissingLink.FILL]


def test_executed_intent_without_order_is_a_snapshot_failure() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    intent = SimpleNamespace(
        intent_id="i",
        plan_id="p",
        instrument_id="BTC",
        status="EXECUTED",
        reason=None,
        created_at=now,
    )
    with pytest.raises(SnapshotError, match="executed intent without order"):
        _validate(_account_row(), [], [intent], [], [], [], [])


def test_accepted_no_plan_sell_bundle_is_the_only_legal_empty_plan_shape() -> None:
    intents, orders, fills, ledgers = _no_plan_workspace()
    _validate(
        _account_row(), _positions_for_fills(orders, fills), intents, orders, fills, ledgers, []
    )


@pytest.mark.parametrize(
    ("side", "order_type", "status", "intent_status"),
    [
        ("BUY", "MARKET", "FILLED", "EXECUTED"),
        ("SELL", "LIMIT", "FILLED", "EXECUTED"),
        ("SELL", "MARKET", "CANCELLED", "EXECUTED"),
        ("SELL", "MARKET", "FILLED", "REJECTED"),
    ],
)
def test_empty_plan_order_outside_the_accepted_bundle_is_a_snapshot_failure(
    side: str, order_type: str, status: str, intent_status: str
) -> None:
    intents, orders, fills, ledgers = _no_plan_workspace(
        side=side, order_type=order_type, status=status, intent_status=intent_status
    )
    with pytest.raises(SnapshotError, match="empty-plan order"):
        _validate(
            _account_row(), _positions_for_fills(orders, fills), intents, orders, fills, ledgers, []
        )
