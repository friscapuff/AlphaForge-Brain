from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from domain.data.ingest_nvda import load_canonical_dataset, slice_canonical

from scripts.data.generate_manifest import build_manifest


def _validate_dataset_manifest(csv_path: Path) -> None:
    manifest_path = csv_path.parent / "dataset_manifest.json"
    assert manifest_path.exists(), (
        "dataset_manifest.json missing for canonical dataset. "
        "Regenerate via 'poetry run python scripts/data/generate_manifest.py --dataset "
        f"{csv_path}'"
    )
    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    computed = build_manifest(csv_path).to_payload()
    for key in ("dataset_name", "path", "sha256", "row_count", "schema_signature"):
        assert (
            recorded.get(key) == computed[key]
        ), f"Dataset manifest mismatch for {key}: expected {computed[key]!r}"
    assert isinstance(
        recorded.get("generated_at"), str
    ), "Manifest missing generated_at timestamp"


@pytest.fixture(scope="session")
def nvda_canonical() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Session-scoped canonical NVDA dataset (loads once). Skips if CSV missing."""
    csv_primary = Path("data") / "NVDA_5y.csv"
    csv_alt = Path("src") / "domain" / "data" / "NVDA_5y.csv"
    use_alt = not csv_primary.exists() and csv_alt.exists()
    csv_path = csv_primary if not use_alt else csv_alt
    assert (
        csv_path.exists()
    ), "Expected NVDA_5y.csv in data/ or src/domain/data/; add dataset before running tests"
    _validate_dataset_manifest(csv_path)
    # If using alternate location, pass its parent as data_dir so loader finds file
    data_dir = csv_path.parent if use_alt else None
    df, meta = load_canonical_dataset(data_dir=data_dir)
    return df, meta


@pytest.fixture(scope="function")
def nvda_canonical_slice(
    nvda_canonical: tuple[pd.DataFrame, dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df, meta = nvda_canonical
    # Take a deterministic middle slice (avoid edges for moving averages)
    assert (
        len(df) >= 120
    ), f"Dataset unexpectedly small (<120 rows); got {len(df)} rows from {Path('data')/'NVDA_5y.csv' if (Path('data')/'NVDA_5y.csv').exists() else (Path('src')/'domain'/'data'/'NVDA_5y.csv')}"
    mid_start = int(df.iloc[len(df) // 3]["ts"])
    mid_end = (
        int(df.iloc[len(df) // 3 + 100]["ts"])
        if len(df) > (len(df) // 3 + 100)
        else int(df.iloc[-1]["ts"])
    )
    sliced = slice_canonical(mid_start, mid_end)
    return sliced, meta
