from __future__ import annotations

from copy import deepcopy

import pytest
from src.services.hashing.validation_signature import compute_validation_manifest_hash


@pytest.fixture()
def validation_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "significance_status": "pass",
        "failed_checks": [],
        "caution_checks": ["permutation_sampling", "execution_realism"],
        "manifest": {
            "validation_schema_version": 2,
            "validation_significance": "pass",
            "modules": {
                "permutation": {"enabled": True, "executed_permutations": 500},
                "dsr": {"enabled": True},
                "psr": {"enabled": True},
            },
            "permutation_summary": {
                "segments": [
                    {
                        "segment_id": "in_sample",
                        "p_value": 0.01,
                        "artifact_path": "validation/permutation/segment_in_sample.parquet",
                        "artifact_sha256": "a" * 64,
                    },
                    {
                        "segment_id": "walk_forward",
                        "p_value": 0.02,
                        "artifact_path": "validation/permutation/segment_walk_forward.parquet",
                        "artifact_sha256": "b" * 64,
                        "fallback_reason": None,
                    },
                ]
            },
            "cross_validation": {
                "mode": "cpcv",
                "folds": [
                    {
                        "fold_id": "F01",
                        "metrics": {"sharpe": 1.1},
                    },
                    {
                        "fold_id": "F00",
                        "metrics": {"sharpe": 1.0},
                    },
                ],
            },
            "execution_realism": {
                "status": "caution",
                "warnings": [
                    "Capacity ratio breaches configured limit; liquidity may be insufficient.",
                    "Combined transaction costs and market impact exceed configured budget.",
                ],
            },
        },
        "modules": {
            "permutation": True,
            "bias_adjustments": True,
            "cross_validation": "cpcv",
            "execution_realism": True,
        },
        "config": {
            "modules": ["permutation", "dsr", "psr", "cpcv", "realism"],
            "permutation_count": 500,
            "significance_threshold": 0.05,
            "leakage_threshold": 0.1,
            "realism_capacity_bps_limit": 150.0,
            "bias_absolute_threshold": 0.25,
            "bias_relative_threshold": 0.2,
        },
        "permutation": {
            "segments": [
                {
                    "segment_id": "walk_forward",
                    "p_value": 0.02,
                    "histogram": {
                        "bins": 5,
                        "counts": [1, 2, 3, 4, 5],
                    },
                },
                {
                    "segment_id": "in_sample",
                    "p_value": 0.01,
                    "histogram": {
                        "bins": 5,
                        "counts": [5, 4, 3, 2, 1],
                    },
                },
            ]
        },
        "bias_adjustments": {
            "status": "pass",
            "observed_sharpe": 1.5,
            "deflated_sharpe": 1.3,
            "probabilistic_sharpe": 1.2,
        },
        "cross_validation": {
            "mode": "cpcv",
            "leakage_score": 0.08,
            "bias_flag": False,
            "folds": [
                {"fold_id": "F01", "sharpe": 1.1},
                {"fold_id": "F00", "sharpe": 1.0},
            ],
        },
        "execution_realism": {
            "status": "caution",
            "warnings": [
                "Combined transaction costs and market impact exceed configured budget.",
                "Capacity ratio breaches configured limit; liquidity may be insufficient.",
            ],
            "guidance": [
                "Reduce participation or widen execution schedule to lower cost footprint.",
                "Capacity guidance: trim order size or stage execution to remain within limits.",
            ],
        },
        "metadata": {
            "permutation_shortfalls": [
                {"segment_id": "walk_forward", "requested": 1000, "executed": 800},
                {"segment_id": "in_sample", "requested": 500, "executed": 500},
            ],
            "permutation_fallbacks": [
                {"segment_id": "walk_forward", "reason": "insufficient_data"},
                {"segment_id": "in_sample", "reason": "timeout"},
            ],
            "realism_status": "caution",
        },
        "artifacts": {
            "validation/permutation/segment_in_sample.parquet": {
                "sha256": "a" * 64,
                "size": 1024,
            },
            "validation/permutation/segment_walk_forward.parquet": {
                "sha256": "b" * 64,
                "size": 2048,
            },
        },
    }


def test_validation_manifest_hash_stable_across_order(
    validation_payload: dict[str, object]
) -> None:
    h1 = compute_validation_manifest_hash(validation_payload)
    assert isinstance(h1, str) and len(h1) == 64

    shuffled = deepcopy(validation_payload)
    shuffled_manifest = shuffled["manifest"]  # type: ignore[index]
    assert isinstance(shuffled_manifest, dict)
    segments = shuffled_manifest["permutation_summary"]["segments"]  # type: ignore[index]
    segments.reverse()
    folds = shuffled_manifest["cross_validation"]["folds"]  # type: ignore[index]
    folds.reverse()
    realism = shuffled_manifest["execution_realism"]  # type: ignore[index]
    assert isinstance(realism, dict)
    realism_warnings = realism["warnings"]  # type: ignore[index]
    realism_warnings.reverse()
    caution_checks = shuffled["caution_checks"]  # type: ignore[index]
    assert isinstance(caution_checks, list)
    caution_checks.reverse()
    modules = shuffled["modules"]  # type: ignore[index]
    assert isinstance(modules, dict)
    shuffled["modules"] = {k: modules[k] for k in reversed(list(modules.keys()))}
    permutation_segments = shuffled["permutation"]["segments"]  # type: ignore[index]
    permutation_segments.reverse()
    cv_section = shuffled["cross_validation"]["folds"]  # type: ignore[index]
    cv_section.reverse()
    realism_section = shuffled["execution_realism"]["guidance"]  # type: ignore[index]
    realism_section.reverse()
    realism_warnings_top = shuffled["execution_realism"]["warnings"]  # type: ignore[index]
    realism_warnings_top.reverse()
    metadata = shuffled["metadata"]  # type: ignore[index]
    assert isinstance(metadata, dict)
    metadata["permutation_shortfalls"].reverse()  # type: ignore[index]
    metadata["permutation_fallbacks"].reverse()  # type: ignore[index]
    artifacts = shuffled["artifacts"]  # type: ignore[index]
    assert isinstance(artifacts, dict)
    shuffled["artifacts"] = dict(reversed(list(artifacts.items())))

    h2 = compute_validation_manifest_hash(shuffled)
    assert h1 == h2


def test_validation_manifest_hash_missing_manifest() -> None:
    assert compute_validation_manifest_hash(None) is None
    assert compute_validation_manifest_hash({}) is None
