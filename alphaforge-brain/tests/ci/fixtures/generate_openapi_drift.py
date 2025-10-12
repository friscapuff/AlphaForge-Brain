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

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "info": {"title": "Fixture Drift", "version": "9.9.9"},
        "paths": {
            "/fixture": {
                "get": {
                    "operationId": "fixtureGet",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Stubbed OpenAPI written to {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
