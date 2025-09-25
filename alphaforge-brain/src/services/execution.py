"""Execution engine (T036).

Responsibility: translate target position deltas into trades honoring
lot size and rounding policy. Cost calculations are deferred to costs service.

This is intentionally minimal; order book simulation out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

from ..models.execution_config import ExecutionConfig, RoundingMode
from ..models.trade import Trade, TradeSide


@dataclass
class PositionState:
    symbol: str
    quantity: float = 0.0


def _round_lot(qty: float, lot: int, mode: RoundingMode) -> int:
    lots = qty / lot
    if mode == RoundingMode.FLOOR:
        lots_int = floor(lots)
    elif mode == RoundingMode.CEIL:
        lots_int = ceil(lots)
    else:  # ROUND
        lots_int = round(lots)
    return int(lots_int * lot)


def generate_trades(
    *,
    symbol: str,
    target_quantity: float,
    state: PositionState,
    price: float,
    config: ExecutionConfig,
    ts: object,
    strategy_id: str,
    run_id: str | None = None,
) -> list[Trade]:
    """Return list of trades to move from current to target position.

    Currently at most one trade is generated (direct jump). Future logic may
    stage orders. Returns empty if no effective change after rounding.
    """
    delta: float = target_quantity - state.quantity
    if abs(delta) < 1e-12:
        return []
    rounded: int = _round_lot(abs(delta), config.lot_size, config.rounding_mode)
    if rounded == 0:
        return []
    side: TradeSide = TradeSide.BUY if delta > 0 else TradeSide.SELL
    trade_qty: float = float(rounded)
    if side == TradeSide.SELL:
        trade_qty = float(rounded)  # explicit for clarity
    state.quantity += trade_qty if side == TradeSide.BUY else -trade_qty
    trade = Trade(
        ts=ts,
        symbol=symbol,
        side=side,
        quantity=trade_qty,
        price=price,
        strategy_id=strategy_id,
        run_id=run_id,
    )
    return [trade]


__all__ = ["PositionState", "generate_trades"]
