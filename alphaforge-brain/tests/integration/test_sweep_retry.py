from __future__ import annotations

from pathlib import Path

from domain.run.create import InMemoryRunRegistry
from domain.schemas.run_config import RunConfig
from models.parameter_definition import ParameterCollection
from services.sweeps import execute_sweep
from services.sweeps.repository import load_manifest


def test_retry_marks_non_targeted_combinations_skipped(
    tmp_path: Path,
    temp_artifacts_root: Path,
    sample_run_config: RunConfig,
    sample_parameter_collection: ParameterCollection,
) -> None:
    registry = InMemoryRunRegistry()
    sweep_id = "sweep-retry"

    initial = execute_sweep(
        sweep_id=sweep_id,
        base_config=sample_run_config,
        parameters=sample_parameter_collection,
        registry=registry,
        storage_root=temp_artifacts_root,
        artifacts_base=tmp_path / "runs",
    )

    retry_ids = [combo.combination_id for combo in initial.manifest.combinations[:2]]
    assert retry_ids

    retried = execute_sweep(
        sweep_id=sweep_id,
        base_config=sample_run_config,
        parameters=sample_parameter_collection,
        registry=registry,
        storage_root=temp_artifacts_root,
        artifacts_base=tmp_path / "runs",
        retry_combination_ids=retry_ids,
    )

    assert retried.manifest.notes == ["SWEEP_RETRY_EXECUTION"]

    combos = {combo.combination_id: combo for combo in retried.manifest.combinations}
    for target in retry_ids:
        combo = combos[target]
        assert combo.status.value == "succeeded"
        assert combo.run_hash is not None
    for cid, combo in combos.items():
        if cid not in retry_ids:
            assert combo.status.value == "skipped"
            assert combo.run_hash is None

    derived = retried.manifest.derived_metrics
    total_expected = sample_parameter_collection.combination_count
    assert derived["total_combinations"] == total_expected
    assert derived["succeeded_combinations"] == len(retry_ids)
    assert derived["skipped_combinations"] == total_expected - len(retry_ids)
    assert derived["per_ticker_totals"]["DET"]["skipped"] == total_expected - len(
        retry_ids
    )

    record = load_manifest(sweep_id, storage_root=temp_artifacts_root)
    assert record.manifest.notes == ["SWEEP_RETRY_EXECUTION"]
    orchestrator_checkpoint = record.manifest.trust_gates.orchestrator
    assert orchestrator_checkpoint is not None
    sanitized = orchestrator_checkpoint.sanitized_parameters or {}
    assert sanitized["retry_requested"] is True
    assert sanitized["retry_combination_ids"] == sorted(retry_ids)
