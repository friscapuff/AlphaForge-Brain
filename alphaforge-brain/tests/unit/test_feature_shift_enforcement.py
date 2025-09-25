from __future__ import annotations

import pytest
from src.models.feature_spec import FeatureSpec
from src.services.features import build_registry


def test_feature_registry_requires_shift_when_global_shift_enabled() -> None:
    specs = [
        FeatureSpec(
            name="sma_fast",
            version="1.0",
            inputs=["close"],
            params={"window": 5},
            shift_applied=True,
        ),
        FeatureSpec(
            name="sma_slow",
            version="1.0",
            inputs=["close"],
            params={"window": 15},
            shift_applied=True,
        ),
    ]
    reg = build_registry(specs, global_shift=1)
    assert reg.names() == ["sma_fast", "sma_slow"]


def test_feature_registry_raises_when_missing_shift() -> None:
    specs = [
        FeatureSpec(
            name="sma_fast",
            version="1.0",
            inputs=["close"],
            params={"window": 5},
            shift_applied=True,
        ),
        FeatureSpec(
            name="sma_slow",
            version="1.0",
            inputs=["close"],
            params={"window": 15},
            shift_applied=False,
        ),
    ]
    with pytest.raises(ValueError):
        build_registry(specs, global_shift=1)
