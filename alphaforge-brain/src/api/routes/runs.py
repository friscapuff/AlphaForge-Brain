from __future__ import annotations

# ruff: noqa: B008
# Rationale: FastAPI dependency injection idiom uses Depends(callable) as a default
# parameter. We intentionally preserve this canonical style for clarity and
# tooling compatibility; rule B008 would otherwise flag each endpoint.
from datetime import datetime, timezone
from typing import Any, Mapping, Union

from domain.errors import NotFoundError
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from lib.artifacts import artifact_index
from pydantic import BaseModel

from infra.artifacts_root import resolve_artifact_root

router = APIRouter(prefix="", tags=["runs"])  # Root mounted


class RunCreateResponse(BaseModel):
    run_id: str
    run_hash: str
    status: str
    created_at: datetime
    created: bool


class RunListItem(BaseModel):
    run_hash: str
    created_at: datetime | None = None
    status: str = "SUCCEEDED"


class RunListResponse(BaseModel):
    items: list[RunListItem]


def _registry(request: Request) -> InMemoryRunRegistry:
    reg = getattr(request.app.state, "registry", None)
    if not isinstance(reg, InMemoryRunRegistry):  # precise runtime check
        raise HTTPException(status_code=500, detail="registry not initialized")
    return reg


@router.post("/runs", response_model=RunCreateResponse)
async def post_run(
    cfg: RunConfig, registry: InMemoryRunRegistry = Depends(_registry)
) -> RunCreateResponse:  # T050
    run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
    created_at = datetime.now(timezone.utc)
    # For now status is SUCCEEDED because orchestration is synchronous & terminal
    return RunCreateResponse(
        run_id=run_hash,
        run_hash=run_hash,
        status="SUCCEEDED",
        created_at=created_at,
        created=created,
    )


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    registry: InMemoryRunRegistry = Depends(_registry),
) -> RunListResponse:
    # Collect with created_at if present then sort newest first
    entries: list[tuple[str, float]] = []
    for h, rec in registry.store.items():
        ts = float(rec.get("created_at", 0.0))
        entries.append((h, ts))
    entries.sort(key=lambda x: x[1], reverse=True)
    items = [
        RunListItem(
            run_hash=h,
            created_at=datetime.fromtimestamp(ts, tz=timezone.utc),
            status="SUCCEEDED",
        )
        for h, ts in entries
    ]
    return RunListResponse(items=items)


class ArtifactDescriptor(BaseModel):
    name: str
    sha256: str
    size: int


class RunDetailResponse(BaseModel):
    run_id: str
    run_hash: str
    status: str
    phase: str
    artifacts: list[ArtifactDescriptor]
    summary: dict[str, Any] | None = None
    data_hash: str | None = None
    calendar_id: str | None = None
    validation_summary: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None  # alias copy
    manifest: dict[str, Any] | None = None


@router.get("/runs/{run_hash}", response_model=RunDetailResponse)
async def get_run_detail(
    run_hash: str,
    registry: InMemoryRunRegistry = Depends(_registry),
    include_anomalies: bool = Query(
        False, description="Include dataset anomaly counters when available"
    ),
) -> RunDetailResponse:  # T051
    rec = registry.get(run_hash)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    # Load artifacts manifest if present
    import json

    from infra.artifacts_root import resolve_artifact_root

    base = resolve_artifact_root(None)
    manifest_path = base / run_hash / "manifest.json"
    artifacts: list[ArtifactDescriptor] = []
    manifest: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text("utf-8"))
            manifest = m
            for f in m.get("files", []):
                if isinstance(f, dict) and {"name", "sha256", "size"}.issubset(
                    f.keys()
                ):
                    artifacts.append(
                        ArtifactDescriptor(
                            name=f["name"], sha256=f["sha256"], size=int(f["size"])
                        )
                    )
        except Exception:  # pragma: no cover - manifest parse resilience
            pass
    summary = rec.get("summary")
    if include_anomalies:
        # Always surface anomaly_counters key (empty dict fallback) when flag set
        counters: dict[str, int] | None = None
        try:  # pragma: no cover - defensive import
            from domain.data.ingest_nvda import get_dataset_metadata

            meta = get_dataset_metadata()
            mc = getattr(meta, "anomaly_counters", None)
            if isinstance(mc, dict):  # copy to avoid mutation sharing
                counters = dict(mc)
        except Exception:  # pragma: no cover - ignore if ingestion unavailable
            counters = None
        # Normalize summary to dict if possible so we can attach key
        if not isinstance(summary, dict):
            summary = {} if counters is not None else summary
        if isinstance(summary, dict):
            # Insert even if counters None (treat as empty mapping) to satisfy contract
            summary = {**summary, "anomaly_counters": counters or {}}
    # Phase is always finalize in synchronous baseline
    # Extract dataset metadata (if merged into hash augmentation earlier) from manifest if present
    data_hash = None
    calendar_id = None
    if manifest:
        data_hash = manifest.get("data_hash")
        calendar_id = manifest.get("calendar_id")
    validation_summary = (
        rec.get("validation_summary")
        if isinstance(rec.get("validation_summary"), dict)
        else None
    )
    return RunDetailResponse(
        run_id=run_hash,
        run_hash=run_hash,
        status="SUCCEEDED",
        phase="finalize",
        artifacts=artifacts,
        summary=summary if isinstance(summary, dict) else None,
        data_hash=data_hash,
        calendar_id=calendar_id,
        validation_summary=validation_summary,
        validation=validation_summary,
        manifest=manifest,
    )


@router.post("/runs/{run_hash}/cancel")
async def cancel_run(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, str]:
    rec = registry.get(run_hash)
    if rec is None:
        # Map to DomainError pathway via NotFoundError so test_errors expectation passes
        raise NotFoundError(f"run {run_hash} not found")
    # Synchronous orchestrator already completed; cancellation is a no-op placeholder
    try:  # append cancellation event for SSE tests
        buf = get_global_buffer(run_hash)
        buf.append("cancelled", {"run_hash": run_hash, "status": "CANCELLED"})
    except Exception:  # pragma: no cover - resilience
        pass
    return {"status": "CANCELLED", "run_hash": run_hash}


@router.get("/runs/{run_hash}/artifacts")
async def list_artifacts(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    base = resolve_artifact_root(None)
    files_list = artifact_index(run_hash, base_dir=base)
    # Ensure files_list is serializable list (artifact_index contract assumed)
    return {"run_hash": run_hash, "files": list(files_list)}


JsonLike = Mapping[str, Any] | list[Any] | str | int | float | bool | None
ArtifactResponse = Union[JsonLike, dict[str, Any], bytes]


@router.get("/runs/{run_hash}/artifacts/{name}")
async def get_artifact(
    run_hash: str, name: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> ArtifactResponse:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    base = resolve_artifact_root(None)
    path = base / run_hash / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    # naive content-type inference
    if name.endswith(".json"):
        import json

        try:
            loaded = json.loads(path.read_text("utf-8"))
            if (
                isinstance(loaded, (dict, list, str, int, float, bool))
                or loaded is None
            ):
                return loaded
            # Fallback: wrap unexpected type into diagnostic dict
            return {"value": str(loaded), "type": type(loaded).__name__}
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="artifact unreadable") from e
    if name.endswith(".parquet"):
        import pandas as pd

        try:
            df = pd.read_parquet(path)
            return {"columns": list(df.columns), "row_count": int(len(df))}
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="artifact unreadable") from e
    # fallback raw bytes
    return path.read_bytes()
