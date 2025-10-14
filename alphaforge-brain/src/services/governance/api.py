from __future__ import annotations

from fastapi import APIRouter, status

from . import storage
from .models import BenchmarkTrendAlert, WaiverCadenceSnapshot

__all__ = ["router"]

router = APIRouter(prefix="/api/internal/governance", tags=["governance"])


@router.post("/benchmark-alerts", status_code=status.HTTP_202_ACCEPTED)
def create_benchmark_trend_alert(alert: BenchmarkTrendAlert) -> dict[str, str]:
    """Accept a benchmark trend alert and persist it to artifact storage."""

    storage.append_benchmark_alert(alert)
    return {"status": "accepted", "alert_id": str(alert.alert_id)}


@router.post("/waiver-cadence", status_code=status.HTTP_200_OK)
def update_waiver_cadence(snapshot: WaiverCadenceSnapshot) -> dict[str, str]:
    """Persist the latest waiver cadence snapshot for downstream dashboards."""

    storage.write_waiver_cadence_snapshot(snapshot)
    return {"status": "persisted", "generated_at": snapshot.generated_at.isoformat()}
