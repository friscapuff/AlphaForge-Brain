"""Sweep orchestrator service for sequential execution and manifest persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

from domain.run.create import InMemoryRunRegistry, create_or_get
from domain.run.orchestrator import build_sweep_execution_plan
from domain.schemas.run_config import RunConfig
from models.manifest import (
    SweepCapStatus,
    SweepCombination,
    SweepCombinationStatus,
    SweepDataQualityStatus,
    SweepManifest,
    SweepParameterAssignment,
    SweepStatus,
    SweepTrustGateCheckpoint,
    SweepTrustGateEvidence,
    TickerSweepManifest,
)
from models.parameter_definition import (
    ParameterCollection,
    ParameterDefinition,
    ParameterDefinitionError,
)
from prometheus_client import CollectorRegistry

from infra.config import get_settings
from infra.utils.hash import canonical_json

from . import telemetry as sweep_telemetry

DEFAULT_SWEEP_ROOT = Path("zz_artifacts") / "sweeps"


@dataclass(slots=True)
class SweepTickerSpec:
    """Per-ticker sweep execution context."""

    symbol: str
    overrides: Mapping[str, Any] | None = None
    timeframe: str | None = None


@dataclass(slots=True)
class SweepExecutionResult:
    """Result bundle produced after executing a sweep."""

    manifest: SweepManifest
    manifest_path: Path
    ticker_manifests: Mapping[str, Path]


def execute_sweep(
    *,
    sweep_id: str,
    base_config: RunConfig,
    parameters: ParameterCollection,
    registry: InMemoryRunRegistry,
    tickers: Sequence[SweepTickerSpec | Mapping[str, Any]] | None = None,
    initiator: str | None = None,
    storage_root: Path | None = None,
    artifacts_base: Path | None = None,
    retry_combination_ids: Sequence[str] | None = None,
    metrics_registry: CollectorRegistry | None = None,
    audit_path: Path | None = None,
    audit_environment: Mapping[str, str] | None = None,
) -> SweepExecutionResult:
    """Execute a parameter sweep sequentially and persist parent/ticker manifests."""

    settings = get_settings()
    combination_cap = settings.sweep_combination_cap
    submitted_at = datetime.now(timezone.utc)
    telemetry_registry = metrics_registry or sweep_telemetry.create_registry()
    sweep_start = perf_counter()

    ticker_specs = _coerce_ticker_specs(tickers, fallback_symbol=base_config.symbol)

    sweep_dir = _ensure_directory((storage_root or DEFAULT_SWEEP_ROOT) / sweep_id)

    all_combinations: list[SweepCombination] = []
    ticker_combinations: dict[str, list[SweepCombination]] = {}
    ticker_payloads: dict[str, Mapping[str, Any]] = {}
    ticker_paths: dict[str, Path] = {}
    ticker_stats: dict[str, dict[str, int]] = {}
    ticker_cap_status: dict[str, SweepCapStatus] = {}
    ticker_partial_reasons: dict[str, str | None] = {}
    ticker_guardrails: dict[str, dict[str, Any]] = {}
    ticker_data_quality: dict[str, SweepDataQualityStatus] = {}
    ticker_variance: dict[str, dict[str, float | int]] = {}
    ticker_latencies: dict[str, int] = {}

    retry_set = {cid for cid in (retry_combination_ids or [])}

    notes: list[str] = []
    if retry_set:
        notes.append("SWEEP_RETRY_EXECUTION")

    for spec in ticker_specs:
        ticker_timer = perf_counter()
        ticker_config = _apply_ticker_config(base_config, spec)
        ticker_parameters = merge_parameter_overrides(parameters, spec.overrides)
        plan = build_sweep_execution_plan(ticker_config, ticker_parameters)
        plan_count = len(plan)

        guardrail_info: dict[str, Any] = {
            "requested_combinations": plan_count,
            "combination_cap": combination_cap,
        }

        cap_hit = combination_cap > 0 and plan_count > combination_cap
        if cap_hit:
            ticker_cap_status[spec.symbol] = SweepCapStatus.HIT
            ticker_partial_reasons[spec.symbol] = "cap_hit"
            guardrail_info["cap_status"] = SweepCapStatus.HIT.value
            if "OPTIMIZATION_SWEEP_LIMIT_HIT" not in notes:
                notes.append("OPTIMIZATION_SWEEP_LIMIT_HIT")
            data_quality_status = SweepDataQualityStatus.REVIEW
            ticker_variance[spec.symbol] = {}
        else:
            ticker_cap_status[spec.symbol] = SweepCapStatus.OK
            ticker_partial_reasons[spec.symbol] = None
            guardrail_info["cap_status"] = SweepCapStatus.OK.value
            data_quality_status = SweepDataQualityStatus.PASS
            ticker_variance[spec.symbol] = {
                "pnl_delta_bps": 0.0,
                "drawdown_delta_pct": 0.0,
                "trade_count_delta": 0,
            }

        ticker_data_quality[spec.symbol] = data_quality_status
        guardrail_info["data_quality_status"] = data_quality_status.value
        ticker_guardrails[spec.symbol] = guardrail_info

        combos_for_ticker: list[SweepCombination] = []
        stats = {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0}
        for entry in plan:
            combination_id = f"{spec.symbol}::{entry.combination_id}"
            should_execute = (not cap_hit) and (
                not retry_set or combination_id in retry_set
            )
            started_at: datetime | None = None
            completed_at: datetime | None = None
            run_hash: str | None = None
            status = SweepCombinationStatus.SUCCEEDED
            trust_gate_summary = None
            if should_execute:
                started_at = datetime.now(timezone.utc)
                run_hash, _record, _created = create_or_get(
                    entry.run_config,
                    registry,
                    seed=entry.run_config.seed,
                    artifacts_base=artifacts_base,
                )
                completed_at = datetime.now(timezone.utc)
                stats["succeeded"] += 1
            else:
                status = SweepCombinationStatus.SKIPPED
                stats["skipped"] += 1
            stats["total"] += 1
            combo = SweepCombination(
                combination_id=combination_id,
                parameters=[
                    SweepParameterAssignment(name=name, value=value)
                    for name, value in entry.parameters.items()
                ],
                run_hash=run_hash,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                trust_gate_summary=trust_gate_summary,
            )
            combos_for_ticker.append(combo)
            all_combinations.append(combo)
        guardrail_info["executed_combinations"] = stats["succeeded"]
        guardrail_info["skipped_combinations"] = stats["skipped"]
        ticker_duration_ms = int((perf_counter() - ticker_timer) * 1000)
        guardrail_info["latency_ms"] = ticker_duration_ms
        ticker_latencies[spec.symbol] = ticker_duration_ms
        ticker_combinations[spec.symbol] = combos_for_ticker
        ticker_payloads[spec.symbol] = ticker_parameters.as_payload()
        ticker_stats[spec.symbol] = stats
        ticker_manifest_path = _write_ticker_manifest(
            sweep_dir=sweep_dir,
            sweep_id=sweep_id,
            ticker=spec.symbol,
            combinations=combos_for_ticker,
            normalized_parameters=ticker_payloads[spec.symbol],
            guardrail=guardrail_info,
        )
        ticker_paths[spec.symbol] = ticker_manifest_path

        sweep_telemetry.record_checkpoint(
            registry=telemetry_registry,
            sweep_id=sweep_id,
            ticker=spec.symbol,
            checkpoint="orchestrator",
            duration_ms=ticker_duration_ms,
            combination_cap=combination_cap,
            requested=plan_count,
            executed=stats["succeeded"],
            skipped=stats["skipped"],
            cap_status=ticker_cap_status[spec.symbol].value,
            data_quality_status=data_quality_status.value,
            audit_path=audit_path,
            environment=audit_environment,
        )
        if cap_hit:
            sweep_telemetry.record_guardrail_event(
                registry=telemetry_registry,
                sweep_id=sweep_id,
                ticker=spec.symbol,
                reason="combination_cap",
                requested=plan_count,
                cap=combination_cap,
                cap_status=ticker_cap_status[spec.symbol].value,
                data_quality_status=data_quality_status.value,
                audit_path=audit_path,
                environment=audit_environment,
            )

    overall_cap_status = (
        SweepCapStatus.HIT
        if any(status is SweepCapStatus.HIT for status in ticker_cap_status.values())
        else SweepCapStatus.OK
    )
    if ticker_data_quality:
        if any(
            status is SweepDataQualityStatus.FAIL
            for status in ticker_data_quality.values()
        ):
            overall_data_quality = SweepDataQualityStatus.FAIL
        elif any(
            status is SweepDataQualityStatus.REVIEW
            for status in ticker_data_quality.values()
        ):
            overall_data_quality = SweepDataQualityStatus.REVIEW
        else:
            overall_data_quality = SweepDataQualityStatus.PASS
    else:
        overall_data_quality = SweepDataQualityStatus.PASS
    orchestrator_latency_ms = int((perf_counter() - sweep_start) * 1000)
    orchestrator_notes = (
        ["OPTIMIZATION_SWEEP_LIMIT_HIT"]
        if overall_cap_status is SweepCapStatus.HIT
        else []
    )

    if notes:
        seen_notes: set[str] = set()
        unique_notes: list[str] = []
        for note in notes:
            if note not in seen_notes:
                seen_notes.add(note)
                unique_notes.append(note)
        notes = unique_notes

    trust_gates = SweepTrustGateEvidence(
        payload_validation=SweepTrustGateCheckpoint(
            sanitized_parameters={"parameters": parameters.as_payload()}
        ),
        normalization=SweepTrustGateCheckpoint(
            sanitized_parameters={
                "base": parameters.as_payload(),
                "per_ticker": ticker_payloads,
            }
        ),
        orchestrator=SweepTrustGateCheckpoint(
            sanitized_parameters={
                "combination_cap": combination_cap,
                "retry_requested": bool(retry_set),
                "retry_combination_ids": sorted(retry_set) if retry_set else None,
                "ticker_guardrails": ticker_guardrails,
            },
            cap_status=overall_cap_status,
            data_quality_status=overall_data_quality,
            latency_ms=orchestrator_latency_ms,
            notes=orchestrator_notes,
        ),
        manifest=SweepTrustGateCheckpoint(
            sanitized_parameters={
                "combination_ids": [combo.combination_id for combo in all_combinations],
                "cap_status_per_ticker": {
                    symbol: status.value for symbol, status in ticker_cap_status.items()
                },
                "data_quality_status_per_ticker": {
                    symbol: status.value
                    for symbol, status in ticker_data_quality.items()
                },
                "latency_ms_per_ticker": dict(ticker_latencies),
            },
            cap_status=overall_cap_status,
            data_quality_status=overall_data_quality,
            notes=orchestrator_notes,
        ),
    )

    succeeded_count = sum(
        1
        for combo in all_combinations
        if combo.status == SweepCombinationStatus.SUCCEEDED
    )
    failed_count = sum(
        1 for combo in all_combinations if combo.status == SweepCombinationStatus.FAILED
    )
    skipped_count = sum(
        1
        for combo in all_combinations
        if combo.status == SweepCombinationStatus.SKIPPED
    )

    derived_metrics = {
        "total_combinations": len(all_combinations),
        "succeeded_combinations": succeeded_count,
        "failed_combinations": failed_count,
        "skipped_combinations": skipped_count,
        "per_ticker_totals": ticker_stats,
        "cap_status_per_ticker": {
            symbol: status.value for symbol, status in ticker_cap_status.items()
        },
        "data_quality_status_per_ticker": {
            symbol: status.value for symbol, status in ticker_data_quality.items()
        },
        "latency_ms_per_ticker": dict(ticker_latencies),
        "orchestrator_latency_ms": orchestrator_latency_ms,
    }

    manifest = SweepManifest(
        sweep_id=sweep_id,
        status=(
            SweepStatus.FAILED
            if overall_cap_status is SweepCapStatus.HIT
            else SweepStatus.COMPLETED
        ),
        submitted_at=submitted_at,
        completed_at=datetime.now(timezone.utc),
        initiator=initiator,
        parameter_definitions=[defn.model_copy(deep=True) for defn in parameters],
        combinations=all_combinations,
        tickers=[
            TickerSweepManifest(
                ticker=symbol,
                combination_cap=combination_cap,
                cap_status=ticker_cap_status.get(symbol, SweepCapStatus.OK),
                data_quality_status=ticker_data_quality.get(
                    symbol, SweepDataQualityStatus.PASS
                ),
                variance_metrics=ticker_variance.get(symbol, {}),
                manifest_path=ticker_paths[symbol].as_posix(),
                partial_execution_reason=ticker_partial_reasons.get(symbol),
            )
            for symbol in ticker_combinations
        ],
        combination_cap=combination_cap,
        derived_metrics=derived_metrics,
        notes=notes,
        trust_gates=trust_gates,
    )

    manifest_path = sweep_dir / "manifest.json"
    write_started = perf_counter()
    _write_json(manifest_path, manifest.to_storage_dict())
    manifest_latency_ms = int((perf_counter() - write_started) * 1000)
    sweep_telemetry.record_checkpoint(
        registry=telemetry_registry,
        sweep_id=sweep_id,
        ticker="__aggregate__",
        checkpoint="manifest",
        duration_ms=manifest_latency_ms,
        combination_cap=combination_cap,
        requested=len(all_combinations),
        executed=succeeded_count,
        skipped=skipped_count,
        cap_status=overall_cap_status.value,
        data_quality_status=overall_data_quality.value,
        audit_path=audit_path,
        environment=audit_environment,
    )
    updated_derived_metrics = dict(manifest.derived_metrics)
    updated_derived_metrics["manifest_latency_ms"] = manifest_latency_ms
    updated_derived_metrics["overall_data_quality_status"] = overall_data_quality.value
    updated_trust_gates = manifest.trust_gates
    if manifest.trust_gates.manifest is not None:
        updated_trust_gates = manifest.trust_gates.model_copy(
            update={
                "manifest": manifest.trust_gates.manifest.model_copy(
                    update={"latency_ms": manifest_latency_ms}
                )
            }
        )
    manifest = manifest.model_copy(
        update={
            "derived_metrics": updated_derived_metrics,
            "trust_gates": updated_trust_gates,
        }
    )

    return SweepExecutionResult(
        manifest=manifest,
        manifest_path=manifest_path,
        ticker_manifests=ticker_paths,
    )


def _coerce_ticker_specs(
    tickers: Sequence[SweepTickerSpec | Mapping[str, Any]] | None,
    *,
    fallback_symbol: str,
) -> list[SweepTickerSpec]:
    if not tickers:
        return [SweepTickerSpec(symbol=fallback_symbol)]
    specs: list[SweepTickerSpec] = []
    for entry in tickers:
        if isinstance(entry, SweepTickerSpec):
            specs.append(entry)
            continue
        if not isinstance(entry, Mapping):
            raise ValueError(
                "Ticker specification must be a mapping or SweepTickerSpec"
            )
        symbol = entry.get("symbol") or fallback_symbol
        overrides = entry.get("overrides")
        timeframe = entry.get("timeframe")
        specs.append(
            SweepTickerSpec(
                symbol=str(symbol),
                overrides=overrides if isinstance(overrides, Mapping) else None,
                timeframe=str(timeframe) if timeframe else None,
            )
        )
    return specs


def _apply_ticker_config(base: RunConfig, spec: SweepTickerSpec) -> RunConfig:
    config = base.model_copy(deep=True)
    object.__setattr__(config, "symbol", spec.symbol)
    if spec.timeframe:
        object.__setattr__(config, "timeframe", spec.timeframe)
    return config


def merge_parameter_overrides(
    base: ParameterCollection, overrides: Mapping[str, Any] | None
) -> ParameterCollection:
    override_defs: dict[str, ParameterDefinition] = {}
    if overrides:
        for name, payload in overrides.items():
            if isinstance(payload, ParameterDefinition):
                override_defs[name] = payload
            else:
                try:
                    override_defs[name] = ParameterDefinition.from_payload(
                        name, payload
                    )
                except (ValueError, ParameterDefinitionError) as exc:
                    raise ParameterDefinitionError(
                        f"Invalid override for parameter '{name}': {exc}"
                    ) from exc
    merged: list[ParameterDefinition] = []
    seen: set[str] = set()
    for definition in base:
        candidate = override_defs.get(definition.name)
        if candidate is not None:
            merged.append(candidate)
            seen.add(definition.name)
        else:
            merged.append(definition)
            seen.add(definition.name)
    for name, definition in override_defs.items():
        if name not in seen:
            merged.append(definition)
    result_defs = [definition.model_copy(deep=True) for definition in merged]
    return ParameterCollection(result_defs)


def _write_ticker_manifest(
    *,
    sweep_dir: Path,
    sweep_id: str,
    ticker: str,
    combinations: Sequence[SweepCombination],
    normalized_parameters: Mapping[str, Any],
    guardrail: Mapping[str, Any] | None = None,
) -> Path:
    ticker_dir = _ensure_directory(sweep_dir / _slugify_ticker(ticker))
    payload = {
        "sweep_id": sweep_id,
        "ticker": ticker,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "combinations": [
            {
                "combination_id": combo.combination_id,
                "run_hash": combo.run_hash,
                "status": combo.status.value,
                "parameters": {
                    assignment.name: assignment.value for assignment in combo.parameters
                },
            }
            for combo in combinations
        ],
        "normalized_parameters": normalized_parameters,
    }
    if guardrail:
        payload["guardrail"] = dict(guardrail)
    manifest_path = ticker_dir / "manifest.json"
    _write_json(manifest_path, payload)
    return manifest_path


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = canonical_json(payload)
    path.write_text(text, encoding="utf-8")


_SLUG_REGEX = re.compile(r"[^A-Za-z0-9_-]+")


def _slugify_ticker(symbol: str) -> str:
    slug = _SLUG_REGEX.sub("_", symbol.upper())
    return slug.strip("_") or "TICKER"


__all__ = [
    "DEFAULT_SWEEP_ROOT",
    "SweepExecutionResult",
    "SweepTickerSpec",
    "execute_sweep",
    "merge_parameter_overrides",
]
