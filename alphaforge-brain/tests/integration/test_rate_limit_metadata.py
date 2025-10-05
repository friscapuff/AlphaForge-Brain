import uuid

from api.app import create_app
from fastapi.testclient import TestClient

# Test that rate limit 429 response returns structured error code and we can infer reset (TBD: header)
# Currently we expose reset seconds via internal attribute; future enhancement can surface header.


def test_rate_limit_returns_code_and_generates_reset_hint():
    app = create_app()
    client = TestClient(app)
    # Exhaust limiter quickly (9 calls)
    payload = {
        "paths": 20,
    }
    # Need a run id first
    r_run = client.post(
        "/api/v1/backtests",
        json={
            "symbol": "NVDA",
            "date_range": {"start": "2024-01-01", "end": "2024-01-02"},
            "strategy": {"name": "ema"},
            "risk": {"initial_equity": 10000},
        },
    )
    run_id = r_run.json()["run_id"]
    hit = None
    for _ in range(12):
        r = client.post(
            f"/api/v1/backtests/{run_id}/montecarlo",
            json=payload,
            headers={"x-correlation-id": str(uuid.uuid4())},
        )
        if r.status_code == 429:
            hit = r
            break
    assert hit is not None, "Did not trigger rate limit"
    body = hit.json()
    assert body["error"]["code"] == "RATE_LIMIT"
