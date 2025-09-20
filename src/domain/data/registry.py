from __future__ import annotations

from typing import Any, Callable, Iterable

_ProviderFunc = Callable[..., Any]
_REGISTRY: dict[str, _ProviderFunc] = {}


def provider(name: str) -> Callable[[_ProviderFunc], _ProviderFunc]:
    def decorator(fn: _ProviderFunc) -> _ProviderFunc:
        if name in _REGISTRY:
            raise ValueError(f"Provider already registered: {name}")
        _REGISTRY[name] = fn
        return fn
    return decorator


def get_provider_registry() -> dict[str, _ProviderFunc]:  # pragma: no cover - trivial
    return dict(_REGISTRY)


class ProviderRegistry:
    @staticmethod
    def get(name: str) -> _ProviderFunc:
        try:
            return _REGISTRY[name]
        except KeyError as e:  # pragma: no cover - defensive
            raise KeyError(f"Provider not registered: {name}") from e

    @staticmethod
    def list() -> dict[str, _ProviderFunc]:  # pragma: no cover - trivial
        return get_provider_registry()


class _ProviderObjectRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Any] = {}

    def register(self, name: str, provider: Any) -> Any:
        # Overwrite to allow test isolation / provider replacement
        self._items[name] = provider
        return provider

    def get(self, name: str) -> Any:
        return self._items[name]

    def list(self) -> Iterable[Any]:  # pragma: no cover - trivial
        return list(self._items.values())


provider_registry = _ProviderObjectRegistry()


__all__ = ["provider", "get_provider_registry", "ProviderRegistry", "provider_registry"]
