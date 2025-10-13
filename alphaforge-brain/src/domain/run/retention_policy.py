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

import importlib
import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.run_validation_status import coerce_validation_status
from prometheus_client import REGISTRY, CollectorRegistry
from services.audit.governance_logger import (
    append_audit_log,
    emit_governance_metric,
    record_governance_event,
)

from .create import InMemoryRunRegistry

_POLICY_ENV_VAR = "RETENTION_POLICY_PATH"
_BREACH_LOG_ENV_VAR = "RETENTION_BREACH_LOG_PATH"
_METRIC_ENV_LABEL = "RETENTION_METRIC_ENVIRONMENT"
_DEFAULT_POLICY_PATH = Path("configs/retention/policy.yaml")


@dataclass(slots=True)
class RetentionConfig:
    keep_last: int = 50
    top_k_per_strategy: int = 5
    max_full_bytes: int | None = None
    policy_version: str = "2025.10.13"
    pin_expiry_days: int | None = None
    waiver_required: bool = False
    audit_log_path: Path = field(
        default_factory=lambda: Path("zz_artifacts/retention_audit.log")
    )
    breach_log_path: Path = field(
        default_factory=lambda: Path("zz_artifacts/retention_breaches.log")
    )
    metric_labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RetentionConfig:
        keep_last_raw = payload.get("max_runs", payload.get("keep_last", 50))
        top_k_raw = payload.get(
            "per_strategy_top", payload.get("top_k_per_strategy", 5)
        )
        max_full_bytes_val = payload.get("max_full_bytes")
        pin_expiry_raw = payload.get("pin_expiry_days")

        keep_last = int(keep_last_raw) if keep_last_raw is not None else 50
        top_k = int(top_k_raw) if top_k_raw is not None else 5
        max_full_bytes = (
            int(max_full_bytes_val) if max_full_bytes_val is not None else None
        )
        pin_expiry_days = int(pin_expiry_raw) if pin_expiry_raw is not None else None

        policy_version = (
            str(payload.get("policy_version", "unknown")).strip() or "unknown"
        )
        waiver_required = bool(payload.get("waiver_required", False))

        audit_log_path_raw = payload.get("audit_log_path")
        audit_log_path = (
            Path(str(audit_log_path_raw))
            if audit_log_path_raw
            else Path("zz_artifacts/retention_audit.log")
        )
        breach_log_path_raw = payload.get("breach_log_path")
        breach_log_path = (
            Path(str(breach_log_path_raw))
            if breach_log_path_raw
            else Path("zz_artifacts/retention_breaches.log")
        )

        metric_labels_payload = payload.get("metric_labels") or {}
        metric_labels: dict[str, str] = {}
        if isinstance(metric_labels_payload, Mapping):
            for key, value in metric_labels_payload.items():
                metric_labels[str(key)] = str(value)

        return cls(
            keep_last=keep_last,
            top_k_per_strategy=top_k,
            max_full_bytes=max_full_bytes,
            policy_version=policy_version,
            pin_expiry_days=pin_expiry_days,
            waiver_required=waiver_required,
            audit_log_path=audit_log_path,
            breach_log_path=breach_log_path,
            metric_labels=metric_labels,
        )

    def as_dict(self) -> dict[str, Any]:  # pragma: no cover - convenience helper
        return {
            "keep_last": self.keep_last,
            "top_k_per_strategy": self.top_k_per_strategy,
            "max_full_bytes": self.max_full_bytes,
            "policy_version": self.policy_version,
            "pin_expiry_days": self.pin_expiry_days,
            "waiver_required": self.waiver_required,
            "audit_log_path": self.audit_log_path.as_posix(),
            "breach_log_path": self.breach_log_path.as_posix(),
            "metric_labels": dict(self.metric_labels),
        }


def _load_retention_payload(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"retention policy not found at {path}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            yaml_module = importlib.import_module("yaml")
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Retention policy is YAML but PyYAML is not installed; install PyYAML or provide JSON payload."
            ) from exc
        loaded = yaml_module.safe_load(text)
        if not isinstance(loaded, Mapping):
            raise ValueError(
                "Retention policy must deserialize to a mapping object"
            ) from None
        data = loaded

    if not isinstance(data, Mapping):
        raise ValueError(
            "Retention policy must deserialize to a mapping object"
        ) from None
    return data


@lru_cache(maxsize=8)
def _cached_retention_config(path_str: str, mtime_ns: int) -> RetentionConfig:
    return RetentionConfig.from_mapping(_load_retention_payload(Path(path_str)))


def load_retention_config(
    path: Path | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> RetentionConfig:
    env = environment or os.environ
    candidate = path or env.get(_POLICY_ENV_VAR)
    candidate_path = Path(candidate) if candidate else _DEFAULT_POLICY_PATH
    resolved = (
        candidate_path
        if candidate_path.is_absolute()
        else (Path.cwd() / candidate_path)
    )
    resolved = resolved.resolve()
    mtime_ns = resolved.stat().st_mtime_ns
    cfg = _cached_retention_config(str(resolved), mtime_ns)

    breach_override = env.get(_BREACH_LOG_ENV_VAR)
    if breach_override:
        cfg = replace(cfg, breach_log_path=Path(breach_override))

    metric_labels = dict(cfg.metric_labels)
    env_label = env.get(_METRIC_ENV_LABEL)
    if env_label:
        metric_labels.setdefault("environment", env_label)
    if metric_labels != cfg.metric_labels:
        cfg = replace(cfg, metric_labels=metric_labels)

    return cfg


def _resolve_breach_log_path(
    cfg: RetentionConfig, environment: Mapping[str, str] | None
) -> Path:
    env = environment or os.environ
    override = env.get(_BREACH_LOG_ENV_VAR)
    if override:
        return Path(override)
    return cfg.breach_log_path


def _log_retention_breach(
    *,
    breach: Mapping[str, Any],
    cfg: RetentionConfig,
    metrics_registry: CollectorRegistry,
    environment: Mapping[str, str] | None,
) -> None:
    labels = {
        "event_type": "retention_breach",
        "reason": str(breach.get("type", "unknown")),
    }
    for key, value in cfg.metric_labels.items():
        labels.setdefault(key, value)

    emit_governance_metric(
        registry=metrics_registry,
        name="retention",
        description="Retention breach event counter",
        labels=labels,
    )

    details = dict(breach)
    details["policy_version"] = cfg.policy_version

    record_governance_event(
        message="retention.policy.breach",
        details=details,
        environment=environment,
    )
    append_audit_log(
        payload={"message": "retention.policy.breach", "details": details},
        audit_path=_resolve_breach_log_path(cfg, environment),
        environment=environment,
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
    status_field = record.get("validation_status")
    if status_field is not None:
        try:
            if coerce_validation_status(status_field).is_failed():
                return True
        except Exception:
            pass
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
    registry: InMemoryRunRegistry,
    cfg: RetentionConfig | None = None,
    *,
    metrics_registry: CollectorRegistry | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = environment or os.environ
    cfg = cfg or load_retention_config(environment=env)
    metrics = metrics_registry or REGISTRY
    runs = list(registry.store.items())
    if not runs:
        return {
            "keep_full": set(),
            "demote": set(),
            "pinned": set(),
            "top_k": set(),
            "breaches": [],
            "policy_version": cfg.policy_version,
        }

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

    breaches: list[dict[str, Any]] = []
    non_pinned_demoted = sorted(h for h in demote if h not in pinned_hashes)
    if len(all_hashes) > cfg.keep_last and non_pinned_demoted:
        breaches.append(
            {
                "type": "max_runs",
                "limit": cfg.keep_last,
                "total_runs": len(all_hashes),
                "demoted": non_pinned_demoted,
            }
        )

    for strategy, items in by_strategy.items():
        if len(items) > cfg.top_k_per_strategy:
            strat_demoted = sorted(
                h for h, _ in items if h in demote and h not in pinned_hashes
            )
            if strat_demoted:
                breaches.append(
                    {
                        "type": "per_strategy",
                        "strategy": strategy,
                        "limit": cfg.top_k_per_strategy,
                        "demoted": strat_demoted,
                    }
                )

    if len(pinned_hashes) > cfg.keep_last:
        breaches.append(
            {
                "type": "pinned_overflow",
                "limit": cfg.keep_last,
                "pinned": sorted(pinned_hashes),
            }
        )

    for breach in breaches:
        _log_retention_breach(
            breach=breach,
            cfg=cfg,
            metrics_registry=metrics,
            environment=env,
        )

    return {
        "keep_full": keep_full,
        "demote": demote,
        "pinned": pinned_hashes,
        "top_k": top_k_hashes,
        "breaches": breaches,
        "policy_version": cfg.policy_version,
    }


def apply_retention_plan(
    registry: InMemoryRunRegistry, plan: Mapping[str, Any]
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


__all__ = [
    "RetentionConfig",
    "apply_retention_plan",
    "plan_retention",
    "load_retention_config",
]
