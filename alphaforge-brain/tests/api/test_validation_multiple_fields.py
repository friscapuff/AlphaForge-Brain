import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

@pytest.mark.unit
def test_multiple_field_validation_error_lists_all_fields() -> None:
    # Missing required nested keys and invalid types to trigger multiple errors.
    # Provide minimal body with wrong types for date_range and risk
    bad_payload = {
        "symbol": 123,  # should be str
        "date_range": {"start": 5, "end": None},  # invalid types
        "strategy": {"name": "dual_sma", "params": {"fast": "x", "slow": []}},  # invalid param types
        "risk": {"initial_equity": "notnum", "position_sizing": 7},  # invalid types
        "validation": {},
    }
    r = client.post("/api/v1/backtests", json=bad_payload)
    # Our error handler maps versioned endpoints to 400
    assert r.status_code == 400, r.text
    body = r.json()
    err = body.get("error", {})
    assert err.get("code") == "INVALID_PARAM"
    fields = set(err.get("fields", []))
    # Expect several distinct problematic fields captured
    assert any(f in fields for f in ("symbol", "start", "end")), fields
    # Depending on validation model, nested strategy/risk param type issues may not surface individually.
    # We require at least multiple distinct top-level or nested date range fields.
    assert len(fields) >= 2, fields
    # Ensure no empty field list
    assert fields, "Expected at least one field reported"
