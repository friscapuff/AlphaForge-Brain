import os

import pytest
from domain.schemas.run_config import (
    ExecutionSpec,
    RiskSpec,
    RunConfig,
    StrategySpec,
    ValidationSpec,
)

pytestmark = pytest.mark.feature008

# T042 Backend Payload Update Tests (validation_caution fields)
# T086 Disabled Scenario (threshold unset or no p-values)
#
# Scenarios:
# 1. Disabled by default (no env) -> flag False, metrics [] even if p-values present.
# 2. Threshold set; permutation p-value below threshold triggers caution; others above ignored.
# 3. Threshold + metric filter restricting to 'permutation' (ensure filter respected, ignoring block_bootstrap low p-value if filter excludes it).
# 4. Disabled when no p-values provided even with threshold (empty mapping) -> False.
# 5. Metric filter present but none qualifying -> False.
#
# We reuse RunConfig with short date range to keep runtime minimal. Validation p-values are
# injected by monkeypatching the validation structure returned by orchestrator pipeline via
# patching domain.run.create._run (simpler: monkeypatch create_or_get validation output by
# intercepting validation service used downstream). To avoid deep plumbing, we patch
# domain.run.create.run_validation to return synthetic validation dict.


def _cfg():
    return RunConfig(
        indicators=[],
        strategy=StrategySpec(name="buy_hold", params={}),
        risk=RiskSpec(model="none", params={}),
        execution=ExecutionSpec(),
        validation=ValidationSpec(),
        symbol="NVDA",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-05",
        seed=17,
    )


def _clear_env():
    for k in [
        "AF_VALIDATION_CAUTION_PVALUE",
        "AF_VALIDATION_CAUTION_METRICS",
    ]:
        if k in os.environ:
            del os.environ[k]
    from settings import validation_caution as _vc

    _vc.load_caution_settings.cache_clear()  # type: ignore


def _refresh_settings():
    from settings import validation_caution as _vc

    _vc.load_caution_settings.cache_clear()  # type: ignore
    return _vc.load_caution_settings()


@pytest.fixture(autouse=True)
def _auto_clear():
    _clear_env()
    yield
    _clear_env()


def _patch_validation(monkeypatch, payload):
    """Patch orchestrate to inject synthetic validation structure.

    The run creation path calls orchestrate(...) which returns a dict with keys
    including 'summary', 'validation', 'equity', etc. We only need 'validation'
    (plus minimal others to satisfy downstream logic). Provide a lightweight
    fake orchestrate that ignores inputs.
    """
    import domain.run.create as create_mod

    def fake_orchestrate(*args, **kwargs):  # signature not critical for test
        return {
            "summary": {"metrics": {"dummy": 1.0}},
            "validation": payload,
            "equity": None,
            "equity_df": None,
            "normalized_equity_df": None,
            "completed_trades": [],
        }

    monkeypatch.setattr(create_mod, "orchestrate", fake_orchestrate)


def _invoke(cfg):
    from domain.run.create import InMemoryRunRegistry, create_or_get

    reg = InMemoryRunRegistry()
    h, rec, detail = create_or_get(cfg, reg)
    return h, rec, detail


def test_t086_disabled_default_threshold(monkeypatch):
    """No env threshold set -> caution disabled even if low p-value present."""
    _patch_validation(
        monkeypatch,
        {
            "summary": {},
            "permutation": {"p_value": 0.001},
            "block_bootstrap": {"p_value": 0.02},
        },
    )
    cfg = _cfg()
    _, rec, _ = _invoke(cfg)
    assert rec.get("validation_caution") is False
    assert rec.get("validation_caution_metrics") == []


def test_t042_threshold_triggers_caution(monkeypatch):
    os.environ["AF_VALIDATION_CAUTION_PVALUE"] = "0.01"
    _refresh_settings()

    _patch_validation(
        monkeypatch,
        {
            "summary": {},
            "permutation": {"p_value": 0.009},  # below threshold
            "block_bootstrap": {"p_value": 0.5},
        },
    )
    cfg = _cfg()
    _, rec, _ = _invoke(cfg)
    assert rec.get("validation_caution") is True
    assert rec.get("validation_caution_metrics") == ["permutation"], rec.get(
        "validation_caution_metrics"
    )


def test_t042_metric_filter(monkeypatch):
    os.environ["AF_VALIDATION_CAUTION_PVALUE"] = "0.05"
    os.environ["AF_VALIDATION_CAUTION_METRICS"] = (
        "permutation"  # filter out block_bootstrap
    )
    settings = _refresh_settings()
    assert settings.metric_filter == ("permutation",)
    from services.validation_caution import compute_caution

    flag, metrics = compute_caution(
        {
            "permutation": 0.5,
            "block_bootstrap": 0.001,
        }
    )
    assert flag is False
    assert metrics == []


def test_t042_no_pvalues_with_threshold(monkeypatch):
    os.environ["AF_VALIDATION_CAUTION_PVALUE"] = "0.05"
    _refresh_settings()

    _patch_validation(monkeypatch, {"summary": {}})  # no p-values
    cfg = _cfg()
    _, rec, _ = _invoke(cfg)
    assert rec.get("validation_caution") is False
    assert rec.get("validation_caution_metrics") == []


def test_t042_no_metrics_passing_filter(monkeypatch):
    os.environ["AF_VALIDATION_CAUTION_PVALUE"] = "0.05"
    os.environ["AF_VALIDATION_CAUTION_METRICS"] = "permutation,monte_carlo_slippage"
    settings = _refresh_settings()
    assert set(settings.metric_filter) == {"permutation", "monte_carlo_slippage"}

    _patch_validation(
        monkeypatch,
        {
            "summary": {},
            "permutation": {"p_value": 0.1},  # above threshold
            "monte_carlo_slippage": {"p_value": 0.2},
            "block_bootstrap": {"p_value": 0.001},  # would trigger but not in filter
        },
    )
    cfg = _cfg()
    _, rec, _ = _invoke(cfg)
    assert rec.get("validation_caution") is False
    assert rec.get("validation_caution_metrics") == []
