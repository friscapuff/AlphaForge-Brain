"""Runtime import guard preventing Brain↔Mind cross-root imports."""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from services.audit.governance_logger import record_governance_event

_BANNED_PREFIX = "alphaforge_mind"
_ALLOWED_IMPORTER_PREFIXES: tuple[str, ...] = ("shared.", "tests.", "alphaforge_mind.")
_DISABLE_ENV = "ALPHAFORGE_IMPORT_GUARD_DISABLE"
_ALLOW_ENV = "ALPHAFORGE_IMPORT_GUARD_ALLOW"
_LOG_PATH_ENV = "IMPORT_GUARD_LOG_PATH"
_DEFAULT_LOG_PATH = Path("zz_artifacts/import_guard/events.json")
_ACTIVE_GUARD: CrossRootImportGuard | None = None


class CrossRootImportError(ImportError):
    """Raised when a forbidden cross-root import is attempted."""

    def __init__(self, module: str, *, importer: str | None = None) -> None:
        message = (
            f"Importing '{module}' from AlphaForge Brain runtime is not permitted"
            " (see Principle IX: dual-root separation)."
        )
        if importer:
            message += f" Detected from importer '{importer}'."
        super().__init__(message)
        self.module = module
        self.importer = importer


class CrossRootImportGuard(importlib.abc.MetaPathFinder):
    """Meta path finder that blocks imports of forbidden module prefixes."""

    def __init__(self, allowed_importers: Sequence[str]) -> None:
        self.allowed_importers = tuple(allowed_importers)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: object | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith(_BANNED_PREFIX):
            return None

        if _import_allowed(self.allowed_importers):
            return None

        importer = _current_importer()
        _record_blocked_import(fullname, importer)
        raise CrossRootImportError(fullname, importer=importer)


def _import_allowed(allowed_importers: Sequence[str]) -> bool:
    callers = _caller_modules()
    for module in callers:
        if any(module.startswith(prefix) for prefix in allowed_importers):
            return True
    extra_allow = _extra_allowed_importers()
    if extra_allow:
        for module in callers:
            if any(module.startswith(prefix) for prefix in extra_allow):
                return True
    return False


def _caller_modules() -> list[str]:
    modules: list[str] = []
    for frame in inspect.stack()[1:]:  # skip this module frame
        module = frame.frame.f_globals.get("__name__")
        if module:
            modules.append(module)
    return modules


def _current_importer() -> str | None:
    callers = _caller_modules()
    return callers[0] if callers else None


def _extra_allowed_importers() -> tuple[str, ...]:
    raw = os.getenv(_ALLOW_ENV)
    if not raw:
        return ()
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(parts)


def _resolve_log_path() -> Path:
    override = os.getenv(_LOG_PATH_ENV)
    path = Path(override) if override else _DEFAULT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _record_blocked_import(module: str, importer: str | None) -> None:
    log_path = _resolve_log_path()
    payload = {
        "module": module,
        "importer": importer,
        "stack": _caller_modules(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")

    record_governance_event(
        message="import.guard.blocked",
        details={"module": module, "importer": importer},
    )


def install_import_guard() -> CrossRootImportGuard | None:
    """Install the import guard on ``sys.meta_path`` if not disabled."""

    global _ACTIVE_GUARD

    if os.getenv(_DISABLE_ENV, "").lower() in {"1", "true", "on"}:
        return None

    if _ACTIVE_GUARD is not None:
        return _ACTIVE_GUARD

    guard = CrossRootImportGuard(_ALLOWED_IMPORTER_PREFIXES)
    sys.meta_path.insert(0, guard)
    _ACTIVE_GUARD = guard
    return guard


def uninstall_import_guard() -> None:
    """Remove the import guard if currently installed."""

    global _ACTIVE_GUARD

    if _ACTIVE_GUARD and _ACTIVE_GUARD in sys.meta_path:
        sys.meta_path.remove(_ACTIVE_GUARD)
    _ACTIVE_GUARD = None


def is_guard_installed() -> bool:
    return _ACTIVE_GUARD is not None


__all__ = [
    "CrossRootImportError",
    "CrossRootImportGuard",
    "install_import_guard",
    "uninstall_import_guard",
    "is_guard_installed",
]
