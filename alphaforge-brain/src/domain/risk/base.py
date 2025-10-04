from __future__ import annotations

from typing import Any, Callable, Protocol


class RiskModel(Protocol):  # pragma: no cover
    def size(self, equity: float, signal: Any) -> float:  # refine later
        ...


_RiskFactory = Callable[..., RiskModel]
_REGISTRY: dict[str, _RiskFactory] = {}


def risk_model(name: str) -> Callable[[_RiskFactory], _RiskFactory]:
    def decorator(cls: _RiskFactory) -> _RiskFactory:
        if name in _REGISTRY:
            raise ValueError(f"Risk model already registered: {name}")
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_risk_registry() -> dict[str, _RiskFactory]:  # pragma: no cover - trivial
    return dict(_REGISTRY)


__all__ = ["RiskModel", "get_risk_registry", "risk_model"]
