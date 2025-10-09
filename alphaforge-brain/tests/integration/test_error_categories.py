from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def test_unexpected_error_returns_structured_body():
    app = create_app()
    client = TestClient(app)
    # Trigger a failure by sending obviously wrong types
    r = client.post("/api/v1/backtests", json={"symbol": 123})
    assert r.status_code in (400, 422, 500)
    body = r.json()
    assert isinstance(body, dict)
    # New contract requires error_code
    assert "error_code" in body
