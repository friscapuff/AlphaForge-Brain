from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class Verbosity(str, Enum):
    production = "production"
    development = "development"
    ci = "ci"


class RedactionMode(str, Enum):
    strict = "strict"  # remove potentially sensitive values from responses/logs
    relaxed = "relaxed"  # allow limited, non-sensitive hints (e.g., counts)


@dataclass
class ErrorPolicy:
    """Environment-driven error verbosity and redaction policy (FR-009, FR-013).

    This placeholder defines the surface. Concrete behavior will be driven by
    tests in T005/T005a and implemented in later tasks.
    """

    verbosity: Verbosity = Verbosity.production
    redaction: RedactionMode = RedactionMode.strict

    @property
    def show_debug(self) -> bool:
        return self.verbosity in (Verbosity.development, Verbosity.ci)

    @staticmethod
    def load_from_env() -> ErrorPolicy:
        mode = os.getenv("ERROR_VERBOSITY", "production").lower().strip()
        if mode in {"dev", "development"}:
            v = Verbosity.development
        elif mode in {"ci"}:
            v = Verbosity.ci
        else:
            v = Verbosity.production
        redaction_raw = os.getenv("ERROR_REDACTION_MODE", "strict").lower().strip()
        if redaction_raw in {"relaxed"}:
            r = RedactionMode.relaxed
        else:
            r = RedactionMode.strict
        return ErrorPolicy(verbosity=v, redaction=r)

    def redact_value(self, value: str | None) -> str | None:
        """Redact a value based on the configured redaction mode.

        Strict mode removes values; relaxed mode can return a generic placeholder.
        """
        if value is None:
            return None
        if self.redaction == RedactionMode.strict:
            return ""
        return "[redacted]"


__all__ = ["ErrorPolicy", "RedactionMode", "Verbosity"]
