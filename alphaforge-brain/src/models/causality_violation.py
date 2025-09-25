"""Causality violation metric.

T033 - CausalityViolationMetric model

Records counts / severity of forward-looking data usage detected during run.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import BaseModelStrict


class CausalityViolationMetric(BaseModelStrict):  # FR-040..FR-042
    name: str = Field(description="Identifier for the causality check")
    violation_count: int = Field(ge=0)
    severity_score: float = Field(ge=0)
    threshold: float | None = Field(default=None, ge=0)
    breached: bool | None = None

    @model_validator(mode="after")
    def _derive(self) -> CausalityViolationMetric:
        if self.threshold is not None and self.breached is None:
            self.__dict__["breached"] = self.severity_score > self.threshold
        return self


__all__ = ["CausalityViolationMetric"]
