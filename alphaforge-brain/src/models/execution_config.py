from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BaseModelStrict


class FillPolicy(str, Enum):  # FR-007
    NEXT_BAR_OPEN = "NEXT_BAR_OPEN"
    NEXT_TICK_SURROGATE = "NEXT_TICK_SURROGATE"


class RoundingMode(str, Enum):  # FR-009
    FLOOR = "FLOOR"
    ROUND = "ROUND"
    CEIL = "CEIL"


class ExecutionConfig(BaseModelStrict):  # FR-007, FR-009
    fill_policy: FillPolicy = Field(description="Timing of fills")
    lot_size: int = Field(ge=1)
    rounding_mode: RoundingMode
