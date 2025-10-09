from __future__ import annotations

import statistics
import time

from api.app import create_app
from fastapi.testclient import TestClient


def test_error_middleware_overhead_smoke():
    app = create_app()
    client = TestClient(app)

    # Warmup
    for _ in range(5):
        client.get("/health")

    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.get("/health")
        t1 = time.perf_counter()
        assert resp.status_code == 200
        times.append((t1 - t0) * 1000.0)

    p50 = statistics.median(times)
    # This is a smoke-level sanity check; keep threshold generous for CI variability
    assert p50 < 15.0, f"unexpected overhead: p50={p50:.2f}ms"
