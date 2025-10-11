"""Telemetry helpers for trust gate execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import structlog
from prometheus_client import CollectorRegistry, Gauge, Histogram

logger = structlog.get_logger("trust_gates")


@dataclass
class _RegistryMetrics:
    status: Gauge
    duration: Histogram


_REGISTRIES: Dict[int, _RegistryMetrics] = {}
_STATUS_STATES = ("pass", "warn", "fail")


def _ensure_metrics(registry: CollectorRegistry) -> _RegistryMetrics:
    key = id(registry)
    metrics = _REGISTRIES.get(key)
    if metrics is not None:
        return metrics
    status_gauge = Gauge(
        "trust_gate_status",
        "Trust gate status flag (1=current status)",
        labelnames=("gate", "status"),
        registry=registry,
    )
    duration_hist = Histogram(
        "trust_gate_duration_seconds",
        "Trust gate execution duration",
        labelnames=("gate",),
        registry=registry,
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    )
    metrics = _RegistryMetrics(status=status_gauge, duration=duration_hist)
    _REGISTRIES[key] = metrics
    return metrics


def create_registry() -> CollectorRegistry:
    """Return a dedicated CollectorRegistry for trust gate metrics."""

    registry = CollectorRegistry()
    _ensure_metrics(registry)
    return registry


def emit_gate_metrics(
    *, registry: CollectorRegistry, gate: str, status: str, duration_ms: int
) -> None:
    """Record structlog event and Prometheus samples for a gate result."""

    metrics = _ensure_metrics(registry)
    secs = max(duration_ms, 0) / 1000.0
    for candidate in _STATUS_STATES:
        value = 1.0 if candidate == status else 0.0
        metrics.status.labels(gate=gate, status=candidate).set(value)
    metrics.duration.labels(gate=gate).observe(secs)
    logger.info(
        "trust_gate.result",
        gate=gate,
        status=status,
        duration_ms=duration_ms,
    )


__all__ = ["create_registry", "emit_gate_metrics"]
