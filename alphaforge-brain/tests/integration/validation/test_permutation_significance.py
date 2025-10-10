from __future__ import annotations

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

xfail_perm = pytest.mark.xfail(
    reason="Masters permutation validation pipeline not implemented",
    strict=False,
)


def _client() -> TestClient:
    return TestClient(create_app())


@xfail_perm
@pytest.mark.integration
def test_permutation_validation_emits_segment_p_values_and_histogram_summary() -> None:
    client = _client()
    payload = {
        "indicators": [
            {
                "name": "dual_sma",
                "params": {"short_window": 6, "long_window": 18},
            }
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 6, "long_window": 18},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.2}},
        "execution": {"mode": "sim", "slippage_bps": 0.25, "fee_bps": 0.15},
        "validation": {
            "permutation": {"segments": ["in_sample", "walk_forward"], "count": 500},
            "block_bootstrap": {"n": 128},
            "walk_forward": {"splits": 4},
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-02-01",
        "end": "2024-02-05",
        "seed": 314,
    }
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 200, resp.text
    run_hash = resp.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200
    body = detail.json()

    permutation = body["validation"]["permutation"]
    assert permutation["schema_version"] == 2
    segments = {seg["segment_id"]: seg for seg in permutation["segments"]}
    assert set(segments) == {"in_sample", "walk_forward"}

    for segment in segments.values():
        assert segment["p_value"] < 0.05
        assert segment["effect_size"] is not None
        histogram = segment["histogram"]
        assert histogram["bins"] == 50
        assert histogram["counts"] and sum(histogram["counts"]) == 500
        assert (
            segment["artifact"]
            == f"validation/permutation/{segment['segment_id']}.parquet"
        )
