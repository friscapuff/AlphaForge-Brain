from __future__ import annotations

from dataclasses import dataclass
from math import inf, log
from statistics import NormalDist
from typing import Any, Mapping

from domain.validation.masters.bias_adjustment import (
    BIAS_ABSOLUTE_THRESHOLD_DEFAULT,
    BIAS_RELATIVE_THRESHOLD_DEFAULT,
    SharpeBiasAdjustment,
)

_EULER_MASCHERONI = 0.5772156649015329


@dataclass(slots=True)
class BiasAdjustmentInputs:
    observed_sharpe: float
    sample_size: int
    trials: int
    benchmark_sharpe: float
    skewness: float = 0.0
    kurtosis: float = 3.0
    cscv_adjusted_sharpe: float | None = None
    run_hash: str = ""
    absolute_threshold: float = BIAS_ABSOLUTE_THRESHOLD_DEFAULT
    relative_threshold: float = BIAS_RELATIVE_THRESHOLD_DEFAULT
    extra_metadata: Mapping[str, Any] | None = None


class BiasAdjustmentsCalculator:
    """Compute Deflated & Probabilistic Sharpe diagnostics for Masters validation."""

    def compute(self, **kwargs: Any) -> SharpeBiasAdjustment:
        inputs = self._coerce_inputs(kwargs)
        variance_term = self._variance_term(
            inputs.observed_sharpe, inputs.skewness, inputs.kurtosis
        )
        sigma_sr = (variance_term / max(inputs.sample_size - 1, 1)) ** 0.5

        effective_trials = max(float(inputs.trials), 1.0)
        effective_observations = self._effective_observations(
            inputs.sample_size, effective_trials
        )
        sigma_adjusted = (variance_term / max(effective_observations - 1, 1.0)) ** 0.5
        psr = NormalDist().cdf(
            self._safe_divide(
                inputs.observed_sharpe - inputs.benchmark_sharpe, sigma_adjusted
            )
        )

        penalty = sigma_sr * max(log(effective_trials) - 0.5 * _EULER_MASCHERONI, 0.0)
        deflated = max(inputs.observed_sharpe - penalty, -inf)

        adjustment = SharpeBiasAdjustment(
            run_hash=inputs.run_hash,
            observed_sharpe=inputs.observed_sharpe,
            deflated_sharpe=deflated,
            probabilistic_sharpe=min(max(psr, 0.0), 1.0),
            assumed_trials=int(round(effective_trials)),
            benchmark_sharpe=inputs.benchmark_sharpe,
            skewness=inputs.skewness,
            kurtosis=inputs.kurtosis,
            cscv_adjusted_sharpe=inputs.cscv_adjusted_sharpe,
            extra_metadata=dict(inputs.extra_metadata or {}),
        )
        if inputs.cscv_adjusted_sharpe is not None:
            adjustment = adjustment.with_bias_evaluation(
                absolute_threshold=inputs.absolute_threshold,
                relative_threshold=inputs.relative_threshold,
            )
        return adjustment

    @staticmethod
    def _coerce_inputs(options: Mapping[str, Any]) -> BiasAdjustmentInputs:
        try:
            return BiasAdjustmentInputs(**options)
        except TypeError as exc:  # pragma: no cover - defensive guard
            raise TypeError(
                f"Unsupported bias adjustment arguments: {options!r}"
            ) from exc

    @staticmethod
    def _variance_term(observed: float, skewness: float, kurtosis: float) -> float:
        return 1 - skewness * observed + ((kurtosis - 1.0) / 4.0) * observed**2

    @staticmethod
    def _effective_observations(sample_size: int, trials: float) -> float:
        if sample_size <= 1:
            return 2.0
        base = log(max(sample_size, 2)) + log(max(trials, 1.0)) - _EULER_MASCHERONI
        return max(base, 2.0)

    @staticmethod
    def _safe_divide(numerator: float, denominator: float) -> float:
        if denominator == 0:
            return inf if numerator > 0 else -inf if numerator < 0 else 0.0
        return numerator / denominator


__all__ = ["BiasAdjustmentsCalculator", "BiasAdjustmentInputs", "SharpeBiasAdjustment"]
