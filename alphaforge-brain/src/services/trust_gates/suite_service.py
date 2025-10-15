"""Trust gate suite orchestration."""

from __future__ import annotations

import importlib
import inspect
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable, Mapping, MutableSequence, Sequence, cast

from prometheus_client import CollectorRegistry
from services.audit.governance_logger import append_audit_log, record_governance_event

from . import telemetry
from .baseline import TrustGateBaseline, load_baseline
from .config_loader import (
    ToleranceConfigError,
    ToleranceProfile,
    load_tolerance_profile,
)
from .models import TrustGateResult, TrustGateSummary

DEFAULT_GATE_ORDER = (
    "golden_run",
    "causality",
    "ingest_idempotency",
    "timezone",
    "universe_stamp",
    "equity_reconciliation",
    "accounting",
    "journaling",
)

_GATE_MODULE_MAP = {
    "golden_run": "golden_run",
    "causality": "causality",
    "ingest_idempotency": "ingest",
    "timezone": "timezone",
    "universe_stamp": "universe",
    "equity_reconciliation": "equity",
    "accounting": "accounting",
    "journaling": "journaling",
}

_TRUST_GATES_LATENCY_LOG = Path("zz_artifacts/governance/trust_gates_latency.jsonl")


class UnknownGateError(ValueError):
    """Raised when a requested gate name is not recognised."""


class TrustGateSuiteService:
    """Evaluate the configured trust gate suite for a run manifest."""

    def __init__(
        self, report_dir: Path | None = None, tolerance_profile: str | None = None
    ) -> None:
        self._baseline = load_baseline()
        self._report_dir = Path(report_dir or "artifacts/trust_gates/reports")
        self._tolerance_profile = tolerance_profile or self._baseline.tolerance_profile

    @property
    def baseline(self) -> TrustGateBaseline:  # pragma: no cover - simple getter
        return self._baseline

    @property
    def tolerance_profile(self) -> str:
        return self._tolerance_profile

    def available_gates(self) -> Sequence[str]:
        return DEFAULT_GATE_ORDER

    def run(
        self,
        *,
        only: Iterable[str] | None = None,
        dry_run: bool = False,
        candidate_manifest: Mapping[str, object] | None = None,
        run_id: str | None = None,
        config_hash: str | None = None,
        registry: CollectorRegistry | None = None,
    ) -> TrustGateSummary:
        metrics_registry = registry or telemetry.create_registry()
        gates = tuple(only) if only else DEFAULT_GATE_ORDER
        for gate in gates:
            if gate not in _GATE_MODULE_MAP:
                raise UnknownGateError(f"Unknown trust gate: {gate}")

        tolerance_profile: ToleranceProfile | None = None
        try:
            tolerance_profile = load_tolerance_profile(self._tolerance_profile)
        except ToleranceConfigError as exc:
            telemetry.emit_config_error(
                registry=metrics_registry,
                gate="causality",
                profile=self._tolerance_profile,
                reason=getattr(exc, "reason", "unknown"),
            )
            if not dry_run:
                raise
        manifest = candidate_manifest or self._baseline.manifest_snapshot

        suite_id_override = f"{run_id}:trust_suite" if run_id else None
        if dry_run:
            # Skip execution but provide structural summary for callers.
            placeholder_results = [
                TrustGateResult(name=gate, status="dry-run", metrics={}, diagnostics={})
                for gate in gates
            ]
            summary = TrustGateSummary(
                status="dry-run",
                results=placeholder_results,
                runtime_ms=0,
                tolerance_profile=self._tolerance_profile,
                tolerance_profile_version=(
                    tolerance_profile.version if tolerance_profile else None
                ),
                tolerance_profile_hash=(
                    tolerance_profile.config_hash if tolerance_profile else None
                ),
                report_path=None,
                config_hash=config_hash or self._baseline.config_hash,
                enabled_gates=list(gates),
            )
            if suite_id_override:
                summary = replace(summary, suite_id=suite_id_override)
            return summary

        results: MutableSequence[TrustGateResult] = []
        start = perf_counter()

        for gate in gates:
            module_name = _GATE_MODULE_MAP[gate]
            module = importlib.import_module(
                f"services.trust_gates.gates.{module_name}"
            )
            evaluate = cast(Callable[..., TrustGateResult], module.evaluate)
            parameters = inspect.signature(evaluate).parameters
            kwargs: dict[str, object] = {}
            if "baseline" in parameters:
                kwargs["baseline"] = self._baseline
            if "candidate_manifest" in parameters:
                kwargs["candidate_manifest"] = manifest
            if "tolerance_profile" in parameters and tolerance_profile is not None:
                kwargs["tolerance_profile"] = tolerance_profile
            if "run_id" in parameters and run_id is not None:
                kwargs["run_id"] = run_id
            gate_start = perf_counter()
            result = evaluate(**kwargs)
            if not isinstance(result, TrustGateResult):
                raise TypeError(
                    f"Gate '{gate}' returned unexpected type {type(result)!r}; expected TrustGateResult."
                )
            gate_duration_ms = int((perf_counter() - gate_start) * 1000)
            result = replace(result, duration_ms=gate_duration_ms)
            results.append(result)
            telemetry.emit_gate_metrics(
                registry=metrics_registry,
                gate=gate,
                status=result.status,
                duration_ms=gate_duration_ms,
                profile=self._tolerance_profile,
            )

        runtime_ms = int((perf_counter() - start) * 1000)
        status = "pass" if all(not result.is_failure for result in results) else "fail"
        summary = TrustGateSummary(
            status=status,
            results=list(results),
            runtime_ms=runtime_ms,
            tolerance_profile=self._tolerance_profile,
            tolerance_profile_version=(
                tolerance_profile.version if tolerance_profile else None
            ),
            tolerance_profile_hash=(
                tolerance_profile.config_hash if tolerance_profile else None
            ),
            report_path=None,
            config_hash=config_hash or self._baseline.config_hash,
            enabled_gates=list(gates),
        )
        if suite_id_override:
            summary = replace(summary, suite_id=suite_id_override)

        try:
            manifest_payload = summary.manifest_block()
            encoded_manifest = json.dumps(
                manifest_payload, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            telemetry.emit_manifest_payload_size(
                registry=metrics_registry,
                profile=self._tolerance_profile,
                size_bytes=len(encoded_manifest),
            )
        except Exception:  # pragma: no cover - defensive emission guard
            struct_payload = {
                "suite_id": summary.suite_id,
                "profile": self._tolerance_profile,
            }
            record_governance_event(
                message="trust_gates.manifest_serialization_failure",
                details=struct_payload,
            )

        details_payload: dict[str, object] = {
            "run_id": run_id,
            "status": status,
            "runtime_ms": runtime_ms,
            "threshold_ms": 5000,
            "within_sla": runtime_ms <= 5000,
            "tolerance_profile": self._tolerance_profile,
            "tolerance_profile_version": summary.tolerance_profile_version,
            "tolerance_profile_hash": summary.tolerance_profile_hash,
            "config_hash": summary.config_hash,
            "enabled_gates": summary.enabled_gates,
        }
        latency_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "trust_gates.suite_runtime",
            "details": details_payload,
        }
        append_audit_log(payload=latency_payload, audit_path=_TRUST_GATES_LATENCY_LOG)
        record_governance_event(
            message="trust_gates.suite_runtime",
            details=details_payload,
        )
        return summary
