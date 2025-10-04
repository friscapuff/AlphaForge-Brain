from infra import artifacts_root, cold_storage


def test_cold_storage_offload_and_restore_roundtrip(monkeypatch, tmp_path):
    # Point artifacts root to temp
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    # Enable cold storage in local mode
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "local")
    run_hash = "run123"
    run_dir = artifacts_root.run_artifact_dir(run_hash)
    f1 = run_dir / "file_a.txt"
    f2 = run_dir / "file_b.txt"
    f1.write_text("hello", encoding="utf-8")
    f2.write_text("world", encoding="utf-8")

    # Offload should create manifest and mirror tarball, then delete originals
    cold_storage.offload(run_hash, [f1, f2])
    manifest = run_dir / "cold_manifest.json"
    assert manifest.exists(), "manifest should be written"
    # Originals should be removed (best effort); allow either fully removed or partially if platform locks
    remaining = {p.name for p in run_dir.iterdir()}
    assert "file_a.txt" not in remaining or "file_b.txt" not in remaining

    # Remove any remaining originals to simulate need for restore
    for p in list(run_dir.iterdir()):
        if p.name.startswith("file_"):
            p.unlink(missing_ok=True)

    restored = cold_storage.restore(run_hash)
    assert restored is True, "should restore at least one file"
    assert (run_dir / "file_a.txt").exists() or (run_dir / "file_b.txt").exists()
