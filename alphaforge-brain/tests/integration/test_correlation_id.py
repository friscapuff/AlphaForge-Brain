import uuid

from api.app import create_app
from fastapi.testclient import TestClient

# T095: Correlation ID propagation test (backend)
# Ensures: client-specified x-correlation-id echoed back; if omitted, server generates one.


def test_correlation_id_echo_explicit():
    app = create_app()
    client = TestClient(app)
    cid = str(uuid.uuid4())
    r = client.post(
        "/api/v1/backtests",
        json={
            "symbol": "NVDA",
            "date_range": {"start": "2024-01-01", "end": "2024-01-10"},
            "strategy": {"name": "ema_cross"},
            "risk": {"initial_equity": 10000},
        },
        headers={"x-correlation-id": cid},
    )
    assert r.status_code in (200, 202)
    assert r.headers.get("x-correlation-id") == cid


def test_correlation_id_generated_when_missing():
    app = create_app()
    client = TestClient(app)
    r = client.post(
        "/api/v1/backtests",
        json={
            "symbol": "NVDA",
            "date_range": {"start": "2024-01-01", "end": "2024-01-10"},
            "strategy": {"name": "ema_cross"},
            "risk": {"initial_equity": 10000},
        },
    )
    assert r.status_code in (200, 202)
    gen = r.headers.get("x-correlation-id")
    assert gen is not None and len(gen) > 10 and gen != "null"
