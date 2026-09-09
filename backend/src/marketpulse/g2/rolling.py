from __future__ import annotations

import math
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import pairwise

from marketpulse.market_data.models import (
    AuxiliaryContext,
    NormalizedBookTicker,
    NormalizedKline,
    NormalizedMarketEvent,
    NormalizedTrade,
)

from .models import FeatureSnapshot
from .structure import analyze_structure


@dataclass
class _SymbolRollingState:
    trades: deque[NormalizedTrade] = field(default_factory=lambda: deque(maxlen=120))
    books: deque[NormalizedBookTicker] = field(default_factory=lambda: deque(maxlen=30))
    klines: deque[NormalizedKline] = field(default_factory=lambda: deque(maxlen=60))
    auxiliary: AuxiliaryContext | None = None
    previous_oi: float | None = None
    previous_imbalance: float | None = None
    previous_volume: float | None = None
    previous_breakout_level: float | None = None


class RollingFeatureEngine:
    """In-memory incremental rolling state; it never reads historical data per tick."""

    def __init__(self) -> None:
        self._states: dict[str, _SymbolRollingState] = {}

    def copy(self) -> RollingFeatureEngine:
        """Return an isolated working copy for an input frame."""
        copied = RollingFeatureEngine()
        copied._states = deepcopy(self._states)
        return copied

    def commit(self, working: RollingFeatureEngine) -> None:
        """Publish a successfully processed frame's rolling-state changes."""
        self._states = working._states

    def ingest(self, event: NormalizedMarketEvent, auxiliary: AuxiliaryContext | None = None, btc_return: float | None = None) -> FeatureSnapshot:
        state = self._states.setdefault(event.instrument_id, _SymbolRollingState())
        if isinstance(event, NormalizedTrade):
            state.trades.append(event)
        elif isinstance(event, NormalizedBookTicker):
            state.books.append(event)
        elif isinstance(event, NormalizedKline):
            state.klines.append(event)
        if auxiliary is not None:
            state.auxiliary = auxiliary
        return self._snapshot(event, state, btc_return)

    def _snapshot(self, event: NormalizedMarketEvent, state: _SymbolRollingState, btc_return: float | None) -> FeatureSnapshot:
        trades = list(state.trades)
        prices = [item.price for item in trades]
        current_price = prices[-1] if prices else (state.klines[-1].close if state.klines else None)
        short_return = self._return(prices)
        prior_return = self._return(prices[:-1]) if len(prices) > 2 else None
        acceleration = short_return - prior_return if short_return is not None and prior_return is not None else None
        volatility = self._volatility(prices)
        buy = sum(item.quantity for item in trades if item.side.lower() == "buy")
        sell = sum(item.quantity for item in trades if item.side.lower() == "sell")
        total_flow = buy + sell
        imbalance = (buy - sell) / total_flow if total_flow else None
        flow_change = imbalance - state.previous_imbalance if imbalance is not None and state.previous_imbalance is not None else None
        if imbalance is not None:
            state.previous_imbalance = imbalance
        volume = sum(item.quantity for item in trades)
        prior_volume = state.previous_volume
        volume_acceleration = (volume - prior_volume) / prior_volume if prior_volume and prior_volume > 0 else None
        state.previous_volume = volume
        historical_windows = [item.quantity for item in trades[:-10]]
        baseline = sum(historical_windows) / len(historical_windows) if historical_windows else None
        relative_volume = volume / baseline if baseline and baseline > 0 else None
        spread, depth, liquidity_change = self._liquidity(state)
        auxiliary = state.auxiliary
        oi_change = None
        if auxiliary and auxiliary.oi is not None and state.previous_oi is not None and state.previous_oi != 0:
            oi_change = (auxiliary.oi - state.previous_oi) / state.previous_oi
        if auxiliary and auxiliary.oi is not None:
            state.previous_oi = auxiliary.oi
        structure = analyze_structure(list(state.klines))
        structure_changed = structure.breakout_level is not None and structure.breakout_level != state.previous_breakout_level
        if structure.breakout_level is not None:
            state.previous_breakout_level = structure.breakout_level
        return FeatureSnapshot(
            instrument_id=event.instrument_id,
            symbol=f"{event.base_asset}-{event.quote_asset}",
            market_type=event.market_type,
            event_time=event.event_time,
            current_price=current_price,
            short_return=short_return,
            price_acceleration=acceleration,
            volatility=volatility,
            window_volume=volume,
            relative_volume=relative_volume,
            volume_acceleration=volume_acceleration,
            aggressive_buy_volume=buy,
            aggressive_sell_volume=sell,
            buy_sell_imbalance=imbalance,
            flow_strength_change=flow_change,
            spread=spread,
            basic_depth=depth,
            liquidity_change=liquidity_change,
            oi=auxiliary.oi if auxiliary else None,
            oi_change=oi_change,
            funding_rate=auxiliary.funding_rate if auxiliary else None,
            liquidation_availability=auxiliary.data_quality if auxiliary else "UNAVAILABLE",
            relative_btc_strength=short_return - btc_return if short_return is not None and btc_return is not None else None,
            structure_changed=structure_changed,
            structure=structure,
        )

    @staticmethod
    def _return(prices: list[float]) -> float | None:
        if len(prices) < 2 or prices[0] == 0:
            return None
        return (prices[-1] - prices[0]) / prices[0]

    @staticmethod
    def _volatility(prices: list[float]) -> float | None:
        if len(prices) < 3:
            return None
        returns = [(right - left) / left for left, right in pairwise(prices) if left]
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        return math.sqrt(sum((value - mean) ** 2 for value in returns) / len(returns))

    @staticmethod
    def _liquidity(state: _SymbolRollingState) -> tuple[float | None, float | None, float | None]:
        if not state.books:
            return None, None, None
        latest = state.books[-1]
        mid = (latest.bid_price + latest.ask_price) / 2
        spread = (latest.ask_price - latest.bid_price) / mid if mid else None
        depth = latest.bid_quantity + latest.ask_quantity
        previous = state.books[-2] if len(state.books) > 1 else None
        previous_depth = previous.bid_quantity + previous.ask_quantity if previous else None
        change = (depth - previous_depth) / previous_depth if previous_depth else None
        return spread, depth, change
