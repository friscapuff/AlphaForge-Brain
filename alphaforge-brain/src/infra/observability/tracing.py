from __future__ import annotations

import os
import threading
import tracemalloc
from contextlib import contextmanager
from time import perf_counter_ns, process_time_ns, time_ns
from typing import Any, Iterator

from infra.logging import get_logger
from infra.persistence import record_trace_span

__all__ = ["trace_validation_span"]

_TRACEMALLOC_LOCK = threading.Lock()


def _ensure_tracemalloc() -> None:
    if tracemalloc.is_tracing():
        return
    with _TRACEMALLOC_LOCK:
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)


_SIMPLE_TYPES = (str, int, float, bool, type(None))


def _coerce_value(value: Any) -> Any:
    if isinstance(value, _SIMPLE_TYPES):
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce_value(v) for k, v in value.items()}
    return str(value)


def _normalize_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    normalised: dict[str, Any] = {}
    for key, value in attributes.items():
        if value is None:
            continue
        normalised[str(key)] = _coerce_value(value)
    return normalised


@contextmanager
def trace_validation_span(
    name: str,
    *,
    run_hash: str | None = None,
    correlation_id: str | None = None,
    persist: bool = True,
    logger_name: str = "validation.observability",
) -> Iterator[dict[str, Any]]:
    """Context manager capturing timing and memory metrics for validation spans."""

    _ensure_tracemalloc()
    logger = get_logger(logger_name)
    span_name = name if name.startswith("validation.") else f"validation.{name}"

    wall_start_ns = perf_counter_ns()
    cpu_start_ns = process_time_ns()
    epoch_start_ms = time_ns() // 1_000_000
    current_start, peak_start = tracemalloc.get_traced_memory()
    thread_id = threading.get_ident()
    process_id = os.getpid()
    span_attributes: dict[str, Any] = {}

    try:
        yield span_attributes
    except Exception as exc:  # pragma: no cover - propagate after tagging
        span_attributes.setdefault("exception", exc.__class__.__name__)
        span_attributes.setdefault("exception_message", str(exc))
        raise
    finally:
        wall_end_ns = perf_counter_ns()
        cpu_end_ns = process_time_ns()
        epoch_end_ms = time_ns() // 1_000_000
        current_end, peak_end = tracemalloc.get_traced_memory()

        duration_ms = (wall_end_ns - wall_start_ns) / 1_000_000
        cpu_ms = (cpu_end_ns - cpu_start_ns) / 1_000_000
        mem_delta_bytes = max(0, current_end - current_start)
        peak_delta_bytes = max(0, peak_end - peak_start)

        attributes = _normalize_attributes(span_attributes)
        log_payload: dict[str, Any] = {
            "span": span_name,
            "duration_ms": round(duration_ms, 3),
            "cpu_ms": round(cpu_ms, 3),
            "mem_delta_bytes": mem_delta_bytes,
            "mem_peak_bytes": peak_end,
            "thread_id": thread_id,
            "process_id": process_id,
        }
        if peak_delta_bytes:
            log_payload["mem_peak_delta_bytes"] = peak_delta_bytes
        if run_hash:
            log_payload["run_hash"] = run_hash
        if correlation_id:
            log_payload["correlation_id"] = correlation_id
        if attributes:
            log_payload.update(attributes)

        logger.info("validation_span", **log_payload)

        if persist and run_hash:
            try:
                record_trace_span(
                    run_hash=run_hash,
                    name=span_name,
                    started_at_ms=epoch_start_ms,
                    ended_at_ms=epoch_end_ms,
                    correlation_id=correlation_id,
                    attributes={
                        **attributes,
                        "duration_ms": round(duration_ms, 3),
                        "cpu_ms": round(cpu_ms, 3),
                        "mem_delta_bytes": mem_delta_bytes,
                        "mem_peak_bytes": peak_end,
                        "mem_peak_delta_bytes": peak_delta_bytes,
                        "thread_id": thread_id,
                        "process_id": process_id,
                    },
                )
            except Exception as exc:  # pragma: no cover - persistence is best effort
                logger.warning(
                    "validation_span_persist_failed",
                    span=span_name,
                    run_hash=run_hash,
                    error=exc.__class__.__name__,
                    error_message=str(exc),
                )
