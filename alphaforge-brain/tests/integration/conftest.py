from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection

# Integration-level conftest to expose fixtures defined in fixtures_manifest.py
# Ensures manifest_loader fixture is discoverable by pytest in integration tests.
from .fixtures_manifest import artifact_hashes, manifest_loader  # noqa: F401


@pytest.fixture(autouse=True)
def stub_fast_create_or_get(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace expensive orchestration with a deterministic stub for integration tests."""
    from services.sweeps import orchestrator as sweeps_orchestrator

    def _fake_create_or_get(
        config: RunConfig,
        registry: Any,
        *,
        seed: int | None = None,
        artifacts_base: Path | None = None,
    ) -> tuple[str, dict[str, Any], bool]:
        signature = f"{config.symbol}-{config.timeframe}-{hash(tuple(sorted(config.strategy.params.items())))}"
        existing = registry.get(signature)
        if existing is not None:
            return signature, existing, False
        record = {
            "hash": signature,
            "summary": {"metrics": {"sharpe": 1.0}},
            "validation_summary": {},
            "p_values": {},
        }
        registry.set(signature, record)
        return signature, record, True

    monkeypatch.setattr(
        sweeps_orchestrator,
        "create_or_get",
        _fake_create_or_get,
        raising=True,
    )


@pytest.fixture()
def temp_artifacts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("ALPHAFORGEB_SWEEP_ROOT", str(tmp_path / "sweeps"))
    sweep_root = tmp_path / "sweeps"
    monkeypatch.chdir(tmp_path)
    return sweep_root


@pytest.fixture()
def sample_run_config() -> RunConfig:
    payload: dict[str, Any] = {
        "start": "2024-01-01",
        "end": "2024-01-05",
        "symbol": "DET",
        "timeframe": "1h",
        "strategy": {"name": "dual_sma", "params": {"fast": 5, "slow": 20}},
        "risk": {"model": "fixed_fraction", "params": {"fraction": 0.1}},
        "execution": {"mode": "sim", "slippage_bps": 0, "fee_bps": 0},
        "validation": {"permutation": {"trials": 4}},
    }
    return RunConfig.model_validate(payload)


@pytest.fixture()
def sample_parameter_collection() -> ParameterCollection:
    parameters = {
        "fast": {"mode": "list", "values": [5, 8]},
        "slow": {"mode": "list", "values": [30, 45]},
    }
    return ParameterCollection.from_raw(parameters)
