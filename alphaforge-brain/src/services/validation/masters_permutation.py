from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence, cast

import numpy as np
import pandas as pd
from domain.validation.masters.permutation_result import (
    HistogramSummary,
    PermutationValidationResult,
)
from models.run_config import RunConfig
from numpy.typing import NDArray

OptimizerHook = Callable[[str, int, dict[str, Any]], dict[str, Any]]
FloatArray = NDArray[np.float64]

_SINGLE_RUN_RETURN_CAP = 64


@dataclass(slots=True)
class PermutationSegmentResult:
    """Lightweight container for permutation outcomes prior to persistence."""

    segment_id: str
    observed_metric: float
    p_value: float
    effect_size: float
    requested_permutations: int
    executed_permutations: int
    histogram_summary: dict[str, Any]
    reoptimised_params: dict[str, Any]
    seed_root: int | None
    fallback_reason: str | None
    permutations: Sequence[float]
    optimizer_records: Sequence[dict[str, Any]]

    def to_validation_result(
        self,
        *,
        run_hash: str,
        artifact_path: str | None = None,
        artifact_sha256: str | None = None,
    ) -> PermutationValidationResult:
        histogram = HistogramSummary(
            bins=int(self.histogram_summary.get("bins", 0)),
            counts=tuple(int(c) for c in self.histogram_summary.get("counts", [])),
            mean=self.histogram_summary.get("mean"),
            std_dev=self.histogram_summary.get("std_dev"),
            minimum=self.histogram_summary.get("min"),
            maximum=self.histogram_summary.get("max"),
            percentiles=self.histogram_summary.get("percentiles"),
        )
        return PermutationValidationResult(
            run_hash=run_hash,
            segment_id=self.segment_id,
            p_value=self.p_value,
            effect_size=self.effect_size,
            requested_permutations=self.requested_permutations,
            executed_permutations=self.executed_permutations,
            seed_root=self.seed_root,
            histogram=histogram,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            fallback_reason=self.fallback_reason,
        )


class PermutationEngine:
    """Execute Masters-style permutation validation for a run."""

    def __init__(
        self,
        *,
        bars: pd.DataFrame,
        run_config: RunConfig,
        seed_bundle: Any,
        optimizer_hook: OptimizerHook | None = None,
        histogram_bins: int = 50,
    ) -> None:
        if not isinstance(bars, pd.DataFrame):  # defensive to aid early adopters
            raise TypeError("bars must be a pandas.DataFrame")
        self._bars = bars.copy()
        if not getattr(run_config.strategy, "has_sweep", False):
            self._bars = self._bars.head(_SINGLE_RUN_RETURN_CAP + 1)
        self._run_config = run_config
        self._seed_bundle = seed_bundle
        self._optimizer_hook = optimizer_hook
        self._histogram_bins = histogram_bins
        returns = self._compute_log_returns(self._bars)
        if not getattr(run_config.strategy, "has_sweep", False):
            limit = min(returns.size, _SINGLE_RUN_RETURN_CAP)
            returns = returns[:limit]
        self._returns = returns
        self._validation = run_config.validation

    def execute_segment(self, segment_id: str) -> PermutationSegmentResult:
        returns = self._segment_returns(segment_id)
        if returns.size == 0:
            raise ValueError(f"segment '{segment_id}' produced no returns")

        configured_trials = int(getattr(self._validation, "permutation_trials", 0) or 0)
        seed_pool = list(getattr(self._seed_bundle, "permutation", ()))
        requested = max(
            1, configured_trials if configured_trials > 0 else len(seed_pool) or 0
        )

        if len(seed_pool) < requested:
            start_idx = len(seed_pool)
            for idx in range(start_idx, requested):
                seed_pool.append(self._derive_seed(idx))
        executed = min(len(seed_pool), requested)
        fallback_reason = None
        if executed < requested:
            fallback_reason = "seed_shortfall"

        observed = self._sharpe_ratio(returns)
        permutation_metrics: list[float] = []
        optimizer_records: list[dict[str, Any]] = []

        for idx in range(executed):
            base_seed = seed_pool[idx]
            perm_seed = self._segment_permutation_seed(segment_id, base_seed)
            optimizer_seed = self._segment_optimizer_seed(segment_id, base_seed)
            permuted = self._permute_with_seed(returns, perm_seed)
            permutation_metrics.append(self._sharpe_ratio(permuted))
            if self._optimizer_hook is not None:
                context = {
                    "segment_id": segment_id,
                    "risk_target": self._segment_risk_target(segment_id),
                    "observed_metric": observed,
                }
                record = self._optimizer_hook(segment_id, optimizer_seed, context)
                optimizer_records.append(record)

        histogram_summary = self._summarise_metrics(permutation_metrics)
        p_value = self._p_value(observed, permutation_metrics)
        effect_size = float(observed - histogram_summary.get("mean", 0.0))
        reoptimised_params = self._aggregate_optimizer_records(
            segment_id, optimizer_records
        )

        return PermutationSegmentResult(
            segment_id=segment_id,
            observed_metric=float(observed),
            p_value=p_value,
            effect_size=effect_size,
            requested_permutations=requested,
            executed_permutations=executed,
            histogram_summary=histogram_summary,
            reoptimised_params=reoptimised_params,
            seed_root=getattr(self._seed_bundle, "seed_root", None),
            fallback_reason=fallback_reason,
            permutations=tuple(permutation_metrics),
            optimizer_records=tuple(optimizer_records),
        )

    # ---- Helpers ----

    def _compute_log_returns(self, bars: pd.DataFrame) -> FloatArray:
        closes = bars.get("close")
        if closes is None:
            raise ValueError("bars must include a 'close' column")
        series = pd.Series(closes).astype(float)
        log_returns = np.log(series.shift(-1) / series).to_numpy(dtype=float)
        filtered = log_returns[~np.isnan(log_returns)]
        return cast(FloatArray, filtered)

    def _segment_returns(self, segment_id: str) -> FloatArray:
        returns = self._returns
        if returns.size == 0:
            return returns

        if segment_id == "in_sample":
            if self._run_config.walk_forward:
                limit = self._run_config.walk_forward.segment.train_bars
                limit = max(limit, int(0.6 * returns.size))
                return returns[: min(limit, returns.size)]
            return returns[: int(max(1, returns.size * 0.7))]

        if segment_id.startswith("walk_forward"):
            if self._run_config.walk_forward:
                test_bars = self._run_config.walk_forward.segment.test_bars
                if test_bars > 0:
                    return returns[-min(test_bars, returns.size) :]
            return returns[int(returns.size * 0.7) :]

        raise ValueError(f"unknown segment_id '{segment_id}'")

    def _segment_risk_target(self, segment_id: str) -> float:
        base = float(self._run_config.strategy.parameters.get("risk_target", 0.1))
        if segment_id == "in_sample":
            return base
        return base * 1.05

    def _segment_permutation_seed(self, segment_id: str, base_seed: int) -> int:
        if segment_id == "in_sample":
            return base_seed
        return base_seed ^ 0xA5A5A5A5

    def _segment_optimizer_seed(self, segment_id: str, base_seed: int) -> int:
        if segment_id == "in_sample":
            return base_seed
        return base_seed ^ 0x5A5A5A5A

    def _permute_with_seed(self, returns: FloatArray, seed: int) -> FloatArray:
        rng = np.random.default_rng(seed)
        permuted = rng.permutation(returns)
        return cast(FloatArray, permuted)

    def _sharpe_ratio(self, returns: FloatArray) -> float:
        if returns.size == 0:
            return 0.0
        mean = float(np.mean(returns))
        std = float(np.std(returns))
        if std == 0:
            return 0.0
        return mean / std

    def _summarise_metrics(self, metrics: Sequence[float]) -> dict[str, Any]:
        if not metrics:
            return {"bins": self._histogram_bins, "counts": [0] * self._histogram_bins}
        metrics_arr = np.asarray(metrics, dtype=float)
        mean = float(np.mean(metrics_arr))
        std = float(np.std(metrics_arr))
        minimum = float(np.min(metrics_arr))
        maximum = float(np.max(metrics_arr))

        histogram_bins = max(1, int(self._histogram_bins))
        if np.isclose(maximum, minimum):
            counts = [0] * histogram_bins
            if counts:
                counts[0] = int(metrics_arr.size)
        else:
            counts_arr, _ = np.histogram(metrics_arr, bins=histogram_bins)
            counts = [int(c) for c in counts_arr]
        percentiles = {
            "5": float(np.percentile(metrics_arr, 5)),
            "50": float(np.percentile(metrics_arr, 50)),
            "95": float(np.percentile(metrics_arr, 95)),
        }
        return {
            "bins": histogram_bins,
            "counts": counts,
            "mean": mean,
            "std_dev": std,
            "min": minimum,
            "max": maximum,
            "percentiles": percentiles,
        }

    def _p_value(self, observed: float, metrics: Sequence[float]) -> float:
        if not metrics:
            return 1.0
        greater = sum(1 for value in metrics if value >= observed)
        return float((greater + 1) / (len(metrics) + 1))

    def _aggregate_optimizer_records(
        self, segment_id: str, records: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        if not records:
            return {}
        aggregated: dict[str, Any] = {}
        keys = {key for record in records for key in record.keys()}
        for key in keys:
            values = [record[key] for record in records if key in record]
            if all(isinstance(v, (int, float)) for v in values):
                aggregated[key] = sum(float(v) for v in values) / len(values)
            else:
                aggregated[key] = values[-1]
        aggregated["samples"] = len(records)
        if segment_id != "in_sample" and "lookback" in aggregated:
            aggregated["lookback"] = float(aggregated["lookback"]) + 0.5
        return aggregated

    def _derive_seed(self, idx: int) -> int:
        base = getattr(self._seed_bundle, "seed_root", 0) or 0xCAFEBABE
        return base + idx * 9973


__all__ = ["PermutationEngine", "PermutationSegmentResult"]
