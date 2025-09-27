from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

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
        "zero_volume",  # threaded from canonical dataset (NVDA integration T020)
    )

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Work on a copy to guarantee idempotency
        out = df.copy(deep=True)
        # zero_volume threading: if present it remains; engine does not create or drop it.

        # Collect planned feature columns per indicator
        indicator_objects = list(indicator_registry.list())

        # Support legacy function-style indicators (like dual_sma) via registry facade
        try:
            fn_indicator_registry = IndicatorRegistry.list()
        except Exception:  # pragma: no cover - defensive
            fn_indicator_registry = {}

        planned: dict[str, pd.Series] = {}
        # Treat all existing columns as reserved/base; function-style indicators often echo inputs
        base_cols: set[str] = set(map(str, out.columns)) | set(self.base_columns)

        # First apply function style indicators (they return full DataFrame with features), then object style
        for _name, fn in sorted(fn_indicator_registry.items()):  # deterministic order
            # Call legacy function indicator without unsupported params kwarg (mypy call-arg fix)
            try:
                feats = fn(out)
            except Exception:
                continue
            # Normalize outputs
            if isinstance(feats, pd.Series):
                feats = feats.to_frame()
            elif not isinstance(feats, pd.DataFrame):
                # Support legacy shapes like (DataFrame, meta) or list with DataFrame first
                if (
                    isinstance(feats, (list, tuple))
                    and feats
                    and isinstance(feats[0], (pd.DataFrame, pd.Series))
                ):
                    feats = feats[0]
                    if isinstance(feats, pd.Series):
                        feats = feats.to_frame()
                else:
                    # Unknown return type; ignore
                    continue
            # Add only new columns (ignore any base/original columns echoed by the function)
            for c in feats.columns:
                if c in base_cols:
                    continue
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
            # Assign columns using Index to satisfy pandas typing expectations (avoid list->Index assignment mismatch)
            feats.columns = pd.Index(cols)

            for c in cols:
                if c in base_cols:
                    # Don't allow overriding original columns
                    raise ValueError(f"Feature column collides with base column: {c}")
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

    def build_features_chunked(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int,
        overlap: int = 0,
    ) -> pd.DataFrame:
        """Compute features in deterministic chunks and stitch results.

        Contract (FR-130/131):
        - Preserve original index order and values.
        - Output must be identical to monolithic build for same inputs.
        - Overlap ensures rolling-window indicators near chunk boundaries are correct.
        """
        from services.chunking import iter_chunk_slices

        if chunk_size <= 0 or chunk_size >= len(df):
            return self.build_features(df)

        # Prepare output as a copy of input to maintain base columns and idempotency
        out = df.copy(deep=True)
        feature_cols_order: list[str] | None = None

        n = len(df)
        for start, end, drop in iter_chunk_slices(n, chunk_size, overlap):
            window = df.iloc[start:end]
            built = self.build_features(window)
            if drop > 0:
                built = built.iloc[drop:]

            # On first chunk, discover feature columns and initialize them in final DataFrame
            if feature_cols_order is None:
                base_cols: set[str] = set(map(str, df.columns)) | set(self.base_columns)
                feature_cols_order = [c for c in built.columns if c not in base_cols]
                # Initialize columns in deterministic order
                for c in feature_cols_order:
                    out[c] = pd.Series(index=df.index, dtype=built[c].dtype)

            assert feature_cols_order is not None
            # Compute target slice aligned to original df index
            tgt_start = start + drop
            tgt_end = end
            if tgt_start >= tgt_end:
                continue
            # Assign only feature columns for the non-overlap region using positional indexing
            row_count = tgt_end - tgt_start
            if row_count > 0:
                out.iloc[
                    tgt_start:tgt_end, out.columns.get_indexer(feature_cols_order)
                ] = built.iloc[:row_count][feature_cols_order].to_numpy()

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
    chunk_size: int | None = None,
    overlap: int | None = None,
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
        if isinstance(chunk_size, int) and chunk_size > 0:
            eff_overlap = _compute_overlap(df, indicators, chunk_size, overlap)
            return _engine_singleton.build_features_chunked(df, chunk_size=chunk_size, overlap=eff_overlap)
        return _engine_singleton.build_features(df)
    if candle_hash is None or cache_root is None:
        if isinstance(chunk_size, int) and chunk_size > 0:
            eff_overlap = _compute_overlap(df, indicators, chunk_size, overlap)
            return _engine_singleton.build_features_chunked(df, chunk_size=chunk_size, overlap=eff_overlap)
        return _engine_singleton.build_features(df)
    # Caching path
    # Resolve indicators list deterministically
    if indicators is None:
        from domain.indicators.registry import indicator_registry as _reg

        indicators = list(_reg.list())
    # Instantiate cache
    from infra.cache.features import FeaturesCache

    cache = FeaturesCache(cache_root)

    def _builder(inner_df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(chunk_size, int) and chunk_size > 0:
            eff_overlap = _compute_overlap(inner_df, indicators, chunk_size, overlap)
            return _engine_singleton.build_features_chunked(inner_df, chunk_size=chunk_size, overlap=eff_overlap)
        return _engine_singleton.build_features(inner_df)

    # Indicators is guaranteed non-None here
    assert indicators is not None
    inds_for_cache = indicators
    return cache.load_or_build(
        df,
        inds_for_cache,
        _builder,
        candle_hash=candle_hash,
        engine_version=engine_version,
    )


def build_features_auto_chunk(
    df: pd.DataFrame,
    *,
    target_chunk_mb: int = 256,
    max_rows_cap: int = 2_000_000,
    use_cache: bool = False,
    candle_hash: str | None = None,
    cache_root: Path | None = None,
    engine_version: str = "v1",
    indicators: Iterable[Any] | None = None,
    overlap: int | None = None,
) -> pd.DataFrame:
    """Convenience wrapper: choose chunk size by memory budget and delegate to build_features.

    If use_cache is True, candle_hash and cache_root should be provided; otherwise it
    will compute directly.
    """
    try:
        from services.chunking import choose_chunk_size

        cs = choose_chunk_size(df, target_chunk_mb=target_chunk_mb, max_rows_cap=max_rows_cap)
    except Exception:
        # Fallback to monolithic if estimation fails
        cs = 0
    return build_features(
        df,
        use_cache=use_cache,
        candle_hash=candle_hash,
        cache_root=cache_root,
        engine_version=engine_version,
        indicators=indicators,
        chunk_size=cs,
        overlap=overlap,
    )

# --- Internal helpers ---
def _compute_overlap(
    df: pd.DataFrame,
    indicators: Iterable[Any] | None,
    chunk_size: int,
    overlap: int | None,
) -> int:
    """Infer effective overlap for chunked feature computation.

    Combines object and function-style indicators and takes max required overlap.
    Returns 0 on any failure (fail-safe) to avoid blocking computation.
    """
    eff_overlap = 0 if overlap is None else int(overlap)
    if overlap is not None:
        return eff_overlap
    try:
        from domain.indicators.registry import IndicatorRegistry as _FnReg
        from domain.indicators.registry import indicator_registry as _reg
        from services.chunking import (
            compute_required_overlap,
            compute_required_overlap_for_functions,
        )

        if indicators is None:
            objs = list(_reg.list())
        else:
            objs = list(indicators)
        eff_overlap = compute_required_overlap(objs)
        try:
            fn_map = _FnReg.list()
            sample = df.iloc[: max(100, min(len(df), 500))]
            fn_ov = compute_required_overlap_for_functions(
                fn_map, sample, _engine_singleton.base_columns
            )
            if fn_ov > eff_overlap:
                eff_overlap = fn_ov
        except Exception:
            pass
    except Exception:
        eff_overlap = 0
    return eff_overlap
