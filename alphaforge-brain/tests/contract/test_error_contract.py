from __future__ import annotations

import re

from api.app import create_app
from fastapi.testclient import TestClient


def test_error_contract_includes_correlation_id_and_kebab_code():
    app = create_app()
    client = TestClient(app)
    # Hit a known validation error path to force an error response
    r = client.post(
        "/api/v1/backtests",
        json={"symbol": "", "date_range": {"start": "2024-01-01", "end": "2024-01-10"}},
    )
    assert r.status_code in (400, 422)
    body = r.json()
    assert isinstance(body, dict)
    # Header correlation
    cid = r.headers.get("x-correlation-id")
    assert cid and isinstance(cid, str)
    # Body correlation_id must match header
    assert body.get("correlation_id") == cid
    # Error code is kebab-case and stable
    ec = body.get("error_code")
    assert isinstance(ec, str)
    assert re.fullmatch(r"[a-z0-9\-]+", ec)
    # For this validation path we expect invalid-param
    assert ec == "invalid-param"
    # Message is present
    assert isinstance(body.get("message"), str)
