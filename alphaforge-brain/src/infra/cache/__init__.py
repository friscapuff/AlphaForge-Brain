from __future__ import annotations

from typing import Protocol, runtime_checkable

try:
    from .candles import CandleCache
except Exception:  # pragma: no cover - mypy shim fallback

    @runtime_checkable
    class CandleCache(Protocol):  # type: ignore[no-redef]
        ...


try:
    from .features import FeaturesCache
except Exception:  # pragma: no cover

    @runtime_checkable
    class FeaturesCache(Protocol):  # type: ignore[no-redef]
        ...


try:
    from .metrics import CacheMetrics, CacheMetricsRecorder, cache_metrics
except Exception:  # pragma: no cover

    class CacheMetrics:  # type: ignore[no-redef]
        hits: int
        misses: int
        rebuilds: int
        writes: int

    class CacheMetricsRecorder:  # type: ignore[no-redef]
        def record_hit(self) -> None: ...
        def record_miss(self) -> None: ...
        def record_rebuild(self) -> None: ...
        def record_write(self) -> None: ...
        def get(self) -> CacheMetrics:
            # Provide a concrete return to satisfy strict mypy in fallback shim
            return CacheMetrics()

    cache_metrics = CacheMetricsRecorder()

__all__ = [
    "CacheMetrics",
    "CacheMetricsRecorder",
    "CandleCache",
    "FeaturesCache",
    "cache_metrics",
]
