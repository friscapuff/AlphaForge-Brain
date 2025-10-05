import os
from datetime import datetime, timezone

from infra.credentials import Credential, get_env_credential
from infra.utils.time import to_utc_ms


def test_to_utc_ms_basic():
    dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    ms = to_utc_ms(dt)
    assert isinstance(ms, int)
    assert ms > 0


def test_get_env_credential_present(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    cred = get_env_credential("API_KEY")
    assert isinstance(cred, Credential)
    assert cred.value == "secret"


def test_get_env_credential_missing():
    # ensure var not set
    if "MISSING_KEY" in os.environ:
        del os.environ["MISSING_KEY"]
    cred = get_env_credential("MISSING_KEY")
    assert cred is None
