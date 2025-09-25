from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd
from _pytest.monkeypatch import MonkeyPatch
from domain.metrics.calculator import build_equity_curve, compute_metrics


def test_metrics_include_anomalies_flag(
    monkeypatch: MonkeyPatch,
) -> None:  # monkeypatch fixture from pytest
    # Create minimal equity curve
    ts = pd.date_range("2024-01-01", periods=3, freq="1D")
    eq = pd.DataFrame({"timestamp": ts, "equity": [100.0, 101.0, 101.5]})
    curve = build_equity_curve(eq)

    class DummyMeta:
        symbol: ClassVar[str] = "NVDA"
        timeframe: ClassVar[str] = "1d"
        data_hash: ClassVar[str] = "dummy"
        calendar_id: ClassVar[str] = "NASDAQ"
        row_count_raw: ClassVar[int] = 10
        row_count_canonical: ClassVar[int] = 10
        first_ts: ClassVar[int] = 0
        last_ts: ClassVar[int] = 0
        anomaly_counters: ClassVar[dict[str, int]] = {
            "duplicates_dropped": 1,
            "unexpected_gaps": 0,
        }

    def fake_get_dataset_metadata() -> Any:
        return DummyMeta()

    # Patch metadata fetch to avoid real dataset dependency in test env
    monkeypatch.setenv("ALPHAFORGE_TEST_MODE", "1")
    monkeypatch.setitem(globals(), "_patched", True)
    import domain.metrics.calculator as calc_mod

    monkeypatch.setattr(
        calc_mod, "get_dataset_metadata", fake_get_dataset_metadata, raising=False
    )

    metrics = compute_metrics(pd.DataFrame(), curve, include_anomalies=True)
    assert "anomaly_counters" in metrics, "anomaly_counters not surfaced"
    assert metrics["anomaly_counters"]["duplicates_dropped"] == 1
