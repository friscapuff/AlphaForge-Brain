from __future__ import annotations

import pytest
from services.adapters.trades import legacy_fills_to_fills, legacy_trades_to_completed


class _DummyTrade:
    # Minimal attributes to simulate legacy trade
    def __init__(self):
        import datetime as dt

        self.entry_ts = dt.datetime.utcnow()
        self.exit_ts = self.entry_ts
        self.entry_price = 10.0
        self.exit_price = 10.5
        self.qty = 1.0
        self.pnl = 0.5
        self.return_pct = 0.05
        self.holding_period_bars = 0
        self.symbol = "SYM"


class _DummyFill:
    def __init__(self):
        import datetime as dt

        self.ts = dt.datetime.utcnow()
        self.quantity = 1.0
        self.price = 10.0
        self.order_id = "o1"
        self.run_id = None


@pytest.mark.unit
@pytest.mark.feature008
def test_t017_empty_inputs():
    assert legacy_trades_to_completed([]) == []
    assert legacy_fills_to_fills([]) == []


@pytest.mark.unit
@pytest.mark.feature008
def test_t017_basic_mapping():
    t = _DummyTrade()
    c = legacy_trades_to_completed([t])
    assert len(c) == 1
    ct = c[0]
    # Attribute presence (not strict type assertion due to placeholder Any typing)
    for attr in [
        "entry_ts",
        "exit_ts",
        "entry_price",
        "exit_price",
        "pnl",
        "return_pct",
        "holding_period_secs",
    ]:
        assert hasattr(ct, attr), f"missing {attr}"
    f = _DummyFill()
    fills = legacy_fills_to_fills([f])
    assert len(fills) == 1
    fill = fills[0]
    for attr in ["ts", "price", "size", "order_id"]:
        assert hasattr(fill, attr)
