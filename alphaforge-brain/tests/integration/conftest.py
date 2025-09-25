# Integration-level conftest to expose fixtures defined in fixtures_manifest.py
# Ensures manifest_loader fixture is discoverable by pytest in integration tests.
from .fixtures_manifest import artifact_hashes, manifest_loader  # noqa: F401
