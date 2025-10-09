from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def _cause_validation_error(client: TestClient):
    return client.post("/api/v1/backtests", json={})


def test_error_shape_is_deterministic_for_identical_failures():
    app = create_app()
    client = TestClient(app)
    r1 = _cause_validation_error(client)
    r2 = _cause_validation_error(client)
    assert r1.status_code in (400, 422)
    assert r2.status_code == r1.status_code
    b1 = r1.json()
    b2 = r2.json()
    assert type(b1) is type(b2)
    # Deterministic top-level key set with new contract
    if isinstance(b1, dict) and isinstance(b2, dict):
        expected_keys = {"error_code", "message", "correlation_id"}
        assert expected_keys.issubset(set(b1.keys()))
        assert set(b1.keys()) == set(b2.keys())
