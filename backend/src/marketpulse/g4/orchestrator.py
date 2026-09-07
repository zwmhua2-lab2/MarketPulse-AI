from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from marketpulse.clock import Clock, SystemClock
from marketpulse.g3.models import BestBidAsk, DataQuality, RunMode
from marketpulse.g3.service import PaperExecutionService
from marketpulse.runtime import HealthRegistry

from .models import HealthComponent, HealthStatus, ReevaluationOutcome
from .reevaluation import PositionReevaluationService


class SafetyRuntime:
    """Glue the market-data path onto protection, limit fills and re-evaluation.

    Every symbol is serialized through one asyncio lock so SL / TP / manual close / fills cannot
    interleave in-process; PostgreSQL row locks provide the cross-process guarantee.
    """

    def __init__(
        self,
        *,
        execution: PaperExecutionService,
        protection,
        reevaluation: PositionReevaluationService,
        health: HealthRegistry,
        clock: Clock | None = None,
        reevaluation_enabled: bool = True,
    ) -> None:
        self.execution = execution
        self.protection = protection
        self.reevaluation = reevaluation
        self.health = health
        self.clock = clock or SystemClock()
        self.reevaluation_enabled = reevaluation_enabled
        self._locks: dict[str, asyncio.Lock] = {}

    async def on_market_data(
        self,
        run_mode: RunMode,
        bbo: BestBidAsk,
        *,
        force_reevaluation: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Market Event / Fresh BBO → protection → limit fills → re-evaluation."""
        now = now or self.clock.now()
        lock = self._locks.setdefault(bbo.instrument_id, asyncio.Lock())
        async with lock:
            fresh = self._mark_freshness(bbo, now)
            protection = await self.protection.evaluate(run_mode, bbo.instrument_id, bbo, now=now)
            # Protection always runs before fills: a stop breach cancels pending adds first, so a
            # stale add limit order can never re-open a position that just closed.
            # `process_open_orders` obtains its own action-time clock immediately before the
            # final settlement guards; this event timestamp is candidate-selection context only.
            await self.execution.process_open_orders(run_mode, bbo)
            reevaluation: ReevaluationOutcome | None = None
            if self.reevaluation_enabled:
                should, reason = self.reevaluation.meaningful.should_evaluate(
                    run_mode,
                    bbo.instrument_id,
                    now=now,
                    price=bbo.bid,
                    state_version=int(await self.execution.state_version_for(bbo.instrument_id)),
                    force=force_reevaluation,
                )
                if should:
                    reevaluation = await self.reevaluation.evaluate(
                        run_mode,
                        bbo.instrument_id,
                        bbo,
                        triggering_event=reason,
                        now=now,
                        force=force_reevaluation,
                    )
                    self.reevaluation.meaningful.mark(
                        run_mode,
                        bbo.instrument_id,
                        now=now,
                        price=bbo.bid,
                        state_version=int(
                            await self.execution.state_version_for(bbo.instrument_id)
                        ),
                    )
        return {
            "instrument_id": bbo.instrument_id,
            "fresh": fresh,
            "protection": protection,
            "reevaluation": reevaluation,
        }

    def _mark_freshness(self, bbo: BestBidAsk, now: datetime) -> bool:
        fresh = (
            bbo.tradable
            and bbo.data_quality is DataQuality.FRESH
            and (now - bbo.received_at.astimezone(UTC)).total_seconds() <= 5.0
        )
        self.health.set(
            HealthComponent.CORE_MARKET_DATA.value,
            HealthStatus.HEALTHY.value if fresh else HealthStatus.UNAVAILABLE.value,
            instrument_id=bbo.instrument_id,
        )
        return fresh
