from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from domain.validation.masters.cross_validation_models import CrossValidationSummary
from domain.validation.masters.permutation_result import PermutationValidationResult
from domain.validation.realism.report import ExecutionRealismReport

from infra.utils.hash import canonical_json

from .masters_permutation import PermutationSegmentResult
from .pipeline import ValidationResults, ValidationRuntimeConfig


@dataclass(slots=True)
class ValidationArtifact:
    path: Path
    sha256: str
    size: int


def build_validation_payload(
    run_hash: str,
    base_path: Path,
    *,
    runtime_config: ValidationRuntimeConfig,
    results: ValidationResults,
) -> tuple[dict[str, object], tuple[ValidationArtifact, ...]]:
    run_dir = base_path / run_hash
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[ValidationArtifact] = []

    permutation_records, permutation_artifacts = _materialize_permutation_artifacts(
        run_dir, run_hash, results.segments
    )
    artifacts.extend(permutation_artifacts)

    cross_validation_payload, cross_artifact = _materialize_cross_validation_artifact(
        run_dir, results.cross_validation
    )
    if cross_artifact is not None:
        artifacts.append(cross_artifact)

    realism_payload, realism_artifact = _materialize_realism_artifact(
        run_dir, results.execution_realism
    )
    if realism_artifact is not None:
        artifacts.append(realism_artifact)

    permutation_summary = [
        record.to_manifest_fragment() for record in permutation_records
    ]
    manifest_fragment = {
        "validation_schema_version": 2,
        "validation_significance": results.aggregate.validation_significance,
        "modules": _manifest_module_map(runtime_config, permutation_records),
        "permutation_summary": {"segments": permutation_summary},
    }
    if results.bias_adjustment is not None:
        manifest_fragment["sharpe_adjustments"] = (
            results.bias_adjustment.to_manifest_fragment()
        )
    if cross_validation_payload["manifest"] is not None:
        manifest_fragment["cross_validation"] = cross_validation_payload["manifest"]
    if realism_payload["manifest"] is not None:
        manifest_fragment["execution_realism"] = realism_payload["manifest"]

    config_meta = {
        "modules": list(runtime_config.modules),
        "permutation_count": runtime_config.permutation_count,
        "significance_threshold": runtime_config.significance_threshold,
        "leakage_threshold": runtime_config.leakage_threshold,
        "realism_capacity_bps_limit": runtime_config.realism_capacity_bps_limit,
        "bias_absolute_threshold": runtime_config.bias_absolute_threshold,
        "bias_relative_threshold": runtime_config.bias_relative_threshold,
    }

    payload: dict[str, object] = {
        "schema_version": 2,
        "significance_status": results.aggregate.validation_significance,
        "failed_checks": list(results.aggregate.failed_checks),
        "caution_checks": list(results.aggregate.caution_checks),
        "metadata": dict(results.aggregate.metadata),
        "modules": _module_toggle_map(runtime_config),
        "config": config_meta,
        "permutation": {
            "segments": (
                [
                    {
                        **perm.to_api_payload(),
                        "observed_metric": segment.observed_metric,
                        "effect_size": segment.effect_size,
                    }
                    for perm, segment in zip(permutation_records, results.segments)
                ]
                if results.segments
                else []
            ),
        },
        "bias_adjustments": (
            results.bias_adjustment.to_api_payload()
            if results.bias_adjustment is not None
            else None
        ),
        "cross_validation": cross_validation_payload["api"],
        "execution_realism": realism_payload["api"],
        "manifest": manifest_fragment,
        "artifacts": {
            artifact.path.as_posix(): {"sha256": artifact.sha256, "size": artifact.size}
            for artifact in artifacts
        },
    }

    return payload, tuple(artifacts)


def extract_artifacts(payload: Mapping[str, object]) -> Iterable[ValidationArtifact]:
    artifacts = payload.get("artifacts", {})
    if not isinstance(artifacts, Mapping):
        return tuple()
    extracted: list[ValidationArtifact] = []
    for rel_path, meta in artifacts.items():
        if not isinstance(meta, Mapping):
            continue
        path_obj = Path(rel_path)
        extracted.append(
            ValidationArtifact(
                path=path_obj,
                sha256=str(meta.get("sha256", "")),
                size=int(meta.get("size", 0)),
            )
        )
    return tuple(extracted)


def _materialize_permutation_artifacts(
    run_dir: Path,
    run_hash: str,
    segments: tuple[PermutationSegmentResult, ...],
) -> tuple[tuple[PermutationValidationResult, ...], tuple[ValidationArtifact, ...]]:
    if not segments:
        return tuple(), tuple()

    artifacts: list[ValidationArtifact] = []
    records: list[PermutationValidationResult] = []
    for segment in segments:
        rel_path = (
            Path("validation") / "permutation" / f"segment_{segment.segment_id}.parquet"
        )
        target = run_dir / rel_path
        payload = {
            "segment_id": segment.segment_id,
            "observed_metric": segment.observed_metric,
            "permutations": list(segment.permutations),
            "histogram": segment.histogram_summary,
            "optimizer_records": list(segment.optimizer_records),
        }
        digest, size = _write_json(target, payload)
        artifact = ValidationArtifact(path=rel_path, sha256=digest, size=size)
        artifacts.append(artifact)
        records.append(
            segment.to_validation_result(
                run_hash=run_hash,
                artifact_path=rel_path.as_posix(),
                artifact_sha256=digest,
            )
        )
    return tuple(records), tuple(artifacts)


def _materialize_cross_validation_artifact(
    run_dir: Path, summary: CrossValidationSummary | None
) -> tuple[dict[str, object], ValidationArtifact | None]:
    if summary is None:
        return {"api": None, "manifest": None}, None

    rel_path = Path("validation") / "cscv" / "folds.parquet"
    target = run_dir / rel_path
    payload = {
        "mode": summary.mode.value,
        "seed_root": summary.seed_root,
        "leakage_score": summary.leakage_score,
        "bias_flag": summary.bias_flag,
        "cscv_adjusted_sharpe": summary.cscv_adjusted_sharpe,
        "folds": [fold.metadata_payload() for fold in summary.folds],
    }
    digest, size = _write_json(target, payload)
    artifact = ValidationArtifact(path=rel_path, sha256=digest, size=size)
    api_payload = summary.to_api_payload() | {
        "folds_artifact": rel_path.as_posix(),
        "folds_artifact_sha256": digest,
    }
    manifest_payload = {
        "mode": summary.mode.value,
        "leakage_score": summary.leakage_score,
        "folds_artifact": rel_path.as_posix(),
        "folds_artifact_sha256": digest,
        "bias_flag": summary.bias_flag,
    }
    return {"api": api_payload, "manifest": manifest_payload}, artifact


def _materialize_realism_artifact(
    run_dir: Path, report: ExecutionRealismReport | None
) -> tuple[dict[str, object], ValidationArtifact | None]:
    if report is None:
        return {"api": None, "manifest": None}, None

    rel_path = Path("validation") / "realism.json"
    target = run_dir / rel_path
    payload = report.metadata_payload()
    digest, size = _write_json(target, payload)
    artifact = ValidationArtifact(path=rel_path, sha256=digest, size=size)
    api_payload = report.to_api_payload() | {
        "artifact": rel_path.as_posix(),
        "artifact_sha256": digest,
    }
    manifest_payload = report.to_manifest_fragment() | {
        "artifact": rel_path.as_posix(),
        "artifact_sha256": digest,
    }
    return {"api": api_payload, "manifest": manifest_payload}, artifact


def _module_toggle_map(runtime_config: ValidationRuntimeConfig) -> dict[str, object]:
    modules = set(runtime_config.modules)
    cross_val_state: str | bool = False
    if "cpcv" in modules:
        cross_val_state = "cpcv"
    elif "purged_kfold" in modules:
        cross_val_state = "purged_kfold"
    return {
        "permutation": "permutation" in modules,
        "bias_adjustments": any(m in modules for m in ("dsr", "psr")),
        "cross_validation": cross_val_state,
        "execution_realism": "realism" in modules,
    }


def _manifest_module_map(
    runtime_config: ValidationRuntimeConfig,
    permutation_results: Sequence[PermutationValidationResult],
) -> dict[str, object]:
    modules = set(runtime_config.modules)
    executed = sum(result.executed_permutations for result in permutation_results)
    return {
        "permutation": {
            "enabled": "permutation" in modules,
            "executed_permutations": executed,
        },
        "dsr": {"enabled": "dsr" in modules},
        "psr": {"enabled": "psr" in modules},
        "purged_kfold": {"enabled": "purged_kfold" in modules},
        "cpcv": {"enabled": "cpcv" in modules},
        "realism": {"enabled": "realism" in modules},
    }


def _write_json(path: Path, payload: Mapping[str, object]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json(payload)
    path.write_text(text, encoding="utf-8")
    data = text.encode("utf-8")
    from hashlib import sha256

    digest = sha256(data).hexdigest()
    return digest, len(data)


__all__ = ["build_validation_payload", "extract_artifacts", "ValidationArtifact"]
