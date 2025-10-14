from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from services.governance.models import (
    WaiverCadenceRecord,
    WaiverCadenceSnapshot,
    WaiverEscalationStatus,
)

WAIVER_SECTION_PATTERN = re.compile(r"^##\s+WAIVER:\s*(?P<waiver_id>\S+)")
FIELD_PATTERN = re.compile(r"^(?P<key>[A-Za-z][A-Za-z _-]*):\s*(?P<value>.+)$")
FR_PATTERN = re.compile(r"FR-\d+")
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(slots=True)
class ParsedWaiver:
    waiver_id: str
    opened_at: date
    expires_at: date | None
    fr_ids: list[str]
    next_action: str


def classify_escalation(age_days: int) -> WaiverEscalationStatus:
    if age_days >= 60:
        return WaiverEscalationStatus.ESCALATED
    if age_days >= 45:
        return WaiverEscalationStatus.WARNING
    return WaiverEscalationStatus.NORMAL


def build_record(
    *,
    waiver_id: str,
    fr_ids: list[str],
    opened_at: date,
    reference_date: date,
    next_action: str = "",
) -> WaiverCadenceRecord:
    age_days = max((reference_date - opened_at).days, 0)
    escalation = classify_escalation(age_days)
    return WaiverCadenceRecord(
        waiver_id=waiver_id,
        fr_ids=fr_ids,
        opened_at=opened_at,
        age_days=age_days,
        escalation_status=escalation,
        next_action=next_action,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_waiver_sections(lines: list[str]) -> Iterator[tuple[int, str]]:
    for index, line in enumerate(lines):
        match = WAIVER_SECTION_PATTERN.match(line.strip())
        if match:
            yield index, match.group("waiver_id")


def _extract_field(block: list[str], field_name: str) -> str | None:
    for line in block:
        match = FIELD_PATTERN.match(line.strip())
        if match and match.group("key").lower() == field_name.lower():
            return match.group("value").strip()
    return None


def _parse_date(value: str | None, *, field: str, waiver_id: str) -> date:
    if not value:
        raise ValueError(f"Waiver {waiver_id} missing required '{field}' field")
    match = DATE_PATTERN.search(value)
    if not match:
        raise ValueError(f"Waiver {waiver_id} has invalid '{field}' value: {value}")
    return date.fromisoformat(match.group(1))


def _parse_next_action(block: list[str]) -> str:
    raw = _extract_field(block, "Next Action")
    return raw or ""


def _collect_fr_ids(block: Iterable[str]) -> list[str]:
    ids: list[str] = []
    for line in block:
        for match in FR_PATTERN.findall(line):
            ids.append(match)
    return sorted(set(ids))


def parse_waivers(path: Path) -> list[ParsedWaiver]:
    if not path.exists():
        raise FileNotFoundError(f"Waiver file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    sections = list(_iter_waiver_sections(lines))
    parsed: list[ParsedWaiver] = []

    for idx, waiver_id in sections:
        # Determine block extent
        next_idx = next((n for n, _ in sections if n > idx), len(lines))
        block = lines[idx:next_idx]

        opened_value = _extract_field(block, "Opened")
        opened_at = _parse_date(opened_value, field="Opened", waiver_id=waiver_id)

        expires_value = _extract_field(block, "Expires")
        expires_at = None
        if expires_value:
            try:
                expires_at = _parse_date(
                    expires_value, field="Expires", waiver_id=waiver_id
                )
            except ValueError:
                expires_at = None

        fr_ids = _collect_fr_ids(block)
        next_action = _parse_next_action(block)

        parsed.append(
            ParsedWaiver(
                waiver_id=waiver_id,
                opened_at=opened_at,
                expires_at=expires_at,
                fr_ids=fr_ids,
                next_action=next_action,
            )
        )

    return parsed


def _emit_snapshot(records: list[WaiverCadenceRecord], out_path: Path) -> None:
    snapshot = WaiverCadenceSnapshot(
        generated_at=datetime.now(timezone.utc),
        items=records,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate waiver cadence snapshot")
    default_root = _repo_root()
    parser.add_argument(
        "--waivers",
        type=Path,
        default=default_root / "WAIVERS.md",
        help="Path to WAIVERS.md",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_root / "zz_artifacts" / "governance" / "waiver_cadence.json",
        help="Output path for cadence snapshot JSON",
    )
    parser.add_argument(
        "--reference-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Reference date for age calculations (ISO format)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    parsed_waivers = parse_waivers(args.waivers)

    records = [
        build_record(
            waiver_id=item.waiver_id,
            fr_ids=item.fr_ids,
            opened_at=item.opened_at,
            reference_date=args.reference_date,
            next_action=item.next_action,
        )
        for item in parsed_waivers
    ]

    _emit_snapshot(records, args.out)

    print(
        json.dumps(
            {
                "status": "ok",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(records),
                "output": args.out.as_posix(),
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
