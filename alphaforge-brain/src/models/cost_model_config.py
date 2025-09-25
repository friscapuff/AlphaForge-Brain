from __future__ import annotations

from pydantic import Field, model_validator

from .base import BaseModelStrict


class CostModelConfig(BaseModelStrict):  # FR-008, FR-039
    slippage_bps: float = Field(ge=0)
    spread_pct: float | None = Field(default=None, ge=0)
    participation_rate: float | None = Field(default=None, ge=0)
    fee_bps: float = Field(ge=0)
    borrow_cost_bps: float = Field(ge=0)

    @model_validator(mode="after")
    def _xor_extended_model(self) -> CostModelConfig:
        if self.spread_pct is not None and self.participation_rate is not None:
            raise ValueError("spread_pct and participation_rate are mutually exclusive")
        return self
