from __future__ import annotations

import time
from datetime import datetime, timezone

__all__ = ["utc_ms", "to_utc_ms"]


def utc_ms() -> int:
    """Current UTC time in epoch milliseconds."""
    return int(time.time() * 1000)


def to_utc_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)
