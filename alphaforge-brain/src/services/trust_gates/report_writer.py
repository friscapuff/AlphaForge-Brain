"""Trust gate report emission utilities."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from infra.utils.hash import canonical_json

from .models import TrustGateResult, TrustGateSummary


def _to_posix(path: Path) -> str:
    return path.as_posix()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(payload), encoding="utf-8")


def _result_payload(result: TrustGateResult) -> dict[str, object]:
    return {
        "name": result.name,
        "status": result.status,
        "metrics": dict(result.metrics),
        "diagnostics": dict(result.diagnostics),
        "artifact": result.artifact,
        "correlation_id": result.correlation_id,
        "duration_ms": result.duration_ms,
        "waiver_ref": result.waiver_ref,
    }


def write_suite_report(
    summary: TrustGateSummary,
    base_dir: Path,
    *,
    run_id: str,
) -> TrustGateSummary:
    """Persist trust gate diagnostics and signed report for a suite summary."""

    report_dir = base_dir / run_id
    report_dir.mkdir(parents=True, exist_ok=True)

    updated_results: list[TrustGateResult] = []
    gate_payloads: list[dict[str, object]] = []

    for result in summary.results:
        diag_name = f"gate_{result.name}_diagnostics.json"
        diag_path = report_dir / diag_name
        _write_json(
            diag_path,
            {
                "metrics": dict(result.metrics),
                "diagnostics": dict(result.diagnostics),
            },
        )
        artifact_ref = _to_posix(diag_path)
        updated_result = replace(
            result,
            artifact=artifact_ref,
            duration_ms=result.duration_ms or 0,
        )
        updated_results.append(updated_result)
        gate_payloads.append(_result_payload(updated_result))

    report_payload = {
        "schema_version": summary.schema_version,
        "suite_id": summary.suite_id,
        "run_id": run_id,
        "status": summary.status,
        "executed_at": summary.executed_at.isoformat().replace("+00:00", "Z"),
        "suite_version": summary.suite_version,
        "config_hash": summary.config_hash,
        "tolerance_profile": summary.tolerance_profile,
        "runtime_ms": summary.runtime_ms,
        "enabled_gates": list(summary.enabled_gates),
        "gates": gate_payloads,
    }

    report_path = report_dir / "trust_gate_report.json"
    _write_json(report_path, report_payload)

    report_bytes = canonical_json(report_payload).encode("utf-8")
    signature = hashlib.sha256(report_bytes).hexdigest()
    signature_path = report_dir / "trust_gate_report.sig"
    signature_path.write_text(signature, encoding="utf-8")

    updated_summary = replace(
        summary,
        results=updated_results,
        report_path=_to_posix(report_path),
        signature_path=_to_posix(signature_path),
    )
    return updated_summary


__all__ = ["write_suite_report"]
