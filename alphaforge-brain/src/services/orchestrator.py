"""Run orchestrator skeleton (T047).

Coordinates high-level phases. Actual integration with API & persistence will
be added later. Provides event hooks (callbacks) for SSE emission & logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

PhaseCallback = Callable[[str], None]


@dataclass
class RunOrchestrator:
    run_id: str
    on_phase: PhaseCallback | None = None
    phases_executed: list[str] = field(default_factory=list)

    def _emit(self, phase: str) -> None:
        self.phases_executed.append(phase)
        if self.on_phase:
            self.on_phase(phase)

    def execute(self) -> None:
        """Execute deterministic ordered phases.

        Side effects: invokes callback per phase and appends to phases_executed.
        """
        for phase in [
            "INGEST",
            "FEATURES",
            "EXECUTION",
            "COSTS",
            "EQUITY",
            "METRICS",
            "VALIDATION",
            "ROBUSTNESS",
            "MANIFEST",
            "SUMMARY",
            "DONE",
        ]:
            self._emit(phase)


__all__ = ["RunOrchestrator"]
