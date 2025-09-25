"""Causality guard (T035).

Provides a lightweight context that records attempted forward-looking access.
In STRICT mode it raises; in PERMISSIVE it records violations for later metrics.
Actual data access interception is abstracted; here we expose an API the
execution layer can call when it detects a breach (hook integration later).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
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
    yield guard


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
