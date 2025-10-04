#!/usr/bin/env python3
"""Quick environment sanity check.

Emits JSON describing availability and versions of critical runtime libs.
Safe to run pre-test to diagnose missing dependencies (e.g. SQLAlchemy).
Exit codes:
 0: All required packages importable
 1: One or more required packages missing

Optional packages are reported but do not affect exit code.
"""
from __future__ import annotations

import importlib
import json
import sys
from typing import Any

try:  # local import; if path not set, allow silent fallback
    from infra.version_pins import PINNED  # type: ignore
except Exception:  # pragma: no cover - defensive
    PINNED = {}

REQUIRED = [
    ("fastapi", None),
    ("pydantic", None),
    ("numpy", None),
    ("pandas", None),
    (
        "SQLAlchemy",
        "sqlalchemy",
    ),  # user may refer to capitalized name; import is sqlalchemy
]

OPTIONAL = [
    ("pyarrow", None),
    ("structlog", None),
]


def _probe(mod_name: str) -> tuple[bool, str | None]:
    try:
        m = importlib.import_module(mod_name)
        ver = getattr(m, "__version__", None)
        return True, ver if isinstance(ver, str) else None
    except Exception:
        return False, None


def main() -> int:
    report: dict[str, Any] = {"required": {}, "optional": {}, "pinned_mismatch": {}}
    missing = []
    for display, real in REQUIRED:
        name = real or display
        ok, ver = _probe(name)
        info: dict[str, Any] = {"ok": ok, "version": ver}
        pinned = PINNED.get(display.lower()) or PINNED.get(display)
        if pinned and ver and ver != pinned:
            info["expected"] = pinned
            report["pinned_mismatch"][display] = {"expected": pinned, "found": ver}
        report["required"][display] = info
        if not ok:
            missing.append(display)
    for display, real in OPTIONAL:
        name = real or display
        ok, ver = _probe(name)
        report["optional"][display] = {"ok": ok, "version": ver}
    status = "ok" if not missing else "missing"
    if report["pinned_mismatch"]:
        status = "drift" if status == "ok" else status + "+drift"
    report["status"] = status
    report["missing"] = missing
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if not missing else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
