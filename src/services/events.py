"""SSE event emitter (T048).

Provides generator yielding heartbeat and phase events. Timing is abstracted;
heartbeat_interval_sec acts as metadata (caller controls actual sleep for tests determinism).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from typing import Any


def event_stream(phases: Iterable[str], heartbeat_interval_sec: int = 15) -> Iterator[dict[str, Any]]:
    """Yield a deterministic sequence of heartbeat, phase, and terminal events.

    Caller is responsible for sleeping between heartbeats if used in real time; this
    function itself is pure and side-effect free beyond datetime acquisition.
    """
    yield {"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat(), "interval": heartbeat_interval_sec}
    for p in phases:
        yield {"type": "phase", "phase": p, "ts": datetime.now(timezone.utc).isoformat()}
    yield {"type": "terminal", "ts": datetime.now(timezone.utc).isoformat()}

__all__ = ["event_stream"]
