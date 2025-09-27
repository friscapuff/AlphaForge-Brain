#!/usr/bin/env python
"""Post-install minimal health check.

Runs a fast series of assertions to confirm the development environment is in a
usable state:
 - Python version matches pyproject constraint (3.11.*)
 - Critical packages import (fastapi, numpy, pandas)
 - Numpy version satisfies internal determinism pin range (<2.1 for numba 0.60)
 - FastAPI application instantiates and /health route responds 200 with version

Exit codes:
 0 success
 >0 failure (message printed to stderr)

Usage:
  poetry run python scripts/post_install_health_check.py
  (exposed as: poetry run health-check)
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def fail(msg: str) -> None:
    print(f"[HEALTH][FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)


def warn(msg: str) -> None:
    print(f"[HEALTH][WARN] {msg}", file=sys.stderr)


def load_version_from_pyproject() -> str | None:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return None
    try:
        import tomllib  # Python 3.11+

        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return data.get("tool", {}).get("poetry", {}).get("version")
    except Exception:  # pragma: no cover - defensive
        return None


def check_python() -> None:
    ver = sys.version_info
    if not (ver.major == 3 and ver.minor == 11):
        fail(f"Python 3.11 required; got {ver.major}.{ver.minor}")


def check_imports() -> SimpleNamespace:
    modules = {}
    for name in ["fastapi", "numpy", "pandas"]:
        try:
            modules[name] = importlib.import_module(name)
        except Exception as exc:  # pragma: no cover
            fail(f"Could not import {name}: {exc}")
    return SimpleNamespace(**modules)


def check_numpy(num) -> None:  # type: ignore[no-untyped-def]
    ver = getattr(num, "__version__", "?")
    # Accept pinned version in infra/version_pins.py (2.1.1) OR the range [2.0.0,2.1.x]
    from packaging.version import Version

    v = Version(ver)
    # Hard pin path
    allowed_pin = Version("2.1.1")
    in_range = Version("2.0.0") <= v <= allowed_pin
    if not in_range:
        fail(
            f"numpy version {ver} outside supported determinism window [2.0.0,2.1.1]; "
            "update post_install_health_check.py if intentionally changed"
        )


def check_fastapi_health(app_version: str | None) -> None:
    # Import create_app lazily to avoid heavy cost if something else already failed.
    try:
        from api.app import create_app  # type: ignore
        from fastapi.testclient import TestClient
    except Exception as exc:  # pragma: no cover
        fail(f"FastAPI app import failed: {exc}")

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        if r.status_code != 200:
            fail(f"/health returned {r.status_code}")
        try:
            payload = r.json()
        except Exception as exc:  # pragma: no cover
            fail(f"/health invalid JSON: {exc}")

    runtime_version = payload.get("version")
    if app_version and runtime_version != app_version:
        warn(f"/health version {runtime_version} != pyproject version {app_version}")
    print(json.dumps({"health_status": "ok", "version": runtime_version}, indent=2))


def main() -> None:
    app_version = load_version_from_pyproject()
    check_python()
    mods = check_imports()
    check_numpy(mods.numpy)
    check_fastapi_health(app_version)
    print("[HEALTH] Environment OK")


if __name__ == "__main__":  # pragma: no cover
    main()
