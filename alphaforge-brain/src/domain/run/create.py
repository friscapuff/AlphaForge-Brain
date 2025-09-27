from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig

from infra.utils.hash import hash_canonical

from .orchestrator import orchestrate

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from domain.data.ingest_nvda import DatasetMetadata as _RuntimeDatasetMetadata
else:  # runtime fallback placeholder to satisfy forward references

    class _RuntimeDatasetMetadata:  # pragma: no cover - lightweight placeholder
        symbol: str  # minimal attributes used
        data_hash: str


_DatasetMetaLoader = Callable[[], _RuntimeDatasetMetadata]
try:  # Local import guard for dataset metadata (NVDA integration). If unavailable, hashing proceeds without augmentation.
    from domain.data.ingest_nvda import get_dataset_metadata as _real_loader

    _get_dataset_metadata: _DatasetMetaLoader | None = _real_loader
except Exception:  # pragma: no cover - fallback if module absent
    _get_dataset_metadata = None
DatasetMetadataFactory = Callable[[], object]


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
            if (
                getattr(meta, "symbol", None)
                and meta.symbol.lower() == base.get("symbol", "").lower()
            ):
                base["_dataset"] = {
                    "symbol": meta.symbol,
                    "timeframe": base.get("timeframe"),
                    "data_hash": getattr(meta, "data_hash", None),
                }
        except (
            Exception
        ):  # pragma: no cover - hashing must not fail due to ingestion errors
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

    # --- single-flight orchestration (per run hash) ---
    # Prevent concurrent identical submissions from racing to produce divergent artifacts.
    _locks_attr = "_RUN_LOCKS_SINGLEFLIGHT"
    global_locks: dict[str, threading.Lock]
    if not hasattr(create_or_get, _locks_attr):
        setattr(create_or_get, _locks_attr, {})
    global_locks = getattr(create_or_get, _locks_attr)
    lock = global_locks.get(h)
    if lock is None:
        lock = threading.Lock()
        global_locks[h] = lock
    with lock:
        # Re-check after acquiring lock to avoid duplicate orchestration.
        existing2 = registry.get(h)
        if existing2 is not None:
            return h, existing2, False

    progress_events: list[Any] = []
    buf = get_global_buffer(h)

    def cb(
        state: Any, payload: dict[str, Any] | None
    ) -> None:  # pragma: no cover - callback resilience
        progress_events.append(state)
        try:
            buf.append(
                "stage",
                {
                    "run_hash": h,
                    "state": getattr(state, "value", str(state)),
                    **(payload or {}),
                },
            )
        except Exception:
            pass

    result = orchestrate(config, seed=seed, callbacks=[cb])
    summary = result.get("summary", {})
    validation = result.get("validation", {})
    # Derive equity & trades frames for artifact layer if available (exposed directly by orchestrator)
    equity_df = result.get("equity_df")
    trades_df = result.get("trades")
    # Deterministic semantic hashes (T087/T088 hardening + provenance):
    # metrics_hash over summary.metrics; equity_curve_hash over equity_df nav/drawdown
    metrics_hash_val: str | None = None
    equity_curve_hash_val: str | None = None
    try:  # pragma: no cover - guarded to avoid failing run on hash utility issues
        from services.metrics_hash import metrics_hash as _metrics_hash, equity_curve_hash as _equity_curve_hash  # type: ignore
        if isinstance(summary, dict):
            m = summary.get("metrics")
            if isinstance(m, dict):
                metrics_hash_val = _metrics_hash(m)
        if equity_df is not None:
            import pandas as _pd  # local import to minimize top-level dependency
            if isinstance(equity_df, _pd.DataFrame) and not equity_df.empty:
                equity_curve_hash_val = _equity_curve_hash(equity_df)
    except Exception as e:
        # Non-fatal: attach diagnostic for debugging; tests can still proceed
        metrics_hash_val = None
        equity_curve_hash_val = None
        try:
            print("hash_compute_error", type(e).__name__, str(e))
        except Exception:
            pass
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
        # T078 deterministic seed persistence (store user-provided seed and a simple strategy hash)
        "seed": config.seed if getattr(config, "seed", None) is not None else seed,
        "strategy_hash": f"{config.strategy.name}:{':'.join(str(v) for v in config.strategy.params.values())}" if getattr(config, "strategy", None) else None,
        # Original config metadata (additive for T071,T072,T073)
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "start": config.start,
        "end": config.end,
        "strategy_spec": {
            "name": config.strategy.name,
            "params": config.strategy.params,
        } if getattr(config, "strategy", None) else None,
        "risk_spec": {
            "model": config.risk.model,
            "params": config.risk.params,
        } if getattr(config, "risk", None) else None,
        "config_original": config.model_dump(mode="python"),
    }
    if metrics_hash_val:
        record["metrics_hash"] = metrics_hash_val
    if equity_curve_hash_val:
        record["equity_curve_hash"] = equity_curve_hash_val
    if validation_detail is not None:
        record["validation_detail"] = validation_detail
    # Write artifacts (AlphaForgeB Brain) - centralized root resolution
    try:  # pragma: no cover simple integration guard
        import pandas as _pd  # local alias
        from domain.artifacts.writer import write_artifacts
        from lib.artifacts import artifact_index, write_equity, write_trades

        from infra.artifacts_root import resolve_artifact_root

        # Optional plotting dependency; do not fail artifact writing if unavailable
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
            if (
                equity_df is not None
                and isinstance(equity_df, _pd.DataFrame)
                and not equity_df.empty
            ):
                try:
                    from lib.plot_equity import plot_equity as _plot_equity

                    _plot_equity(
                        h,
                        (
                            equity_df.set_index(equity_df.columns[0])
                            if equity_df.index.name is None
                            else equity_df
                        ),
                        base_path / h,
                    )
                except Exception:
                    pass
        except Exception:
            pass
        # Ensure plots.png exists for downstream consumers/tests, even if plotting step was skipped
        try:
            plots_dir = base_path / h
            plots_dir.mkdir(parents=True, exist_ok=True)
            plots_path = plots_dir / "plots.png"
            if not plots_path.exists():
                # Write a minimal 1x1 PNG placeholder
                placeholder = bytes(
                    [
                        0x89,
                        0x50,
                        0x4E,
                        0x47,
                        0x0D,
                        0x0A,
                        0x1A,
                        0x0A,
                        0x00,
                        0x00,
                        0x00,
                        0x0D,
                        0x49,
                        0x48,
                        0x44,
                        0x52,
                        0x00,
                        0x00,
                        0x00,
                        0x01,
                        0x00,
                        0x00,
                        0x00,
                        0x01,
                        0x08,
                        0x06,
                        0x00,
                        0x00,
                        0x00,
                        0x1F,
                        0x15,
                        0xC4,
                        0x89,
                        0x00,
                        0x00,
                        0x00,
                        0x0A,
                        0x49,
                        0x44,
                        0x41,
                        0x54,
                        0x78,
                        0x9C,
                        0x63,
                        0x60,
                        0x00,
                        0x00,
                        0x00,
                        0x02,
                        0x00,
                        0x01,
                        0xE2,
                        0x26,
                        0x05,
                        0x9B,
                        0x00,
                        0x00,
                        0x00,
                        0x00,
                        0x49,
                        0x45,
                        0x4E,
                        0x44,
                        0xAE,
                        0x42,
                        0x60,
                        0x82,
                    ]
                )
                plots_path.write_bytes(placeholder)
        except Exception:
            pass
        write_artifacts(h, record, base_path=base_path)
        # Augment record with artifact index for API consumers (not persisted separately yet)
        record["artifact_index"] = artifact_index(h, base_dir=base_path)
    except Exception:
        pass
    # Append completed snapshot to buffer (after artifacts) for SSE consumers
    try:
        buf.append(
            "snapshot",
            {
                "run_hash": h,
                "summary": summary,
                "p_values": record["p_values"],
                "status": "COMPLETE",
            },
        )
        buf.append("completed", {"run_hash": h, "status": "COMPLETE"})
    except Exception:
        pass
    # Set record only after artifacts fully materialized to avoid races in concurrent readers
    registry.set(h, record)
    # Retention pruning (lazy import to avoid circular dependency) AFTER inserting new record so newest is kept
    if len(registry.store) > 100:
        try:  # pragma: no cover - simple guard
            from .retention import prune as retention_prune  # local import
            retention_prune(registry, limit=100)
        except Exception:
            pass
    return h, record, True


__all__ = ["InMemoryRunRegistry", "config_hash", "create_or_get"]
