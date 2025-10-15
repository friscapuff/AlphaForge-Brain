"""TradeContextSnapshot model for enriched journaling (Phase 016)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import Field, model_validator

from .base import BaseModelStrict


class TradeContextSnapshot(BaseModelStrict):
    id: str
    schema_version: str = Field(default="2025.10.16")
    trade_id: str
    collected_at: datetime
    market_symbol: str
    bid: float | None = None
    ask: float | None = None
    spread_bps: float | None = None
    volatility_score: float | None = Field(default=None, ge=0.0)
    volume_window: float | None = Field(default=None, ge=0.0)
    checklist: dict[str, str] = Field(default_factory=dict)
    indicators: dict[str, float] = Field(default_factory=dict)
    notes: str | None = None

    @model_validator(mode="after")
    def _normalise_maps(self) -> TradeContextSnapshot:
        checklist = {str(key): str(value) for key, value in self.checklist.items()}
        self.__dict__["checklist"] = dict(sorted(checklist.items()))

        indicator_items = []
        for key, value in self.indicators.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            indicator_items.append((str(key), numeric))
        indicator_items.sort(key=lambda item: item[0])
        self.__dict__["indicators"] = {key: val for key, val in indicator_items}
        return self

    def model_dump_for_hash(self) -> Mapping[str, Any]:
        return self.model_dump(mode="json")


__all__ = ["TradeContextSnapshot"]
