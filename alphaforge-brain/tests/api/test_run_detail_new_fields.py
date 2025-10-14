from __future__ import annotations

import time

from api.app import app
from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.schemas.run_config import RunConfig
from fastapi.testclient import TestClient
from pydantic import ValidationError

client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "start": "2024-01-01",
        "end": "2024-01-02",
        # Use a symbol that triggers synthetic dataset generation in orchestrator fallback
        "symbol": "TEST",
        "timeframe": "1m",
        "indicators": [
            {"name": "sma", "params": {"window": 5}},
        ],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "seed": 111,
    }


def test_run_detail_includes_new_dataset_fields_and_alias() -> None:
    p = _payload()
    r = client.post("/runs", json=p)
    assert r.status_code in {200, 202}
    run_hash = r.json()["run_hash"]
    _materialize_run_if_needed(run_hash, p)

    detail = _wait_for_run_detail(run_hash)

    assert set(
        ["data_hash", "calendar_id", "validation_summary", "validation"]
    ).issubset(detail.keys())
    # validation alias should mirror validation_summary exactly
    assert detail.get("validation_summary") == detail.get("validation")

    # When include_anomalies=true summary should contain anomaly_counters key (even if empty dict)
    detail_with = _wait_for_run_detail(run_hash, include_anomalies=True)
    summary_obj = detail_with.get("summary", {})
    assert (
        "anomaly_counters" in summary_obj
    ), "anomaly_counters missing when include_anomalies=true"


def test_run_detail_includes_persistence_and_accounting_metadata() -> None:
    p = _payload()
    r = client.post("/runs", json=p)
    assert r.status_code in {200, 202}
    run_hash = r.json()["run_hash"]
    _materialize_run_if_needed(run_hash, p)

    detail = _wait_for_run_detail(run_hash)

    persistence_block = detail.get("persistence")
    assert isinstance(persistence_block, dict)
    assert persistence_block.get("schema_version")
    assert persistence_block.get("record_id")

    accounting_block = detail.get("accounting")
    assert accounting_block is not None
    assert accounting_block.get("status")
    # delta/tolerance may be None on perfectly balanced ledger but keys should exist
    assert "delta" in accounting_block
    assert "tolerance" in accounting_block


def _wait_for_run_detail(
    run_hash: str, *, include_anomalies: bool = False, timeout: float = 5.0
) -> dict[str, object]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    params = "?include_anomalies=true" if include_anomalies else ""
    while time.time() < deadline:
        response = client.get(f"/runs/{run_hash}{params}")
        if response.status_code == 200:
            return response.json()
        last_error = AssertionError(f"Unexpected status {response.status_code}")
        time.sleep(0.05)
    if last_error is not None:
        raise last_error
    raise AssertionError("Timed out waiting for run detail")


def _materialize_run_if_needed(run_hash: str, payload: dict[str, object]) -> None:
    registry = getattr(client.app.state, "registry", None)
    if not isinstance(registry, InMemoryRunRegistry):
        return
    if registry.get(run_hash) is not None:
        return
    try:
        cfg = RunConfig.model_validate(payload)
    except ValidationError:
        return
    computed_hash, _, _ = create_or_get(cfg, registry, seed=cfg.seed)
    if computed_hash != run_hash:
        # Sweep submissions use a sweep_id that differs from the actual run hash; in that
        # scenario we rely on external orchestrators and cannot synthesize a record here.
        return
