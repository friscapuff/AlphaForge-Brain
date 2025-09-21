import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import RunConfig, IndicatorSpec, StrategySpec, RiskSpec, ExecutionSpec, ValidationSpec


def _config():
    return RunConfig(
        symbol="TEST",
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        indicators=[IndicatorSpec(name="dual_sma", params={"fast":5, "slow":12})],
        strategy=StrategySpec(name="dual_sma", params={"short_window":5, "long_window":12}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction":0.1}),
        execution=ExecutionSpec(slippage_bps=1),
        validation=ValidationSpec(),
    )


def test_get_run_with_anomalies(monkeypatch, tmp_path: Path):
    app = create_app()
    client = TestClient(app)

    # patch dataset metadata to deterministic dummy
    class DummyMeta:
        symbol = "NVDA"
        timeframe = "1d"
        data_hash = "dummyhash"
        calendar_id = "NASDAQ"
        row_count_raw = 100
        row_count_canonical = 95
        first_ts = 0
        last_ts = 0
        anomaly_counters = {"duplicates_dropped":2, "rows_dropped_missing":1}

    def fake_get_dataset_metadata():
        return DummyMeta()

    import domain.data.ingest_nvda as ingest_mod
    monkeypatch.setattr(ingest_mod, "get_dataset_metadata", fake_get_dataset_metadata, raising=False)

    cfg = _config()
    registry = app.state.registry  # type: ignore[attr-defined]
    run_hash, record, created = create_or_get(cfg, registry, seed=cfg.seed)
    assert created is True

    # fetch run with anomalies
    r = client.get(f"/runs/{run_hash}?include_anomalies=true")
    assert r.status_code == 200
    payload = r.json()
    assert payload["run_hash"] == run_hash
    summary = payload.get("summary")
    assert summary and "anomaly_counters" in summary
    assert summary["anomaly_counters"]["duplicates_dropped"] == 2
