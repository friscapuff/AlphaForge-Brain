from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from api.app import app


def test_request_logging_correlation_id(caplog):
    client = TestClient(app)
    correlation_id = "test-corr-123"
    # Trigger a simple health request (always 200)
    resp = client.get("/health", headers={"x-correlation-id": correlation_id})
    assert resp.status_code == 200
    # Scan captured logs for our structured entry
    matched: list[dict[str, Any]] = []
    for rec in caplog.records:
        if rec.name == "api.request" and getattr(rec, "correlation_id", None) == correlation_id:
            matched.append(
                {
                    "message": rec.getMessage(),
                    "correlation_id": getattr(rec, "correlation_id", None),
                    "path": getattr(rec, "path", None),
                    "method": getattr(rec, "method", None),
                    "status_code": getattr(rec, "status_code", None),
                }
            )
    assert matched, "expected at least one request_completed log with correlation id"
    # Ensure path and method were logged
    entry = matched[0]
    assert entry["path"] == "/health"
    assert entry["method"] == "GET"
    assert entry["status_code"] == 200
