from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig
from infra.utils.hash import hash_canonical

try:  # Local import guard for dataset metadata (NVDA integration). If unavailable, hashing proceeds without augmentation.
    from domain.data.ingest_nvda import get_dataset_metadata as _get_dataset_metadata
except Exception:  # pragma: no cover - fallback if module absent
    _get_dataset_metadata = None

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
    """Compute canonical hash for a run config including dataset binding.

    Augments the raw config with dataset provenance fields (symbol,timeframe,data_hash) once
    dataset metadata is resolvable. This ensures perturbations to the underlying dataset
    (e.g., price edit) produce a new run hash even if the logical config is unchanged.
    Fallback: if metadata loader unavailable, reverts to legacy hashing (pure config fields).
    """
    base = config.model_dump(mode="python")
    # Resolve dataset metadata only if symbol/timeframe present and loader imported.
    if _get_dataset_metadata is not None:
        try:
            meta = _get_dataset_metadata()
            # Only attach if symbols match (future multi-symbol extension may need registry keyed by (symbol,timeframe)).
            if getattr(meta, "symbol", None) and meta.symbol.lower() == base.get("symbol", "").lower():
                base["_dataset"] = {
                    "symbol": meta.symbol,
                    "timeframe": base.get("timeframe"),
                    "data_hash": getattr(meta, "data_hash", None),
                }
        except Exception:  # pragma: no cover - hashing must not fail due to ingestion errors
            pass
    digest: str = hash_canonical(base)
    return digest


def create_or_get(
    config: RunConfig,
    registry: InMemoryRunRegistry,
    *,
    seed: int | None = None,
    artifacts_base: Path | None = None,
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
    # Derive equity & trades frames for artifact layer if available (exposed directly by orchestrator)
    equity_df = result.get("equity_df")
    trades_df = result.get("trades")
    # Build validation detail (distributions & folds) for artifact layer
    try:  # pragma: no cover - small integration guard
        from domain.artifacts.validation_merge import merge_validation
        validation_detail = merge_validation(validation)
    except Exception:
        validation_detail = None

    from datetime import datetime, timezone
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
        "created_at": datetime.now(timezone.utc).timestamp(),
    }
    if validation_detail is not None:
        record["validation_detail"] = validation_detail
    registry.set(h, record)
    # Write artifacts (AlphaForgeB Brain) - centralized root resolution
    try:  # pragma: no cover simple integration guard
        import pandas as _pd  # local alias

        from domain.artifacts.writer import write_artifacts
        from infra.artifacts_root import resolve_artifact_root
        from lib.artifacts import artifact_index, write_equity, write_trades
        from lib.plot_equity import plot_equity
        base_path = resolve_artifact_root(artifacts_base)
        # Persist equity & trades if structures convertible to DataFrame
        try:
            if equity_df is not None and isinstance(equity_df, _pd.DataFrame):
                write_equity(h, equity_df, base_dir=base_path)
        except Exception:
            pass
        try:
            if trades_df is not None and isinstance(trades_df, list):
                tdf = _pd.DataFrame(trades_df)
                if not tdf.empty:
                    write_trades(h, tdf, base_dir=base_path)
        except Exception:
            pass
        # Plot equity if present
        try:
            if equity_df is not None and isinstance(equity_df, _pd.DataFrame) and not equity_df.empty:
                plot_equity(
                    h,
                    equity_df.set_index(equity_df.columns[0]) if equity_df.index.name is None else equity_df,
                    base_path / h,
                )
        except Exception:
            pass
        write_artifacts(h, record, base_path=base_path)
        # Augment record with artifact index for API consumers (not persisted separately yet)
        record["artifact_index"] = artifact_index(h, base_dir=base_path)
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


__all__ = ["InMemoryRunRegistry", "config_hash", "create_or_get"]
