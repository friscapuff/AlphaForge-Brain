import json

from fastapi.testclient import TestClient

from api.app import create_app


def _make_run(client: TestClient):
    payload = {
        "indicators": [{"name": "dual_sma", "params": {"fast": 5, "slow": 15}}],
        "strategy": {"name": "dual_sma", "params": {"short_window": 5, "long_window": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"slippage_bps": 0, "fee_bps": 0},
        "validation": {},
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-03",
        "seed": 11,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    return r.json()["run_hash"]


def test_events_snapshot_and_heartbeat():
    app = create_app()
    client = TestClient(app)
    run_hash = _make_run(client)
    resp = client.get(f"/runs/{run_hash}/events")
    assert resp.status_code == 200
    events = []
    for block in resp.text.strip().split("\n\n"):
        if not block.strip():
            continue
        data_line = [line for line in block.splitlines() if line.startswith("data: ")]
        if data_line:
            payload = json.loads(data_line[0][6:])
            events.append(payload)
    types = [e.get("type") for e in events]
    assert "heartbeat" in types
    assert "snapshot" in types
