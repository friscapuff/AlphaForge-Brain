"""Governance retention CLI commands."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

import click
from domain.run.retention_policy import load_retention_config
from services.audit.governance_logger import append_audit_log, record_governance_event

PIN_STORE_ENV = "RETENTION_PIN_STORE"
DEFAULT_PIN_STORE = Path("zz_artifacts/retention/pinned_runs.json")
RETENTION_LATENCY_LOG = Path("zz_artifacts/governance/retention_cli_latency.jsonl")


def _resolve_pin_store(environment: Mapping[str, str] | None = None) -> Path:
    env = environment or os.environ
    candidate = env.get(PIN_STORE_ENV)
    path = Path(candidate) if candidate else DEFAULT_PIN_STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({"pinned": {}}, indent=2), encoding="utf-8")
    return path


def _load_pin_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"pinned": {}}, indent=2), encoding="utf-8")
        return {"pinned": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {"pinned": {}}
    pinned = payload.get("pinned")
    if not isinstance(pinned, dict):
        payload["pinned"] = {}
    return payload


def _save_pin_state(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _emit_cli_event(
    command: str,
    *,
    start_time: float,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    duration_ms = int((perf_counter() - start_time) * 1000)
    details: dict[str, Any] = {
        "duration_ms": duration_ms,
        "threshold_ms": 5000,
        "within_sla": duration_ms <= 5000,
    }
    if metadata:
        details.update(metadata)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"retention.cli.{command}",
        "details": details,
    }
    append_audit_log(payload=payload, audit_path=RETENTION_LATENCY_LOG)
    record_governance_event(message=f"retention.cli.{command}", details=details)


@click.group(help="Retention governance tooling")
def retention() -> None:
    """Primary click group for retention governance."""


@retention.group(help="Inspect retention policy metadata")
def policy() -> None:
    """Policy sub-command group."""


@policy.command("inspect")
def policy_inspect() -> None:
    """Print the active retention policy configuration."""

    start = perf_counter()
    cfg = load_retention_config()
    serialized = json.dumps(cfg.as_dict(), indent=2)
    click.echo(serialized)
    _emit_cli_event(
        "policy.inspect",
        start_time=start,
        metadata={
            "policy_version": cfg.policy_version,
            "bytes": len(serialized.encode("utf-8")),
        },
    )


@retention.command("pin")
@click.option("--run-hash", required=True, help="Run hash to pin for retention.")
@click.option("--waiver-id", help="Associated waiver identifier if required.")
@click.option("--note", help="Optional annotation stored with the pin entry.")
def pin(run_hash: str, waiver_id: str | None, note: str | None) -> None:
    """Pin a run under the active retention policy."""

    start = perf_counter()
    cfg = load_retention_config()
    if cfg.waiver_required and not waiver_id:
        raise click.ClickException(
            "Retention policy requires --waiver-id for pin operations."
        )

    store_path = _resolve_pin_store()
    state = _load_pin_state(store_path)
    pinned = state.setdefault("pinned", {})

    timestamp = datetime.now(timezone.utc).isoformat()
    pinned[run_hash] = {
        "waiver_id": waiver_id,
        "note": note,
        "pinned_at": timestamp,
        "policy_version": cfg.policy_version,
    }
    _save_pin_state(store_path, state)
    _emit_cli_event(
        "pin",
        start_time=start,
        metadata={
            "run_hash": run_hash,
            "waiver_id": waiver_id,
            "note": note,
            "policy_version": cfg.policy_version,
            "pin_store": str(store_path),
            "pinned_total": len(pinned),
        },
    )
    click.echo(f"Pinned run {run_hash} under policy {cfg.policy_version}")


@retention.command("unpin")
@click.option("--run-hash", required=True, help="Run hash to remove from pinned set.")
def unpin(run_hash: str) -> None:
    """Remove a run from the pinned retention set."""

    start = perf_counter()
    cfg = load_retention_config()
    store_path = _resolve_pin_store()
    state = _load_pin_state(store_path)
    pinned = state.setdefault("pinned", {})

    if pinned.pop(run_hash, None) is None:
        raise click.ClickException(f"Run {run_hash} is not currently pinned.")

    _save_pin_state(store_path, state)
    _emit_cli_event(
        "unpin",
        start_time=start,
        metadata={
            "run_hash": run_hash,
            "policy_version": cfg.policy_version,
            "pin_store": str(store_path),
            "pinned_total": len(pinned),
        },
    )
    click.echo(f"Unpinned run {run_hash}")


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point."""

    try:
        retention.main(args=argv, prog_name="retention", standalone_mode=False)
    except click.ClickException as exc:  # pragma: no cover - click handles formatting
        raise SystemExit(str(exc)) from exc
    return 0


__all__ = ["retention", "policy", "pin", "unpin", "main"]
