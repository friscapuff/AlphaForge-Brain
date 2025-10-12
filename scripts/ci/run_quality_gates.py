#!/usr/bin/env python3
"""Unified CI Quality Gates (T020).

Enforces (fails with non-zero exit):
 1. Determinism replay integrity (wraps determinism_replay.py)
 2. OpenAPI contract drift (hash comparison vs canonical snapshot)
 3. Migration head checksum (check_migrations_head.py)
 4. Memory cap (memory_cap_probe.py emitting RSS payload)
 5. Cross-root integrity (check_cross_root.py)

Exit codes:
 0 success, 1 failure. First failing gate short-circuits the run to keep
 diagnostics focused. A summary JSON is written to
 zz_artifacts/quality_gates_summary.json for downstream dashboards.

Fixture overrides:
 - Set `AF_QG_FIXTURE_<GATE>` to the absolute path of a replacement script
     (e.g. `AF_QG_FIXTURE_DETERMINISM`). Missing overrides mark the gate as skipped.
 - Set `AF_FORCE_QG_FAILURE` to a comma-separated list of gates (or `all`) to
     deliberately fail targeted gates while still emitting diagnostics.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "zz_artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

GATE_ORDER = ["determinism", "contract", "migrations", "memory", "cross_root"]
SUMMARY_VERSION = "1.0.0"

SKIP_TEMPLATES: dict[str, dict[str, Any]] = {
    "determinism": {"exit_code": -1, "failed": False, "skipped": True},
    "contract": {
        "exit_code": -1,
        "committed_hash": "",
        "regen_hash": "",
        "drift": False,
        "failed": False,
        "skipped": True,
    },
    "migrations": {
        "exit_code": -1,
        "output": "",
        "failed": False,
        "skipped": True,
    },
    "memory": {
        "exit_code": -1,
        "within_cap": True,
        "rss_bytes": 0,
        "cap_bytes": 0,
        "failed": False,
        "skipped": True,
    },
    "cross_root": {
        "exit_code": -1,
        "output": "",
        "failed": False,
        "skipped": True,
    },
}


def _skip_result(gate: str, reason: str | None) -> dict[str, Any]:
    payload = deepcopy(SKIP_TEMPLATES[gate])
    if reason:
        payload["reason"] = reason
    return payload


def _forced_failures() -> set[str]:
    raw = os.environ.get("AF_FORCE_QG_FAILURE", "")
    tokens = {token.strip().lower() for token in raw.split(",") if token.strip()}
    if "all" in tokens:
        return set(GATE_ORDER)
    return tokens


def _should_force(gate: str, forced: Iterable[str]) -> bool:
    return gate.lower() in forced


def _run(cmd: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    brain_src = ROOT / "alphaforge-brain" / "src"
    brain_root = ROOT / "alphaforge-brain"
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    for candidate in (str(brain_root), str(brain_src)):
        if candidate not in parts:
            parts.append(candidate)
    if parts:
        env["PYTHONPATH"] = os.pathsep.join(parts)
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    return proc.returncode, proc.stdout


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_script(name: str, default: Path | None) -> tuple[Path | None, str | None]:
    env_key = f"AF_QG_FIXTURE_{name.upper()}"
    override = os.environ.get(env_key)
    if override:
        override_path = Path(override)
        if override_path.exists():
            return override_path, None
        return None, f"fixture override missing: {override_path}"
    if default and default.exists():
        return default, None
    if default:
        return None, f"default script missing: {default}"
    return None, "no script configured"


def determinism_gate(summary: dict[str, Any], forced: set[str]) -> bool:
    script, skip_reason = _resolve_script(
        "determinism",
        ROOT / "alphaforge-brain" / "scripts" / "ci" / "determinism_replay.py",
    )
    if script is None:
        summary["determinism"] = _skip_result("determinism", skip_reason)
        return False

    out_path = ARTIFACT_DIR / "determinism_replay.json"
    code, out = _run(
        [
            sys.executable,
            str(script),
            "--out",
            str(out_path),
        ]
    )
    detail: dict[str, Any] = {
        "exit_code": code,
        "stdout": out.strip(),
        "script": str(script),
    }
    if out_path.exists():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            payload = {"error": f"parse failure: {exc}"}
        detail["payload"] = payload
    payload_ok = detail.get("payload", {}).get("ok", True)
    forced_failure = _should_force("determinism", forced)
    failed = forced_failure or code != 0 or not payload_ok
    if not payload_ok and code == 0:
        detail.setdefault("reason", "payload flagged non-determinism")
    if forced_failure:
        detail["forced_failure"] = True
    detail["failed"] = failed
    summary["determinism"] = detail
    if failed:
        summary.setdefault("failures", []).append("determinism")
    return failed


def contract_drift_gate(summary: dict[str, Any], forced: set[str]) -> bool:
    committed = ROOT / "openapi.deref.json"
    if not committed.exists():
        summary["contract"] = _skip_result("contract", "openapi.deref.json missing")
        return False

    script, skip_reason = _resolve_script(
        "contract", ROOT / "scripts" / "dev" / "export_openapi.py"
    )
    if script is None:
        summary["contract"] = _skip_result("contract", skip_reason)
        return False

    regen_path = ARTIFACT_DIR / "openapi.deref.regen.json"
    override_set = os.environ.get("AF_QG_FIXTURE_CONTRACT")
    if override_set:
        cmd = [sys.executable, str(script), "--out", str(regen_path)]
    else:
        cmd = [sys.executable, str(script)]
    code, out = _run(cmd)
    detail: dict[str, Any] = {
        "exit_code": code,
        "stdout": out.strip(),
        "script": str(script),
        "regen_path": str(regen_path),
    }
    if code != 0:
        detail["failed"] = True
        detail["error"] = "schema regeneration failed"
        summary["contract"] = detail
        summary.setdefault("failures", []).append("contract")
        return True

    produced_path = (
        regen_path if override_set else ARTIFACT_DIR / "openapi.generated.json"
    )
    if not produced_path.exists():
        detail["failed"] = True
        detail["error"] = f"regen artifact missing: {produced_path}"
        summary["contract"] = detail
        summary.setdefault("failures", []).append("contract")
        return True

    if produced_path != regen_path:
        regen_path.write_text(
            produced_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    detail["source_artifact"] = str(produced_path)

    try:
        committed_json = json.loads(committed.read_text(encoding="utf-8"))
        regen_json = json.loads(regen_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        detail["failed"] = True
        detail["error"] = f"json parse failure: {exc}"
        summary["contract"] = detail
        summary.setdefault("failures", []).append("contract")
        return True

    committed_norm = json.dumps(committed_json, sort_keys=True)
    regen_norm = json.dumps(regen_json, sort_keys=True)
    h_committed = _sha256_text(committed_norm)
    h_regen = _sha256_text(regen_norm)
    drift = h_committed != h_regen
    detail.update(
        {
            "committed_hash": h_committed,
            "regen_hash": h_regen,
            "drift": drift,
        }
    )
    forced_failure = _should_force("contract", forced)
    failed = forced_failure or drift
    if forced_failure:
        detail["forced_failure"] = True
    detail["failed"] = failed
    summary["contract"] = detail
    if failed:
        summary.setdefault("failures", []).append("contract")
    return failed


def migrations_head_gate(summary: dict[str, Any], forced: set[str]) -> bool:
    script, skip_reason = _resolve_script(
        "migrations", ROOT / "scripts" / "ci" / "check_migrations_head.py"
    )
    if script is None:
        summary["migrations"] = _skip_result("migrations", skip_reason)
        return False

    code, out = _run([sys.executable, str(script)])
    detail = {
        "exit_code": code,
        "output": out.strip(),
        "script": str(script),
    }
    forced_failure = _should_force("migrations", forced)
    failed = forced_failure or code != 0
    if forced_failure:
        detail["forced_failure"] = True
    detail["failed"] = failed
    summary["migrations"] = detail
    if failed:
        summary.setdefault("failures", []).append("migrations")
    return failed


def memory_cap_gate(summary: dict[str, Any], forced: set[str]) -> bool:
    script, skip_reason = _resolve_script(
        "memory", ROOT / "scripts" / "ci" / "memory_cap_probe.py"
    )
    if script is None:
        summary["memory"] = _skip_result("memory", skip_reason)
        return False

    out_path = ARTIFACT_DIR / "memory_cap.json"
    code, out = _run([sys.executable, str(script), "--out", str(out_path)])
    detail: dict[str, Any] = {
        "exit_code": code,
        "stdout": out.strip(),
        "script": str(script),
        "out": str(out_path),
    }
    if out_path.exists():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            payload = {"error": f"parse failure: {exc}", "raw_output": out.strip()}
        detail.update(payload)
    forced_failure = _should_force("memory", forced)
    within_cap = detail.get("within_cap", True)
    failed = forced_failure or code != 0 or not within_cap
    if forced_failure:
        detail["forced_failure"] = True
    if not within_cap:
        detail.setdefault("reason", "RSS above configured cap")
    detail["failed"] = failed
    summary["memory"] = detail
    if failed:
        summary.setdefault("failures", []).append("memory")
    return failed


def cross_root_gate(summary: dict[str, Any], forced: set[str]) -> bool:
    script, skip_reason = _resolve_script(
        "cross_root", ROOT / "scripts" / "ci" / "check_cross_root.py"
    )
    if script is None:
        summary["cross_root"] = _skip_result("cross_root", skip_reason)
        return False

    code, out = _run([sys.executable, str(script)])
    detail = {
        "exit_code": code,
        "output": out.strip(),
        "script": str(script),
    }
    forced_failure = _should_force("cross_root", forced)
    failed = forced_failure or code != 0
    if forced_failure:
        detail["forced_failure"] = True
    detail["failed"] = failed
    summary["cross_root"] = detail
    if failed:
        summary.setdefault("failures", []).append("cross_root")
    return failed


def main() -> int:
    summary: dict[str, Any] = {"failures": []}
    forced = _forced_failures()
    gate_funcs = {
        "determinism": determinism_gate,
        "contract": contract_drift_gate,
        "migrations": migrations_head_gate,
        "memory": memory_cap_gate,
        "cross_root": cross_root_gate,
    }

    failure_seen = False
    for gate in GATE_ORDER:
        if failure_seen:
            summary[gate] = _skip_result(gate, "short-circuit after failure")
            continue
        failed = gate_funcs[gate](summary, forced)
        failure_seen = failure_seen or failed

    summary["passed"] = not failure_seen
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["version"] = SUMMARY_VERSION
    out_file = ARTIFACT_DIR / "quality_gates_summary.json"
    out_file.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
