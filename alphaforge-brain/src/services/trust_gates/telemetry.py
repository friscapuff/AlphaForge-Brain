"""Telemetry helpers for trust gate execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

logger = structlog.get_logger("trust_gates")


@dataclass
class _RegistryMetrics:
    status: Gauge
    duration: Histogram
    failure: Counter
    config_error: Counter


_REGISTRIES: dict[int, _RegistryMetrics] = {}
_STATUS_STATES = ("pass", "warn", "fail")


class TrustGateRegistry(CollectorRegistry):
    """CollectorRegistry that gracefully resolves counter base names."""

    def get_sample_value(
        self, name: str, labels: Mapping[str, str] | None = None
    ) -> float | None:
        normalized = dict(labels) if labels is not None else None
        value = super().get_sample_value(name, normalized)
        if value is None and not name.endswith("_total"):
            value = super().get_sample_value(f"{name}_total", normalized)
        return value


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
    failure_counter = Counter(
        "trust_gate_failure",
        "Trust gate failure counter",
        labelnames=("gate", "profile"),
        registry=registry,
    )
    config_error_counter = Counter(
        "trust_gate_config_error",
        "Trust gate configuration error counter",
        labelnames=("gate", "profile", "reason"),
        registry=registry,
    )
    metrics = _RegistryMetrics(
        status=status_gauge,
        duration=duration_hist,
        failure=failure_counter,
        config_error=config_error_counter,
    )
    _REGISTRIES[key] = metrics
    return metrics


def create_registry() -> CollectorRegistry:
    """Return a dedicated CollectorRegistry for trust gate metrics."""

    registry = TrustGateRegistry()
    _ensure_metrics(registry)
    return registry


def emit_gate_metrics(
    *,
    registry: CollectorRegistry,
    gate: str,
    status: str,
    duration_ms: int,
    profile: str | None = None,
) -> None:
    """Record structlog event and Prometheus samples for a gate result."""

    metrics = _ensure_metrics(registry)
    secs = max(duration_ms, 0) / 1000.0
    for candidate in _STATUS_STATES:
        value = 1.0 if candidate == status else 0.0
        metrics.status.labels(gate=gate, status=candidate).set(value)
    metrics.duration.labels(gate=gate).observe(secs)
    if status == "fail":
        metrics.failure.labels(gate=gate, profile=profile or "unknown").inc()
    logger.info(
        "trust_gate.result",
        gate=gate,
        status=status,
        duration_ms=duration_ms,
        profile=profile,
    )


def emit_config_error(
    *,
    registry: CollectorRegistry,
    gate: str,
    profile: str,
    reason: str,
) -> None:
    metrics = _ensure_metrics(registry)
    metrics.config_error.labels(gate=gate, profile=profile, reason=reason).inc()
    logger.error(
        "trust_gate.config_error",
        gate=gate,
        profile=profile,
        reason=reason,
    )


__all__ = [
    "TrustGateRegistry",
    "create_registry",
    "emit_gate_metrics",
    "emit_config_error",
]
