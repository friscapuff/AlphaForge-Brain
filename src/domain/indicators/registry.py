from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

import pandas as pd


class IndicatorProtocol:
    """Lightweight structural protocol for indicators.

    An indicator object should expose:
      - compute(df: pd.DataFrame) -> pd.DataFrame | pd.Series
      - feature_columns() -> list[str]  (names of columns produced)
      - name attribute (used only for diagnostics / sorting fallback)
    We don't formally `typing.Protocol` here to keep runtime dependencies minimal.
    """

    name: str

    def compute(self, df: pd.DataFrame) -> pd.DataFrame | pd.Series:
        raise NotImplementedError

    def feature_columns(self) -> list[str]:
        raise NotImplementedError


class _IndicatorRegistry:
    """Runtime registry for indicator objects.

    Design goals:
      - Preserve insertion order (list internally).
      - Idempotent register: re-registering the same object is a no-op.
      - Allow multiple distinct objects even if same class/params (engine handles duplicate feature collisions explicitly).
    """

    def __init__(self) -> None:
        self._items: list[IndicatorProtocol] = []

    def register(self, indicator: IndicatorProtocol) -> IndicatorProtocol:
        # Idempotent by object identity
        if indicator not in self._items:
            self._items.append(indicator)
        return indicator

    def list(self) -> Iterable[IndicatorProtocol]:
        # Return shallow copy to prevent external mutation
        return list(self._items)

    def clear(self) -> None:  # pragma: no cover - only for potential test resets
        self._items.clear()


# Singleton exported for import usage in tests
indicator_registry = _IndicatorRegistry()

IndicatorFn = Callable[[pd.DataFrame], pd.DataFrame | pd.Series]
_FUNCTION_REGISTRY: dict[str, IndicatorFn] = {}


def indicator(name: str) -> Callable[[IndicatorFn], IndicatorFn]:
    """Function decorator registration API (back-compat with earlier tests).

    Enforces unique names; raises ValueError on duplicate registration.
    Registered callables are stored separately from object-based registry.
    """

    def decorator(fn: IndicatorFn) -> IndicatorFn:
        if name in _FUNCTION_REGISTRY:
            raise ValueError(f"Indicator already registered: {name}")
        _FUNCTION_REGISTRY[name] = fn
        return fn

    return decorator


def get_indicator_registry() -> dict[str, IndicatorFn]:  # pragma: no cover - trivial
    return dict(_FUNCTION_REGISTRY)


__all__ = [
    "IndicatorProtocol",
    "get_indicator_registry",
    "indicator",
    "indicator_registry",
]


class IndicatorRegistry:  # Back-compat facade for tests referencing IndicatorRegistry.get
    @staticmethod
    def get(name: str) -> IndicatorFn:  # returns function style indicator if present
        reg = get_indicator_registry()
        try:
            return reg[name]
        except KeyError as e:  # pragma: no cover
            raise KeyError(f"Indicator not registered: {name}") from e

    @staticmethod
    def list() -> dict[str, IndicatorFn]:  # pragma: no cover - trivial
        return get_indicator_registry()

__all__.append("IndicatorRegistry")
