from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response

try:
    import prometheus_client as _prom

    HAS_PROM = True
    PROM_MEDIA_TYPE = _prom.CONTENT_TYPE_LATEST
    _prom_generate_latest = _prom.generate_latest
except Exception:  # pragma: no cover - optional until dependency is installed
    PROM_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"
    _prom_generate_latest = None  # type: ignore[assignment]
    HAS_PROM = False


router = APIRouter()


# Bounded-label error counter (FR-012). Labels are restricted to small, finite sets.
registry: Any = None
api_error_total: Any = None
if HAS_PROM:
    registry = _prom.CollectorRegistry()
    api_error_total = _prom.Counter(
        "api_error_total",
        "Total API errors by category, endpoint, and status",
        labelnames=("category", "endpoint", "status"),
        registry=registry,
    )


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus metrics in text format (FR-012)."""
    if HAS_PROM and _prom_generate_latest is not None:
        output = _prom_generate_latest(registry)
    else:
        output = b"# prometheus_client not installed\n"
    return Response(content=output, media_type=PROM_MEDIA_TYPE)


__all__ = ["HAS_PROM", "api_error_total", "registry", "router"]
