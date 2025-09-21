from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REQUIRED_COLUMNS = {"timestamp","open","high","low","close","volume"}


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
    ap.add_argument("--out", default="dataset_presence.json")
    args = ap.parse_args()
    candidates = [
        Path("data") / f"{args.symbol.upper()}_5y.csv",
        Path("src/domain/data") / f"{args.symbol.upper()}_5y.csv",
    ]
    report: dict[str, object] = {
        "symbol": args.symbol.upper(),
        "timeframe": args.timeframe,
        "present": False,
        "path": None,
        "size_bytes": 0,
        "sha256": None,
        "required_columns_ok": False,
    }
    found = next((p for p in candidates if p.exists()), None)
    if found:
        report["present"] = True
        report["path"] = str(found)
        report["size_bytes"] = found.stat().st_size
        report["sha256"] = sha256_file(found)
        try:
            import pandas as pd
            df = pd.read_csv(found, nrows=1)
            report["required_columns_ok"] = REQUIRED_COLUMNS.issubset(df.columns)
        except Exception:
            report["required_columns_ok"] = False
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Exit codes: 0 present+columns ok, 2 missing, 3 present but columns fail
    if not report["present"]:
        sys.exit(2)
    if not report["required_columns_ok"]:
        sys.exit(3)

if __name__ == "__main__":
    main()
