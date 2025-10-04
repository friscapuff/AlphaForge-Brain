from pathlib import Path

import pandas as pd
import pytest
from domain.data.adjustments import AdjustmentFactors
from domain.data.ingest_nvda import load_canonical_dataset


def test_full_adjusted_requires_factors(tmp_path: Path):
    # Point to real data directory; test only the error path without factors
    data_dir = Path("data")
    if not (data_dir / "NVDA_5y.csv").exists():
        pytest.skip("NVDA dataset not present")
    with pytest.raises(ValueError):
        load_canonical_dataset(data_dir=data_dir, adjustment_policy="full_adjusted", adjustment_factors=None)  # type: ignore[arg-type]


def test_dataset_hash_incorporates_policy_and_factors(tmp_path: Path):
    data_dir = Path("data")
    if not (data_dir / "NVDA_5y.csv").exists():
        pytest.skip("NVDA dataset not present")
    # Load baseline (no adjustments)
    df0, meta0 = load_canonical_dataset(data_dir=data_dir)
    # Create a fabricated split event that does not align to any ts to avoid changing numerical data while testing hash behavior
    events = pd.DataFrame({"ts": [0], "split": [2.0]})
    factors = AdjustmentFactors(events=events, coverage_full=True)
    df1, meta1 = load_canonical_dataset(
        data_dir=data_dir, adjustment_policy="full_adjusted", adjustment_factors=factors
    )
    # Hashes must differ due to policy incorporation even if numerical data unchanged (event ts=0 outside range)
    assert meta0.data_hash != meta1.data_hash
    # Re-ingest with same factors yields identical hash (idempotent)
    _, meta2 = load_canonical_dataset(
        data_dir=data_dir, adjustment_policy="full_adjusted", adjustment_factors=factors
    )
    assert meta1.data_hash == meta2.data_hash
