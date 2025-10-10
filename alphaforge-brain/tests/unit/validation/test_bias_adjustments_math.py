from __future__ import annotations

from importlib import import_module

import pytest

xfail_bias_adjustments = pytest.mark.xfail(
    reason="Bias adjustments calculator not implemented",
    strict=False,
)

try:  # pragma: no cover - module scheduled for future implementation
    _module = import_module("src.services.validation.bias_adjustments")
except ImportError as exc:  # pragma: no cover - exercised via xfail
    BiasAdjustmentsCalculator = None  # type: ignore[assignment]
    SharpeBiasAdjustment = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:  # pragma: no cover - future success path
    BiasAdjustmentsCalculator = getattr(_module, "BiasAdjustmentsCalculator", None)
    SharpeBiasAdjustment = getattr(_module, "SharpeBiasAdjustment", None)
    if BiasAdjustmentsCalculator is None or SharpeBiasAdjustment is None:
        _IMPORT_ERROR = ImportError("Bias adjustments exports missing")
    else:
        _IMPORT_ERROR = None


@xfail_bias_adjustments
def test_deflated_and_probabilistic_sharpe_match_reference_formula() -> None:
    if BiasAdjustmentsCalculator is None:
        pytest.xfail(f"bias adjustments module unavailable: {_IMPORT_ERROR}")

    calculator = BiasAdjustmentsCalculator()
    result = calculator.compute(
        observed_sharpe=1.95,
        sample_size=756,
        skewness=-0.3,
        kurtosis=3.7,
        trials=120,
        benchmark_sharpe=0.5,
    )

    assert isinstance(result, SharpeBiasAdjustment)
    assert result.observed_sharpe == pytest.approx(1.95, rel=1e-9)
    assert result.deflated_sharpe == pytest.approx(1.62, rel=1e-2)
    assert result.probabilistic_sharpe == pytest.approx(0.987, rel=1e-3)
    assert result.assumed_trials == 120
    assert result.benchmark_sharpe == pytest.approx(0.5, rel=1e-9)
    assert result.status == "pass"


@xfail_bias_adjustments
def test_bias_flag_triggers_on_threshold_breach() -> None:
    if BiasAdjustmentsCalculator is None:
        pytest.xfail(f"bias adjustments module unavailable: {_IMPORT_ERROR}")

    calculator = BiasAdjustmentsCalculator()
    adjustment = calculator.compute(
        observed_sharpe=1.20,
        sample_size=504,
        skewness=0.1,
        kurtosis=3.2,
        trials=80,
        benchmark_sharpe=0.25,
        cscv_adjusted_sharpe=0.85,
    )

    assert adjustment.deflated_sharpe < adjustment.observed_sharpe
    assert adjustment.cscv_adjusted_sharpe == pytest.approx(0.85, rel=1e-9)
    assert adjustment.bias_flag is True
    assert adjustment.status in {"caution", "fail"}

    repeat = calculator.compute(
        observed_sharpe=1.20,
        sample_size=504,
        skewness=0.1,
        kurtosis=3.2,
        trials=80,
        benchmark_sharpe=0.25,
        cscv_adjusted_sharpe=0.85,
    )
    assert repeat == adjustment
