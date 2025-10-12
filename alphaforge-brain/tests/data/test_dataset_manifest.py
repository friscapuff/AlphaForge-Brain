from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.data.generate_manifest import DEFAULT_DATASET, build_manifest
from scripts.data.generate_manifest import main as generate_main


def test_build_manifest_produces_expected_fields() -> None:
    manifest = build_manifest(DEFAULT_DATASET)
    payload = manifest.to_payload()

    assert payload["dataset_name"] == "NVDA_5y"
    assert payload["path"] == "alphaforge-brain/Data/NVDA_5y.csv"
    assert payload["row_count"] == 1256
    assert (
        payload["sha256"]
        == "18bdaad43a07c2898ed7db591e9eefe68caafbb49d669e1269af265431f31bc9"
    )
    signature = payload["schema_signature"]
    assert isinstance(signature, list) and signature
    names = [entry["name"] for entry in signature]
    assert names == ["Date", "Close/Last", "Volume", "Open", "High", "Low"]
    dtype_map = {entry["name"]: entry["dtype"] for entry in signature}
    assert dtype_map["Volume"] == "integer"
    for name in ("Date", "Close/Last", "Open", "High", "Low"):
        assert dtype_map[name] == "string"
    assert all(entry["nullable"] is False for entry in signature)


def test_cli_writes_manifest_file(tmp_path: Path) -> None:
    output_path = tmp_path / "dataset_manifest.json"
    exit_code = generate_main([str(DEFAULT_DATASET), "--output", str(output_path)])
    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["dataset_name"] == "NVDA_5y"
    assert payload["row_count"] == 1256
    assert (
        payload["sha256"]
        == "18bdaad43a07c2898ed7db591e9eefe68caafbb49d669e1269af265431f31bc9"
    )
    assert "generated_at" in payload


def test_cli_requires_output_when_multiple_datasets(tmp_path: Path) -> None:
    second = tmp_path / "second.csv"
    second.write_text("col\n1\n2\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        generate_main([str(DEFAULT_DATASET), str(second)])
