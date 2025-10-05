"""Cost model application (T037).

Applies slippage, spread OR participation adjustment (mutually exclusive per config),
fees, and borrow costs to a trade list producing effective trade prices and
aggregated cost components.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..models.cost_model_config import CostModelConfig


@dataclass
class CostBreakdown:
    slippage: float = 0.0
    spread: float = 0.0
    fees: float = 0.0
    borrow: float = 0.0

    def total(self) -> float:
        return self.slippage + self.spread + self.fees + self.borrow


def _is_buy(side: Any, size: float | None) -> bool:
    """Determine if a trade/fill represents a BUY side.

    Accepts:
      - side: Enum or string with values like BUY/SELL
      - size: signed quantity (positive => buy/add, negative => sell/reduce)
    """
    if side is not None:
        try:
            # Enum: use name or value
            val = getattr(side, "name", None) or getattr(side, "value", None)
            if isinstance(val, str):
                return val.upper() == "BUY"
        except Exception:
            pass
        if isinstance(side, str):
            return side.upper() == "BUY"
    if size is not None:
        try:
            return float(size) > 0
        except Exception:
            return False
    # Default conservative
    return False


def apply_costs(
    trades: Iterable[Any], config: CostModelConfig
) -> tuple[list[Any], CostBreakdown]:
    adjusted: list[Any] = []
    breakdown = CostBreakdown()
    for t in trades:
        # Base price adjustment (copy trade with modified price)
        price = getattr(t, "price", None)
        if price is None:
            raise TypeError("trade/fill object must have a 'price' attribute")
        qty_raw = getattr(t, "quantity", None)
        if qty_raw is None:
            qty_raw = getattr(t, "size", None)
        if qty_raw is None:
            raise TypeError("trade/fill object must have 'quantity' or 'size'")
        try:
            qty = abs(float(qty_raw))
        except Exception as e:
            raise TypeError("quantity/size must be numeric") from e
        side_attr = getattr(t, "side", None)
        is_buy = _is_buy(
            side_attr, float(qty_raw) if isinstance(qty_raw, (int, float)) else None
        )
        # Slippage (bps)
        if config.slippage_bps:
            slip_factor = config.slippage_bps / 10_000.0
            price *= 1 + (slip_factor if is_buy else -slip_factor)
            breakdown.slippage += abs(getattr(t, "price", price) * slip_factor * qty)
        # Spread or participation
        if config.spread_pct is not None:
            sp = config.spread_pct
            half = sp / 2.0
            price *= 1 + (half if is_buy else -half)
            breakdown.spread += abs(getattr(t, "price", price) * half * qty)
        elif config.participation_rate is not None:
            # Simplified model: participation rate => impact proportional factor
            part = config.participation_rate / 100.0
            price *= 1 + (part if is_buy else -part)
            breakdown.spread += abs(getattr(t, "price", price) * part * qty)
        # Fees (bps, always increases cost absolute)
        if config.fee_bps:
            fee_factor = config.fee_bps / 10_000.0
            breakdown.fees += abs(getattr(t, "price", price) * fee_factor * qty)
        # Borrow cost (bps) only for shorts (SELL opening). We approximate all sells contribute.
        if config.borrow_cost_bps and not is_buy:
            borrow_factor = config.borrow_cost_bps / 10_000.0
            breakdown.borrow += abs(getattr(t, "price", price) * borrow_factor * qty)
        adjusted.append(t)
    return adjusted, breakdown


__all__ = ["CostBreakdown", "apply_costs"]
