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

from dataclasses import dataclass
from typing import Any, Iterable

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

    keep_full = keep_last_hashes | top_k_hashes | pinned_hashes
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


__all__ = ["RetentionConfig", "plan_retention", "apply_retention_plan"]
