from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from services.governance.models import CapStatus, SweepAcceptanceResult

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _PROJECT_ROOT.parent
_DEFAULT_FIXTURES_DIR = _PROJECT_ROOT / "tests" / "sweeps" / "fixtures"
_DEFAULT_OUTPUT_PATH = (
    _REPO_ROOT / "zz_artifacts" / "governance" / "sweep_acceptance.json"
)


@dataclass(frozen=True)
class FixtureDefinition:
    scenario_id: str
    ticker: str
    input_payload_hash: str
    expected_ordering: list[str]
    observed_ordering: list[str]
    cap_hit: bool
    anomalies: list[str]
    runbook_link: str
    allow_ordering_mismatch: bool = False

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> FixtureDefinition:
        observed = raw.get("observed") or {}
        return cls(
            scenario_id=raw["scenario_id"],
            ticker=raw["ticker"],
            input_payload_hash=raw["input_payload_hash"],
            expected_ordering=list(_coerce_sequence(raw.get("expected_ordering", []))),
            observed_ordering=list(_coerce_sequence(observed.get("ordering", []))),
            cap_hit=bool(observed.get("cap_hit", False)),
            anomalies=list(_coerce_sequence(observed.get("anomalies", []))),
            runbook_link=raw["runbook_link"],
            allow_ordering_mismatch=bool(raw.get("allow_ordering_mismatch", False)),
        )


def _coerce_sequence(values: Any) -> Iterable[str]:
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return (str(item) for item in values)
    return []


def _load_fixture(path: Path) -> FixtureDefinition:
    data = json.loads(path.read_text(encoding="utf-8"))
    return FixtureDefinition.parse(data)


def evaluate_fixture(path: Path) -> SweepAcceptanceResult:
    definition = _load_fixture(path)
    anomalies = set(definition.anomalies)
    if (
        not definition.allow_ordering_mismatch
        and definition.expected_ordering != definition.observed_ordering
    ):
        anomalies.add("ordering_mismatch")

    cap_status = CapStatus.HIT if definition.cap_hit else CapStatus.PASS

    return SweepAcceptanceResult(
        scenario_id=definition.scenario_id,
        ticker=definition.ticker,
        input_payload_hash=definition.input_payload_hash,
        expected_ordering=definition.expected_ordering,
        observed_ordering=definition.observed_ordering,
        cap_status=cap_status,
        anomaly_flags=sorted(anomalies),
        runbook_link=definition.runbook_link,
    )


def run_acceptance_suite(
    *, fixtures_dir: Path | None = None, output_path: Path | None = None
) -> list[SweepAcceptanceResult]:
    fixtures_dir = fixtures_dir or _DEFAULT_FIXTURES_DIR
    output_path = output_path or _DEFAULT_OUTPUT_PATH

    results: list[SweepAcceptanceResult] = []
    if fixtures_dir.exists():
        for fixture_path in sorted(fixtures_dir.glob("*.json")):
            results.append(evaluate_fixture(fixture_path))

    results.sort(key=lambda item: item.scenario_id)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump(mode="json") for item in results]
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    return results
