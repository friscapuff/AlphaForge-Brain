"""Capture ingestion baseline (Phase K T061).

Runs ingestion_perf then writes canonical baseline JSON to benchmarks/ directory.
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path
from typing import Any


# Defer path bootstrap into a helper to keep imports at top (E402 compliant)
def _ensure_src_on_path() -> None:
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    return None


_ensure_src_on_path()
ROOT = Path(__file__).resolve().parents[2]

INGEST_PATH = ROOT / "scripts" / "bench" / "ingestion_perf.py"
ns = runpy.run_path(str(INGEST_PATH))
run_ingestion = ns["run"]  # runtime dynamic; expected to be callable


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--timeframe", default="1d")
    ap.add_argument("--out", default="benchmarks/baseline_ingestion_nvda_1d.json")
    args = ap.parse_args()
    res: dict[str, Any] = run_ingestion(args.symbol, args.timeframe, None, None)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"Baseline captured -> {out_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
