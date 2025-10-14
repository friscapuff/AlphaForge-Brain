from __future__ import annotations

from time import perf_counter

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

from infra.config import get_settings


@pytest.mark.perf
def test_sweep_rejection_latency_under_two_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AF_OPTIMIZATION_MAX_COMBINATIONS", "1")
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover
        pass

    app = create_app()
    client = TestClient(app)

    payload = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "symbol": "LAT",
        "timeframe": "1h",
        "strategy": {
            "name": "dual_sma",
            "parameters": {
                "fast": {"mode": "list", "values": [5, 8, 13]},
                "slow": {"mode": "single", "value": 30},
            },
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
    }

    start = perf_counter()
    response = client.post("/runs", json=payload)
    duration = perf_counter() - start

    assert response.status_code == 400
    assert duration < 2.0, f"Sweep rejection exceeded latency budget: {duration:.3f}s"
    body = response.json()
    assert body.get("error", {}).get("code") == "OPTIMIZATION_SWEEP_LIMIT_HIT"

    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover
        pass
