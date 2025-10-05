"""Snapshot & SSE helpers (T044).

Builds SummarySnapshot from metrics dict and provides minimal SSE formatting.
"""

from __future__ import annotations

from ..models.summary_snapshot import SummarySnapshot


def build_summary(
    run_id: str, metrics: dict[str, float], cautions: int = 0, violations: int = 0
) -> SummarySnapshot:
    return SummarySnapshot(
        run_id=run_id,
        total_return=metrics.get("total_return"),
        cagr=None,  # placeholder until time-scaling implemented
        sharpe=metrics.get("sharpe"),
        sortino=None,
        max_drawdown=metrics.get("max_drawdown"),
        calmar=None,
        trade_count=None,
        caution_metric_count=cautions,
        violation_metric_count=violations,
    )


def sse_format(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


__all__ = ["build_summary", "sse_format"]
