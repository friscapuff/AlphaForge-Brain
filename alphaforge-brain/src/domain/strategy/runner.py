from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, cast

import pandas as pd

# build_features imported lazily inside function to allow monkeypatch in tests to intercept
from domain.indicators.registry import IndicatorRegistry
from domain.schemas.run_config import RunConfig
from domain.strategy.base import StrategyRegistry
from services.causality_guard import (
    CausalityGuard,
    CausalityMode,
    causality_context,
    guard_context,
)

from infra.persistence import record_causality_stats


class _StrategyCallable(Protocol):  # pragma: no cover - typing helper
    def __call__(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame: ...


# Ensure legacy function-style indicators are registered (e.g., dual_sma) by importing their module.
try:  # pragma: no cover - defensive import
    __import__("domain.indicators.sma")
except Exception:  # pragma: no cover
    pass


@dataclass
class RunnerStats:
    feature_built: bool = False
    rows_in: int = 0
    rows_out: int = 0


def run_strategy(
    config: RunConfig,
    candles: pd.DataFrame,
    *,
    features: pd.DataFrame | None = None,
    use_feature_cache: bool = True,
    candle_hash: str | None = None,
    cache_root: str | None = None,
    engine_version: str = "v1",
    stats: RunnerStats | None = None,
    guard_mode: str | None = None,
    guard: CausalityGuard | None = None,
    run_hash: str | None = None,
) -> pd.DataFrame:
    """Generate strategy signals timeline.

    Parameters
    ----------
    config : RunConfig (strategy + indicator specs)
    candles : raw candle DataFrame (must include timestamp, open/high/low/close/volume)
    features : optional pre-computed feature DataFrame (same index & base columns)
    use_feature_cache : forward to feature builder
    candle_hash, cache_root, engine_version : cache params (only used if we build features)
    stats : optional RunnerStats mutated with simple counters

    Returns
    -------
    DataFrame with at least original candle columns plus strategy feature columns and a `signal` column.
    """
    if stats is None:
        stats = RunnerStats()

    if candles.empty:
        return candles.copy()

    stats.rows_in = len(candles)

    # Pre-feature-build: apply any function-style indicators listed in config that the feature engine
    # will not automatically parameterize. We only support 'dual_sma' legacy naming where run config
    # uses fast/slow while strategy expects short_window/long_window.
    indicator_frames: list[pd.DataFrame] = []
    for spec in config.indicators:
        if spec.name == "dual_sma":
            fn = IndicatorRegistry.get("dual_sma")
            dual_params = {
                "short_window": spec.params.get(
                    "fast", spec.params.get("short_window", 10)
                ),
                "long_window": spec.params.get(
                    "slow", spec.params.get("long_window", 50)
                ),
            }
            # Pass parameters to function-style indicator to materialize expected SMA columns
            try:
                fn_typed = cast(
                    Callable[[pd.DataFrame, dict[str, Any]], pd.DataFrame], fn
                )
                df_ind = fn_typed(candles, dual_params)
                if isinstance(df_ind, pd.Series):  # defensive normalization
                    df_ind = df_ind.to_frame()
                indicator_frames.append(df_ind)
            except TypeError:
                # Fallback for older signature without params
                legacy = fn(candles)
                if isinstance(legacy, pd.Series):
                    legacy = legacy.to_frame()
                indicator_frames.append(legacy)

    if indicator_frames:
        # Merge sequentially (they all start from base candles copy)
        merged = candles.copy()
        for f in indicator_frames:
            for col in f.columns:
                if col not in merged.columns:
                    merged[col] = f[col]
        candles = merged

    from domain.features.engine import (
        build_features as _bf,  # local import for monkeypatch visibility
    )

    # Resolve strategy factory and normalize parameters before executing (may run inside guard context)
    strat_name = config.strategy.name
    # Ensure strategy implementations imported so decorators execute (lazy import pattern)
    try:  # pragma: no cover - defensive
        __import__(f"domain.strategy.{strat_name}")
    except Exception:
        # Not fatal; registry may already contain strategy
        pass
    # Accept either (df, params) or legacy (df) callables
    factory: Callable[..., pd.DataFrame] = StrategyRegistry.get(strat_name)
    strategy_params: dict[str, Any] = dict(config.strategy.params)
    # Normalize parameter names for dual_sma strategy: accept fast/slow aliases
    if strat_name == "dual_sma":
        if "fast" in strategy_params and "short_window" not in strategy_params:
            strategy_params["short_window"] = strategy_params["fast"]
        if "slow" in strategy_params and "long_window" not in strategy_params:
            strategy_params["long_window"] = strategy_params["slow"]

    # Prepare factories for feature handling
    def _merge_feats() -> pd.DataFrame:
        assert features is not None
        feat = features.copy()
        for frame in indicator_frames:
            for col in frame.columns:
                if col not in feat.columns:
                    feat[col] = frame[col]
        return feat

    def _build_feats() -> pd.DataFrame:
        return _bf(
            candles,
            use_cache=use_feature_cache,
            candle_hash=candle_hash,
            cache_root=(
                None if cache_root is None else __import__("pathlib").Path(cache_root)
            ),
            engine_version=engine_version,
        )

    # Execute feature building and strategy within a single guard context if provided
    if guard is not None:
        _ctx = guard_context(guard)
    elif guard_mode is not None:
        _ctx = causality_context(guard_mode)
    else:
        _ctx = None

    if _ctx is not None:
        with _ctx:
            if features is not None:
                features = _merge_feats()
            else:
                features = _build_feats()
                stats.feature_built = True
            result = factory(features, strategy_params)
    else:
        if features is not None:
            features = _merge_feats()
        else:
            features = _build_feats()
            stats.feature_built = True
        result = factory(features, strategy_params)

    # Strategy already executed; defensive runtime check (avoid mypy mixed inheritance confusion)
    if not isinstance(result, pd.DataFrame):  # pragma: no cover - defensive
        raise TypeError("Strategy factory must return a pandas DataFrame")

    # Enforce no lookahead by ensuring signal at row i only derived from <= i features.
    # Dual SMA strategy already respects this (iterative loop). For future strategies we could
    # add validation hooks here; currently we just trust implementation.

    # Filter out rows where required SMA columns are not fully valid (NaN) if present.
    if "signal" in result.columns and result["signal"].notna().sum() == 0:
        # All NaN -> treat as empty output while preserving columns
        empty_out = result.iloc[0:0].copy()
        stats.rows_out = 0
        return empty_out

    stats.rows_out = len(result)
    # Persist causality stats if guard provided and run_hash available
    if guard is not None and run_hash is not None:
        try:
            record_causality_stats(
                run_hash=run_hash,
                mode=getattr(guard, "_mode", CausalityMode.PERMISSIVE),
                violations=len(guard.violations or []),
                phase="strategy",
            )
        except Exception:
            # Persistence is best-effort here; orchestrator has separate persistence path
            pass
    return result


__all__ = ["RunnerStats", "run_strategy"]
