"""Causality guard (T035).

Provides a lightweight context that records attempted forward-looking access.
In STRICT mode it raises; in PERMISSIVE it records violations for later metrics.
Actual data access interception is abstracted; here we expose an API the
execution layer can call when it detects a breach (hook integration later).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import ClassVar


class CausalityMode:
    STRICT: ClassVar[str] = "STRICT"
    PERMISSIVE: ClassVar[str] = "PERMISSIVE"


@dataclass(frozen=True)
class CausalityViolation:
    feature: str
    offset: int  # positive indicates look-ahead bars
    detail: str | None = None


class CausalityGuard:
    def __init__(self, mode: str) -> None:
        if mode not in (CausalityMode.STRICT, CausalityMode.PERMISSIVE):
            raise ValueError("Unknown causality mode")
        self._mode = mode
        self._violations: list[CausalityViolation] = []

    def record(self, feature: str, offset: int, detail: str | None = None) -> None:
        if offset <= 0:
            return  # not a forward look
        violation = CausalityViolation(feature=feature, offset=offset, detail=detail)
        self._violations.append(violation)
        if self._mode == CausalityMode.STRICT:
            raise RuntimeError(f"Causality violation: {feature} offset +{offset}")

    # Backwards compat + explicit name used in tests
    def record_violation(
        self, feature: str, offset: int, detail: str | None = None
    ) -> None:  # pragma: no cover - thin wrapper
        self.record(feature, offset, detail)

    @property
    def violations(self) -> list[CausalityViolation]:  # immutable copy if needed
        return list(self._violations)

    # Method form expected by test_causality_guard (keep both interfaces)
    def violations_(self) -> list[CausalityViolation]:  # pragma: no cover - alias
        return self.violations

    # Provide callable style to match test usage (violations())
    def __call__(self) -> list[CausalityViolation]:  # pragma: no cover
        return self.violations


@contextmanager
def causality_context(mode: str) -> Iterator[CausalityGuard]:
    guard = CausalityGuard(mode)
    # Set as current guard for duration of context
    token = _current_guard.set(guard)
    _enable_pandas_instrumentation(True)
    try:
        yield guard
    finally:
        # Restore previous context value
        _current_guard.reset(token)
        _enable_pandas_instrumentation(False)


@contextmanager
def guard_context(guard: CausalityGuard) -> Iterator[CausalityGuard]:
    """Context manager that uses the provided guard instance as current and enables instrumentation."""
    token = _current_guard.set(guard)
    _enable_pandas_instrumentation(True)
    try:
        yield guard
    finally:
        _current_guard.reset(token)
        _enable_pandas_instrumentation(False)


# Alias if callers prefer semantic name from spec (T110)
CausalAccessContext = CausalityGuard


@contextmanager
def causal_access_context(
    mode: str,
) -> Iterator[CausalAccessContext]:  # pragma: no cover - thin alias
    with causality_context(mode) as g:
        yield g


__all__ = [
    "CausalityGuard",
    "CausalAccessContext",
    "CausalityMode",
    "CausalityViolation",
    "causality_context",
    "causal_access_context",
]

# --- Context propagation helpers ---

# Context variable to hold the current guard instance during feature/strategy execution
_current_guard: ContextVar[CausalityGuard | None] = ContextVar(
    "current_causality_guard", default=None
)


def set_current_guard(guard: CausalityGuard | None) -> None:
    """Set the current guard in context. Prefer using causality_context."""
    _current_guard.set(guard)


def get_current_guard() -> CausalityGuard | None:
    """Return the current CausalityGuard if set in context, else None."""
    return _current_guard.get()


def record_future_access(feature: str, offset: int, detail: str | None = None) -> None:
    """Convenience helper to record a forward-looking access using the current guard.

    If no guard is active, this is a no-op to keep callers lightweight.
    """
    guard = _current_guard.get()
    if guard is not None:
        guard.record(feature, offset, detail)


__all__ += [
    "set_current_guard",
    "get_current_guard",
    "record_future_access",
    "guard_context",
]


# --- Pandas instrumentation to detect lookahead operations (e.g., shift(-1)) ---

_PATCHED: bool = False
_orig_series_shift = None
_orig_frame_shift = None


def _extract_periods(args: tuple[object, ...], kwargs: dict[str, object]) -> int:
    if "periods" in kwargs and isinstance(kwargs["periods"], (int, float)):
        # periods may be float; coerce to int
        return int(kwargs["periods"])
    if args:
        p = args[0]
        if isinstance(p, (int, float)):
            return int(p)
    return 1


def _enable_pandas_instrumentation(enable: bool) -> None:
    global _PATCHED, _orig_series_shift, _orig_frame_shift
    import pandas as _pd  # local import to avoid global dependency at import time

    if enable and not _PATCHED:
        _orig_series_shift = _pd.Series.shift
        _orig_frame_shift = _pd.DataFrame.shift

        def _series_shift(self, *args, **kwargs):  # pragma: no cover - runtime patch
            periods = _extract_periods(args, kwargs)
            if periods is not None and periods < 0:
                record_future_access(
                    feature="pandas.Series.shift",
                    offset=abs(int(periods)),
                    detail=str(periods),
                )
            return _orig_series_shift(self, *args, **kwargs)

        def _frame_shift(self, *args, **kwargs):  # pragma: no cover - runtime patch
            periods = _extract_periods(args, kwargs)
            if periods is not None and periods < 0:
                record_future_access(
                    feature="pandas.DataFrame.shift",
                    offset=abs(int(periods)),
                    detail=str(periods),
                )
            return _orig_frame_shift(self, *args, **kwargs)

        # Runtime monkeypatch (pandas exposes these attributes; ignore no longer needed)
        _pd.Series.shift = _series_shift
        _pd.DataFrame.shift = _frame_shift
        _PATCHED = True
    elif not enable and _PATCHED:
        if _orig_series_shift is not None:
            _pd.Series.shift = _orig_series_shift
        if _orig_frame_shift is not None:
            _pd.DataFrame.shift = _orig_frame_shift
        _PATCHED = False
