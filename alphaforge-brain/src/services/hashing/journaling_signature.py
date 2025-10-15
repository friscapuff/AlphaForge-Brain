"""Deterministic signatures for enriched journaling payloads (Decision 4)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from typing import Any

from infra.utils.hash import hash_canonical

_JOURNALING_TRADE_KEYS = {"id", "symbol", "entry_ts", "exit_ts"}
_FILL_KEYS = {"order_id", "ts", "price"}
_SNAPSHOT_KEYS = {"trade_id", "collected_at", "schema_version"}
_AGGREGATE_KEYS = {"run_id", "expectancy_by_strategy", "schema_version"}


def hash_enriched_journaling_payload(
    payload: Mapping[str, Any] | Sequence[Any] | Set[Any] | None,
) -> str | None:
    """Return a deterministic hash for enriched journaling payload structures.

    The helper normalises trade, fill, snapshot, and aggregate collections so
    ordering differences cannot affect downstream retention evidence or trust
    gate manifests. For empty or missing payloads, ``None`` is returned so
    callers can gracefully skip hashing when journaling is disabled.
    """

    if payload is None:
        return None

    if isinstance(payload, (str, bytes, bytearray)):
        raise TypeError("Journaling payload must be a mapping or sequence of mappings")

    normalized = _normalize_payload(payload)
    return hash_canonical(normalized)


def _normalize_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        if _looks_like_completed_trade(value):
            return _normalize_completed_trade(value)
        if _looks_like_fill(value):
            return _normalize_fill(value)
        if _looks_like_snapshot(value):
            return _normalize_snapshot(value)
        if _looks_like_aggregate(value):
            return _normalize_aggregate(value)

        normalized: dict[str, Any] = {}
        for key in sorted(value, key=str):
            item = value[key]
            if key in {"completed_trades", "trades"}:
                normalized[str(key)] = _normalize_completed_trade_sequence(item)
            elif key in {"snapshots", "trade_context_snapshots"}:
                normalized[str(key)] = _normalize_snapshot_sequence(item)
            elif key in {"aggregates", "journaling_aggregates", "manifests"}:
                normalized[str(key)] = _normalize_aggregate_sequence(item)
            else:
                normalized[str(key)] = _normalize_payload(item)
        return normalized

    if isinstance(value, Set):
        return _normalize_sequence(
            sorted((_normalize_payload(item) for item in value), key=hash_canonical)
        )

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized_items = [_normalize_payload(item) for item in value]
        return _normalize_sequence(normalized_items)

    return value


def _normalize_completed_trade(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in sorted(payload, key=str):
        if key == "fills":
            normalized[key] = _normalize_fill_sequence(payload[key])
        else:
            normalized[key] = _normalize_payload(payload[key])
    return normalized


def _normalize_fill(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _normalize_payload(val)
        for key, val in sorted(payload.items(), key=lambda kv: str(kv[0]))
    }


def _normalize_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {
        str(key): _normalize_payload(val)
        for key, val in sorted(payload.items(), key=lambda kv: str(kv[0]))
    }
    checklist = normalized.get("checklist")
    if isinstance(checklist, Mapping):
        normalized["checklist"] = {
            str(key): str(checklist[key]) for key in sorted(checklist, key=str)
        }
    indicators = normalized.get("indicators")
    if isinstance(indicators, Mapping):
        normalized["indicators"] = {
            str(key): _normalize_payload(indicators[key])
            for key in sorted(indicators, key=str)
        }
    return normalized


def _normalize_aggregate(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {
        str(key): _normalize_payload(val)
        for key, val in sorted(payload.items(), key=lambda kv: str(kv[0]))
    }
    for section in (
        "expectancy_by_strategy",
        "checklist_adherence",
        "risk_distribution",
        "mae_mfe_stats",
    ):
        content = normalized.get(section)
        if isinstance(content, Mapping):
            normalized[section] = {
                str(key): _normalize_payload(content[key])
                for key in sorted(content, key=str)
            }
    sources = normalized.get("source_artifacts")
    if isinstance(sources, Sequence) and not isinstance(
        sources, (str, bytes, bytearray)
    ):
        normalized["source_artifacts"] = sorted(str(item) for item in sources)
    breach_flags = normalized.get("breach_flags")
    if isinstance(breach_flags, Sequence) and not isinstance(
        breach_flags, (str, bytes, bytearray)
    ):
        normalized["breach_flags"] = sorted(str(item) for item in breach_flags)
    return normalized


def _normalize_fill_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, Mapping):
            normalized.append(_normalize_fill(entry))
    normalized.sort(
        key=lambda item: (
            str(item.get("ts", "")),
            str(item.get("order_id", "")),
            hash_canonical(item),
        )
    )
    return normalized


def _normalize_sequence(items: Sequence[Any]) -> list[Any]:
    if not items:
        return []
    if all(isinstance(item, Mapping) for item in items):
        if all("id" in item for item in items):
            return sorted(
                items,
                key=lambda item: (str(item.get("id", "")), hash_canonical(item)),
            )
        if all("trade_id" in item for item in items):
            return sorted(
                items,
                key=lambda item: (str(item.get("trade_id", "")), hash_canonical(item)),
            )
    if all(isinstance(item, (str, int, float, bool)) or item is None for item in items):
        return sorted(items, key=lambda value: "" if value is None else str(value))
    return sorted(items, key=hash_canonical)


def _normalize_snapshot_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, Mapping):
            normalized.append(_normalize_snapshot(entry))
    normalized.sort(
        key=lambda item: (
            str(item.get("trade_id", "")),
            str(item.get("id", "")),
            hash_canonical(item),
        )
    )
    return normalized


def _normalize_completed_trade_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, Mapping):
            normalized.append(_normalize_completed_trade(entry))
    normalized.sort(key=lambda item: (str(item.get("id", "")), hash_canonical(item)))
    return normalized


def _normalize_aggregate_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, Mapping):
            normalized.append(_normalize_aggregate(entry))
    normalized.sort(
        key=lambda item: (
            str(item.get("run_id", "")),
            str(item.get("generated_at", "")),
            hash_canonical(item),
        )
    )
    return normalized


def _looks_like_completed_trade(payload: Mapping[str, Any]) -> bool:
    return _JOURNALING_TRADE_KEYS.issubset(payload.keys())


def _looks_like_fill(payload: Mapping[str, Any]) -> bool:
    return _FILL_KEYS.issubset(payload.keys())


def _looks_like_snapshot(payload: Mapping[str, Any]) -> bool:
    return _SNAPSHOT_KEYS.issubset(payload.keys())


def _looks_like_aggregate(payload: Mapping[str, Any]) -> bool:
    return _AGGREGATE_KEYS.issubset(payload.keys())


__all__ = ["hash_enriched_journaling_payload"]
