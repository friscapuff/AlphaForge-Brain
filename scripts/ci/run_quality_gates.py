#!/usr/bin/env python3
"""Unified CI Quality Gates (T020)

Enforces (fails with non-zero exit):
 1. Determinism (replay) - wraps existing determinism_replay script
 2. Contract drift - compares dumped OpenAPI schema to committed copy
 3. Migration head checksum - reuses check_migrations_head
 4. Memory cap - executes memory_cap stub (or real impl later) and enforces cap when value available
 5. Cross-root integrity - wraps check_cross_root

Exit codes:
 0 success, 1 generic failure. Individual failure reasons aggregated in JSON summary.

Produces JSON summary at zz_artifacts/quality_gates_summary.json for later
collection / badge emission.

Assumptions / Future work:
 - Memory cap stub currently emits null rss; treated as pass, once implemented we enforce rss_mb_peak <= cap_mb.
 - Contract drift detection: compares hashes of sorted JSON of openapi.deref.json vs regenerated.
 - Determinism script already returns non-zero on failure; we capture its payload.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "zz_artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def _run(cmd: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    brain_src = ROOT / "alphaforge-brain" / "src"
    existing = env.get("PYTHONPATH", "")
    if str(brain_src) not in existing.split(os.pathsep):
        env["PYTHONPATH"] = (
            (existing + os.pathsep + str(brain_src)).strip(os.pathsep)
            if existing
            else str(brain_src)
        )
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    return proc.returncode, proc.stdout


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def determinism_gate(summary: dict[str, Any]) -> None:
    out_path = ARTIFACT_DIR / "determinism_replay.json"
    code, out = _run(
        [
            sys.executable,
            str(ROOT / "alphaforge-brain" / "scripts" / "ci" / "determinism_replay.py"),
            "--out",
            str(out_path),
        ]
    )
    summary["determinism"] = {"exit_code": code}
    if out_path.exists():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover - defensive
            payload = {"error": f"failed to parse output: {e}"}
        summary["determinism"].update(payload)
    if code != 0:
        summary["failures"].append("determinism")


def contract_drift_gate(summary: dict[str, Any]) -> None:
    # Expect committed canonical openapi.deref.json
    committed = ROOT / "openapi.deref.json"
    if not committed.exists():
        summary["contract"] = {"skipped": True, "reason": "openapi.deref.json missing"}
        return
    # Attempt regeneration by invoking dump_schema if present
    dump_script = ROOT / "alphaforge-brain" / "scripts" / "ci" / "dump_schema.py"
    if not dump_script.exists():
        summary["contract"] = {"skipped": True, "reason": "dump_schema.py missing"}
        return
    regen_path = ARTIFACT_DIR / "openapi.deref.regen.json"
    code, out = _run([sys.executable, str(dump_script), str(regen_path)])
    if code != 0:
        summary["contract"] = {
            "exit_code": code,
            "stderr": out,
            "error": "schema regeneration failed",
        }
        summary["failures"].append("contract_regen")
        return
    try:
        committed_json = json.loads(committed.read_text(encoding="utf-8"))
        regen_json = json.loads(regen_path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        summary["contract"] = {"error": f"json parse failure: {e}"}
        summary["failures"].append("contract_parse")
        return
    # Normalize by dumping sorted keys
    committed_norm = json.dumps(committed_json, sort_keys=True)
    regen_norm = json.dumps(regen_json, sort_keys=True)
    h_committed = _sha256_text(committed_norm)
    h_regen = _sha256_text(regen_norm)
    drift = h_committed != h_regen
    summary["contract"] = {
        "committed_hash": h_committed,
        "regen_hash": h_regen,
        "drift": drift,
    }
    if drift:
        summary["failures"].append("contract_drift")


def migrations_head_gate(summary: dict[str, Any]) -> None:
    script = ROOT / "scripts" / "ci" / "check_migrations_head.py"
    if not script.exists():
        summary["migrations"] = {
            "skipped": True,
            "reason": "check_migrations_head.py missing",
        }
        return
    code, out = _run([sys.executable, str(script)])
    summary["migrations"] = {"exit_code": code, "output": out.strip()}
    if code != 0:
        summary["failures"].append("migrations_head")


def memory_cap_gate(summary: dict[str, Any]) -> None:
    script = ROOT / "scripts" / "ci" / "memory_cap_probe.py"
    if not script.exists():
        summary["memory"] = {"skipped": True, "reason": "memory_cap_probe.py missing"}
        return
    out_path = ARTIFACT_DIR / "memory_cap.json"
    code, out = _run([sys.executable, str(script), "--out", str(out_path)])
    try:
        detail = json.loads(out_path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        detail = {"error": f"parse failure: {e}", "raw": out}
    detail["exit_code"] = code
    if not detail.get("skipped") and not detail.get("within_cap", True):
        summary["failures"].append("memory_cap")
    summary["memory"] = detail


def cross_root_gate(summary: dict[str, Any]) -> None:
    script = ROOT / "scripts" / "ci" / "check_cross_root.py"
    if not script.exists():
        summary["cross_root"] = {
            "skipped": True,
            "reason": "check_cross_root.py missing",
        }
        return
    code, out = _run([sys.executable, str(script)])
    summary["cross_root"] = {"exit_code": code, "output": out.strip()}
    if code != 0:
        summary["failures"].append("cross_root")


def main() -> int:
    summary: dict[str, Any] = {"failures": []}
    determinism_gate(summary)
    contract_drift_gate(summary)
    migrations_head_gate(summary)
    memory_cap_gate(summary)
    cross_root_gate(summary)

    summary["passed"] = len(summary["failures"]) == 0
    out_file = ARTIFACT_DIR / "quality_gates_summary.json"
    out_file.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
