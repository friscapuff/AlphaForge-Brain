from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

"""Ring buffer stub for SSE Last-Event-ID resume (T052).

Future implementation goals:
- Append events with incremental integer IDs.
- Provide snapshot() returning list of events >= a given last_event_id (bounded length).
- Evict oldest when capacity exceeded.

Determinism considerations:
- Event ordering strictly by monotonically increasing integer id.
- No wall-clock dependent mutation besides timestamp already baked into event payload.
"""


@dataclass
class EventRecord:
    id: int
    type: str
    data: dict[str, Any]


class EventRingBuffer:
    def __init__(self, capacity: int = 512) -> None:
        self.capacity = capacity
        self._events: deque[EventRecord] = deque()
        self._next_id = 0

    def append(self, type_: str, data: dict[str, Any]) -> int:
        rec = EventRecord(self._next_id, type_, data)
        self._events.append(rec)
        self._next_id += 1
        if len(self._events) > self.capacity:
            self._events.popleft()
        return rec.id

    def since(self, last_event_id: int | None) -> list[EventRecord]:
        if last_event_id is None:
            return list(self._events)
        return [e for e in self._events if e.id > last_event_id]


# Global fallback storage (used when orchestrator needs to push events before SSE route instantiates app-level buffer)
GLOBAL_EVENT_BUFFERS: dict[str, EventRingBuffer] = {}


def get_global_buffer(run_hash: str, capacity: int = 512) -> EventRingBuffer:
    buf = GLOBAL_EVENT_BUFFERS.get(run_hash)
    if buf is None:
        buf = EventRingBuffer(capacity=capacity)
        GLOBAL_EVENT_BUFFERS[run_hash] = buf
    return buf


__all__ = [
    "GLOBAL_EVENT_BUFFERS",
    "EventRecord",
    "EventRingBuffer",
    "get_global_buffer",
]
