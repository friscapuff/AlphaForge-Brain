from __future__ import annotations

from src.services.metrics_hash import equity_curve_hash, metrics_hash


def test_metrics_hash_order_independent() -> None:
    a = {"sharpe": 0.123456789, "total_return": 0.42}
    b = {"total_return": 0.42, "sharpe": 0.123456789}
    assert metrics_hash(a) == metrics_hash(b)


def test_metrics_hash_mutation_changes_hash() -> None:
    base = {"sharpe": 0.5, "total_return": 0.10}
    h0 = metrics_hash(base)
    base["sharpe"] = 0.6
    assert metrics_hash(base) != h0


def test_equity_curve_hash_identical_lists_equal() -> None:
    class Bar:
        def __init__(self, nav: float, drawdown: float):
            self.nav = nav
            self.drawdown = drawdown

    curve1 = [Bar(100 + i, 0.0) for i in range(5)]
    curve2 = [Bar(100 + i, 0.0) for i in range(5)]
    assert equity_curve_hash(curve1) == equity_curve_hash(curve2)


def test_equity_curve_hash_differs_on_change() -> None:
    class Bar:
        def __init__(self, nav: float, drawdown: float):
            self.nav = nav
            self.drawdown = drawdown

    curve = [Bar(100 + i, 0.0) for i in range(5)]
    h0 = equity_curve_hash(curve)
    curve[2].nav += 1.0
    assert equity_curve_hash(curve) != h0
