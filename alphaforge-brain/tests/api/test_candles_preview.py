from __future__ import annotations

from datetime import datetime, timedelta, timezone

from api.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

# For now we rely on local provider data existence; if empty, endpoint should return empty list gracefully.


def test_candles_preview_param_validation() -> None:
    end = datetime.now(timezone.utc)
    start = end + timedelta(days=1)  # invalid (end < start)
    resp = client.get(
        "/candles",
        params={
            "symbol": "TEST",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 10,
        },
    )
    assert resp.status_code == 400
    assert "end must be >= start" in resp.text


def test_candles_preview_empty_ok() -> None:
    # Choose a symbol/time range likely absent
    end = datetime(2020, 1, 2, tzinfo=timezone.utc)
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    resp = client.get(
        "/candles",
        params={
            "symbol": "NO_DATA_SYMBOL",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "NO_DATA_SYMBOL"
    assert body["items"] == []
