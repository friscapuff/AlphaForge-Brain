from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def _trigger_server_error(client: TestClient):
    # Use canonical endpoint with malformed payload to trigger server-side path; may produce 500
    return client.post("/api/v1/backtests", json={"symbol": None})


def test_prod_mode_is_user_safe(monkeypatch):
    monkeypatch.setenv("ERROR_VERBOSITY", "production")
    app = create_app()
    client = TestClient(app)
    r = _trigger_server_error(client)
    body = r.json()
    assert isinstance(body, dict)
    # In production, no debug block should be present
    assert "debug" not in body
    # Correlation header present
    assert r.headers.get("x-correlation-id")


def test_dev_mode_allows_debug_block(monkeypatch):
    monkeypatch.setenv("ERROR_VERBOSITY", "development")
    app = create_app()
    client = TestClient(app)
    r = _trigger_server_error(client)
    body = r.json()
    assert isinstance(body, dict)
    # In development, debug block may appear
    if r.status_code >= 500:
        assert "debug" in body and isinstance(body["debug"], dict)
    assert r.headers.get("x-correlation-id")
