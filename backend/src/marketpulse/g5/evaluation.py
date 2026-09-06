"""Deterministic evaluation of a completed G5 replay workspace.

The evaluation layer derives a minimal, reproducible :class:`ReplayEvaluationReport` from the
durable business facts of a finished Replay PostgreSQL workspace. Every metric is read back
from PostgreSQL inside one repeatable-read, read-only transaction and every float aggregate is
computed with :func:`math.fsum` over primary-key-ordered row inputs.

The authoritative metric source is the durable workspace itself. In-memory replay results are
never used as a fact source; ``workspace_digest`` is provenance only and is deliberately
excluded from ``evaluation_digest``.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from marketpulse.db.models import (
    AccountRecord,
    AIDecisionRecord,
    FillRecord,
    LedgerEntryRecord,
    MarketEventRecord,
    PaperOrderRecord,
    PositionRecord,
    TradePlanRecord,
    TradeRecord,
)
from marketpulse.g3.models import RunMode

from .canonical import canonicalize_value

TRADE_STATUS_OPEN = "OPEN"
TRADE_STATUS_CLOSED = "CLOSED"

_ALLOWED_ORDER_SIDES = ("BUY", "SELL")
_ALLOWED_TRADE_STATUSES = (TRADE_STATUS_OPEN, TRADE_STATUS_CLOSED)

#: Metric fields that define the evaluation result. ``workspace_digest`` (provenance) and
#: ``evaluation_digest`` (self fingerprint) are intentionally excluded so the evaluation digest
#: changes only when the evaluated economic result changes.
_EVALUATION_METRIC_FIELDS = (
    "market_event_count",
    "decision_count",
    "plan_count",
    "order_count",
    "fill_count",
    "buy_fill_count",
    "sell_fill_count",
    "buy_filled_notional",
    "sell_filled_notional",
    "total_fees",
    "ledger_cash_delta",
    "account_realized_pnl",
    "final_cash_balance",
    "final_reserved_cash",
    "open_position_count",
    "open_quantity",
    "trade_count",
    "closed_trade_count",
    "open_trade_count",
    "exit_reason_counts",
    "is_flat",
)


class ReplayEvaluationError(RuntimeError):
    """Raised when durable replay facts cannot support a trusted evaluation report."""


@dataclass(frozen=True)
class ReplayEvaluationReport:
    """Deterministic trading and economic result of one completed replay workspace."""

    workspace_digest: str
    market_event_count: int
    decision_count: int
    plan_count: int
    order_count: int
    fill_count: int
    buy_fill_count: int
    sell_fill_count: int
    buy_filled_notional: float
    sell_filled_notional: float
    total_fees: float
    ledger_cash_delta: float
    account_realized_pnl: float
    final_cash_balance: float
    final_reserved_cash: float
    open_position_count: int
    open_quantity: float
    trade_count: int
    closed_trade_count: int
    open_trade_count: int
    exit_reason_counts: tuple[tuple[str | None, int], ...]
    is_flat: bool
    evaluation_digest: str

    def metrics(self) -> dict[str, object]:
        """Return the evaluated metrics only, excluding both digest fields."""

        return {name: getattr(self, name) for name in _EVALUATION_METRIC_FIELDS}

    def as_dict(self) -> dict[str, object]:
        return {
            "workspace_digest": self.workspace_digest,
            **self.metrics(),
            "evaluation_digest": self.evaluation_digest,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            canonicalize_value(self.metrics()),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


async def evaluate_replay_workspace(
    engine: AsyncEngine,
    *,
    workspace_digest: str,
) -> ReplayEvaluationReport:
    """Derive the deterministic evaluation report from one replay workspace.

    ``workspace_digest`` must be produced by :func:`marketpulse.g5.canonical.capture_workspace_snapshot`
    over the accepted replay business table set; it is provenance and never feeds the evaluation
    digest.
    """

    sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    async with sessions() as session:
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
        # Integer counts are exact; no float SQL aggregate is used anywhere in this layer.
        market_event_count = await _count(session, MarketEventRecord)
        decision_count = await _count(session, AIDecisionRecord)
        plan_count = await _count(session, TradePlanRecord)
        order_count = await _count(session, PaperOrderRecord)
        fill_count = await _count(session, FillRecord)

        order_sides = {
            order_id: side
            for order_id, side in (
                await session.execute(
                    select(PaperOrderRecord.order_id, PaperOrderRecord.side).order_by(
                        PaperOrderRecord.order_id
                    )
                )
            ).all()
        }
        fills = list(
            (
                await session.scalars(select(FillRecord).order_by(FillRecord.fill_id))
            ).all()
        )
        ledger_entries = list(
            (
                await session.scalars(
                    select(LedgerEntryRecord).order_by(LedgerEntryRecord.entry_id)
                )
            ).all()
        )
        positions = list(
            (
                await session.scalars(
                    select(PositionRecord).order_by(PositionRecord.position_id)
                )
            ).all()
        )
        trades = list(
            (await session.scalars(select(TradeRecord).order_by(TradeRecord.trade_id))).all()
        )
        accounts = list(
            (await session.scalars(select(AccountRecord).order_by(AccountRecord.account_id))).all()
        )

        replay_accounts = [record for record in accounts if record.run_mode == RunMode.REPLAY]
        if len(replay_accounts) != 1:
            raise ReplayEvaluationError(
                f"expected exactly one REPLAY account, found {len(replay_accounts)}"
            )
        account = replay_accounts[0]
        durable_account = (
            await session.execute(
                select(
                    AccountRecord.cash_balance,
                    AccountRecord.reserved_cash,
                    AccountRecord.realized_pnl,
                ).where(AccountRecord.account_id == account.account_id)
            )
        ).one()

    buy_notionals: list[float] = []
    sell_notionals: list[float] = []
    buy_fill_count = 0
    sell_fill_count = 0
    for fill in fills:
        side = order_sides.get(fill.order_id)
        if side is None:
            raise ReplayEvaluationError(
                f"fill {fill.fill_id!r} has no durable order {fill.order_id!r}"
            )
        if side not in _ALLOWED_ORDER_SIDES:
            raise ReplayEvaluationError(
                f"fill {fill.fill_id!r} resolves to unsupported order side {side!r}"
            )
        notional = fill.price * fill.quantity
        if side == "BUY":
            buy_fill_count += 1
            buy_notionals.append(notional)
        else:
            sell_fill_count += 1
            sell_notionals.append(notional)

    fill_fee_total = math.fsum(fill.fee for fill in fills)
    ledger_fee_total = math.fsum(entry.fee for entry in ledger_entries)
    if fill_fee_total != ledger_fee_total:
        raise ReplayEvaluationError(
            "accounting inconsistency: fill fees do not match ledger fees "
            f"({fill_fee_total!r} != {ledger_fee_total!r})"
        )
    ledger_cash_delta = math.fsum(entry.cash_delta for entry in ledger_entries)

    quantities = [position.quantity for position in positions]
    negative_quantities = [quantity for quantity in quantities if quantity < 0]
    if negative_quantities:
        raise ReplayEvaluationError(
            f"durable positions contain negative quantity: {negative_quantities!r}"
        )
    positive_quantities = [quantity for quantity in quantities if quantity > 0]

    unknown_statuses = sorted(
        {trade.status for trade in trades if trade.status not in _ALLOWED_TRADE_STATUSES}
    )
    if unknown_statuses:
        raise ReplayEvaluationError(
            f"unsupported durable trade statuses: {unknown_statuses!r}"
        )
    exit_counts: dict[str | None, int] = {}
    for trade in trades:
        if trade.status == TRADE_STATUS_CLOSED:
            exit_counts[trade.exit_reason] = exit_counts.get(trade.exit_reason, 0) + 1
    # None first, then exit reason strings in lexicographic ascending order.
    exit_reason_counts = tuple(
        sorted(exit_counts.items(), key=lambda item: (item[0] is not None, item[0] or ""))
    )

    final_reserved_cash = float(durable_account.reserved_cash)
    is_flat = all(quantity == 0 for quantity in quantities) and final_reserved_cash == 0

    metrics: dict[str, Any] = {
        "market_event_count": market_event_count,
        "decision_count": decision_count,
        "plan_count": plan_count,
        "order_count": order_count,
        "fill_count": fill_count,
        "buy_fill_count": buy_fill_count,
        "sell_fill_count": sell_fill_count,
        "buy_filled_notional": math.fsum(buy_notionals),
        "sell_filled_notional": math.fsum(sell_notionals),
        "total_fees": fill_fee_total,
        "ledger_cash_delta": ledger_cash_delta,
        "account_realized_pnl": float(durable_account.realized_pnl),
        "final_cash_balance": float(durable_account.cash_balance),
        "final_reserved_cash": final_reserved_cash,
        "open_position_count": len(positive_quantities),
        "open_quantity": math.fsum(positive_quantities),
        "trade_count": len(trades),
        "closed_trade_count": sum(
            1 for trade in trades if trade.status == TRADE_STATUS_CLOSED
        ),
        "open_trade_count": sum(1 for trade in trades if trade.status == TRADE_STATUS_OPEN),
        "exit_reason_counts": exit_reason_counts,
        "is_flat": is_flat,
    }

    report = ReplayEvaluationReport(
        workspace_digest=workspace_digest,
        evaluation_digest="",
        **metrics,
    )
    _verify_accounting(
        report,
        fill_fee_total=fill_fee_total,
        ledger_cash_delta=ledger_cash_delta,
        durable_account=durable_account,
    )
    return replace(report, evaluation_digest=report.digest())


def _verify_accounting(
    report: ReplayEvaluationReport,
    *,
    fill_fee_total: float,
    ledger_cash_delta: float,
    durable_account: tuple[float, float, float],
) -> None:
    """Re-check every reported economic aggregate against the durable facts."""

    if report.total_fees != fill_fee_total:
        raise ReplayEvaluationError(
            f"reported total_fees {report.total_fees!r} != durable fill fee total {fill_fee_total!r}"
        )
    if report.ledger_cash_delta != ledger_cash_delta:
        raise ReplayEvaluationError(
            f"reported ledger_cash_delta {report.ledger_cash_delta!r} != durable total "
            f"{ledger_cash_delta!r}"
        )
    cash_balance, reserved_cash, realized_pnl = durable_account
    if report.final_cash_balance != cash_balance:
        raise ReplayEvaluationError(
            f"reported final_cash_balance {report.final_cash_balance!r} != durable {cash_balance!r}"
        )
    if report.final_reserved_cash != reserved_cash:
        raise ReplayEvaluationError(
            f"reported final_reserved_cash {report.final_reserved_cash!r} != durable {reserved_cash!r}"
        )
    if report.account_realized_pnl != realized_pnl:
        raise ReplayEvaluationError(
            f"reported account_realized_pnl {report.account_realized_pnl!r} != durable {realized_pnl!r}"
        )


async def _count(session: AsyncSession, model: type) -> int:
    return int((await session.scalar(select(func.count()).select_from(model))) or 0)
