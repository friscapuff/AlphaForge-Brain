from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from infra.utils.hash import canonical_json, hash_canonical


class MetricsSummary(BaseModel):
    trades: int = 0
    returns_total: float = 0.0
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float = 0.0  # negative value
    volatility: float | None = None

    def canonical_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")

    def canonical_hash(self) -> str:
        h: str = hash_canonical(self.canonical_dict())
        return h

    def canonical_json(self) -> str:
        s: str = canonical_json(self.canonical_dict())
        return s

__all__ = ["MetricsSummary"]
