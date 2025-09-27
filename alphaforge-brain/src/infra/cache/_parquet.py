from __future__ import annotations

"""Parquet (pyarrow) availability helpers.

Centralizes lazy detection, lightweight type narrowing, and one-time
structured logging when we degrade to CSV fallback storage. This keeps
cache modules small and consistent while allowing mypy to reason about
the pyarrow branch (without requiring a custom plugin).
"""

from types import ModuleType
from typing import TypeGuard, Any

from infra.logging import get_logger

_PYARROW_MODULE: ModuleType | None | object = object()  # sentinel until first probe
_FALLBACK_LOGGED = False


def _import_pyarrow() -> ModuleType | None:  # pragma: no cover - import outcome env specific
    try:  # Attempt fast path: already cached resolution
        import pyarrow as pa  # type: ignore

        return pa  # type: ignore[no-any-return]
    except Exception:
        return None


def parquet_available() -> bool:
    """Return True if pyarrow import succeeds.

    Result is cached for the process lifetime.
    """
    global _PYARROW_MODULE
    if _PYARROW_MODULE is object() or isinstance(_PYARROW_MODULE, object) and not isinstance(_PYARROW_MODULE, ModuleType):  # first probe or sentinel
        mod = _import_pyarrow()
        _PYARROW_MODULE = mod  # may be None
    return isinstance(_PYARROW_MODULE, ModuleType)


def load_pyarrow() -> ModuleType | None:
    """Return the imported pyarrow module (or None if unavailable)."""
    parquet_available()  # ensure probe executed
    return _PYARROW_MODULE if isinstance(_PYARROW_MODULE, ModuleType) else None


def is_pyarrow(mod: Any) -> TypeGuard[ModuleType]:  # pragma: no cover - trivial
    """TypeGuard to let mypy treat guarded value as a loaded module."""
    return isinstance(mod, ModuleType) and getattr(mod, "__name__", "") == "pyarrow"


def log_csv_fallback_once(reason: str) -> None:
    """Emit a single structured log event the first time we fall back to CSV.

    The event is intentionally terse to stay inexpensive for hot paths.
    """
    global _FALLBACK_LOGGED
    if _FALLBACK_LOGGED:  # pragma: no cover - idempotency guard
        return
    _FALLBACK_LOGGED = True
    logger = get_logger("cache")
    logger.warning("cache_parquet_fallback", reason=reason)


__all__ = [
    "parquet_available",
    "load_pyarrow",
    "is_pyarrow",
    "log_csv_fallback_once",
]
