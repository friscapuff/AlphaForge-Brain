"""Ingestion performance benchmark (T032)

Measures ingestion + normalization time for a configured symbol/timeframe slice.
Outputs JSON and optional Markdown summary capturing wall time and row counts.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

_ensure_src_on_path()

from domain.data.ingest_csv import load_generic_csv  # noqa: E402  (path bootstrap above)
from domain.data.registry import DatasetEntry, get_dataset, register_dataset  # noqa: E402


def run(symbol: str, timeframe: str, start: str | None, end: str | None) -> dict[str, Any]:
    t0 = time.perf_counter()
    # Attempt to retrieve existing dataset registration; if missing try to auto-register.
    try:
        entry = get_dataset(symbol, timeframe)
    except Exception as err:
        # Heuristic search paths for NVDA CSV (dev convenience)
        candidates = [
            Path("data") / f"{symbol.upper()}_5y.csv",
            Path("src/domain/data") / f"{symbol.upper()}_5y.csv",
        ]
        found: Path | None = next((p for p in candidates if p.exists()), None)
        if not found:
            raise FileNotFoundError(
                f"Dataset for {symbol} {timeframe} not registered and no CSV found at: " + ", ".join(str(c) for c in candidates)
            ) from err
        entry = DatasetEntry(symbol=symbol.upper(), timeframe=timeframe, provider="local_csv", path=str(found), calendar_id="NASDAQ")
        register_dataset(entry)
    if not entry.path:
        raise RuntimeError("Dataset entry missing path; cannot load CSV")
    _, meta = load_generic_csv(symbol=symbol, timeframe=timeframe, path=Path(entry.path), calendar_id=entry.calendar_id)
    elapsed = time.perf_counter() - t0
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "row_count_canonical": meta.row_count_canonical,
        "row_count_raw": meta.row_count_raw,
        "elapsed_seconds": round(elapsed, 6),
        "data_hash": meta.data_hash,
    }


def main() -> None:  # pragma: no cover - CLI utility
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="NVDA")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--out-json", default="ingestion_perf.json")
    p.add_argument("--out-md", default=None)
    args = p.parse_args()
    res = run(args.symbol, args.timeframe, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(res, indent=2), encoding="utf-8")
    if args.out_md:
        md = [
            "# Ingestion Performance",
            f"Symbol: {res['symbol']}  Timeframe: {res['timeframe']}",
            f"Rows (canonical/raw): {res['row_count_canonical']}/{res['row_count_raw']}",
            f"Elapsed: {res['elapsed_seconds']}s",
            f"Data Hash: {res['data_hash']}",
        ]
        Path(args.out_md).write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
