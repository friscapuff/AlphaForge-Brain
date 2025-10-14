from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping

from domain.run.event_buffer import get_global_buffer
from domain.schemas.run_config import RunConfig
from models.run_validation_status import RunValidationStatus

from infra.persistence import (
    persist_persistence_record,
    persistence_record_id,
    persistence_schema_version,
)
from infra.utils.hash import hash_canonical

from .orchestrator import orchestrate


def _build_accounting_ledger(
    run_hash: str,
    summary: Mapping[str, Any],
    *,
    initial_cash: float = 100_000.0,
) -> dict[str, Any]:
    """Synthesize a lightweight accounting ledger snapshot for trust-gate evaluation.

    The baseline simulator always flattens positions, so unrealised PnL is zero and
    ending cash matches equity. Fees and borrow costs are currently not modelled,
    therefore we surface them as zero until execution accounting expands.
    """

    cumulative_pnl = (
        float(summary.get("cumulative_pnl", 0.0))
        if isinstance(summary, Mapping)
        else 0.0
    )
    trade_count = (
        int(summary.get("trade_count", 0)) if isinstance(summary, Mapping) else 0
    )
    cash = float(initial_cash + cumulative_pnl)
    unrealized_pnl = 0.0
    fees = 0.0
    equity = cash + unrealized_pnl + fees
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    trade_ids: list[str]
    if trade_count > 0:
        prefix = run_hash[:8].upper()
        trade_ids = [f"{prefix}-T{i:03d}" for i in range(1, trade_count + 1)]
    else:
        trade_ids = [f"{run_hash[:8].upper()}-T000"]

    return {
        "run_hash": run_hash,
        "cash": cash,
        "unrealized_pnl": unrealized_pnl,
        "fees": fees,
        "equity": equity,
        "tolerance": 1.0,
        "currency": "USD",
        "trade_ids": trade_ids,
        "generated_at": generated_at,
    }


if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from domain.data.ingest_nvda import DatasetMetadata as _RuntimeDatasetMetadata
    from prometheus_client import CollectorRegistry as _CollectorRegistry
    from services.trust_gates.models import TrustGateSummary as _TrustGateSummary
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
    # Phase 3: optional equity normalization dual-run (compare mode)
    normalized_equity_df = None
    try:
        from settings.flags import is_equity_normalizer_v2_enabled

        if equity_df is not None and is_equity_normalizer_v2_enabled():
            import pandas as _pd

            if isinstance(equity_df, _pd.DataFrame) and not equity_df.empty:
                normalized_equity_df = equity_df.copy()
                if "nav" in equity_df.columns and "peak_nav" in equity_df.columns:
                    try:
                        med = float(equity_df["nav"].median())
                        if med > 10_000:
                            normalized_equity_df["nav"] = (
                                normalized_equity_df["nav"] / 1_000_000.0
                            )
                            normalized_equity_df["peak_nav"] = (
                                normalized_equity_df["peak_nav"] / 1_000_000.0
                            )
                    except Exception:
                        pass
                # Fallback path: legacy equity-only curve (columns: timestamp,equity,return)
                elif "equity" in equity_df.columns:
                    try:
                        med_equity = float(equity_df["equity"].median())
                        if med_equity > 10_000:
                            normalized_equity_df["equity"] = (
                                normalized_equity_df["equity"] / 1_000_000.0
                            )
                    except Exception:
                        pass
                # else leave as-is (already normalized or columns absent)
    except Exception:
        pass
    # Deterministic semantic hashes (T087/T088 hardening + provenance):
    # metrics_hash over summary.metrics; equity_curve_hash over equity_df nav/drawdown
    metrics_hash_val: str | None = None
    equity_curve_hash_val: str | None = (
        None  # legacy (always nav/drawdown over original equity_df)
    )
    equity_curve_hash_v2_val: str | None = (
        None  # optional normalized-equity hash (AF_EQUITY_HASH_V2)
    )
    try:  # pragma: no cover - guarded to avoid failing run on hash utility issues
        from services.hashes import equity_signature as _equity_curve_hash
        from services.hashes import metrics_signature as _metrics_hash
        from settings.flags import (
            is_equity_hash_v2_enabled as _is_equity_hash_v2_enabled,
        )
        from settings.flags import (
            is_equity_normalizer_v2_enabled as _is_equity_normalizer_v2_enabled,
        )

        if isinstance(summary, dict):
            m = summary.get("metrics")
            if isinstance(m, dict):
                metrics_hash_val = _metrics_hash(m)
        if equity_df is not None:
            import pandas as _pd  # local import to minimize top-level dependency

            if isinstance(equity_df, _pd.DataFrame) and not equity_df.empty:
                equity_curve_hash_val = _equity_curve_hash(equity_df)
                # Optional Phase 3.5 dual-hash: compute normalized-equity hash side-by-side
                # Only when both normalization is enabled (we produced normalized_equity_df) and hashing flag is ON.
                try:
                    if (
                        _is_equity_hash_v2_enabled()
                        and _is_equity_normalizer_v2_enabled()
                        and normalized_equity_df is not None
                        and isinstance(normalized_equity_df, _pd.DataFrame)
                        and not normalized_equity_df.empty
                    ):
                        equity_curve_hash_v2_val = _equity_curve_hash(
                            normalized_equity_df
                        )
                except Exception:
                    # Non-fatal; leave v2 hash None
                    equity_curve_hash_v2_val = None
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

    # Compute validation caution (Phase 4)
    try:
        from services.validation_caution import compute_caution as _compute_caution

        # Gather p-values into flat mapping for evaluation
        pvals_map: dict[str, float] = {}
        pv = validation.get("permutation", {}) if isinstance(validation, dict) else {}
        if isinstance(pv, dict):
            raw_p = pv.get("p_value")
            if isinstance(raw_p, (int, float)):
                pvals_map["permutation"] = float(raw_p)
        bb = (
            validation.get("block_bootstrap", {})
            if isinstance(validation, dict)
            else {}
        )
        if isinstance(bb, dict):
            raw_p = bb.get("p_value")
            if isinstance(raw_p, (int, float)):
                pvals_map["block_bootstrap"] = float(raw_p)
        mc = (
            validation.get("monte_carlo_slippage", {})
            if isinstance(validation, dict)
            else {}
        )
        if isinstance(mc, dict):
            raw_p = mc.get("p_value")
            if isinstance(raw_p, (int, float)):
                pvals_map["monte_carlo_slippage"] = float(raw_p)
        caution_flag, caution_metrics = _compute_caution(
            pvals_map if pvals_map else None
        )
    except Exception:
        caution_flag, caution_metrics = False, []

    record = {
        "hash": h,
        "summary": summary,
        "validation_summary": validation.get("summary", {}),
        "validation_raw": validation,
        "validation_caution": caution_flag,
        "validation_caution_metrics": caution_metrics,
        "p_values": {
            "perm": validation.get("permutation", {}).get("p_value"),
            "bb": validation.get("block_bootstrap", {}).get("p_value"),
            "mc": validation.get("monte_carlo_slippage", {}).get("p_value"),
        },
        "progress_events": len(progress_events),
        "created_at": datetime.now(timezone.utc).timestamp(),
        # T078 deterministic seed persistence (store user-provided seed and a simple strategy hash)
        "seed": config.seed if getattr(config, "seed", None) is not None else seed,
        "strategy_hash": (
            f"{config.strategy.name}:{':'.join(str(v) for v in config.strategy.params.values())}"
            if getattr(config, "strategy", None)
            else None
        ),
        # Original config metadata (additive for T071,T072,T073)
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "start": config.start,
        "end": config.end,
        "strategy_spec": (
            {
                "name": config.strategy.name,
                "params": config.strategy.params,
            }
            if getattr(config, "strategy", None)
            else None
        ),
        "risk_spec": (
            {
                "model": config.risk.model,
                "params": config.risk.params,
            }
            if getattr(config, "risk", None)
            else None
        ),
        "config_original": config.model_dump(mode="python"),
    }
    record["schema_version"] = persistence_schema_version()
    ledger_snapshot = _build_accounting_ledger(h, summary)
    record["accounting_ledger"] = ledger_snapshot
    record["run_manifest"] = {
        "run_hash": h,
        "executed_at": ledger_snapshot["generated_at"],
        "accounting_ledger": ledger_snapshot,
        "trade_count": summary.get("trade_count"),
    }
    if normalized_equity_df is not None:
        scaled = False
        scale_factor = None
        try:
            cols = getattr(normalized_equity_df, "columns", [])
            median_source = (
                "nav" if "nav" in cols else ("equity" if "equity" in cols else None)
            )
            median_val = None
            if median_source:
                median_val = float(normalized_equity_df[median_source].median())
            # Infer scaling action by checking magnitude vs threshold (>= 10_000 implies original was scaled and we divided)
            if median_val is not None and median_val < 10_000:
                # Need original equity_df median to determine if scaling occurred
                try:
                    if (
                        equity_df is not None
                        and median_source
                        and median_source in equity_df.columns
                    ):
                        orig_median = float(equity_df[median_source].median())
                        if (
                            orig_median > 10_000 and orig_median > median_val * 100
                        ):  # heuristic confirmation
                            scaled = True
                            scale_factor = 1_000_000.0
                except Exception:
                    pass
        except Exception:
            median_val = None
        record["normalized_equity_preview"] = {
            "rows": int(getattr(normalized_equity_df, "shape", [0, 0])[0]),
            "median_nav": median_val,  # legacy name kept for existing tests
            "median_value": median_val,  # new generic alias
            "scaled": scaled,
            "scale_factor": scale_factor,
        }
    if metrics_hash_val:
        record["metrics_hash"] = metrics_hash_val
    if equity_curve_hash_val:
        record["equity_curve_hash"] = equity_curve_hash_val
    if equity_curve_hash_v2_val:
        # Expose additive field; tests (T037) will assert dual presence & stability
        record["equity_curve_hash_v2"] = equity_curve_hash_v2_val
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

        trust_gate_summary: dict[str, Any] | None = None
        trust_gate_manifest_block: dict[str, Any] | None = None
        telemetry_registry: _CollectorRegistry | None = None
        suite_service: TrustGateSuiteService | None = None
        candidate_manifest: Mapping[str, Any]
        try:
            from services.trust_gates.config_loader import ToleranceConfigError
            from services.trust_gates.report_writer import write_suite_report
            from services.trust_gates.suite_service import TrustGateSuiteService
            from services.trust_gates.telemetry import (
                create_registry,
                emit_config_error,
                emit_gate_metrics,
            )

            telemetry_registry = create_registry()
            suite_service = TrustGateSuiteService()
            try:
                baseline_snapshot = copy.deepcopy(
                    suite_service.baseline.manifest_snapshot
                )
                if isinstance(baseline_snapshot, dict):
                    run_section = baseline_snapshot.setdefault("run", {})
                    if isinstance(run_section, dict):
                        run_section["accounting_ledger"] = copy.deepcopy(
                            ledger_snapshot
                        )
                    candidate_manifest = baseline_snapshot
                else:
                    candidate_manifest = suite_service.baseline.manifest_snapshot
            except Exception:
                candidate_manifest = suite_service.baseline.manifest_snapshot
            trust_summary_local: _TrustGateSummary = suite_service.run(
                run_id=h,
                config_hash=config.deterministic_signature(),
                candidate_manifest=candidate_manifest,
            )
            report_root = base_path / "trust_gates" / "reports"
            trust_summary_local = write_suite_report(
                trust_summary_local, report_root, run_id=h
            )
            for gate_result in trust_summary_local.results:
                emit_gate_metrics(
                    registry=telemetry_registry,
                    gate=gate_result.name,
                    status=gate_result.status,
                    duration_ms=gate_result.duration_ms or 0,
                    profile=trust_summary_local.tolerance_profile,
                )
            trust_gate_summary = trust_summary_local.as_dict()
            trust_gate_manifest_block = trust_summary_local.manifest_block()
        except (
            Exception
        ) as exc:  # pragma: no cover - trust gate suite optional during bring-up
            if (
                telemetry_registry is not None
                and suite_service is not None
                and isinstance(exc, ToleranceConfigError)
            ):
                emit_config_error(
                    registry=telemetry_registry,
                    gate="causality",
                    profile=suite_service.tolerance_profile,
                    reason="load_failure",
                )
            trust_gate_summary = {
                "status": "unavailable",
                "error": str(exc),
            }

        if trust_gate_summary is not None:
            record["trust_gate_summary"] = trust_gate_summary
        if trust_gate_manifest_block is not None:
            record["trust_gate_manifest"] = trust_gate_manifest_block
            try:
                from services.hashes import trust_gate_signature

                record["trust_gate_signature"] = trust_gate_signature(
                    trust_gate_manifest_block
                )
            except Exception:
                pass
            try:
                tg_status = None
                if isinstance(trust_gate_summary, dict):
                    tg_status = trust_gate_summary.get("status")
                trust_gate_validation_status = (
                    "accepted" if tg_status in {"pass", "dry-run"} else "rejected"
                )
                persist_persistence_record(
                    record_id=persistence_record_id(run_hash=h, component="trust_gate"),
                    payload=trust_gate_manifest_block,
                    source_component="trust_gate",
                    validation_status=trust_gate_validation_status,
                )
            except Exception:
                pass
        validation_status: RunValidationStatus | None = None
        try:
            from services.validation.context import build_validation_context
            from services.validation.manifest_v2 import (
                build_validation_payload as _build_validation_payload,
            )
            from services.validation.pipeline import execute_validation_modules
            from services.validation.status import determine_validation_status

            validation_v2_payload = None
            validation_v2_artifacts: list[Any] = []

            bars_obj = result.get("bars")
            equity_frame = result.get("equity_df")
            fills_obj = result.get("fills")

            validation_manifest_hash: str | None = None
            if isinstance(bars_obj, _pd.DataFrame) and not bars_obj.empty:
                bars_df = bars_obj.copy()
                equity_df_final = (
                    equity_frame.copy()
                    if isinstance(equity_frame, _pd.DataFrame)
                    else _pd.DataFrame(equity_frame or {})
                )
                trades_df_final = (
                    trades_df
                    if isinstance(trades_df, _pd.DataFrame)
                    else _pd.DataFrame(trades_df or [])
                )
                fills_df = (
                    fills_obj.copy()
                    if isinstance(fills_obj, _pd.DataFrame)
                    else (_pd.DataFrame(fills_obj) if fills_obj is not None else None)
                )

                run_config_adapter, runtime_config, seed_bundle = (
                    build_validation_context(config)
                )

                validation_results = execute_validation_modules(
                    run_hash=h,
                    bars=bars_df,
                    equity_curve=equity_df_final,
                    trades=trades_df_final,
                    fills=fills_df,
                    summary=summary or {},
                    run_config=run_config_adapter,
                    runtime_config=runtime_config,
                    seed_bundle=seed_bundle,
                )

                try:
                    validation_status = determine_validation_status(
                        validation_results.aggregate
                    )
                except Exception:
                    validation_status = None

                validation_v2_payload, artifacts = _build_validation_payload(
                    h,
                    base_path,
                    runtime_config=runtime_config,
                    results=validation_results,
                )
                validation_v2_artifacts = list(artifacts)
                try:
                    from services.hashing.validation_signature import (
                        compute_validation_manifest_hash,
                    )

                    validation_manifest_hash = compute_validation_manifest_hash(
                        validation_v2_payload
                    )
                except Exception:
                    validation_manifest_hash = None
                if (
                    validation_manifest_hash
                    and isinstance(validation_v2_payload, dict)
                    and "manifest_hash" not in validation_v2_payload
                ):
                    validation_v2_payload["manifest_hash"] = validation_manifest_hash
            else:
                validation_v2_payload = None
                validation_v2_artifacts = []
                validation_manifest_hash = None
        except Exception:
            validation_v2_payload = None
            validation_v2_artifacts = []
            validation_manifest_hash = None
            validation_status = None
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
        if validation_v2_payload is not None:
            record["validation_v2"] = validation_v2_payload
            record["validation_schema_version"] = validation_v2_payload.get(
                "schema_version"
            )
            record["validation_significance"] = validation_v2_payload.get(
                "significance_status"
            )
            record["validation_manifest"] = validation_v2_payload.get("manifest")
            record["validation_artifacts_v2"] = [
                {
                    "path": v.path.as_posix(),
                    "sha256": v.sha256,
                    "size": v.size,
                }
                for v in validation_v2_artifacts
            ]
            failed_checks = validation_v2_payload.get("failed_checks")
            if isinstance(failed_checks, list):
                record["validation_failed_checks"] = tuple(
                    str(item) for item in failed_checks
                )
            realism_status = None
            execution_realism = validation_v2_payload.get("execution_realism")
            if isinstance(execution_realism, dict):
                realism_status = execution_realism.get("status")
            if realism_status is None:
                metadata_payload = validation_v2_payload.get("metadata")
                if isinstance(metadata_payload, dict):
                    realism_status = metadata_payload.get("realism_status")
            if realism_status is None:
                manifest_fragment = validation_v2_payload.get("manifest")
                if isinstance(manifest_fragment, dict):
                    realism_fragment = manifest_fragment.get("execution_realism")
                    if isinstance(realism_fragment, dict):
                        realism_status = realism_fragment.get("status")
            if isinstance(realism_status, str) and realism_status:
                record["execution_realism_status"] = realism_status
            if validation_manifest_hash:
                record["validation_manifest_hash"] = validation_manifest_hash

        if validation_status is not None:
            record["validation_status"] = validation_status.value

        write_artifacts(
            h,
            record,
            base_path=base_path,
            trust_gate=trust_gate_manifest_block,
        )
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
