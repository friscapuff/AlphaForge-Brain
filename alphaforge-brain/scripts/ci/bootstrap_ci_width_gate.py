#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def load_validation(validation_path: Path) -> dict[str, Any]:
    try:
        return json.loads(validation_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(
            f"ERROR: failed to read validation.json at {validation_path}: {e}",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="CI gate for bootstrap CI width (FR-122/FR-152)"
    )
    ap.add_argument(
        "run_dir",
        type=str,
        help="Path to run artifacts directory containing validation.json",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Maximum allowed CI width (overrides env)",
    )
    ap.add_argument(
        "--mode",
        type=str,
        default=os.environ.get("BOOT_CI_MODE", "STRICT").upper(),
        choices=["STRICT", "PERMISSIVE"],
        help="Gate mode",
    )
    args = ap.parse_args()

    thr = args.threshold
    if thr is None:
        env_thr = os.environ.get("BOOT_CI_WIDTH_MAX")
        if env_thr:
            try:
                thr = float(env_thr)
            except Exception:
                pass
    if thr is None:
        thr = 0.05  # default conservative width in CI

    vpath = Path(args.run_dir) / "validation.json"
    data = load_validation(vpath)
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    # Expect bootstrap info injected by writer under validation["bootstrap"]["ci"]
    bb = data.get("bootstrap") if isinstance(data, dict) else None
    ci = None
    if isinstance(bb, dict):
        ci = bb.get("ci")
    # Fallback: check top-level summary if provided by runner
    if not isinstance(ci, (list, tuple)):
        ci = summary.get("block_bootstrap_ci") or None
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        print("WARN: No bootstrap CI found; skipping gate.")
        sys.exit(0)
    try:
        width = float(ci[1]) - float(ci[0])
    except Exception:
        print("WARN: Invalid CI values; skipping gate.")
        sys.exit(0)

    if width > thr:
        msg = f"CI width {width:.6f} exceeds threshold {thr:.6f}"
        if args.mode == "STRICT":
            print(f"FAIL: {msg}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"WARN: {msg}")
            sys.exit(0)
    else:
        print(f"PASS: CI width {width:.6f} <= threshold {thr:.6f}")
        sys.exit(0)


if __name__ == "__main__":
    main()
