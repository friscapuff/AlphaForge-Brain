#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out", type=str, default="zz_artifacts/determinism_replay.json"
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": args.seed,
        "ok": False,
        "r1": {
            "sized_hash": "aaa",
            "fills_hash": "bbb",
            "positions_hash": "ccc",
        },
        "r2": {
            "sized_hash": "xxx",
            "fills_hash": "yyy",
            "positions_hash": "zzz",
        },
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print("Determinism replay: FAIL")
    print(f"Summary written: {out_path}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
