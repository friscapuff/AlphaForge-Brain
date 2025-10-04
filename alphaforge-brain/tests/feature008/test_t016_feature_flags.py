from __future__ import annotations

import importlib

import pytest

MODULE = "settings.flags"


@pytest.mark.unit
@pytest.mark.feature008
def test_t016_flags_default_false(monkeypatch):
    # Ensure env vars not set
    for k in ["AF_UNIFIED_TRADES", "AF_EQUITY_NORMALIZER_V2"]:
        monkeypatch.delenv(k, raising=False)
    mod = importlib.import_module(MODULE)
    # Clear caches (lru cached functions)
    mod.is_unified_trades_enabled.cache_clear()  # type: ignore[attr-defined]
    mod.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore[attr-defined]
    assert mod.is_unified_trades_enabled() is False
    assert mod.is_equity_normalizer_v2_enabled() is False


@pytest.mark.unit
@pytest.mark.feature008
def test_t016_flags_toggle_true(monkeypatch):
    monkeypatch.setenv("AF_UNIFIED_TRADES", "1")
    monkeypatch.setenv("AF_EQUITY_NORMALIZER_V2", "true")
    mod = importlib.reload(importlib.import_module(MODULE))
    # clear caches then test
    mod.is_unified_trades_enabled.cache_clear()  # type: ignore[attr-defined]
    mod.is_equity_normalizer_v2_enabled.cache_clear()  # type: ignore[attr-defined]
    assert mod.is_unified_trades_enabled() is True
    assert mod.is_equity_normalizer_v2_enabled() is True
