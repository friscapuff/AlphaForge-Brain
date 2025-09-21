import pandas as pd

from domain.indicators.sma import SimpleMovingAverage


def test_sma_no_lookahead():
    # Construct deterministic ascending close prices
    ts = pd.date_range("2024-01-01", periods=20, freq="1D")
    close = pd.Series(range(100, 120))
    df = pd.DataFrame({"timestamp": ts, "open": close, "high": close, "low": close, "close": close, "volume": 1})

    sma = SimpleMovingAverage(window=5)
    feats = sma.compute(df)
    col = sma.feature_columns()[0]
    # For each row where SMA is defined, ensure it's the mean of the previous 'window' closes including current
    for idx in range(len(df)):
        if idx < 4:
            assert pd.isna(feats.iloc[idx][col])
        else:
            window_vals = close.iloc[idx-4:idx+1]
            expected = window_vals.mean()
            assert feats.iloc[idx][col] == expected
