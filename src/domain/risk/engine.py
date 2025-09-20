from __future__ import annotations

import math

import pandas as pd

from domain.schemas.run_config import RunConfig


def _fixed_fraction_size(equity: float, price: float, fraction: float) -> float:
    if price <= 0 or price != price:  # NaN check (price != price)
        return 0.0
    notional = equity * fraction
    if notional <= 0:
        return 0.0
    size = notional / price
    return float(size)


def _volatility_target_size(equity: float, price: float, target_vol: float, realized_vol: float, base_fraction: float) -> float:
    """Scale position inversely with realized volatility.

    fraction_effective = base_fraction * (target_vol / realized_vol)  (capped to 1.0)
    realized_vol expected as annualized volatility (e.g. 0.2 for 20%).
    target_vol is desired annualized volatility, e.g. 0.15.
    """
    if price <= 0 or realized_vol <= 0 or target_vol <= 0:
        return 0.0
    scale = target_vol / realized_vol
    fraction = min(1.0, base_fraction * scale)
    return _fixed_fraction_size(equity, price, fraction)


def _kelly_fraction_size(equity: float, price: float, p_win: float, payoff_ratio: float, base_fraction: float) -> float:
    """Kelly sizing variant: f* = p - (1-p)/R where R=payoff_ratio (avg win / avg loss absolute).

    We then multiply by base_fraction as a dampener. Clamp to [0,1]. Negative -> 0.
    """
    if price <= 0 or payoff_ratio <= 0:
        return 0.0
    p = p_win
    if not (0 <= p <= 1):
        return 0.0
    kelly = p - (1 - p) / payoff_ratio
    if not math.isfinite(kelly):  # pragma: no cover - defensive
        return 0.0
    kelly = max(0.0, min(1.0, kelly))
    eff = min(1.0, kelly * base_fraction)
    return _fixed_fraction_size(equity, price, eff)


def apply_risk(config: RunConfig, signals_df: pd.DataFrame, *, equity: float = 100_000.0) -> pd.DataFrame:
    """Apply risk sizing producing a `position_size` column.

    Current implementation: fixed fraction of equity allocated per bar when signal is non-null.
    Ignores direction for now (execution simulator can apply sign in T025).
    """
    model = config.risk.model
    params = config.risk.params or {}
    out = signals_df.copy()

    if model == "fixed_fraction":
        fraction = float(params.get("fraction", 0.1))
        if not (0 < fraction <= 1):
            raise ValueError("fraction must be in (0,1]")
        prices = out.get("close")
        if prices is None:
            raise ValueError("signals_df must contain 'close' column")
        sizes = [
            _fixed_fraction_size(equity, float(prices.iloc[i]), fraction)
            if not pd.isna(out["signal"].iloc[i]) else 0.0
            for i in range(len(out))
        ]
        out["position_size"] = sizes
        return out
    elif model == "volatility_target":
        # Params: target_vol (annualized), lookback (bars), base_fraction
        target_vol = float(params.get("target_vol", 0.15))
        lookback = int(params.get("lookback", 20))
        base_fraction = float(params.get("base_fraction", 0.1))
        if lookback <= 1:
            raise ValueError("lookback must be >1 for volatility_target")
        prices = out.get("close")
        if prices is None:
            raise ValueError("signals_df must contain 'close' column")
        # Use simple returns for realized vol estimate (stdev * sqrt(annualization_factor))
        rets = prices.pct_change()
        # Assume timeframe ~ 1 minute to remain generic? Instead we just produce a *relative* volatility.
        # For determinism across timeframes we won't attempt annualization scaling beyond sqrt(N) of lookback.
        rolling_std = rets.rolling(lookback).std()
        # Replace NaN with large number to force zero sizing early
        rolling_std_filled = rolling_std.fillna(1e9)
        sizes = []
        for i in range(len(out)):
            if pd.isna(out["signal"].iloc[i]):
                sizes.append(0.0)
                continue
            price = float(prices.iloc[i])
            rv = float(rolling_std_filled.iloc[i])
            sizes.append(_volatility_target_size(equity, price, target_vol, rv, base_fraction))
        out["position_size"] = sizes
        return out
    elif model == "kelly_fraction":
        # Params: p_win (0..1), payoff_ratio (>0), base_fraction (dampen true Kelly)
        p_win = float(params.get("p_win", 0.55))
        payoff_ratio = float(params.get("payoff_ratio", 1.0))
        base_fraction = float(params.get("base_fraction", 0.5))
        prices = out.get("close")
        if prices is None:
            raise ValueError("signals_df must contain 'close' column")
        sizes = []
        for i in range(len(out)):
            if pd.isna(out["signal"].iloc[i]):
                sizes.append(0.0)
                continue
            price = float(prices.iloc[i])
            sizes.append(_kelly_fraction_size(equity, price, p_win, payoff_ratio, base_fraction))
        out["position_size"] = sizes
        return out
    else:  # pragma: no cover - future models
        raise ValueError(f"Unsupported risk model: {model}")


__all__ = ["apply_risk"]
