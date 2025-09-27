from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient

from infra.utils.hash import hash_canonical


def test_run_create_content_hash_stable():
    app = create_app()
    client = TestClient(app)
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
        "seed": 1234,
    }
    r = client.post("/runs", json=payload)
    assert r.status_code == 200
    data = r.json()
    ch = data["content_hash"]
    # Recompute expected (mirror server logic excluding content_hash itself)
    base_payload = {}
    for k, v in data.items():
        if k == "content_hash":
            continue
        if k == "created_at":
            # Server hashed str(datetime_obj) which uses space separator, while response JSON uses 'T'
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(v)
                v = str(dt)
            except Exception:
                v = str(v)
        base_payload[k] = str(v)
    expected = hash_canonical(base_payload)
    assert ch == expected


def test_run_detail_content_hash_stable():
    app = create_app()
    client = TestClient(app)
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
        "seed": 5678,
    }
    r = client.post("/runs", json=payload)
    run_hash = r.json()["run_hash"]
    detail = client.get(f"/runs/{run_hash}").json()
    ch = detail["content_hash"]
    # Mirror server logic: exclude heavy nested objects (manifest, artifacts, summary, validation* fields)
    base_payload = {}
    from datetime import datetime

    for k, v in detail.items():
        if k in {
            "content_hash",
            "manifest",
            "artifacts",
            "summary",
            "validation_summary",
            "validation",
        }:
            continue
        if k == "created_at":
            try:
                dt = datetime.fromisoformat(v)
                v = str(dt)
            except Exception:
                v = str(v)
        if isinstance(v, (dict, list)):
            base_payload[k] = k
        else:
            base_payload[k] = str(v)
    expected = hash_canonical(base_payload)
    assert ch == expected
