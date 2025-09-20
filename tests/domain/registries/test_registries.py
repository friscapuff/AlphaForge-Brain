import pytest

# Will fail until registries implemented
from domain.indicators.registry import get_indicator_registry, indicator
from domain.risk.base import get_risk_registry, risk_model
from domain.strategy.base import get_strategy_registry, strategy
from domain.validation.registry import get_validation_registry, validation_test


def test_indicator_registry_decorator():
    @indicator(name="sma")
    def sma(data):
        return [1, 2, 3]

    assert "sma" in get_indicator_registry()


def test_strategy_registry_decorator():
    @strategy(name="dual_sma")
    class DualSMA:
        def run(self, features):  # pragma: no cover - placeholder
            return []

    assert "dual_sma" in get_strategy_registry()


def test_risk_registry_decorator():
    @risk_model(name="fixed_fraction")
    class FixedFraction:
        def size(self, equity, signal):  # pragma: no cover - placeholder
            return 1.0

    assert "fixed_fraction" in get_risk_registry()


def test_validation_registry_decorator():
    @validation_test(name="permutation")
    def permutation_test(state):  # pragma: no cover - placeholder
        return {"p_value": 0.5}

    assert "permutation" in get_validation_registry()


def test_duplicate_registration_raises():
    @indicator(name="dup_test")
    def foo(x):
        return x

    with pytest.raises(ValueError):
        @indicator(name="dup_test")
        def foo2(x):
            return x
