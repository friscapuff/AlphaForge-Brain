# ruff: noqa: E402
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Ensure package path for any local imports if added later
SYS_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(SYS_ROOT))
from typing import Any


def run_cmd(args: list[str], env: dict[str, str] | None = None) -> tuple[int, str, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    cp = subprocess.run(args, capture_output=True, text=True, env=merged_env)
    return cp.returncode, cp.stdout, cp.stderr


def find_latest_run_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = [
        p for p in root.iterdir() if p.is_dir() and (p / "validation.json").exists()
    ]
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance suite orchestrator (Phase F)")
    ap.add_argument("--artifacts-root", type=str, default="artifacts")
    ap.add_argument("--ci-threshold", type=float, default=0.05)
    ap.add_argument(
        "--mode", type=str, default="STRICT", choices=["STRICT", "PERMISSIVE"]
    )
    ap.add_argument("--out", type=str, default="zz_artifacts/acceptance_summary.json")
    args = ap.parse_args()

    summary: dict[str, Any] = {"steps": []}
    exit_code = 0

    # Step 1: Determinism replay
    code, out, err = run_cmd(
        [
            sys.executable,
            "alphaforge-brain/scripts/ci/determinism_replay.py",
            "--out",
            "zz_artifacts/determinism_replay.json",
        ]
    )
    summary["steps"].append(
        {
            "name": "determinism_replay",
            "code": code,
            "stdout": out[-5000:],
            "stderr": err[-5000:],
        }
    )
    if code != 0:
        exit_code = 1

    # Step 2: Bootstrap CI width gate if validation.json present
    latest = find_latest_run_dir(Path(args.artifacts_root))
    if latest:
        gate_env = {
            "BOOT_CI_WIDTH_MAX": str(args.ci_threshold),
            "BOOT_CI_MODE": args.mode,
        }
        code2, out2, err2 = run_cmd(
            [
                sys.executable,
                "alphaforge-brain/scripts/ci/bootstrap_ci_width_gate.py",
                str(latest),
            ],
            env=gate_env,
        )
        summary["steps"].append(
            {
                "name": "bootstrap_ci_width_gate",
                "code": code2,
                "stdout": out2[-5000:],
                "stderr": err2[-5000:],
            }
        )
        if code2 != 0 and args.mode == "STRICT":
            exit_code = 1
    else:
        summary["steps"].append(
            {
                "name": "bootstrap_ci_width_gate",
                "skipped": True,
                "reason": "no validation.json found",
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Acceptance summary written: {out_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
