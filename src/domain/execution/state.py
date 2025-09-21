from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: str  # LONG / SHORT
    qty: float
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    holding_period: int  # bars


def _infer_trades(fills: pd.DataFrame) -> pd.DataFrame:
    """Infer round-trip trades from fills.

    Assumptions:
    - Single position at a time (no pyramiding)
    - Direction flips immediately flatten then reverse (treated as two trades)
    - Entry = first fill of direction when flat; exit = next fill that changes direction or sets position to zero.
    - Fills DataFrame columns: timestamp, side (BUY/SELL), qty, price, position_after.
    """
    if fills.empty:
        return fills.iloc[0:0].copy()

    trades = []
    entry_qty = 0.0
    entry_value = 0.0
    entry_ts = None
    side_dir = 0  # +1 long, -1 short

    for i in range(len(fills)):
        f = fills.iloc[i]
        direction = 1 if f.side == "BUY" else -1
        if side_dir == 0:  # opening
            side_dir = direction
            entry_ts = f.timestamp
            entry_qty = f.qty
            entry_value = f.qty * f.price
        elif direction == side_dir:
            # add to position (we could treat as scaling, but spec says no partial complexity; ignore for baseline)
            # We'll average cost by accumulating
            entry_value += f.qty * f.price
            entry_qty += f.qty
        else:
            # opposite side: closes existing position (no partial leftover per assumptions)
            exit_ts = f.timestamp
            # PnL for long: (exit - avg_entry)*qty ; for short: (avg_entry - exit)*qty
            avg_entry = entry_value / entry_qty if entry_qty else 0.0
            if side_dir == 1:
                pnl = (f.price - avg_entry) * entry_qty
            else:  # short
                pnl = (avg_entry - f.price) * entry_qty
            return_pct = (pnl / (entry_value)) if entry_value else 0.0
            holding = int((exit_ts - entry_ts).total_seconds() // 60) if isinstance(exit_ts, pd.Timestamp) else 0
            trades.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "side": "LONG" if side_dir == 1 else "SHORT",
                "qty": entry_qty,
                "entry_price": avg_entry,
                "exit_price": f.price,
                "pnl": pnl,
                "return_pct": return_pct,
                "holding_period": holding,
            })
            # Start new position in opposite direction? In baseline simulator we jump directly to target, so treat this fill also as new entry
            side_dir = direction
            entry_ts = f.timestamp
            entry_qty = f.qty
            entry_value = f.qty * f.price

    # If still holding at end with no exit, we ignore unrealized open trade (baseline). Future enhancement may realize at last close.

    return pd.DataFrame(trades)


def build_state(fills: pd.DataFrame, positions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build trade list and summary stats.

    Summary dict keys:
      cumulative_pnl: sum of realized trade PnL
      trade_count: number of round trips
    """
    trades = _infer_trades(fills)
    cumulative_pnl = float(trades["pnl"].sum()) if not trades.empty else 0.0
    summary = {
        "cumulative_pnl": cumulative_pnl,
        "trade_count": len(trades),
    }
    return trades, summary


__all__ = ["Trade", "build_state"]
