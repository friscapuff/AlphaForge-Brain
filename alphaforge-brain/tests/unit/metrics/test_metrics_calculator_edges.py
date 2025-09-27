import pandas as pd
from domain.metrics.calculator import build_equity_curve, compute_metrics


def test_build_equity_curve_empty():
    empty = pd.DataFrame(columns=["timestamp", "equity"])[:0]
    out = build_equity_curve(empty)
    assert list(out.columns) == ["timestamp", "equity", "return"]
    assert out.empty


def test_compute_metrics_empty_equity():
    trades = pd.DataFrame()
    out = compute_metrics(trades, pd.DataFrame(columns=["timestamp", "equity"])[:0])
    assert out["total_return"] == 0.0
    assert out["sharpe"] == 0.0
    assert out["max_drawdown"] == 0.0


def test_compute_metrics_single_point():
    eq = pd.DataFrame(
        [
            {"timestamp": 1, "equity": 100.0},
            {"timestamp": 2, "equity": 100.0},
        ]
    )
    eq2 = build_equity_curve(eq)
    m = compute_metrics(pd.DataFrame(), eq2)
    assert m["total_return"] == 0.0
    assert m["sharpe"] == 0.0  # zero variance path


def test_compute_metrics_gain_and_drawdown():
    eq = pd.DataFrame(
        [
            {"timestamp": 1, "equity": 100.0},
            {"timestamp": 2, "equity": 110.0},
            {"timestamp": 3, "equity": 105.0},
            {"timestamp": 4, "equity": 120.0},
        ]
    )
    curve = build_equity_curve(eq)
    m = compute_metrics(pd.DataFrame(), curve)
    # floating point guard
    assert round(m["total_return"], 4) == 0.20  # (120/100 -1)
    assert m["max_drawdown"] <= 0  # negative value


def test_compute_metrics_include_anomalies_populates_defaults(monkeypatch):
    class DummyMD:
        anomaly_counters = {"duplicates_dropped": 2}

    # monkeypatch get_dataset_metadata symbol in module
    import domain.metrics.calculator as calc

    monkeypatch.setattr(calc, "get_dataset_metadata", lambda: DummyMD())
    eq = pd.DataFrame(
        [
            {"timestamp": 1, "equity": 100.0},
            {"timestamp": 2, "equity": 101.0},
        ]
    )
    curve = build_equity_curve(eq)
    m = compute_metrics(pd.DataFrame(), curve, include_anomalies=True)
    expected_keys = {
        "duplicates_dropped",
        "rows_dropped_missing",
        "zero_volume_rows",
        "future_rows_dropped",
        "unexpected_gaps",
        "expected_closures",
    }
    assert set(m["anomaly_counters"].keys()) == expected_keys
