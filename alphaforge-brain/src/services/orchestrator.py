"""Run orchestrator skeleton with journaling integration (Phase 016).

Coordinates high-level phases for a run. Inserts a dedicated journaling phase
between ``METRICS`` and ``VALIDATION`` that prepares enriched artifacts and
persists them to ``zz_artifacts/journaling`` while enforcing the <= 3% runtime
budget established during research (Decision 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Callable, Mapping, Sequence

from models.completed_trade import CompletedTrade
from models.trade_context_snapshot import TradeContextSnapshot
from services.journaling.enrichment import prepare_enriched_payload
from services.journaling.writer import (
    JournalingWriteResult,
    write_journaling_artifacts,
)

PhaseCallback = Callable[[str], None]

_JOURNALING_RUNTIME_BUDGET_SECONDS = 1.2  # 3% of 40 second benchmark window


@dataclass
class RunOrchestrator:
    run_id: str
    on_phase: PhaseCallback | None = None
    phases_executed: list[str] = field(default_factory=list)
    journaling_enabled: bool = True
    journaling_base_dir: Path | None = None
    trades: Sequence[CompletedTrade] = field(default_factory=list)
    snapshots: Sequence[TradeContextSnapshot] = field(default_factory=list)
    price_events: Mapping[str, Sequence[float]] | None = None
    journaling_result: JournalingWriteResult | None = field(default=None, init=False)
    journaling_runtime_ms: float | None = field(default=None, init=False)
    journaling_budget_breached: bool = field(default=False, init=False)
    journaling_metadata: dict[Path, dict[str, str]] = field(
        default_factory=dict, init=False
    )

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
            "JOURNALING",
            "VALIDATION",
            "ROBUSTNESS",
            "MANIFEST",
            "SUMMARY",
            "DONE",
        ]:
            if phase == "JOURNALING":
                self._execute_journaling_phase()
            else:
                self._emit(phase)

    def _execute_journaling_phase(self) -> None:
        if not self.journaling_enabled:
            self._emit("JOURNALING")
            return

        if not self.trades:
            self.journaling_result = None
            self.journaling_runtime_ms = 0.0
            self._emit("JOURNALING")
            return

        start = perf_counter()
        artifacts = prepare_enriched_payload(
            self.run_id,
            list(self.trades),
            snapshots=list(self.snapshots),
            price_events=self.price_events,
        )
        result = write_journaling_artifacts(
            self.run_id,
            artifacts,
            base_dir=self.journaling_base_dir,
        )

        elapsed_ms = (perf_counter() - start) * 1000.0
        self.journaling_result = result
        self.journaling_runtime_ms = elapsed_ms
        self.journaling_budget_breached = (
            elapsed_ms > _JOURNALING_RUNTIME_BUDGET_SECONDS * 1000.0
        )

        metadata: dict[Path, dict[str, str]] = {}
        if result.trade_path.exists():
            descriptor: dict[str, str] = {
                "schema_version": artifacts.schema_version,
            }
            if artifacts.signature:
                descriptor["canonical_hash"] = artifacts.signature
            if artifacts.source_artifacts:
                descriptor["source_artifacts"] = ",".join(artifacts.source_artifacts)
            metadata[result.trade_path] = descriptor
        if (
            result.aggregate_path is not None
            and result.aggregate_path.exists()
            and artifacts.aggregate is not None
        ):
            aggregate_descriptor: dict[str, str] = {
                "schema_version": artifacts.aggregate.schema_version,
                "canonical_hash": artifacts.aggregate.artifact_hash,
            }
            if artifacts.source_artifacts:
                aggregate_descriptor["source_artifacts"] = ",".join(
                    artifacts.source_artifacts
                )
            metadata[result.aggregate_path] = aggregate_descriptor
        self.journaling_metadata = metadata

        self._emit("JOURNALING")


__all__ = ["RunOrchestrator"]
