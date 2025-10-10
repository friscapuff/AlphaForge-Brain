from __future__ import annotations

from datetime import timedelta
from importlib import import_module

import pytest

from tests.fixtures.validation import validation_fixtures

xfail_cross_validation = pytest.mark.xfail(
    reason="Cross-validation scheduler not implemented",
    strict=False,
)

try:  # pragma: no cover - scheduler arriving in later phase
    _module = import_module("src.services.validation.cpcv_scheduler")
except ImportError as exc:  # pragma: no cover - exercised via xfail
    CrossValidationScheduler = None  # type: ignore[assignment]
    CrossValidationSummary = None  # type: ignore[assignment]
    CrossValidationFold = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:  # pragma: no cover - future success path
    CrossValidationScheduler = getattr(_module, "CrossValidationScheduler", None)
    CrossValidationSummary = getattr(_module, "CrossValidationSummary", None)
    CrossValidationFold = getattr(_module, "CrossValidationFold", None)
    if any(
        obj is None
        for obj in (
            CrossValidationScheduler,
            CrossValidationSummary,
            CrossValidationFold,
        )
    ):
        _IMPORT_ERROR = ImportError("Cross-validation scheduler exports missing")
    else:
        _IMPORT_ERROR = None


@xfail_cross_validation
def test_purged_kfold_uses_time_based_embargo_default() -> None:
    if CrossValidationScheduler is None:
        pytest.xfail(f"cross-validation scheduler unavailable: {_IMPORT_ERROR}")

    fixture = validation_fixtures(permutation_trials=32)
    scheduler = CrossValidationScheduler(
        bars=fixture.bars,
        run_config=fixture.run_config,
        seed_bundle=fixture.seeds,
    )

    summary = scheduler.build(mode="purged_kfold", folds=4)

    assert isinstance(summary, CrossValidationSummary)
    assert summary.mode == "purged_kfold"
    assert summary.seed_root == fixture.seeds.cross_validation
    assert summary.leakage_score is not None

    for fold in summary.folds:
        assert isinstance(fold, CrossValidationFold)
        assert fold.purge_span == timedelta(days=30)
        assert fold.train_start < fold.train_end
        assert fold.test_start < fold.test_end


@xfail_cross_validation
def test_cpcv_fallback_deterministic_and_bias_flag_threshold() -> None:
    if CrossValidationScheduler is None:
        pytest.xfail(f"cross-validation scheduler unavailable: {_IMPORT_ERROR}")

    fixture = validation_fixtures(permutation_trials=48)
    scheduler = CrossValidationScheduler(
        bars=fixture.bars,
        run_config=fixture.run_config,
        seed_bundle=fixture.seeds,
    )

    summary = scheduler.build(
        mode="auto", folds=6, max_combinations=10, observed_sharpe=1.10
    )

    assert summary.mode == "cpcv"
    assert summary.seed_root == fixture.seeds.cross_validation
    fold_ids = [fold.fold_id for fold in summary.folds]
    assert fold_ids == sorted(fold_ids)

    assert 0.0 <= summary.leakage_score <= 1.0

    # Bias flag should trigger when CSCV-adjusted Sharpe breaches both absolute and relative thresholds
    assert summary.bias_flag is True
    assert summary.cscv_adjusted_sharpe <= 0.85

    repeat = scheduler.build(
        mode="auto", folds=6, max_combinations=10, observed_sharpe=1.10
    )
    assert repeat.folds == summary.folds
    assert repeat.cscv_adjusted_sharpe == pytest.approx(
        summary.cscv_adjusted_sharpe, rel=1e-9
    )
