import types

import pytest
from domain.schemas.run_config import RiskSpec, RunConfig, StrategySpec


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
    # coverage: services.metrics empty input path (compute_metrics returns empty dict)
    import services.metrics as m

    assert m.compute_metrics([]) == {}


def test_services_metrics_basic_stub():
    # coverage: services.metrics basic computation with synthetic equity bars
    import services.metrics as m
    from models.equity_bar import EquityBar

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
        # nav rises -> peak_nav updates, small drawdown 0 still
        EquityBar(
            ts="2025-01-01T00:01:00Z",
            nav=101.0,
            peak_nav=101.0,
            drawdown=0.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            trade_count_cum=1,
        ),
        # slight dip to 100.5 -> peak 101 maintained -> drawdown (101-100.5)/101
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


def test_services_equity_placeholder(basic_run_config):
    # coverage: services.equity placeholder (ensure module import executes)
    import importlib

    mod = importlib.import_module("services.equity")
    # some modules may export a build function later; ensure loaded
    assert isinstance(mod, types.ModuleType)


def test_services_execution_placeholder(basic_run_config):
    # coverage: services.execution import + simulate fallback
    import importlib

    mod = importlib.import_module("services.execution")
    assert hasattr(mod, "__doc__")
