import io
import sys
from types import ModuleType, SimpleNamespace

import pytest

from infra import cold_storage


@pytest.fixture(autouse=True)
def patch_artifact_root(monkeypatch, tmp_path):
    monkeypatch.setenv("ALPHAFORGEB_ARTIFACT_ROOT", str(tmp_path))
    # ensure enable flag isn't leaking between tests
    monkeypatch.delenv("AF_COLD_STORAGE_ENABLED", raising=False)
    monkeypatch.delenv("AF_COLD_STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("AF_COLD_STORAGE_BUCKET", raising=False)
    monkeypatch.delenv("AF_COLD_STORAGE_PREFIX", raising=False)


def test_provider_s3_missing_bucket_returns_none(monkeypatch):
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "s3")

    class _StubClient:
        def client(self, name):  # pragma: no cover - trivial stub
            assert name == "s3"
            return SimpleNamespace()

    monkeypatch.setitem(sys.modules, "boto3", _StubClient())
    assert cold_storage._provider() is None


def test_provider_s3_returns_stub_with_bucket(monkeypatch):
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("AF_COLD_STORAGE_BUCKET", "bucket-123")

    class _TrackingClient:
        def __init__(self):
            self.put_calls = []
            self.get_calls = []

        def put_object(self, *, Bucket, Key, Body):
            self.put_calls.append((Bucket, Key, Body))

        def get_object(self, *, Bucket, Key):
            self.get_calls.append((Bucket, Key))
            return {"Body": io.BytesIO(b"payload")}

    tracking_client = _TrackingClient()
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=lambda name: tracking_client),
    )

    provider = cold_storage._provider()
    assert provider is not None
    provider.put_object("runs/hash/blob.tar.gz", b"data")
    provider.get_object("runs/hash/blob.tar.gz")
    assert tracking_client.put_calls
    assert tracking_client.get_calls


def test_provider_gcs_returns_stub(monkeypatch):
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "gcs")
    monkeypatch.setenv("AF_COLD_STORAGE_BUCKET", "bucket-gcs")

    class _Bucket:
        def __init__(self):
            self._store = {}

        def blob(self, key):
            bucket = self

            class _Blob:
                def upload_from_string(self, data):
                    bucket._store[key] = data

                def download_as_bytes(self):
                    return bucket._store[key]

            return _Blob()

    bucket = _Bucket()

    storage_module = ModuleType("google.cloud.storage")

    class _StorageClient:
        def bucket(self, name):
            assert name == "bucket-gcs"
            return bucket

    storage_module.Client = lambda: _StorageClient()
    cloud_module = ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = ModuleType("google")
    google_module.cloud = cloud_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

    provider = cold_storage._provider()
    assert provider is not None
    provider.put_object("runs/hash/blob.tar.gz", b"content")
    out = provider.get_object("runs/hash/blob.tar.gz")
    assert out == b"content"


def test_provider_gcs_missing_dependency_returns_none(monkeypatch):
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "gcs")
    monkeypatch.delenv("AF_COLD_STORAGE_BUCKET", raising=False)
    for module_name in [
        "google",
        "google.cloud",
        "google.cloud.storage",
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)
    assert cold_storage._provider() is None


def test_provider_gcs_missing_bucket_returns_none(monkeypatch):
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "gcs")
    monkeypatch.delenv("AF_COLD_STORAGE_BUCKET", raising=False)

    storage_module = ModuleType("google.cloud.storage")

    class _StorageClient:
        def bucket(self, name):  # pragma: no cover - defensive
            raise AssertionError("bucket should not be called when config missing")

    storage_module.Client = lambda: _StorageClient()
    cloud_module = ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = ModuleType("google")
    google_module.cloud = cloud_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

    assert cold_storage._provider() is None


def test_restore_manifest_missing_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "local")
    run_hash = "hash123"
    run_dir = tmp_path / run_hash
    run_dir.mkdir()
    manifest = run_dir / "cold_manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    assert cold_storage.restore(run_hash) is False


def test_restore_handles_corrupted_archive(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_COLD_STORAGE_ENABLED", "1")
    monkeypatch.setenv("AF_COLD_STORAGE_PROVIDER", "local")
    run_hash = "hash456"
    run_dir = tmp_path / run_hash
    run_dir.mkdir()
    mirror_dir = tmp_path / "cold-mirror" / "runs" / run_hash
    mirror_dir.mkdir(parents=True)
    manifest_path = run_dir / "cold_manifest.json"
    manifest_path.write_text(
        f'{{"key": "runs/{run_hash}/bad.tar.gz"}}', encoding="utf-8"
    )
    (mirror_dir / "bad.tar.gz").write_bytes(b"not a valid gzip stream")

    assert cold_storage.restore(run_hash) is False
