"""Run retention policy (T017/T018 groundwork).

Policy:
    - Keep last N full runs globally (ordered by created_at desc) -> default 50
    - Keep top K per strategy by primary metric (higher is better) -> default 5
    - Pinned runs are always kept full (override) regardless of age or rank.
    - Demoted runs transition from retention_state in {full,pinned,top_k} to 'manifest-only'.

Inputs (in-memory registry model):
    registry.store: run_hash -> record with keys:
         created_at (timestamp), strategy_name (optional), primary_metric_value (optional), pinned (bool), retention_state(optional)

Outputs:
    plan: dict with keys:
         keep_full: set[str]
         demote: set[str]
         pinned: set[str]
         top_k: set[str]

Edge cases:
    - If created_at missing assign 0 (oldest).
    - If primary_metric_value missing treat as -inf for ranking.
    - If fewer than thresholds, no demotions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .create import InMemoryRunRegistry


@dataclass(slots=True)
class RetentionConfig:
    keep_last: int = 50
    top_k_per_strategy: int = 5
    max_full_bytes: int | None = (
        None  # Optional soft cap on total bytes of 'full' runs (excluding pinned). Oldest demoted first.
    )


def _rank_top_k(run_items: Iterable[tuple[str, dict[str, Any]]], k: int) -> set[str]:
    if k <= 0:
        return set()
    # Sort descending by primary_metric_value (None -> -inf)
    ordered = sorted(
        run_items,
        key=lambda kv: float(kv[1].get("primary_metric_value", float("-inf"))),
        reverse=True,
    )
    return {h for h, _ in ordered[:k]}


def _estimate_run_bytes(run_hash: str, rec: dict[str, Any]) -> int:
    # Best-effort: sum file sizes in artifact dir excluding manifest.json and .evicted
    try:

        from infra.artifacts_root import resolve_artifact_root

        base = resolve_artifact_root(None)
        rdir = base / run_hash
        total = 0
        if rdir.exists():
            for p in rdir.iterdir():
                if not p.is_file():
                    continue
                if p.name in {"manifest.json", ".evicted"}:
                    continue
                try:
                    total += p.stat().st_size
                except Exception:
                    continue
        return total
    except Exception:  # pragma: no cover - estimation must not break retention planning
        return 0


def _normalize_status(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized or None
    return None


def _significance_failed(record: Mapping[str, Any]) -> bool:
    status = _normalize_status(record.get("validation_significance"))
    if status == "fail":
        return True
    validation_v2 = record.get("validation_v2")
    if isinstance(validation_v2, Mapping):
        status = _normalize_status(validation_v2.get("significance_status"))
        if status == "fail":
            return True
        metadata = validation_v2.get("metadata")
        if isinstance(metadata, Mapping):
            status = _normalize_status(metadata.get("significance_status"))
            if status == "fail":
                return True
        manifest_fragment = validation_v2.get("manifest")
        if isinstance(manifest_fragment, Mapping):
            status = _normalize_status(manifest_fragment.get("validation_significance"))
            if status == "fail":
                return True
    failed_checks = record.get("validation_failed_checks")
    if isinstance(failed_checks, (list, tuple, set)):
        for entry in failed_checks:
            if _normalize_status(str(entry)) == "permutation_significance":
                return True
    return False


def _realism_failed(record: Mapping[str, Any]) -> bool:
    status = _normalize_status(record.get("execution_realism_status"))
    if status == "fail":
        return True
    validation_v2 = record.get("validation_v2")
    if isinstance(validation_v2, Mapping):
        realism_payload = validation_v2.get("execution_realism")
        if isinstance(realism_payload, Mapping):
            status = _normalize_status(realism_payload.get("status"))
            if status == "fail":
                return True
        metadata = validation_v2.get("metadata")
        if isinstance(metadata, Mapping):
            status = _normalize_status(metadata.get("realism_status"))
            if status == "fail":
                return True
        manifest_fragment = validation_v2.get("manifest")
        if isinstance(manifest_fragment, Mapping):
            realism_fragment = manifest_fragment.get("execution_realism")
            if isinstance(realism_fragment, Mapping):
                status = _normalize_status(realism_fragment.get("status"))
                if status == "fail":
                    return True
    failed_checks = record.get("validation_failed_checks")
    if isinstance(failed_checks, (list, tuple, set)):
        for entry in failed_checks:
            if _normalize_status(str(entry)) == "execution_realism":
                return True
    return False


def plan_retention(
    registry: InMemoryRunRegistry, cfg: RetentionConfig | None = None
) -> dict[str, set[str]]:
    cfg = cfg or RetentionConfig()
    runs = list(registry.store.items())
    if not runs:
        return {"keep_full": set(), "demote": set(), "pinned": set(), "top_k": set()}

    # Normalize created_at
    for _h, rec in runs:
        if "created_at" not in rec:
            rec["created_at"] = 0.0
    # Global keep_last (newest first)
    newest = sorted(runs, key=lambda kv: kv[1].get("created_at", 0.0), reverse=True)
    keep_last_hashes = {h for h, _ in newest[: cfg.keep_last]}

    # Group by strategy_name
    by_strategy: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for h, rec in runs:
        strat = (
            rec.get("strategy_name")
            or rec.get("strategy", {}).get("name")
            or "_default"
        )
        by_strategy.setdefault(strat, []).append((h, rec))
    top_k_hashes: set[str] = set()
    for strat, items in by_strategy.items():  # noqa: B007 (explicit var)
        top_k_hashes |= _rank_top_k(items, cfg.top_k_per_strategy)

    pinned_hashes = {h for h, r in runs if r.get("pinned")}

    # Validation caution gating: exclude flagged runs from promotion unless pinned.
    caution_hashes = {h for h, r in runs if r.get("validation_caution")}
    # Validation significance & realism gating (FR-010): block automatic promotion when either fails.
    significance_failures = {h for h, r in runs if _significance_failed(r)}
    realism_failures = {h for h, r in runs if _realism_failed(r)}
    gated_failures = (significance_failures | realism_failures) - pinned_hashes
    # Pinned always kept regardless of gating; others are filtered out
    keep_full = pinned_hashes | (
        (keep_last_hashes | top_k_hashes) - caution_hashes - gated_failures
    )
    all_hashes = {h for h, _ in runs}
    demote = all_hashes - keep_full

    # Apply size budget: if max_full_bytes set, compute cumulative size of non-pinned kept runs ordered oldest first and demote until under budget
    if cfg.max_full_bytes is not None:
        # Collect candidate kept (non-pinned) runs with sizes
        candidates = []
        for h, rec in runs:
            if h in pinned_hashes:
                continue  # never demote pinned
            if h not in keep_full:
                continue
            size = _estimate_run_bytes(h, rec)
            candidates.append((h, rec.get("created_at", 0.0), size))
        # Sort oldest first so we demote the least recent
        candidates.sort(key=lambda t: t[1])
        total_bytes = sum(c[2] for c in candidates)
        idx = 0
        while total_bytes > cfg.max_full_bytes and idx < len(candidates):
            h, _ts, sz = candidates[idx]
            # Skip if already essential (top_k or keep_last? we allow demotion if not pinned)
            if h in keep_full:
                keep_full.discard(h)
                demote.add(h)
                total_bytes -= sz
            idx += 1
    return {
        "keep_full": keep_full,
        "demote": demote,
        "pinned": pinned_hashes,
        "top_k": top_k_hashes,
    }


def apply_retention_plan(
    registry: InMemoryRunRegistry, plan: dict[str, set[str]]
) -> None:
    for h, rec in list(registry.store.items()):
        if h in plan["demote"]:
            # Demote only if not pinned
            if rec.get("pinned"):
                continue
            rec["retention_state"] = "manifest-only"
        else:
            # Mark reasons
            if rec.get("pinned"):
                rec["retention_state"] = "pinned"
            elif h in plan["top_k"]:
                rec["retention_state"] = "top_k"
            else:
                rec["retention_state"] = "full"


__all__ = ["RetentionConfig", "apply_retention_plan", "plan_retention"]
