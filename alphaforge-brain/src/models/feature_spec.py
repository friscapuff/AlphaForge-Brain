from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import BaseModelStrict


class FeatureSpec(BaseModelStrict):  # FR-004, FR-005
    name: str
    version: str
    inputs: list[str]
    params: dict[str, Any] = Field(default_factory=dict)
    shift_applied: bool
