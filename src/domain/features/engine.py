from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

# We assume an indicator registry exposed similarly to domain.indicators.registry
try:
    from domain.indicators.registry import IndicatorRegistry, indicator_registry
except Exception as e:  # pragma: no cover - defensive
    raise ImportError("indicator registry not available: " + str(e)) from e


class FeatureEngine:
    """Applies all registered indicators to a candle DataFrame and returns augmented DataFrame.

    Contract enforced by tests:
    - Original columns retained.
    - New feature columns appended in deterministic order: sorted by indicator name then column name.
    - Duplicate feature column names raise ValueError before mutation.
    - Idempotent: does not mutate input; repeated calls with same input produce identical output.
    """

    base_columns: Sequence[str] = (
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Work on a copy to guarantee idempotency
        out = df.copy(deep=True)

        # Collect planned feature columns per indicator
        indicator_objects = list(indicator_registry.list())

        # Support legacy function-style indicators (like dual_sma) via registry facade
        try:
            fn_indicator_registry = IndicatorRegistry.list()
        except Exception:  # pragma: no cover - defensive
            fn_indicator_registry = {}

        planned: dict[str, pd.Series] = {}
        # First apply function style indicators (they return full DataFrame with features), then object style
        for _name, fn in sorted(fn_indicator_registry.items()):  # deterministic order
            # Skip if already handled by object indicator with same name semantics
            try:
                feats = fn(out, params={})
            except Exception:
                continue
            if isinstance(feats, pd.Series):
                feats = feats.to_frame()
            # Add only new columns
            for c in feats.columns:
                if c in planned:
                    raise ValueError(f"Duplicate feature column: {c}")
                planned[c] = feats[c]

        for ind in indicator_objects:
            # Expect indicators expose: name, compute(df)->DataFrame or Series, and a feature_columns() list.
            # Fallback heuristics if not present.
            name = getattr(ind, "name", ind.__class__.__name__)

            # Standardized method to produce a DataFrame of features
            if hasattr(ind, "compute"):
                feats = ind.compute(out)
            elif callable(ind):
                feats = ind(out)
            else:  # pragma: no cover
                raise AttributeError(f"Indicator {name} lacks compute/__call__")

            if isinstance(feats, pd.Series):
                feats = feats.to_frame()

            # Determine feature column names: indicator may supply feature_columns; else build heuristics
            if hasattr(ind, "feature_columns"):
                cols = list(ind.feature_columns())
            else:
                # Heuristic: prefix each feat column with indicator class name
                cols = [f"{name}_{c}" for c in feats.columns]

            if len(cols) != len(feats.columns):  # pragma: no cover
                raise ValueError("Feature column name count mismatch")

            # Rename features DataFrame to planned column names
            feats.columns = cols

            for c in cols:
                if c in planned:
                    # Collision detected prior to any mutation of output
                    raise ValueError(f"Duplicate feature column: {c}")

            for c in cols:
                planned[c] = feats[c]

        # Deterministic ordering: sort by indicator name then column
        # We need a mapping from column -> indicator name for sorting. We embedded indicator name in column; we can parse until first '_' segment.
        def sort_key(col: str) -> tuple[str, str]:
            parts = col.split("_")
            return (parts[0], col)

        ordered_cols = sorted(planned.keys(), key=sort_key)

        for col in ordered_cols:
            out[col] = planned[col]

        return out


_engine_singleton = FeatureEngine()


def build_features(
    df: pd.DataFrame,
    *,
    use_cache: bool = True,
    candle_hash: str | None = None,
    cache_root: Path | None = None,
    engine_version: str = "v1",
    indicators: Iterable[Any] | None = None,
) -> pd.DataFrame:
    """Public feature builder with optional caching.

    Parameters
    ----------
    df : input candle DataFrame
    use_cache : toggle caching (default True)
    candle_hash : required if use_cache True (used as part of key)
    cache_root : directory for feature cache
    engine_version : version string for invalidation
    indicators : override indicator set (defaults to registry contents)
    """
    if not use_cache:
        return _engine_singleton.build_features(df)
    if candle_hash is None or cache_root is None:
        # Fall back to direct compute if insufficient cache params provided
        return _engine_singleton.build_features(df)
    try:
        from infra.cache.features import FeaturesCache
        if indicators is None:
            from domain.indicators.registry import indicator_registry
            indicators = list(indicator_registry.list())
        cache = FeaturesCache(cache_root)

        def builder(inner_df: pd.DataFrame) -> pd.DataFrame:
            return _engine_singleton.build_features(inner_df)

        return cache.load_or_build(
            df,
            indicators,
            builder,
            candle_hash=candle_hash,
            engine_version=engine_version,
        )
    except Exception:
        # Fail-safe: compute directly if cache path has issues
        return _engine_singleton.build_features(df)
