from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig
from infra.utils.hash import hash_canonical

from .orchestrator import orchestrate


@dataclass
class InMemoryRunRegistry:
    store: dict[str, dict[str, Any]] = field(default_factory=dict)
    progress_counts: dict[str, int] = field(default_factory=dict)

    def get(self, run_hash: str) -> dict[str, Any] | None:
        return self.store.get(run_hash)

    def set(self, run_hash: str, record: dict[str, Any]) -> None:
        self.store[run_hash] = record


def config_hash(config: RunConfig) -> str:
    # Use model_dump for stable representation
    data = config.model_dump(mode="python")
    digest: str = hash_canonical(data)
    return digest


def create_or_get(
    config: RunConfig,
    registry: InMemoryRunRegistry,
    *,
    seed: int | None = None,
) -> tuple[str, dict[str, Any], bool]:
    """Return (hash, record, created_flag).

    If hash exists, returns cached record with created_flag False.
    Else runs orchestrator, stores minimal record snapshot (summary + validation summary + config hash), returns created_flag True.
    """
    h = config_hash(config)
    existing = registry.get(h)
    if existing is not None:
        return h, existing, False

    progress_events: list[Any] = []
    buf = get_global_buffer(h)

    def cb(state: Any, payload: dict[str, Any] | None) -> None:  # pragma: no cover - callback resilience
        progress_events.append(state)
        try:
            buf.append("stage", {"run_hash": h, "state": getattr(state, "value", str(state)), **(payload or {})})
        except Exception:
            pass

    result = orchestrate(config, seed=seed, callbacks=[cb])
    summary = result.get("summary", {})
    validation = result.get("validation", {})
    # Build validation detail (distributions & folds) for artifact layer
    try:  # pragma: no cover - small integration guard
        from domain.artifacts.validation_merge import merge_validation
        validation_detail = merge_validation(validation)
    except Exception:
        validation_detail = None

    record = {
        "hash": h,
        "summary": summary,
        "validation_summary": validation.get("summary", {}),
        "validation_raw": validation,
        "p_values": {
            "perm": validation.get("permutation", {}).get("p_value"),
            "bb": validation.get("block_bootstrap", {}).get("p_value"),
            "mc": validation.get("monte_carlo_slippage", {}).get("p_value"),
        },
        "progress_events": len(progress_events),
    }
    if validation_detail is not None:
        record["validation_detail"] = validation_detail
    registry.set(h, record)
    # Write artifacts (idempotent) - base path 'artifacts' relative root for now
    try:  # pragma: no cover simple integration guard
        from domain.artifacts.writer import write_artifacts
        base_path = Path("artifacts")
        write_artifacts(h, record, base_path=base_path)
    except Exception:
        pass
    # Append completed snapshot to buffer (after artifacts) for SSE consumers
    try:
        buf.append("snapshot", {"run_hash": h, "summary": summary, "p_values": record["p_values"], "status": "COMPLETE"})
        buf.append("completed", {"run_hash": h, "status": "COMPLETE"})
    except Exception:
        pass
    # Retention pruning (lazy import to avoid circular dependency)
    if len(registry.store) > 100:
        try:  # pragma: no cover - simple guard
            from .retention import prune as retention_prune  # local import
            retention_prune(registry, limit=100)
        except Exception:
            pass
    return h, record, True


__all__ = ["InMemoryRunRegistry", "create_or_get", "config_hash"]
