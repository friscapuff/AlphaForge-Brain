from __future__ import annotations

from api.app import create_app
from client import AlphaForgeMindClient
from fastapi.testclient import TestClient


def _make_run(client_http: AlphaForgeMindClient, seed: int) -> str:
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": seed,
    }
    return client_http.submit_run(payload).run_hash


def test_sdk_retention_diff():
    app = create_app()
    test_client = TestClient(app)
    client_http = AlphaForgeMindClient("http://testserver", session=test_client)
    # create a few runs
    for i in range(4):
        _make_run(client_http, 9000 + i)
    # diff with a smaller keep_last to ensure some new_demotions appear (depending on default config)
    diff = client_http.diff_retention_plan(keep_last=1)
    assert "diff" in diff
    assert set(diff["diff"].keys()) >= {"new_demotions", "new_full", "lost_full"}
