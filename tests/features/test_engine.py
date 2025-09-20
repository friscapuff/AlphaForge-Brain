from datetime import datetime, timezone

import pandas as pd
import pytest

# We expect an indicator registry already exists similar to strategies/indicators used earlier.
# Import the registry and a sample indicator (SMA) used in earlier tasks.
from domain.indicators.registry import indicator_registry  # type: ignore
from domain.indicators.sma import SimpleMovingAverage  # type: ignore

# The engine (to be implemented) will live at domain/features/engine.py
# and expose a function build_features(df: pd.DataFrame) -> pd.DataFrame
# plus maybe a class FeatureEngine for future extension. For now we just test the functional contract.

@pytest.fixture(scope="module")
def candles_df():
    data = {
        "timestamp": [
            datetime(2024,1,1,0,0,tzinfo=timezone.utc),
            datetime(2024,1,1,0,1,tzinfo=timezone.utc),
            datetime(2024,1,1,0,2,tzinfo=timezone.utc),
            datetime(2024,1,1,0,3,tzinfo=timezone.utc),
            datetime(2024,1,1,0,4,tzinfo=timezone.utc),
        ],
        "open": [100,101,102,103,104],
        "high": [101,102,103,104,105],
        "low":  [ 99,100,101,102,103],
        "close":[100.5,101.5,102.5,103.5,104.5],
        "volume":[10,11,12,13,14],
    }
    return pd.DataFrame(data)


def test_engine_applies_registered_indicators(candles_df):
    # Ensure SMA indicator is registered. (If registry already populated, re-register is idempotent/no-op.)
    indicator_registry.register(SimpleMovingAverage(window=3))  # type: ignore

    from domain.features import engine  # import deferred until after fixture/registration

    out = engine.build_features(candles_df.copy())

    # Original columns must remain
    for col in ["timestamp","open","high","low","close","volume"]:
        assert col in out.columns

    # SMA should have produced a column. Convention assumption: f"SMA_{window}_close"
    assert any(c.startswith("SMA_3_close") for c in out.columns), "Expected SMA feature column present"

    # Shape: same number of rows
    assert len(out) == len(candles_df)


def test_engine_duplicate_feature_collision_raises(candles_df):
    # Register two indicators that intentionally collide in feature naming.
    # We'll simulate by creating two SMA objects with same window but we will monkeypatch their feature_name method
    class SMAAlias(SimpleMovingAverage):  # type: ignore
        def feature_columns(self):  # type: ignore
            # Force same column name as original SMA
            return [f"SMA_{self.window}_close"]

    indicator_registry.register(SimpleMovingAverage(window=2))  # ensure base
    indicator_registry.register(SMAAlias(window=2))  # collision

    from domain.features import engine

    with pytest.raises(ValueError):
        engine.build_features(candles_df.copy())


def test_engine_deterministic_column_order(candles_df):
    # Ensure registry does not contain prior collision artifacts
    indicator_registry.clear()  # type: ignore
    indicator_registry.register(SimpleMovingAverage(window=3))  # type: ignore
    from domain.features import engine

    out1 = engine.build_features(candles_df.copy())
    out2 = engine.build_features(candles_df.copy())

    assert list(out1.columns) == list(out2.columns), "Column order must be deterministic"


def test_engine_idempotent_same_input_same_output(candles_df):
    indicator_registry.clear()  # type: ignore
    indicator_registry.register(SimpleMovingAverage(window=4))  # type: ignore
    from domain.features import engine

    df_in = candles_df.copy()
    out1 = engine.build_features(df_in)
    out2 = engine.build_features(df_in)

    # Deep equality: values identical including NaNs alignment (use pandas testing helper)
    pd.testing.assert_frame_equal(out1, out2)
