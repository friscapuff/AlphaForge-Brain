from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

# Phase J (G03): dataset registry mapping (symbol,timeframe) -> provider/path/calendar metadata.


@dataclass(slots=True)
class DatasetEntry:
    symbol: str
    timeframe: str
    provider: str
    path: str | None = None  # For local_csv
    calendar_id: str | None = None


_DATASET_REGISTRY: dict[tuple[str, str], DatasetEntry] = {}


def register_dataset(entry: DatasetEntry) -> None:
    key = (entry.symbol.upper(), entry.timeframe)
    _DATASET_REGISTRY[key] = entry  # overwrite allowed for updates/tests


def get_dataset(symbol: str, timeframe: str) -> DatasetEntry:
    key = (symbol.upper(), timeframe)
    try:
        return _DATASET_REGISTRY[key]
    except KeyError as e:  # pragma: no cover - defensive
        raise KeyError(
            f"Dataset not registered for symbol={symbol} timeframe={timeframe}"
        ) from e


def list_datasets() -> list[DatasetEntry]:  # pragma: no cover - trivial
    return list(_DATASET_REGISTRY.values())


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


__all__ = [
    "DatasetEntry",
    "ProviderRegistry",
    "get_dataset",
    "get_provider_registry",
    "list_datasets",
    "provider",
    "provider_registry",
    "register_dataset",
]
