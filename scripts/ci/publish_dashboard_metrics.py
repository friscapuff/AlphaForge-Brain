from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from services.governance.models import WaiverCadenceSnapshot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish governance dashboard metrics")
    default_root = _repo_root()
    parser.add_argument(
        "--cadence",
        type=Path,
        default=default_root / "zz_artifacts" / "governance" / "waiver_cadence.json",
        help="Path to waiver cadence snapshot JSON",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_root / "zz_artifacts" / "governance" / "dashboard_metrics.prom",
        help="Output path for Prometheus metrics payload",
    )
    return parser.parse_args(argv)


def _load_snapshot(path: Path) -> WaiverCadenceSnapshot:
    if not path.exists():
        raise FileNotFoundError(f"Cadence snapshot not found: {path}")
    return WaiverCadenceSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def _render_metrics(snapshot: WaiverCadenceSnapshot) -> str:
    lines: list[str] = []
    status_counts: Counter[str] = Counter()

    for item in snapshot.items:
        status = item.escalation_status.value
        status_counts[status] += 1
        labels = f'waiver_id="{item.waiver_id}",status="{status}"'
        lines.append(f"waiver_cadence_age_days{{{labels}}} {item.age_days}")

    for status, count in sorted(status_counts.items()):
        lines.append(f'waiver_cadence_status_total{{status="{status}"}} {count}')

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    snapshot = _load_snapshot(args.cadence)
    payload = _render_metrics(snapshot)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "metrics_path": args.out.as_posix(),
                "items": len(snapshot.items),
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
