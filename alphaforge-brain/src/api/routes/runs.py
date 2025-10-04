from __future__ import annotations

from collections.abc import Mapping

# ruff: noqa: B008
# Rationale: FastAPI dependency injection idiom uses Depends(callable) as a default
# parameter. We intentionally preserve this canonical style for clarity and
# tooling compatibility; rule B008 would otherwise flag each endpoint.
from datetime import datetime, timezone
from typing import Any, Union

from domain.errors import NotFoundError
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.run.event_buffer import get_global_buffer
from domain.run.retention_policy import (
    RetentionConfig,
    apply_retention_plan,
    plan_retention,
)
from domain.schemas.run_config import RunConfig
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from lib.artifacts import artifact_index
from pydantic import BaseModel

from infra.artifacts_root import evicted_dir, run_artifact_dir
from infra.audit import write_event

router = APIRouter(prefix="", tags=["runs"])  # Root mounted


# In-memory retention configuration (mutable via /settings/retention)
class _RetentionSettings(BaseModel):
    keep_last: int = 50
    top_k_per_strategy: int = 5
    max_full_bytes: int | None = None


_DEFAULT_RETENTION = _RetentionSettings()


class RunCreateResponse(BaseModel):
    run_id: str
    run_hash: str
    status: str
    created_at: datetime
    created: bool
    api_version: str | None = None
    schema_version: str | None = None
    content_hash: str | None = None


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
    # Contract augmentation (api_version/schema_version/content_hash)
    from infra.utils.hash import hash_canonical

    base_payload = {
        "run_id": run_hash,
        "run_hash": run_hash,
        "status": "SUCCEEDED",
        "created_at": created_at,
        "created": created,
        "api_version": "0.1",
        "schema_version": "0.1",
    }
    base_payload["content_hash"] = hash_canonical(
        {k: str(v) for k, v in base_payload.items() if k != "content_hash"}
    )
    return RunCreateResponse(**base_payload)


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
    api_version: str | None = None
    schema_version: str | None = None
    content_hash: str | None = None
    pinned: bool | None = None
    retention_state: str | None = None
    metrics_hash: str | None = None
    equity_curve_hash: str | None = None


class RunHashesResponse(BaseModel):
    run_hash: str
    manifest_hash: str | None = None
    metrics_hash: str | None = None
    equity_curve_hash: str | None = None
    provenance_hash: str | None = None  # combined attestation hash
    api_version: str | None = None


@router.get("/runs/{run_hash}/hashes", response_model=RunHashesResponse)
async def get_run_hashes(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> RunHashesResponse:
    """Lightweight hash attestation endpoint.

    Returns only hash fields so external systems can verify provenance without fetching
    full run detail or manifest. `provenance_hash` is a canonical hash over the triple
    (manifest_hash, metrics_hash, equity_curve_hash) ignoring Nones.
    """
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    import json

    from infra.artifacts_root import resolve_artifact_root as _rar_local2
    from infra.utils.hash import hash_canonical

    base_path = _rar_local2(None)
    manifest_hash = None
    metrics_hash_val = (
        rec.get("metrics_hash") if isinstance(rec.get("metrics_hash"), str) else None
    )
    equity_curve_hash_val = (
        rec.get("equity_curve_hash")
        if isinstance(rec.get("equity_curve_hash"), str)
        else None
    )
    manifest_path = base_path / run_hash / "manifest.json"
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text("utf-8"))
            if isinstance(m, dict):
                mh = m.get("manifest_hash")
                if isinstance(mh, str):
                    manifest_hash = mh
                # Prefer manifest values for semantic hashes if present
                if isinstance(m.get("metrics_hash"), str):
                    metrics_hash_val = m["metrics_hash"]
                if isinstance(m.get("equity_curve_hash"), str):
                    equity_curve_hash_val = m["equity_curve_hash"]
        except Exception:  # pragma: no cover
            pass
    # Build provenance hash from available pieces (order-independent canonical form)
    components = {}
    if manifest_hash:
        components["manifest_hash"] = manifest_hash
    if metrics_hash_val:
        components["metrics_hash"] = metrics_hash_val
    if equity_curve_hash_val:
        components["equity_curve_hash"] = equity_curve_hash_val
    provenance_hash = hash_canonical(components) if components else None
    return RunHashesResponse(
        run_hash=run_hash,
        manifest_hash=manifest_hash,
        metrics_hash=metrics_hash_val,
        equity_curve_hash=equity_curve_hash_val,
        provenance_hash=provenance_hash,
        api_version="0.1",
    )


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

    from infra.artifacts_root import resolve_artifact_root as _rar_local

    base_path = _rar_local(None)
    manifest_path = base_path / run_hash / "manifest.json"
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
    # Prefer manifest-sourced semantic hashes, fallback to record if absent
    metrics_hash_val = None
    equity_curve_hash_val = None
    if manifest:
        mh = manifest.get("metrics_hash")
        ech = manifest.get("equity_curve_hash")
        if isinstance(mh, str):
            metrics_hash_val = mh
        if isinstance(ech, str):
            equity_curve_hash_val = ech
    if metrics_hash_val is None:
        mh_rec = rec.get("metrics_hash")
        if isinstance(mh_rec, str):
            metrics_hash_val = mh_rec
    if equity_curve_hash_val is None:
        ech_rec = rec.get("equity_curve_hash")
        if isinstance(ech_rec, str):
            equity_curve_hash_val = ech_rec
    validation_summary = (
        rec.get("validation_summary")
        if isinstance(rec.get("validation_summary"), dict)
        else None
    )
    from infra.utils.hash import hash_canonical

    pinned = bool(rec.get("pinned", False))
    retention_state = rec.get("retention_state", "full")
    payload = {
        "run_id": run_hash,
        "run_hash": run_hash,
        "status": "SUCCEEDED",
        "phase": "finalize",
        "artifacts": artifacts,
        "summary": summary if isinstance(summary, dict) else None,
        "data_hash": data_hash,
        "calendar_id": calendar_id,
        "validation_summary": validation_summary,
        "validation": validation_summary,
        "manifest": manifest,
        "api_version": "0.1",
        "schema_version": "0.1",
        "pinned": pinned,
        "retention_state": retention_state,
        "metrics_hash": metrics_hash_val,
        "equity_curve_hash": equity_curve_hash_val,
    }
    payload["content_hash"] = hash_canonical(
        {
            k: (str(v) if not isinstance(v, (dict, list)) else k)
            for k, v in payload.items()
            if k
            not in {
                "content_hash",
                "manifest",
                "artifacts",
                "summary",
                "validation_summary",
                "validation",
            }
        }
    )
    return RunDetailResponse(**payload)


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
    # resolve_artifact_root intentionally not assigned; we only call inside loop for clarity
    # Provide base_dir explicitly via resolve_artifact_root for reproducibility
    from infra.artifacts_root import resolve_artifact_root as _rar

    files_list = artifact_index(run_hash, base_dir=_rar(None))
    # Ensure files_list is serializable list (artifact_index contract assumed)
    return {"run_hash": run_hash, "files": list(files_list), "api_version": "0.1"}


JsonLike = Mapping[str, Any] | list[Any] | str | int | float | bool | None
ArtifactResponse = Union[JsonLike, dict[str, Any], bytes]


@router.get("/runs/{run_hash}/artifacts/{name}")
async def get_artifact(
    run_hash: str, name: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> ArtifactResponse:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    # Removed unused base assignment (previously triggered F841)
    from infra.artifacts_root import resolve_artifact_root as _rar2

    path = _rar2(None) / run_hash / name
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
        try:
            from lib.artifacts import read_parquet_or_csv as _rpoc

            df = _rpoc(path)
            return {"columns": list(df.columns), "row_count": len(df)}
        except Exception as e2:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="artifact unreadable") from e2
    # fallback raw bytes
    return path.read_bytes()


@router.post("/runs/{run_hash}/pin")
async def pin_run(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    rec["pinned"] = True
    rec["retention_state"] = "pinned"
    # Recompute retention to refresh top_k/full classifications
    plan = plan_retention(registry, RetentionConfig())
    apply_retention_plan(registry, plan)
    write_event("PIN", run_hash, retention_state="pinned")
    return {
        "run_hash": run_hash,
        "pinned": True,
        "retention_state": "pinned",
        "api_version": "0.1",
    }


@router.post("/runs/{run_hash}/unpin")
async def unpin_run(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    rec["pinned"] = False
    rec.setdefault("retention_state", "full")
    if rec["retention_state"] == "pinned":
        rec["retention_state"] = "full"  # revert to full baseline
    # Recompute retention classifications after unpin
    plan = plan_retention(registry, RetentionConfig())
    apply_retention_plan(registry, plan)
    write_event("UNPIN", run_hash, retention_state=rec["retention_state"])
    return {
        "run_hash": run_hash,
        "pinned": False,
        "retention_state": rec["retention_state"],
        "api_version": "0.1",
    }


@router.post("/runs/{run_hash}/rehydrate")
async def rehydrate_run(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    # Backward compatibility: if not demoted, treat as noop success
    if rec.get("retention_state") != "manifest-only":
        write_event("REHYDRATE", run_hash, restored=False, noop=True)
        return {
            "run_hash": run_hash,
            "rehydrated": True,
            "api_version": "0.1",
            "restored": False,
            "noop": True,
        }
    rdir = run_artifact_dir(run_hash)
    ed = evicted_dir(run_hash)
    restored_any = False
    if ed.exists():
        for p in list(ed.iterdir()):
            target = rdir / p.name
            try:
                p.replace(target)
                restored_any = True
            except Exception:
                pass
    rec["retention_state"] = "full"
    write_event("REHYDRATE", run_hash, restored=restored_any)
    return {
        "run_hash": run_hash,
        "rehydrated": True,
        "api_version": "0.1",
        "restored": restored_any,
    }


@router.post("/runs/{run_hash}/restore")
async def restore_cold_storage(
    run_hash: str, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    """Restore run artifacts from cold storage (if available).

    If run is already full this is a no-op. If manifest-only and cold manifest exists, attempt
    remote download + extraction. Falls back to standard rehydrate if cold storage disabled.
    """
    rec = registry.get(run_hash)
    if rec is None:
        raise HTTPException(status_code=404, detail="run not found")
    if rec.get("retention_state") != "manifest-only":
        write_event("RESTORE", run_hash, cold=False, noop=True)
        return {
            "run_hash": run_hash,
            "restored": False,
            "noop": True,
            "api_version": "0.1",
        }
    # Try cold storage restore first
    cold_success = False
    try:  # pragma: no cover - network path optional
        from infra.cold_storage import cold_storage_enabled
        from infra.cold_storage import restore as cold_restore

        if cold_storage_enabled():
            cold_success = cold_restore(run_hash)
    except Exception:
        cold_success = False
    # Fallback: local rehydrate (evicted dir move) if cold restore failed
    if not cold_success:
        rdir = run_artifact_dir(run_hash)
        ed = evicted_dir(run_hash)
        for p in list(ed.iterdir()):
            target = rdir / p.name
            try:
                p.replace(target)
                cold_success = True
            except Exception:
                pass
    if cold_success:
        rec["retention_state"] = "full"
    write_event(
        "RESTORE",
        run_hash,
        cold=True if cold_success else False,
        fallback=not cold_success,
    )
    return {"run_hash": run_hash, "restored": cold_success, "api_version": "0.1"}


@router.post("/runs/retention/apply")
async def apply_retention(
    registry: InMemoryRunRegistry = Depends(_registry),
) -> dict[str, Any]:
    # Use dynamic retention settings if present on app.state
    # Access current request via dependency injection would be cleaner; quick access through global import not available
    # Fallback to default settings stored at module level (mutated by /settings/retention)
    cfg = RetentionConfig(
        keep_last=_DEFAULT_RETENTION.keep_last,
        top_k_per_strategy=_DEFAULT_RETENTION.top_k_per_strategy,
    )
    plan = plan_retention(registry, cfg)
    apply_retention_plan(registry, plan)
    # Physical demotion: move non-manifest artifacts of demoted runs to .evicted
    # Removed unused base assignment (F841) - using resolve_artifact_root inline where needed
    for h in plan["demote"]:
        rec = registry.get(h)
        if rec is None:
            continue
        # Move artifacts (idempotent: if already moved, loop finds none)
        rdir = run_artifact_dir(h)
        ed = evicted_dir(h)
        for p in list(rdir.iterdir()):
            if p.name in {"manifest.json", ".evicted"}:
                continue
            try:
                p.replace(ed / p.name)
            except Exception:
                pass
        # Cold storage offload (best-effort): offload files now inside evicted dir
        try:  # pragma: no cover - network / optional path
            from infra.cold_storage import cold_storage_enabled, offload

            if cold_storage_enabled():
                files_to_offload = [
                    p
                    for p in ed.iterdir()
                    if p.is_file() and p.name not in {"manifest.json", ".evicted"}
                ]
                offload(h, files_to_offload)
        except Exception:
            pass
        rec["retention_state"] = "manifest-only"
    # Audit demotions
    for h in plan["demote"]:
        # Only log demote once per application; idempotence not enforced yet
        write_event("DEMOTE", h)
    write_event(
        "RETENTION_APPLY",
        None,
        kept=len(plan["keep_full"]),
        demoted=len(plan["demote"]),
    )
    return {
        "api_version": "0.1",
        "kept": sorted(plan["keep_full"]),
        "demoted": sorted(plan["demote"]),
        "pinned": sorted(plan["pinned"]),
        "top_k": sorted(plan["top_k"]),
    }


@router.get("/settings/retention")
async def get_retention_settings() -> dict[str, Any]:
    return {
        "keep_last": _DEFAULT_RETENTION.keep_last,
        "top_k_per_strategy": _DEFAULT_RETENTION.top_k_per_strategy,
        "max_full_bytes": _DEFAULT_RETENTION.max_full_bytes,
        "api_version": "0.1",
    }


class RetentionUpdateRequest(BaseModel):
    keep_last: int | None = None
    top_k_per_strategy: int | None = None
    max_full_bytes: int | None = None


@router.post("/settings/retention")
async def update_retention_settings(
    body: RetentionUpdateRequest, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    if body.keep_last is not None:
        if not (1 <= body.keep_last <= 500):
            raise HTTPException(status_code=400, detail="keep_last out of bounds")
        _DEFAULT_RETENTION.keep_last = body.keep_last
    if body.top_k_per_strategy is not None:
        if not (0 <= body.top_k_per_strategy <= 50):
            raise HTTPException(
                status_code=400, detail="top_k_per_strategy out of bounds"
            )
        _DEFAULT_RETENTION.top_k_per_strategy = body.top_k_per_strategy
    if body.max_full_bytes is not None:
        if body.max_full_bytes < 0:
            raise HTTPException(status_code=400, detail="max_full_bytes out of bounds")
        _DEFAULT_RETENTION.max_full_bytes = body.max_full_bytes
    write_event(
        "RETENTION_CONFIG_UPDATE",
        None,
        keep_last=_DEFAULT_RETENTION.keep_last,
        top_k=_DEFAULT_RETENTION.top_k_per_strategy,
        max_full_bytes=_DEFAULT_RETENTION.max_full_bytes,
    )
    # Immediately apply new plan
    cfg = RetentionConfig(
        keep_last=_DEFAULT_RETENTION.keep_last,
        top_k_per_strategy=_DEFAULT_RETENTION.top_k_per_strategy,
        max_full_bytes=_DEFAULT_RETENTION.max_full_bytes,
    )
    plan = plan_retention(registry, cfg)
    apply_retention_plan(registry, plan)
    return {
        "keep_last": _DEFAULT_RETENTION.keep_last,
        "top_k_per_strategy": _DEFAULT_RETENTION.top_k_per_strategy,
        "max_full_bytes": _DEFAULT_RETENTION.max_full_bytes,
        "api_version": "0.1",
    }


@router.get("/retention/metrics")
async def get_retention_metrics(
    registry: InMemoryRunRegistry = Depends(_registry),
) -> dict[str, Any]:
    counts: dict[str, int] = {"full": 0, "pinned": 0, "top_k": 0, "manifest-only": 0}
    bytes_map: dict[str, int] = {k: 0 for k in counts}
    from infra.artifacts_root import resolve_artifact_root as _rar_metrics

    base = _rar_metrics(None)
    for h, rec in registry.store.items():
        state = rec.get("retention_state") or "full"
        if state not in counts:
            counts[state] = 0
            bytes_map.setdefault(state, 0)
        counts[state] += 1
        rdir = base / h
        if rdir.exists():
            sz = 0
            for p in rdir.iterdir():
                if not p.is_file():
                    continue
                if p.name in {"manifest.json", ".evicted"}:
                    continue
                try:
                    sz += p.stat().st_size
                except Exception:
                    pass
            bytes_map[state] += sz
    total = sum(counts.values())
    counts["total"] = total
    bytes_map["total_bytes"] = sum(
        bytes_map[k]
        for k in bytes_map
        if k in {"full", "pinned", "top_k", "manifest-only"}
    )
    max_full = _DEFAULT_RETENTION.max_full_bytes
    budget_remaining: int | None = None
    if max_full is not None:
        full_bytes = bytes_map.get("full", 0)
        # budget_remaining is clipped at zero to avoid negative exposure
        budget_remaining = max(0, max_full - full_bytes)
    # Audit rotation metrics (best-effort)
    audit_metrics: dict[str, Any] = {}
    try:  # pragma: no cover - defensive
        from infra.audit import rotation_metrics

        r = rotation_metrics()
        if r["rotation_count"]:
            ratio = None
            if r["rotated_original_bytes"] > 0:
                ratio = r["rotated_compressed_bytes"] / r["rotated_original_bytes"]
            audit_metrics = {**r, "compression_ratio": ratio}
    except Exception:
        pass
    return {
        "api_version": "0.1",
        "counts": counts,
        "bytes": bytes_map,
        "max_full_bytes": max_full,
        "budget_remaining": budget_remaining,
        "audit_rotation": audit_metrics,
    }


@router.get("/retention/plan")
async def get_retention_plan(
    registry: InMemoryRunRegistry = Depends(_registry),
) -> dict[str, Any]:
    """Dry-run retention plan. Computes classification and demotion set without applying changes.

    Returns same keys as apply plan plus meta counts. Does not perform physical demotion.
    """
    cfg = RetentionConfig(
        keep_last=_DEFAULT_RETENTION.keep_last,
        top_k_per_strategy=_DEFAULT_RETENTION.top_k_per_strategy,
        max_full_bytes=_DEFAULT_RETENTION.max_full_bytes,
    )
    plan = plan_retention(registry, cfg)
    return {
        "api_version": "0.1",
        "keep_full": sorted(plan["keep_full"]),
        "demote": sorted(plan["demote"]),
        "pinned": sorted(plan["pinned"]),
        "top_k": sorted(plan["top_k"]),
        "summary": {
            "kept": len(plan["keep_full"]),
            "demoted": len(plan["demote"]),
            "pinned": len(plan["pinned"]),
            "top_k": len(plan["top_k"]),
        },
        "max_full_bytes": _DEFAULT_RETENTION.max_full_bytes,
    }


class RetentionPlanDiffRequest(BaseModel):
    keep_last: int | None = None
    top_k_per_strategy: int | None = None
    max_full_bytes: int | None = None


@router.post("/retention/plan/diff")
async def retention_plan_diff(
    body: RetentionPlanDiffRequest, registry: InMemoryRunRegistry = Depends(_registry)
) -> dict[str, Any]:
    """Compute diff between current retention plan and a hypothetical configuration.

    Returns sets of runs that would change classification (new_demotions, new_full, lost_full).
    new_demotions: runs that are currently kept full but would be demoted.
    new_full: runs currently demoted that would become full/top_k/pinned.
    unchanged: counts summary for convenience.
    """
    current_cfg = RetentionConfig(
        keep_last=_DEFAULT_RETENTION.keep_last,
        top_k_per_strategy=_DEFAULT_RETENTION.top_k_per_strategy,
        max_full_bytes=_DEFAULT_RETENTION.max_full_bytes,
    )
    current_plan = plan_retention(registry, current_cfg)
    alt_cfg = RetentionConfig(
        keep_last=(
            body.keep_last
            if body.keep_last is not None
            else _DEFAULT_RETENTION.keep_last
        ),
        top_k_per_strategy=(
            body.top_k_per_strategy
            if body.top_k_per_strategy is not None
            else _DEFAULT_RETENTION.top_k_per_strategy
        ),
        max_full_bytes=(
            body.max_full_bytes
            if body.max_full_bytes is not None
            else _DEFAULT_RETENTION.max_full_bytes
        ),
    )
    alt_plan = plan_retention(registry, alt_cfg)
    current_full = current_plan["keep_full"]
    alt_full = alt_plan["keep_full"]
    new_demotions = sorted(current_full - alt_full)
    new_full = sorted(alt_full - current_full)
    lost_full = new_demotions  # alias for explicitness
    return {
        "api_version": "0.1",
        "current": {
            "kept": len(current_full),
            "demoted": len(current_plan["demote"]),
        },
        "alternative": {
            "kept": len(alt_full),
            "demoted": len(alt_plan["demote"]),
            "config": {
                "keep_last": alt_cfg.keep_last,
                "top_k_per_strategy": alt_cfg.top_k_per_strategy,
                "max_full_bytes": alt_cfg.max_full_bytes,
            },
        },
        "diff": {
            "new_demotions": new_demotions,
            "new_full": new_full,
            "lost_full": lost_full,
        },
    }
