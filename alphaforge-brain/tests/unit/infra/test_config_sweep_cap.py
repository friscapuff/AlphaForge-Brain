from __future__ import annotations

from infra.config import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_sweep_combination_cap_defaults(monkeypatch) -> None:
    monkeypatch.delenv("AF_OPTIMIZATION_MAX_COMBINATIONS", raising=False)
    monkeypatch.delenv("APP_OPTIMIZATION_MAX_COMBINATIONS", raising=False)
    _reset_settings_cache()

    settings = get_settings()

    assert settings.optimization_max_combinations == 0
    assert settings.sweep_combination_cap == 0


def test_sweep_combination_cap_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("AF_OPTIMIZATION_MAX_COMBINATIONS", "37")
    _reset_settings_cache()

    settings = get_settings()

    assert settings.optimization_max_combinations == 37
    assert settings.sweep_combination_cap == 37

    monkeypatch.delenv("AF_OPTIMIZATION_MAX_COMBINATIONS", raising=False)
    monkeypatch.setenv("APP_OPTIMIZATION_MAX_COMBINATIONS", "15")
    _reset_settings_cache()

    fallback_settings = get_settings()

    assert fallback_settings.sweep_combination_cap == 15

    monkeypatch.delenv("APP_OPTIMIZATION_MAX_COMBINATIONS", raising=False)
    _reset_settings_cache()
