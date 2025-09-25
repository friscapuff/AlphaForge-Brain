import math

import pytest
from src.models.cost_model_config import CostModelConfig
from src.models.trade import TradeSide
from src.services.costs import CostBreakdown, apply_costs
from tests.factories import trade


def test_cost_application_order_and_components():
    trades = [
        trade(price=100.0, qty=10, side=TradeSide.BUY),
        trade(price=100.0, qty=5, side=TradeSide.SELL),
    ]
    cfg = CostModelConfig(
        slippage_bps=25,  # 0.25%
        spread_pct=0.002,  # 0.2% total spread (0.1 each side)
        participation_rate=None,
        fee_bps=10,  # 0.10%
        borrow_cost_bps=50,  # 0.50% on sells only
    )
    adjusted, breakdown = apply_costs(trades, cfg)
    assert len(adjusted) == 2

    # Slippage: 0.25% * notional per trade
    expected_slip_buy = 100.0 * 0.0025 * 10
    expected_slip_sell = 100.0 * 0.0025 * 5
    assert math.isclose(
        breakdown.slippage, expected_slip_buy + expected_slip_sell, rel_tol=1e-9
    )

    # Spread: half-spread 0.001 applied once per trade to original price * qty
    expected_spread = 100.0 * 0.001 * 10 + 100.0 * 0.001 * 5
    assert math.isclose(breakdown.spread, expected_spread, rel_tol=1e-9)

    # Fees always positive
    expected_fees = 100.0 * 0.001 * 10 + 100.0 * 0.001 * 5  # 10 bps
    assert math.isclose(breakdown.fees, expected_fees, rel_tol=1e-9)

    # Borrow only on SELL quantity
    expected_borrow = 100.0 * 0.005 * 5
    assert math.isclose(breakdown.borrow, expected_borrow, rel_tol=1e-9)

    assert math.isclose(
        breakdown.total(),
        breakdown.slippage + breakdown.spread + breakdown.fees + breakdown.borrow,
    )


def test_costs_participation_mutual_exclusion():
    trades = [trade(price=50.0, qty=20, side=TradeSide.BUY)]
    cfg = CostModelConfig(
        slippage_bps=0,
        spread_pct=None,
        participation_rate=5.0,  # 5%
        fee_bps=0,
        borrow_cost_bps=0,
    )
    _, breakdown = apply_costs(trades, cfg)
    # Participation treated like spread component accumulation
    expected = 50.0 * 0.05 * 20
    assert math.isclose(breakdown.spread, expected, rel_tol=1e-9)


def test_zero_cost_config_no_effect():
    trades = [trade(price=10.0, qty=1, side=TradeSide.BUY)]
    cfg = CostModelConfig(
        slippage_bps=0,
        spread_pct=None,
        participation_rate=None,
        fee_bps=0,
        borrow_cost_bps=0,
    )
    _, breakdown = apply_costs(trades, cfg)
    assert breakdown == CostBreakdown()


@pytest.mark.parametrize(
    "use_spread,spread_pct,participation",
    [
        (True, 0.004, None),  # 0.4% total spread
        (False, None, 3.0),  # 3% participation impact
    ],
)
def test_parametrized_spread_vs_participation(
    use_spread: bool, spread_pct: float | None, participation: float | None
):
    trades = [trade(price=20.0, qty=10, side=TradeSide.BUY)]
    cfg = CostModelConfig(
        slippage_bps=0,
        spread_pct=spread_pct,
        participation_rate=participation,
        fee_bps=0,
        borrow_cost_bps=0,
    )
    _, breakdown = apply_costs(trades, cfg)
    if use_spread:
        assert breakdown.spread > 0 and math.isclose(
            breakdown.spread, 20.0 * (spread_pct / 2) * 10, rel_tol=1e-9
        )
    else:
        assert breakdown.spread > 0 and math.isclose(
            breakdown.spread, 20.0 * (participation / 100.0) * 10, rel_tol=1e-9
        )
