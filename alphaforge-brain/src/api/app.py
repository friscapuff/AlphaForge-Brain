from __future__ import annotations

import logging
import os
import platform
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

from api.error_handlers import install_error_handlers
from api.middleware.correlation import correlation_middleware
from domain.run.create import InMemoryRunRegistry
from fastapi import FastAPI
from fastapi import Request as _Request
from fastapi import Response as _Response

from infra.config import (
    get_settings as _get_settings,  # direct import to avoid mypy attr-defined on package proxy
)
from infra.import_guard import install_import_guard
from infra.logging import init_logging

try:  # pragma: no cover - lightweight runtime fetch
    from importlib.metadata import version as _importlib_version

    _version_func: Callable[[str], str] | None = _importlib_version
except Exception:  # pragma: no cover - very old Python
    _version_func = None
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


def _install_custom_openapi(app: FastAPI) -> None:
    """Attach OpenAPI schema factory that injects shared components."""

    try:  # pragma: no cover - exercised indirectly by tests
        from fastapi.openapi.utils import get_openapi as _get_openapi_local
    except Exception:  # pragma: no cover - defensive import guard
        return

    def _custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = _get_openapi_local(
            title=app.title,
            version=app.version,
            routes=app.routes,
            description=getattr(app, "description", None),
        )
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        if "ErrorResponse" not in schemas:
            schemas["ErrorResponse"] = {
                "type": "object",
                "properties": {
                    "error_code": {
                        "type": "string",
                        "description": "kebab-case error code",
                    },
                    "message": {"type": "string"},
                    "details": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": ["string", "null"]},
                                "message": {"type": "string"},
                                "code": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "correlation_id": {"type": ["string", "null"]},
                    "docs_url": {"type": ["string", "null"]},
                    "debug": {
                        "type": ["object", "null"],
                        "properties": {
                            "stack_summary": {"type": ["string", "null"]},
                            "hint": {"type": ["string", "null"]},
                        },
                    },
                },
                "required": ["error_code", "message"],
            }
        headers = components.setdefault("headers", {})
        headers["X-Correlation-ID"] = {
            "description": "Correlation identifier echoed back in error responses and logs",
            "schema": {"type": "string"},
        }
        app.openapi_schema = schema
        return app.openapi_schema

    setattr(  # noqa: B010 deliberate instance mutation for FastAPI hook
        app,
        "openapi",
        cast(Callable[[], dict[str, Any]], _custom_openapi),
    )


def create_app() -> FastAPI:
    install_import_guard()
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

    # Correlation middleware (T008)
    app.middleware("http")(correlation_middleware)

    # Request completion log (keep simple and independent of correlation implementation)
    @app.middleware("http")
    async def _request_log_middleware(
        request: _Request,
        call_next: Callable[[_Request], Awaitable[_Response]],
    ) -> _Response:
        start = _time.time()
        response: _Response = await call_next(request)
        duration_ms = int((_time.time() - start) * 1000)
        corr_id = getattr(
            getattr(request, "state", object()), "correlation_id", None
        ) or request.headers.get("x-correlation-id")
        try:
            base_logger = logging.getLogger("api.request")
            logger = logging.LoggerAdapter(base_logger, {"correlation_id": corr_id})
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": duration_ms,
                },
            )
            try:
                import structlog

                structlog.get_logger("api.request").bind(
                    correlation_id=corr_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=getattr(response, "status_code", None),
                    duration_ms=duration_ms,
                ).info("request_completed")
            except Exception:
                pass
        except Exception:
            pass
        return response

    # T102: Pre-register canonical daily datasets (NVDA, AAPL) eliminating fallback paths
    try:  # pragma: no cover - defensive
        from domain.data.registry import DatasetEntry, register_dataset

        for sym in ("NVDA", "AAPL"):
            register_dataset(
                DatasetEntry(
                    symbol=sym,
                    timeframe="1d",
                    provider="local_csv",
                    path=f"data/{sym}_5y.csv",  # expected future ingestion artifact
                    calendar_id="NASDAQ",
                )
            )
    except Exception:
        # Registration best-effort; tests relying on deterministic dataset hash may still inject
        pass

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
    # Newly added backtest run creation endpoint (feature 006)
    try:  # pragma: no cover - defensive
        from api.routes.backtest_run import router as backtest_run_router

        app.include_router(backtest_run_router)
    except Exception:  # pragma: no cover
        pass
    # Feature 006 T067 versioned market routes
    try:  # pragma: no cover - defensive
        from api.routes.v1_market import router as v1_market_router

        app.include_router(v1_market_router)
    except Exception:
        pass
    # Feature 006 T068 versioned backtests submission endpoint
    try:  # pragma: no cover - defensive
        from api.routes.v1_backtests import router as v1_backtests_router

        app.include_router(v1_backtests_router)
    except Exception:
        pass
    # Canonicalization helper endpoint (exposes canonical JSON + hash for arbitrary payloads)
    try:  # pragma: no cover - defensive (should normally succeed)
        from api.routes.canonical import router as canonical_router  # simple import

        app.include_router(canonical_router)
    except Exception:  # pragma: no cover - avoid failing app startup if optional
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
    app.state.registry = (
        registry  # app.state is dynamic, acceptable for runtime; ignore removed
    )

    # Attach new runs router (T050-T051 implementation)
    try:  # pragma: no cover - defensive
        from api.routes.runs import router as runs_router

        app.include_router(runs_router)
    except Exception:  # pragma: no cover
        pass
    # Existing SSE routes (run_events) already mounted earlier (legacy). Future refactor will consolidate.

    # (Existing artifact endpoints removed here; future T055+ will reintroduce refined versions.)

    # Final assurance: include /metrics if still missing (defensive ordering)
    try:  # pragma: no cover - defensive
        if not any(getattr(r, "path", None) == "/metrics" for r in app.routes):
            try:
                from api.metrics import router as _metrics_router

                app.include_router(_metrics_router)
            except Exception:
                try:
                    import prometheus_client

                    make_app = getattr(prometheus_client, "make_asgi_app", None)
                    if callable(make_app):
                        app.mount("/metrics", make_app())
                except Exception:
                    pass
    except Exception:
        pass

    _install_custom_openapi(app)

    return app


app = create_app()
