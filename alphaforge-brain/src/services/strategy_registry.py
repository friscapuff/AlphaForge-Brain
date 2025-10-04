"""Strategy registry optional metadata recorder (T046).

Stores arbitrary metadata keyed by strategy id for later inclusion in manifest.
"""

from __future__ import annotations

from typing import Any


class StrategyRegistry:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def register(self, strategy_id: str, metadata: dict[str, Any]) -> None:
        self._data[strategy_id] = dict(sorted(metadata.items()))

    def get(self, strategy_id: str) -> dict[str, Any] | None:
        return self._data.get(strategy_id)

    def all(self) -> dict[str, dict[str, Any]]:
        return {k: v.copy() for k, v in self._data.items()}


__all__ = ["StrategyRegistry"]
