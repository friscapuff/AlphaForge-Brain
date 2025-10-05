from __future__ import annotations

from pydantic import Field, model_validator

from .base import BaseModelStrict


class WalkForwardSegmentConfig(BaseModelStrict):  # FR-046, FR-048
    train_bars: int = Field(ge=1)
    test_bars: int = Field(ge=1)
    warmup_bars: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_relationships(self) -> WalkForwardSegmentConfig:
        if self.warmup_bars >= self.train_bars:
            raise ValueError("warmup_bars must be < train_bars")
        return self


class WalkForwardOptimizationConfig(BaseModelStrict):  # FR-046
    enabled: bool = True
    param_grid: dict[str, list[int | float | str]]

    @model_validator(mode="after")
    def _non_empty(self) -> WalkForwardOptimizationConfig:
        if self.enabled and not self.param_grid:
            raise ValueError("param_grid required when optimization enabled")
        return self


class WalkForwardRobustnessConfig(BaseModelStrict):  # FR-047
    compute: bool = True


class WalkForwardConfig(BaseModelStrict):  # FR-046..FR-048
    segment: WalkForwardSegmentConfig
    optimization: WalkForwardOptimizationConfig
    robustness: WalkForwardRobustnessConfig
