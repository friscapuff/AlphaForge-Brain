from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast

import pandas as pd

from domain.schemas.run_config import RunConfig


def _apply_slippage_model(base_price: float, side: int, model_conf: Mapping[str, Any] | None, row: pd.Series, *, qty: float | None = None) -> float:
    """Extended slippage models beyond fixed bps:
    Models:
      spread_pct: params {spread_pct: float} -> adjust half-spread against the side (buy pays +spread/2, sell receives -spread/2)
      participation_rate: params {participation_pct: float} -> slippage impact proportional to participation share of volume
    If model not provided returns base_price unchanged.
    qty optional for participation rate (if None, treated as 0 -> no impact).
    """
    if not model_conf:
        return base_price
    name = str(model_conf.get("model")) if model_conf.get("model") is not None else None
    params_obj = model_conf.get("params", {})
    params: dict[str, Any]
    if isinstance(params_obj, dict):
        params = cast(dict[str, Any], params_obj)
    else:
        params = {}
    price = base_price
    if name == "spread_pct":
        spread = float(params.get("spread_pct", 0.0))
        # spread_pct expressed as fraction (e.g. 0.001 = 10 bps total spread). We add half-spread for buys, subtract for sells.
        half = price * (spread / 2.0)
        price = price + half * side  # side=1 buy -> +half; side=-1 sell -> -half
    elif name == "participation_rate":
        participation = float(params.get("participation_pct", 0.1))
        vol = float(row.get("volume", 0.0))
        if vol > 0 and qty is not None and qty > 0:
            share = min(1.0, (qty / vol) * participation)
            # Impact modeled as price * share * side
            price = price * (1.0 + share * side)
    return price


@dataclass
class ExecutionResult:
    fills: pd.DataFrame
    positions: pd.DataFrame


def _apply_costs(price: float, *, slippage_bps: float, fee_bps: float, side: int) -> float:
    # Slippage: worsen the price in direction of trade. Buy -> higher price, Sell -> lower price.
    slip_mult = 1.0 + (slippage_bps / 10_000.0 * side)
    exec_price = price * slip_mult
    # Fees expressed in bps of notional; we model as added to effective price for buys, subtracted for sells.
    fee_mult = 1.0 + (fee_bps / 10_000.0 * side)
    return exec_price * fee_mult


def simulate(
    config: RunConfig,
    sized_df: pd.DataFrame,
    *,
    initial_cash: float = 100_000.0,
    skip_zero_volume: bool = False,
    flatten_end: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate naive T+1 execution.

    sized_df: DataFrame with columns at least ['timestamp','open','close','signal','position_size'].
    We interpret position_size as the absolute target size (units) when signal is present.

    T+1 rule: a signal on row i leads to an order executed on row i+1 at that row's open (adjusted for costs).
    Last row signal is ignored (no next bar).

    Returns (fills_df, positions_df)
    fills_df columns: ['timestamp','side','qty','price','cost_basis','cash_after','position_after']
    positions_df columns: ['timestamp','position','cash','equity'] (position in units, mark-to-market on close price)
    """
    if sized_df.empty:
        empty = sized_df.iloc[0:0].copy()
        return empty, empty

    required_cols = {"timestamp", "open", "close", "signal", "position_size"}
    missing = required_cols - set(sized_df.columns)
    if missing:
        raise ValueError(f"sized_df missing required columns: {missing}")

    fee_bps = float(config.execution.fee_bps)
    slippage_bps = float(config.execution.slippage_bps)
    slippage_model_conf = config.execution.slippage_model

    rows = []
    position = 0.0
    cash = float(initial_cash)

    # We'll create a positions snapshot per bar (after potential fill that occurred due to previous bar signal)
    pos_rows = []

    # Iterate to second last index for signals because last bar cannot fill.
    for i in range(len(sized_df)):
        row = sized_df.iloc[i]
        # Execute fill if there was a signal on previous bar (i-1)
        if i > 0:
            prev = sized_df.iloc[i - 1]
            if not pd.isna(prev.get("signal")) and prev.get("signal") != 0:
                # Determine desired direction from signal sign
                direction = 1 if prev.signal > 0 else -1
                target_abs = float(prev.position_size)
                target = direction * target_abs
                # Current open price is execution base
                exec_price = float(row.open)
                # Extended slippage first (impacts raw), then bps slippage + fees
                exec_price = _apply_slippage_model(exec_price, direction, slippage_model_conf, row, qty=abs(target - position))
                exec_price = _apply_costs(exec_price, slippage_bps=slippage_bps, fee_bps=fee_bps, side=direction)
                # Simple model: always move from current position to target (no partial logic)
                # Skip if zero volume and skip_zero_volume flag
                vol = float(row.get("volume", 1.0))
                if skip_zero_volume and vol == 0:
                    # Do not change position; treat as missed execution
                    pass
                else:
                    delta = target - position
                    if abs(delta) > 1e-12:  # there is a change
                        notional = delta * exec_price
                        # For buys delta>0 -> cash decreases; for sells delta<0 -> cash increases.
                        cash -= notional
                        position = target
                        rows.append(
                            {
                                "timestamp": row.timestamp,
                                "side": "BUY" if direction > 0 else "SELL",
                                "qty": abs(delta),
                                "price": exec_price,
                                "cost_basis": notional,
                                "cash_after": cash,
                                "position_after": position,
                            }
                        )
        # Mark current position snapshot using close price for equity
        mtm_price = float(row.close)
        equity = cash + position * mtm_price
        pos_rows.append({
            "timestamp": row.timestamp,
            "position": position,
            "cash": cash,
            "equity": equity,
        })

    # Optional flatten at end: if holding non-zero position create synthetic fill at final bar close price
    if flatten_end and position != 0.0:
        last_row = sized_df.iloc[-1]
        direction = -1 if position > 0 else 1  # opposite to close
        exec_price = float(last_row.close)
        exec_price = _apply_slippage_model(exec_price, direction, slippage_model_conf, last_row, qty=abs(position))
        exec_price = _apply_costs(exec_price, slippage_bps=slippage_bps, fee_bps=fee_bps, side=direction)
        delta = -position
        notional = delta * exec_price
        cash -= notional
        position = 0.0
        rows.append(
            {
                "timestamp": last_row.timestamp,
                "side": "SELL" if direction < 0 else "BUY",
                "qty": abs(delta),
                "price": exec_price,
                "cost_basis": notional,
                "cash_after": cash,
                "position_after": position,
                "synthetic": True,
            }
        )
        if pos_rows:
            pos_rows[-1]["position"] = 0.0
            pos_rows[-1]["cash"] = cash
            pos_rows[-1]["equity"] = cash

    fills_df = pd.DataFrame(rows)
    positions_df = pd.DataFrame(pos_rows)
    return fills_df, positions_df


__all__ = ["simulate", "ExecutionResult"]
