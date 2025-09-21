"""Compare current ingestion metrics to a stored baseline JSON (Phase K T062/T063).

Severity classification:
    - 0: Perfect match (symbol,timeframe,row counts,data_hash)
    - 20: Minor drift (only elapsed_seconds differs or non-critical fields like performance timing)
    - 50: Breaking drift (row counts or data_hash differ)

Exit codes follow the above mapping enabling CI policy gating.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(p: Path) -> dict[str, Any]:
    data: Any = json.loads(p.read_text(encoding="utf-8"))
    # Coerce to dict[str, Any] (baseline JSON schema is known)
    assert isinstance(data, dict)
    return data


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", help="Path to baseline ingestion_perf JSON")
    ap.add_argument("current", help="Path to current ingestion_perf JSON")
    args = ap.parse_args()
    base = load_json(Path(args.baseline))
    cur = load_json(Path(args.current))
    breaking_fields = []
    for field in ["symbol", "timeframe", "row_count_canonical", "row_count_raw", "data_hash"]:
        if base.get(field) != cur.get(field):
            breaking_fields.append(field)
    if breaking_fields:
        print("BREAKING drift detected in fields: " + ", ".join(breaking_fields))
        for f in breaking_fields:
            print(f"  {f}: baseline={base.get(f)} current={cur.get(f)}")
        sys.exit(50)
    # Only elapsed_seconds difference is considered minor (even if identical we still report)
    elapsed_base = base.get("elapsed_seconds")
    elapsed_cur = cur.get("elapsed_seconds")
    if elapsed_base != elapsed_cur:
        print(f"MINOR drift (elapsed_seconds) baseline={elapsed_base} current={elapsed_cur}")
        sys.exit(20)
    print("PERFECT match (including elapsed_seconds)")
    sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
