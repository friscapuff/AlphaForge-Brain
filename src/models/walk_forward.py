"""Executed walk-forward segment & aggregate results.

T030 - WalkForward models

These are distinct from the configuration objects (walk_forward_config) and
capture realized outcomes per segment plus an aggregate wrapper.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from .base import BaseModelStrict
from .validation_result import ValidationResult


class WalkForwardSegmentResult(BaseModelStrict):  # FR-046..FR-048
    index: int = Field(ge=0)
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    selected_params: dict[str, int | float | str] = Field(default_factory=dict)
    optimization_score: float | None = None
    validation: list[ValidationResult] = Field(default_factory=list)
    realized_return: float | None = None
    realized_sharpe: float | None = None

    @model_validator(mode="after")
    def _time_order(self) -> WalkForwardSegmentResult:
        if not (self.train_start < self.train_end <= self.test_start < self.test_end):
            raise ValueError("segment temporal ordering invalid")
        return self


class WalkForwardAggregateResult(BaseModelStrict):  # FR-046..FR-048
    segments: list[WalkForwardSegmentResult]
    composite_validation: list[ValidationResult] = Field(default_factory=list)
    overall_return: float | None = None
    overall_sharpe: float | None = None
    robustness_notes: list[str] = Field(default_factory=list)

    def segment_count(self) -> int:
        return len(self.segments)

__all__ = [
    "WalkForwardAggregateResult",
    "WalkForwardSegmentResult",
]
