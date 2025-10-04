from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import BaseModelStrict


class DatasetSnapshot(BaseModelStrict):  # FR-001..FR-003
    path: str
    data_hash: str = Field(description="Dataset content SHA-256")
    calendar_id: str
    bar_count: int
    first_ts: datetime
    last_ts: datetime
    gap_count: int
    holiday_gap_count: int
    duplicate_count: int

    def integrity_ok(self) -> bool:
        return self.duplicate_count == 0 and self.bar_count >= 0
