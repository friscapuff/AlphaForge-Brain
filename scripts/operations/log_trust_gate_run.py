"""Automation script to log trust gate run attestations and enforce governance policy."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import zipfile
from typing import Any, Dict, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "operations" / "trust_gates.md"
WAIVERS_PATH = ROOT / "WAIVERS.md"
COLD_STORAGE_DIR = ROOT / "artifacts" / "trust_gates" / "waivers_cold"
REPORTS_ROOT = ROOT / "artifacts" / "trust_gates" / "reports"

AUTOMATION_HEADER = "## Run Attestation: "


class GovernanceError(RuntimeError):
    """Raised when governance policy is violated."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Run ID to document")
    parser.add_argument(
        "--report-path",
        help="Explicit trust_gate_report.json path (defaults to artifacts/trust_gates/reports/<run_id>/trust_gate_report.json)",
    )
    parser.add_argument(
        "--waiver-attachment",
        action="append",
        default=[],
        help="Path to supporting waiver attachment to archive",
    )
    parser.add_argument(
        "--operator",
        required=True,
        help="Name or handle of operator performing the attestation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print attestation entry without writing to disk",
    )
    return parser.parse_args()


def load_report(
    run_id: str, report_path: Optional[str]
) -> tuple[pathlib.Path, Dict[str, Any]]:
    candidate = (
        pathlib.Path(report_path)
        if report_path
        else REPORTS_ROOT / run_id / "trust_gate_report.json"
    )
    if not candidate.exists():
        raise GovernanceError(f"trust_gate_report.json not found at {candidate}")
    with candidate.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return candidate, data


def extract_attestation(report: Dict[str, Any]) -> Dict[str, Any]:
    trust = report.get("trust_gate") or report
    metadata = {
        "suite_version": trust.get("suite_version"),
        "tolerance_profile": trust.get("tolerance_profile"),
        "executed": trust.get("executed_at"),
        "baseline_version": trust.get("baseline_version"),
        "vendor_versions": trust.get("vendor_versions"),
        "dataset_hashes": trust.get("dataset_hashes"),
        "waivers": trust.get("waivers"),
        "tolerance_arbitration": trust.get("tolerance_arbitration"),
    }
    missing = [key for key, value in metadata.items() if value in (None, "")]
    if missing:
        raise GovernanceError(f"Report missing required fields: {', '.join(missing)}")
    return metadata


def ensure_waiver_policy(waivers: Any) -> None:
    if not waivers:
        return
    now = dt.datetime.utcnow()
    for waiver in waivers:
        expiry = waiver.get("expiry")
        if not expiry:
            raise GovernanceError(f"Waiver missing expiry: {waiver}")
        expiry_dt = dt.datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        delta = expiry_dt - now
        if delta.total_seconds() > 90 * 24 * 3600:
            raise GovernanceError(f"Waiver expiry exceeds 90-day limit: {waiver}")


def archive_waivers(run_id: str, attachments: list[str]) -> Optional[pathlib.Path]:
    if not attachments:
        return None
    COLD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"{run_id}_waivers_{timestamp}.zip"
    archive_path = COLD_STORAGE_DIR / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for attachment in attachments:
            path = pathlib.Path(attachment).resolve()
            if not path.exists():
                raise GovernanceError(f"Attachment not found: {path}")
            zipf.write(path, arcname=path.name)
    return archive_path


def compute_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_entry(
    run_id: str,
    metadata: Dict[str, Any],
    operator: str,
    cold_storage: Optional[pathlib.Path],
    report_hash: str,
) -> str:
    executed = metadata["executed"]
    vendor_versions = ", ".join(metadata.get("vendor_versions", []))
    dataset_hashes = ", ".join(metadata.get("dataset_hashes", []))
    waivers = metadata.get("waivers") or []
    waiver_summary = (
        ", ".join(f"{w.get('id')} (exp {w.get('expiry')})" for w in waivers) or "none"
    )
    entry_lines = [
        f"## Run Attestation: {run_id}",
        f"- Executed: {executed}",
        f"- Suite Version: {metadata['suite_version']}",
        f"- Tolerance Profile: {metadata['tolerance_profile']}",
        f"- Vendor Versions: {vendor_versions}",
        f"- Dataset Hashes: {dataset_hashes}",
        f"- Baseline Version: {metadata['baseline_version']}",
        f"- Waivers: {waiver_summary}",
        f"- Tolerance Arbitration: {metadata['tolerance_arbitration'] or 'none'}",
        f"- Cold Storage Copy: {cold_storage if cold_storage else 'none'}",
        f"- Trust Gate Report Hash: {report_hash}",
        f"- Logged By: {operator}",
        "",
    ]
    return "\n".join(entry_lines)


def append_entry(entry: str, dry_run: bool) -> None:
    if dry_run:
        print(entry)
        return
    if not DOC_PATH.exists():
        raise GovernanceError(f"Operations guide not found: {DOC_PATH}")
    with DOC_PATH.open("a", encoding="utf-8") as doc:
        doc.write("\n" + entry)
    subprocess.run(["git", "add", str(DOC_PATH)], check=False)


def main() -> int:
    args = parse_args()
    report_path, report = load_report(args.run_id, args.report_path)
    metadata = extract_attestation(report)
    ensure_waiver_policy(metadata.get("waivers"))
    cold_storage = archive_waivers(args.run_id, args.waiver_attachment)
    report_hash = compute_hash(report_path)
    entry = render_entry(
        args.run_id, metadata, args.operator, cold_storage, report_hash
    )
    append_entry(entry, args.dry_run)
    print(f"Logged trust gate run {args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
