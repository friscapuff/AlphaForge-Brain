from datetime import datetime, timezone

from models.execution_config import ExecutionConfig, FillPolicy, RoundingMode
from services.execution import PositionState, generate_trades


def _cfg(mode: RoundingMode, lot: int = 10) -> ExecutionConfig:
    return ExecutionConfig(
        fill_policy=FillPolicy.NEXT_BAR_OPEN, lot_size=lot, rounding_mode=mode
    )


def test_generate_trades_floor_rounds_down():
    state = PositionState(symbol="XYZ")
    cfg = _cfg(RoundingMode.FLOOR, lot=10)
    # target 23 -> delta 23 -> floor lots = 2 * 10 = 20
    trades = generate_trades(
        symbol="XYZ",
        target_quantity=23,
        state=state,
        price=100.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    assert len(trades) == 1
    assert trades[0].quantity == 20
    assert state.quantity == 20


def test_generate_trades_ceil_rounds_up():
    state = PositionState(symbol="XYZ")
    cfg = _cfg(RoundingMode.CEIL, lot=10)
    trades = generate_trades(
        symbol="XYZ",
        target_quantity=23,
        state=state,
        price=50.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    # ceil lots = 3 * 10 = 30
    assert trades[0].quantity == 30
    assert state.quantity == 30


def test_generate_trades_round_nearest():
    state = PositionState(symbol="XYZ")
    cfg = _cfg(RoundingMode.ROUND, lot=10)
    trades = generate_trades(
        symbol="XYZ",
        target_quantity=26,
        state=state,
        price=10.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    # 26/10 = 2.6 -> round -> 3 lots -> 30
    assert trades[0].quantity == 30
    # second call with small delta below half lot should produce no trade
    trades2 = generate_trades(
        symbol="XYZ",
        target_quantity=27,
        state=state,
        price=10.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    assert trades2 == []


def test_generate_trades_sell_path_and_zero_delta():
    state = PositionState(symbol="XYZ", quantity=50)
    cfg = _cfg(RoundingMode.FLOOR, lot=10)
    # Move down to 15 -> delta -35 -> floor(3.5)=3 lots -> 30
    trades = generate_trades(
        symbol="XYZ",
        target_quantity=15,
        state=state,
        price=5.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    assert trades[0].side.name == "SELL"
    assert trades[0].quantity == 30
    assert state.quantity == 20
    # Now target 20 -> no trade
    trades2 = generate_trades(
        symbol="XYZ",
        target_quantity=20,
        state=state,
        price=5.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    assert trades2 == []


def test_generate_trades_small_delta_below_one_lot():
    state = PositionState(symbol="XYZ")
    cfg = _cfg(RoundingMode.FLOOR, lot=10)
    trades = generate_trades(
        symbol="XYZ",
        target_quantity=5,
        state=state,
        price=1.0,
        config=cfg,
        ts=datetime.now(timezone.utc),
        strategy_id="s1",
        run_id=None,
    )
    assert trades == []  # floor(0.5 lots)=0 -> ignored
