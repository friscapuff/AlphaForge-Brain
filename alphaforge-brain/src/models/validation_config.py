from __future__ import annotations

from pydantic import Field, model_validator

from .base import BaseModelStrict


class ValidationConfig(BaseModelStrict):  # FR-019..FR-022
    permutation_trials: int = Field(ge=0)
    seed: int = Field(ge=0)
    caution_p_threshold: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _validate_threshold(self) -> ValidationConfig:
        if self.caution_p_threshold == 0:
            raise ValueError("caution_p_threshold must be > 0 for meaningful warning")
        return self
