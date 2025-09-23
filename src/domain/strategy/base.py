from __future__ import annotations

from typing import Any, Callable, Protocol


class Strategy(Protocol):  # pragma: no cover - structural
    def __call__(self, df: Any, params: dict[str, Any] | None = None) -> Any: ...

StrategyFactory = Callable[[Any, dict[str, Any] | None], Any]

_StrategyFactory = Callable[..., Any]
_REGISTRY: dict[str, _StrategyFactory] = {}


def strategy(name: str) -> Callable[[_StrategyFactory], _StrategyFactory]:
    def decorator(cls: _StrategyFactory) -> _StrategyFactory:
        # Fully idempotent: if name already registered, keep original mapping.
        if name not in _REGISTRY:
            _REGISTRY[name] = cls
        return cls
    return decorator


def get_strategy_registry() -> dict[str, _StrategyFactory]:  # pragma: no cover - trivial
    return dict(_REGISTRY)


class StrategyRegistry:
    @staticmethod
    def get(name: str) -> _StrategyFactory:
        try:
            return _REGISTRY[name]
        except KeyError as e:  # pragma: no cover - defensive
            raise KeyError(f"Strategy not registered: {name}") from e

    @staticmethod
    def list() -> dict[str, _StrategyFactory]:  # pragma: no cover - trivial
        return get_strategy_registry()


__all__ = ["Strategy", "StrategyRegistry", "get_strategy_registry", "strategy"]
