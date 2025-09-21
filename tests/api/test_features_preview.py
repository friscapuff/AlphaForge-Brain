from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)

def test_features_preview_empty() -> None:
    payload = {
        "symbol": "NO_DATA_SYMBOL",
        "start": "2020-01-01T00:00:00Z",
        "end": "2020-01-02T00:00:00Z",
        "limit": 50
    }
    resp = client.post("/features/preview", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "NO_DATA_SYMBOL"
    assert data["count"] == 0
    assert data["columns"] == []
    assert data["items"] == []
