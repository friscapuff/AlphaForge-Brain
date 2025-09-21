"""T029: Deterministic equity curve & metrics

Two identical equity/position inputs must yield identical equity curve (bitwise equality)
and identical metrics dicts. Serves as a fast determinism sentinel independent of full
orchestrator runs.
"""

from __future__ import annotations

import pandas as pd

from domain.metrics.calculator import build_equity_curve, compute_metrics


def test_equity_curve_and_metrics_deterministic() -> None:
    ts = pd.date_range("2024-01-01", periods=5, freq="1D")
    eq_vals = [100.0, 100.5, 101.0, 100.8, 101.3]
    positions = pd.DataFrame({"timestamp": ts, "equity": eq_vals})

    curve1 = build_equity_curve(positions)
    curve2 = build_equity_curve(positions.copy())
    # DataFrame exact equality (same columns order and values)
    pd.testing.assert_frame_equal(curve1, curve2)

    metrics1 = compute_metrics(pd.DataFrame(), curve1)
    metrics2 = compute_metrics(pd.DataFrame(), curve2)
    assert metrics1 == metrics2, "Metrics differ for identical equity input"
