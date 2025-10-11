"""Trust gate suite orchestration."""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Iterable, Mapping, MutableSequence, Sequence

from .baseline import TrustGateBaseline, load_baseline
from .models import TrustGateResult, TrustGateSummary

DEFAULT_GATE_ORDER = (
    "golden_run",
    "causality",
    "ingest_idempotency",
    "timezone",
    "universe_stamp",
    "equity_reconciliation",
    "accounting",
)

_GATE_MODULE_MAP = {
    "golden_run": "golden_run",
    "causality": "causality",
    "ingest_idempotency": "ingest",
    "timezone": "timezone",
    "universe_stamp": "universe",
    "equity_reconciliation": "equity",
    "accounting": "accounting",
}


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
    ) -> TrustGateSummary:
        gates = tuple(only) if only else DEFAULT_GATE_ORDER
        for gate in gates:
            if gate not in _GATE_MODULE_MAP:
                raise UnknownGateError(f"Unknown trust gate: {gate}")

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
                report_path=None,
                config_hash=config_hash,
                enabled_gates=list(gates),
            )
            if suite_id_override:
                summary = replace(summary, suite_id=suite_id_override)
            return summary

        results: MutableSequence[TrustGateResult] = []
        start = perf_counter()

        manifest = candidate_manifest or self._baseline.manifest_snapshot

        for gate in gates:
            module_name = _GATE_MODULE_MAP[gate]
            module = importlib.import_module(
                f"services.trust_gates.gates.{module_name}"
            )
            evaluate = module.evaluate
            if gate == "golden_run":
                result = evaluate(candidate_manifest=manifest, baseline=self._baseline)
            else:
                result = evaluate(baseline=self._baseline)
            if not isinstance(result, TrustGateResult):
                raise TypeError(
                    f"Gate '{gate}' returned unexpected type {type(result)!r}; expected TrustGateResult."
                )
            results.append(result)

        runtime_ms = int((perf_counter() - start) * 1000)
        status = "pass" if all(not result.is_failure for result in results) else "fail"
        summary = TrustGateSummary(
            status=status,
            results=list(results),
            runtime_ms=runtime_ms,
            tolerance_profile=self._tolerance_profile,
            report_path=None,
            config_hash=config_hash or self._baseline.config_hash,
            enabled_gates=list(gates),
        )
        if suite_id_override:
            summary = replace(summary, suite_id=suite_id_override)
        return summary
