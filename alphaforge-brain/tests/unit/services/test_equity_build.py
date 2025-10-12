from datetime import datetime, timedelta, timezone
from enum import Enum
from types import SimpleNamespace

import pytest
from services.equity import _is_buy, build_equity


def _trade(ts_offset_min: int, side: str, qty: float, price: float):
    ts = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(
        minutes=ts_offset_min
    )
    return SimpleNamespace(
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
        _trade(0, "BUY", 10, 100.0),  # nav increases a bit via scaled cash flow
        _trade(1, "BUY", 5, 101.0),
        _trade(2, "SELL", 8, 99.0),  # potential nav dip due to negative flow
        _trade(3, "BUY", 2, 102.0),
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
    t1 = _trade(2, "BUY", 1, 100.0)
    t2 = _trade(0, "BUY", 1, 100.0)
    t3 = _trade(1, "BUY", 1, 100.0)
    bars = build_equity([t1, t2, t3])
    ts_list = [b.ts for b in bars]
    assert ts_list == sorted(ts_list)


class _FakeSide(Enum):
    BUY = "buy"
    SELL = "sell"


def test_build_equity_enum_side_and_size_fallback_handles_nav_floor():
    ts_base = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    huge_buy = SimpleNamespace(
        ts=ts_base,
        symbol="XYZ",
        side=_FakeSide.BUY,
        quantity=None,
        size=1_200_000,
        price=1_000_000.0,
        strategy_id="s1",
        run_id=None,
    )
    sell_without_side = SimpleNamespace(
        ts=ts_base + timedelta(minutes=1),
        symbol="XYZ",
        side=None,
        quantity=-2_500_000,
        price=2.0,
        strategy_id="s1",
        run_id=None,
    )
    buy_from_qty_sign = SimpleNamespace(
        ts=ts_base + timedelta(minutes=2),
        symbol="XYZ",
        side=None,
        quantity=2000,
        price=2.0,
        strategy_id="s1",
        run_id=None,
    )

    bars = build_equity([sell_without_side, huge_buy, buy_from_qty_sign])
    # Sorted order ensures huge buy executes first -> nav forced to floor value
    assert bars[0].nav == pytest.approx(1e-9)
    # Peak should remain at the initial nav even after clamp
    assert bars[0].peak_nav == pytest.approx(1.0)
    # Enum side resolved via .name attribute and size fallback populates exposures
    assert bars[0].gross_exposure > 0
    # Quantity sign fallback handles sell -> position reduced
    assert bars[1].net_exposure < 0
    # Positive quantity with side None treated as buy and reduces short exposure magnitude
    assert bars[2].net_exposure > bars[1].net_exposure
    assert bars[2].trade_count_cum == 3


def test_is_buy_handles_non_numeric_quantity():
    class Uncooperative:
        def __float__(self):
            raise ValueError("boom")

    assert _is_buy(None, Uncooperative()) is False


def test_is_buy_none_side_and_qty_defaults_to_false():
    assert _is_buy(None, None) is False


def test_is_buy_enum_value_sell_false():
    class Side(Enum):
        BUY = "BUY"
        SELL = "SELL"

    assert _is_buy(Side.SELL, None) is False


def test_is_buy_string_side_case_insensitive():
    assert _is_buy("buy", None) is True
    assert _is_buy("sell", None) is False
