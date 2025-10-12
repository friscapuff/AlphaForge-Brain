import types

import pytest
from domain.schemas.run_config import RiskSpec, RunConfig, StrategySpec
from models.equity_bar import EquityBar


@pytest.fixture
def basic_run_config():
    return RunConfig(
        strategy=StrategySpec(name="dual_sma", params={"fast": 5, "slow": 10}),
        risk=RiskSpec(model="none", params={}),
        symbol="NVDA",
        timeframe="1m",
        start="2025-01-01",
        end="2025-01-01",
    )


def _fake_trades(n=0):
    return [
        {
            "timestamp": f"2025-01-01T00:0{i}:00Z",
            "qty": 1,
            "price": 100 + i,
            "side": "BUY" if i % 2 == 0 else "SELL",
        }
        for i in range(n)
    ]


def test_services_metrics_zero_bars():
    import services.metrics as m

    assert m.compute_metrics([]) == {}


def test_services_metrics_basic_stub():
    import services.metrics as m

    bars = [
        EquityBar(
            ts="2025-01-01T00:00:00Z",
            nav=100.0,
            peak_nav=100.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=0,
        ),
        EquityBar(
            ts="2025-01-01T00:01:00Z",
            nav=101.0,
            peak_nav=101.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=1,
        ),
        EquityBar(
            ts="2025-01-01T00:02:00Z",
            nav=100.5,
            peak_nav=101.0,
            drawdown=(101.0 - 100.5) / 101.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=2,
        ),
    ]
    res = m.compute_metrics(bars)
    assert res["total_return"] > 0
    assert "sharpe" in res


def test_services_metrics_single_bar_returns_total_only():
    import services.metrics as m

    bar = EquityBar(
        ts="2025-01-01T00:00:00Z",
        nav=150.0,
        peak_nav=150.0,
        drawdown=0.0,
        gross_exposure=0.0,
        net_exposure=0.0,
        trade_count_cum=0,
    )
    res = m.compute_metrics([bar])
    assert res == {"total_return": 0.0}


def test_services_metrics_zero_volatility_has_zero_sharpe():
    import services.metrics as m

    bars = [
        EquityBar(
            ts="2025-01-01T00:00:00Z",
            nav=100.0,
            peak_nav=100.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=0,
        ),
        EquityBar(
            ts="2025-01-01T00:01:00Z",
            nav=100.0,
            peak_nav=100.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=1,
        ),
        EquityBar(
            ts="2025-01-01T00:02:00Z",
            nav=100.0,
            peak_nav=100.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=2,
        ),
        EquityBar(
            ts="2025-01-01T00:03:00Z",
            nav=100.0,
            peak_nav=100.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=3,
        ),
    ]

    res = m.compute_metrics(bars)
    assert res["max_drawdown"] == 0.0
    assert res["volatility"] == 0.0
    assert res["sharpe"] == 0.0


def test_services_equity_placeholder(basic_run_config):
    import importlib

    mod = importlib.import_module("services.equity")
    assert isinstance(mod, types.ModuleType)


def test_services_execution_placeholder(basic_run_config):
    import importlib

    mod = importlib.import_module("services.execution")
    assert hasattr(mod, "__doc__")
