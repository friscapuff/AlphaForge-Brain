from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from domain.validation.masters.bias_adjustment import SharpeBiasAdjustment
from domain.validation.masters.cross_validation_models import (
    CrossValidationSummary,
)
from domain.validation.masters.permutation_result import (
    PermutationValidationResult,
)
from domain.validation.realism.report import (
    ExecutionRealismAnalyzer,
    ExecutionRealismReport,
)

from infra.observability import trace_validation_span
from infra.persistence import clear_validation_trace_spans

from .aggregator import ValidationAggregate, ValidationAggregator
from .bias_adjustments import BiasAdjustmentsCalculator
from .cpcv_scheduler import CrossValidationScheduler
from .masters_permutation import PermutationEngine, PermutationSegmentResult
from .seeding import ValidationSeedBundle


@dataclass(frozen=True)
class ValidationRuntimeConfig:
    """Minimal configuration required to drive Masters validation services."""

    permutation_count: int
    significance_threshold: float
    leakage_threshold: float
    realism_capacity_bps_limit: float
    bias_absolute_threshold: float
    bias_relative_threshold: float
    modules: tuple[str, ...]
    seed_root: int


@dataclass(frozen=True)
class ValidationResults:
    """Aggregated output from Masters validation services."""

    segments: tuple[PermutationSegmentResult, ...]
    permutation: tuple[PermutationValidationResult, ...]
    bias_adjustment: SharpeBiasAdjustment | None
    cross_validation: CrossValidationSummary | None
    execution_realism: ExecutionRealismReport | None
    aggregate: ValidationAggregate


def execute_validation_modules(
    *,
    run_hash: str,
    bars: pd.DataFrame,
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    fills: pd.DataFrame | None,
    summary: Mapping[str, Any],
    run_config: Any,
    runtime_config: ValidationRuntimeConfig,
    seed_bundle: ValidationSeedBundle,
) -> ValidationResults:
    """Run Masters validation modules and return domain-level results.

    Parameters
    ----------
    run_hash:
        Stable identifier for the run under evaluation.
    bars:
        Price series (OHLCV) used to compute permutation segments and leakage spans.
    equity_curve:
        Equity history produced by the strategy; used to derive Sharpe statistics.
    trades:
        Round-trip trade DataFrame (may be empty) for sample size metadata.
    fills:
        Raw execution fills. When ``None`` an empty DataFrame is used for realism analysis.
    summary:
        Run summary dictionary - must include the metrics block with Sharpe ratio when available.
    run_config:
        Object exposing ``strategy``, ``validation``, and ``walk_forward`` attributes as used by
        the specialised validation services.
    runtime_config:
        Normalised validation configuration with threshold/seed metadata.
    seed_bundle:
        Deterministic seeds for permutation batches, optimizer hooks, CPCV combinations, and realism overlays.
    """

    if not isinstance(bars, pd.DataFrame) or bars.empty:
        raise ValueError("bars DataFrame is required to execute Masters validation")

    fills_df = fills if isinstance(fills, pd.DataFrame) else pd.DataFrame()
    trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame()

    if not runtime_config.modules:
        clear_validation_trace_spans(run_hash=run_hash)
        aggregator = ValidationAggregator(
            significance_threshold=runtime_config.significance_threshold,
            leakage_threshold=runtime_config.leakage_threshold,
        )
        aggregate = aggregator.aggregate(
            permutations=(),
            bias_adjustment=None,
            cross_validation=None,
            realism=None,
        )
        return ValidationResults(
            segments=tuple(),
            permutation=tuple(),
            bias_adjustment=None,
            cross_validation=None,
            execution_realism=None,
            aggregate=aggregate,
        )

    with trace_validation_span("total", run_hash=run_hash) as total_span:
        with trace_validation_span("permutation", run_hash=run_hash) as perm_span:
            segments = _run_permutation_segments(
                run_hash=run_hash,
                bars=bars,
                run_config=run_config,
                seed_bundle=seed_bundle,
                modules=runtime_config.modules,
            )
            permutation_results = tuple(
                seg.to_validation_result(run_hash=run_hash) for seg in segments
            )
            perm_span["enabled"] = "permutation" in runtime_config.modules
            perm_span["segments"] = len(segments)
            if segments:
                perm_span["permutations_requested"] = sum(
                    int(seg.requested_permutations) for seg in segments
                )
                perm_span["permutations_executed"] = sum(
                    int(seg.executed_permutations) for seg in segments
                )
                perm_span["fallbacks"] = sum(
                    1 for seg in segments if seg.fallback_reason is not None
                )

        with trace_validation_span("cross_validation", run_hash=run_hash) as cv_span:
            cross_validation = _run_cross_validation(
                run_hash=run_hash,
                bars=bars,
                run_config=run_config,
                seed_bundle=seed_bundle,
                runtime_config=runtime_config,
                observed_sharpe=_extract_observed_sharpe(summary, equity_curve),
            )
            if cross_validation is None:
                cv_span["enabled"] = False
            else:
                cv_span["enabled"] = True
                cv_span["mode"] = cross_validation.mode.value
                cv_span["folds"] = len(cross_validation.folds)
                cv_span["leakage_score"] = cross_validation.leakage_score
                cv_span["bias_flag"] = bool(cross_validation.bias_flag)

        with trace_validation_span("bias_adjustment", run_hash=run_hash) as bias_span:
            bias_adjustment = _run_bias_adjustments(
                run_hash=run_hash,
                equity_curve=equity_curve,
                runtime_config=runtime_config,
                cross_validation=cross_validation,
                observed_sharpe=_extract_observed_sharpe(summary, equity_curve),
                trades=trades_df,
            )
            if bias_adjustment is None:
                bias_span["enabled"] = False
            else:
                bias_span["enabled"] = True
                bias_span["bias_flag"] = bool(bias_adjustment.bias_flag)
                bias_span["status"] = bias_adjustment.status
                bias_span["assumed_trials"] = int(bias_adjustment.assumed_trials)

        with trace_validation_span(
            "execution_realism", run_hash=run_hash
        ) as realism_span:
            realism = _run_execution_realism(
                run_hash=run_hash,
                fills=fills_df,
                bars=bars,
                run_config=run_config,
                runtime_config=runtime_config,
                seed_bundle=seed_bundle,
            )
            if realism is None:
                realism_span["enabled"] = False
            else:
                realism_span["enabled"] = True
                realism_span["status"] = realism.status
                realism_span["warnings"] = len(realism.warnings)
                realism_span["guidance"] = len(realism.guidance)

        aggregator = ValidationAggregator(
            significance_threshold=runtime_config.significance_threshold,
            leakage_threshold=runtime_config.leakage_threshold,
        )
        with trace_validation_span("aggregate", run_hash=run_hash) as aggregate_span:
            aggregate = aggregator.aggregate(
                permutations=permutation_results,
                bias_adjustment=bias_adjustment,
                cross_validation=cross_validation,
                realism=realism,
            )
            aggregate_span["status"] = aggregate.validation_significance
            aggregate_span["failed_checks"] = len(aggregate.failed_checks)
            aggregate_span["caution_checks"] = len(aggregate.caution_checks)

        results = ValidationResults(
            segments=segments,
            permutation=permutation_results,
            bias_adjustment=bias_adjustment,
            cross_validation=cross_validation,
            execution_realism=realism,
            aggregate=aggregate,
        )

        total_span["modules_enabled"] = len(runtime_config.modules)
        total_span["significance_status"] = aggregate.validation_significance
        total_span["failed_checks"] = len(aggregate.failed_checks)
        total_span["caution_checks"] = len(aggregate.caution_checks)
        total_span["permutation_segments"] = len(results.segments)
        if results.execution_realism is not None:
            total_span["execution_realism_status"] = results.execution_realism.status

        return results


def _run_permutation_segments(
    *,
    run_hash: str,
    bars: pd.DataFrame,
    run_config: Any,
    seed_bundle: ValidationSeedBundle,
    modules: Sequence[str],
) -> tuple[PermutationSegmentResult, ...]:
    if "permutation" not in modules:
        return tuple()

    engine = PermutationEngine(
        bars=bars,
        run_config=run_config,
        seed_bundle=seed_bundle,
    )
    segment_ids = ["in_sample"]
    if getattr(run_config, "walk_forward", None) is not None:
        segment_ids.append("walk_forward")

    segment_results: list[PermutationSegmentResult] = []
    for segment_id in segment_ids:
        result = engine.execute_segment(segment_id)
        segment_results.append(result)
    return tuple(segment_results)


def _run_cross_validation(
    *,
    run_hash: str,
    bars: pd.DataFrame,
    run_config: Any,
    seed_bundle: ValidationSeedBundle,
    runtime_config: ValidationRuntimeConfig,
    observed_sharpe: float,
) -> CrossValidationSummary | None:
    if not {"purged_kfold", "cpcv"} & set(runtime_config.modules):
        return None

    scheduler = CrossValidationScheduler(
        bars=bars,
        run_config=run_config,
        seed_bundle=seed_bundle,
    )
    folds = _resolve_fold_count(run_config)
    mode = _resolve_cross_validation_mode(runtime_config.modules)
    max_combinations = _resolve_max_combinations(run_config)
    summary = scheduler.build(
        mode=mode,
        folds=folds,
        max_combinations=max_combinations,
        observed_sharpe=observed_sharpe,
        leakage_threshold=runtime_config.leakage_threshold,
    )
    return replace(summary, run_hash=run_hash)


def _run_bias_adjustments(
    *,
    run_hash: str,
    equity_curve: pd.DataFrame,
    runtime_config: ValidationRuntimeConfig,
    cross_validation: CrossValidationSummary | None,
    observed_sharpe: float,
    trades: pd.DataFrame,
) -> SharpeBiasAdjustment | None:
    if not {"dsr", "psr"} & set(runtime_config.modules):
        return None

    returns = _equity_returns(equity_curve)
    if returns.empty:
        return None

    sample_size = int(len(returns))
    skewness = float(returns.skew()) if len(returns) > 2 else 0.0
    if len(returns) > 3:
        try:
            kurtosis_value = returns.kurtosis(fisher=False)
        except TypeError:
            kurtosis_value = returns.kurtosis()
        kurtosis = float(kurtosis_value)
    else:
        kurtosis = 3.0
    assumed_trials = max(runtime_config.permutation_count, 1)
    trials_from_trades = max(int(len(trades)), 1)
    assumed_trials = max(assumed_trials, trials_from_trades)
    cscv_adjusted = cross_validation.cscv_adjusted_sharpe if cross_validation else None

    calculator = BiasAdjustmentsCalculator()
    result = calculator.compute(
        run_hash=run_hash,
        observed_sharpe=observed_sharpe,
        sample_size=sample_size,
        trials=assumed_trials,
        benchmark_sharpe=0.0,
        skewness=skewness,
        kurtosis=kurtosis,
        cscv_adjusted_sharpe=cscv_adjusted,
        absolute_threshold=runtime_config.bias_absolute_threshold,
        relative_threshold=runtime_config.bias_relative_threshold,
        extra_metadata={
            "sample_size": sample_size,
            "returns_source": "equity_curve",
            "trades_observed": int(len(trades)),
        },
    )
    if cscv_adjusted is not None:
        result = result.with_bias_evaluation(
            absolute_threshold=runtime_config.bias_absolute_threshold,
            relative_threshold=runtime_config.bias_relative_threshold,
        )
    return result


def _run_execution_realism(
    *,
    run_hash: str,
    fills: pd.DataFrame,
    bars: pd.DataFrame,
    run_config: Any,
    runtime_config: ValidationRuntimeConfig,
    seed_bundle: ValidationSeedBundle,
) -> ExecutionRealismReport | None:
    if "realism" not in runtime_config.modules:
        return None

    analyzer = ExecutionRealismAnalyzer(seed=seed_bundle.realism)
    fills_df = fills.copy() if isinstance(fills, pd.DataFrame) else pd.DataFrame()
    if fills_df.empty:
        fills_df = pd.DataFrame(columns=["timestamp", "side", "qty", "price", "adv"])
    else:
        fills_df = fills_df.copy()
    if "timestamp" in fills_df.columns and not np.issubdtype(
        fills_df["timestamp"].dtype, np.datetime64
    ):
        fills_df["timestamp"] = pd.to_datetime(
            fills_df["timestamp"], unit="ms", errors="ignore"
        )
    if "quantity" not in fills_df.columns and "qty" in fills_df.columns:
        fills_df["quantity"] = fills_df["qty"].astype(float)
    if "adv" not in fills_df.columns:
        fills_df["adv"] = np.nan
    if fills_df["adv"].isna().all():
        volume_series = bars.get("volume") if isinstance(bars, pd.DataFrame) else None
        if volume_series is not None and not getattr(volume_series, "empty", True):
            derived_adv = float(pd.Series(volume_series).tail(20).mean())
            if not np.isnan(derived_adv) and derived_adv > 0:
                fills_df.loc[:, "adv"] = derived_adv
    if "symbol" not in fills_df.columns:
        fills_df["symbol"] = getattr(run_config, "symbol", "")

    budget_bps = _resolve_budget_bps(run_config)
    capacity_limit = max(float(runtime_config.realism_capacity_bps_limit), 0.0)
    strategy_costs_applied = bool(
        getattr(run_config.execution, "costs_included", False)
    )

    report = analyzer.evaluate(
        fills=fills_df,
        run_config=run_config,
        bars=bars,
        budget_bps=budget_bps,
        capacity_limit=capacity_limit,
        strategy_costs_applied=strategy_costs_applied,
    )
    return replace(report, run_hash=run_hash)


def _resolve_fold_count(run_config: Any) -> int:
    wf = getattr(run_config, "walk_forward", None)
    if wf is None:
        return 4
    segment = getattr(wf, "segment", None)
    if segment is not None:
        train_bars = getattr(segment, "train_bars", None)
        test_bars = getattr(segment, "test_bars", None)
        if isinstance(train_bars, int) and isinstance(test_bars, int) and test_bars > 0:
            from math import ceil

            folds_estimate = ceil((train_bars + test_bars) / test_bars)
            return max(int(folds_estimate), 2)
    return 6 if getattr(wf, "optimization", None) else 4


def _resolve_cross_validation_mode(modules: Sequence[str]) -> str:
    return "cpcv" if "cpcv" in modules else "purged_kfold"


def _resolve_max_combinations(run_config: Any) -> int | None:
    wf = getattr(run_config, "walk_forward", None)
    if wf is None:
        return None
    optimization = getattr(wf, "optimization", None)
    if optimization is None:
        return None
    grid = getattr(optimization, "param_grid", None)
    if not isinstance(grid, Mapping):
        return None
    total = 1
    for values in grid.values():
        if not isinstance(values, Sequence) or not values:
            continue
        total *= len(values)
    return max(int(total), 1)


def _extract_observed_sharpe(
    summary: Mapping[str, Any], equity_curve: pd.DataFrame
) -> float:
    metrics = summary.get("metrics") if isinstance(summary, Mapping) else None
    if isinstance(metrics, Mapping) and "sharpe" in metrics:
        try:
            return float(metrics.get("sharpe", 0.0))
        except (TypeError, ValueError):
            pass
    returns = _equity_returns(equity_curve)
    if returns.empty:
        return 0.0
    return _safe_sharpe(returns)


def _equity_returns(equity_curve: pd.DataFrame) -> pd.Series:
    if not isinstance(equity_curve, pd.DataFrame) or equity_curve.empty:
        return pd.Series(dtype=float)
    column = "return" if "return" in equity_curve.columns else None
    if column is None and "equity" in equity_curve.columns:
        equity = equity_curve["equity"].astype(float)
        returns = equity.pct_change().dropna()
        return returns
    if column is None:
        return pd.Series(dtype=float)
    return equity_curve[column].astype(float)


def _safe_sharpe(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    mean = returns.mean()
    std = returns.std(ddof=0)
    if std == 0:
        return 0.0
    return float(mean / std)


def _resolve_budget_bps(run_config: Any) -> float:
    execution = getattr(run_config, "execution", None)
    if execution is None:
        return 50.0
    slippage = float(getattr(execution, "slippage_bps", 0.0) or 0.0)
    fee = float(getattr(execution, "fee_bps", 0.0) or 0.0)
    borrow = float(getattr(execution, "borrow_cost_bps", 0.0) or 0.0)
    return slippage + fee + borrow


__all__ = [
    "ValidationRuntimeConfig",
    "ValidationResults",
    "execute_validation_modules",
]
