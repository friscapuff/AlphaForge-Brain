"""Baseline hash capture script (Phase 0 - T002).

Generates deterministic baseline hashes for three representative runs using
minimal synthetic configuration objects and (optionally) orchestrate().

Output JSON (default: artifacts/baseline_hashes_v1.json):
{
    "schema_version": 1,
    "strategies": [
         {"id": str, "seed": int, "run_config_signature": str, "metrics_hash": str,
            "equity_hash": str, "metrics_keys": [..], "equity_len": int, "mode": "orchestrate|mock"}
    ],
    "created_at": ISO8601,
    "tool_version": "baseline_capture:v1",
    "env": {...}
}

Flags:
    --diagnostics      Only emit environment diagnostic JSON (no orchestrate / hashing)
    --mock-on-fail     If orchestrate import/run fails, fall back to deterministic mock data

Rationale:
- Avoid DB/persistence side-effects for purity.
- Use internal metrics hashing (legacy path, will migrate under FR-005/FR-008).
- Provide stable foundation for regression comparisons (T023, T072, T080).

Future Extensions:
- --with-persistence to route through domain.run.create
- Performance timing harness reuse for T003
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from domain.schemas.run_config import ExecutionSpec as OrchestratorExecutionSpec  # type: ignore
from domain.schemas.run_config import RiskSpec as OrchestratorRiskSpec  # type: ignore
from domain.schemas.run_config import RunConfig  # type: ignore
from domain.schemas.run_config import StrategySpec as OrchestratorStrategySpec  # type: ignore
from domain.schemas.run_config import ValidationSpec as OrchestratorValidationSpec  # type: ignore

# NOTE: We deliberately defer all heavy domain/pandas/pyarrow imports until AFTER
# diagnostics mode short-circuits. This allows `--diagnostics` to succeed even if
# compiled extensions are currently misaligned (e.g. numpy / pandas ABI issues).

_ROOT = pathlib.Path(__file__).resolve().parent.parent / "alphaforge-brain" / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if TYPE_CHECKING:  # pragma: no cover - only for static type checking
    from models.cost_model_config import CostModelConfig
    from models.dataset_snapshot import DatasetSnapshot
    from models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
    from models.feature_spec import FeatureSpec

    #
    from models.strategy_config import StrategyConfig  # noqa: F401
    from models.validation_config import ValidationConfig
    from models.walk_forward_config import WalkForwardConfig


@dataclass
class StrategyVariant:
    id: str
    params: dict[str, Any]


def _lazy_domain_imports():  # Import set used outside diagnostics
    global RunConfig, StrategyConfig, DatasetSnapshot, ExecutionConfig, RoundingMode, FillPolicy
    global CostModelConfig, ValidationConfig, WalkForwardConfig, FeatureSpec
    from domain.schemas.run_config import RunConfig  # type: ignore

    if "RunConfig" in globals():  # Already imported
        return
    from models.cost_model_config import CostModelConfig  # type: ignore
    from models.dataset_snapshot import DatasetSnapshot  # type: ignore
    from models.execution_config import ExecutionConfig, FillPolicy, RoundingMode  # type: ignore
    from models.feature_spec import FeatureSpec  # type: ignore

    # RunConfig is already referenced from domain.schemas above for runtime; avoid duplicate type alias here.
    from models.strategy_config import StrategyConfig  # type: ignore
    from models.validation_config import ValidationConfig  # type: ignore
    from models.walk_forward_config import WalkForwardConfig  # type: ignore


def _lazy_metrics_imports():
    global compute_metrics, build_equity_curve, equity_curve_hash
    if "compute_metrics" in globals():  # Already imported
        return
    from domain.metrics.calculator import build_equity_curve, compute_metrics  # type: ignore
    from services.metrics_hash import equity_curve_hash  # type: ignore


def _synthetic_dataset() -> DatasetSnapshot:
    now = datetime.now(timezone.utc)
    return DatasetSnapshot(
        path="synthetic://baseline",
        data_hash="synthetic_data_v1",  # Stable placeholder
        calendar_id="UTC",
        bar_count=1000,
        first_ts=now,
        last_ts=now,
        gap_count=0,
        holiday_gap_count=0,
        duplicate_count=0,
    )


def _base_validation() -> ValidationConfig:
    # Updated to reflect current ValidationConfig fields.
    # caution_p_threshold must be > 0 per model validator; choose tiny value to minimize gating.
    return ValidationConfig(
        permutation_trials=0,
        seed=123,
        caution_p_threshold=0.0001,
    )


def _walk_forward_disabled() -> WalkForwardConfig | None:
    return None


def _execution() -> ExecutionConfig:
    # Use a valid FillPolicy from execution_config (no IMMEDIATE exists)
    return ExecutionConfig(
        lot_size=1,
        rounding_mode=RoundingMode.ROUND,
        fill_policy=FillPolicy.NEXT_BAR_OPEN,
    )


def _costs() -> CostModelConfig:
    return CostModelConfig(
        slippage_bps=0.0,
        fee_bps=0.0,
        borrow_cost_bps=0.0,
    )


def _features() -> list[FeatureSpec]:
    # Provide one dummy feature to exercise feature normalization ordering
    return [
        FeatureSpec(
            name="baseline_feature",
            version="1",
            inputs=["price"],
            params={"window": 5},
            shift_applied=False,
        )
    ]


def _run_config(variant: StrategyVariant) -> RunConfig:
    _lazy_domain_imports()
    # Build orchestrator (domain.schemas.run_config) compatible config.
    # Provide minimal viable fields; risk model placeholder.
    _lazy_domain_imports()
    # Map our simple variant params to orchestrator StrategySpec
    strategy = OrchestratorStrategySpec(name="buy_hold", params=variant.params or {})
    risk = OrchestratorRiskSpec(model="none", params={})
    execution = OrchestratorExecutionSpec()
    validation = OrchestratorValidationSpec()
    # Fixed synthetic window (using orchestrator fallback synthetic dataset path via TEST symbol)
    return RunConfig(
        indicators=[],
        strategy=strategy,
        risk=risk,
        execution=execution,
        validation=validation,
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=123,
    )


def _metrics_hash(metrics: dict[str, float]) -> str:
    # Canonical ordering by key, stable string -> sha256
    items = sorted(metrics.items())
    blob = json.dumps(items, separators=(",", ":"))
    return sha256(blob.encode("utf-8")).hexdigest()


def _mock_series(seed: int, length: int = 32) -> list[dict[str, float]]:
    import random

    random.seed(seed)
    nav = 1.0
    peak = 1.0
    series: list[dict[str, float]] = []
    for i in range(length):
        nav *= 1 + random.uniform(-0.002, 0.002)
        peak = max(peak, nav)
        dd = (peak - nav) / peak if peak > 0 else 0.0
        series.append({"ts": i, "nav": nav, "drawdown": dd})
    return series


def capture(
    strategies: list[StrategyVariant], seeds: list[int], *, mock_on_fail: bool
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for variant, seed in zip(strategies, seeds):
        mode = "orchestrate"
        try:
            cfg = _run_config(variant)
        except Exception:
            if not mock_on_fail:
                raise
            # If config construction itself fails, fall back to mock
            mode = "mock"
            cfg = None  # type: ignore
            metrics = {"config_error": 1}
            equity = _mock_series(seed)
            _lazy_metrics_imports()
            metrics_h = _metrics_hash(metrics)
            eq_hash = (
                equity_curve_hash(equity) if equity else sha256(b"EMPTY").hexdigest()
            )
            records.append(
                {
                    "id": variant.id,
                    "seed": seed,
                    "run_config_signature": "<unavailable>",
                    "metrics_hash": metrics_h,
                    "equity_hash": eq_hash,
                    "metrics_keys": sorted(list(metrics.keys())),
                    "equity_len": len(equity),
                    "mode": mode,
                }
            )
            continue
        try:
            _lazy_metrics_imports()
            from domain.run.orchestrator import (
                orchestrate,  # type: ignore  # lazy import for env isolation
            )

            result = orchestrate(cfg, seed=seed)
            summary = result.get("summary", result)
            # Orchestrator attaches raw equity_df (DataFrame) under result; leverage it directly.
            equity_df = result.get("equity_df")
            equity: list[dict[str, float]] = []
            if equity_df is not None:
                try:
                    # Expect columns: timestamp, equity, return
                    for _idx, row in getattr(equity_df, "iterrows", lambda: [])():  # type: ignore
                        ts = int(row.get("timestamp") if hasattr(row, "get") else row.timestamp)  # type: ignore
                        nav = float(row.get("equity") if hasattr(row, "get") else row.equity)  # type: ignore
                        equity.append({"ts": ts, "nav": nav})
                except Exception:
                    equity = []
            if not equity and summary.get("equity_curve"):
                # Legacy path if summary held a pre-built equity_curve list
                try:
                    equity_raw = summary.get("equity_curve") or []
                    equity = [
                        {
                            "ts": int(
                                e.get("ts")
                                if isinstance(e, dict)
                                else getattr(e, "ts", i)
                            ),
                            "nav": float(
                                e.get("nav")
                                if isinstance(e, dict)
                                else getattr(e, "nav", 0.0)
                            ),
                        }
                        for i, e in enumerate(equity_raw)
                    ]
                except Exception:
                    equity = []
            # If still empty but we have positions/trades, attempt to rebuild from positions if provided
            if not equity and "positions" in summary:
                try:
                    positions_df = summary["positions"]
                    if (
                        positions_df is not None
                        and hasattr(positions_df, "empty")
                        and not positions_df.empty
                    ):
                        curve_df = build_equity_curve(positions_df)
                        for _idx, row in curve_df.iterrows():  # type: ignore
                            equity.append(
                                {
                                    "ts": int(row["timestamp"]),
                                    "nav": float(row["equity"]),
                                }
                            )
                except Exception:
                    equity = []
            metrics = summary.get("metrics") or {}
            if not metrics:
                metrics = compute_metrics([], [], include_anomalies=False)
        except Exception:
            if not mock_on_fail:
                raise
            mode = "mock"
            # Deterministic mock metrics from config signature pieces
            if cfg is not None and hasattr(cfg, "deterministic_signature"):
                sig = cfg.deterministic_signature()
            elif cfg is not None and hasattr(cfg, "canonical_hash"):
                sig = cfg.canonical_hash()
            else:
                sig = variant.id
            metrics = {
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "trade_count": 0,
                "signature_bytes": len(sig),
            }
            equity = _mock_series(seed)
        _lazy_metrics_imports()  # Ensure hash impl available even in mock path
        metrics_h = _metrics_hash(metrics)
        eq_hash = equity_curve_hash(equity) if equity else sha256(b"EMPTY").hexdigest()
        if cfg is not None and hasattr(cfg, "deterministic_signature"):
            run_sig = cfg.deterministic_signature()
        elif cfg is not None and hasattr(cfg, "canonical_hash"):
            run_sig = cfg.canonical_hash()
        else:
            run_sig = "<unavailable>"
        records.append(
            {
                "id": variant.id,
                "seed": seed,
                "run_config_signature": run_sig,
                "metrics_hash": metrics_h,
                "equity_hash": eq_hash,
                "metrics_keys": sorted(list(metrics.keys())),
                "equity_len": len(equity),
                "mode": mode,
            }
        )
    return {
        "schema_version": 1,
        "strategies": records,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": "baseline_capture:v1",
    }


def _dependency_diagnostics() -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        import numpy  # type: ignore

        info["numpy_version"] = numpy.__version__
    except Exception as e:  # pragma: no cover
        info["numpy_error"] = str(e)
    try:
        import pandas  # type: ignore

        info["pandas_version"] = pandas.__version__
    except Exception as e:  # pragma: no cover
        info["pandas_error"] = str(e)
    try:
        import pyarrow  # type: ignore

        info["pyarrow_version"] = pyarrow.__version__
    except Exception as e:  # pragma: no cover
        info["pyarrow_error"] = str(e)
    return info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/baseline_hashes_v1.json")
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Only output environment diagnostics JSON and exit",
    )
    parser.add_argument(
        "--mock-on-fail",
        action="store_true",
        help="Fallback to deterministic mock data if orchestrate fails (env issues)",
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    strategies = [
        StrategyVariant("sma_fast_slow", {"fast": 5, "slow": 20}),
        StrategyVariant("sma_single", {"window": 10}),
        StrategyVariant("sma_noise", {"noise": 0.01}),
    ]
    seeds = [123, 123, 456]

    diagnostics = _dependency_diagnostics()

    if args.diagnostics:
        payload = {
            "schema_version": 1,
            "strategies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "baseline_capture:v1",
            "env": diagnostics,
            "mode": "diagnostics",
        }
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        print("Diagnostics written. Skipping orchestrate.")
        return

    try:
        payload = capture(strategies, seeds, mock_on_fail=args.mock_on_fail)
        payload["env"] = diagnostics
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        print(f"Baseline hashes written: {args.out}")
    except Exception as e:  # pragma: no cover
        placeholder = {
            "schema_version": 1,
            "strategies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "baseline_capture:v1",
            "error": str(e),
            "env": diagnostics,
            "action_required": "Resolve NumPy/Pandas compiled extension mismatch (align with pyproject pins: numpy '<2.1,>=2.0.0') then rerun script",
        }
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(placeholder, f, indent=2, sort_keys=True)
        print("Baseline capture failed; placeholder written with diagnostics.")


if __name__ == "__main__":  # pragma: no cover
    main()
