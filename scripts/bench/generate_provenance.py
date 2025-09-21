"""Generate dataset provenance file (Phase K T065).

Outputs JSON with: symbol, timeframe, source_path, file_size_bytes, sha256_raw, generated_at_utc.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--timeframe", default="1d")
    ap.add_argument("--out", default="benchmarks/dataset_provenance_nvda_1d.json")
    ap.add_argument("--path", default=None, help="Explicit dataset CSV path; auto-detect if omitted")
    args = ap.parse_args()
    candidates = [
        Path(args.path) if args.path else None,
        Path("data") / f"{args.symbol.upper()}_5y.csv",
        Path("src/domain/data") / f"{args.symbol.upper()}_5y.csv",
    ]
    found = next((p for p in candidates if p and p.exists()), None)
    if not found:
        raise FileNotFoundError("Dataset CSV not found in candidates; supply --path")
    found = found.resolve()
    provenance = {
        "symbol": args.symbol.upper(),
        "timeframe": args.timeframe,
        "source_path": str(found),
        "file_size_bytes": found.stat().st_size,
        "sha256_raw": sha256_file(found),
        "generated_at_utc": int(time.time()),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"Wrote provenance -> {out_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
