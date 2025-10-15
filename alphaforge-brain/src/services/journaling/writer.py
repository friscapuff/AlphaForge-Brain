"""Persistence helpers for enriched journaling artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from models.completed_trade import CompletedTrade
from models.trade_context_snapshot import TradeContextSnapshot

from .artifact_paths import resolve_journaling_root
from .enrichment import JournalingArtifacts

if TYPE_CHECKING:  # pragma: no cover - aggregate lands in Phase 5
    from models.journaling_aggregate import JournalingAggregate
else:  # temporary alias until aggregate model is introduced
    JournalingAggregate = Any  # type: ignore[assignment]


@dataclass(slots=True)
class JournalingWriteResult:
    run_path: Path
    trade_path: Path
    snapshots_path: Path | None
    reasons_path: Path | None
    aggregate_path: Path | None
    signature: str


def write_journaling_artifacts(
    run_id: str,
    artifacts: JournalingArtifacts,
    *,
    base_dir: Path | None = None,
) -> JournalingWriteResult:
    root = resolve_journaling_root(base_dir)
    run_path = root / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    trade_path = run_path / "completed_trades.json"
    _write_completed_trades(trade_path, artifacts.trades, artifacts.signature)

    snapshots_path = None
    if artifacts.snapshots:
        snapshots_path = run_path / "snapshots"
        snapshots_path.mkdir(parents=True, exist_ok=True)
        _write_snapshots(snapshots_path, artifacts.snapshots)

    reasons_path = None
    if artifacts.reasons:
        reasons_path = run_path / "reasons.json"
        with reasons_path.open("w", encoding="utf-8") as handle:
            json.dump(artifacts.reasons, handle, ensure_ascii=False, indent=2)

    aggregate_path = None
    if artifacts.aggregate is not None:
        aggregate_path = run_path / "aggregates.json"
        _write_aggregate(aggregate_path, artifacts.aggregate)

    return JournalingWriteResult(
        run_path=run_path,
        trade_path=trade_path,
        snapshots_path=snapshots_path,
        reasons_path=reasons_path,
        aggregate_path=aggregate_path,
        signature=artifacts.signature or "",
    )


def _write_completed_trades(
    trade_path: Path,
    trades: Iterable[CompletedTrade],
    signature: str | None,
) -> None:
    records = []
    sorted_trades = sorted(trades, key=lambda trade: trade.id)
    for trade in sorted_trades:
        record = trade.model_dump(mode="json")
        if signature:
            record["hash_signature"] = signature
        records.append(record)

    with trade_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def _write_snapshots(
    snapshots_dir: Path,
    snapshots: Iterable[TradeContextSnapshot],
) -> None:
    sorted_snapshots = sorted(
        snapshots,
        key=lambda snapshot: (snapshot.trade_id, snapshot.id),
    )

    for snapshot in sorted_snapshots:
        target_path = snapshots_dir / f"trade-{snapshot.trade_id}.json"
        with target_path.open("w", encoding="utf-8") as handle:
            json.dump(
                snapshot.model_dump(mode="json"), handle, ensure_ascii=False, indent=2
            )


def _write_aggregate(path: Path, aggregate: JournalingAggregate) -> None:
    payload = aggregate.model_dump(mode="json")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


__all__ = ["write_journaling_artifacts", "JournalingWriteResult"]
