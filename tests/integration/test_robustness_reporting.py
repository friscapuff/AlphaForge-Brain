"""Robustness Reporting Integration (T016)

Validates composite robustness scoring pipeline (p-value + stability proxy)
using ValidationResult model and robustness_score service. Ensures
deterministic output and monotonic response to improved stability.
"""

from __future__ import annotations

from models.validation_result import ValidationResult
from services.robustness import robustness_score


def test_robustness_reporting() -> None:  # T016
    v1 = ValidationResult(metric_name="sharpe", observed_value=1.2, permutation_distribution=[0.5, 0.6, 0.7, 0.8])
    v2 = ValidationResult(metric_name="returns", observed_value=0.15, permutation_distribution=[0.05, 0.07, 0.09, 0.11])
    score = robustness_score([v1, v2], oos_consistency=0.25)
    assert 0.0 <= score <= 1.0
    # Determinism
    score2 = robustness_score([v1, v2], oos_consistency=0.25)
    assert score == score2
    # Monotonicity: better stability increases composite
    higher = robustness_score([v1, v2], oos_consistency=0.5)
    assert higher >= score

__all__ = ["test_robustness_reporting"]
