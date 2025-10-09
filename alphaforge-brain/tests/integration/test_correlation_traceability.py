from __future__ import annotations

import logging

from api.app import create_app
from fastapi.testclient import TestClient


def test_response_correlation_id_present_in_logs(caplog):
    app = create_app()
    client = TestClient(app)
    caplog.set_level(logging.INFO)
    r = client.post("/api/v1/backtests", json={})
    cid = r.headers.get("x-correlation-id")
    assert cid
    # Ensure a log record references the same correlation id
    records = [
        rec for rec in caplog.records if getattr(rec, "correlation_id", None) == cid
    ]
    assert records, "expected at least one log record with matching correlation_id"
