"""T030: validation.json should include anomaly counters (alignment test)

We emulate a validation summary build path and assert anomaly counters surface
inside the `summary` section of validation.json written by the artifact writer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from domain.artifacts.writer import write_artifacts


def test_validation_json_contains_anomaly_counters(
    tmp_path: Path, monkeypatch: Any
) -> None:
    class DummyMeta:  # pragma: no cover - simple structure
        data_hash: str = "abc"
        calendar_id: str = "NASDAQ"
        anomaly_counters: ClassVar[dict[str, int]] = {
            "duplicates_dropped": 2,
            "unexpected_gaps": 1,
        }

    def fake_get_dataset_metadata() -> Any:  # minimal stub
        return DummyMeta()

    import domain.artifacts.writer as w

    monkeypatch.setattr(w, "get_dataset_metadata", fake_get_dataset_metadata)

    record = {
        "summary": {"metrics": {"total_return": 0.05}},
        # Force writer to construct validation_summary via build (patched meta used)
    }
    run_hash = "dummy_run_hash"
    manifest = write_artifacts(run_hash, record, tmp_path)
    vpath = tmp_path / run_hash / "validation.json"
    assert vpath.exists(), "validation.json not written"
    content = json.loads(vpath.read_text("utf-8"))
    assert "summary" in content, "validation.json missing summary section"
    summary = content["summary"]
    assert (
        "anomaly_counters" in summary
    ), "anomaly_counters missing from validation summary"
    assert summary["anomaly_counters"]["unexpected_gaps"] == 1
    # Manifest should still include data_hash/calendar_id pass-through
    assert manifest.get("data_hash") == "abc"
