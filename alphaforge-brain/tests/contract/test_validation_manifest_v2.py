from __future__ import annotations

import pytest
from api.app import create_app
from fastapi.testclient import TestClient

xfail_manifest_v2 = pytest.mark.xfail(
    reason="Validation manifest v2 contract pending implementation",
    strict=False,
)


def _make_client() -> TestClient:
    return TestClient(create_app())


@xfail_manifest_v2
@pytest.mark.contract
def test_validation_manifest_enforces_schema_version_and_artifacts() -> None:
    client = _make_client()
    payload = {
        "indicators": [
            {
                "name": "dual_sma",
                "params": {"short_window": 5, "long_window": 12},
            }
        ],
        "strategy": {
            "name": "dual_sma",
            "params": {"short_window": 5, "long_window": 12},
        },
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0.5, "fee_bps": 0.25},
        "validation": {
            "permutation": {"n": 500},
            "block_bootstrap": {"n": 250},
            "walk_forward": {"splits": 5},
        },
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-05",
        "seed": 4242,
    }
    creation = client.post("/runs", json=payload)
    assert creation.status_code == 200, creation.text
    run_hash = creation.json()["run_hash"]

    detail = client.get(f"/runs/{run_hash}")
    assert detail.status_code == 200, detail.text
    body = detail.json()

    # Contract expectations for manifest v2
    assert body.get("validation_schema_version") == 2
    manifest = body.get("validation_manifest")
    assert isinstance(manifest, dict)

    toggles = manifest.get("modules")
    assert toggles == {
        "permutation": True,
        "bias_adjustments": True,
        "cross_validation": "cpcv",
        "execution_realism": True,
    }

    artifacts = {art["name"]: art for art in body.get("artifacts", [])}
    histogram_artifact = artifacts["validation/permutation/segment_in_sample.parquet"]
    assert histogram_artifact["sha256"]
    assert artifacts["validation/cscv/folds.parquet"]["sha256"]
    assert artifacts["validation/realism.json"]["sha256"]
