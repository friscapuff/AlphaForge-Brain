"""API request validation schemas (T049).

Defines Pydantic models for incoming run creation & query parameters.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    strategy_id: str
    features: list[str]
    params: dict[str, Any] = Field(default_factory=dict)
    walk_forward: bool = False


class RunQuery(BaseModel):
    include_anomalies: bool = False
    include_validation: bool = True


__all__ = ["RunCreateRequest", "RunQuery"]
