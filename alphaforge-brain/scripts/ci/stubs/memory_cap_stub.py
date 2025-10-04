"""Memory ceiling CI stub (T002) placeholder.

Exits 0 and prints a JSON result indicating no measurement. Replace with real
RSS sampling sweep enforcing CI caps (1.5 GB hard cap).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(out: str | None = None) -> int:
    summary = {
        "status": "STUB",
        "todo": "Implement memory ceiling sweep and enforcement",
        "rss_mb_peak": None,
        "cap_mb": 1536,
        "within_cap": True,
    }
    payload = json.dumps(summary, indent=2)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(main(out_path))
