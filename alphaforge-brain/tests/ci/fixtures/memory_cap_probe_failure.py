#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="zz_artifacts/memory_cap.json")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "rss_mb_peak": 2048.0,
        "cap_mb": 1536,
        "within_cap": False,
        "samples": 5,
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
