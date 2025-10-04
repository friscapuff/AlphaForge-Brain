"""Type-friendly cache metrics shim.

Provides minimal definitions used for type checking. Runtime may use
implementation under src.infra.cache.metrics; this shim's API matches.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    rebuilds: int = 0
    writes: int = 0

    def snapshot(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "rebuilds": self.rebuilds,
            "writes": self.writes,
        }


class CacheMetricsRecorder:
    def __init__(self) -> None:
        self._m = CacheMetrics()
        self._lock = Lock()

    def record_hit(self) -> None:
        with self._lock:
            self._m.hits += 1

    def record_miss(self) -> None:
        with self._lock:
            self._m.misses += 1

    def record_rebuild(self) -> None:
        with self._lock:
            self._m.rebuilds += 1

    def record_write(self) -> None:
        with self._lock:
            self._m.writes += 1

    def get(self) -> CacheMetrics:
        return self._m


cache_metrics = CacheMetricsRecorder()

__all__ = ["CacheMetrics", "CacheMetricsRecorder", "cache_metrics"]
