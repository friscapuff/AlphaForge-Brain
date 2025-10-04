import pytest
from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in ["AF_ENABLE_EXTENDED_PERCENTILES", "AF_ENABLE_ADVANCED_VALIDATION"]:
        monkeypatch.delenv(k, raising=False)
    yield


# T097 -----------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t097_flag_off_omits_extended_percentiles(monkeypatch):
    monkeypatch.setenv("AF_ENABLE_EXTENDED_PERCENTILES", "0")
    # establish run
    payload = {
        "symbol": "TESTX",
        "date_range": {"start": "2024-06-01", "end": "2024-06-05"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 10000},
    }
    r = client.post("/api/v1/backtests", json=payload)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    mc = client.post(
        f"/api/v1/backtests/{run_id}/montecarlo",
        json={"paths": 30, "extended_percentiles": True},
    )
    assert mc.status_code == 200, mc.text
    body = mc.json()
    # extended_percentiles field should be null when flag disabled
    assert body.get("extended_percentiles") is None


# T098 -----------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t098_advanced_validation_flag_off_discards(monkeypatch):
    monkeypatch.setenv("AF_ENABLE_ADVANCED_VALIDATION", "0")
    p = {
        "symbol": "FLAGADV",
        "date_range": {"start": "2024-07-01", "end": "2024-07-02"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 5000},
        "extended_validation_toggles": {"sensitivity": True},
        "advanced": {"regime_flags": ["bull"]},
    }
    r = client.post("/api/v1/backtests", json=p)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    res = client.get(f"/api/v1/backtests/{run_id}")
    assert res.status_code == 200
    body = res.json()
    assert body.get("extended_validation_toggles") is None
    assert body.get("advanced") is None


# T101 -----------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.feature006
def test_t101_walkforward_metrics_presence(monkeypatch):
    # independent of flags
    p = {
        "symbol": "WFTEST",
        "date_range": {"start": "2024-08-01", "end": "2024-08-02"},
        "strategy": {"name": "dual_sma"},
        "risk": {"initial_equity": 8000},
    }
    r = client.post("/api/v1/backtests", json=p)
    run_id = r.json()["run_id"]
    wf = client.get(f"/api/v1/backtests/{run_id}/walkforward")
    assert wf.status_code == 200
    body = wf.json()
    splits = body.get("splits", [])
    assert isinstance(splits, list) and len(splits) >= 1
    for s in splits:
        m = s.get("metrics")
        assert isinstance(m, dict), "metrics missing in split"
        assert {"return", "sharpe"}.issubset(m.keys())
