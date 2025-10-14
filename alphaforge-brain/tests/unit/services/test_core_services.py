from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from models.equity_bar import EquityBar
from models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from services.equity import build_equity
from services.execution import PositionState, generate_trades
from services.metrics import compute_metrics


@dataclass
class _Trade:
    ts: datetime
    price: float
    quantity: float
    symbol: str
    side: object | None = None


class _SideEnum:
    """Minimal shim mimicking Enum interface used inside _is_buy."""

    def __init__(self, name: str | None = None, value: str | None = None) -> None:
        self.name = name
        self.value = value


def _equity_bar(ts: datetime, nav: float, peak: float, drawdown: float) -> EquityBar:
    return EquityBar(
        ts=ts,
        nav=nav,
        peak_nav=peak,
        drawdown=drawdown,
        gross_exposure=abs(peak - nav) * 10,
        net_exposure=(nav - peak) * 5,
        trade_count_cum=1,
    )


def test_build_equity_sorts_and_accumulates_trades() -> None:
    first = _Trade(
        ts=datetime(2024, 1, 1, 9, tzinfo=timezone.utc),
        price=100.0,
        quantity=1.0,
        symbol="XYZ",
        side="BUY",
    )
    second = _Trade(
        ts=datetime(2024, 1, 1, 9, 1, tzinfo=timezone.utc),
        price=102.0,
        quantity=-0.5,
        symbol="XYZ",
        side=_SideEnum(name="SELL"),
    )
    third = _Trade(
        ts=datetime(2024, 1, 1, 9, 2, tzinfo=timezone.utc),
        price=99.0,
        quantity=0.75,
        symbol="ABC",
        side=None,
    )

    bars = build_equity([third, second, first])  # intentionally unsorted
    assert [b.ts for b in bars] == sorted(b.ts for b in bars)
    assert bars[0].trade_count_cum == 1
    assert bars[-1].trade_count_cum == 3
    # Ensure nav updated in both directions and never non-positive
    assert all(bar.nav > 0 for bar in bars)
    # Drawdown values remain within [0, 1)
    assert all(0.0 <= bar.drawdown < 1.0 for bar in bars)


def test_generate_trades_respects_rounding_modes() -> None:
    cfg = ExecutionConfig(
        fill_policy=FillPolicy.NEXT_BAR_OPEN,
        lot_size=10,
        rounding_mode=RoundingMode.ROUND,
    )
    state = PositionState(symbol="XYZ")

    trades = generate_trades(
        symbol="XYZ",
        target_quantity=25,
        state=state,
        price=101.5,
        config=cfg,
        ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        strategy_id="strat",
        run_id="run",
    )
    assert len(trades) == 1
    trade = trades[0]
    assert trade.quantity == pytest.approx(20)  # rounded to nearest lot
    assert state.quantity == pytest.approx(20)

    # Second call with minimal delta should yield no trades
    trades_again = generate_trades(
        symbol="XYZ",
        target_quantity=20.000000000001,
        state=state,
        price=101.5,
        config=cfg,
        ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        strategy_id="strat",
        run_id="run",
    )
    assert trades_again == []


def test_compute_metrics_handles_empty_and_series() -> None:
    assert compute_metrics([]) == {}

    bars = [
        _equity_bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 1.0, 1.0, 0.0),
        _equity_bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 1.05, 1.05, 0.0),
        _equity_bar(
            datetime(2024, 1, 3, tzinfo=timezone.utc), 1.02, 1.05, (1.05 - 1.02) / 1.05
        ),
    ]
    metrics = compute_metrics(bars)
    assert set(metrics) == {
        "total_return",
        "avg_return",
        "volatility",
        "sharpe",
        "max_drawdown",
    }
    assert metrics["total_return"] == pytest.approx(bars[-1].nav / bars[0].nav - 1)
    assert metrics["max_drawdown"] == pytest.approx(bars[2].drawdown)
