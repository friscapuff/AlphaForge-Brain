from __future__ import annotations

from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.manifest import SweepDataQualityStatus
from models.parameter_definition import ParameterCollection
from prometheus_client import CollectorRegistry
from services.sweeps.orchestrator import execute_sweep


def _build_run_config() -> RunConfig:
    payload: dict[str, object] = {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "TRUST",
        "timeframe": "1h",
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
    }
    return RunConfig.model_validate(payload)


def test_data_quality_variance_within_thresholds() -> None:
    base_config = _build_run_config()
    parameters = ParameterCollection.from_raw(
        {
            "fast": {"mode": "list", "values": [5, 8]},
            "slow": {"mode": "list", "values": [30, 45]},
        }
    )
    registry = InMemoryRunRegistry()
    metrics_registry = CollectorRegistry()

    result = execute_sweep(
        sweep_id="variance-test",
        base_config=base_config,
        parameters=parameters,
        registry=registry,
        metrics_registry=metrics_registry,
    )

    manifest = result.manifest
    assert manifest.trust_gates.manifest is not None
    assert (
        manifest.trust_gates.manifest.data_quality_status is SweepDataQualityStatus.PASS
    )
    assert manifest.derived_metrics["overall_data_quality_status"] == "pass"

    for ticker_manifest in manifest.tickers:
        assert ticker_manifest.data_quality_status is SweepDataQualityStatus.PASS
        metrics = ticker_manifest.variance_metrics
        assert "pnl_delta_bps" in metrics
        assert abs(float(metrics["pnl_delta_bps"])) <= 0.1
        assert "drawdown_delta_pct" in metrics
        assert abs(float(metrics["drawdown_delta_pct"])) <= 0.001
        assert "trade_count_delta" in metrics
        assert abs(int(metrics["trade_count_delta"])) == 0
