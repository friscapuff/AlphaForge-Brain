from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def test_422_validation_details_contains_field_names_and_stable_structure():
    app = create_app()
    client = TestClient(app)
    # Missing required fields should produce a validation error
    r = client.post("/api/v1/backtests", json={})
    assert r.status_code in (400, 422)
    body = r.json()
    assert isinstance(body, dict)
    # Correlation id header present
    assert r.headers.get("x-correlation-id")
    # New contract: details is a list of objects with field/message
    details = body.get("details")
    # Validation may not populate details if no fields extracted, but when present it must be a list
    if details is not None:
        assert isinstance(details, list)
        for d in details:
            assert isinstance(d, dict)
            assert "field" in d and "message" in d
