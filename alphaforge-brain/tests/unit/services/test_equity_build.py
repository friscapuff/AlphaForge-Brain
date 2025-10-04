from datetime import datetime, timedelta, timezone

from models.trade import Trade, TradeSide
from services.equity import build_equity


def _trade(ts_offset_min: int, side: TradeSide, qty: float, price: float) -> Trade:
    ts = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(
        minutes=ts_offset_min
    )
    return Trade(
        ts=ts,
        symbol="XYZ",
        side=side,
        quantity=qty,
        price=price,
        strategy_id="s1",
        run_id=None,
    )


def test_build_equity_empty():
    assert build_equity([]) == []


def test_build_equity_increasing_then_drawdown():
    trades = [
        _trade(0, TradeSide.BUY, 10, 100.0),  # nav increases a bit via scaled cash flow
        _trade(1, TradeSide.BUY, 5, 101.0),
        _trade(2, TradeSide.SELL, 8, 99.0),  # potential nav dip due to negative flow
        _trade(3, TradeSide.BUY, 2, 102.0),
    ]
    bars = build_equity(trades)
    assert len(bars) == 4
    # Peak nav monotonic non-decreasing
    peaks = [b.peak_nav for b in bars]
    assert peaks == sorted(peaks)
    # Drawdown consistent with nav/peak
    for b in bars:
        expected_dd = (b.peak_nav - b.nav) / b.peak_nav if b.peak_nav > 0 else 0.0
        assert abs(expected_dd - b.drawdown) < 1e-9
    # trade_count_cum increments sequentially
    assert [b.trade_count_cum for b in bars] == [1, 2, 3, 4]


def test_build_equity_ordering_sorted_by_ts():
    # Provide trades out of chronological order -> build_equity sorts them
    t1 = _trade(2, TradeSide.BUY, 1, 100.0)
    t2 = _trade(0, TradeSide.BUY, 1, 100.0)
    t3 = _trade(1, TradeSide.BUY, 1, 100.0)
    bars = build_equity([t1, t2, t3])
    ts_list = [b.ts for b in bars]
    assert ts_list == sorted(ts_list)
