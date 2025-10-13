"""Governance audit logging and Prometheus metric helpers."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping

from prometheus_client import CollectorRegistry, Counter

DEFAULT_LOGGER_NAME = "governance"
DEFAULT_METRIC_PREFIX = "governance"
DEFAULT_AUDIT_PATH = Path("zz_artifacts/governance_audit.log")

__all__ = [
    "emit_governance_metric",
    "append_audit_log",
    "record_governance_event",
    "resolve_default_audit_path",
]


def _get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger


_METRIC_CACHE: dict[tuple[CollectorRegistry, tuple[str, ...]], Counter] = {}


def emit_governance_metric(
    *,
    registry: CollectorRegistry,
    name: str,
    description: str,
    labels: Mapping[str, str] | None = None,
    increment: float = 1.0,
) -> None:
    """Emit a counter metric for governance-related events."""

    labels = labels or {}
    cache_key = (registry, tuple(sorted(labels.keys())))
    counter = _METRIC_CACHE.get(cache_key)
    if counter is None:
        counter = Counter(
            f"{DEFAULT_METRIC_PREFIX}_event_total",
            "Governance event counter",
            labelnames=tuple(sorted(labels.keys())),
            registry=registry,
        )
        _METRIC_CACHE[cache_key] = counter
    counter.labels(**labels).inc(increment)


def resolve_default_audit_path(environment: Mapping[str, str] | None = None) -> Path:
    env = environment or os.environ
    override = env.get("GOVERNANCE_AUDIT_PATH")
    if override:
        return Path(override)
    return DEFAULT_AUDIT_PATH


def append_audit_log(
    *,
    payload: Mapping[str, Any],
    audit_path: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    target = audit_path or resolve_default_audit_path(environment)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return target


def record_governance_event(
    *,
    message: str,
    details: Mapping[str, Any] | None = None,
    audit_path: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    logger = _get_logger()
    logger.info(message, extra={"details": details or {}})
    append_audit_log(
        payload={"message": message, "details": details or {}},
        audit_path=audit_path,
        environment=environment,
    )
