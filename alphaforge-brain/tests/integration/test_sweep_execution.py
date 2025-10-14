from __future__ import annotations

from pathlib import Path

from api.app import create_app
from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection
from services.sweeps import execute_sweep


def test_execute_sweep_persists_manifest(
    tmp_path: Path,
    temp_artifacts_root: Path,
    sample_run_config: RunConfig,
    sample_parameter_collection: ParameterCollection,
) -> None:
    registry = InMemoryRunRegistry()

    result = execute_sweep(
        sweep_id="sweep-001",
        base_config=sample_run_config,
        parameters=sample_parameter_collection,
        registry=registry,
        tickers=None,
        initiator="integration@test",
        storage_root=temp_artifacts_root,
        artifacts_base=tmp_path / "runs",
    )

    manifest_path = temp_artifacts_root / "sweep-001" / "manifest.json"
    assert manifest_path.exists()
    data = manifest_path.read_text(encoding="utf-8")
    assert "sweep-001" in data
    assert (
        len(result.manifest.combinations)
        == sample_parameter_collection.combination_count
    )
    assert result.manifest.tickers[0].ticker == "DET"
    assert len(result.ticker_manifests) == 1

    ticker_manifest = next(iter(result.ticker_manifests.values()))
    assert ticker_manifest.exists()
    ticker_data = ticker_manifest.read_text(encoding="utf-8")
    assert "run_hash" in ticker_data
    assert result.manifest.trust_gates.manifest is not None
    derived = result.manifest.derived_metrics
    assert (
        derived["total_combinations"] == sample_parameter_collection.combination_count
    )
    assert (
        derived["succeeded_combinations"]
        == sample_parameter_collection.combination_count
    )
    assert derived["skipped_combinations"] == 0
    per_ticker = derived["per_ticker_totals"]
    assert per_ticker["DET"]["total"] == sample_parameter_collection.combination_count
    assert (
        per_ticker["DET"]["succeeded"] == sample_parameter_collection.combination_count
    )
    assert result.manifest.notes == []


def test_sweep_status_endpoint_returns_manifest(
    tmp_path: Path,
    temp_artifacts_root: Path,
    sample_run_config: RunConfig,
    sample_parameter_collection: ParameterCollection,
) -> None:
    app = create_app()
    registry: InMemoryRunRegistry = app.state.registry  # type: ignore[assignment]

    result = execute_sweep(
        sweep_id="sweep-002",
        base_config=sample_run_config,
        parameters=sample_parameter_collection,
        registry=registry,
        tickers=None,
        storage_root=temp_artifacts_root,
        artifacts_base=tmp_path / "runs",
    )

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get(f"/api/v1/sweeps/{result.manifest.sweep_id}")
    payload = response.json()
    assert response.status_code == 200, payload
    assert payload["sweep_id"] == "sweep-002"
    assert payload["status"] == "completed"
    assert payload["combination_cap"] == result.manifest.combination_cap
    assert len(payload["combinations"]) == sample_parameter_collection.combination_count
    assert payload["telemetry_reference"]["manifest_path"].endswith("manifest.json")
    assert (
        payload["derived_metrics"]["total_combinations"]
        == sample_parameter_collection.combination_count
    )
    assert payload["derived_metrics"]["skipped_combinations"] == 0
    assert payload["notes"] == []


def test_sweep_status_missing_manifest_returns_404(temp_artifacts_root: Path) -> None:
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/sweeps/unknown-sweep")
    assert response.status_code == 404
    assert response.json()["detail"] == "sweep not found"
