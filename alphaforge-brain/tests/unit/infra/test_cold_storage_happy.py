from uuid import uuid4

import pytest

from infra.cold_storage import offload, restore


@pytest.fixture(autouse=True)
def enable_cold_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "local")
    # Point artifact root to tmp path so LocalMirrorProvider writes there
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path))
    run_hash = f"run_{uuid4().hex[:8]}"
    run_dir = tmp_path / run_hash
    run_dir.mkdir(parents=True)
    (run_dir / "equity.csv").write_text("t,nav\n0,1.0", encoding="utf-8")
    (run_dir / "metrics.json").write_text("{}", encoding="utf-8")
    yield run_hash, run_dir


def test_offload_and_restore_round_trip(enable_cold_storage):
    run_hash, run_dir = enable_cold_storage
    files = list(run_dir.glob("*.*"))
    # Offload
    offload(run_hash, files)
    # Originals (except manifest) should be deleted
    remaining = {p.name for p in run_dir.iterdir()}
    # Manifest should exist and original data files removed
    assert "cold_manifest.json" in remaining
    assert "equity.csv" not in remaining and "metrics.json" not in remaining
    # Restore
    restored = restore(run_hash)
    assert restored is True
    restored_files = {p.name for p in run_dir.iterdir()}
    assert {"equity.csv", "metrics.json", "cold_manifest.json"}.issubset(restored_files)


def test_offload_idempotent_no_files(enable_cold_storage):
    run_hash, run_dir = enable_cold_storage
    # Call with empty list -> no manifest written
    offload(run_hash, [])
    assert not (run_dir / "cold_manifest.json").exists()


def test_restore_missing_manifest_returns_false(enable_cold_storage):
    run_hash, run_dir = enable_cold_storage
    # Remove manifest if any and attempt restore
    mp = run_dir / "cold_manifest.json"
    if mp.exists():
        mp.unlink()
    assert restore(run_hash) is False
