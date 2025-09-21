import pandas as pd

from domain.metrics.calculator import compute_metrics, build_equity_curve


def test_metrics_include_anomalies_flag(monkeypatch):
    # Create minimal equity curve
    ts = pd.date_range("2024-01-01", periods=3, freq="1D")
    eq = pd.DataFrame({"timestamp": ts, "equity": [100.0, 101.0, 101.5]})
    curve = build_equity_curve(eq)

    class DummyMeta:
        symbol = "NVDA"
        timeframe = "1d"
        data_hash = "dummy"
        calendar_id = "NASDAQ"
        row_count_raw = 10
        row_count_canonical = 10
        first_ts = 0
        last_ts = 0
        anomaly_counters = {"duplicates_dropped": 1, "unexpected_gaps": 0}

    def fake_get_dataset_metadata():
        return DummyMeta()

    # Patch metadata fetch to avoid real dataset dependency in test env
    monkeypatch.setenv("ALPHAFORGE_TEST_MODE", "1")
    monkeypatch.setitem(globals(), "_patched", True)
    import domain.metrics.calculator as calc_mod
    monkeypatch.setattr(calc_mod, "get_dataset_metadata", fake_get_dataset_metadata, raising=False)

    metrics = compute_metrics(pd.DataFrame(), curve, include_anomalies=True)
    assert "anomaly_counters" in metrics, "anomaly_counters not surfaced"
    assert metrics["anomaly_counters"]["duplicates_dropped"] == 1
