from __future__ import annotations

import pandas as pd
import pytest
from services.hashes import equity_signature, metrics_signature
from services.metrics_hash import equity_curve_hash, metrics_hash


@pytest.mark.unit
@pytest.mark.feature008
def test_t023_metrics_signature_parity():
    metrics = {
        "sharpe": 1.234567891234,
        "trade_count": 42,
        "max_drawdown": 0.1029384756,
    }
    legacy = metrics_hash(metrics)
    new = metrics_signature(metrics)
    assert legacy == new, "metrics_signature drifted from legacy metrics_hash"


@pytest.mark.unit
@pytest.mark.feature008
def test_t023_equity_signature_parity_dataframe():
    df = pd.DataFrame(
        {"nav": [10000.0, 10010.5, 9999.2], "drawdown": [0.0, 0.0, 0.001123]}
    )
    legacy = equity_curve_hash(df)
    new = equity_signature(df)
    assert legacy == new, "equity_signature drifted for DataFrame input"


@pytest.mark.unit
@pytest.mark.feature008
def test_t023_equity_signature_parity_sequence():
    sequence = [
        {"nav": 10000.0, "drawdown": 0.0},
        {"nav": 10005.0, "drawdown": 0.0},
        {"nav": 9995.0, "drawdown": 0.0005},
    ]
    legacy = equity_curve_hash(sequence)
    new = equity_signature(sequence)
    assert legacy == new, "equity_signature drifted for sequence input"
