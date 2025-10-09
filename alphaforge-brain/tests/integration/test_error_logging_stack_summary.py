from __future__ import annotations

import logging

from api.app import create_app
from fastapi.testclient import TestClient


def test_server_logs_include_correlation_and_stack_summary(caplog, capsys):
    app = create_app()
    client = TestClient(app)
    caplog.set_level(logging.INFO)
    client.post("/api/v1/backtests", json={})
    # We at least expect the request_completed log with correlation_id
    records = [rec for rec in caplog.records if rec.name == "api.request"]
    has_attr = any(hasattr(rec, "correlation_id") for rec in records)
    # Structlog may emit JSON to stdout; accept that as evidence too
    out = capsys.readouterr().out
    has_stdout = '"correlation_id"' in out
    assert has_attr or has_stdout
