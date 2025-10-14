"""Telemetry helpers for sweep execution guardrails and checkpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import structlog
from prometheus_client import CollectorRegistry, Counter, Histogram
from services.audit.governance_logger import (
    append_audit_log,
    emit_governance_metric,
)

logger = structlog.get_logger("sweeps")


@dataclass(slots=True)
class _SweepMetrics:
    checkpoint_latency: Histogram
    combinations_total: Counter
    guardrail_events: Counter


_REGISTRIES: dict[int, _SweepMetrics] = {}
_DEFAULT_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def _ensure_metrics(registry: CollectorRegistry) -> _SweepMetrics:
    key = id(registry)
    cached = _REGISTRIES.get(key)
    if cached is not None:
        return cached
    latency_hist = Histogram(
        "sweep_checkpoint_latency_seconds",
        "Latency of sweep checkpoints",
        labelnames=(
            "sweep_id",
            "ticker",
            "checkpoint",
            "cap_status",
            "data_quality_status",
        ),
        registry=registry,
        buckets=_DEFAULT_BUCKETS,
    )
    combinations_counter = Counter(
        "sweep_combinations_total",
        "Total combinations processed during a sweep checkpoint",
        labelnames=(
            "sweep_id",
            "ticker",
            "checkpoint",
            "cap_status",
            "data_quality_status",
        ),
        registry=registry,
    )
    guardrail_counter = Counter(
        "sweep_guardrail_events_total",
        "Sweep guardrail events",
        labelnames=(
            "sweep_id",
            "ticker",
            "reason",
            "cap_status",
            "data_quality_status",
        ),
        registry=registry,
    )
    metrics = _SweepMetrics(
        checkpoint_latency=latency_hist,
        combinations_total=combinations_counter,
        guardrail_events=guardrail_counter,
    )
    _REGISTRIES[key] = metrics
    return metrics


def create_registry() -> CollectorRegistry:
    """Return a dedicated CollectorRegistry for sweep telemetry metrics."""

    registry = CollectorRegistry()
    _ensure_metrics(registry)
    return registry


def record_checkpoint(
    *,
    registry: CollectorRegistry,
    sweep_id: str,
    ticker: str,
    checkpoint: str,
    duration_ms: int,
    combination_cap: int,
    requested: int,
    executed: int,
    skipped: int,
    cap_status: str,
    data_quality_status: str,
    audit_path: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Emit telemetry samples and audit log entry for a sweep checkpoint."""

    metrics = _ensure_metrics(registry)
    seconds = max(duration_ms, 0) / 1000.0
    labels = {
        "sweep_id": sweep_id,
        "ticker": ticker,
        "checkpoint": checkpoint,
        "cap_status": cap_status,
        "data_quality_status": data_quality_status,
    }
    metrics.checkpoint_latency.labels(**labels).observe(seconds)
    metrics.combinations_total.labels(**labels).inc(max(executed, 0))
    payload = {
        "message": "sweep.checkpoint",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "sweep_id": sweep_id,
        "ticker": ticker,
        "checkpoint": checkpoint,
        "cap_status": cap_status,
        "data_quality_status": data_quality_status,
        "duration_ms": duration_ms,
        "requested_combinations": requested,
        "executed_combinations": executed,
        "skipped_combinations": skipped,
        "combination_cap": combination_cap,
    }
    append_audit_log(payload=payload, audit_path=audit_path, environment=environment)
    emit_governance_metric(
        registry=registry,
        name="sweep_checkpoint",
        description="Sweep checkpoint telemetry",
        labels={
            "event_type": "sweep_checkpoint",
            "checkpoint": checkpoint,
            "reason": "n/a",
            "cap_status": cap_status,
            "data_quality_status": data_quality_status,
        },
    )
    logger.info("sweep.checkpoint", **payload)
    return payload


def record_guardrail_event(
    *,
    registry: CollectorRegistry,
    sweep_id: str,
    ticker: str,
    reason: str,
    requested: int,
    cap: int,
    cap_status: str,
    data_quality_status: str,
    audit_path: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Log a guardrail event (e.g., combination cap hit) with telemetry."""

    metrics = _ensure_metrics(registry)
    labels = {
        "sweep_id": sweep_id,
        "ticker": ticker,
        "reason": reason,
        "cap_status": cap_status,
        "data_quality_status": data_quality_status,
    }
    metrics.guardrail_events.labels(**labels).inc()
    payload = {
        "message": "sweep.guardrail",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "sweep_id": sweep_id,
        "ticker": ticker,
        "reason": reason,
        "requested_combinations": requested,
        "combination_cap": cap,
        "cap_status": cap_status,
        "data_quality_status": data_quality_status,
    }
    append_audit_log(payload=payload, audit_path=audit_path, environment=environment)
    emit_governance_metric(
        registry=registry,
        name="sweep_guardrail",
        description="Sweep guardrail telemetry",
        labels={
            "event_type": "sweep_guardrail",
            "checkpoint": "guardrail",
            "reason": reason,
            "cap_status": cap_status,
            "data_quality_status": data_quality_status,
        },
    )
    logger.warning("sweep.guardrail", **payload)
    return payload


__all__ = [
    "create_registry",
    "record_checkpoint",
    "record_guardrail_event",
]
