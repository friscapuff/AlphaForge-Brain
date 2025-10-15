"""Enrichment helpers for enriched journaling artifacts (Phase 016)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from models.completed_trade import CompletedTrade
from models.fill import Fill
from models.trade_context_snapshot import TradeContextSnapshot
from services.hashing import hash_enriched_journaling_payload

if TYPE_CHECKING:  # pragma: no cover - introduced in Phase 5
    from models.journaling_aggregate import JournalingAggregate
else:  # lightweight placeholder until aggregate model lands
    JournalingAggregate = Any  # type: ignore[assignment]

_JOURNALING_SCHEMA_VERSION = "2025.10.16"


@dataclass(slots=True)
class JournalingArtifacts:
    run_id: str
    trades: list[CompletedTrade]
    snapshots: list[TradeContextSnapshot]
    reasons: list[dict[str, str]]
    signature: str | None
    schema_version: str = _JOURNALING_SCHEMA_VERSION
    aggregate: JournalingAggregate | None = None
    source_artifacts: list[str] = field(default_factory=list)


def prepare_enriched_payload(
    run_id: str,
    trades: Sequence[CompletedTrade],
    *,
    snapshots: Sequence[TradeContextSnapshot] | None = None,
    price_events: Mapping[str, Sequence[float]] | None = None,
) -> JournalingArtifacts:
    """Return enriched journaling payload artifacts for a run.

    Parameters
    ----------
    run_id:
        Identifier of the run associated with these artifacts.
    trades:
        CompletedTrade payloads requiring derived metrics. The function does not
        mutate the input objects; enriched copies are returned.
    snapshots:
        Optional trade context snapshots captured during the run.
    price_events:
        Optional mapping of trade_id -> iterable price observations used to
        compute MAE/MFE beyond fill prices.
    """

    snapshot_index: dict[str, TradeContextSnapshot] = {}
    if snapshots:
        snapshot_index = {snapshot.id: snapshot for snapshot in snapshots}

    enriched_trades: list[CompletedTrade] = []
    normalization_events = price_events or {}
    reasons: list[dict[str, str]] = []

    for trade in trades:
        reference_prices = normalization_events.get(trade.id, ())
        enriched = _enrich_trade(trade, reference_prices)
        enriched_trades.append(enriched)

        if (
            enriched.context_snapshot_id
            and enriched.context_snapshot_id not in snapshot_index
        ):
            reasons.append(
                {
                    "trade_id": enriched.id,
                    "code": "snapshot_missing",
                    "detail": f"No snapshot found for id {enriched.context_snapshot_id}",
                }
            )

    sorted_reasons = sorted(reasons, key=lambda item: item["trade_id"])

    ordered_snapshots = sorted(
        snapshots or [], key=lambda snap: (snap.trade_id, snap.id)
    )

    payload_for_hash = {
        "run_id": run_id,
        "schema_version": _JOURNALING_SCHEMA_VERSION,
        "completed_trades": [
            trade.model_dump(mode="json") for trade in enriched_trades
        ],
        "snapshots": [
            snapshot.model_dump(mode="json") for snapshot in ordered_snapshots
        ],
        "reasons": sorted_reasons,
    }
    signature = hash_enriched_journaling_payload(payload_for_hash)

    source_artifacts = _compute_source_artifacts(
        enriched_trades,
        ordered_snapshots,
        sorted_reasons,
    )
    return JournalingArtifacts(
        run_id=run_id,
        trades=enriched_trades,
        snapshots=ordered_snapshots,
        reasons=sorted_reasons,
        signature=signature,
        source_artifacts=source_artifacts,
    )


def _enrich_trade(
    trade: CompletedTrade,
    price_events: Iterable[float],
) -> CompletedTrade:
    price_series = list(price_events)
    if trade.fills:
        price_series.extend(
            fill.price for fill in trade.fills if fill.price is not None
        )
    price_series.extend([trade.entry_price, trade.exit_price])
    price_series = [price for price in price_series if price is not None]

    direction = 1 if trade.quantity >= 0 else -1
    mae, mfe = _compute_excursions(direction, trade.entry_price, price_series)

    r_multiple = _compute_r_multiple(trade.pnl, trade.fills)
    expectancy_bucket = _bucket_expectancy(r_multiple)
    risk_flag = trade.risk_flag or _derive_risk_flag(trade.fills)

    update_payload = {
        "schema_version": trade.schema_version or _JOURNALING_SCHEMA_VERSION,
        "mae": mae,
        "mfe": mfe,
        "r_multiple": r_multiple,
        "expectancy_bucket": expectancy_bucket,
        "risk_flag": risk_flag,
    }

    if not trade.context_snapshot_id and trade.fills:
        update_payload["context_snapshot_id"] = _infer_snapshot_id(trade.fills[0])

    return trade.model_copy(update=update_payload)


def _compute_excursions(
    direction: int,
    entry_price: float,
    price_series: Sequence[float],
) -> tuple[float, float]:
    if not price_series:
        return 0.0, 0.0

    min_price = min(price_series)
    max_price = max(price_series)

    if direction >= 0:
        mae = max(0.0, entry_price - min_price)
        mfe = max(0.0, max_price - entry_price)
    else:
        mae = max(0.0, max_price - entry_price)
        mfe = max(0.0, entry_price - min_price)
    return round(mae, 2), round(mfe, 2)


def _compute_r_multiple(pnl: float, fills: Sequence[Fill] | None) -> float:
    risk_unit = None
    if fills:
        for fill in fills:
            inputs = getattr(fill, "expectancy_inputs", None)
            if inputs and "risk_unit" in inputs:
                try:
                    candidate = float(inputs["risk_unit"])
                except (TypeError, ValueError):
                    continue
                if candidate > 0:
                    risk_unit = candidate
                    break
    if risk_unit is None or risk_unit == 0:
        risk_unit = max(abs(pnl), 1.0)
    return round(pnl / risk_unit, 3)


def _bucket_expectancy(r_multiple: float) -> str:
    if r_multiple > 0:
        return "positive"
    if r_multiple < 0:
        return "negative"
    return "neutral"


def _derive_risk_flag(fills: Sequence[Fill] | None) -> str | None:
    if not fills:
        return None
    for fill in fills:
        tier = getattr(fill, "risk_tier", None)
        if tier is None:
            continue
        tier_lower = str(tier).lower()
        if tier_lower == "aggressive":
            return "elevated_position"
        if tier_lower == "moderate":
            return "balanced_position"
    return None


def _infer_snapshot_id(fill: object) -> str | None:
    stop_id = getattr(fill, "stop_id", None)
    if stop_id:
        return f"ctx-{stop_id}"
    return None


def _compute_source_artifacts(
    trades: Sequence[CompletedTrade],
    snapshots: Sequence[TradeContextSnapshot],
    reasons: Sequence[dict[str, str]],
) -> list[str]:
    paths: list[str] = ["completed_trades.json"]
    if snapshots:
        snapshot_paths = [
            f"snapshots/trade-{snapshot.trade_id}.json" for snapshot in snapshots
        ]
        # preserve deterministic ordering and remove duplicates
        snapshot_paths = list(dict.fromkeys(snapshot_paths))
        paths.extend(snapshot_paths)
    if reasons:
        paths.append("reasons.json")
    return paths


__all__ = ["JournalingArtifacts", "prepare_enriched_payload"]
