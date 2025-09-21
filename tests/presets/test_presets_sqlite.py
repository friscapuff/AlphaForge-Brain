from __future__ import annotations

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from domain.presets.service import SQLitePresetService, get_preset_service


def test_sqlite_backend_create_list_get_delete(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path = tmp_path / "presets_test.db"
    monkeypatch.setenv("ALPHAFORGE_PRESET_BACKEND", "sqlite")
    monkeypatch.setenv("ALPHAFORGE_PRESET_DB", str(db_path))

    svc = get_preset_service()
    assert isinstance(svc, SQLitePresetService)

    pid, created = svc.create("dual_sma_default", {"fast": 5, "slow": 15})
    assert created is True
    pid2, created2 = svc.create("dual_sma_default", {"fast": 5, "slow": 15})
    assert pid2 == pid and created2 is False

    items = svc.list()
    assert any(it["preset_id"] == pid for it in items)

    fetched = svc.get(pid)
    assert fetched and fetched["name"] == "dual_sma_default"

    deleted = svc.delete(pid)
    assert deleted is True
    assert svc.get(pid) is None


def test_sqlite_backend_env_switch_reinit(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path1 = tmp_path / "p1.db"
    db_path2 = tmp_path / "p2.db"
    monkeypatch.setenv("ALPHAFORGE_PRESET_BACKEND", "sqlite")
    monkeypatch.setenv("ALPHAFORGE_PRESET_DB", str(db_path1))
    svc1 = get_preset_service()
    pid, _ = svc1.create("x", {"a": 1})
    assert svc1.get(pid)

    # Force new process style re-init by clearing module-level cache
    from domain.presets import service as mod
    mod._service = None

    monkeypatch.setenv("ALPHAFORGE_PRESET_DB", str(db_path2))
    svc2 = get_preset_service()
    assert svc2 is not svc1
    pid2, _ = svc2.create("y", {"b": 2})
    assert svc2.get(pid2)
