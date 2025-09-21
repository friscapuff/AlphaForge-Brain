from __future__ import annotations

from typing import Any, Callable

_ValidationFunc = Callable[..., Any]
_REGISTRY: dict[str, _ValidationFunc] = {}

def validation_test(name: str) -> Callable[[_ValidationFunc], _ValidationFunc]:
    def decorator(fn: _ValidationFunc) -> _ValidationFunc:
        if name in _REGISTRY:
            raise ValueError(f"Validation test already registered: {name}")
        _REGISTRY[name] = fn
        return fn
    return decorator


def get_validation_registry() -> dict[str, _ValidationFunc]:  # pragma: no cover - trivial
    return dict(_REGISTRY)


__all__ = ["get_validation_registry", "validation_test"]
