"""Statistical validation results for a single metric.

T029 - ValidationResult model

Holds permutation / bootstrap distributions and derived p-values. Higher level
aggregation (multiple metrics, composite judgment) will occur elsewhere.
"""

from __future__ import annotations

from statistics import mean

from pydantic import Field, model_validator

from .base import BaseModelStrict


class ValidationResult(BaseModelStrict):  # FR-019..FR-024
    metric_name: str
    observed_value: float
    permutation_distribution: list[float] = Field(default_factory=list)
    p_value: float | None = Field(default=None, ge=0, le=1)
    caution_threshold: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _derive_or_check(self) -> ValidationResult:
        if self.p_value is None and self.permutation_distribution:
            greater = sum(
                1 for x in self.permutation_distribution if x >= self.observed_value
            )
            self.__dict__["p_value"] = greater / len(self.permutation_distribution)
        if self.p_value is not None and not (0 <= self.p_value <= 1):
            raise ValueError("p_value outside [0,1]")
        return self

    def is_caution(self) -> bool:
        if self.p_value is None or self.caution_threshold is None:
            return False
        return self.p_value < self.caution_threshold

    def distribution_mean(self) -> float | None:
        if not self.permutation_distribution:
            return None
        return mean(self.permutation_distribution)


__all__ = ["ValidationResult"]
