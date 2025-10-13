"""Tolerance profile loader for trust gate enforcement (US1/T009)."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from services.audit.governance_logger import record_governance_event

from infra.utils.hash import hash_canonical

_ROOT = Path(__file__).resolve().parents[4]
_PROFILES_DIR = _ROOT / "configs" / "trust_gates" / "tolerances"


class ToleranceConfigError(RuntimeError):
    """Raised when a tolerance configuration cannot be loaded or validated."""

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason or "unknown"


@dataclass(frozen=True)
class ToleranceMetric:
    """Single metric tolerance specification."""

    comparator: str
    threshold: float
    severity: str = "fail"
    description: str | None = None

    def within_bounds(self, value: float) -> bool:
        op = self.comparator
        if op == "<":
            return value < self.threshold
        if op == "<=":
            return value <= self.threshold
        if op == ">":
            return value > self.threshold
        if op == ">=":
            return value >= self.threshold
        if op in {"=", "=="}:
            return value == self.threshold
        raise ToleranceConfigError(
            f"Unsupported comparator '{op}' in tolerance metric",
            reason="invalid_metric",
        )


@dataclass(frozen=True)
class ToleranceProfile:
    """Container for tolerance metadata and metric specifications."""

    profile_id: str
    version: str
    schema_version: str
    metrics: dict[str, ToleranceMetric]
    metadata: Mapping[str, Any]
    source_path: Path
    config_hash: str

    def metric(self, name: str) -> ToleranceMetric:
        try:
            return self.metrics[name]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ToleranceConfigError(
                f"Metric '{name}' missing from tolerance profile {self.profile_id}",
                reason="invalid_metric",
            ) from exc


def _load_raw_profile(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ToleranceConfigError(
            f"tolerance profile not found at {path}",
            reason="not_found",
        ) from exc

    data: Mapping[str, Any]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            yaml_module = importlib.import_module("yaml")
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise ToleranceConfigError(
                "Tolerance profile is YAML but PyYAML is not installed; install PyYAML or provide JSON payload.",
                reason="dependency_missing",
            ) from exc
        try:
            loaded = yaml_module.safe_load(text)
        except Exception as exc:  # pragma: no cover - propagate parse failure
            raise ToleranceConfigError(
                f"Failed to parse tolerance profile at {path}: {exc}",
                reason="invalid_format",
            ) from exc
        if not isinstance(loaded, Mapping):
            raise ToleranceConfigError(
                "Tolerance profile must deserialize to a mapping object",
                reason="invalid_format",
            ) from None
        data = loaded
    if not isinstance(data, Mapping):
        raise ToleranceConfigError(
            "Tolerance profile must be an object mapping",
            reason="invalid_format",
        )
    return data


def _normalise_metric(name: str, payload: Mapping[str, Any]) -> ToleranceMetric:
    comparator = str(payload.get("comparator", "")).strip()
    if comparator not in {"<", "<=", ">", ">=", "=", "=="}:
        raise ToleranceConfigError(
            f"Metric '{name}' comparator must be one of <, <=, >, >=, ==",
            reason="invalid_metric",
        )
    threshold_raw = payload.get("threshold")
    if threshold_raw is None:
        raise ToleranceConfigError(
            f"Metric '{name}' threshold must be provided",
            reason="invalid_metric",
        )
    try:
        threshold = float(threshold_raw)
    except (TypeError, ValueError) as exc:
        raise ToleranceConfigError(
            f"Metric '{name}' threshold must be numeric",
            reason="invalid_metric",
        ) from exc
    severity = str(payload.get("severity", "fail")).strip() or "fail"
    description = payload.get("description")
    if description is not None:
        description = str(description)
    return ToleranceMetric(
        comparator=comparator,
        threshold=threshold,
        severity=severity,
        description=description,
    )


def _build_profile(path: Path, data: Mapping[str, Any]) -> ToleranceProfile:
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ToleranceConfigError(
            "Tolerance profile missing schema_version",
            reason="invalid_profile",
        )
    profile_id = data.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise ToleranceConfigError(
            "Tolerance profile missing profile_id",
            reason="invalid_profile",
        )
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ToleranceConfigError(
            "Tolerance profile missing version metadata",
            reason="invalid_profile",
        )
    metrics_payload = data.get("metrics")
    if not isinstance(metrics_payload, Mapping) or not metrics_payload:
        raise ToleranceConfigError(
            "Tolerance profile metrics block must be a mapping",
            reason="invalid_profile",
        )
    metrics: dict[str, ToleranceMetric] = {}
    for key, value in metrics_payload.items():
        if not isinstance(key, str):
            raise ToleranceConfigError(
                "Metric names must be strings",
                reason="invalid_metric",
            )
        if not isinstance(value, Mapping):
            raise ToleranceConfigError(
                f"Metric '{key}' must be a mapping",
                reason="invalid_metric",
            )
        metrics[key] = _normalise_metric(key, value)
    metadata = data.get("metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    config_hash = hash_canonical(data)
    return ToleranceProfile(
        profile_id=profile_id.strip(),
        version=version.strip(),
        schema_version=schema_version.strip(),
        metrics=metrics,
        metadata=metadata,
        source_path=path,
        config_hash=config_hash,
    )


@lru_cache(maxsize=16)
def load_tolerance_profile(profile_name: str) -> ToleranceProfile:
    """Load and cache the tolerance profile identified by ``profile_name``."""

    if not profile_name or not profile_name.strip():
        raise ToleranceConfigError(
            "Tolerance profile name must be provided",
            reason="invalid_request",
        )
    path = _PROFILES_DIR / f"{profile_name}.yaml"
    try:
        data = _load_raw_profile(path)
        return _build_profile(path, data)
    except ToleranceConfigError as exc:
        record_governance_event(
            message="trust_gate.tolerance_profile_error",
            details={
                "profile": profile_name,
                "path": str(path),
                "reason": getattr(exc, "reason", "unknown"),
                "error": str(exc),
            },
        )
        raise


__all__ = [
    "ToleranceConfigError",
    "ToleranceMetric",
    "ToleranceProfile",
    "load_tolerance_profile",
]
