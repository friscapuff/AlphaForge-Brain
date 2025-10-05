from __future__ import annotations

from importlib import import_module

from infra.version_pins import PINNED


def test_numpy_version_guard() -> None:
    np = import_module("numpy")
    expected = PINNED.get("numpy")
    assert expected is not None, "Pinned numpy version missing"
    actual = getattr(np, "__version__", None)
    assert (
        actual == expected
    ), f"NumPy version mismatch: expected {expected}, got {actual}"  # deterministic failure if drift
