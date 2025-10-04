import pytest

# Will fail until registries implemented
from domain.indicators.registry import get_indicator_registry, indicator
from domain.risk.base import get_risk_registry, risk_model
from domain.strategy.base import get_strategy_registry, strategy
from domain.validation.registry import get_validation_registry, validation_test


def test_indicator_registry_decorator() -> None:
    def sma(data: object) -> list[int]:
        return [1, 2, 3]

    indicator(name="sma")(sma)

    assert "sma" in get_indicator_registry()


def test_strategy_registry_decorator() -> None:
    @strategy(name="dual_sma")
    class DualSMA:
        def run(
            self, features: object
        ) -> list[object]:  # pragma: no cover - placeholder
            return []

    assert "dual_sma" in get_strategy_registry()


def test_risk_registry_decorator() -> None:
    @risk_model(name="fixed_fraction")
    class FixedFraction:
        def size(
            self, equity: float, signal: float
        ) -> float:  # pragma: no cover - placeholder
            return 1.0

    assert "fixed_fraction" in get_risk_registry()


def test_validation_registry_decorator() -> None:
    def permutation_test(
        state: object,
    ) -> dict[str, float]:  # pragma: no cover - placeholder
        return {"p_value": 0.5}

    validation_test(name="permutation")(permutation_test)

    assert "permutation" in get_validation_registry()


def test_duplicate_registration_raises() -> None:
    def foo(x: int) -> int:
        return x

    indicator(name="dup_test")(foo)

    with pytest.raises(ValueError):

        def foo2(x: int) -> int:
            return x

        indicator(name="dup_test")(foo2)
