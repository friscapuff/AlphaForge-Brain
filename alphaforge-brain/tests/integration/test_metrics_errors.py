from __future__ import annotations

from api.app import create_app
from fastapi.testclient import TestClient


def test_metrics_endpoint_exposes_text_format():
    app = create_app()
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert ctype.startswith("text/plain")
    assert "api_error_total" in r.text or "prometheus_client" in r.text
