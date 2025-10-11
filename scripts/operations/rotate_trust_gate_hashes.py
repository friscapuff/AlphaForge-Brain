"""Re-validate trust gate report signatures within a time window."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import pathlib
from typing import Any, Dict, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORTS_ROOT = ROOT / "artifacts" / "trust_gates" / "reports"
DOC_PATH = ROOT / "docs" / "operations" / "trust_gates.md"
AUTOMATION_HEADER = "## Run Attestation: "


class RotationError(RuntimeError):
    """Raised when hash rotation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        default="90d",
        help="Time window to scan (e.g., 90d, 12h). Use 'all' to scan entire history.",
    )
    return parser.parse_args()


def parse_window(since: str) -> dt.datetime:
    if since == "all":
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    unit = since[-1]
    value = int(since[:-1])
    if unit == "d":
        delta = dt.timedelta(days=value)
    elif unit == "h":
        delta = dt.timedelta(hours=value)
    else:
        raise RotationError(f"Unsupported window format: {since}")
    return dt.datetime.now(dt.timezone.utc) - delta


def iter_reports(since: dt.datetime) -> Iterable[pathlib.Path]:
    if not REPORTS_ROOT.exists():
        return []
    for run_dir in REPORTS_ROOT.iterdir():
        if not run_dir.is_dir():
            continue
        report_path = run_dir / "trust_gate_report.json"
        if not report_path.exists():
            continue
        mtime = dt.datetime.fromtimestamp(
            report_path.stat().st_mtime, tz=dt.timezone.utc
        )
        if mtime >= since:
            yield report_path


def compute_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_attestation(run_id: str) -> Dict[str, Any]:
    if not DOC_PATH.exists():
        return {}
    with DOC_PATH.open("r", encoding="utf-8") as doc:
        content = doc.read()
    marker = f"{AUTOMATION_HEADER}{run_id}\n"
    idx = content.find(marker)
    if idx == -1:
        return {}
    section = content[idx:].split("\n## Run Attestation:", 1)[0]
    attestation: Dict[str, Any] = {}
    for line in section.splitlines():
        if line.startswith("- "):
            key, _, value = line[2:].partition(": ")
            attestation[key.lower()] = value.strip()
    return attestation


def main() -> int:
    args = parse_args()
    since = parse_window(args.since)
    failures = []
    print(f"Scanning trust gate reports modified since {since.isoformat()}")
    for report_path in iter_reports(since):
        run_id = report_path.parent.name
        report_hash = compute_hash(report_path)
        attestation = load_attestation(run_id)
        recorded = attestation.get("trust_gate_report_hash")
        if recorded and recorded != report_hash:
            failures.append((run_id, recorded, report_hash))
        elif not recorded:
            print(
                f"Run {run_id} has no recorded hash; append manually after verification."
            )
        else:
            print(f"Run {run_id} hash verified: {report_hash}")
    if failures:
        for run_id, expected, actual in failures:
            print(f"HASH MISMATCH {run_id}: expected {expected}, actual {actual}")
        raise RotationError(
            "One or more hashes mismatched; investigate before proceeding."
        )
    print("Hash rotation completed with no mismatches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
