from __future__ import annotations

from typing import Any

from .base import BaseModelStrict


class StrategyConfig(BaseModelStrict):  # FR-004
    id: str
    required_features: list[str]
    parameters: dict[str, Any]
