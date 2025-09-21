from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from api.error_handlers import install_error_handlers
from domain.errors import NotFoundError
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import RunConfig
from infra.config import get_settings
from infra.logging import init_logging
try:  # pragma: no cover - lightweight runtime fetch
    from importlib.metadata import version as _pkg_version
except Exception:  # pragma: no cover - very old Python
    _pkg_version = None  # type: ignore


def create_app() -> FastAPI:
    settings = get_settings()
    init_logging()

    # Resolve package version dynamically so FastAPI surface stays in sync with pyproject version.
    resolved_version = None
    if _pkg_version:
        try:
            resolved_version = _pkg_version("project-a-backend")
        except Exception:  # pragma: no cover - package not installed (editable dev mode)
            resolved_version = None
    if not resolved_version:
        # Fallback: parse pyproject.toml directly (dev editable mode without installed dist)
        try:
            import tomllib  # Python 3.11+
            pyproj = Path("pyproject.toml")
            if pyproj.exists():
                data = tomllib.loads(pyproj.read_text("utf-8"))
                resolved_version = data.get("tool", {}).get("poetry", {}).get("version")
        except Exception:  # pragma: no cover - best effort
            resolved_version = None
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

    @app.post("/runs", tags=["runs"])
    async def create_run(cfg: RunConfig) -> dict[str, Any]:
        run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
        return {"run_hash": run_hash, "created": created, "p_values": record.get("p_values")}

    @app.get("/runs/{run_hash}", tags=["runs"])
    async def get_run(run_hash: str, include_anomalies: bool = False) -> dict[str, Any]:
        rec = registry.get(run_hash)
        if not rec:
            raise HTTPException(status_code=404, detail="run not found")
        # Attach manifest if present
        manifest_path = Path("artifacts") / run_hash / "manifest.json"
        manifest = None
        data_hash: str | None = None
        calendar_id: str | None = None
        if manifest_path.exists():  # pragma: no cover simple path
            try:
                import json
                manifest = json.loads(manifest_path.read_text("utf-8"))
                # Extract dataset metadata if present (additive exposure)
                data_hash = manifest.get("data_hash")
                calendar_id = manifest.get("calendar_id")
            except Exception:
                manifest = None
        summary_obj = rec.get("summary") or {}
        if include_anomalies:
            try:  # pragma: no cover - integration guard
                from domain.data.ingest_nvda import get_dataset_metadata
                summary_obj = dict(summary_obj)
                summary_obj.setdefault("anomaly_counters", dict(get_dataset_metadata().anomaly_counters))
            except Exception:
                summary_obj = dict(summary_obj)
                summary_obj.setdefault("anomaly_counters", {})
        return {
            "run_hash": run_hash,
            "summary": summary_obj,
            # Explicit surface of validation summary (alias kept for backward compat if clients used old key)
            "validation_summary": rec.get("validation_summary"),
            "validation": rec.get("validation_summary"),  # legacy alias
            "data_hash": data_hash,
            "calendar_id": calendar_id,
            "manifest": manifest,
        }

    @app.get("/runs", tags=["runs"])
    async def list_runs(limit: int = 20) -> dict[str, Any]:
        items = []
        for h, rec in list(registry.store.items())[-limit:]:  # naive recent ordering
            items.append({"run_hash": h, "trade_count": rec.get("summary", {}).get("trade_count")})
        return {"items": list(reversed(items))}

    @app.post("/runs/{run_hash}/cancel", tags=["runs"])
    async def cancel_run(run_hash: str) -> dict[str, Any]:
        """Cancel a run (best-effort).

        Current implementation runs synchronously so cancellation is effectively a no-op
        if the run already completed. We still provide the endpoint and maintain a
        status field for forward compatibility once long-running async orchestration
        or SSE streaming is introduced (T051+).
        """
        rec = registry.get(run_hash)
        if not rec:
            raise NotFoundError(f"run {run_hash} not found")
        # If already terminal just echo status
        status = rec.get("status") or "COMPLETE"  # baseline: runs finish immediately today
        # Semantics: even if already COMPLETE we allow a client cancel call to transition to CANCELLED
        # so that downstream code and tests observing a user-driven cancellation get a uniform state
        # (future async orchestration would gate this on in-flight progress). Only ERROR and existing
        # CANCELLED remain immutable terminal states.
        if status in {"CANCELLED", "ERROR"}:
            return {"run_hash": run_hash, "status": status}
        # COMPLETE -> CANCELLED (idempotent if already just switched earlier)
        rec["status"] = "CANCELLED"
        rec["cancelled"] = True
        # Append cancellation event to SSE buffer if present
        bufs = getattr(app.state, "event_buffers", None)
        if isinstance(bufs, dict) and run_hash in bufs:
            try:
                bufs[run_hash].append("cancelled", {"run_hash": run_hash, "status": "CANCELLED"})
            except Exception:  # pragma: no cover - defensive
                pass
        return {"run_hash": run_hash, "status": rec["status"]}

    @app.get("/runs/{run_hash}/artifacts", tags=["artifacts"])
    async def list_artifacts(run_hash: str) -> dict[str, Any]:
        # Require run existence
        rec = registry.get(run_hash)
        if not rec:
            raise HTTPException(status_code=404, detail="run not found")
        manifest_path = Path("artifacts") / run_hash / "manifest.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="manifest missing")
        import json
        try:
            manifest = json.loads(manifest_path.read_text("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=500, detail="manifest unreadable") from e
        return {"run_hash": run_hash, "files": manifest.get("files", [])}

    @app.get("/runs/{run_hash}/artifacts/{name}", tags=["artifacts"])
    async def get_artifact(run_hash: str, name: str) -> FileResponse:
        # Validate manifest membership to avoid path traversal
        manifest_path = Path("artifacts") / run_hash / "manifest.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="manifest missing")
        import json
        try:
            manifest = json.loads(manifest_path.read_text("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=500, detail="manifest unreadable") from e
        allowed = {f["name"] for f in manifest.get("files", []) if isinstance(f, dict) and "name" in f}
        if name not in allowed:
            raise HTTPException(status_code=404, detail="artifact not found")
        # Build safe path
        file_path = Path("artifacts") / run_hash / name
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="artifact file missing")
        media_type = "application/json" if name.endswith(".json") else "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=name)

    return app


app = create_app()
