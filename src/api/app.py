from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import FastAPI

from api.error_handlers import install_error_handlers
from domain.run.create import InMemoryRunRegistry
from infra.config import (
    get_settings as _get_settings,  # direct import to avoid mypy attr-defined on package proxy
)
from infra.logging import init_logging

try:  # pragma: no cover - lightweight runtime fetch
    from importlib.metadata import version as _version_func  # returns Callable[[str], str]
except Exception:  # pragma: no cover - very old Python
    _version_func = None  # type: ignore[assignment]
_maybe_version: Callable[[str], str] | None = _version_func


def resolve_package_version(dist_name: str) -> str | None:
    """Resolve canonical package version with pyproject as source of truth.

    In editable development the installed distribution metadata can lag behind
    the `pyproject.toml` version (stale wheel). To avoid OpenAPI / README drift
    the pyproject value wins when both sources are available and differ.
    """
    installed: str | None = None
    if _maybe_version is not None:
        try:
            installed = _maybe_version(dist_name)
        except Exception:  # pragma: no cover - fallback path
            installed = None
    py_ver: str | None = None
    try:  # pragma: no cover - trivial parsing
        import tomllib
        pyproj = Path("pyproject.toml")
        if pyproj.exists():
            data = tomllib.loads(pyproj.read_text("utf-8"))
            py_ver = data.get("tool", {}).get("poetry", {}).get("version")
    except Exception:  # pragma: no cover - benign
        py_ver = None
    # Preference order: pyproject (if present), else installed, else None
    return py_ver or installed


def create_app() -> FastAPI:
    settings = _get_settings()
    init_logging()

    # Resolve package version dynamically so FastAPI surface stays in sync with pyproject version.
    resolved_version: str | None = resolve_package_version("project-a-backend")
    app = FastAPI(
        title="Project A Backend",
        version=resolved_version or "0.0.0+dev",
        root_path=settings.api_root_path,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_error_handlers(app)

    # Mount additional routers (T047-T049 + T051)
    try:
        from api.routes.candles import router as candles_router
        app.include_router(candles_router)
    except Exception:  # pragma: no cover - defensive
        pass
    try:
        from api.routes.features import router as features_router
        app.include_router(features_router)
    except Exception:  # pragma: no cover - defensive
        pass
    try:
        from api.routes.presets import router as presets_router
        app.include_router(presets_router)
    except Exception:  # pragma: no cover - defensive
        pass
    try:
        from api.routes.run_events import router as run_events_router
        app.include_router(run_events_router)
    except Exception:  # pragma: no cover - defensive
        pass

    started_at = datetime.now(timezone.utc)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str | int]:  # pragma: no cover - trivial
        now = datetime.now(timezone.utc)
        return {
            "status": "ok",
            "version": app.version,
            "python": platform.python_version(),
            "uptime_sec": int((now - started_at).total_seconds()),
            "build": os.getenv("APP_BUILD", "dev"),
        }

    # In-memory registry singleton (single-user scope)
    registry = InMemoryRunRegistry()
    # Store on app.state for typed access; avoid dynamic attribute for mypy
    if not hasattr(app, "state"):
        raise RuntimeError("FastAPI app missing state object")
    app.state.registry = registry  # app.state is dynamic, acceptable for runtime; ignore removed

    # Attach new runs router (T050-T051 implementation)
    try:  # pragma: no cover - defensive
        from api.routes.runs import router as runs_router
        app.include_router(runs_router)
    except Exception:  # pragma: no cover
        pass
    # Existing SSE routes (run_events) already mounted earlier (legacy). Future refactor will consolidate.

    # (Existing artifact endpoints removed here; future T055+ will reintroduce refined versions.)

    return app


app = create_app()
