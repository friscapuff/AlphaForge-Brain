from __future__ import annotations

from datetime import datetime
from importlib import import_module

import pandas as pd
import pytest

from tests.fixtures.validation import validation_fixtures

xfail_execution_realism = pytest.mark.xfail(
    reason="Execution realism report not implemented",
    strict=False,
)

try:  # pragma: no cover - module slated for later phase
    _module = import_module("src.domain.validation.realism.report")
except ImportError as exc:  # pragma: no cover - exercised via xfail
    ExecutionRealismAnalyzer = None  # type: ignore[assignment]
    ExecutionRealismReport = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:  # pragma: no cover - future success path
    ExecutionRealismAnalyzer = getattr(_module, "ExecutionRealismAnalyzer", None)
    ExecutionRealismReport = getattr(_module, "ExecutionRealismReport", None)
    if ExecutionRealismAnalyzer is None or ExecutionRealismReport is None:
        _IMPORT_ERROR = ImportError("Execution realism exports missing")
    else:
        _IMPORT_ERROR = None


@xfail_execution_realism
def test_execution_realism_report_includes_required_guidance_fields() -> None:
    if ExecutionRealismAnalyzer is None:
        pytest.xfail(f"execution realism analyzer unavailable: {_IMPORT_ERROR}")

    fixture = validation_fixtures()
    analyzer = ExecutionRealismAnalyzer(seed=fixture.seeds.realism)

    fills = pd.DataFrame(
        [
            {
                "timestamp": datetime(2024, 2, 1, 9, 30),
                "symbol": "SSE",
                "side": "buy",
                "quantity": 1500,
                "price": 101.25,
                "adv": 1_000_000,
            },
            {
                "timestamp": datetime(2024, 2, 1, 9, 32),
                "symbol": "SSE",
                "side": "sell",
                "quantity": 1800,
                "price": 101.15,
                "adv": 950_000,
            },
        ]
    )

    report = analyzer.evaluate(
        fills=fills,
        run_config=fixture.run_config,
        bars=fixture.bars,
        budget_bps=50,
        capacity_limit=0.75,
    )

    assert isinstance(report, ExecutionRealismReport)
    assert report.status in {"pass", "caution", "fail"}
    assert report.transaction_cost_bps >= 0
    assert report.market_impact_bps >= 0
    assert 0 <= report.capacity_ratio <= 2
    assert isinstance(report.warnings, list)
    assert isinstance(report.guidance, list)
    assert any("capacity" in guidance.lower() for guidance in report.guidance)


@xfail_execution_realism
def test_double_count_avoided_when_strategy_includes_costs() -> None:
    if ExecutionRealismAnalyzer is None:
        pytest.xfail(f"execution realism analyzer unavailable: {_IMPORT_ERROR}")

    fixture = validation_fixtures()
    analyzer = ExecutionRealismAnalyzer(seed=fixture.seeds.realism)

    fills = pd.DataFrame(
        [
            {
                "timestamp": datetime(2024, 2, 1, 10, 5),
                "symbol": "SSE",
                "side": "buy",
                "quantity": 2200,
                "price": 102.05,
                "adv": 750_000,
            }
        ]
    )

    with_costs = analyzer.evaluate(
        fills=fills,
        run_config=fixture.run_config,
        bars=fixture.bars,
        budget_bps=25,
        capacity_limit=0.6,
        strategy_costs_applied=True,
    )

    without_costs = analyzer.evaluate(
        fills=fills,
        run_config=fixture.run_config,
        bars=fixture.bars,
        budget_bps=25,
        capacity_limit=0.6,
        strategy_costs_applied=False,
    )

    assert with_costs.transaction_cost_bps <= without_costs.transaction_cost_bps
    assert with_costs.market_impact_bps <= without_costs.market_impact_bps
    assert "double-count" not in " ".join(with_costs.warnings).lower()
    assert without_costs.capacity_ratio == pytest.approx(
        with_costs.capacity_ratio, rel=1e-3
    )
