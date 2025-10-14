from __future__ import annotations

from datetime import date

import pytest
from services.governance.models import WaiverCadenceRecord, WaiverEscalationStatus

from scripts.ci import waiver_cadence


@pytest.mark.unit
@pytest.mark.parametrize(
    "age_days, expected_status",
    [
        (0, WaiverEscalationStatus.NORMAL),
        (10, WaiverEscalationStatus.NORMAL),
        (45, WaiverEscalationStatus.WARNING),
        (59, WaiverEscalationStatus.WARNING),
        (60, WaiverEscalationStatus.ESCALATED),
        (82, WaiverEscalationStatus.ESCALATED),
    ],
)
def test_classify_escalation_returns_expected_status(
    age_days: int, expected_status: WaiverEscalationStatus
) -> None:
    assert waiver_cadence.classify_escalation(age_days) is expected_status


def test_build_record_populates_age_and_status() -> None:
    opened_at = date(2025, 9, 1)
    reference = date(2025, 10, 16)

    record = waiver_cadence.build_record(
        waiver_id="W-001",
        fr_ids=["FR-211"],
        opened_at=opened_at,
        reference_date=reference,
        next_action="Review with governance board",
    )

    assert isinstance(record, WaiverCadenceRecord)
    assert record.age_days == (reference - opened_at).days
    assert record.escalation_status is WaiverEscalationStatus.WARNING
