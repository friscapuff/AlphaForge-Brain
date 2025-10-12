#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out", type=str, default="zz_artifacts/openapi.deref.regen.json"
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    committed = repo_root / "openapi.deref.json"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(committed.read_text(encoding="utf-8"))
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Fixture wrote canonical OpenAPI spec to {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
