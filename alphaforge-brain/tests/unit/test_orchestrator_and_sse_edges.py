from __future__ import annotations

from api.app import create_app
from domain.run.event_buffer import get_global_buffer
from domain.run.orchestrator import Orchestrator, OrchestratorState
from domain.schemas.run_config import (
    ExecutionSpec,
    IndicatorSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)
from fastapi.testclient import TestClient


def _basic_config(symbol: str = "SSE") -> RunConfig:
    return RunConfig(
        indicators=[
            IndicatorSpec(name="sma", params={"window": 5}),
            IndicatorSpec(name="sma", params={"window": 15}),
        ],
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 15}),
        risk=RiskSpec(model="fixed_fraction", params={"fraction": 0.1}),
        execution=ExecutionSpec(mode="sim"),
        validation=ValidationSpec(),
        symbol=symbol,
        timeframe="1m",
        start="2024-01-01",
        end="2024-01-02",
        seed=123,
    )


def test_orchestrator_cancellation_before_start():
    cfg = _basic_config(symbol="ASYNC")
    orch = Orchestrator(cfg)
    orch.cancel()
    result = orch.run()
    assert orch.state == OrchestratorState.CANCELLED
    assert result.get("cancelled") is True


def test_orchestrator_double_run_idempotent():
    cfg = _basic_config(symbol="IDEMP")
    orch = Orchestrator(cfg)
    first = orch.run()
    second = orch.run()
    assert first is second  # same cached dict
    assert orch.state == OrchestratorState.COMPLETE


def test_sse_resume_after_snapshot_includes_no_duplicates():
    app = create_app()
    client = TestClient(app)
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "NVDA",
        "timeframe": "1d",
        "start": "2024-01-01",
        "end": "2024-02-01",
        "seed": 42,
    }
    r = client.post("/runs", json=payload)
    run_hash = r.json()["run_hash"]
    # First fetch (fresh) -> should contain heartbeat + snapshot
    resp1 = client.get(f"/runs/{run_hash}/events", headers={})
    body1 = resp1.content.decode()
    assert "snapshot" in body1
    # Resume with Last-Event-ID=1 -> expect empty or cancellation only
    resp2 = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "1"})
    body2 = resp2.content.decode()
    # No duplicate snapshot
    assert body2.count("snapshot") == 0


def test_sse_stream_cancellation_event_injected():
    app = create_app()
    client = TestClient(app)
    payload = {
        "indicators": [],
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 15}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim"},
        "validation": {},
        "symbol": "SSE",
        "timeframe": "1m",
        "start": "2024-01-01",
        "end": "2024-01-02",
        "seed": 99,
    }
    r = client.post("/runs", json=payload)
    run_hash = r.json()["run_hash"]
    # Inject a cancellation event after completion by appending to global buffer
    buf = get_global_buffer(run_hash)
    buf.append("cancelled", {"run_hash": run_hash, "status": "CANCELLED"})
    # Fetch events after snapshot id (1) -> expect cancelled synthetic event id 2
    resp = client.get(f"/runs/{run_hash}/events", headers={"Last-Event-ID": "1"})
    body = resp.content.decode()
    assert "cancelled" in body
