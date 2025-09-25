from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    rebuilds: int = 0  # corruption or forced rebuild
    writes: int = 0

    def snapshot(self) -> dict[str, int]:  # pragma: no cover - trivial
        return {
            "hits": self.hits,
            "misses": self.misses,
            "rebuilds": self.rebuilds,
            "writes": self.writes,
        }


class CacheMetricsRecorder:
    def __init__(self) -> None:
        self._metrics = CacheMetrics()
        self._lock = Lock()

    def record_hit(self) -> None:
        with self._lock:
            self._metrics.hits += 1

    def record_miss(self) -> None:
        with self._lock:
            self._metrics.misses += 1

    def record_rebuild(self) -> None:
        with self._lock:
            self._metrics.rebuilds += 1

    def record_write(self) -> None:
        with self._lock:
            self._metrics.writes += 1

    def get(self) -> CacheMetrics:
        return self._metrics


# Singleton (simple global) usable by caches
cache_metrics = CacheMetricsRecorder()

__all__ = ["CacheMetrics", "CacheMetricsRecorder", "cache_metrics"]
