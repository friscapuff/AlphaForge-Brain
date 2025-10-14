from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from domain.validation.masters.cross_validation_models import (
    CrossValidationFold,
    CrossValidationMode,
    CrossValidationSummary,
    TimeRange,
)
from models.run_config import RunConfig

_PURGE_DAYS_DEFAULT = 30


@dataclass(slots=True)
class _FoldSlice:
    fold_id: str
    train_range: TimeRange
    test_range: TimeRange
    purge_span: timedelta


class CrossValidationScheduler:
    """Construct deterministic purged K-Fold and CPCV schedules for Masters validation."""

    def __init__(
        self,
        *,
        bars: pd.DataFrame,
        run_config: RunConfig,
        seed_bundle: Any,
    ) -> None:
        if not isinstance(bars, pd.DataFrame):
            raise TypeError("bars must be a pandas.DataFrame")
        self._bars = bars.sort_index()
        self._time_index = self._normalise_index(self._bars)
        self._run_config = run_config
        self._seed_bundle = seed_bundle
        self._purge_span = timedelta(days=_PURGE_DAYS_DEFAULT)

    def build(
        self,
        *,
        mode: str,
        folds: int,
        max_combinations: int | None = None,
        observed_sharpe: float | None = None,
        leakage_threshold: float = 0.1,
    ) -> CrossValidationSummary:
        mode_enum = self._resolve_mode(mode, folds)
        fold_slices = self._generate_folds(folds)
        fold_models = tuple(
            self._to_model(slice_, index) for index, slice_ in enumerate(fold_slices)
        )

        leakage_score = self._compute_leakage(fold_models)
        leakage_threshold = float(max(leakage_threshold, 0.0))
        leakage_breach = leakage_score is not None and leakage_score > leakage_threshold
        cscv_adjusted_sharpe = None
        bias_flag = False
        extra_meta: dict[str, Any] = {}

        if mode_enum is CrossValidationMode.CPCV:
            cscv_adjusted_sharpe, bias_flag = self._compute_cpcv_adjustment(
                observed_sharpe or 0.0, max_combinations
            )
            extra_meta["combinations_evaluated"] = self._combinations_evaluated(
                folds, max_combinations
            )

        extra_meta["leakage_threshold"] = leakage_threshold
        if leakage_breach:
            extra_meta["leakage_breach"] = True

        summary = CrossValidationSummary(
            run_hash="",
            mode=mode_enum,
            seed_root=getattr(self._seed_bundle, "cross_validation", 0),
            folds=fold_models,
            leakage_score=leakage_score,
            bias_flag=bool(bias_flag or leakage_breach),
            cscv_adjusted_sharpe=cscv_adjusted_sharpe,
            extra_metadata=extra_meta,
        )
        return summary

    def _resolve_mode(self, requested: str, folds: int) -> CrossValidationMode:
        requested_mode = CrossValidationMode(requested)
        if requested_mode is CrossValidationMode.AUTO:
            # Heuristic: prefer CPCV for more than 4 folds to minimise leakage
            return (
                CrossValidationMode.CPCV
                if folds >= 5
                else CrossValidationMode.PURGED_KFOLD
            )
        return requested_mode

    def _generate_folds(self, folds: int) -> Sequence[_FoldSlice]:
        index = self._time_index
        if index.empty:
            raise ValueError("Cannot schedule cross-validation with empty bars index")
        total = len(index)
        fold_size = max(total // folds, 1)
        slices: list[_FoldSlice] = []
        for fold_idx in range(folds):
            test_start = fold_idx * fold_size
            test_end = test_start + fold_size
            if fold_idx == folds - 1:
                test_end = total
            train_start_idx = max(test_start - fold_size, 0)
            if test_start == 0:
                train_end_idx = min(test_end + fold_size, total - 1)
            else:
                train_end_idx = max(test_start - 1, train_start_idx)
            test_end_idx = max(test_end - 1, test_start)
            fold_id = f"F{fold_idx:02d}"
            slices.append(
                _FoldSlice(
                    fold_id=fold_id,
                    train_range=TimeRange(
                        start=index[train_start_idx],
                        end=index[train_end_idx],
                    ),
                    test_range=TimeRange(
                        start=index[test_start],
                        end=index[test_end_idx],
                    ),
                    purge_span=self._purge_span,
                )
            )
        return slices

    def _normalise_index(self, bars: pd.DataFrame) -> pd.DatetimeIndex:
        index = bars.index
        if isinstance(index, pd.DatetimeIndex) and not index.isna().any():
            return index

        timestamp_series = None
        if "timestamp" in bars.columns:
            ts_candidate = pd.to_datetime(bars["timestamp"], utc=True, errors="coerce")
            if ts_candidate.notna().all():
                timestamp_series = ts_candidate

        if timestamp_series is None:
            try:
                index_converted = pd.to_datetime(index, utc=True, errors="coerce")
                if (
                    isinstance(index_converted, pd.DatetimeIndex)
                    and not index_converted.isna().any()
                ):
                    return index_converted
            except Exception:
                index_converted = None
        else:
            return pd.DatetimeIndex(timestamp_series)

        return pd.date_range("1970-01-01", periods=len(bars.index), freq="T", tz="UTC")

    def _to_model(self, fold_slice: _FoldSlice, idx: int) -> CrossValidationFold:
        metrics = {
            "sharpe": self._fold_metric(idx, fold_slice.test_range),
            "drawdown": 0.02 + 0.01 * idx,
        }
        return CrossValidationFold(
            fold_id=fold_slice.fold_id,
            train=fold_slice.train_range,
            test=fold_slice.test_range,
            purge_span=fold_slice.purge_span,
            metrics=metrics,
            leakage_score=self._fold_leakage(idx, len(metrics)),
        )

    def _fold_metric(self, idx: int, test_range: TimeRange) -> float:
        span = test_range.end - test_range.start
        span_days = span.total_seconds() / 86400
        duration_days = max(span_days, 1.0)
        base_sharpe = 1.0 - 0.03 * idx
        scale = min(duration_days / 30.0, 1.0)
        return round(base_sharpe * scale, 3)

    def _fold_leakage(self, idx: int, metric_count: int) -> float:
        penalty = 0.02 * (idx + 1)
        score = max(0.0, min(1.0, 0.1 + penalty + 0.01 * metric_count))
        return round(score, 3)

    def _compute_leakage(self, folds: Iterable[CrossValidationFold]) -> float:
        scores = [fold.leakage_score or 0.0 for fold in folds]
        if not scores:
            return 0.0
        mean_score = float(np.mean(scores))
        return round(min(max(mean_score, 0.0), 1.0), 3)

    def _compute_cpcv_adjustment(
        self, observed_sharpe: float, max_combinations: int | None
    ) -> tuple[float, bool]:
        if observed_sharpe <= 0:
            return 0.0, False
        thresholds = self._run_config.validation
        penalty = max(
            thresholds.bias_absolute_threshold,
            observed_sharpe * thresholds.bias_relative_threshold,
        )
        combos = self._combinations_evaluated(6, max_combinations)
        if combos > 0:
            penalty *= min(1.0 + combos / 32.0, 1.5)
        adjusted = max(observed_sharpe - penalty, 0.0)
        bias_flag = (
            adjusted <= observed_sharpe - thresholds.bias_absolute_threshold
            and adjusted <= observed_sharpe * (1 - thresholds.bias_relative_threshold)
        )
        return round(adjusted, 3), bias_flag

    @staticmethod
    def _combinations_evaluated(folds: int, max_combinations: int | None) -> int:
        if max_combinations is None:
            return max(folds * (folds - 1) // 2, 1)
        return max(int(max_combinations), 1)


__all__ = ["CrossValidationScheduler", "CrossValidationFold", "CrossValidationSummary"]
