"""Generate grouped mypy error markdown and update metrics history.

Usage:
  python scripts/type_hygiene/generate_mypy_grouping.py \
      --baseline zz_artifacts/type_hygiene/mypy_baseline.json \
      --out-markdown zz_artifacts/type_hygiene/mypy_grouping.md \
      --metrics-history zz_artifacts/type_hygiene/metrics_history.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def build_markdown(baseline: dict[str, Any]) -> str:
    summary = baseline["summary"]
    errors: list[dict[str, Any]] = baseline["errors"]
    by_code: dict[str, int] = summary["by_code"]
    lines: list[str] = []
    lines.append("# Mypy Error Grouping (Baseline)")
    lines.append("")
    lines.append(f"Captured (UTC): {summary['captured_at']}")
    lines.append("")
    lines.append(
        f"Total errors: {summary['total_errors']} across {summary['unique_files']} files."
    )
    lines.append("")
    lines.append("## Breakdown by code")
    lines.append("")
    for code, count in sorted(by_code.items()):
        lines.append(f"- `{code}`: {count}")
    lines.append("")
    lines.append("## Details by Code")
    seen_codes = sorted(by_code.keys())
    for code in seen_codes:
        lines.append(f"\n### `{code}`")
        for err in [e for e in errors if e["code"] == code]:
            rel = err["path"].replace("\\", "/")
            lines.append(f"- {rel}:{err['line']} — {err['message']}")
    lines.append("")
    return "\n".join(lines)


def append_metrics_history(history_path: Path, baseline: dict[str, Any]) -> None:
    try:
        history = load_json(history_path)
        if not isinstance(history, list):  # corrupt sentinel
            history = []
    except FileNotFoundError:
        history = []
    entry = {
        "timestamp_utc": _dt.datetime.utcnow().isoformat() + "Z",
        "event": "grouping_generated",
        "total_errors": baseline["summary"]["total_errors"],
        "by_code": baseline["summary"]["by_code"],
    }
    history.append(entry)
    save_json(history_path, history)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--out-markdown", type=Path, required=True)
    ap.add_argument("--metrics-history", type=Path, required=True)
    ns = ap.parse_args()

    baseline = load_json(ns.baseline)
    md = build_markdown(baseline)
    save_text(ns.out_markdown, md)
    append_metrics_history(ns.metrics_history, baseline)
    print(f"Wrote grouping to {ns.out_markdown} and appended metrics history.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
