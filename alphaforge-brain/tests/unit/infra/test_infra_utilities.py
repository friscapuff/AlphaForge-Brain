from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from infra.cold_storage import cold_storage_enabled, offload, restore
from infra.time.timestamps import to_epoch_ms
from infra.utils.hash import (
    canonical_json,
    hash_canonical,
    row_digest,
    sha256_hex,
    sha256_of_text,
)


def test_to_epoch_ms_handles_naive_tz_and_clip_future() -> None:
    series = pd.Series(
        [
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            pd.NaT,
        ],
        name="ts",
    )
    result = to_epoch_ms(series, assume_tz="America/New_York")
    expected_first = pd.Timestamp("2024-01-01 17:00:00+00:00").value // 1_000_000
    expected_second = pd.Timestamp("2024-01-01 12:00:00+00:00").value // 1_000_000
    assert result.iloc[0] == expected_first
    assert result.iloc[1] == expected_second
    assert result.iloc[2] is pd.NA

    future_dates = pd.Series(
        [
            datetime(2000, 1, 1, tzinfo=timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=1),
        ]
    )
    clipped = to_epoch_ms(future_dates, clip_future=True)
    assert clipped.index.size == 1
    assert (
        clipped.iloc[0] == pd.Timestamp("2000-01-01T00:00:00+00:00").value // 1_000_000
    )


def test_hash_helpers_produce_canonical_output() -> None:
    payload = {
        "b": 2,
        "a": 1.234567890123456,
        "when": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    json_str = canonical_json(payload)
    assert json.loads(json_str) == json.loads(json_str)  # valid JSON round-trip
    assert json_str.startswith('{"a":1.23456789012')  # sorted keys + rounded float

    digest = hash_canonical(payload)
    assert digest == sha256_hex(canonical_json(payload).encode("utf-8"))
    assert sha256_of_text("alpha") == sha256_hex(b"alpha")

    row = {"foo": 10, "bar": "baz"}
    assert row_digest(row) == hash_canonical(row)


@pytest.mark.parametrize("provider", [None, "local"])
def test_cold_storage_offload_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str | None
) -> None:
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path))
    if provider is None:
        monkeypatch.delenv("AF_COLD_STORAGE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
        monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", provider)

    run_hash = "RUNTEST"
    run_dir = tmp_path / run_hash
    run_dir.mkdir()
    artifact = run_dir / "sample.txt"
    artifact.write_text("payload", encoding="utf-8")
    manifest_json = run_dir / "manifest.json"
    manifest_json.write_text("{}", encoding="utf-8")

    offload(run_hash, [artifact, manifest_json])

    if provider is None:
        assert not (run_dir / "cold_manifest.json").exists()
        assert artifact.exists()
        return

    manifest = run_dir / "cold_manifest.json"
    assert manifest.exists()
    manifest_payload = json.loads(manifest.read_text("utf-8"))
    assert manifest_payload["run_hash"] == run_hash
    assert manifest_payload["count"] == 2

    # Artifact should be removed after offload (manifest retained)
    assert not artifact.exists()
    assert manifest_json.exists()

    restored = restore(run_hash)
    assert restored is True
    assert artifact.exists()

    updated_manifest = json.loads(manifest.read_text("utf-8"))
    assert "restored_at" in updated_manifest


def test_cold_storage_enabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AF_COLD_STORAGE_ENABLED", raising=False)
    assert cold_storage_enabled() is False
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    assert cold_storage_enabled() is True
