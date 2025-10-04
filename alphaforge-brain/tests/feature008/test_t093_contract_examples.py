import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.feature008

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contracts"


def _load(name: str):
    with (CONTRACT_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def test_t093_fill_example_keys():
    data = _load("fill.example.json")
    for k in ["ts", "order_id", "size", "price"]:
        assert k in data


def test_t093_completed_trade_example_keys():
    data = _load("completed_trade.example.json")
    expected = {
        "id",
        "symbol",
        "entry_ts",
        "exit_ts",
        "entry_price",
        "exit_price",
        "quantity",
        "pnl",
        "return_pct",
        "holding_period_secs",
    }
    assert expected.issubset(data.keys())


def test_t093_equity_bar_example_drawdown_consistency():
    data = _load("equity_bar.example.json")
    nav = data["nav"]
    peak = data["peak_nav"]
    dd = data["drawdown"]
    expected_dd = (peak - nav) / peak
    assert abs(expected_dd - dd) < 1e-9


def test_t093_run_payload_example_preview():
    data = _load("run_payload.example.json")
    preview = data.get("normalized_equity_preview") or {}
    assert {"rows", "median_nav", "median_value", "scaled", "scale_factor"}.issubset(
        preview.keys()
    )
    assert preview["median_nav"] == preview["median_value"]
    # metrics hash placeholders present
    assert "metrics_hash" in data and "equity_curve_hash" in data
