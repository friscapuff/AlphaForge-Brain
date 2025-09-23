"""Cost model application (T037).

Applies slippage, spread OR participation adjustment (mutually exclusive per config),
fees, and borrow costs to a trade list producing effective trade prices and
aggregated cost components.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..models.cost_model_config import CostModelConfig
from ..models.trade import Trade, TradeSide


@dataclass
class CostBreakdown:
    slippage: float = 0.0
    spread: float = 0.0
    fees: float = 0.0
    borrow: float = 0.0

    def total(self) -> float:
        return self.slippage + self.spread + self.fees + self.borrow


def apply_costs(trades: Iterable[Trade], config: CostModelConfig) -> tuple[list[Trade], CostBreakdown]:
    adjusted: list[Trade] = []
    breakdown = CostBreakdown()
    for t in trades:
        # Base price adjustment (copy trade with modified price)
        price = t.price
        # Slippage (bps)
        if config.slippage_bps:
            slip_factor = config.slippage_bps / 10_000.0
            price *= 1 + (slip_factor if t.side == TradeSide.BUY else -slip_factor)
            breakdown.slippage += abs(t.price * slip_factor * t.quantity)
        # Spread or participation
        if config.spread_pct is not None:
            sp = config.spread_pct
            half = sp / 2.0
            price *= 1 + (half if t.side == TradeSide.BUY else -half)
            breakdown.spread += abs(t.price * half * t.quantity)
        elif config.participation_rate is not None:
            # Simplified model: participation rate => impact proportional factor
            part = config.participation_rate / 100.0
            price *= 1 + (part if t.side == TradeSide.BUY else -part)
            breakdown.spread += abs(t.price * part * t.quantity)
        # Fees (bps, always increases cost absolute)
        if config.fee_bps:
            fee_factor = config.fee_bps / 10_000.0
            breakdown.fees += abs(t.price * fee_factor * t.quantity)
        # Borrow cost (bps) only for shorts (SELL opening). We approximate all sells contribute.
        if config.borrow_cost_bps and t.side == TradeSide.SELL:
            borrow_factor = config.borrow_cost_bps / 10_000.0
            breakdown.borrow += abs(t.price * borrow_factor * t.quantity)
        adjusted.append(t)
    return adjusted, breakdown

__all__ = ["CostBreakdown", "apply_costs"]
