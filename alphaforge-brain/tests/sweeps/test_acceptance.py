from __future__ import annotations

import json
from pathlib import Path

import pytest
from services.orchestration import sweep_acceptance

FIXTURES_DIR = Path(__file__).with_suffix("").parent / "fixtures"
EXPECTED_DIR = Path(__file__).resolve().parents[1] / "data" / "sweeps" / "expected"


def _load_expected(name: str) -> dict[str, object]:
    path = EXPECTED_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_partial_cap_result_matches_expected() -> None:
    result = sweep_acceptance.evaluate_fixture(FIXTURES_DIR / "partial_cap.json")
    assert result.model_dump(mode="json") == _load_expected("partial_cap.expected.json")


def test_observed_ordering_anomaly_detected() -> None:
    result = sweep_acceptance.evaluate_fixture(FIXTURES_DIR / "anomaly_ordering.json")
    expected = _load_expected("anomaly_ordering.expected.json")
    assert result.anomaly_flags == expected["anomaly_flags"]
    assert "ordering_mismatch" in result.anomaly_flags
    assert result.model_dump(mode="json") == expected


def test_suite_runner_writes_aggregate_payload(tmp_path: Path) -> None:
    aggregate_path = tmp_path / "sweep_acceptance.json"
    results = sweep_acceptance.run_acceptance_suite(
        fixtures_dir=FIXTURES_DIR,
        output_path=aggregate_path,
    )

    expected_payload = sorted(
        (
            _load_expected("partial_cap.expected.json"),
            _load_expected("anomaly_ordering.expected.json"),
            _load_expected("deterministic_order.expected.json"),
        ),
        key=lambda item: item["scenario_id"],
    )

    serialized_results = [item.model_dump(mode="json") for item in results]
    assert serialized_results == expected_payload

    aggregate_payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
    assert aggregate_payload == expected_payload


@pytest.mark.parametrize(
    "fixture_name, expected_anomalies",
    [
        ("deterministic_order.json", []),
        ("partial_cap.json", ["partial_execution"]),
        ("anomaly_ordering.json", ["ordering_mismatch", "unexpected_variance"]),
    ],
)
def test_anomaly_flags_align_with_expected(
    fixture_name: str, expected_anomalies: list[str]
) -> None:
    result = sweep_acceptance.evaluate_fixture(FIXTURES_DIR / fixture_name)
    assert result.anomaly_flags == expected_anomalies
