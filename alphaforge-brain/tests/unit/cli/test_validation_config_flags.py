from __future__ import annotations

import os
from importlib import import_module

import pytest

xfail_cli_validation = pytest.mark.xfail(
    reason="Validation CLI flags not implemented",
    strict=False,
)

try:  # pragma: no cover - module expected in later phase
    _module = import_module("src.services.cli.validation_flags")
except ImportError as exc:  # pragma: no cover - exercised via xfail path
    ValidationConfigFlags = None  # type: ignore[assignment]
    resolve_validation_config = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:  # pragma: no cover - future success path
    ValidationConfigFlags = getattr(_module, "ValidationConfigFlags", None)
    resolve_validation_config = getattr(_module, "resolve_validation_config", None)
    if ValidationConfigFlags is None or resolve_validation_config is None:
        _IMPORT_ERROR = ImportError("Validation CLI exports missing")
    else:
        _IMPORT_ERROR = None


@xfail_cli_validation
def test_validation_flag_defaults_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if resolve_validation_config is None:
        pytest.xfail(f"validation CLI module unavailable: {_IMPORT_ERROR}")

    for key in [
        "AF_VALIDATION_MODULES",
        "AF_VALIDATION_PERMUTATION_COUNT",
        "AF_VALIDATION_SIGNIFICANCE_THRESHOLD",
        "AF_LEAKAGE_THRESHOLD",
        "AF_REALISM_CAPACITY_BPS_LIMIT",
    ]:
        monkeypatch.delenv(key, raising=False)

    flags = resolve_validation_config(cli_args=(), env=os.environ.copy())

    assert isinstance(flags, ValidationConfigFlags)
    assert flags.modules == [
        "permutation",
        "dsr",
        "psr",
        "purged_kfold",
        "cpcv",
        "realism",
    ]
    assert flags.permutation_count == 500
    assert flags.significance_threshold == pytest.approx(0.01, rel=1e-9)
    assert flags.leakage_threshold == pytest.approx(0.1, rel=1e-9)
    assert flags.capacity_limit_bps == 500

    manifest_fragment = flags.to_manifest_fragment()
    assert manifest_fragment["modules"] == flags.modules
    assert manifest_fragment["permutation_count"] == flags.permutation_count


@xfail_cli_validation
def test_cli_overrides_and_env_merge_preserve_sort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if resolve_validation_config is None:
        pytest.xfail(f"validation CLI module unavailable: {_IMPORT_ERROR}")

    monkeypatch.setenv("AF_VALIDATION_MODULES", "permutation,realism")
    monkeypatch.setenv("AF_VALIDATION_PERMUTATION_COUNT", "250")
    monkeypatch.setenv("AF_VALIDATION_SIGNIFICANCE_THRESHOLD", "0.02")

    flags = resolve_validation_config(
        cli_args=(
            "--validation-modules",
            "psr,cpcv",
            "--significance-threshold",
            "0.015",
        ),
        env=os.environ.copy(),
    )

    assert flags.modules == ["cpcv", "psr"]
    assert flags.permutation_count == 250
    assert flags.significance_threshold == pytest.approx(0.015, rel=1e-9)

    metadata_hash_1 = flags.stable_hash()
    flags_again = resolve_validation_config(
        cli_args=(
            "--validation-modules",
            "psr,cpcv",
            "--significance-threshold",
            "0.015",
        ),
        env=os.environ.copy(),
    )
    assert flags_again.modules == flags.modules
    assert flags_again.stable_hash() == metadata_hash_1
