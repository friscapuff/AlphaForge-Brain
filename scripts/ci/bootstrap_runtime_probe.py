#!/usr/bin/env python3
"""Bootstrap Runtime Probe

Measures first-run (cold bootstrap) vs second-run (warmed) runtime for the
core deterministic pipeline (leveraging determinism_replay.run_once) and
computes ratio = first / second. Policy: ratio <= threshold (default 1.2).

Outputs JSON to stdout (and optional --out path):
{
  "first_s": float,
  "second_s": float,
  "ratio": float,
  "threshold": float,
  "pass": bool
}

Rationale: The first invocation includes module import, registry population,
and any lazy schema initialization, approximating bootstrap cost relative to
steady-state execution.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DET_SCRIPT = ROOT / "alphaforge-brain" / "scripts" / "ci" / "determinism_replay.py"


def load_replay_module():  # type: ignore
    from importlib.machinery import SourceFileLoader

    spec = SourceFileLoader("_determinism_replay", str(DET_SCRIPT)).load_module()  # type: ignore
    return spec


def timed_call(fn, *a, **kw) -> tuple[float, Any]:
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    t1 = time.perf_counter()
    return t1 - t0, out


def probe(seed: int) -> dict[str, Any]:
    mod = load_replay_module()
    first_s, _ = timed_call(mod.run_once, seed)  # type: ignore[attr-defined]
    second_s, _ = timed_call(mod.run_once, seed)  # type: ignore[attr-defined]
    ratio = (first_s / second_s) if second_s > 0 else float("inf")
    return {
        "first_s": first_s,
        "second_s": second_s,
        "ratio": ratio,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--threshold", type=float, default=1.2)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    res = probe(args.seed)
    res["threshold"] = args.threshold
    res["pass"] = bool(res["ratio"] <= args.threshold)
    out_json = json.dumps(res, indent=2, sort_keys=True)
    print(out_json)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
    return 0 if res["pass"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
